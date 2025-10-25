# 任务清单：TelegramChatKnowledgeCuration（Telegram 聊天知识整顿与问答支持）

标识信息：INTENT_TITLE_2_4=TelegramChatKnowledgeCuration；COUNT_3D=005；生成时间=2025-10-11 21:05:00

参考文档：
- 需求文档：D:/AI_Projects/CodexFeatured/DevPlans/005_TelegramChatKnowledgeCuration/DemandDescription.md
- 开发计划：D:/AI_Projects/CodexFeatured/DevPlans/005_TelegramChatKnowledgeCuration/DevPlan.md
- 技术决策：D:/AI_Projects/CodexFeatured/DevPlans/005_TelegramChatKnowledgeCuration/Tech_Decisions.md

输出路径：D:/AI_Projects/CodexFeatured/DevPlans/005_TelegramChatKnowledgeCuration/Tasks.md

---

## 技术决策摘要

本任务清单基于 Tech_Decisions.md 的实施细节生成。下面仅为提炼，完整内容以技术决策文档为准。

### 新增依赖（见 Tech_Decisions.md §1.1）

| 依赖 | 版本 | 用途 | 参考 |
|-----|------|------|------|
| fastapi | 0.118.0 | HTTP API 框架 | Tech_Decisions.md §1.1 |
| uvicorn | 0.37.0 | ASGI 服务器 | Tech_Decisions.md §1.1 |
| pydantic | 2.12.0 | 数据模型与校验 | Tech_Decisions.md §1.1 |
| pydantic-settings | 2.11.0 | 配置与 .env 加载 | Tech_Decisions.md §1.1 |
| openai | 2.2.0 | 官方 SDK（LLM 调用） | Tech_Decisions.md §1.1 |
| httpx | 0.27.2 | 异步 HTTP 客户端 | Tech_Decisions.md §1.1 |
| beautifulsoup4 | 4.13.0 | HTML 解析 | Tech_Decisions.md §1.1 |
| lxml | 6.0.0 | HTML/XML 解析引擎 | Tech_Decisions.md §1.1 |
| orjson | 3.11.3 | 高性能 JSON | Tech_Decisions.md §1.1 |
| redis | 6.4.0 | 缓存/限流 | Tech_Decisions.md §1.1 |
| celery | 5.5.3 | 异步任务队列 | Tech_Decisions.md §1.1 |
| pymongo | 4.15.2 | MongoDB 客户端 | Tech_Decisions.md §1.1 |
| chromadb-client | 1.1.1 | 向量检索 | Tech_Decisions.md §1.1 |

> 备注：pytest/pytest-asyncio 可按需加入测试依赖，不纳入本功能运行时清单。

### 大模型配置（见 Tech_Decisions.md §2）
- 模型：gpt-4o-mini（默认，可选 gpt-4o-mini-translate/gpt-4o）
- 提示词模板：见 Tech_Decisions.md §2.1/§2.2/§2.3（全文模板见下文“提示词模板”步骤）
- 调用参数：temperature=0.0, max_tokens=200, timeout=30, retries=3
- 批处理：每批50个；限速约60/分钟；失败指数回退 1s/2s/4s

### API 配置（见 Tech_Decisions.md §3）
- 端口：8000（接入现有服务）
- 路由前缀：/api/telegram-curation/
- 端点清单与测试命令：见 Tech_Decisions.md §3.2（本清单在阶段4复写）

### 数据模型（见 Tech_Decisions.md §4）
- ChatMessage：提供完整 Pydantic 示例（见 §4.1）
- NormalizedMessage、Thread、KnowledgeSlice、QARecord：提供字段/存储规范（§4.2–§4.5）；按规范实现 Pydantic 定义
- 字段命名与转换规范（§4.6–§4.7）

### 配置文件（见 Tech_Decisions.md §5）
- .env：完整模板见 §5.1（在步骤1.2内原样落盘）
- config.py：完整示例见 §5.2（在步骤1.2内原样落盘）

---

## 任务清单

