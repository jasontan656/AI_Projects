# 测试场景文档：TelegramCuration

标识信息：MODULE_NAME=TelegramCuration；COUNT_3D=005；INTENT_TITLE_2_4=TelegramChatKnowledgeCuration；生成时间=2025-10-11 12:00:00

**参考文档**：
- 需求文档：D:/AI_Projects/CodexFeatured/DevPlans/005_TelegramChatKnowledgeCuration/DemandDescription.md
- 开发计划：D:/AI_Projects/CodexFeatured/DevPlans/005_TelegramChatKnowledgeCuration/DevPlan.md
- 技术决策：D:/AI_Projects/CodexFeatured/DevPlans/005_TelegramChatKnowledgeCuration/Tech_Decisions.md
- 任务清单：D:/AI_Projects/CodexFeatured/DevPlans/005_TelegramChatKnowledgeCuration/Tasks.md

**输出路径**：D:/AI_Projects/Kobe/SimulationTest/TelegramCuration_testscenarios.md

---

## 1. 项目理解

### 1.1 开发目的
- 将 Telegram 聊天记录转化为结构化、可检索、可审计的业务知识与问答素材，支撑客服问答、报价引导、信息收集与风格一致性管控（需求文档第1节）。
- 业务价值：统一口径、提升响应一致性与效率、沉淀可复用知识、辅助报价与需求澄清、降低培训成本（需求文档第3节“业务价值”）。

### 1.2 核心功能（从需求文档第3节整理，并结合现有代码实现）
- 导入与解析：将 Telegram 导出（HTML/JSON）解析为结构化 `ChatMessage` 列表（现有实现：`services.parse_telegram_export`）。
- 主题线程与知识切片：按会话线程生成 `KnowledgeSlice`（现有占位实现：`services.build_knowledge_slices`；后台任务名：`telegram.build_slices`）。
- 基础 API：
  - POST `/api/telegram-curation/ingest/start`（启动异步导入，返回 task_id）。
  - GET `/api/telegram-curation/task/{task_id}`（查询占位任务状态）。
  - POST `/api/telegram-curation/slices/query`（查询切片，当前占位返回空）。
- 任务队列能力（依赖模块 TaskQueue）：
  - 通用任务接口：POST `/task/start`、GET `/task/status/{task_id}`、GET `/task/result/{task_id}`。
  - Telegram 专属任务：`telegram.ingest_channel`、`telegram.build_slices`、`telegram.index_batch`、`telegram.evaluate_quality`。
- 性能/质量（需求文档第5节）：全量10万消息 ≤ 30 分钟；增量5千消息 ≤ 5 分钟；检索 P95 ≤ 800ms；并发 ≥ 50 rps/5 分钟；噪声剔除准确率 ≥ 95% 等。

### 1.3 技术架构（结合 DevPlan 与代码）
- 顶层应用：`Kobe/main.py` FastAPI 应用，挂载 `/health`、`/task/*` 与 `/api/telegram-curation/*` 路由。
- 模块边界：
  - `Kobe/TelegramCuration`（本模块）：`models.py`、`services.py`、`routers.py`、`tasks.py`、`utils.py`、`prompts/`。
  - `Kobe/SharedUtility/TaskQueue`：Celery 应用封装（`app.py`）、任务注册（`registry.py@task/send_task`）、演示任务（`tasks.py`）、API 数据模型（`schemas.py`）。
- 依赖关系：FastAPI、Pydantic v3、Celery（RabbitMQ 作为 broker，Redis 可选作结果后端）、可选 bs4 + lxml 解析 HTML、orjson（如可用）。（详见 Tech_Decisions.md §1、§3、§5）
- 运行/部署：使用 `uvicorn Kobe.main:app` 启动 API；`celery -A Kobe.SharedUtility.TaskQueue.app:app worker -l info` 启动 worker；可选 Prometheus 指标暴露 `/metrics`。

### 1.4 实现细节（从代码提取）
- API 端点：
  - GET `/health`（健康检查）。
  - POST `/task/start`、GET `/task/status/{task_id}`、GET `/task/result/{task_id}`（任务编排）。
  - POST `/api/telegram-curation/ingest/start`、GET `/api/telegram-curation/task/{task_id}`、POST `/api/telegram-curation/slices/query`。
- CLI 命令：
  - 启动服务：`uvicorn Kobe.main:app --host 0.0.0.0 --port 8000`。
  - 启动 Celery：`celery -A Kobe.SharedUtility.TaskQueue.app:app worker -l info`。
- Celery 任务（TelegramCuration）：`telegram.ingest_channel`、`telegram.build_slices`、`telegram.index_batch`、`telegram.evaluate_quality`。
- 依赖服务：RabbitMQ（必需，`RABBITMQ_URL`）、Redis（可选结果后端，`REDIS_URL`）、MongoDB/ChromaDB（在需求与技术决策中列出，用于持久化与向量检索，当前代码未直接调用）。
- 数据流（现阶段）：
  1) 客户端上传/指定导出文件目录 →
  2) API `/api/telegram-curation/ingest/start` 返回任务 ID →
  3)（预期）后台任务 `telegram.ingest_channel` 调用 `services.parse_telegram_export` 解析消息 →
  4)（预期）线程聚合/切片生成，通过 `telegram.build_slices` 与 `services.build_knowledge_slices` →
  5)（预期）索引入库（MongoDB/ChromaDB）与查询 `/api/telegram-curation/slices/query`。
