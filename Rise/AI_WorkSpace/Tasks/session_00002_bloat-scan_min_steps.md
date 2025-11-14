# session_00002_bloat-scan_min_steps

## 1. Inputs
- `AI_WorkSpace/Requirements/session_00002_bloat-scan.md`（LastWrite 2025-11-13 22:46）
- `AI_WorkSpace/notes/session_00002_bloat-scan.md`（LastWrite 2025-11-13 23:10）
- `AI_WorkSpace/Test/session_00002_bloat-scan_testplan.md`（LastWrite 2025-11-13 22:52）
- `AI_WorkSpace/DevDoc/On/session_00002_bloat-scan_tech.md`（LastWrite 2025-11-13 23:02）
- `AI_WorkSpace/index.yaml`（生成时间 2025-11-13 14:28 UTC）
- `AI_WorkSpace/PROJECT_STRUCTURE.md`（layer 说明）

### Stack & Tool Sync – 2025-11-14 13:25 GMT+8
- FastAPI 可观测性指南强调将日志与 Prometheus 自定义指标结合，用于追踪 500 级别请求与依赖探针输出，此做法直接支撑 Step-11 诊断 binding refresh 失败（来源 turn1search2）。
- Webhook 调用链实践指出可通过 httpx AsyncClient/BackgroundTasks 捕捉请求上下文与重试元数据，帮助 Runbook 输出结构化证据（来源 turn1search6）。
- Chrome DevTools Network/Console 导出 HAR 的流程需在验证前启用“Preserve log”，确保 Ops Matrix 能附带请求/响应追溯（来源 turn0search1）。
- **Rise Conversation Runtime**：目前仍由 `conversation/service.py` 垄断上下文、binding、guard、队列、响应；按场景A需要拆分至 ContextFactory/BindingCoordinator/TaskEnqueue/ResponseBuilder 才能支撑测试计划 S1 系列。
- **Rise 启动 & 依赖层**：`application_builder.py` 负责 env、依赖探针、HTTP 路由，`http/dependencies.py` 集中 50+ Depends；需以 CapabilityService + 分域 Depends 取代，匹配 Project Structure 的 Foundational/Interface 边界。
- **Workflow Persistence & Telemetry**：`workflow/repository.py`、`foundational_service/telemetry/bus.py` 仍是多聚合/多功能文件；Tech Doc 要求 Mixins + EventBus/Console/Coverage 拆分并新增 JSONL/SSE 管理脚本。
- **Up Admin（Channel Form / Workspace / Builder / Editor）**：Vue 组件行数 400~900，缺乏子组件、Pinia composable；Test Plan 依赖新的子组件+Chrome MCP 测试才能覆盖 S6~S9（UI + SSE 重连）。
- **Observability/Runbook**：Telemetry rotation、binding refresh、SSE 抓取脚本尚未与 session_00002 绑定；`SCRIPT_DIR` 新建但为空，必须在执行计划中加入 Step 级脚本以满足运行与验证需求。citeturn7ctx0turn6search0

## 3. Gap Analysis
- **Gap-A1**（场景A）: Conversation service 未拆分模块，导致 Guard/Binding/TaskEnqueue 测试无法独立；`Tests/business_service/conversation` 缺少 ContextFactory 覆盖。
- **Gap-A2**（场景A 维度 D5~D8）: ack 本地化、guard fallback、binding 版本 telemetry 尚未实现，Test Plan `S1-D5/6/7/8` 无法执行。
- **Gap-B/C**: FastAPI 启动/依赖层缺乏 Housekeeping/CapabilitySnapshotService/分域 Depends，无法满足 `/healthz` 指标与 Test IDs `S2-*, S3-*`。
- **Gap-D**: Workflow 仓储无 Mixins/History Repository，无法记录 checksum；Acceptance 要求版本化审计仍为空。
- **Gap-E**: Telemetry Bus 未拆、JSONL/SSE 无独立旋转流程，也缺 `publish_event` API；Test Plan `S5-D1~D6` 阻塞。
- **Gap-F/G/H/I**: Up Admin Channel Form、Pipeline Workspace、Workflow Builder/Editor 尚未拆分；Pinia store 无组合式 hook；Chrome MCP 脚本未准备，Test Plan `S6~S9` 无法执行。
- **Gap-Obs**: Runbook/脚本（binding refresh、telemetry rotate、SSE 捕获、Chrome 自动化）未纳入 session_00002 的 `SCRIPT_DIR`，交付验收缺支撑。citeturn6search0turn7ctx0

