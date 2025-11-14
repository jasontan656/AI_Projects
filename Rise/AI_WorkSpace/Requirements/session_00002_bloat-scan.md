# Rise/Up 臃肿文件治理规格（session_00002_bloat-scan）

## 背景与目标
- 2025-11-13（UTC-8）起，Rise 与 Up 代码库出现 9 个超过 400 行且横跨多职责的“巨石”模块，已触发 microservice smell 研究中定义的“功能聚合”“紧耦合交互”等臭味，若不拆解将持续放大维护成本与交付风险。citeturn0search0turn0search5
- Telegram 渠道是当前唯一对外入口；任何会话策略、channel binding、Workflow CRUD 变更都需同步影响 Up Admin，从而形成“配置-执行”闭环。
- 目标：以小型内部团队也可执行的标准，完成 Rise/Up 臃肿文件拆分、数据契约重整、运维防线与观察性增强，避免出现“再造 God Object”的反复拉扯。参考 Refactoring 社区对“Moving Features Between Objects”“Replace Function with Command”等手法的建议，要求每个模块保持单一职责，必要时通过命令对象/委派来封装复杂状态。citeturn1search2turn1search7

## 参与方与职责
- **Telegram Conversation Runtime**：监听 webhook、解析更新、调用 BindingCoordinator/Guard/TaskEnqueue、在 1s 内产出 ack。
- **Channel Binding Coordinator**：维护 redis/mongo snapshot、刷新 token、追踪 secret 版本与 entry config。
- **Pipeline Guard & Task Enqueue Service**：对 workflow/pipeline 节点进行策略检查、构建 TaskEnvelope、推送 redis/队列。
- **Rise Startup & Capability Service**：加载 .env、校验依赖（Mongo/Redis/Rabbit/Telegram/public-endpoint）、对外暴露健康探针。
- **Workflow Persistence 层**：Tool/Stage/Workflow 三条聚合 + 版本历史 + 发布记录，负责 CRUD、索引、历史封存。
- **Telemetry Console & Coverage Recorder**：负责结构化事件渲染、镜像、SSE 及覆盖率 JSONL。
- **Up Admin Operators**：通过 PipelineWorkspace、WorkflowBuilder、ChannelForm、LogStream 维护资源；需感知后台拆分后的 API 字段、事件与错误。
- **Observability 消费者**：Webhook 监控、WorkflowLogStream、ChannelHealthCard、CLI 或外部警报系统，使用统一事件模型 & 指标。

