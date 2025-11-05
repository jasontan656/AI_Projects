## MODIFIED Requirements

### Requirement: Node Draft Creation UI
- SHALL: 节点草稿创建与编辑界面在 `PipelineWorkspace` 的「Nodes」标签页呈现，并内嵌节点动作编排入口，保存时写入 Pinia `pipelineDraft.nodes` 以及最新 `actions` 契约。

#### Scenario: Compose node within Nodes tab
- **GIVEN** 用户通过侧边栏进入 `PipelineWorkspace`
- **WHEN** 切换到「Nodes」标签并点击“新建节点”
- **THEN** 表单在标签内容区展示元素（Element Plus 表单 + 动作列表组件），允许配置 `allowLLM`、节点元数据与 `actions`
- **AND** 点击保存后 Pinia 中的节点草稿包含 `actions` 数组并刷新 `docs/contracts/pipeline-node-draft.json`

### Requirement: Prompt Template Hub Separation
- SHALL: 提示词模板管理独立于节点表单，放置在「Prompts」标签页，提供模板列表、详情预览与保存按钮，避免与节点编辑共享同一表单或自动保存。

#### Scenario: Manage prompt inside Prompts tab
- **GIVEN** 用户在侧边栏点击「Prompts」
- **WHEN** 选择某个模板并进入编辑视图
- **THEN** 页面展示模板列表 + 只读预览 + Codemirror 编辑器，提交时需要显式点击“保存模板”按钮
- **AND** 保存成功后 Pinia `promptDraft.prompts` 更新并同步刷新 `docs/contracts/prompt-draft.json`

### Requirement: Variables and Logs modules
- SHALL: 「Variables」标签页展示 Redis/运行时变量树（可搜索、可复制），「Logs」标签页提供实时流日志列表，并在无后端连接时展示占位提示。

#### Scenario: Inspect runtime variables
- **GIVEN** 用户切换到「Variables」标签
- **WHEN** 输入搜索关键字
- **THEN** 面板过滤变量树并允许复制值到剪贴板，未命中时给出空状态提示。

#### Scenario: Stream node logs
- **GIVEN** 用户切换到「Logs」标签
- **WHEN** 系统建立 WebSocket/SSE 连接
- **THEN** 日志流以按时间排序的列表显示，支持暂停/恢复；连接失败则显示重试按钮和占位说明。

### Requirement: Workspace Navigation Layout
- SHALL: `PipelineWorkspace` 保持左侧导航和顶部标签结构，至少包含 Nodes、Prompts、Workflow、Variables、Logs、Settings 导航项，并默认聚焦 Nodes 标签。

#### Scenario: Navigation matches project standard
- **GIVEN** 新用户打开 `PipelineWorkspace`
- **THEN** 侧边栏显示上述六个模块项且 Nodes 处于选中状态
- **AND** 切换任一模块会在主面板呈现对应占位或功能区，为后续模块实现提供固定骨架。
