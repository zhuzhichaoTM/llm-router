"""
Provider base interface and common utilities.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class TokenUsage:
    """Token usage information."""
    input_tokens: int
    output_tokens: int
    total_tokens: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ChatMessage:
    """Chat message representation."""
    role: str
    content: str


@dataclass
class ChatRequest:
    """Chat completion request."""
    messages: list[ChatMessage]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    stop: Optional[list[str]] = None


@dataclass
class ChatChoice:
    """Single chat completion choice."""
    index: int
    message: ChatMessage
    finish_reason: str


@dataclass
class ChatResponse:
    """Chat completion response."""
    id: str
    object: str
    created: int
    model: str
    choices: list[ChatChoice]
    usage: TokenUsage

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                    },
                    "finish_reason": choice.finish_reason,
                }
                for choice in self.choices
            ],
            "usage": self.usage.to_dict(),
        }


@dataclass
class ModelInfo:
    """Model information."""
    id: str
    name: str
    provider: str
    context_window: int
    input_price_per_1k: Decimal
    output_price_per_1k: Decimal


@dataclass
class HealthStatus:
    """Provider health status."""
    is_healthy: bool
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None


class IProvider(ABC):
    """
    Interface for LLM providers.

    All provider implementations must implement these methods.
    """

    @abstractmethod
    async def chat_completion(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Perform a chat completion request.

        Args:
            request: The chat completion request

        Returns:
            ChatResponse: The response from the provider

        Raises:
            ProviderError: If the request fails
        """
        pass

    @abstractmethod
    async def stream_chat_completion(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[str]:
        """
        Perform a streaming chat completion request.

        Args:
            request: The chat completion request

        Yields:
            str: Chunks of the response

        Raises:
            ProviderError: If the request fails
        """
        pass

    @abstractmethod
    async def get_model_list(self) -> list[ModelInfo]:
        """
        Get the list of available models from this provider.

        Returns:
            list[ModelInfo]: List of available models
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Check the health status of this provider.

        Returns:
            HealthStatus: The health status of the provider
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            str: Provider name (e.g., "openai", "anthropic")
        """
        pass

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: str,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate the cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model_id: Model identifier

        Returns:
            tuple[Decimal, Decimal]: (input_cost, output_cost)
        """
        # Default implementation - should be overridden by specific providers
        return Decimal("0"), Decimal("0")


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class RateLimitError(ProviderError):
    """Exception raised when rate limit is exceeded."""
    pass


class AuthenticationError(ProviderError):
    """Exception raised for authentication failures."""
    pass


class TimeoutError(ProviderError):
    """Exception raised when request times out."""
    pass
