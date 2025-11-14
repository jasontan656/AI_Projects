# 技术策划（Tech Doc）· Session 00001 · compliance-audit

## 1. Background & Scope
- 目标：把 Requirements（S1–S5）与 Test Plan（RG-DEP-001 等）约束落为 Rise/Up 两仓的模块级设计，建立 Telegram 渠道表征测试、覆盖门禁、Secret/TLS 守护与模式冲突检测的统一规范。
- 场景范围：  
  - **S1 Webhook 表征测试（离线）**：在 `tests/business_service/conversation` 子树打造 Golden Telegram 对话、TestClient 插桩与 Telemetry snapshot，直连 `RG-DEP-001/RG-API-001/RG-LOG-001`。  
  - **S2 Runtime Gateway & Queue 守护**：RuntimeGateway 及 ChannelHealthStore 重构与其 pytest 套件，对应 `RG-DEP-001/RG-CYCLE-001/RG-SIZE-001`。  
  - **S3 Admin 覆盖门禁**：WorkflowChannelForm/ChannelHealthCard/Pinia store、Rise workflow API，确保 coverage status 为 webhook 启用前置条件。  
  - **S4 Webhook Secret/TLS 守护**：Secret 唯一性、证书监测与 Observability 事件，遵循 Telegram 官方“唯一 secret + TLS 证书可用性”建议。citeturn0search0  
  - **S5 冲突模式检测**：防止同时启用 webhook 与 polling，依据社区案例锁定互斥策略。citeturn0reddit15
- 排除项：不交付新业务流程、不过度扩展 Up Admin 的 UI 以外区域；OpenAI/Redis/Mongo 的部署细节保持现状，仅描述接口与状态契约。

## 2. Tech Stack Overview
### 后端（Rise）
- Python 3.11 + FastAPI 0.118.x：所有表征测试通过 `fastapi.testclient.TestClient` 上下文触发 lifespan，保证依赖覆盖与资源清理（Context7 `/fastapi/fastapi/0.118.2` · testing-events）。  
- aiogram 3.22.0 Dispatcher + webhook server：遵循官方 webhook setup（Context7 `/websites/aiogram_dev_en_v3_22_0`），由 `interface_entry/http/telegram/routes.py` 反向代理至业务层。  
- Pydantic v2 DTO、Redis 7（`redis-py` 6.4）作为 coverage state & rate counter、MongoDB 7（PyMongo 4.6）持久化 `workflow_run_coverage`，OpenAI SDK 1.105 用于 orchestrator stage。  
- Observability：Rich logging、`src/foundational_service/telemetry/bus.py`、Prometheus exporter，新增 coverage status/证书指标；`var/logs/test_runs` 用于 QA 下载。

### 前端（Up）
- Vue 3.4 + Vite 5 + Pinia + Element Plus + Vue Flow；`CodeMirror` 维持 prompt 编辑体验。  
- Pinia `channelPolicy` store 拆分 coverage/health/error 状态，遵循 Pinia 官方对 async actions try/catch 与集中 error store 的实践（Exa · StudyRaid《Build Scalable Vue.js Apps with Pinia State Management》）。  
- 组件拆分遵循现有 AGENTS 约束（窄职责 + props/emits 契约）。

### 基础设施与运行
- Telegram Bot API（webhook 模式，TLS 证书与 secret token 需唯一）。citeturn0search0  
- Redis：`rise:coverage:workflow:<workflow_id>`、`rise:coverage:last_run`, `rise:channel:test_heartbeat`.  
- Mongo：`workflow_run_coverage`（历史执行）、`workflow_channels`（新增 `testCoverage` 字段）。  
- Prometheus/Grafana：新增 `rise_coverage_status`、`rise_webhook_cert_expiry_days` 指标。

### 测试 & 质量工具
- pytest + coverage + snapshot（`snapshottest` 或 `pytest-approvaltests`）确保 Golden 日志/响应稳定。  
- Schemathesis/HTTPX 组合用于接口 fuzzing，呼应“以 OpenAPI 生成用例”的社区经验（Exa · Medium《Boost Your FastAPI Reliability with Schemathesis Automated Testing》）。  
- 门禁脚本：`import-linter`（RG-DEP-001）、`madge`（UP-CYCLE-001）、`radon` 行数/复杂度守卫。