- 配置项（来自 DevPlan/Tech_Decisions）：
  - 数据库/中间件：`MONGODB_URI`、`REDIS_URL`、`RABBITMQ_URL`、`CHROMADB_URL`。
  - LLM：`OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL`。
  - 应用：`APP_ENV`、`DEBUG`、`LOG_LEVEL`、`API_HOST`、`API_PORT`、`BATCH_SIZE`、`TIMEOUT`。

---

## 2. 测试场景设计

说明：以下覆盖7个维度，共71个场景。每个场景均给出“优先级/描述/输入/操作/预期输出/验收标准/随机化策略/依赖关系”。API 路径与任务名均来自现有代码；对 MongoDB/ChromaDB/LLM 等虽未在代码中直接调用，但保留场景以契合需求与技术决策，作为系统级验证与回归的先行定义。

### 2.1 维度1：功能覆盖（16 个）

#### Scenario-1.1：正常导入小文件（JSON）
- 优先级：P0
- 描述：解析包含 18 条消息的 JSON 导出为 `ChatMessage` 列表。
- 输入：
  * 文件：`test_data/telegram_small.json`（18 条，字段包含 id/text/date/from）
  * API：POST `/api/telegram-curation/ingest/start`
  * payload：`{"sourceDir":"test_data/","workspaceDir":"outputs/"}`
- 操作：
  1) 调用导入 API 获取 `task_id`；
  2) 轮询 GET `/api/telegram-curation/task/{task_id}`，直到返回占位状态；
  3) 脚本直调 `services.parse_telegram_export(path, chat_id)` 比对解析条数。
- 预期输出：
  * 返回 `task_id` 非空；
  * `parse_telegram_export` 返回 18 条，时间升序；
  * 日志包含 `parse_telegram_export: start/done` 且 `count=18`。
- 验收标准：
  * 无异常；
  * 字段完整：`message_id/sender/text/created_at`；
  * 升序排序稳定。
- 随机化策略：消息内容随机生成（长度 10–120 字），`sender` 从 3 人中随机；
- 依赖关系：无。

#### Scenario-1.2：正常导入小文件（HTML）
- 优先级：P0
- 描述：解析 20 条消息的 HTML 导出。
- 输入：`test_data/telegram_small.html`（20 条，Telegram 标准类名 `.message/.from_name/.text/.date`）
- 操作：同 Scenario-1.1，另验证 HTML 分支。
- 预期输出：解析 20 条；字段完整；无 XSS 注入（纯文本）。
- 验收标准：解析成功；字段不为空（必要字段）；HTML 标签文本化。
- 随机化策略：`text` 随机嵌入 emoji/URL/换行。
- 依赖关系：无。

#### Scenario-1.3：空文件导入
- 优先级：P1
- 描述：导入 0 条消息的 HTML/JSON。
- 输入：`test_data/telegram_empty.html|json`
- 操作：直调服务函数并记录返回长度。
- 预期输出：返回空列表；无异常。
- 验收标准：长度=0；日志 `count=0`。
- 随机化策略：无。
- 依赖关系：无。

#### Scenario-1.4：格式错误 JSON（顶层非数组）
- 优先级：P0
- 描述：JSON 顶层为对象时抛出 `ValueError`。
- 输入：`test_data/telegram_bad.json`（`{"messages":[]}`）
- 操作：调用 `parse_telegram_export` 捕获异常。
- 预期输出：`ValueError: expected a list of messages`。
- 验收标准：异常类型与信息匹配；无进程崩溃。
- 随机化策略：无。
- 依赖关系：无。

#### Scenario-1.5：缺失文件
- 优先级：P0
- 描述：路径不存在时抛出 `FileNotFoundError`。
- 输入：`test_data/not_exist.html`
- 操作：调用 `parse_telegram_export`。
- 预期输出：抛出 `FileNotFoundError`。
- 验收标准：异常类型正确；日志包含 start 行。
- 随机化策略：无。
- 依赖关系：无。

#### Scenario-1.6：bs4 未安装（HTML 分支）
- 优先级：P1
- 描述：卸载/禁用 bs4 时解析 HTML 抛出 `ValueError("bs4 is required")`。
- 输入：`test_data/telegram_small.html`
- 操作：在隔离环境卸载 bs4；调用解析。
- 预期输出：明确报错信息。
- 验收标准：异常信息包含 `bs4`；JSON 分支不受影响。
- 随机化策略：无。
- 依赖关系：无。

#### Scenario-1.7：since/until 时间窗口过滤
- 优先级：P0
- 描述：仅返回指定日期范围内消息。
- 输入：`since=2025-09-01`，`until=2025-09-30`；样本 100 条跨 60 天。
- 操作：调用 `parse_telegram_export(path, chat_id, since, until)`。
- 预期输出：仅 9 月份消息；升序。
- 验收标准：边界包含性校验（含 09-01/09-30）。
- 随机化策略：消息时间戳在近 90 天内随机。
- 依赖关系：无。

#### Scenario-1.8：超长消息正文与多字节字符
- 优先级：P1
- 描述：解析 10KB 文本消息与大量 emoji/中日韩字符。
- 输入：构造长文本与混合字符。
- 操作：解析并统计长度与字符保真。
- 预期输出：文本不截断；编码正确；日志无 UnicodeError。
- 验收标准：原文==解析结果；包含 emoji 字面。
- 随机化策略：长度 1–10KB 随机，字符集随机。
- 依赖关系：无。

