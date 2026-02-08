"""
Cost Optimization Engine - Multi-dimensional cost analysis and optimization.

This module provides:
- Multi-dimensional cost analysis (user, department, model)
- Cost driving factor analysis
- Model efficiency analysis
- Intelligent optimization strategies
- Budget management
- Cost forecasting
- AI-driven cost recommendations
"""
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cost import CostRecord
from src.models.provider import Provider, ProviderModel
from src.models.routing import RoutingDecision
from src.models.user import User
from src.db.session import SessionManager
from src.config.redis_config import RedisKeys
from src.services.redis_client import RedisService
from src.agents.load_balancer import ProviderMetrics


class OptimizationStrategy(str, Enum):
    """Cost optimization strategies."""
    CACHE_FAVORING = "cache_favoring"
    MODEL_DOWNGRADE = "model_downgrade"
    BATCH_OPTIMIZATION = "batch_optimization"
    BUDGET_ENFORCEMENT = "budget_enforcement"
    HYBRID_APPROACH = "hybrid"


class CostDimension(str, Enum):
    """Cost analysis dimensions."""
    BY_USER = "by_user"
    BY_MODEL = "by_model"
    BY_PROVIDER = "by_provider"
    BY_DATE = "by_date"
    BY_HOUR = "by_hour"
    BY_SCENARIO = "by_scenario"


@dataclass
class CostAnalysis:
    """Cost analysis result."""
    dimension: CostDimension
    breakdown: Dict[str, float]
    total_cost: float
    trend: List[Tuple[str, float]]  # (period, cost)
    growth_rate: float
    recommendations: List[str]


@dataclass
class BudgetInfo:
    """Budget information."""
    total_budget: float
    spent: float
    remaining: float
    utilization_rate: float
    daily_average: float
    projected_monthly: float
    over_budget: bool


@dataclass
class ModelEfficiency:
    """Model efficiency metrics."""
    model_id: str
    total_requests: int
    total_cost: float
    total_tokens: int
    avg_latency_ms: float
    avg_cost_per_1k: float
    cost_efficiency: float  # Requests per dollar


