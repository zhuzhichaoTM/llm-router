# LLM Router

智能多模型 API 网关 - 一个基于 FastAPI 的 LLM 路由系统，支持多个 LLM 提供商的智能路由、成本监控和负载均衡。

## 功能特性

- **智能路由**: 基于内容分析和规则的智能请求路由
- **多提供商支持**: 支持 OpenAI、Anthropic 等多个 LLM 提供商
- **负载均衡**: 支持加权轮询、最小延迟等多种负载均衡策略
- **成本监控**: 实时追踪和统计 API 调用成本
- **路由开关**: 支持安全路由开关切换，带有延迟生效和冷却机制
- **认证授权**: API Key 认证和基于角色的访问控制
- **限流保护**: 基于 Redis 的灵活限流机制

## 项目结构

```
llm-router/
├── src/                          # Python 后端源码
│   ├── config/                   # 配置管理
│   ├── providers/                # Provider 适配器
│   ├── agents/                   # Agent 实现
│   ├── api/v1/                  # v1 API 路由
│   ├── models/                  # 数据模型
│   ├── db/                      # 数据库
│   ├── services/                # 业务服务
│   ├── schemas/                 # Pydantic 模式
│   └── utils/                   # 工具函数
├── frontend/                    # React 前端 (待实现)
├── docker/                      # Docker 配置
├── scripts/                     # 脚本
├── tests/                       # 测试
└── requirements.txt             # Python 依赖
```

## 快速开始

### 方式一：使用启动脚本（推荐）

#### Docker 完整部署
```bash
# 一键启动所有服务（PostgreSQL, Redis, Backend, Frontend）
./scripts/start.sh
```

#### 本地开发环境
```bash
# 使用本地 Python 运行后端
./scripts/dev.sh
```

### 方式二：手动启动

#### 1. 环境要求

- Python 3.11+
- uv（推荐的 Python 包管理器）
- PostgreSQL 15+
- Redis 7+

#### 2. 安装 uv（如未安装）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 3. 同步依赖

```bash
uv sync
```

#### 4. 配置环境变量

复制 `.env.example` 到 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必要的环境变量：

```env
# Application
APP_NAME=LLM Router
APP_ENV=development
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://llm_router:llm_router_password@localhost:5432/llm_router

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
SECRET_KEY=your-secret-key
ADMIN_API_KEY=your-admin-api-key
API_KEY_SALT=your-salt

# Providers
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

#### 5. 启动依赖服务

使用 Docker Compose 启动 PostgreSQL 和 Redis：

```bash
docker-compose up -d postgres redis
```

#### 6. 初始化数据库

```bash
uv run scripts/init_db.py
```

这将创建数据库表并初始化默认数据（包括管理员用户和示例提供商配置）。

#### 7. 运行测试（可选）

```bash
uv run scripts/test_basic.py
```

#### 8. 启动服务

```bash
uv run uvicorn src.main:app --reload --port 8000
```

服务将在 `http://localhost:8000` 启动。

#### 9. 访问 API 文档

打开浏览器访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

## API 使用示例

### 聊天完成

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### 获取模型列表

```bash
curl http://localhost:8000/api/v1/chat/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 切换路由开关

```bash
curl -X POST http://localhost:8000/api/v1/router/toggle \
  -H "Authorization: Bearer YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "value": false,
    "reason": "Maintenance"
  }'
```

### 查看成本统计

```bash
curl http://localhost:8000/api/v1/cost/current \
  -H "Authorization: Bearer YOUR_ADMIN_API_KEY"
```

## Docker 部署

### 使用 Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 单独构建并运行后端

```bash
docker build -f docker/Dockerfile.backend -t llm-router-backend .
docker run -p 8000:8000 llm-router-backend
```

## API 端点

### 聊天 API

- `POST /api/v1/chat/completions` - 聊天完成
- `GET /api/v1/chat/models` - 获取模型列表

### 路由控制 API

- `GET /api/v1/router/status` - 获取路由状态
- `POST /api/v1/router/toggle` - 切换路由开关
- `GET /api/v1/router/history` - 获取切换历史
- `GET /api/v1/router/metrics` - 获取路由指标
- `GET /api/v1/router/rules` - 获取路由规则列表
- `POST /api/v1/router/rules` - 创建路由规则

### 成本 API

- `GET /api/v1/cost/current` - 获取当前成本
- `GET /api/v1/cost/daily` - 获取每日成本
- `GET /api/v1/cost/summary` - 获取成本摘要
- `GET /api/v1/cost/by-model` - 按模型获取成本
- `GET /api/v1/cost/by-user` - 按用户获取成本

### Provider 管理 API

- `GET /api/v1/providers` - 获取提供商列表
- `POST /api/v1/providers` - 创建提供商
- `GET /api/v1/providers/{id}` - 获取提供商详情
- `POST /api/v1/providers/{id}/health` - 健康检查
- `GET /api/v1/providers/{id}/models` - 获取提供商模型列表
- `POST /api/v1/providers/{id}/models` - 创建模型

## 配置说明

### 路由规则

路由规则支持以下条件类型：

- `regex`: 使用正则表达式匹配请求内容
- `complexity`: 基于内容复杂度匹配

支持的操作类型：

- `use_model`: 使用指定模型
- `use_provider`: 使用指定提供商

### Provider 配置

支持以下 Provider 类型：

- `openai`: OpenAI API
- `anthropic`: Anthropic API
- `custom`: 自定义 Provider

## 开发指南

### 添加新的 Provider

1. 在 `src/providers/` 下创建新的 Provider 类，继承 `IProvider`
2. 在 `src/providers/factory.py` 中注册新 Provider
3. 实现所有必需的方法

### 添加新的路由策略

1. 在 `src/agents/routing_agent.py` 中添加新的路由方法
2. 更新 `RoutingMethod` 枚举
3. 实现对应的路由逻辑

## 测试

运行基础功能测试：

```bash
uv run scripts/test_basic.py
```

运行单元测试：

```bash
uv run pytest tests/ -v
```

## 许可证

MIT License
