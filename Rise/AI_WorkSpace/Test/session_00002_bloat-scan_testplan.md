# Rise / Up / Telegram 臃肿治理 – 端到端验证计划（session_00002_bloat-scan）

## 封面
- **范围**：验证场景 A~I 及八大维度在 Rise（FastAPI + aiogram）、Up Admin（Vue3 + Vite + Pinia）、Telegram 渠道间的真实互锁行为。
- **来源**：`AI_WorkSpace/Requirements/session_00002_bloat-scan.md`、`AI_WorkSpace/notes/session_00002_bloat-scan.md`、`AI_WorkSpace/index.yaml`、`PROJECT_STRUCTURE.md`。
- **State Lock**：`sequence.current.id = 00002`（锁定 true），Test plan 首次创建（目录检查已记录于 notes）。
- **参考**：Context7#2 `/websites/benavlabs_github_io_fastapi-boilerplate`（FastAPI 测试结构），Exa#5 `alex-jacobs.com/posts/fastapitests`（FastAPI 集成测试），Exa#6 `testdriven.io/courses/tdd-fastapi/intro`（FastAPI + Docker TDD）。

## 环境矩阵
| 平台 | 启动模式 | 必备变量/依赖 | 与生产差异 | 工具 |
| --- | --- | --- | --- | --- |
| Rise Backend | `uvicorn src.interface_entry.bootstrap.app:app --reload` 或 `docker compose up api redis mongo` | `.env`（TELEGRAM_BOT_TOKEN、REDIS_URL、MONGODB_URI、RABBITMQ_URL）、Redis7、Mongo7、RabbitMQ、aiogram webhook stub | 仅日志级别为 DEBUG，其余配置与 prod 等同；可切至 staging redis/mongo | `pytest`, `uvicorn`, `docker compose`, `redis-cli`, `mongosh`, aiogram stubs |
| Up Admin | `pnpm install && pnpm dev --host 0.0.0.0 --port 5173`；E2E 通过 Chrome DevTools MCP 驱动 | `.env.development` 配置 `VITE_API_BASE_URL` 指向 Rise；`VITE_ENABLE_OBSERVABILITY=true` | Dev server 无 CDN；Feature Flag 可被脚本切换；接口相同 | `pnpm vitest`, `mcp__chrome-devtools`, Playwright 备选 |
| Telegram | 真 Bot API + 公网 webhook，或 `mock-telegram-gateway`（aiogram stub） | 真实模式需 Ops 提供 token、ngrok/Cloudflare tunnel；mock 模式需 aiogram stub | Mock 仅覆盖 Rise 行为；至少一次回归使用真 Telegram 验证 TLS/速率 | `python tests/tools/telegram_e2e.py`, `curl https://api.telegram.org/...`, ngrok |
| Observability & 工具 | Redis/Mongo 命名空间、Chrome DevTools trace、SSE 监听器、Prometheus `/metrics`、PagerDuty/Slack sandbox、Ops Matrix (`Step-11_ops_matrix.ps1`) | 使用 `session_00002` 前缀隔离；Chrome DevTools 需保持登录态；Prometheus 若无部署则用 uvicorn stats 备用；Ops Matrix 脚本串联 binding refresh/telemetry/workspace nav 并推送 Slack/PagerDuty sandbox | 与生产一致，仅限命名空间 | `redis-cli`, `mongosh`, `curl`, `kubectl logs`, `promtool`, `pwsh Step-11_ops_matrix.ps1` |

## 数据 & 夹具策略
- **Rise**：pytest fixtures 在 `tests/conftest.py` 中注入 redis/mongo 空间；执行 `scripts/reset_test_data.py --namespace session_00002` 做清理；TaskEnvelope 使用 faker 固定字段；Binding snapshot 从 `tests/fixtures/binding_snapshot.json` 注入。
- **Up**：Vitest 启动 `tests/setup/vitest.setup.js` 模拟 actor headers；Chrome DevTools E2E 操作真实 UI，保存 payload 与 SSE 证据；测试后调用 `/api/workflows/{id}` DELETE 清理；截图/HAR 存于 `AI_WorkSpace/TestArtifacts/session_00002/`。
- **Telegram**：`tests/tools/telegram_e2e.py` 支持 `--mode mock` 与 `--mode real`；真实模式需登记 token 并在 24h 内清理消息；mock 模式使用 aiogram stub。
- **凭证管理**：Telegram token、PagerDuty key、Slack webhook 在 `.env.test` 中注入；执行后立即吊销；敏感信息不得写入 git。
- **防污染**：Redis/Mongo key 加 `session_00002` 前缀；Up 侧 workflow/channel 命名 `E2E-00002-<testid>`；Telegram 真号对话手动删除记录。

