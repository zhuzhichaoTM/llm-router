"""
Test helpers and utilities for better test isolation.
"""
import asyncio
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.base import Base
from src.models import *  # Import all models


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    # Use in-memory SQLite for tests to avoid connection issues
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with automatic rollback."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        # Automatic rollback after each test
        await session.rollback()


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.hget = AsyncMock(return_value=None)
    mock_client.hgetall = AsyncMock(return_value={})
    mock_client.hset = AsyncMock(return_value=True)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.lpush = AsyncMock(return_value=1)
    mock_client.ltrim = AsyncMock(return_value=True)
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.incrby = AsyncMock(return_value=1)
    mock_client.flushall = AsyncMock(return_value=True)

    return mock_client


async def create_test_user(session: AsyncSession, **kwargs):
    """Create a test user in the database."""
    from src.models.user import User, UserRole, UserStatus

    user = User(
        username=kwargs.get("username", "testuser"),
        email=kwargs.get("email", "test@example.com"),
        role=kwargs.get("role", UserRole.USER),
        status=kwargs.get("status", UserStatus.ACTIVE),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_test_provider(session: AsyncSession, **kwargs):
    """Create a test provider in the database."""
    from src.models.provider import Provider, ProviderType, ProviderStatus

    provider = Provider(
        name=kwargs.get("name", "test_provider"),
        provider_type=kwargs.get("provider_type", ProviderType.OPENAI),
        base_url=kwargs.get("base_url", "https://api.openai.com/v1"),
        api_key=kwargs.get("api_key", "test_key"),
        status=kwargs.get("status", ProviderStatus.ACTIVE),
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    return provider


async def create_test_api_key(session: AsyncSession, user_id: int, **kwargs):
    """Create a test API key in the database."""
    from src.models.user import APIKey

    api_key = APIKey(
        user_id=user_id,
        key_hash=kwargs.get("key_hash", "test_hash"),
        name=kwargs.get("name", "test_key"),
        is_active=kwargs.get("is_active", True),
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key