以下按阶段组织，每个 Step 的 sub_steps 均为可手动执行的原子操作；每个 Step 均含可验证的验收标准（acceptance）。所有技术细节均引用 Tech_Decisions.md 的对应章节。

### 阶段0：环境准备与依赖安装

Step 0.1: 更新依赖清单（见 Tech_Decisions.md §1.1）
- sub_steps:
  - 若不存在则新建 `Kobe/Requirements.txt`。
  - 在文件末尾添加以下依赖（库名=版本）：
    - fastapi==0.118.0
    - uvicorn==0.37.0
    - pydantic==2.12.0
    - pydantic-settings==2.11.0
    - openai==2.2.0
    - httpx==0.27.2
    - beautifulsoup4==4.13.0
    - lxml==6.0.0
    - orjson==3.11.3
    - redis==6.4.0
    - celery==5.5.3
    - pymongo==4.15.2
    - chromadb-client==1.1.1
  - 保存文件。
- acceptance:
  - Requirements.txt 包含上述所有条目且版本号与 Tech_Decisions.md §1.1 一致。
  - 无重复、无拼写错误（区分连字符与下划线）。

Step 0.2: 安装依赖（见 Tech_Decisions.md §1.1）
- sub_steps:
  - Windows：`cd Kobe && python -m venv .venv && .venv\Scripts\activate`。
  - 安装：`pip install -r Requirements.txt`。
  - 校验：`python -c "import fastapi, bs4, lxml, httpx, orjson; print('ok')"` 输出 ok。
- acceptance:
  - pip 安装无错误码（exit code 0）。
  - 上述 import 语句执行无异常。

### 阶段1：基础结构与配置

Step 1.1: 创建目录结构（见 DevPlan.md §3.1）
- sub_steps:
  - 创建目录：
    - `Kobe/TelegramCuration/`
    - `Kobe/SharedUtility/`（如已存在则跳过）
    - `Kobe/TelegramCuration/tests/`
  - 在 `Kobe/TelegramCuration/` 内创建文件：`__init__.py`, `models.py`, `services.py`, `routers.py`, `tasks.py`, `utils.py`, `README.md`。
  - 确认复用模块目录存在：`Kobe/SharedUtility/RichLogger/`、`Kobe/SharedUtility/TaskQueue/`（若尚未接入，请记录待办，不在本清单范围内实现）。
- acceptance:
  - 目录与文件均存在且可读写。
  - `__init__.py` 存在（包可导入）。

Step 1.2: 创建配置文件（见 Tech_Decisions.md §5.1–§5.2）
- sub_steps:
  - 在 `Kobe/` 目录创建 `.env` 文件，写入以下内容（原样来自 §5.1）：

```
# 数据库
MONGODB_URI=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
CHROMADB_URL=http://localhost:8001

# 大模型
OPENAI_API_KEY=sk-xxxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# 应用
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
API_PORT=8000
API_HOST=0.0.0.0

# 运行参数
BATCH_SIZE=50
TIMEOUT=30
```

  - 在 `Kobe/` 或公共配置路径创建 `config.py`，写入以下内容（原样来自 §5.2）：

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    mongodb_uri: str = Field(..., env="MONGODB_URI")
    redis_url: str = Field(..., env="REDIS_URL")
    rabbitmq_url: str = Field(..., env="RABBITMQ_URL")

    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")

    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    api_port: int = Field(default=8000, env="API_PORT")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")

    batch_size: int = Field(default=50, env="BATCH_SIZE")
    timeout: int = Field(default=30, env="TIMEOUT")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

  - 将 `.env` 中的敏感变量替换为实际值（OPENAI_API_KEY 等）。
- acceptance:
  - `.env` 与 `config.py` 均可读，`python -c "from config import settings; print(settings.api_port)"` 输出 8000。
  - 变量可从环境覆盖且大小写不敏感（case_sensitive=False）。

### 阶段2：数据模型定义

