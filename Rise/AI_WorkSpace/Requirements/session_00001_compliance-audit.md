# Session 00001 · compliance-audit (Assessment Focus · Full Rewrite)

Generated at: 2025-11-12

说明：本文件为“审计/盘点现状”版本，仅列出结构合规相关的发现（Findings）、证据（Evidence）、影响（Impact）与优先级（Priority）。不包含未来方案与改造设计；若需进入方案阶段，将在收到明确指示后另行编写。

## Scope
- 范围：对照 `AI_WorkSpace/PROJECT_STRUCTURE.md`、`Rise/AGENTS.md`、`Up/AGENTS.md`，检查分层依赖、目录落位、文件职责粒度与（项目仓库内的）文档痕迹。
- 不在范围：安全/合法性、零信任、网关/WAF 等非结构性议题。
- 明确排除：整棵 `AI_WorkSpace\` 树（仅用于元信息与 AI 产物，不属于项目代码）；本审计只读取/写入 `Requirements` 与 `session_notes`，不将 `AI_WorkSpace` 作为被审计对象。
- 参考（记录 Context7/Exa 引用 ID，用于可追溯）：
  - Context7: `/fastapi-practices/fastapi_best_architecture`, `/jiayuxu0/fastapi-template`
  - Exa: `https://www.scrums.com/checklists/modernize-your-legacy-software`, `https://nix-united.com/blog/legacy-application-modernization-strategies/`, `https://ardura.consulting/our-blog/modernizing-legacy-systems-when-to-rebuild-refactor-or-replace/`

## Findings (with Evidence, Impact, Priority)

1) Business Service 反向依赖 Business Logic · Priority P0
- Evidence
  - path: `src/business_service/conversation/service.py:16`
  - code: `from business_logic.workflow import WorkflowRunResult, WorkflowStageResult`
- Impact
 - 违反“自上而下单向依赖”的架构约束（Business Service 不应依赖 Business Logic），削弱可替换性与可测试性，增加变更扩散风险。

2) Foundational 反向依赖 Business Logic/Service · Priority P0
- Evidence
  - path: `src/foundational_service/persist/worker.py:12`
  - code: `from business_logic.workflow import WorkflowExecutionContext, WorkflowOrchestrator, WorkflowRunResult`
  - path: `src/foundational_service/persist/worker.py:13`
  - code: `from business_service.workflow import StageRepository, WorkflowRepository`
  - path: `src/foundational_service/integrations/memory_loader.py:10-11`
  - code: `from business_service.knowledge import KnowledgeSnapshotService` / `from business_service.knowledge.models import AssetGuardReport, SnapshotResult`
  - path: `src/foundational_service/messaging/channel_binding_event_publisher.py:10`
  - code: 引用 `business_service.channel.events`
- Impact
  - 基础层（Foundational）不应上行依赖业务逻辑/业务服务；该类依赖提高层间耦合，阻碍抽换与复用。

3) Business Service 依赖 Interface/Entry 适配器 · Priority P0
- Evidence
  - path: `src/business_service/conversation/primitives.py:9`
  - code: `from interface_entry.telegram.adapters import append_streaming_buffer, telegram_update_to_core`
- Impact
  - 业务服务层不应引用入口适配器（协议/界面细节应停留在入口层），导致业务层携带界面形态，降低可移植性。

4) 超大“胖文件”且多职责混杂（后端） · Priority P0
- Evidence
  - path: `src/business_service/conversation/service.py`
  - size: 约 1286 行；聚合频道健康、Runtime 网关、Pipeline、入/出站契约、重试与观测等多种职责。
- Impact
  - 评审与测试困难；任何小改动都可能牵动多处逻辑，极易产生回归。

5) Up 组件过度承载（前端） · Priority P1
- Evidence
  - `Up/src/components/PromptEditor.vue` ≈ 437 行：混合布局、表单校验、编辑器状态与样式切换；
  - `Up/src/components/NodeDraftForm.vue` ≈ 396 行；`Up/src/components/WorkflowChannelForm.vue` ≈ 388 行。
