# Workflow Builder & 发布入口（session_20251109_0149）

## 背景与范围
- **目标**：在 Up 前端提供 Workflow 列表、详情与编辑体验，可组合节点/提示词、配置执行策略并触发发布/回滚，完成报告 M1 交付。
- **范围**：
  - 新增 Workflow store/service（Pinia + `src/services/workflowService.js`）对接 Rise `/api/workflows`、`/api/workflows/{id}/publish`、`/rollback`。
  - 在 `src/views` 下新增 Workflow Builder 视图（可沿用 `PipelineWorkspace` 外壳或拆分路由），支持 Draft → Published 状态切换。
  - 与现有 `NodeDraftForm.vue`、`PromptEditor.vue` 共用数据：Workflow 选择已有节点、提示词引用，不直接在 Builder 内编辑节点。
  - 前后端契约参考 Rise `docs/contracts/pipeline-node-draft.json`、`prompt-draft.json` 以及 workflow schema（需与后端确认字段）。
- **不包含**：渠道策略、Telegram 绑定（归入 M2 文档）；实时日志与变量/工具扩展（M3 文档）。

## 信息结构与组件
| 组件/文件 | 角色 | 说明 |
| --- | --- | --- |
| `src/stores/workflowDraft.js` | Pinia Store | 保存 workflow 列表、当前选中项、临时编辑态、发布记录。 |
| `src/services/workflowService.js` | API 层 | 封装 list/create/update/delete/publish/rollback，沿用 `requestJson`。 |
| `src/views/WorkflowBuilder.vue` | 视图容器 | 复用 `workspace-shell`，提供菜单 → Builder → 发布记录 Tabs。 |
| `src/components/WorkflowList.vue` | 左侧列表 | 展示 workflow 名称、状态、最新发布人/时间；支持搜索、删除。 |
| `src/components/WorkflowEditor.vue` | 右侧编辑器 | 允许选择节点顺序、提示词引用、执行策略（重试、timeout、并发）。 |
| `src/components/WorkflowPublishPanel.vue` | 发布与回滚 | 显示当前版本、差异、发布按钮、回滚历史。 |

### 数据关系
```
workflow {
  id,
  name,
  status: 'draft' | 'published',
  version,
  nodeSequence: [nodeId],
  promptBindings: [{ nodeId, promptId }],
  strategy: { retryLimit, timeoutMs },
  metadata: { description, tags }
}
```
- `nodeSequence` 与 `promptBindings` 引用 `pipelineStore.nodes`、`promptDraftStore.prompts`；保存前需校验引用是否合法。
- 发布时提交 `workflowId + targetVersion`，后端生成 snapshot；回滚调用 `/api/workflows/{id}/rollback?version=`。

## 交互流程
1. **进入 Workflow 菜单**  
   - 通过 `PipelineWorkspace` 新增导航项或独立路由 `/workflows`。  
   - 初始化加载 workflow 列表，自动选中第一条或空态提示。
2. **创建 Workflow**  
   - 点击“新建 Workflow”进入编辑视图，填写名称、描述，拖拽/选择节点顺序，绑定提示词与策略。  
   - 保存后回到列表，状态为 Draft。
3. **编辑/预览差异**  
   - 选中 workflow 时右侧显示当前配置，可切换到“发布记录”Tab 查看历史版本、diff（至少列出 version、操作人、时间）。  
4. **发布**  
   - 点击“发布”→ 弹出确认框，展示将要执行的节点/策略摘要，确认后调用 `/publish`。  
   - 发布成功后刷新状态（`status = published`，`version++`），记录操作日志。
5. **回滚**  
   - 在历史版本列表选择条目 → “回滚到此版本”，弹窗确认 → 调 `/rollback`。  
   - 回滚成功后提示“已恢复至 vX”，并刷新编辑器数据。

## Success Path & Core Workflow
1. **列表加载**：进入 Workflow 菜单，`workflowStore.fetchList()` 成功返回→ 左列渲染 && 右侧选中第一条或空态卡片。
2. **新建/保存**：用户在 `WorkflowEditor` 填写必填字段并点击“保存草稿”→ `workflowService.create/update` 成功 → store 更新 → toast “保存成功”。
3. **发布**：点击“发布”→ 校验编辑器无脏数据→ 调用 `/publish` → store 更新状态/版本 → 发布记录表追加记录。
4. **回滚**：在发布记录中选定版本→ 调用 `/rollback` → store 重载 workflow → toast “回滚完成”。
5. **引用校验**：保存/发布前校验 `nodeSequence`、`promptBindings` 均引用现有 ID，若节点被删除需即时提示并阻止提交。

## Failure Modes & Defensive Behaviors
- **未保存离场**：`WorkflowEditor` 需实现 `isDirty()`，在切换 workflow、跳离页面或尝试发布时弹出确认。
- **引用失效**：若 `nodeSequence` 中包含已删除节点，UI 应在列表项展示警告并禁用发布按钮，提示用户修复。
- **发布失败**：捕获 `/publish` 错误代码（如 409 版本冲突、422 校验失败），在 `WorkflowPublishPanel` 显示详细信息并保留草稿。
- **并发编辑**：若后端返回版本冲突，应提示“已有更新，需刷新后再编辑”，并提供“刷新”按钮。
- **删除保护**：禁止删除已发布 workflow，或在删除前确认“将同时撤销渠道绑定”；后端返回 409 时需照实呈现。

## Constraints & Acceptance (GIVEN / WHEN / THEN)
- **GIVEN** 用户在 Workflow 编辑器修改数据但未保存，**WHEN** 切换列表项或导航离开，**THEN** 弹出确认框，取消则留在当前视图。
- **GIVEN** workflow 包含失效节点/提示词引用，**WHEN** 用户点击“发布”，**THEN** 阻止请求并显示“请先修复引用”提示。
- **GIVEN** 后端返回发布冲突（409），**WHEN** 用户查看发布面板，**THEN** 面板内显示冲突原因并提供“刷新数据”按钮。
- **GIVEN** 用户在发布记录中选择版本，**WHEN** 点击“回滚”，**THEN** 要求再次确认并在成功后 toast + 写入操作日志。
- **GIVEN** workflow 列表为空，**WHEN** 进入 Workflow 菜单，**THEN** 显示空态卡片和“创建 Workflow” CTA，不渲染无意义面板。
