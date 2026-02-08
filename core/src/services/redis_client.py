"""
Redis client service wrapper.
"""
from typing import Optional, Any
import redis.asyncio as aioredis

from src.config.redis_config import RedisConfig


class RedisService:
    """High-level Redis service wrapper."""

    _client: Optional[aioredis.Redis] = None

    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        """Get Redis client instance."""
        if cls._client is None:
            cls._client = await RedisConfig.get_client()
        return cls._client

    @classmethod
    async def get(cls, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get value from Redis."""
        client = await cls.get_client()
        value = await client.get(key)
        return value if value is not None else default

    @classmethod
    async def set(cls, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set value in Redis."""
        client = await cls.get_client()
        return await client.set(key, value, ex=ex)

    @classmethod
    async def delete(cls, key: str) -> int:
        """Delete key from Redis."""
        client = await cls.get_client()
        return await client.delete(key)

    @classmethod
    async def hget(cls, key: str, field: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get hash field value."""
        client = await cls.get_client()
        value = await client.hget(key, field)
        return value if value is not None else default

    @classmethod
    async def hset(cls, key: str, field: str, value: Any) -> bool:
        """Set hash field value."""
        client = await cls.get_client()
        return await client.hset(key, field, value)

    @classmethod
    async def hgetall(cls, key: str) -> dict:
        """Get all hash fields."""
        client = await cls.get_client()
        return await client.hgetall(key)

    @classmethod
    async def hdel(cls, key: str, *fields: str) -> int:
        """Delete hash fields."""
        client = await cls.get_client()
        return await client.hdel(key, *fields)

    @classmethod
    async def incr(cls, key: str, amount: int = 1) -> int:
        """Increment value."""
        client = await cls.get_client()
        return await client.incrby(key, amount)

    @classmethod
    async def incrbyfloat(cls, key: str, amount: float) -> float:
        """Increment value by float amount."""
        client = await cls.get_client()
        return await client.incrbyfloat(key, amount)

    @classmethod
    async def expire(cls, key: str, seconds: int) -> bool:
        """Set key expiration."""
        client = await cls.get_client()
        return await client.expire(key, seconds)

    @classmethod
    async def ttl(cls, key: str) -> int:
        """Get key time to live."""
        client = await cls.get_client()
        return await client.ttl(key)

    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if key exists."""
        client = await cls.get_client()
        return await client.exists(key) > 0

    @classmethod
    async def lpush(cls, key: str, *values: Any) -> int:
        """Push values to list (left)."""
        client = await cls.get_client()
        return await client.lpush(key, *values)

    @classmethod
    async def rpush(cls, key: str, *values: Any) -> int:
        """Push values to list (right)."""
        client = await cls.get_client()
        return await client.rpush(key, *values)

    @classmethod
    async def lrange(cls, key: str, start: int = 0, end: int = -1) -> list:
        """Get list range."""
        client = await cls.get_client()
        return await client.lrange(key, start, end)

    @classmethod
    async def ltrim(cls, key: str, start: int, end: int) -> bool:
        """Trim list."""
        client = await cls.get_client()
        return await client.ltrim(key, start, end)

    @classmethod
    async def lpop(cls, key: str) -> Optional[Any]:
        """Pop from list (left)."""
        client = await cls.get_client()
        return await client.lpop(key)

    @classmethod
    async def rpop(cls, key: str) -> Optional[Any]:
        """Pop from list (right)."""
        client = await cls.get_client()
        return await client.rpop(key)

    @classmethod
    async def llen(cls, key: str) -> int:
        """Get list length."""
        client = await cls.get_client()
        return await client.llen(key)

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection."""
        if cls._client:
            await cls._client.close()
            cls._client = None
