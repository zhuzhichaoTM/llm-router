"""
Anthropic Provider implementation.
"""
import time
from typing import AsyncIterator, Optional
from decimal import Decimal

import httpx
from httpx import HTTPStatusError, RequestError, TimeoutException

from src.providers.base import (
    IProvider,
    ChatRequest,
    ChatResponse,
    ChatChoice,
    ChatMessage,
    TokenUsage,
    ModelInfo,
    HealthStatus,
    ProviderError,
    AuthenticationError,
    RateLimitError,
    TimeoutError as ProviderTimeoutError,
)


# Model pricing (in USD per 1K tokens)
ANTHROPIC_PRICING = {
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-2.1": {"input": 0.008, "output": 0.024},
    "claude-2": {"input": 0.008, "output": 0.024},
    "claude-instant-1.2": {"input": 0.0008, "output": 0.0024},
}


class AnthropicProvider(IProvider):
    """Anthropic API provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        timeout: int = 60,
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            base_url: Base URL for Anthropic API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "anthropic"

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Perform chat completion."""
        client = self._get_client()

        # Convert messages to Anthropic format
        # Anthropic format: messages array with alternating user/assistant
        anthropic_messages = []
        for msg in request.messages:
            anthropic_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": request.model,
            "messages": anthropic_messages,
            "max_tokens": request.max_tokens or 1024,
            "stream": False,
        }

        if request.temperature:
            payload["temperature"] = request.temperature
        if request.stop:
            payload["stop_sequences"] = request.stop

        start_time = time.time()

        try:
            response = await client.post("/v1/messages", json=payload)
            response.raise_for_status()

            data = response.json()

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Parse response to match OpenAI format
            assistant_message = data.get("content", [])
            content = ""
            if assistant_message and isinstance(assistant_message, list):
                content = assistant_message[0].get("text", "")

            usage_data = data.get("usage", {})

            return ChatResponse(
                id=data.get("id", ""),
                object="chat.completion",
                created=data.get("created_at", int(time.time())),
                model=data.get("model", request.model),
                choices=[
                    ChatChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content=content),
                        finish_reason=data.get("stop_reason", "stop"),
                    )
                ],
                usage=TokenUsage(
                    input_tokens=usage_data.get("input_tokens", 0),
                    output_tokens=usage_data.get("output_tokens", 0),
                    total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
                ),
            )

        except HTTPStatusError as e:
            status_code = e.response.status_code

            if status_code == 401:
                raise AuthenticationError(
                    "Invalid API key or authentication failed",
                    status_code=status_code,
                )
            elif status_code == 429:
                raise RateLimitError(
                    "Rate limit exceeded",
                    status_code=status_code,
                )
            else:
                error_data = e.response.json().get("error", {})
                raise ProviderError(
                    error_data.get("message", "Unknown error"),
                    status_code=status_code,
                    details=error_data,
                )

        except TimeoutException:
            raise ProviderTimeoutError("Request timeout")

        except RequestError as e:
            raise ProviderError(f"Network error: {str(e)}")

    async def stream_chat_completion(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[str]:
        """Perform streaming chat completion."""
        client = self._get_client()

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in request.messages:
            anthropic_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": request.model,
            "messages": anthropic_messages,
            "max_tokens": request.max_tokens or 1024,
            "stream": True,
        }

        if request.temperature:
            payload["temperature"] = request.temperature
        if request.stop:
            payload["stop_sequences"] = request.stop

        try:
            async with client.stream("POST", "/v1/messages", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        # In a real implementation, parse SSE data
                        # This is a simplified version
                        yield data

        except HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed", status_code=e.response.status_code)
            elif e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded", status_code=e.response.status_code)
            raise ProviderError(f"HTTP error: {e.response.status_code}")
        except (TimeoutException, RequestError) as e:
            raise ProviderError(f"Network error: {str(e)}")

    async def get_model_list(self) -> list[ModelInfo]:
        """Get list of available models."""
        # Anthropic doesn't have a public models endpoint
        # Return known models
        models = []

        for model_id, pricing in ANTHROPIC_PRICING.items():
            # Extract model name
            name_map = {
                "claude-3-opus-20240229": "Claude 3 Opus",
                "claude-3-sonnet-20240229": "Claude 3 Sonnet",
                "claude-3-haiku-20240307": "Claude 3 Haiku",
                "claude-2.1": "Claude 2.1",
                "claude-2": "Claude 2",
                "claude-instant-1.2": "Claude Instant 1.2",
            }

            # Set context window based on model
            context_windows = {
                "claude-3-opus-20240229": 200000,
                "claude-3-sonnet-20240229": 200000,
                "claude-3-haiku-20240307": 200000,
                "claude-2.1": 200000,
                "claude-2": 100000,
                "claude-instant-1.2": 100000,
            }

            models.append(
                ModelInfo(
                    id=model_id,
                    name=name_map.get(model_id, model_id),
                    provider="anthropic",
                    context_window=context_windows.get(model_id, 100000),
                    input_price_per_1k=Decimal(str(pricing["input"])),
                    output_price_per_1k=Decimal(str(pricing["output"])),
                )
            )

        return models

    async def health_check(self) -> HealthStatus:
        """Check provider health."""
        client = self._get_client()

        start_time = time.time()

        try:
            # Try a simple message as health check
            payload = {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 10,
            }

            response = await client.post("/v1/messages", json=payload)
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)

            return HealthStatus(
                is_healthy=True,
                latency_ms=latency_ms,
            )

        except HTTPStatusError as e:
            return HealthStatus(
                is_healthy=False,
                error_message=f"HTTP {e.response.status_code}",
            )
        except (TimeoutException, RequestError) as e:
            return HealthStatus(
                is_healthy=False,
                error_message=str(e),
            )

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: str,
    ) -> tuple[Decimal, Decimal]:
        """Calculate cost for a request."""
        pricing = ANTHROPIC_PRICING.get(model_id, {"input": 0, "output": 0})

        input_cost = Decimal(str(pricing["input"])) * input_tokens / Decimal("1000")
        output_cost = Decimal(str(pricing["output"])) * output_tokens / Decimal("1000")

        return input_cost, output_cost
