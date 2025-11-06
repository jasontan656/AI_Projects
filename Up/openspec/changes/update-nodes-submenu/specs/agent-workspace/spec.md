## MODIFIED Requirements

### Requirement: Nodes tab must surface submenu before switching views
- SHALL: 左侧导航点击 `Nodes` 时在导航右侧弹出子菜单（至少包含“新建节点”“查看已创建节点”），主体区域保持当前内容，且不再在 Header 显示“新建节点”按钮。

#### Scenario: Popover submenu on nodes entry
- **GIVEN** 用户点击左侧 `Nodes` 标签
- **THEN** 导航右侧出现包含“新建节点”“查看已创建节点”的悬浮菜单
- **AND** 主体区域维持之前的视图，直到用户选择菜单项
- **AND** 点击空白处或切换其他标签会关闭该菜单。

### Requirement: Nodes view modes must align with submenu selection
- SHALL: 根据子菜单选择在 `PipelineWorkspace` 渲染两种节点视图：
  1. Create：全屏呈现节点表单。
  2. Manage：呈现 `NodeList + NodeDraftForm` 双列界面。

#### Scenario: Switch to create view
- **GIVEN** 子菜单弹出
- **WHEN** 用户选择“新建节点”
- **THEN** 页面切换到全屏节点表单，列表隐藏
- **AND** 表单保存成功后自动切换到 manage 视图并刷新列表。

#### Scenario: Switch to manage view
- **GIVEN** 子菜单弹出
- **WHEN** 用户选择“查看已创建节点”
- **THEN** 页面渲染节点列表与节点表单双列布局
- **AND** 列表支持刷新、删除、选中等现有操作。
