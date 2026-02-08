# Stage 0 测试验证计划

## 项目信息

- **项目**: LLM Router - 智能多模型 API 网关
- **阶段**: Stage 0 - 技术验证
- **日期**: 2025-02-07
- **状态**: 测试完成

---

## 测试文件结构

```
llm-router/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                          # Pytest 配置和夹具
│   ├── unit/                                # 单元测试
│   │   ├── test_providers.py          # Provider 测试
│   │   ├── test_agents.py             # Agent 测试
│   │   ├── test_models.py             # 数据模型测试
│   │   └── test_api.py                # API 端点测试
│   └── integration/                         # 集成测试
│       └── test_chat_api.py         # 端到端流程测试
├── scripts/
│   ├── run_tests.sh                        # 自动化测试运行脚本
│   └── test_summary.sh                     # 测试总结报告脚本
└── pytest.ini                                # Pytest 配置
```

---

## 测试用例清单

### 1. Provider 单元测试 (test_providers.py)

#### 1.1 ProviderFactory 测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_registered_providers | 验证所有内置 Provider 已注册 | ✅ |
| test_create_openai_provider | 验证 OpenAI Provider 创建 | ✅ |
| test_create_anthropic_provider | 验证 Anthropic Provider 创建 | ✅ |
| test_create_unknown_provider | 验证未知 Provider 创建时抛出错误 | ✅ |
| test_get_cached_provider | 验证 Provider 缓存机制 | ✅ |

#### 1.2 OpenAIProvider 测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_get_provider_name | 验证 Provider 名称正确 | ✅ |
| test_calculate_cost | 验证成本计算（gpt-3.5-turbo） | ✅ |
| test_calculate_cost_unknown_model | 验证未知模型成本为 0 | ✅ |
| test_health_check_success | 验证健康检查成功 | ✅ |
| test_health_check_failure | 验证健康检查失败 | ✅ |
| test_chat_completion_success | 验证聊天完成成功 | ✅ |

#### 1.3 AnthropicProvider 测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_get_provider_name | 验证 Provider 名称正确 | ✅ |
| test_calculate_cost | 验证成本计算（claude-3-haiku） | ✅ |
| test_calculate_cost_unknown_model | 验证未知模型成本为 0 | ✅ |
| test_health_check_success | 验证健康检查成功 | ✅ |
| test_chat_completion_success | 验证聊天完成成功 | ✅ |

#### 1.4 数据类测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_token_usage_creation | TokenUsage 数据类创建 | ✅ |
| test_token_usage_to_dict | TokenUsage to_dict 方法 | ✅ |
| test_chat_request_creation | ChatRequest 数据类创建 | ✅ |
| test_chat_response_to_dict | ChatResponse to_dict 方法 | ✅ |

---

### 2. Agent 单元测试 (test_agents.py)

#### 2.1 GatewayOrchestrator 测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_initialization | 验证初始化 | ✅ |
| test_get_status_default | 验证默认状态 | ✅ |
| test_toggle_immediate | 验证立即切换 | ✅ |
| test_toggle_with_delay | 验证延迟切换 | ✅ |
| test_toggle_in_cooldown | 验证冷却期间切换 | ✅ |
| test_get_history | 验证历史记录 | ✅ |
| test_get_metrics | 验证指标获取 | ✅ |

#### 2.2 RoutingAgent 测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_initialization | 验证初始化 | ✅ |
| test_route_with_fixed_provider | 验证固定 Provider 路由 | ✅ |
| test_route_default | 验证默认路由（加权轮询）| ✅ |
| test_weighted_round_robin_routing | 验证加权轮询路由 | ✅ |
| test_get_available_models | 验证获取可用模型 | ✅ |
| test_get_available_providers | 验证获取可用 Provider | ✅ |

#### 2.3 ProviderAgent 测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_initialization | 验证初始化 | ✅ |
| test_health_check_all | 验证所有 Provider 健康检查 | ✅ |
| test_health_check_single | 验证单个 Provider 健康检查 | ✅ |
| test_get_best_provider | 验证获取最佳 Provider | ✅ |
| test_get_all_providers | 验证获取所有 Provider | ✅ |

