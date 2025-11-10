# 渠道绑定与 Telegram 健康检查（session_20251109_0149）

## 背景与范围
- **目标**：落实报告 M2，围绕 Telegram 渠道提供配置、健康、测试与解绑能力，使 Workflow 从“已发布”到“可触达用户”形成闭环。
- **范围**：
  1. 新增 Channel Policy store/service（`src/stores/channelPolicy.js`、`src/services/channelService.js`）连接 Rise `/api/workflow-channels`、`/api/channels/telegram/*`。
  2. 在 Workflow 详情页（或新路由 `/workflows/:id`）增设“渠道设置”Tab，提供 Telegram Bot Token、Webhook、回退文案、速率限制等表单。
  3. 提供健康状态卡片（轮询 + 手动刷新）、一键测试对话框、解绑流程，以及针对敏感信息的 UI 保护。
- **不包含**：其他渠道（Slack/Email 等）与日志画布功能，这些归入后续阶段。

## 模块划分
| 组件/文件 | 作用 |
| --- | --- |
| `src/stores/channelPolicy.js` | 管理当前 workflow 的渠道配置、健康数据、测试记录、轮询状态。 |
| `src/services/channelService.js` | 统一封装渠道 CRUD、健康、测试接口；负责附加 Actor 头、错误映射。 |
| `src/components/WorkflowChannelForm.vue` | Telegram 表单组件，负责渲染/校验并暴露 `isDirty`、`getPayload()`。 |
| `src/components/ChannelHealthCard.vue` | 展示健康状态灯、关键指标、最近一次检查/错误，并提供手动刷新按钮。 |
| `src/components/ChannelTestPanel.vue` | 弹窗/侧板，供用户发送测试消息、查看历史结果。 |

## API 契约
| 功能 | Method & Path | Request | 响应要点 |
| --- | --- | --- | --- |
| 获取渠道配置 | `GET /api/workflow-channels/{workflowId}?channel=telegram` | 无 | 200 → `data.channelPolicy`；404 → 未绑定，UI 进入空态。 |
| 创建/更新配置 | `PUT /api/workflow-channels/{workflowId}` | `channelPolicy` 负载（见下） | 200 → `data.channelPolicy` + `meta.version`；422 → 字段错误。 |
| 删除配置 | `DELETE /api/workflow-channels/{workflowId}?channel=telegram` | 无 | 204，若 409 则表示 Workflow 正在使用。 |
| 健康检查 | `GET /api/channels/telegram/health?workflowId=...&includeMetrics=true` | 可选 query | 200 → `{ status, lastCheckedAt, lastError, metrics }`；503/504 视作 `status='unknown'`。 |
| 发送测试消息 | `POST /api/channels/telegram/test` | `{ workflowId, chatId, payloadText, waitForResult, correlationId? }` | `{ status, responseTimeMs, telegramMessageId?, errorCode?, traceId }`。 |

`channelPolicy` 结构（仅 Telegram）：
```
{
  workflowId: string,
  channel: 'telegram',
  botToken: string,
  webhookUrl: string,
  waitForResult: boolean,
  workflowMissingMessage: string,
  timeoutMessage: string,
  metadata: {
    allowedChatIds: string[],
    rateLimitPerMin: number,
    locale: 'zh-CN' | 'en-US'
  },
  updatedAt: string,
  updatedBy: string
}
```

## 表单与校验细节
- **Bot Token**：匹配 `^\d{5,}:[A-Za-z0-9_-]{35}$`；输入框提供“粘贴 Token”按键，保存后 UI 仅显示前 6 位 + “****” + 末尾 4 位，并提供「重新输入」按钮。变更 token 需二次确认。
- **Webhook URL**：必须 https；如域名不在 `VITE_TELEGRAM_WEBHOOK_WHITELIST`，显示黄色警告但允许保存。禁止空格与 query 中的空白字符。
- **回退文案**：`workflowMissingMessage` 与 `timeoutMessage` 最长 256 字，支持变量 `{workflow_id}`、`{correlation_id}`，下方展示变量提示并允许一键复制。
- **Allowed Chat IDs**：用 tag 输入组件，保存前转换为整数字符串并去重；如输入非整数则标红且禁用保存。
- **Rate Limit**：范围 1–600，默认 60，超过范围时展示 inline 错误。
- **表单脏值**：`WorkflowChannelForm` 暴露 `isDirty()`；Tab 切换或导航离开需调用，若返回 true 则弹出 `ElMessageBox`。

## 健康状态与轮询策略
- **轮询节奏**：默认 30s；若请求失败，按 30s → 60s → 120s 退避，三次失败后暂停自动轮询并显示“连续失败，点击重试”。
- **状态映射**：  
  - `up`（绿）：显示 `metrics.webhookLatencyMs`、`metrics.queueBacklog`。  
  - `degraded`（黄）：当 latency > 2000ms 或 backlog > 50 时由后端返回；UI 显示警告 + 建议操作。  
  - `down`（红）：显示 `lastError`、`traceId`；提供复制按钮，方便提交给后端。  
  - `unknown`（灰）：未绑定或健康接口异常。
