# LLM API 网关 Agent 详细实现方案

## 目标
基于 `llm-router-product-features.md` 的核心功能需求，优化丰富 `llm-router-system-design.md` 中的各 Agent 实现，总体设计架构保持不变，详细分析每个功能点的实现方案，功能点与需求文档一一对应，充分考虑非功能需求。

---

## 一、功能点与 Agent 映射总览

| 产品功能需求 | 对应 Agent | 核心功能点 |
|------------|-----------|-----------|
| 1.1 多供应商集成 | Provider Agent | Provider 管理、API 调用、配额管理、密钥轮换 |
| 1.1 模型选择开关 | Gateway Orchestrator | 开关状态管理、冷却时间、生效延迟、状态监控 |
| 1.2 智能路由引擎 | Routing Agent | 内容分析、智能决策、负载均衡、故障转移、精细化匹配 |
| 1.3 成本控制引擎 | Cost Agent | 实时成本监控、多维度分析、智能优化、预算管理 |
| 1.4 安全监控引擎 | Security Agent | 数据安全、访问控制、审计监控、威胁检测 |
| 1.5 数据分析引擎 | Analytics Agent | 性能监控、业务分析、智能分析、告警系统 |
| 本地模型管理 | LocalModel Agent | 模型加载、GPU 调度、混合路由、本地推理 |
| 工具调用系统 | Tools Agent | 工具注册、工具发现、工具执行、工具推理 |

---

## 二、各 Agent 详细实现方案

### 2.1 Gateway Orchestrator (网关编排 Agent)

#### 功能点映射
| 产品需求功能点 | Agent 功能 | 实现方案 |
|--------------|-----------|---------|
| 模型选择开关-状态管理 | 开关控制 | 内存存储开关状态 + Redis 持久化 |
| 模型选择开关-冷却时间 | 防抖机制 | 冷却期检查（默认5分钟） |
| 模型选择开关-生效延迟 | 延迟生效 | 配置变更后10秒延迟生效 |
| 模型选择开关-权限控制 | 权限验证 | 仅超级管理员可修改 |
| 模型选择开关-状态监控 | 监控指标 | 开关切换频率、路由准确率监控 |

#### 数据结构设计

**内存数据结构**
```
RoutingSwitchState:
├── enabled: bool (开关状态)
├── last_toggle_time: timestamp (最后切换时间)
├── cooldown_seconds: int (冷却时间，默认300秒)
├── pending_change: bool|null (待生效的变更)
├── pending_time: timestamp (变更请求时间)
└── delay_seconds: int (生效延迟，默认10秒)

状态计算:
├── is_in_cooldown: 如果距离上次切换时间 < 冷却时间，则为 true
└── effective_state: 如果延迟时间已过，返回 pending_change，否则返回 enabled
```

**Redis 数据结构**
```
routing:switch (Hash)
├── enabled: bool (开关状态)
├── last_toggle: timestamp (最后切换时间)
├── pending: bool|null (待生效的变更)
└── pending_time: timestamp (变更请求时间)

routing:switch:metrics (Hash)
├── toggle_count: int (切换次数，按小时统计)
├── toggle_hour: int (统计小时)
├── routing_accuracy: float (路由准确率，最近1小时)
└── performance_impact_ms: int (性能影响，毫秒)
```

**PostgreSQL 表结构**
```sql
-- 路由开关操作记录
CREATE TABLE routing_switch_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    old_state BOOLEAN NOT NULL,
    new_state BOOLEAN NOT NULL,
    triggered_by VARCHAR(100) NOT NULL,  -- user_id 或 system
    trigger_reason VARCHAR(500),
    is_auto_trigger BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 路由开关监控统计
CREATE TABLE routing_switch_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_hour TIMESTAMP WITH TIME ZONE NOT NULL UNIQUE,
    toggle_count INTEGER DEFAULT 0,
    routing_accuracy DECIMAL(5,4) DEFAULT 0.0000,
    avg_latency_ms INTEGER,
    avg_cpu_usage_percent DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 核心算法设计

**开关切换算法**

```
切换开关请求 ─────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[1. 权限验证] ───────────────────────────────────────────────────┤
  │                                                                │
  ├─── 检查：是否为超级管理员？                                 │
  │                                                                │
  ├─ 否 ──→ 返回错误：Permission denied                           │
  │                                                                │
  └─── 是 ──→ 继续                                            │
      │                                                             │
      ▼                                                           │
[2. 冷却期检查] ──────────────────────────────────────────────────┤
  │                                                                │
  ├─── 检查：距离上次切换时间 < 冷却期（300秒）？               │
  │                                                                │
  ├─ 是 且状态不变更 ──→ 返回错误：Cooldown: Xs remaining          │
  │                                                                │
  └─── 否 ──→ 继续                                            │
      │                                                             │
      ▼                                                           │
[3. 设置延迟生效] ───────────────────────────────────────────────────┤
  │                                                                │
  ├─── 设置 pending_change = 目标状态                              │
  ├─── 设置 pending_time = 当前时间                                 │
  ├─── 记录操作历史到数据库                                      │
  └─── 启动延迟任务（10秒后生效）                                │
      │                                                             │
      ▼                                                           │
[4. 延迟生效任务] (10秒后)                                      │
      │                                                             │
      ├─── 应用 pending_change 到 enabled                               │
      ├─── 更新 last_toggle_time = 当前时间                            │
      ├─── 清除 pending_change 和 pending_time                         │
      ├─── 持久化到 Redis                                            │
      └─── 返回成功消息：Switch will enable/disable in 10s             │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘
```

**智能降级算法**

```
健康检查循环 ─────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[获取路由引擎健康状态] ─────────────────────────────────────────────────┤
  │                                                                │
  ├─── 检查项：                                                  │
  │   - 路由决策成功率                                              │
  │   - 平均响应时间                                                 │
  │   - 错误率                                                      │
  │   - CPU 使用率                                                    │
  │                                                                │
  └─── 返回 health_status:                                         │
      ├── is_degraded: bool (是否降级)                                 │
      ├── severity: str (critical/warning/normal)                         │
      └── reason: str (降级原因)                                        │
                                                                  │
[判断是否需要降级] ─────────────────────────────────────────────────┤
  │                                                                │
  ├─ is_degraded == false ──→ 不降级                            │
  │                                                                │
  └─ is_degraded == true ──→ 根据 severity 决定                │
      │                                                         │
      ├─ severity == 'critical' ──→ 立即关闭智能路由        │
      │   │                                                        │
      │   └── [执行紧急关闭]                                        │
      │       - 停止路由引擎                                         │
      │       - 使用默认路由（直连 Provider）                           │
      │       - 发送严重告警                                         │
      │                                                        │
      └─ severity == 'warning' ──→ 检查配置                     │
          │                                                     │
          └─ auto_degrade_on_warning == true ──→ 优雅降级     │
              │                                                 │
              └── [执行优雅降级]                              │
                  - 降低路由复杂度                              │
                  - 减少实时计算                                 │
                  - 发送警告告警                                 │
              │                                                 │
              └─ auto_degrade_on_warning == false ──→ 不降级    │
                  │                                                 │
                  └── 仅记录警告                                │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘
```

#### 非功能需求考虑

| 需求类型 | 实现方案 | 性能指标 |
|---------|---------|---------|
| 性能 | 开关切换 <10ms，状态检查 <1ms | 切换延迟：<10ms |
| 可靠性 | Redis 持久化 + PostgreSQL 审计日志 | 99.99% 可用性 |
| 可扩展性 | 分布式状态同步（Redis Pub/Sub） | 支持多实例 |
| 安全性 | 权限验证 + 操作审计日志 | RBAC 控制 |

---

### 2.2 Routing Agent (路由 Agent)

#### 功能点映射
| 产品需求功能点 | 子功能 | 实现方案 |
|--------------|-------|---------|
| **内容分析模块** | 意图识别 | 轻量级分类模型 + 规则引擎混合 |
| | 复杂度计算 | 多维度评分 + 机器学习模型 |
| | 场景分类 | 多标签分类 + 场景知识库 |
| | 多语言检测 | fastText + 语言置信度评分 |
| **智能决策引擎** | 实时性能评分 | 滑动窗口 + 指数衰减 |
| | 多维度成本分析 | Token 成本计算 + ROI 评估 |
| **负载均衡** | 动态负载均衡 | 加权轮询 + 动态权重调整 |
| | 故障转移 | 健康检查 + 自动切换 |
| **精细化匹配** | 任务复杂度路由 | 复杂度阈值分级路由 |
| | 内容类型路由 | 内容特征识别 + 规则匹配 |
| | 业务优先级路由 | 优先级队列 + 权重分配 |
| | 自定义路由规则 | 规则引擎 + 用户自定义规则 |
| **性能优化** | 智能队列管理 | 优先级队列 + 动态调整 |
| | 超时精细控制 | 分层超时 + 动态调整 |
| | 连接池优化 | 连接复用 + 健康检查 |

#### 数据结构设计

**PostgreSQL 表结构**
```sql
-- 意图识别模型配置
CREATE TABLE intent_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,  -- 'local', 'cloud'
    model_path VARCHAR(500),
    confidence_threshold DECIMAL(5,4) DEFAULT 0.8000,
    supported_intents TEXT[],  -- ['qa', 'creative', 'code', ...]
    performance_metrics JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 内容分析缓存
CREATE TABLE content_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    intent VARCHAR(50),
    intent_confidence DECIMAL(5,4),
    complexity_score INTEGER,
    scenarios TEXT[],
    detected_language VARCHAR(10),
    language_confidence DECIMAL(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 自定义路由规则
CREATE TABLE custom_routing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(200) NOT NULL,
    owner_id VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,  -- 'priority', 'scenario', 'complexity', 'custom'
    conditions JSONB NOT NULL,  -- 规则条件
    actions JSONB NOT NULL,      -- 路由动作
    priority INTEGER DEFAULT 0,  -- 规则优先级
    enabled BOOLEAN DEFAULT TRUE,
    match_count BIGINT DEFAULT 0,
    last_matched_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 性能评分历史
CREATE TABLE provider_performance_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    response_speed_score DECIMAL(5,4),    -- 0-1
    success_rate_score DECIMAL(5,4),       -- 0-1
    quality_score DECIMAL(5,4),           -- 0-1
    load_score DECIMAL(5,4),              -- 0-1
    cost_score DECIMAL(5,4),              -- 0-1
    total_score DECIMAL(5,4),            -- 加权总分
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 负载均衡权重配置
CREATE TABLE load_balancer_weights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    weight DECIMAL(5,4) NOT NULL,  -- 0-1, 相对权重
    region VARCHAR(50),
    min_requests_per_min INTEGER DEFAULT 0,
    max_requests_per_min INTEGER,
    current_requests_per_min INTEGER DEFAULT 0,
    weight_reason VARCHAR(200),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(provider_id, model, region)
);

-- 路由决策记录
CREATE TABLE routing_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(100),
    content_hash VARCHAR(64),
    intent VARCHAR(50),
    intent_confidence DECIMAL(5,4),
    complexity_score INTEGER,
    scenarios TEXT[],
    selected_provider VARCHAR(100),
    selected_model VARCHAR(100),
    decision_reason VARCHAR(200),
    decision_latency_ms INTEGER,
    expected_quality INTEGER,  -- 0-100
    actual_quality INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Redis 数据结构**
```python
# 实时性能评分（滑动窗口）
Key: routing:perf:{provider}:{model}
Type: Hash
Fields:
  - speed_score: float        # 响应速度评分（指数衰减）
  - success_score: float      # 成功率评分
  - quality_score: float      # 质量评分
  - load_score: float         # 负载评分
  - total_score: float        # 总分
  - request_count: int        # 请求计数
  - last_update: timestamp    # 最后更新时间

# 内容分析缓存
Key: routing:cache:content:{content_hash}
Type: Hash
Fields (TTL: 1小时):
  - intent: str
  - intent_confidence: float
  - complexity: int
  - scenarios: json_array
  - language: str
  - language_conf: float

# 自定义路由规则缓存
Key: routing:rules:{rule_id}
Type: JSON
Fields (TTL: 实时更新):
  - 条件和动作的完整 JSON 配置

# 负载均衡状态
Key: routing:lb:{provider}:{model}
Type: Hash
Fields:
  - current_requests: int     # 当前并发请求数
  - active_connections: int   # 活跃连接数
  - last_request_time: timestamp
  - health_status: str       # healthy, degraded, down

# 故障转移状态
Key: routing:failover:{provider}
Type: Hash
Fields:
  - status: str               # active, failed, recovering
  - fail_count: int           # 连续失败次数
  - last_fail_time: timestamp
  - backup_providers: json_array
```

**数据结构**
```
ContentAnalysisResult (内容分析结果)
├── intent: str (主要意图，如 qa/creative/code/translation/summary)
├── intent_confidence: float (意图置信度，0-1)
├── complexity_score: int (复杂度评分，0-100)
├── scenarios: str[] (场景列表)
├── language: str (检测到的语言代码，如 en/zh/es)
├── language_confidence: float (语言置信度，0-1)
└── metadata: dict (额外元数据)

ProviderPerformance (Provider 性能评分)
├── provider_id: str (Provider 标识)
├── model: str (模型名称)
├── response_speed_score: float (响应速度评分，权重 30%，0-1)
├── success_rate_score: float (成功率评分，权重 25%，0-1)
├── quality_score: float (质量评分，权重 25%，0-1)
├── load_score: float (负载评分，权重 20%，0-1)
├── cost_score: float (成本评分，额外考虑，0-1)
├── total_score: float (加权总分)
└── last_update: timestamp (最后更新时间)

综合评分计算公式：
total = speed_score × 0.30 + success_rate_score × 0.25 +
       quality_score × 0.25 + load_score × 0.20

其中：
- speed_score = min(1.0, 1.0 - (avg_latency_ms - 100) / 2000)
- success_rate_score = min(1.0, max(0.0, success_rate))
- load_score = max(0.0, 1.0 - load_percent / 100)

RoutingDecision (路由决策结果)
├── selected_provider: str (选中的 Provider ID)
├── selected_model: str (选中的模型)
├── reason: str (决策原因)
├── expected_quality: int (预期质量评分，0-100)
├── expected_latency_ms: int (预期延迟毫秒)
├── estimated_cost_usd: float (预估成本美元)
└── metadata: dict (额外元数据)
```

#### 核心算法设计

**1. 意图识别算法（混合模型 + 规则引擎）**

