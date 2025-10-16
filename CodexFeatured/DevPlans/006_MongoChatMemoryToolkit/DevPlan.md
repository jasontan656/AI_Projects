# 开发计划：客户对话数据服务工具

标识信息：INTENT_TITLE_2_4=MongoChatMemoryToolkit；COUNT_3D=006；生成时间=2025-10-15 20:17:23
需求文档：D:/AI_Projects/CodexFeatured/DevPlans/006_MongoChatMemoryToolkit/DemandDescription.md
输出路径：D:/AI_Projects/CodexFeatured/DevPlans/006_MongoChatMemoryToolkit/DevPlan.md

---

## 1. 项目概述

### 1.1 需求摘要
客户对话数据服务工具旨在为终端客服、业务智能体和数据治理团队提供一致的历史对话资产。系统需要对个人与群组渠道的消息进行全生命周期管理，从实时捕获、短期缓存、持久化沉淀到语义索引，确保任意角色都能在毫秒级获取到准确的上下文。在现有多渠道客服体系中，历史数据分散、画像缺失、审计薄弱导致智能体答复不稳定，本项目通过三层存储架构与标准化接口，构建统一的数据入口，强化结构化查询与语义检索能力，满足精细化服务与合规审计双重诉求。同时，需求强调画像维护与高价值对话归档，要求工具支持事件驱动与批量调度并存的运行模式，并对性能、质量、可观测性做出量化约束。

### 1.2 开发目标
1. 提供高吞吐的会话采集接口，支撑 Redis 热缓存与 MongoDB 主存储的协同写入，并在 Redis 异常时自动降级到直接持久化。
2. 构建统一的历史查询与语义检索 API，服务人工客服与智能体，对应结构化检索与向量相似度检索双链路。
3. 建立客户与群组画像管理能力，支持字段级审计与冲突补齐任务，确保画像准确率与留档周期达标。
4. 实现导出与复盘服务，为管理人员提供按时间段、客户、群组维度的导出文件及周报数据。
5. 落实安全、合规、可观测性要求，包括脱敏流水线、访问审计、指标监控与异常报警，满足项目约束。

### 1.3 项目类型
单体后端应用（FastAPI + Celery 背景任务），部署于现有 Kobe 服务体系内。接口层以 HTTP API 为主，辅助异步任务链路处理耗时操作。

---
## 2. 架构设计

### 2.1 功能域划分
- **会话采集与缓存域**：负责接收个人及群组消息，将内容写入 Redis 热缓存并触发批量持久化任务，保障实时性并维持缓存命中率指标。
- **数据持久化与查询域**：将对话与画像数据写入 MongoDB，提供条件丰富的结构化查询接口，并维护索引策略与数据分片；在降级模式下直接承担写入职责。
- **语义索引与检索域**：管理向量化流水线、Chroma collection 与查询代理，服务智能体的语义检索需求并负责降级策略，确保召回与准确率达标。
- **画像治理域**：处理客户与群组画像的创建、更新、冲突检测、版本留存，并与消息记录保持一致性，支撑补齐和审计任务。
- **复盘导出与报表域**：生成复盘摘要、导出档案、周报指标，为运营与管理提供可读数据输出，并与任务队列协作处理长耗时操作。
- **安全审计与合规模块**：落实脱敏、访问控制、审计日志，协调权限校验与合规留痕，确保所有操作可追踪。
- **可观测性与运行保障域**：采集日志、指标、追踪信息，对性能指标与异常场景进行报警，支撑降级决策与周报输出。

### 2.2 模块清单

#### 模块1：routers/ingestion.py
- **路径**：`Kobe/MongoChatMemoryToolkit/routers/ingestion.py`
- **职责**：暴露消息接入与批量导入 HTTP 路由，接收来自聊天渠道或调度任务的消息，执行参数校验、鉴权、节流控制，再将合法请求委派给采集服务；兼容个人与群组两类入口，并将异常转化为可审计错误响应，保证调用者得到明确反馈。
- **输入**：单条或批量消息载荷、来源渠道标识、调用主体凭证、幂等键。
- **输出**：标准化确认响应（Redis 写入成功/降级路径）、失败时的 JSON 错误码与 request_id。
- **依赖**：`services.ingestion`, `utils.auth`, `utils.masking`, `SharedUtility.RichLogger`。
- **是否复用**：否（新建）。

#### 模块2：routers/history.py
- **路径**：`Kobe/MongoChatMemoryToolkit/routers/history.py`
- **职责**：提供结构化历史查询、语义检索触发及降级查询接口，按照业务角色控制字段可见性，统一分页、排序、时间窗口逻辑，并对外返回带有检索统计的响应体，保障人工客服与智能体都能获取稳定结果。
- **输入**：查询条件（用户/群组 ID、时间范围、关键词、语义检索开关）、分页参数、调用方角色。
- **输出**：结构化 JSON 结果集，包括消息列表、上下文摘要、检索命中率等统计信息。
- **依赖**：`services.retrieval`, `services.semantic`, `models.search`, `SharedUtility.RichLogger`。
- **是否复用**：否（新建）。

#### 模块3：routers/profile.py
- **路径**：`Kobe/MongoChatMemoryToolkit/routers/profile.py`
- **职责**：提供客户与群组画像的读取、增量更新、冲突审计接口，协调外部画像消费方的读写协议，记录变更原因并按策略触发补齐任务，实现字段级合规可追踪。
- **输入**：画像查询条件、更新指令、版本信息、调用方凭证。
- **输出**：画像详情、变更确认、审计 token 用于追溯。
- **依赖**：`services.profile`, `models.profiles`, `utils.auth`, `SharedUtility.RichLogger`。
- **是否复用**：否（新建）。

#### 模块4：routers/export.py
- **路径**：`Kobe/MongoChatMemoryToolkit/routers/export.py`
- **职责**：实现复盘导出、周报生成等接口，支持同步预览与异步任务模式，负责写入导出任务队列并返回追踪 ID，以免阻塞接口线程，在导出完成后联动通知通道。
- **输入**：导出参数（客户/群组列表、时间区间、格式类型）、通知目标、调用方信息。
- **输出**：导出任务受理结果、同步预览片段或异步下载链接。
- **依赖**：`services.reporting`, `tasks.report_generation`, `SharedUtility.TaskQueue`, `SharedUtility.RichLogger`。
- **是否复用**：部分复用 `SharedUtility.TaskQueue`。

#### 模块5：services/ingestion.py
- **路径**：`Kobe/MongoChatMemoryToolkit/services/ingestion.py`
- **职责**：封装消息入队主流程，包括字段脱敏、写入 Redis、聚合批次、调度 Celery 任务，内建 backpressure 策略与异常降级逻辑，保障在高峰期仍能满足写入 SLA。
- **输入**：标准化消息模型、写入策略参数、追踪上下文。
- **输出**：写入状态对象（成功、降级、失败详情）、批次事件通知。
- **依赖**：`models.messages`, `services.persistence`, `tasks.cache_sync`, `SharedUtility.TaskQueue`, `SharedUtility.RichLogger`。
- **是否复用**：复用 `SharedUtility.TaskQueue`。

#### 模块6：services/persistence.py
- **路径**：`Kobe/MongoChatMemoryToolkit/services/persistence.py`
- **职责**：提供对 MongoDB 的数据访问封装，涵盖集合管理、批量写入、索引维护、分页查询，处理事务性批量写入与回滚，并输出审计日志。
- **输入**：消息批次、画像更新指令、查询条件对象。
- **输出**：数据库写入结果、游标对象、集合统计信息。
- **依赖**：`models.messages`, `models.profiles`, `SharedUtility.RichLogger`。
- **是否复用**：否（新建）。

