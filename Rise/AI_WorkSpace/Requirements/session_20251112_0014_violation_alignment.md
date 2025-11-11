# Rise + Up 违规整改业务需求（session_20251112_0014_violation_alignment）

## Background
- 违规基线：依据 `D:\AI_Projects\.codex\prompts\WriteRise.md` 第 52-55 行的 4 类违规与第 143-154 行的处理要求，Rise/Up 需拆解入口层超载、业务逻辑直连基础设施以及 Store 过载等问题，保证“功能不变，仅结构重排”。
- Clean Architecture 最新实践强调“请求路由→服务→仓储”逐层分离，业务规则驻留在 Use Case 层，由外圈（接口/基础设施）依赖内圈，而不是反向依赖。citeturn0search1turn0search2
- Pinia 社区在 2025 年的讨论中再次确认：Store 负责跨组件共享状态，复杂副作用/网络调用适合放入独立 composable 或服务模块，从而避免状态层被业务逻辑淹没。citeturn0reddit12
- 现状：Rise 侧 `interface_entry/bootstrap/application_builder.py`、`business_logic/workflow/orchestrator.py`、`business_service/conversation/service.py`；Up 侧 `src/stores/workflowDraft.js`、`src/stores/channelPolicy.js`、`src/views/WorkflowBuilder.vue` 均命中上述违规，需要按层拆分并补齐数据流与验证路径。

## Roles
- **Operator（人）**：在 Up 控制台配置节点/流程/渠道，并发起测试；需要稳定回馈与可见的健康指示。
- **Rise Interface Entry 层（FastAPI + Telegram webhook）**：负责 HTTP/SSE/Telegram 入口，仅做协议适配与依赖注入，不再持有运行时 supervisor 细节。
- **Rise Business Logic 层（Workflow Orchestrator 等）**：协调节点/舞台执行，输出 summary，禁止直接触达 Redis/Mongo，而是经由 Foundational Service repository。
- **Rise Foundational Service 层**：实现持久化与运行时（TaskRuntime、Channel Health、Workflow Summary Repository），对上暴露接口，对下耦合具体存储。
- **Up Admin Store/Controller 层**：Pinia stores 仅存状态 + 轻量 getter；业务流程（轮询/频控/API 调度）迁入 `services/` 与 `composables/`。
- **Observability & Telemetry**：沿用现有 telemetry 事件；重组后需验证 stage 事件、channel health 事件仍然上报。

## Scenarios
### Scenario Index（标记：S1~S4）
- **S1：Workflow 执行与摘要持久化（后端）** — `business_logic/workflow` + `foundational_service/persist`。标签：核心持久化、Redis/Mongo。
- **S2：Telegram 会话入口去耦（后端）** — `business_service/conversation` 拆分 config/runtime/health。标签：入口去耦、异步队列。
- **S3：渠道策略绑定与健康轮询（前端+后端）** — `channelPolicy` store + services + scheduler。标签：Channel 策略、轮询、防抖。
- **S4：Workflow Builder 视图协调（前端）** — `useWorkflowBuilderController`、store 协调、SSE 管理。标签：视图控制器、SSE、路由守卫。

### S1：Workflow 执行与摘要持久化（后端原始描述）
- **触发**：`WorkflowOrchestrator.execute` 接收 `WorkflowExecutionContext`（来源：TelegramFlow 或 HTTP）。
- **预置/前提**：Workflow/Stage 定义已通过 `business_service.workflow` 仓储加载；新建 `business_logic/workflow/models.py` 提供 dataclass；`foundational_service/persist/workflow_summary_repository.py` 提供持久化接口。
- **步骤**：
  1. Orchestrator 仅负责加载 stage → 调用 `behavior_agents_bridge` → 聚合 `WorkflowStageResult`。
  2. 调用注入的 `WorkflowSummaryRepository.append(chat_id, summary_entry)`，该仓储内部串联 Redis `append_chat_summary` + Mongo `chat_history` `$push`。
  3. Telemetry 事件保持 `workflow.stage`，新增 `workflow.summary.persisted`（由仓储发出）。
- **系统反馈**：执行成功返回 `WorkflowRunResult`；持久化异常由仓储捕获并再抛业务异常，供上层决定告警。
- **数据变更**：Redis key `chat_summary:{chat_id}` 追加、TTL 3600；Mongo `chat_history` 文档更新。
- **监控**：Event bus 统计 `workflow.summary.persisted` 成功/失败比；Prometheus 指标或日志计数。

#### S1 子场景扩展
##### S1-D1 核心功能：HTTP 同步执行 + Telegram 异步回写
- **触发条件**：Operator 通过 HTTP API 触发 workflow；或 Telegram update 经 gateway 进入 orchestrator，`WorkflowExecutionContext.channel in {HTTP, TELEGRAM}`。
- **步骤序列**：
  1. Interface Entry 将 HTTP/TG payload 正规化 → 注入 orchestrator。
  2. Orchestrator 串行执行 stage，期间通过 `behavior_agents_bridge` 调用 OpenAI SDK。
  3. 最后调用 repository 同步写 Redis（`LPUSH`）、异步 `asyncio.to_thread` 写 Mongo。
  4. 返回结果及 summary id。
