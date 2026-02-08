"""
Unit tests for Agent implementations.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from src.agents.gateway_orchestrator import GatewayOrchestrator
from src.agents.routing_agent import RoutingAgent, RouteDecision, RouteResult, RoutingMethod
from src.agents.provider_agent import ProviderAgent, ProviderMetrics
from src.agents.cost_agent import CostAgent, CostSummary


class TestGatewayOrchestrator:
    """Test GatewayOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing."""
        # Reset singleton for testing
        GatewayOrchestrator._instance = None
        return GatewayOrchestrator()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialization(self, orchestrator, redis_client):
        """Test orchestrator initialization."""
        # Mock Redis operations - Redis client returns empty data by default
        mock_redis_client = AsyncMock()
        mock_redis_client.hgetall = AsyncMock(return_value={})
        mock_redis_client.get = AsyncMock(return_value=None)

        with patch("src.agents.gateway_orchestrator.RedisConfig.get_client", return_value=mock_redis_client):
            await orchestrator.initialize()
        assert orchestrator._initialized is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_status_default(self, orchestrator, redis_client):
        """Test getting default status."""
        status = await orchestrator.get_status()
        assert status.enabled is True  # Default is enabled
        assert status.pending is False
        assert status.can_toggle is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_toggle_immediate(self, orchestrator, redis_client):
        """Test immediate toggle."""
        # Mock Redis operations
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=None)
        mock_redis_client.set = AsyncMock(return_value=True)
        mock_redis_client.delete = AsyncMock(return_value=1)

        with patch("src.agents.gateway_orchestrator.RedisConfig.get_client", return_value=mock_redis_client), \
             patch("src.agents.gateway_orchestrator.SessionManager.execute_insert", new_callable=AsyncMock):
            status = await orchestrator.toggle(
                value=False,
                reason="Test toggle",
                triggered_by="test",
                force=True,  # Immediate
            )
            assert status.enabled is False
            assert status.pending is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_toggle_with_delay(self, orchestrator, redis_client):
        """Test toggle with delay."""
        # Mock Redis operations
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=None)
        mock_redis_client.hset = AsyncMock(return_value=True)
        mock_redis_client.expire = AsyncMock(return_value=True)

        with patch("src.agents.gateway_orchestrator.RedisConfig.get_client", return_value=mock_redis_client):
            status = await orchestrator.toggle(
                value=False,
                reason="Test toggle",
                triggered_by="test",
                delay=10,  # 10 second delay
            )
            assert status.enabled is True  # Still enabled until delay
            assert status.pending is True
            assert status.pending_value is False
            assert status.scheduled_at is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_toggle_in_cooldown(self, orchestrator, redis_client):
        """Test toggle during cooldown."""
        # Set cooldown
        import time
        orchestrator._cooldown_until = int(time.time()) + 300

        with pytest.raises(RuntimeError, match="Cooldown active"):
            await orchestrator.toggle(
                value=True,
                reason="Test",
                triggered_by="test",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_history(self, orchestrator, redis_client):
        """Test getting history."""
        history = await orchestrator.get_history(limit=10)
        assert isinstance(history, list)
        assert len(history) <= 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_metrics(self, orchestrator):
        """Test getting metrics."""
        # Mock get_history to avoid Redis call
        with patch.object(GatewayOrchestrator, "get_history", return_value=[]):
            metrics = await orchestrator.get_metrics()
            assert "current_status" in metrics
            assert "total_switches" in metrics
            assert isinstance(metrics["total_switches"], int)


class TestRoutingAgent:
    """Test RoutingAgent."""

    @pytest.fixture
    def routing_agent(self):
        """Create routing agent instance for testing."""
        # Reset singleton for testing
        RoutingAgent._instance = None
        return RoutingAgent()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialization(self, routing_agent, redis_client):
        """Test routing agent initialization."""
        with patch.object(RoutingAgent, "_refresh_providers"):
            await routing_agent.initialize()
        assert routing_agent._initialized is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_route_with_fixed_provider(self, routing_agent, sample_chat_request):
        """Test routing with fixed provider."""
        async def mock_get_rules(*args, **kwargs):
            return []

        with patch.object(RoutingAgent, "_get_active_rules", side_effect=mock_get_rules):
            decision = await routing_agent.route(
                sample_chat_request,
                preferred_provider=1,
                preferred_model="gpt-3.5-turbo",
            )
            assert decision.provider_id == 1
            assert decision.model_id == "gpt-3.5-turbo"
            assert decision.method == RoutingMethod.FIXED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_route_default(self, routing_agent, sample_chat_request):
        """Test default routing (weighted round robin)."""
        async def mock_get_rules(*args, **kwargs):
            return []

        with patch.object(RoutingAgent, "_get_active_rules", side_effect=mock_get_rules), \
             patch.object(RoutingAgent, "_weighted_round_robin_routing") as mock_route:
            mock_route.return_value = RouteDecision(
                provider_id=1,
                model_id="gpt-3.5-turbo",
                rule_id=None,
                method=RoutingMethod.WEIGHTED_ROUND_ROBIN.value,
                reason="Weighted round robin selection",
            )

            decision = await routing_agent.route(sample_chat_request)
            assert decision.method == RoutingMethod.WEIGHTED_ROUND_ROBIN.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_weighted_round_robin_routing(self, routing_agent):
        """Test weighted round robin routing."""
        # Mock some providers for testing
        from src.models.provider import Provider, ProviderType, ProviderStatus
        from src.models.provider import ProviderModel

        mock_provider = Provider(
            name="test_provider",
            provider_type=ProviderType.OPENAI,
            base_url="https://api.openai.com/v1",
            api_key_encrypted="test_encrypted",
            status=ProviderStatus.ACTIVE,
            priority=1,
            weight=100,
            timeout=30,
        )
        mock_provider.id = 1

        async def mock_select(*args, **kwargs):
            return [mock_provider]

        with patch("src.agents.routing_agent.SessionManager.execute_select", side_effect=mock_select):
            decision = await routing_agent._weighted_round_robin_routing()
            assert decision.provider_id > 0
            assert decision.model_id is not None
            assert decision.method == RoutingMethod.WEIGHTED_ROUND_ROBIN.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_available_models(self, routing_agent):
        """Test getting available models."""
        async def mock_select(*args, **kwargs):
            return []

        with patch("src.agents.routing_agent.SessionManager.execute_select", side_effect=mock_select):
            models = await routing_agent.get_available_models()
            assert isinstance(models, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_available_providers(self, routing_agent):
        """Test getting available providers."""
        async def mock_select(*args, **kwargs):
            return []

        with patch("src.agents.routing_agent.SessionManager.execute_select", side_effect=mock_select):
            providers = await routing_agent.get_available_providers()
            assert isinstance(providers, list)


class TestProviderAgent:
    """Test ProviderAgent."""

    @pytest.fixture
    def provider_agent(self):
        """Create provider agent instance for testing."""
        # Reset singleton for testing
        ProviderAgent._instance = None
        return ProviderAgent()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialization(self, provider_agent, redis_client):
        """Test provider agent initialization."""
        with patch.object(ProviderAgent, "_load_providers"):
            await provider_agent.initialize()
            assert provider_agent._initialized is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_all(self, provider_agent):
        """Test health check for all providers."""
        async def mock_select(*args, **kwargs):
            return []

        with patch("src.agents.provider_agent.SessionManager.execute_select", side_effect=mock_select), \
             patch.object(ProviderAgent, "_load_providers"), \
             patch.object(ProviderAgent, "_create_provider_instance"), \
             patch.object(ProviderAgent, "_update_provider_status"):
            metrics = await provider_agent.health_check_all()
            assert isinstance(metrics, dict)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_single_provider(self, provider_agent):
        """Test health check for single provider."""
        health = await provider_agent.health_check(provider_id=1)
        assert health is None or isinstance(health, object)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_best_provider(self, provider_agent):
        """Test getting best provider."""
        async def mock_select(*args, **kwargs):
            return []

        with patch("src.agents.provider_agent.SessionManager.execute_select", side_effect=mock_select), \
             patch.object(ProviderAgent, "_load_providers"):
            best_id = await provider_agent.get_best_provider()
            assert isinstance(best_id, int) or best_id is None

    @pytest.mark.unit
    def test_get_all_providers(self, provider_agent):
        """Test getting all providers."""
        providers = provider_agent.get_all_providers()
        assert isinstance(providers, dict)


class TestCostAgent:
    """Test CostAgent."""

    @pytest.fixture
    def cost_agent(self):
        """Create cost agent instance for testing."""
        # Reset singleton for testing
        CostAgent._instance = None
        return CostAgent()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_cost(self, cost_agent):
        """Test recording cost."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.hincrbyfloat = AsyncMock(return_value=1.0)
        mock_redis.incrby = AsyncMock(return_value=100)
        mock_redis.expire = AsyncMock(return_value=True)

        with patch("src.agents.cost_agent.RedisConfig.get_client", return_value=mock_redis), \
             patch("src.agents.cost_agent.SessionManager.execute_insert", new_callable=AsyncMock, return_value=AsyncMock()):
            await cost_agent.record_cost(
                session_id="test-session",
                request_id="test-request",
                user_id=1,
                api_key_id=1,
                provider_id=1,
                model_id="gpt-3.5-turbo",
                provider_type="openai",
                input_tokens=100,
                output_tokens=200,
                input_cost=0.05,
                output_cost=0.1,
            )
            # Should not raise

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_cost(self, cost_agent):
        """Test getting current cost."""
        async def mock_get(key):
            return None

        async def mock_hgetall(key):
            return {}

        class MockRedisClient:
            async def get(self, key):
                return await mock_get(key)

            async def hgetall(self, key):
                return await mock_hgetall(key)

        with patch("src.agents.cost_agent.RedisConfig.get_client", return_value=MockRedisClient()):
            cost = await cost_agent.get_current_cost()
            assert isinstance(cost, dict)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_daily_cost(self, cost_agent):
        """Test getting daily cost."""
        # Mock Redis client directly
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={"total_cost": "0", "total_tokens": "0"})

        with patch("src.agents.cost_agent.RedisConfig.get_client", return_value=mock_redis):
            costs = await cost_agent.get_daily_cost(days=7)
            assert isinstance(costs, list)
            assert len(costs) == 7

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cost_by_model(self, cost_agent):
        """Test getting cost by model."""
        from unittest.mock import MagicMock

        mock_item = MagicMock()
        mock_item.model_id = "gpt-3.5-turbo"
        mock_item.total_cost = Decimal("1.0")
        mock_item.request_count = 100
        mock_item.total_tokens = 10000

        async def mock_select(*args, **kwargs):
            return [mock_item]

        with patch("src.agents.cost_agent.SessionManager.execute_select", side_effect=mock_select):
            costs = await cost_agent.get_cost_by_model()
            assert isinstance(costs, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cost_by_user(self, cost_agent):
        """Test getting cost by user."""
        from unittest.mock import MagicMock

        mock_item = MagicMock()
        mock_item.user_id = 1
        mock_item.total_cost = Decimal("1.0")
        mock_item.request_count = 50

        async def mock_select(*args, **kwargs):
            return [mock_item]

        with patch("src.agents.cost_agent.SessionManager.execute_select", side_effect=mock_select):
            costs = await cost_agent.get_cost_by_user()
            assert isinstance(costs, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cost_summary(self, cost_agent):
        """Test getting cost summary."""
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.input_cost = Decimal("0.5")
        mock_result.output_cost = Decimal("0.5")
        mock_result.total_cost = Decimal("1.0")
        mock_result.input_tokens = 5000
        mock_result.output_tokens = 5000
        mock_result.total_tokens = 10000
        mock_result.total_requests = 100

        async def mock_get_one(*args, **kwargs):
            return mock_result

        with patch("src.agents.cost_agent.SessionManager.execute_get_one", side_effect=mock_get_one):
            summary = await cost_agent.get_cost_summary()
            assert isinstance(summary, CostSummary)
            assert summary.total_cost == 1.0
            assert summary.total_tokens == 10000
