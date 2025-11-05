# Pipeline Node Management

## ADDED Requirements

### Requirement: Actions replace legacy systemPrompt
- SHALL: 节点创建/编辑流程以 ctions[] 取代自由文本 systemPrompt，结构与 docs/contracts/pipeline-node-draft.json 保持一致。

#### Scenario: Save node with scripted actions
- **GIVEN** 用户在节点表单添加动作
- **WHEN** 点击保存
- **THEN** 请求 payload MUST 包含每个动作的 id、	ype、order、config，且移除裸文本 systemPrompt
- **AND** 若加载旧节点仅有 systemPrompt，页面自动生成单个 prompt_append 动作并提示迁移。

### Requirement: LLM gating disables prompt actions
- SHALL: 当 llowLLM 为 false 时，需要禁用或移除 prompt_append 动作，并阻止携带该动作的节点保存。

#### Scenario: Block prompt actions when LLM disabled
- **GIVEN** 动作列表存在 prompt_append
- **WHEN** 用户关闭“允许访问大模型”
- **THEN** prompt_append 条目标记为禁用且保存操作显示错误提示，直到动作被删除或重新启用 LLM。

### Requirement: Action ordering controls and context menu
- SHALL: 动作列表提供显式“上移/下移”按钮维持顺序，并支持右键快捷菜单打开动作设置或跳转配置。

#### Scenario: Reorder actions via buttons
- **GIVEN** 列表包含至少两个动作
- **WHEN** 用户点击某动作的“上移”按钮
- **THEN** 该动作与上一条交换顺序，order 字段连续更新为 0..n-1。

#### Scenario: Open action context menu
- **GIVEN** 用户右键点击动作条目
- **WHEN** 弹出快捷菜单
- **THEN** 菜单包含“查看设置”等选项，用于打开动作详情面板或跳转至配置标签。

### Requirement: Action config schema alignment
- SHALL: config 字段仅暴露契约允许的键（	emplateId、legacyText、inputMapping、disabled），并按类型执行校验。

#### Scenario: Validate prompt_append config
- **GIVEN** 用户为 prompt_append 选择模板
- **THEN** config.templateId 记录所选模板 ID，legacyText 为空
- **AND** 未选择模板时保留 legacyText 提示文本，同时仍符合契约结构。

### Requirement: Prompt template store reuse and preview
- SHALL: 提示词动作复用 promptDraftStore 数据源列出模板，并通过只读 Markdown 预览呈现内容。

#### Scenario: Select and preview template
- **GIVEN** promptDraftStore 已加载模板列表
- **WHEN** 用户下拉选择模板并打开预览
- **THEN** 列表展示模板名称/更新时间，预览弹窗渲染 Markdown 且不提供编辑控件。