- **资源与状态**：Redis list 缓存最新 20 条；Mongo `chat_history` `summary_entries` 数组；`WorkflowRunResult` 保留在内存直至响应发出。
- **输出与反馈**：HTTP 200 + `result_id`；Telegram 同步路径直接回推文本，异步路径发送 ack 后由 outbound worker 回写。
- **用户提示**：Telegram-EN 成功：“Workflow completed. Summary ID: {id}.”；Telegram-TL 失败：“Nabigo ang pag-save ng buod. Subukan muli o hintayin ang abiso。”；HTTP 降级：`{"status":"partial","message":"Summary queued for retry"}`。
- **系统日志/事件**：`INFO workflow.summary.persisted`（字段：`chat_id`, `stages`, `redis_seq`, `mongo_ack`）。
- **告警/通知**：PagerDuty「Workflow Summary Persist Failure」在 `mongo_ack=false ∧ retry_count>=3` 时触发。
- **人工处理指引**：Site Ops 使用 `workflow_summary_repository.replay(chat_id)` 回放并比对 Redis/Mongo 行数。

##### S1-D2 性能/容量：高并发 200 rps 写入
- **触发条件**：多源渠道高峰期持续 200 rps；Redis/Mongo 已开启副本集。
- **步骤序列**：
  1. Orchestrator 将 summary 写入 `SummaryWriteQueue`。
  2. Repository worker 批量 `pipeline` 写 Redis，再批量写 Mongo。
  3. Mongo 延迟 >150 ms 时切换 `bulk_writer` 并记录延迟标签。
- **资源与状态**：`SummaryWriteQueue`、`redis_conn_pool`、Mongo 连接池 50→80。
- **输出与反馈**：成功返回 `202 Accepted` + `summaryWriteMode=BATCH`；排队 >2s 返回 `429`。
- **用户提示**：UI toast “System busy, summaries queued (ETA 2s).”；Telegram “Processing high load, please wait.”；降级文本 “Summary stored in cache only; archive pending.”。
- **系统日志/事件**：`WARN workflow.summary.backpressure`（字段：`queue_depth`, `avg_latency_ms`）。
- **告警/通知**：Grafana alert「Workflow Summary Queue Depth」≥500 持续 1 min → Slack `#rise-ops`。
- **人工处理指引**：运行 `scripts/redis/scale_pool.ps1` 或 `mongo --eval 'db.chat_history.reIndex()'`，必要时限流部分渠道。

##### S1-D3 安全/权限：未授权 workflow 请求
- **触发条件**：API 请求缺少 `X-Actor-Id` 或 token 无 `workflow:write` scope。
- **步骤序列**：FastAPI dependency 校验 JWT → 失败则短路 orchestrator → Telemetry 记录 `auth_failed`。
- **资源与状态**：仅记录审计日志。
- **输出与反馈**：HTTP 403；Telegram 返回 “Operator token invalid”。
- **用户提示**：EN/TL/ZH 多语言拒绝文案。
- **系统日志/事件**：`SECURITY workflow.execute.denied`（`actor_id`, `scope`, `source_ip`）。
- **告警/通知**：SIEM 连续 10 次 403 触发邮件。
- **人工处理指引**：安全团队补发正确 scope 或停用 Token。

##### S1-D4 数据一致性：Redis/Mongo 双写差异
- **触发条件**：Mongo 写成功但 Redis 连接中断，或反之。
- **步骤序列**：Repository 标记 `half_persisted` → 写入 `consistency_repair_queue` → 定时 job 补写缺失存储。
- **资源与状态**：`consistency_repair_queue`（Redis stream）、`repair_job`。
- **输出与反馈**：业务结果附 `summary_consistency="REPAIRING"`。
- **用户提示**：Operator UI Banner “Summary stored but cross-store sync pending”。
- **系统日志/事件**：`ERROR workflow.summary.consistency_gap`。
- **告警/通知**：Opsgenie 当 repair queue 深度 >50。
- **人工处理指引**：运行 `python tools/repair_summary.py --chat-id ...`，比对 Redis/Mongo 条数一致。

##### S1-D5 防御/降级：Redis 停机仅写 Mongo
- **触发条件**：Redis endpoint 不健康。
- **步骤序列**：Repository 读取 flag `summary_write_mode=MONGO_ONLY` → 仅写 Mongo → 产生日志 `workflow.summary.degraded`。
- **资源与状态**：Mongo 单写、Config flag。
- **输出与反馈**：提示“summary archived, realtime feed unavailable”。
- **用户提示**：EN “Realtime recap paused; archive copy saved.”；TL “Pansamantalang naka-pause ang realtime recap.”。
- **系统日志/事件**：`WARN workflow.summary.degraded`。
- **告警/通知**：Teams + SMS 值班。
- **人工处理指引**：排查 Redis，恢复后重置 flag 并抽检 5 条 summary。

