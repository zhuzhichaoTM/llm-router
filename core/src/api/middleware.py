"""
API middleware for authentication, rate limiting, and logging.
"""
import time
from typing import Optional, Callable
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import settings
from src.models.user import User, APIKey
from src.services.redis_client import RedisService


class APIKeyAuth:
    """API key authentication middleware."""

    @staticmethod
    async def verify_api_key(request: Request) -> Optional[tuple[User, APIKey]]:
        """
        Verify API key from request.

        Args:
            request: FastAPI request

        Returns:
            tuple[User, APIKey]: User and API key if valid

        Raises:
            HTTPException: If API key is invalid
        """
        from sqlalchemy import select

        # Get API key from header
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not api_key:
            return None

        # Check for admin key
        if api_key == settings.admin_api_key:
            # Create a temporary admin user
            admin_user = User(
                id=0,
                username="admin",
                email="admin@llm-router.local",
                role="admin",
                status="active",
            )
            return admin_user, None

        # Hash the API key
        from src.utils.encryption import hash_api_key
        key_hash = hash_api_key(api_key)

        # Check cache first
        cache_key = f"api_key:{key_hash}"
        cached = await RedisService.get(cache_key)

        if cached:
            import json
            cached_data = json.loads(cached)
            user = User(
                id=cached_data["user_id"],
                username=cached_data["username"],
                email=cached_data["email"],
                role=cached_data["role"],
                status=cached_data["status"],
            )
            api_key_obj = APIKey(
                id=cached_data["api_key_id"],
                user_id=cached_data["user_id"],
                key_hash=key_hash,
                name=cached_data["name"],
                is_active=cached_data["is_active"],
            )
            return user, api_key_obj

        # Query database
        from src.db.session import SessionManager

        api_key_obj = await SessionManager.execute_get_one(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
        )

        if not api_key_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        # Get user
        user = await SessionManager.execute_get_one(
            select(User).where(User.id == api_key_obj.user_id)
        )

        if not user or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        # Cache the result
        await RedisService.set(
            cache_key,
            json.dumps({
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "status": user.status.value,
                "api_key_id": api_key_obj.id,
                "name": api_key_obj.name,
                "is_active": api_key_obj.is_active,
            }),
            ttl=300,  # 5 minutes
        )

        # Update last used
        from datetime import datetime, timezone
        api_key_obj.last_used_at = datetime.now(timezone.utc)
        api_key_obj.request_count += 1
        await SessionManager.execute_update(
            select(APIKey).where(APIKey.id == api_key_obj.id),
            commit=True,
        )

        return user, api_key_obj


def require_auth(f: Callable) -> Callable:
    """Decorator to require authentication."""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request object not found",
            )

        user, api_key = await APIKeyAuth.verify_api_key(request)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
            )

        # Add user to kwargs
        kwargs["user"] = user
        kwargs["api_key"] = api_key

        return await f(*args, **kwargs)

    return wrapper


def require_admin(f: Callable) -> Callable:
    """Decorator to require admin access."""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request object not found",
            )

        user, api_key = await APIKeyAuth.verify_api_key(request)

        if not user or user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        # Add user to kwargs
        kwargs["user"] = user
        kwargs["api_key"] = api_key

        return await f(*args, **kwargs)

    return wrapper


class RateLimiter:
    """Rate limiting middleware."""

    @staticmethod
    async def check_rate_limit(
        request: Request,
        user: Optional[User] = None,
        api_key: Optional[APIKey] = None,
    ) -> None:
        """
        Check rate limit for request.

        Args:
            request: FastAPI request
            user: Optional user
            api_key: Optional API key

        Raises:
            HTTPException: If rate limit is exceeded
        """
        if not settings.rate_limit_enabled:
            return

        # Use API key hash or IP address as identifier
        if api_key:
            identifier = f"apikey:{api_key.id}"
        else:
            identifier = f"ip:{request.client.host}"

        # Check per-minute limit
        minute_key = f"rate_limit:{identifier}:minute"
        minute_count = await RedisService.get(minute_key, 0)
        minute_count = int(minute_count) if minute_count else 0

        if minute_count >= settings.rate_limit_requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {settings.rate_limit_requests_per_minute} requests per minute.",
            )

        # Increment counter
        await RedisService.incr(minute_key)
        await RedisService.expire(minute_key, 60)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""

    async def dispatch(self, request: Request, call_next):
        """Process request and log."""
        start_time = time.time()

        # Log request
        from src.utils.logging import logger
        logger.info(
            f"{request.method} {request.url.path} - "
            f"IP: {request.client.host}"
        )

        # Process request
        try:
            response = await call_next(request)

            # Log response
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.2f}ms"
            )

            return response

        except Exception as e:
            # Log error
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Error: {str(e)} - "
                f"Time: {process_time:.2f}ms"
            )
            raise


def setup_cors(app) -> None:
    """
    Setup CORS middleware.

    Args:
        app: FastAPI application
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
