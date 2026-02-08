"""
Provider factory for creating provider instances.
"""
from typing import Dict, Type, Optional

from src.providers.base import IProvider, ProviderError
from src.providers.openai import OpenAIProvider
from src.providers.anthropic import AnthropicProvider


class ProviderFactory:
    """
    Factory for creating provider instances.

    Supports dynamic registration and creation of providers.
    """

    _providers: Dict[str, Type[IProvider]] = {}
    _instances: Dict[str, IProvider] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[IProvider]) -> None:
        """
        Register a provider class.

        Args:
            name: Provider name (e.g., "openai", "anthropic")
            provider_class: Provider class to register
        """
        cls._providers[name] = provider_class

    @classmethod
    def create_provider(
        cls,
        name: str,
        **kwargs,
    ) -> IProvider:
        """
        Create a new provider instance.

        Args:
            name: Provider name
            **kwargs: Provider-specific arguments

        Returns:
            IProvider: Provider instance

        Raises:
            ProviderError: If provider type is not registered
        """
        if name not in cls._providers:
            raise ProviderError(f"Unknown provider type: {name}")

        provider_class = cls._providers[name]
        return provider_class(**kwargs)

    @classmethod
    def get_provider(
        cls,
        name: str,
        **kwargs,
    ) -> IProvider:
        """
        Get or create a provider instance (cached).

        Args:
            name: Provider name
            **kwargs: Provider-specific arguments (only used for first creation)

        Returns:
            IProvider: Provider instance
        """
        if name not in cls._instances:
            cls._instances[name] = cls.create_provider(name, **kwargs)

        return cls._instances[name]

    @classmethod
    def has_provider(cls, name: str) -> bool:
        """Check if a provider is registered."""
        return name in cls._providers

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    async def close_all(cls) -> None:
        """Close all provider instances."""
        for provider in cls._instances.values():
            if hasattr(provider, "close"):
                await provider.close()  # type: ignore
        cls._instances.clear()


# Register built-in providers
ProviderFactory.register_provider("openai", OpenAIProvider)
ProviderFactory.register_provider("anthropic", AnthropicProvider)


def create_openai_provider(
    api_key: str,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    timeout: int = 60,
) -> OpenAIProvider:
    """
    Create an OpenAI provider.

    Args:
        api_key: OpenAI API key
        base_url: Base URL for OpenAI API
        organization: Optional organization ID
        timeout: Request timeout in seconds

    Returns:
        OpenAIProvider: Provider instance
    """
    return ProviderFactory.create_provider(
        "openai",
        api_key=api_key,
        base_url=base_url or "https://api.openai.com/v1",
        organization=organization,
        timeout=timeout,
    )


def create_anthropic_provider(
    api_key: str,
    base_url: Optional[str] = None,
    timeout: int = 60,
) -> AnthropicProvider:
    """
    Create an Anthropic provider.

    Args:
        api_key: Anthropic API key
        base_url: Base URL for Anthropic API
        timeout: Request timeout in seconds

    Returns:
        AnthropicProvider: Provider instance
    """
    return ProviderFactory.create_provider(
        "anthropic",
        api_key=api_key,
        base_url=base_url or "https://api.anthropic.com",
        timeout=timeout,
    )