##### S1-D6 观察性/运维：Telemetry 丢失
- **触发条件**：`workflow.summary.persisted` 5 分钟内无事件。
- **步骤序列**：Telemetry agent 检测 counter 下降 → 调 `verify_summary_hook()` → 重新绑定 hook → 写恢复日志。
- **资源与状态**：`telemetry_hooks_registry`、`wf_summary_events_total`。
- **输出与反馈**：Operator Dashboard 黄色提示。
- **用户提示**：“Summary telemetry delayed; data replaying.”。
- **系统日志/事件**：`INFO telemetry.hook.rebind`。
- **告警/通知**：Grafana alert 5 m 无事件触发。
- **人工处理指引**：SRE `kubectl rollout restart` telemetry pod，确认事件恢复。

##### S1-D7 人工操作/配置管理：回放历史摘要
- **触发条件**：稽核要求重放 30 天摘要。
- **步骤序列**：Admin Panel 触发 `ReplaySummaries` → Service 读取 Mongo 写 Redis → Telemetry 记录 `manual_replay=true`。
- **资源与状态**：Mongo 游标、Redis 暂存、`replay_job_status`。
- **输出与反馈**：进度条 + CSV 导出。
- **用户提示**：“Replay completed (30 records).”/“Replay stopped at entry 12.”。
- **系统日志/事件**：`AUDIT workflow.summary.replay`。
- **告警/通知**：无。
- **人工处理指引**：与稽核清单对照后归档。

##### S1-D8 业务特殊：菲律宾数据驻留/法规
- **触发条件**：`user_country=PH` 且含个人信息。
- **步骤序列**：Orchestrator 标记 `requires_gov_mirror=true` → Repository 写 Redis/Mongo 后调用 `gov_audit_bridge.enqueue` → 政府节点不可用则记录 backlog。
- **资源与状态**：`gov_audit_queue`、`audit_backlog_metrics`。
- **输出与反馈**：Operator UI 显示“PH audit pending/complete”。
- **用户提示**：Telegram 附“Data stored per PH BI policy.”。
- **系统日志/事件**：`INFO workflow.summary.audit_dispatch`。
- **告警/通知**：Backlog >100 → 邮件至合规。
- **人工处理指引**：合规专员导出 backlog 并上传政府门户。

### S2：Telegram 会话入口去耦（后端原始描述）
- **触发**：`TelegramConversationService.handle_update` 接收 Telegram update。
- **新模块**：`business_service/conversation/config.py`（dataclass）、`business_service/conversation/runtime_gateway.py`（TaskRuntime/TaskSubmitter）、`business_service/conversation/health.py`（Channel health）。
- **步骤**：Config 输出提示语 → Gateway 入队/监听 → Health 更新状态。
- **业务规则**：Service 仅 orchestrate inbound→workflow→outbound。
- **返回**：同步模式返回 workflow 输出；异步模式返回 Ack 文案。
- **数据**：队列入列记录，health store 写入 Redis。

#### S2 子场景扩展
##### S2-D1 核心功能：同步/异步入口切换
- **触发条件**：Telegram update 携带文本/回调，config `mode in {sync, async}`。
- **步骤序列**：Config 解析 → Runtime Gateway 判定模式 → 同步调 orchestrator 或异步返回 `AsyncResultHandle`。
- **资源与状态**：`TelegramEntryConfig` cache、`TaskRuntimeQueue`、Redis health。
- **输出与反馈**：同步返回结果，异步返回 ack + `task_id`。
- **用户提示**：EN “Here is your answer”；TL 失败 “Hindi kumpleto ang request”；降级 “Channel switched to async due to load”。
- **系统日志/事件**：`INFO telegram.entry.dispatch`。
- **告警/通知**：`telegram_entry_sync_latency_p95>2s` → Slack。
- **人工处理指引**：Operator 在 Admin Panel 切至 async 并观察健康灯。

##### S2-D2 性能/容量：高并发排队 + 粘性会话
- **触发条件**：频道宣讲，瞬间 500 QPS。
- **步骤序列**：Gateway 基于 `chat_id` 分区 → `PriorityQueue` 保序 → 队列 >1000 启第二 worker。
- **资源与状态**：RabbitMQ/Redis stream、`sticky_session_map`。
- **输出与反馈**：Ack 包含 ETA，超时提示排队。
- **用户提示**：“Queue busy, estimated wait {eta}s”；降级 “We'll notify you once processed”。
- **系统日志/事件**：`WARN telegram.entry.queue_backpressure`。
- **告警/通知**：PagerDuty queue_depth>2000。
- **人工处理指引**：扩 worker 或临时关闭低优先级 channel。

