"""
OpenAI Provider implementation.
"""
import time
import tiktoken
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
OPENAI_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-32k": {"input": 0.06, "output": 0.12},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-vision-preview": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-16k": {"input": 0.001, "output": 0.002},
    "gpt-3.5-turbo-0125": {"input": 0.0005, "output": 0.0015},
}


class OpenAIProvider(IProvider):
    """OpenAI API provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        organization: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            base_url: Base URL for OpenAI API
            organization: Optional organization ID
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.organization = organization
        self.timeout = timeout

        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            if self.organization:
                headers["OpenAI-Organization"] = self.organization

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
        return "openai"

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Perform chat completion."""
        client = self._get_client()

        payload = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ],
            "temperature": request.temperature,
            "stream": False,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop is not None:
            payload["stop"] = request.stop

        start_time = time.time()

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()

            data = response.json()

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Parse response
            choices = [
                ChatChoice(
                    index=choice["index"],
                    message=ChatMessage(
                        role=choice["message"]["role"],
                        content=choice["message"]["content"],
                    ),
                    finish_reason=choice["finish_reason"],
                )
                for choice in data.get("choices", [])
            ]

            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            return ChatResponse(
                id=data["id"],
                object=data["object"],
                created=data["created"],
                model=data["model"],
                choices=choices,
                usage=usage,
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

        payload = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ],
            "temperature": request.temperature,
            "stream": True,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop is not None:
            payload["stop"] = request.stop

        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        if data == "[DONE]":
                            break

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
        client = self._get_client()

        try:
            response = await client.get("/models")
            response.raise_for_status()

            data = response.json()

            models = []
            for model_data in data.get("data", []):
                model_id = model_data["id"]

                # Get pricing for this model
                pricing = OPENAI_PRICING.get(model_id, {"input": 0, "output": 0})

                models.append(
                    ModelInfo(
                        id=model_id,
                        name=model_data.get("display_name", model_id),
                        provider="openai",
                        context_window=model_data.get("context_window", 4096),
                        input_price_per_1k=Decimal(str(pricing["input"])),
                        output_price_per_1k=Decimal(str(pricing["output"])),
                    )
                )

            return models

        except (HTTPStatusError, RequestError) as e:
            raise ProviderError(f"Failed to get models: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """
        Check provider health with detailed error information.

        Returns:
            HealthStatus: Health status with detailed error messages if unhealthy
        """
        client = self._get_client()

        start_time = time.time()

        try:
            # Try to get models list as a health check
            response = await client.get("/models")
            response.raise_for_status()

            latency_ms = int((time.time() - start_time) * 1000)

            return HealthStatus(
                is_healthy=True,
                latency_ms=latency_ms,
            )

        except HTTPStatusError as e:
            status_code = e.response.status_code
            error_msg = f"HTTP {status_code} error"

            # Provide detailed error messages based on status code
            if status_code == 401:
                error_msg = "Authentication failed: Invalid API key"
            elif status_code == 403:
                error_msg = "Access forbidden: Check your API permissions"
            elif status_code == 404:
                error_msg = "API endpoint not found: Check the base URL configuration"
            elif status_code == 429:
                error_msg = "Rate limit exceeded: Too many requests"
            elif status_code == 500:
                error_msg = "OpenAI server error: Please try again later"
            elif status_code == 503:
                error_msg = "OpenAI service unavailable: Service is temporarily down"
            else:
                # Try to get more details from response
                try:
                    error_data = e.response.json().get("error", {})
                    error_msg = error_data.get("message", f"HTTP {status_code} error")
                except Exception:
                    error_msg = f"HTTP {status_code} error"

            return HealthStatus(
                is_healthy=False,
                error_message=error_msg,
            )

        except TimeoutException:
            return HealthStatus(
                is_healthy=False,
                error_message=f"Connection timeout: Provider did not respond within {self.timeout} seconds",
            )

        except RequestError as e:
            error_msg = str(e)

            # Provide more helpful error messages
            if "connect" in error_msg.lower():
                error_msg = "Connection refused: Unable to connect to the provider API. Check the base URL."
            elif "resolve" in error_msg.lower():
                error_msg = "DNS resolution failed: Unable to resolve the provider hostname"
            elif "ssl" in error_msg.lower() or "certificate" in error_msg.lower():
                error_msg = "SSL certificate error: Unable to establish secure connection"
            else:
                error_msg = f"Network error: {error_msg}"

            return HealthStatus(
                is_healthy=False,
                error_message=error_msg,
            )

        except Exception as e:
            return HealthStatus(
                is_healthy=False,
                error_message=f"Unexpected error: {str(e)}",
            )

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: str,
    ) -> tuple[Decimal, Decimal]:
        """Calculate cost for a request."""
        pricing = OPENAI_PRICING.get(model_id, {"input": 0, "output": 0})

        input_cost = Decimal(str(pricing["input"])) * input_tokens / Decimal("1000")
        output_cost = Decimal(str(pricing["output"])) * output_tokens / Decimal("1000")

        return input_cost, output_cost

    @staticmethod
    def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for
            model: Model to use for tokenization

        Returns:
            int: Number of tokens
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except KeyError:
            # Fallback to cl100k_base encoding
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
