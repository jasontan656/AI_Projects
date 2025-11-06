# Proposal: Update Nodes Entry With Submenu Flow

## Background
- 当前 `Nodes` 标签点击后直接展示 NodeList + NodeDraftForm 双列视图，并在 Header 右上角提供“新建节点”按钮。
- `docs/temprompt.md` 要求重新设计交互：点击 `Nodes` 时弹出子菜单，包含“新建节点”“查看已创建节点”。
- 新建节点流程需改为表单全屏显示；管理节点时才展示列表 + 表单双列布局。

## Goals
1. 为 `Nodes` 标签引入子菜单视图，集中展示可选操作。
2. 支持三种视图模式：
   - 子菜单（默认）
   - 全屏新建节点表单
   - 查看节点（列表 + 表单双列）
3. 移除 Header 中的“新建节点”按钮，避免入口重复。
4. 维护现有节点动作、模板选择、LLM gating 等功能不变。
5. 完成后同步更新 `docs/ProjectDev` 相关文档。

## Non-Goals
- 不修改 Prompts/Workflow/Variables/Logs 的交互。
- 不引入额外节点动作类型或后端契约变更。
- 不实现新的权限或多语言支持。

## Deliverables
- Vue 组件更新：`PipelineWorkspace.vue`、`NodeDraftForm.vue`、`NodeList.vue`、可能新增 `NodeSubMenu`。
- 样式与状态管理调整，确保三种视图稳定切换。
- 更新 `docs/ProjectDev/01_layout.md` / `02_nodes.md` 等文档，记录新的结构与交互。