##### S2-D3 安全/权限：Telegram 签名校验失败
- **触发条件**：Webhook 缺少/错误 `X-Telegram-Bot-Api-Secret-Token`。
- **步骤序列**：Interface 校验 → 失败直接 403 → 记 `security.telegram.signature_failed`。
- **资源与状态**：`secret_token_cache`。
- **输出与反馈**：HTTP 403；用户不可见。
- **用户提示**：无。
- **系统日志/事件**：安全日志含 `ip`, `token_hash`, `bot_username`。
- **告警/通知**：SIEM 告警。
- **人工处理指引**：Rotate bot token，更新 `WEB_HOOK_SECRET`。

##### S2-D4 数据一致性：队列确认与 runtime 状态同步
- **触发条件**：消息入列但 worker 崩溃未 ACK。
- **步骤序列**：记录 `pending_receipts` → 心跳 job 30 s 扫描 → 重新入列并标记 `retry=true`。
- **资源与状态**：Redis `conversation_pending`、runtime metrics。
- **输出与反馈**：用户收到“Still processing”或第二次 ack。
- **用户提示**：EN/TL “We are retrying your request”。
- **系统日志/事件**：`INFO telegram.entry.retry`。
- **告警/通知**：`pending_receipts>100` → 邮件。
- **人工处理指引**：检查 pending，如为毒消息写入 `dead_letter_queue` 并通知用户。

##### S2-D5 防御/降级：依赖不可达
- **触发条件**：TaskRuntime 无法连接 RabbitMQ/Redis。
- **步骤序列**：Gateway 捕获异常 → 切 `local_fallback_queue` → 通知 Operator → 定期重连。
- **资源与状态**：`local_queue`（容量 100）、`degraded_flag`。
- **输出与反馈**：提示“Service degraded, expect delay”。
- **用户提示**：多语言降级文案。
- **系统日志/事件**：`WARN telegram.entry.degraded`。
- **告警/通知**：Teams + SMS。
- **人工处理指引**：运行 `diagnose_runtime.ps1`，恢复后 `flush local_queue`。

##### S2-D6 观察性/运维：Channel Health 心跳
- **触发条件**：Health 模块需 30 s 更新 Redis key。
- **步骤序列**：Health 读取 worker 状态 → 写 `last_seen`, `pending`, `mode` → 触发 `channel.health.update`。
- **资源与状态**：Redis `channel_health:telegram`。
- **输出与反馈**：Admin Dashboard 灯色。
- **用户提示**：UI “Telegram channel healthy (latency {ms})”。
- **系统日志/事件**：`INFO channel.health`。
- **告警/通知**：`latency>3s` 或 `last_seen>60s`。
- **人工处理指引**：Ops 检查 worker Pod，必要时重启。

##### S2-D7 人工操作/配置管理：手动排空与暂停
- **触发条件**：升级 orchestrator 需暂停 5 分钟。
- **步骤序列**：Admin Panel 点击 Pause → Gateway 停接任务并等待队列清空 → 写 `channel_paused=true`。
- **资源与状态**：Redis flag `channel_paused`。
- **输出与反馈**：Telegram 自动回复“Channel maintenance in progress”。
- **用户提示**：多语言维护文案。
- **系统日志/事件**：`AUDIT telegram.entry.paused`。
- **告警/通知**：记录于 change log。
- **人工处理指引**：维护完点击 Resume，确认 health 恢复。

##### S2-D8 业务特殊：菲律宾法定节假日自动模式
- **触发条件**：PH 法定假日，需自动 async + 人工兜底。
- **步骤序列**：Scheduler 拉 `ph_holidays` → 匹配后写 `mode=async`, `manual_guard=true` → Health 通知值班。
- **资源与状态**：`holiday_cache`、`manual_guard_roster`。
- **输出与反馈**：提示“Expect manual review before completion”。
- **用户提示**：同上。
- **系统日志/事件**：`INFO telegram.entry.mode_switch`（`reason=holiday`）。
- **告警/通知**：值班群提醒。
- **人工处理指引**：指派人工审核 pending 并在 4 小时内清空。

### S3：渠道策略绑定与健康轮询（前端+后端原始描述）
- **触发**：Operator 在 Workflow Builder → Channel Tab 保存/查看策略或发起测试。
- **模块**：`src/schemas/channelPolicy.js`、`src/services/channelPolicyClient.js`、`src/services/channelHealthScheduler.js`、`src/stores/channelPolicy.js`。
- **步骤**：发布成功 → Store 拉取策略 → Scheduler 轮询健康 → `sendChannelTest` 前执行频控。
- **反馈**：UI 显示健康、冷却倒计时、测试记录。
- **数据**：前端 state + 后端 health API。

