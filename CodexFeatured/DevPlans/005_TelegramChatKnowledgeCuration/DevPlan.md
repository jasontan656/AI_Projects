# 开发计划：TelegramChatKnowledgeCuration

标识信息：INTENT_TITLE_2_4=TelegramChatKnowledgeCuration；COUNT_3D=005；生成时间=2025-10-11 19:26:09
需求文档：D:\AI_Projects\CodexFeatured\DevPlans\005_TelegramChatKnowledgeCuration\DemandDescription.md
输出路径：D:\AI_Projects\CodexFeatured\DevPlans\005_TelegramChatKnowledgeCuration\DevPlan.md

---

## 1. 项目概述

### 1.1 需求摘要
本项目旨在将 Telegram 群组/频道的历史与增量聊天记录转化为结构化、可检索、可复用的企业知识资产，覆盖“高质量采集—清洗规范—主题归类—问答抽取—知识片生成—索引检索—评估报表”的全链路闭环。系统优先保证溯源可追踪与合规可控，在多源异构与大体量数据下提供稳定、低延迟、可观察的工程能力，为客服问答、运营洞察、内部学习与内容二次创作提供支撑。

### 1.2 开发目标
- 建立统一的数据接入、清洗、线程构建、脱敏与分类流水线
- 面向问答与知识库发布生成“知识片”标准单元并建立高效索引
- 提供异步任务化的重建/增量流程与在线检索 API
- 构建评估与运营报表，形成持续优化的闭环

### 1.3 项目类型
Web 应用（backend + Celery 后台服务）

---

## 2. 架构设计

### 2.1 功能域划分
- 数据接入域：装载 Telegram 导出数据、媒体管理与异常兜底
- 预处理域：消息规范化、线程构建、隐私脱敏
- 智能标注域：主题与意图分类、问答对抽取
- 知识生产域：知识片生成、版本化与治理
- 索引与检索域：增量/重建索引、混合检索与答案综合
- 评估与运营域：离线/在线评估、趋势报表与导出
- 运维治理域：任务编排、重试补偿、审计与限流

