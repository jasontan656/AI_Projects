# Session Notes 2025-11-11 23:55 CST

## User Intent
- 用户要求：依照 `D:/AI_Projects/.codex/prompts/WriteRise.md` 中 violation 定义（52-55 行）与处理要求（143-154 行），对 Rise（后端）与 Up（前端）做一次全面 violation 梳理，并讨论合规化落地细节。
- 目标：输出中文讨论稿，覆盖当前违规点、所需拆分的模块/Schema、处理步骤与留存风险，后续将形成正式业务需求文档。

## Repo Context
- `Rise/src/interface_entry/bootstrap/application_builder.py:1` 起超过 400 行，集成日志、环境覆写、FastAPI 路由、Telegram runtime、任务队列、健康探针，入口层直接处理 Runtime 细节，触发 Violation #1/#4。
- `Rise/src/business_logic/workflow/orchestrator.py:1` 同时定义 `WorkflowExecutionContext/WorkflowStageResult/WorkflowRunResult` dataclass，并直接调用 `project_utility.db.append_chat_summary` 与 Mongo 集合更新，违反 “逻辑层不得直接操作基础设施” (#2/#3)。
- `Rise/src/business_service/conversation/service.py`（>800 行）集成 config、上下文 dataclass、队列适配、健康检查、重试控制，业务服务层与 schemas/基础设施混杂，命中 #1/#3。
- `Up/src/stores/workflowDraft.js:1` 定义空白 workflow schema、Pinia state、全部 CRUD/发布 API 调用；`Up/src/stores/channelPolicy.js:1` 同时构建策略 schema、健康 polling、频控逻辑，均为 Store 过度承担业务流 (#1/#3)。
- `D:/AI_Projects/.codex/prompts/WriteRise.md` 明确 violation 定义（52-55 行）及处理步骤（143-154 行）：必须拆出辅助模块/Schema，保留原功能，描述迁移路径与验证策略，未处理的 violation 需登记风险。

## Technology Stack
- 后端：FastAPI、aiogram、Redis、Mongo、RabbitMQ（来自 `AI_WorkSpace/index.yaml` 与 `PROJECT_STRUCTURE.md`）。
- 前端：Vue 3 + Vite 5 + Pinia + Element Plus。Store 负责 API 协同，需与服务/Schema 分离（参阅 `AGENTS.md`）。

## Search Results / External Guidance
- [CTX1] `/ardalis/cleanarchitecture` 指南：入口层仅作路由/协议转换，业务逻辑集中在 Use Case 层，Schema（Entities）独立存放，促使职责单一。
- [EXA1] StudyRaid《Architecture principles of Pinia stores》（2025-01-16）：强调 Store 模块化、状态/动作分离，复杂逻辑抽离到服务层，保持 Pinia 以状态为主。
- [EXA2] CodeSignal《Designing a Maintainable Backend Architecture with FastAPI》（2025-01-01）：建议分离 routing/controller/service 层，入口层只桥接请求，业务逻辑独立可测。
- [WEB1] Reddit 讨论《How should I decouple my app logic from my stores?》（2024-01-01）指出应将业务逻辑抽成服务层，Pinia 仅管理状态和轻量动作，组件可替换实现。
- [WEB2] Shopware ADR《Replace Vuex with Pinia》（2024-06-17）要求 Store 输出类型定义、保持单一职责，为迁移提供最佳实践。

## Architecture Findings
1. **入口层过载**：`application_builder.py` 集成 runtime/bootstrap 与 HTTP 路由。需拆分 `bootstrap/runtime_supervisor.py`, `bootstrap/telegram_entry.py`, `bootstrap/logging.py` 等模块，并由入口调用。（Violation #1/#4）
2. **业务逻辑直接触底层**：`workflow/orchestrator.py` 操作 Redis/Mongo 并内联 dataclass。需新建 `business_logic/workflow/models.py` 与 `foundational_service/persist/workflow_summary_repository.py`，执行链通过接口注入。（Violation #2/#3）
3. **业务服务臃肿**：`conversation/service.py` 既定义数据结构又驱动任务/健康、回放。建议拆分 config/schema、runtime 适配、健康服务三个模块，Service 聚焦 orchestrate。（Violation #1/#3）
4. **前端 Store 违反分层**：`workflowDraft.js`、`channelPolicy.js` 同时作为 schema + service + state 容器。需引入 `src/schemas`、`src/services/*`、调度器/频控 helper，让 Store 仅维护状态和调用结果。（Violation #1/#3）
5. **视图层耦合**：`WorkflowBuilder.vue` 直接掌控 Store 动作、轮询、测试按钮与 SSE。应评估建立 `WorkflowBuilderController`（setup composable）承载业务编排，视图只消费状态（潜在 Violation #4）。

## File References
- `Rise/src/interface_entry/bootstrap/application_builder.py:1-200, 200+` – 入口层与 helper 混在同文件。
- `Rise/src/business_logic/workflow/orchestrator.py:1-200` – dataclass 与持久化逻辑共存。
- `Rise/src/business_service/conversation/service.py` – 大型 Service 混杂 config/runtime。
- `Up/src/stores/workflowDraft.js:1-200` – schema + API + state。
- `Up/src/stores/channelPolicy.js:1-200` – schema +健康轮询+限流。

## Violations & Remediation
1. **Interface Layer overload (Rise)** – 拆分 logging/runtime/channel bootstrap，入口仅负责 FastAPI app 创建与依赖注入。
2. **Business Logic touching persistence (Rise)** – 抽出 workflow models + summary repository，让 orchestrator 仅 orchestrate。
3. **Business Service mixing schemas/helpers (Rise)** – 将 dataclass 移到 `business_service/conversation/models.py`，runtime/helpers移到专属模块。
4. **Store overreach (Up)** – 建立 `src/schemas/workflow.js`, `src/services/workflowDraftService.js`, `src/services/channelHealthScheduler.js`；Store 仅引用它们。
5. **View-controller gap (Up)** – 设计 `useWorkflowBuilderController` composable，将轮询/测试/发布逻辑下沉，视图保持展示与事件绑定。