- **心跳超时**：超过 5s 无响应即视为失败，记录在健康卡底部并触发退避。

## 测试消息流程
1. 用户点击“发送测试消息”→ 打开 `ChannelTestPanel`；默认 `chatId` 取自最近一次成功记录（存 localStorage），`payloadText` 默认为 `/ping {workflow_id}`。
2. 表单字段：`chatId`（必填，整数）、`payloadText`（最长 512 字）、`waitForResult`（勾选后 UI 需展示“正在等待执行结果”状态条）。
3. 提交后禁用按钮，调用 `/test`，并记录请求时间。  
4. 收到响应：  
   - `status='success'`：显示“messageId / responseTimeMs”，并在结果列表顶部插入成功记录。若 `waitForResult=true`，继续轮询 Workflow 日志 15s 以确认最终节点状态。  
   - `status='failed'`：显示 `errorCode`、`traceId`，提示用户跳转 Workflow 日志 Tab，记录失败条目并允许复制详情。  
5. **频率限制**：前端在 60s 内最多允许 3 次测试，超过则提示“测试频率超限，请稍后再试”，同时灰掉按钮 30s。

## 交互流程总览
1. **进入 Tab**：若 workflow 未发布，则展示空态卡片（含“去发布”按钮）并禁用表单；若已发布，则触发 `channelStore.fetch(workflowId)` + 健康轮询。
2. **编辑 & 保存**：表单字段变更 → `保存` 按钮亮起 → 校验通过后调用 `PUT` → 更新 store → toast 成功 → 重置脏态。
3. **健康监控**：健康卡每 30s 自动刷新，用户也可点击“立即刷新”；若多次失败则显示暂停提示与“重新开始轮询”按钮。
4. **测试**：调用 `/test` + 可选日志轮询；结果列表展示最近 10 条（可滚动），旧记录自动裁剪。
5. **解绑**：点击“解绑渠道”→ `ElMessageBox` 提示“Telegram 将停止服务”→ 确认后调用 DELETE → 表单恢复空态，健康卡显示“未绑定”。

## Success Path & Core Workflow
1. Workflow 已发布 → 用户打开渠道 Tab → 成功加载 channelPolicy → 表单填充 + 健康卡显示 `status='up'`。
2. 用户修改 token/webhook → 点击“保存” → 前端校验通过 → `channelService.save()` 返回 200 → UI toast “配置已同步”并触发健康刷新。
3. Health Card 轮询成功 → 状态灯绿/黄/红/灰按规则刷新，底部显示“上次检查 09:32:15 / traceId=xxx”。
4. 用户发送测试消息（频率未超限）→ `/test` 返回 success → 结果列表新增记录，并显示 response time；若 waitForResult 选择了 true，则额外提示“workflow 已完成/超时”。
5. 用户解绑 → DELETE 返回 204 → 表单清空、健康卡灰色、测试记录面板锁定，且写入操作日志（在 Workflow 的活动流中展示）。

## Failure Modes & Defensive Behaviors
- **未发布 workflow**：Tab 保持只读，提示“需发布 Workflow 才能绑定 Telegram”，并提供跳转按钮。
- **Token / Webhook 格式错误**：实时校验并在表单下方展示错误描述；保存按钮保持禁用。
- **健康接口异常**：若 3 次连续失败，暂停自动轮询、弹出黄色 Alert，点击“立即重试”才会恢复。
- **测试频率过高**：超过 3 次/分钟则阻止调用，并启动 30s 冷却计时器。
- **测试失败 / Trace 丢失**：记录详细信息（HTTP status、errorCode、traceId），引导用户去日志 Tab；若没有 traceId，则提示“后端未返回 traceId，请联系 SRE”。
- **解绑失败（409）**：如后端提示“Workflow 正在运行”，则将错误提示渲染到弹窗中，不自动关闭。
- **敏感信息泄露防护**：表单中 Token 永不以纯文本显示，复制操作需用户确认；健康日志中禁止打印 Token/Webhook。

## Constraints & Acceptance（GIVEN / WHEN / THEN）
- GIVEN workflow 尚未发布，WHEN 用户打开渠道 Tab，THEN Tab 显示不可编辑提示与“前往发布”按钮，所有输入禁用。
- GIVEN 用户填入符合格式的 Token/Webhook，WHEN 点击“保存”，THEN 请求成功后必须立即刷新健康状态并弹出成功提示。
- GIVEN 健康接口返回 `status='down'`，WHEN UI 渲染健康卡，THEN 状态灯为红色并展示 `lastError` + `traceId`。
- GIVEN 用户在 60 秒内触发第 4 次测试，WHEN 点击提交，THEN 前端阻止请求并提示“测试频率超限”。
- GIVEN 连续 3 次健康轮询失败，WHEN 状态区域刷新，THEN 显示“已暂停轮询”并提供“立即重试”按钮。
- GIVEN 用户确认解绑且后台返回 204，WHEN UI 刷新，THEN 表单恢复空态、健康卡灰色、测试面板禁用，并在 Workflow 活动流记录此操作。