Step 2.1: 定义 Pydantic 数据模型（优先基于 Tech_Decisions.md §4；不足处参考 DevPlan.md §4.1）
- sub_steps:
  - 在 `Kobe/TelegramCuration/models.py` 添加基础导入：

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
```

  - 定义 ChatMessage（来自 Tech_Decisions.md §4.1 完整示例）：

```python
class ChatMessage(BaseModel):
    message_id: str
    chat_id: str
    sender: str
    text: str | None = None
    created_at: datetime
    reply_to: str | None = None
    media: list[str] | None = None
    reactions: list[str] | None = None
    forwards: int = 0
    is_pinned: bool = False
    is_service: bool = False
```

  - 按 §4.2–§4.5 的字段规范，定义下列模型（基于规范补齐为 Pydantic 定义）：

```python
class NormalizedMessage(BaseModel):
    message_id: str
    text_clean: Optional[str] = None
    entities: List[str] = []
    urls: List[str] = []
    hashtags: List[str] = []
    mentions: List[str] = []
    created_at: datetime

class Thread(BaseModel):
    thread_id: str
    message_ids: List[str]
    representative: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    topic: Optional[str] = None
    participants: List[str] = []
    turns: int = 0
    coherence_score: float = 0.0

class KnowledgeSlice(BaseModel):
    slice_id: str
    title: str
    summary: str
    tags: List[str] = []
    sources: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    lifecycle: str = "draft"  # draft/published/deprecated
    owner: Optional[str] = None
    score: float = 0.0
    freshness: Optional[int] = None

class QAPair(BaseModel):
    question: str
    answers: List[str] = []
    evidence_ids: List[str] = []
    confidence: float = 0.0
```

  - 如需 API 请求/响应模型（DevPlan.md §4.1 已给出），可补充：

```python
class QueryRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: dict = {}

class QueryResponse(BaseModel):
    hits: List[dict] = []
    latency_ms: int = 0
```

- acceptance:
  - 可 `from Kobe.TelegramCuration.models import ChatMessage, KnowledgeSlice` 正常导入。
  - 字段名、类型与 §4.1–§4.5 规范一致；必填/默认值符合规范。
  - 对示例数据进行实例化不报错。

### 阶段3：核心功能实现

Step 3.0: 准备提示词模板（LLM）（见 Tech_Decisions.md §2.1–§2.3）
- sub_steps:
  - 在 `Kobe/TelegramCuration/` 新建 `prompts/` 目录与文件：`classifier.md`、`slice_summarizer.md`、`qa_generator.md`。
  - 复制下列模板至对应文件（原样来自 Tech_Decisions.md，保留 JSON 输出约束）：

classifier.md（§2.1 信息筛选/结构化标注）
```
你是一名企业知识治理的筛选与标注专家。请阅读若干条来自 Telegram 的原始消息，去除噪声和与业务无关的内容，判断每条消息是否属于“可用于业务知识库沉淀的有价值信息”。要求：

1) 判断标准：
   - 有价值：涉及业务流程、产品问题、客户反馈、复盘、指标、可复用操作经验等；
   - 无价值：泛闲聊、转发链接无上下文、贴图表情、系统通知；
2) 输出严格的 JSON 对象（仅一层），包含：
   {
     "usable": true|false|"verify",
     "reason": "30-60字说明",
     "topic": "主题(可选)",
     "entities": ["关键实体1","关键实体2"],
     "actions": ["动作1","动作2"],
     "confidence": 0.0-1.0
   }
3) 当无法确定时设置 usable="verify" 并在 reason 中说明需要人工确认的点。
4) 严格只输出 JSON，不要额外文字。