#### 模块7：services/retrieval.py
- **路径**：`Kobe/MongoChatMemoryToolkit/services/retrieval.py`
- **职责**：实现结构化历史查询协调器，整合 MongoDB、Redis 数据，执行排序、分页、脱敏过滤，并向语义检索链路提供降级 fallback。
- **输入**：`HistoryQuery` 模型、角色上下文、性能参数。
- **输出**：消息列表、分页指针、统计元数据。
- **依赖**：`services.persistence`, `models.search`, `utils.masking`, `SharedUtility.RichLogger`。
- **是否复用**：否（新建）。

#### 模块8：services/semantic.py
- **路径**：`Kobe/MongoChatMemoryToolkit/services/semantic.py`
- **职责**：管理向量化与语义检索服务端逻辑，对接 Chroma 客户端与 LangChain 检索链，负责构建查询过滤、结果重排序、阈值策略与降级处理，并统计召回指标。
- **输入**：`SemanticSearchRequest`、嵌入模型配置、召回策略。
- **输出**：`SemanticSearchResponse`、命中率统计、降级标记。
- **依赖**：`tasks.vectorization`, `utils.transformers`, `SharedUtility.TaskQueue`, `SharedUtility.RichLogger`。
- **是否复用**：部分复用 `SharedUtility.TaskQueue`。

#### 模块9：services/profile.py
- **路径**：`Kobe/MongoChatMemoryToolkit/services/profile.py`
- **职责**：管理画像生命周期，包括字段映射、冲突检测、版本化记录、补齐任务调度，确保画像数据与对话记录一致并满足审计要求。
- **输入**：`ProfileUpsertRequest`、画像规则配置、版本号。
- **输出**：更新确认对象、需补齐字段列表、审计事件。
- **依赖**：`models.profiles`, `tasks.profile_repair`, `services.persistence`, `SharedUtility.RichLogger`。
- **是否复用**：否（新建）。

#### 模块10：services/reporting.py
- **路径**：`Kobe/MongoChatMemoryToolkit/services/reporting.py`
- **职责**：整合历史数据与画像信息，生成复盘摘要、导出文件内容与周报指标，处理导出格式转换、进度回写与通知触发，确保长耗时作业不会阻塞接口。
- **输入**：导出参数对象、查询结果集、模板配置。
- **输出**：导出文件路径、摘要数据、任务状态。
- **依赖**：`services.retrieval`, `services.profile`, `tasks.report_generation`, `SharedUtility.TaskQueue`, `SharedUtility.RichLogger`。
- **是否复用**：复用 `SharedUtility.TaskQueue`。

#### 模块11：services/observability.py
- **路径**：`Kobe/MongoChatMemoryToolkit/services/observability.py`
- **职责**：封装指标采集、日志埋点、追踪上下文生成，统一对接 Prometheus/OpenTelemetry，向周报提供指标拉取接口，确保关键事件日志覆盖率与性能指标采集满足要求。
- **输入**：事件类型、指标数值、上下文标签。
- **输出**：日志记录、metrics 推送、trace span。
- **依赖**：`SharedUtility.RichLogger`, `Kobe/api/bridge_logger`, `Kobe/tools/langchain_tools`。
- **是否复用**：复用 `SharedUtility.RichLogger`。

#### 模块12：tasks/vectorization.py
- **路径**：`Kobe/MongoChatMemoryToolkit/tasks/vectorization.py`
- **职责**：定义向量化 Celery 任务，批量处理消息文本生成嵌入，写入 Chroma，并回传成功率，支持重试、幂等与链式编排，满足 Backend Constitution 的调度规范。
- **输入**：消息批次 ID、消息内容列表、向量化配置。
- **输出**：嵌入写入统计、失败明细。
- **依赖**：`services.persistence`, `utils.transformers`, `SharedUtility.TaskQueue`, `SharedUtility.RichLogger`。
- **是否复用**：复用 `SharedUtility.TaskQueue`。

#### 模块13：tasks/cache_sync.py
- **路径**：`Kobe/MongoChatMemoryToolkit/tasks/cache_sync.py`
- **职责**：负责 Redis 与 MongoDB 之间的同步任务，包括缓存写出、缓存重建、超时降级执行，保障缓存命中率，同时在 Redis 故障时触发降级直写逻辑。
- **输入**：缓存批次描述、操作类型、重试策略。
- **输出**：同步执行结果、重试计划、告警事件。
- **依赖**：`services.ingestion`, `services.persistence`, `SharedUtility.TaskQueue`, `SharedUtility.RichLogger`。
- **是否复用**：复用 `SharedUtility.TaskQueue`。

#### 模块14：tasks/profile_repair.py
- **路径**：`Kobe/MongoChatMemoryToolkit/tasks/profile_repair.py`
- **职责**：定义画像补齐与审计 Celery 任务，扫描缺失字段或冲突记录，协调外部数据源校验并回写审计日志，确保画像补齐时效指标。
- **输入**：画像实体列表、缺失字段清单、重试策略。
- **输出**：补齐结果、冲突报告、审计引用 ID。
- **依赖**：`services.profile`, `services.persistence`, `SharedUtility.TaskQueue`, `SharedUtility.RichLogger`。
- **是否复用**：复用 `SharedUtility.TaskQueue`。

#### 模块15：tasks/report_generation.py
- **路径**：`Kobe/MongoChatMemoryToolkit/tasks/report_generation.py`
- **职责**：负责复盘导出与周报生成 Celery 任务，执行数据聚合、模板渲染、文件生成与上传，期间记录进度并在失败时重试或通知人工介入，确保导出成功率与时效指标达成。
- **输入**：导出请求参数、模板 ID、目标存储信息。
- **输出**：导出文件路径、生成耗时、失败明细。
- **依赖**：`services.reporting`, `services.retrieval`, `SharedUtility.TaskQueue`, `SharedUtility.RichLogger`。
- **是否复用**：复用 `SharedUtility.TaskQueue`。

#### 模块16：models/messages.py
- **路径**：`Kobe/MongoChatMemoryToolkit/models/messages.py`
- **职责**：定义消息相关 Pydantic 模型，涵盖单条消息、批量写入、缓存项结构与脱敏标记，供接口层与服务层一致验证与序列化。
- **输入**：原始消息载荷、来源渠道元数据。
- **输出**：合法化消息模型实例、字段验证错误。
- **依赖**：`pydantic`, `datetime`, `enum`。
- **是否复用**：否（新建）。

#### 模块17：models/profiles.py
- **路径**：`Kobe/MongoChatMemoryToolkit/models/profiles.py`
- **职责**：定义客户与群组画像模型、版本记录、冲突条目与补齐任务载荷，支持字段级描述与验证规则，确保画像治理一致。
- **输入**：画像更新请求、历史版本数据。
- **输出**：标准化画像对象、待补齐字段集合。
- **依赖**：`pydantic`, `typing`, `datetime`。
- **是否复用**：否（新建）。

#### 模块18：models/search.py
- **路径**：`Kobe/MongoChatMemoryToolkit/models/search.py`
- **职责**：封装历史查询与语义检索请求/响应模型，统一分页、排序、阈值参数，提供响应数据结构供路由直接返回。
- **输入**：查询参数、检索策略。
- **输出**：查询响应、统计摘要、降级标记。
- **依赖**：`pydantic`, `typing`。
- **是否复用**：否（新建）。

#### 模块19：models/audit.py
- **路径**：`Kobe/MongoChatMemoryToolkit/models/audit.py`
- **职责**：定义审计事件、访问记录、脱敏流水线日志模型，与 observability 模块共享字段约定，为合规检查提供结构化数据。
- **输入**：访问事件、操作主体信息。
- **输出**：审计记录对象、序列化结构。
- **依赖**：`pydantic`, `uuid`, `datetime`。
- **是否复用**：否（新建）。

#### 模块20：utils/auth.py
- **路径**：`Kobe/MongoChatMemoryToolkit/utils/auth.py`
- **职责**：封装角色鉴权、租户隔离校验、细粒度字段访问控制逻辑，对接已有身份系统，确保访问控制符合合规要求并生成审计 token。
- **输入**：请求上下文、角色声明、操作类型。
- **输出**：鉴权结果、拒绝原因、审计 token。
- **依赖**：`Kobe/api/mcp_routes`, `SharedUtility.RichLogger`。
- **是否复用**：部分复用既有权限模式。

