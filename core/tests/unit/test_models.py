"""
Unit tests for data models.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import Integer
from sqlalchemy.orm import mapped_column

from src.models.base import Base, TimestampMixin
from src.models.user import User, APIKey, UserRole, UserStatus
from src.models.provider import Provider, ProviderModel, ProviderType, ProviderStatus
from src.models.routing import RoutingRule, RoutingDecision, RoutingSwitchState
from src.models.cost import CostRecord


class TestTimestampMixin:
    """Test TimestampMixin."""

    @pytest.mark.unit
    def test_timestamp_mixin_creation(self):
        """Test that TimestampMixin adds timestamps."""
        class TestModel(Base, TimestampMixin):
            __tablename__ = "test"
            id = mapped_column(Integer, primary_key=True, autoincrement=True)

        model = TestModel()
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")

        # They should be None initially
        assert model.created_at is None
        assert model.updated_at is None


class TestUserRole:
    """Test UserRole enum."""

    @pytest.mark.unit
    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"


class TestUserStatus:
    """Test UserStatus enum."""

    @pytest.mark.unit
    def test_user_status_values(self):
        """Test UserStatus enum values."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.DELETED.value == "deleted"


class TestProviderType:
    """Test ProviderType enum."""

    @pytest.mark.unit
    def test_provider_type_values(self):
        """Test ProviderType enum values."""
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.CUSTOM.value == "custom"


class TestProviderStatus:
    """Test ProviderStatus enum."""

    @pytest.mark.unit
    def test_provider_status_values(self):
        """Test ProviderStatus enum values."""
        assert ProviderStatus.ACTIVE.value == "active"
        assert ProviderStatus.INACTIVE.value == "inactive"
        assert ProviderStatus.UNHEALTHY.value == "unhealthy"