输入：messages（字符串数组，最多20条）。
输出：与输入等长的 JSON 结果数组。
```

slice_summarizer.md（§2.2 知识切片摘要生成）
```
你是一名文档编辑与知识沉淀专家。针对同主题的对话线程（已聚合），请在保持事实与引用可追溯的前提下，生成一个便于复用的“知识切片”摘要。严格输出 JSON：
{
  "title": "12-20字标题",
  "summary": "200-400字摘要",
  "bullets": ["要点1","要点2","要点3"],
  "sources": ["msg:123","msg:456"],
  "time_window": "2025-10-01 ~ 2025-10-03",
  "scope": "边界与适用范围(50-100字)",
  "confidence": 0.0-1.0
}
要求：
1) sources 必须为原始消息 ID；
2) 摘要须可读、客观、中立；
3) 仅输出 JSON；
输入：thread_messages（包含 message_id/text/created_at/sender）。
```

qa_generator.md（§2.3 切片到 QA 生成）
```
你是一名知识问答构建专家。请基于给定的知识切片集合，生成可用于检索与评测的标准 QA 对。仅输出 JSON 数组，每个元素：
{
  "question": "...",
  "answer": "...",
  "slice_id": "...",
  "evidence_ids": ["msg:..."],
  "confidence": 0.0-1.0
}
要求：
1) 问题覆盖切片的关键要点；
2) 答案可直接由切片证据支持；
3) evidence_ids 必须为原始消息 ID；
4) 严格只输出 JSON。
输入：slices（包含 slice_id/title/summary/sources）。
```

- acceptance:
  - 三个模板文件存在；内容与 Tech_Decisions.md 对应章节一致，且仅 JSON 输出。

Step 3.1: 实现核心服务逻辑（见 DevPlan.md §4.2；技术细节见 Tech_Decisions.md §1、§2、§7）
- sub_steps:
  - 在 `services.py` 添加必要导入：`bs4`、`lxml`、`orjson`、`httpx`、`openai.AsyncOpenAI`、`config.settings`、`Kobe.SharedUtility.RichLogger`。
  - 实现 `parse_telegram_export(path: str, chat_id: str, since: str|None=None, until: str|None=None) -> list[ChatMessage]`：
    - 解析 Telegram HTML/JSON 导出（bs4+lxml），按时间/会话过滤；
    - 产出 ChatMessage 列表；记录总计与耗时日志；
    - 异常：FileNotFoundError、ValueError（格式错误）、UnicodeDecodeError；
    - 参考：Tech_Decisions.md §1.1（依赖）、§4.1（字段规范）。
  - 实现 `build_knowledge_slices(threads: list[Thread]) -> list[KnowledgeSlice]`：
    - 汇总同主题消息，调用 LLM 模板（slice_summarizer.md；Tech_Decisions.md §2.2）；
    - 控制批量与速率（批量50、60/min；§2）；
    - 解析 JSON（orjson）；
    - 日志包含分片数量与异常条目统计。
  - 如需字段筛选或分类函数，调用 classifier.md（Tech_Decisions.md §2.1）；如需 QA 生成，调用 qa_generator.md（§2.3）。
- acceptance：
  - `from Kobe.TelegramCuration.services import parse_telegram_export, build_knowledge_slices` 可导入；
  - 对样例数据运行能得到非空结果（本阶段可用最小样本验证）；
  - 关键事件日志可见（开始、完成、数量、耗时、异常捕获）。

### 阶段4：API 路由实现（如需 HTTP API）

Step 4.1: 实现 FastAPI 路由（见 Tech_Decisions.md §3.2；DevPlan.md §4.3）
- sub_steps：
  - 在 `routers.py`：

```python
from fastapi import APIRouter, HTTPException
from Kobe.TelegramCuration.models import QueryRequest
from Kobe.TelegramCuration.services import parse_telegram_export
router = APIRouter(prefix="/api/telegram-curation", tags=["TelegramCuration"])
```

  - 实现 POST `/ingest/start`：请求体字段 `sourceDir`、`workspaceDir`；返回 `{task_id}`（见 §3.2）。
  - 实现 GET `/task/{task_id}`：返回任务状态 `{ task_id, status, progress, stats }`。
  - 实现 POST `/slices/query`：请求 `{ query, topK }`；返回 `hits`（见 §3.2）。
  - 在 `Kobe/main.py` 注册：`from Kobe.TelegramCuration.routers import router as telegram_router; app.include_router(telegram_router)`。
  - 启动：`uvicorn Kobe.main:app --reload --port 8000`。
  - 测试命令（来自 §3.2）：

```
curl -X POST http://localhost:8000/api/telegram-curation/ingest/start \
  -H "Content-Type: application/json" \
  -d '{"sourceDir":"D:/AI_Projects/TelegramChatHistory/Original","workspaceDir":"D:/AI_Projects/TelegramChatHistory/Workspace"}'