#### 模块21：utils/masking.py
- **路径**：`Kobe/MongoChatMemoryToolkit/utils/masking.py`
- **职责**：集中脱敏策略（手机号、邮箱、地理位置等），在写入和查询返回时执行，确保脱敏覆盖率与审计追踪并输出掩码摘要。
- **输入**：消息内容、画像字段、脱敏规则。
- **输出**：脱敏后的数据对象、脱敏日志。
- **依赖**：`re`, `pydantic`, `SharedUtility.RichLogger`。
- **是否复用**：否（新建）。

#### 模块22：utils/transformers.py
- **路径**：`Kobe/MongoChatMemoryToolkit/utils/transformers.py`
- **职责**：提供文本归一化、语言检测、向量化前处理、摘要生成工具，供向量化任务与导出模块复用，并对处理过程输出指标。
- **输入**：原始文本、消息元数据。
- **输出**：清洗文本、摘要、向量化输入。
- **依赖**：`langchain`, `SharedUtility.RichLogger`。
- **是否复用**：否（新建）。

#### 模块23：config.py
- **路径**：`Kobe/MongoChatMemoryToolkit/config.py`
- **职责**：集中管理配置项（Redis、MongoDB、Chroma 连接、向量化参数、脱敏规则开关），使用 pydantic-settings 读取 `.env` 并暴露类型安全配置对象。
- **输入**：环境变量、默认配置。
- **输出**：配置对象实例、校验错误。
- **依赖**：`pydantic_settings`, `os`, `typing`。
- **是否复用**：否（新建）。

### 2.3 架构分层
```
┌─────────────────────────────────────┐
│         接口层 (FastAPI Routers)    │ routers.ingestion/history/profile/export
├─────────────────────────────────────┤
│         业务层 (Domain Services)    │ services.ingestion/persistence/retrieval/semantic/profile/reporting/observability
├─────────────────────────────────────┤
│         数据层 (Models & Repos)     │ models.* + services.persistence + config
├─────────────────────────────────────┤
│    基础设施层 (Redis/Mongo/Chroma)  │ SharedUtility.TaskQueue、外部存储与向量化任务
└─────────────────────────────────────┘
```
- **接口层**：负责请求校验、鉴权、速率限制、响应封装，严禁直接操作数据库或任务队列。
- **业务层**：实现领域流程、批处理策略、异常降级与指标采集，协调多域协作，执行业务决策。
- **数据层**：提供结构化模型、数据访问、索引策略，实现写入一致性与查询效率，维护数据血缘。
- **基础设施层**：统一封装 Redis、MongoDB、Chroma 客户端与 Celery 调度，借助 SharedUtility 管理日志与任务。

### 2.4 数据流设计
```
[外部渠道消息]
   ↓ (routers.ingestion)
[参数校验 + 鉴权] → [脱敏处理]
   ↓
[Redis 热缓存写入] → [缓存命中率监控]
   ↓ (触发条件：静默 5 分钟/批量条数)
[Celery 批量持久化任务]
   ↓                         ↘
[MongoDB 持久化]            [向量化任务 → ChromaDB 向量存储]
   ↓                         ↘
[画像更新触发]            [语义索引刷新]
   ↓                         ↘
[版本记录 & 审计]        [指标上报]

查询侧：
[客户端发起查询] → [routers.history/profile]
   ↓
[services.retrieval / semantic 策略决策]
   ↓
[Redis 缺省 → MongoDB 补齐 → Chroma 语义检索]
   ↓
[结果整合、脱敏、排序]
   ↓
[响应 + 可观测数据 + 审计日志]

降级链路：
[语义检索超时] → [结构化查询回退] → [告警 & 重试排程]
```
关键转换点：
1. 入站消息写入 Redis 前执行字段级脱敏并生成脱敏摘要，供审计核查；
2. Redis 批量刷写任务在进入 MongoDB 前进行幂等与序号校验，避免重复写入；
3. 向量化任务完成后更新消息记录的 `vector_version` 字段，确保检索一致；
4. 查询响应阶段根据角色过滤敏感字段与隐私信息，并附带审计引用 ID；
5. 全流程通过 observability 模块上报日志、指标与 trace，支持周报输出。

---
## 3. 目录结构规划

### 3.1 完整目录树
```
Kobe/
├── MongoChatMemoryToolkit/
│   ├── __init__.py
│   ├── config.py
│   ├── index.yaml
│   ├── models/
│   │   ├── __init__.py
│   │   ├── messages.py
│   │   ├── profiles.py
│   │   ├── search.py
│   │   └── audit.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── ingestion.py
│   │   ├── history.py
│   │   ├── profile.py
│   │   └── export.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ingestion.py
│   │   ├── persistence.py
│   │   ├── retrieval.py
│   │   ├── semantic.py
│   │   ├── profile.py
│   │   ├── reporting.py
│   │   └── observability.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── vectorization.py
│   │   ├── cache_sync.py
│   │   ├── profile_repair.py
│   │   └── report_generation.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── masking.py
│   │   └── transformers.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── README.md
│   └── tests/
│       ├── __init__.py
│       ├── test_ingestion.py
│       ├── test_retrieval.py
│       ├── test_profiles.py
│       ├── test_semantic.py
│       └── fixtures.py
└── SharedUtility/
    └── （复用既有 RichLogger、TaskQueue，无结构调整）
```

### 3.2 文件职责说明

| 文件路径 | 职责 | 是否新建 |
|---------|------|---------|
| `Kobe/MongoChatMemoryToolkit/config.py` | 汇总 Redis/MongoDB/Chroma 连接、阈值、脱敏策略的配置对象，供模块统一引用 | 是 |
| `Kobe/MongoChatMemoryToolkit/index.yaml` | 记录模块元数据、上下游依赖，保证项目能力地图更新 | 是 |
| `Kobe/MongoChatMemoryToolkit/models/messages.py` | 定义消息、批量请求、缓存项等 Pydantic 模型 | 是 |
| `Kobe/MongoChatMemoryToolkit/models/profiles.py` | 定义用户与群组画像数据结构及版本化模型 | 是 |
| `Kobe/MongoChatMemoryToolkit/models/search.py` | 定义查询与检索参数、响应结构 | 是 |
| `Kobe/MongoChatMemoryToolkit/models/audit.py` | 定义审计事件、访问日志模型 | 是 |
| `Kobe/MongoChatMemoryToolkit/routers/ingestion.py` | FastAPI 路由，处理消息接入、批量导入请求 | 是 |
| `Kobe/MongoChatMemoryToolkit/routers/history.py` | 历史查询、语义检索、降级接口 | 是 |
| `Kobe/MongoChatMemoryToolkit/routers/profile.py` | 画像读取与更新接口 | 是 |
| `Kobe/MongoChatMemoryToolkit/routers/export.py` | 导出和周报任务接口 | 是 |
| `Kobe/MongoChatMemoryToolkit/services/ingestion.py` | 消息采集核心逻辑（缓存写入、批处理、降级） | 是 |
| `Kobe/MongoChatMemoryToolkit/services/persistence.py` | MongoDB 数据访问封装、索引管理 | 是 |
| `Kobe/MongoChatMemoryToolkit/services/retrieval.py` | 结构化查询协调器 | 是 |
| `Kobe/MongoChatMemoryToolkit/services/semantic.py` | 向量检索与降级策略实现 | 是 |
| `Kobe/MongoChatMemoryToolkit/services/profile.py` | 画像治理逻辑、冲突检测、任务触发 | 是 |
| `Kobe/MongoChatMemoryToolkit/services/reporting.py` | 导出、周报汇总与模板拼装 | 是 |
| `Kobe/MongoChatMemoryToolkit/services/observability.py` | 指标、日志、Trace 采集封装 | 是 |
| `Kobe/MongoChatMemoryToolkit/tasks/vectorization.py` | Celery 向量化任务定义 | 是 |
| `Kobe/MongoChatMemoryToolkit/tasks/cache_sync.py` | Redis ↔ MongoDB 同步任务 | 是 |
| `Kobe/MongoChatMemoryToolkit/tasks/profile_repair.py` | 画像补齐与审计任务 | 是 |
| `Kobe/MongoChatMemoryToolkit/tasks/report_generation.py` | 导出文件生成与通知任务 | 是 |
| `Kobe/MongoChatMemoryToolkit/utils/auth.py` | 鉴权、角色控制、租户隔离 | 是 |
| `Kobe/MongoChatMemoryToolkit/utils/masking.py` | 敏感字段脱敏、日志标记 | 是 |
| `Kobe/MongoChatMemoryToolkit/utils/transformers.py` | 文本预处理、摘要生成、向量化前处理 | 是 |
| `Kobe/MongoChatMemoryToolkit/tests/test_ingestion.py` | 入站流程单元与集成测试 | 是 |
| `Kobe/MongoChatMemoryToolkit/tests/test_retrieval.py` | 查询及降级链路测试 | 是 |
| `Kobe/MongoChatMemoryToolkit/tests/test_profiles.py` | 画像治理与补齐任务测试 | 是 |
| `Kobe/MongoChatMemoryToolkit/tests/test_semantic.py` | 向量检索与召回测试 | 是 |
| `Kobe/MongoChatMemoryToolkit/tests/fixtures.py` | 测试通用数据与客户端工厂 | 是 |