#### Scenario-1.9：引用链与回复关系（reply_to）
- 优先级：P1
- 描述：包含回复链的对话，`reply_to` 正确填充。
- 输入：含 `reply_to_message_id` 字段的 JSON。
- 操作：解析并构造图谱校验链路。
- 预期输出：被引用消息必须存在；不存在则忽略回复字段。
- 验收标准：随机抽 20% 样本比对。
- 随机化策略：随机生成 10–30% 回复关系。
- 依赖关系：无。

#### Scenario-1.10：服务端 API—启动导入
- 优先级：P0
- 描述：POST `/api/telegram-curation/ingest/start` 正常返回任务 ID。
- 输入：payload 同 Scenario-1.1。
- 操作：调用 API → 校验返回结构。
- 预期输出：`{"task_id": "telegram.ingest_channel:..."}`。
- 验收标准：HTTP 200；JSON 含 `task_id` 且非空。
- 随机化策略：无。
- 依赖关系：无。

#### Scenario-1.11：服务端 API—查询任务状态（占位）
- 优先级：P1
- 描述：GET `/api/telegram-curation/task/{task_id}` 返回占位状态。
- 输入：使用 Scenario-1.10 获取的 `task_id`。
- 操作：调用状态接口。
- 预期输出：形如 `{"task_id": id, "status": "PENDING", "progress": 0}`。
- 验收标准：HTTP 200；字段完整。
- 随机化策略：无。
- 依赖关系：Scenario-1.10。

#### Scenario-1.12：服务端 API—查询切片（占位）
- 优先级：P2
- 描述：POST `/api/telegram-curation/slices/query` 返回空列表。
- 输入：`{"query":"报价","top_k":10}`。
- 操作：调用 API。
- 预期输出：`{"hits": []}`。
- 验收标准：HTTP 200；结构正确。
- 随机化策略：查询关键词随机。
- 依赖关系：无。

#### Scenario-1.13：TaskQueue—启动 demo 任务 long_io
- 优先级：P1
- 描述：POST `/task/start` 提交 `task=long_io`，验证队列与状态流转。
- 输入：`{"task":"long_io","duration_sec":2}`。
- 操作：启动→轮询 `/task/status/{id}`→`/task/result/{id}`。
- 预期输出：状态从 PENDING→STARTED→SUCCESS；最终有 result。
- 验收标准：无 5xx；状态机符合 Celery 语义。
- 随机化策略：`duration_sec` 1–5 随机；`fail_rate` 0–0.1 随机。
- 依赖关系：RabbitMQ/（可选）Redis 就绪。

#### Scenario-1.14：TaskQueue—分片任务 sharded_job
- 优先级：P1
- 描述：`task=sharded_job` 且必填 `shard_key`，验证参数校验与执行。
- 输入：`{"task":"sharded_job","shard_key":"groupA"}`。
- 操作：同 Scenario-1.13。
- 预期输出：HTTP 200；状态 SUCCESS。
- 验收标准：缺失 `shard_key` 时 HTTP 400（路由层逻辑）。
- 随机化策略：`shard_key` 从集合 {A..E} 随机。
- 依赖关系：RabbitMQ/（可选）Redis。

#### Scenario-1.15：Telegram 专属 Celery 任务—ingest_channel
- 优先级：P0
- 描述：直接通过 `send_task('telegram.ingest_channel', ...)` 投递任务。
- 输入：`chat_id='@demo', since/until 可选`。
- 操作：调用注册器发送；轮询状态/结果。
- 预期输出：任务被接受；返回 `{"ingested": N}` 占位结果。
- 验收标准：状态 SUCCESS；日志含 `ingest_channel`。
- 随机化策略：`since/until` 随机开关。
- 依赖关系：RabbitMQ/（可选）Redis。

#### Scenario-1.16：构建知识切片—build_slices（占位）
- 优先级：P1
- 描述：投递 `telegram.build_slices`，验证任务注册与返回结构。
- 输入：`{"window":"last_7d","policy":"default"}`。
- 操作：投递→轮询→取结果。
- 预期输出：返回 `{"slices": 0}` 占位。
- 验收标准：状态 SUCCESS；无异常。
- 随机化策略：`window` 从 {last_1d,last_7d,last_30d} 随机。
- 依赖关系：RabbitMQ/（可选）Redis。

---

### 2.2 维度2：数据多样性（10 个）

#### Scenario-2.1：特殊字符与转义
- 优先级：P1
- 描述：文本包含 emoji、反引号代码块、HTML 标签与引号。
- 输入：
  * 消息1："Hello 😀"
  * 消息2："`python\nprint('hello')`"
  * 消息3："<script>alert('xss')</script>"
- 操作：JSON 分支解析→检查文本保真与安全。
- 预期输出：emoji 保留；代码块文本保留；HTML 标签在 HTML 分支转为纯文本。
- 验收标准：无脚本执行风险；文本不丢失。
- 随机化策略：多类型字符随机组合。
- 依赖关系：无。

#### Scenario-2.2：多媒体占位消息
- 优先级：P2
- 描述：存在仅媒体占位的消息，文本为空/None。
- 输入：构造 `text=None, media=['photo_1.jpg']` 的 JSON。
- 操作：解析并确认 `text` 可为空。
- 预期输出：对象生成成功；不抛异常。
- 验收标准：模型校验通过；字段默认值正确。
- 随机化策略：媒体类型从 {photo,video,doc} 随机。
- 依赖关系：无。

