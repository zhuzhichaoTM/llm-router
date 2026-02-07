# LLM Router 全栈实施计划

## 项目概述

- **项目**: LLM Router - 智能多模型 API 网关
- **状态**: 绿地项目（无现有代码）
- **实施范围**: Stage 0 + 1 (MVP 核心版)
- **技术栈**:
  - 后端: Python 3.11+, FastAPI, SQLAlchemy, Redis
  - 前端: React 18+, TypeScript, Recharts, Ant Design
  - 数据库: PostgreSQL 15+, Redis 7+
  - 部署: Docker, Docker Compose

---

## 实施范围：Stage 0 + 1 (MVP)

### Stage 0 - 技术验证（第1-2周）
1. 项目脚手架搭建
2. Provider 对接验证（OpenAI + Anthropic）
3. 路由算法原型
4. 数据库设计验证

### Stage 1 - MVP 核心版（第3-10周）
1. Provider 抽象层实现
2. Gateway Orchestrator（路由开关控制）
3. 核心路由模块
4. 成本监控模块
5. 基础管理界面（React）
6. 开发者门户（React）

---

## 项目目录结构

```
llm-router/
├── src/                          # Python 后端源码
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── config/                    # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py            # 配置类
│   │   └── redis_config.py        # Redis 配置
│   ├── providers/                 # Provider 适配器
│   │   ├── __init__.py
│   │   ├── base.py                # Provider 基类/接口
│   │   ├── openai.py              # OpenAI 实现
│   │   ├── anthropic.py           # Anthropic 实现
│   │   └── factory.py            # Provider 工厂
│   ├── agents/                    # Agent 实现
│   │   ├── __init__.py
│   │   ├── gateway_orchestrator.py # 网关编排器
│   │   ├── routing_agent.py       # 路由 Agent
│   │   ├── provider_agent.py      # Provider Agent
│   │   └── cost_agent.py          # 成本 Agent
│   ├── api/                       # API 路由
│   │   ├── __init__.py
│   │   ├── v1/                   # v1 API
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # 聊天完成 API
│   │   │   ├── router.py          # 路由控制 API
│   │   │   ├── cost.py            # 成本 API
│   │   │   └── providers.py       # Provider 管理 API
│   │   └── middleware.py          # 中间件
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── base.py                # 基础模型
│   │   ├── user.py                # 用户模型
│   │   ├── provider.py            # Provider 模型
│   │   ├── routing.py             # 路由模型
│   │   └── cost.py               # 成本模型
│   ├── db/                        # 数据库
│   │   ├── __init__.py
│   │   ├── session.py             # 数据库会话
│   │   └── base.py                # 数据库基类
│   ├── services/                  # 业务服务
│   │   ├── __init__.py
│   │   ├── redis_client.py        # Redis 客户端
│   │   ├── cache.py              # 缓存服务
│   │   └── cost_calculator.py    # 成本计算器
│   ├── schemas/                   # Pydantic 模式
│   │   ├── __init__.py
│   │   ├── chat.py                # 聊天请求/响应
│   │   ├── router.py              # 路由相关
│   │   ├── cost.py                # 成本相关
│   │   └── provider.py           # Provider 相关
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       ├── logging.py             # 日志配置
│       └── encryption.py         # 加密工具
├── frontend/                      # React 前端
│   ├── public/
│   ├── src/
│   │   ├── components/            # 通用组件
│   │   ├── pages/                 # 页面
│   │   │   ├── Dashboard/         # 仪表盘
│   │   │   ├── Providers/         # Provider 配置
│   │   │   ├── Routing/           # 路由配置
│   │   │   ├── Cost/              # 成本分析
│   │   │   └── ApiDocs/           # API 文档
│   │   ├── api/                   # API 客户端
│   │   ├── types/                 # TypeScript 类型
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── tests/                         # 测试
│   ├── __init__.py
│   ├── conftest.py                # pytest 配置
│   ├── unit/                      # 单元测试
│   └── integration/               # 集成测试
├── migrations/                    # 数据库迁移
│   ├── __init__.py
│   └── versions/
│       └── 001_init.py           # 初始化表
├── config/                        # 配置文件
│   ├── config.yaml.example
│   └── config.yaml
├── docker/                        # Docker 配置
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── scripts/                       # 脚本
│   ├── init_db.py                 # 初始化数据库
│   └── init_redis.py              # 初始化 Redis
├── requirements.txt               # Python 依赖
├── pyproject.toml                 # 项目配置
├── pytest.ini                     # pytest 配置
├── README.md
└── .gitignore
```

