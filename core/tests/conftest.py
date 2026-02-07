"""
Pytest configuration and fixtures for LLM Router tests.
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from pathlib import Path

# Add src to path
sys_path = str(Path(__file__).parent.parent)
import sys
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def redis_client(event_loop):
    """Get a Redis client for testing."""
    from src.config.redis_config import RedisConfig
    client = await RedisConfig.get_client()
    yield client
    # Cleanup
    await client.flushall()


@pytest.fixture
async def db_session(event_loop):
    """Get a database session for testing."""
    from src.db.base import async_session_maker, Base, engine
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

    # Create test database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with async_session_maker() as session:
        yield session
        await session.rollback()

    # Drop test database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for provider tests."""
    from unittest.mock import AsyncMock, patch
    import httpx

    with patch("httpx.AsyncClient", new_callable=AsyncMock) as mock_client:
        yield mock_client


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    from src.providers.base import ChatRequest, ChatMessage

    return ChatRequest(
        messages=[ChatMessage(role="user", content="Hello, how are you?")],
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def sample_openai_response():
    """Sample OpenAI API response for testing."""
    import json
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! I'm doing well, thank you for asking!",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


@pytest.fixture
def sample_anthropic_response():
    """Sample Anthropic API response for testing."""
    import json
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Hello! I'm doing well, thank you for asking!"}
        ],
        "model": "claude-3-haiku-20240307",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
        },
    }


# Test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.integration,
]