#### Scenario-2.3：极小数据（单条）
- 优先级：P2
- 描述：仅 1 条消息。
- 输入：`count=1`。
- 操作：解析并回传。
- 预期输出：长度=1；排序稳定。
- 验收标准：通过。
- 随机化策略：时间/长度随机。
- 依赖关系：无。

#### Scenario-2.4：中等数据（100–500条）
- 优先级：P1
- 描述：样本 300 条。
- 输入：`telegram_mid.json`（300 条）。
- 操作：解析并计时。
- 预期输出：耗时可接受（< 20 秒）且内存<200MB。
- 验收标准：计时与资源采集满足阈值。
- 随机化策略：长度 10–500 字随机；参与者 10–30 人随机。
- 依赖关系：无。

#### Scenario-2.5：大数据（10,000+）
- 优先级：P1
- 描述：导入 10,000–12,000 条。
- 输入：`telegram_large.json`。
- 操作：解析并计时。
- 预期输出：< 5 分钟完成；无 OOM。
- 验收标准：CPU/内存曲线稳定，峰值内存 < 500MB。
- 随机化策略：条数 9000–11000 随机；长度 10–500 字随机。
- 依赖关系：Scenario-1.1。

#### Scenario-2.6：跨时区时间戳
- 优先级：P2
- 描述：包含 UTC 与本地时区混杂的 `date` 字符串。
- 输入：HTML/JSON 混合样本。
- 操作：解析并统一为 UTC。
- 预期输出：`created_at` 合法且可比较。
- 验收标准：对同一真实顺序排序一致。
- 随机化策略：±12 小时偏移随机。
- 依赖关系：无。

#### Scenario-2.7：异常字符与控制符
- 优先级：P3
- 描述：包含 `\u0000`、软换行等控制字符。
- 输入：构造含控制符文本。
- 操作：解析与清洗。
- 预期输出：安全落地或剔除；无异常。
- 验收标准：无 UnicodeDecodeError；输出可序列化。
- 随机化策略：控制符插入 0–3 处随机。
- 依赖关系：无。

#### Scenario-2.8：超长用户名与群名
- 优先级：P2
- 描述：`sender` 与 `chat_id` 超过 64 字符。
- 输入：随机生成 65–120 字符。
- 操作：解析并检查溢出处理。
- 预期输出：仍可接受；必要时截断不失败。
- 验收标准：无异常；长度策略记录在案。
- 随机化策略：字符集/长度随机。
- 依赖关系：无。

#### Scenario-2.9：多语言混合文本
- 优先级：P2
- 描述：英文/中文/阿拉伯文/西里尔文混合。
- 输入：多语言样本。
- 操作：解析。
- 预期输出：保真；无乱码。
- 验收标准：字节级一致。
- 随机化策略：语言组合随机。
- 依赖关系：无。

#### Scenario-2.10：URL/提及/话题解析占位
- 优先级：P3
- 描述：为后续实体抽取预留样本，当前仅验证不报错。
- 输入：包含 `http://`、`@user`、`#tag`。
- 操作：解析。
- 预期输出：对象生成成功。
- 验收标准：通过。
- 随机化策略：URL/标签随机。
- 依赖关系：无。

---

### 2.3 维度3：并发与性能（8 个）

#### Scenario-3.1：10 并发导入请求（API）
- 优先级：P1
- 描述：10 个并发用户调用 `/api/telegram-curation/ingest/start`。
- 输入：10 个不同小文件（每个 ~100 条）。
- 操作：线程/异步并发；记录响应时间。
- 预期输出：全部 HTTP 200；平均 < 1 分钟；P95 < 2 分钟。
- 验收标准：无 5xx；日志无队列满/连接失败。
- 随机化策略：请求间隔 0–5 秒随机；文件大小 50–150 随机。
- 依赖关系：RabbitMQ 可用。

#### Scenario-3.2：100 并发启动 demo 任务
- 优先级：P2
- 描述：通过 `/task/start` 压力测试 Celery 投递链路。
- 输入：`task=long_io, duration_sec=1`。
- 操作：100 并发提交+轮询状态。
- 预期输出：无任务丢失；状态均可查询。
- 验收标准：丢失率=0；错误率<1%。
- 随机化策略：`fail_rate` 0–2% 随机以检验异常路径。
- 依赖关系：RabbitMQ；Redis（如启用结果后端）。

#### Scenario-3.3：持续 1 小时压力（低速）
- 优先级：P2
- 描述：每秒 1–5 次 `/task/start`，持续 60 分钟。
- 输入：`task=long_io`。
- 操作：发压→采集 CPU/内存/队列深度。
- 预期输出：稳定；无内存泄漏迹象。
- 验收标准：错误率 < 1%；RSS 曲线平稳。
- 随机化策略：间隔/持续时间随机微抖动。
- 依赖关系：稳定的 RabbitMQ。

#### Scenario-3.4：峰值突发（瞬时 200 QPS，10 秒）
- 优先级：P2
- 描述：短时高峰对 `/task/start` 与 `/task/status` 的复合压力。
- 输入：200 QPS 持续 10 秒。
- 操作：并发压测；观测 5xx 与队列。
- 预期输出：可降级但不崩溃；错误率<2%。
- 验收标准：服务存活；健康检查 `/health` 始终 200。
- 随机化策略：峰值注入时间点随机。
- 依赖关系：RabbitMQ/CPU 资源。