- Impact
  - 单组件承担多变更原因（UI 布局、业务校验、网络调用），可复用与测试难度大；与“窄职责+文档契约”不符。

6) Up 文档缺口 · Priority P2
- Evidence
  - `Up/docs/ProjectDev` 未检到 “WorkflowBuilder/PromptEditor” 的父子组件契约说明（orchestrated 子组件清单/事件契约）。
- Impact
  - Orchestrator 组件边界不清晰，影响后续拆分与接入的一致性。

7) one_off 与核心路径隔离（合规） · Info

## Supplemental Evidence — Largest Files（行数）
- 后端 Top
  - 1286: `src/business_service/conversation/service.py`
  - 731: `src/interface_entry/bootstrap/application_builder.py`
  - 575: `src/interface_entry/http/workflows/routes.py`
  - 507: `src/project_utility/logging.py`
  - 400: `src/interface_entry/http/dependencies.py`
  - 392: `src/interface_entry/http/channels/routes.py`
  - 383: `src/foundational_service/persist/redis_queue.py`
  - 380: `src/interface_entry/telegram/handlers.py`
  - 368: `src/foundational_service/persist/worker.py`
  - 362: `src/foundational_service/contracts/telegram.py`
  - 360: `src/foundational_service/telemetry/bus.py`
- 前端 Top
  - 832: `Up/src/views/PipelineWorkspace.vue`
  - 454: `Up/src/components/WorkflowEditor.vue`
  - 449: `Up/src/components/NodeActionList.vue`
  - 437: `Up/src/components/PromptEditor.vue`
  - 396: `Up/src/components/NodeDraftForm.vue`
  - 388: `Up/src/components/WorkflowChannelForm.vue`
  - 274: `Up/src/views/WorkflowBuilder.vue`
- Evidence
  - `src/one_off/*` 目录未见被核心执行路径 import 的反向引用。
- Impact
  - 当前符合“核心不依赖一次性脚本”的要求。

## Recommended Priority (Behavior-Preserving)
- P0（当周内建议处理）：
  - 移除 `business_service → business_logic` 的直接依赖（保留接口/DTO 或由更高层注入结果）。
  - 将 `conversation/service.py` 瘦身为编排壳，拆出子模块（不改变对外行为）；必要的说明记录在项目仓库内（如 `docs/` 或源码 docstring），不使用 `AI_WorkSpace`。
  - 消除 `foundational_service → business_logic`/`business_service` 的上行 import；改为向下可注入抽象或通过中立契约交互。
  - 去除 `business_service → interface_entry` 的适配器引用；协议转换在入口层完成。
- P1（两周内建议处理）：
  - 拆分 Up 大组件为窄职责子组件，服务调用下沉至 services，父组件仅编排。
- P2（一个月内建议处理）：
  - 增补 Up 文档契约（WorkflowBuilder/PromptEditor），形成可追溯的父子组件清单与事件约定。

## Acceptance (for this Audit Round)
- 验收以“事实对齐”与“差距收敛”为准：
  - [A1] 依赖图中不再存在 `business_service → business_logic` 上行 import；
  - [A2] 依赖图中不再存在 `foundational_service → business_logic`/`business_service` 上行 import；
  - [A3] `conversation/service.py` 行数显著下降，父文件仅保留编排逻辑；
  - [A4] Up 组件单个文件行数下降且功能聚焦，存在明确的子组件与 props/emit 契约。

## Notes
- 本文件为 Assessment Focus，旨在“列出问题 + 证据 + 影响 + 优先级”。若需进入 Strategy Focus（方案与改造细化），请在聊天中明确指示，再进行后续写作。

---

## Strategy Requirements · Characterization Harness for `conversation/service.py` Refactor (2025-11-13)