### 环境变量 / feature flag（新增或强化）
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_CERT_PATH`, `WEBHOOK_BASE_URL`.  
- `REDIS_URL`, `MONGO_URL`, `COVERAGE_MAX_AGE_DAYS`（默认 7，<=30 hard limit），`COVERAGE_MIN_GOLDEN`（默认 3，签证类 5）。  
- `ENABLE_SCHEMATHESIS`（CI 夜间 fuzzing）、`CHANNEL_TEST_AUTORUN_CRON`, `PROM_ALERT_WEBHOOK_CERT`.

## 3. Module/File Change Matrix
### S1 · Webhook 表征测试（Test IDs：RG-DEP-001 / RG-API-001 / RG-LOG-001）
- `tests/business_service/conversation/test_telegram_webhook.py`（新增）：实现 Golden 场景、Telemetry snapshot；变更类型 add；支持 `pytest -m characterization`。  
- `tests/business_service/conversation/fixtures/{workflow}/{scenario}.json` 与 `snapshots/*.yml`（新增目录+样例）；add；记录入/出站消息与 side-effects。  
- `tests/business_service/conversation/conftest.py`（新增）：集中 dependency override、Telemetry capture；add；可复用 stub gateway。  
- `src/interface_entry/http/telegram/routes.py`（modify）：暴露 dependency override 钩子、接入 aiogram Router；确保不直接依赖 business logic。  
- `src/business_service/conversation/service.py` + `runtime_dispatch.py`（modify）：拆出 orchestrator/telemetry 注入点，为测试注入 stubs；减轻胖文件。  
- `src/project_utility/telemetry.py`（modify）：提供 `emit_snapshot(event_name, payload, *, sink)`，支持写入 `var/test_runs`.  
- `CI/scripts/check_characterization.sh`（新增）：封装 RG-DEP-001/REG-SIZE-001 相关命令，确保 PR 钩子。

### S2 · Runtime Gateway & Queue 守护（Test IDs：RG-DEP-001 / RG-CYCLE-001 / RG-SIZE-001）
- `tests/business_service/conversation/test_runtime_gateway.py`（新增）：涵盖 enqueue、retry、ChannelHealthStore 心跳；add。  
- `src/business_service/conversation/runtime_dispatch.py`（modify）：显式依赖 `ChannelBindingHealthStore` 接口，抽出 `AsyncResultHandleFactory` 参数。  
- `src/business_service/channel/health_store.py`（modify）：增加 `record_test_heartbeat(workflow_id, *, status, timestamp)`，并将 Redis key 写入 coverage。  
- `src/foundational_service/persist/redis_queue.py`/`worker.py`（modify）：通过 `contracts/workflow_exec.WorkflowExecutor`（已有）注入 orchestrator，去除 BL/BS 上行引用。  
- `src/foundational_service/contracts/workflow_exec.py`（modify）：新增 `CoverageTestResult` DTO，供 worker 返回 telemetry。  
- `docs/testing/runtime_gateway.md`（新增）：记录 stub/queue 行为以支撑 RG-CYCLE-001。

### S3 · Admin 覆盖门禁（Test IDs：RG-PATH-001 / RG-SIZE-001 / UP-SIZE-ALL-001）
- **后端**：  
  - `src/business_service/channel/coverage_status.py`（新增）：封装 Redis/Mongo 访问，由 `CoverageStatusRepository` 与 `CoverageStatusService` 提供 `get_status`, `mark_green`, `mark_yellow`, `mark_red`。  
  - `src/interface_entry/http/workflows/routes.py`（modify）：`GET/POST /workflow-channels/{workflowId}` 增加 `testCoverage` 字段与 `/tests/run` 触发器。  
  - `src/business_service/workflow/repository.py`（modify）：持久化 coverage metadata。  
  - `src/foundational_service/telemetry/bus.py`（modify）：广播 `CoverageTestCompleted`。  
  - `tests/business_service/channel/test_coverage_status.py`（新增）覆盖 Redis/Mongo fallbacks。  
- **前端**：  
  - 新建目录 `Up/src/components/channel-form/`，拆分 `WorkflowChannelForm.vue` → `ChannelFormShell.vue`（编排）、`ChannelFieldsBasic.vue`、`ChannelFieldsSecurity.vue`、`ChannelCoverageGate.vue`。  
  - `Up/src/stores/channelPolicy.js`（modify）：state 增加 `coverageStatus`, `coverageLastRun`, `testScenarios`, `errors`; actions `fetchCoverage`, `runCoverageTests`.  
  - `Up/src/components/ChannelHealthCard.vue` + `ChannelTestPanel.vue`（modify）：渲染覆盖状态与日志流；支持 SSE。  
  - `Up/src/services/channelPolicyClient.js`（modify）：新增 `/tests/run` 与 coverage GET API。

### S4 · Webhook Secret/TLS 守护（Test IDs：RG-DEP-001 / RG-API-001）
- `src/foundational_service/observability/public_endpoint_probe.py`（新增）：周期检查 SSL 证书剩余天数、Secret 重复；写入 Prometheus/Telemetry。  
- `src/foundational_service/messaging/channel_binding_event_publisher.py`（modify）：当 Secret/证书变更时发出 `WebhookCredentialRotated`。  
- `src/interface_entry/http/workflows/routes.py`（modify）：启用渠道时验证唯一 Secret/证书有效期；失败返回 409 + 错误细节。  
- `Up/src/components/channel-form/ChannelFieldsSecurity.vue`（add）：表单输入 webhook Secret、证书；实时展示唯一性校验结果。  
- `Up/src/stores/channelPolicy.js`（modify）：添加 `validateSecretUniqueness` action；出错时 `ChannelCoverageGate` 显示阻塞原因。  
- `obs/alerts/webhook_cert.rules`（新增）：Prometheus 规则 >14d 警告。

### S5 · 冲突模式检测（Test IDs：RG-PATH-001 / UP-CYCLE-001）
- `src/business_service/channel/policy.py`（modify）：新增 `ChannelMode` 枚举（webhook/polling），在服务层阻断双模式。  
- `src/interface_entry/http/workflows/routes.py`（modify）：序列化 `usePolling` 字段，若 webhook 已启用则拒绝 `usePolling=true` 请求。  
- `Up/src/stores/channelPolicy.js` & `ChannelFieldsBasic.vue`（modify）：UI 勾选 `usePolling` 时自动禁用 webhook，显示“需手动验证”提示。  
- `Up/src/components/WorkflowChannelForm.vue`（modify壳）：集中 props/emits；对冲互斥逻辑；配合 `UP-CYCLE-001` 监控 import graph。  
- `tests/business_service/channel/test_channel_modes.py`（add）：验证 API 互斥 rule；`UP/tests/components/ChannelCoverageGate.spec.ts`（add）覆盖前端逻辑。

## 4. Function & Interface Summary
### Rise · 核心后端模块
- `src/interface_entry/http/telegram/routes.TelegramWebhookRoute.handle_update(update: TelegramUpdateDTO)`  
  - 输入：Telegram 原始 JSON + Secret header；输出：202/200；依赖 `aiogram.Router`, `business_service.conversation.service`.  
  - 副作用：写入 `TelemetryEmitter`, 调用 `RuntimeGateway.enqueue`.  
  - 测试钩子：通过 `dependency_overrides["runtime_gateway"]` 注入 stub。
- `tests/business_service/conversation/test_telegram_webhook.py::test_passport_status_dialog()`  
  - 输入：fixture `passport_status_inbound.json`; 断言：HTTP 200、Telemetry snapshot、Redis key diff。  
  - 依赖：`TestClient`, `snapshot_writer`, stub `RuntimeGateway`.  
- `src/business_service/conversation.runtime_dispatch.RuntimeGateway.enqueue(workflow_id, payload, *, retries)`  
  - 输入：workflowId、normalized payload、channel metadata；输出：`WorkflowRunResult`; 依赖 `ChannelBindingHealthStore`, `redis_queue`.  
  - 副作用：写 `rise:coverage:workflow`, `rise:channel:test_heartbeat`; 异常触发 retry/backoff。
- `src/business_service/channel.coverage_status.CoverageStatusService`  
  - 方法：`get(workflow_id)`, `mark_green(...)`, `mark_yellow(...)`, `mark_red(...)`.  
  - 输入：Redis/Mongo clients、clock、retention config；输出：`CoverageStatusDTO`.  
  - 副作用：落地 Redis TTL、Mongo 历史记录；触发 Telemetry。
- `src/foundational_service/observability.public_endpoint_probe.PublicEndpointProbe.run()`  
  - 输入：workflow 列表、证书路径、Secret map；输出：`ProbeResult`; 依赖 OpenSSL 验证、Redis 缓存。  
  - 副作用：写 Prometheus gauge、发 `WebhookCredentialRotated` 事件。
- `src/business_service/channel.policy.ChannelPolicyService.validate_modes(payload)`  
  - 输入：`usePolling`, `enableWebhook`; 输出：`ChannelModeDecision`;  
  - 副作用：记录 audit log；冲突时报错 409。

### Up · Admin 模块
- `Up/src/stores/channelPolicy.js`  
  - state：`coverageStatus`, `coverageLastRun`, `testScenarios`, `errors`, `usePolling`, `webhookEnabled`.  
  - actions：`fetchCoverage(workflowId)`, `runCoverageTests(workflowId)`, `validateSecret(secret)`, `toggleWebhook(mode)`。  
  - 依赖：`channelPolicyClient`, `WorkflowService`, SSE bus；副作用：更新 `ChannelHealthCard`.  
- `Up/src/components/channel-form/ChannelCoverageGate.vue`  
  - props：`coverageStatus`, `lastRun`, `scenarios`, `blockingReasons`; emits：`requestRunTests`.  
  - 逻辑：展示红/黄/绿状态，黄/红时禁用“启用 webhook”按钮并显示 CTA。  
  - 侧效：通过 `runCoverageTests` action 触发后台 API，监听 `WorkflowLogStream`.
- `Up/src/components/channel-form/ChannelFieldsSecurity.vue`  
  - 输入：Secret、证书文件；调用 `validateSecret`；  
  - 副作用：在本地显示唯一性/证书有效期提示。  
- `Up/src/components/WorkflowChannelForm.vue`  
  - 责任：作为编排壳，把 `props` 分发给 `ChannelFormShell`, `ChannelCoverageGate`, `ChannelSubmitActions`；  
  - 依赖：Pinia store、ElementForm；  
  - 副作用：阻断冲突模式提交。

## 5. Best Practices & Guidelines
- **FastAPI 表征测试**：所有 API/Telegram 测试通过 `TestClient` 上下文触发 lifespan，确保依赖注入与资源释放；引用 Context7 `/fastapi/fastapi/0.118.2`（Testing Events）。  
- **aiogram Webhook 安全**：遵循官方 3.22 webhook 指南使用 `secret_token` 与自签证书上传流程（Context7 `/websites/aiogram_dev_en_v3_22_0`）。  
- **Schemathesis Fuzzing**：将 `/workflow-channels/*`、`/telegram/webhook/*` OpenAPI schema 导入 Schemathesis 以寻找边界输入；依据 Exa Medium 文章建议，将其接入夜间 CI。  
- **Pinia 错误治理**：所有异步 action 使用 try/catch 并更新集中 error store，保障 ChannelHealth UI 明确状态（Exa StudyRaid Pinia 指南）。  
- **Secret/TLS 合规**：Telegram 社区建议 Secret 当作密码、避免在多个 bot 复用；证书需监控剩余天数。citeturn0search0  
- **模式互斥**：实际经验显示同一 bot Webhook 与 IFTTT/多个触发器并行会导致更新丢失，故 UI 与 API 必须互斥。citeturn0reddit15

## 6. File & Repo Actions
- **Rise**  
  - 新建：`tests/business_service/conversation/{test_telegram_webhook.py, test_runtime_gateway.py, conftest.py, fixtures/, snapshots/}`；`src/business_service/channel/coverage_status.py`；`src/foundational_service/observability/public_endpoint_probe.py`；`docs/testing/runtime_gateway.md`；`CI/scripts/check_characterization.sh`。  
  - 修改：`src/interface_entry/http/telegram/routes.py`、`src/business_service/conversation/{service.py,runtime_dispatch.py}`、`src/business_service/channel/{health_store.py,policy.py}`、`src/business_service/workflow/repository.py`、`src/foundational_service/{persist/redis_queue.py,contracts/workflow_exec.py,messaging/channel_binding_event_publisher.py,telemetry/bus.py}`、`src/project_utility/telemetry.py`、`src/interface_entry/http/workflows/routes.py`。  
  - 配置：`.importlinter`, `.madgerc`, `pyproject.toml`（radon/mypy 钩子）。  
- **Up**  
  - 新建目录：`src/components/channel-form/`（含 `ChannelFormShell.vue`, `ChannelFieldsBasic.vue`, `ChannelFieldsSecurity.vue`, `ChannelCoverageGate.vue`, `ChannelSubmitActions.vue`）。  
  - 修改：`src/components/WorkflowChannelForm.vue`, `src/components/ChannelHealthCard.vue`, `src/components/ChannelTestPanel.vue`, `src/stores/channelPolicy.js`, `src/services/channelPolicyClient.js`, `src/views/WorkflowBuilder.vue`。  
  - 测试：`tests/components/ChannelCoverageGate.spec.ts`、`tests/stores/channelPolicy.spec.ts`。  
- **Ops/Docs**：`obs/alerts/webhook_cert.rules`、`docs/testing/runtime_gateway.md`、`README-channel-tests.md` 更新运行指令。

## 7. Risks & Constraints
- **Golden 数据脱敏**：真实 Telegram 对话需脱敏；若无法脱敏，转为合成数据并在 README 记录来源。缓解：引入 `scripts/sanitize_transcript.py`，仅保存必要字段。  
- **Redis/Mongo 不可用**：coverage 状态降级为本地 JSON；风险是状态不同步。缓解：`CoverageStatusService` 在降级时自动 mark red 并提醒 Operator。  
- **Schemathesis 运行时长**：夜间 fuzzing 可能耗时；缓解：限定在高风险 workflow，使用 sampled endpoints。  
- **前端循环依赖**：拆分组件后 import graph 复杂；缓解：`madge` 护栏 + 文档化 props/emits。  
- **Secret/TLS 轮换窗口**：在 Secret 更新但测试未跑前 webhook 处于危险期；缓解：自动标记 yellow + 禁用启用按钮，Observability banner 提示。  
- **Polling 兜底需求**：紧急情况下允许 polling 但测试无法覆盖；缓解：记录 `mode: polling`，promote 手工 checklist。

## 8. Implementation Decisions（无开放项）
1. Golden 对话来源于最近 30 天脱敏日志；默认 3 条，高风险（签证/认证）记录 5 条；脚本生成并存档在 `tests/business_service/conversation/fixtures`.  
2. coverage 自动刷新频率：`COVERAGE_MAX_AGE_DAYS=7`；CI 夜间触发 `/tests/run`；超期自动标记 yellow 并显示 banner。  
3. 连续 3 次 characterization 失败自动禁用 webhook；单次失败仅阻断发布并提示 Operator。  
4. 不同 Telegram bot 禁止共用 webhook Secret；Secret 更新后必须重新跑测试才允许启用。  
5. Observability 数据保留：Redis 14 天、Mongo 180 天；Prometheus 指标与 Grafana 面板同周期。  
6. webhook 与 polling 互斥：`ChannelPolicyService` 与 `WorkflowChannelForm` 一致拒绝同时启用，UI 提示“需手动验证”。  
7. `ChannelHealthCard` 将 coverage 状态与绑定启用强绑定，status≠green 时禁用“启用”操作；`ChannelTestPanel` 可直接触发 `/tests/run` 并展示日志。  
8. 所有护栏脚本纳入 PR required checks（RG-DEP-001、RG-ONEOFF-001、RG-SIZE-001、UP-CYCLE-001），其余（Schemathesis、RG-API-001）纳入夜间定时。