@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation."""
    strategy: OptimizationStrategy
    description: str
    expected_savings: float  # Percentage or absolute
    implementation_difficulty: str  # Low, Medium, High
    priority: str  # Low, Medium, High
    estimated_effort_hours: float


class CostAnalyzer:
    """
    Analyzes costs across multiple dimensions.

    Features:
    - User-level cost breakdown
    - Model-level cost analysis
    - Provider cost comparison
    - Temporal cost trends
    """

    def __init__(self):
        """Initialize the cost analyzer."""
        self._cache_ttl = 300  # 5 minutes
        self._analysis_cache: Dict[str, Tuple[Any, float]] = {}

    async def analyze_by_user(
        self,
        user_id: int,
        days: int = 30,
    ) -> CostAnalysis:
        """
        Analyze costs by user.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            CostAnalysis: User cost analysis
        """
        cache_key = f"user_cost:{user_id}:{days}"
        if cache_key in self._analysis_cache:
            cached, timestamp = self._analysis_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached

        # Query costs from database
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        from src.models.cost import CostRecord

        result = await SessionManager.execute_select(
            select(
                CostRecord.user_id,
                func.sum(CostRecord.cost).label("total_cost"),
                func.sum(CostRecord.input_tokens).label("total_tokens"),
                func.sum(CostRecord.output_tokens).label("output_tokens"),
                func.count(CostRecord.id).label("request_count"),
            )
            .where(
                and_(
                    CostRecord.user_id == user_id,
                    CostRecord.created_at >= start_date,
                )
            )
            .group_by(CostRecord.user_id)
        )

        if not result or not result[0][0]:
            # No data for this user
            return CostAnalysis(
                dimension=CostDimension.BY_USER,
                breakdown={},
                total_cost=0.0,
                trend=[],
                growth_rate=0.0,
                recommendations=[],
            )

        row = result[0]
        total_cost = float(row.total_cost or 0)

        # Get daily breakdown
        daily_costs = await SessionManager.execute_select(
            select(
                func.date(CostRecord.created_at).label("date"),
                func.sum(CostRecord.cost).label("daily_cost"),
            )
            .where(
                and_(
                    CostRecord.user_id == user_id,
                    CostRecord.created_at >= start_date,
                )
            )
            .group_by(func.date(CostRecord.created_at))
            .order_by(func.date(CostRecord.created_at))
        )

        breakdown = {
            str(row.date): float(row.daily_cost or 0)
            for row in daily_costs
        }

        # Calculate growth rate (compare first half vs second half)
        sorted_dates = sorted(breakdown.keys())
        if len(sorted_dates) >= 4:
            mid_point = len(sorted_dates) // 2
            first_half_avg = sum(
                breakdown[d] for d in sorted_dates[:mid_point]
            ) / mid_point
            second_half_avg = sum(
                breakdown[d] for d in sorted_dates[mid_point:]
            ) / (len(sorted_dates) - mid_point)
            growth_rate = (
                ((second_half_avg - first_half_avg) / first_half_avg * 100)
                if first_half_avg > 0 else 0
            )
        else:
            growth_rate = 0.0

        # Generate recommendations
        recommendations = []
        if total_cost > 100:  # User with significant costs
            recommendations.append("Consider setting budget alerts")
        if growth_rate > 20:
            recommendations.append("Rapid cost growth detected - review usage")

        analysis = CostAnalysis(
            dimension=CostDimension.BY_USER,
            breakdown=breakdown,
            total_cost=total_cost,
            trend=[(date, cost) for date, cost in sorted(breakdown.items())],
            growth_rate=growth_rate,
            recommendations=recommendations,
        )

        # Cache result
        self._analysis_cache[cache_key] = (analysis, time.time())

        return analysis

    async def analyze_by_model(
        self,
        days: int = 30,
    ) -> CostAnalysis:
        """
        Analyze costs by model.

        Args:
            days: Number of days to analyze

        Returns:
            CostAnalysis: Model cost analysis
        """
        cache_key = f"model_cost:{days}"
        if cache_key in self._analysis_cache:
            cached, timestamp = self._analysis_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached

        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Query from database (through routing decisions)
        from src.models.cost import CostRecord
        from src.models.routing import RoutingDecision

        result = await SessionManager.execute_select(
            select(
                RoutingDecision.model_id,
                func.sum(RoutingDecision.cost).label("total_cost"),
                func.sum(RoutingDecision.input_tokens).label("input_tokens"),
                func.sum(RoutingDecision.output_tokens).label("output_tokens"),
                func.count(RoutingDecision.id).label("request_count"),
            )
            .where(
                and_(
                    RoutingDecision.created_at >= start_date,
                    RoutingDecision.success == 1,
                )
            )
            .group_by(RoutingDecision.model_id)
        )

        if not result:
            return CostAnalysis(
                dimension=CostDimension.BY_MODEL,
                breakdown={},
                total_cost=0.0,
                trend=[],
                growth_rate=0.0,
                recommendations=[],
            )

        breakdown = {
            row.model_id: float(row.total_cost or 0)
            for row in result
        }

        total_cost = sum(breakdown.values())

        # Sort by cost
        sorted_models = sorted(
            breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )

        recommendations = []
        if sorted_models:
            most_expensive = sorted_models[0]
            least_expensive = sorted_models[-1]

            if most_expensive[1] > least_expensive[1] * 2:
                recommendations.append(
                    f"Consider routing from {most_expensive[0]} to {least_expensive[0]} "
                    f"to save {((most_expensive[1] - least_expensive[1]) / most_expensive[1] * 100):.1f}%"
                )

        analysis = CostAnalysis(
            dimension=CostDimension.BY_MODEL,
            breakdown=breakdown,
            total_cost=total_cost,
            trend=[],
            growth_rate=0.0,
            recommendations=recommendations,
        )

        self._analysis_cache[cache_key] = (analysis, time.time())

        return analysis

    async def analyze_efficiency(
        self,
        days: int = 7,
    ) -> List[ModelEfficiency]:
        """
        Analyze model efficiency.

        Args:
            days: Number of days to analyze

        Returns:
            List[ModelEfficiency]: Model efficiency metrics
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        from src.models.cost import CostRecord
        from src.models.routing import RoutingDecision

        # Query model performance and cost data
        results = await SessionManager.execute_select(
            select(
                RoutingDecision.model_id,
                func.sum(RoutingDecision.cost).label("total_cost"),
                func.sum(RoutingDecision.input_tokens).label("input_tokens"),
                func.sum(RoutingDecision.output_tokens).label("output_tokens"),
                func.sum(RoutingDecision.latency_ms).label("total_latency"),
                func.count(RoutingDecision.id).label("request_count"),
                func.avg(RoutingDecision.latency_ms).label("avg_latency"),
            )
            .where(
                and_(
                    RoutingDecision.created_at >= start_date,
                    RoutingDecision.success == 1,
                )
            )
            .group_by(RoutingDecision.model_id)
        )

        efficiencies = []

        for row in results:
            total_cost = float(row.total_cost or 0)
            total_requests = row.request_count or 0
            total_tokens = (row.input_tokens or 0) + (row.output_tokens or 0)
            avg_latency = float(row.avg_latency or 0)

            # Calculate efficiency (requests per dollar)
            cost_efficiency = (
                (total_requests / total_cost)
                if total_cost > 0 else 0
            )

            # Calculate avg cost per 1K tokens
            total_tokens_1k = total_tokens / 1000
            avg_cost_per_1k = (
                (total_cost / total_tokens_1k)
                if total_tokens_1k > 0 else 0
            )

            efficiencies.append(ModelEfficiency(
                model_id=row.model_id,
                total_requests=total_requests,
                total_cost=total_cost,
                total_tokens=total_tokens,
                avg_latency_ms=avg_latency,
                avg_cost_per_1k=avg_cost_per_1k,
                cost_efficiency=cost_efficiency,
            ))

        # Sort by efficiency (highest first)
        efficiencies.sort(key=lambda e: e.cost_efficiency, reverse=True)

        return efficiencies


