"""
Basic functionality test script.

Tests the core functionality of the LLM Router.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_database_connection():
    """Test database connection."""
    print("Testing database connection...")

    try:
        from src.db.base import engine

        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("  (This is expected if PostgreSQL is not running)")
        return False  # Return False instead of failing


async def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")

    try:
        from src.config.redis_config import RedisConfig

        redis = await RedisConfig.get_client()
        await redis.ping()
        print("Redis connection successful!")
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        print("  (This is expected if Redis is not running)")
        return False  # Return False instead of failing


async def test_provider_factory():
    """Test provider factory."""
    print("Testing provider factory...")

    try:
        from src.providers.factory import ProviderFactory

        providers = ProviderFactory.list_providers()
        print(f"Registered providers: {providers}")

        if "openai" in providers and "anthropic" in providers:
            print("Provider factory test passed!")
            return True
        else:
            print("Provider factory test failed!")
            return False
    except Exception as e:
        print(f"Provider factory test failed: {e}")
        return False


async def test_encryption():
    """Test encryption utilities."""
    print("Testing encryption utilities...")

    try:
        from src.utils.encryption import EncryptionManager, hash_api_key, generate_api_key

        # Test encryption/decryption
        secret = "my-secret-key"
        encrypted = EncryptionManager.encrypt(secret)
        decrypted = EncryptionManager.decrypt(encrypted)

        if secret == decrypted:
            print("Encryption/decryption test passed!")
        else:
            print("Encryption/decryption test failed!")
            return False

        # Test API key hashing
        api_key = "test-api-key"
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        if hash1 == hash2 and len(hash1) == 64:
            print("API key hashing test passed!")
        else:
            print("API key hashing test failed!")
            return False

        # Test API key generation
        new_key = generate_api_key()
        if new_key.startswith("llm_"):
            print("API key generation test passed!")
        else:
            print("API key generation test failed!")
            return False

        return True
    except Exception as e:
        print(f"Encryption test failed: {e}")
        return False


async def test_orchestrator():
    """Test gateway orchestrator."""
    print("Testing gateway orchestrator...")

    try:
        from src.agents.gateway_orchestrator import orchestrator

        await orchestrator.initialize()
        status = await orchestrator.get_status()

        print(f"Orchestrator status: enabled={status.enabled}, pending={status.pending}")

        if status.enabled is not None:
            print("Orchestrator test passed!")
            return True
        else:
            print("Orchestrator test failed!")
            return False
    except Exception as e:
        print(f"Orchestrator test failed: {e}")
        print("  (This is expected if Redis is not running)")
        return False  # Return False instead of failing


async def test_routing_agent():
    """Test routing agent."""
    print("Testing routing agent...")

    try:
        from src.agents.routing_agent import routing_agent

        await routing_agent.initialize()
        providers = await routing_agent.get_available_providers()

        print(f"Available providers: {len(providers)}")
        print("Routing agent test passed!")
        return True
    except Exception as e:
        print(f"Routing agent test failed: {e}")
        print("  (This is expected if Database is not running)")
        return False  # Return False instead of failing


async def test_cost_agent():
    """Test cost agent."""
    print("Testing cost agent...")

    try:
        from src.agents.cost_agent import cost_agent

        current = await cost_agent.get_current_cost()
        print(f"Current cost: {current}")
        print("Cost agent test passed!")
        return True
    except Exception as e:
        print(f"Cost agent test failed: {e}")
        print("  (This is expected if Redis is not running)")
        return False  # Return False instead of failing


async def test_settings():
    """Test settings."""
    print("Testing settings...")

    try:
        from src.config.settings import settings

        print(f"App name: {settings.app_name}")
        print(f"App version: {settings.app_version}")
        print(f"Environment: {settings.app_env}")
        print("Settings test passed!")
        return True
    except Exception as e:
        print(f"Settings test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 50)
    print("LLM Router Basic Functionality Test")
    print("=" * 50)
    print()

    tests = [
        ("Settings", test_settings),
        ("Encryption", test_encryption),
        ("Provider Factory", test_provider_factory),
        ("Database", test_database_connection),
        ("Redis", test_redis_connection),
        ("Orchestrator", test_orchestrator),
        ("Routing Agent", test_routing_agent),
        ("Cost Agent", test_cost_agent),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"Test '{name}' raised exception: {e}")
            results.append((name, False))
        print()

    # Print summary
    print("=" * 50)
    print("Test Summary")
    print("=" * 50)

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
