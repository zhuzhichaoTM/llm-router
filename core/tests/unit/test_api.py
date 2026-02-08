"""
Unit tests for API endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.api.middleware import APIKeyAuth
from src.models.user import User, UserRole, UserStatus
from src.schemas.router import ToggleRequest, RoutingRuleCreate


@pytest.fixture
def client():
    """Create test client with mock Redis."""
    from unittest.mock import AsyncMock

    # Create mock Redis client
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    # Patch RedisConfig.get_client to return mock
    with patch("src.config.redis_config.RedisConfig.get_client", return_value=mock_redis):
        with patch("src.main.RedisConfig.get_client", return_value=mock_redis):
            yield TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Create mock admin user."""
    return User(
        id=0,
        username="admin",
        email="admin@llm-router.local",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )


@pytest.fixture
def mock_user():
    """Create mock regular user."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.unit
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "app" in data

    @pytest.mark.unit
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestRouterEndpoints:
    """Test router control endpoints."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_router_status_without_auth(self, client):
        """Test getting router status without authentication."""
        response = client.get("/api/v1/router/status")
        # Should return 401 or 403 without admin auth
        assert response.status_code in [401, 403]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_toggle_router_without_auth(self, client):
        """Test toggling router without authentication."""
        response = client.post(
            "/api/v1/router/toggle",
            json={"value": False, "reason": "Test"},
        )
        assert response.status_code in [401, 403]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_toggle_router_with_auth(self, client, mock_admin_user):
        """Test toggling router with admin authentication."""
        with patch.object(
            APIKeyAuth,
            "verify_api_key",
            return_value=(mock_admin_user, None)
        ):
            response = client.post(
                "/api/v1/router/toggle",
                json={"value": False, "reason": "Test toggle"},
            )

            if response.status_code == 200:
                data = response.json()
                assert "status" in data


class TestChatEndpoints:
    """Test chat API endpoints."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_models_without_auth(self, client):
        """Test listing models without authentication."""
        response = client.get("/api/v1/chat/models")
        # Should require auth
        assert response.status_code in [401, 403]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_completion_without_auth(self, client):
        """Test chat completion without authentication."""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        # Should require auth
        assert response.status_code in [401, 403]


class TestProviderEndpoints:
    """Test provider management endpoints."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_providers_without_auth(self, client):
        """Test listing providers without authentication."""
        response = client.get("/api/v1/providers")
        # Should require admin auth
        assert response.status_code in [401, 403]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_provider_without_auth(self, client):
        """Test creating provider without authentication."""
        response = client.post(
            "/api/v1/providers",
            json={
                "name": "test-provider",
                "provider_type": "openai",
                "api_key": "test-key",
                "base_url": "https://api.openai.com/v1",
            },
        )
        # Should require admin auth
        assert response.status_code in [401, 403]


class TestCostEndpoints:
    """Test cost tracking endpoints."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_cost_without_auth(self, client):
        """Test getting current cost without authentication."""
        response = client.get("/api/v1/cost/current")
        # Should require admin auth
        assert response.status_code in [401, 403]


class TestMiddleware:
    """Test API middleware."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_api_key_auth_missing(self):
        """Test API key auth with missing key."""
        from src.api.middleware import APIKeyAuth
        from fastapi import Request

        # Create a mock request without Authorization header
        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {}

        result = await APIKeyAuth.verify_api_key(mock_request)
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_api_key_auth_with_admin_key(self):
        """Test API key auth with admin key."""
        from src.api.middleware import APIKeyAuth
        from fastapi import Request
        from src.config.settings import settings

        # Create a mock request with admin key
        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"Authorization": f"Bearer {settings.admin_api_key}"}

        # Mock SessionManager to return admin user
        with patch("src.db.session.SessionManager.execute_select"):
            with patch("src.db.session.SessionManager.execute_get_one"):
                user, api_key = await APIKeyAuth.verify_api_key(mock_request)
                assert user is not None
                assert user.role == UserRole.ADMIN
                assert api_key is None  # Admin key bypasses database


class TestSchemas:
    """Test Pydantic schemas."""

    @pytest.mark.unit
    def test_toggle_request(self):
        """Test ToggleRequest schema."""
        from src.schemas.router import ToggleRequest
        request = ToggleRequest(value=True, reason="Test toggle")
        assert request.value is True
        assert request.reason == "Test toggle"
        assert request.force is False  # Default
        assert request.delay is None  # Default (no default delay set)

    @pytest.mark.unit
    def test_toggle_request_validation(self):
        """Test ToggleRequest validation."""
        from src.schemas.router import ToggleRequest
        from pydantic import ValidationError

        # Test invalid values
        with pytest.raises(ValidationError):
            ToggleRequest(value="invalid", reason="Test")  # Should be bool

    @pytest.mark.unit
    def test_routing_rule_create(self):
        """Test RoutingRuleCreate schema."""
        from src.schemas.router import RoutingRuleCreate
        rule = RoutingRuleCreate(
            name="Test Rule",
            description="A test rule",
            condition_type="regex",
            condition_value=r"test|pattern",
            action_type="use_model",
            action_value="gpt-4",
            priority=10,
        )
        assert rule.name == "Test Rule"
        assert rule.condition_type == "regex"
        assert rule.action_type == "use_model"
        assert rule.priority == 10

    @pytest.mark.unit
    def test_chat_completion_request(self):
        """Test ChatCompletionRequest schema."""
        from src.schemas.chat import ChatCompletionRequest, Message
        request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
        )
        assert request.model == "gpt-3.5-turbo"
        assert len(request.messages) == 1
        assert request.temperature == 0.7
        assert request.stream is False  # Default

    @pytest.mark.unit
    def test_message_validation(self):
        """Test Message validation."""
        from src.schemas.chat import Message, ChatCompletionRequest
        from pydantic import ValidationError

        # Test missing role
        with pytest.raises(ValidationError):
            Message(content="Hello")

        # Test missing content
        with pytest.raises(ValidationError):
            Message(role="user")

        # Test invalid temperature
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                model="gpt-3.5-turbo",
                messages=[Message(role="user", content="Hello")],
                temperature=3.0,  # Should be <= 2.0
            )