### 2.2 模块清单
#### 模块：数据接入装载模块
- 路径：Kobe/TelegramCuration/i_ng_es_ti_on_lo_ad_er.py（或 services.py:IngestionLoader）
- 职责：负责从 Telegram 导出数据（JSON/HTML/媒体目录）按频道/群组/时间窗口批量装载，解析元数据（发送者、时间戳、回复关系、附件），并将原始记录映射为统一的内部消息结构，同时在装载过程中进行基础去重与异常行过滤，确保上游数据源不断档可追溯。
- 输入：输入路径、频道标识、起止时间、导出格式标识
- 输出：标准化 ChatMessage 流（可分页迭代器）
- 依赖：SharedUtility/RichLogger, filesystem
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger TaskQueue[0] 等）
#### 模块：媒体素材抓取模块
- 路径：Kobe/TelegramCuration/m_ed_ia_fe_tc_he_r.py（或 services.py:MediaFetcher）
- 职责：抽取消息中引用的媒体资源（图片/音频/视频/文件），对本地磁盘路径、大小、哈希进行登记，生成可延迟拉取与校验的流水，避免大体量素材阻塞主流程；支持失败重试与断点续传策略，并输出与消息 ID 关联的 MediaMeta。
- 输入：消息集合、媒体根目录
- 输出：MediaMeta 记录列表
- 依赖：SharedUtility/RichLogger, OS IO
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：消息规范化模块
- 路径：Kobe/TelegramCuration/m_es_sa_ge_no_rm_al_iz_er.py（或 services.py:MessageNormalizer）
- 职责：统一时区与时间精度、清理控制字符、合并系统消息、展开转发链，执行去重与相似合并，抽取干净的文本字段与结构化引用（@、#、URL），并形成后续可用于主题聚类与问答抽取的标准文本表示。
- 输入：ChatMessage 流
- 输出：NormalizedMessage 流
- 依赖：SharedUtility/RichLogger
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：会话线程构建模块
- 路径：Kobe/TelegramCuration/t_hr_ea_di_ng.py（或 services.py:Threading）
- 职责：基于回复关系、时间间隔与主题相似度，将离散消息聚合为对话线程（Thread），为问答抽取与知识片生成提供上下文窗口；支持阈值配置与滑动窗口策略，输出线程级摘要与代表消息。
- 输入：NormalizedMessage 流
- 输出：Thread 列表
- 依赖：SharedUtility/RichLogger
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：隐私脱敏模块
- 路径：Kobe/TelegramCuration/p_ii_re_da_ct_io_n.py（或 services.py:PIIRedaction）
- 职责：按合规清单对电话号码、邮箱、订单号、地址等敏感字段进行检测与可逆/不可逆脱敏，输出记录脱敏痕迹与审计日志；在保证可追溯的同时降低数据暴露风险，为下游索引与问答环节提供合规数据。
- 输入：Thread 列表/消息流
- 输出：脱敏后的消息/线程
- 依赖：SharedUtility/RichLogger
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：主题与意图分类模块
- 路径：Kobe/TelegramCuration/t_ax_on_om_yc_la_ss_if_ie_r.py（或 services.py:TaxonomyClassifier）
- 职责：结合关键词、模板匹配与可插拔 LLM 分类器，对消息与线程进行业务主题、意图、情感与优先级标注；支持可配置的业务词表与黑白名单策略，产出 TaxonomyTag 以支撑知识片聚合与检索过滤。
- 输入：线程/消息、业务词表
- 输出：TaxonomyTag 列表
- 依赖：SharedUtility/RichLogger, LLM API
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：问答对抽取模块
- 路径：Kobe/TelegramCuration/q_ap_ai_rm_in_er.py（或 services.py:QAPairMiner）
- 职责：在对话线程中识别用户提问与官方/群管理者/知识性回答的配对关系，抽取多轮语境下的问答对，生成结构化的 QAPair，包括问题、答案、证据消息引用与置信度评分，用于后续知识片与文档化。
- 输入：Thread 列表
- 输出：QAPair 列表
- 依赖：SharedUtility/RichLogger, LLM API
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：知识片生成模块
- 路径：Kobe/TelegramCuration/s_li_ce_bu_il_de_r.py（或 services.py:SliceBuilder）
- 职责：将问答对、公告消息与高价值长文整合为可复用的 KnowledgeSlice，统一字段（标题、要点、适用范围、时效性、来源链路、标签），支持细粒度溯源与版本化，为索引与对外知识库发布提供标准单元。
- 输入：QAPair、精选消息
- 输出：KnowledgeSlice 列表
- 依赖：SharedUtility/RichLogger
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：索引与存储模块
- 路径：Kobe/TelegramCuration/i_nd_ex_er.py（或 services.py:Indexer）
- 职责：负责将知识片写入持久化存储（文档库/对象存储）与检索索引（如向量/关键词倒排），实现增量与重建两种模式，维护索引状态、分片与并发控制；对外暴露查询依赖的索引统计信息。
- 输入：KnowledgeSlice 列表
- 输出：IndexRecord 列表/统计
- 依赖：SharedUtility/RichLogger, SharedUtility/TaskQueue, Cache
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger TaskQueue[0] 等）
#### 模块：检索与问答模块
- 路径：Kobe/TelegramCuration/r_et_ri_ev_er.py（或 services.py:Retriever）
- 职责：提供统一的查询接口，支持关键词、语义与混合检索，结合业务标签筛选与新鲜度权重，返回多粒度候选并进行答案综合；与 Q&A 端点集成，输出可解释来源与评分，支撑在线问答场景。
- 输入：QueryRequest
- 输出：QueryResponse（含候选与证据）
- 依赖：SharedUtility/RichLogger, IndexerService
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：质量评估模块
- 路径：Kobe/TelegramCuration/e_va_lu_at_io_n.py（或 services.py:Evaluation）
- 职责：对抽取准确性、覆盖率、延迟与问答效果进行持续评测，提供自动化基准数据集与任务编排，产出评测报表与趋势，作为重建与参数调优的闭环信号，确保系统在规模化增量下保持稳定质量。
- 输入：评测样本/线上日志
- 输出：评测指标与报告
- 依赖：SharedUtility/RichLogger, SharedUtility/TaskQueue
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger TaskQueue[0] 等）
#### 模块：运营报表模块
- 路径：Kobe/TelegramCuration/r_ep_or_ti_ng.py（或 services.py:Reporting）
- 职责：面向业务方输出可读报表：新增知识片、热议主题、未覆盖问题、响应延迟、热点问答等，并提供导出（CSV/Markdown/HTML），为产品与运营决策提供可追踪、可分享的证据。
- 输入：指标与索引统计
- 输出：报表文档/仪表盘数据
- 依赖：SharedUtility/RichLogger
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger[0] 等）
#### 模块：运维与治理模块
- 路径：Kobe/TelegramCuration/g_ov_er_na_nc_e.py（或 services.py:Governance）
- 职责：提供任务调度、重试策略、失败补偿、数据留存/清理、配额限制、配置灰度与变更审计，结合环境变量约束与允许的 Celery 任务白名单，确保系统在多任务高并发下可控、可观察、可恢复。
- 输入：系统配置/运行时指标
- 输出：治理动作与审计事件
- 依赖：SharedUtility/RichLogger, SharedUtility/TaskQueue
- 是否复用：是（复用 Kobe/SharedUtility/RichLogger TaskQueue[0] 等）