class CostOptimizer:
    """
    Implements cost optimization strategies.

    Features:
    - Cache optimization
    - Model downgrade recommendations
    - Budget enforcement
    - Usage alerts
    """

    def __init__(self):
        """Initialize the cost optimizer."""
        self._cache_hit_rate_threshold = 0.3  # Cache hit rate threshold
        self._cost_threshold = 10.0  # Daily cost threshold for budget enforcement

    async def get_optimization_recommendations(
        self,
        user_id: Optional[int] = None,
        provider_ids: Optional[List[int]] = None,
        timeframe: str = "weekly",
    ) -> List[OptimizationRecommendation]:
        """
        Generate cost optimization recommendations.

        Args:
            user_id: Optional user ID
            provider_ids: List of provider IDs to consider
            timeframe: Time period for analysis

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Analyze model efficiency
        analyzer = CostAnalyzer()
        efficiencies = await analyzer.analyze_efficiency(days=7)

        if efficiencies:
            # Check for model downgrade opportunities
            if len(efficiencies) >= 2:
                # Compare most efficient with current usage
                most_efficient = efficiencies[0]
                least_efficient = efficiencies[-1]

                if most_efficient.cost_efficiency > least_efficient.cost_efficiency * 1.5:
                    potential_savings = (
                        least_efficient.total_cost - most_efficient.total_cost
                    ) / least_efficient.total_cost * 100

                    recommendations.append(OptimizationRecommendation(
                        strategy=OptimizationStrategy.MODEL_DOWNGRADE,
                        description=(
                            f"Switch from {least_efficient.model_id} to "
                            f"{most_efficient.model_id} for better cost efficiency"
                        ),
                        expected_savings=potential_savings,
                        implementation_difficulty="Low",
                        priority="Medium" if potential_savings > 20 else "Low",
                        estimated_effort_hours=2,
                    ))

        # Check for budget enforcement needs
        if user_id:
            user_analysis = await analyzer.analyze_by_user(user_id, days=7)
            daily_avg = user_analysis.total_cost / 7

            if daily_avg > self._cost_threshold:
                recommendations.append(OptimizationRecommendation(
                    strategy=OptimizationStrategy.BUDGET_ENFORCEMENT,
                    description=f"Daily cost (${daily_avg:.2f}) exceeds threshold (${self._cost_threshold:.2f})",
                    expected_savings=10.0,  # Estimate
                    implementation_difficulty="Medium",
                    priority="High",
                    estimated_effort_hours=4,
                ))

        # Check for cache optimization opportunities
        recommendations.append(OptimizationRecommendation(
            strategy=OptimizationStrategy.CACHE_FAVORING,
            description="Enable caching for repeated requests to reduce API calls",
            expected_savings=15.0,  # Estimate 15% savings
            implementation_difficulty="Low",
            priority="Low",
            estimated_effort_hours=8,
        ))

        # Sort by priority and potential savings
        recommendations.sort(
            key=lambda r: (
                r.priority == "High",
                r.expected_savings,
            ),
            reverse=True,
        )

        return recommendations


class BudgetManager:
    """
    Manages cost budgets and alerts.

    Features:
    - Budget setting and tracking
    - Utilization monitoring
    - Over-budget alerts
    - Forecasting
    """

    def __init__(self):
        """Initialize the budget manager."""
        self._budget_cache: Dict[int, Dict[str, float]] = {}

    async def set_budget(
        self,
        user_id: int,
        daily_budget: Optional[float] = None,
        monthly_budget: Optional[float] = None,
    ) -> None:
        """
        Set budget for a user.

        Args:
            user_id: User ID
            daily_budget: Daily budget amount
            monthly_budget: Monthly budget amount
        """
        budget_data = {}

        if daily_budget is not None:
            budget_data["daily"] = daily_budget
            budget_data["monthly"] = daily_budget * 30

        if monthly_budget is not None:
            budget_data["monthly"] = monthly_budget
            if daily_budget is None:
                budget_data["daily"] = monthly_budget / 30

        # Save to Redis
        redis_key = RedisKeys.budget_info(user_id)
        import json
        await RedisService.set(
            redis_key,
            json.dumps(budget_data),
            ttl=86400,  # 24 hours
        )

        self._budget_cache[user_id] = budget_data

    async def get_budget_status(
        self,
        user_id: int,
    ) -> BudgetInfo:
        """
        Get budget status for a user.

        Args:
            user_id: User ID

        Returns:
            BudgetInfo: Budget information
        """
        # Get budget from cache or database
        if user_id not in self._budget_cache:
            redis_key = RedisKeys.budget_info(user_id)
            cached = await RedisService.get(redis_key)

            if cached:
                import json
                self._budget_cache[user_id] = json.loads(cached)
            else:
                # No budget set
                self._budget_cache[user_id] = {}

        budget_data = self._budget_cache.get(user_id, {})

        # Get current spending
        analyzer = CostAnalyzer()
        user_analysis = await analyzer.analyze_by_user(user_id, days=7)

        daily_budget = budget_data.get("daily", 0)
        monthly_budget = budget_data.get("monthly", 0)
        spent = user_analysis.total_cost
        daily_average = user_analysis.total_cost / 7 if user_analysis.total_cost > 0 else 0

        # Calculate projected monthly
        projected_monthly = daily_average * 30

        remaining = max(0, monthly_budget - spent)
        utilization_rate = (
            (spent / monthly_budget * 100)
            if monthly_budget > 0 else 0
        )

        over_budget = spent > monthly_budget

        return BudgetInfo(
            total_budget=monthly_budget,
            spent=spent,
            remaining=remaining,
            utilization_rate=utilization_rate,
            daily_average=daily_average,
            projected_monthly=projected_monthly,
            over_budget=over_budget,
        )

    async def check_budget_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for budget alerts.

        Returns:
            List of alert dictionaries
        """
        alerts = []

        # Check all users with budgets
        for user_id in self._budget_cache:
            budget_info = await self.get_budget_status(user_id)

            # Over budget alert
            if budget_info.over_budget:
                alerts.append({
                    "type": "over_budget",
                    "severity": "critical",
                    "user_id": user_id,
                    "spent": budget_info.spent,
                    "budget": budget_info.total_budget,
                    "utilization_rate": budget_info.utilization_rate,
                })

            # High utilization alert
            elif budget_info.utilization_rate > 0.8:
                alerts.append({
                    "type": "high_utilization",
                    "severity": "warning",
                    "user_id": user_id,
                    "spent": budget_info.spent,
                    "budget": budget_info.total_budget,
                    "utilization_rate": budget_info.utilization_rate,
                })

            # Projected over budget
            elif budget_info.projected_monthly > budget_info.total_budget * 1.1:
                alerts.append({
                    "type": "projected_over_budget",
                    "severity": "info",
                    "user_id": user_id,
                    "projected": budget_info.projected_monthly,
                    "budget": budget_info.total_budget,
                    "overage": (
                        budget_info.projected_monthly - budget_info.total_budget
                    ),
                })

        return alerts


# Global instances
cost_analyzer = CostAnalyzer()
cost_optimizer = CostOptimizer()
budget_manager = BudgetManager()
