# Rise + Up 端到端验证方案（session_20251112_0327_violation_alignment）

## 1. 封面
- **范围**：Rise Workflow 执行链（S1）、Telegram 入口去耦（S2）、Up Admin 渠道策略绑定（S3）、Workflow Builder 控制器（S4），覆盖 Requirements `AI_WorkSpace/Requirements/session_20251112_0014_violation_alignment.md` 中 S1-D1 ~ S4-D8 全量子场景。
- **目标**：生成 Demand→Specify→Tech→Tasks→Test 的闭环，验证 Rise（FastAPI + aiogram + Redis + Mongo）、Up Admin（Vue3 + Pinia + Vite）与 Telegram 渠道的协议一致性，确保上线前具备可回归、可观察、可追责的验证基线。
- **文档来源**：
  - 需求：`AI_WorkSpace/Requirements/session_20251112_0014_violation_alignment.md`
  - 技术方案：`AI_WorkSpace/DevDoc/On/session_20251112_0125_violation_alignment_tech.md`
  - 任务拆解：`AI_WorkSpace/Tasks/session_20251112_min_steps.md`
  - 备注：`AI_WorkSpace/notes/session_20251112_0125_violation_alignment_tech.md`
  - 索引 / 结构：`AI_WorkSpace/notes/session_20251111_2135_repo_index.md`、`AI_WorkSpace/PROJECT_STRUCTURE.md`
- **外部最佳实践引用**：CTX-FASTAPI-0.118.2、CTX-VITEST-4.0.7、CTX-CDP-MCP、CTX-AIOGRAM-3.22、CTX-REDIS-PY-6.4.0、CTX-PYMONGO-DRIVER、EXA-FASTAPI-TESTING、EXA-DEVTOOLS-MCP、EXA-TELEGRAM-MOCK。
- **合规基准**：保持 Gov Audit SLA、英/他加禄提示语 parity，所有测试仅通过官方入口（Rise API、Up Admin UI、Telegram webhook/Bot），满足 Behavior Contract 要求。
## 2. 场景映射（Demand→Tasks→Code）
| 场景 | 子场景 (D1-D8) | 任务映射 | 代码/层级 | 验收对齐 |
| --- | --- | --- | --- | --- |
| **S1 Workflow 执行与摘要持久化** | Redis/Mongo 同步、回放、降级、合规等 8 条（Requirements §S1）。 | Tasks Step-01 ~ Step-04（models、repository、orchestrator、依赖注入）。 | `src/business_logic/workflow/*`, `src/foundational_service/persist/workflow_summary_repository.py`, interface deps。层级遵循 `PROJECT_STRUCTURE`：Business Logic → Foundational Service。 | Acceptance 1 + 5（PH 审计）。 |
| **S2 Telegram 会话入口去耦** | mode 切换、队列一致性、健康心跳、节假日策略等 8 条（Requirements §S2）。 | Tasks Step-05 ~ Step-09（config、runtime_gateway、health、service、lifespan）。 | `src/business_service/conversation/*`, `interface_entry/bootstrap/*`；依赖 aiogram runtime。 | Acceptance 2 + 5。 |
| **S3 渠道策略绑定与健康轮询** | 策略保存、越权、健康降级、回滚、合规文案等 8 条（Requirements §S3）。 | Tasks Step-10 ~ Step-13（schemas、channelPolicyClient、channelHealthScheduler、Pinia store）。 | `src/schemas/channelPolicy.js`, `src/services/channelPolicyClient.js`, `src/services/channelHealthScheduler.js`, `src/stores/channelPolicy.js`（Pinia state-only，副作用入 services/composables，参考 DevDoc）。 | Acceptance 3 + 5。 |
| **S4 Workflow Builder 控制器** | 加载/发布、SSE、高容量、权限、并发编辑、紧急冻结、多语提示等 8 条（Requirements §S4）。 | Tasks Step-14 ~ Step-17（workflow service、pipeline SSE client、controller composable、WorkflowBuilder.vue）。 | `src/services/workflowDraftService.js`, `src/services/pipelineSseClient.js`, `src/composables/useWorkflowBuilderController.js`, `src/views/WorkflowBuilder.vue`, `src/stores/workflowDraft.js`。 | Acceptance 4 + 5。 |

> 结构参考 `AI_WorkSpace/notes/session_20251111_2135_repo_index.md` 提供的 index.yaml 输出格式，确保目录→层级映射与 `PROJECT_STRUCTURE` 一致。
## 3. 环境矩阵（Rise / Up / Telegram / 工具）
| 象限 | 环境 & 部署 | 必需变量 / 准入 | 模拟 / 依赖 |
| --- | --- | --- | --- |
| Rise API & Workers | `uvicorn app:app --env-file .env`（FastAPI 0.118.2，lifespan 管理 Redis+Mongo 连接）。 | `.env`：`WORKFLOW_SUMMARY_TTL_SECONDS`, `TELEGRAM_RUNTIME_MODE`, `MONGO_URI`, `REDIS_URL`。`local.settings.json` 记录 Gov Audit queue。
 | Redis 7.x (本地 docker) + Mongo 7.x 副本集；OpenAI SDK stub；`pytest` 使用 `@pytest.mark.asyncio`。FastAPI 生命周期测试遵循 CTX-FASTAPI-0.118.2。 |
