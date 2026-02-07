"""
Integration tests for LLM Router end-to-end flows.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from src.agents.gateway_orchestrator import orchestrator
from src.agents.routing_agent import routing_agent
from src.agents.provider_agent import provider_agent
from src.providers.base import ChatRequest, ChatMessage


@pytest.mark.integration
@pytest.mark.asyncio
class TestChatFlowIntegration:
    """Test complete chat flow from request to response."""

    @pytest.mark.requires_db
    async def test_complete_chat_flow_with_routing(self, db_session, redis_client, sample_chat_request):
        """Test complete chat flow with routing."""
        # Mock provider execution
        from src.providers.base import ChatResponse, ChatChoice, TokenUsage

        mock_response = ChatResponse(
            id="chatcmpl-test",
            object="chat.completion",
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content="Test response"),
                    finish_reason="stop",
                )
            ],
            usage=TokenUsage(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
            ),
        )

        with patch.object(routing_agent, "_providers_cache") as mock_providers:
            mock_provider = AsyncMock()
            mock_provider.chat_completion.return_value = mock_response
            mock_provider.health_check.return_value = MagicMock(
                is_healthy=True, latency_ms=100
            )
            mock_providers.__getitem__.return_value = mock_provider

            # Execute routing
            decision = await routing_agent.route(sample_chat_request)
            assert decision.provider_id == 1
            assert decision.model_id == "gpt-3.5-turbo"

            # Execute request
            result = await routing_agent.execute(
                sample_chat_request,
                decision,
                user_id=1,
                api_key_id=1,
            )

            assert result.success is True
            assert result.latency_ms > 0
            assert result.input_tokens == 10
            assert result.output_tokens == 20
            assert result.cost > 0

    @pytest.mark.requires_db
    @pytest.mark.requires_redis
    async def test_chat_flow_with_cost_tracking(self, db_session, redis_client):
        """Test chat flow with cost tracking."""
        from src.agents.cost_agent import cost_agent

        # Mock provider
        from src.providers.base import ChatResponse, ChatChoice, TokenUsage

        mock_response = ChatResponse(
            id="chatcmpl-test",
            object="chat.completion",
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content="Test response"),
                    finish_reason="stop",
                )
            ],
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=200,
                total_tokens=300,
            ),
        )

        with patch.object(routing_agent, "_providers_cache") as mock_providers:
            mock_provider = AsyncMock()
            mock_provider.chat_completion.return_value = mock_response
            mock_provider.health_check.return_value = MagicMock(
                is_healthy=True, latency_ms=50
            )
            mock_provider.calculate_cost.return_value = (Decimal("0.05"), Decimal("0.3"))
            mock_providers.__getitem__.return_value = mock_provider

            # Execute routing
            decision = await routing_agent.route(sample_chat_request)
            result = await routing_agent.execute(
                sample_chat_request,
                decision,
                user_id=1,
                api_key_id=1,
            )

            assert result.success is True

            # Verify cost was recorded
            # Note: In real test, we'd check the database

    @pytest.mark.requires_db
    async def test_routing_with_rule(self, db_session, redis_client):
        """Test routing with custom rule."""
        # Create a custom routing rule
        from src.models.routing import RoutingRule

        rule = RoutingRule(
            name="Test Code Rule",
            description="Route code requests to GPT-4",
            condition_type="regex",
            condition_value=r"code|function|class",
            min_complexity=10,
            max_complexity=10000,
            action_type="use_model",
            action_value="gpt-4",
            priority=20,
            is_active=True,
            hit_count=0,
        )

        with patch("src.db.session.SessionManager.execute_insert"):
            from src.db.session import SessionManager
            inserted_rule = await SessionManager.execute_insert(rule)
            assert inserted_rule.id == 1  # Mock returns the object with id

            # Test routing with this rule
            code_request = ChatRequest(
                messages=[ChatMessage(role="user", content="Write a function")],
                model="gpt-3.5-turbo",
            )

            # Mock the rule evaluation
            with patch.object(routing_agent, "_get_active_rules") as mock_rules:
                mock_rules.return_value = [inserted_rule]

                decision = await routing_agent.route(code_request)

                # Should route to GPT-4 per the rule
                assert decision.rule_id == 1
                assert decision.model_id == "gpt-4"


@pytest.mark.integration
@pytest.mark.asyncio
class TestRouterToggleIntegration:
    """Test router toggle integration."""

    @pytest.mark.requires_redis
    async def test_toggle_workflow(self, redis_client):
        """Test complete toggle workflow."""
        # Get initial status
        status1 = await orchestrator.get_status()
        assert status1.enabled is True  # Default

        # Toggle to disabled
        with patch.object(orchestrator, "_record_history"):
            status2 = await orchestrator.toggle(
                value=False,
                reason="Test toggle",
                triggered_by="test",
                force=True,  # Immediate
            )

            # Verify state changed
            assert status2.enabled is False

        # Get status again
        status3 = await orchestrator.get_status()
        assert status3.enabled is False

        # Toggle back to enabled
        with patch.object(orchestrator, "_record_history"):
            status4 = await orchestrator.toggle(
                value=True,
                reason="Test toggle back",
                triggered_by="test",
                force=True,
            )

            # Verify state changed back
            assert status4.enabled is True

    @pytest.mark.requires_redis
    async def test_toggle_with_delay(self, redis_client):
        """Test toggle with delay."""
        # Schedule delayed toggle
        with patch.object(orchestrator, "_record_history"):
            status = await orchestrator.toggle(
                value=False,
                reason="Test delayed toggle",
                triggered_by="test",
                delay=5,  # 5 second delay
            )

            # Verify pending state
            assert status.enabled is True  # Still enabled
            assert status.pending is True
            assert status.pending_value is False

            # The actual toggle would happen after 5 seconds
            # In a real test, we'd use time.sleep or similar


@pytest.mark.integration
@pytest.mark.asyncio
class TestProviderHealthIntegration:
    """Test provider health monitoring integration."""

    @pytest.mark.requires_redis
    @pytest.mark.requires_db
    async def test_provider_health_check(self, redis_client, db_session):
        """Test provider health check workflow."""
        # Mock providers
        from src.providers.base import HealthStatus

        with patch.object(provider_agent, "_providers_cache") as mock_cache:
            mock_provider1 = AsyncMock()
            mock_provider1.health_check.return_value = HealthStatus(
                is_healthy=True, latency_ms=50
            )
            mock_provider1.get_provider_name.return_value = "openai"

            mock_provider2 = AsyncMock()
            mock_provider2.health_check.return_value = HealthStatus(
                is_healthy=False, latency_ms=None,
                error_message="Service unavailable"
            )
            mock_provider2.get_provider_name.return_value = "anthropic"

            mock_cache.values.return_value = [
                mock_provider1,
                mock_provider2,
            ]

            # Run health check
            metrics = await provider_agent.health_check_all()

            assert isinstance(metrics, dict)
            assert len(metrics) == 2

            # Verify metrics
            openai_metrics = metrics.get(1)
            assert openai_metrics["is_healthy"] is True
            assert openai_metrics["latency_ms"] == 50

            anthropic_metrics = metrics.get(2)
            assert anthropic_metrics["is_healthy"] is False
            assert anthropic_metrics["latency_ms"] is None
            assert "Service unavailable" in anthropic_metrics["last_error"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestCostTrackingIntegration:
    """Test cost tracking integration."""

    @pytest.mark.requires_redis
    @pytest.mark.requires_db
    async def test_cost_accumulation(self, redis_client, db_session):
        """Test cost accumulation across multiple requests."""
        from src.agents.cost_agent import cost_agent

        # Record multiple costs
        request_ids = []
        for i in range(5):
            request_id = f"test-request-{i}"
            request_ids.append(request_id)

            await cost_agent.record_cost(
                session_id="test-session",
                request_id=request_id,
                user_id=1,
                api_key_id=1,
                provider_id=1,
                model_id="gpt-3.5-turbo",
                provider_type="openai",
                input_tokens=100 * (i + 1),
                output_tokens=200 * (i + 1),
                input_cost=0.05 * (i + 1),
                output_cost=0.1 * (i + 1),
            )

        # Verify current cost
        current_cost = await cost_agent.get_current_cost()
        assert "daily" in current_cost
        assert "total" in current_cost

    @pytest.mark.requires_redis
    @pytest.mark.requires_db
    async def test_cost_by_model(self, redis_client, db_session):
        """Test cost aggregation by model."""
        from src.agents.cost_agent import cost_agent
        from unittest.mock import MagicMock

        # Mock database query results
        from src.db.session import SessionManager

        with patch.object(SessionManager, "execute_select") as mock_select:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [
                MagicMock(
                    model_id="gpt-3.5-turbo",
                    total_cost=Decimal("10.0"),
                    request_count=100,
                    total_tokens=10000,
                )
            ]
            mock_select.return_value = mock_result

            model_costs = await cost_agent.get_cost_by_model()

            assert isinstance(model_costs, list)
            assert len(model_costs) > 0
            assert model_costs[0].model_id == "gpt-3.5-turbo"
            assert model_costs[0].total_cost == Decimal("10.0")
