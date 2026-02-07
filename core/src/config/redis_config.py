"""
Redis configuration and connection management.
"""
from typing import Optional
import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from src.config.settings import settings


class RedisConfig:
    """Redis configuration and connection manager."""

    _pool: Optional[ConnectionPool] = None
    _client: Optional[aioredis.Redis] = None

    @classmethod
    async def get_pool(cls) -> ConnectionPool:
        """Get or create Redis connection pool."""
        if cls._pool is None:
            cls._pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                password=settings.redis_password if settings.redis_password else None,
                db=settings.redis_db,
                decode_responses=True,
            )
        return cls._pool

    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        """Get or create Redis client."""
        if cls._client is None:
            pool = await cls.get_pool()
            cls._client = aioredis.Redis(connection_pool=pool)
        return cls._client

    @classmethod
    async def close(cls) -> None:
        """Close Redis connections."""
        if cls._client:
            await cls._client.close()
            cls._client = None
        if cls._pool:
            await cls._pool.disconnect()
            cls._pool = None


# Redis keys
class RedisKeys:
    """Redis key templates."""

    # Routing switch state
    ROUTING_SWITCH_ENABLED = "router:switch:enabled"
    ROUTING_SWITCH_PENDING = "router:switch:pending"
    ROUTING_SWITCH_COOLDOWN = "router:switch:cooldown"
    ROUTING_SWITCH_HISTORY = "router:switch:history"

    # Provider health and metrics
    PROVIDER_HEALTH = "provider:{provider_id}:health"
    PROVIDER_METRICS = "provider:{provider_id}:metrics"
    PROVIDER_AVG_LATENCY = "provider:{provider_id}:latency"
    PROVIDER_SUCCESS_RATE = "provider:{provider_id}:success_rate"
    PROVIDER_CURRENT_REQUESTS = "provider:{provider_id}:requests"

    # Content analysis cache
    CONTENT_ANALYSIS = "content:analysis:{hash}"
    INTENT_CACHE = "content:intent:{hash}"
    COMPLEXITY_CACHE = "content:complexity:{hash}"

    # Load balancing
    LOAD_BALANCE_STATE = "load_balance:state"
    PROVIDER_WEIGHTS = "load_balance:weights"

    # Cost tracking
    COST_DAILY = "cost:daily:{date}"
    COST_MODEL = "cost:model:{model}"
    COST_USER = "cost:user:{user_id}"
    COST_TOTAL = "cost:total"

    # Rate limiting
    RATE_LIMIT = "rate_limit:{identifier}:{window}"

    # API keys
    API_KEY_CACHE = "api_key:{key_hash}"
