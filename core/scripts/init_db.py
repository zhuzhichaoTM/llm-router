"""
Database initialization script.

Creates initial data for the LLM Router application.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.db.base import Base, async_session_maker, engine
from src.models.user import User, APIKey, UserRole, UserStatus
from src.models.provider import Provider, ProviderModel, ProviderType, ProviderStatus
from src.models.routing import RoutingRule, RoutingSwitchState
from src.utils.encryption import EncryptionManager, generate_api_key


async def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")


async def seed_admin_user():
    """Create default admin user."""
    from sqlalchemy import select

    print("Creating admin user...")

    async with async_session_maker() as session:
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("Admin user already exists.")
            return existing

        # Create admin user
        admin = User(
            username="admin",
            email="admin@llm-router.local",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        await session.flush()

        # Create API key for admin
        api_key_str = generate_api_key(prefix="admin")
        from src.utils.encryption import hash_api_key
        api_key = APIKey(
            user_id=admin.id,
            key_hash=hash_api_key(api_key_str),
            name="Default Admin API Key",
            is_active=True,
        )
        session.add(api_key)
        await session.commit()

        print(f"Admin user created successfully.")
        print(f"Admin API Key: {api_key_str}")
        print(f"IMPORTANT: Save this API key securely!")

        return admin


async def seed_sample_providers():
    """Create sample providers (without API keys)."""
    from sqlalchemy import select
    from decimal import Decimal

    print("Creating sample providers...")

    async with async_session_maker() as session:
        # Check if providers already exist
        result = await session.execute(select(Provider))
        existing = result.scalars().first()

        if existing:
            print("Providers already exist.")
            return

        # Create sample OpenAI provider
        openai = Provider(
            name="openai",
            provider_type=ProviderType.OPENAI,
            api_key_encrypted=EncryptionManager.encrypt("your-openai-api-key-here"),
            base_url="https://api.openai.com/v1",
            timeout=60,
            max_retries=3,
            status=ProviderStatus.INACTIVE,  # Inactive until configured
            priority=100,
            weight=100,
        )
        session.add(openai)
        await session.flush()

        # Add sample models for OpenAI
        models = [
            {
                "model_id": "gpt-4",
                "name": "GPT-4",
                "context_window": 8192,
                "input_price": Decimal("0.03"),
                "output_price": Decimal("0.06"),
            },
            {
                "model_id": "gpt-4-turbo-preview",
                "name": "GPT-4 Turbo",
                "context_window": 128000,
                "input_price": Decimal("0.01"),
                "output_price": Decimal("0.03"),
            },
            {
                "model_id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "context_window": 4096,
                "input_price": Decimal("0.0005"),
                "output_price": Decimal("0.0015"),
            },
        ]

        for model_data in models:
            model = ProviderModel(
                provider_id=openai.id,
                model_id=model_data["model_id"],
                name=model_data["name"],
                context_window=model_data["context_window"],
                input_price_per_1k=model_data["input_price"],
                output_price_per_1k=model_data["output_price"],
                is_active=True,
            )
            session.add(model)

        # Create sample Anthropic provider
        anthropic = Provider(
            name="anthropic",
            provider_type=ProviderType.ANTHROPIC,
            api_key_encrypted=EncryptionManager.encrypt("your-anthropic-api-key-here"),
            base_url="https://api.anthropic.com",
            timeout=60,
            max_retries=3,
            status=ProviderStatus.INACTIVE,  # Inactive until configured
            priority=100,
            weight=100,
        )
        session.add(anthropic)
        await session.flush()

        # Add sample models for Anthropic
        anthropic_models = [
            {
                "model_id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "context_window": 200000,
                "input_price": Decimal("0.015"),
                "output_price": Decimal("0.075"),
            },
            {
                "model_id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "context_window": 200000,
                "input_price": Decimal("0.003"),
                "output_price": Decimal("0.015"),
            },
            {
                "model_id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "context_window": 200000,
                "input_price": Decimal("0.00025"),
                "output_price": Decimal("0.00125"),
            },
        ]

        for model_data in anthropic_models:
            model = ProviderModel(
                provider_id=anthropic.id,
                model_id=model_data["model_id"],
                name=model_data["name"],
                context_window=model_data["context_window"],
                input_price_per_1k=model_data["input_price"],
                output_price_per_1k=model_data["output_price"],
                is_active=True,
            )
            session.add(model)

        await session.commit()

        print("Sample providers created successfully.")
        print("NOTE: Providers are inactive. Configure your API keys to activate them.")


async def seed_initial_routing_rules():
    """Create initial routing rules."""
    from sqlalchemy import select

    print("Creating initial routing rules...")

    async with async_session_maker() as session:
        # Check if rules already exist
        result = await session.execute(select(RoutingRule))
        existing = result.scalars().first()

        if existing:
            print("Routing rules already exist.")
            return

        # Create sample rule: route code-related requests to GPT-4
        code_rule = RoutingRule(
            name="Code completion to GPT-4",
            description="Route code-related requests to GPT-4",
            condition_type="regex",
            condition_value=r"(?i)(code|function|class|def|import|python|javascript)",
            action_type="use_model",
            action_value="gpt-4",
            priority=10,
            is_active=False,  # Disabled by default
        )
        session.add(code_rule)

        # Create sample rule: route simple queries to GPT-3.5
        simple_rule = RoutingRule(
            name="Simple queries to GPT-3.5",
            description="Route simple queries to GPT-3.5 Turbo",
            condition_type="complexity",
            condition_value="low",
            min_complexity=0,
            max_complexity=100,
            action_type="use_model",
            action_value="gpt-3.5-turbo",
            priority=5,
            is_active=False,  # Disabled by default
        )
        session.add(simple_rule)

        await session.commit()

        print("Initial routing rules created successfully.")


async def seed_routing_switch_state():
    """Create routing switch state."""
    from sqlalchemy import select

    print("Creating routing switch state...")

    async with async_session_maker() as session:
        # Check if state already exists
        result = await session.execute(select(RoutingSwitchState))
        existing = result.scalars().first()

        if existing:
            print("Routing switch state already exists.")
            return

        # Create default state
        state = RoutingSwitchState(
            enabled=True,
            pending_switch=False,
            pending_value=False,
        )
        session.add(state)
        await session.commit()

        print("Routing switch state created successfully.")


async def main():
    """Main initialization function."""
    print(f"Initializing {settings.app_name} v{settings.app_version}...")
    print(f"Database: {settings.database_url}")
    print()

    try:
        # Create tables
        await create_tables()

        # Seed initial data
        await seed_admin_user()
        await seed_sample_providers()
        await seed_initial_routing_rules()
        await seed_routing_switch_state()

        print()
        print("=" * 50)
        print("Initialization completed successfully!")
        print("=" * 50)
        print()
        print("Next steps:")
        print("1. Update provider API keys in the database or API")
        print("2. Activate providers in the UI or API")
        print("3. Configure routing rules as needed")
        print()

    except Exception as e:
        print(f"ERROR: Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