| Up Admin（Vite dev server） | `pnpm install && pnpm dev --host`，Chrome 118。 | `.env.development`：`VITE_API_BASE_URL`, `VITE_ENABLE_OBSERVABILITY=true`，浏览器 localStorage 需设置 `up.actorId/up.actorRoles/up.tenantId`。 | `mock-api-server.cjs` 伪造 Rise API；`pnpm vitest --coverage`，Vitest 浏览器模式配置 Playwright Chromium（CTX-VITEST-4.0.7）。 |
| Telegram / Entry | `docker compose up aiogram-runtime`，Webhook 代理到 `https://<ngrok>/telegram`. | `TELEGRAM_BOT_TOKEN`, `WEBHOOK_SECRET`, `BASE_WEBHOOK_URL`。节假日数据从 `ph_holidays.json` 读取。 | aiogram v3.22 runtime（CTX-AIOGRAM-3.22）；Mockoon Telegram Bot API sample（EXA-TELEGRAM-MOCK）用于离线回放；RabbitMQ/Redis stream for queue。 |
| 工具 / 证据 | Chrome DevTools MCP（`mcp call`）+ Playwright 录制；Postman / VSCode Thunderclient；`kubectl`, `redis-cli`, `mongosh`, `pnpm vitest`, `pytest`, `chromedevtools run`。 | MCP Inspector 需 `CHROME_BINARY`, `MCP_INSPECTOR_TOKEN`；日志输出目录 `logs/devtools`. | `mcp.callTool('navigate_page'/'list_network_requests'/'get_network_request')` 记录 Network/Console（CTX-CDP-MCP, EXA-DEVTOOLS-MCP）；`invoke tests` 跑 redis-py 自测，`mongosh --eval` 清理数据（CTX-REDIS-PY-6.4.0, CTX-PYMONGO-DRIVER）。 |
## 4. 数据与模拟策略
- **Rise 后端数据**：
  - 使用 `tests/fixtures/workflow_summary.json` 作为静态模板，结合 `faker` 生成 chat_id、prompt 样本；`pytest` fixture 负责在 `redis-cli --eval flush_summary.lua <chat_id>` 前清空，运行后 `mongosh --eval 'db.chat_history.deleteMany({testRun:true})'` 清理。
  - Redis/Mongo 双写测试遵循 CTX-REDIS-PY-6.4.0 与 CTX-PYMONGO-DRIVER 示例，使用 `redis.from_url` + `client.start_session().with_transaction` 确保一致性。
- **Telegram 事件**：
  - 依托 aiogram webhook handler（CTX-AIOGRAM-3.22），以 Mockoon Telegram Bot API (EXA-TELEGRAM-MOCK) 提供 `/bot<token>/sendMessage`、`/setWebhook` 离线响应，并记录 request/response 供回放。
  - 节假日场景使用 `data/ph_holidays.json`，测试结束后回滚 `mode=sync` 并清空 `manual_guard` 标志。
- **Up Admin 状态**：
  - `tests/unit` 使用 Vitest + Testing Library（CTX-VITEST-4.0.7）mock Pinia store，`pnpm vitest --coverage` 生成报告；Chrome DevTools MCP 记录真实点击和 network HAR（CTX-CDP-MCP, EXA-DEVTOOLS-MCP）。
  - `mock-api-server.cjs` 按 Requirements 的 `/api/channel-policy`, `/api/workflows/:id/publish`, `/api/workflows/:id/logs/stream` 返回数据，避免直接操作数据库。
- **API 调试与 Postman**：
  - API 测试步骤按照 EXA-FASTAPI-TESTING（CSDN FastAPI API 测试流程）执行：创建请求、设定方法/参数、断言响应体，并将脚本同步到 `tests/e2e/postman`。
- **清理策略**：统一在 `scripts/test-teardown.ps1` 中封装 Redis/Mongo truncate、Mockoon session 停止、Chrome DevTools MCP `close_page`、Vitest `--runInBand` 关闭浏览器，防止污染。
## 5. 测试用例矩阵（Sx-Dy，每条 3 层）
> 每条测试均记录唯一 ID，包含触发步骤、命令/脚本、断言（含日志/事件）、前端/后端双重预期、所需工具/数据、自动化等级以及是否纳入回归。Rise API 测试遵循 CTX-FASTAPI-0.118.2 的生命周期模式；前端用例基于 CTX-VITEST-4.0.7 与 Chrome DevTools MCP 录证。

### S1 Workflow 执行与摘要持久化
#### S1-D1 核心功能：HTTP 同步 + Telegram 异步
- `S1-D1-UNIT`（P0 自动，TDD=是）：
  - 触发：`WorkflowOrchestrator.execute` 注入 fake `WorkflowSummaryRepository`，断言顺序与 summary 组装。
  - 命令：`pytest tests/business_logic/test_workflow_orchestrator.py -k test_execute_persists_summary`。
  - 断言：mock 仓储 `append_summary` 被调用一次，`WorkflowRunResult` 含 `result_id`；日志捕获 `workflow.summary.persisted`。
  - 前端/接口预期：HTTP handler 收到 200 + resultId stub。
  - 后端预期：Redis list+Mongo payload 未写入（由 mock 验证）。
  - 工具：pytest、faker、`caplog`。
- `S1-D1-INTEG`（P0 自动，TDD=是）：
  - 触发：`uvicorn` + `httpx.AsyncClient` 走 `/api/workflows/run`，Redis/Mongo docker 启动。
  - 命令：`pytest tests/integration/test_workflow_summary_repository.py -k test_http_and_telegram_channels`。
  - 断言：Redis `LLEN chat_summary:<chat>`=1、Mongo `chat_history` `$slice`=1；SSE 记录 `workflow.summary.persisted` 成功。
  - 前端预期：HTTP 响应 200；Telegram mock ack（Mockoon）返回成功。
  - 后端预期：`redis-cli lrange` 与 `mongosh` 数据一致。
  - 工具：docker compose（Redis/Mongo）、Mockoon、`redis-cli`, `mongosh`、`pytest-asyncio`。