```

- acceptance：
  - 服务可启动无异常；以上 curl 返回 200 且结构与 §3.2 一致；
  - 错误请求返回 4xx，异常处理返回 `{ error, code }`。

### 阶段5：Celery 任务封装（如需后台任务）

Step 5.1: 注册 Celery 任务（见 DevPlan.md §4.4；Tech_Decisions.md §7 映射）
- sub_steps：
  - 在 `tasks.py` 定义任务：
    - `telegram.ingest_channel(chat_id: str, since: str, until: str) -> {ingested: int}`（重试：5次；超时30min）。
    - `telegram.build_slices(window: str, policy: str) -> {slices: int}`（重试：3次；超时60min）。
    - `telegram.index_batch(batch_id: str) -> {indexed: int}`（重试：5次；超时20min）。
    - `telegram.evaluate_quality(dataset: str) -> {accuracy: float, coverage: float}`（重试：2次；超时15min）。
  - 使用项目 `Kobe/SharedUtility/TaskQueue` 的装饰器/Client（如有）。
- acceptance：
  - 任务可被调用并返回结构化结果；
  - 日志包含开始、完成、异常信息与耗时；
  - 与路由/服务层耦合清晰（无循环依赖）。

### 阶段6：集成与完善

Step 6.1: 更新模块索引与关系（见 DevPlan.md §5；Tech_Decisions.md §7）
- sub_steps：
  - 在 `Kobe/TelegramCuration/` 创建 `index.yaml`：

```yaml
module_name: TelegramCuration
description: Telegram 聊天记录整顿与知识切片/QA 支持
version: 1.0.0
exports:
  - name: parse_telegram_export
    type: function
    path: services.py
    description: 解析 Telegram 导出
  - name: KnowledgeSlice
    type: model
    path: models.py
    description: 知识切片数据模型
dependencies:
  - RichLogger
  - TaskQueue
```

  - 在 `Kobe/index.yaml` 增加：

```yaml
relations:
  - path: TelegramCuration/index.yaml
    type: feature_module
