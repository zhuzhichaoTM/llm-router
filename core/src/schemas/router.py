"""
Router-related Pydantic schemas.
"""
from typing import Optional
from pydantic import BaseModel, Field


class SwitchStatusResponse(BaseModel):
    """Routing switch status response schema."""
    enabled: bool = Field(..., description="Whether routing is enabled")
    pending: bool = Field(..., description="Whether there's a pending switch")
    pending_value: Optional[bool] = Field(None, description="Pending switch value")
    scheduled_at: Optional[int] = Field(None, description="Scheduled switch timestamp")
    cooldown_until: Optional[int] = Field(None, description="Cooldown end timestamp")
    can_toggle: bool = Field(..., description="Whether toggle is allowed")


class ToggleRequest(BaseModel):
    """Toggle switch request schema."""
    value: bool = Field(..., description="New switch value")
    reason: str = Field(default="Manual toggle", description="Reason for toggle")
    force: bool = Field(default=False, description="Force immediate toggle")
    delay: Optional[int] = Field(None, ge=0, description="Custom delay in seconds")


class ToggleResponse(BaseModel):
    """Toggle switch response schema."""
    status: SwitchStatusResponse
    message: str


class RouterMetrics(BaseModel):
    """Router metrics schema."""
    current_status: bool = Field(..., description="Current routing status")
    pending_switch: bool = Field(..., description="Whether there's a pending switch")
    cooldown_remaining: int = Field(..., description="Cooldown remaining seconds")
    total_switches: int = Field(..., description="Total number of switches")
    enabled_count: int = Field(..., description="Number of times enabled")
    disabled_count: int = Field(..., description="Number of times disabled")
    recent_history: list = Field(default_factory=list, description="Recent switch history")


class RoutingRuleBase(BaseModel):
    """Base routing rule schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None)
    condition_type: str = Field(..., description="Rule condition type")
    condition_value: str = Field(..., description="Rule condition value")
    min_complexity: Optional[int] = Field(None, ge=0)
    max_complexity: Optional[int] = Field(None, ge=0)
    action_type: str = Field(..., description="Rule action type")
    action_value: str = Field(..., description="Rule action value")
    priority: int = Field(default=0, description="Rule priority")
    is_active: bool = Field(default=True)


class RoutingRuleCreate(RoutingRuleBase):
    """Create routing rule schema."""
    pass


class RoutingRuleUpdate(RoutingRuleBase):
    """Update routing rule schema."""
    pass


class RoutingRuleResponse(RoutingRuleBase):
    """Routing rule response schema."""
    id: int = Field(..., description="Rule ID")
    hit_count: int = Field(..., description="Number of times rule matched")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class RoutingRuleListResponse(BaseModel):
    """Routing rule list response schema."""
    rules: list[RoutingRuleResponse] = Field(..., description="List of rules")
    total: int = Field(..., description="Total number of rules")
