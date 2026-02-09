"""
Provider-related Pydantic schemas.
"""
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ProviderType(str, Enum):
    """Provider type enumeration."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class ProviderStatus(str, Enum):
    """Provider status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNHEALTHY = "unhealthy"


class ProviderBase(BaseModel):
    """Base provider schema."""
    name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    provider_type: ProviderType = Field(..., description="Provider type")
    api_key: str = Field(..., min_length=1, description="API key")
    base_url: str = Field(..., min_length=1, description="Base URL")
    region: Optional[str] = Field(None, max_length=50, description="Provider region")
    organization: Optional[str] = Field(None, max_length=100, description="Organization ID")
    timeout: int = Field(default=60, ge=1, le=300, description="Timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Max retries")
    status: ProviderStatus = Field(default=ProviderStatus.ACTIVE, description="Provider status")
    priority: int = Field(default=100, description="Provider priority")
    weight: int = Field(default=100, ge=1, description="Load balance weight")


class ProviderCreate(ProviderBase):
    """Create provider schema."""
    pass


class ProviderUpdate(BaseModel):
    """Update provider schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, min_length=1)
    base_url: Optional[str] = Field(None, min_length=1)
    region: Optional[str] = Field(None, max_length=50)
    organization: Optional[str] = Field(None, max_length=100)
    timeout: Optional[int] = Field(None, ge=1, le=300)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    status: Optional[ProviderStatus] = None
    priority: Optional[int] = None
    weight: Optional[int] = Field(None, ge=1)


class ProviderResponse(ProviderBase):
    """Provider response schema."""
    id: int = Field(..., description="Provider ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class ProviderModelBase(BaseModel):
    """Base provider model schema."""
    model_id: str = Field(..., min_length=1, max_length=100, description="Model ID")
    name: str = Field(..., min_length=1, max_length=200, description="Model name")
    context_window: int = Field(..., ge=1, description="Context window size")
    input_price_per_1k: float = Field(..., ge=0, description="Input price per 1K tokens")
    output_price_per_1k: float = Field(..., ge=0, description="Output price per 1K tokens")
    is_active: bool = Field(default=True, description="Whether model is active")
    priority: int = Field(default=100, description="Model priority for routing")
    weight: int = Field(default=100, ge=1, description="Load balance weight")


class ProviderModelCreate(ProviderModelBase):
    """Create provider model schema."""
    pass


class ProviderModelUpdate(BaseModel):
    """Update provider model schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    context_window: Optional[int] = Field(None, ge=1)
    input_price_per_1k: Optional[float] = Field(None, ge=0)
    output_price_per_1k: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, description="Model priority for routing")
    weight: Optional[int] = Field(None, ge=1, description="Load balance weight")


class ProviderModelResponse(ProviderModelBase):
    """Provider model response schema."""
    id: int = Field(..., description="Model ID")
    provider_id: int = Field(..., description="Provider ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    healthy: bool = Field(..., description="Whether service is healthy")
    providers: list = Field(..., description="Provider health status")


class ProviderHealth(BaseModel):
    """Provider health schema."""
    provider_id: int = Field(..., description="Provider ID")
    provider_name: str = Field(..., description="Provider name")
    is_healthy: bool = Field(..., description="Health status")
    latency_ms: Optional[int] = Field(None, description="Latency in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message")