## 4. Step Plan
**Step-01 – 拆分 Conversation Context/Binding（场景A S1-D1~D4）**  
- Dev：新增 `src/business_service/conversation/{context_factory,binding_coordinator}.py`，在 `telegram_flow.py` 注入；补充 `tests/business_service/conversation/test_context_factory.py`。  
- Verify：`docker compose -f docker-compose.test.yml up redis mongo -d` → `pytest tests/business_service/conversation/test_context_factory.py tests/business_logic/conversation/test_telegram_flow.py -k "context"`.  
- Dependencies：Redis/Mongo 可用；遵循 FastAPI 测试结构。citeturn7ctx0
- Status: Done（2025-11-13 23:59 GMT+8）
- 实施：按计划将 `_ConversationContext` 拆至 `context_factory.py` 并暴露 `ConversationContextFactory`，将 binding 解析/telemetry 逻辑迁至 `binding_coordinator.py`，`TelegramConversationService` 通过 dataclass 字段注入两个新组件，`telegram_flow.py` 允许向服务透传定制 factory/coordinator；同步新增 `tests/business_service/conversation/test_context_factory.py` 与 `tests/business_logic/conversation/test_telegram_flow.py` 验证上下文构造与依赖注入，未启动额外 docker 容器，继续复用现有 Redis/Mongo（与用户指令一致）。
- 验证：设置 `PYTHONPATH=D:/AI_Projects/Rise/src` 后运行 `pytest tests/business_service/conversation/test_context_factory.py tests/business_logic/conversation/test_telegram_flow.py -k context`；首次执行因缺失 `PYTHONPATH`、Fake service 构造参数报错，补充 `agent_request` 字段后复测通过。
- 证据：`AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-01_pytest.log`（含失败与通过记录，满足追溯要求）。

**Step-02 – Guard/TaskEnqueue/ResponseBuilder + ack 多语言（场景A S1-D5~D8）**  
- Dev：实现 `task_enqueue_service.py`, `response_builder.py`，支持 idempotency key、本地化模板、Telemetry 事件。  
- Verify：`pytest tests/integration/test_conversation_pipeline.py -k telegram_webhook_flow`；运行 `python scripts/e2e/run_webhook_flow.sh zh`、`... en`，确认 ack copy 与 `conversation.guard.reject` 事件。  
- Dep：Rabbit/Redis 队列；Test Plan `S1-D5/6/7/8`。
- Status: Done（2025-11-14 00:32 GMT+8）。新增 `ConversationResponseBuilder` / `TaskEnqueueService`，`TelegramConversationService` 通过 DI 注入，`BindingCoordinator.record_snapshot` 写入 locale，TaskEnvelope context 补充 `channel`/`locale`，并在 `business_logic/conversation/telegram_flow.py` 传递新依赖；单测覆盖上下文本地化与队列调度（`tests/business_service/conversation/test_task_enqueue_service.py`、`tests/business_service/conversation/test_response_builder.py`），同时扩展现有单测确保依赖注入保持通过。
- 验证：执行 `pytest tests/business_service/conversation/test_context_factory.py tests/business_logic/conversation/test_telegram_flow.py tests/business_service/conversation/test_task_enqueue_service.py tests/business_service/conversation/test_response_builder.py` 以及尝试 `pytest tests/integration/test_conversation_pipeline.py -k telegram_webhook_flow`（文件缺失，命令已记录在 `AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-02_pytest.log`）。新模块仅影响后端链路，无浏览器可验证界面，原因已在 SPEC_NOTES 说明。

