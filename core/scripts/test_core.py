"""
Core functionality test script - No external services required.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_settings():
    """Test settings."""
    print("Testing settings...")
    from src.config.settings import settings
    print(f"  App: {settings.app_name}")
    print(f"  Version: {settings.app_version}")
    print(f"  Environment: {settings.app_env}")
    print("  ✓ PASS")
    return True


async def test_encryption():
    """Test encryption utilities."""
    print("Testing encryption utilities...")
    from src.utils.encryption import EncryptionManager, hash_api_key, generate_api_key

    # Test encryption/decryption
    secret = "my-secret-key"
    encrypted = EncryptionManager.encrypt(secret)
    decrypted = EncryptionManager.decrypt(encrypted)

    if secret != decrypted:
        print("  ✗ FAIL: Encryption/decryption")
        return False
    print("  Encryption/decryption OK")

    # Test API key hashing
    api_key = "test-api-key"
    hash1 = hash_api_key(api_key)
    hash2 = hash_api_key(api_key)

    if hash1 != hash2 or len(hash1) != 64:
        print("  ✗ FAIL: API key hashing")
        return False
    print("  API key hashing OK")

    # Test API key generation
    new_key = generate_api_key()
    if not new_key.startswith("llm_"):
        print("  ✗ FAIL: API key generation")
        return False
    print(f"  API key generation OK ({new_key[:12]}...)")

    print("  ✓ PASS")
    return True


async def test_provider_factory():
    """Test provider factory."""
    print("Testing provider factory...")
    from src.providers.factory import ProviderFactory

    providers = ProviderFactory.list_providers()

    if "openai" not in providers or "anthropic" not in providers:
        print("  ✗ FAIL: Missing providers")
        return False

    print(f"  Registered: {', '.join(providers)}")
    print("  ✓ PASS")
    return True


async def test_provider_classes():
    """Test provider classes."""
    print("Testing provider classes...")
    from src.providers.openai import OpenAIProvider
    from src.providers.anthropic import AnthropicProvider

    # Test OpenAI provider creation
    try:
        openai = OpenAIProvider(api_key="test-key")
        if openai.get_provider_name() != "openai":
            print("  ✗ FAIL: OpenAI provider name")
            return False
        print("  OpenAI provider OK")
    except Exception as e:
        print(f"  ✗ FAIL: OpenAI provider: {e}")
        return False

    # Test Anthropic provider creation
    try:
        anthropic = AnthropicProvider(api_key="test-key")
        if anthropic.get_provider_name() != "anthropic":
            print("  ✗ FAIL: Anthropic provider name")
            return False
        print("  Anthropic provider OK")
    except Exception as e:
        print(f"  ✗ FAIL: Anthropic provider: {e}")
        return False

    print("  ✓ PASS")
    return True


async def test_schemas():
    """Test Pydantic schemas."""
    print("Testing schemas...")
    from src.schemas.chat import ChatCompletionRequest, Message, ChatCompletionResponse
    from src.schemas.router import SwitchStatusResponse, ToggleRequest
    from src.schemas.cost import DailyCost, CostSummary
    from src.schemas.provider import ProviderCreate, ModelInfo

    # Test chat request schema
    try:
        req = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[Message(role="user", content="Hello")]
        )
        print("  Chat request schema OK")
    except Exception as e:
        print(f"  ✗ FAIL: Chat request schema: {e}")
        return False

    # Test router schema
    try:
        status = SwitchStatusResponse(enabled=True, pending=False, can_toggle=True)
        print("  Router schema OK")
    except Exception as e:
        print(f"  ✗ FAIL: Router schema: {e}")
        return False

    # Test cost schema
    try:
        cost = DailyCost(date="2024-01-01", cost=0.01, tokens=1000)
        print("  Cost schema OK")
    except Exception as e:
        print(f"  ✗ FAIL: Cost schema: {e}")
        return False

    # Test provider schema
    try:
        provider = ProviderCreate(
            name="test",
            provider_type="openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1"
        )
        print("  Provider schema OK")
    except Exception as e:
        print(f"  ✗ FAIL: Provider schema: {e}")
        return False

    print("  ✓ PASS")
    return True


async def test_models():
    """Test database models."""
    print("Testing database models...")
    from src.models.user import User, APIKey, UserRole, UserStatus
    from src.models.provider import Provider, ProviderModel, ProviderType, ProviderStatus
    from src.models.routing import RoutingRule, RoutingDecision
    from src.models.cost import CostRecord, AuditLog

    # Test user model
    try:
        user = User(
            username="test",
            email="test@example.com",
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        print("  User model OK")
    except Exception as e:
        print(f"  ✗ FAIL: User model: {e}")
        return False

    # Test provider model
    try:
        provider = Provider(
            name="test",
            provider_type=ProviderType.OPENAI,
            api_key_encrypted="encrypted",
            base_url="https://api.openai.com/v1"
        )
        print("  Provider model OK")
    except Exception as e:
        print(f"  ✗ FAIL: Provider model: {e}")
        return False

    # Test routing model
    try:
        rule = RoutingRule(
            name="test-rule",
            condition_type="regex",
            condition_value="test",
            action_type="use_model",
            action_value="gpt-3.5-turbo"
        )
        print("  Routing model OK")
    except Exception as e:
        print(f"  ✗ FAIL: Routing model: {e}")
        return False

    # Test cost model
    try:
        cost = CostRecord(
            session_id="test",
            request_id="test",
            provider_id=1,
            model_id="gpt-3.5-turbo",
            provider_type="openai",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            input_cost=0.0005,
            output_cost=0.0015,
            total_cost=0.002,
            extra_data={}
        )
        print("  Cost model OK")
    except Exception as e:
        print(f"  ✗ FAIL: Cost model: {e}")
        return False

    print("  ✓ PASS")
    return True


async def test_agents():
    """Test agents initialization."""
    print("Testing agents...")
    from src.agents.gateway_orchestrator import GatewayOrchestrator, orchestrator
    from src.agents.routing_agent import RoutingAgent, routing_agent
    from src.agents.cost_agent import CostAgent, cost_agent

    # Test orchestrator instantiation
    if not isinstance(orchestrator, GatewayOrchestrator):
        print("  ✗ FAIL: Orchestrator instance")
        return False
    print("  Orchestrator instance OK")

    # Test routing agent instantiation
    if not isinstance(routing_agent, RoutingAgent):
        print("  ✗ FAIL: Routing agent instance")
        return False
    print("  Routing agent instance OK")

    # Test cost agent instantiation
    if not isinstance(cost_agent, CostAgent):
        print("  ✗ FAIL: Cost agent instance")
        return False
    print("  Cost agent instance OK")

    print("  ✓ PASS")
    return True


async def test_api_modules():
    """Test API modules."""
    print("Testing API modules...")
    from src.api.middleware import APIKeyAuth, RateLimiter
    from src.api.v1 import chat, router as router_module, cost, providers

    # Test middleware
    try:
        APIKeyAuth
        RateLimiter
        print("  Middleware OK")
    except Exception as e:
        print(f"  ✗ FAIL: Middleware: {e}")
        return False

    # Test API routers
    routers = [chat.router, router_module.router, cost.router, providers.router]
    for r in routers:
        if r is None:
            print(f"  ✗ FAIL: Missing router")
            return False
    print(f"  {len(routers)} API routers OK")

    print("  ✓ PASS")
    return True


async def test_services():
    """Test service modules."""
    print("Testing services...")
    from src.services.cost_calculator import CostCalculator
    from src.services.cache import CacheService

    # Test cost calculator
    try:
        input_cost, output_cost = CostCalculator.calculate_cost(
            input_tokens=100,
            output_tokens=50,
            model_id="gpt-3.5-turbo"
        )
        print(f"  Cost calculator OK (input={input_cost}, output={output_cost})")
    except Exception as e:
        print(f"  ✗ FAIL: Cost calculator: {e}")
        return False

    # Test cache service
    try:
        CacheService.hash_key("test", "key")
        print("  Cache service OK")
    except Exception as e:
        print(f"  ✗ FAIL: Cache service: {e}")
        return False

    print("  ✓ PASS")
    return True


async def main():
    """Run all core tests."""
    print("=" * 60)
    print("LLM Router Core Functionality Test")
    print("=" * 60)
    print()

    tests = [
        ("Settings", test_settings),
        ("Encryption", test_encryption),
        ("Provider Factory", test_provider_factory),
        ("Provider Classes", test_provider_classes),
        ("Schemas", test_schemas),
        ("Database Models", test_models),
        ("Agents", test_agents),
        ("API Modules", test_api_modules),
        ("Services", test_services),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            results.append((name, False))
        print()

    # Print summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20} {status}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed! 🎉")
        return 0
    else:
        print(f"{total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