#### S3 子场景扩展
##### S3-D1 核心功能：策略保存与验证
- **触发条件**：Operator 修改 webhook、重试策略并保存。
- **步骤序列**：表单 schema 校验 → `channelPolicyClient.save` → 成功刷新 store 与健康数据。
- **资源与状态**：Pinia `policy` state、`pendingSave`。
- **输出与反馈**：成功 toast + 表单锁定 2 s。
- **用户提示**：ZH “渠道策略已保存”；EN “Channel policy updated”；TL “Na-update ang channel policy.”。
- **系统日志/事件**：前端 `INFO channel.policy.save`；后端 `AUDIT channel_policy_change`。
- **告警/通知**：token/webhook 变更自动邮件抄送安全。
- **人工处理指引**：审批人复核 `channelPolicyChange` 记录。

##### S3-D2 性能/容量：高频轮询与批量测试
- **触发条件**：监控 5 个 channel + 1 分钟内测试 10 次。
- **步骤序列**：Scheduler 合并轮询请求 → 对测试请求写 `cooldownUntil` → UI 显示倒计时。
- **资源与状态**：`healthPollingQueue`、`cooldownMap`。
- **输出与反馈**：部分请求 429，UI 呈现警告条。
- **用户提示**：“Health check paused for 30s due to frequent tests.”。
- **系统日志/事件**：`WARN channel.health.rate_limited`。
- **告警/通知**：本地提示，不外发。
- **人工处理指引**：如需超限，管理员调高阈值或改用 CLI 测试。

##### S3-D3 安全/权限：越权修改
- **触发条件**：角色 `viewer` 尝试保存策略。
- **步骤序列**：前端禁用按钮 → 后端 403。
- **资源与状态**：`currentUser.roles`。
- **输出与反馈**：“无编辑权限”。
- **用户提示**：EN/ZH/TL 权限提示。
- **系统日志/事件**：`SEC channel.policy.denied`。
- **告警/通知**：连续 5 次拒绝触发安全邮件。
- **人工处理指引**：IAM 调整角色或升级权限。

##### S3-D4 数据一致性：前端缓存 vs 后端版本
- **触发条件**：Operator B 打开旧表单，Operator A 刚保存。
- **步骤序列**：保存后推送 SSE `channelPolicy.updated` → 其他客户端比较 `version` → 落后则显示冲突提示。
- **资源与状态**：`policy.version`、SSE 订阅。
- **输出与反馈**：弹窗提供“覆盖/刷新”。
- **用户提示**：“Policy updated elsewhere. Refresh?”。
- **系统日志/事件**：`INFO channel.policy.version_conflict`。
- **告警/通知**：无。
- **人工处理指引**：安排编辑窗口或启用审批。

##### S3-D5 防御/降级：健康 API 不可用
- **触发条件**：`/channels/telegram/health` 超时。
- **步骤序列**：Scheduler 连续 3 次失败 → 暂停轮询 → 使用 `lastHealthySnapshot` → 标记 `cooldownPaused`。
- **资源与状态**：`lastHealthySnapshot`。
- **输出与反馈**：UI 黄色警示。
- **用户提示**：“Health data stale; retry later.”。
- **系统日志/事件**：`WARN channel.health.stale`。
- **告警/通知**：Slack ping。
- **人工处理指引**：调用后端诊断接口，恢复后手动重试。

##### S3-D6 观察性/运维：指标 & 告警
- **触发条件**：需要跟踪 `health_success_rate`、`test_failures`。
- **步骤序列**：Scheduler 上报 Performance entries → Backend 记录健康成功/失败 → Grafana 展示。
- **资源与状态**：`metricsBuffer`。
- **输出与反馈**：Dashboard 图表。
- **用户提示**：无。
- **系统日志/事件**：`INFO channel.health.metric`。
- **告警/通知**：SLO <99% 触发。
- **人工处理指引**：值班复核日志并优化 API。

##### S3-D7 人工操作/配置管理：策略回滚
- **触发条件**：新策略导致渠道不可用。
- **步骤序列**：从 `policyHistory` 选版本 → 点击回滚 → 保存并写 `rolled_back_from` → 自动执行健康测试。
- **资源与状态**：`policyHistory`、`rollbackJob`。
- **输出与反馈**：UI 显示“已回滚”。
- **用户提示**：“Policy rolled back to version v12.”。
- **系统日志/事件**：`AUDIT channel.policy.rollback`。
- **告警/通知**：邮件通知合规与安全。
- **人工处理指引**：24 h 内提交变更报告。