## 场景/维度 → 测试 ID 映射（节选）
| 场景 | 维度 | Test ID | 验收关联 |
| --- | --- | --- | --- |
| A Conversation Runtime | D1 核心流程 | `S1-D1-TEST` | Telegram webhook → ContextFactory/Binding/Guard/Enqueue/Response 全链路；对应 Acceptance#1A |
| A | D2 性能容量 | `S1-D2-TEST` | 压测 300 RPS，指标 `binding.refresh.latency_ms < 150`；Acceptance 场景A性能条款 |
| A | D3 安全权限 | `S1-D3-TEST` | 伪造 header → 403 + telemetry `security.signature_fail`；规则#3 |
| A | D4 数据一致性 | `S1-D4-TEST` | 重放 webhook → Redis 无重复任务；Acceptance “幂等性” |
| A | D5 防御降级 | `S1-D5-TEST` | Redis 队列满 → guard fallback + ack `workflow_locked`；异常矩阵“资源枯竭” |
| A | D6 观测 & Ops | `S1-D6-TEST` | 检查 `conversation.guard.reject` 事件 & 指标 |
| A | D7 运维 | `S1-D7-TEST` | 执行 binding refresh runbook + Up 同步 |
| A | D8 业务变体 | `S1-D8-TEST` | locale=zh/en 的 ack 文案切换 |
| B FastAPI 启动/探针 | D1 | `S2-D1-TEST` | 启动 + probes 输出 `/healthz` snapshot；Acceptance#B1 |
| … | … | … | 其余场景 B~I 及 D1~D8 在附录矩阵列出共 72 个 Test ID |

（附录A：全矩阵详表；附录B：Acceptance 对应关系。）

## 实测路径设计
### Rise Backend
- **Unit/Service（P1 自动化）**：`pytest tests/business_service/conversation/test_context_factory.py::test_binding_snapshot_merge`、`pytest tests/foundational_service/test_capability_snapshot.py`、`pytest tests/business_service/workflow/test_repository_mixins.py`。
- **Integration（P0 自动化）**：`pytest tests/integration/test_conversation_pipeline.py -k telegram_webhook_flow`；`pytest tests/integration/test_health_probes.py`；`pytest tests/integration/test_telemetry_bus.py`。
- **E2E（P0 混合）**：`scripts/e2e/run_webhook_flow.sh`、`scripts/e2e/run_binding_refresh.sh`、`scripts/e2e/run_health_failover.sh`。

### Up Admin
- **Unit**：`pnpm vitest run WorkflowEditor.spec.ts`、`ChannelCredentialCard.spec.ts`。
- **Integration**：`pnpm vitest run useWorkflowBuilderController.spec.ts`、`ChannelFormShell.spec.ts`。
- **E2E**：Chrome DevTools MCP 脚本 `tests/e2e/channel_form_v2.json`、`tests/e2e/pipeline_workspace_v2.json`。

### Telegram
- **Mock**：`python tests/tools/telegram_e2e.py --mode mock --payload fixtures/telegram_update.json`。
- **真实**：手动发送消息至测试 Bot；记录 message_id；核对 Rise 日志、Up LogStream、Bot 回应。

## 工具 & 命令
- Rise：`pytest`, `docker compose -f docker-compose.test.yml up`, `redis-cli`, `mongosh`, `python scripts/refresh_binding.py`。
- Up：`pnpm vitest`, `mcp__chrome-devtools__take_snapshot`, `pnpm dev`。
- Telegram：`python tests/tools/telegram_e2e.py`, `curl https://api.telegram.org/bot$TOKEN/setWebhook`。
- Observability：`curl http://localhost:8000/metrics`, `kubectl logs deployment/rise-api`, `python scripts/fetch_sse.py`，`pwsh AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-11_ops_matrix.ps1 --env staging --workflow wf-demo`。
- 告警演练：`python scripts/pagerduty_test_event.py --routing-key <key> --description "guard reject drill"`，或通过 `Step-11_ops_matrix.ps1` 触发 Slack/PagerDuty sandbox，验证 webhook/Events API 链路。

## 观测与告警验证
- **事件**：`channel.binding.refresh_*`, `conversation.guard.reject`, `workflow.version.published`, `channel.form.validation_failed`, `telemetry.console.mirror_rotated`。
- **指标**：`binding_refresh_latency_seconds`, `conversation_guard_reject_total`, `workflow_save_conflict_total`；使用 `promtool` 或 `curl`+jq。 
- **日志**：`uvicorn` 控制台或 `kubectl logs`，关键字 `workflow_locked`, `binding_snapshot_corrupt`。
- **告警**：PagerDuty sandbox、Slack #rise-ops；需截图/链接佐证。

## 执行计划
1. 准备阶段：Ops 提供 token、搭建依赖、开启 Observability。
2. Backend 阶段：Unit/Integration（8h SLA）。
3. Frontend 阶段：Vitest + Chrome DevTools（6h）。
4. 联合 E2E：真实 Telegram + Up + Rise（2 天）。
5. Observability/告警：Ops 演练。
6. 收尾：汇总报告、Go/No-Go。

角色：Backend（Rise）、Frontend（Up）、Ops（基础设施+告警）、QA（统筹）。故障：Sev-1 立即停测并执行 runbook。

## 报告模板
- 执行记录：日期、环境、Test ID、命令、证据链接、结果、负责人、备注 → `AI_WorkSpace/TestReports/session_00002_bloat-scan_validation.md`。
- 缺陷单：Test ID、Scenario、Expected、Actual、Evidence、Impact、Proposed Fix、Owner、Due → 内部 issue tracker。

## 覆盖与风险
- 72 个 Test ID 覆盖 9 场景×8 维度；多区域部署不在 scope（默认单区域）。
- 风险：Telegram token 审批、Chrome 脚本依赖 selector、Redis/Mongo 共享、Prometheus 缺席；已提供缓解策略。

## 参考
- Context7#2 `/websites/benavlabs_github_io_fastapi-boilerplate`
- Exa#5 https://alex-jacobs.com/posts/fastapitests/
- Exa#6 https://testdriven.io/courses/tdd-fastapi/intro
