"""
Cost calculation service.
"""
from decimal import Decimal
from typing import Dict, Optional


# Default pricing (in USD per 1K tokens)
DEFAULT_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-32k": {"input": 0.06, "output": 0.12},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-vision-preview": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-16k": {"input": 0.001, "output": 0.002},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}


class CostCalculator:
    """Cost calculation service."""

    @staticmethod
    def calculate_cost(
        input_tokens: int,
        output_tokens: int,
        model_id: str,
        input_price_per_1k: Optional[Decimal] = None,
        output_price_per_1k: Optional[Decimal] = None,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model_id: Model identifier
            input_price_per_1k: Custom input price per 1K tokens
            output_price_per_1k: Custom output price per 1K tokens

        Returns:
            tuple[Decimal, Decimal]: (input_cost, output_cost)
        """
        # Use provided prices or get default
        if input_price_per_1k is None:
            pricing = DEFAULT_PRICING.get(model_id, {"input": 0, "output": 0})
            input_price = Decimal(str(pricing["input"]))
        else:
            input_price = Decimal(str(input_price_per_1k))

        if output_price_per_1k is None:
            pricing = DEFAULT_PRICING.get(model_id, {"input": 0, "output": 0})
            output_price = Decimal(str(pricing["output"]))
        else:
            output_price = Decimal(str(output_price_per_1k))

        # Calculate costs
        input_cost = input_price * input_tokens / Decimal("1000")
        output_cost = output_price * output_tokens / Decimal("1000")

        return input_cost, output_cost

    @staticmethod
    def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Estimate number of tokens in text.

        Note: This is a rough estimate. For accurate counting,
        use the provider's token counting function.

        Args:
            text: Text to estimate tokens for
            model: Model to use for estimation

        Returns:
            int: Estimated number of tokens
        """
        # Rough approximation: ~4 characters per token
        return len(text) // 4

    @staticmethod
    def get_model_pricing(model_id: str) -> Dict[str, float]:
        """
        Get pricing for a model.

        Args:
            model_id: Model identifier

        Returns:
            dict: Pricing information
        """
        return DEFAULT_PRICING.get(model_id, {"input": 0, "output": 0})

    @staticmethod
    def set_model_pricing(model_id: str, input_price: float, output_price: float) -> None:
        """
        Set pricing for a model.

        Args:
            model_id: Model identifier
            input_price: Input price per 1K tokens
            output_price: Output price per 1K tokens
        """
        DEFAULT_PRICING[model_id] = {
            "input": input_price,
            "output": output_price,
        }
