"""
简化的 Stage 0 验收脚本
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.providers.base import IProvider
from src.providers.openai import OpenAIProvider
from src.providers.anthropic import AnthropicProvider
from src.providers.factory import ProviderFactory
from src.agents.gateway_orchestrator import orchestrator
from src.agents.routing_agent import routing_agent
from src.agents.provider_agent import provider_agent
from src.agents.cost_agent import cost_agent
from src.models.base import Base

print("=" * 50)
print("Stage 0 简化验收测试")
print("=" * 50)

tests_passed = 0
tests_failed = 0

# Test 1: 配置加载
try:
    assert settings.app_name == "LLM Router"
    assert settings.database_url
    assert settings.redis_url
    print("✅ 配置加载成功")
    tests_passed += 1
except AssertionError as e:
    print(f"❌ 配置验证失败: {e}")
    tests_failed += 1

# Test 2: Provider 抽象层
try:
    assert issubclass(OpenAIProvider, IProvider)
    assert issubclass(AnthropicProvider, IProvider)
    assert "openai" in ProviderFactory.list_providers()
    assert "anthropic" in ProviderFactory.list_providers()
    print("✅ Provider 抽象层完整")
    tests_passed += 1
except AssertionError as e:
    print(f"❌ Provider 抽象层验证失败: {e}")
    tests_failed += 1

# Test 3: Agent 组件
try:
    assert hasattr(orchestrator, "toggle")
    assert hasattr(orchestrator, "get_status")
    assert hasattr(routing_agent, "route")
    assert hasattr(routing_agent, "execute")
    assert hasattr(provider_agent, "health_check_all")
    assert hasattr(cost_agent, "record_cost")
    print("✅ Agent 组件完整")
    tests_passed += 1
except AssertionError as e:
    print(f"❌ Agent 组件验证失败: {e}")
    tests_failed += 1

# Test 4: 数据模型
try:
    from src.models.user import User, APIKey
    from src.models.provider import Provider, ProviderModel
    from src.models.routing import RoutingRule, RoutingDecision
    from src.models.cost import CostRecord
    print("✅ 数据模型完整")
    tests_passed += 1
except AssertionError as e:
    print(f"❌ 数据模型验证失败: {e}")
    tests_failed += 1

# Test 5: API 端点
try:
    from src.api.v1 import chat, router, cost, providers
    assert hasattr(chat, "router")
    assert hasattr(router, "router")
    assert hasattr(cost, "router")
    assert hasattr(providers, "router")
    print("✅ API 端点完整")
    tests_passed += 1
except AssertionError as e:
    print(f"❌ API 端点验证失败: {e}")
    tests_failed += 1

# Test 6: Docker 配置
try:
    docker_files = [
        "docker/Dockerfile.backend",
        "docker/Dockerfile.frontend",
        "docker-compose.yml",
    ]
    for f in docker_files:
        assert Path(f).exists(), f"{f} 不存在"
    print("✅ Docker 配置完整")
    tests_passed += 1
except AssertionError as e:
    print(f"❌ Docker 配置验证失败: {e}")
    tests_failed += 1

# Test 7: 启动脚本
try:
    scripts = [
        "scripts/start.sh",
        "scripts/dev.sh",
        "scripts/init_db.py",
        "scripts/stage0_verification.py",
    ]
    for s in scripts:
        assert Path(s).exists(), f"{s} 不存在"
    print("✅ 启动脚本完整")
    tests_passed += 1
except AssertionError as e:
    print(f"❌ 启动脚本验证失败: {e}")
    tests_failed += 1

print("=" * 50)
print(f"验收结果: {tests_passed} 通过, {tests_failed} 失败")
print("=" * 50)

if tests_failed == 0:
    print("🎉 Stage 0 验收通过！")
    sys.exit(0)
else:
    print("❌ Stage 0 验收失败")
    sys.exit(1)