### Background
- `AI_WorkSpace/Reports/session_00001_compliance-audit_issues.json`（Step-03）指出：在拆分 1,200+ 行的 `src/business_service/conversation/service.py` 前，缺乏 business_service 层级的 characterization 测试，无法证明 Telegram Webhook→Workflow Orchestrator→Runtime Gateway 全链路行为保持不变。
- 现状：`tests/` 仅覆盖 foundational_service，`business_service`、`interface_entry/http/channels` 与 `WorkflowChannelForm` 的配置校验均无自动化护栏，Operators 无法在 Up Admin 中查看测试覆盖状态。
- 目标：在不改动生产行为的前提下，交付一套“离线 Telegram 表征测试 + Admin 覆盖可视化 + 强约束 webhook 配置”的双仓（Rise+Up）需求，确保后续拆分可以在可重复的测试与审批流程下进行。

### Roles
- **Rise Runtime Maintainer**：维护 FastAPI/aiogram entrypoints、`TelegramConversationService` 拆分计划，并负责新增测试夹具与 dependency override。
- **QA / Test Automation Engineer**：编写 `tests/business_service/conversation/*` 套件，管理 golden Telegram transcript、预期 orchestrator 输出、Redis/Mongo stub 数据。
- **Up Admin Operator**：在 `WorkflowChannelForm`、`ChannelHealthCard` 中查看“测试覆盖/最新运行”状态，配置 webhook Secret/证书，阻止未覆盖工作流上线。
- **SRE / Observability Engineer**：将测试结果写入 `TelemetryEmitter`、`channel_policy` 健康指标，并为 `workflow_run_coverage` Redis/Mongo 记录设置保鲜期、报警。
- **Security Reviewer**：确保多 bot/webhook Secret 的隔离、TLS 证书有效性，避免 `treehook.dev` 指出的 secret 复用风险和 webhook 劫持。citeturn1search0

### Scenarios
1. **S1：Webhook 表征测试（离线）**
   - 触发：QA 在本地或 CI 执行 `pytest tests/business_service/conversation/test_telegram_webhook.py::test_passport_status_dialog`.
   - 参与：QA、TestClient (`fastapi.testclient.TestClient`)、`interface_entry/http/telegram/routes.py`、Redis/Mongo stubs。
   - 前置：`fixtures/telegram/passport_status_inbound.json`、`fixtures/telegram/expected_runtime.json` 已建立；`ChannelBindingRuntime` 使用 stub。
   - 步骤：① 通过 `TestClient` 向 `/telegram/webhook/{botToken}` POST Golden Update；② dependency override 注入 stub `RuntimeGateway` / `AsyncPipelineNodeService`；③ 捕获 `TelemetryEmitter` 输出并与 snapshot 对比；④ 清理 stub state。
   - 数据变更：写入 `var/test_runs/<workflow_id>/<timestamp>.jsonl`、`redis://rise:test:coverage:<workflow_id>`；CI artifact 存档。
   - 遥测：`CoverageTestCompleted` 事件（字段：workflowId/botUsername/testId/duration/assertions）。

2. **S2：Runtime Gateway & Queue 守护测试**
   - 触发：`pytest tests/business_service/conversation/test_runtime_gateway.py`.
   - 参与：Runtime Maintainer、`RuntimeGateway`、`AsyncAckReservation`、`ChannelBindingHealthStore`、Redis stub。
   - 前置：构造 `AsyncResultHandleFactory` stub 以注入 `RetryState`；准备 `WorkflowChannelPolicy` fixture（含速率限制）。
   - 步骤：① 模拟 orchestrator 输出 `WorkflowStageResult`；② 断言 `RuntimeGateway.enqueue` 对 `ChannelBindingHealthStore` 的心跳写入；③ 验证异常路径（e.g., `EnqueueFailedError`）触发 retry 上限警报。
   - Up 影响：在 `ChannelHealthCard` 新增“最新测试心跳”字段；当测试失败时，WorkflowBuilder 阻止发布。