#### Scenario-3.5：解析性能基线（中等数据）
- 优先级：P1
- 描述：单机解析 5 千条 JSON 的耗时与内存。
- 输入：`telegram_5k.json`。
- 操作：计时+采样内存峰值。
- 预期输出：≤ 5 分钟；< 400MB。
- 验收标准：满足阈值。
- 随机化策略：文本长度/参与者多样化随机。
- 依赖关系：无。

#### Scenario-3.6：HTML 解析性能（大 DOM）
- 优先级：P2
- 描述：HTML 10k 条，含复杂 DOM 层级。
- 输入：`telegram_large.html`。
- 操作：计时。
- 预期输出：< 7 分钟；无栈溢出。
- 验收标准：通过。
- 随机化策略：标签密度随机。
- 依赖关系：bs4+lxml 可用。

#### Scenario-3.7：任务状态查询放大
- 优先级：P2
- 描述：同一 `task_id` 被 100 客户端并发轮询。
- 输入：`/task/status/{id}`。
- 操作：并发 GET；记录 P95。
- 预期输出：P95 < 200ms（本地）；无锁竞争阻塞。
- 验收标准：错误率<1%。
- 随机化策略：轮询频率 0.5–2s 随机。
- 依赖关系：Redis（如启用结果后端）。

#### Scenario-3.8：Prometheus 指标可用性
- 优先级：P2
- 描述：若启用 `prometheus_fastapi_instrumentator`，验证 `/metrics` 暴露。
- 输入：GET `/metrics`。
- 操作：抓取指标→检查 HTTP 计数器增长。
- 预期输出：指标存在且递增。
- 验收标准：采集无错误。
- 随机化策略：抓取间隔随机。
- 依赖关系：安装 instrumentator。

---

### 2.4 维度4：配置分支（12 个）

#### Scenario-4.1：RabbitMQ 正常
- 优先级：P0
- 描述：RabbitMQ 运行且可连接（`RABBITMQ_URL` 正确）。
- 输入：启动 worker；提交任务。
- 操作：`celery -A ... worker -l info`；调用 `/task/start`。
- 预期输出：任务成功；无重连告警。
- 验收标准：管理 UI 或日志显示连接健康。
- 随机化策略：无。
- 依赖关系：Docker/本机服务。

#### Scenario-4.2：RabbitMQ 宕机
- 优先级：P1
- 描述：关闭 RabbitMQ 后提交任务，观察降级与错误。
- 输入：停止服务。
- 操作：调用 `/task/start`。
- 预期输出：HTTP 5xx 或 4xx，错误信息明确；应用不崩溃。
- 验收标准：错误可观测；自动重试/失败提示到位。
- 随机化策略：宕机时间点随机。
- 依赖关系：无。

#### Scenario-4.3：Redis 结果后端开启
- 优先级：P1
- 描述：配置 `REDIS_URL` 并启用结果后端，验证 `/task/result` 可返回结果内容。
- 输入：`.env` 设置 `enable_result_backend=true`（若有）或按文档配置。
- 操作：提交任务→等待→取结果。
- 预期输出：`result` 字段非空。
- 验收标准：命中率>0（重复查询命中缓存）。
- 随机化策略：查询频率随机。
- 依赖关系：Redis 运行。

#### Scenario-4.4：Redis 关闭
- 优先级：P1
- 描述：不配置结果后端，仅状态可查询。
- 输入：默认 `.env`。
- 操作：提交任务→取结果。
- 预期输出：202 + `state` 返回，无 `result`。
- 验收标准：无异常；功能降级。
- 随机化策略：无。
- 依赖关系：无。

#### Scenario-4.5：MongoDB 本地/远程切换（预留）
- 优先级：P2
- 描述：配置 `MONGODB_URI` 指向本地与远程，验证连接与写入（当实现持久化后执行）。
- 输入：两组连接串。
- 操作：端到端导入→（预期）写入集合。
- 预期输出：集合存在且条数匹配。
- 验收标准：读回比对 100% 一致。
- 随机化策略：库名/集合前缀随机。
- 依赖关系：后续实现。

#### Scenario-4.6：ChromaDB 正常/异常（预留）
- 优先级：P2
- 描述：`CHROMADB_URL` 可用/不可用时的检索影响。
- 输入：设置/清空 URL。
- 操作：调用 `/api/telegram-curation/slices/query`。
- 预期输出：正常时命中>0；异常时降级或报错清晰。
- 验收标准：无崩溃；错误可观测。
- 随机化策略：网络延迟 0–200ms 注入。
- 依赖关系：后续实现。

#### Scenario-4.7：LLM 配置正确（预留）
- 优先级：P2
- 描述：`OPENAI_API_KEY`/`OPENAI_MODEL` 正常时切片摘要可生成。
- 输入：合法 Key。
- 操作：触发 `telegram.build_slices`。
- 预期输出：`summary` 非占位。
- 验收标准：成功率>95%。
- 随机化策略：批大小/速率限制随机。
- 依赖关系：后续实现。

#### Scenario-4.8：LLM 超时/失败（预留）
- 优先级：P2
- 描述：注入 10% 超时，验证重试与降级。
- 输入：timeout=1s；失败注入。
- 操作：触发切片任务。
- 预期输出：重试 3 次；最终失败标记可追踪。
- 验收标准：重试次数准确；错误日志清晰。
- 随机化策略：失败概率 5–15% 随机。
- 依赖关系：后续实现。

