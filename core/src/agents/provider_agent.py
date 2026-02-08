"""
Provider Agent - Manages provider health and performance monitoring.
"""
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.redis_config import RedisConfig, RedisKeys
from src.config.settings import settings
from src.providers.base import IProvider, HealthStatus
from src.models.provider import Provider, ProviderStatus, ProviderPerformanceHistory
from src.models.routing import RoutingDecision
from src.db.session import SessionManager
from src.utils.logging import logger


@dataclass
class ProviderMetrics:
    """Provider metrics data."""
    provider_id: int
    provider_name: str
    is_healthy: bool
    latency_ms: Optional[int]
    success_rate: float
    total_requests: int
    failed_requests: int
    last_error: Optional[str]


class ProviderAgent:
    """
    Provider Agent monitors provider health and performance.

    Features:
    - Health checks for all providers
    - Performance tracking
    - Automatic failover
    - Performance history
    """

    _instance: Optional["ProviderAgent"] = None

    def __new__(cls) -> "ProviderAgent":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the provider agent."""
        if self._initialized:
            return

        self._initialized = True
        self._providers: Dict[int, IProvider] = {}
        self._metrics_cache: Dict[int, ProviderMetrics] = {}
        self._last_check_time: Dict[int, datetime] = {}

    async def initialize(self) -> None:
        """Initialize the provider agent."""
        # Load active providers
        await self._load_providers()

    async def _load_providers(self) -> None:
        """Load active providers from database."""
        from sqlalchemy import select

        providers = await SessionManager.execute_select(
            select(Provider).where(Provider.status == ProviderStatus.ACTIVE)
        )

        for provider in providers:
            try:
                # Create provider instance
                provider_instance = await self._create_provider_instance(provider)
                self._providers[provider.id] = provider_instance
                logger.info(f"Loaded provider: {provider.name} (ID: {provider.id})")
            except Exception as e:
                logger.error(f"Failed to load provider {provider.name}: {e}")

    async def _create_provider_instance(self, provider: Provider) -> IProvider:
        """Create provider instance from database record."""
        from src.utils.encryption import EncryptionManager
        from src.providers.factory import ProviderFactory

        # Decrypt API key
        api_key = EncryptionManager.decrypt(provider.api_key_encrypted)

        # Create provider based on type
        provider_type = provider.provider_type.value
        if provider_type == "openai":
            return ProviderFactory.create_provider(
                "openai",
                api_key=api_key,
                base_url=provider.base_url,
                organization=provider.organization,
                timeout=provider.timeout,
            )
        elif provider_type == "anthropic":
            return ProviderFactory.create_provider(
                "anthropic",
                api_key=api_key,
                base_url=provider.base_url,
                timeout=provider.timeout,
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    async def health_check_all(self) -> Dict[int, ProviderMetrics]:
        """
        Perform health checks on all providers.

        Returns:
            Dict[int, ProviderMetrics]: Provider ID to metrics mapping
        """
        from sqlalchemy import select

        # Get all providers
        providers = await SessionManager.execute_select(select(Provider))

        results = {}

        for provider in providers:
            try:
                provider_instance = self._providers.get(provider.id)
                if not provider_instance:
                    # Try to create provider instance
                    try:
                        provider_instance = await self._create_provider_instance(provider)
                        self._providers[provider.id] = provider_instance
                    except Exception as e:
                        logger.error(f"Failed to create provider instance: {e}")
                        results[provider.id] = ProviderMetrics(
                            provider_id=provider.id,
                            provider_name=provider.name,
                            is_healthy=False,
                            latency_ms=None,
                            success_rate=0.0,
                            total_requests=0,
                            failed_requests=0,
                            last_error="Failed to initialize",
                        )
                        continue

                # Perform health check
                health = await provider_instance.health_check()

                # Get performance stats
                performance = await self._get_provider_performance(provider.id)

                metrics = ProviderMetrics(
                    provider_id=provider.id,
                    provider_name=provider.name,
                    is_healthy=health.is_healthy,
                    latency_ms=health.latency_ms,
                    success_rate=performance.get("success_rate", 1.0),
                    total_requests=performance.get("total_requests", 0),
                    failed_requests=performance.get("failed_requests", 0),
                    last_error=health.error_message,
                )

                results[provider.id] = metrics
                self._metrics_cache[provider.id] = metrics
                self._last_check_time[provider.id] = datetime.now(timezone.utc)

                # Update provider status in database
                await self._update_provider_status(
                    provider.id,
                    health.is_healthy,
                    health.error_message,
                )

                logger.info(
                    f"Health check for {provider.name}: "
                    f"{'healthy' if health.is_healthy else 'unhealthy'}, "
                    f"latency: {health.latency_ms}ms"
                )

            except Exception as e:
                logger.error(f"Health check failed for {provider.name}: {e}")
                results[provider.id] = ProviderMetrics(
                    provider_id=provider.id,
                    provider_name=provider.name,
                    is_healthy=False,
                    latency_ms=None,
                    success_rate=0.0,
                    total_requests=0,
                    failed_requests=0,
                    last_error=str(e),
                )

        return results

    async def health_check(self, provider_id: int) -> Optional[HealthStatus]:
        """
        Perform health check on a specific provider.

        Args:
            provider_id: Provider ID to check

        Returns:
            Optional[HealthStatus]: Health status if provider exists
        """
        provider = self._providers.get(provider_id)
        if not provider:
            return None

        return await provider.health_check()

    async def _get_provider_performance(self, provider_id: int) -> Dict[str, Any]:
        """
        Get performance statistics for a provider.

        Args:
            provider_id: Provider ID

        Returns:
            dict: Performance statistics
        """
        from sqlalchemy import select, func, and_

        # Get performance from last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        result = await SessionManager.execute_get_one(
            select(
                func.count(RoutingDecision.id).label("total_requests"),
                func.sum(
                    RoutingDecision.success.cast(Integer)
                ).label("successful_requests"),
                func.avg(RoutingDecision.latency_ms).label("avg_latency"),
            ).where(
                and_(
                    RoutingDecision.provider_id == provider_id,
                    RoutingDecision.created_at >= one_hour_ago,
                )
            )
        )

        if not result or result.total_requests == 0:
            return {
                "success_rate": 1.0,
                "total_requests": 0,
                "failed_requests": 0,
                "avg_latency": None,
            }

        successful = result.successful_requests or 0
        total = result.total_requests
        failed = total - successful

        return {
            "success_rate": successful / total if total > 0 else 1.0,
            "total_requests": total,
            "failed_requests": failed,
            "avg_latency": float(result.avg_latency) if result.avg_latency else None,
        }

    async def _update_provider_status(
        self,
        provider_id: int,
        is_healthy: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Update provider status in database.

        Args:
            provider_id: Provider ID
            is_healthy: Whether provider is healthy
            error_message: Optional error message
        """
        from sqlalchemy import update

        new_status = ProviderStatus.ACTIVE if is_healthy else ProviderStatus.UNHEALTHY

        await SessionManager.execute_update(
            update(Provider)
            .where(Provider.id == provider_id)
            .values(status=new_status)
        )

    async def record_performance(
        self,
        provider_id: int,
        model_id: str,
        latency_ms: int,
        success: bool,
    ) -> None:
        """
        Record provider performance for history tracking.

        Args:
            provider_id: Provider ID
            model_id: Model ID
            latency_ms: Response latency in milliseconds
            success: Whether request was successful
        """
        # Update in-memory cache
        cache_key = f"{provider_id}:{model_id}"

        if cache_key not in self._performance_cache:
            self._performance_cache[cache_key] = {
                "latencies": [],
                "success_count": 0,
                "fail_count": 0,
            }

        cache = self._performance_cache[cache_key]
        cache["latencies"].append(latency_ms)

        if success:
            cache["success_count"] += 1
        else:
            cache["fail_count"] += 1

        # Keep only last 100 latency measurements
        if len(cache["latencies"]) > 100:
            cache["latencies"] = cache["latencies"][-100:]

        # Periodically write to database (every 100 requests or 5 minutes)
        total_requests = cache["success_count"] + cache["fail_count"]
        if total_requests % 100 == 0:
            await self._persist_performance_history(provider_id, model_id)

    async def _persist_performance_history(
        self,
        provider_id: int,
        model_id: str,
    ) -> None:
        """
        Persist performance history to database.

        Args:
            provider_id: Provider ID
            model_id: Model ID
        """
        cache_key = f"{provider_id}:{model_id}"
        cache = self._performance_cache.get(cache_key)

        if not cache or not cache["latencies"]:
            return

        # Calculate metrics
        total_requests = cache["success_count"] + cache["fail_count"]
        avg_latency = sum(cache["latencies"]) / len(cache["latencies"])
        success_rate = cache["success_count"] / total_requests if total_requests > 0 else 1.0

        # Create performance history record
        history = ProviderPerformanceHistory(
            provider_id=provider_id,
            model_id=model_id,
            avg_latency_ms=int(avg_latency),
            success_rate=round(success_rate, 2),
            total_requests=total_requests,
            failed_requests=cache["fail_count"],
        )

        await SessionManager.execute_insert(history)

        # Clear cache
        del self._performance_cache[cache_key]

    async def get_best_provider(
        self,
        provider_ids: Optional[list[int]] = None,
    ) -> Optional[int]:
        """
        Get the best provider based on performance metrics.

        Args:
            provider_ids: List of provider IDs to consider (None for all)

        Returns:
            Optional[int]: Best provider ID
        """
        # Get all active providers
        from sqlalchemy import select

        if provider_ids:
            providers = await SessionManager.execute_select(
                select(Provider).where(
                    and_(
                        Provider.id.in_(provider_ids),
                        Provider.status == ProviderStatus.ACTIVE,
                    )
                )
            )
        else:
            providers = await SessionManager.execute_select(
                select(Provider).where(Provider.status == ProviderStatus.ACTIVE)
            )

        if not providers:
            return None

        # Sort by priority and then by success rate
        best_provider = None
        best_score = -1

        for provider in providers:
            metrics = self._metrics_cache.get(provider.id)

            if not metrics:
                score = 0.5  # Default score for new providers
            else:
                # Score based on health, success rate, and latency
                health_score = 1.0 if metrics.is_healthy else 0.0
                success_score = metrics.success_rate
                latency_score = 1.0
                if metrics.latency_ms:
                    if metrics.latency_ms < 500:
                        latency_score = 1.0
                    elif metrics.latency_ms < 1000:
                        latency_score = 0.8
                    elif metrics.latency_ms < 2000:
                        latency_score = 0.5
                    else:
                        latency_score = 0.2

                score = (health_score * 0.4 + success_score * 0.4 + latency_score * 0.2)

            # Apply priority
            score = score + (provider.priority / 1000)

            if score > best_score:
                best_score = score
                best_provider = provider.id

        return best_provider

    async def refresh_providers(self) -> None:
        """Refresh provider instances from database."""
        logger.info("Refreshing providers...")
        self._providers.clear()
        self._metrics_cache.clear()
        await self._load_providers()

    async def get_provider_instance(self, provider_id: int) -> Optional[IProvider]:
        """
        Get provider instance by ID.

        Args:
            provider_id: Provider ID

        Returns:
            Optional[IProvider]: Provider instance or None
        """
        return self._providers.get(provider_id)

    def get_all_providers(self) -> Dict[int, IProvider]:
        """Get all loaded provider instances."""
        return self._providers.copy()

    async def close_all(self) -> None:
        """Close all provider instances."""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                try:
                    await provider.close()
                except Exception as e:
                    logger.error(f"Error closing provider: {e}")

        self._providers.clear()
        self._metrics_cache.clear()
        self._performance_cache.clear()


# Global instance
provider_agent = ProviderAgent()
