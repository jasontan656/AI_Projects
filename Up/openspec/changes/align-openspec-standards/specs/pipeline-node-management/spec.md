## MODIFIED Requirements

### Requirement: Actions replace legacy systemPrompt
- SHALL: 节点创建/编辑流程使用有序 `actions` 列表代替自由文本 `systemPrompt`，并与 `docs/contracts/pipeline-node-draft.json` 字段保持一致。

#### Scenario: Save node with scripted actions
- **GIVEN** 用户在节点表单添加一个或多个动作
- **WHEN** 点击保存
- **THEN** 请求 payload MUST 包含 `actions[].id`、`type`、`order`、`config` 字段，且无遗留 `systemPrompt` 自由文本
- **AND** 若加载旧节点仅有 `systemPrompt`，界面自动生成单个 `prompt_append` 动作并提示迁移。

### Requirement: LLM gating disables prompt actions
- SHALL: 当 `allowLLM` 为 false 时禁用或移除 `prompt_append` 动作，并阻止携带该动作的节点保存。

#### Scenario: Block prompt actions when LLM disabled
- **GIVEN** 动作列表存在至少一个 `prompt_append`
- **WHEN** 用户关闭“允许访问大模型”开关
- **THEN** `prompt_append` 条目被标记为禁用且保存按钮显示错误提示，直到用户删除或重新启用 LLM。

### Requirement: Action ordering controls and context menu
- SHALL: 动作列表提供显式的“上移/下移”按钮维持顺序，并支持在动作快捷菜单中通过右键打开设置入口（例如跳转到动作配置或弹出设置面板）。

#### Scenario: Reorder actions via buttons
- **GIVEN** 动作列表至少包含两项
- **WHEN** 用户点击某动作的“上移”按钮
- **THEN** 该动作与上一项交换顺序，`order` 字段同步更新为 0..n-1 连续值。

#### Scenario: Open action context menu
- **GIVEN** 用户右键点击某动作条目
- **WHEN** 弹出快捷菜单
- **THEN** 菜单提供“查看设置”选项，点击后打开动作设置面板或跳转至对应配置区域。

### Requirement: Action config schema alignment
- SHALL: 每个动作的 `config` 仅暴露契约定义的键：`templateId`、`legacyText`、`inputMapping`（预留）、`disabled`，并根据类型附带校验。

#### Scenario: Validate prompt_append config
- **GIVEN** 用户在动作中选择模板
- **THEN** `config.templateId` 保存为所选模板 ID 且 `legacyText` 为空
- **AND** 未选择模板时自动保留 `legacyText` 提示文本，保证契约字段存在。

### Requirement: Template preview is read-only
- SHALL: 提示词模板预览从 Pinia 模板 store 拉取内容并以 Markdown 只读形式展示，禁止在弹窗中编辑。

#### Scenario: Show locked template preview
- **GIVEN** 用户在动作里选择模板 A
- **WHEN** 打开模板预览抽屉
- **THEN** 抽屉渲染模板 A 的 Markdown，且未提供任何输入控件；需要修改时提示前往「Prompts」标签。
