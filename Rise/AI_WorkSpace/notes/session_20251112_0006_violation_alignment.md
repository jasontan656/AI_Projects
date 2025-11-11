# Session Notes 2025-11-12 00:06 CST

## User Intent
- 用户希望依照 `D:\AI_Projects\.codex\prompts\WriteRise.md` 中对 violation 的定义（52-55 行）与处理方法（143-154 行），对 Rise 后端与 Up 前端的违规分层进行梳理，并讨论合规化落地细节。
- 目标是在讨论阶段形成一份覆盖全部违规点、整改路径、验证策略与风险登记的业务需求草案。

## Repo Context
- `D:\AI_Projects\Rise\src\interface_entry\bootstrap\application_builder.py`：入口层单文件集成环境加载、日志初始化、FastAPI 路由挂载、Telegram runtime bootstrap、任务队列监控等，头部 120 行展示了 `FastAPI` app、`TelemetryConsoleSubscriber`、`RuntimeSupervisor` 的直接依赖，说明接口层承担了 runtime/infra 细节。
- `D:\AI_Projects\Rise\src\business_logic\workflow\orchestrator.py`：业务逻辑层的 orchestrator 既定义 `WorkflowExecutionContext/WorkflowRunResult/WorkflowStageResult` dataclass，又直接调用 `append_chat_summary` 与 `get_mongo_database` 进行 Redis/Mongo 持久化，命中“业务逻辑直连基础设施”+“模型与处理混合”违规。
- `D:\AI_Projects\Rise\src\business_service\conversation\service.py`：>800 行的 TelegramConversationService 同时声明配置 dataclass、队列适配器、健康监控，全局变量 `_TASK_SUBMITTER_FACTORY/_CHANNEL_HEALTH_STORE` 与 helper 混杂。
- `D:\AI_Projects\Up\src\stores\workflowDraft.js`：Pinia store 内嵌 Schema 初始化 (`createEmptyWorkflow`)、API 调用 (`workflowService` CRUD)、状态管理，缺少独立 schema/service。
- `D:\AI_Projects\Up\src\stores\channelPolicy.js`：Store 统管策略 schema、健康轮询、频控节流、API 协调，导致状态层与业务层耦合。

## Technology Stack
- 后端：FastAPI、Pydantic v2、aiogram、Redis、MongoDB、RabbitMQ、aio-pika、OpenAI SDK（参见 `AI_WorkSpace/index.yaml` 依赖列表）。
- 前端：Vue 3 + Vite 5、Pinia、Element Plus、Vue Flow、CodeMirror 6；HTTP 客户端统一由 `src/services/httpClient.js` 注入 `X-Actor-*` 头。
- 配置：`.env` 管理 RabbitMQ/Redis/Mongo/Telegram 变量；观察性由 `foundational_service/telemetry` 负责。

## Search Results
- **Context7 (/ardalis/cleanarchitecture)**：强调 Core/UseCase/Infrastructure/Web 分层，入口层仅负责协议适配，业务逻辑应位于 Use Case 层，所有实体/Schema 需独立模块；同时给出验证在 Endpoint + Use Case 双重防御的策略，支撑我们拆分入口超载代码并保持上下游契合。
- **Exa (StudyRaid《Build Scalable Vue.js Apps with Pinia State Management》, 2025-01-16)**：主张 Pinia Store 聚焦状态，复杂业务逻辑下沉到服务/composable，支撑我们提出 store/service/schema 解耦；同一检索还返回 Marco Quintella 的 2025-05-17 实践文章，突出“store 只存状态，副作用交给服务”。
- **Exa (Dev.to《Layered Architecture & Dependency Injection: A Recipe for Clean and Testable FastAPI Code》, 2025-05-29)**：提出 FastAPI 分层：Presentation(路由)→Service→DAO，并利用 DI 保持入口最小化，呼应我们对 application_builder 过载的判定。
- **Web Search (`turn0search0`, `turn0search4`, `turn0search7`)**：Full Stack Hub / DeepWiki / Compile N Run 等 2025-06~10 的资料重申 FastAPI 项目需严格 API→Service→CRUD 链路，禁止跳层；Compile N Run 还指出“Keep routes clean, move business logic to service functions”，为我们制订整改目标提供公开基线。
- **Web Search (`turn0reddit13`, `turn0reddit16`, `turn0reddit19`)**：社区讨论强调在 FastAPI 中通过服务类 +依赖注入替代大量路由逻辑；`/r/FastAPI` 2024-12 的帖子特别提醒“路由层不应越权访问 repository”，作为违规判断的旁证。

