"""
Gateway Orchestrator - Manages routing switch state and control.
"""
import time
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.redis_config import RedisConfig, RedisKeys
from src.models.routing import RoutingSwitchHistory, RoutingSwitchState
from src.db.session import SessionManager


class RoutingSwitchStatus(str, Enum):
    """Routing switch status."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    PENDING = "pending"


@dataclass
class SwitchInfo:
    """Routing switch information."""
    enabled: bool
    pending: bool
    pending_value: Optional[bool]
    scheduled_at: Optional[int]
    cooldown_until: Optional[int]
    can_toggle: bool


class GatewayOrchestrator:
    """
    Gateway Orchestrator manages the routing switch state.

    Features:
    - State management (in-memory + Redis)
    - Delayed生效 (10 second delay)
    - Cooldown control (5 minutes)
    - History tracking
    """

    _instance: Optional["GatewayOrchestrator"] = None

    def __new__(cls) -> "GatewayOrchestrator":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the orchestrator."""
        if self._initialized:
            return

        self._initialized = True
        self._enabled: bool = True
        self._pending_switch: bool = False
        self._pending_value: bool = False
        self._scheduled_at: Optional[int] = None
        self._cooldown_until: Optional[int] = None

    async def initialize(self) -> None:
        """Initialize from Redis/Database."""
        # Try to load from Redis first
        redis = await RedisConfig.get_client()

        # Check for pending switch
        pending_key = RedisKeys.ROUTING_SWITCH_PENDING
        pending_data = await redis.hgetall(pending_key)

        if pending_data:
            self._pending_switch = pending_data.get("pending", "false").lower() == "true"
            self._pending_value = pending_data.get("value", "false").lower() == "true"
            self._scheduled_at = int(pending_data.get("scheduled_at", 0)) if pending_data.get("scheduled_at") else None

        # Get cooldown
        cooldown_key = RedisKeys.ROUTING_SWITCH_COOLDOWN
        cooldown_str = await redis.get(cooldown_key)
        if cooldown_str:
            try:
                self._cooldown_until = int(cooldown_str)
            except ValueError:
                self._cooldown_until = None

        # Get current state
        enabled_key = RedisKeys.ROUTING_SWITCH_ENABLED
        enabled_str = await redis.get(enabled_key)
        if enabled_str:
            self._enabled = enabled_str.lower() == "true"

        # Process any pending switch
        await self._process_pending_switch()

    async def get_status(self) -> SwitchInfo:
        """
        Get current routing switch status.

        Returns:
            SwitchInfo: Current switch information
        """
        # Process any pending switch
        await self._process_pending_switch()

        now = int(time.time())
        can_toggle = self._cooldown_until is None or now > self._cooldown_until

        return SwitchInfo(
            enabled=self._enabled,
            pending=self._pending_switch,
            pending_value=self._pending_value if self._pending_switch else None,
            scheduled_at=self._scheduled_at,
            cooldown_until=self._cooldown_until,
            can_toggle=can_toggle,
        )

    async def toggle(
        self,
        value: bool,
        reason: str,
        triggered_by: str,
        force: bool = False,
        delay: Optional[int] = None,
    ) -> SwitchInfo:
        """
        Toggle the routing switch.

        Args:
            value: New value (True for enabled, False for disabled)
            reason: Reason for the toggle
            triggered_by: User/system that triggered the toggle
            force: Force immediate toggle (ignore delay)
            delay: Custom delay in seconds (default: 10)

        Returns:
            SwitchInfo: Updated switch information
        """
        now = int(time.time())

        # Check cooldown
        if self._cooldown_until and now < self._cooldown_until:
            if not force:
                cooldown_remaining = self._cooldown_until - now
                raise RuntimeError(f"Cooldown active. {cooldown_remaining} seconds remaining.")

        # Calculate delay
        effective_delay = 0 if force else (delay or 10)

        if effective_delay > 0:
            # Schedule delayed switch
            self._pending_switch = True
            self._pending_value = value
            self._scheduled_at = now + effective_delay

            # Save to Redis
            redis = await RedisConfig.get_client()
            await redis.hset(
                RedisKeys.ROUTING_SWITCH_PENDING,
                mapping={
                    "pending": "true",
                    "value": str(value).lower(),
                    "scheduled_at": str(self._scheduled_at),
                },
            )

            # Auto-expire after delay
            await redis.expire(RedisKeys.ROUTING_SWITCH_PENDING, effective_delay + 60)

        else:
            # Immediate switch
            old_enabled = self._enabled
            self._enabled = value
            self._pending_switch = False
            self._scheduled_at = None

            # Update cooldown
            self._cooldown_until = now + 300  # 5 minutes cooldown
            redis = await RedisConfig.get_client()
            await redis.set(RedisKeys.ROUTING_SWITCH_COOLDOWN, str(self._cooldown_until), ex=300)
            await redis.delete(RedisKeys.ROUTING_SWITCH_PENDING)

            # Update current state
            await redis.set(RedisKeys.ROUTING_SWITCH_ENABLED, str(value).lower())

            # Record history
            await self._record_history(old_enabled, value, reason, triggered_by)

        return await self.get_status()

    async def _process_pending_switch(self) -> None:
        """Process any pending switch."""
        if not self._pending_switch or self._scheduled_at is None:
            return

        now = int(time.time())

        if now >= self._scheduled_at:
            # Execute pending switch
            old_enabled = self._enabled
            self._enabled = self._pending_value
            self._pending_switch = False
            self._pending_value = False
            self._scheduled_at = None

            # Update cooldown
            self._cooldown_until = now + 300  # 5 minutes cooldown
            redis = await RedisConfig.get_client()
            await redis.set(RedisKeys.ROUTING_SWITCH_COOLDOWN, str(self._cooldown_until), ex=300)
            await redis.delete(RedisKeys.ROUTING_SWITCH_PENDING)

            # Update current state
            await redis.set(RedisKeys.ROUTING_SWITCH_ENABLED, str(self._enabled).lower())

            # Record history
            await self._record_history(
                old_enabled,
                self._enabled,
                "Scheduled switch",
                "system",
            )

    async def _record_history(
        self,
        old_enabled: bool,
        new_enabled: bool,
        reason: str,
        triggered_by: str,
    ) -> None:
        """Record switch history."""
        history = RoutingSwitchHistory(
            old_enabled=old_enabled,
            new_enabled=new_enabled,
            trigger_reason=reason,
            triggered_by=triggered_by,
            effective_at=int(time.time()),
        )

        await SessionManager.execute_insert(history)

        # Also add to Redis history
        redis = await RedisConfig.get_client()
        history_key = RedisKeys.ROUTING_SWITCH_HISTORY
        history_entry = {
            "old_enabled": str(old_enabled).lower(),
            "new_enabled": str(new_enabled).lower(),
            "reason": reason,
            "triggered_by": triggered_by,
            "timestamp": str(int(time.time())),
        }

        # Add to list (keep last 100)
        await redis.lpush(history_key, str(history_entry))
        await redis.ltrim(history_key, 0, 99)

    async def get_history(self, limit: int = 100) -> list[dict]:
        """
        Get routing switch history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            list[dict]: History entries
        """
        redis = await RedisConfig.get_client()
        history_key = RedisKeys.ROUTING_SWITCH_HISTORY

        entries = await redis.lrange(history_key, 0, limit - 1)

        result = []
        for entry in entries:
            try:
                # Parse entry
                import ast
                parsed = ast.literal_eval(entry)
                parsed["timestamp"] = int(parsed["timestamp"])
                result.append(parsed)
            except (ValueError, SyntaxError):
                continue

        return result

    async def get_metrics(self) -> dict:
        """
        Get orchestrator metrics.

        Returns:
            dict: Metrics data
        """
        status = await self.get_status()
        history = await self.get_history(100)

        # Calculate statistics
        total_switches = len(history)
        enabled_count = sum(1 for h in history if h.get("new_enabled") == "true")
        disabled_count = sum(1 for h in history if h.get("new_enabled") == "false")

        now = int(time.time())
        cooldown_remaining = max(0, (self._cooldown_until or 0) - now) if self._cooldown_until else 0

        return {
            "current_status": status.enabled,
            "pending_switch": status.pending,
            "cooldown_remaining": cooldown_remaining,
            "total_switches": total_switches,
            "enabled_count": enabled_count,
            "disabled_count": disabled_count,
            "recent_history": history[:10],
        }

    async def is_enabled(self) -> bool:
        """
        Check if routing is enabled.

        Returns:
            bool: True if routing is enabled
        """
        await self._process_pending_switch()
        return self._enabled


# Global instance
orchestrator = GatewayOrchestrator()