### 3.3 配置文件规划
- **Kobe/MongoChatMemoryToolkit/config.py**：主配置文件，使用 pydantic-settings 加载环境变量，提供 Redis/MongoDB/Chroma/TaskQueue 参数、阈值、脱敏开关与降级策略设置。
- **Kobe/.env（现有）**：新增键值（待 TechDecisions 给出默认值）：`REDIS_URL`, `MONGODB_URI`, `CHROMADB_URL`, `CHAT_MEMORY_VECTOR_COLLECTION_INDIVIDUAL`, `CHAT_MEMORY_VECTOR_COLLECTION_GROUP`, `CHAT_MEMORY_CACHE_TTL_SECONDS`, `CHAT_MEMORY_WRITE_BATCH_SIZE`, `CHAT_MEMORY_VECTOR_EMBED_MODEL`, `CHAT_MEMORY_EXPORT_BUCKET`。
- **Kobe/MongoChatMemoryToolkit/logging_config.yaml（可选）**：如需要精细化日志格式，可定义模块级别配置并在 RichLogger 初始化时加载。
- **Kobe/MongoChatMemoryToolkit/README.md**：记录模块背景、运行方式、API 说明、性能基线与测试指引。

---
## 4. 模块接口设计

### 4.1 数据模型

#### ChatMessagePayload
```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, constr

class ChannelType(str, Enum):
    individual = "individual"
    group = "group"

class ChatMessagePayload(BaseModel):
    message_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="消息唯一标识")
    chat_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="会话标识")
    sender_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="发送者 ID")
    channel: ChannelType = Field(..., description="消息来源渠道类型")
    content: str = Field(..., description="原始消息文本")
    raw_metadata: dict = Field(default_factory=dict, description="原始渠道元数据")
    occurred_at: datetime = Field(..., description="消息产生时间")
    language: str = Field(default="unknown", description="语言推断结果")
    masked: bool = Field(default=False, description="是否完成脱敏处理")
    tenant_id: str = Field(..., description="租户/业务线识别码")
```
字段说明：`message_id`、`chat_id`、`sender_id` 均为必填字符串；`channel` 区分个人与群组；`content` 保存原始文本；`raw_metadata` 记录渠道扩展信息；`occurred_at` 采用 ISO 时间戳；`language` 存储语言识别结果；`masked` 指出是否已完成脱敏；`tenant_id` 用于租户隔离。

#### ChatMessageBatch
```python
from typing import List
from pydantic import BaseModel, Field

class ChatMessageBatch(BaseModel):
    batch_id: str = Field(..., description="批次 ID，便于追踪")
    source: str = Field(..., description="来源系统标识")
    items: List[ChatMessagePayload] = Field(..., min_items=1, description="消息列表")
    received_at: datetime = Field(default_factory=datetime.utcnow, description="批次接收时间")
    prefer_async: bool = Field(default=True, description="是否偏好异步处理")
```
字段说明：`batch_id` 关联任务链；`source` 标识触发源；`items` 保存消息数组；`received_at` 标记批次接收时间；`prefer_async` 控制处理模式。

#### ChatMessageRecord
```python
class ChatMessageRecord(ChatMessagePayload):
    vector_version: int = Field(default=0, description="向量化版本号")
    archived_at: datetime = Field(default_factory=datetime.utcnow, description="入库时间")
    ingestion_status: str = Field(default="cached", description="缓存/写入状态")
    persist_origin: str = Field(default="cache_flush", description="持久化来源类型")
```
字段说明：`vector_version` 标记向量化进度；`archived_at` 记录入库时间；`ingestion_status` 描述当前状态；`persist_origin` 记录持久化路径。

#### ProfileSnapshot
```python
from typing import List, Dict, Union

class AttributeItem(BaseModel):
    key: str = Field(..., description="画像字段")
    value: Union[str, int, float, bool, dict] = Field(..., description="字段值")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    source: str = Field(default="system", description="来源渠道")

class ProfileSnapshot(BaseModel):
    profile_id: str = Field(..., description="客户或群组 ID")
    profile_type: str = Field(..., pattern="^(individual|group)$", description="画像类型")
    attributes: List[AttributeItem] = Field(default_factory=list, description="画像字段集合")
    version: int = Field(..., description="版本号")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    updated_by: str = Field(..., description="操作主体")
    audit_ref: str | None = Field(default=None, description="审计引用 ID")
    expires_at: datetime | None = Field(default=None, description="画像有效期")
```
字段说明：`attributes` 保存字段集合及置信度；`version` 支持版本管理；`updated_by` 记录操作主体；`audit_ref` 关联审计；`expires_at` 处理有效期。

#### ProfileUpsertRequest
```python
class ProfileUpsertRequest(BaseModel):
    profile: ProfileSnapshot = Field(..., description="待更新画像快照")
    merge_strategy: str = Field(default="merge", description="merge/replace 策略")
    conflict_policy: str = Field(default="record", description="record/override 策略")
    reason: str = Field(..., description="更新原因")
    request_id: str = Field(..., description="幂等请求ID")
```
字段说明：包含画像快照、合并策略、冲突策略、原因与幂等键。

#### SemanticSearchRequest
```python
class SemanticSearchRequest(BaseModel):
    profile_id: str = Field(..., description="客户或群组 ID")
    profile_type: str = Field(..., description="individual/group")
    query_text: str = Field(..., min_length=1, description="语义查询文本")
    top_k: int = Field(default=8, ge=1, le=50, description="返回条目数量")
    score_threshold: float = Field(default=0.35, ge=0, le=1, description="相似度阈值")
    time_range: tuple[datetime, datetime] | None = Field(default=None, description="时间范围过滤")
    include_metadata: bool = Field(default=True, description="是否返回元数据")
    tenant_id: str = Field(..., description="租户隔离标识")
```
字段说明：`profile_id`+`profile_type` 定位 collection；`query_text` 为查询文本；`top_k` 限制结果条数；`score_threshold` 控制质量；`time_range` 可筛选时间；`include_metadata` 控制信息量；`tenant_id` 确保隔离。

#### SemanticSearchResponse
```python
class SemanticMatch(BaseModel):
    message_id: str
    chat_id: str
    content_excerpt: str
    score: float
    occurred_at: datetime
    metadata: dict

class SemanticSearchResponse(BaseModel):
    matches: list[SemanticMatch]
    fallback_used: bool = Field(default=False)
    latency_ms: int = Field(...)
    recall_rate: float = Field(...)
    trace_id: str = Field(..., description="用于追踪的 Trace ID")
```
字段说明：响应包含匹配列表、是否降级、耗时、召回率与 trace ID。