- `S1-D1-E2E`（P1 半自动，纳入回归）：
  - 触发：Operator 通过 Postman 触发 HTTP workflow + Telegram bot 手动消息。
  - 命令：`newman run tests/e2e/workflow_summary.postman_collection.json`；并在 Telegram 客户端发送 `#test-summary`。
  - 断言：Postman Tests 校验 `result_id`，Chrome DevTools MCP `list_network_requests` 验证 `/api/workflows/run` 200，`get_network_request` 查看 payload；`redis-cli`/`mongosh` 校验写入；PagerDuty 未触发。
  - 前端预期：Up 通知 toast 显示 partial/success 文案。
  - 后端预期：日志 `INFO workflow.summary.persisted`。
  - 工具：Postman/Newman、Chrome DevTools MCP（CTX-CDP-MCP, EXA-DEVTOOLS-MCP）、Telegram bot、redis-cli、mongosh。

#### S1-D2 性能/容量：200 rps 写入
- `S1-D2-UNIT`（P0 自动）：`SummaryWriteQueue` worker 单测模拟 redis pipeline，断言批量写入策略切换。
  - 命令：`pytest tests/foundational_service/test_summary_queue.py -k test_bulk_flush_latency_tag`。
  - 断言：Latency>150ms 时 `bulk_writer` 标记；日志 `workflow.summary.backpressure`。
  - 前端预期：无 UI；CLI 输出 `summaryWriteMode=BATCH`。
  - 后端预期：Redis pipeline 使用 `LPUSH` 批量。
  - 工具：pytest + `freezegun`。
- `S1-D2-INTEG`（P0 自动）：使用 `locust` or `hey` 模拟 200 rps。
  - 命令：`hey -z 60s -c 50 -q 200 http://localhost:8000/api/workflows/run`。
  - 断言：Mongo 写入成功率≥99%，Backpressure 指标写入 Prometheus；Grafana alert 未触发或在 >500 queue depth 触发。
  - 前端预期：HTTP 202 + `summaryWriteMode=BATCH`。
  - 后端预期：Redis `LLEN` 队列小于阈值；`WARN workflow.summary.backpressure` 频率可控。
  - 工具：hey、Prometheus scrapes、`kubectl logs`。
- `S1-D2-E2E`（P2 人工）：夜间压测任务。
  - 命令：`python tools/load/summary_writer_stress.py --rps 200 --duration 900`。
  - 断言：UI toast“System busy”呈现；Ops Grafana 截图；Slack 警报记录。
  - 前端预期：Up Admin health banner提示排队；Telegram degrade 文案。
  - 后端预期：Redis/Mongo 指标恢复。
  - 工具：脚本 + Grafana、Slack webhooks。

#### S1-D3 安全/权限：未授权请求
- `S1-D3-UNIT`（P0 自动）：FastAPI dependency 单测，缺少 `workflow:write` scope.
  - 命令：`pytest tests/interface_entry/test_auth_dependencies.py -k test_workflow_scope_required`。
  - 断言：返回 403，日志 `SECURITY workflow.execute.denied` 含 actor_id。
  - 前端预期：HTTP 403 JSON；Up Admin Toast 显示多语言拒绝。
  - 后端预期：Telemetry `auth_failed`。
  - 工具：pytest, `respx`。
- `S1-D3-INTEG`（P0 自动）：`newman` 测试 403 及 SIEM 触发。
  - 命令：`newman run tests/e2e/security/workflow_scope.postman_collection.json`。
  - 断言：10 次 403 触发 SIEM webhook（mock server），`security.telegram.signature_failed` 未出现。
  - 前端预期：HTTP 403；Telegram Bot 提示 token invalid。
  - 后端预期：Audit 表记录。
  - 工具：Newman、Mock SIEM。
- `S1-D3-E2E`（P1 半自动）：真实角色切换。
  - 步骤：Ops 以 Reviewer 身份登录 Up Admin，尝试运行 workflow。
  - 命令：Chrome DevTools MCP `navigate_page=https://up.local/workflows`，`list_console_messages` 捕捉 403；`get_network_request` 确认 403 payload。
  - 断言：Console 无 JS error；API 403；PagerDuty 未触发。
  - 前端预期：多语言弹窗。
  - 后端预期：Audit 记录。
  - 工具：Chrome DevTools MCP、role-based account。

#### S1-D4 数据一致性：双写差异
- `S1-D4-UNIT`（P0 自动）：`consistency_repair_queue` producer+consumer 单测。
  - 命令：`pytest tests/foundational_service/test_consistency_repair.py`。
  - 断言：`half_persisted` 标记→入队 payload；repair job 补写成功。
  - 前端预期：API 响应 `summary_consistency="REPAIRING"`。
  - 后端预期：Redis/Mongo 补写成功；日志 `ERROR workflow.summary.consistency_gap`。
  - 工具：pytest, fakeredis, pymongo-memory-server。
- `S1-D4-INTEG`（P0 自动）：故意中断 Redis。
  - 命令：`pytest tests/integration/test_consistency_repair_flow.py -k redis_down`。
  - 断言：Mongo 成功写；Redis backlog 入 repair；Opsgenie webhook（mock）仅在>50时触发。
  - 前端预期：UI Banner“Summary stored but cross-store sync pending”。
  - 后端预期：repair job 清空 backlog。
  - 工具：docker stop redis, pytest, Opsgenie mock。
- `S1-D4-E2E`（P1 半自动）：真实 repair CLI。
  - 命令：`python tools/repair_summary.py --chat-id faker --dry-run`。
  - 断言：CLI 显示 diff；`mongosh`/`redis-cli` 再次对比为 0；Change log 记录。
  - 前端预期：Banner 消失。
  - 后端预期：repair 队列深度指标下降。
  - 工具：CLI、Grafana、Change log。