### 2.3 架构分层
```
┌─────────────────────────────────────┐
│         接口层 (API/CLI)            │
├─────────────────────────────────────┤
│         业务层 (Services)           │
├─────────────────────────────────────┤
│         数据层 (Models)             │
├─────────────────────────────────────┤
│    基础设施层 (Database/Cache)      │
└─────────────────────────────────────┘
```
- 接口层：对外暴露 HTTP API 与 CLI，接收请求或触发任务
- 业务层：实现装载、清洗、分类、抽取、生成、检索等核心流程
- 数据层：统一 Pydantic v2 模型与校验，保障数据契约稳定
- 基础设施层：缓存、消息队列、持久化与索引组件，提供可靠支撑

### 2.4 数据流设计
```
[输入数据]
   ↓
[数据验证] ← Pydantic Models
   ↓
[业务处理] ← Services
   ↓
[数据转换]
   ↓
[输出结果]

并行：
- 日志记录 ← RichLogger
- 性能监控 ← Metrics
```

---

## 3. 目录结构规划

### 3.1 完整目录树
```
Kobe/
├── TelegramCuration/
│   ├── __init__.py            # 模块导出与版本信息
│   ├── models.py              # Pydantic 数据模型（ChatMessage/KnowledgeSlice/...）
│   ├── services.py            # 业务服务聚合（见模块清单）
│   ├── routers.py             # FastAPI 路由（/api/ingest, /api/knowledge, /api/qna）
│   ├── tasks.py               # Celery 任务（ingest_channel/index_batch/...）
│   ├── utils.py               # 工具函数（IO/文本/时间/校验）
│   ├── config.py              # 模块级配置（阈值/策略）
│   └── README.md              # 使用说明与示例
├── SharedUtility/
│   ├── RichLogger/            # 复用：统一日志
│   └── TaskQueue/             # 复用：任务队列
└── TempUtility/
    └── TelegramCuration/      # 临时脚本、一次性迁移
```

### 3.2 文件职责说明
- `Kobe/TelegramCuration/models.py`：定义核心数据模型（ChatMessage/KnowledgeSlice/QAPair 等）
- `Kobe/TelegramCuration/services.py`：装载、清洗、分类、抽取、生成、检索等服务聚合
- `Kobe/TelegramCuration/routers.py`：HTTP 路由与请求响应模型绑定
- `Kobe/TelegramCuration/tasks.py`：Celery 任务定义与编排
- `Kobe/TelegramCuration/utils.py`：IO/文本/时间/校验等通用工具
- `Kobe/TelegramCuration/config.py`：模块级可调参数与策略
- `Kobe/TelegramCuration/README.md`：模块说明与使用范例

### 3.3 配置文件规划
- `Kobe/.env`：敏感配置（OpenAI Key、Redis/Mongo/RabbitMQ 连接等）
- `Kobe/TelegramCuration/config.py`：阈值、窗口、重试与合规模式等业务参数

---

## 4. 模块接口设计

### 4.1 数据模型
#### ChatMessage
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class ChatMessage(BaseModel):
    message_id: str = Field(..., description="原始消息ID")
    chat_id: str = Field(..., description="群/频道ID")
    sender: str = Field(..., description="发送者标识")
    text: str = Field('', description="纯文本内容")
    created_at: datetime = Field(..., description="发送时间，统一到UTC")
    reply_to: Optional[str] = Field(None, description="回复目标ID")
    media: Optional[list[str]] = Field(default=None, description="媒体本地路径列表")
```

#### KnowledgeSlice
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

class KnowledgeSlice(BaseModel):
    slice_id: str = Field(..., description="知识片ID")
    title: str = Field(..., description="标题/主题")
    summary: str = Field(..., description="要点摘要")
    tags: List[str] = Field(default_factory=list, description="业务标签")
    sources: List[str] = Field(..., description="溯源消息ID列表")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

#### QAPair
```python
from pydantic import BaseModel, Field
from typing import List

