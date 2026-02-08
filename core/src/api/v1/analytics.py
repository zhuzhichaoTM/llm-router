"""
Analytics API endpoints for system performance and usage analysis.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case, literal_column
from sqlalchemy.orm import selectinload

from src.utils.logging import logger
from src.db.base import async_session_maker
from src.models.routing import RoutingDecision
from src.models.cost import CostRecord
from src.models.user import User, APIKey

router = APIRouter(prefix="/analytics", tags=["analytics"])


class PerformanceMetrics(BaseModel):
    """Performance metrics response."""
    avgResponseTime: float
    p95ResponseTime: float
    p99ResponseTime: float
    errorRate: float
    qps: float
    totalRequests: int


class ErrorLogEntry(BaseModel):
    """Error log entry."""
    id: str
    request_id: str
    error_code: str
    error_message: str
    error_type: str
    provider_id: Optional[str]
    model: Optional[str]
    timestamp: str


class ErrorSummary(BaseModel):
    """Error summary response."""
    total: int
    byType: dict[str, int]


class ModelAnalyticsEntry(BaseModel):
    """Model analytics entry."""
    model: str
    request_count: int
    success_count: int
    success_rate: float
    avg_latency: float
    total_cost: float
    total_tokens: int


class UserAnalyticsEntry(BaseModel):
    """User analytics entry."""
    user_id: int
    request_count: int
    total_cost: float
    last_active: str


class UserAnalyticsResponse(BaseModel):
    """User analytics response."""
    totalUsers: int
    activeUsers: int
    newUsers: int
    topUsers: list[UserAnalyticsEntry]


class CostAnalyticsEntry(BaseModel):
    """Cost analytics entry."""
    model: str
    request_count: int
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float


class CostAnalyticsResponse(BaseModel):
    """Cost analytics response."""
    totalCost: float
    byModel: list[CostAnalyticsEntry]
    trend: list[dict]


class AlertEntry(BaseModel):
    """Alert entry."""
    id: str
    rule_name: str
    severity: str
    description: str
    is_active: bool
    triggered_at: Optional[str]


async def _verify_api_key(request: Request):
    """Verify API key and return user."""
    from src.api.middleware import APIKeyAuth
    result = await APIKeyAuth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    user, api_key = result
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user, api_key


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    request: Request,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """
    Get performance metrics for a date range.

    Returns average, P95, P99 response times, error rate, QPS, and total requests.
    """
    user, api_key = await _verify_api_key(request)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

        async with async_session_maker() as session:
            # Get routing decisions for the date range
            result = await session.execute(
                select(RoutingDecision)
                .where(RoutingDecision.created_at >= start_dt)
                .where(RoutingDecision.created_at < end_dt)
                .order_by(RoutingDecision.created_at)
            )
            decisions = result.scalars().all()

            if not decisions:
                return PerformanceMetrics(
                    avgResponseTime=0,
                    p95ResponseTime=0,
                    p99ResponseTime=0,
                    errorRate=0,
                    qps=0,
                    totalRequests=0,
                )

            # Calculate metrics
            latencies = [d.latency_ms for d in decisions]
            latencies.sort()
            n = len(latencies)

            avg_latency = sum(latencies) / n
            p95_latency = latencies[int(n * 0.95)] if n >= 20 else latencies[-1]
            p99_latency = latencies[int(n * 0.99)] if n >= 100 else latencies[-1]

            success_count = sum(1 for d in decisions if d.success)
            error_rate = (n - success_count) / n if n > 0 else 0

            # Calculate QPS (requests per second over the date range)
            time_diff = (end_dt - start_dt).total_seconds()
            qps = n / time_diff if time_diff > 0 else 0

            return PerformanceMetrics(
                avgResponseTime=round(avg_latency, 2),
                p95ResponseTime=round(p95_latency, 2),
                p99ResponseTime=round(p99_latency, 2),
                errorRate=round(error_rate, 4),
                qps=round(qps, 2),
                totalRequests=n,
            )

    except Exception as e:
        logger.error(f"Get performance metrics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/errors", response_model=list[ErrorLogEntry])
async def get_error_logs(
    request: Request,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Maximum number of entries to return"),
):
    """Get error logs for a date range."""
    user, api_key = await _verify_api_key(request)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

        async with async_session_maker() as session:
            # Get failed routing decisions
            result = await session.execute(
                select(RoutingDecision)
                .where(RoutingDecision.created_at >= start_dt)
                .where(RoutingDecision.created_at < end_dt)
                .where(RoutingDecision.success == False)
                .order_by(RoutingDecision.created_at.desc())
                .limit(limit)
            )
            errors = result.scalars().all()

            return [
                ErrorLogEntry(
                    id=str(e.id),
                    request_id=e.request_id,
                    error_code="500",
                    error_message=e.error_message or "Unknown error",
                    error_type="5xx" if not e.success else "4xx",
                    provider_id=str(e.provider_id),
                    model=e.model_id,
                    timestamp=e.created_at.isoformat(),
                )
                for e in errors
            ]

    except Exception as e:
        logger.error(f"Get error logs error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/errors/summary", response_model=ErrorSummary)
async def get_error_summary(
    request: Request,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get error summary for a date range."""
    user, api_key = await _verify_api_key(request)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

        async with async_session_maker() as session:
            # Get total errors
            total_result = await session.execute(
                select(func.count(RoutingDecision.id))
                .where(RoutingDecision.created_at >= start_dt)
                .where(RoutingDecision.created_at < end_dt)
                .where(RoutingDecision.success == False)
            )
            total = total_result.scalar() or 0

            # Get errors by type (based on error message)
            result = await session.execute(
                select(RoutingDecision)
                .where(RoutingDecision.created_at >= start_dt)
                .where(RoutingDecision.created_at < end_dt)
                .where(RoutingDecision.success == False)
            )
            errors = result.scalars().all()

            by_type = {}
            for e in errors:
                error_type = "5xx"
                if "timeout" in (e.error_message or "").lower():
                    error_type = "timeout"
                elif "rate_limit" in (e.error_message or "").lower():
                    error_type = "rate_limit"
                by_type[error_type] = by_type.get(error_type, 0) + 1

            return ErrorSummary(total=total, byType=by_type)

    except Exception as e:
        logger.error(f"Get error summary error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/models", response_model=list[ModelAnalyticsEntry])
