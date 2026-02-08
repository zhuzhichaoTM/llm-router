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

# Import test helpers
from tests.helpers import test_engine, test_session, mock_redis


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for the test session."""
    policy = asyncio.get_event_loop_policy()
    yield policy


@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Clean up
    loop.close()
    asyncio.set_event_loop(None)


@pytest.fixture
async def redis_client(event_loop):
    """Get a mock Redis client for testing."""
    from unittest.mock import AsyncMock

    async def mock_get(key):
        return None

    async def mock_set(key, value, ex=None):
        return True

    async def mock_hget(key, field):
        return None

    async def mock_hgetall(key):
        return {}

    async def mock_hset(key, mapping=None, **kwargs):
        return True

    async def mock_expire(key, time):
        return True

    async def mock_delete(*keys):
        return 1

    async def mock_incr(key):
        return 1

    async def mock_incrby(key, amount):
        return 1

    async def mock_lpush(key, *values):
        return 1

    async def mock_ltrim(key, start, stop):
        return True

    async def mock_lrange(key, start, stop):
        return []

    async def mock_flushall():
        return True

    async def mock_ping():
        return True

    class MockRedisClient:
        async def get(self, key):
            return await mock_get(key)

        async def set(self, key, value, ex=None):
            return await mock_set(key, value, ex)

        async def hget(self, key, field):
            return await mock_hget(key, field)

        async def hgetall(self, key):
            return await mock_hgetall(key)

        async def hset(self, key, mapping=None, **kwargs):
            return await mock_hset(key, mapping, **kwargs)

        async def expire(self, key, time):
            return await mock_expire(key, time)

        async def delete(self, *keys):
            return await mock_delete(*keys)

        async def incr(self, key):
            return await mock_incr(key)

        async def incrby(self, key, amount):
            return await mock_incrby(key, amount)

        async def lpush(self, key, *values):
            return await mock_lpush(key, *values)

        async def ltrim(self, key, start, stop):
            return await mock_ltrim(key, start, stop)

        async def lrange(self, key, start, stop):
            return await mock_lrange(key, start, stop)

        async def flushall(self):
            return await mock_flushall()

        async def ping(self):
            return await mock_ping()

    yield MockRedisClient()


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


@pytest.fixture
async def db_session(test_session) -> AsyncGenerator:
    """Alias for test_session for backward compatibility."""
    yield test_session