---

## 实施任务清单

### 第一阶段：项目初始化与基础设施

#### 1.1 后端项目初始化
- [x] 创建 Python 项目目录结构
- [x] 配置 `requirements.txt` (FastAPI, SQLAlchemy, Redis, httpx, pytest 等)
- [x] 配置 `pyproject.toml`
- [x] 配置 `pytest.ini`
- [x] 创建 `.env.example` 配置模板
- [x] 配置日志系统 (src/utils/logging.py)
- [x] 配置加密工具 (src/utils/encryption.py)

#### 1.2 前端项目初始化
- [ ] 使用 Vite 创建 React + TypeScript 项目
- [ ] 安装依赖 (Ant Design, Recharts, React Router, axios)
- [ ] 配置路由结构
- [ ] 配置 API 基础路径和拦截器

#### 1.3 数据库设计
- [ ] 创建数据库表结构定义 (src/models/)
  - [ ] users (用户表)
  - [ ] api_keys (API Key 表)
  - [ ] providers (Provider 配置表)
  - [ ] provider_models (模型配置表)
  - [ ] routing_decisions (路由决策记录表)
  - [ ] routing_switch_history (路由开关历史表)
  - [ ] cost_records (成本记录表)
  - [ ] audit_logs (审计日志表)
- [ ] 创建数据库迁移脚本 (migrations/)
- [ ] 创建数据库会话管理 (src/db/session.py)

#### 1.4 Redis 配置
- [ ] 定义 Redis 数据结构 (src/services/redis_client.py)
  - [ ] 路由开关状态
  - [ ] 内容分析缓存
  - [ ] 实时性能评分
  - [ ] 负载均衡状态
  - [ ] 成本实时统计
  - [ ] 限流计数器
  - [ ] API Key 缓存

#### 1.5 配置管理
- [ ] 创建配置类 (src/config/settings.py)
  - [ ] 数据库配置
  - [ ] Redis 配置
  - [ ] Provider API Key 配置
  - [ ] 路由开关配置
- [ ] 创建配置验证

---

### 第二阶段：Provider 抽象层

#### 2.1 Provider 基类
- [ ] 定义 IProvider 接口 (src/providers/base.py)
  - [ ] `chat_completion()` 方法
  - [ ] `stream_chat_completion()` 方法
  - [ ] `get_model_list()` 方法
  - [ ] `health_check()` 方法

#### 2.2 Provider 实现
- [ ] OpenAI Provider (src/providers/openai.py)
  - [ ] 实现聊天完成 API
  - [ ] 实现流式响应
  - [ ] 实现 Token 计算
- [ ] Anthropic Provider (src/providers/anthropic.py)
  - [ ] 实现聊天完成 API
  - [ ] 实现流式响应
  - [ ] 实现 Token 计算

#### 2.3 Provider 工厂
- [ ] 实现动态 Provider 创建 (src/providers/factory.py)
- [ ] 实现 Provider 注册机制

#### 2.4 单元测试
- [ ] Provider 基类测试
- [ ] OpenAI Provider 测试 (mock)
- [ ] Anthropic Provider 测试 (mock)

---

### 第三阶段：Gateway Orchestrator

