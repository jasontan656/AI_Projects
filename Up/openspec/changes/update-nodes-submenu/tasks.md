# Tasks

1. ✅ 审查现有 `PipelineWorkspace`、`NodeDraftForm`、`NodeList` 状态逻辑，列出需要拆分的视图与依赖。
2. ✅ 在 `PipelineWorkspace` 中新增 `nodesViewMode`（create/manage）及切换方法，默认进入 manage；移除 Header 的“新建节点”按钮。
3. ✅ 实现子菜单组件 `NodeSubMenu`，以悬浮卡片形式锚定在 `Nodes` 菜单右侧，提供“新建节点”“查看已创建节点”并绑定切换。
4. ✅ 调整主体布局：
   - create 模式渲染居中全屏 `NodeDraftForm`。
   - manage 模式保留 `NodeList + NodeDraftForm` 双列。
5. ✅ 更新 `NodeDraftForm`、`NodeList` 的样式与渲染逻辑，使其在不同模式下正常工作；确保保存成功后自动切换到 manage。
6. ✅ 回归测试节点创建、模板选择、LLM gating、节点删除等流程；执行 `npm run build`。
7. ✅ 更新 `docs/ProjectDev/01_layout.md` 与 `docs/ProjectDev/02_nodes.md`，记录新的子菜单与视图说明。
