"""
Load Balancer - Dynamic load balancing for providers.

This module provides:
- Weight-based traffic distribution
- Real-time performance scoring
- Automatic weight adjustment
- Region-aware routing
"""
import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import statistics

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.provider import Provider, ProviderStatus
from src.db.session import SessionManager
from src.config.redis_config import RedisConfig, RedisKeys
from src.services.redis_client import RedisService


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategy types."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_LATENCY = "least_latency"
    REGION_AWARE = "region_aware"
    ADAPTIVE = "adaptive"


@dataclass
class ProviderMetrics:
    """Real-time provider metrics."""
    provider_id: int
    name: str
    weight: int
    current_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    last_error: Optional[str] = None
    last_updated: float = field(default_factory=time.time)
    region: Optional[str] = None
    is_healthy: bool = True


@dataclass
class LoadBalancingDecision:
    """Load balancing decision result."""
    provider_id: int
    provider_name: str
    strategy: LoadBalancingStrategy
    reason: str
    estimated_latency_ms: float
    confidence: float


class MetricsCollector:
    """
    Collects and aggregates provider metrics.

    Sources:
    - Redis cache (real-time)
    - Database (historical)
    - Health checks (current status)
    """

    def __init__(self):
        """Initialize the metrics collector."""
        self._metrics_cache: Dict[int, ProviderMetrics] = {}
        self._cache_ttl = 30  # seconds
        self._latency_window_size = 100

    async def get_provider_metrics(
        self,
        provider_id: int,
        force_refresh: bool = False,
    ) -> ProviderMetrics:
        """
        Get metrics for a provider.

        Args:
            provider_id: Provider ID
            force_refresh: Force refresh from database

        Returns:
            ProviderMetrics: Provider metrics
        """
        # Check cache
        if not force_refresh and provider_id in self._metrics_cache:
            cached = self._metrics_cache[provider_id]
            if time.time() - cached.last_updated < self._cache_ttl:
                return cached

        # Fetch from database and Redis
        from src.models.provider import Provider

        provider = await SessionManager.execute_get_one(
            select(Provider).where(Provider.id == provider_id)
        )

        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        # Get real-time metrics from Redis
        redis_key = RedisKeys.provider_metrics(provider_id)
        redis_metrics = await RedisService.get(redis_key)

        if redis_metrics:
            import json
            metrics_data = json.loads(redis_metrics)
            metrics = ProviderMetrics(
                provider_id=provider.id,
                name=provider.name,
                weight=provider.weight,
                current_connections=metrics_data.get("current_connections", 0),
                total_requests=metrics_data.get("total_requests", 0),
                successful_requests=metrics_data.get("successful_requests", 0),
                failed_requests=metrics_data.get("failed_requests", 0),
                avg_latency_ms=metrics_data.get("avg_latency_ms", 0.0),
                success_rate=metrics_data.get("success_rate", 1.0),
                last_error=metrics_data.get("last_error"),
                region=provider.region,
                is_healthy=metrics_data.get("is_healthy", True),
            )
        else:
            # Default metrics if no Redis data
            metrics = ProviderMetrics(
                provider_id=provider.id,
                name=provider.name,
                weight=provider.weight,
                region=provider.region,
                is_healthy=provider.status == ProviderStatus.ACTIVE,
            )

        # Update cache
        self._metrics_cache[provider_id] = metrics

        return metrics

    async def update_provider_metrics(
        self,
        provider_id: int,
        success: bool,
        latency_ms: int,
        error: Optional[str] = None,
    ) -> None:
        """
        Update metrics after a request.

        Args:
            provider_id: Provider ID
            success: Whether request was successful
            latency_ms: Request latency in milliseconds
            error: Optional error message
        """
        metrics = await self.get_provider_metrics(provider_id, force_refresh=True)

        # Update metrics
        metrics.total_requests += 1
        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
            metrics.last_error = error

        # Update average latency (moving average)
        if metrics.total_requests == 1:
            metrics.avg_latency_ms = latency_ms
        else:
            alpha = 0.2  # Smoothing factor
            metrics.avg_latency_ms = (
                alpha * latency_ms +
                (1 - alpha) * metrics.avg_latency_ms
            )

        # Update success rate
        metrics.success_rate = (
            metrics.successful_requests / metrics.total_requests
        )

        # Update health status
        if not success and metrics.failed_requests > 5:
            metrics.is_healthy = False
        elif success and metrics.success_rate > 0.9:
            metrics.is_healthy = True

        metrics.last_updated = time.time()

        # Save to Redis
        import json
        redis_key = RedisKeys.provider_metrics(provider_id)
        await RedisService.set(
            redis_key,
            json.dumps({
                "current_connections": metrics.current_connections,
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "avg_latency_ms": metrics.avg_latency_ms,
                "success_rate": metrics.success_rate,
                "last_error": metrics.last_error,
                "is_healthy": metrics.is_healthy,
            }),
            ttl=300,  # 5 minutes
        )

        # Update cache
        self._metrics_cache[provider_id] = metrics