#### S1-D5 防御/降级：Redis 停机
- `S1-D5-UNIT`：配置 flag 驱动的降级测试。
  - 命令：`pytest tests/foundational_service/test_summary_repository.py -k mongo_only_mode`。
  - 断言：`summary_write_mode=MONGO_ONLY` 仅触发 Mongo 写+日志 `workflow.summary.degraded`。
  - 前端预期：HTTP 返回 “summary archived, realtime feed unavailable”。
  - 后端预期：Redis 调用被跳过。
  - 工具：pytest。
- `S1-D5-INTEG`：停 Redis 观察降级链路。
  - 命令：`docker stop rise-redis && pytest tests/integration/test_summary_degraded_flow.py`。
  - 断言：Teams/SMS 模拟器收到告警；Mongo 写成功。
  - 前端预期：Telegram TL 文案提示暂停。
  - 后端预期：`WARN workflow.summary.degraded` 计数。
  - 工具：docker, pytest, sms mock。
- `S1-D5-E2E`：运维手动演练。
  - 步骤：Ops 在维护窗口拉闸 Redis，触发 degrade，再 `docker start`。
  - 断言：Banners 先出现后消失，`redis-cli info` 正常；PagerDuty 闪告关闭。
  - 工具：Ops runbook。

#### S1-D6 观察性：Telemetry 丢失
- `S1-D6-UNIT`：`telemetry hooks` 重新绑定单测。
  - 命令：`pytest tests/project_utility/test_telemetry_hooks.py -k rebind`。
  - 断言：无事件 5 分钟触发 `verify_summary_hook`，hook 状态更新。
  - 前端预期：Dashboard yellow banner。
  - 后端预期：`INFO telemetry.hook.rebind`。
  - 工具：pytest, time freeze。
- `S1-D6-INTEG`：停 telemetry agent。
  - 命令：`kubectl scale deploy telemetry-agent --replicas=0 && pytest tests/integration/test_telemetry_gap.py`。
  - 断言：Grafana Alert 触发；恢复后 `workflow.summary.persisted` 速率回升。
  - 前端预期：Monitoring UI 提示恢复。
  - 后端预期：SSE backlog 重放。
  - 工具：kubectl, Grafana API。
- `S1-D6-E2E`：SRE 手动演练。
  - 步骤：在 Stage 环境拉闸 telemetry，再 `kubectl rollout restart`。
  - 断言：WorkLog 记录；alert 关闭；OPS 验证 via Slack。
  - 工具：Ops runbook。

#### S1-D7 人工操作：历史摘要回放
- `S1-D7-UNIT`：`ReplaySummaries` service 单测。
  - 命令：`pytest tests/business_service/test_replay_summaries.py`。
  - 断言：Mongo 游标→Redis 写→Telemetry `manual_replay=true`。
  - 前端预期：API 200 + 进度字段。
  - 后端预期：Redis recount=Mongo 条数。
  - 工具：pytest。
- `S1-D7-INTEG`：Admin API `POST /workflows/replay`。
  - 命令：`newman run tests/e2e/workflow_replay.postman_collection.json`。
  - 断言：CSV 导出含 30 rows；`AUDIT workflow.summary.replay` 记录。
  - 前端预期：Up Admin 进度条走完。
  - 后端预期：Redis TTL 重置。
  - 工具：Newman, CSV diff。
- `S1-D7-E2E`：稽核演练。
  - 步骤：稽核登录 Up Admin，执行 replay，下载 CSV。
  - 证据：Chrome DevTools MCP 录制点击 `workflowReplayButton`，`list_network_requests` 捕获 `/replay` 200；`get_network_request` 保存响应。
  - 断言：人工对照稽核清单。

#### S1-D8 业务特殊：菲律宾数据驻留
- `S1-D8-UNIT`：`gov_audit_bridge` 入队单测。
  - 命令：`pytest tests/foundational_service/test_gov_audit_bridge.py`。
  - 断言：`user_country=PH`→enqueue→`INFO workflow.summary.audit_dispatch`。
  - 前端预期：API payload 增 `govAuditStatus=pending`。
  - 后端预期：`gov_audit_queue` message。
  - 工具：pytest, fakeredis, fake queue。
- `S1-D8-INTEG`：`gov_audit_queue` + backlog。
  - 命令：`pytest tests/integration/test_gov_audit_flow.py`。
  - 断言：Government endpoint down → backlog metric >0 → 邮件 mock。
  - 前端预期：UI 显示“PH audit pending/complete”。
  - 后端预期：SLA 监控 tracer。
  - 工具：pytest, smtp mock。
- `S1-D8-E2E`：合规联调。
  - 步骤：生产前在 staging 将 `user_country=PH` 测试案例运行；导出 backlog 上传政府门户（手动）。
  - 断言：Gov 门户确认；`gov_audit_queue` 清零；Email 归档。
### S2 Telegram 会话入口去耦
#### S2-D1 核心功能：同步/异步入口
- `S2-D1-UNIT`：`TelegramEntryConfig` + `RuntimeGateway` 单测（aiogram）。命令：`pytest tests/business_service/conversation/test_runtime_gateway.py -k mode_switch`；断言 sync→orchestrator 调用一次，async 返回 `AsyncResultHandle`。
- `S2-D1-INTEG`：`pytest tests/integration/test_telegram_entry_modes.py`，通过 aiogram webhook + Mockoon 发送 update，断言 ack 含 task_id、Redis health 更新。依赖 CTX-AIOGRAM-3.22。
- `S2-D1-E2E`：Telegram Bot 实测：Chrome DevTools MCP 记录 Up Admin 触发 mode 切换/API `/channel-policy` save；Telegram 客户端手发消息，验证同步结果或 async 提示。

