# Session Notes 2025-11-11 23:20 CST

## User Intent
- 当前目标：根据 `D:\AI_Projects\.codex\prompts\WriteRise.md` 中的 violation 定义（52-55 行）与处理要求（143-154 行），梳理 Rise（后端）与 Up（前端）在分层合规上的违规点，并准备后续讨论/需求文档。
- 需要输出中文讨论，最终将形成业务需求文档，强调结构性合规与拆分策略。

## Repo Context
- `Rise/src/interface_entry/bootstrap/application_builder.py`（Interface/Entry 层）体量 > 400 行，直接负责日志初始化、环境变量覆写、FastAPI 路由、Telegram 引导、队列/Redis 管控等，混合大量 helper/生命周期逻辑（Violation #1/#4）。
- `Rise/src/business_logic/workflow/orchestrator.py`（Business Logic 层）在 orchestrate 时直接操作 `project_utility.db.append_chat_summary` 与 Mongo 集合（`get_mongo_database()`），同时定义 `WorkflowStageResult`, `WorkflowRunResult`, `WorkflowExecutionContext` dataclass（Violation #2/#3）。
- `Rise/src/business_service/conversation/service.py`（Business Service 层）包含 Adapter builder、任务入队、回调重试、Channel health 读写、多个 dataclass（`TelegramEntryConfig`, `_ConversationContext`, `AsyncResultHandle`）混在同文件，且直接 orchestrate worker/runtime（Violation #1/#3）。
- `Up/src/stores/workflowDraft.js`（Business Service 层）既定义 workflow schema（`createEmptyWorkflow`, inline strategy/metadata）又直接发起 CRUD/publish API 调用（Violation #1/#3，Store 过于肥大）。
- `Up/src/stores/channelPolicy.js`（Business Service 层）同时内联空 policy schema、健康轮询定时器、频控窗口逻辑、API 调度，导致 Store 持有状态+业务流程+限流策略（Violation #1/#3）。
- `Up/src/views/WorkflowBuilder.vue`（Interface 层）强耦合 6 个子面板与 Pinia store 细节；缺乏中间 Service 层，导致 Entry 层直接驱动业务动作（潜在 Violation #4，需在后续讨论中确认）。

## Technology Stack
- 后端：FastAPI + Telemetry/Redis/Mongo/AIO-Pika（依据 `AI_WorkSpace/index.yaml` 与 `PROJECT_STRUCTURE.md`）。
- 前端：Vue 3 + Vite 5 + Pinia + Element Plus；store 承担 API 协调（参考工程内 AGENTS.md 指南）。
- 现状：前后端均缺少明确的 schema/服务分层文件夹，导致 entry/service/store 直接耦合底层工具与 API。

## Search Results / External Guidance
- [CTX1] FastAPI 官方多路由拆分示例强调利用 `APIRouter` 与模块化组织，保持主应用轻量（支持 Violation #1/#4 的整改方向）。
- [EXA1] 2025-01-23 Clean Architecture 文章强调“分离关注点、层级依赖向内、可测试性”——支撑我们要求的 downward-only 依赖与模块拆分。
- `turn0search0`（Shopware Pinia 文档）建议 Store 拆分+类型导出，避免单文件塞入多职责。
- `turn0search1`（CodingEasyPeasy）提出“模块化 Store + 将复杂逻辑抽到 service/helper”以减少 Store 体积。
- `turn0reddit12` 讨论中建议把非 Vue 逻辑放到独立服务层，由 Store 调用，避免 state 与业务逻辑混杂。

## Architecture Findings
1. Entry 层（`interface_entry/bootstrap/application_builder.py`）直接持有长流程与 helper，违背“入口只做 routing/依赖注入”原则；需要拆分到 `bootstrap/logging.py`, `bootstrap/runtime.py`, `bootstrap/channel.py` 等模块，并以 orchestrator 方式调用。
2. Business Logic 层（`business_logic/workflow/orchestrator.py`）直接访问 Redis/Mongo（foundation），并在同文件定义 dataclass schema —— 需抽出 `workflow_models.py`（schemas）与 `workflow_summary_service.py`（持久化适配），Orchestrator 只 orchestrate。
3. Business Service 层（`business_service/conversation/service.py`）既定义 config/context/result dataclass，又维护全局单例/工厂、任务队列、健康/回放流程。建议：
   - 抽出 `conversation_context.py`（schemas）、`conversation_runtime.py`（TaskRuntime 适配）、`conversation_health_service.py`（健康 & fallback），Service 文件仅 orchestrate。
4. Up 侧 Pinia Store（`workflowDraft.js`, `channelPolicy.js`）包含 schema 定义 + API + 轮询/频控，导致 Store 逻辑臃肿，UI 难以复用。需提炼 `src/schemas/workflowDraft.js`, `src/services/workflowDraftMapper.js`, `src/services/channelHealthScheduler.js` 等，Store 仅处理 state/调度。

## File References
- `Rise/src/interface_entry/bootstrap/application_builder.py`（~1-220 行 helper + lifecycle）。
- `Rise/src/business_logic/workflow/orchestrator.py`（~1-200 行 dataclass + Mongo/Redis 调用）。
- `Rise/src/business_service/conversation/service.py`（~1-220 行 dataclass + runtime glue）。
- `Up/src/stores/workflowDraft.js`（~1-200 行 schema+API）。
- `Up/src/stores/channelPolicy.js`（~1-200 行 schema+health poll+API）。

## Violations & Remediation (per definition)
1. **Violation #1/#4** — `interface_entry/bootstrap/application_builder.py` (Interface Layer)
   - Action: 提炼 `logging_bootstrap`, `channel_bootstrap`, `runtime_supervision` 模块；入口仅调用 orchestrator。
2. **Violation #2/#3** — `business_logic/workflow/orchestrator.py` (Business Logic Layer)
   - Action: 新建 `business_logic/workflow/models.py` 存放 dataclass；新建 `foundational_service/persist/workflow_summary_repository.py` 由 orchestrator 调用。
3. **Violation #1/#3** — `business_service/conversation/service.py` (Business Service Layer)
   - Action: 拆为 `conversation_config.py`（dataclass）、`conversation_binding_runtime.py`（binding provider + health）与 `conversation_queue_bridge.py`（TaskRuntime & Submitter）；Service 仅 orchestrate。
4. **Violation #1/#3** — `Up/src/stores/workflowDraft.js` (Business Service Layer)
   - Action: 抽出 `createEmptyWorkflow` 至 `src/schemas/workflow.js`；CRUD/publish 调用转移到 `workflowDraftService`，Store 只调 service。
5. **Violation #1/#3** — `Up/src/stores/channelPolicy.js` (Business Service Layer)
   - Action: 新建 `src/schemas/channelPolicy.js` + `src/services/channelHealthScheduler.js`；Store 调用 scheduler 提供的 `start/stop/schedule` API，移除 inline timer。
6. **Potential Violation #4** — `Up/src/views/WorkflowBuilder.vue` (Interface Layer)
   - Action: 评估是否需要新增 `WorkflowBuilderController`（组合 store/service），避免视图直接 orchestrate 所有业务操作。

## Open Items
- 需确认用户希望的合规梳理颗粒度（是否覆盖更多模块/Store）。
- 讨论对后续需求文档的章节、优先级排序。