3. **S3：Admin 覆盖门禁**
   - 触发：Operator 在 `WorkflowChannelForm` 勾选“启用 Telegram 绑定”并提交。
   - 参与：Up Admin UI (`WorkflowChannelForm.vue`)、`channelPolicy` store、`WorkflowChannelService` API、Rise `/workflow-channels/{workflowId}`。
   - 前置：Rise 暴露新只读字段 `testCoverage.status` 与 `testCoverage.updatedAt`，并提供 `POST /workflow-channels/{workflowId}/tests/run` 触发即时测试。
   - 步骤：① UI 获取 coverage 状态并提示“最后成功运行时间”与“覆盖场景列表”；② 若 status != `green`，禁用“启用”按钮并显示原因；③ Operator 可点击“重新运行”调用 API，查看日志流。
   - 数据：Up store 缓存 coverage 状态（Pinia），Rise 记录在 Redis `rise:coverage:workflow:<id>` + Mongo `workflow_run_coverage`。

4. **S4：Webhook Secret/TLS 守护**
   - 触发：Operator 在 Up 中更新 bot webhook Secret 或上传新的 TLS 证书。
   - 前置：`treehook.dev`、blog.zelia.dev 建议每个渠道独立 Secret + 固定 IP/TLS 监控。citeturn1search0turn1search1
   - 步骤：① Up 校验 Secret 未在其他 workflow 使用；② 将证书到期时间写入 Rise `PublicEndpointProbe`；③ Observability 作业每 6h 检查证书、Secret 使用频率，与 coverage 状态联动发警。
   - 结果：当证书到期<14d 或 Secret 重复，`ChannelHealthCard`、`WorkflowLogStream` 显示警告；Rise API 拒绝启用请求。

5. **S5：冲突模式检测**
   - 场景：Operator 尝试同时启用 Telegram webhook 与 polling（Qiita 指出的冲突）。citeturn1search2
   - 要求：Up 在 `channelPolicy` 中新增布尔字段 `usePolling`; 若为 true，则自动禁用 webhook + 显示提示“测试护栏无法覆盖 polling，需手动验证”；Rise API 拒绝 webhook & polling 同时启用。

### Data / State
- **测试夹具**：`tests/business_service/conversation/fixtures/<workflow>/<scenario>.json`（Telegram inbound）、`expected_outputs.json`（orchestrator output）、`runtime_side_effects.json`；需在 README 中描述格式与生成方法。
- **Snapshot 资产**：`tests/business_service/conversation/snapshots/<workflow>/<scenario>.yml` 保存 `TelemetryEmitter` 行为、Redis key 修改，便于审查 diff。
- **Coverage 状态存储**：
  - Redis：`rise:coverage:workflow:<workflow_id>` 保存 `{"status":"green|yellow|red","last_run":"ISO8601","scenarios":["passport_status", ...]}`。
  - Mongo：`workflow_run_coverage` 集合记录历史 run（workflowId, botUsername, gitSha, result, duration, assertions, operatorId）。
- **Up Admin 状态**：Pinia `channelPolicy` store 增加 `coverageStatus`、`coverageLastRun`, `testScenarios`；`WorkflowBuilder.vue` 将其传给 `ChannelHealthCard` 与 `WorkflowChannelForm`.
- **Secrets/Certs**：`workflow_channel` 文档扩展 `webhookSecretVersion`、`certExpiry`；Rise 通过 `PublicEndpointProbe` 写入 `app.state.webhook_security`.

