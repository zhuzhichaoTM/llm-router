"""
Cost-related Pydantic schemas.
"""
from typing import Optional
from pydantic import BaseModel, Field


class DailyCost(BaseModel):
    """Daily cost schema."""
    date: str = Field(..., description="Date (ISO format)")
    cost: float = Field(..., description="Total cost")
    tokens: int = Field(..., description="Total tokens")


class ModelCost(BaseModel):
    """Model cost schema."""
    model_id: str = Field(..., description="Model ID")
    total_cost: float = Field(..., description="Total cost")
    request_count: int = Field(..., description="Number of requests")
    total_tokens: int = Field(..., description="Total tokens")


class UserCost(BaseModel):
    """User cost schema."""
    user_id: int = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username")
    total_cost: float = Field(..., description="Total cost")
    request_count: int = Field(..., description="Number of requests")


class CostSummary(BaseModel):
    """Cost summary schema."""
    period: str = Field(..., description="Period description")
    total_cost: float = Field(..., description="Total cost")
    input_cost: float = Field(..., description="Input cost")
    output_cost: float = Field(..., description="Output cost")
    total_tokens: int = Field(..., description="Total tokens")
    input_tokens: int = Field(..., description="Input tokens")
    output_tokens: int = Field(..., description="Output tokens")
    total_requests: int = Field(..., description="Total requests")


class CurrentCostResponse(BaseModel):
    """Current cost response schema."""
    daily: dict = Field(..., description="Daily cost stats")
    total: float = Field(..., description="Total cost")


class CostByModelResponse(BaseModel):
    """Cost by model response schema."""
    models: list[ModelCost] = Field(..., description="Cost by model")


class CostByUserResponse(BaseModel):
    """Cost by user response schema."""
    users: list[UserCost] = Field(..., description="Cost by user")
