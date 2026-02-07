"""
Unit tests for Provider implementations.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from src.providers.base import (
    IProvider,
    ChatRequest,
    ChatMessage,
    ChatResponse,
    ChatChoice,
    TokenUsage,
    HealthStatus,
    ProviderError,
)
from src.providers.openai import OpenAIProvider
from src.providers.anthropic import AnthropicProvider
from src.providers.factory import ProviderFactory


class TestProviderFactory:
    """Test ProviderFactory."""

    def test_registered_providers(self):
        """Test that all built-in providers are registered."""
        providers = ProviderFactory.list_providers()
        assert "openai" in providers
        assert "anthropic" in providers

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = ProviderFactory.create_provider(
            "openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        )
        assert isinstance(provider, IProvider)
        assert provider.get_provider_name() == "openai"

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        provider = ProviderFactory.create_provider(
            "anthropic",
            api_key="test-key",
            base_url="https://api.anthropic.com",
        )
        assert isinstance(provider, IProvider)
        assert provider.get_provider_name() == "anthropic"

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with pytest.raises(ProviderError):
            ProviderFactory.create_provider("unknown", api_key="test-key")

    def test_get_cached_provider(self):
        """Test getting cached provider."""
        provider1 = ProviderFactory.get_provider("openai", api_key="test-key")
        provider2 = ProviderFactory.get_provider("openai")
        assert provider1 is provider2  # Same instance


class TestOpenAIProvider:
    """Test OpenAIProvider."""

    @pytest.fixture
    def provider(self):
        """Create OpenAI provider for testing."""
        return OpenAIProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            timeout=60,
        )

    @pytest.mark.unit
    def test_get_provider_name(self, provider):
        """Test provider name."""
        assert provider.get_provider_name() == "openai"

    @pytest.mark.unit
    def test_calculate_cost(self, provider):
        """Test cost calculation."""
        input_cost, output_cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=2000,
            model_id="gpt-3.5-turbo",
        )
        assert input_cost == Decimal("0.0005")  # 0.0005 per 1K tokens
        assert output_cost == Decimal("0.0015")  # 0.0015 per 1K tokens
        total_cost = input_cost + output_cost
        assert total_cost == Decimal("0.0020")

    @pytest.mark.unit
    def test_calculate_cost_unknown_model(self, provider):
        """Test cost calculation with unknown model."""
        input_cost, output_cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=2000,
            model_id="unknown-model",
        )
        assert input_cost == Decimal("0")
        assert output_cost == Decimal("0")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_success(self, provider, sample_openai_response):
        """Test successful health check."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = MagicMock(
                status_code=200,
                raise_for_status=MagicMock(),
                json=lambda: sample_openai_response,
            )
            mock_client_class.return_value = mock_client

            # Create new provider instance with mocked client
            provider = OpenAIProvider(api_key="test-key")
            provider._client = mock_client

            health = await provider.health_check()

            assert health.is_healthy is True
            assert health.latency_ms is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider):
        """Test failed health check."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "error": {
                    "message": "Unauthorized",
                    "type": "invalid_request_error",
                }
            }
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Create new provider instance with mocked client
            provider = OpenAIProvider(api_key="test-key")
            provider._client = mock_client

            health = await provider.health_check()

            assert health.is_healthy is False
            assert "Unauthorized" in health.error_message

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, provider, sample_openai_response):
        """Test successful chat completion."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = sample_openai_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OpenAIProvider(api_key="test-key")
            provider._client = mock_client

            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                model="gpt-3.5-turbo",
            )

            response = await provider.chat_completion(request)

            assert response.id == "chatcmpl-test123"
            assert response.model == "gpt-3.5-turbo"
            assert len(response.choices) == 1
            assert response.choices[0].message.content == "Hello! I'm doing well, thank you for asking!"
            assert response.choices[0].finish_reason == "stop"
            assert response.usage.input_tokens == 10
            assert response.usage.output_tokens == 20
            assert response.usage.total_tokens == 30


class TestAnthropicProvider:
    """Test AnthropicProvider."""

    @pytest.fixture
    def provider(self):
        """Create Anthropic provider for testing."""
        return AnthropicProvider(
            api_key="test-key",
            base_url="https://api.anthropic.com",
            timeout=60,
        )

    @pytest.mark.unit
    def test_get_provider_name(self, provider):
        """Test provider name."""
        assert provider.get_provider_name() == "anthropic"

    @pytest.mark.unit
    def test_calculate_cost(self, provider):
        """Test cost calculation."""
        input_cost, output_cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=2000,
            model_id="claude-3-haiku-20240307",
        )
        assert input_cost == Decimal("0.00025")  # 0.00025 per 1K tokens
        assert output_cost == Decimal("0.00125")  # 0.00125 per 1K tokens
        total_cost = input_cost + output_cost
        assert total_cost == Decimal("0.0015")

    @pytest.mark.unit
    def test_calculate_cost_unknown_model(self, provider):
        """Test cost calculation with unknown model."""
        input_cost, output_cost = provider.calculate_cost(
            input_tokens=1000,
            output_tokens=2000,
            model_id="unknown-model",
        )
        assert input_cost == Decimal("0")
        assert output_cost == Decimal("0")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_success(self, provider, sample_anthropic_response):
        """Test successful health check."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = sample_anthropic_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = AnthropicProvider(api_key="test-key")
            provider._client = mock_client

            health = await provider.health_check()

            assert health.is_healthy is True
            assert health.latency_ms is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, provider, sample_anthropic_response):
        """Test successful chat completion."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = sample_anthropic_response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = AnthropicProvider(api_key="test-key")
            provider._client = mock_client

            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                model="claude-3-haiku-20240307",
            )

            response = await provider.chat_completion(request)

            assert response.id == "msg_test123"
            assert response.model == "claude-3-haiku-20240307"
            assert len(response.choices) == 1
            assert response.choices[0].message.content == "Hello! I'm doing well, thank you for asking!"
            assert response.choices[0].finish_reason == "end_turn"
            assert response.usage.input_tokens == 10
            assert response.usage.output_tokens == 20
            assert response.usage.total_tokens == 30


class TestTokenUsage:
    """Test TokenUsage dataclass."""

    @pytest.mark.unit
    def test_token_usage_creation(self):
        """Test TokenUsage creation."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
        )
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200
        assert usage.total_tokens == 300

    @pytest.mark.unit
    def test_token_usage_to_dict(self):
        """Test TokenUsage to_dict method."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
        )
        result = usage.to_dict()
        assert result == {
            "input_tokens": 100,
            "output_tokens": 200,
            "total_tokens": 300,
        }


class TestChatRequest:
    """Test ChatRequest dataclass."""

    @pytest.mark.unit
    def test_chat_request_creation(self, sample_chat_request):
        """Test ChatRequest creation."""
        assert sample_chat_request.model == "gpt-3.5-turbo"
        assert len(sample_chat_request.messages) == 1
        assert sample_chat_request.messages[0].role == "user"
        assert sample_chat_request.temperature == 0.7


class TestChatResponse:
    """Test ChatResponse dataclass."""

    @pytest.mark.unit
    def test_chat_response_to_dict(self):
        """Test ChatResponse to_dict method."""
        response = ChatResponse(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content="Test response"),
                    finish_reason="stop",
                )
            ],
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=200,
                total_tokens=300,
            ),
        )
        result = response.to_dict()
        assert result["id"] == "test-id"
        assert result["model"] == "gpt-3.5-turbo"
        assert len(result["choices"]) == 1
        assert result["choices"][0]["message"]["content"] == "Test response"
