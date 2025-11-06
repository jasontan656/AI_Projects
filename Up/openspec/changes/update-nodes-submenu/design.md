# Design Notes

## 状态切换
- 在 `PipelineWorkspace` 增加 `const nodesViewMode = ref("manage")`。
- 提供 `enterNodesMenu()`（仅负责弹出子菜单）、`startCreateNode()`、`startManageNodes()`。
- 监听路由或导航选择：
  - 点击左侧 `Nodes` 时弹出子菜单，主体视图保持不变；
  - 选择子菜单项进入对应模式，关闭子菜单。
- 节点保存成功后调用 `startManageNodes()` 并刷新列表。

## 子菜单呈现
- 使用 `NodeSubMenu` 组件，通过绝对定位的悬浮卡片锚定在 `Nodes` 菜单右侧，点击外部关闭。

## 布局调整
- `workspace-pane--two-column` 仅在 manage 模式启用。
- create 模式中，将 `NodeDraftForm` 包裹在自适应容器内（宽度控制在 960px 以内）。
- 工具栏提供“返回节点菜单”按钮，方便再次唤起悬浮菜单。

## 组件改动
- `NodeDraftForm` 接收 `layout` prop（`full`/`split`），控制宽度与边距。
- `NodeList` 仅在 manage 下渲染，避免无数据时空白。
- `NodeSubMenu` 组件内置两个按钮（新建/查看），选择后发出事件供父组件切换视图。

## 文档同步
- 调整 ProjectDev 文档，描述悬浮子菜单与两种视图流程。
- 同步 temprompt.md 中提及的更改事项，确保所有 bullet 覆盖。
