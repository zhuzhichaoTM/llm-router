"""
Failover Manager - Intelligent fault detection and automatic failover.

This module provides:
- Health check monitoring
- Automatic failure detection (<3 seconds)
- Automatic provider switching
- Progressive recovery
- Circuit breaker pattern
"""
import asyncio
import time
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.provider import Provider, ProviderStatus
from src.db.session import SessionManager
from src.config.redis_config import RedisConfig, RedisKeys
from src.services.redis_client import RedisService
from src.providers.base import IProvider, HealthStatus


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes before closing
    timeout_seconds: int = 60  # Seconds before attempting recovery
    half_open_max_calls: int = 3  # Max calls in half-open state


@dataclass
class ProviderHealth:
    """Provider health status."""
    provider_id: int
    name: str
    is_healthy: bool
    circuit_state: CircuitState
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_check_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    error_message: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class FailoverDecision:
    """Failover decision result."""
    should_failover: bool
    from_provider_id: Optional[int]
    to_provider_id: Optional[int]
    reason: str
    original_provider_healthy: bool
    confidence: float


class HealthChecker:
    """
    Performs health checks on providers.

    Features:
    - Asynchronous health checks
    - Configurable intervals
    - Timeout handling
    - Graceful degradation
    """

    def __init__(self):
        """Initialize the health checker."""
        self._check_interval = 30  # seconds
        self._check_timeout = 10  # seconds
        self._health_status: Dict[int, ProviderHealth] = {}
        self._running = False
        self._check_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start background health checking."""
        if self._running:
            return

        self._running = True
        self._check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self) -> None:
        """Stop background health checking."""
        self._running = False

        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                await self._check_all_providers()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                print(f"Health check error: {e}")
                await asyncio.sleep(5)

    async def _check_all_providers(self) -> None:
        """Check health of all active providers."""
        from src.models.provider import Provider
        from src.agents.provider_agent import provider_agent

        providers = await SessionManager.execute_select(
            select(Provider).where(Provider.status == ProviderStatus.ACTIVE)
        )

        for provider in providers:
            try:
                # Get provider instance
                provider_instance = await provider_agent.get_provider(provider.id)

                if not provider_instance:
                    continue

                # Perform health check with timeout
                health = await asyncio.wait_for(
                    provider_instance.health_check(),
                    timeout=self._check_timeout,
                )

                # Update health status
                await self._update_health_status(
                    provider_id=provider.id,
                    is_healthy=health.is_healthy,
                    latency_ms=health.latency_ms,
                    error_message=health.error_message,
                )

            except asyncio.TimeoutError:
                await self._update_health_status(
                    provider_id=provider.id,
                    is_healthy=False,
                    error_message="Health check timeout",
                )
            except Exception as e:
                await self._update_health_status(
                    provider_id=provider.id,
                    is_healthy=False,
                    error_message=str(e),
                )

    async def _update_health_status(
        self,
        provider_id: int,
        is_healthy: bool,
        latency_ms: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Update health status for a provider.

        Args:
            provider_id: Provider ID
            is_healthy: Whether provider is healthy
            latency_ms: Health check latency
            error_message: Optional error message
        """
        from src.models.provider import Provider

        # Get provider name
        provider = await SessionManager.execute_get_one(
            select(Provider).where(Provider.id == provider_id)
        )

        # Get or create health status
        if provider_id not in self._health_status:
            self._health_status[provider_id] = ProviderHealth(
                provider_id=provider_id,
                name=provider.name if provider else "Unknown",
                is_healthy=is_healthy,
                circuit_state=CircuitState.CLOSED,
            )

        health = self._health_status[provider_id]
        now = time.time()

        if is_healthy:
            health.success_count += 1
            health.consecutive_failures = 0
            health.consecutive_successes += 1
            health.last_success_time = now
            health.error_message = None
        else:
            health.failure_count += 1
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            health.last_failure_time = now
            health.error_message = error_message

        health.is_healthy = is_healthy
        health.latency_ms = latency_ms
        health.last_check_time = now

        # Save to Redis
        import json
        redis_key = RedisKeys.provider_health(provider_id)
        await RedisService.set(
            redis_key,
            json.dumps({
                "is_healthy": is_healthy,
                "circuit_state": health.circuit_state.value,
                "failure_count": health.failure_count,
                "success_count": health.success_count,
                "last_check_time": now,
                "error_message": error_message,
            }),
            ttl=60,  # 1 minute
        )

    async def get_health_status(self, provider_id: int) -> ProviderHealth:
        """
        Get health status for a provider.

        Args:
            provider_id: Provider ID

        Returns:
            ProviderHealth: Health status
        """
        if provider_id not in self._health_status:
            # Try to load from Redis
            import json
            redis_key = RedisKeys.provider_health(provider_id)
            cached = await RedisService.get(redis_key)

            if cached:
                data = json.loads(cached)
                from src.models.provider import Provider
                provider = await SessionManager.execute_get_one(
                    select(Provider).where(Provider.id == provider_id)
                )

                self._health_status[provider_id] = ProviderHealth(
                    provider_id=provider_id,
                    name=provider.name if provider else "Unknown",
                    is_healthy=data.get("is_healthy", True),
                    circuit_state=CircuitState(data.get("circuit_state", "closed")),
                    failure_count=data.get("failure_count", 0),
                    success_count=data.get("success_count", 0),
                    last_check_time=data.get("last_check_time"),
                    error_message=data.get("error_message"),
                )
            else:
                # Default to healthy
                from src.models.provider import Provider
                provider = await SessionManager.execute_get_one(
                    select(Provider).where(Provider.id == provider_id)
                )

                self._health_status[provider_id] = ProviderHealth(
                    provider_id=provider_id,
                    name=provider.name if provider else "Unknown",
                    is_healthy=True,
                    circuit_state=CircuitState.CLOSED,
                )

        return self._health_status[provider_id]


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by:
    - Opening circuit after threshold failures
    - Allowing test requests during half-open
    - Closing circuit after recovery confirmed
    """

    def __init__(
        self,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """Initialize the circuit breaker."""
        self.config = config or CircuitBreakerConfig()
        self._states: Dict[int, CircuitState] = {}
        self._state_change_times: Dict[int, float] = {}

    async def should_allow_request(
        self,
        provider_id: int,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if request should be allowed through circuit breaker.

        Args:
            provider_id: Provider ID

        Returns:
            tuple[bool, Optional[str]]: (allow, reason)
        """
        state = self._get_state(provider_id)
        now = time.time()

        if state == CircuitState.OPEN:
            # Check if timeout has elapsed
            state_time = self._state_change_times.get(provider_id, 0)
            if now - state_time > self.config.timeout_seconds:
                # Transition to half-open for testing
                await self._set_state(provider_id, CircuitState.HALF_OPEN)
                return True, "Circuit breaker half-open (testing recovery)"
            else:
                remaining = int(self.config.timeout_seconds - (now - state_time))
                return False, f"Circuit breaker open ({remaining}s remaining)"

        elif state == CircuitState.HALF_OPEN:
            # Check if too many calls in half-open
            health = await health_checker.get_health_status(provider_id)
            if health.consecutive_failures >= self.config.half_open_max_calls:
                await self._set_state(provider_id, CircuitState.OPEN)
                return False, "Circuit breaker re-opened (recovery test failed)"

        return True, None

    async def record_success(
        self,
        provider_id: int,
    ) -> None:
        """
        Record a successful request.

        Args:
            provider_id: Provider ID
        """
        state = self._get_state(provider_id)

        if state == CircuitState.HALF_OPEN:
            # Check if we've reached success threshold
            health = await health_checker.get_health_status(provider_id)
            if health.consecutive_successes >= self.config.success_threshold:
                await self._set_state(provider_id, CircuitState.CLOSED)

    async def record_failure(
        self,
        provider_id: int,
    ) -> None:
        """
        Record a failed request.

        Args:
            provider_id: Provider ID
        """
        health = await health_checker.get_health_status(provider_id)

        # Check if we should open the circuit
        if health.consecutive_failures >= self.config.failure_threshold:
            await self._set_state(provider_id, CircuitState.OPEN)

    def _get_state(self, provider_id: int) -> CircuitState:
        """Get current circuit state."""
        return self._states.get(provider_id, CircuitState.CLOSED)

    async def _set_state(
        self,
        provider_id: int,
        state: CircuitState,
    ) -> None:
        """Set circuit state."""
        old_state = self._get_state(provider_id)

        if old_state != state:
            self._states[provider_id] = state
            self._state_change_times[provider_id] = time.time()

            # Save to Redis
            redis_key = RedisKeys.circuit_breaker_state(provider_id)
            await RedisService.set(
                redis_key,
                state.value,
                ttl=3600,  # 1 hour
            )