class QAPair(BaseModel):
    question: str = Field(...)
    answers: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0)
```

#### QueryRequest / QueryResponse
```python
from pydantic import BaseModel, Field
from typing import List

class QueryRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    top_k: int = Field(10, ge=1, le=50)
    filters: dict = Field(default_factory=dict)

class QueryResponse(BaseModel):
    hits: List[dict] = Field(default_factory=list, description="候选+分数+来源")
    latency_ms: int = Field(0)
```

### 4.2 公共接口（库/工具）
```python
async def parse_telegram_export(path: str, chat_id: str, since: str | None = None, until: str | None = None) -> list[ChatMessage]:
    """解析 Telegram 导出，产出标准 ChatMessage 列表。"""
```
```python
async def build_knowledge_slices(threads: list[Thread]) -> list[KnowledgeSlice]:
    """从对话线程构建知识片。"""
```

### 4.3 API 接口规范（HTTP）
#### POST /api/ingest/start
- 描述：启动指定频道/时间窗的增量装载
- 请求：{"chat_id":"@channel","since":"2025-01-01","until":"2025-12-31"}
- 响应：{"task_id":"telegram.ingest_channel:abc"}
- 错误码：400 参数错误；409 任务重复

#### GET /api/ingest/status?task_id={id}
- 描述：查询装载任务状态
- 响应：{"state":"STARTED","progress":42}

#### POST /api/knowledge/rebuild
- 描述：从已清洗数据重建知识片与索引（长流程，异步）
- 响应：{"task_id":"telegram.build_slices"}

#### POST /api/knowledge/query
- 描述：混合检索问答
- 请求：{"query":"如何导出聊天记录？","top_k":8}
- 响应：{"hits":[{"slice_id":"S123","score":0.82}],"latency_ms":120}

### 4.4 Celery 任务接口
#### telegram.ingest_channel
- 参数：chat_id(str), since(str), until(str)
- 返回：{"ingested": 12345}
- 重试：指数退避，最大5次；超时：30min

#### telegram.build_slices
- 参数：window(str), policy(str)
- 返回：{"slices": 800}
- 重试：3次；超时：60min

#### telegram.index_batch
- 参数：batch_id(str)
- 返回：{"indexed": 2000}
- 重试：5次；超时：20min

#### telegram.evaluate_quality
- 参数：dataset(str)
- 返回：{"accuracy": 0.93, "coverage": 0.88}
- 重试：2次；超时：15min

---

## 5. 模块依赖关系
```
routers.py
   ↓
services.py
   ↓
models.py

