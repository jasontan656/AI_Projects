# session_00002_bloat-scan 技术规划

## 1. Background & Scope
- 需求范围：Rise / Up 臃肿治理 9 大场景（A Conversation Runtime、B FastAPI 启动/探针、C 依赖工厂、D Workflow 仓储、E Telemetry Bus、F Channel Form、G Pipeline Workspace、H Workflow Builder、I Workflow Editor），每个场景需覆盖核心、性能、安全、一致性、防御、观测、运维、业务八大维度。
- 本文目标：将 Requirements + Test Plan 映射到具体模块/文件/函数/接口、外部依赖与实施决策，指导小型团队按层实现；同时遵循 `PROJECT_STRUCTURE.md` 的分层约束。
- 参考：FastAPI 测试结构与 CI（Context7#2 `/websites/benavlabs_github_io_fastapi-boilerplate`）、Pinia store/组合实践（Context7#3 `/vuejs/pinia`）、微服务臭味/事件日志拆分（Exa#3/Exa#4）、FastAPI 集成测试与 Docker TDD（Exa#5/Exa#6）、Pinia Colada 数据获取（Exa#7）。

## 2. Tech Stack Overview
- **Rise Backend**：Python 3.11、FastAPI 0.118.x、Starlette、Pydantic v2、aiogram 3.22、aio-pika 9.4、Redis 7、MongoDB 7、RabbitMQ、OpenAI SDK 1.105、Rich 13、uvicorn；pytest + httpx AsyncClient + docker-compose（Redis/Mongo/RabbitMQ）用于集成测试。citeturn1search2
- **Up Admin**：Vue 3、Vite 5、Pinia + Composition API、Element Plus、Vue Router、Vue Flow、CodeMirror 6、Vitest；Chrome DevTools MCP/Playwright 作为 UI 自动化；可按需引入 `@pinia/colada` 提供缓存/乐观更新。citeturn3search7turn3search8
- **Infra/工具**：Redis/Mongo/RabbitMQ 容器；Prometheus `/metrics`；PagerDuty/Slack；Telegram Bot API（真实 + aiogram mock）；ngrok/Cloudflare tunnel；Chrome DevTools MCP；`scripts/reset_test_data.py`、`scripts/refresh_binding.py`、`scripts/rotate_telemetry.sh`、`scripts/fetch_sse.py`；faker 数据。
- **配置/Flag**：`TELEGRAM_BOT_TOKEN`、`WEB_HOOK`、`REDIS_URL`、`MONGODB_URI`、`RABBITMQ_URL`、`OPENAI_API_KEY`、`VITE_API_BASE_URL`、`VITE_ENABLE_OBSERVABILITY`、`ENABLE_CHANNEL_FORM_V2` 等；测试环境集中在 `.env.test`。

## 3. Module/File Change Matrix
| 场景 | 模块/文件 | Change Type | 内容摘要 |
| --- | --- | --- | --- |
| A Conversation Runtime | `src/business_service/conversation/service.py` → `conversation/context_factory.py`, `binding_coordinator.py`, `task_enqueue_service.py`, `response_builder.py`；`business_logic/conversation/telegram_flow.py` | Split/Modify | ContextFactory 聚合 redis/mongo 状态；BindingCoordinator 刷新 snapshot + telemetry；TaskEnqueue 将 `TaskEnvelope` 写入 redis/rabbit；ResponseBuilder 输出 ack；telegram_flow 依赖注入新服务。 |
| B FastAPI 启动/探针 | `src/interface_entry/bootstrap/application_builder.py` → `startup_housekeeping.py`, `capability_service.py`, `health_routes.py` | Split | Housekeeping 负责 env/log 初始化；CapabilityService 管理 probe 状态；health routes 专注 API。 |
| C 依赖工厂 | `src/interface_entry/http/dependencies.py` → `dependencies/workflow.py`, `dependencies/channel.py`, `dependencies/telemetry.py` | Split/Move | FastAPI Depends 按领域划分，避免巨石文件及循环导入。 |
| D Workflow 仓储 | `src/business_service/workflow/repository.py` → `repository/tool_repository.py`, `stage_repository.py`, `workflow_repository.py`, `workflow_history_repository.py`, `mixins/mongo_crud.py` | Split | CRUD mixin 封装，history 独立 append-only；支持同步/异步双实现。 |
| E Telemetry Bus | `src/foundational_service/telemetry/bus.py` → `telemetry/event_bus.py`, `telemetry/console_view.py`, `telemetry/coverage_recorder.py` | Split | `publish_event` 成唯一入口；Console 渲染与 Coverage JSONL/SSE 分离；匹配 Log2MS 事件驱动实践。 |
| F Channel Form | `src/components/WorkflowChannelForm.vue` → `channel-form/ChannelCredentialCard.vue`, `ChannelRateLimitForm.vue`, `ChannelSecurityPanel.vue`, `ChannelFormShell.vue`; `src/composables/useChannelForm.js`；`src/stores/channelPolicy.js` | Split/Modify | 子组件负责 Credential/RateLimit/Security；`useChannelForm` 统一 baseline/dirty/payload；store 三段 DTO + telemetry。 |
| G Pipeline Workspace | 新建 `src/layouts/WorkspaceShell.vue`; `src/views/workspace/{NodesView.vue,...}`；`src/stores/workspaceNav.js` | Add/Refactor | Shell + 子视图懒加载 + 导航 store，替代 930 行巨石。 |
| H Workflow Builder | `src/composables/useWorkflowBuilderController.js` → `useWorkflowCrud.js`, `useWorkflowLogs.js`, `useWorkflowMeta.js`, `useChannelTestGuard.js`; `WorkflowBuilder.vue` 更新 | Split | Hooks 专责 CRUD/日志/元数据/渠道守卫；WorkflowBuilder 按需组合；支持 SSE retry。 |
| I Workflow Editor | `src/components/WorkflowEditor.vue` → `PromptBindingTable.vue`, `ExecutionStrategyForm.vue`; `src/composables/useWorkflowForm.js` | Split | 表单状态与 UI 解耦；易于单测与复用。 |
| 观测/运维 | `scripts/refresh_binding.py`, `scripts/rotate_telemetry.sh`, `scripts/fetch_sse.py`, `AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-11_ops_matrix.ps1`, `AI_WorkSpace/Test/...` | Modify/Add | Runbook & Test plan 依赖的脚本/文档，以及 Ops Matrix 自动化（串联 binding refresh、telemetry probe、workspace nav 与 Slack/PagerDuty 通知）。 |