#### S2-D2 性能/容量：高并发排队
- `S2-D2-UNIT`：`PriorityQueue` + `sticky_session_map` 单测，命令 `pytest tests/business_service/conversation/test_queue_backpressure.py`，断言 500 QPS 分区正确。
- `S2-D2-INTEG`：`locust -f tests/load/telegram_queue.py --users 500 --spawn-rate 50`；断言 queue 深度指标、`WARN telegram.entry.queue_backpressure` 日志、PagerDuty mock。
- `S2-D2-E2E`：运营演练：ngrok 接入真实 Telegram，群发脚本 `python tools/telegram_spam.py --count 500`，观察 ack ETA、Slack 提示。

#### S2-D3 安全/权限：签名校验
- `S2-D3-UNIT`：接口层缺失 `X-Telegram-Bot-Api-Secret-Token` 单测；命令 `pytest tests/interface_entry/test_telegram_signature.py`。
- `S2-D3-INTEG`：`newman run tests/e2e/telegram_signature.postman_collection.json`，断言 HTTP 403 + 安全日志字段。
- `S2-D3-E2E`：真实 webhook rotate：使用 Chrome DevTools MCP 记录 Up Admin Channel Tab 保存新 secret，RabbitMQ 观察事件；发送伪造请求确认被拒。

#### S2-D4 数据一致性：pending receipts
- `S2-D4-UNIT`：`pending_receipts` 心跳单测，命令 `pytest tests/business_service/conversation/test_pending_receipts.py`。
- `S2-D4-INTEG`：杀死 worker 模拟崩溃：`kubectl delete pod telegram-worker-0` 后运行 `pytest tests/integration/test_pending_retry.py`，断言重新入列、邮件通知。
- `S2-D4-E2E`：Ops 手动 `dead_letter_queue` 检查，脚本 `python tools/telegram_dlx_report.py`，对照用户通知。

#### S2-D5 防御/降级：依赖不可达
- `S2-D5-UNIT`：`local_fallback_queue` 单测 `pytest tests/business_service/conversation/test_degraded_mode.py`。
- `S2-D5-INTEG`：关闭 RabbitMQ → `pytest tests/integration/test_local_queue_fill.py`，断言告警 + `degraded_flag=true`。
- `S2-D5-E2E`：维护窗口拉闸外部依赖，操作 `diagnose_runtime.ps1`，Chrome DevTools MCP 记录 Up Admin health banner；恢复后 `flush local_queue`。

#### S2-D6 观察性：Channel Health 心跳
- `S2-D6-UNIT`：`ChannelHealthReporter` 单测，命令 `pytest tests/business_service/conversation/test_channel_health.py`。
- `S2-D6-INTEG`：`pytest tests/integration/test_channel_health_sse.py` 订阅 Redis key & SSE，断言 30s 更新；Grafana 阈值报警。
- `S2-D6-E2E`：Up Admin Channel Tab 观察灯色，Chrome DevTools MCP `take_snapshot` 记录 UI，`list_network_requests` 捕获 `/api/channels/<id>/health` 请求。

#### S2-D7 人工操作：手动排空/暂停
- `S2-D7-UNIT`：store flag 单测 `pytest tests/business_service/conversation/test_pause_resume.py`。
- `S2-D7-INTEG`：调用 Admin API `POST /channels/pause`（Newman 用例），断言 `channel_paused=true`，队列停止入列。
- `S2-D7-E2E`：运维 runbook：Up Admin 中按 Pause，Chrome DevTools MCP 记录点击+Network；Telegram 自动回复维护文案。

#### S2-D8 业务特殊：菲律宾节假日
- `S2-D8-UNIT`：`ph_holidays` scheduler 单测 `pytest tests/business_service/conversation/test_ph_holiday_mode.py`。
- `S2-D8-INTEG`：模拟假日 JSON，运行 `pytest tests/integration/test_holiday_async_guard.py`，断言 `manual_guard=true`、值班提醒。
- `S2-D8-E2E`：法定假日前演练：Scheduler 强制 set holiday，Chrome DevTools MCP 记录 Channel Tab 切换为 async；运营手动审核 pending。
### S3 渠道策略绑定与健康轮询（Up + Rise）
> 所有 Up Admin 用例：Chrome DevTools MCP 记录 `navigate_page`, `take_snapshot`, `list_network_requests`, `get_network_request`, `list_console_messages`，并保存截图；自动化部分使用 Vitest + Testing Library（CTX-VITEST-4.0.7）。

#### S3-D1 核心功能：策略保存
- `S3-D1-UNIT`：`channelPolicyClient` 单测，命令 `pnpm vitest run --coverage src/services/channelPolicyClient.test.js -t savePolicy`；断言 fetch body/headers（X-Actor-*）。
- `S3-D1-INTEG`：`pnpm vitest run src/stores/channelPolicy.test.js -t save_and_refresh`（带 mocked scheduler）；断言 store 只存状态，轮询由服务触发。
- `S3-D1-E2E`：Chrome DevTools MCP：`navigate_page https://up.local/workflows/:id/channel`→填写表单→`chromedevtools take_snapshot`→`list_network_requests` 检查 `/api/channel-policy` 200→`get_network_request` 保存 payload；核对 UI toast（EN/ZH/TL）。