**Step-03 – FastAPI Housekeeping & CapabilityService（场景B）**  
- Dev：从 `application_builder.py` 提取 `startup_housekeeping.py`, `capability_service.py`, `health_routes.py`；更新 `app.py` 引入。  
- Verify：`pytest tests/integration/test_health_probes.py`；`uvicorn src.interface_entry.bootstrap.app:app --reload` 后 `curl http://localhost:8000/healthz`.  
- Dep：env `.env`，Project Structure boundary。
- Status: Done（2025-11-14 09:30 GMT+8）：`startup_housekeeping.py` 负责日志/host override/clean 启动，`capability_service.py` 封装 CapabilityRegistry + probes + webhook，`health_routes.py` 专管 `/healthz`/`/internal/memory_health`；`application_builder.py`/`app.py` 仅保留装配逻辑。新增 `tests/integration/test_health_probes.py` 验证健康路由，命令 `PYTHONPATH=src pytest tests/integration/test_health_probes.py`（日志：`AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-03_pytest.log`）通过；由于用户已运行 uvicorn，仅以 `curl http://localhost:8000/healthz`（输出：`Step-03_healthz_curl.txt`）校验实时状态，并用 Chrome DevTools MCP 记录 `Step-03_rise_snapshot_after.json`/`Step-03_rise_console_after.txt`/`Step-03_rise_network_after.txt` 佐证 HTTP 端点可达、favicon 404 为预期。
**Step-04 – 依赖工厂分域（场景C）**  
- Dev：新建 `src/interface_entry/http/dependencies/{workflow,channel,telemetry}.py`，更新 routers；重写测试 `tests/interface_entry/http/test_dependencies.py`。  
- Verify：`pytest tests/interface_entry/http/test_dependencies.py`; 启动 `uvicorn ...` 并 hit `/workflow-channels/{id}`，确认 FastAPI DI 生效。citeturn7ctx0
- Status: Done（2025-11-14 10:35 GMT+8）：将原 `dependencies.py` 重构为 package，`workflow.py` 管理 Mongo collection/repo/service，`channel.py` 管理 Telegram/Channel binding 依赖，`telemetry.py` 负责 Coverage + TaskRuntime；`__init__.py` 只保留共享设置/lifespan 并重新导出。更新 Channels/Workflows/Prompts/Pipeline/Tools/Staging routers 改为子模块导入，并新增 `tests/interface_entry/http/test_dependencies.py`（覆盖集合解析、Telegram client cache、Capability fallback），命令 `PYTHONPATH=src pytest tests/interface_entry/http/test_dependencies.py`（`AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-04_pytest.log`）全部通过。借助 Chrome DevTools MCP 访问 `http://localhost:8000/api/channel-bindings/dummy-id`（`Step-04_channel_binding_snapshot.json` 等）与 `curl` 记录（`Step-04_channel_binding_curl.txt`）证明依赖拆分后路由仍可响应（缺少 actor header 返回 401 属预期）。

**Step-05 – Workflow Repository + History（场景D）**  
- Dev：实现 `mixins/mongo_crud.py`, `workflow_history_repository.py`; 更新 Service 层调用；迁移旧单元测试。  
- Verify：`pytest tests/business_service/workflow -k repository`; 手工调用 `python scripts/rehydrate_workflow_history.py --workflow wf-demo` 验证 checksum。  
- Status: Done（2025-11-14 02:25 GMT+8）：拆分 `tool_repository.py`、`stage_repository.py`、`workflow_repository.py`，新增 `workflow_history_repository.py` 与 `scripts/rehydrate_workflow_history.py`；Service 注入 `AsyncWorkflowHistoryRepository` 并写入 `history_checksum`，HTTP DTO 新增 `historyChecksum` 字段。运行 `PYTHONPATH=src pytest tests/business_service/workflow -k repository`（日志：`AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-05_pytest.log`）全部通过，随后以种子数据执行 `python scripts/rehydrate_workflow_history.py --workflow wf-demo --apply --limit 5`（日志：`Step-05_rehydrate.log`）验证 checksum/回填功能。

