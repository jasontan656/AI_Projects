## MODIFIED Requirements

### Requirement: Nodes entry opens main-area selection panel
- SHALL: 左侧导航点击 `Nodes` 时，在工作区主区域（右侧面板）渲染节点操作面板，而非侧边浮层；面板至少包含“新建节点”“查看已创建节点”。
- SHALL: 面板在用户明确选择操作或切换到其他导航标签前保持显示，主区域不预先加载 create/manage 内容。

#### Scenario: Render main panel on nodes click
- **GIVEN** 用户当前不在 `Nodes` 视图
- **WHEN** 点击左侧导航 `Nodes`
- **THEN** 主区域显示节点操作面板，突出“新建节点”“查看已创建节点”两个操作
- **AND** 工作区标题与描述更新为节点上下文，但不加载节点表单或列表。

#### Scenario: Exit panel on selection
- **GIVEN** 节点操作面板已显示
- **WHEN** 用户选择其中任一操作
- **THEN** 面板关闭并切换至对应视图
- **AND** 再次点击“返回节点菜单”或重新点击 `Nodes` 导航会恢复该面板。

#### Scenario: Close panel on nav change
- **GIVEN** 节点操作面板已显示
- **WHEN** 用户切换到其他导航标签
- **THEN** 节点操作面板关闭，主区域切换到目标标签内容。