## 设计原则与既定决策
1. **单一职责 + Extract Class**：每个 Python/Vue 文件控制在单一职责或 300 行以内；若业务/工具逻辑混杂，立即抽出命令对象或子组件。citeturn1search7
2. **接口注入优先**：所有跨层依赖通过 Protocol/Factory 提供，禁止新增全局 setter，现有全局 setter 需迁移至工厂。
3. **DTO 分段**：WorkflowChannelRequest/Response 固定为 credential/rateLimit/security 三段；Rise/Up 均按该 schema 读写。
4. **健康与日志兼容**：/healthz 与 /workflow-channels/* 仅允许追加字段，旧字段不可更名；Up Admin 需能在两周内消化新增字段但无需热部署。
5. **单区域部署默认**：当前默认单区域（亚太唯一 AZ）；如需多区域由后续立项，本文不做扩展。
6. **无分段保存**：Channel Form 与 Workflow Form 默认一次性保存，保持操作原子性；后续若需分段另起规格。
7. **Telemetry 命名**：统一 `domain.action`，事件必须含 `level`, `correlation_id`, `channel`, `workflowId`; 颜色/过滤配置由 Up LogStream 消费。
8. **日志 SSE Retry-After**：Rise SSE 在退避时写入 `retry-after-ms` header；Up `useWorkflowLogs` 强制读取并显示倒计时。
9. **Feature Flag 退场计划**：ChannelFormV2/PipelineWorkspaceV2/TelemetryConsoleV2 均需 flag & 退场日期；flag 默认 30 天内回收。
10. **审计与回溯**：任何抽象拆分必须在 `AI_WorkSpace/DevDoc/On` 记录背景、边界与退场计划，方便后续 smell 扫描与 tooling。

## 场景蓝图

### 场景A：Conversation Runtime 解耦
- **触发**：接收 Telegram webhook、binding 版本变更、策略更新。
- **流程**  
  1. `UpdateIngress` 校验签名 → TraceSpan 写入 `telegram.update.received`.  
  2. `ConversationContextFactory`（新模块）加载 chat state、workflow hint、policy fallback。  
  3. `BindingCoordinator` 拉取 redis snapshot，不一致时触发 refresh 并推送 telemetry。  
  4. `PipelineGuardService` 校验节流、白名单、workflow availability，生成决策。  
  5. `TaskEnqueueService` 构建 `TaskEnvelope`（含 idempotency key、payload、timeout）并推送 redis/rabbit。  
  6. `ResponseBuilder` 根据 guard/enqueue 结果生成 ack / fallback 文案并返回 Telegram。
- **数据/接口**：所有上下文经 `ConversationContext` dataclass 传递，包含 `bindingVersion`, `policySnapshot`, `entryConfig`, `agentHints`；Up 侧 `ChannelHealthCard` 订阅新事件 `channel.binding.latency`.
- **Up 影响**：ChannelForm UI 需展示 binding 版本、上次刷新时间、策略 fallback 状态；WorkflowLogStream 新增 `conversation.guard.reject` 事件分组。
- **维度覆盖**  
  | 维度 | 规范 |
  | --- | --- |
  | 核心流程 | 30ms 内完成上下文装配；guard+enqueue 出错必须输出结构化 ack。 |
  | 性能/容量 | 单进程 300 RPS；超出时半开断路器+队列回退。 |
  | 安全/权限 | 校验 Telegram secret header；仅允许白名单 chatId 继续；敏感字段在 telemetry 中脱敏。 |
  | 数据一致性 | `bindingVersion` + `idempotencyKey` 组合确保重复投递幂等；redis/mongo 写入包裹事务或补偿脚本。 |
  | 防御策略 | guard fail 返回 `workflow_locked` copy，后台开启自动 refresh；连续失败 3 次触发人工 runbook。 |
  | 观测/告警 | 指标 `conversation.guard.reject_count`, `binding.refresh.latency`；严重级别告警走 PagerDuty。 |
  | 手动运维 | Runbook《binding-refresh》包含 redis flush、snapshot rebuild、Up UI 验证。 |
  | 业务变体 | 支持多语言 ack：中文/英文根据 channel locale；默认中文。 |

### 场景B：FastAPI 启动与健康探针解耦
- **流程**：`startup.housekeeping` 负责 .env 解析、日志目录、可选清理；`capabilities.probes` 注册 Mongo/Redis/Rabbit/Telegram/PublicEndpoint/Memory；`api.health` 使用 `CapabilitySnapshotService` 输出 `/healthz`、`/healthz/readiness`、`/internal/memory_health`。
- **Up 影响**：WorkflowBuilder `ChannelHealthCard` 读取 `probeVersion`, `lastProbeTs`; PipelineWorkspace 顶部加入“后端健康”提示。
- **维度覆盖**：与场景A同结构（略述）：性能（健康 API SLA 200ms）、安全（仅 GET/HEAD, 加签 optional）、一致性（snapshot 更新原子）、防御（探针失败退避+flag）、观测（latency 直方图）、运维（`uvicorn --check-capability` 脚本）、业务（单 AZ 默认）。

### 场景C：依赖工厂分拆
- **流程**：`dependencies/workflow.py`、`dependencies/channel.py`、`dependencies/telemetry.py` 各自 expose FastAPI Depends；router 仅 import 所需子模块，避免循环。
- **Up 影响**：requestJson 仍收到 `{code,message}` 错误；无需变更。
- **维度覆盖**：核心=模块化 DI；性能=延迟加载；安全=不可泄漏连接串；一致性=连接池重用；防御=Dead letter fallback；观测="dependency.factory.init" 事件；运维=脚本检测模块 wiring；业务=支持未来 Slack/HTTP channel。

### 场景D：Workflow 仓储分层
- **流程**：`MongoCrudMixin` 提供通用 CRUD/索引；`tool_repository.py`、`stage_repository.py`、`workflow_repository.py`、`workflow_history_repository.py` 分别实现聚合；异步实现 mirror 同样接口。
- **Up 影响**：Workflow 列表/详情 API 字段保持 `workflowId/name/status/versionHistory`；新增 `historyChecksum` 用于 Admin diff。
- **维度覆盖**：聚焦一致性（写入+历史 append-only）、性能（分页 50 条/请求）、安全（字段过滤 PII）、防御（写失败重试）、观测（Mongo 操作 metrics）、运维（`python tools/rehydrate_workflow_history.py`）、业务（BI 用例优先）。

### 场景E：Telemetry Bus 分拆
- **流程**：`TelemetryConsoleView` 仅负责 Rich 渲染 + 颜色主题；`CoverageEventRecorder` 负责 JSONL + SSE；`publish_event` 函数写入共享 async queue；Designite/工具输出事件可直接注入（为后续 smell 监测做准备）。citeturn0search1
- **Up 影响**：WorkflowLogStream 必须能识别 `telemetry.console.mirror`, `coverage.run.completed`; `logService` 需处理新的 `mirrorFile` 元数据。
- **维度覆盖**：关注性能（SSE 1k events/min）、安全（敏感字段脱敏）、一致性（event_id 单调）、防御（落盘失败回退到 stdout）、观测（镜像文件大小告警）、运维（rotate 脚本）、业务（多语言描述）。

### 场景F：Channel Form 模块化
- **流程**：将 611 行组件拆为 `ChannelCredentialCard`（token/webhook/轮询）、`ChannelRateLimitForm`（速率/白名单/localization）、`ChannelSecurityPanel`（secret/cert/coverage 测试）、父组件 `ChannelFormShell` 管理 dirty + 提交。
- **Up 影响**：各子组件提供 `isDirty()`、`validate()`；父组件统一发射 `save`；UI 文案更新以突出 credential/安全区别；表单 copy 见“交互与文案”。
- **Rise 影响**：DTO 可按段校验并返回 `errors.credential`, `errors.rateLimit`, `errors.security`。
- **维度覆盖**：核心=子组件化；性能=局部渲染；安全=token 不回显；一致性=baseline 比对；防御=子组件校验失败阻止提交；观测=Form Dirty 事件；运维=Feature Flag 退回；业务=操作员中英双语切换。

### 场景G：Pipeline Workspace 视图切片
- **流程**：引入 `WorkspaceShell`（aside+header+actions）；nodes/prompts/workflow/variables/logs/settings 各自为 view，懒加载 + keep-alive；导航状态放入 `workspaceNavStore`。
- **Up 影响**：路由地址分段 `/workspace/nodes` 等；操作员无刷新即可切换；日志视图保留 SSE 连接状态在 store。
- **维度覆盖**：核心=视图拆分；性能=首屏 <2s, 懒加载 chunk；安全=路由守卫确认 operator role；一致性=store 提供单一 source of truth；防御=视图故障 fallback 为空态；观测=导航事件 telemetry；运维=Feature Flag, vitest 覆盖；业务=“Soon” tab retired。

### 场景H：Workflow Builder 控制器拆分
- **流程**：`useWorkflowCrud`, `useWorkflowLogs`, `useWorkflowMeta`, `useChannelTestGuard` 四个 composable 组合；CRUD hook 负责 dirty & confirmLeave，Logs hook 管理 SSE 订阅/退避与过滤，Meta hook 拉取变量/工具，Channel guard hook 管理发送测试/冷却。
- **Up 影响**：`WorkflowBuilder.vue` 改为组合式 API + `<script setup>`；易于测试；日志标签 UI 显示 retry 倒计时。
- **维度覆盖**：核心=逻辑拆分；性能=懒加载；安全=操作前权限校验；一致性=store 更新单点；防御=hook 抛错→Toast；观测=Hook instrumentation；运维=独立 Vitest；业务=Workflow 发布流程 unchanged。

### 场景I：Workflow Editor 表单组件化
- **流程**：`PromptBindingTable` 负责节点-提示词映射 + 清理；`ExecutionStrategyForm` 专注重试/超时；`useWorkflowForm` 管理 form/baseline/errors/isDirty；主组件仅渲染 UI。
- **Up 影响**：`WorkflowEditor` 事件 `save/dirty-change` 保持；新增“批量绑定”操作；文案细化。
- **维度覆盖**：核心=UI 拆分；性能=局部 diff；安全=字段校验；一致性=baseline 复制；防御=策略越界阻止提交；观测=Form Telemetry；运维=组件 storybook；业务=BI 工作流默认策略 2 次重试。

## 数据与状态模型
- **ConversationContext**：`chatId`, `channel`, `workflowId`, `bindingVersion`, `entryConfig`, `policySnapshot`, `agentHints`, `telemetryTags`; TTL 5 min。
- **BindingSnapshot**：`workflowId`, `channel`, `botTokenRef`, `webhookUrl`, `waitForResult`, `rateLimitPerMin`, `allowedChatIds`, `locale`, `secretVersion`, `certificateFingerprint`, `updatedAt`。
- **TaskEnvelope**：`taskId`, `idempotencyKey`, `workflowId`, `nodeSequence`, `payload`, `timeoutMs`, `retryLimit`, `metadata(traceId, locale, channel)`。
- **WorkflowDefinition**：`workflowId`, `name`, `status`, `nodeSequence`, `promptBindings`, `strategy`, `metadata(description,tags)`, `version`, `historyChecksum`, `updatedBy`, `updatedAt`。
- **TelemetryEvent**：`event_id`, `timestamp`, `event_type`, `level`, `correlation_id`, `channel`, `workflowId`, `payload`, `tags`, `mirrorFile`.
- **Admin Form State**：`credential`, `rateLimit`, `security` 三段 baseline + dirty flags；`workflowForm` baseline per field。

## 业务规则与 SLA
1. Telegram ack 必须在 1s 内返回；guard reject 需在 300ms 内生成 copy。
2. Channel binding 刷新成功后 5s 内同步到 redis + mongo snapshot，并广播事件。
3. Workflow CRUD：保存事务必须包含版本戳；冲突返回 409，并附带最新版本 diff。
4. Channel Form 保存：credential/rateLimit/security 三段全部校验通过才允许提交；任何字段错误返回结构化 `errors`。
5. Health probes：/healthz 200ms SLA；探针连续 3 次失败 → readiness=false；Up UI 显示红色 banner。
6. Telemetry：事件落盘成功率 ≥ 99.9%；mirror 文件按 50MB 滚动。
7. Observability：Workflow 日志 SSE 需支持 1k 事件/分钟；断线 3 次自动退避 30s 并提示。
8. 数据保留：Binding snapshot 30 天，Telemetry JSONL 7 天，Workflow 历史永久保留。

## 交互与文案
- **Telegram Ack**  
  - 成功：`已收到申请（#${taskId}），我们将尽快回复。`  
  - guard reject：`当前工作流繁忙，请稍后再试（参考代码：workflow_locked）。`  
  - binding 缺失：`频道尚未完成配置，请联系运营同学。`
- **Up Channel Form**  
  - Credential 提示：`Webhook URL 与 Token 仅在禁用轮询时必填。`  
  - Security 面板 3 态：未设置 → 黄色提示；设置但未验证 → 蓝色提醒；验证通过 → 绿色勾。  
  - Dirty 提醒：顶部 banner “本页存在未保存更改（Credential + Security）”。
- **Workflow Builder**  
  - 保存成功 toast：“Workflow 已保存，版本 v${version}”。  
  - 发布 confirm：“发布将冻结当前版本，是否继续？”  
  - 日志断线 banner：“日志流已断开，系统将在 ${retryAfter}s 后重连”。

## 观测与遥测
- **指标**：`conversation.guard.reject_count`, `binding.refresh.latency_ms`, `task.enqueue.duration_ms`, `health_probe.latency_ms`, `workflow.save.conflict_rate`, `channel_form.validation_error_count`, `sse.disconnect_count`.
- **日志**：结构化 JSON（level, event_type, workflowId, channel, tags, message）。Up LogStream 需显示 event_type + level +简短描述。
- **事件**：  
  - `channel.binding.refresh_start|success|failure`  
  - `conversation.guard.reject` (payload含 reason, chatId)  
  - `workflow.version.published` (包含 version, operator)  
  - `channel.form.validation_failed` (payload含 segment, field)  
  - `telemetry.console.mirror_rotated`
- **警报**：  
  - 触发条件：指标超阈（如 guard reject >50/min），SSE 断线 5min，health probe fail 三连。  
  - 路由：PagerDuty（P1/P2）、Slack #rise-ops（P3）。  
  - 内容模板：“[Rise][P1] Conversation Guard Reject 爆量 - workflow=${id} - since=${timestamp}”。

## 异常与防御矩阵
| 失败类型 | 触发条件 | 检测信号 | 自动处理/降级 | 用户提示/告警 | 人工补救 | 验证指标 |
| --- | --- | --- | --- | --- | --- | --- |
| 并发冲突 | Workflow 保存版本落后 | 409 + diff | 自动重试一次；失败返回冲突详情 | Up toast + PagerDuty P3 | 手动合并并重试保存 | `workflow.save.conflict_rate` < 2% |
| 资源枯竭 | Redis 队列耗尽/连接池不足 | Redis 指标/timeout | 启用背压，写入 `queue_full` 事件 | Telegram ack fallback + Slack 告警 | 扩容 redis、清理积压 | 队列长度恢复 < 10k |
| 依赖宕机 | Mongo/Redis/Telegram probe fail | /healthz readiness=false | 自动进入降级模式（仅返回告警 ack） | Up 顶部红 Banner + PagerDuty P1 | 确认依赖恢复，执行 runbook | readiness= true |
| 数据损坏 | Binding snapshot 缺失字段 | Schema 验证失败 | 回退到上一次快照；触发 `binding.snapshot_corrupt` | ChannelForm 提示需重新保存 | 运营重填表单，后端重建 snapshot | 校验通过率 100% |
| 配置错误 | Channel Form 输入非法 | 表单校验 error | 阻止提交 | 表单内红色错误 + toast | 运营修正输入 | 校验失败字段归零 |
| 安全事件 | Secret 恶意访问/泄漏 | Telemetry `security.secret.rotate` | 立即轮换 secret + 暂停 webhook | Telegram ack 提示安全自检 + PagerDuty P1 | 手动 rotate + audit | secretVersion 增量 |
| 合规异常 | Telemetry 包含 PII | 日志扫描器检测 | 自动 mask 字段 + 停止镜像 | Slack P2 | 数据保护负责人审查 + purge | PII 事件=0 |

## 运维与手动流程
1. **Binding Refresh Runbook**：执行 `python scripts/refresh_binding.py --workflow <id> --channel telegram --base-url http://localhost:8000`，携带 `X-Actor-Id`/`X-Actor-Roles` 头部刷新 `/api/channel-bindings/{workflow}/refresh`，打印最新 bindingVersion/locale，并对照 Up ChannelForm “同步”操作与日志事件验证 redis/mongo snapshot。
2. **Workflow History Rehydrate**：运行 `python tools/rehydrate_workflow_history.py --workflow <id>`，确保版本 checksum 一致。
3. **Telemetry Mirror Rotate**：每日 02:00 UTC 执行 `scripts/rotate_telemetry.sh`，校验 JSONL 完整，上传至 S3。
4. **Health Probe Drill**：每周一次模拟依赖宕机，确认 `/healthz`、Up banner、PagerDuty 告警链路。
5. **Feature Flag Rollout**：ChannelFormV2 → 先在 staging 打开 48h，再逐批开放生产（10%→50%→100%），任何阶段若 error rate >3% 立即回滚。
6. **Ops Matrix Drill**：运行 `pwsh AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-11_ops_matrix.ps1 --env <local|staging> --workflow <id> --SlackWebhook <url> --PagerDutyRoutingKey <key>`，串联 binding refresh、telemetry probe、workspace 导航脚本，并将结果写入 `Step-11_ops_matrix_summary.json` 及 Slack/PagerDuty sandbox，形成可审计的运维闭环。

## 验收标准
- 场景 A-I 的新模块/组件均完成、行数受控且拥有单元/集成测试；Vitest/Pytest 覆盖率不低于 70%。
- Channel Form、Pipeline Workspace、Workflow Builder 在 Feature Flag 打开后 48h 内无 Sev-1/2 事故。
- `/healthz`、`/workflow-channels/*` 接口保持兼容且新增字段可被 Up UI 正确渲染。
- Telemetry 事件可被 WorkflowLogStream 和外部订阅者解码，镜像文件按策略滚动。
- 异常矩阵中每个失败类型对应的指标与告警均已配置并演练一次。