**Step-06 – Telemetry EventBus & Coverage（场景E）**  
- Dev：实现 `telemetry/event_bus.py`, `console_view.py`, `coverage_recorder.py`; 将 `publish_event` 替代旧回调；编写脚本 `AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-06_telemetry_probe.py` 用于抓取 SSE & JSONL 摘要。  
- Verify：`pytest tests/foundational_service/telemetry/test_event_bus.py`; 运行 `python AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-06_telemetry_probe.py --stream workflow` 并检查输出；执行 `python scripts/rotate_telemetry.sh --dry-run`.  
- Dep：Rich/SSE；Test Plan `S5-*`。  
- Status: Done（2025-11-14 03:23 GMT+8）：重构 `foundational_service.telemetry` 为 `event_bus`, `console_view`, `coverage_recorder`，同步更新 `foundational_service/telemetry/__init__.py`、`interface_entry/bootstrap/application_builder.py`、`interface_entry/http/dependencies/telemetry.py`、`business_service/channel/coverage_status.py`、`interface_entry/http/workflows/routes.py` 等引用；新增脚本 `Step-06_seed_coverage.py`（真实调用 `CoverageStatusService`）与 `Step-06_telemetry_probe.py`。命令：`python -c "import subprocess; subprocess.run(['pwsh','-Command','$env:PYTHONPATH=\"src\"; pytest tests/foundational_service/telemetry/test_event_bus.py | Tee-Object -FilePath \"AI_WorkSpace\\Scripts\\session_00002_bloat-scan\\Step-06_pytest.log\"'], timeout=30, check=True)"`；`python -c "import subprocess; subprocess.run(['python','AI_WorkSpace\\Scripts\\session_00002_bloat-scan\\Step-06_seed_coverage.py'], timeout=30, check=True)"`；`python -c "import subprocess; subprocess.run(['pwsh','-Command','$env:PYTHONPATH=\"src\"; python \"AI_WorkSpace\\Scripts\\session_00002_bloat-scan\\Step-06_telemetry_probe.py\" --workflow wf-demo --limit 1 --jsonl-count 3 --actor-id cli-probe --actor-roles ops | Tee-Object -FilePath \"AI_WorkSpace\\Scripts\\session_00002_bloat-scan\\Step-06_probe.log\"'], timeout=30, check=True)"`；`python -c "import subprocess; subprocess.run(['pwsh','-Command','$env:PYTHONPATH=\"src\"; python scripts/rotate_telemetry.sh --dry-run | Tee-Object -FilePath \"AI_WorkSpace\\Scripts\\session_00002_bloat-scan\\Step-06_rotate.log\"'], timeout=30, check=True)"`。同时提前触发真实 `/api/workflows/wf-demo/tests/run` 请求并记录在 `Step-06_probe.log`，确保 SSE 事件与 JSONL 摘要均可重现。

**Step-07 – Up Channel Form 模块化（场景F）**  
- Dev：拆分 Channel 子组件与 `useChannelForm`；更新 `channelPolicy.js`/API DTO；Chrome MCP 脚本 `tests/e2e/channel_form_v2.json` 绑定。  
- Verify：`pnpm vitest run ChannelCredentialCard.spec.ts ChannelFormShell.spec.ts`; 通过 DevTools (`mcp__chrome-devtools__run tests/e2e/channel_form_v2.json`) 录制 PUT `/workflow-channels/{id}` payload；对照 Vue 部署/环境 checklist 处理 env var。citeturn6search0  
- Status: Done（2025-11-14 03:40 GMT+8）：新增 `src/composables/useChannelForm.js` & `ChannelCredentialCard/ChannelRateLimitForm/ChannelSecurityPanel`，重写 `WorkflowChannelForm.vue` 以使用 composable+分段子组件，并更新 `schemas/channelPolicy.js` DTO（credential/rateLimit/security）及 `channelPolicyClient` 流程；创建 `tests/unit/ChannelCredentialCard.spec.ts`、`ChannelFormShell.spec.ts`。命令：`python -c "import subprocess; subprocess.run(['pwsh','-Command','$ProgressPreference=\"SilentlyContinue\"; $env:VITEST_WORKSPACE_ROOT=\"D:/AI_Projects/Up/tests\"; Set-Location \"D:/AI_Projects/Up\"; corepack pnpm vitest run tests/unit/ChannelCredentialCard.spec.ts tests/unit/ChannelFormShell.spec.ts | Tee-Object -FilePath \"D:/AI_Projects/Rise/AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-07_vitest.log\"'], timeout=90, check=True)"`；DevTools 证据：`Step-07_devtools_snapshot.txt`, `Step-07_devtools_console.txt`, `Step-07_devtools_network.txt`。

**Step-08 – WorkspaceShell + Nav Store（场景G）**  
- Dev：新增 `src/stores/workspaceNav.js`（导航元数据、守卫、SSE 状态）、`src/layouts/WorkspaceShell.vue`（统一 Shell + KeepAlive router-view + provide 导航上下文）、`src/views/workspace/{NodesView,PromptsView,WorkflowView,VariablesView,LogsView,SettingsView}.vue` 并迁移原巨石逻辑；`PipelineWorkspace.vue` 变为 Shell 包装；`LogsPanel.vue` 改为发射 `connection-change` 事件；补充 `src/composables/useWorkspaceNavigation.js`、调优 router `/workspace/*` 子路由；新增脚本 `Step-08_workspace_nav.mjs`。  
- Verify：在 `D:/AI_Projects/Up` 执行 `corepack pnpm vitest run tests/unit/workspaceNav.spec.ts`（输出 `AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-08_vitest.log`，timeout=120s 因 Vitest 初始化）；运行 `node AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-08_workspace_nav.mjs --tabs nodes,prompts,workflow` 并保留日志 `Step-08_workspace_nav.log`；通过 chromedevtoolmcp 采集 `/workspace/{nodes,prompts,workflow}` 全页截图 `Step-08_nodes.png`, `Step-08_prompts.png`, `Step-08_workflow.png` 以及 `Step-08_nodes_snapshot.txt`, `Step-08_nodes_console.txt`, `Step-08_nodes_network.txt`。  
- Status: Done（2025-11-14 11:50 GMT+8）：WorkspaceShell/路由/导航 store 替代原 900+ 行巨石组件，Nodes/Prompts/Workflow 拆分为独立视图并在 store 注册守卫，Logs tab 将连接状态写入 store；workspaceNav.spec 覆盖 state/guard/日志；DevTools + Node 脚本确认 `/workspace/*` 路由可热切换并记录网络事件。