## Architecture Findings
1. **入口层（Rise/interface_entry）超载**：`application_builder.py` 混入 logging/runtime/bootstrap 逻辑，违反“接口层只聚合路由与依赖注入”的要求；需拆出 `bootstrap/logging.py`, `runtime_supervisor.py`, `telegram_entry.py` 等职能模块。
2. **业务逻辑层触碰基础设施**：`workflow/orchestrator.py` 直接写 Redis/Mongo；应新建 `foundational_service/persist/workflow_summary_repository.py` 暴露 `append_summary(chat_id, summary)`，并将 dataclass 移入 `business_logic/workflow/models.py`。
3. **业务服务层臃肿**：`conversation/service.py` 汇聚 config/dataclass/队列操作/健康状态；需拆分 `conversation/config.py`, `conversation/runtime_adapter.py`, `conversation/health.py`，Service 聚焦 orchestrate。
4. **前端 Store 职责越界**：`workflowDraft.js`、`channelPolicy.js` 将 schema + service + state 集中，违背 Pinia “store 以状态为中心”实践；需建立 `src/schemas/workflow.js`, `src/services/workflowDraftService.js`, `src/services/channelHealthScheduler.js`。
5. **视图层缺少中间协调层**：`WorkflowBuilder.vue` 直接操控 store actions 与轮询逻辑，缺乏独立的 controller/composable，易再度堆叠逻辑。

## File References
- `D:\AI_Projects\Rise\src\interface_entry\bootstrap\application_builder.py`（入口层 1-120 行展示多重依赖）。
- `D:\AI_Projects\Rise\src\business_logic\workflow\orchestrator.py`（dataclass + `_persist_summary` 操作 Redis/Mongo）。
- `D:\AI_Projects\Rise\src\business_service\conversation\service.py`（全局变量与 dataclass 混杂）。
- `D:\AI_Projects\Up\src\stores\workflowDraft.js`、`...\channelPolicy.js`（state + schema + API 行为）。

## Violations & Remediation
1. **Violation #1/#4（Interface 层超载）**：`interface_entry/bootstrap/application_builder.py` → 拆分 logging/runtime/bootstrap 模块，入口仅保留 FastAPI app 创建与路由挂载；Runtime 逻辑移至 `interface_entry/runtime/supervisors.py` 扩展。
2. **Violation #2/#3（业务逻辑直连基建 + 模型混入）**：`business_logic/workflow/orchestrator.py` → 提取 dataclass 至 `business_logic/workflow/models.py`，新增 `foundational_service/persist/workflow_summary_repository.py` 处理 Redis/Mongo；Orchestrator 通过接口调用。
3. **Violation #1/#3（业务服务臃肿）**：`business_service/conversation/service.py` → 定义 `conversation/config.py`（dataclass）、`conversation/runtime_gateway.py`（TaskRuntime/Submitter 工厂）、`conversation/health_store.py`（健康逻辑）等，让 Service 只 orchestrate。
4. **Violation #1/#3（前端 Store 过载）**：`src/stores/workflowDraft.js` & `channelPolicy.js` → 建立 `src/schemas/*.js` 存放初始结构，`src/services/workflowDraftService.js`、`channelHealthService.js` 承担 API/轮询并由 stores 引用。
5. **Violation #4（视图直接调度逻辑）**：`src/views/WorkflowBuilder.vue` → 新建 `src/composables/useWorkflowBuilderController.js` 作为协调器，视图仅订阅状态与触发事件。

## Requirement Doc Update (2025-11-12 00:14)
- 已根据 Write Mode 产出业务需求文档：`AI_WorkSpace\Requirements\session_20251112_0014_violation_alignment.md`，覆盖 Background→Open Questions 结构。
- 文档引用外部实践：FastAPI 分层（turn0search1/turn0search2）与 Pinia Store 角色划分（turn0reddit12）。
- 关键约束与验证：
  - Rise 需落地 `workflow_summary_repository`、`conversation runtime gateway`；
  - Up 需新增 schemas/services/composables 并保持原 API 契约不变；
  - Acceptance 包含 Redis/Mongo、队列、前端轮询的 GIVEN/WHEN/THEN；
  - Exceptions 列举 Redis/Mongo 不可达、队列阻塞、健康轮询熔断等路径。

## Update 2025-11-12 00:40
- 按照“场景维度穷举”指令，已为 S1~S4 每个主场景补写 8 条子场景（核心/性能/安全/数据一致性/防御/观察性/人工/业务特殊），并在文档内保留触发条件、步骤序列、资源状态、输出反馈。
- 每条子场景同步给出多语言提示语、系统日志字段、告警/通知渠道及人工处理指引，实现 Step5 要求；提示语与日志格式整理进《提示语与交互设计汇总》。
- 新增 Data/State、Rules、异常与防御矩阵、Acceptance、自检等章节，明确 gov audit、repair queue、health scheduler 等新增资源链路，矩阵覆盖并发冲突、资源耗尽、依赖不可达、数据污染、配置缺失。
- “未覆盖清单”仅保留未来 SMS/Email 渠道占位，当前 8 维度已全部覆盖；Open Questions 保留 DI/Telemetry/频控/Gov SLA 待答复。

## Update 2025-11-12 00:50
- 将原先的 Open Questions 全部转为“Implementation Decisions”，明确：① FastAPI `Depends` + `lru_cache` 足以提供仓储共享；② Controller 级 telemetry 仅在 publish/health 操作采样；③ 频控默认 3 次/分钟并支持后端下发覆盖；④ Gov audit 可用率 <95% 连续 30 分钟时自动降级为人工导出并触发合规告警。
- 需求文档现无未解答问题，所有决策可直接指导重构落地，避免过度设计同时覆盖既定场景。
