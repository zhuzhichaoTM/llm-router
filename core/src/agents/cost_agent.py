"""
Cost Agent - Tracks and analyzes LLM usage costs.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import select, func, and_
from decimal import Decimal

from src.config.redis_config import RedisConfig, RedisKeys
from src.config.settings import settings
from src.models.cost import CostRecord
from src.db.session import SessionManager
from src.utils.encryption import generate_session_id


@dataclass
class CostSummary:
    """Cost summary data."""
    period: str
    total_cost: float
    input_cost: float
    output_cost: float
    total_tokens: int
    input_tokens: int
    output_tokens: int
    total_requests: int


@dataclass
class ModelCost:
    """Cost per model."""
    model_id: str
    total_cost: float
    request_count: int
    total_tokens: int


@dataclass
class UserCost:
    """Cost per user."""
    user_id: int
    username: Optional[str]
    total_cost: float
    request_count: int


class CostAgent:
    """
    Cost Agent tracks and analyzes LLM usage costs.

    Features:
    - Real-time cost tracking via Redis
    - Persistent cost records in PostgreSQL
    - Cost aggregation by time, model, user
    - Budget monitoring
    """

    _instance: Optional["CostAgent"] = None

    def __new__(cls) -> "CostAgent":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the cost agent."""
        if self._initialized:
            return

        self._initialized = True

    async def record_cost(
        self,
        session_id: str,
        request_id: str,
        user_id: Optional[int],
        api_key_id: Optional[int],
        provider_id: int,
        model_id: str,
        provider_type: str,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record cost for a request.

        Args:
            session_id: Session identifier
            request_id: Request identifier
            user_id: Optional user ID
            api_key_id: Optional API key ID
            provider_id: Provider ID
            model_id: Model ID
            provider_type: Provider type
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            input_cost: Input cost
            output_cost: Output cost
            metadata: Optional metadata
        """
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens

        # Record in database
        cost_record = CostRecord(
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            api_key_id=api_key_id,
            provider_id=provider_id,
            model_id=model_id,
            provider_type=provider_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=Decimal(str(input_cost)),
            output_cost=Decimal(str(output_cost)),
            total_cost=Decimal(str(total_cost)),
            metadata=metadata or {},
        )

        await SessionManager.execute_insert(cost_record)

        # Update Redis real-time stats
        await self._update_redis_cost(
            user_id=user_id,
            model_id=model_id,
            provider_id=provider_id,
            input_cost=input_cost,
            output_cost=output_cost,
            total_tokens=total_tokens,
        )

    async def _update_redis_cost(
        self,
        user_id: Optional[int],
        model_id: str,
        provider_id: int,
        input_cost: float,
        output_cost: float,
        total_tokens: int,
    ) -> None:
        """Update Redis real-time cost stats."""
        redis = await RedisConfig.get_client()
        today = date.today().isoformat()
        now = int(datetime.now(timezone.utc).timestamp())

        # Daily cost
        await redis.hincrbyfloat(
            RedisKeys.COST_DAILY.format(date=today),
            "total_cost",
            input_cost + output_cost,
        )
        await redis.hincrby(
            RedisKeys.COST_DAILY.format(date=today),
            "total_tokens",
            total_tokens,
        )
        await redis.expire(RedisKeys.COST_DAILY.format(date=today), 86400 * 7)

        # Model cost
        await redis.hincrbyfloat(
            RedisKeys.COST_MODEL.format(model=model_id),
            "total_cost",
            input_cost + output_cost,
        )
        await redis.hincrby(
            RedisKeys.COST_MODEL.format(model=model_id),
            "total_tokens",
            total_tokens,
        )
        await redis.expire(RedisKeys.COST_MODEL.format(model=model_id), 86400 * 7)

        # User cost
        if user_id:
            await redis.hincrbyfloat(
                RedisKeys.COST_USER.format(user_id=user_id),
                "total_cost",
                input_cost + output_cost,
            )
            await redis.hincrby(
                RedisKeys.COST_USER.format(user_id=user_id),
                "total_tokens",
                total_tokens,
            )
            await redis.expire(RedisKeys.COST_USER.format(user_id=user_id), 86400 * 7)

        # Total cost
        await redis.incrbyfloat(RedisKeys.COST_TOTAL, input_cost + output_cost)

    async def get_current_cost(self) -> Dict[str, Any]:
        """
        Get current real-time cost stats.

        Returns:
            dict: Current cost statistics
        """
        redis = await RedisConfig.get_client()
        today = date.today().isoformat()

        # Get daily cost
        daily = await redis.hgetall(RedisKeys.COST_DAILY.format(date=today))
        daily_cost = float(daily.get("total_cost", 0))
        daily_tokens = int(daily.get("total_tokens", 0))

        # Get total cost
        total_cost = await redis.get(RedisKeys.COST_TOTAL) or "0"

        return {
            "daily": {
                "cost": daily_cost,
                "tokens": daily_tokens,
            },
            "total": float(total_cost),
        }

    async def get_daily_cost(
        self,
        days: int = 7,
    ) -> list[Dict[str, Any]]:
        """
        Get daily cost for the last N days.

        Args:
            days: Number of days

        Returns:
            list[dict]: Daily cost data
        """
        result = []
        redis = await RedisConfig.get_client()

        for i in range(days):
            d = date.today() - timedelta(days=i)
            daily = await redis.hgetall(RedisKeys.COST_DAILY.format(date=d.isoformat()))

            result.append({
                "date": d.isoformat(),
                "cost": float(daily.get("total_cost", 0)),
                "tokens": int(daily.get("total_tokens", 0)),
            })

        return list(reversed(result))

    async def get_cost_by_model(self, limit: int = 20) -> list[ModelCost]:
        """
        Get cost aggregated by model.

        Args:
            limit: Maximum number of models

        Returns:
            list[ModelCost]: Cost by model
        """
        from sqlalchemy import select, func

        result = await SessionManager.execute_select(
            select(
                CostRecord.model_id,
                func.sum(CostRecord.total_cost).label("total_cost"),
                func.count(CostRecord.id).label("request_count"),
                func.sum(CostRecord.total_tokens).label("total_tokens"),
            ).group_by(CostRecord.model_id)
            .order_by(func.sum(CostRecord.total_cost).desc())
            .limit(limit)
        )

        return [
            ModelCost(
                model_id=row.model_id,
                total_cost=float(row.total_cost),
                request_count=row.request_count,
                total_tokens=row.total_tokens,
            )
            for row in result
        ]

    async def get_cost_by_user(self, limit: int = 20) -> list[UserCost]:
        """
        Get cost aggregated by user.

        Args:
            limit: Maximum number of users

        Returns:
            list[UserCost]: Cost by user
        """
        from sqlalchemy import select, func
        from src.models.user import User

        result = await SessionManager.execute_select(
            select(
                CostRecord.user_id,
                User.username,
                func.sum(CostRecord.total_cost).label("total_cost"),
                func.count(CostRecord.id).label("request_count"),
            ).join(
                User,
                CostRecord.user_id == User.id
            ).where(
                CostRecord.user_id.isnot(None)
            ).group_by(
                CostRecord.user_id,
                User.username,
            ).order_by(
                func.sum(CostRecord.total_cost).desc()
            ).limit(limit)
        )

        return [
            UserCost(
                user_id=row.user_id,
                username=row.username,
                total_cost=float(row.total_cost),
                request_count=row.request_count,
            )
            for row in result
        ]

    async def get_cost_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CostSummary:
        """
        Get cost summary for a date range.

        Args:
            start_date: Start date (defaults to today)
            end_date: End date (defaults to today)

        Returns:
            CostSummary: Cost summary
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = date.today()

        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

        from sqlalchemy import select, func

        result = await SessionManager.execute_get_one(
            select(
                func.sum(CostRecord.input_cost).label("input_cost"),
                func.sum(CostRecord.output_cost).label("output_cost"),
                func.sum(CostRecord.total_cost).label("total_cost"),
                func.sum(CostRecord.input_tokens).label("input_tokens"),
                func.sum(CostRecord.output_tokens).label("output_tokens"),
                func.sum(CostRecord.total_tokens).label("total_tokens"),
                func.count(CostRecord.id).label("total_requests"),
            ).where(
                and_(
                    CostRecord.created_at >= start_dt,
                    CostRecord.created_at <= end_dt,
                )
            )
        )

        period = f"{start_date.isoformat()} to {end_date.isoformat()}"

        return CostSummary(
            period=period,
            total_cost=float(result.total_cost or 0),
            input_cost=float(result.input_cost or 0),
            output_cost=float(result.output_cost or 0),
            total_tokens=result.total_tokens or 0,
            input_tokens=result.input_tokens or 0,
            output_tokens=result.output_tokens or 0,
            total_requests=result.total_requests or 0,
        )


# Global instance
cost_agent = CostAgent()
