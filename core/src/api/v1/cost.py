"""
Cost tracking API endpoints.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Query

from src.api.middleware import require_admin
from src.schemas.cost import (
    CurrentCostResponse,
    DailyCost,
    CostSummary,
    ModelCost,
    CostByModelResponse,
    UserCost,
    CostByUserResponse,
)
from src.agents.cost_agent import cost_agent
from src.utils.logging import logger


router = APIRouter(prefix="/cost", tags=["cost"])


@router.get("/current", response_model=CurrentCostResponse)
async def get_current_cost(request: Request):
    """
    Get current real-time cost statistics.

    Returns the current daily cost and total cost from Redis.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        current = await cost_agent.get_current_cost()
        return CurrentCostResponse(**current)
    except Exception as e:
        logger.error(f"Get current cost error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/daily", response_model=list[DailyCost])
async def get_daily_cost(
    request: Request,
    days: int = Query(7, ge=1, le=90),
):
    """
    Get daily cost for the last N days.

    Returns daily cost statistics for the specified number of days.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        daily = await cost_agent.get_daily_cost(days=days)
        return [DailyCost(**d) for d in daily]
    except Exception as e:
        logger.error(f"Get daily cost error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/summary", response_model=CostSummary)
async def get_cost_summary(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Get cost summary for a date range.

    Returns aggregated cost statistics for the specified period.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        summary = await cost_agent.get_cost_summary(start_date, end_date)
        return CostSummary(**summary)
    except Exception as e:
        logger.error(f"Get cost summary error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/by-model", response_model=CostByModelResponse)
async def get_cost_by_model(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get cost aggregated by model.

    Returns cost statistics grouped by model.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        models = await cost_agent.get_cost_by_model(limit=limit)
        return CostByModelResponse(
            models=[ModelCost(**m.__dict__) for m in models]
        )
    except Exception as e:
        logger.error(f"Get cost by model error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/by-user", response_model=CostByUserResponse)
async def get_cost_by_user(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get cost aggregated by user.

    Returns cost statistics grouped by user.
    """
    # Verify admin access
    from src.api.middleware import APIKeyAuth

    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result

    if not user or user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        users = await cost_agent.get_cost_by_user(limit=limit)
        return CostByUserResponse(
            users=[UserCost(**u.__dict__) for u in users]
        )
    except Exception as e:
        logger.error(f"Get cost by user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