class FailoverManager:
    """
    Manages automatic failover between providers.

    Features:
    - Rapid failure detection (<3 seconds)
    - Automatic provider switching
    - Progressive recovery testing
    - Graceful degradation
    """

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        """Initialize the failover manager."""
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self._detection_window = 3  # seconds
        self._failure_history: Dict[int, List[float]] = {}

    async def should_failover(
        self,
        provider_id: int,
    ) -> FailoverDecision:
        """
        Determine if failover is needed.

        Args:
            provider_id: Current provider ID

        Returns:
            FailoverDecision: Failover decision
        """
        # Check circuit breaker
        allowed, reason = await self.circuit_breaker.should_allow_request(provider_id)

        if not allowed:
            # Circuit breaker is open, definitely failover
            return FailoverDecision(
                should_failover=True,
                from_provider_id=provider_id,
                to_provider_id=None,
                reason=f"Circuit breaker: {reason}",
                original_provider_healthy=False,
                confidence=1.0,
            )

        # Check health status
        health = await health_checker.get_health_status(provider_id)

        if not health.is_healthy:
            return FailoverDecision(
                should_failover=True,
                from_provider_id=provider_id,
                to_provider_id=None,
                reason=f"Provider unhealthy: {health.error_message or 'Unknown error'}",
                original_provider_healthy=False,
                confidence=0.9,
            )

        # Check for rapid failures in detection window
        recent_failures = self._get_recent_failures(provider_id, self._detection_window)

        if len(recent_failures) >= 3:
            return FailoverDecision(
                should_failover=True,
                from_provider_id=provider_id,
                to_provider_id=None,
                reason=f"Rapid failures detected: {len(recent_failures)} failures in {self._detection_window}s",
                original_provider_healthy=False,
                confidence=0.85,
            )

        # No failover needed
        return FailoverDecision(
            should_failover=False,
            from_provider_id=provider_id,
            to_provider_id=None,
            reason="Provider healthy",
            original_provider_healthy=True,
            confidence=1.0,
        )

    def _get_recent_failures(
        self,
        provider_id: int,
        window_seconds: int,
    ) -> List[float]:
        """Get recent failure timestamps for a provider."""
        now = time.time()
        cutoff = now - window_seconds

        if provider_id not in self._failure_history:
            return []

        # Filter and clean old failures
        recent = [
            timestamp for timestamp in self._failure_history[provider_id]
            if timestamp > cutoff
        ]

        self._failure_history[provider_id] = recent

        return recent

    async def record_failure(
        self,
        provider_id: int,
    ) -> None:
        """
        Record a provider failure.

        Args:
            provider_id: Provider that failed
        """
        now = time.time()

        if provider_id not in self._failure_history:
            self._failure_history[provider_id] = []

        self._failure_history[provider_id].append(now)

        # Notify circuit breaker
        await self.circuit_breaker.record_failure(provider_id)

    async def record_success(
        self,
        provider_id: int,
    ) -> None:
        """
        Record a provider success.

        Args:
            provider_id: Provider that succeeded
        """
        # Clear recent failures
        self._failure_history[provider_id] = []

        # Notify circuit breaker
        await self.circuit_breaker.record_success(provider_id)

    async def select_alternative_provider(
        self,
        current_provider_id: int,
        available_provider_ids: List[int],
    ) -> Optional[int]:
        """
        Select an alternative provider for failover.

        Args:
            current_provider_id: Provider that failed
            available_provider_ids: List of alternative provider IDs

        Returns:
            Optional[int]: Selected alternative provider ID
        """
        if not available_provider_ids:
            return None

        # Filter out the failed provider
        alternatives = [
            pid for pid in available_provider_ids
            if pid != current_provider_id
        ]

        if not alternatives:
            return None

        # Check health of alternatives
        healthy_alternatives = []

        for provider_id in alternatives:
            health = await health_checker.get_health_status(provider_id)
            if health.is_healthy:
                allowed, _ = await self.circuit_breaker.should_allow_request(provider_id)
                if allowed:
                    healthy_alternatives.append(provider_id)

        if not healthy_alternatives:
            # No healthy alternatives, return first available
            return alternatives[0]

        # Select based on least failures
        selected = min(
            healthy_alternatives,
            key=lambda pid: len(self._get_recent_failures(pid, 60))
        )

        return selected


# Global instances
health_checker = HealthChecker()
circuit_breaker = CircuitBreaker()
failover_manager = FailoverManager(circuit_breaker)