## 4. Function & Interface Summary
- **ConversationContextFactory**：`build(update)` → `ConversationContext`（chatId/channel/workflowId/bindingVersion/policySnapshot/entryConfig/agentHints）；依赖 Redis `binding_snapshot:*` 与 Mongo workflow 元数据；记录 TraceSpan。
- **BindingCoordinator**：`get_runtime(context)` / `refresh_if_stale(context)`；当 snapshot 缺失或版本落后时刷新 redis/mongo 并发布 `channel.binding.refresh_*`。
- **PipelineGuardService (Protocol)**：`evaluate(context, workflow_id)` 返回 `PipelineGuardDecision`（ALLOW/FALLBACK/BLOCK）；使用 rate limiter、allowedChatIds、workflow 状态；拒绝时发出 `conversation.guard.reject`。
- **TaskEnqueueService**：`enqueue(context, workflow)` 构建 `TaskEnvelope`（task_id、idempotencyKey、nodeSequence、payload、timeout、strategy）写入 redis 队列或 RabbitMQ；生成 telemetry `task.enqueue`；通过 Redis `SETNX` 或 Rabbit dedupe header 保证幂等。
- **ResponseBuilder**：`build_ack(decision, task_id, locale)`；返回 Telegram 文案（中文/英文），覆盖 fallback copy。
- **CapabilitySnapshotService**：`refresh_all()`、`snapshot()`；管理 probe state `state/detail/updatedAt/probeVersion`；供 `/healthz`、`/healthz/readiness`、`/internal/memory_health` 使用。
- **Dependencies 模块**：`get_workflow_repository()`, `get_channel_binding_service()`, `get_telemetry_bus()` 等 FastAPI Depends；利用 Pydantic Settings + lazy 单例；遵守官方“分模块注入 + AsyncClient 测试”范式。citeturn1search2
- **MongoCrudMixin**：`create`, `update`, `delete`, `get`, `list`, `_ensure_indexes`; `WorkflowHistoryRepository` 提供 `append_history`, `get_history`, `compare_checksum`。
- **Telemetry Event Bus**：`publish_event(event_type, payload)`（async）；`TelemetryConsoleView` 订阅渲染 Rich；`CoverageEventRecorder` 写 JSONL + SSE；rotate 脚本控制文件大小。
- **Channel Form 组件**：CredentialCard/RateLimitForm/SecurityPanel 分别处理各自字段与验证；`useChannelForm` 负责 baseline、dirty、payload、validate；`ChannelFormShell` 合并结果并发射 `save`。
- **WorkspaceShell + workspaceNav Store**：Shell 提供统一导航/布局；store 管理 active tab、keep-alive、Feature Flag；支持 telemetry 记录导航事件。
- **Workflow Hooks**：`useWorkflowCrud`（create/select/save/publish/rollback + confirmLeave）、`useWorkflowLogs`（SSE 订阅、重连、retry-after 倒计时）、`useWorkflowMeta`（变量/工具拉取 + 错误处理）、`useChannelTestGuard`（secret/coverage/冷却决策）。所有 hook 在 async action 顶部调用 `useStore()`，避免 SSR 实例错乱。citeturn3search7
- **refresh_binding.py**：CLI 调用 `/api/channel-bindings/{workflow}/refresh` 并回读 binding detail，用于 runbook/自动化校验 redis/mongo snapshot。
- **Step-11_ops_matrix.ps1**：PowerShell 聚合脚本，依次执行 binding refresh、`Step-06_telemetry_probe.py`、`Step-08_workspace_nav.mjs`，并通过 Slack Incoming Webhook 与 PagerDuty Events API 汇报结果，生成 `Step-11_ops_matrix_summary.json`。
- **Workflow Editor Components**：`useWorkflowForm` 提供状态管理；`PromptBindingTable` 管理节点-提示词；`ExecutionStrategyForm` 管理重试/超时；事件 `dirty-change`/`save` 与旧接口兼容。