class LoadBalancer:
    """
    Load balancer for provider selection.

    Features:
    - Multiple load balancing strategies
    - Real-time metrics-based decisions
    - Automatic weight adjustment
    - Health awareness
    """

    def __init__(self):
        """Initialize the load balancer."""
        self.metrics_collector = MetricsCollector()
        self._round_robin_index = 0
        self._connection_counts: Dict[int, int] = {}

    async def select_provider(
        self,
        provider_ids: List[int],
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE,
        user_region: Optional[str] = None,
        exclude_unhealthy: bool = True,
    ) -> LoadBalancingDecision:
        """
        Select the best provider based on strategy.

        Args:
            provider_ids: List of provider IDs to choose from
            strategy: Load balancing strategy
            user_region: Optional user region for region-aware routing
            exclude_unhealthy: Whether to exclude unhealthy providers

        Returns:
            LoadBalancingDecision: Selection decision
        """
        if not provider_ids:
            raise RuntimeError("No providers available")

        # Get metrics for all providers
        all_metrics = []
        for provider_id in provider_ids:
            try:
                metrics = await self.metrics_collector.get_provider_metrics(provider_id)
                all_metrics.append(metrics)
            except Exception:
                continue

        # Filter unhealthy providers if requested
        if exclude_unhealthy:
            all_metrics = [m for m in all_metrics if m.is_healthy]

        if not all_metrics:
            # Fallback: include unhealthy providers
            all_metrics = [
                await self.metrics_collector.get_provider_metrics(pid)
                for pid in provider_ids
            ]

        # Apply strategy
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._round_robin(all_metrics)
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin(all_metrics)
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return await self._least_connections(all_metrics)
        elif strategy == LoadBalancingStrategy.LEAST_LATENCY:
            return await self._least_latency(all_metrics)
        elif strategy == LoadBalancingStrategy.REGION_AWARE:
            return await self._region_aware(all_metrics, user_region)
        else:  # ADAPTIVE
            return await self._adaptive(all_metrics)

    async def _round_robin(
        self,
        metrics_list: List[ProviderMetrics],
    ) -> LoadBalancingDecision:
        """Round-robin selection."""
        selected = metrics_list[self._round_robin_index % len(metrics_list)]
        self._round_robin_index += 1

        return LoadBalancingDecision(
            provider_id=selected.provider_id,
            provider_name=selected.name,
            strategy=LoadBalancingStrategy.ROUND_ROBIN,
            reason="Round-robin selection",
            estimated_latency_ms=selected.avg_latency_ms,
            confidence=0.5,
        )

    async def _weighted_round_robin(
        self,
        metrics_list: List[ProviderMetrics],
    ) -> LoadBalancingDecision:
        """Weighted round-robin based on provider weight."""
        total_weight = sum(m.weight for m in metrics_list)

        # Calculate weighted index
        weighted_index = self._round_robin_index % total_weight
        current_weight = 0

        selected = None
        for metrics in metrics_list:
            current_weight += metrics.weight
            if weighted_index < current_weight:
                selected = metrics
                break

        if selected is None:
            selected = metrics_list[0]

        self._round_robin_index += 1

        return LoadBalancingDecision(
            provider_id=selected.provider_id,
            provider_name=selected.name,
            strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
            reason=f"Weighted round-robin (weight={selected.weight})",
            estimated_latency_ms=selected.avg_latency_ms,
            confidence=0.7,
        )

    async def _least_connections(
        self,
        metrics_list: List[ProviderMetrics],
    ) -> LoadBalancingDecision:
        """Select provider with least connections."""
        # Sort by current connections
        sorted_metrics = sorted(metrics_list, key=lambda m: m.current_connections)
        selected = sorted_metrics[0]

        # Increment connection count
        selected.current_connections += 1
        self._connection_counts[selected.provider_id] = selected.current_connections

        return LoadBalancingDecision(
            provider_id=selected.provider_id,
            provider_name=selected.name,
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
            reason=f"Least connections ({selected.current_connections} active)",
            estimated_latency_ms=selected.avg_latency_ms,
            confidence=0.8,
        )

    async def _least_latency(
        self,
        metrics_list: List[ProviderMetrics],
    ) -> LoadBalancingDecision:
        """Select provider with lowest average latency."""
        # Filter providers with sufficient data
        valid_metrics = [
            m for m in metrics_list
            if m.total_requests >= 5  # Need at least 5 requests
        ]

        if not valid_metrics:
            # Fallback to weighted round-robin
            return await self._weighted_round_robin(metrics_list)

        # Sort by latency
        sorted_metrics = sorted(valid_metrics, key=lambda m: m.avg_latency_ms)
        selected = sorted_metrics[0]

        return LoadBalancingDecision(
            provider_id=selected.provider_id,
            provider_name=selected.name,
            strategy=LoadBalancingStrategy.LEAST_LATENCY,
            reason=f"Lowest latency ({selected.avg_latency_ms:.1f}ms)",
            estimated_latency_ms=selected.avg_latency_ms,
            confidence=0.9,
        )

    async def _region_aware(
        self,
        metrics_list: List[ProviderMetrics],
        user_region: Optional[str],
    ) -> LoadBalancingDecision:
        """Select provider based on region proximity."""
        if not user_region:
            # No region info, fallback to weighted round-robin
            return await self._weighted_round_robin(metrics_list)

        # Find providers in same or nearby region
        same_region = [m for m in metrics_list if m.region == user_region]

        if same_region:
            # Use least latency within same region
            selected = min(same_region, key=lambda m: m.avg_latency_ms)

            return LoadBalancingDecision(
                provider_id=selected.provider_id,
                provider_name=selected.name,
                strategy=LoadBalancingStrategy.REGION_AWARE,
                reason=f"Same region ({user_region})",
                estimated_latency_ms=selected.avg_latency_ms,
                confidence=0.95,
            )

        # No providers in same region, fallback to weighted
        return await self._weighted_round_robin(metrics_list)

    async def _adaptive(
        self,
        metrics_list: List[ProviderMetrics],
    ) -> LoadBalancingDecision:
        """
        Adaptive strategy combining multiple factors.

        Scoring:
        - Success rate: 40% weight
        - Latency: 30% weight
        - Current connections: 20% weight
        - Weight: 10% weight
        """
        def calculate_score(metrics: ProviderMetrics) -> float:
            """Calculate composite score."""
            # Success rate score (0-1)
            success_score = metrics.success_rate

            # Latency score (inverse, normalized)
            # Lower latency = higher score
            max_latency = max(m.avg_latency_ms for m in metrics_list) or 100
            if max_latency > 0:
                latency_score = 1 - (metrics.avg_latency_ms / max_latency)
            else:
                latency_score = 1.0

            # Connections score (inverse)
            max_connections = max(m.current_connections for m in metrics_list) or 1
            if max_connections > 0:
                connections_score = 1 - (metrics.current_connections / max_connections)
            else:
                connections_score = 1.0

            # Weight score (normalized)
            max_weight = max(m.weight for m in metrics_list) or 1
            weight_score = metrics.weight / max_weight if max_weight > 0 else 0

            # Composite score
            score = (
                success_score * 0.40 +
                latency_score * 0.30 +
                connections_score * 0.20 +
                weight_score * 0.10
            )

            return score

        # Calculate scores for all providers
        scored = [
            (metrics, calculate_score(metrics))
            for metrics in metrics_list
        ]

        # Select highest score
        selected, score = max(scored, key=lambda x: x[1])

        return LoadBalancingDecision(
            provider_id=selected.provider_id,
            provider_name=selected.name,
            strategy=LoadBalancingStrategy.ADAPTIVE,
            reason=f"Adaptive (score={score:.2f}, success={selected.success_rate:.2f}, latency={selected.avg_latency_ms:.1f}ms)",
            estimated_latency_ms=selected.avg_latency_ms,
            confidence=score,
        )

    async def release_connection(self, provider_id: int) -> None:
        """
        Release a connection after request completion.

        Args:
            provider_id: Provider ID
        """
        if provider_id in self._connection_counts:
            self._connection_counts[provider_id] -= 1
            if self._connection_counts[provider_id] <= 0:
                del self._connection_counts[provider_id]