#### Scenario-4.9：DEBUG 与 Production 模式对比
- 优先级：P1
- 描述：`DEBUG=true/false` 对日志与错误暴露的影响。
- 输入：两套 `.env`。
- 操作：运行应用→触发典型请求。
- 预期输出：Debug 模式日志更详细；Prod 模式隐去栈细节。
- 验收标准：敏感信息不外泄。
- 随机化策略：请求顺序随机。
- 依赖关系：无。

#### Scenario-4.10：LOG_LEVEL 不同级别
- 优先级：P2
- 描述：`LOG_LEVEL`=DEBUG/INFO/WARN。
- 输入：三套 `.env`。
- 操作：压测→比对日志量与性能。
- 预期输出：等级越低日志越多；性能差异可接受。
- 验收标准：INFO 下性能满足指标。
- 随机化策略：请求模式随机。
- 依赖关系：无。

#### Scenario-4.11：BATCH_SIZE/TIMEOUT 调优（预留）
- 优先级：P2
- 描述：批大小/超时对吞吐与失败率影响。
- 输入：BATCH_SIZE=10/50/100，TIMEOUT=15/30/60。
- 操作：端到端导入→切片→检索。
- 预期输出：找到最优区间。
- 验收标准：综合指标最优（吞吐/错误率/成本）。
- 随机化策略：网延 0–200ms 随机。
- 依赖关系：后续实现。

#### Scenario-4.12：ALLOWED_TASKS 白名单
- 优先级：P1
- 描述：配置 `ALLOWED_TASKS` 限制可投递任务名。
- 输入：`ALLOWED_TASKS=telegram.ingest_channel,telegram.build_slices`。
- 操作：尝试发送未在名单中的任务名。
- 预期输出：返回 400 或抛出错误（后端 `ValueError`），请求被拒绝。
- 验收标准：仅白名单任务可执行。
- 随机化策略：名单子集随机。
- 依赖关系：TaskQueue 注册器。

---

### 2.5 维度5：异常与错误恢复（10 个）

#### Scenario-5.1：网络超时（LLM 调用占位）
- 优先级：P1
- 描述：模拟 LLM 调用 1s 超时并触发重试。
- 输入：timeout=1；失败注入 10%。
- 操作：触发 `telegram.build_slices`。
- 预期输出：自动重试 3 次；失败后标记“需人工复核”。
- 验收标准：重试间隔与次数正确；日志可追踪。
- 随机化策略：失败概率 5–15%。
- 依赖关系：后续实现。

#### Scenario-5.2：RabbitMQ 连接中断与恢复
- 优先级：P1
- 描述：任务执行时重启 RabbitMQ。
- 输入：长任务（`long_io` 10s）。
- 操作：投递后 5 秒重启服务。
- 预期输出：自动重连；任务继续或重试。
- 验收标准：无数据丢失；最终可查询状态。
- 随机化策略：重启时刻随机。
- 依赖关系：RabbitMQ。

#### Scenario-5.3：Celery worker 重启
- 优先级：P1
- 描述：执行中重启 worker。
- 输入：`long_io` 10s。
- 操作：5 秒后重启 worker。
- 预期输出：任务不丢；最终完成或失败可见。
- 验收标准：无重复处理；状态一致。
- 随机化策略：重启次数 1–2 次随机。
- 依赖关系：RabbitMQ/Redis（可选）。

#### Scenario-5.4：磁盘空间不足（工作区）
- 优先级：P2
- 描述：工作目录不可写/满盘。
- 输入：将工作区指向只读目录。
- 操作：启动导入。
- 预期输出：明确错误；不崩溃。
- 验收标准：错误日志可读；HTTP 4xx/5xx 合理。
- 随机化策略：目录随机挑选。
- 依赖关系：无。

#### Scenario-5.5：内存不足压力（解析大 DOM）
- 优先级：P2
- 描述：受限内存容器运行 HTML 解析。
- 输入：限制容器内存 512MB。
- 操作：解析 10k 条 HTML。
- 预期输出：无 OOM；必要时分批。
- 验收标准：监控曲线无崩溃。
- 随机化策略：批大小随机。
- 依赖关系：容器环境。

#### Scenario-5.6：中途取消任务
- 优先级：P2
- 描述：投递后立刻撤销任务。
- 输入：获取 `task_id` 后调用 revoke（若暴露）。
- 操作：撤销→观察状态。
- 预期输出：状态变更为 REVOKED 或 FAILURE。
- 验收标准：无僵尸任务。
- 随机化策略：撤销时机随机。
- 依赖关系：Celery revoke 能力。

#### Scenario-5.7：不合法任务名
- 优先级：P0
- 描述：`task` 不满足 slug 正则（含大写/空格/特殊符号）。
- 输入：`{"task":"BAD-NAME!"}`。
- 操作：POST `/task/start`。
- 预期输出：HTTP 422（由 Pydantic 模型校验）。
- 验收标准：错误信息包含 pattern。
- 随机化策略：非法字符集随机。
- 依赖关系：TaskQueue/schemas。

#### Scenario-5.8：结果后端不可用
- 优先级：P2
- 描述：配置 Redis 但连接失败。
- 输入：错误 `REDIS_URL`。
- 操作：提交任务并获取结果。
- 预期输出：可查询状态但 `result` 不可用；错误日志提示。
- 验收标准：应用不崩溃；错误可观测。
- 随机化策略：错误地址随机。
- 依赖关系：Redis 关闭。

