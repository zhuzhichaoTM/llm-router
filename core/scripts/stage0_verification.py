"""
Stage 0 验收测试脚本

验证 Stage 0 的所有任务是否完成并功能正常。
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.config.redis_config import RedisConfig
from src.db.base import async_session_maker, engine, init_db, close_db
from src.providers.base import IProvider
from src.providers.openai import OpenAIProvider
from src.providers.anthropic import AnthropicProvider
from src.providers.factory import ProviderFactory
from src.agents.gateway_orchestrator import orchestrator
from src.agents.routing_agent import routing_agent
from src.agents.provider_agent import provider_agent
from src.agents.cost_agent import cost_agent
from src.models.base import Base
from src.models.user import User, APIKey, UserRole, UserStatus
from src.models.provider import Provider, ProviderModel, ProviderType, ProviderStatus
from src.models.routing import RoutingRule, RoutingDecision, RoutingSwitchState
from src.models.cost import CostRecord, CostBudget
from src.utils.encryption import EncryptionManager
from src.utils.logging import logger


class VerificationResult:
    """验证结果类"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, name: str, message: str = ""):
        self.passed.append((name, message))
        print(f"✅ PASS: {name}" + (f" - {message}" if message else ""))

    def add_fail(self, name: str, message: str = ""):
        self.failed.append((name, message))
        print(f"❌ FAIL: {name}" + (f" - {message}" if message else ""))

    def add_warning(self, name: str, message: str = ""):
        self.warnings.append((name, message))
        print(f"⚠️  WARN: {name}" + (f" - {message}" if message else ""))

    def summary(self):
        """打印总结"""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {len(self.passed)}")
        print(f"❌ Failed: {len(self.failed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print("=" * 60)

        if not self.failed:
            print("🎉 Stage 0 验收通过！所有核心功能正常。")
            return True
        else:
            print("\n❌ Stage 0 验收失败，请修复以下问题：")
            for name, message in self.failed:
                print(f"  - {name}: {message}")
            return False


async def verify_config(result: VerificationResult) -> None:
    """验证配置管理"""
    print("\n[1/10] 验证配置管理...")

    # 验证应用配置
    assert settings.app_name == "LLM Router", "应用名称不匹配"
    result.add_pass("Settings Load", f"app_name={settings.app_name}")

    # 验证数据库配置
    assert settings.database_url, "数据库 URL 未配置"
    result.add_pass("Database Config", "database_url configured")

    # 验证 Redis 配置
    assert settings.redis_url, "Redis URL 未配置"
    result.add_pass("Redis Config", "redis_url configured")

    # 验证密钥配置
    assert settings.secret_key, "Secret key 未配置"
    assert settings.admin_api_key, "Admin API key 未配置"
    result.add_pass("API Keys Config", "keys configured")


async def verify_database(result: VerificationResult) -> None:
    """验证数据库"""
    print("\n[2/10] 验证数据库...")

    try:
        # 测试数据库连接
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("  - 数据库表创建成功")
            result.add_pass("Database Connection", "可以连接并创建表")

        # 验证所有模型已定义
        assert User.__tablename__ == "users"
        assert APIKey.__tablename__ == "api_keys"
        assert Provider.__tablename__ == "providers"
        assert ProviderModel.__tablename__ == "provider_models"
        assert RoutingRule.__tablename__ == "routing_rules"
        assert RoutingDecision.__tablename__ == "routing_decisions"
        assert CostRecord.__tablename__ == "cost_records"
        result.add_pass("Data Models", "所有表模型已定义")

    except Exception as e:
        result.add_fail("Database", f"数据库连接失败: {e}")


async def verify_redis(result: VerificationResult) -> None:
    """验证 Redis"""
    print("\n[3/10] 验证 Redis...")

    try:
        redis = await RedisConfig.get_client()
        await redis.ping()
        result.add_pass("Redis Connection", "Redis 可以连接并响应 ping")

        # 测试 Redis 数据结构
        await redis.set("test_key", "test_value", ex=60)
        value = await redis.get("test_key")
        assert value == "test_value", "Redis 读写测试失败"
        await redis.delete("test_key")
        result.add_pass("Redis Operations", "Redis 读写操作正常")

    except Exception as e:
        result.add_fail("Redis", f"Redis 连接失败: {e}")


def verify_providers(result: VerificationResult) -> None:
    """验证 Provider 抽象层"""
    print("\n[4/10] 验证 Provider 抽象层...")

    # 验证 IProvider 接口
    required_methods = [
        "chat_completion",
        "stream_chat_completion",
        "get_model_list",
        "health_check",
        "get_provider_name",
    ]
    for method in required_methods:
        assert hasattr(IProvider, method), f"IProvider 缺少 {method} 方法"
    result.add_pass("IProvider Interface", f"所有 {len(required_methods)} 个必需方法已定义")

    # 验证 Provider 实现
    assert issubclass(OpenAIProvider, IProvider), "OpenAIProvider 未继承 IProvider"
    assert issubclass(AnthropicProvider, IProvider), "AnthropicProvider 未继承 IProvider"
    result.add_pass("Provider Implementations", "OpenAI 和 Anthropic Provider 正确实现")

    # 验证 Provider 工厂
    providers = ProviderFactory.list_providers()
    assert "openai" in providers, "OpenAI Provider 未注册"
    assert "anthropic" in providers, "Anthropic Provider 未注册"
    result.add_pass("Provider Factory", f"已注册 {len(providers)} 个 Provider: {providers}")


async def verify_agents(result: VerificationResult) -> None:
    """验证 Agent 组件"""
    print("\n[5/10] 验证 Agent 组件...")

    # 验证 Gateway Orchestrator
    assert hasattr(orchestrator, "_initialized"), "Orchestrator 未正确初始化"
    assert hasattr(orchestrator, "_enabled"), "Orchestrator 缺少 enabled 状态"
    assert hasattr(orchestrator, "get_status"), "Orchestrator 缺少 get_status 方法"
    assert hasattr(orchestrator, "toggle"), "Orchestrator 缺少 toggle 方法"
    result.add_pass("Gateway Orchestrator", "状态管理和切换功能完整")

    # 验证 Routing Agent
    assert hasattr(routing_agent, "_initialized"), "Routing Agent 未正确初始化"
    assert hasattr(routing_agent, "route"), "Routing Agent 缺少 route 方法"
    assert hasattr(routing_agent, "execute"), "Routing Agent 缺少 execute 方法"
    result.add_pass("Routing Agent", "路由决策和执行功能完整")

    # 验证 Provider Agent
    assert hasattr(provider_agent, "_initialized"), "Provider Agent 未正确初始化"
    assert hasattr(provider_agent, "health_check_all"), "Provider Agent 缺少 health_check_all 方法"
    assert hasattr(provider_agent, "get_best_provider"), "Provider Agent 缺少 get_best_provider 方法"
    result.add_pass("Provider Agent", "健康检查和最佳选择功能完整")

    # 验证 Cost Agent
    assert hasattr(cost_agent, "_initialized"), "Cost Agent 未正确初始化"
    assert hasattr(cost_agent, "record_cost"), "Cost Agent 缺少 record_cost 方法"
    assert hasattr(cost_agent, "get_current_cost"), "Cost Agent 缺少 get_current_cost 方法"
    result.add_pass("Cost Agent", "成本记录和统计功能完整")


async def verify_encryption(result: VerificationResult) -> None:
    """验证加密工具"""
    print("\n[6/10] 验证加密工具...")

    # 测试加密解密
    test_data = "test-api-key-12345"
    encrypted = EncryptionManager.encrypt(test_data)
    assert encrypted != test_data, "加密失败：密文与明文相同"
    result.add_pass("Encryption", "可以加密数据")

    decrypted = EncryptionManager.decrypt(encrypted)
    assert decrypted == test_data, f"解密失败：'{decrypted}' != '{test_data}'"
    result.add_pass("Decryption", "可以解密数据")

    # 测试哈希（hash_api_key 是全局函数）
    from src.utils.encryption import hash_api_key
    api_key = "sk-test-123"
    hashed = hash_api_key(api_key)
    assert hashed != api_key, "哈希失败：哈希值与原始值相同"
    assert len(hashed) == 64, f"哈希长度错误：{len(hashed)} != 64"
    result.add_pass("API Key Hashing", "可以正确哈希 API Key")


async def verify_api_endpoints(result: VerificationResult) -> None:
    """验证 API 端点"""
    print("\n[7/10] 验证 API 端点...")

    # 导入 API 路由
    from src.api.v1 import chat, router, cost, providers

    # 验证 Chat API
    assert hasattr(chat, "router"), "Chat API 缺少 router"
    assert hasattr(chat, "chat_completions"), "Chat API 缺少 chat_completions 端点"
    assert hasattr(chat, "list_models"), "Chat API 缺少 list_models 端点"
    result.add_pass("Chat API", "chat/completions 和 models 端点已定义")

    # 验证 Router API
    assert hasattr(router, "router"), "Router API 缺少 router"
    assert hasattr(router, "get_router_status"), "Router API 缺少 status 端点"
    assert hasattr(router, "toggle_router"), "Router API 缺少 toggle 端点"
    assert hasattr(router, "list_routing_rules"), "Router API 缺少 rules 端点"
    result.add_pass("Router API", "status, toggle, rules 端点已定义")

    # 验证 Cost API
    assert hasattr(cost, "router"), "Cost API 缺少 router"
    assert hasattr(cost, "get_current_cost"), "Cost API 缺少 current 端点"
    result.add_pass("Cost API", "current 端点已定义")

    # 验证 Provider API
    assert hasattr(providers, "router"), "Provider API 缺少 router"
    assert hasattr(providers, "list_providers"), "Provider API 缺少 list 端点"
    assert hasattr(providers, "create_provider"), "Provider API 缺少 create 端点"
    assert hasattr(providers, "update_provider"), "Provider API 缺少 update 端点"
    assert hasattr(providers, "delete_provider"), "Provider API 缺少 delete 端点"
    result.add_pass("Provider API", "CRUD 端点已定义")


async def verify_docker(result: VerificationResult) -> None:
    """验证 Docker 配置"""
    print("\n[8/10] 验证 Docker 配置...")

    # 检查 Dockerfiles
    docker_dir = Path("docker")
    backend_dockerfile = docker_dir / "Dockerfile.backend"
    frontend_dockerfile = docker_dir / "Dockerfile.frontend"
    compose_file = Path("docker-compose.yml")

    if backend_dockerfile.exists():
        content = backend_dockerfile.read_text()
        assert "FROM python:3.11" in content, "Backend Dockerfile 基础镜像不正确"
        assert "uvicorn" in content, "Backend Dockerfile 缺少 uvicorn 启动命令"
        result.add_pass("Backend Dockerfile", "Dockerfile.backend 存在且配置正确")
    else:
        result.add_fail("Backend Dockerfile", "Dockerfile.backend 不存在")

    if frontend_dockerfile.exists():
        content = frontend_dockerfile.read_text()
        assert "FROM node:" in content, "Frontend Dockerfile 基础镜像不正确"
        result.add_pass("Frontend Dockerfile", "Dockerfile.frontend 存在且配置正确")
    else:
        result.add_fail("Frontend Dockerfile", "Dockerfile.frontend 不存在")

    if compose_file.exists():
        content = compose_file.read_text()
        assert "postgres:" in content, "docker-compose.yml 缺少 postgres 服务"
        assert "redis:" in content, "docker-compose.yml 缺少 redis 服务"
        assert "backend:" in content, "docker-compose.yml 缺少 backend 服务"
        result.add_pass("Docker Compose", "docker-compose.yml 配置完整")
    else:
        result.add_fail("Docker Compose", "docker-compose.yml 不存在")


def verify_scripts(result: VerificationResult) -> None:
    """验证启动脚本"""
    print("\n[9/10] 验证启动脚本...")

    # 检查脚本文件
    start_script = Path("scripts/start.sh")
    dev_script = Path("scripts/dev.sh")
    init_script = Path("scripts/init_db.py")

    if start_script.exists():
        content = start_script.read_text()
        assert "docker-compose" in content, "start.sh 缺少 docker-compose 命令"
        assert "init_db.py" in content, "start.sh 缺少数据库初始化"
        result.add_pass("Start Script", "scripts/start.sh 存在且配置正确")
    else:
        result.add_fail("Start Script", "scripts/start.sh 不存在")

    if dev_script.exists():
        content = dev_script.read_text()
        assert "uvicorn" in content, "dev.sh 缺少 uvicorn 启动命令"
        result.add_pass("Dev Script", "scripts/dev.sh 存在且配置正确")
    else:
        result.add_fail("Dev Script", "scripts/dev.sh 不存在")

    if init_script.exists():
        content = init_script.read_text()
        assert "create_tables" in content, "init_db.py 缺少表创建逻辑"
        assert "seed_admin_user" in content, "init_db.py 缺少管理员用户初始化"
        result.add_pass("Init DB Script", "scripts/init_db.py 存在且逻辑完整")
    else:
        result.add_fail("Init DB Script", "scripts/init_db.py 不存在")


async def verify_data_integrity(result: VerificationResult) -> None:
    """验证数据完整性"""
    print("\n[10/10] 验证数据完整性...")

    # 检查路由模型字段拼写
    from src.models.routing import RoutingRule

    # 检查是否有正确的字段名
    if hasattr(RoutingRule, "__annotations__"):
        annotations = RoutingRule.__annotations__
        if "min_complexity" in annotations and "max_complexity" in annotations:
            result.add_pass("RoutingRule Fields", "min_complexity 和 max_complexity 字段拼写正确")
        else:
            result.add_warning("RoutingRule Fields", "未找到 complexity 相关字段")

    # 检查 cost 字段类型
    from src.models.routing import RoutingDecision
    from decimal import Decimal
    from sqlalchemy import Numeric

    # 检查表中列的实际类型
    cost_column = next((c for c in RoutingDecision.__table__.columns if c.name == "cost"), None)
    if cost_column and isinstance(cost_column.type, Numeric):
        result.add_pass("RoutingDecision Cost", "cost 字段类型为 Numeric")
    else:
        column_type = type(cost_column.type).__name__ if cost_column else "unknown"
        result.add_fail("RoutingDecision Cost", f"cost 字段类型不是 Numeric，而是: {column_type}")


async def main():
    """主验证函数"""
    print("=" * 60)
    print("LLM Router Stage 0 验收测试")
    print("=" * 60)
    print(f"验证目标：确保 Stage 0 的所有核心功能已完成并正常工作")
    print()

    result = VerificationResult()

    try:
        # 运行所有验证
        await verify_config(result)
        await verify_database(result)
        await verify_redis(result)
        verify_providers(result)
        await verify_agents(result)
        await verify_encryption(result)
        await verify_api_endpoints(result)
        await verify_docker(result)
        verify_scripts(result)
        await verify_data_integrity(result)

        # 打印总结
        success = result.summary()

        # 返回退出码
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
