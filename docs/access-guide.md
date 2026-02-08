# 访问指南

## Web 界面访问

### 本地开发环境

#### 1. 启动服务

```bash
# 方式一：使用 Docker Compose（推荐）
docker-compose up -d postgres redis

# 方式二：使用开发脚本
./scripts/dev.sh

# 方式三：手动启动后端
uv run python -m uvicorn core.src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 访问 Web 界面

- **后端管理 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **管理仪表盘**: http://localhost:8000/

### 开发者门户

#### 1. 快速开始

1. **获取 API Key**
   ```bash
   # 方式一：使用管理员 API Key（测试环境）
   export ADMIN_API_KEY=your-admin-api-key

   # 方式二：创建新 API Key
   curl -X POST http://localhost:8000/api/v1/api-keys \
     -H "Authorization: Bearer $ADMIN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "测试密钥",
       "user_id": 1,
       "is_active": true
     }'
   ```

2. **查看支持的模型列表**
   ```bash
   curl http://localhost:8000/api/v1/chat/models \
     -H "Authorization: Bearer $ADMIN_API_KEY"
   ```

3. **发送测试消息**
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/completions \
     -H "Authorization: Bearer $ADMIN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [
         {"role": "user", "content": "Hello, how are you?"}
       ],
       "temperature": 0.7,
       "stream": false
     }'
   ```

#### 4. **启用流式响应**
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/completions \
     -H "Authorization: Bearer $ADMIN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [
         {"role": "user", "content": "Hello, how are you?"}
       ],
       "stream": true
     }' \
     --no-buffer
   ```

### 管理控制台 API

#### 路由状态
```bash
# 查看路由状态
curl http://localhost:8000/api/v1/router/status \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

**响应示例：**
```json
{
  "enabled": true,
  "pending": false,
  "can_toggle": true,
  "pending_switch": null,
  "pending_value": false,
  "scheduled_at": null,
  "cooldown_until": null
}
```

#### 切换路由开关
```bash
curl -X POST http://localhost:8000/api/v1/router/toggle \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "value": false,
    "reason": "维护中",
    "force": false
  }'
```

#### 路由规则管理
```bash
# 列出路由规则
curl http://localhost:8000/api/v1/router/rules \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

# 创建路由规则
curl -X POST http://localhost:8000/api/v1/router/rules \
  -H "Authorization: Bearer $ADMIN_API_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "代码生成规则",
    "description": "路由代码相关请求到 GPT-4",
    "condition_type": "regex",
    "condition_value": "code|programming|function",
    "action_type": "use_model",
    "action_value": "gpt-4",
    "priority": 10,
    "is_active": true
  }'
```

#### 删除路由规则
```bash
curl -X DELETE http://localhost:8000/api/v1/router/rules/{rule_id} \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

### Provider 管理 API

#### 查看 Providers
```bash
curl http://localhost:8000/api/v1/providers \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

**响应示例：**
```json
[
  {
    "id": 1,
    "name": "openai",
    "provider_type": "openai",
    "base_url": "https://api.openai.com/v1",
    "status": "active",
    "priority": 100,
    "weight": 100,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### 创建 Provider
```bash
curl -X POST http://localhost:8000/api/v1/providers \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "openai-prod",
    "provider_type": "openai",
    "api_key": "your-openai-api-key",
    "base_url": "https://api.openai.com/v1",
    "priority": 100,
    "weight": 100,
    "status": "active"
  }'
```

#### Provider 健康检查
```bash
curl -X POST http://localhost:8000/api/v1/providers/{provider_id}/health \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

**响应示例：**
```json
{
  "healthy": true,
  "providers": [
    {
      "provider_id": 1,
      "provider_name": "openai",
      "is_healthy": true,
      "provider_name": "openai",
      "latency_ms": 150,
      "error_message": null
    }
  ]
}
```

#### 查看 Provider 模型
```bash
curl http://localhost:8000/api/v1/providers/{provider_id}/models \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

#### 创建模型配置
```bash
curl -X POST http://localhost:8000/api/v1/providers/{provider_id}/models \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "gpt-4",
    "name": "GPT-4",
    "context_window": 8192,
    "input_price_per_1k": 0.03,
    "output_price_per_1k": 0.06,
    "is_active": true
  }'
```

### 成本追踪 API

#### 获取当前成本
```bash
curl http://localhost:8000/api/v1/cost/current \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

**响应示例：**
```json
{
  "daily": {
    "cost": 12.50,
    "tokens": 5240
  },
  "total": 1234.50
}
```

#### 获取每日成本
```bash
curl http://localhost:8000/api/v1/cost/daily?days=7 \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

**响应示例：**
```json
[
  {
    "date": "2024-01-01",
    "cost": 12.50,
    "tokens": 5240
  }
]
```

#### 按模型获取成本
```bash
curl http://localhost:8000/api/v1/cost/by-model \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

#### 按用户获取成本
```bash
curl http://localhost:8000/api/v1/cost/by-user \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

#### 成本摘要
```bash
curl http://localhost:8000/api/v1/cost/summary?start_date=2024-01-01&end_date=2024-01-07 \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

**响应示例：**
```json
{
  "period": "2024-01-01 to 2024-01-07",
  "total_cost": 87.50,
  "input_cost": 35.00,
  "output_cost": 52.50,
  "total_tokens": 35100,
  "input_tokens": 14040,
  "output_tokens": 21060,
  "total_requests": 585
}
```