#### S3-D2 性能/容量：轮询
- `S3-D2-UNIT`：`channelHealthScheduler` 使用 fake timers `pnpm vitest run src/services/channelHealthScheduler.test.js -t polling_backoff`，断言退避/批量测试逻辑。
- `S3-D2-INTEG`：`pnpm vitest run src/stores/channelPolicy.test.js -t health_refresh_high_frequency`，借助 `vi.useFakeTimers()` 模拟高频轮询并确认 cooldownMap 生效。
- `S3-D2-E2E`：Chrome DevTools MCP + Playwright：运行 `pnpm vitest browser --config vitest.browser.config.ts -t channel_health_stream`，Chromium 中记录 FPS；手动 `chromedevtools list_network_requests` 确认 SSE/REST 调用间隔符合配置。

#### S3-D3 安全/权限：越权
defense
- `S3-D3-UNIT`：Pinia 权限守卫单测，命令 `pnpm vitest run src/stores/channelPolicy.test.js -t deny_without_role`，断言 store 抛错 + state 不变。
- `S3-D3-INTEG`：`pnpm vitest run src/views/WorkflowBuilder.test.js -t channel_tab_guard`，mock Router+roles。
- `S3-D3-E2E`：Chrome DevTools MCP 以 Viewer 账号访问 Channel Tab，记录 403 network & `SEC workflow.builder.log_denied`；Telegram 侧 verify 无越权写。

#### S3-D4 数据一致性：前端缓存 vs 后端版本
- `S3-D4-UNIT`：`usePolicyVersion` composable 单测 `pnpm vitest run src/composables/policyVersion.test.js`。
- `S3-D4-INTEG`：`pnpm vitest run src/services/channelPolicyClient.test.js -t version_conflict`，mock SSE `channelPolicy.updated`。
- `S3-D4-E2E`：Chrome DevTools MCP 打开两个浏览器实例，A 保存策略，B 观察冲突提示；`get_network_request` 验证 `/channel-policy/version` 响应。

#### S3-D5 防御/降级：健康 API 不可用
- `S3-D5-UNIT`：scheduler fallback 单测 `pnpm vitest run src/services/channelHealthScheduler.test.js -t fallback_to_snapshot`。
- `S3-D5-INTEG`：Mock API 500，`pnpm vitest run src/views/ChannelTab.test.js -t health_api_downtime`，断言 UI 黄色提示。
- `S3-D5-E2E`：Chrome DevTools MCP 录制 fail 请求→`list_console_messages`（warning）→Ops Slack 截图；后台 `channel.health.snapshot` 事件存在。

#### S3-D6 观察性/运维：指标 & 告警
- `S3-D6-UNIT`：Telemetry helper 单测 `pnpm vitest run src/services/telemetryClient.test.js -t channel_metrics`。
- `S3-D6-INTEG`：`pnpm vitest run src/views/ChannelTab.test.js -t telemetry_emit_on_save`，断言 `telemetry.send('channel.policy.save', ...)`。
- `S3-D6-E2E`：Chrome DevTools MCP + Grafana：保存策略→Grafana dashboard capture `channel_policy_change_total`；`list_network_requests` 确认 `/telemetry` 请求。

#### S3-D7 人工操作：策略回滚
- `S3-D7-UNIT`：`channelPolicy.store.rollback` 单测 `pnpm vitest run src/stores/channelPolicy.test.js -t rollback_snapshot`。
- `S3-D7-INTEG`：`pnpm vitest run src/services/channelPolicyClient.test.js -t rollback_api` 调用 `/channel-policy/:id/rollback`。
- `S3-D7-E2E`：Chrome DevTools MCP 录制回滚流程（点击历史版本→确认），验证 UI Banner “rolled back”；`list_network_requests` 查看 POST /rollback 200。

#### S3-D8 业务特殊：渠道合规文案
- `S3-D8-UNIT`：`copywriting.yaml` 校验脚本 `pnpm vitest run src/utils/copywritingValidator.test.js`，确保 EN/TL/中文存量。
- `S3-D8-INTEG`：`pnpm vitest run src/views/ChannelTab.test.js -t bilingual_prompt_required` 阻止保存缺字文案。
- `S3-D8-E2E`：Chrome DevTools MCP 录制 Channel Tab 保存 Telegram 文案→`take_snapshot` 验证 copy preview，`list_network_requests` 记录 payload；稽核导出 `copywriting.yaml` 变更。
### S4 Workflow Builder 控制器
#### S4-D1 核心功能：加载→编辑→发布
- `S4-D1-UNIT`：`useWorkflowBuilderController` 单测 `pnpm vitest run src/composables/useWorkflowBuilderController.test.js -t load_save_publish`，mock stores/SSE。
- `S4-D1-INTEG`：`pnpm vitest run src/views/WorkflowBuilder.test.js -t publish_flow`，确保 store 仅状态，controller 负责 side-effect。
- `S4-D1-E2E`：Chrome DevTools MCP（浏览器 A）执行完整编辑→发布→`beforeRouteLeave`；`list_network_requests` 验证 `/publish` 200；`list_console_messages` 确认无残余订阅。

#### S4-D2 性能/容量：SSE + 大型 Workflow
- `S4-D2-UNIT`：virtual list & buffer 单测 `pnpm vitest run src/components/WorkflowCanvas.test.js -t high_volume_virtualization`。
- `S4-D2-INTEG`：`pnpm vitest browser --testNamePattern "SSE buffer"`，Playwright Chromium 记录 FPS，断言控制器切分页/高容量提示。
- `S4-D2-E2E`：Chrome DevTools MCP `performance_start_trace` + `emulate_network Fast 3G`，确认 SSE 退避、UI banner“Large workflow...”。