```

- acceptance：
  - 两个 YAML 均为合法 YAML（可被 `python -c "import yaml,sys;yaml.safe_load(open('Kobe/TelegramCuration/index.yaml','r',encoding='utf-8'))"` 解析）。

Step 6.2: 编写模块 README（见 DemandDescription.md §1–§4、Tech_Decisions.md §3/§5）
- sub_steps：
  - 在 `Kobe/TelegramCuration/README.md` 填写：功能说明、使用方式（代码示例）、配置说明（.env 关键项）、API 文档引用（§3）。
- acceptance：
  - README 覆盖功能、使用、配置三部分并能独立指导运行。

### 阶段7：测试与验收

Step 7.1: 单元测试（见 Tech_Decisions.md §8）
- sub_steps：
  - 目录：`Kobe/TelegramCuration/tests/`；文件：`test_models.py`, `test_services.py`。
  - `test_models.py`：校验 ChatMessage/KnowledgeSlice 字段与默认值；非法输入触发 ValidationError。
  - `test_services.py`：使用最小样例（3–5条消息）验证 `parse_telegram_export` 与 `build_knowledge_slices`。
  - 运行：`pytest Kobe/TelegramCuration/tests -q`。
- acceptance：
  - 通过率 100%；核心函数覆盖测试，覆盖率 ≥ 70%。

Step 7.2: 功能与性能验证（见 DemandDescription.md 性能与验收条款）
- sub_steps：
  - 功能：按需求文档的使用场景执行端到端，验证输出结构与期望一致；
  - 性能：P95 响应时间 ≤ 800ms；吞吐量 ≥ 50 req/s（以 `/slices/query` 为基准进行压测）；
  - 可追溯性：知识库条目需附带源消息 ID，追溯率 = 100%；
  - 质量：样本 100 条消息的清洗/标注准确率 ≥ 95%。
- acceptance：
  - 所有指标达标；错误处理覆盖无效输入与边界条件；
  - 形成一份“全流程操作指引 + 报告”。

---

## 需求到实现映射

- 原始导出解析 → 模块：TelegramCuration.services → 文件：`Kobe/TelegramCuration/services.py` → 技术：bs4+lxml（Tech_Decisions.md §1.1）。
- 对话规整/去噪 → 模块：TelegramCuration.services → `services.py` → 规则+Pydantic 校验（§4.2/§4.6/§4.7）。
- 话题聚类/线程 → 模块：TelegramCuration.services → `services.py` → 基于时间/引用关系的线程化（参见 DevPlan.md §4.3 Thread）。
- 知识切片生成 → 模块：TelegramCuration.services → `services.py` → LLM 模板 §2.2。
- QA 生成与查询 → 模块：TelegramCuration.services/routers → `services.py`/`routers.py` → LLM 模板 §2.3 与 `/slices/query`。
- 后台任务编排 → 模块：TelegramCuration.tasks → `Kobe/TelegramCuration/tasks.py` → Celery（§1.1）。
- API 接入 → 模块：TelegramCuration.routers → `routers.py` → 路由/中间件（§3）。
- 配置与密钥 → 模块：Kobe.config → `Kobe/config.py` + `.env`（§5）。

依赖关系（执行顺序）
- 配置（Step 1.2）在前 → 数据模型（Step 2.1）→ 业务逻辑（Step 3.1）→ API（Step 4.1）→ 任务队列（Step 5.1）→ 集成文档（Step 6）→ 测试与验收（Step 7）。

---

## 执行顺序说明

1) 严格按阶段顺序执行（阶段0 → 阶段7）。
2) 阶段内标记 [P] 的任务可并行（本清单默认串行）。
3) 每完成一个 Step，依据 acceptance 清单自检。

---

## 性能验证清单（依据 DemandDescription.md）

- [ ] P95 响应时间 ≤ 800 ms
- [ ] 吞吐量 ≥ 50 req/s
- [ ] 后台作业 2 小时内处理 ≥ 100 万条消息（如涉及批处理）

---

## 功能验收清单（依据 DemandDescription.md）

- [ ] 提供“全流程操作指引 + 报告”文档
- [ ] 至少一个对话样本通过一次人工校验
- [ ] 100 条样本清洗/标注准确率 ≥ 95%
- [ ] 知识库条目 100% 可追溯到源消息 ID

---

## 规范引用

- CodexFeatured/Common/BackendConstitution.yaml
- CodexFeatured/Common/CodeCommentStandard.yaml
- Tech_Decisions.md（依赖/提示词/API/字段/配置）
- DevPlan.md（目录/模块/接口/数据模型示例）
- DemandDescription.md（业务目标/性能/验收）

工作流版本：2.1 | 生成时间：2025-10-11 21:05:00

---

## 质量门控自检（输出前校验）

- 前置文档引用完整性：已在依赖、配置、数据模型、API、提示词各步骤标注 Tech_Decisions.md 对应章节。
- 业务目标覆盖度：
  - 导出解析/规整/分片/QA/检索/API/任务队列均有对应步骤；
  - 交付物（操作指引+报告）在阶段7明确产出。
- 任务原子性：各 sub_step 为单一、可手动执行动作，且具有明确产出或校验命令。
- 技术细节完整性：
  - 依赖含库名+版本；
  - 配置包含 .env 与 config.py 原文；
  - 提示词模板完整粘贴在 Step 3.0；
  - API 路由与 curl 测试命令已给出。
- 验收标准完整性：每个 Step 均列出 acceptance，具可验证条件与期望结果。