class AutoWeightAdjuster:
    """
    Automatically adjusts provider weights based on performance.

    Adjusts weights to:
    - Increase weight for better performing providers
    - Decrease weight for underperforming providers
    - Maintain balance in the system
    """

    def __init__(self, load_balancer: LoadBalancer):
        """Initialize the auto weight adjuster."""
        self.load_balancer = load_balancer
        self._adjustment_interval = 300  # 5 minutes
        self._min_weight = 10
        self._max_weight = 1000
        self._adjustment_factor = 0.1  # 10% adjustment

    async def auto_adjust_weights(
        self,
        provider_ids: List[int],
    ) -> Dict[int, int]:
        """
        Automatically adjust provider weights.

        Args:
            provider_ids: List of provider IDs

        Returns:
            Dict mapping provider_id to new weight
        """
        adjustments = {}

        for provider_id in provider_ids:
            metrics = await self.load_balancer.metrics_collector.get_provider_metrics(
                provider_id,
                force_refresh=True,
            )

            # Calculate performance score
            if metrics.total_requests < 10:
                # Not enough data, skip
                continue

            # Performance factors
            success_factor = metrics.success_rate
            latency_factor = max(0, 1 - (metrics.avg_latency_ms / 1000))  # Normalize to <1s

            # Composite score (0-1)
            performance_score = (success_factor + latency_factor) / 2

            # Calculate target weight
            current_weight = metrics.weight

            if performance_score > 0.8:
                # High performance, increase weight
                new_weight = int(current_weight * (1 + self._adjustment_factor))
            elif performance_score < 0.5:
                # Low performance, decrease weight
                new_weight = int(current_weight * (1 - self._adjustment_factor))
            else:
                # Average performance, keep current
                new_weight = current_weight

            # Clamp to min/max
            new_weight = max(self._min_weight, min(self._max_weight, new_weight))

            if new_weight != current_weight:
                adjustments[provider_id] = new_weight

                # Update database (would need async DB session)
                # await self._update_provider_weight(provider_id, new_weight)

        return adjustments


# Global instances
metrics_collector = MetricsCollector()
load_balancer = LoadBalancer()
auto_weight_adjuster = AutoWeightAdjuster(load_balancer)