#### S4-D3 安全/权限：日志越权
- `S4-D3-UNIT`：权限 guard 单测 `pnpm vitest run src/stores/workflowDraft.test.js -t deny_log_tab`。
- `S4-D3-INTEG`：`pnpm vitest run src/views/WorkflowBuilder.test.js -t log_tab_role_guard`，mock permissions。
- `S4-D3-E2E`：Chrome DevTools MCP 以 Reviewer 登录，尝试打开日志，确认 403 Network & UI 文案，SIEM 记录 `SEC workflow.builder.log_denied`。

#### S4-D4 数据一致性：并发编辑
- `S4-D4-UNIT`：`workflowDraft` conflict reducer 单测 `pnpm vitest run src/stores/workflowDraft.test.js -t conflict_resolution`。
- `S4-D4-INTEG`：`pnpm vitest run src/services/workflowDraftService.test.js -t sse_version_conflict`，mock SSE 通知。
- `S4-D4-E2E`：两浏览器实例 A/B 同时编辑：Chrome DevTools MCP 记录 Diff 弹窗与 SSE 事件；验证 `INFO workflow.builder.version_conflict`。

#### S4-D5 防御/降级：SSE 断连
- `S4-D5-UNIT`：`pipelineSseClient` 重连单测 `pnpm vitest run src/services/pipelineSseClient.test.js -t exponential_backoff`。
- `S4-D5-INTEG`：断开网络（Playwright `context.setOffline(true)`）运行 `pnpm vitest browser`，断言 fallback polling。
- `S4-D5-E2E`：Chrome DevTools MCP `emulate_network Slow 3G`，观察 “Realtime updates paused” 提示、`WARN workflow.builder.sse_fallback`。

#### S4-D6 观察性：Controller 指标
- `S4-D6-UNIT`：`telemetry.send` hook 单测 `pnpm vitest run src/services/telemetryClient.test.js -t workflow_builder_metrics`。
- `S4-D6-INTEG`：`pnpm vitest run src/views/WorkflowBuilder.test.js -t telemetry_emit`，mock aggregator。
- `S4-D6-E2E`：Chrome DevTools MCP + Grafana capture `workflow_builder_publish_latency`；`list_network_requests` 验证 `/telemetry` 上传。

#### S4-D7 人工操作：紧急开关
- `S4-D7-UNIT`：feature flag reducer 单测 `pnpm vitest run src/stores/workflowDraft.test.js -t freeze_flag`。
- `S4-D7-INTEG`：`pnpm vitest run src/views/WorkflowBuilder.test.js -t freeze_banner`，模拟 flag 打开。
- `S4-D7-E2E`：现场演练：Ops 设置 `freeze_editing=true`（Feature toggle API），Chrome DevTools MCP 录制按钮置灰，邮件通知 teams。

#### S4-D8 业务特殊：多语提示 & 菲律宾法规
- `S4-D8-UNIT`：表单校验单测 `pnpm vitest run src/components/PromptEditor.test.js -t bilingual_required`。
- `S4-D8-INTEG`：`pnpm vitest run src/composables/useWorkflowBuilderController.test.js -t gov_audit_prompt`，断言 controller 拦截缺失文案。
- `S4-D8-E2E`：Chrome DevTools MCP 录制发布流程，故意删除他加禄提示→阻止发布→`list_network_requests` 显示 422；稽核导出 log，验证 Acceptance #5。
## 6. 观察性与指标
| 事件/指标 | 采集方式 | 合格阈值 / 断言 |
| --- | --- | --- |
| `workflow.summary.persisted` 事件 | FastAPI telemetry hook + `redis-cli monitor`；Tests 用 `caplog` 验证。 | 成功率 ≥99%，5 分钟无事件触发 `telemetry.hook.rebind`（S1-D6）。 |
| Redis/Mongo 深度 | `redis-cli llen chat_summary:*`、`mongosh` 查询；Grafana 面板 `queue_depth`, `write_latency_ms`。 | Redis `LLEN` ≤20；Mongo 写延迟 <150ms；Repair queue 深度 <50。 |
| `telegram.entry.*` 指标 | aiogram middleware 发送 SSE；`channel.health` Redis 键 `last_seen/pending/mode`。 | `last_seen` <30s；`queue_depth` <2000；节假日模式下 `manual_guard` ack ≤4h。 |
| Up Admin 前端度量 | `telemetry.send('channel.policy.save', ...)` + `workflow_builder_publish_latency`；Chrome DevTools MCP `performance_start_trace`。 | 发布 latency P95 <2s；SSE reconnect ≤5 次；High volume 模式 FPS ≥30。 |
| Gov Audit backlog | `gov_audit_queue_depth` Prometheus + 邮件。 | backlog <100；若 >100，邮件+导出任务在 24h 内完成。 |
| Alert 通道验证 | PagerDuty/Slack/Teams/SMS 模拟 webhook。 | 模拟事件被接收并可关闭；无误报（S1-D5/S2-D2/S3-D6/S4-D5）。 |
## 7. 执行排期与责任分工
| 顺序 | 关联 Tasks | 内容 | 负责人 | 预计耗时 | 回退/清理 |
| --- | --- | --- | --- | --- | --- |
| 1 | Step-01~04 | Rise Workflow summary unit+integration 套件（S1-D1~D5）。 | 后端 | 6h | `scripts/test-teardown.ps1` + `redis-cli flushdb` + `mongosh drop`。 |
| 2 | Step-05~09 | Telegram entry/health tests（S2 全部）。 | 后端（对接运营） | 8h | `kubectl rollout undo deploy/telegram-worker`，恢复 RabbitMQ/Redis。 |
| 3 | Step-10~13 | Channel policy schema/service/store 测试、Vitest 覆盖（S3）。 | 前端 | 7h | `pnpm vitest --runInBand --coverage false` 清缓存；Chrome DevTools MCP 关闭所有页。 |
| 4 | Step-14~17 | Workflow Builder controller + SSE E2E（S4）。 | 前端 + QA | 8h | 关闭 `freeze_editing` flag；`pnpm vitest --update` 重置快照。 |
| 5 | Step-18 | Cross-scenario E2E（Acceptance 1~5）+ Gov Audit rehearsal。 | QA + 合规 + 运营 | 10h | 数据回滚脚本 + 稽核文档归档。 |
| 6 | Regression | 将自动化用例接入 CI：`pytest`、`pnpm vitest`, `newman`, `locust smoke`。 | QA | 持续 | 失败时回滚到最近成功构建（Git tag），清理临时 env。 |