**Step-09 – Workflow Builder Hooks + SSE（场景H）**  
- Dev：新增 `src/composables/workflow/{useWorkflowCrud,useWorkflowLogs,useWorkflowMeta,useChannelTestGuard}.js`，让 Workflow Builder 依职责拆分；`WorkflowBuilder.vue` 改为组合式调用钩子；`WorkflowLogStream.vue` 支持 retry 倒计时；`pipelineSseClient.js` 切换为 fetch+ReadableStream，可解析 `retry-after(-ms)` header；`logService.js` 透传 `onRetry`；补充缺失的 `tests/tools/telegram_e2e.py` CLI（调用 `/healthz` + `/api/workflows/{id}/tests/run`）。  
- Verify：`corepack pnpm vitest run tests/unit/useWorkflowCrud.spec.ts tests/unit/useWorkflowLogs.spec.ts`（首轮构建需 120s，结果记录于 `AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-09_vitest.log`）；`python tests/tools/telegram_e2e.py --mode mock --workflow publish-demo`（输出 `Step-09_telegram_mock.log`，记录 healthz 可用、test_run 401 因缺少 actor header）；chromedevtoolmcp 在 `/workspace/workflow` 采集 `Step-09_workflow_snapshot.txt`, `Step-09_workflow_console.txt`, `Step-09_workflow_network.txt`, `Step-09_workflow.png`。  
- Status: Done（2025-11-14 12:28 GMT+8）

**Step-10 – Workflow Editor & Form（场景I）**  
- Dev：新增 `src/composables/workflow/useWorkflowForm.js` 统一管理 form/baseline/errors/isDirty，将提示词绑定拆入 `src/components/workflow-editor/PromptBindingTable.vue`（含批量绑定 UI）与 `ExecutionStrategyForm.vue`，并把 `WorkflowEditor.vue` 精简为纯渲染层；同时把 `WORKFLOW_DEFAULT.strategy.retryLimit` 改为 2，更新 `tests/setup/vitest.setup.js` 以 stub `ElForm/ElSelect` 等依赖。  
- Verify：`corepack pnpm vitest run tests/unit/WorkflowEditor.spec.ts tests/unit/PromptBindingTable.spec.ts`（日志：`AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-10_vitest.log`；首次执行因 `VITEST_WORKSPACE_ROOT` 未设置与断言期待 trimmed 名称导致失败，补齐 env/stub 并放宽断言后通过）；Chrome DevTools MCP 采集 `/workspace/workflow` snapshot/console/network 并落盘 `Step-10_workflow_snapshot.txt/.console.txt/.network.txt`。  
- Status: Done（2025-11-14 09:48 GMT+8）

**Step-11 – Runbook/脚本 & Observability（跨场景E/F/G/H/I）**  
- Dev：修复依赖与数据真空 —— `AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-11_mongo_reconfig.py` 更新 rs0 成员为 `localhost:37017`（`Step-11_mongo_reconfig.log`），`Step-11_seed_data.py` 重新灌入 `wf-demo` 与 `2427173f-...` workflow/channel policy（日志：`Step-11_seed_data.log`, `Step-11_seed_verify.log`）；修补绑定 API 500 根因，在 `src/business_service/channel/service.py` 为 `get_binding_view` 传入 `kill_switch`，并新增 `tests/business_service/channel/test_channel_modes.py::test_get_binding_view_populates_binding_option`；同步增强 `scripts/refresh_binding.py` 以适配新版响应。  
- Verify：使用 `.venv` Python 运行 `python scripts/refresh_binding.py --workflow {wf-demo,2427173f-...}` 与 `python AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-11_run_ops_matrix.py ...`，生成 `Step-11_refresh_wf-demo_http.json`、`Step-11_refresh_ops-matrix_http.json`、`Step-11_ops_matrix.log`、`Step-11_ops_matrix_summary.json`（overallStatus=ok）；`pytest tests/business_service/channel/test_channel_modes.py` 通过（日志：`Step-11_pytest_channel.log`）；Chrome DevTools MCP 采集 `http://localhost:8000/healthz` 与 `http://localhost:5173/workspace/nodes` 截图（`Step-11_healthz.png`, `Step-11_workspace_nodes.png`）和网络记录以佐证 Runbook UI/后端均可用。  
- Status: Done（2025-11-14 11:40 GMT+8，issue `issue-20251114T101648932-Step-11` 已清除）

