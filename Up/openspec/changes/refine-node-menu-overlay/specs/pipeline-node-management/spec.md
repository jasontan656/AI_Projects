## MODIFIED Requirements

### Requirement: Nodes view exposes menu/create/manage states
- SHALL: 节点视图状态包含 `menu`、`create`、`manage` 三种模式；默认进入 `menu`，并通过用户选择触发后续模式。
- SHALL: `menu` 模式仅渲染节点操作面板，不加载节点列表或表单资源。

#### Scenario: Enter create from menu
- **GIVEN** 当前处于 `menu` 模式
- **WHEN** 用户选择“新建节点”
- **THEN** 状态切换到 `create`
- **AND** 全屏节点表单渲染并初始化为新建状态
- **AND** 保存成功后切换到 `manage` 并刷新节点列表。

#### Scenario: Enter manage from menu
- **GIVEN** 当前处于 `menu` 模式
- **WHEN** 用户选择“查看已创建节点”
- **THEN** 状态切换到 `manage`
- **AND** 渲染 NodeList + NodeDraftForm 双列界面，保持既有操作（刷新、选择、删除）。

#### Scenario: Return to menu
- **GIVEN** 当前处于 `create` 或 `manage` 模式
- **WHEN** 用户点击“返回节点菜单”或通过其他入口回到菜单
- **THEN** 状态切换到 `menu`
- **AND** 主区域再次展示节点操作面板。