#### 2.4 CostAgent 测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_record_cost | 验证成本记录 | ✅ |
| test_get_current_cost | 验证当前成本获取 | ✅ |
| test_get_daily_cost | 验证每日成本获取 | ✅ |
| test_get_cost_by_model | 验证按模型成本获取 | ✅ |
| test_get_cost_by_user | 验证按用户成本获取 | ✅ |
| test_get_cost_summary | 验证成本摘要获取 | ✅ |

---

### 3. 数据模型单元测试 (test_models.py)

#### 3.1 枚举类型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_user_role_values | UserRole 枚举值 | ✅ |
| test_user_status_values | UserStatus 枚举值 | ✅ |
| test_provider_type_values | ProviderType 枚举值 | ✅ |
| test_provider_status_values | ProviderStatus 枚举值 | ✅ |

#### 3.2 User 模型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_user_creation | User 模型创建 | ✅ |
| test_user_with_default_values | User 模型默认值 | ✅ |

#### 3.3 APIKey 模型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_api_key_creation | API Key 模型创建 | ✅ |
| test_api_key_with_expires_at | API Key 过期时间 | ✅ |

#### 3.4 Provider 模型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_provider_creation | Provider 模型创建 | ✅ |
| test_provider_with_region | Provider 模型（带区域） | ✅ |

#### 3.5 ProviderModel 模型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_provider_model_creation | ProviderModel 模型创建 | ✅ |

#### 3.6 RoutingRule 模型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_routing_rule_creation | RoutingRule 模型创建 | ✅ |

#### 3.7 RoutingDecision 模型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_routing_decision_creation | RoutingDecision 模型创建 | ✅ |

#### 3.8 RoutingSwitchState 模型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_routing_switch_state_creation | RoutingSwitchState 模型创建 | ✅ |

#### 3.9 CostRecord 模型测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_cost_record_creation | CostRecord 模型创建 | ✅ |

---

### 4. API 端点单元测试 (test_api.py)

#### 4.1 健康检查端点测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_health_check | 健康检查端点 | ✅ |
| test_root_endpoint | 根端点 | ✅ |

#### 4.2 Router 控制端点测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_get_router_status_without_auth | 无认证获取状态 | ✅ |
| test_toggle_router_without_auth | 无认证切换 | ✅ |
| test_toggle_router_with_auth | 认证后切换 | ✅ |

#### 4.3 Chat 端点测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_list_models_without_auth | 无认证获取模型 | ✅ |
| test_chat_completion_without_auth | 无认证聊天 | ✅ |

#### 4.4 Provider 端点测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_list_providers_without_auth | 无认证获取 Provider | ✅ |
| test_create_provider_without_auth | 无认证创建 Provider | ✅ |

#### 4.5 Cost 端点测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_get_current_cost_without_auth | 无认证获取成本 | ✅ |

#### 4.6 中间件测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_api_key_auth_missing | API Key 缺失 | ✅ |
| test_api_key_auth_with_admin_key | 管理 Key 认证 | ✅ |

#### 4.7 Schema 验证测试
| 测试用例 | 描述 | 状态 |
|---------|------|------|
| test_toggle_request | ToggleRequest Schema | ✅ |
| test_toggle_request_validation | ToggleRequest 验证 | ✅ |
| test_routing_rule_create | RoutingRuleCreate Schema | ✅ |
| test_chat_completion_request | ChatCompletionRequest Schema | ✅ |
| test_message_validation | Message 验证 | ✅ |
| test_message_validation_invalid | 无效 Message 验证 | ✅ |

---

### 5. 集成测试 (test_chat_api.py)

#### 5.1 聊天流程集成测试
| 测试用例 | 描述 | 状态 | 标记 |
|---------|------|------|-------|
| test_complete_chat_flow_with_routing | 完整聊天流程（含路由） | ✅ | @integration |
| test_chat_flow_with_cost_tracking | 聊天流程（含成本追踪） | ✅ | @integration |
| test_routing_with_rule | 自定义规则路由 | ✅ | @integration |

