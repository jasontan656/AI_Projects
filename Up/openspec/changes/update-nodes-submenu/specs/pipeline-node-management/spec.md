## MODIFIED Requirements

### Requirement: Node list availability is limited to manage view
- SHALL: 节点列表组件仅在 manage 视图渲染，与节点表单双列展示；create 视图不加载列表资源。

#### Scenario: Hide list in create view
- **GIVEN** 用户通过子菜单进入“新建节点”视图
- **THEN** 页面不渲染 NodeList，节点表单占据主要内容区域
- **AND** 所有节点相关操作（删除、刷新）保持不可见。

### Requirement: Node form must adapt to view mode
- SHALL: `NodeDraftForm` 在 create 视图下以全屏布局呈现，在 manage 视图下与列表并排显示，同时维持动作编排与 LLM gating 逻辑。

#### Scenario: Full width form in create view
- **GIVEN** 当前处于 create 视图
- **THEN** 表单宽度扩展至容器允许的最大值（不限制在 720px）
- **AND** 保存成功后触发切换至 manage 视图并刷新节点列表。

#### Scenario: Paired form in manage view
- **GIVEN** 当前处于 manage 视图
- **THEN** 表单保持原有宽度约束，与列表维持双列布局，不影响动作编辑、模板选择等功能。