```
内容输入 ─────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[1. 检查缓存] ──────────────────────────────────────────────┤
  │                                                                │
  ├─ 命中 ──→ 返回缓存的 intent 和 confidence                    │
  │                                                                │
  └─ 未命中 ──→ 继续                                         │
      │                                                             │
      ▼                                                           │
[2. 规则引擎快速匹配] ─────────────────────────────────────────┤
  │                                                                │
  ├─── 规则模式：                                                 │
  │   │                                                          │
  │   ├─── qa: 疑问类 (what/how/why/when/where/who/which, ?)      │
  │   │                                                          │
  │   ├─── creative: 创作类 (write/create/generate/compose,       │
  │   │                  story/poem/article/essay, imagine/if) │
  │   │                                                          │
  │   ├─── code: 代码类 (write/implement/code/function/class,      │
  │   │               python/js/java/go/rust, bug/fix/debug) │
  │   │                                                          │
  │   ├─── translation: 翻译类 (translate/翻译,                    │
  │   │                  in english/chinese/spanish/french) │
  │   │                                                          │
  │   └─── summary: 摘要类 (summarize/summary/摘要,                │
  │                  in short/brief/concise)                      │
  │                                                                │
  └─── 匹配成功且置信度 > 0.95 ──→ 返回结果        │
                                                                  │
[3. 本地模型推理] ─────────────────────────────────────────────────┤
  │                                                                │
  ├─── 使用轻量级本地模型（Llama-3.2-1B）                     │
  ├─── 推理目标：<20ms                                         │
  └─── 返回 model_result (intent, confidence)                      │
                                                                  │
[4. 结果融合] ───────────────────────────────────────────────────┤
  │                                                                │
  ├─── 如果规则结果存在且置信度高 → 直接使用规则结果              │
  ├─── 如果规则结果不存在或置信度低 → 融合规则和模型结果      │
  └─── 融合策略：加权平均或优先采用模型结果                        │
                                                                  │
[5. 缓存结果] ───────────────────────────────────────────────────┤
  │                                                                │
  ├─── 写入缓存（TTL: 1小时）                                   │
  └─── 返回 (final_intent, confidence)                          │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘

组件职责：
┌───────────────────────────────────────────────────────────────────┐
│ CacheManager: 缓存层（Redis）                        │
│   - 读写缓存，TTL: 3600s                               │
│                                                            │
│ RuleEngine: 规则引擎                            │
│   - 正则模式匹配                                               │
│   - 快速响应，<1ms                                           │
│                                                            │
│ LocalModel: 轻量级本地推理                    │
│   - Llama-3.2-1B 模型                                       │
│   - 推理时间 <20ms                                           │
└───────────────────────────────────────────────────────────────────┘
```

**2. 复杂度计算算法（多维度评分）**

```
计算复杂度请求 ─────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[多维度评分] ───────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 语义复杂度 (Semantic, 权重 30%) ─────────────────┤      │
  │   │                                                          │
  │   ├─── 文本长度因素：min(1.0, len(content) / 5000)       │
  │   │                                                          │
  │   ├─── 句子数量因素：min(1.0, 句子数 / 50)             │
  │   │                                                          │
  │   ├─── 词汇多样性：类型-标记比 (TTR)                      │
  │   │                                                          │
  │   └─── 嵌套结构：min(1.0, 嵌套层级 / 5)               │
  │   └─── 综合：sum(因素) / count(因素) × 100                │
  │                                                             │
  ├─── 推理深度 (Reasoning, 权重 25%) ───────────────────┤        │
  │   │                                                          │
  │   ├─── 基础分：30                                               │
  │   │                                                          │
  │   ├─── 推理关键词计数：× 8                          │
  │   │                                                          │
  │   ├─── 多步骤指令计数：× 10                         │
  │   │                                                          │
  │   ├─── 条件逻辑计数：(if + when) × 5                      │
  │   │                                                          │
  │   ├─── 意图调整：                                         │
  │   │   - code: +15                                               │
  │   │   - qa: +10                                                 │
  │   │                                                          │
  │   └─── 综合：min(100, 基础分 + 各因素得分)           │
  │                                                             │
  ├─── 知识需求 (Knowledge, 权重 20%) ──────────────────────┤    │
  │   │                                                          │
  │   ├─── 基础分：20                                               │
  │   │                                                          │
  │   ├─── 专业领域检测：每个领域 +15 分                     │
  │   │   - medical, legal, financial, technical, scientific...    │
  │   │                                                          │
  │   ├─── 实体检测：(姓名 + 年份 + 金额) × 2              │
  │   │                                                          │
  │   └─── 外部引用检测：有 URL +10 分                           │
  │   └─── 综合：min(100, 基础分 + 各因素得分)           │
  │                                                             │
  ├─── 上下文需求 (Context, 权重 15%) ────────────────────────┤   │
  │   │                                                          │
  │   ├─── 基础分：20                                               │
  │   │                                                          │
  │   ├─── 指代词计数：× 5                           │
  │   │                                                          │
  │   ├─── 引用前文检测：有 +15 分                          │
  │   │                                                          │
  │   ├─── 对话指示：有 +10 分                              │
  │   │                                                          │
  │   └─── 历史引用：有 +20 分                           │
  │   └─── 综合：min(100, 基础分 + 各因素得分)           │
  │                                                             │
  └─── 特殊任务 (Special, 权重 10%) ───────────────────────────┤       │
      │                                                          │
      ├─── 基础分：10                                               │
      │                                                          │
      ├─── 代码相关：有 +30，多代码块 +20               │
      │                                                          │
      ├─── 数学计算：有 +25                                      │
      │                                                          │
      ├─── 翻译任务：意图 == translation 时 +20                  │
      └─── 综合：min(100, 基础分 + 各因素得分)           │
                                                                  │
[加权计算] ───────────────────────────────────────────────────────┤
  │                                                                │
  total = Semantic × 0.30 + Reasoning × 0.25 +               │
          Knowledge × 0.20 + Context × 0.15 +                    │
          Special × 0.10                                            │
  result = int(min(100, max(0, total)))                            │
  return result                                                      │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘
```

**3. 场景分类算法（多标签分类）**

```
内容输入 ─────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[场景匹配] ───────────────────────────────────────────────────┤
  │                                                                │
  ├─── 遍历所有场景配置：                                         │
  │   │                                                          │
  │   ├─── office_assistant:                                      │
  │   │   - keywords: [email, schedule, calendar, meeting, reminder] │
  │   │   - model_preference: efficient (优先经济型)        │
  │   │                                                          │
  │   ├─── content_creation:                                       │
  │   │   - keywords: [write, create, article, blog, social media]│
  │   │   - model_preference: creative (优先创造力)        │
  │   │                                                          │
  │   ├─── tech_development:                                      │
  │   │   - keywords: [code, debug, api, database, deploy]   │
  │   │   - model_preference: technical (优先技术能力)    │
  │   │                                                          │
  │   ├─── education:                                            │
  │   │   - keywords: [teach, explain, learn, tutorial, lesson]│
  │   │   - model_preference: balanced (平衡型)            │
  │   │                                                          │
  │   ├─── customer_service:                                      │
  │   │   - keywords: [help, support, issue, problem, resolve]  │
  │   │   - model_preference: empathetic (优先共情能力)   │
  │   │                                                          │
  │   └─── research:                                             │
  │       - keywords: [analyze, study, research, data, report] │
  │       - model_preference: high_quality (高质量)      │
  │                                                                │
  ├─── 对每个场景：                                               │
  │   │                                                          │
  │   ├─── 计算关键词匹配数                                        │
  │   │                                                          │
  │   └─── 计算置信度：min(1.0, 匹配数 / 关键词数)   │
  │                                                                │
  └─── 按置信度排序，返回场景列表                             │
                                                                  │
────────────────────────────────────────────────────────────────────┘

输出格式：
[(scenario_name, confidence), ...]
- 按置信度从高到低排序
- 支持多标签（一个内容可属于多个场景）
```

**4. 多语言检测算法**

```
内容输入 ─────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[使用 fastText 模型检测] ───────────────────────────────────────┤
  │                                                                │
  ├─── 加载模型：lid.176.bin（预训练的语言识别模型）           │
  ├─── 预处理：移除换行符，处理内容                           │
  └─── 预测：获取 top-1 预测结果                            │
      ├─── 返回：labels[0], probs[0]                         │
      │   - labels[0]: 预测的语言代码 (如 en/zh/es/fr) │
      │   - probs[0]: 预测置信度 (0-1)                     │
                                                                  │
[语言映射] ───────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── en → English                                              │
  ├─── zh → Chinese                                              │
  ├─── es → Spanish                                               │
  ├─── fr → French                                                │
  ├─── de → German                                                │
  ├─── ja → Japanese                                               │
  ├─── ko → Korean                                                │
  ├─── ru → Russian                                               │
  ├─── ar → Arabic                                                │
  └─── pt → Portuguese                                            │
                                                                  │
返回：(language_code, confidence)                                    │
  - language_code: 如 'en', 'zh'                                │
  - confidence: 置信度 0-1                                    │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘

检测特点：
- 基于 fastText 快速文本分类
- 支持 176 种语言识别
- 推理时间：<5ms
- 置信度评估模型预测的可靠性
```

**5. 智能决策引擎（性能评分 + 成本考虑）**

```
路由决策请求 ─────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[1. 过滤可用 Provider] ───────────────────────────────────────────┤
  │                                                                │
  ├─── 检查条件：                                                  │
  │   - 复杂度与模型能力匹配                                    │
  │   - 预算限制                                                 │
  │   - Provider 健康状态                                       │
  │                                                                │
  └─── 返回 candidates 列表                                        │
      │                                                             │
      ▼                                                           │
[2. 获取实时性能评分] ─────────────────────────────────────────┤
  │                                                                │
  └─── 对每个候选 Provider：                                          │
      └─── 查询 performance_monitor.get_score(provider_id, model)    │
                                                                  │
[3. 应用自定义路由规则] ─────────────────────────────────────────┤
  │                                                                │
  ├─── 检查是否有自定义规则匹配                                   │
  ├─── 优先级排序规则                                               │
  └─── 应用第一个匹配的规则 → 返回决策                             │
                                                                  │
[4. 综合评分决策] ────────────────────────────────────────────┤
  │                                                                │
  ├─── 基础权重配置：                                              │
  │   - performance: 0.40 (性能，权重 40%)                        │
  │   - cost: 0.25 (成本，权重 25%)                             │
  │   - quality: 0.20 (质量，权重 20%)                           │
  │   - latency: 0.15 (延迟，权重 15%)                           │
  │                                                                │
  ├─── 根据任务复杂度动态调整权重：                                  │
  │   ├─── 复杂度 > 80 → quality: 0.40, cost: 0.15           │
  │   ├─── 复杂度 < 50 → cost: 0.40, quality: 0.15             │
  │                                                                │
  ├─── 根据用户优先级动态调整权重：                                  │
  │   ├─── critical → quality: 0.45, cost: 0.10                    │
  │   ├─── low → cost: 0.45, quality: 0.10                        │
  │                                                                │
  └─── 计算每个候选的综合评分并选择最高分                       │
      total_score =                                                   │
          perf_score × 0.40 +                                    │
          (1 - provider.cost_score) × 0.25 +                        │
          provider.quality_score × 0.20 +                                │
          (1 - provider.latency_score) × 0.15                         │
                                                                  │
[5. 返回 RoutingDecision] ──────────────────────────────────────┤
  │                                                                │
  ├─── selected_provider: 最佳 Provider ID                           │
  ├─── selected_model: 选择的模型名称                              │
  ├─── reason: "Best overall score: X.XXX"                        │
  ├─── expected_quality: 预期质量 0-100                        │
  ├─── expected_latency_ms: 预期延迟毫秒                         │
  └─── estimated_cost_usd: 预估成本美元                         │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘
```

**6. 动态负载均衡流程（加权轮询 + 动态权重）**

```
Provider 选择请求 ────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[1. 过滤健康 Provider] ──────────────────────────────────────────────┤
  │                                                                │
  ├─── 获取所有候选 Provider                                         │
  │                                                                │
  ├─── 过滤条件：                                                  │
  │   ├─── health_status = 'healthy'                                   │
  │   └─── 未达到故障阈值                                           │
  │                                                                │
  └─── 返回健康 Provider 列表                                       │
                                                                  │
[2. 检查健康 Provider 数量] ──────────────────────────────────────────┤
  │                                                                │
  ├─── 有健康 Provider ──→ 继续                          │
  │                                                                │
  └─── 无健康 Provider ──→ [选择风险最低的]                │
      ├─── 评估失败次数                                              │
      ├─── 评估最后失败时间                                           │
      └─── 返回风险最低的 Provider                                    │
                                                                  │
[3. 根据策略选择 Provider] ──────────────────────────────────────────┤
  │                                                                │
  ├─── Adaptive（自适应，默认）                                      │
  │   │                                                          │
  │   └─── [加权随机选择]                                       │
  │       ├─── 获取每个 Provider 的动态权重                            │
  │       ├─── 总权重 = sum(所有权重)                                 │
  │       ├─── 随机数 r ∈ [0, 总权重)                             │
  │       ├─── 累积权重直到 ≥ r                                    │
  │       └─── 返回对应的 Provider                                    │
  │                                                                │
  ├─── Round Robin（轮询）                                          │
  │   │                                                          │
  │   └─── [循环轮询]                                           │
  │       ├─── 维护索引指针                                              │
  │       ├─── 每次选择下一个 Provider                                  │
  │       └─── 到达末尾后回到开头                                       │
  │                                                                │
  └─── Least Connections（最少连接）                                  │
      │                                                          │
      └─── [选择连接数最少的]                                      │
          ├─── 获取当前连接数（从 Redis）                                │
          └─── 返回连接数最少的 Provider                                │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[动态权重计算流程] ────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[获取性能数据] ────────────────────────────────────────────────────────┤
  │                                                                │
  └─── 从 Redis/Monitor 获取：                                          │
      ├─── avg_latency_ms：平均延迟                                    │
      ├─── success_rate：成功率                                         │
      ├─── cost_score：成本评分（越低越好）                             │
      └─── load_percent：负载百分比                                    │
                                                                  │
[计算各因子] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 响应时间因子（权重 30%）：                                      │
  │   └─── response_time_factor = max(0.1, 1.0 - (延迟 - 100) / 2000)   │
  │       - 延迟 100ms → 1.0                                        │
  │       - 延迟 1000ms → 0.55                                      │
  │       - 延迟 2100ms → 0.1（最小值）                              │
  │                                                                │
  ├─── 成功率因子（权重 30%）：                                        │
  │   └─── success_rate_factor = max(0.1, success_rate)                    │
  │       - 100% 成功率 → 1.0                                         │
  │       - 50% 成功率 → 0.5                                          │
  │       - 最低 0.1                                                     │
  │                                                                │
  ├─── 成本因子（权重 20%）：                                        │
  │   └─── cost_factor = max(0.1, 1.0 - cost_score)                     │
  │       - 成本评分 0（最便宜）→ 1.0                                    │
  │       - 成本评分 0.9 → 0.1                                         │
  │                                                                │
  └─── 负载因子（权重 20%）：                                          │
      └─── load_factor = max(0.1, 1.0 - load_percent / 100)             │
          - 负载 0% → 1.0                                            │
          - 负载 50% → 0.5                                            │
          - 负载 90% → 0.1（最小值）                                   │
                                                                  │
[计算最终权重] ────────────────────────────────────────────────────────┤
  │                                                                │
  └─── weight = 1.0 × (响应时间因子 ^ 0.3) ×                      │
                (成功率因子 ^ 0.3) ×                                │
                (成本因子 ^ 0.2) ×                                    │
                (负载因子 ^ 0.2)                                       │
                                                                  │
  限制到 [0.1, 1.0] 范围                                        │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[权重更新循环] ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[每 60 秒执行一次] ──────────────────────────────────────────────────┤
  │                                                                │
  ├─── 获取所有 Provider 的最新性能数据                             │
  │                                                                │
  ├─── 为每个 Provider 重新计算权重                                   │
  │                                                                │
  ├─── 更新 Redis 中的权重值                                       │
  │                                                                │
  └─── 捕获异常并记录                                              │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘
```

**7. 故障转移流程**

