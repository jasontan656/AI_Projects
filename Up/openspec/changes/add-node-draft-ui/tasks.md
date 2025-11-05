# Tasks

- [x] 重构 PipelineWorkspace 左侧导航与标签结构，默认选中「Nodes」并容纳节点草稿表单 + 动作列表组件。
- [x] 在「Prompts」标签实现模板列表、Codemirror 编辑器和显式保存按钮，移除自动保存逻辑。
- [x] 为「Variables」「Logs」标签提供占位视图：变量树搜索框/空状态、日志流连接提示与重试操作。
- [x] 保存节点/提示词草稿时同步更新 docs/contracts/pipeline-node-draft.json 与 docs/contracts/prompt-draft.json。
- [x] 更新 proposal.md 描述以反映 SideNav + 多标签布局和动作编排入口。
- [x] 运行 openspec validate add-node-draft-ui --strict，确认文档与契约一致。
