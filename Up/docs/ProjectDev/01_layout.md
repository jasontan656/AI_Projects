# 布局与导航结构

## 1. 路由与入口
- `src/router/index.js` 中仅注册 `/pipelines`，所有界面挂载在 `PipelineWorkspace.vue`。
- 默认访问 `/` 会被 redirect 至 `/pipelines`。

## 2. 页面骨架（PipelineWorkspace.vue）
```
el-container
 ├─ el-aside (248px)
 │   └─ el-menu → 左侧导航
 └─ el-container
     ├─ el-header → 顶部标题 / 操作区
     └─ el-main   → 各功能模块
```

### 2.1 左侧导航
- Element Plus `el-menu-item` 顺序：Nodes, Prompts, Workflow, Variables, Logs, Settings。
- 点击 `Nodes` 会在导航右侧弹出 `NodeSubMenu`（悬浮卡片），但不立即改变主体区域；其它标签依旧是常规内容切换。
- 子菜单提供“新建节点”“查看已创建节点”两个入口，后续可扩展更多操作。点击空白区域或切换其他标签会关闭子菜单。

### 2.2 顶部 Header
- `workspace-title-row` 组合标题、标签（uppercase）与描述。
- 主操作按钮仅在 `Prompts` 模块下展示“新建提示词”；`Nodes` 的新建入口已移动到子菜单。

### 2.3 主体区域
- `workspace-pane` 为每个模块的容器。
- Nodes 模块由子菜单动作驱动两种主视图：
  1. **create**：节点表单居中全屏显示，隐藏 NodeList；
  2. **manage**：展示 NodeList + NodeDraftForm 双列布局，并保留顶部“返回节点菜单”操作。
- Prompts 模块仍使用 CSS Grid：`grid-template-columns: 320px minmax(0,1fr)`；其他模块为单列布局。

## 3. 响应式处理
- `@media (max-width: 1200px)`：双列布局自动降级为单列堆叠。
- `@media (max-width: 960px)`：
  - `el-aside` 变成水平分布；
  - Header 转为纵向排布；
  - 主体保持单列，避免窄屏拥挤。

## 4. 样式约定
- 颜色、间距等设计 token 由 `src/styles/tokens.css` 提供。
- 阴影统一使用 `var(--shadow-panel)`，确保节点/提示词列表卡片视觉一致。
- 标题说明组合统一 ellipsis，防止中文被背景覆盖。

## 5. 扩展建议
1. 将导航抽象为独立组件，便于未来添加权限控制或徽标。
2. Header 操作按钮改为配置化（根据模块注入 actions），提升扩展性。
3. 对移动端进一步适配：折叠侧栏、使用抽屉式导航。
4. 可考虑为各模块引入面包屑或辅助提示，提高可发现性。