#### HistoryQuery
```python
class HistoryQuery(BaseModel):
    profile_id: str | None = None
    chat_id: str | None = None
    profile_type: str = Field(default="individual")
    keyword: str | None = Field(default=None)
    start_time: datetime | None = Field(default=None)
    end_time: datetime | None = Field(default=None)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    include_summary: bool = Field(default=False)
    include_raw: bool = Field(default=False)
    tenant_id: str = Field(..., description="租户隔离标识")
```
字段说明：支持按 profile、chat、关键字、时间筛选及分页、摘要选项，并带租户隔离。

#### HistoryQueryResponse
```python
class HistoryQueryResponse(BaseModel):
    items: list[ChatMessageRecord]
    pagination: dict
    summary: str | None
    metrics: dict
    request_id: str
```
字段说明：返回消息列表、分页、摘要、指标统计与请求 ID。

#### ExportRequest
```python
class ExportRequest(BaseModel):
    target_type: str = Field(..., description="individual/group")
    target_ids: list[str] = Field(..., description="导出对象列表")
    time_range: tuple[datetime, datetime] = Field(..., description="导出时间范围")
    include_profiles: bool = Field(default=True)
    format: str = Field(default="jsonl", description="jsonl/csv/pdf")
    notify_channel: str | None = Field(default=None)
    compress: bool = Field(default=True, description="是否压缩输出")
```
字段说明：定义导出范围、格式、通知方式、压缩选项。

#### AuditEvent
```python
class AuditEvent(BaseModel):
    event_id: str = Field(...)
    actor_id: str = Field(...)
    actor_role: str = Field(...)
    action: str = Field(...)
    resource_type: str = Field(...)
    resource_id: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = Field(default=True)
    detail: dict = Field(default_factory=dict)
    tenant_id: str = Field(...)
```
字段说明：记录操作主体、资源、结果、详情及租户信息。

### 4.2 公共接口（服务层）

#### ingest_message_async
```python
async def ingest_message_async(payload: ChatMessagePayload, *, request_id: str, actor: str) -> ChatMessageRecord:
    """写入单条消息到 Redis 缓存并调度批量持久化任务。"""
```
- 参数：`payload` 消息数据；`request_id` 用于追踪；`actor` 调用主体。
- 返回：`ChatMessageRecord`，含缓存状态与追踪信息。
- 异常：`CacheWriteError`, `ValidationError`, `PermissionDenied`。

#### enqueue_batch_ingestion
```python
async def enqueue_batch_ingestion(batch: ChatMessageBatch) -> dict:
    """提交批量消息写入任务，根据 prefer_async 决定同步或异步返回。"""
```
- 参数：`batch` 消息批次。
- 返回：包含 `batch_id`, `queued`, `eta_seconds` 的状态字典。
- 异常：`BatchRejectedError`, `PermissionDenied`, `RateLimitExceeded`。

#### query_history
```python
async def query_history(params: HistoryQuery, *, actor_role: str) -> HistoryQueryResponse:
    """执行结构化历史查询，自动拼接 Redis/Mongo 数据并进行脱敏与分页。"""
```
- 参数：查询参数与角色标识。
- 返回：`HistoryQueryResponse`，含列表、分页、摘要、指标。
- 异常：`ValidationError`, `PermissionDenied`, `QueryTimeoutError`。

#### search_semantic
```python
async def search_semantic(request: SemanticSearchRequest, *, actor_role: str) -> SemanticSearchResponse:
    """触发语义检索并处理降级逻辑，返回匹配及性能指标。"""
```
- 参数：语义请求、角色。
- 返回：`SemanticSearchResponse`。
- 异常：`VectorStoreTimeout`, `PermissionDenied`, `EmbeddingUnavailableError`。

#### upsert_profile
```python
async def upsert_profile(request: ProfileUpsertRequest, *, actor_id: str) -> ProfileSnapshot:
    """更新或创建画像，写入版本记录并触发补齐任务。"""
```
- 参数：更新请求、操作人。
- 返回：最新画像快照。
- 异常：`ConflictDetectedError`, `PermissionDenied`, `ValidationError`。

#### request_export
```python
async def request_export(payload: ExportRequest, *, actor_id: str) -> dict:
    """提交导出/周报任务，返回任务 ID 与预计完成时间。"""
```
- 参数：导出请求、操作人。
- 返回：`{"task_id": str, "status": "queued", "eta": int}`。
- 异常：`ExportRejectedError`, `PermissionDenied`, `ResourceBusyError`。

### 4.3 API 接口规范

#### POST /api/memory/messages
- **描述**：写入单条个人或群组消息。
- **请求格式**：`ChatMessagePayload` JSON。
- **响应格式**：
```json
{
  "message_id": "abc123",
  "status": "cached",
  "vector_version": 0,
  "archived": false,
  "request_id": "req-20251015-0001"
}
```
- **错误码**：400 参数错误；401 未授权；409 消息重复；500 内部错误。
- **认证**：Bearer Token + 角色 `chat.memory.write`。

#### POST /api/memory/messages/batch
- **描述**：批量写入消息，默认异步处理。
- **请求格式**：`ChatMessageBatch`。
- **响应格式**：`{"batch_id": "batch-001", "queued": true, "eta_seconds": 30}`。
- **错误码**：400 批次无效；429 超出速率限制；500 内部错误。
- **认证**：`chat.memory.write` 角色。

#### GET /api/memory/history
- **描述**：结构化历史查询，支持分页、摘要、脱敏。
- **请求参数**：`profile_id`, `chat_id`, `keyword`, `start_time`, `end_time`, `page`, `page_size`, `include_summary`。
- **响应格式**：`{"items": [...], "pagination": {...}, "summary": "...", "metrics": {...}}`。
- **错误码**：400 请求错误；401 未授权；403 无访问权限；504 查询超时。
- **认证**：`chat.memory.read`。

#### POST /api/memory/search
- **描述**：语义检索历史对话并返回相似消息。
- **请求格式**：`SemanticSearchRequest`。
- **响应格式**：`SemanticSearchResponse`。
- **错误码**：400 请求错误；401 未授权；429 请求过多；504 向量检索超时。
- **认证**：`chat.memory.search`。

#### GET /api/memory/profile/{profile_id}
- **描述**：读取客户或群组画像。
- **响应格式**：`ProfileSnapshot`。
- **错误码**：404 未找到；401 未授权；403 权限不足。
- **认证**：`chat.profile.read`。

#### POST /api/memory/profile
- **描述**：创建或更新画像，写入版本记录。
- **请求格式**：`ProfileUpsertRequest`。
- **响应格式**：最新画像快照。
- **错误码**：400 校验失败；409 冲突需人工确认；401 未授权。
- **认证**：`chat.profile.write`。

#### POST /api/memory/export
- **描述**：提交导出或周报生成任务。
- **请求格式**：`ExportRequest`。
- **响应格式**：`{"task_id": "exp-20251015-01", "status": "queued", "eta": 180}`。
- **错误码**：400 参数错误；429 排队过多；500 内部错误。
- **认证**：`chat.memory.export`。

### 4.4 Celery 任务接口

#### mongo_chat_memory.vectorize_message_batch
- **参数**：`batch_id` (str), `messages` (list[dict]), `embedding_model` (str), `retry_count` (int = 0)。
- **返回值**：`{"batch_id": ..., "processed": 120, "failed": 2}`。
- **重试策略**：指数退避（初始 5 秒，最大 5 分钟），最大重试 5 次。
- **超时**：300 秒。

#### mongo_chat_memory.flush_cache_batch
- **参数**：`batch_id`, `chat_id`, `messages`, `force_persist` (bool)。
- **返回值**：`{"batch_id": ..., "persisted": true}`。
- **重试策略**：固定间隔 30 秒，最大 3 次；失败触发告警并走降级直写。
- **超时**：120 秒。