```
Provider 失败 ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[1. 记录失败] ────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 失败计数 + 1                                                │
  ├─── 记录失败时间戳                                              │
  │                                                                │
  └─── 检查：失败次数 >= 阈值（3 次）？                          │
                                                                  │
[2. 判断是否故障转移] ────────────────────────────────────────────┤
  │                                                                │
  ├─── 否 ──→ 暂不执行故障转移                                    │
  │                                                                │
  └─── 是 ──→ [标记为故障状态]                                  │
      ├─── 更新 Redis：                                                │
      │   └─── key: routing:failover:{provider_id}                   │
      │       ├─── status: failed                                      │
      │       ├─── fail_count: 失败次数                                 │
      │       └─── last_fail_time: 失败时间                           │
      │                                                                │
      ├─── [发送告警]                                                │
      │   ├─── 级别：CRITICAL                                         │
      │   ├─── 事件：Provider 故障转移                          │
      │   └─── 渠道：短信、邮件、企业微信                             │
      │                                                                │
      └─── [获取备用 Provider]                                        │
          ├─── 查询配置的备用 Provider 列表                             │
          ├─── 检查备用 Provider 健康状态                             │
          └─── 返回健康的备用 Provider                                    │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[Provider 成功] ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[1. 检查是否在失败列表] ───────────────────────────────────────────┤
  │                                                                │
  └─── 否 ──→ 无需处理                                            │
                                                                  │
  是 → 继续                                                      │
      │                                                             │
      ▼                                                           │
[2. 重置失败计数] ────────────────────────────────────────────────────┤
  │                                                                │
  └─── failure_counts[provider_id] = 0                                 │
                                                                  │
[3. 检查是否已恢复] ──────────────────────────────────────────────┤
  │                                                                │
  └─── 执行健康检查：                                                │
      ├─── 发送测试请求到 Provider                                      │
      ├─── 设置超时：10 秒                                             │
      └─── 等待响应                                                      │
                                                                  │
[4. 处理恢复] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 健康检查成功 ──→ [标记为恢复中]                       │
  │   ├─── 更新 Redis：                                                │
  │   │   └─── status: recovering                                    │
  │   └─── [渐进式恢复] ──→ 逐步引流                       │
  │       ├─── 初始：10% 流量                                          │
  │       ├─── 逐步增加到 25%、50%、75%、100%                           │
  │       └─── 每步间隔：60 秒                                         │
  │                                                                │
  └─── 健康检查失败 ──→ 保持故障状态                                 │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[配置参数]
┌───────────────────────────────────────────────────────────────────┐
│ FAILURE_THRESHOLD: 3 次连续失败                           │
│ RECOVERY_CHECK_INTERVAL: 60 秒                        │
│ FAILURE_TIMEOUT: 300 秒（失败超时）                         │
│ GRADUAL_RECOVERY_STEPS: [10%, 25%, 50%, 75%, 100%]         │
│ STEP_INTERVAL: 60 秒                                           │
└───────────────────────────────────────────────────────────────────┘
```

#### 非功能需求考虑

| 需求类型 | 实现方案 | 性能指标 |
|---------|---------|---------|
| 性能 | 缓存层 + 本地模型 + 并行处理 | 路由决策：<50ms |
| 可扩展性 | 规则引擎 + 动态加载 + 分片 | 支持 1000+ 规则 |
| 可靠性 | 故障转移 + 降级策略 | 故障检测：<3秒 |
| 安全性 | 输入验证 + 内容审核 | 支持敏感内容过滤 |

---

### 2.3 Provider Agent (Provider 管理 Agent)

#### 功能点映射
| 产品需求功能点 | 子功能 | 实现方案 |
|--------------|-------|---------|
| **多供应商集成** | Provider 管理 | 统一抽象层 + 适配器模式 |
| | API 调用 | LiteLLM 统一接口 |
| | 配额管理 | 实时追踪 + 预警 |
| | 密钥轮换 | 定期轮换 + 多密钥池 |
| **统一接口** | 格式转换 | 请求/响应转换器 |
| | 参数映射 | 参数映射表 |
| | 速率限制 | 自适应限流 |

#### 数据结构设计

**PostgreSQL 表结构**
```sql
-- Provider 配置
CREATE TABLE providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id VARCHAR(100) UNIQUE NOT NULL,
    provider_type VARCHAR(50) NOT NULL,  -- openai, anthropic, google, local
    provider_name VARCHAR(200),
    api_endpoint VARCHAR(500),
    config JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active',  -- active, disabled, maintenance
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Provider 模型配置
CREATE TABLE provider_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id VARCHAR(100) NOT NULL REFERENCES providers(provider_id),
    model_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    model_type VARCHAR(50),  -- chat, completion, embedding, image
    max_tokens INTEGER,
    supports_streaming BOOLEAN DEFAULT TRUE,
    supports_function_calling BOOLEAN DEFAULT FALSE,
    supports_vision BOOLEAN DEFAULT FALSE,
    cost_per_1k_input DECIMAL(10, 6),
    cost_per_1k_output DECIMAL(10, 6),
    context_length INTEGER,
    quality_score DECIMAL(5, 4),  -- 0-1
    capabilities JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'available',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API 密钥管理
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id VARCHAR(100) NOT NULL REFERENCES providers(provider_id),
    key_name VARCHAR(200),
    encrypted_key TEXT NOT NULL,  -- AES-256 加密
    key_hash VARCHAR(64) UNIQUE NOT NULL,  -- 用于标识
    status VARCHAR(20) DEFAULT 'active',
    rotation_period_days INTEGER DEFAULT 90,
    last_rotated_at TIMESTAMP WITH TIME ZONE,
    next_rotation_at TIMESTAMP WITH TIME ZONE,
    usage_count BIGINT DEFAULT 0,
    rate_limit_per_minute INTEGER,
    rate_limit_per_day INTEGER,
    current_usage_today BIGINT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 配额管理
CREATE TABLE quota_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id VARCHAR(100) NOT NULL REFERENCES providers(provider_id),
    key_id UUID REFERENCES api_keys(id),
    limit_type VARCHAR(50) NOT NULL,  -- requests, tokens, cost
    limit_period VARCHAR(50),  -- minute, hour, day, month
    limit_value BIGINT NOT NULL,
    current_usage BIGINT DEFAULT 0,
    warning_threshold DECIMAL(5, 2) DEFAULT 0.80,  -- 80%
    hard_limit BOOLEAN DEFAULT TRUE,
    reset_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Provider 健康状态
CREATE TABLE provider_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id VARCHAR(100) NOT NULL REFERENCES providers(provider_id),
    model VARCHAR(100),
    is_healthy BOOLEAN DEFAULT TRUE,
    latency_ms INTEGER,
    last_check_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    uptime_percentage DECIMAL(5, 4),
    metadata JSONB DEFAULT '{}'
);

-- 请求参数映射表
CREATE TABLE parameter_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_provider VARCHAR(100) NOT NULL,
    from_param VARCHAR(100) NOT NULL,
    to_provider VARCHAR(100) NOT NULL,
    to_param VARCHAR(100) NOT NULL,
    transformation_type VARCHAR(50),  -- direct, rename, transform, default
    transformation_rule JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Redis 数据结构**
```
provider:keys:active:{provider_id} (List)
Value: [key_id_1, key_id_2, ...]  # 活跃密钥ID列表，用于轮询

provider:key:{key_id}:usage (Hash)
├── requests_today: int (今日请求数)
├── requests_minute: int (当分钟请求数)
├── tokens_today: int (今日token数)
├── cost_today: decimal (今日成本)
└── last_reset: timestamp (最后重置时间)

provider:quota:{quota_id} (Hash)
├── current_usage: int (当前使用量)
├── warning_sent: bool (是否已发送预警)
└── limit_reached: bool (是否达到限制)

provider:rate:{key_id}:requests (String, Lua脚本控制)
Value: 请求计数（滑动窗口）

provider:health:{provider_id} (Hash, TTL: 30s)
├── is_healthy: bool
├── latency_ms: int
└── last_check: timestamp
```

**数据结构**
```
ProviderConfig (Provider 配置)
├── provider_id: str (Provider 标识)
├── provider_type: str (类型: openai/anthropic/google/local)
├── api_endpoint: str (API 端点)
├── models: dict (模型配置字典)
├── api_keys: list (API 密钥列表)
└── health_check_config: HealthCheckConfig (健康检查配置)

ModelConfig (模型配置)
├── model_name: str (模型名称)
├── max_tokens: int (最大 Token 数)
├── context_length: int (上下文长度)
├── supports_streaming: bool (支持流式)
├── supports_function_calling: bool (支持函数调用)
├── supports_vision: bool (支持视觉)
├── cost_per_1k_input: decimal (输入 Token 成本)
├── cost_per_1k_output: decimal (输出 Token 成本)
└── quality_score: float (质量评分 0-1)

APIKeyConfig (API 密钥配置)
├── key_id: str (密钥 ID)
├── key_name: str (密钥名称)
├── encrypted_key: str (加密后的密钥)
├── status: str (状态: active/deprecating/inactive)
├── rotation_period_days: int (轮换周期，默认 90 天)
├── rate_limit_per_minute: int (每分钟限流)
└── rate_limit_per_day: int (每天限流)

ProviderRequest (Provider 请求，统一格式)
├── model: str (模型名称)
├── messages: list (消息列表)
├── temperature: float (温度，默认 0.7)
├── max_tokens: int|null (最大 Token 数)
├── top_p: float|null (Top-P 采样)
├── stream: bool (是否流式)
├── tools: list|null (工具列表)
└── metadata: dict (额外元数据)

ProviderResponse (Provider 响应，统一格式)
├── id: str (响应 ID)
├── object: str (对象类型)
├── created: int (创建时间戳)
├── model: str (模型名称)
├── choices: list (选择列表)
├── usage: dict (Token 使用统计)
├── provider_id: str (Provider ID)
├── latency_ms: int (延迟毫秒)
└── metadata: dict (额外元数据)
```

#### 核心算法设计

**1. API 调用流程（统一接口 + LiteLLM）**

```
API 调用请求 ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[1. 速率限制检查] ────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 检查当前请求速率是否超过限制                                 │
  │                                                                │
  ├─── 超限 ──→ 返回 429 Too Many Requests                      │
  │                                                                │
  └─── 未超限 ──→ 继续                                        │
      │                                                             │
      ▼                                                           │
[2. 选择 API 密钥] ────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 从密钥池获取下一个可用密钥                                    │
  │   - 轮询机制                                                   │
  │   - 跳过故障/冷却中的密钥                                        │
  │   - 跳过非活跃状态的密钥                                       │
  │                                                                │
  └─── 无可用密钥 ──→ 返回错误：No available API keys           │
                                                                  │
  获取到密钥 → 继续                                            │
      │                                                             │
      ▼                                                           │
[3. 转换请求格式] ──────────────────────────────────────────────────┤
  │                                                                │
  ├─── 获取参数映射表：                                              │
  │   - 从数据库/缓存读取映射关系                                       │
  │   - 包含：参数名称映射、转换类型、转换规则                           │
  │                                                                │
  ├─── 应用参数映射：                                                │
  │   - 遍历统一格式请求的参数                                       │
  │   - 查找映射表                                                 │
  │   - 应用转换规则（如 rename、transform、default）                      │
  │                                                                │
  └─── 生成 Provider 原生格式请求                                      │
                                                                  │
[4. 调用 Provider API] ─────────────────────────────────────────────┤
  │                                                                │
  ├─── 构建 LiteLLM 请求：                                          │
  │   ├─── model: provider_id/model_name                              │
  │   ├─── messages: 消息列表                                       │
  │   ├─── api_key: 选择的密钥                                      │
  │   ├─── api_base: Provider 端点                                   │
  │   └─── 可选参数：temperature, max_tokens, top_p, stream           │
  │                                                                │
  ├─── 通过 LiteLLM 发送请求                                         │
  │   ├─── 统一接口，支持多 Provider                                 │
  │   ├─── 自动处理不同 Provider 的差异                                 │
  │   └─── 记录开始时间                                              │
  │                                                                │
  └─── 等待响应                                                      │
                                                                  │
[5. 处理响应] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 成功响应：                                                   │
  │   │                                                          │
  │   ├─── 转换响应格式到统一格式：                                    │
  │   │   ├─── id: 响应 ID                                        │
  │   │   ├─── object: 对象类型                                      │
  │   │   ├─── created: 创建时间戳                                   │
  │   │   ├─── model: 模型名称                                       │
  │   │   ├─── choices: 选择列表                                     │
  │   │   ├─── usage: Token 使用统计                                 │
  │   │   ├─── provider_id: Provider ID                              │
  │   │   ├─── latency_ms: 延迟毫秒                               │
  │   │   └─── metadata: 额外元数据                               │
  │   │                                                          │
  │   ├─── 计算延迟：latency_ms = (结束时间 - 开始时间) × 1000           │
  │   │                                                          │
  │   ├─── 更新使用统计：                                              │
  │   │   - 更新密钥使用计数                                          │
  │   │   - 记录 Token 使用量                                         │
  │   │                                                          │
  │   ├─── 记录成功：                                                │
  │   │   - 标记密钥为成功状态                                        │
  │   │   - 更新性能指标                                             │
  │   │                                                          │
  │   └─── 返回统一格式响应                                            │
  │                                                                │
  └─── 异常响应：                                                   │
      │                                                          │
      ├─── 记录失败：                                                │
      │   - 标记密钥为失败状态                                        │
      │   - 记录错误信息                                              │
      │                                                          │
      ├─── 尝试重试（如配置了重试策略）                                  │
      │   - 指数退避重试                                            │
      │   - 最大重试次数限制                                           │
      │                                                          │
      └─── 重试失败后抛出异常                                          │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘

组件职责：
┌───────────────────────────────────────────────────────────────────┐
│ RateLimiter: 速率限制器                               │
│   - 令牌桶算法 / 滑动窗口算法                                   │
│   - 按用户/IP/密钥分别限流                                      │
│                                                            │
│ APIKeyPool: API 密钥池                                │
│   - 轮询选择可用密钥                                             │
│   - 故障密钥冷却机制（5分钟）                                      │
│                                                            │
│ ParameterMapper: 参数映射器                        │
│   - 统一格式 → Provider 原生格式                               │
│   - 支持参数重命名、转换、默认值                                  │
│                                                            │
│ LiteLLM: 统一 API 调用库                                 │
│   - 标准化不同 Provider 的接口                                   │
│   - 支持流式响应                                               │
└───────────────────────────────────────────────────────────────────┘
```

**2. API 密钥轮换流程**

```
密钥轮换请求 ───────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[1. 验证原密钥] ───────────────────────────────────────────────────┤
  │                                                                │
  ├─── 查询密钥信息：                                                │
  │   - 密钥 ID 是否存在                                             │
  │   - 密钥状态是否正常                                             │
  │   - 轮换周期配置                                               │
  │                                                                │
  └─── 密钥不存在 ──→ 返回错误：API key not found               │
                                                                  │
  存在 → 继续                                                  │
      │                                                             │
      ▼                                                           │
[2. 生成新密钥] ─────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 检查是否提供新密钥：                                         │
  │   ├─── 已提供 → 使用提供的新密钥                                 │
  │   └─── 未提供 → 生成新密钥                                      │
  │                                                                │
  └─── 加密新密钥：                                                │
      - 使用 AES-256 加密                                           │
      - 计算密钥哈希（SHA-256）用于标识                               │
                                                                  │
[3. 创建新密钥记录] ───────────────────────────────────────────────────┤
  │                                                                │
  ├─── 密钥名称：原名称_rotated_YYYYMMDD                              │
  │   - provider_id：继承自原密钥                                   │
  │   - encrypted_key：加密后的密钥                                    │
  │   - key_hash：密钥哈希标识                                       │
  │   - rotation_period_days：继承自原密钥                               │
  │   - status：active                                               │
  │                                                                │
  └─── 写入数据库（api_keys 表）                                     │
                                                                  │
[4. 标记旧密钥为待下线] ─────────────────────────────────────────────┤
  │                                                                │
  ├─── 更新旧密钥状态：                                              │
  │   - status：deprecating（待下线）                              │
  │   - deprecate_at：当前时间 + 10分钟                              │
  │                                                                │
  └─── 在 10 分钟内仍可用，之后完全下线                                 │
                                                                  │
