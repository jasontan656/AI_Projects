# 节点菜单右侧弹出重构设计

## 背景与目标
- 用户在侧栏点击 `Nodes` 后，期望右侧主内容区首先展示操作子菜单（如“新建节点”“查看已建节点”），而非立即进入某个具体子流程。
- 本重构旨在以阶段化状态驱动节点工作流，使菜单、创建、管理等界面在主区域内顺畅切换，并为未来扩展其他节点操作提供统一入口。

## 现状诊断
- `src/views/PipelineWorkspace.vue` 仅通过 `nodesMenuVisible` 控制一个绝对定位的 `<NodeSubMenu>` 浮层，主区域仍保持上一次的 `nodesViewMode` 内容，导致动线与用户预期不符。
- `NodeSubMenu.vue` 是静态卡片，缺乏可扩展的操作模型，且未与主内容布局联动。
- `enterNodesMenu`、`handleMenuClick` 等逻辑只切换浮层显示，未重置 `pipelineDraftStore` 选中节点，也没有处理创建草稿与返回菜单之间的状态一致性。
- 文档级别的 `click` 监听与窗口尺寸监听只服务于浮层定位，一旦改为主区域渲染将变成冗余与潜在异常源。

## 方案概述
- **阶段状态机**：在 `PipelineWorkspace` 引入 `nodesStage`（取值 `menu | create | manage`），初始为 `menu`，点击菜单项或按钮再切换到对应阶段；原 `nodesViewMode` 可删除或兼容映射。
- **主区域布局**：使用条件渲染在 `.workspace-main` 内输出三段视图：菜单卡片、创建表单、管理双栏；移除侧栏绝对定位弹层及相关事件监听。
- **子菜单组件再设计**：`NodeSubMenu` 改为接收操作列表 `actions`（包含 `id`、`label`、`description`、`icon`、`stage`、`guard` 等字段），内部按数组渲染按钮，并发出统一的 `select` 事件，由父级决定后续行动。
- **事件流统一**：将“返回节点菜单”按钮、更高层导航切换、节点保存完成等动作统一调用 `setNodesStage('menu' | ...)`，并在阶段切换时同步调整 Pinia store。
- **状态协同**：进入 `menu` 阶段时调用 `pipelineDraftStore.resetSelection()` 清空选中项；进入 `manage` 时刷新节点列表；进入 `create` 时调用 `nodeFormRef.newEntry()` 初始化草稿。

## 组件与数据结构调整
- `src/views/PipelineWorkspace.vue`
  - 新增 `nodesStage`、`nodeActions` 响应式变量与 `setNodesStage` 方法。
  - 将 `NodeSubMenu` 迁移到主内容区的 `v-if="nodesStage === 'menu'"` 容器内。
  - 调整 `handleMenuClick('nodes')` 为仅设置 `nodesStage = 'menu'` 并取消浮层定位逻辑；其他导航保持现有流程。
  - 在节点保存、删除、切换导航的钩子中根据需返回的阶段调用 `setNodesStage`。
- `src/components/NodeSubMenu.vue`
  - 接收 `actions` props，默认包含“新建”“管理”两项，可扩展。
  - 以 `el-card` + `el-button` 渲染操作并暴露 `select(action)` 事件；支持禁用、描述说明、图标插槽。
  - 补充键盘可达性（`@keyup.enter`）与 `aria` 属性，提升可访问性。
- `src/components/NodeList.vue`
  - 根据 `nodesStage` 决定是否渲染；在菜单态无需显示列表，可通过父级包裹条件渲染。
  - 删除节点后，如当前阶段是 `manage` 且列表为空，可回退到 `menu` 阶段。

## 成功路径与核心流程
1. 初始加载 `activeNav = 'nodes'` 时调用 `setNodesStage('menu')`，右侧展示 `NodeSubMenu`，`pipelineDraftStore` 中 `selectedNodeId` 被重置。
2. 用户点击“新建节点”操作，`NodeSubMenu` 发出 `select('create')`，父级调用 `startCreateNode()`：设置阶段为 `create`、重置选中节点并初始化表单，右侧渲染全宽 `NodeDraftForm`。
3. 用户提交表单成功后触发 `handleNodeSaved`，调用 `startManageNodes({ nodeId })`：阶段切换为 `manage`，刷新节点列表并定位新节点。
4. 在管理视图中，左列 `NodeList` 展示节点，右列 `NodeDraftForm` 可编辑，顶部“返回节点菜单”按钮调用 `setNodesStage('menu')`，恢复到入口菜单。

## 失败模式与防御行为
- **未保存草稿被覆盖**：在 `nodesStage === 'create'` 且表单存在脏数据时，若用户再次选择“新建”或返回菜单，需弹出确认对话框或启用草稿缓存，避免误丢数据。
- **空数据管理态**：删除最后一个节点后保留在 `manage` 会出现空界面，需检测 `pipelineStore.nodes.length === 0` 时强制回到 `menu` 并提示“暂无节点，请先新建”。
- **快速切换导航**：从 `nodes` 切到其他导航再返回时应调用 `setNodesStage('menu')`，确保不会残留旧的 `create`/`manage` 界面。
- **接口异常回滚**：节点保存或删除接口报错时保持原阶段不变，并通过 Element Plus 消息提示用户，防止界面提前跳转造成错觉。
- **小屏幕折叠**：在 ≤960px 布局下，菜单卡片需占满宽度且可以滚动；必要时使用 `el-scrollbar` 包装，避免内容溢出。

## 约束与验收检查
- GIVEN 用户位于 `Nodes` 导航且 `pipelineStore.nodes` 为空
  WHEN 页面加载完成
  THEN 主区域显示节点菜单卡片，提示可新建节点，无残留的列表或表单。
- GIVEN 用户点击菜单中的“新建节点”
  WHEN 节点表单初始化成功
  THEN 阶段切换为 `create`，`selectedNodeId` 被清空，表单进入草稿状态。
- GIVEN 用户处于管理视图并删除最后一个节点
  WHEN 删除接口返回成功
  THEN 阶段自动回到 `menu`，并显示“暂无节点”文案提醒继续创建。

## 后续演进建议
- 扩展 `nodeActions` 模型，支持权限过滤、图标集成及自定义说明，满足批量操作、导入导出等场景。
- 引入统一的阶段状态守卫（如基于路由或 Pinia），保证在外部模块触发节点流程时也能复用同一套状态机。
- 编写针对阶段切换的组件测试（Vitest + Vue Test Utils），覆盖空数据、草稿未保存提示以及导航往返等关键路径。
