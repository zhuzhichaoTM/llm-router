"""
Caching service wrapper.
"""
import json
import hashlib
from typing import Optional, Any, Callable, TypeVar
from functools import wraps

from src.services.redis_client import RedisService


T = TypeVar("T")


class CacheService:
    """High-level caching service."""

    @staticmethod
    def _serialize(value: Any) -> str:
        """Serialize value for storage."""
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        return json.dumps(value)

    @staticmethod
    def _deserialize(value: str) -> Any:
        """Deserialize value from storage."""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        value = await RedisService.get(key)
        if value is None:
            return None
        return CacheService._deserialize(value)

    @staticmethod
    async def set(key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        serialized = CacheService._serialize(value)
        await RedisService.set(key, serialized, ex=ttl)

    @staticmethod
    async def delete(key: str) -> None:
        """
        Delete key from cache.

        Args:
            key: Cache key
        """
        await RedisService.delete(key)

    @staticmethod
    async def get_or_set(
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get value from cache or compute and store.

        Args:
            key: Cache key
            factory: Function to compute value if not cached
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        value = await CacheService.get(key)
        if value is not None:
            return value

        # Compute value
        result = factory()

        # Check if it's async
        if hasattr(result, "__await__"):
            result = await result

        # Cache the result
        await CacheService.set(key, result, ttl)

        return result

    @staticmethod
    def hash_key(*parts: str) -> str:
        """
        Generate a hash key from parts.

        Args:
            *parts: Parts to hash

        Returns:
            Hashed key
        """
        combined = ":".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key

    Usage:
        @cached(ttl=60)
        async def get_user_data(user_id: str):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: **kwargs) -> T:
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}"
            if args:
                cache_key += f":{':'.join(str(arg) for arg in args)}"
            if kwargs:
                sorted_kwargs = sorted(kwargs.items())
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted_kwargs)}"

            # Try to get from cache
            cached_value = await CacheService.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function
            result = await func(*args, **kwargs)

            # Cache result
            await CacheService.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator
