"""
Advanced Monitoring and Analytics - Real-time monitoring and intelligent analysis.

This module provides:
- Real-time metrics collection and aggregation
- Performance monitoring (latency, throughput, error rates)
- System health monitoring
- Alerting system with configurable thresholds
- Dashboard metrics aggregation
- Historical data analysis
- Anomaly detection
- Custom metrics support
"""
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from statistics import mean, median, stdev
from decimal import Decimal

from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.routing import RoutingDecision
from src.models.provider import Provider, ProviderModel
from src.models.cost import CostRecord
from src.models.user import User
from src.db.session import SessionManager
from src.config.redis_config import RedisKeys
from src.services.redis_client import RedisService


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"  # Monotonically increasing value
    GAUGE = "gauge"  # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Count and sum of observations


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class MetricData:
    """Individual metric data point."""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class Alert:
    """Alert notification."""
    id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    current_value: float
    threshold: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Health check result."""
    service: str
    status: HealthStatus
    message: str
    response_time_ms: float
    last_check: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """Aggregated system metrics."""
    timestamp: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float
    active_connections: int
    total_cost: float
    cache_hit_rate: float


@dataclass
class AnomalyDetectionResult:
    """Anomaly detection result."""
    detected: bool
    metric_name: str
    current_value: float
    expected_range: Tuple[float, float]
    deviation_score: float  # 0-1, higher = more anomalous
    confidence: float
    timestamp: datetime


class MetricsCollector:
    """
    Collects and aggregates metrics in real-time.

    Features:
    - In-memory buffer for recent metrics
    - Time-window aggregation
    - Label-based grouping
    """

    def __init__(self, buffer_size: int = 10000):
        """Initialize metrics collector."""
        self._buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=buffer_size))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def record_metric(self, metric: MetricData) -> None:
        """
        Record a metric data point.

        Args:
            metric: Metric data to record
        """
        async with self._lock:
            if metric.metric_type == MetricType.COUNTER:
                self._counters[metric.name] += metric.value
            elif metric.metric_type == MetricType.GAUGE:
                self._gauges[metric.name] = metric.value
            elif metric.metric_type == MetricType.HISTOGRAM:
                self._histograms[metric.name].append(metric.value)

            # Store in buffer with timestamp
            key = self._make_key(metric.name, metric.labels)
            self._buffer[key].append({
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat(),
                "labels": metric.labels,
            })

    async def get_metric(
        self,
        name: str,
        metric_type: MetricType,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """
        Get current metric value.

        Args:
            name: Metric name
            metric_type: Type of metric
            labels: Optional labels for filtering

        Returns:
            Current metric value or None
        """
        async with self._lock:
            if metric_type == MetricType.COUNTER:
                return self._counters.get(name, 0.0)
            elif metric_type == MetricType.GAUGE:
                return self._gauges.get(name)
            elif metric_type == MetricType.HISTOGRAM:
                values = self._histograms.get(name, [])
                if values:
                    return mean(values)
                return None

        return None

    async def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """
        Get histogram statistics (percentiles).

        Args:
            name: Histogram name
            labels: Optional labels for filtering

        Returns:
            Dict with count, sum, min, max, avg, p50, p95, p99
        """
        async with self._lock:
            values = self._histograms.get(name, [])

            if not values:
                return {}

            sorted_values = sorted(values)
            count = len(sorted_values)

            return {
                "count": count,
                "sum": sum(sorted_values),
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "avg": mean(sorted_values),
                "p50": sorted_values[int(count * 0.5)],
                "p95": sorted_values[int(count * 0.95)] if count >= 20 else sorted_values[-1],
                "p99": sorted_values[int(count * 0.99)] if count >= 100 else sorted_values[-1],
            }

    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key from name and labels."""
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}@{label_str}"

    async def reset(self) -> None:
        """Reset all metrics (use with caution)."""
        async with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._buffer.clear()


class AlertManager:
    """
    Manages alerting rules and notifications.

    Features:
    - Configurable thresholds
    - Multiple alert conditions
    - Alert deduplication
    - Alert history tracking
    """

    def __init__(self):
        """Initialize alert manager."""
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []

    async def add_rule(
        self,
        rule_id: str,
        metric_name: str,
        condition: str,  # "gt", "lt", "eq", "gte", "lte"
        threshold: float,
        severity: AlertSeverity,
        window_seconds: int = 60,
    ) -> None:
        """
        Add an alert rule.

        Args:
            rule_id: Unique rule identifier
            metric_name: Metric to monitor
            condition: Comparison condition
            threshold: Threshold value
            severity: Alert severity
            window_seconds: Time window for evaluation
        """
        self._rules[rule_id] = {
            "metric_name": metric_name,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "window_seconds": window_seconds,
            "created_at": datetime.now(timezone.utc),
        }

    async def remove_rule(self, rule_id: str) -> bool:
        """
        Remove an alert rule.

        Args:
            rule_id: Rule to remove

        Returns:
            True if rule was removed
        """
        return self._rules.pop(rule_id, None) is not None

    async def evaluate_rule(
        self,
        rule_id: str,
        current_value: float,
    ) -> Optional[Alert]:
        """
        Evaluate an alert rule.

        Args:
            rule_id: Rule to evaluate
            current_value: Current metric value

        Returns:
            Alert if triggered, None otherwise
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return None

        triggered = False

        condition = rule["condition"]
        threshold = rule["threshold"]

        if condition == "gt" and current_value > threshold:
            triggered = True
        elif condition == "lt" and current_value < threshold:
            triggered = True
        elif condition == "eq" and current_value == threshold:
            triggered = True
        elif condition == "gte" and current_value >= threshold:
            triggered = True
        elif condition == "lte" and current_value <= threshold:
            triggered = True

        if triggered:
            alert = Alert(
                id=f"{rule_id}_{int(time.time())}",
                severity=rule["severity"],
                title=f"Alert: {rule['metric_name']}",
                description=(
                    f"{rule['metric_name']} is {current_value:.2f}, "
                    f"threshold is {threshold:.2f}"
                ),
                metric_name=rule["metric_name"],
                current_value=current_value,
                threshold=threshold,
                triggered_at=datetime.now(timezone.utc),
            )

            self._active_alerts[rule_id] = alert
            self._alert_history.append(alert)

            return alert

        # Check if alert should be resolved
        if rule_id in self._active_alerts:
            existing_alert = self._active_alerts[rule_id]
            existing_alert.resolved_at = datetime.now(timezone.utc)
            del self._active_alerts[rule_id]

        return None

    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())

    async def get_alert_history(
        self,
        limit: int = 100,
    ) -> List[Alert]:
        """Get alert history."""
        return self._alert_history[-limit:]


class HealthMonitor:
    """
    Monitors system health and component status.

    Features:
    - Component health checks
    - Dependency health tracking
    - Health status aggregation
    """

    def __init__(self):
        """Initialize health monitor."""
        self._checks: Dict[str, Callable] = {}
        self._results: Dict[str, HealthCheckResult] = {}
        self._last_update: Optional[datetime] = None

    def register_check(
        self,
        service: str,
        check_func: Callable[[], HealthCheckResult],
    ) -> None:
        """
        Register a health check function.

        Args:
            service: Service name
            check_func: Health check function
        """
        self._checks[service] = check_func

    async def check_service(self, service: str) -> HealthCheckResult:
        """
        Check health of a specific service.

        Args:
            service: Service name

        Returns:
            Health check result
        """
        check_func = self._checks.get(service)

        if not check_func:
            return HealthCheckResult(
                service=service,
                status=HealthStatus.UNKNOWN,
                message="No health check registered",
                response_time_ms=0,
                last_check=datetime.now(timezone.utc),
            )

        try:
            result = check_func()
            self._results[service] = result
            self._last_update = datetime.now(timezone.utc)
            return result
        except Exception as e:
            return HealthCheckResult(
                service=service,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=0,
                last_check=datetime.now(timezone.utc),
            )

    async def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all registered services.

        Returns:
            Dict of service name to health check result
        """
        results = {}

        for service in self._checks:
            results[service] = await self.check_service(service)

        return results

    async def get_system_health(self) -> HealthStatus:
        """
        Get overall system health status.

        Returns:
            Overall health status
        """
        if not self._results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in self._results.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN


class AnomalyDetector:
    """
    Detects anomalies in metrics using statistical analysis.

    Features:
    - Statistical outlier detection
    - Trend analysis
    - Seasonal pattern detection
    """

    def __init__(self, window_size: int = 100):
        """Initialize anomaly detector."""
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._threshold_std: float = 2.5  # Standard deviations threshold

    async def analyze(
        self,
        metric_name: str,
        value: float,
    ) -> AnomalyDetectionResult:
        """
        Analyze a metric value for anomalies.

        Args:
            metric_name: Name of metric
            value: Current value

        Returns:
            Anomaly detection result
        """
        history = self._history[metric_name]

        # Add current value to history
        history.append(value)

        # Need enough data points for analysis
        if len(history) < 10:
            return AnomalyDetectionResult(
                detected=False,
                metric_name=metric_name,
                current_value=value,
                expected_range=(value, value),
                deviation_score=0.0,
                confidence=0.0,
                timestamp=datetime.now(timezone.utc),
            )

        # Calculate statistics
        values_list = list(history)
        avg = mean(values_list)
        try:
            std = stdev(values_list)
        except:
            std = 0.0

        # Calculate z-score
        if std > 0:
            z_score = abs((value - avg) / std)
        else:
            z_score = 0.0

        # Determine if anomaly
        is_anomaly = z_score > self._threshold_std

        # Calculate expected range (±2 standard deviations)
        expected_min = avg - (2 * std)
        expected_max = avg + (2 * std)

        # Calculate deviation score (0-1)
        deviation_score = min(z_score / self._threshold_std, 1.0)

        # Confidence increases with more data points
        confidence = min(len(history) / 50, 1.0)

        return AnomalyDetectionResult(
            detected=is_anomaly,
            metric_name=metric_name,
            current_value=value,
            expected_range=(expected_min, expected_max),
            deviation_score=deviation_score,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
        )


class MetricsAggregator:
    """
    Aggregates metrics for dashboard and analytics.

    Features:
    - Time-series aggregation
    - Multi-dimensional grouping
    - Pre-computed rollups
    """

    async def aggregate_system_metrics(
        self,
        window_seconds: int = 60,
    ) -> SystemMetrics:
        """
        Aggregate system metrics for a time window.

        Args:
            window_seconds: Time window in seconds

        Returns:
            Aggregated system metrics
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(seconds=window_seconds)

        # Query routing decisions from database
        from src.models.routing import RoutingDecision

        result = await SessionManager.execute_select(
            select(
                func.count(RoutingDecision.id).label("total"),
                func.sum(RoutingDecision.success).label("successful"),
                func.avg(RoutingDecision.latency_ms).label("avg_latency"),
                func.sum(RoutingDecision.cost).label("total_cost"),
            )
            .where(RoutingDecision.created_at >= start_time)
        )

        if not result or not result[0][0]:
            # No data in window
            return SystemMetrics(
                timestamp=end_time,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                requests_per_second=0.0,
                active_connections=0,
                total_cost=0.0,
                cache_hit_rate=0.0,
            )

        row = result[0]
        total_requests = row.total or 0
        successful_requests = int(row.successful or 0)
        failed_requests = total_requests - successful_requests

        success_rate = (
            (successful_requests / total_requests * 100)
            if total_requests > 0 else 0
        )

        avg_latency = float(row.avg_latency or 0)

        # Get percentiles
        percentiles = await self._get_latency_percentiles(start_time, end_time)

        # Calculate requests per second
        requests_per_second = total_requests / window_seconds if window_seconds > 0 else 0

        # Get active connections from Redis
        active_connections = await RedisService.get("system:active_connections") or 0

        return SystemMetrics(
            timestamp=end_time,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            p50_latency_ms=percentiles.get("p50", 0),
            p95_latency_ms=percentiles.get("p95", 0),
            p99_latency_ms=percentiles.get("p99", 0),
            requests_per_second=requests_per_second,
            active_connections=int(active_connections),
            total_cost=float(row.total_cost or 0),
            cache_hit_rate=0.0,  # TODO: Implement cache hit tracking
        )

    async def _get_latency_percentiles(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, float]:
        """Get latency percentiles for time window."""
        from src.models.routing import RoutingDecision

        # Get all latencies in window
        result = await SessionManager.execute_select(
            select(RoutingDecision.latency_ms)
            .where(
                and_(
                    RoutingDecision.created_at >= start_time,
                    RoutingDecision.created_at <= end_time,
                )
            )
            .order_by(RoutingDecision.latency_ms)
        )

        if not result:
            return {"p50": 0, "p95": 0, "p99": 0}

        latencies = [row.latency_ms for row in result if row.latency_ms is not None]

        if not latencies:
            return {"p50": 0, "p95": 0, "p99": 0}

        count = len(latencies)
        return {
            "p50": latencies[int(count * 0.5)],
            "p95": latencies[int(count * 0.95)] if count >= 20 else latencies[-1],
            "p99": latencies[int(count * 0.99)] if count >= 100 else latencies[-1],
        }

    async def get_metrics_summary(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get metrics summary for dashboard.

        Args:
            hours: Number of hours to summarize

        Returns:
            Metrics summary dict
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        from src.models.routing import RoutingDecision

        # Query metrics
        result = await SessionManager.execute_select(
            select(
                func.count(RoutingDecision.id).label("total"),
                func.sum(RoutingDecision.success).label("successful"),
                func.avg(RoutingDecision.latency_ms).label("avg_latency"),
                func.sum(RoutingDecision.cost).label("total_cost"),
                func.count(func.distinct(RoutingDecision.user_id)).label("unique_users"),
            )
            .where(RoutingDecision.created_at >= start_time)
        )

        if not result or not result[0][0]:
            return {
                "total_requests": 0,
                "success_rate": 0,
                "avg_latency_ms": 0,
                "total_cost": 0,
                "unique_users": 0,
            }

        row = result[0]
        total = row.total or 0
        successful = int(row.successful or 0)

        return {
            "total_requests": total,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_latency_ms": float(row.avg_latency or 0),
            "total_cost": float(row.total_cost or 0),
            "unique_users": row.unique_users or 0,
        }


class MonitoringEngine:
    """
    Main monitoring engine coordinating all monitoring features.

    Features:
    - Real-time metrics collection
    - Alert management
    - Health monitoring
    - Anomaly detection
    - Metrics aggregation
    """

    def __init__(self):
        """Initialize the monitoring engine."""
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.health_monitor = HealthMonitor()
        self.anomaly_detector = AnomalyDetector()
        self.metrics_aggregator = MetricsAggregator()

        # Setup default alert rules
        self._setup_default_alerts()

    def _setup_default_alerts(self):
        """Setup default alerting rules."""
        # These will be configured via admin API
        asyncio.create_task(self._initialize_rules())

    async def _initialize_rules(self):
        """Initialize alert rules."""
        # Example: High error rate alert
        await self.alert_manager.add_rule(
            rule_id="high_error_rate",
            metric_name="error_rate",
            condition="gt",
            threshold=5.0,  # 5%
            severity=AlertSeverity.ERROR,
            window_seconds=60,
        )

        # Example: High latency alert
        await self.alert_manager.add_rule(
            rule_id="high_latency",
            metric_name="latency_ms_p95",
            condition="gt",
            threshold=2000.0,  # 2 seconds
            severity=AlertSeverity.WARNING,
            window_seconds=60,
        )

    async def record_request(
        self,
        success: bool,
        latency_ms: float,
        cost: float,
        user_id: int,
        provider_id: int,
        model_id: str,
    ) -> None:
        """
        Record a request metric.

        Args:
            success: Whether request was successful
            latency_ms: Request latency in milliseconds
            cost: Request cost
            user_id: User ID
            provider_id: Provider ID
            model_id: Model ID
        """
        timestamp = datetime.now(timezone.utc)

        # Record counter metrics
        await self.metrics_collector.record_metric(MetricData(
            name="requests_total",
            value=1,
            timestamp=timestamp,
            metric_type=MetricType.COUNTER,
            labels={"user_id": str(user_id), "provider_id": str(provider_id)},
        ))

        if success:
            await self.metrics_collector.record_metric(MetricData(
                name="requests_successful",
                value=1,
                timestamp=timestamp,
                metric_type=MetricType.COUNTER,
            ))
        else:
            await self.metrics_collector.record_metric(MetricData(
                name="requests_failed",
                value=1,
                timestamp=timestamp,
                metric_type=MetricType.COUNTER,
            ))

        # Record latency histogram
        await self.metrics_collector.record_metric(MetricData(
            name="latency_ms",
            value=latency_ms,
            timestamp=timestamp,
            metric_type=MetricType.HISTOGRAM,
            labels={"model_id": model_id},
        ))

        # Record cost
        await self.metrics_collector.record_metric(MetricData(
            name="cost_total",
            value=cost,
            timestamp=timestamp,
            metric_type=MetricType.COUNTER,
        ))

        # Check for anomalies
        latency_anomaly = await self.anomaly_detector.analyze("latency_ms", latency_ms)
        if latency_anomaly.detected:
            # Trigger alert for anomalous latency
            alert = Alert(
                id=f"latency_anomaly_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                title="Anomalous Latency Detected",
                description=f"Latency {latency_ms:.2f}ms is outside normal range",
                metric_name="latency_ms",
                current_value=latency_ms,
                threshold=latency_anomaly.expected_range[1],
                triggered_at=timestamp,
            )
            self.alert_manager._alert_history.append(alert)

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for dashboard.

        Returns:
            Dict with dashboard metrics
        """
        # Get system metrics for last minute
        system_metrics = await self.metrics_aggregator.aggregate_system_metrics(window_seconds=60)

        # Get summary for last 24 hours
        summary = await self.metrics_aggregator.get_metrics_summary(hours=24)

        # Get active alerts
        active_alerts = await self.alert_manager.get_active_alerts()

        # Get health status
        health_status = await self.health_monitor.get_system_health()

        return {
            "system_metrics": {
                "total_requests": system_metrics.total_requests,
                "success_rate": system_metrics.success_rate,
                "avg_latency_ms": system_metrics.avg_latency_ms,
                "p95_latency_ms": system_metrics.p95_latency_ms,
                "requests_per_second": system_metrics.requests_per_second,
                "active_connections": system_metrics.active_connections,
            },
            "summary": summary,
            "active_alerts_count": len(active_alerts),
            "health_status": health_status.value,
        }


# Global instances
metrics_collector = MetricsCollector()
alert_manager = AlertManager()
health_monitor = HealthMonitor()
anomaly_detector = AnomalyDetector()
metrics_aggregator = MetricsAggregator()
monitoring_engine = MonitoringEngine()