class TestUser:
    """Test User model."""

    @pytest.mark.unit
    def test_user_creation(self, db_session):
        """Test creating a user."""
        user = User(
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER
        assert user.status == UserStatus.ACTIVE

    @pytest.mark.unit
    def test_user_with_default_values(self):
        """Test user with default values."""
        user = User(
            username="testuser",
            email="test@example.com",
        )
        assert user.role == UserRole.USER  # Default
        assert user.status == UserStatus.ACTIVE  # Default


class TestAPIKey:
    """Test APIKey model."""

    @pytest.mark.unit
    def test_api_key_creation(self):
        """Test creating an API key."""
        api_key = APIKey(
            user_id=1,
            key_hash="test-hash-123456",
            name="Test Key",
            is_active=True,
        )
        assert api_key.user_id == 1
        assert api_key.key_hash == "test-hash-123456"
        assert api_key.name == "Test Key"
        assert api_key.is_active is True
        assert api_key.request_count == 0  # Default

    @pytest.mark.unit
    def test_api_key_with_expires_at(self):
        """Test API key with expiration."""
        future_time = datetime.now(timezone.utc) + timedelta(days=30)
        api_key = APIKey(
            user_id=1,
            key_hash="test-hash-123456",
            name="Test Key",
            is_active=True,
            expires_at=future_time,
        )
        assert api_key.expires_at == future_time


class TestProvider:
    """Test Provider model."""

    @pytest.mark.unit
    def test_provider_creation(self):
        """Test creating a provider."""
        from src.utils.encryption import EncryptionManager

        provider = Provider(
            name="test-provider",
            provider_type=ProviderType.OPENAI,
            api_key_encrypted=EncryptionManager.encrypt("test-key"),
            base_url="https://api.openai.com/v1",
            timeout=60,
            max_retries=3,
            status=ProviderStatus.ACTIVE,
            priority=100,
            weight=100,
        )
        assert provider.name == "test-provider"
        assert provider.provider_type == ProviderType.OPENAI
        assert provider.timeout == 60
        assert provider.priority == 100
        assert provider.weight == 100

    @pytest.mark.unit
    def test_provider_with_region(self):
        """Test provider with region."""
        from src.utils.encryption import EncryptionManager

        provider = Provider(
            name="test-provider",
            provider_type=ProviderType.OPENAI,
            api_key_encrypted=EncryptionManager.encrypt("test-key"),
            base_url="https://api.openai.com/v1",
            region="us-east-1",
        )
        assert provider.region == "us-east-1"


class TestProviderModel:
    """Test ProviderModel model."""

    @pytest.mark.unit
    def test_provider_model_creation(self):
        """Test creating a provider model."""
        model = ProviderModel(
            provider_id=1,
            model_id="gpt-4",
            name="GPT-4",
            context_window=8192,
            input_price_per_1k=Decimal("0.03"),
            output_price_per_1k=Decimal("0.06"),
            is_active=True,
        )
        assert model.provider_id == 1
        assert model.model_id == "gpt-4"
        assert model.name == "GPT-4"
        assert model.context_window == 8192
        assert model.input_price_per_1k == Decimal("0.03")
        assert model.output_price_per_1k == Decimal("0.06")
        assert model.is_active is True


class TestRoutingRule:
    """Test RoutingRule model."""

    @pytest.mark.unit
    def test_routing_rule_creation(self):
        """Test creating a routing rule."""
        rule = RoutingRule(
            name="Test Rule",
            description="A test routing rule",
            condition_type="regex",
            condition_value=r"code|python",
            min_complexity=0,
            max_complexity=1000,
            action_type="use_model",
            action_value="gpt-4",
            priority=10,
            is_active=True,
            hit_count=0,
        )
        assert rule.name == "Test Rule"
        assert rule.condition_type == "regex"
        assert rule.action_type == "use_model"
        assert rule.action_value == "gpt-4"
        assert rule.priority == 10
        assert rule.is_active is True
        assert rule.hit_count == 0


class TestRoutingDecision:
    """Test RoutingDecision model."""

    @pytest.mark.unit
    def test_routing_decision_creation(self):
        """Test creating a routing decision."""
        from decimal import Decimal
        from src.utils.encryption import hash_content

        decision = RoutingDecision(
            session_id="test-session-123",
            request_id="test-request-456",
            user_id=1,
            api_key_id=1,
            content_hash=hash_content("test content"),
            intent="test_intent",
            complexity_score=0.5,
            provider_id=1,
            model_id="gpt-3.5-turbo",
            routing_rule_id=1,
            routing_method="rule_based",
            success=True,
            latency_ms=100,
            input_tokens=10,
            output_tokens=20,
            cost=Decimal("0.0015"),
        )
        assert decision.session_id == "test-session-123"
        assert decision.request_id == "test-request-456"
        assert decision.success is True
        assert decision.latency_ms == 100
        assert decision.input_tokens == 10
        assert decision.output_tokens == 20
        assert decision.cost == Decimal("0.0015")


class TestRoutingSwitchState:
    """Test RoutingSwitchState model."""

    @pytest.mark.unit
    def test_routing_switch_state_creation(self):
        """Test creating a routing switch state."""
        state = RoutingSwitchState(
            enabled=True,
            pending_switch=False,
            pending_value=False,
            scheduled_at=None,
            cooldown_until=None,
        )
        assert state.enabled is True
        assert state.pending_switch is False
        assert state.pending_value is False
        assert state.scheduled_at is None
        assert state.cooldown_until is None


class TestCostRecord:
    """Test CostRecord model."""

    @pytest.mark.unit
    def test_cost_record_creation(self):
        """Test creating a cost record."""
        from src.utils.encryption import hash_content
        from decimal import Decimal

        record = CostRecord(
            session_id="test-session-123",
            request_id="test-request-456",
            user_id=1,
            api_key_id=1,
            provider_id=1,
            model_id="gpt-3.5-turbo",
            provider_type="openai",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            input_cost=Decimal("0.0005"),
            output_cost=Decimal("0.0015"),
            total_cost=Decimal("0.0020"),
            extra_data={"test": "data"},
        )
        assert record.session_id == "test-session-123"
        assert record.provider_id == 1
        assert record.model_id == "gpt-3.5-turbo"
        assert record.input_tokens == 10
        assert record.output_tokens == 20
        assert record.total_tokens == 30
        assert record.input_cost == Decimal("0.0005")
        assert record.output_cost == Decimal("0.0015")
        assert record.total_cost == Decimal("0.0020")
        assert record.extra_data == {"test": "data"}