#### Scenario-5.9：HTML 结构异常
- 优先级：P1
- 描述：缺少 `.from_name` 或 `.text` 节点。
- 输入：畸形 HTML。
- 操作：解析并容错。
- 预期输出：跳过异常项；整体成功。
- 验收标准：无未捕获异常。
- 随机化策略：缺失字段随机。
- 依赖关系：无。

#### Scenario-5.10：JSON 字段类型异常
- 优先级：P1
- 描述：`text` 为对象/数组。
- 输入：构造非字符串 text。
- 操作：解析。
- 预期输出：通过 `str()` 转换成功（代码实现）。
- 验收标准：无异常；文本可序列化。
- 随机化策略：类型多样随机。
- 依赖关系：无。

---

### 2.6 维度6：依赖服务状态（8 个）

#### Scenario-6.1：MongoDB 宕机→恢复（预留）
- 优先级：P2
- 描述：停止 MongoDB → 导入失败 → 重启后重试成功。
- 输入：`MONGODB_URI` 指向本地实例。
- 操作：停止→导入→启动→重试。
- 预期输出：第一次失败；第二次成功；数据完整。
- 验收标准：错误信息明确；恢复正常。
- 随机化策略：重试间隔随机。
- 依赖关系：后续持久化实现。

#### Scenario-6.2：RabbitMQ 反压与队列深度
- 优先级：P1
- 描述：高并发提交导致队列积压。
- 输入：快速提交 1000 任务。
- 操作：观测队列深度与消费速率。
- 预期输出：系统可承受；无崩溃。
- 验收标准：消费-生产差恒定或逐步清空。
- 随机化策略：提交速率随机。
- 依赖关系：RabbitMQ。

#### Scenario-6.3：Redis 内存淘汰策略（如启用）
- 优先级：P3
- 描述：设置 `maxmemory` 与淘汰策略，观测结果丢失概率。
- 输入：Redis 配置。
- 操作：高频 `/task/result` 查询。
- 预期输出：在可控范围内；可降级到仅状态。
- 验收标准：业务无致命影响。
- 随机化策略：查询频率随机。
- 依赖关系：Redis。

#### Scenario-6.4：ChromaDB 心跳与版本端点
- 优先级：P3
- 描述：`/api/v2/heartbeat` 与 `/api/v2/version` 可访问。
- 输入：正常与异常两组。
- 操作：GET 端点。
- 预期输出：正常返回 200/版本号；异常时清晰错误。
- 验收标准：监控接入成功。
- 随机化策略：请求时间随机。
- 依赖关系：ChromaDB 实例。

#### Scenario-6.5：LLM 限流（429）
- 优先级：P3
- 描述：触发 429，验证指数退避与排队（当集成实现后）。
- 输入：速率超阈值。
- 操作：触发切片构建。
- 预期输出：退避重试；最终成功或失败可见。
- 验收标准：无雪崩；成本受控。
- 随机化策略：速率/批量随机。
- 依赖关系：后续实现。

#### Scenario-6.6：多依赖同时异常
- 优先级：P2
- 描述：RabbitMQ 暂停 + Redis 关闭。
- 输入：联合故障。
- 操作：提交任务并观察。
- 预期输出：稳定失败并提示；进程不崩溃。
- 验收标准：错误清晰；健康检查仍 200。
- 随机化策略：恢复顺序随机。
- 依赖关系：无。

#### Scenario-6.7：环境变量缺失
- 优先级：P1
- 描述：`.env` 缺少关键项（如 `RABBITMQ_URL`）。
- 输入：移除配置。
- 操作：启动应用/worker。
- 预期输出：启动失败或运行时报错清晰。
- 验收标准：错误信息包含变量名；不静默失败。
- 随机化策略：缺项随机。
- 依赖关系：无。

#### Scenario-6.8：Prometheus 端点暴露关闭
- 优先级：P3
- 描述：未安装 instrumentator 时不应暴露 `/metrics`。
- 输入：默认环境。
- 操作：GET `/metrics`。
- 预期输出：404 或未注册；应用正常。
- 验收标准：健康检查仍 200。
- 随机化策略：无。
- 依赖关系：无。

---

### 2.7 维度7：真实使用场景（7 个）

#### Scenario-7.1：个人聊天记录小规模导入→切片（占位）
- 优先级：P0
- 描述：100 条个人聊天→导入→（预期）生成 5–15 个知识切片。
- 输入：`telegram_personal.html`（100 条）。
- 操作：启动导入→等待→触发 `telegram.build_slices`。
- 预期输出：占位结果；任务成功。
- 验收标准：端到端无 5xx；日志链路完整。
- 随机化策略：消息/主题随机。
- 依赖关系：Scenario-1.2、1.16。

#### Scenario-7.2：工作群大规模导入（1 万条）
- 优先级：P0
- 描述：导入大群记录并验证性能阈值。
- 输入：`telegram_workgroup_10k.html`。
- 操作：同前；计时。
- 预期输出：≤ 5 分钟。
- 验收标准：满足阈值；无 OOM。
- 随机化策略：长度/参与者分布随机。
- 依赖关系：Scenario-2.5。

#### Scenario-7.3：多群批量导入（并行 5 个）
- 优先级：P1
- 描述：同时导入 5 个群（每个 500 条）。
- 输入：5 个文件。
- 操作：并发调 API/任务。
- 预期输出：全部成功；平均响应时间可接受。
- 验收标准：队列吞吐稳定；无丢失。
- 随机化策略：文件大小/顺序随机。
- 依赖关系：RabbitMQ。