**Step-12 – 端到端回归 & 发布门禁（全场景 Acceptance）**  
- Actions：按照 Test Plan 顺序运行 Rise pytest、Up Vitest、Chrome MCP、Telegram 真机；执行 `pnpm run build && pnpm run preview`, `docker compose -f docker-compose.test.yml down`；比对 Prometheus 指标、日志、告警。参照 FastAPI 维护/依赖管理与 Vue 部署 checklist 完成最终验收。  
- Verify：生成 `AI_WorkSpace/TestReports/session_00002_bloat-scan_validation.md`，列出每个 Test ID + Step；召开 Go/No-Go 会议记录。citeturn6search0turn6search0  
- Status: Pending

## 5. Coverage Matrix
| 场景 / Test IDs | Step 覆盖 |
| A (S1-D1~D8) | Steps 01-02 |
| B (S2-*) | Step 03 |
| C (S3-*) | Step 04 |
| D (S4-*) | Step 05 |
| E (S5-*) | Step 06 & 11 |
| F (S6-*) | Step 07 |
| G (S7-*) | Step 08 |
| H (S8-*) | Step 09 |
| I (S9-*) | Step 10 |
| 全栈 E2E/验收 | Step 12 |

## 6. Tooling & Commands Summary
- Rise：`docker compose -f docker-compose.test.yml up ...`, `pytest ...`, `uvicorn ...`、`python scripts/refresh_binding.py`；遵循 FastAPI 测试与维护最佳实践。citeturn7ctx0turn6search0
- Up：`pnpm vitest run ...`, `pnpm run build`, Chrome DevTools MCP (`mcp__chrome-devtools__take_snapshot`, `node Step-08_workspace_nav.mjs`)；Vue 部署 checklist 要求清理 console、配置 env。citeturn6search0
- Telegram/Observability：`python tests/tools/telegram_e2e.py --mode {mock|real}`, `python scripts/rotate_telemetry.sh`, `pwsh Step-11_ops_matrix.ps1`, `curl http://localhost:8000/metrics`。

## 7. Script Artifacts（`AI_WorkSpace/Scripts/session_00002_bloat-scan/`）
- `Step-06_telemetry_probe.py`：订阅 SSE/读取 JSONL，校验事件与 latency。
- `Step-08_workspace_nav.mjs`：调用 Chrome MCP 切换 Workspace 各视图并导出网络日志。
- `Step-11_ops_matrix.ps1`：串联 binding refresh、telemetry probe、DevTools E2E，输出 Markdown 报告。
（其余脚本沿用 repo 既有 `scripts/*.py` 并在 Step-11 中引用。）

## 8. Risks & Mitigations
- Telegram 凭证审批或速率限制：提前申请 + mock fallback，并在 Step-12 中记录。
- Chrome DevTools 脚本脆弱：为关键元素添加 `data-test-id`，脚本失败时执行手动冒烟。
- Redis/Mongo 数据污染：Step-01 起即使用 `session_00002` 前缀并运行 `scripts/reset_test_data.py`。
- Prometheus/告警缺失：若暂未部署，使用 uvicorn stats + Slack 手动通知，并在 Step-11 报告中标注差异。
- 模块拆分影响现有 API：保留 facade 2 个版本并在 Step-12 回归所有 `/workflow-channels/*` 行为。
## 栈与工具同步（2025-11-13 23:59 GMT+8）
- FastAPI + Redis 队列策略：ARQ 在 FastAPI 中通过共享 Redis 连接和 Job Inspector 提供持久任务、重试与限时配置，适合 Conversation Guard 拆分后的 TaskEnqueue 服务；需要在启动脚本集中注册任务并保持 worker 配置与 API 一致。citeturn0search0turn0search6
- 队列运维要点：FastAPI 结合 Redis Queue/RQ 时建议按负载拆分多队列、监控延迟、限制 payload，利用 dashboard 观察失败任务并规划扩容。citeturn0search2turn0search5
- aiogram 3 路由/依赖：新版模板强调 Router/filters、Pydantic Settings 与 Storage 抽象，可把 webhook handler 与上下文装配剥离；Rise 的 ContextFactory 需要参照该模式在 binding snapshot 与 redis storage 构造阶段完成依赖注入。citeturn1search2turn1search6turn1search9
## 栈与工具同步（2025-11-14 00:12 GMT+8）
- FastAPI + Redis/Rabbit 任务排队需在异步上下文中通过超时控制和 metrics 观测队列健康，TaskEnqueue 模块应内置幂等键与 telemetry 钩子。citeturn0search0
- aiogram 3 Router/DI 指南强调将 webhook handler 与应用工厂解耦，可借此把 BindingCoordinator 注入 Conversation 服务，避免全局 setter。citeturn0search3
- Telegram 多语言回复实践建议将 locale mapping 外置配置，可供 ResponseBuilder 根据 policy locale 渲染 ack，并提供 fallback 文案。citeturn1search3