#### 3.1 路由开关状态管理
- [ ] 实现内存状态管理 (RoutingSwitchState)
- [ ] 实现 Redis 状态持久化
- [ ] 实现延迟生效机制 (10秒延迟)
- [ ] 实现冷却时间控制 (5分钟)

#### 3.2 路由控制 API
- [ ] POST /api/v1/router/toggle (切换开关)
- [ ] GET /api/v1/router/status (查询状态)
- [ ] GET /api/v1/router/history (历史记录)
- [ ] GET /api/v1/router/metrics (监控指标)

#### 3.3 权限控制
- [ ] 实现超级管理员权限验证
- [ ] 实现 API Key 认证中间件

#### 3.4 数据模型
- [ ] 创建路由开关历史模型
- [ ] 创建路由开关统计模型

---

### 第四阶段：核心路由模块

#### 4.1 基础路由逻辑
- [ ] 实现基于请求内容的简单路由
- [ ] 实现固定规则路由配置
- [ ] 实现轮询负载均衡
- [ ] 实现简单故障重试

#### 4.2 路由决策引擎
- [ ] 实现路由决策算法
- [ ] 实现规则引擎 (基于正则匹配)
- [ ] 实现负载均衡算法 (加权轮询)

#### 4.3 数据模型
- [ ] 创建路由决策模型
- [ ] 创建自定义路由规则模型
- [ ] 创建 Provider 性能历史模型

#### 4.4 路由 API
- [ ] POST /api/v1/chat/completions (主要 API)
- [ ] GET /api/v1/models (获取模型列表)
- [ ] GET /api/v1/routing/rules (获取路由规则)
- [ ] POST /api/v1/routing/rules (创建路由规则)

---

### 第五阶段：成本监控模块

#### 5.1 成本计算引擎
- [ ] 实现 Token 计数器
- [ ] 实现成本计算逻辑 (按 Provider 模型定价)
- [ ] 实现成本归因 (用户、模型等维度)

#### 5.2 实时成本追踪
- [ ] 实现 Redis 实时成本累积
- [ ] 实现 PostgreSQL 成本记录持久化
- [ ] 实现成本数据聚合

#### 5.3 成本 API
- [ ] GET /api/v1/cost/current (当前成本)
- [ ] GET /api/v1/cost/daily (日成本统计)
- [ ] GET /api/v1/cost/by-model (按模型统计)
- [ ] GET /api/v1/cost/by-user (按用户统计)

#### 5.4 数据模型
- [ ] 创建成本记录模型
- [ ] 创建成本预算模型

---

### 第六阶段：后端 API 集成

#### 6.1 中间件
- [ ] 认证中间件 (API Key 验证)
- [ ] 限流中间件 (Redis 计数器)
- [ ] 请求日志中间件
- [ ] 错误处理中间件

#### 6.2 API 路由注册
- [ ] 注册聊天完成 API
- [ ] 注册路由控制 API
- [ ] 注册成本 API
- [ ] 注册 Provider 管理 API

#### 6.3 API 文档
- [ ] 集成 Swagger/OpenAPI 文档
- [ ] 配置 API 文档页面

---

### 第七阶段：前端 - 基础架构

#### 7.1 布局与导航
- [ ] 创建主布局组件
- [ ] 创建侧边栏导航
- [ ] 创建顶部导航栏
- [ ] 配置路由 (React Router)

#### 7.2 API 客户端
- [ ] 创建 axios 实例
- [ ] 配置请求/响应拦截器
- [ ] 实现 API Key 认证
- [ ] 创建 API 服务模块

#### 7.3 通用组件
- [ ] Loading 组件
- [ ] Error 组件
- [ ] Card 组件
- [ ] Table 组件
- [ ] Chart 组件 (基于 Recharts)
- [ ] Modal 组件
- [ ] Form 组件封装

---

### 第八阶段：前端 - 管理控制台

#### 8.1 仪表盘首页 (Dashboard)
- [ ] 系统概览卡片
  - [ ] 活跃会话数
  - [ ] 平均响应时间
  - [ ] 路由准确率
  - [ ] 系统健康度