#### mongo_chat_memory.rebuild_cache
- **参数**：`chat_id`, `limit`。
- **返回值**：`{"chat_id": ..., "rebuilt": true, "hit_rate": 0.87}`。
- **重试策略**：指数退避，最大 3 次。
- **超时**：60 秒。

#### mongo_chat_memory.profile_gap_fill
- **参数**：`profile_id`, `missing_fields`, `priority`。
- **返回值**：`{"profile_id": ..., "filled": [...], "pending": [...]}`。
- **重试策略**：指数退避 + 人工兜底，最大 6 次。
- **超时**：900 秒。

#### mongo_chat_memory.generate_report
- **参数**：`export_request`, `destination`, `template_id`。
- **返回值**：`{"task_id": ..., "output_path": "...", "size_mb": 42}`。
- **重试策略**：指数退避，最大 3 次；失败发送告警。
- **超时**：1800 秒。

---
## 5. 模块依赖关系

### 5.1 依赖图
```
routers.(ingestion|history|profile|export)
      ↓
services.ingestion → services.persistence → MongoDB
      ↓                          ↘
services.semantic  → ChromaDB     ↘
services.retrieval → Redis        ↘
services.profile   → tasks.profile_repair
services.reporting → tasks.report_generation
services.observability → SharedUtility.RichLogger / Metrics

tasks.vectorization ↔ services.persistence / services.semantic

tasks.cache_sync ↔ services.ingestion / Redis

utils.(auth|masking|transformers) → 被 routers/services 引用
models.* → 提供类型定义给所有层使用
config.py → 为所有服务提供配置来源
```
依赖校验：接口层只依赖业务层；业务层依赖模型、配置与基础设施客户端封装；任务层通过 TaskQueue 注册且不与接口层互调；无循环依赖链，满足架构约束。

### 5.2 外部依赖
- 异步 Redis 客户端（预期使用 `redis.asyncio` 或 `aioredis`，由 TechDecisions 确认）。
- MongoDB 异步驱动（Motor）。
- 向量数据库 Chroma 官方 Python SDK，配合 LangChain VectorStore 接口。
- LangChain/LangGraph 组件，用于语义检索链路与嵌入生成。
- Celery 与 RabbitMQ 作为后台任务调度与消息代理。
- OpenTelemetry/Prometheus 客户端，支撑指标与追踪。
- MinIO SDK（如导出文件需写入对象存储）。
- 可选的 HTTPX 客户端，用于外部补齐数据访问。

---
## 6. 复用与新建

### 6.1 复用现有模块
| 模块 | 路径 | 用途 |
|-----|------|------|
| RichLogger | Kobe/SharedUtility/RichLogger | 提供统一日志记录、结构化输出与 Trace 上下文 |
| TaskQueue | Kobe/SharedUtility/TaskQueue | 注册 Celery 任务、读取共享调度配置 |
| bridge_logger | Kobe/api/bridge_logger.py | 将业务日志与 API 调用链进行关联 |
| langchain_tools | Kobe/tools/langchain_tools.py | 复用既有 LangChain 工具注册与追踪能力 |

### 6.2 新建模块
| 模块 | 路径 | 职责 |
|-----|------|------|
| MongoChatMemoryToolkit | Kobe/MongoChatMemoryToolkit/ | 客户对话数据服务核心模块根目录 |
| Message Models | Kobe/MongoChatMemoryToolkit/models/messages.py | 定义消息/批量/记录模型 |
| Profile Models | Kobe/MongoChatMemoryToolkit/models/profiles.py | 定义画像模型、版本控制与冲突描述 |
| Search Models | Kobe/MongoChatMemoryToolkit/models/search.py | 定义查询/检索模型 |
| Audit Models | Kobe/MongoChatMemoryToolkit/models/audit.py | 定义审计事件模型 |
| Ingestion Router | Kobe/MongoChatMemoryToolkit/routers/ingestion.py | 消息接入 API |
| History Router | Kobe/MongoChatMemoryToolkit/routers/history.py | 历史查询与语义检索 API |
| Profile Router | Kobe/MongoChatMemoryToolkit/routers/profile.py | 画像管理 API |
| Export Router | Kobe/MongoChatMemoryToolkit/routers/export.py | 导出与周报 API |
| Ingestion Service | Kobe/MongoChatMemoryToolkit/services/ingestion.py | 消息采集逻辑 |
| Persistence Service | Kobe/MongoChatMemoryToolkit/services/persistence.py | MongoDB 数据访问 |
| Retrieval Service | Kobe/MongoChatMemoryToolkit/services/retrieval.py | 结构化查询协调 |
| Semantic Service | Kobe/MongoChatMemoryToolkit/services/semantic.py | 向量检索与降级 |
| Profile Service | Kobe/MongoChatMemoryToolkit/services/profile.py | 画像治理 |
| Reporting Service | Kobe/MongoChatMemoryToolkit/services/reporting.py | 导出/周报汇总 |
| Observability Service | Kobe/MongoChatMemoryToolkit/services/observability.py | 指标与日志封装 |
| Vectorization Tasks | Kobe/MongoChatMemoryToolkit/tasks/vectorization.py | 向量化 Celery 任务 |
| Cache Sync Tasks | Kobe/MongoChatMemoryToolkit/tasks/cache_sync.py | 缓存同步任务 |
| Profile Repair Tasks | Kobe/MongoChatMemoryToolkit/tasks/profile_repair.py | 画像补齐任务 |
| Report Generation Tasks | Kobe/MongoChatMemoryToolkit/tasks/report_generation.py | 导出任务实现 |
| Auth Utils | Kobe/MongoChatMemoryToolkit/utils/auth.py | 鉴权工具 |
| Masking Utils | Kobe/MongoChatMemoryToolkit/utils/masking.py | 脱敏工具 |
| Transformers Utils | Kobe/MongoChatMemoryToolkit/utils/transformers.py | 文本预处理 |
| Tests | Kobe/MongoChatMemoryToolkit/tests/ | 单元与集成测试套件 |

---
## 7. 范围与边界

### 7.1 包含功能
- 个人与群组聊天记录的实时采集、缓存、批量持久化，覆盖 Redis→Mongo→Chroma 全链路。
- MongoDB 基于条件的结构化查询能力，包含分页、排序、审计字段与脱敏输出。
- 向量化、语义检索与降级策略，为智能体提供高召回历史上下文服务。
- 客户与群组画像的维护、冲突审计、版本追踪与补齐任务。
- 复盘导出、周报汇总、指标统计以及对象存储对接。
- 安全合规链路：脱敏、访问控制、审计日志、密钥管理。
- 可观测性：日志、指标、Trace、周报模板及告警触发。

### 7.2 不包含功能
- 聊天渠道接入、消息发送能力（由 Telegram Bot 模块负责）。
- 业务知识文档的生成、编辑、管理与前端展示。
- 智能体提示词配置、对话流程编排、模型策略（由智能体编排模块负责）。
- 新增模型部署与嵌入服务运维，仅消费既定模型。
- 数据分析前端与 BI 仪表盘实现，仅提供数据 API 与导出文件。

### 7.3 技术边界
- 存储仅限 Redis/MongoDB/Chroma，禁止让 Redis 承担持久化职责，不得引入未审批数据库。
- 向量检索必须使用 Chroma collection，并通过 metadata 过滤；禁止 per-user collection 与未授权数据串联。
- Celery 任务必须通过 SharedUtility.TaskQueue 注册，禁止在请求线程执行长耗时逻辑。
- 鉴权需复用现有身份体系与令牌校验，不允许自建认证流程。
- 脱敏规则需与安全团队共享配置，禁止硬编码敏感信息。
- API 不暴露未脱敏的原始消息内容给无权角色，需保持字段访问粒度控制。

---
## 8. 项目约束遵循