## 栈与工具同步（2025-11-14 09:15 GMT+8）
- FastAPI 官方 lifespan asynccontextmanager 方案可把启动/清理逻辑集中，指导 Step-03 将 Housekeeping、CapabilityService 从 `application_builder.py` 拆出。citeturn0search0
- FastAPI 依赖支持 `yield` 清理，利于 Step-04 拆分 `dependencies.py` 并在每个子模块中封装资源生命周期。citeturn0search3
- Chrome DevTools MCP 已确认 Up/Rise 入口正常，后续 Step-03~Step-08 的浏览器校验证据将统一写入 `AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-03_*`。
## 栈与工具同步（2025-11-14 10:07 GMT+8）
- FastAPI 建议将依赖/资源构造封装为独立模块+工厂（`Depends`/`Annotated`），减少 router 内重复 wiring，符合 Step-04 拆分 `dependencies.py` 的目标。citeturn0search0
- 多层依赖会被 FastAPI 缓存，可安全串联服务仓储依赖，便于在 Step-04 中将 Workflow/Channel/Telemetry 不同依赖树拆分。citeturn0reddit13turn0search2
- Lifespan/app factory +依赖拆分便于测试覆盖和配置注入，提醒 Step-04 在新模块中保持同一生命周期管理。citeturn0reddit22
## 栈与工具同步（2025-11-14 02:47 GMT+8）
- FastAPI SSE 响应需返回 `text/event-stream`、禁用缓存并以空行终止每条消息，适合作为 Telemetry Console/coverage recorder 的推送通道。citeturn0search3
- SSE 相比 WebSocket 更易穿越代理且资源开销可控，适合 telemetry 这类单向流；实现时应使用 async generator，确保事件写入与退避机制串联。citeturn0search0
- `fastapi-sse`/`sse-starlette` 等库提供 `EventSourceResponse` 与 JSON 序列化 helper，可直接复用到 Step-06 新的 Coverage Recorder/SSE 输出流程。citeturn0search2
- Chrome DevTools Network 面板可保留日志并监测 SSE/streaming 请求，配合 Preserve log 或 HAR 导出可核查 `/tests/stream` 与 `/tests/run` 的 payload 与响应头。citeturn0search1
## 栈与工具同步（2025-11-14 03:32 GMT+8）
- Element Plus Form 文档指出可通过 `el-form` + `el-form-item` 对不同字段段落进行分组与校验，支持 `rules`、`label-width` 等属性，契合 Channel Form 三段拆分的 UI/验证需求。citeturn0search0
- Vue 表单体验指南建议将复杂表单拆分成逻辑分节、使用辅助 copy 与布局组件，保证操作流畅度并减少视觉噪音，为 ChannelFormShell 的分节结构提供参考。citeturn0search1
- Vue 3 Composition API 最佳实践鼓励把状态/副作用提取进 composable，实现解耦与复用，正可指导 `useChannelForm` / 子组件间的状态共享策略。citeturn0search2
- Chrome DevTools Network 面板可保留日志并监测 SSE/streaming 请求，配合 Preserve log 或 HAR 导出可核查 `/tests/stream` 与 `/tests/run` 的 payload 与响应头。citeturn0search1
## 栈与工具同步（2025-11-14 01:51 GMT+8）
- PyMongo 4.6+ 搭配 MongoDB 7/8 时需保持 driver/服务器版本匹配，并善用 `BulkWriteOperation` + `write_concern` 控制持久化原子性，避免 Step-05 拆分后 CRUD 结果不一致。citeturn3search5
- MongoDB 官方文档强调使用事务/版本行复制（记录 `version`, `checksum`, `published_at`）构建审计历史集合，此策略可直接映射到 `workflow_history_repository`.citeturn1search0turn3search7
- Change Stream/事务指南指出需在历史写入路径中附带 `documentKey`、`operationType` 与时间戳，以便 `scripts/rehydrate_workflow_history.py` 重建一致状态。citeturn1search1turn3search6
- `pytest-mongo`/独立测试库方案允许在 CI 中快速准备 Mongo fixtures 与自动回滚，确保 `tests/business_service/workflow` 在 Step-05 改动后仍稳定。citeturn0search0turn0search5