##### S3-D8 业务特殊：渠道合规文案
- **触发条件**：菲律宾 BI 要求测试消息包含英/他加禄免责声明。
- **步骤序列**：Schema 增 `disclaimer.ph/en` → 保存校验必填 → `sendChannelTest` 附多语文本 → 后端日志记录 `bi_disclaimer=true`。
- **资源与状态**：Pinia `disclaimer`、API payload。
- **输出与反馈**：Telegram 显示三语文本。
- **用户提示**：“[BI] Ang mensaheng ito ay para sa opisyal na pagsusuri.” 等。
- **系统日志/事件**：`INFO channel.policy.test_disclaimer`。
- **告警/通知**：缺字段 → CI 告警。
- **人工处理指引**：合规审核模板，更新 schema 默认值。

### S4：Workflow Builder 视图协调（前端原始描述）
- **触发**：Operator 在 `/workflow/:id` 切换节点、保存、发布、查看日志。
- **模块**：`useWorkflowBuilderController` 统一 orchestrate stores、scheduler、telemetry。
- **步骤**：路由进入加载 → 保存/发布时刷新 → 离开页面停止轮询/SSE。
- **反馈**：视图仅消费 `controller.state`。
- **数据**：Pinia 状态树 + 浏览器内存。

#### S4 子场景扩展
##### S4-D1 核心功能：加载→编辑→发布
- **触发条件**：Operator 访问 `/workflow/123`。
- **步骤序列**：Controller 拉取 workflow → 本地校验 → 发布 API → 刷新。
- **资源与状态**：`controller.state`、`workflowDraft.currentWorkflow`。
- **输出与反馈**：成功 toast + 发布 cooldown。
- **用户提示**：EN “Workflow published”；ZH “流程已发布”；TL “Nalathala ang workflow”。
- **系统日志/事件**：`INFO workflow.builder.publish`。
- **告警/通知**：发布失败 ≥3 次 → 邮件。
- **人工处理指引**：查看 publish API 日志并回滚。

##### S4-D2 性能/容量：SSE + 大型 Workflow
- **触发条件**：200+ 节点 + SSE 每秒 5 条。
- **步骤序列**：Controller 批处理 SSE、使用 VirtualList、FPS<30 时切分页。
- **资源与状态**：`sseBuffer`、`virtualScrollState`。
- **输出与反馈**：UI 提示“高容量模式”。
- **用户提示**：“Large workflow, switched to paging view.”。
- **系统日志/事件**：`WARN workflow.builder.high_volume`。
- **告警/通知**：前端性能指标 `perf.low_fps`。
- **人工处理指引**：拆分 workflow 或关闭实时日志。

##### S4-D3 安全/权限：日志越权
- **触发条件**：Role=Reviewer 访问日志 tab。
- **步骤序列**：Controller 根据角色隐藏 tab；越权请求 403。
- **资源与状态**：`currentUser.permissions`。
- **输出与反馈**：“权限不足”。
- **用户提示**：多语言权限提示。
- **系统日志/事件**：`SEC workflow.builder.log_denied`。
- **告警/通知**：连续 5 次触发安全邮件。
- **人工处理指引**：审查角色映射。

##### S4-D4 数据一致性：并发编辑
- **触发条件**：多人同时编辑同一 workflow。
- **步骤序列**：订阅 `workflow.updated` SSE → 发现版本冲突 → 弹 Diff → 选择保留版本。
- **资源与状态**：`draftVersion`、`conflictDialogState`。
- **输出与反馈**：冲突弹窗。
- **用户提示**：“Detected newer version from {user}”。
- **系统日志/事件**：`INFO workflow.builder.version_conflict`。
- **告警/通知**：无。
- **人工处理指引**：如冲突频繁则启用锁定模式。

##### S4-D5 防御/降级：SSE 断连
- **触发条件**：网络受限导致 SSE 断开。
- **步骤序列**：监测 `EventSource.onerror` → 指数退避 → 失败 >5 次切轮询 → UI 显示离线。
- **资源与状态**：`sseRetryCount`、`pollingTimer`。
- **输出与反馈**：“Realtime updates paused”。
- **用户提示**：EN/TL/ZH 离线提示。
- **系统日志/事件**：`WARN workflow.builder.sse_fallback`。
- **告警/通知**：无。
- **人工处理指引**：指导用户检查网络，必要时运维排查 SSE。

##### S4-D6 观察性/运维：Controller 指标
- **触发条件**：需捕获 `publish_latency`, `sse_subscribe_time`。
- **步骤序列**：Controller 前后调用 `telemetry.send` → 后端聚合 `workflow_builder_*` 指标。
- **资源与状态**：`telemetryBuffer`。
- **输出与反馈**：Ops Dashboard。
- **用户提示**：无。
- **系统日志/事件**：`INFO workflow.builder.metric`。
- **告警/通知**：SLO 未达触发。
- **人工处理指引**：分析 KPI 并优化慢点。