- [ ] 路由控制面板
  - [ ] 开关状态显示
  - [ ] 开关切换按钮
  - [ ] 模型分布饼图
- [ ] 性能监控
  - [ ] 响应时间趋势图
- [ ] 成本状态
  - [ ] 今日成本
  - [ ] 成本趋势图
  - [ ] 预算使用进度

#### 8.2 Provider 配置页面
- [ ] Provider 列表
- [ ] 添加/编辑 Provider
  - [ ] Provider 名称
  - [ ] API Key 输入
  - [ ] 基础 URL 配置
  - [ ] 区域选择
  - [ ] 超时配置
- [ ] Provider 状态显示
- [ ] 模型列表配置
- [ ] Provider 健康检查

#### 8.3 路由配置页面
- [ ] 路由开关控制
  - [ ] 开/关按钮
  - [ ] 状态历史
  - [ ] 冷却时间显示
- [ ] 路由规则列表
  - [ ] 规则名称
  - [ ] 规则类型
  - [ ] 优先级
  - [ ] 启用状态
- [ ] 添加/编辑路由规则
  - [ ] 条件配置
  - [ ] 动作配置
- [ ] 默认模型配置
- [ ] 负载均衡权重配置

#### 8.4 成本分析页面
- [ ] 成本概览
  - [ ] 今日/本周/本月成本
  - [ ] 成本趋势图
- [ ] 按模型成本分析
  - [ ] 成本柱状图
  - [ ] 成本占比
- [ ] 按用户成本分析
- [ ] 成本预算设置
- [ ] 成本预警配置

---

### 第九阶段：前端 - 开发者门户

#### 9.1 API 文档页面
- [ ] Swagger UI 集成
- [ ] API 端点列表
- [ ] 请求/响应示例
- [ ] 错误码说明

#### 9.2 快速开始指南
- [ ] 获取 API Key 步骤
- [ ] 选择模型说明
- [ ] 发送请求示例
  - [ ] Python 示例
  - [ ] JavaScript 示例
  - [ ] cURL 示例

#### 9.3 API 测试工具
- [ ] 在线 API 测试器
- [ ] 请求参数输入
- [ ] 响应显示
- [ ] 历史请求记录

#### 9.4 监控面板
- [ ] API 调用统计
- [ ] 成功/失败率
- [ ] 平均延迟
- [ ] Token 使用量

---

### 第十阶段：部署配置

#### 10.1 Docker 配置
- [ ] 创建后端 Dockerfile
- [ ] 创建前端 Dockerfile
- [ ] 配置 Nginx 反向代理

#### 10.2 Docker Compose 配置
- [ ] 配置后端服务
- [ ] 配置前端服务
- [ ] 配置 PostgreSQL 服务
- [ ] 配置 Redis 服务
- [ ] 配置网络和卷

#### 10.3 部署脚本
- [ ] 创建初始化脚本 (scripts/)
- [ ] 创建部署脚本
- [ ] 创建环境变量模板

---

### 第十一阶段：测试与文档

#### 11.1 后端测试
- [ ] Provider 适配器单元测试
- [ ] Gateway Orchestrator 单元测试
- [ ] 路由 Agent 单元测试
- [ ] 成本 Agent 单元测试
- [ ] API 集成测试
- [ ] 端到端测试

#### 11.2 前端测试
- [ ] 组件单元测试 (Vitest)
- [ ] 集成测试
- [ ] E2E 测试 (Playwright)

#### 11.3 文档
- [ ] README.md 更新
- [ ] API 文档完善
- [ ] 部署文档
- [ ] 配置说明文档

---

## 关键文件清单

