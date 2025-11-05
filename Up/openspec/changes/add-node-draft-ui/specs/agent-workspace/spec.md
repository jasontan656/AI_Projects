## ADDED Requirements

### Requirement: Nodes tab drafting workspace
- SHALL: PipelineWorkspace 在左侧导航中提供「Nodes」标签，标签内容以全幅表单呈现节点基础字段与动作列表，并将保存结果写入 Pinia pipelineDraft.nodes 和契约快照。

#### Scenario: Compose node within Nodes tab
- **GIVEN** 用户通过侧边栏进入 PipelineWorkspace
- **WHEN** 在默认选中的「Nodes」标签填写名称、切换 llowLLM、添加动作并点击“保存节点”
- **THEN** Pinia pipelineDraft.nodes 新增一条带有 ctions 数组的草稿
- **AND** docs/contracts/pipeline-node-draft.json 更新为包含最新草稿字段。

### Requirement: Prompt hub isolation
- SHALL: 「Prompts」标签提供模板列表、Codemirror 编辑器与只读预览，保存需显式触发按钮，不得与节点表单共享自动保存逻辑。

#### Scenario: Manage prompt inside Prompts tab
- **GIVEN** 用户切换到「Prompts」标签
- **WHEN** 选择模板并编辑内容后点击“保存模板”
- **THEN** Pinia promptDraft.prompts 更新对应条目并刷新 docs/contracts/prompt-draft.json
- **AND** 模板预览区显示 Markdown 渲染结果，编辑器仍保留最新内容。

### Requirement: Navigation skeleton with variables and logs
- SHALL: 左侧导航至少列出 Nodes、Prompts、Workflow、Variables、Logs、Settings，并为未完成模块提供占位区域，包括变量树搜索与日志流提示。

#### Scenario: Switch between modules
- **GIVEN** 用户点击「Variables」或「Logs」导航项
- **THEN** 主面板展示相应占位：变量面板显示搜索框与空状态，日志面板显示“等待连接”提示与重试操作。

### Requirement: Contract snapshots for nodes and prompts
- SHALL: 节点与提示词草稿保存时同步刷新 docs/contracts/pipeline-node-draft.json 与 docs/contracts/prompt-draft.json，与 Pinia 状态保持一致。

#### Scenario: Export latest contracts
- **GIVEN** 用户分别保存节点和提示词草稿
- **WHEN** 查看对应契约文件
- **THEN** 文件内容与最新编辑结果匹配，包括 ctions、模板字段与时间戳。
