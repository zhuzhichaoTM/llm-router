"""
Chat-related Pydantic schemas.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message schema."""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """Chat completion request schema."""
    model: str = Field(..., description="Model identifier")
    messages: List[Message] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    stream: bool = Field(False, description="Enable streaming")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")


class Usage(BaseModel):
    """Token usage schema."""
    input_tokens: int = Field(..., description="Input tokens")
    output_tokens: int = Field(..., description="Output tokens")
    total_tokens: int = Field(..., description="Total tokens")


class Choice(BaseModel):
    """Choice schema."""
    index: int = Field(..., description="Choice index")
    message: Message = Field(..., description="Message")
    finish_reason: str = Field(..., description="Finish reason")


class ChatCompletionResponse(BaseModel):
    """Chat completion response schema."""
    id: str = Field(..., description="Response ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Choice] = Field(..., description="Choices")
    usage: Usage = Field(..., description="Token usage")


class ChatCompletionErrorResponse(BaseModel):
    """Chat completion error response schema."""
    error: dict = Field(..., description="Error details")


class ModelInfo(BaseModel):
    """Model information schema."""
    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Model name")
    provider: str = Field(..., description="Provider name")
    context_window: int = Field(..., description="Context window size")
    input_price_per_1k: float = Field(..., description="Input price per 1K tokens")
    output_price_per_1k: float = Field(..., description="Output price per 1K tokens")
    priority: int = Field(default=100, description="Model priority for routing")
    weight: int = Field(default=100, description="Load balance weight")