### 后端关键文件
| 文件 | 描述 |
|------|------|
| `src/main.py` | FastAPI 应用入口 |
| `src/config/settings.py` | 配置管理 |
| `src/providers/base.py` | Provider 基类 |
| `src/providers/openai.py` | OpenAI Provider |
| `src/providers/anthropic.py` | Anthropic Provider |
| `src/providers/factory.py` | Provider 工厂 |
| `src/agents/gateway_orchestrator.py` | 网关编排器 |
| `src/agents/routing_agent.py` | 路由 Agent |
| `src/agents/cost_agent.py` | 成本 Agent |
| `src/api/v1/chat.py` | 聊天 API |
| `src/api/v1/router.py` | 路由控制 API |
| `src/api/v1/cost.py` | 成本 API |
| `src/models/*.py` | 数据模型 |
| `src/schemas/*.py` | Pydantic 模式 |

### 前端关键文件
| 文件 | 描述 |
|------|------|
| `frontend/src/App.tsx` | 应用根组件 |
| `frontend/src/main.tsx` | 应用入口 |
| `frontend/src/api/` | API 客户端 |
| `frontend/src/components/` | 通用组件 |
| `frontend/src/pages/Dashboard/` | 仪表盘页面 |
| `frontend/src/pages/Providers/` | Provider 配置页面 |
| `frontend/src/pages/Routing/` | 路由配置页面 |
| `frontend/src/pages/Cost/` | 成本分析页面 |
| `frontend/src/pages/ApiDocs/` | API 文档页面 |

---

## 验收标准

### 后端验收
- [ ] OpenAI Provider 可正常调用
- [ ] Anthropic Provider 可正常调用
- [ ] 路由开关可正常切换
- [ ] 路由决策延迟 < 50ms
- [ ] 成本计算准确率 > 99.9%
- [ ] API 响应时间 P95 < 200ms
- [ ] 单元测试覆盖率 > 80%

### 前端验收
- [ ] 仪表盘正常显示
- [ ] Provider 配置功能可用
- [ ] 路由配置功能可用
- [ ] 成本数据正确展示
- [ ] API 文档可访问
- [ ] 在线 API 测试工具可用
- [ ] 响应式设计在移动端可用

### 集成验收
- [ ] Docker Compose 一键启动
- [ ] 端到端流程测试通过
- [ ] 负载测试 > 1000 QPS
- [ ] 成本追踪数据完整
- [ ] 路由历史记录完整

---

## 验证步骤

### 1. 本地开发环境启动
```bash
# 1. 启动依赖服务 (PostgreSQL, Redis)
docker-compose up -d postgres redis

# 2. 初始化数据库
python scripts/init_db.py

# 3. 启动后端
cd src && uvicorn main:app --reload --port 8000

# 4. 启动前端
cd frontend && npm run dev

# 5. 访问
# - 后端 API: http://localhost:8000
# - API 文档: http://localhost:8000/docs
# - 前端: http://localhost:5173
```

### 2. API 测试
```bash
# 1. 测试 Provider 健康检查
curl http://localhost:8000/api/v1/providers/health

# 2. 测试聊天完成
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# 3. 测试路由开关切换
curl -X POST http://localhost:8000/api/v1/router/toggle \
  -H "Authorization: Bearer ADMIN_API_KEY"

# 4. 测试成本查询
curl http://localhost:8000/api/v1/cost/current
```

### 3. 完整部署测试
```bash
# 启动所有服务
docker-compose up -d

# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

---

## 风险与依赖

### 技术风险
1. **Provider API 变更** - 使用抽象层隔离，定期检查 API 变更
2. **路由算法效果** - 先实现简单规则，后续可迭代优化
3. **性能瓶颈** - 使用缓存、连接池优化，做好性能测试

### 外部依赖
- OpenAI API Key
- Anthropic API Key
- PostgreSQL 15+
- Redis 7+

---

## 后续优化方向 (Stage 2+)

- 智能内容分析 (意图识别、复杂度评分)
- 动态负载均衡 (基于实时性能)
- 故障自动转移
- 增强安全引擎 (TLS、RBAC、审计日志)
- Kubernetes 部署配置
- Prometheus + Grafana 监控