[5. 记录审计日志] ─────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 记录操作详情：                                                │
  │   - 操作类型：key_rotation                                        │
  │   - 操作者：system/auto                                          │
  │   - old_key_id：原密钥 ID                                        │
  │   - new_key_id：新密钥 ID                                        │
  │   - 操作时间：当前时间                                             │
  │                                                                │
  └─── 写入审计日志（audit_logs 表）                                   │
                                                                  │
[6. 添加到密钥池] ─────────────────────────────────────────────────────┤
  │                                                                │
  └─── 新密钥加入轮询队列，立即可用                                      │
                                                                  │
[7. 返回新密钥 ID] ────────────────────────────────────────────────────┘


[自动轮换循环] ─────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[每小时检查一次] ─────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 查询到期的密钥：                                              │
  │   - next_rotation_at <= 当前时间                                    │
  │   - status = active                                             │
  │                                                                │
  └─── 对每个到期密钥：                                             │
      - 执行密钥轮换流程                                            │
      - 捕获异常并记录                                              │
                                                                  │
  循环继续（sleep 3600 秒） ─────────────────────────────────────────┘


[密钥池轮询流程] ────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[获取下一个密钥请求] ──────────────────────────────────────────────────┤
  │                                                                │
  ├─── 从队列头部获取密钥 ID                                         │
  ├─── 队列轮转（将头部移到尾部）                                     │
  │                                                                │
  └─── 检查密钥状态：                                                │
      │                                                             │
      ├─── 状态非 active ──→ 跳过，尝试下一个                           │
      │   │                                                          │
      ├─── 在故障冷却期 ──→ 跳过，尝试下一个                           │
      │   │   - 故障时间 < 5分钟                                        │
      │   │   - 冷却期已过则移除故障标记                               │
      │   │                                                          │
      └─── 可用 ──→ 返回密钥 ID                                    │
                                                                  │
  所有密钥都不可用 ──→ 抛出异常：No available API keys           │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘

故障恢复流程 ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[API 调用成功] ────────────────────────────────────────────────────┤
  │                                                                │
  └─── 检查密钥是否在失败列表：                                      │
      ├─── 是 ──→ 移除失败标记，恢复可用状态                        │
      └─── 否 ──→ 无需处理                                            │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘

[API 调用失败] ────────────────────────────────────────────────────┤
  │                                                                │
  └─── 标记密钥为失败状态：                                          │
      - 记录失败时间戳                                              │
      - 进入 5 分钟冷却期                                           │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘
```

**3. 配额管理流程**

```
配额检查请求 ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[获取配额限制] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 查询数据库（quota_limits 表）：                                  │
  │   ├─── provider_id                                             │
  │   ├─── key_id                                                  │
  │   └─── limit_type（requests/tokens/cost）                         │
  │                                                                │
  └─── 返回配额配置列表：                                            │
      ├─── limit_value：限制值                                        │
      ├─── warning_threshold：警告阈值（默认 80%）                       │
      ├─── hard_limit：是否硬限制                                     │
      └─── limit_period：限制周期（minute/hour/day/month）                │
                                                                  │
[检查每个配额] ─────────────────────────────────────────────────────┤
  │                                                                │
  ▼                                                                │
[获取当前使用量] ────────────────────────────────────────────────────┤
  │                                                                │
  └─── 从 Redis 读取：                                              │
      └─── key: provider:quota:{quota_id}                              │
          └─── field: current_usage                                    │
                                                                  │
[计算使用比例] ────────────────────────────────────────────────────────┤
  │                                                                │
  └─── usage_ratio = current_usage / limit_value                           │
                                                                  │
[判断阈值] ─────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 使用比例 >= 警告阈值（80%）？                                │
  │   │                                                          │
  │   └─── 是 且未发送过警告 ──→ [发送警告]                       │
  │       ├─── 发送告警：WARNING 级别                                  │
  │       ├─── 内容：配额使用率、预计耗尽时间                           │
  │       ├─── 渠道：邮件、Webhook、企业微信                             │
  │       └─── 标记已发送：warning_sent = true                   │
  │                                                                │
  ├─── 使用比例 >= 100% 且 hard_limit = true？                         │
  │   │                                                          │
  │   └─── 是 ──→ [拒绝请求]                                   │
  │       ├─── 返回：False, "Quota exceeded: {quota_type}"             │
  │       └─── 记录配额超限事件                                         │
  │                                                                │
  └─── 所有配额检查通过 ──→ 允许请求                         │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[记录使用量] ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[增量更新使用量] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 原子操作（Redis HINCRBY）：                                   │
  │   └─── new_usage = old_usage + delta                             │
  │                                                                │
  └─── 更新 Redis：                                                  │
      ├─── key: provider:quota:{quota_id}                              │
      └─── field: current_usage                                        │
                                                                  │
[检查是否超限] ────────────────────────────────────────────────────────┤
  │                                                                │
  └─── new_usage >= limit_value 且 hard_limit = true？                      │
      │                                                             │
      └─── 是 ──→ [发送超限告警]                                  │
          ├─── 级别：CRITICAL                                        │
          ├─── 内容：配额已完全使用，已拒绝新请求                           │
          └─── 渠道：短信、邮件、企业微信                               │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[配额重置] ──────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[触发时机] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 周期性重置：                                                 │
  │   ├─── minute：每分钟重置                                       │
  │   ├─── hour：每小时重置                                         │
  │   ├─── day：每天重置（00:00）                                    │
  │   └─── month：每月重置（1日 00:00）                               │
  │                                                                │
  └─── 手动重置：                                                   │
      └─── 管理员触发                                               │
                                                                  │
[重置操作] ────────────────────────────────────────────────────────┤
  │                                                                │
  └─── 更新 Redis：                                                  │
      ├─── key: provider:quota:{quota_id}                              │
      └─── field: current_usage = 0                                     │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘
```

**4. 健康检查流程**

```
健康检查启动 ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[为每个 Provider 启动检查循环] ─────────────────────────────────┤
  │                                                                │
  ├─── 并发启动多个检查任务                                        │
  │   ├─── Provider 1 ──→ 检查循环                               │
  │   ├─── Provider 2 ──→ 检查循环                               │
  │   └─── Provider N ──→ 检查循环                                 │
  │                                                                │
  └─── 检查间隔：30 秒                                            │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[单次健康检查循环] ───────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[执行健康检查] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 发送测试请求：                                                │
  │   ├─── model: test-model                                         │
  │   ├─── messages: [{"role": "user", "content": "ping"}]           │
  │   └─── max_tokens: 10                                           │
  │                                                                │
  ├─── 设置超时：10 秒                                               │
  │                                                                │
  └─── 等待响应                                                      │
                                                                  │
[处理结果] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 成功：                                                       │
  │   ├─── 计算延迟：latency_ms = (响应时间 - 开始时间) × 1000       │
  │   ├─── 结果：(True, latency_ms)                                  │
  │   │                                                          │
  │   └─── [更新健康状态] ──→ 状态：健康                          │
  │       ├─── is_healthy: true                                      │
  │       ├─── latency_ms: 实际延迟                                  │
  │       └─── consecutive_failures: 0                                  │
  │                                                                │
  ├─── 超时：                                                       │
  │   ├─── 计算延迟：10000 ms（10 秒）                                │
  │   ├─── 结果：(False, 10000)                                     │
  │   │                                                          │
  │   └─── [记录失败] ──→ 失败计数 + 1                           │
  │                                                                │
  └─── 异常：                                                       │
      ├─── 计算延迟：0 ms                                            │
      ├─── 结果：(False, 0)                                          │
      │                                                          │
      └─── [记录失败] ──→ 失败计数 + 1                           │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[健康状态更新逻辑] ────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[检查失败处理] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 连续失败次数 + 1                                              │
  │                                                                │
  ├─── 失败次数 >= 阈值（3 次）？                                 │
  │   │                                                          │
  │   ├─── 否 ──→ 仅记录失败次数                                    │
  │   │                                                          │
  │   └─── 是 ──→ [标记为不健康]                                  │
  │       ├─── is_healthy: false                                     │
  │       ├─── consecutive_failures: 失败次数                             │
  │       └─── [发送告警]                                        │
  │           ├─── 级别：CRITICAL                                     │
  │           ├─── 事件：Provider down                               │
  │           └─── 渠道：短信、邮件、企业微信                             │
  │                                                                │
  └─── 保存到 Redis：                                                  │
      └─── key: provider:health:{provider_id}                           │
          ├─── is_healthy: true/false                                  │
          ├─── latency_ms: 延迟毫秒                                    │
          ├─── consecutive_failures: 连续失败次数                           │
          └─── last_check: 检查时间戳                                  │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[健康恢复处理] ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[检查成功处理] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 检查之前是否为不健康状态                                        │
  │                                                                │
  ├─── 否 ──→ 无需特殊处理                                        │
  │                                                                │
  └─── 是 ──→ [发送恢复通知]                                   │
      ├─── 级别：INFO                                               │
      ├─── 事件：Provider recovered                                │
      └─── 渠道：邮件、企业微信                                       │
                                                                  │
  重置失败计数 = 0                                                   │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[故障转移触发] ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[Provider 标记为不健康] ─────────────────────────────────────────────┤
  │                                                                │
  ├─── 路由引擎收到通知                                              │
  │                                                                │
  ├─── 从可用 Provider 列表中移除该 Provider                       │
  │                                                                │
  └─── 后续请求自动路由到其他可用 Provider                     │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘


[Provider 恢复] ────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[Provider 标记为健康] ─────────────────────────────────────────────────┤
  │                                                                │
  ├─── 路由引擎收到通知                                              │
  │                                                                │
  ├─── 将该 Provider 重新加入可用列表                         │
  │                                                                │
  └─── 后续请求可以再次路由到该 Provider                         │
                                                                  │
────────────────────────────────────────────────────────────────────────────┘

配置参数：
┌───────────────────────────────────────────────────────────────────┐
│ 检查间隔：30 秒                                     │
│ 超时时间：10 秒                                       │
│ 失败阈值：3 次连续失败                                │
│ Redis TTL：30 秒                                      │
└───────────────────────────────────────────────────────────────────┘
```

#### 非功能需求考虑

| 需求类型 | 实现方案 | 性能指标 |
|---------|---------|---------|
| 性能 | 连接池 + 异步调用 + 缓存 | API 调用：<5ms 额外延迟 |
| 可靠性 | 密钥池 + 故障切换 | 密钥切换：<100ms |
| 安全性 | 密钥加密 + 轮换 + 审计 | AES-256 加密 |
| 可扩展性 | Provider 适配器 + 动态配置 | 支持新 Provider 快速接入 |

---

## 三、剩余 Agent 详细实现方案

### 3.1 Cost Agent (成本 Agent)

#### 功能点映射
| 产品需求功能点 | 子功能 | 实现方案 |
|--------------|-------|---------|
| **实时成本监控** | 毫秒级成本追踪 | Token 级精确计算 + 流式更新 |
| | 智能预警系统 | 多阈值预警 + 预测预警 |
| **多维度成本分析** | 模型成本分析 | 单模型 + 多模型对比 |
| | 多层级成本分摊 | 用户/部门/应用/功能级分摊 |
| | 成本驱动因素分析 | 因子分解 + 归因分析 |
| | 投资回报分析 | ROI 计算 + 价值评估 |
| **智能成本优化** | AI 驱动的模型推荐 | 成本-质量权衡推荐 |
| | 多层次缓存优化 | 请求/模型/知识缓存 |
| | 批量处理优化 | 请求合并 + 时间窗口 |
| | 智能预算管理 | 预算分配 + 监控 + 调整 |

#### 数据结构设计

**PostgreSQL 表结构**
```sql
-- 成本记录（Token 级）
CREATE TABLE cost_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(100),
    provider_id VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd DECIMAL(12, 6) NOT NULL,
    cost_breakdown JSONB,  -- {input_cost, output_cost, ...}
    request_time TIMESTAMP WITH TIME ZONE NOT NULL,
    record_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 成本分摊记录
CREATE TABLE cost_allocation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cost_record_id UUID REFERENCES cost_records(id),
    allocation_type VARCHAR(50) NOT NULL,  -- user, department, application, function
    allocation_id VARCHAR(100) NOT NULL,  -- 具体分摊对象 ID
    allocated_amount DECIMAL(12, 6) NOT NULL,
    allocation_percentage DECIMAL(5, 4),
    metadata JSONB DEFAULT '{}'
);

-- 预算配置
CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_name VARCHAR(200) NOT NULL,
    budget_type VARCHAR(50) NOT NULL,  -- user, department, application, global
    target_id VARCHAR(100),  -- 关联的用户/部门/应用 ID
    budget_period VARCHAR(50) NOT NULL,  -- daily, weekly, monthly, yearly
    budget_amount DECIMAL(12, 2) NOT NULL,
    used_amount DECIMAL(12, 2) DEFAULT 0,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    warning_threshold DECIMAL(5, 2) DEFAULT 0.80,  -- 80%
    hard_limit BOOLEAN DEFAULT TRUE,
    auto_adjust BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 成本优化建议
CREATE TABLE cost_optimization_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suggestion_type VARCHAR(50) NOT NULL,  -- model_replacement, caching, batching
    target_model VARCHAR(100),
    recommended_model VARCHAR(100),
    estimated_savings_usd DECIMAL(12, 2),
    estimated_savings_percentage DECIMAL(5, 2),
    confidence_score DECIMAL(5, 4),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, applied, dismissed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- 成本预测记录
CREATE TABLE cost_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_type VARCHAR(50) NOT NULL,  -- daily, weekly, monthly
    target_date DATE NOT NULL,
    predicted_amount DECIMAL(12, 2) NOT NULL,
    actual_amount DECIMAL(12, 2),
    accuracy_score DECIMAL(5, 4),
    model_used VARCHAR(100),
    prediction_factors JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Redis 数据结构**
```python
# 实时成本统计（滑动窗口）
Key: cost:stats:{user_id}:{period}
Type: Hash (TTL: 根据周期设置)
Fields:
  - total_cost: decimal        # 总成本
  - total_tokens: int         # 总 token 数
  - request_count: int        # 请求数
  - model_costs: json         # 各模型成本 {"gpt-4": 100.50, ...}

# 预算使用状态
Key: cost:budget:{budget_id}
Type: Hash
Fields:
  - used_amount: decimal      # 已使用金额
  - warning_sent: bool        # 是否已发送预警
  - limit_reached: bool      # 是否达到限制
  - last_updated: timestamp

# 成本预警队列
Key: cost:alerts:queue
Type: List
Value: [alert_json_1, alert_json_2, ...]

# 缓存统计
Key: cost:cache:stats
Type: Hash
Fields:
  - hit_count: int           # 命中次数
  - miss_count: int          # 未命中次数
  - saved_cost: decimal      # 节省的成本
```

#### 核心算法设计（流程图 + 原理介绍）

**1. 毫秒级成本追踪流程**

```
用户请求 ────────────────────────────────────────────────────────────┐
  │                                                                  │
  ▼                                                                  │
[Provider 调用]                                                       │
  │                                                                  │
  ├─── 响应返回 ────────────────────────────────────────────────────┤
  │   │                                                              │
  │   ├─── 提取 usage 信息                                            │
  │   │   - input_tokens                                              │
  │   │   - output_tokens                                             │
  │   │                                                              │
  │   ▼                                                              │
  │   [查询模型定价]                                                  │
  │   │                                                              │
  │   ├─── 查询本地缓存（Redis）                                     │
  │   │                                                              │
  │   └─── 缓存未命中 → 查询数据库                                   │
  │       │                                                          │
  │       └─── 更新缓存                                              │
  │                                                                  │
  │   ▼                                                              │
  │   [计算成本]                                                     │
  │   │                                                              │
  │   ├─── input_cost = input_tokens × price_per_1k_input / 1000     │
  │   │                                                              │
  │   ├─── output_cost = output_tokens × price_per_1k_output / 1000   │
  │   │                                                              │
  │   └─── total_cost = input_cost + output_cost                    │
  │                                                                  │
  │   ▼                                                              │
  │   [写入成本记录]                                                  │
  │   │                                                              │
  │   ├─── 写入 PostgreSQL (cost_records)                             │
  │   │   - 异步写入，不阻塞响应                                      │
  │   │                                                              │
  │   ├─── 更新 Redis 实时统计                                        │
  │   │   - 原子操作，保证一致性                                      │
  │   │                                                              │
  │   └─── 更新用户预算状态                                            │
  │       - 检查是否超预算                                            │
  │       - 触发预警（如需要）                                         │
  │                                                                  │
  ▼                                                                  │
[返回响应] ────────────────────────────────────────────────────────────┘
```

**2. 智能预警系统原理**

```
触发条件检查 ───────────────────────────────────────────────────────┐
  │                                                                │
  ├─── [预算预警]                                                  │
  │   │                                                          │
  │   ├─── 使用比例 >= 警告阈值（默认 80%）                         │
  │   │   AND 未发送过预警                                          │
  │   │                                                          │
  │   └─── [发送预警]                                               │
  │       - 预警级别：WARNING                                      │
  │       - 渠道：邮件、Webhook、企业微信                            │
  │       - 内容：预算使用进度、预计耗尽时间                           │
  │                                                                │
  ├─── [异常成本预警]                                               │
  │   │                                                          │
  │   ├─── 当前成本 > 历史均值 × 2                                   │
  │   │   OR 增长率 > 50%（相比上周）                                │
  │   │                                                          │
  │   └─── [发送预警]                                               │
  │       - 分析异常原因（模型选择、请求量等）                          │
  │       - 提供优化建议                                            │
  │                                                                │
  ├─── [浪费预警]                                                   │
  │   │                                                          │
  │   ├─── 使用高级模型处理简单任务（复杂度 < 50）                      │
  │   │   AND 成本 > 预期成本 × 2                                    │
  │   │                                                          │
  │   └─── [发送预警]                                               │
  │       - 识别浪费的请求                                          │
  │       - 建议使用更经济的模型                                     │
  │                                                                │
  ├─── [账户预警]                                                   │
  │   │                                                          │
  │   └─── API 余额 < $100                                          │
  │       [发送预警]                                                │
  │                                                                │
  └─── [预测预警]                                                   │
      │                                                          │
      └─── 基于趋势预测未来超出预算                                    │
          [发送预警]                                                │
                                                                  │
                                                                  │
[预警聚合与去重] ───────────────────────────────────────────────┘
  │
  └─── 合并相同类型的预警（避免告警风暴）
      │
      ▼
[发送通知]
  │
  ├─── 记录预警历史
  │
  └─── 标记预警已发送
```

**3. 多维度成本分析原理**

```
[成本数据收集] ────────────────────────────────────────────────────┐
  │                                                                │
  ├─── 按模型分析                                                   │
  │   │                                                          │
  │   ├─── 统计每个模型的：                                         │
  │   │   - 总成本                                                  │
  │   │   - Token 数量                                              │
  │   │   - 请求数量                                                │
  │   │   - 平均成本/Token                                          │
  │   │                                                          │
  │   ├─── 计算模型效率：                                            │
  │   │   - 效率 = 质量评分 / 成本                                   │
  │   │   - 对比各模型性价比                                         │
  │   │                                                          │
  │   └─── 分析模型使用趋势：                                         │
  │       - 时间序列分析                                            │
  │       - 识别使用模式变化                                         │
  │                                                                │
  ├─── 按层级分摊                                                   │
  │   │                                                          │
  │   ├─── 用户级分摊：                                              │
  │   │   - 按用户 ID 分组统计                                       │
  │   │   - 计算每个用户的成本占比                                     │
  │   │                                                          │
  │   ├─── 部门级分摊：                                              │
  │   │   - 按部门标签分组                                           │
  │   │   - 计算部门成本                                            │
  │   │                                                          │
  │   ├─── 应用级分摊：                                              │
  │   │   - 按应用 ID 分组                                           │
  │   │   - 计算应用成本                                            │
  │   │                                                          │
  │   └─── 功能级分摊：                                              │
  │       - 按功能标签分组                                           │
  │       - 计算功能成本                                            │
  │                                                                │
  ├─── 成本驱动因素分析                                              │
  │   │                                                          │
  │   ├─── 因子分解：                                                │
  │   │   - 总成本 = ∑(请求数 × 平均Token数 × 单价)                     │
  │   │   - 识别哪个因子变化影响最大                                  │
  │   │                                                          │
  │   ├─── 归因分析：                                                │
  │   │   - 成本增加原因（请求数↑？模型选择更贵？单价上涨？）            │
  │   │   - 提供优化建议                                            │
  │   │                                                          │
  │   └── 时间分布分析：                                              │
  │       - 识别高峰时段、成本变化模式                                  │
  │                                                                │
  └─── 投资回报分析                                                  │
      │                                                          │
      ├─── ROI 计算：                                                │
      │   - ROI = (收益 - 成本) / 成本 × 100%                         │
      │   - 收益 = 效率提升 + 成本节约 + 收入增加                        │
      │                                                          │
      ├─── 价值评估：                                                │
      │   - AI 应用对业务的实际价值                                    │
      │   - 用户满意度、任务完成度等指标                                │
      │                                                          │
      └─── 效率提升分析：                                              │
          - 对比使用前后的工作效率                                    │
          - 量化效率提升                                              │
                                                                  │
[生成报告] ────────────────────────────────────────────────────────┘
```

**4. 智能成本优化策略原理**

```
[分析当前使用模式] ───────────────────────────────────────────────┐
  │                                                                │
  ├─── 收集数据：                                                  │
  │   - 历史成本数据                                                │
  │   - 请求复杂度分布                                              │
  │   - 模型使用模式                                                │
  │   - 缓存命中率                                                 │
  │                                                                │
  [生成优化建议] ────────────────────────────────────────────────┘
  │
  ├─── AI 驱动的模型推荐
  │   │
  │   ├─── 分析任务复杂度 → 推荐合适的模型
  │   │   - 低复杂度（<50）：推荐经济模型
  │   │   - 中等复杂度（50-80）：推荐平衡模型
  │   │   - 高复杂度（>80）：推荐高质量模型
  │   │
  │   └─── 模型替换建议
  │       - 识别可以用更便宜模型替代的场景
  │       - 估算节省成本
  │
  ├─── 多层次缓存优化
  │   │
  │   ├─── 请求缓存
  │   │   - 缓存相同请求的响应（TTL 可配置）
  │   │   - 相似请求去重（基于内容哈希）
  │   │
  │   ├─── 模型缓存
  │   │   - 缓存模型的中间推理结果
  │   │   - 支持增量计算
  │   │
  │   └─── 知识缓存
  │       - 缓存常见问题的答案
  │       - 缓存热门内容的摘要
  │
  ├─── 批量处理优化
  │   │
  │   ├─── 请求合并
  │   │   - 合并多个小请求为一个批量请求
  │   │   - 使用 Provider 的批处理 API
  │   │
  │   ├─── 智能队列
  │   │   - 按相似性分组请求
  │   │   - 优先合并高价值请求
  │   │
  │   └─── 时间窗口处理
  │       - 在固定时间窗口内批量处理
  │       - 平衡延迟和成本
  │
  └─── 智能预算管理
      │
      ├─── 预算分配
      │   - 为不同部门/项目分配独立预算
      │   - 基于历史数据预测预算需求
      │
      ├─── 预算监控
      │   - 实时监控预算使用情况
      │   - 可视化预算进度
      │
      ├─── 预算调整
      │   - 自动调整预算（基于预测）
      │   - 跨预算池动态分配
      │
      └─── 预算报告
          - 定期生成预算使用报告
          - 提供预算优化建议

[应用优化措施] ────────────────────────────────────────────────┘
  │
  └─── 记录优化效果
      - 实际节省成本
      - 对服务质量的影响
```

#### 非功能需求考虑

| 需求类型 | 实现方案 | 性能指标 |
|---------|---------|---------|
| 性能 | 异步写入 + 批量更新 + Redis 缓存 | 成本计算：<10ms |
| 可靠性 | 事务保证 + 幂等写入 + 重试机制 | 99.99% 数据完整性 |
| 可扩展性 | 分片存储 + 水平扩展 | 支持 20TB+ 数据 |
| 安全性 | 成本数据访问控制 + 审计日志 | RBAC 控制 |

---

### 3.2 Security Agent (安全 Agent)

#### 功能点映射
| 产品需求功能点 | 子功能 | 实现方案 |
|--------------|-------|---------|
| **多层数据安全** | 全链路加密 | TLS 1.3 + AES-256 存储 |
| | 敏感信息保护 | PII 检测 + 脱敏 + 数据分级 |
| | API 安全防护 | 请求验证 + 参数过滤 + 限流 |
| | 数据生命周期管理 | 分类 + 保留 + 归档 + 安全删除 |
| **访问控制** | 多因素认证 | API Key + JWT + OAuth 2.0 + SAML |
| | 细粒度权限控制 | RBAC + ABAC |
| | 精细化访问策略 | 资源/操作/数据/时间/数量级 |
| **审计与监控** | 完整的操作日志 | 操作/访问/安全/错误/性能日志 |
| | 智能异常监控 | 实时监控 + 异常检测 + 自动响应 |
| | 合规审计支持 | 审计报告 + 合规检查 |
| **高级安全** | 威胁检测与防御 | 入侵/恶意代码/异常流量检测 |
| | 数据安全增强 | 加密 + 脱敏 + 水印 + 防泄漏 |
| | 安全配置管理 | 基线 + 加固 + 扫描 + 更新 |

#### 数据结构设计

**PostgreSQL 表结构**
```sql
-- 敏感信息检测记录
CREATE TABLE pii_detection_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(100),
    detected_entities JSONB,  -- [{"type": "email", "value": "***", "position": 10}, ...]
    masked_content TEXT,
    original_content TEXT,
    data_level VARCHAR(20),  -- public, internal, secret, top_secret
    detection_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 访问控制策略
CREATE TABLE access_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_name VARCHAR(200) NOT NULL,
    policy_type VARCHAR(50) NOT NULL,  -- rbac, abac
    resource_pattern VARCHAR(200),  -- /v1/chat/completions/*
    action VARCHAR(50),  -- read, write, delete
    effect VARCHAR(10) NOT NULL,  -- allow, deny
    conditions JSONB DEFAULT '{}',  -- 条件表达式
    priority INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户权限
CREATE TABLE user_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    role_id UUID REFERENCES roles(id),
    attribute_policies JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 操作审计日志
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),
    request_id VARCHAR(255),
    operation_type VARCHAR(50) NOT NULL,  -- api_call, config_change, etc.
    resource VARCHAR(200),
    result VARCHAR(20),  -- success, failure, blocked
    details JSONB DEFAULT '{}',
    client_ip VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 安全事件
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,  -- intrusion, brute_force, data_leak, etc.
    severity VARCHAR(20),  -- critical, high, medium, low
    description TEXT,
    affected_resources JSONB DEFAULT '{}',
    attacker_info JSONB DEFAULT '{}',
    response_taken TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- IP 白名单/黑名单
CREATE TABLE ip_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ip_address VARCHAR(50) NOT NULL,
    ip_range VARCHAR(50),  -- CIDR notation
    list_type VARCHAR(10) NOT NULL,  -- whitelist, blacklist
    reason VARCHAR(500),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Redis 数据结构**
```python
# 速率限制（滑动窗口）
Key: security:rate:{user_id}:{endpoint}
Type: String (Lua 脚本控制)
Value: 请求时间戳列表

# 失败登录/请求计数
Key: security:failures:{user_id}
Type: Hash
Fields:
  - count: int               # 失败次数
  - locked_until: timestamp  # 锁定到期时间
  - last_attempt: timestamp

# 会话令牌
Key: security:session:{session_token}
Type: Hash (TTL: 会话时长)
Fields:
  - user_id: str
  - permissions: json
  - created_at: timestamp
  - last_activity: timestamp

# 威胁评分
Key: security:threat:{ip_address}
Type: Hash (TTL: 1小时)
Fields:
  - score: int               # 威胁评分 0-100
  - events: json             # 最近的事件列表
```

#### 核心算法设计（流程图 + 原理介绍）

**1. 敏感信息检测与脱敏流程**

```
用户请求内容 ───────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[内容分析] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── PII 实体检测                                               │
  │   │                                                          │
  │   ├─── 检测类型：                                              │
  │   │   - 邮箱地址                                                │
  │   │   - 手机号码                                                │
  │   │   - 身份证号                                                │
  │   │   - 银行卡号                                                │
  │   │   - 姓名、地址、日期                                         │
  │   │                                                          │
  │   ├─── 检测方法：                                              │
  │   │   - 正则表达式匹配                                           │
  │   │   - 本地轻量级模型（如 phi-3-mini）                          │
  │   │   - 规则引擎 + 机器学习混合                                   │
  │   │                                                          │
  │   └─── 定位实体位置：                                            │
  │       - 字符位置偏移                                              │
  │       - 上下文范围                                              │
  │                                                                │
  ├─── 数据分级                                                   │
  │   │                                                          │
  │   ├─── 公开（public）                                           │
  │   │   - 不包含敏感信息                                           │
  │   │                                                          │
  │   ├─── 内部（internal）                                         │
  │   │   - 包含一般敏感信息                                         │
  │   │                                                          │
  │   ├─── 秘密（secret）                                           │
  │   │   - 包含重要敏感信息                                         │
  │   │                                                          │
  │   └─── 绝密（top_secret）                                       │
  │       - 包含高度敏感信息                                         │
  │                                                                │
  ├─── 脱敏处理                                                   │
  │   │                                                          │
  │   ├─── 脱敏策略：                                              │
  │   │   - 完全替换：***                                           │
  │   │   - 部分隐藏：user@***.com                                 │
  │   │   - 掩码：****1234                                          │
  │   │   - 哈希：SHA-256(原始值)                                   │
  │   │                                                          │
  │   └─── 可逆脱敏（仅内部使用）                                    │
  │       - 加密存储（AES-256）                                      │
  │       - 需要时解密                                              │
  │                                                                │
  ▼                                                                │
[访问控制决策] ────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 检查数据级别：                                              │
  │   │                                                          │
  │   ├─── 公开数据：允许访问                                         │
  │   │                                                          │
  │   └─── 敏感数据：检查权限                                         │
  │       - 用户是否有该级别数据的访问权限？                            │
  │       - 是否需要二次认证？                                        │
  │                                                                │
  ▼                                                                │
[记录审计日志] ────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 记录：                                                      │
  │   - 检测到的敏感信息（加密后）                                   │
  │   - 脱敏操作                                                  │
  │   - 访问决策                                                  │
  │   - 请求来源                                                  │
  │                                                                │
  ▼                                                                │
[处理请求] ────────────────────────────────────────────────────────┘
```

**2. 访问控制流程**

```
用户请求 ─────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[身份验证] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 检查认证方式：                                              │
  │   │                                                          │
  │   ├─── API Key                                                │
  │   │   - 验证 Key 有效性                                        │
  │   │   - 检查 Key 权限                                         │
  │   │   - 检查 Key 状态（激活/禁用/过期）                          │
  │   │                                                          │
  │   ├─── JWT Token                                              │
  │   │   - 验证签名                                               │
  │   │   - 检查过期时间                                           │
  │   │   - 解析用户信息                                            │
  │   │                                                          │
  │   ├─── OAuth 2.0                                              │
  │   │   - 验证访问令牌                                           │
  │   │   - 检查令牌范围                                           │
  │   │                                                          │
  │   └─── SAML 2.0 (企业 SSO)                                     │
  │       - 验证 SAML 断言                                         │
  │       - 提取用户信息                                            │
  │                                                                │
  ▼                                                                │
[权限检查] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── RBAC 检查：                                                │
  │   │                                                          │
  │   ├─── 获取用户角色                                              │
  │   │                                                          │
  │   ├─── 检查角色是否有资源访问权限                                  │
  │   │                                                          │
  │   └─── 检查角色是否有操作权限                                      │
  │                                                                │
  ├─── ABAC 检查：                                                │
  │   │                                                          │
  │   ├─── 获取用户属性（部门、级别等）                                │
  │   │                                                          │
  │   ├─── 获取资源属性（数据级别、所有者等）                            │
  │   │                                                          │
  │   └─── 评估访问策略                                              │
  │       - 时间限制（只在工作时间）                                     │
  │       - 数量限制（每天最多 N 次请求）                                │
  │       - 地理限制（只允许特定地区）                                  │
  │                                                                │
  ▼                                                                │
[精细化访问策略] ─────────────────────────────────────────────────┤
  │                                                                │
  ├─── 资源级别：                                                  │
  │   - 限制特定 API 端点                                           │
  │   - 限制特定资源（如特定用户的请求）                                │
  │                                                                │
  ├─── 操作级别：                                                  │
  │   - 区分读取/写入/删除操作                                        │
  │   - 为不同操作设置不同权限                                         │
  │                                                                │
  ├─── 数据级别：                                                  │
  │   - 根据数据敏感度控制访问                                        │
  │   - 敏感数据需要额外认证                                          │
  │                                                                │
  ├─── 时间限制：                                                  │
  │   - 设置访问时间窗口                                             │
  │   - 非工作时间自动拒绝                                            │
  │                                                                │
  └─── 数量限制：                                                  │
      - 限制访问次数和频率                                           │
      - 超限后自动封禁                                              │
                                                                  │
[决策] ─────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 允许 → 处理请求                                            │
  │                                                                │
  └─── 拒绝 → 返回 403 Forbidden                                   │
      - 记录拒绝原因                                              │
      - 发送告警（如需要）                                           │
                                                                  │
[记录审计日志] ──────────────────────────────────────────────────────┘
```

**3. 威胁检测流程**

```
实时流量监控 ─────────────────────────────────────────────────────┐
  │                                                                │
  ├─── [异常流量检测]                                              │
  │   │                                                          │
  │   ├─── 流量模式分析：                                            │
  │   │   - 检测突发流量 spike                                       │
  │   │   - 检测异常高频请求                                          │
  │   │   - 检测非正常时间段访问                                       │
  │   │                                                          │
  │   ├─── 统计分析：                                                │
  │   │   - 与历史数据对比                                           │
  │   │   - 与同类型用户对比                                           │
  │   │   - 异常检测（如 3 倍标准差）                                  │
  │   │                                                          │
  │   └─── 触发条件：                                                │
  │       - QPS 超过阈值 × 3                                         │
  │       - 单用户请求频率异常                                        │
  │       - API 调用模式异常                                          │
  │                                                                │
  ├─── [恶意请求检测]                                              │
  │   │                                                          │
  │   ├─── 注入攻击检测：                                             │
  │   │   - SQL 注入                                               │
  │   │   - 命令注入                                               │
  │   │   - XSS 攻击                                               │
  │   │                                                          │
  │   ├─── 参数验证：                                                │
  │   │   - 验证参数类型和范围                                         │
  │   │   - 过滤特殊字符                                            │
  │   │   - 长度限制                                                │
  │   │                                                          │
  │   └─── 模式识别：                                                │
  │       - 已知攻击模式匹配                                          │
  │       - 异常参数组合                                              │
  │                                                                │
  ├─── [暴力破解检测]                                              │
  │   │                                                          │
  │   ├─── 失败登录计数：                                            │
  │   │   - 单 IP/用户失败次数                                        │
  │   │   - 短时间内失败 > N 次                                      │
  │   │                                                          │
  │   ├─── 模式识别：                                                │
  │   │   - 密码喷洒攻击                                             │
  │   │   - 凭证填充攻击                                             │
  │   │                                                          │
  │   └─── 响应措施：                                                │
  │       - 临时锁定 IP                                              │
  │       - 要求 CAPTCHA                                             │
  │       - 发送告警                                                │
  │                                                                │
  ├─── [入侵检测]                                                  │
  │   │                                                          │
  │   ├─── 行为分析：                                                │
  │   │   - 异常操作序列                                             │
  │   │   - 权限提升尝试                                              │
  │   │   - 扫描行为                                                │
  │   │                                                          │
  │   └─── 机器学习检测：                                            │
  │       - 异常行为识别模型                                          │
  │       - 用户行为基线分析                                          │
  │                                                                │
  └─── [数据泄漏检测]                                              │
      │                                                          │
      ├─── 敏感数据外传：                                            │
      │   - 检测大量敏感数据传输                                        │
      │   - 检测异常数据访问模式                                        │
      │                                                          │
      ├─── 异常访问：                                                │
      │   - 异常时间访问                                              │
      │   - 异常频率访问                                              │
      │                                                          │
      └─── 水印追踪：                                                │
          - 数据嵌入数字水印                                          │
          - 泄露后可追踪来源                                           │
                                                                  │
[威胁评分与响应] ───────────────────────────────────────────────┤
  │                                                                │
  ├─── 评分标准：                                                  │
  │   │                                                          │
  │   ├─── 低（0-25）：正常行为，记录即可                               │
  │   │                                                          │
  │   ├─── 中（26-50）：需要关注，可能触发告警                           │
  │   │                                                          │
  │   ├─── 高（51-75）：需要立即处理，自动响应                          │
  │   │                                                          │
  │   └─── 严重（76-100）：紧急，自动阻断 + 人工介入                      │
  │                                                                │
  ├─── 响应措施：                                                  │
  │   │                                                          │
  │   ├─── 记录事件                                                 │
  │   │   - 详细记录威胁事件                                           │
  │   │   - 保存证据                                                │
  │   │                                                          │
  │   ├─── 发送告警                                                 │
  │   │   - 根据级别选择通知方式                                       │
  │   │   - 邮件、短信、Webhook、企业微信                               │
  │   │                                                          │
  │   ├─── 自动响应                                                 │
  │   │   - 限制/封禁 IP                                            │
  │   │   - 暂停用户账号                                             │
  │   │   - 启用额外验证                                             │
  │   │                                                          │
  │   └── 生成报告                                                 │
  │       - 安全事件报告                                             │
  │       - 处理建议                                                │
  │                                                                │
  ▼                                                                │
[更新威胁情报] ────────────────────────────────────────────────────┘
```

#### 非功能需求考虑

| 需求类型 | 实现方案 | 性能指标 |
|---------|---------|---------|
| 性能 | 异步审计 + 缓存 + 并行检测 | 安全检测：<15ms |
| 可靠性 | 故障隔离 + 降级策略 | 99.999% 可用性 |
| 安全性 | 多层防护 + 密钥轮换 | AES-256 加密 |
| 可扩展性 | 规则引擎 + 插件化 | 支持 100 万+ IP 规则 |

---

### 3.3 Analytics Agent (分析 Agent)

#### 功能点映射
| 产品需求功能点 | 子功能 | 实现方案 |
|--------------|-------|---------|
| **系统性能监控** | API 性能监控 | 响应时间/分布/趋势/异常 |
| | 错误率监控 | 统计/类型分析/根因分析 |
| | 吞吐量监控 | QPS/并发数/分布/峰值 |
| | 资源使用监控 | CPU/内存/磁盘/网络/GPU |
| | 成本监控 | 实时/趋势/分布/分析 |
| **深度业务分析** | 多维调用量统计 | 总量/模型/用户/时间/地域 |
| | 用户行为分析 | 画像/模式/留存/价值/分群 |
| | 模型使用分析 | 偏好/性能/成本/效率/趋势 |
| | 业务价值分析 | 指标/评估/效率/成本/ROI |
| **智能分析系统** | 趋势分析与预测 | 时间序列分析/预测 |
| | 性能瓶颈诊断 | 根因分析/优化建议 |
| | 智能报表系统 | 仪表盘/历史趋势/自定义报表 |
| **智能告警系统** | 多级告警机制 | 严重/警告/信息 |
| | 告警通知管理 | 多渠道/策略/模板/抑制/升级 |
| | 告警响应自动化 | 自动处理/工单集成/知识库 |

#### 数据结构设计

**PostgreSQL 表结构**
```sql
-- 性能指标（时间序列）
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15, 6) NOT NULL,
    tags JSONB DEFAULT '{}',  -- {provider: "openai", model: "gpt-4", ...}
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 错误记录
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255),
    error_code VARCHAR(50),
    error_message TEXT,
    error_type VARCHAR(50),  -- 4xx, 5xx, timeout, rate_limit
    provider_id VARCHAR(100),
    model VARCHAR(100),
    user_id VARCHAR(100),
    stack_trace TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户行为事件
CREATE TABLE user_behavior_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,  -- api_call, model_switch, config_change
    event_data JSONB DEFAULT '{}',
    session_id VARCHAR(255),
    client_info JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 告警规则
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(200) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    condition JSONB NOT NULL,  -- {operator: ">", threshold: 100}
    severity VARCHAR(20) NOT NULL,  -- critical, warning, info
    duration_seconds INTEGER DEFAULT 300,  -- 持续时间
    enabled BOOLEAN DEFAULT TRUE,
    notification_channels JSONB DEFAULT '[]',  -- ["email", "webhook"]
    suppression_rules JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 告警记录
CREATE TABLE alert_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES alert_rules(id),
    severity VARCHAR(20) NOT NULL,
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'active',  -- active, acknowledged, resolved
    message TEXT,
    metadata JSONB DEFAULT '{}',
    actions_taken TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Redis 数据结构**
```python
# 实时指标（滑动窗口）
Key: metrics:realtime:{metric_name}:{tags_hash}
Type: Hash (TTL: 5分钟)
Fields:
  - count: int               # 数据点数量
  - sum: decimal             # 总和
  - avg: decimal             # 平均值
  - min: decimal             # 最小值
  - max: decimal             # 最大值
  - p50: decimal             # P50 分位
  - p95: decimal             # P95 分位
  - p99: decimal             # P99 分位

# 告警状态
Key: alerts:active:{rule_id}
Type: Hash
Fields:
  - triggered_at: timestamp
  - consecutive_count: int
  - last_notified: timestamp

# 用户会话
Key: session:{session_id}
Type: Hash (TTL: 30分钟)
Fields:
  - user_id: str
  - start_time: timestamp
  - event_count: int
  - last_event: timestamp
```

#### 核心算法设计（流程图 + 原理介绍）

**1. 实时性能监控流程**

```
API 请求响应 ──────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[采集指标] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 响应时间指标：                                              │
  │   - latency_ms（总延迟）                                         │
  │   - routing_latency_ms（路由决策延迟）                           │
  │   - provider_latency_ms（Provider 调用延迟）                       │
  │                                                                │
  ├─── 错误指标：                                                  │
  │   - error_rate（错误率）                                        │
  │   - error_type（错误类型）                                      │
  │   - error_message（错误信息）                                    │
  │                                                                │
  ├─── 吞吐量指标：                                                │
  │   - qps（每秒查询数）                                            │
  │   - concurrent_requests（并发请求数）                              │
  │                                                                │
  ├─── 资源指标：                                                  │
  │   - cpu_usage_percent                                           │
  │   - memory_usage_percent                                        │
  │   - disk_usage_percent                                          │
  │   - network_bandwidth_mbps                                       │
  │                                                                │
  └─── 成本指标：                                                  │
      - cost_usd（单次请求成本）                                      │
      - total_cost_usd（累计成本）                                   │
                                                                  │
[实时处理] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 写入 Redis（滑动窗口）                                        │
  │   - 使用 Redis Hash 存储指标                                     │
  │   - 定期清理过期数据                                            │
  │                                                                │
  ├─── 计算统计值：                                                │
  │   - 平均值、最大值、最小值                                        │
  │   - P50、P95、P99 分位数                                        │
  │                                                                │
  └─── 更新监控面板：                                                │
      - 推送实时数据到 WebSocket                                    │
      - 更新前端仪表盘                                              │
                                                                  │
[持久化存储] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 批量写入 PostgreSQL                                          │
  │   - 使用批量插入提高效率                                         │
  │   - 按时间分片存储                                              │
  │   - 保留 1 年历史数据                                            │
  │                                                                │
  └─── 写入 VictoriaMetrics（时序数据库）                              │
      - 高效的时序数据存储和查询                                      │
      - 支持长期存储和快速查询                                        │
                                                                  │
[异常检测] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 实时异常检测：                                                │
  │   │                                                          │
  │   ├─── 阈值检测：                                                │
  │   │   - 响应时间 > P99 + 2×标准差                                 │
  │   │   - 错误率 > 5%                                             │
  │   │   - QPS 异常变化                                             │
  │   │                                                          │
  │   └─── 统计检测：                                                │
  │       - 与历史数据对比                                           │
  │       - 使用控制图（Control Chart）                                │
  │       - 检测异常点                                               │
  │                                                                │
  └─── 趋势异常：                                                  │
      - 使用移动平均                                               │
      - 检测趋势变化                                               │
      - 预测异常                                               │
                                                                  │
[生成告警] ────────────────────────────────────────────────────────┘
```

**2. 智能告警系统流程**