### Rules
- 每个 workflow 至少需 3 条 Golden Telegram 对话：入站文本、含附件、含命令；高风险服务（签证/认证）需 5 条。默认 30 天需要刷新一次。
- Characterization 测试必须走 FastAPI `TestClient` + dependency override，而非直接调用 service（符合 fastapi 官方建议，可验证 lifespan hook 与依赖覆盖）。citeturn2search0
- Tests 禁止访问真实 Telegram/Redis/Mongo；统一使用 faker/stub，避免污染生产状态。
- `WorkflowChannelForm` 在启用 webhook 前校验：coverage status = green、webhook Secret 未复用、证书>30 天；任一失败则 API 返回 409 并提示 UI。
- 覆盖状态与 channel 健康强绑定：`ChannelHealthCard` 将覆盖失效视为 P1 告警；`channelPolicy.scheduleNextPoll` 在 coverage 过期时缩短轮询间隔以提醒 Operator。
- 每次 `POST /workflow-channels/{workflowId}/tests/run` 结果需写入 Telemetry + `var/logs/test_runs`，并供 Up 立即拉取显示。
- Observability 任务若发现 coverage >14 天未运行，自动在 Up 顶部 banner 展示“需要重新训练”的提示，且 `sendChannelTest` throttle 仍可使用但提示“结果不被记录”。
- 微信?? (typo). Additionally, Slack/HTTP future channels must reuse same coverage interface once onboarded（document contract now）。

### Exceptions
- **Telegram API schema变更**：若表征测试因未知字段失败，Rise 需自动将 status 调为 yellow 并附带 diff；Operator 可设置 `overrideUntil`（<=72h）以临时允许 webhook 连通，同时触发人工审查。
- **Redis/Mongo 不可用**：测试运行 fallback 到本地 JSON 缓存，status 设置为 red 并向 Operators 提示“数据源未写入，结果仅供参考”。
- **Secret 轮换**：在 Secret 更新但未重新跑测试前，status 自动置为 yellow，Up 显示“请重新运行测试以验证新 Secret”。
- **Polling 模式**：若运维出于紧急需要启用 polling，系统允许但 coverage 记录 `mode: polling` 并标注需手动验收；Webhook 测试暂停执行。

### Acceptance
- **A1** GIVEN workflow 缺少 `tests/business_service/conversation` 夹具 WHEN Operator 尝试启用 webhook THEN Rise API 返回 409，Up UI 提示“请先完成表征测试”。
- **A2** GIVEN QA 使用 `pytest -m characterization` 运行所有场景 WHEN 测试通过 THEN Redis `rise:coverage:workflow:<id>` 更新为 green 且 Up 表单 5 秒内刷新状态；如失败，ChannelHealthCard 显示失败详情并保留 disable。
- **A3** GIVEN Operator 在 Up 中点击“重新运行测试” WHEN Rise 完成后台执行 THEN `WorkflowLogStream` 输出 telemetry，Operator 可下载最新 `var/test_runs` JSON，监控中同时出现 `CoverageTestCompleted` 事件。
- **监控期望**：Prometheus exporter 暴露 `rise_coverage_status{workflow_id=...}`，Grafana 面板展示红/黄/绿分布；Up SSE channel 在 status 变化时推送消息。

### Open Questions (含默认值，不需用户补充)
1. **Golden 数据来源**：默认取自最近 30 天真实对话脱敏记录；若敏感字段无法脱敏，则用合成输入并在 README 说明。
2. **最小刷新频次**：默认每 7 天自动跑一次 characterization（由 Github Actions 调用 `/tests/run`），可通过环境变量 `COVERAGE_MAX_AGE_DAYS` 覆盖。
3. **覆盖失败后的自动恢复**：默认连续 3 次失败才触发自动禁用 webhook；单次失败仅警告并要求人工确认。
4. **跨渠道复用策略**：默认不同 Telegram bot 不能共用 webhook Secret；未来扩展 Slack/HTTP 时沿用同一接口与状态文档。
5. **观测数据保留期**：Redis 记录 14 天、Mongo 180 天，满足审计追溯要求；可在 `config/observability.yaml` 参数化。