#### Scenario-7.4：用户中途取消导入
- 优先级：P2
- 描述：用户因等待过长取消任务。
- 输入：`task_id`。
- 操作：revoke（若提供）→状态监控。
- 预期输出：REVOKED/FAILURE；资源释放。
- 验收标准：无残留临时文件。
- 随机化策略：取消时刻随机。
- 依赖关系：Celery revoke 能力。

#### Scenario-7.5：重复导入幂等
- 优先级：P1
- 描述：同一导出重复导入，验证幂等（后续持久化实现后执行）。
- 输入：同一文件两次。
- 操作：两次导入。
- 预期输出：第二次跳过/覆盖；无重复条目。
- 验收标准：条目总数不翻倍。
- 随机化策略：间隔时间随机。
- 依赖关系：持久化实现。

#### Scenario-7.6：检索问答路径（占位）
- 优先级：P2
- 描述：导入→切片→（预期）索引→查询 `/slices/query`。
- 输入：`query=报价`。
- 操作：端到端。
- 预期输出：命中列表包含来源与时间戳。
- 验收标准：命中率>0；延迟 P95<800ms。
- 随机化策略：关键词随机。
- 依赖关系：后续检索实现。

#### Scenario-7.7：合规与敏感信息校验（占位）
- 优先级：P2
- 描述：导入包含敏感项→（预期）清洗与可见范围控制。
- 输入：包含手机号/邮箱/价格细节的样本。
- 操作：端到端。
- 预期输出：敏感字段按策略处理。
- 验收标准：无泄露；日志可追溯。
- 随机化策略：敏感项分布随机。
- 依赖关系：策略实现。

---

## 3. 场景统计

| 维度 | 场景数量 | P0场景 | P1场景 | P2场景 | P3场景 |
|------|---------:|-------:|-------:|-------:|-------:|
| 功能覆盖 | 16 | 4 | 7 | 4 | 1 |
| 数据多样性 | 10 | 0 | 3 | 6 | 1 |
| 并发与性能 | 8 | 0 | 2 | 6 | 0 |
| 配置分支 | 12 | 1 | 5 | 5 | 1 |
| 异常恢复 | 10 | 2 | 5 | 3 | 0 |
| 依赖服务 | 8 | 0 | 2 | 5 | 1 |
| 真实场景 | 7 | 2 | 1 | 4 | 0 |
| 合计 | 71 | 9 | 25 | 33 | 4 |

说明：P0≥15 的目标将在后续实现落地（持久化/检索/LLM 集成）后追加收敛。本版优先保障已落地能力的可用性与稳健性，预留系统级场景以对齐需求与技术决策。

---

## 4. 执行顺序建议

1) 第一轮（冒烟+基础能力，约 60–90 分钟）：
- P0：Scenario-1.1/1.2/1.4/1.5/1.7/1.10/1.15/5.7/7.1/7.2（10 个）
- 目的：验证解析路径、关键 API、任务基本链路。

2) 第二轮（重要功能与边界，约 3–4 小时）：
- 核心 P1：1.3/1.6/1.8/1.9/1.11/1.13/1.14/1.16/2.4/3.1/3.5/4.1/4.2/4.3/4.4/5.2/5.3/5.9/5.10/6.2/6.7/7.3/7.5。

3) 第三轮（系统与可靠性补全，约 3 小时）：
- P2/P3：其余场景按模块并行执行，优先并发/配置分支/恢复类。

---

## 5. 随机化总策略

### 5.1 数据随机化
- 消息数量：指定范围内随机（如 10–20、9000–11000）。
- 消息内容：从预定义词库与模板随机生成，包含 emoji/URL/多语言。
- 消息顺序：导入前随机打乱，校验解析后排序稳定。
- 消息长度：10–10,000 字符随机，覆盖短/长文本。

### 5.2 时间随机化
- 请求间隔：0–5 秒随机抖动。
- 消息时间戳：近 90 天内随机，跨不同时区与夏令时边界。

### 5.3 配置随机化
- 每轮测试随机选择一种配置组合（RabbitMQ/Redis 开关、LOG_LEVEL、BATCH_SIZE/TIMEOUT）。

### 5.4 失败注入
- API 超时 10% 概率（对占位/后续实现的外部调用）。
- 网络中断 5% 概率（RabbitMQ/Redis）。
- 服务重启 1% 概率（worker/rabbitmq）。

---

## 6. 验收标准总览

### 6.1 功能性标准
- 第一轮 P0 场景全部通过（≥ 10 个）。
- 第二轮 P1 场景通过率 ≥ 95%。
- 无阻塞性 Bug（定义：任务链路不可用/解析失败率>5%）。

### 6.2 性能标准
- 解析：10k 条消息 < 5 分钟；内存峰值 < 500MB。
- API：健康检查稳定；任务状态查询 P95 < 200ms（本地）。
- 并发：`/task/start` 在 100 并发下错误率 < 1%。

### 6.3 稳定性标准
- 连续运行 1 小时无崩溃；错误率 < 1%。
- 故障恢复 < 10 秒（RabbitMQ/worker 重启后任务可继续/可重试）。

### 6.4 可观测性标准
- 关键操作均有日志（start/done + 关键计数）。
- 错误信息清晰、包含上下文（任务名/文件/范围）。
- 可通过日志与状态端点追踪一次任务的全链路。

---

工作流版本：2.0 | 生成时间：2025-10-11 12:00:00