并行依赖：
- RichLogger (日志)
- TaskQueue (任务队列)
```

### 5.2 外部依赖（留待 TechDecisions 细化）
- 文档数据库/对象存储：用于知识片与元数据持久化
- 检索索引：向量与倒排混合检索能力
- 异步 HTTP 客户端：拉取媒体与外部服务
- 数据验证：Pydantic v2（已确定）

---

## 6. 复用与新建

### 6.1 复用现有模块
- RichLogger（`Kobe/SharedUtility/RichLogger`）：统一日志
- TaskQueue（`Kobe/SharedUtility/TaskQueue`）：任务编排

### 6.2 新建模块
- TelegramCuration（`Kobe/TelegramCuration/*`）：本计划新增的业务模块与文件

---

## 7. 范围与边界

### 7.1 包含功能
- 历史+增量数据装载、清洗、线程构建、脱敏与分类
- 问答对抽取、知识片生成、索引与检索 API
- 评估基线与运营报表导出

### 7.2 不包含功能
- 外观复杂的前端可视化（仅提供必要的接口）
- 私有化部署脚本与 CI/CD（留待后续阶段）

### 7.3 技术边界
- 做什么：专注后端数据到知识的生产与服务化
- 不做什么：不内置重型 ETL 与 DWH，同步策略后续确定

---

## 8. 项目约束遵循
- Python ≥ 3.10，使用 Pydantic v2 进行数据校验
- FastAPI 作为 HTTP 框架；长流程统一由 Celery 承载
- 统一使用 RichLogger 记录日志，禁止随意 print
- 任务白名单从 `.env` 中读取，遵循 slug 命名规则
- 可观察性暴露 Metrics/Logs/Traces，便于排障

---

## 9. 下一步工作
立即进入 TechDecisionsGeneration：
- 选择向量/倒排检索方案与具体依赖版本
- 明确 LLM 提示词与调用策略（如需）
- 细化数据库/对象存储结构与索引分片策略
- 确定配置项清单与默认值

---

工作流版本：2.0 | 生成时间：2025-10-11 19:26:09

---

## 附录 A：数据字段与业务语义
- 字段对照表：消息、线程、问答对、知识片与索引记录的完整字段、类型、是否必填、默认值、示例与验证规则详细列举，确保上下游契约一致。
- ChatMessage 字段解释：message_id、chat_id、sender、text、created_at、reply_to、media、reactions、forwards、is_pinned、is_service 等。
- KnowledgeSlice 字段解释：slice_id、title、summary、tags、sources、created_at、version、lifecycle（draft/published/deprecated）、owner、score、freshness 等。
- 线程 Thread 字段解释：thread_id、message_ids、representative、start_at、end_at、topic、participants、turns、coherence_score 等。

### 字段清单（节选）
| 实体 | 字段 | 类型 | 必需 | 描述 |
|---|---|---|---|---|
| ChatMessage | message_id | str | 是 | 源系统唯一标识 |
| ChatMessage | chat_id | str | 是 | 频道/群组标识 |
| ChatMessage | sender | str | 是 | 发送者（脱敏后） |
| ChatMessage | text | str | 否 | 纯文本内容（清洗后） |
| ChatMessage | created_at | datetime | 是 | 统一到 UTC |
| ChatMessage | reply_to | str | 否 | 回复目标ID |
| KnowledgeSlice | slice_id | str | 是 | 知识片唯一标识 |
| KnowledgeSlice | title | str | 是 | 标题/主题 |
| KnowledgeSlice | summary | str | 是 | 要点摘要（≤ 800 字） |
| KnowledgeSlice | tags | list[str] | 否 | 业务标签 |
| KnowledgeSlice | sources | list[str] | 是 | 溯源消息ID列表 |

## 附录 B：任务编排策略
- ingest_channel → normalize → threading → redact → classify → mine_qa → build_slices → index_batch 的标准流水线。
- 支持 chain/group/chord 组合：对大批量数据按分片并发处理，再聚合统计与回写索引状态。
- 失败补偿：对幂等步骤（规范化、分类）采用“重放+校验”和“写入前比较”，避免重复写入。
- 限流与并发：按媒体抓取/索引写入设置独立并发池，避免阻塞关键路径。

## 附录 C：性能与容量规划
- 目标：P95 接口延迟 ≤ 800ms；重建 100 万条消息 ≤ 2 小时（并行度可配置）。
- 样本容量评估：消息平均 180 字，线程平均 6 条消息，问答对覆盖率 ≥ 30%。
- 指标：QPS、失败率、重试率、索引写入速率、缓存命中率、向量召回率、答案可解释性评分等。

## 附录 D：运维与监控指标
- Celery 任务指标：运行中/成功/失败/重试、队列长度、吞吐量、任务时长分布。
- API 指标：请求数、延迟分位、错误码分布、热点路由排名。
- 业务指标：新增知识片、问答覆盖率、冷门未命中 TopN、主题热度变化。
- 资源指标：CPU/内存/IO/网络、连接池占用、磁盘使用、水位告警阈值。

## 附录 E：风险与合规
- 隐私：对手机号、邮箱、地址等敏感信息执行可配置脱敏；存储访问最小权限；日志避免写敏感原文。
- 版权：遵循来源可追溯和引用规范；导出时保留来源标识与时间戳。
- 审计：关键操作写审计事件，保留 180 天以上；支持导出 CSV/JSON。

## 附录 F：实施里程碑（示例）
1) 第 1 周：需求澄清、数据样本收集、验证导出格式与数量级、确定词表。
2) 第 2 周：完成装载与规范化、线程构建与脱敏；跑通最小评估集。
3) 第 3 周：完成分类、问答抽取、知识片生成；初版索引与检索接口。
4) 第 4 周：评估优化与运营报表、故障注入与稳定性测试、文档完善与移交。

## 附录 G：示例提示词（占位，待 TechDecisions 细化）
```
系统：你是资深对话整理助手，请在不杜撰信息的前提下，基于给定对话摘取问题与答案，保留溯源ID，确保答案可验证。
约束：
- 不可生成未在对话中出现的结论；
- 若答案不完整，请明确标注“需补充”。
输出：JSON，字段 question/answers/evidence_ids/confidence。
```