### 8.1 技术栈约束
- **Python ≥ 3.10**：新模块遵循 async/await，兼容现有虚拟环境 `Kobe/.venv`。
- **FastAPI**：新增路由统一通过 `Kobe/main.py` 注册，复用全局中间件与异常处理器。
- **Pydantic v2**：所有模型采用 v2 语法，使用 `model_config = ConfigDict(extra="forbid")` 阻止未定义字段。
- **LangChain/LangGraph**：语义检索与向量化链路优先用 Runnable/VectorStore 抽象，后续 TechDecisions 决定具体组件组合。
- **Celery + RabbitMQ + Redis**：所有后台任务通过 TaskQueue 注册，命名遵守 slug 规范，依赖 RabbitMQ 作为 broker、Redis 作为缓存。
- **RichLogger**：日志统一走 RichLogger 工厂，输出结构化日志，禁止 print。
- **配置管理**：使用 pydantic-settings + `.env`，遵守集中密钥管理策略；敏感参数不写入代码。
- **异步 I/O**：Redis、MongoDB、Chroma 操作均需使用异步客户端，避免阻塞主线程。

### 8.2 架构约束
- **模块职责单一**：接口层不包含业务逻辑；业务层不直接暴露 API；任务层不调用路由。
- **依赖无环**：所有服务按照接口→服务→数据→基础设施的单向顺序，确保无循环引用。
- **目录规范**：新增模块位于 `Kobe/` 下并创建 `index.yaml`，保持项目能力地图完整。
- **日志规范**：关键事件（写入、查询、检索、画像更新、导出）通过 observability 模块统一埋点。
- **降级策略**：Redis 故障自动降级到 MongoDB；语义检索超时回退到结构化查询，触发告警。
- **审计留痕**：所有访问通过 `AuditEvent` 记录，满足安全与合规要求。

---
## 9. 下一步工作
1. 启动 TechDecisionsGeneration 工作流，确认 Redis/MongoDB/Chroma 客户端库版本、连接池策略、LangChain 组件、向量化模型与脱敏规则配置来源。
2. 基于本开发计划拆解开发任务，编制执行看板（模型实现、API 开发、任务编排、测试、演练等），明确优先级与人天。
3. 配置本地与 CI 环境的 Redis/MongoDB/Chroma 服务，确保开发与自动化测试环境均可复现性能指标。
4. 制定性能基准测试方案，包括写入吞吐、查询响应、语义检索准确率、降级路径验证，并准备监控仪表盘。
5. 与安全与合规团队评审脱敏策略、访问控制方案与审计字段，确保上线前满足监管要求。

---

**工作流版本**：2.0 | **生成时间**：2025-10-15 20:17:23
附加设计说明：为满足性能指标，采集链路将采用批次聚合策略（默认 200 条或 5 秒 whichever first），并在 Redis 缓存写入后即时更新命中率指标，使用滑动窗口统计；持久化任务将根据集合热度动态调整批次大小，避免单次写入超过 MongoDB 事务限制。语义检索在并发高峰时按队列排队，超过 200ms 未获得锁则直接返回降级结果并写入告警，以确保智能体体验稳定。所有异步任务均携带 trace id，以便跨服务追踪，并在重试前写入审计以满足合规要求。

异常恢复策略：当 Redis 出现连续失败时，`services.ingestion` 会触发“降级保护模式”，直接调用 `services.persistence` 进行写入，同时通过 `services.observability` 上报 `cache_downgrade_active` 指标；恢复后由 `tasks.cache_sync` 主动从 MongoDB 拉取最新窗口数据重建缓存。向量化失败时会记录未成功的消息列表并进入独立死信队列，由值班人员确认后重放；若 Chroma 服务不可用，将自动暂停语义检索并提示“结构化检索结果已返回”，同时发送告警到运维渠道。

容量规划假设：系统按每日新增 50,000 条个人消息、群组峰值 10,000 条的设定进行容量规划，Redis 设置 8GB 内存用于热点数据缓存；MongoDB 建议使用分片集群或副本集，启用 TTL 索引管理缓存转储集合；Chroma collection 预计每条记录 2KB，按一年数据约 40GB，需结合对象存储做冷备份。导出任务默认使用对象存储临时保存生成文件，过期后通过生命周期策略自动清理。
依赖治理补充：
- 所有外部服务客户端实例通过 `config.py` 提供的连接工厂创建，并在应用启动时初始化，防止散落配置。
- 需要对 MongoDB、Redis、Chroma 客户端启用健康检查与重连策略，结合 FastAPI 生命周期事件实现自动恢复。
- TaskQueue 注册的 Celery 任务需在模块加载时调用 `registry.task` 装饰器，确保与现有任务发现机制一致；新增任务 slug 需加入 `ALLOWED_TASKS` 环境变量列表，避免越权调用。
- LangChain 库需结合 TechDecisions 定义统一的嵌入模型与 retriever 配置，避免多处重复定义；语义检索组件应实现接口以支持将来替换向量库。

风险与缓解：
1. **MongoDB 写入压力**——通过批次聚合、索引优化与副本集部署缓解，同时为每个集合设计写入指标监控，超阈值自动扩容或降级。
2. **向量化延迟**——采用异步队列并行处理，必要时拆分批次，若 backlog 超过阈值则启用临时增量 worker；同时在服务层设置查询阈值，超过阈值直接降级。
3. **画像数据冲突**——在 `services.profile` 内实现冲突策略（record/override），并确保 `tasks.profile_repair` 在 30 分钟内完成补齐；冲突持续存在时发出人工工单。
4. **权限配置错误**——增强 `utils.auth` 与审计联动，针对拒绝访问记录详细原因，定期审计角色与资源映射表。
合规落实说明：安全团队需参与脱敏规则设计，`utils/masking` 将提供配置驱动方案，允许通过 `.env` 指定正则与替换策略，并在运行时输出摘要日志供审计抽查。访问控制除角色校验外，还需记录操作目的（purpose）字段，默认由调用方透传并在 `AuditEvent.detail` 中存档，满足“访问主体、目的、时间”要求。画像版本历史通过 MongoDB 集合 `profile_versions` 保存，采用事件溯源模式，可按版本回放；为满足 730 天留存要求，需配置对象存储周期性备份并设置防篡改策略。周报模板将由 `services.reporting` 结合 observability 指标自动生成，覆盖写入成功率、缓存命中率、检索召回率、画像补齐时效等指标，确保管理层透明度。

测试与验证策略：开发阶段需编写入站链路、查询链路、语义检索、画像治理、任务调度五大类测试；并通过 SimulationTest 目录扩展集成测试脚本，模拟 Redis 故障、向量库异常、批量导出高峰等场景。性能验证采用 pytest-benchmark 与自定义脚本压测 Redis/MongoDB 写入及语义检索响应，确保达到需求中的 P95 指标；同时准备 Chaos 测试脚本验证降级逻辑。上线前需执行安全审计清单，包括访问日志抽查、脱敏覆盖率抽样、画像版本回放、Celery 任务重试策略检查。
补充说明：下一步需同步 DevOps 团队确认部署形态，建议以独立 Helm Chart 管理 MongoChatMemoryToolkit 相关配置，并在 CI 流程中加入静态检查（mypy、ruff）、安全扫描（bandit）以及自动化测试，确保提交质量。发布策略建议采用灰度：先在测试环境完成全链路验证，再于生产环境开启小流量观测，确认 Redis 命中率与语义检索召回率达标后逐步放量。随着数据规模增长，应与数据仓库团队评估是否需将历史对话通过 CDC 导入离线仓库，用于 BI 和模型训练；对应链路可在后续 TechDecisions 中讨论。
错误码与日志字段约定：所有路由遵循统一错误码前缀 `MEMORY_`，例如参数错误返回 `MEMORY_VALIDATION_ERROR`，权限不足返回 `MEMORY_FORBIDDEN`，后端故障返回 `MEMORY_INTERNAL_ERROR`，便于调用方快速定位问题。`SharedUtility.RichLogger` 输出字段统一包含 `trace_id`, `request_id`, `tenant_id`, `actor_id`, `action`, `resource_type`, `duration_ms`, `result` 等键，支持在观测平台搜索与告警。语义检索链路额外记录 `vector_version` 与 `fallback_used`，方便核对降级率；导出任务日志需记录生成耗时、输出文件大小、下载链接过期时间，以满足运维与审计需求。

