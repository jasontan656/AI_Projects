# Rise ↔ Up 对接能力报告（2025-11-09）

## 1. 背景
- 目标：让 Rise 后端（Telegram 队列、Workflow Orchestrator）与 Up 前端（节点/提示词工作台）形成可发布、可测试、可回退的闭环，支持 Telegram Bot 在生产环境稳定触发。
- 现状：Rise 后端已实现 Telegram 入口排队、Redis+Rabbit 双写、workflow 执行链；Up 前端提供节点/提示词创建，但缺少 workflow 可视化与渠道绑定能力。

## 2. 当前能力
### 2.1 后端（Rise）
- **入口**：`src/business_service/conversation/service.py` 现已无条件封包 Telegram update，写入 Redis Streams + Rabbit quorum queue，支持 workflow 缺失时标记 `workflow_pending`。
- **队列/Worker**：`src/foundational_service/persist/worker.py` 将任务交由 `WorkflowTaskProcessor`，并在 Rabbit 失败时仅记录事件，保证 Redis 主链不中断。
- **契约**：`docs/contracts/prompt-draft.json`、`pipeline-node-draft.json` 描述的 Prompt/Node 结构可直接落库，workflow 构建仍需额外逻辑。

### 2.2 前端（Up）
- **节点/提示词工作台**：`src/views/PipelineWorkspace.vue` 提供菜单→创建→管理三阶段体验，`PromptEditor.vue`、`NodeDraftForm.vue` 已具备 CRUD、未保存守卫。
- **API 层**：`src/services/promptService.js`、`pipelineService.js` 针对 `/api/prompts`、`/api/pipeline-nodes`，使用 `requestJson` 自动附加 Actor 头；`.env.development` 默认指向 `http://localhost:8000`，可通过部署变量切换。
- **契约匹配**：列表/编辑器遵循 docs/contracts 描述的字段，前端输出可直接对接 Rise 后端。

## 3. 缺口与影响
| 缺口 | 影响 | 说明 |
| --- | --- | --- |
| Workflow Builder 缺失 | 无法在前端组合节点 + 提示词生成 workflowId | 目前必须依赖后端脚本或 DB 操作，前端无法确认发布结果，也无法重复利用配置。|
| 渠道/Telegram 绑定视图缺失 | 无法声明“workflow X 服务 Telegram channel” | Rise 需要 workflow policy（timeout、entry config、channel），前端无表单；Telegram Bot 无法受控发布/下线。|
| 发布/回滚流程缺失 | 无 CI/CD 标识，运维难以追踪 | 没有“发布 workflow”“回滚版本”“触发测试消息”的按钮，出问题只能改 DB。|
| 错误可观测性弱 | 联调期间难以定位异常 | `requestJson` 抛错后 UI 缺少统一 toast；Prompt/Node 保存失败时只在控制台有日志。|
| 工具/变量/Workflow 视图未实现 | 无法配置更复杂流程 | NodeActionList 仅支持 prompt append；其他 nav（workflow、variables、logs）标记为 “Soon”。|

## 4. 实施建议
### 4.1 第一阶段：Workflow Builder + 发布入口
1. **Workflow 列表/详情**：显示 workflow 状态（draft/published）、绑定节点、提示词引用、创建人、最后发布人。存储结构建议复用后端 `workflows` 集合字段，前端需新增 store + service。
2. **Workflow 编辑器**：允许从 node/prompt store 选择资源，设置执行顺序和策略（重试、timeout、channel metadata）。可先用表单/列表方式，后续再引入可视化画布。
3. **发布/回滚操作**：Workflow 详情页提供“发布”“回滚到上一版”，调用后端 `/api/workflows/{id}/publish` 等接口；返回成功后刷新状态并记录操作日志。
4. **错误提示规范**：封装 `useApiFeedback()`，统一处理 `requestJson` 错误，在顶部提示条与 Element Plus Message 中展示。

### 4.2 第二阶段：渠道与 Telegram 绑定
1. **Channel Policy 表单**：在 Workflow 详情页新增 “渠道设置” Tab，配置 Telegram bot token、webhook URL、entry config（wait_for_result、workflow_missing 文案等），直接调用 Rise 新增的 `/api/workflow-channels`。
2. **健康状态展示**：展示 `telegram_webhook`、`task_runtime` 能力状态（可调用 Rise `/internal/capabilities`），在 UI 上显示绿/黄/红灯；提供“触发测试消息”按钮。需要后端暴露测试接口（例如 `/api/channels/telegram/test`）。

### 4.3 第三阶段：日志与可视化
1. **Workflow Logs**：嵌入 SSE/WebSocket，将 Rise 侧 `task_worker` 日志/metrics 拉到前端展示，便于调试 Telegram 任务。
2. **变量、工具、模板扩展**：逐步开放 Variables/Tools 标签，支持更多 orchestrator 功能。

## 5. 防御性考虑
- **权限控制**：发布/绑定操作需校验 Actor 角色（`ops-admin`）。可在前端基于 `X-Actor-Roles` 做简易门控，后端再做最终鉴权。
- **未保存守卫**：Workflow Builder 需沿用 Prompts/Nodes 的 `isDirty` 机制，防止半成品被误发布。
- **回滚策略**：发布前自动保存 workflow snapshot（含节点/提示词版本），便于出问题时快速回退。
- **环境配置**：联调/生产需明确 `VITE_API_BASE_URL`、Actor/Tenant 变量，并在 README/Docs 记录如何修改。

## 6. 里程碑建议
1. **M1（1-2 周）**：完成 Workflow 列表 + 编辑表单 + 发布按钮；后端补 `/api/workflows` CRUD。
2. **M2（2 周）**：上线渠道绑定 UI、测试按钮；后端暴露 channel API 与健康检查。
3. **M3（2+ 周）**：Workflow 日志、可视化画布、变量/工具扩展，打磨 UX 并为更多外部渠道铺路。

完成 M1+M2 后，即可在前端配置 workflow、绑定 Telegram、触发测试，实现“正确流程触发 Bot”。M3 作为增强阶段，用于持续改进操作体验与可 observability。