##### S4-D7 人工操作/配置管理：紧急开关
- **触发条件**：发布窗口前需要冻结编辑。
- **步骤序列**：管理员启用 `freeze_editing` flag → Controller 置灰控件 → 记录 `freeze` 事件。
- **资源与状态**：`featureFlags.freezeEditing`。
- **输出与反馈**：提示“系统维护”。
- **用户提示**：“Editing temporarily disabled”。
- **系统日志/事件**：`AUDIT workflow.builder.freeze_on`。
- **告警/通知**：邮件通知相关团队。
- **人工处理指引**：维护完成后关闭 flag 并验证。

##### S4-D8 业务特殊：多语种提示与菲律宾法规
- **触发条件**：含 BI 节点的 workflow 必须附英/他加禄提示。
- **步骤序列**：Controller 根据 metadata 加载模板 → 校验必填 → 缺失则阻止发布。
- **资源与状态**：`localeTemplates`、`validationErrors`。
- **输出与反馈**：错误 toast 列缺失字段。
- **用户提示**：“Fill BI bilingual prompts before publishing.”。
- **系统日志/事件**：`WARN workflow.builder.locale_missing`。
- **告*** End Patch
- **告警/通知**：CI 构建失败通知。
- **人工处理指引**：内容团队补齐文案后重新发布。

## Data / State
- **Workflow Summary 流**：`WorkflowRunResult` → `WorkflowSummaryRepository`（Redis/Mongo）。Redis 存最近 20 条，Mongo 存档 + `updated_at`；仓储负责 `SummaryWriteQueue`、`consistency_repair_queue`、幂等与 TTL。
- **Telegram Runtime 流**：Update → Config（同步/异步/节假日）→ Runtime Gateway（enqueue / await / local fallback）→ Workflow Service → Outbound；Gateway 维护 `pending_receipts`、`channel_paused`、`manual_guard`。
- **Channel Policy 流**：Store 请求 `channelPolicyClient`；Scheduler 维护 `healthPollingQueue`、`cooldownMap`、`lastHealthySnapshot`；SSE `channelPolicy.updated` 解决版本冲突。
- **Workflow Builder 状态流**：Controller 汇总 `workflowDraft`, `channelPolicy`, `health`, `testHistory`，计算 `canPublish`, `cooldownUntil`, `freezeEditing` 等派生字段。
- **Audit & Compliance 流**：`gov_audit_queue`, `policyHistory`, `changeLogs` 贯穿 S1/S3/S4，满足菲律宾政府审计。

## Rules
1. **依赖方向**：接口/入口层只能依赖业务/状态层，业务层只能依赖契约，仓储/基础层提供实现；禁止反向调用。citeturn0search1turn0search2
2. **数据持久化**：业务逻辑不得直接操作 Redis/Mongo，必须通过 Foundational Service 仓储并确保幂等/TTL。
3. **Store 职责**：Pinia store 仅存状态与 getter，副作用/轮询放入 service/composable。citeturn0reddit12
4. **入口轻量化**：`application_builder.py` 只负责 app 创建与路由注册，运行时 bootstrap、logging、telegram 逻辑迁至独立模块。citeturn0search1turn0search2
5. **功能等价验证**：迁移遵循“复制→替换”策略，保证 API 契约不变。
6. **多语言/合规**：凡触及菲律宾政府渠道的提示语、测试消息，必须附 EN/TL（必要时 ZH）并记入审计。

## Exceptions
- **Redis/Mongo 不可达**：仓储记录 `workflow.summary.persisted` 失败事件，仍返回业务结果但附 warning，Ops 需修复并通过 repair queue 补写。
- **TaskRuntime 队列阻塞**：Gateway 超时返回 `async_failure_text` 并标记 `queue_timeout`，Operator 可视情况暂停 channel。
- **Channel Health 连续失败**：Scheduler 暂停轮询，`cooldownPaused=true`，需人工点击“重试健康检查”。
- **Workflow Builder SSE 未关闭**：Controller 在 `onBeforeUnmount` 必须 unsubscribe；浏览器崩溃时由后端超时。
- **模块迁移遗漏引用**：PR 必须搜索 `_TASK_RUNTIME_FACTORY` 等旧 helper 并替换。
- **Gov Audit Backlog**：`gov_audit_queue` backlog >100 必须 24h 内人工导出并补交。

## Acceptance (GIVEN/WHEN/THEN)
1. **Workflow Summary**：GIVEN chat_id 且 Redis/Mongo 可用；WHEN 执行 workflow；THEN Redis & Mongo 同步更新且 `workflow.summary.persisted=success`。
2. **Conversation Gateway**：GIVEN async ack 配置；WHEN Telegram update 触发异步；THEN Gateway 返回任务 ID，Service 不直接访问 `_TASK_RUNTIME_FACTORY`。
3. **Channel Policy Store**：GIVEN Workflow 已发布；WHEN 打开 Channel Tab；THEN Store 仅提供状态，轮询由 scheduler 控制，Pinia state 无 `setTimeout` 引用。
4. **Workflow Builder Controller**：GIVEN 用户离开页面；WHEN `beforeRouteLeave` 触发；THEN controller 停止轮询/SSE，日志无残余订阅。
5. **Regulation**：GIVEN `user_country=PH`；WHEN 产生 summary 或渠道测试；THEN 文案含英/他加禄，`gov_audit_queue` 接收镜像任务。