数据治理补充：MongoDB 集合将根据数据主题拆分为 `chat_messages_individual`, `chat_messages_group`, `profiles`, `profile_versions`, `export_jobs`, `audit_events` 等，所有集合默认启用复合索引（例如 `{chat_id: 1, occurred_at: -1}`）以优化查询。向量化数据在 Chroma 中按 collection 隔离，metadata 包含 `tenant_id`, `profile_type`, `profile_id`, `chat_id`, `message_id`, `occured_at`, `ingestion_state`，确保过滤精确。Redis 缓存键采用 `memory:{tenant_id}:{chat_id}` 命名，值序列化为 JSON，设置 5 分钟 TTL 并在写入 Mongo 后自动刷新 TTL，保证热点数据可复用。画像补齐任务在执行前会检查消息记录中是否存在相关上下文，避免重复补齐。
持续交付计划：项目将采用 trunk-based 开发策略，所有功能分支需通过自动化测试与代码评审方可合并。CI 流程在触发单元测试后还会运行示例流水线：1) 启动临时 Redis/MongoDB/Chroma 容器；2) 执行消息写入→批量刷写→语义检索→画像更新→导出全链路脚本；3) 收集性能指标并与阈值对比，若 P95 超出预期则阻断合并。上线前必须完成灾备演练，验证 Redis 故障、RabbitMQ 中断、Chroma 超时情况下系统是否正确降级，并确认日志与告警准确触发。运维需根据 observability 模块提供的仪表盘配置预警阈值（如缓存命中率低于 70%、语义检索降级率高于 5%、画像补齐延迟超过 20 分钟等），确保问题及时暴露。
监控与报警细则：`services.observability` 将定义统一指标命名规范，例如 `memory_ingest_latency_ms`, `memory_cache_hit_ratio`, `memory_vectorization_backlog`, `memory_profile_conflict_count`, `memory_export_duration_ms` 等，并将其暴露给 Prometheus。报警策略按照业务影响分级：一级报警指 Redis 降级模式持续超过 5 分钟或 MongoDB 写入失败率超过 1%；二级报警指语义检索降级率超过 10% 或导出任务失败率超过 5%；三级提示信号用于提醒画像补齐超时、周报生成延迟等需要人工关注但不影响核心流程的事项。所有报警同时推送到 Slack/邮件，并记录在 audit 事件中，便于事后复盘。为了防止指标噪声，将结合 Prometheus Alertmanager 的抖动抑制策略，确保只有持续异常才会触发。
数据归档计划：为满足长期留存与成本平衡，聊天记录将在 MongoDB 保留一年热数据，超过期限的历史将按季度转储至压缩 JSONL 存储于对象存储的冷归档区，同时保留向量索引摘要以便快速恢复。恢复流程需编写脚本支持自动回放历史档案至 MongoDB 和 Chroma，包含幂等检查与版本验证，确保归档与恢复一致。归档任务计划由 Celery 定时任务触发，并在执行前校验磁盘空间和对象存储配额，执行后生成报告供合规审阅。该方案需要 TechDecisions 后续确认具体备份频率与加密策略。
知识转移与培训：项目交付后需安排三轮培训。第一轮面向后端开发团队，讲解模块结构、编码规范、任务注册流程以及常见故障排查方法，确保后续迭代可持续。第二轮面向客服运营与数据分析团队，演示历史查询、语义检索、导出周报的使用方式，并说明访问权限申请流程。第三轮面向运维与安全团队，覆盖监控仪表盘、告警处理、审计抽查、备份恢复操作等内容。培训资料需存放在项目知识库，包含示例脚本、FAQ、故障演练记录，以支持新成员快速上手。
开放接口治理：为便于后续扩展，本模块所有对外 API 将在 `Kobe/api` 层注册到统一的 OpenAPI 文档，添加详细的字段描述、示例请求与响应，并标记需要的权限 scope。文档生成后同步给客户端开发团队，便于在智能体或客服前端集成。若未来需要对接第三方渠道或外部合作方，可在此基础上引入 API Gateway，对敏感接口附加 IP 白名单与速率限制策略。同时建议在 `Kobe/MongoChatMemoryToolkit/README.md` 中维护接口变更日志（changelog），使用语义化版本控制，避免跨团队沟通遗漏。
性能调优预案：上线后需在首月密切跟踪核心指标，根据实时数据调整缓存 TTL、批次大小与向量检索阈值。例如，当 Redis 命中率连续三天低于 75% 时，自动缩短批次刷写间隔或增加缓存容量；当语义检索召回率低于 70% 时，动态调低 `score_threshold` 并触发模型评估工作流程。若导出任务平均耗时超过 10 分钟，则需要考虑拆分导出范围、提高 Celery worker 并发或改进数据聚合策略。所有调整需记录在运维变更日志，确保后续回溯。
兼容性考量：当前系统主要服务 Telegram 渠道，但为支持未来扩展到邮件、网页客服或语音渠道，消息模型在 `raw_metadata` 中预留了可扩展字段，允许存储附件列表、语音转写、情感评分等信息。服务层在处理时应保持对未知字段的兼容性，避免因为新增渠道字段导致入站失败。若新增渠道有不同的身份标识规则，可通过 `utils.transformers` 中的标准化方法统一映射到内部 `profile_id`，并在配置文件中声明映射策略，确保跨渠道数据仍然归一。
日志留存策略：按照合规要求，所有审计日志需保存至少两年。应用侧将日志写入集中式日志平台，并在本地保留 7 天滚动文件以便快速排查；平台侧配置 S3/对象存储做长期归档，同时启用检索索引，支持以 `trace_id` 或 `actor_id` 快速定位记录。对于包含敏感信息的日志，`utils.masking` 将在写入前进行二次脱敏，确保日志系统不会暴露原始数据。
灾难恢复演练：每季度至少进行一次全链路灾备演练，包括 MongoDB 主节点故障切换、Redis 数据丢失模拟、Chroma 集群扩容与回滚测试，确保应急预案有效。演练需生成报告并记录恢复耗时、数据一致性验证结果以及改进建议。
团队协作节奏：建议采用每周滚动迭代会议，跟踪指标达成情况、异常处理进展与需求变更，保持跨团队信息同步。
里程碑建议：
- **M1（第1周）**：完成架构基线、配置加载、模型定义与入站 API 骨架。
- **M2（第2-3周）**：实现持久化、检索、画像治理与任务队列，覆盖主要单元测试。
- **M3（第4周）**：补齐语义检索链路、导出任务、可观测性埋点与性能调优。
- **M4（第5周）**：执行联调与验收，完成合规审计、备份演练与知识转移。
里程碑完成后需开展回顾，总结指标达成度与改进点，形成持续优化闭环。
持续关注需求动态，若新增渠道或法规要求变化，应及时更新本计划并重新评估风险。
团队需对关键指标设定周度目标，并在例会上复盘偏差成因与纠正动作。
如遇到跨团队依赖阻塞，应通过项目例会升级并记录责任人、预计解决时间与验证步骤。
建议在每次发布后进行 360 度反馈，收集客服、智能体、运维等多角色意见以迭代优化。
对于重大缺陷需建立事后分析模板，记录根因、影响范围、补救措施与长期防范方案。
保留关键决策记录，便于在未来需求评审时快速回溯历史上下文与取舍依据。
默认保留需求假设清单，随版本更新及时维护以避免偏离初衷。
后续演进需与 TechDecisions 输出保持同步，防止文档失效。
保持文档与实现联动。