### 测试和监控 API

#### 系统健康检查
```bash
curl http://localhost:8000/health
```

**响应示例：**
```json
{
  "status": "healthy",
  "app": "LLM Router",
  "version": "1.0.0",
  "dependencies": {
    "database": "connected",
    "redis": "connected",
    "providers": {
      "openai": "healthy",
      "anthropic": "unhealthy"
    }
  },
  "last_check": "2024-01-01T12:00:00Z",
  "check_interval": 30
}
```

### 错误码说明

| HTTP Code | 说明 | 示例例 |
|----------|------|--------|
| 200 | 请求成功 | 成功的 API 调用 |
| 400 | 请求参数错误 | 缺少必需的参数 |
| 401 | 未授权 | 缺少或错误的 Authorization header |
| 403 | 禁止访问 | 权限不足 |
| 404 | 未找到 | 资源不存在 |
| 429 | 太多请求 | 超过速率限制 |
| 500 | 服务器错误 | 服务器内部错误 |
| 502 | 网关错误 | 路由配置错误 |
| 503 | 服务不可用 | 智能路由已关闭 |
| 504 | 网关超时 | 路由切换失败 |

### WebSocket API

#### 连接 WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    console.log('Connected to WebSocket');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onclose = () => {
    console.log('Disconnected from WebSocket');
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

#### 事件类型

- `chat.message.new` - 新聊天消息
- `chat.chunk.received` - 收到流式块
- `chat.complete` - 聊天完成
- `provider.health.updated` - Provider 健康状态更新
- `routing.decision` - 路由决策事件

#### 示例：接收流式响应

```javascript
ws.send(JSON.stringify({
  "action": "subscribe",
  "topics": ["chat.chunk.received", "provider.health.updated"]
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "chat.chunk.received") {
    console.log(`Chunk: ${data.content}`);
  }
};
```

---

## 前端项目结构

```
frontend/
├── src/
│   ├── components/       # React 组件
│   ├── pages/           # 页面组件
│   ├── api/             # API 客户端
│   ├── store/            # 状态管理
│   ├── hooks/            # 自定义 hooks
│   ├── types/            # TypeScript 类型
│   ├── utils/            # 工具函数
│   └── styles/           # 样式
├── public/                # 静态资源
├── package.json        # 依赖配置
└── tsconfig.json           # TypeScript 配置
```

---

## Docker 部署

### 构建和运行

#### 后端部署

```bash
# 构建镜像
docker build -f docker/Dockerfile.backend -t llm-router-backend

# 运行容器
docker run -p 8000:8000 llm-router-backend \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db \
  -e REDIS_URL=redis://localhost:6379 \
  -e SECRET_KEY=your-secret-key \
  -e ADMIN_API_KEY=your-admin-api-key
```

#### 前端部署

```bash
# 构建镜像
docker build -f docker/Dockerfile.frontend -t llm-router-frontend

# 运行容器
docker run -p 3000:80 llm-router-frontend
```

### Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 停止所有服务
docker-compose down
```

---

## 故障排除

### 后端无法启动

```bash
# 检查端口占用
lsof -ti :8000

# 检查数据库连接
psql postgresql://user:pass@localhost:5432/db -c "SELECT 1"
```

### 前端无法访问

```bash
# 检查容器运行状态
docker ps | grep llm-router

# 查看容器日志
docker logs llm-router-backend
```

### API 调用失败

```bash
# 查看后端日志
tail -n 50 logs/llm-router-backend

# 检查 Provider 健康
curl http://localhost:8000/api/v1/providers \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

---

## 性能优化建议

### 后端优化

1. **连接池管理**
   - 保持 HTTP 连接复用
   - 限制最大连接数

2. **缓存策略**
   - Redis 缓存热点数据
   - API 响应缓存

3. **异步处理**
   - 所有 I/O 操作异步
   - 流式响应避免阻塞

### 前端优化

1. **代码分割**
   - 使用代码分割
   - 按路由懒加载

2. **状态管理**
   - 使用 React Query
   - 状态持久化

3. **虚拟滚动**
   - 实现列表虚拟滚动
   - 骚懒加载图片

---

## 安全最佳实践

1. **API Key 保护**
   - 使用强密钥
   - 定期轮换密钥
   - 设置 IP 白名单

2. **数据加密**
   - 传输层 TLS 加密
   - 数据库加密存储
   - 敏感信息脱敏

3. **访问控制**
   - 实施 RBAC
   - API Key 权限检查
   - 用户权限隔离

4. **审计日志**
   - 记录所有操作
   - 定期审计日志
   - 异常检测

---

## 部分环境

### 环境变量配置

创建 `.env.local` 文件用于本地开发：

```env
# Application
APP_ENV=development
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-local-secret-key
ADMIN_API_KEY=your-local-admin-api-key
API_KEY_SALT=your-salt

# Providers
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Frontend
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

### 运行开发服务器

```bash
# 方式一：uvicorn
uv run uvicorn core.src.main:app --reload --host 0.0.0.0 --port 8000

# 方式二：docker-compose
docker-compose up -d postgres redis backend
```

---

## 下一步

1. 根据需求添加新功能
2. 优化性能和安全
3. 添加更多测试
4. 扩展前端界面