```
指标数据流 ───────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[规则引擎] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 加载告警规则：                                              │
  │   │                                                          │
  │   ├─── 从数据库加载活跃规则                                      │
  │   │                                                          │
  │   └─── 缓存到 Redis                                            │
  │                                                                │
  ├─── 评估规则：                                                  │
  │   │                                                          │
  │   ├─── 对每条规则：                                              │
  │   │   │                                                      │
  │   │   ├─── 检查条件：                                            │
  │   │   │   - 指标名称匹配                                          │
  │   │   │   - 比较操作符（>、<、>=、<=、==）                          │
  │   │   │   - 阈值条件                                            │
  │   │   │   - 标签匹配（如特定 Provider、模型）                       │
  │   │   │                                                      │
  │   │   ├─── 检查持续时间：                                         │
  │   │   │   - 需要持续 N 秒才触发                                   │
  │   │   │   - 避免瞬时波动误报                                      │
  │   │   │                                                      │
  │   │   └─── 检查抑制规则：                                         │
  │   │       - 是否在抑制时间段                                       │
  │   │       - 是否同类告警已发送                                     │
  │   │       - 告警聚合处理                                         │
  │   │                                                          │
  │   └─── 规则示例：                                                │
  │       - 错误率 > 5% 持续 5 分钟 = 严重告警                           │
  │       - 响应时间 P95 > 3000ms 持续 3 分钟 = 警告                     │
  │       - CPU 使用率 > 90% 持续 10 分钟 = 警告                        │
  │       - 成本超预算 = 严重告警                                      │
  │                                                                │
  ▼                                                                │
[告警决策] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 确定严重级别：                                              │
  │   │                                                          │
  │   ├─── 严重（critical）：                                         │
  │   │   - 系统核心功能中断                                           │
  │   │   - 需要立即响应                                             │
  │   │   - 影响：所有用户                                            │
  │   │                                                          │
  │   ├─── 警告（warning）：                                         │
  │   │   - 系统性能下降                                             │
  │   │   - 需要及时处理                                             │
  │   │   - 影响：部分用户                                            │
  │   │                                                          │
  │   └─── 信息（info）：                                             │
  │       - 系统状态变化                                             │
  │       - 需要关注                                                 │
  │       - 影响：无或很小                                           │
  │                                                                │
  ├─── 告警聚合：                                                  │
  │   │                                                          │
  │   ├─── 合并相同类型的告警                                         │
  │   │   - 同一规则在时间窗口内的多次触发合并                           │
  │   │   - 避免告警风暴                                             │
  │   │                                                          │
  │   └─── 上下文关联：                                              │
  │       - 关联相关的告警                                           │
  │       - 提供综合分析                                             │
  │                                                                │
  ▼                                                                │
[发送通知] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 通知渠道：                                                  │
  │   │                                                          │
  │   ├─── 邮件：                                                   │
  │   │   - 严重/警告：立即发送                                      │
  │   │   - 信息：按小时汇总发送                                     │
  │   │   - 包含详细的告警信息和建议                                   │
  │   │                                                          │
  │   ├─── 短信：                                                   │
  │   │   - 仅严重告警                                              │
  │   │   - 简要描述 + 处理链接                                      │
  │   │                                                          │
  │   ├─── Webhook：                                               │
  │   │   - 推送到第三方平台（钉钉、企业微信、Slack）                      │
  │   │   - 自定义消息格式                                           │
  │   │                                                          │
  │   └──── 企业微信：                                               │
  │       - 支持富文本消息                                            │
  │       - 支持卡片式通知                                            │
  │                                                                │
  ├─── 通知策略：                                                  │
  │   │                                                          │
  │   ├─── 分级通知：                                                │
  │   │   - 不同级别不同渠道和频率                                      │
  │   │   - 自动升级机制                                             │
  │   │                                                          │
  │   ├─── 时间抑制：                                                │
  │   │   - 非工作时间不发送信息级告警                                  │
  │   │   - 同一告警最小间隔                                          │
  │   │                                                          │
  │   └─── 人员轮换：                                                │
  │       - 值班人员轮换                                             │
  │       - 升级通知机制                                             │
  │                                                                │
  ▼                                                                │
[自动响应] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 自动处理：                                                  │
  │   │                                                          │
  │   ├─── 严重告警：                                                │
  │   │   - 自动创建工单                                             │
  │   │   - 分配给值班人员                                           │
  │   │   - 发送升级通知（如未及时处理）                                 │
  │   │                                                          │
  │   ├─── 警告告警：                                                │
  │   │   - 记录到监控平台                                           │
  │   │   - 发送通知到值班群                                           │
  │   │                                                          │
  │   └─── 信息告警：                                                │
  │       - 仅记录，不发送通知                                         │
  │       - 用于长期趋势分析                                           │
  │                                                                │
  ├─── 响应模板：                                                  │
  │   │                                                          │
  │   ├─── 工单模板：                                                │
  │   │   - 自动填写工单信息                                           │
  │   │   - 包含告警详情、影响范围、处理建议                              │
  │   │                                                          │
  │   └─── 响应模板：                                                │
  │       - 提供常见问题的处理步骤                                     │
  │       - 链接到知识库                                             │
  │                                                                │
  └─── 知识库沉淀：                                                │
      - 记录处理过程                                               │
      - 总结处理经验                                               │
      - 生成知识文档                                               │
                                                                  │
[记录与跟踪] ──────────────────────────────────────────────────────┘
```

**3. 趋势分析与预测原理**

```
[历史数据收集] ─────────────────────────────────────────────────┐
  │                                                                │
  ├─── 时间序列数据：                                              │
  │   - API 响应时间                                               │
  │   - 请求量（QPS）                                              │
  │   - 错误率                                                    │
  │   - 成本                                                      │
  │   - 资源使用                                                   │
  │                                                                │
  └─── 数据聚合：                                                  │
      - 按小时/天/周聚合                                           │
      - 计算统计值（均值、分位数等）                                 │
                                                                  │
[趋势分析] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 时间序列分析：                                              │
  │   │                                                          │
  │   ├─── 移动平均：                                               │
  │   │   - 简单移动平均（SMA）                                      │
  │   │   - 指数移动平均（EMA）                                      │
  │   │   - 平滑数据，识别趋势                                       │
  │   │                                                          │
  │   ├─── 趋势分解：                                               │
  │   │   - 趋势项（长期趋势）                                        │
  │   │   - 季节项（周期性变化）                                      │
  │   │   - 残差项（随机波动）                                        │
  │   │                                                          │
  │   ├─── 变化点检测：                                              │
  │   │   - 检测趋势变化点                                           │
  │   │   - 识别异常时段                                             │
  │   │                                                          │
  │   └─── 周期性分析：                                              │
  │       - 识别日/周/月周期                                         │
  │       - 业务高峰期预测                                           │
  │                                                                │
  ├─── 异常检测：                                                  │
  │   │                                                          │
  │   ├─── 统计方法：                                                │
  │   │   - Z-score（标准分数）                                      │
  │   │   - IQR（四分位距）                                          │
  │   │   - 3σ 原则                                                │
  │   │                                                          │
  │   ├─── 机器学习方法：                                            │
  │   │   - 孤立森林（Isolation Forest）                              │
  │   │   - One-Class SVM                                          │
  │   │   - LSTM 异常检测                                           │
  │   │                                                          │
  │   └─── 异常模式识别：                                            │
  │       - 识别重复出现的异常模式                                     │
  │       - 根因分析建议                                             │
  │                                                                │
  └─── 相关性分析：                                                │
      - 分析不同指标之间的关联                                         │
      - 因果分析（如成本与请求量的关系）                                │
      - 找出关键影响因素                                             │
                                                                  │
[预测模型] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 预测目标：                                                  │
  │   - 未来需求预测（请求量）                                        │
  │   - 成本预测                                                   │
  │   - 资源需求预测                                               │
  │   - 性能趋势预测                                               │
  │                                                                │
  ├─── 预测方法：                                                  │
  │   │                                                          │
  │   ├─── 简单方法：                                                │
  │   │   - 线性外推                                                │
  │   │   - 移动平均预测                                             │
  │   │                                                          │
  │   ├─── 时间序列模型：                                             │
  │   │   - ARIMA                                                  │
  │   │   - Prophet（Facebook）                                     │
  │   │   - LSTM                                                   │
  │   │                                                          │
  │   └─── 机器学习模型：                                             │
  │       - 回归模型                                                │
  │       - 集成方法（Random Forest、XGBoost）                         │
  │                                                                │
  ├─── 模型训练：                                                  │
  │   │                                                          │
  │   ├─── 使用历史数据训练                                            │
  │   │   - 滚动窗口训练                                             │
  │   │   - 定期更新模型                                             │
  │   │                                                          │
  │   └─── 模型评估：                                                │
  │       - 使用验证集评估                                            │
  │       - 计算 MAPE、MAE、RMSE                                    │
  │       - 95% 预测准确率目标                                        │
  │                                                                │
  └─── 预测输出：                                                  │
      - 未来 7/30/90 天预测                                          │
      - 预测区间（置信区间）                                          │
      - 预测精度评估                                               │
                                                                  │
[容量规划] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 基于预测的容量建议：                                          │
  │   │                                                          │
  │   ├─── 请求量预测 → 需要的 API 实例数量                            │
  │   │   - 考虑高峰时段                                             │
  │   │   - 建议扩展比例                                             │
  │   │                                                          │
  │   ├─── 成本预测 → 预算调整建议                                    │
  │   │   - 预测未来成本                                             │
  │   │   - 建议预算调整                                             │
  │   │                                                          │
  │   ├─── 资源预测 → 基础设施规划                                    │
  │   │   - CPU/内存需求                                            │
  │   │   - 存储空间需求                                             │
  │   │   - 网络带宽需求                                             │
  │   │                                                          │
  │   └─── 模型需求 → 本地模型资源配置                                 │
  │       - GPU 资源需求                                            │
  │       - 模型加载策略                                             │
  │                                                                │
  └─── 优化建议：                                                  │
      - 成本优化建议                                               │
      - 性能优化建议                                               │
      - 架构优化建议                                               │
                                                                  │
[生成报告] ──────────────────────────────────────────────────────┘
```

#### 非功能需求考虑

| 需求类型 | 实现方案 | 性能指标 |
|---------|---------|---------|
| 性能 | 时序数据库 + 批量写入 + 异步处理 | 监控数据更新：<1s |
| 可靠性 | 数据持久化 + 容错处理 | 99.99% 可用性 |
| 可扩展性 | 分片存储 + 水平扩展 | 支持 100 万+ 数据点/秒 |
| 实时性 | WebSocket 推送 + 滑动窗口 | 告警触发延迟：<5s |

---

### 3.4 LocalModel Agent (本地模型管理 Agent)

#### 功能点映射
| 产品需求功能点 | 子功能 | 实现方案 |
|--------------|-------|---------|
| **模型管理** | 模型加载 | ollama.cpp + 按需加载 |
| | 模型卸载 | LRU 策略 + 主动卸载 |
| | 模型缓存 | 内存缓存 + 预加载热门模型 |
| **GPU 资源调度** | GPU 资源分配 | 动态分配 + 碎片整理 |
| | 显存管理 | 精确计算 + 复用优化 |
| | 负载均衡 | 多 GPU 轮询 |
| **混合路由** | 云本混合决策 | 成本/质量/延迟权衡 |
| | 自动切换 | 本地失败切云端 |
| **本地推理** | 推理执行 | ollama API |
| | 性能监控 | 延迟/吞吐量/GPU 使用率 |

#### 数据结构设计

**PostgreSQL 表结构**
```sql
-- 本地模型配置
CREATE TABLE local_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    parameter_size VARCHAR(20) NOT NULL,  -- 1B, 3B, 7B, etc.
    quantization VARCHAR(20) NOT NULL,      -- INT4, INT8, FP16
    family VARCHAR(50),                  -- llama, phi, gemma, etc.
    model_file_path VARCHAR(500),
    download_url VARCHAR(500),
    download_status VARCHAR(20) DEFAULT 'pending',
    file_size_bytes BIGINT,
    loaded BOOLEAN DEFAULT FALSE,
    gpu_required_mb INTEGER DEFAULT 2048,
    max_context_length INTEGER DEFAULT 4096,
    supported_tasks TEXT[],
    performance_metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- GPU 资源池
CREATE TABLE gpu_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gpu_id INTEGER NOT NULL,
    gpu_name VARCHAR(100) NOT NULL,
    total_memory_mb INTEGER NOT NULL,
    available_memory_mb INTEGER NOT NULL,
    allocated_memory_mb INTEGER DEFAULT 0,
    loaded_model_id UUID REFERENCES local_models(id),
    temperature_celsius DECIMAL(5, 2),
    utilization_percent DECIMAL(5, 2),
    status VARCHAR(20) DEFAULT 'available',
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 模型使用记录
CREATE TABLE local_model_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES local_models(id),
    request_id VARCHAR(255),
    user_id VARCHAR(100),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER,
    gpu_memory_used_mb INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 混合路由决策记录
CREATE TABLE hybrid_routing_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255),
    user_id VARCHAR(100),
    complexity_score INTEGER,
    quality_requirement INTEGER,
    is_realtime BOOLEAN,
    gpu_available_mb INTEGER,
    selected_provider_type VARCHAR(20),  -- local, cloud
    selected_model VARCHAR(100),
    decision_reason VARCHAR(200),
    estimated_cost_usd DECIMAL(10, 6),
    actual_cost_usd DECIMAL(10, 6),
    estimated_latency_ms INTEGER,
    actual_latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Redis 数据结构**
```python
# 模型状态
Key: local:model:{model_name}
Type: Hash
Fields:
  - status: str               # unloaded, loading, loaded, error
  - gpu_id: int|null
  - load_time: timestamp
  - last_used: timestamp
  - use_count: int

# GPU 状态
Key: local:gpu:{gpu_id}
Type: Hash (TTL: 5秒)
Fields:
  - available_mb: int
  - temperature: decimal
  - utilization: decimal
  - loaded_model: str|null

# 模型访问统计
Key: local:model:stats:{model_name}
Type: Hash (TTL: 1天)
Fields:
  - request_count: int
  - avg_latency_ms: int
  - total_tokens: int
  - last_used: timestamp
```

#### 核心算法设计（流程图 + 原理介绍）

**1. 模型加载与 GPU 调度流程**

```
推理请求 ─────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[检查模型是否已加载] ─────────────────────────────────────────────┤
  │                                                                │
  ├─── 已加载 ──→ [直接使用]                                     │
  │                                                                │
  └─── 未加载 ──→ [检查 GPU 资源]                                  │
      │                                                          │
      ├─── GPU 可用 ──→ [加载模型]                                 │
      │   │                                                      │
      │   ├─── 计算所需显存                                         │
      │   │   - 基于模型大小和量化级别                                 │
      │   │   - 添加安全边际（10-20%）                               │
      │   │                                                      │
      │   ├─── 选择合适的 GPU                                        │
      │   │   - 显存充足                                             │
      │   │   - 负载最低                                             │
      │   │                                                      │
      │   ├─── 卸载 LRU 模型（如需要）                                │
      │   │   - 识别最久未使用的模型                                   │
      │   │   - 安全卸载（等待当前请求完成）                              │
      │   │                                                      │
      │   └─── 加载模型到 GPU                                        │
      │       - 通过 ollama API 加载                                 │
      │       - 监控加载进度                                           │
      │       - 加载完成后更新状态                                      │
      │                                                          │
      └─── GPU 不可用 ──→ [决策使用云端模型]                          │
                                                                  │
[执行推理] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 调用 ollama API                                            │
  │   │                                                          │
  │   ├─── 构建请求                                                │
  │   │   - model、messages、temperature 等                         │
  │   │                                                          │
  │   ├─── 发送请求                                                │
  │   │   - HTTP/gRPC 通信                                        │
  │   │   - 支持流式响应                                            │
  │   │                                                          │
  │   └─── 接收响应                                                │
  │       - 解析响应内容                                             │
  │       - 提取 token 信息                                         │
  │       - 计算延迟                                               │
  │                                                                │
  ▼                                                                │
[更新状态] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 更新模型状态：                                              │
  │   - last_used 时间                                            │
  │   - use_count                                                │
  │   - avg_latency_ms                                            │
  │                                                                │
  ├─── 更新 GPU 状态：                                              │
  │   - 显存使用                                                   │
  │   - 利用率                                                     │
  │   - 温度                                                       │
  │                                                                │
  └─── 记录使用日志：                                                │
      - 请求详情、性能数据                                           │
                                                                  │
[返回响应] ────────────────────────────────────────────────────────┘
```

**2. 混合路由决策流程**

```
推理请求 ─────────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[内容分析] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 计算复杂度：0-100 分                                         │
  │                                                                │
  ├─── 质量要求：低/中/高                                          │
  │                                                                │
  └─── 是否实时：true/false                                         │
                                                                  │
[检查条件] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── GPU 是否可用？                                               │
  │   │                                                          │
  │   ├─── 是 ──→ 继续                                            │
  │   │                                                          │
  │   └─── 否 ──→ [使用云端模型]                                    │
  │                                                                │
  ├─── 任务复杂度？                                                │
  │   │                                                          │
  │   ├─── 低复杂度（<50）                                         │
  │   │   └─── [优先本地模型]                                       │
  │   │                                                          │
  │   ├─── 中等复杂度（50-80）                                      │
  │   │   └─── [根据质量要求决策]                                    │
  │   │       - 高质量要求 → 云端                                     │
  │   │       - 低质量要求 → 本地（如 7B 模型）                         │
  │   │                                                          │
  │   └─── 高复杂度（>80）                                         │
  │       - [使用云端高质量模型]                                      │
  │                                                                │
  ├─── 实时要求？                                                  │
  │   │                                                          │
  │   ├─── 是 ──→ [优先本地模型]（低延迟）                             │
  │   │                                                          │
  │   └─── 否 ──→ [考虑云端模型]（更高质量）                           │
  │                                                                │
  └─── 成本考虑？                                                  │
      - 成本敏感 → 优先本地模型                                        │
      - 质量优先 → 考虑云端模型                                        │
                                                                  │
