"""
Router control API endpoints.
"""
from fastapi import APIRouter, Request, HTTPException, status

from src.api.middleware import require_admin
from src.schemas.router import (
    SwitchStatusResponse,
    ToggleRequest,
    ToggleResponse,
    RouterMetrics,
    RoutingRuleCreate,
    RoutingRuleUpdate,
    RoutingRuleResponse,
    RoutingRuleListResponse,
)
from src.agents.gateway_orchestrator import orchestrator
from src.agents.routing_agent import routing_agent
from src.utils.logging import logger


router = APIRouter(prefix="/router", tags=["router"])


@router.get("/status", response_model=SwitchStatusResponse)
async def get_router_status(request: Request):
    """
    Get current routing switch status.

    Returns the current state of the routing switch, including
    any pending switches and cooldown information.
    """
    from src.api.middleware import require_admin
    await require_admin(request.get_route_handler())(request)

    try:
        status_info = await orchestrator.get_status()
        return SwitchStatusResponse(
            enabled=status_info.enabled,
            pending=status_info.pending,
            pending_value=status_info.pending_value,
            scheduled_at=status_info.scheduled_at,
            cooldown_until=status_info.cooldown_until,
            can_toggle=status_info.can_toggle,
        )
    except Exception as e:
        logger.error(f"Get router status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/toggle", response_model=ToggleResponse)
async def toggle_router(
    request: ToggleRequest,
    http_request: Request,
):
    """
    Toggle routing switch.

    Enables or disables the routing switch with optional delay.
    Default delay is 10 seconds for safety.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth
    user, api_key = await APIKeyAuth.verify_api_key(http_request)

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        status_info = await orchestrator.toggle(
            value=request.value,
            reason=request.reason,
            triggered_by=user.username,
            force=request.force,
            delay=request.delay,
        )

        logger.info(
            f"Router toggle by {user.username}: "
            f"{'enabled' if status_info.enabled else 'disabled'}"
        )

        return ToggleResponse(
            status=SwitchStatusResponse(
                enabled=status_info.enabled,
                pending=status_info.pending,
                pending_value=status_info.pending_value,
                scheduled_at=status_info.scheduled_at,
                cooldown_until=status_info.cooldown_until,
                can_toggle=status_info.can_toggle,
            ),
            message=f"Routing switch {'enabled' if status_info.enabled else 'disabled'}",
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Toggle router error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/history", response_model=list[dict])
async def get_router_history(
    request: Request,
    limit: int = 100,
):
    """
    Get routing switch history.

    Returns the history of routing switch toggles.
    """
    from src.api.middleware import require_admin
    await require_admin(request.get_route_handler())(request)

    try:
        history = await orchestrator.get_history(limit=limit)
        return history
    except Exception as e:
        logger.error(f"Get router history error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/metrics", response_model=RouterMetrics)
async def get_router_metrics(request: Request):
    """
    Get router metrics.

    Returns statistics about router performance and usage.
    """
    from src.api.middleware import require_admin
    await require_admin(request.get_route_handler())(request)

    try:
        metrics = await orchestrator.get_metrics()
        return RouterMetrics(**metrics)
    except Exception as e:
        logger.error(f"Get router metrics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/rules", response_model=RoutingRuleListResponse)
async def list_routing_rules(http_request: Request):
    """
    List all routing rules.

    Returns all configured routing rules.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth
    user, api_key = await APIKeyAuth.verify_api_key(http_request)

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        rules = await routing_agent._get_active_rules()
        return RoutingRuleListResponse(
            rules=[
                RoutingRuleResponse(
                    id=rule.id,
                    name=rule.name,
                    description=rule.description,
                    condition_type=rule.condition_type,
                    condition_value=rule.condition_value,
                    min_complexity=rule.min_complexity,
                    max_complexity=rule.max_complexity,
                    action_type=rule.action_type,
                    action_value=rule.action_value,
                    priority=rule.priority,
                    is_active=rule.is_active,
                    hit_count=rule.hit_count,
                    created_at=rule.created_at.isoformat(),
                    updated_at=rule.updated_at.isoformat(),
                )
                for rule in rules
            ],
            total=len(rules),
        )
    except Exception as e:
        logger.error(f"List routing rules error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/rules", response_model=RoutingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_rule(
    request: RoutingRuleCreate,
    http_request: Request,
):
    """
    Create a new routing rule.

    Creates a new routing rule for automatic provider/model selection.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth
    user, api_key = await APIKeyAuth.verify_api_key(http_request)

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    from src.models.routing import RoutingRule

    try:
        rule = RoutingRule(
            name=request.name,
            description=request.description,
            condition_type=request.condition_type,
            condition_value=request.condition_value,
            min_complexity=request.min_complexity,
            max_complexity=request.max_complexity,
            action_type=request.action_type,
            action_value=request.action_value,
            priority=request.priority,
            is_active=request.is_active,
        )

        from src.db.session import SessionManager
        result = await SessionManager.execute_insert(rule)

        return RoutingRuleResponse(
            id=result.id,
            name=result.name,
            description=result.description,
            condition_type=result.condition_type,
            condition_value=result.condition_value,
            min_complexity=result.min_complexity,
            max_complexity=result.max_complexity,
            action_type=result.action_type,
            action_value=result.action_value,
            priority=result.priority,
            is_active=result.is_active,
            hit_count=result.hit_count,
            created_at=result.created_at.isoformat(),
            updated_at=result.updated_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"Create routing rule error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
