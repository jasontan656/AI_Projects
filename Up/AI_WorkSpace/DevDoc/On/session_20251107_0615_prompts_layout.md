# Prompts 界面阶段化编排（session_20251107_0615）

## 背景与范围
- 文件：`src/views/PipelineWorkspace.vue`、`src/components/PromptList.vue`、`src/components/PromptEditor.vue`、`src/stores/promptDraft.js`。
- 目标：让 Prompts 标签页复用 Nodes 菜单式体验，提供“开始创建 / 进入管理”入口，统一 UI 构图与交互节奏。
- 范围：仅限前端工作台（Element Plus 布局 + Pinia store），不涉及后端 API 改动。

## 结构重构要点
- 新增 `promptStage`（`menu | create | manage`）与 `ensureCanLeavePromptStage`，入口逻辑与 `nodesStage` 对齐。
- 引入 `PromptSubMenu`（可复用 `NodeSubMenu` 样式），在 `menu` 阶段渲染 CTA 卡片；`create` 阶段强制全屏 `PromptEditor`；`manage` 阶段渲染 `PromptList + PromptEditor` 双列。
- 为 `PromptEditor` 补充 `isDirty()`、`syncBaseline()`、`refresh()`、`newEntry()` 暴露，供阶段守卫调用；`promptDraftStore` 保持 `selectedPromptId`，在阶段切换时驱动 selection。
- 删除提示词或 API 返回空列表时，`PipelineWorkspace` 自动回退到 `menu` 并弹出提示，防止用户停留在空态页面。

## Success Path & Core Workflow
1. 用户进入 Workspace，默认 `activeNav = 'prompts'` 时设置 `promptStage = 'menu'`。`PromptSubMenu` 展示“开始创建”“进入管理”卡片，并根据 `promptStore.promptCount` 自动禁用管理入口。
2. 选择“开始创建” → `setPromptStage('create')` 调用 `promptDraftStore.resetSelection()`、`promptEditorRef.newEntry()`、`promptEditorRef.syncBaseline()`，用户在全屏编辑器填写表单并点击保存；成功后调用 `handlePromptSaved({ promptId })` 自动跳转到 `manage` 并高亮新建项。
3. 选择“进入管理” → 阶段切换为 `manage`，加载 `PromptList`（触发 `listPromptDrafts`）与 `PromptEditor` 分栏视图；侧边列表点击某项会更新 `selectedPromptId` 并将内容映射到编辑器。
4. 头部“新建提示词”按钮在 `manage` 阶段触发 `promptEditorRef.newEntry()`，并将 `promptStage` 维持在 `manage`，用于快速在同一视图新建后返回列表。
5. 用户保存或删除提示词后，界面通过 Pinia store 更新列表；若当前选择项被删除则 fallback 到第一条，若列表为空则自动切回 `menu` 并 toast “暂无提示词，请先创建”。

## Failure Modes & Defensive Behaviors
- **未保存离场**：`ensureCanLeavePromptStage` 检查 `promptEditorRef.isDirty()`；若为真，通过 `ElMessageBox` 提示“提示词草稿尚未保存”，阻止跨阶段或跨导航切换。
- **空列表进入管理**：当 `promptStore.promptCount === 0` 或 `listPromptDrafts` 返回空数组时，强制 `promptStage = 'menu'` 并展示 info message，防止管理视图没有内容。
- **API 异常**：`refreshPrompts` 捕获异常并在菜单/管理阶段分别提示“加载提示词失败”；在错误期间禁用 CTA，避免重复请求。
- **删除后状态错乱**：`handleDeletePrompt` 在成功删除后检查当前选中 ID 与阶段；若删除的是当前项则重置 selection 并尝试选中最新 `promptStore.prompts[0]`，否则保持原状态。
- **并发导航**：在 `activeNav` 切换到其他标签（nodes/workflow）前调用 `ensureCanLeavePromptStage`，统一处理未保存状态，防止 prompts 编辑器残留。

## Constraints & Acceptance (GIVEN / WHEN / THEN)
- GIVEN 用户停留在 `create` 或 `manage` 阶段且编辑器脏数据，WHEN 尝试切换阶段或离开 Prompts 标签，THEN 弹出确认对话框，只有确认后才允许离场。
- GIVEN Prompts API 返回空列表，WHEN 阶段即将切换到 `manage`，THEN 自动回退至 `menu` 并展示“暂无提示词”提示，任何管理按钮保持禁用。
- GIVEN 用户在 `manage` 阶段删除当前选中提示词，WHEN 删除成功回调触发，THEN `promptDraftStore` 重置选中项并（若存在）选中最新一条；若无剩余数据则回退 `promptStage`。
- GIVEN `promptStage = 'manage'` 且用户点击“新建提示词”，WHEN `promptEditorRef.newEntry()` 完成，THEN 保持 `promptStage` 不变但将右侧表单切换为新建态，并在保存成功后将列表自动滚动到新记录。
- GIVEN `promptStage = 'menu'` 且用户点击“进入管理”，WHEN `promptStore.promptCount` 小于 1，THEN 管理卡片显示禁用态与原因文案，避免误导点击。