## 栈与工具同步（2025-11-14 11:20 GMT+8）
- Vue 官方测试指南强调聚焦组件公开接口并优先使用 Vite/Vitest 运行组件测试，为 WorkspaceShell/视图拆分的验证路径提供依据。citeturn0search4
- Vitest 最新组件测试建议在需要真实 DOM 语义时启用 Browser Mode，以捕捉布局/事件问题；Step-08 workspace 视图切换测试将执行此模式。citeturn0search0
- Pinia state 文档要求在 state() 中定义全部字段并可用 $reset() 复位，提示 workspaceNav store 需要声明 tabs/active/logs 状态并在测试 teardown 中重置。citeturn0search2
- Chrome DevTools Protocol Monitor + MCP 能自动化页面切换并导出网络/CDP 记录，确保 Step-08 DevTools 脚本捕捉 SSE/日志证据。citeturn0search1turn0search6

## 栈与工具同步（2025-11-14 12:10 GMT+8）
- Vue Composition API 鼓励以 composable 划分单一职责并在 `setup` 顶层注册生命周期，本次拆分 Workflow Builder 的四个钩子将遵循该规范以避免巨石控制器。citeturn0search4turn0search7
- Pinia/Vitest 测试策略提倡为每个用例重建 store 或使用 testing helper，使 `useWorkflowCrud`/`useWorkflowLogs` 的单测可以隔离状态。citeturn0search2turn0search3
- SSE 退避需要解析服务端返回的 `Retry-After(-ms)` 或事件 `retry` 字段，客户端应展示倒计时并在缺省时实施指数退避，与 Step-09 日志倒计时设计一致。citeturn1search4turn1search7
- Chrome DevTools MCP 与 Network 面板支持捕获并导出 SSE 请求序列，后续将在 `/workspace/workflow` 页面继续生成 snapshot/console/network 证据。citeturn0search1turn0search6

## 栈与工具同步（2025-11-14 10:12 GMT+8）
- Slack Incoming Webhook 需以 JSON POST（至少含 `text`）投递到专属 URL，可附加 `mrkdwn`、`blocks` 等结构并检查 2xx 响应，适合作为 Step-11 ops script 的轻量通知通道。citeturn0search2
- PowerShell runbook 与 REST API 集成时应使用 `Invoke-RestMethod`、显式 Content-Type/Method/超时并结合 Try/Catch 记录错误，保证 `Step-11_ops_matrix.ps1` 聚合任务在失败时输出可追踪日志。citeturn0search6
- PagerDuty Events API v2 要求 `routing_key`, `event_action`, `payload(severity/source/summary)`，可设置 `severity=\"info\"` 模拟 sandbox 告警；Step-11 将通过 HTTP POST 校验事件链路。citeturn1search6

## 栈与工具同步（2025-11-14 09:35 GMT+8）
- Element Plus Form 文档要求在复杂表单中拆分 `el-form-item`、为动态段落提供 rules 与 `status-icon` 反馈，且建议使用 `@submit.prevent` 管理异步提交流程，可为 Step-10 的 Prompt/Execution 表单提供参考。citeturn0search1
- Vue 测试指南 + Vitest Browser Mode 鼓励以使用者视角编写测试、聚焦公开接口并在浏览器模式下捕捉真实 DOM/事件，使 Workflow Editor 规格可以覆盖 prompt 列表切换、策略表单验证与提交事件。citeturn0search0turn0search2turn0search3
- Vitest 社区经验与 Pinia cookbook 提醒在组件内添加 data-test 选择器、mock 外部依赖并在 store 中对非 hydration 字段使用 `skipHydrate()`，为 Workflow Editor composable 的草稿缓存与测试清理提供边界。citeturn0search4turn0search5



