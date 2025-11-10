# 前后端契约对齐指南（阶段一）

## 背景
- 目标：以 Rise 后端当前已实现的接口为基准，确保 Up 前端（Vue + Pinia）提交与消费的字段完全匹配，同时保留前端作为契约事实来源的角色。
- 范围：节点编排（`src/services/pipelineService.js`、`src/components/NodeDraftForm.vue`）与提示词管理（`src/services/promptService.js`、`src/components/PromptEditor.vue`）的请求/响应字段、状态同步流程。
- 前提：后端尚存在占位符实现，前端需避免发送未被识别的字段；后续扩展字段将在新一轮设计中补充。

## 成功路径与核心流程
1. **节点创建 / 更新**
   - 表单提交经 `NodeDraftForm.handleSubmit`（`src/components/NodeDraftForm.vue:204`）组装 payload。
- 后端 DTO `PipelineNodeRequest` 仅接受：`name`、`allowLLM`、`systemPrompt`、`createdAt`，以及可选的 `pipelineId`（≥1 字符）、`status`（`draft|published`）、`strategy`（字典）。额外字段会被忽略。
- 由于 Rise 当前未存储 `actions`，`serializeActionsForApi` 输出仅用于前端内部；在调用 `pipelineService` 时需剥离 `actions` 并只保留按动作生成的 `systemPrompt`。
- 列表接口 `/api/pipeline-nodes` 返回 `ApiResponse` 包裹的 `PipelineNodeListResponse`（含 `page/pageSize/total/items[]`，每个节点带 `latestSnapshot`）。前端解析完成后同步 Pinia store（`src/stores/pipelineDraft.js:20-66`）。
- 写操作需附带 `X-Actor-Id`（可在 `.env` 或本地存储配置），否则 FastAPI 会返回 401；前端请求封装提供本地默认值 `dev-actor` 以便自测。
2. **提示词创建 / 更新**
   - `PromptEditor.handleSubmit`（`src/components/PromptEditor.vue:118-154`）校验名称与 Markdown。
   - `promptService`（`src/services/promptService.js:24-76`）提交 `name`、`markdown`，后端返回最新列表，`promptDraft` store 更新。
3. **契约文档维护**
   - 对应 JSON Schema 位于 `docs/contracts/pipeline-node-draft.json` 与 `docs/contracts/prompt-draft.json`。当后端引入新字段（如未来的 `actions` 持久化）时，需先更新 Schema，再同步 Rise 的 DTO。

## 失败模式与防御策略
- **字段未被后端识别**：`PipelineNodeRequest`/`PromptPayload` 都对字段做强校验；一旦传入空字符串或包含未声明键，将触发 422。前端须在服务层过滤仅允许字段，并验证 `createdAt` 为 ISO 字符串。
- **缺失 Actor Header**：若未提供 `X-Actor-Id` 等标头，后端会以 `UNAUTHENTICATED` 拒绝请求。前端统一通过 `requestJson` 注入默认值，并允许在 LocalStorage (`up.actorId` 等) 覆盖。
- **动作数据丢失**：Rise 暂未持久化 `actions`；若仍从前端提交，数据会被 Backend 忽略。需在 `pipelineService` 将动作转化为 `systemPrompt` 后不再发送 `actions`，并在界面提示“动作仅存于前端草稿”。
- **禁用 LLM 时仍包含提示词动作**：`NodeDraftForm` 已通过 `hasPromptActions` 检测；若用户强行提交，应拒绝保存并提示先移除动作。
- **提示词名称为空**：`PromptPayload` 要求 `name` 长度 ≥1；前端必须在 `PromptEditor` 中强制校验或提供默认值，避免 422。
- **分页参数非法**：`page < 1` 或 `pageSize` 不在 1..100 会触发 `INVALID_PAGE(_SIZE)` 错误；调用列表 API 前需限制 UI 输入。
- **错误信息不统一**：Rise 错误体采用 `{code, message}` 格式。`request()` 的错误解析逻辑应优先读取这两个字段，保证用户能看到后端返回的具体原因。

## 约束与验收检查（GIVEN / WHEN / THEN）
- **节点提交字段**
  - GIVEN 后端仅接受 `name`、`allowLLM`、`systemPrompt`、`createdAt`（可选 `pipelineId/status/strategy`）
  - WHEN 用户在 `NodeDraftForm` 点击保存
  - THEN 请求体不得包含 `actions` 或其他未声明键；否则拦截并提示“动作仅在前端草稿中保存”。
- **动作配置扩展**
  - GIVEN 后端尚未保存动作，未来计划增加 `actions` 字段
  - WHEN 我们更新 `nodeActions.sanitizeConfig`、契约 JSON 及 Rise DTO
  - THEN 必须同步发布到前后端，确保 `actions` 落库后再开放 UI 操作。
- **提示词校验**
  - GIVEN 后端将 `name` 设为必填
  - WHEN `PromptEditor` 触发 `handleSubmit`
  - THEN 若名称为空，前端必须阻止提交并显示错误。
- **响应格式**
  - GIVEN 后端确定列表接口统一返回 `{ items: [], total: n }`
  - WHEN `fetchNodes` / `fetchPrompts` 解析响应
  - THEN 只能依赖该结构；若检测到旧格式，记录告警并提示升级。

## 后续工作
- 已获取 Rise DTO 定义，需在 `pipelineService`/`promptService` 添加字段白名单与日期格式校验，避免无效数据到达后端。
- 提供 `.env` 入口与 LocalStorage fallback 维护 Actor 信息，便于无后端认证模块时的本地调试。
- 准备下一阶段设计输入：扩展 `strategy` 枚举、动作类型配置、日志/变量真实 API 对接。