## 提示语与交互设计汇总
- **成功模板**：`success_message.<channel>.<locale>` 统一保存在 `copywriting.yaml`，引用各场景提供的 EN/ZH/TL 文案。
- **失败/降级模板**：`failure_text`、`degraded_text` 字段由 services/composables 注入，各子场景给出示例。
- **系统日志格式**：`<LEVEL> <context> key=value`，核心字段 `chat_id`, `workflow_id`, `policy_version`, `channel`, `reason`。
- **告警/通知映射**：S1/S2 高优 PagerDuty + SMS；S3/S4 走 Slack/Teams；合规定向邮件；手动操作记录在 WorkLog。
- **人工指引登记**：所有子场景的角色、工具（Admin Panel、CLI、kubectl、mongo shell）与完成标准同步至 `AI_WorkSpace/WorkLogs/templates/manual_runbook.md`。

## 异常与防御矩阵
| 失败类型 | 触发条件 | 检测信号 | 自动处理/降级策略 | 用户提示/告警 | 人工补救步骤 | 验证指标 |
| --- | --- | --- | --- | --- | --- | --- |
| Redis 连接耗尽 | Redis pool >90% | `workflow.summary.backpressure` WARN | 切换 `MONGO_ONLY` + 限流 | “Realtime summary paused”；PagerDuty+SMS | 扩容/清理长连接 | Redis `connected_clients` 恢复 |
| Mongo 写失败 | 副本集不可用 | `workflow.summary.persisted` ERROR | 重试→写 repair queue | “Archive pending” UI banner | 运行 repair job | Mongo `writeConcern` ACK 正常 |
| 队列阻塞 | RabbitMQ down | `telegram.entry.degraded` WARN | `local_fallback_queue` + async ack | Telegram 降级提示；Teams+SMS | 修复依赖并 flush 队列 | `pending_receipts` 清零 |
| 并发冲突 | 多人编辑 workflow/policy | `version_conflict` 事件 | 弹窗提醒/强制刷新 | “内容被他人更新” | 排班或启用锁定 | SSE 冲突事件归零 |
| 资源耗尽（前端） | Workflow >200 节点 FPS<30 | `perf.low_fps` metric | 切分页/虚拟滚动 | “高容量模式” 提示 | 拆分流程/关闭实时日志 | FPS≥45 |
| 依赖不可达（健康 API） | `/channels/.../health` 超时 | Scheduler 失败≥3 | 暂停轮询 + 使用快照 | 黄色提示 + Slack ping | 修复 API 手动重试 | 成功率>99% |
| 数据污染 | Gov audit 字段缺失 | Schema 校验失败 | 阻止发布 | 错误 toast + CI fail | 合规补齐字段 | 发布成功且日志含 `bi_disclaimer` |
| 配置缺失/提示语错误 | Copywriting 缺字段 | 构建检查失败 | CI 中止 | CI 邮件 | 更新 YAML 重跑 | CI 通过 |

## 未覆盖清单
- 当前 8 大维度已在 S1~S4 覆盖；未来若新增 SMS/Email 渠道，再补充对应场景。

## Implementation Decisions
1. **Repository 注入**：沿用 FastAPI `Depends` + `lru_cache` 作为轻量 DI，接口/入口层共享同一仓储实例即可满足当前重构目标，不再引入额外容器。
2. **前端 Telemetry 粒度**：`useWorkflowBuilderController` 内置 `telemetry.send` 钩子，仅在 publish/health 操作上报性能；健康轮询耗时也经过 scheduler 统一记录，运营无需额外配置。
3. **Channel 频控配置**：短期继续使用前端常量（3 次/分钟）；scheduler 若收到后端 `frequencyWindow` 字段则自动覆盖，无需新增配置界面。
4. **Gov Audit SLA**：当政府镜像节点可用率 <95% 持续 30 分钟时，自动切换为“人工导出”模式，同时向合规与 Site Ops 推送告警并要求 24 小时内补交。

## 自检
- ✅ 场景拆分覆盖四大主场景与 8 维度子场景。
- ✅ 每个子场景包含触发条件、步骤、资源状态、输出反馈、提示语、日志、告警、人工指引。
- ✅ 已构建异常与防御矩阵，涵盖并发冲突、资源耗尽、依赖不可达、数据污染、配置缺失等类别。
- ✅ 数据/规则/验收/提示语章节保持一致并补充新要素。
- ✅ 未发现需标记的缺失维度，仅记录未来渠道扩展需求。