async def get_model_analytics(
    request: Request,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get model usage analytics for a date range."""
    user, api_key = await _verify_api_key(request)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

        async with async_session_maker() as session:
            # Get model statistics
            result = await session.execute(
                select(
                    RoutingDecision.model_id,
                    func.count(RoutingDecision.id).label("count"),
                    func.sum(case((RoutingDecision.success == True, 1), else_=0)).label("success_count"),
                    func.avg(RoutingDecision.latency_ms).label("avg_latency"),
                    func.sum(RoutingDecision.cost).label("total_cost"),
                    func.sum(RoutingDecision.input_tokens + RoutingDecision.output_tokens).label("total_tokens"),
                )
                .where(RoutingDecision.created_at >= start_dt)
                .where(RoutingDecision.created_at < end_dt)
                .group_by(RoutingDecision.model_id)
            )
            rows = result.all()

            return [
                ModelAnalyticsEntry(
                    model=row.model_id,
                    request_count=row.count,
                    success_count=row.success_count or 0,
                    success_rate=round((row.success_count or 0) / row.count, 4) if row.count > 0 else 0,
                    avg_latency=round(row.avg_latency, 2) if row.avg_latency else 0,
                    total_cost=float(row.total_cost or 0),
                    total_tokens=row.total_tokens or 0,
                )
                for row in rows
            ]

    except Exception as e:
        logger.error(f"Get model analytics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/users", response_model=UserAnalyticsResponse)
async def get_user_analytics(
    request: Request,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get user analytics for a date range."""
    user, api_key = await _verify_api_key(request)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

        async with async_session_maker() as session:
            # Get total users
            total_users_result = await session.execute(
                select(func.count(User.id))
            )
            total_users = total_users_result.scalar() or 0

            # Get active users (users with requests in the date range)
            active_users_result = await session.execute(
                select(func.count(func.distinct(RoutingDecision.user_id)))
                .where(RoutingDecision.created_at >= start_dt)
                .where(RoutingDecision.created_at < end_dt)
            )
            active_users = active_users_result.scalar() or 0

            # Get new users (created in the date range)
            new_users_result = await session.execute(
                select(func.count(User.id))
                .where(User.created_at >= start_dt)
                .where(User.created_at < end_dt)
            )
            new_users = new_users_result.scalar() or 0

            # Get top users by request count
            top_users_result = await session.execute(
                select(
                    RoutingDecision.user_id,
                    func.count(RoutingDecision.id).label("count"),
                    func.sum(RoutingDecision.cost).label("total_cost"),
                    func.max(RoutingDecision.created_at).label("last_active"),
                )
                .where(RoutingDecision.created_at >= start_dt)
                .where(RoutingDecision.created_at < end_dt)
                .group_by(RoutingDecision.user_id)
                .order_by(func.count(RoutingDecision.id).desc())
                .limit(10)
            )
            top_users_rows = top_users_result.all()

            top_users = [
                UserAnalyticsEntry(
                    user_id=row.user_id,
                    request_count=row.count,
                    total_cost=float(row.total_cost or 0),
                    last_active=row.last_active.isoformat(),
                )
                for row in top_users_rows
            ]

            return UserAnalyticsResponse(
                totalUsers=total_users,
                activeUsers=active_users,
                newUsers=new_users,
                topUsers=top_users,
            )

    except Exception as e:
        logger.error(f"Get user analytics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/cost", response_model=CostAnalyticsResponse)
async def get_cost_analytics(
    request: Request,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get cost analytics for a date range."""
    user, api_key = await _verify_api_key(request)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

        async with async_session_maker() as session:
            # Get total cost
            total_cost_result = await session.execute(
                select(func.sum(CostRecord.total_cost))
                .where(CostRecord.created_at >= start_dt)
                .where(CostRecord.created_at < end_dt)
            )
            total_cost = total_cost_result.scalar() or 0

            # Get cost by model
            by_model_result = await session.execute(
                select(
                    CostRecord.model_id,
                    func.count(CostRecord.id).label("count"),
                    func.sum(CostRecord.input_tokens).label("input_tokens"),
                    func.sum(CostRecord.output_tokens).label("output_tokens"),
                    func.sum(CostRecord.input_cost).label("input_cost"),
                    func.sum(CostRecord.output_cost).label("output_cost"),
                    func.sum(CostRecord.total_cost).label("total_cost"),
                )
                .where(CostRecord.created_at >= start_dt)
                .where(CostRecord.created_at < end_dt)
                .group_by(CostRecord.model_id)
            )
            by_model_rows = by_model_result.all()

            by_model = [
                CostAnalyticsEntry(
                    model=row.model_id,
                    request_count=row.count,
                    input_tokens=row.input_tokens or 0,
                    output_tokens=row.output_tokens or 0,
                    input_cost=float(row.input_cost or 0),
                    output_cost=float(row.output_cost or 0),
                    total_cost=float(row.total_cost or 0),
                )
                for row in by_model_rows
            ]

            # Get cost trend (by day)
            trend_result = await session.execute(
                select(
                    func.date(CostRecord.created_at).label("date"),
                    func.sum(CostRecord.total_cost).label("cost"),
                )
                .where(CostRecord.created_at >= start_dt)
                .where(CostRecord.created_at < end_dt)
                .group_by(func.date(CostRecord.created_at))
                .order_by(func.date(CostRecord.created_at))
            )
            trend_rows = trend_result.all()

            trend = [{"date": str(row.date), "cost": float(row.cost or 0)} for row in trend_rows]

            return CostAnalyticsResponse(
                totalCost=float(total_cost),
                byModel=by_model,
                trend=trend,
            )

    except Exception as e:
        logger.error(f"Get cost analytics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/alerts", response_model=list[AlertEntry])
async def get_alerts(request: Request):
    """Get active alerts."""
    user, api_key = await _verify_api_key(request)

    try:
        # For now, return empty list
        # TODO: Implement alert system
        return []

    except Exception as e:
        logger.error(f"Get alerts error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