[决策树] ────────────────────────────────────────────────────────┤
  │                                                                │
  │   开始                                                        │
  │     │                                                         │
  │     ├─ 复杂度 < 50 且 GPU 可用？                                 │
  │     │   ├─ 是 → 尝试本地 1B-3B 模型                               │
  │     │   │   ├─ 成功 → 使用本地                                   │
  │     │   │   └─ 失败 → 切换云端低成本模型                            │
  │     │   │                                                     │
  │     │   └─ 否 → 使用云端低成本模型                                │
  │     │                                                         │
  │     ├─ 复杂度 50-80 且 实时要求 且 GPU 可用？                       │
  │     │   ├─ 是 → 尝试本地 3B-7B 模型                               │
  │     │   │   ├─ 成功 → 使用本地                                   │
  │     │   │   └─ 失败 → 切换云端中等模型                             │
  │     │   │                                                     │
  │     │   └─ 否 → 选择云端中等模型                                  │
  │     │                                                         │
  │     └─ 复杂度 > 80 或 质量要求 > 90？                             │
  │         ├─ 是 → 使用云端高质量模型                                 │
  │         │                                                     │
  │         └─ 否 → GPU 可用？                                      │
  │             ├─ 是 → 尝试本地 7B 模型                              │
  │             │   ├─ 成功 → 使用本地                               │
  │             │   └─ 失败 → 切换云端默认模型                           │
  │             │                                                 │
  │             └─ 否 → 使用云端默认模型                               │
  │                                                                │
  ▼                                                                │
[执行推理] ────────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 本地推理（通过 ollama）                                     │
  │   │                                                          │
  │   └─── 记录成本：$0.00（零边际成本）                              │
  │                                                                │
  └─── 云端推理（通过 Provider Agent）                               │
      │                                                          │
      └─── 记录成本：按 token 计费                                   │
                                                                  │
[更新决策记录] ──────────────────────────────────────────────────────┘
```

#### 非功能需求考虑

| 需求类型 | 实现方案 | 性能指标 |
|---------|---------|---------|
| 性能 | 模型缓存 + GPU 预热 | 本地推理：<2s（3B 模型） |
| 可靠性 | 自动降级 + 故障切换 | 本地失败自动切云端 |
| 可扩展性 | 多 GPU 支持 | 支持多 GPU 并行 |
| 成本 | 本地零边际成本 | 100% 本地推理节省 |

---

### 3.5 Tools Agent (工具 Agent)

#### 功能点映射
| 产品需求功能点 | 子功能 | 实现方案 |
|--------------|-------|---------|
| **工具管理** | 工具注册 | 动态注册 + 验证 |
| | 工具发现 | 工具目录 + 搜索 |
| | 工具执行 | 安全执行 + 超时控制 |
| **工具调用推理** | 工具选择 | 本地/远端模型推理 |
| | 参数提取 | 结构化解析 |
| | 结果验证 | 结果验证与修正 |

#### 数据结构设计

**PostgreSQL 表结构**
```sql
-- 工具注册表
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    tool_type VARCHAR(50) NOT NULL,  -- http_proxy, database, custom
    description TEXT,
    config JSONB NOT NULL,
    permissions JSONB DEFAULT '[]',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 工具调用记录
CREATE TABLE tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255),
    tool_id UUID REFERENCES tools(id),
    tool_name VARCHAR(100),
    parameters JSONB,
    execution_time_ms INTEGER,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Redis 数据结构**
```python
# 工具缓存
Key: tools:{tool_id}
Type: JSON (TTL: 1小时)
Value: 工具完整配置

# 工具调用统计
Key: tools:stats:{tool_id}
Type: Hash (TTL: 1天)
Fields:
  - call_count: int
  - avg_execution_time_ms: int
  - success_rate: float
```

#### 核心算法设计（流程图 + 原理介绍）

**1. 工具调用流程**

```
工具调用请求 ─────────────────────────────────────────────────────┐
  │                                                                │
  ▼                                                                │
[工具发现与选择] ─────────────────────────────────────────────────┤
  │                                                                │
  ├─── 工具目录查找：                                              │
  │   │                                                          │
  │   ├─── 按名称查找                                                │
  │   │                                                          │
  │   ├─── 按类型查找（HTTP、数据库、自定义）                            │
  │   │                                                          │
  │   └─── 按关键词搜索                                              │
  │                                                                │
  └─── AI 辅助选择（如果需要工具推荐）                                 │
      - 分析用户意图                                                │
      - 推荐合适的工具                                               │
      - 提供工具说明                                                │
                                                                  │
[参数提取与验证] ─────────────────────────────────────────────────┤
  │                                                                │
  ├─── 结构化参数提取：                                             │
  │   │                                                          │
  │   ├─── 使用 LLM 提取参数                                        │
  │   │   - 可以使用本地模型或远端模型                                 │
  │   │   - 简单工具用本地，复杂工具用远端                             │
  │   │                                                          │
  │   └─── 参数验证：                                                │
  │       - 检查必需参数                                             │
  │       - 验证参数类型和范围                                         │
  │       - 清理和规范化参数                                          │
  │                                                                │
  ▼                                                                │
[工具执行] ───────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 获取工具配置：                                                │
  │   │                                                          │
  │   ├─── 从缓存读取（如可用）                                       │
  │   │                                                          │
  │   └─── 从数据库读取                                             │
  │                                                                │
  ├─── 权限检查：                                                  │
  │   │                                                          │
  │   ├─── 检查用户是否有权限调用该工具                                   │
  │   │                                                          │
  │   └─── 检查工具是否启用                                           │
  │                                                                │
  ├─── 安全执行：                                                  │
  │   │                                                          │
  │   ├─── HTTP 代理工具：                                            │
  │   │   │                                                      │
  │   │   ├─── 验证 URL（白名单）                                    │
  │   │   │                                                      │
  │   │   ├─── 设置超时（默认 30 秒）                                   │
  │   │   │                                                      │
  │   │   └─── 限制响应大小（默认 10MB）                                 │
  │   │                                                          │
  │   ├─── 数据库工具：                                               │
  │   │   │                                                      │
  │   │   ├─── 验证 SQL 注入                                         │
  │   │   │                                                      │
  │   │   ├─── 限制查询结果数量                                        │
  │   │   │                                                      │
  │   │   └─── 使用只读账户（如可能）                                   │
  │   │                                                          │
  │   └─── 自定义工具：                                               │
  │       │                                                      │
  │       ├─── 沙箱执行环境                                           │
  │       │                                                      │
  │       ├─── 资源限制（CPU、内存）                                    │
  │       │                                                      │
  │       └─── 超时控制                                              │
  │                                                                │
  └─── 结果处理：                                                  │
      │                                                          │
      ├─── 解析工具响应                                             │
      │                                                          │
      ├─── 验证结果格式                                             │
      │                                                          │
      └─── 返回结构化结果                                             │
                                                                  │
[记录与监控] ──────────────────────────────────────────────────────┤
  │                                                                │
  ├─── 记录调用日志：                                                │
  │   - 工具 ID、参数、执行时间、结果                                   │
  │                                                                │
  └─── 更新统计信息：                                                │
      - 调用次数、成功率、平均执行时间                                   │
                                                                  │
[返回结果] ────────────────────────────────────────────────────────┘
```

#### 非功能需求考虑

| 需求类型 | 实现方案 | 性能指标 |
|---------|---------|---------|
| 性能 | 工具缓存 + 异步执行 | 工具调用：<500ms（简单工具） |
| 安全性 | 白名单 + 沙箱 + 注入防护 | 防止恶意代码执行 |
| 可扩展性 | 动态注册 + 插件化 | 支持自定义工具 |

---

## 四、非功能需求汇总

### 4.1 性能需求

| 组件 | 指标 | 目标值 |
|------|------|--------|
| Gateway Orchestrator | 开关切换延迟 | <10ms |
| Routing Agent | 路由决策时间 | <50ms |
| Provider Agent | API 调用额外延迟 | <5ms |
| Cost Agent | 成本计算时间 | <10ms |
| Security Agent | 安全检测时间 | <15ms |
| Analytics Agent | 监控数据更新 | <1s |
| LocalModel Agent | 本地推理延迟 | <2s（3B 模型） |
| Tools Agent | 工具调用延迟 | <500ms（简单工具） |

### 4.2 可靠性需求

| 组件 | 目标可用性 | 故障恢复时间 |
|------|-----------|-------------|
| 整体系统 | 99.99% | <30秒 |
| Routing Agent | 99.995% | 自动降级 <5秒 |
| Provider Agent | 99.99% | 故障转移 <3秒 |
| Security Agent | 99.999% | 立即 |
| Analytics Agent | 99.99% | <1分钟 |

### 4.3 安全需求

| 需求 | 实现方案 |
|------|---------|
| 传输加密 | TLS 1.3 |
| 存储加密 | AES-256 |
| 密钥轮换 | 90天自动轮换 |
| 访问控制 | RBAC + ABAC |
| 审计日志 | 完整记录 |

### 4.4 可扩展性需求

| 组件 | 扩展方式 | 支持规模 |
|------|---------|---------|
| 整体系统 | 水平扩展 | 20,000+ QPS |
| 数据存储 | 分片 | 20TB+ |
| 规则配置 | 动态加载 | 1,000+ 规则 |
| IP 规则 | 分布式存储 | 100 万+ |

---

## 五、修改文件清单

需要修改的系统设计文件：

| 文件路径 | 修改内容 |
|---------|---------|
| `/Users/zhuzhichao/Documents/code/github/llm-router/llm-router-system-design.md` | 用上述详细实现方案更新各 Agent 部分 |

---

## 六、验收标准

实现完成后，应满足以下验收标准：

1. **功能完整性**：每个 Agent 的实现方案覆盖产品需求文档中的所有相关功能点
2. **非功能需求满足**：性能、可靠性、安全性、可扩展性指标均满足需求
3. **架构一致性**：总体架构保持不变，各 Agent 协作方式符合原设计
4. **可执行性**：实现方案具备足够的细节，可以直接用于开发

---

---

## 七、架构改进：功能分离优化（2024年更新）

### 7.1 改进背景

为优化系统架构和用户体验，对前端功能模块进行了重新划分：

- **原设计**：模型接入页面包含API连接配置和优先级/负载均衡配置
- **问题**：功能职责不清，模型接入和路由策略混合在一起
- **新设计**：功能分离，各司其职

### 7.2 功能模块划分

#### 7.2.1 模型接入页面（Provider配置）

**职责**：负责大模型API的接入配置

**功能范围**：
- 添加/编辑/删除模型Provider
- 配置API连接信息（Base URL、API Key、Region等）
- 配置连接参数（超时时间、重试次数等）
- 查看Provider健康状态

**移除的功能**：
- ~~优先级配置~~ → 迁移到路由配置页面
- ~~负载均衡权重~~ → 迁移到路由配置页面

**保留的字段**：
- name: Provider名称
- provider_type: Provider类型（openai/anthropic/custom）
- base_url: API基础URL
- api_key: API密钥（加密存储）
- region: 区域
- organization: 组织ID
- timeout: 超时时间（秒）
- max_retries: 最大重试次数
- status: 状态（active/inactive/unhealthy）

#### 7.2.2 路由配置页面

**职责**：负责智能路由策略和模型选择配置

**功能范围**：
1. **路由开关控制**
   - 启用/禁用智能路由
   - 查看路由状态和历史

2. **路由规则管理**
   - 创建/编辑/删除路由规则
   - 配置匹配条件（正则表达式、复杂度等）
   - 配置路由动作（使用特定模型/Provider）

3. **模型优先级与负载均衡配置**（新增）
   - 为每个模型配置优先级（priority）
   - 为每个模型配置负载均衡权重（weight）
   - 可视化展示所有模型的配置状态

### 7.3 前端实现改动

#### 7.3.1 模型接入页面（`/frontend/src/pages/Providers/index.tsx`）

**移除的字段**：
```typescript
// 表单中移除
- priority: 优先级
- weight: 负载均衡权重

// 表格列中移除
- 优先级列
- 权重列

// 初始化时移除
setEditingProvider({ status: 'active' }); // 不再包含 priority 和 weight
```

**保留的功能**：
- Provider基本信息配置
- 健康检查
- API连接测试

#### 7.3.2 路由配置页面（`/frontend/src/pages/Routing/index.tsx`）

**新增的功能模块**：
```typescript
// 新增状态
const [models, setModels] = React.useState<Array<ProviderModel & { 
  providerName: string; 
  providerPriority: number; 
  providerWeight: number 
}>>([]);
const [modelModalVisible, setModelModalVisible] = React.useState(false);
const [editingModel, setEditingModel] = React.useState<Partial<typeof models[0]> | null>(null);
const [modelForm] = Form.useForm();

// 新增函数
const handleEditModel = (model: typeof models[0]) => { ... };
const handleModelModalOk = async () => { ... };

// 新增表格列
const modelColumns = [
  { title: '模型ID', dataIndex: 'model_id' },
  { title: '模型名称', dataIndex: 'name' },
  { title: 'Provider', dataIndex: 'providerName' },
  { title: '优先级', dataIndex: 'providerPriority' },
  { title: '负载权重', dataIndex: 'providerWeight' },
  { title: '操作', key: 'action' }
];
```

**新增的UI组件**：
1. 模型优先级与负载均衡配置卡片
2. 模型配置模态框（配置优先级和权重）

### 7.4 后端API说明

**使用的现有API**：
- `GET /api/v1/providers` - 获取Provider列表（包含priority和weight）
- `PUT /api/v1/providers/{id}` - 更新Provider配置（可更新priority和weight）
- `GET /api/v1/providers/{id}/models` - 获取Provider的模型列表

**数据流**：
1. 路由配置页面调用Provider API获取所有Provider
2. 遍历每个Provider获取其模型列表
3. 合并Provider的priority和weight到模型数据中
4. 在表格中展示
5. 用户点击"配置"按钮打开模态框
6. 提交时调用Provider Update API更新priority和weight

### 7.5 用户体验改进

#### 改进前：
- 用户需要在模型接入页面配置优先级和权重
- 概念混淆：不知道这些参数用于什么
- 配置分散：路由规则和模型优先级在不同位置

#### 改进后：
- 模型接入页面专注于API连接配置
- 路由配置页面统一管理所有路由相关配置
- 功能职责清晰，用户更容易理解
- 配置集中，管理更方便

### 7.6 数据库schema说明

**Provider表**（保持不变）：
```sql
CREATE TABLE providers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT,
    base_url VARCHAR(500) NOT NULL,
    region VARCHAR(100),
    organization VARCHAR(200),
    timeout INTEGER DEFAULT 60,
    max_retries INTEGER DEFAULT 3,
    status VARCHAR(20) DEFAULT 'active',
    priority INTEGER DEFAULT 100,  -- 用于路由选择
    weight INTEGER DEFAULT 100,    -- 用于负载均衡
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**注意**：
- `priority` 和 `weight` 字段保留在Provider表中
- 前端通过路由配置页面来管理这些字段
- 模型接入页面不再显示这些字段

### 7.7 文件修改清单

**前端文件**：
1. `/frontend/src/pages/Providers/index.tsx` - 移除priority和weight相关代码
2. `/frontend/src/pages/Routing/index.tsx` - 添加模型优先级配置功能
3. `/frontend/src/components/Layout/index.tsx` - 更新侧边栏菜单文字

**后端文件**：
- 无需修改，使用现有API

**文档文件**：
1. `/doc/llm-router-system-design.md` - 添加本节内容

---

## 八、版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 1.0 | 2024-01 | 初始版本 | System |
| 1.1 | 2024-02 | 功能分离优化：模型接入与路由配置分离 | System |