## 5. Best Practices & Guidelines
1. **FastAPI**：模块化依赖注入、pytest + AsyncClient、docker-compose 驱动服务、CI 运行 `pytest --cov` 并上传报告。citeturn1search2
2. **Pinia**：store id 唯一、`useStore()` 顶部调用、store 组合/依赖通过 provide/inject；对复杂操作拆分多个 store/composable；可结合 Pinia Colada 处理数据获取/缓存/乐观更新。citeturn3search7turn3search8
3. **微服务臭味治理**：对 God Object 立即拆分；记录 telemetry 事件（Log2MS 思路）方便后续自动化分析；保持模块职责单一。citeturn0search0turn0search5
4. **测试/运维**：遵循 Test Plan：Rise 用 pytest + docker，Up 用 Vitest + Chrome DevTools MCP，Telegram 同时 mock/real；Prometheus/告警演练纳入回归。citeturn2search0turn2search1

## 6. File & Repo Actions
- Rise：创建/移动上述模块文件；更新 `__init__.py` 暴露新服务；扩展 `tests/`；维护脚本 (`refresh_binding.py`, `rotate_telemetry.sh`, `fetch_sse.py`)；如需引入新的依赖（如 `dataclasses-json`），更新 `pyproject.toml`。
- Up：新增 channel-form 子组件、layout、workspace 子视图、workspaceNav store、workflow hooks、workflow editor 子组件；更新 `WorkflowBuilder.vue`、`WorkflowEditor.vue`、`PipelineWorkspace.vue`、`WorkflowChannelForm.vue`、`channelPolicy.js`；必要时在 `package.json` 增加 `@pinia/colada`。
- 文档/工具：维持 Requirements/Test plan/DevDoc 同步；在 DevDoc/notes 中记录 Feature Flag/兼容层退场时间。

## 7. Risks & Constraints
- **Telegram token**：审批延迟→E2E 需 mock；上线前必须跑真实 Telegram 测试。Mitigation：Ops 提前 3 天申请，保留 mock fallback。
- **Chrome DevTools 脚本敏感**：UI class 变动导致自动化失败；Mitigation：定义统一 data-test attr + 保留手动作业。
- **共享 Redis/Mongo 污染**：其他团队测试可能写入；Mitigation：使用 `session_00002` 前缀 + `reset_test_data.py`；必要时独立实例。
- **Prometheus 缺失**：若暂未部署，临时用 uvicorn stats；文档中注明差异并计划补齐。
- **兼容层**：Conversation old facade 在 2 个版本内移除；上线前需回归旧 API 行为。

## 8. Implementation Decisions
1. Conversation Runtime 正式拆为 ContextFactory/BindingCoordinator/PipelineGuard/TaskEnqueue/ResponseBuilder 五段并通过 DI 注册，彻底移除全局 setter。
2. FastAPI 依赖工厂按领域划分并通过 router include 注入，杜绝巨石 `dependencies.py`。
3. Workflow 仓储采用 MongoCrudMixin + 独立 history 集合，保存时写 checksum，便于 diff 与回滚。
4. Telemetry Bus 仅暴露 `publish_event`；Console/SSE 模块订阅事件队列；镜像文件通过轮转脚本管理。
5. Up Channel Form 按 credential/rateLimit/security 三段 DTO 一次性保存；Feature Flag `ENABLE_CHANNEL_FORM_V2` 控制 rollout（默认 30 天内回收）。
6. Pipeline Workspace 引入 `WorkspaceShell + 子视图 + workspaceNav store`；Workflow Builder hooks 拆分；Workflow Editor 利用 `useWorkflowForm + 子组件`。
7. Pinia store 在 async action 顶部调用 `useStore()`，遵循官方 SSR/组合式建议；必要时引入 Pinia Colada 优化数据获取。citeturn3search7turn3search8
8. 测试与运维执行严格遵循 Test Plan：pytest/Vitest、Chrome DevTools MCP、Telegram mock/real、Prometheus/告警演练，所有命令与证据需记录在 Test Reports。