失败回退原则：任何一环失败即停止后续执行，先用 `git worktree` 切回稳定分支，清理 Redis/Mongo/Mockoon/Chrome 状态，再重启流程。
## 8. 报告与问题单模版
**执行记录表头**（执行阶段自由选择存储路径）：
| 字段 | 说明 |
| --- | --- |
| Date / Timezone | 例如 `2025-11-12 10:00 CST` |
| Environment | Rise commit / Up commit / Telegram bot token (mask) |
| Scenario / Test ID | 如 `S3-D4-INTEG` |
| Result | Pass / Fail / Blocked |
| Evidence | Chrome DevTools MCP log ID、Network reqid、Redis/Mongo 查询、Grafana 截图 |
| Metrics | 关键指标值（latency、queue_depth、FPS） |
| Notes | 数据清洗、人工操作记录 |

**问题单模版**（建议记录在 `AI_WorkSpace/WorkLogs/issues`）：
1. 关联场景 & Test ID。
2. GIVEN/WHEN/THEN（引用 Acceptance 条款）。
3. 期望 vs 实际（含前端/后端视角）。
4. 日志/截图链接（Chrome DevTools MCP log、Prometheus、redis-cli/mongosh 输出）。
5. 影响面评估 + 建议修复任务（引用 Tasks step）。
6. 需要更新的文档（Requirements/DevDoc/notes）。
## 9. 覆盖性检查
| Acceptance | GIVEN/WHEN/THEN | 覆盖 Test ID | 状态 |
| --- | --- | --- | --- |
| 1 Workflow Summary 同步 | GIVEN chat_id & Redis/Mongo；WHEN 执行 workflow；THEN Redis & Mongo 同步 + `workflow.summary.persisted=success`. | `S1-D1-UNIT/INTEG/E2E`, `S1-D4-*`, `S1-D5-*`, `S1-D8-*`. | ✅ |
| 2 Conversation Gateway Async Ack | GIVEN async ack；WHEN Telegram update 触发；THEN Gateway 返回任务 ID 且 Service 不直接触达 runtime factory。 | `S2-D1-*`, `S2-D2-*`, `S2-D5-*`, `S2-D8-*`. | ✅ |
| 3 Channel Policy Store 专责 | GIVEN Workflow 已发布；WHEN 打开 Channel Tab；THEN Store 仅状态，轮询受 scheduler 控制。 | `S3-D1-*`, `S3-D2-*`, `S3-D3-*`, `S3-D5-*`. | ✅ |
| 4 Workflow Builder Controller 清理 | GIVEN 离开页面；WHEN beforeRouteLeave；THEN controller 停止轮询/SSE。 | `S4-D1-*`, `S4-D5-*`. | ✅ |
| 5 Regulation (PH & 文案) | GIVEN `user_country=PH` 或渠道测试；WHEN 产生 summary/测试；THEN 文案含 EN/TL 且 `gov_audit_queue` 接收任务。 | `S1-D8-*`, `S3-D8-*`, `S4-D8-*`. | ✅ |

**未覆盖清单**：无（S1~S4 × D1~D8 三层用例已列）。如未来新增渠道（SMS/Email），需复制 S3/S4 模式扩展。
## 10. References
1. `AI_WorkSpace/Requirements/session_20251112_0014_violation_alignment.md` – 场景与 Acceptance 定义。
2. `AI_WorkSpace/DevDoc/On/session_20251112_0125_violation_alignment_tech.md` – 模块矩阵与技术约束。
3. `AI_WorkSpace/Tasks/session_20251112_min_steps.md` – Step-01~18 验证入口。
4. `AI_WorkSpace/notes/session_20251112_0125_violation_alignment_tech.md` – Context7/Exa 参考登记。
5. `AI_WorkSpace/notes/session_20251111_2135_repo_index.md` – Index 导航 & 目录层级。
6. `AI_WorkSpace/PROJECT_STRUCTURE.md` – Clean Architecture 分层。
7. CTX-FASTAPI-0.118.2 – FastAPI 依赖注入 & lifespan 测试指南。
8. CTX-VITEST-4.0.7 – Vitest 覆盖与浏览器模式最佳实践。
9. CTX-CDP-MCP – Chrome DevTools MCP 工具调用与网络/性能录制。
10. CTX-AIOGRAM-3.22 – aiogram webhook/timeout/background handler 规范。
11. CTX-REDIS-PY-6.4.0 – Redis 连接、pipeline、测试命令。
12. CTX-PYMONGO-DRIVER – PyMongo 事务/会话验证。
13. EXA-FASTAPI-TESTING – FastAPI API 测试流程（Postman/Newman）。
14. EXA-DEVTOOLS-MCP – Chrome DevTools MCP 官方贴士与 AI 自动化指南。
15. EXA-TELEGRAM-MOCK – Mockoon Telegram Bot API 样例。