#### 5.2 路由开关集成测试
| 测试用例 | 描述 | 状态 | 标记 |
|---------|------|-------|
| test_toggle_workflow | 切换工作流 | ✅ | @integration |
| test_toggle_with_delay | 延迟切换 | ✅ | @integration |

#### 5.3 Provider 健康监控集成测试
| 测试用例 | 描述 | 状态 | 标记 |
|---------|------|-------|
| test_provider_health_check | Provider 健康检查 | ✅ | @integration |

#### 5.4 成本追踪集成测试
| 测试用例 | 描述 | 状态 | 标记 |
|---------|------|-------|
| test_cost_accumulation | 成本累积 | ✅ | @integration |
| test_cost_by_model | 按模型成本 | ✅ | @integration |

---

## 测试标记

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.requires_db` - 需要数据库
- `@pytest.mark.requires_redis` - 需要 Redis

---

## 如何运行测试

### 查看测试总结
```bash
./scripts/test_summary.sh
```

### 运行所有测试（覆盖率要求 > 60%）
```bash
# 确保依赖已安装
uv sync

# 运行测试（覆盖率报告将保失败如果低于 60%）
uv run pytest tests/ -v --cov=src --cov-fail-under=60
```

### 只运行单元测试
```bash
uv run pytest tests/unit/ -v --cov=src
```

### 只运行集成测试
```bash
uv run pytest tests/integration/ -v --cov=src --cov-append
```

### 生成 HTML 覆盖率报告
```bash
uv run pytest tests/ -v --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 测试覆盖率目标

| 模块 | 目标 | 说明 |
|------|------|------|
| Provider 抽象层 | >80% | 基类和实现需要高覆盖率 |
| Agent 组件 | >80% | 核心业务逻辑需要高覆盖率 |
| 数据模型 | >70% | 模型类和枚举需要高覆盖率 |
| API 端点 | >70% | 路由和请求处理需要覆盖率 |
| 整体覆盖率 | >60% | Stage 0 要求 |

---

## 注意事项

1. 某些测试需要数据库和 Redis 连接，运行前请先启动：
   ```bash
   docker-compose up -d postgres redis
   ```
   或者使用开发脚本：
   ```bash
   ./scripts/dev.sh
   ```

2. 首次运行需要安装测试依赖：
   ```bash
   uv sync
   ```

3. 覆盖率低于 60% 将导致测试失败，确保核心功能都有测试覆盖

4. 使用 `--cov-fail-under=60` 确保覆盖率达标

---

## 测试文件统计

| 类型 | 文件数 | 测试用例数 |
|------|--------|-----------|
| 单元测试 | 4 | ~70 |
| 集成测试 | 1 | ~10 |
| 测试夹具 | 1 | 5+ |
| 脚本工具 | 3 | - |
| **总计** | **~85** |

---

## Stage 0 验收标准

| 标准 | 要求 | 状态 |
|------|------|------|
| 项目脚手架搭建 | 完成目录结构、依赖配置 | ✅ |
| Provider 对接验证 | OpenAI、Anthropic 实现完成 | ✅ |
| 路由算法原型 | 规则路由、加权轮询实现 | ✅ |
| 数据库设计验证 | 所有表模型定义完成 | ✅ |
| 单元测试 | ~70 个测试用例 | ✅ |
| 集成测试 | ~10 个测试用例 | ✅ |
| 测试覆盖率要求 | 配置 pytest.ini | ✅ |
| Docker 配置 | Dockerfile 和 docker-compose.yml | ✅ |
| 启动脚本 | start.sh, dev.sh, test_summary.sh | ✅ |

---

## 下一步（Stage 1 - MVP 核心版）

根据 `llm-router-impl-plan.md`，Stage 1 的主要任务：

1. Provider 抽象层增强
2. Gateway Orchestrator 完善
3. 核心路由模块完善
4. 成本监控模块完善
5. 基础管理界面（React）
6. 开发者门户（React）
