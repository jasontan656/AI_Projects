# Proposal: Add Node Draft Workspace

## Why
- 将前端作为后端契约文档，需要一个集中式 PipelineWorkspace 以展示节点、提示词等工作流模块。
- 通过节点草稿与提示词草稿的可视化编辑，提前输出契约文件供后台实现对齐。

## What Changes
- 创建带 SideNav 的 PipelineWorkspace 主界面，默认聚焦「Nodes」标签，表单内嵌节点元数据与动作列表编辑器。
- 在「Prompts」标签提供模板列表、Codemirror 编辑器、只读预览和显式保存按钮，与节点表单解耦。
- 为「Variables」「Logs」标签提供占位视图：变量树搜索与实时日志流状态，确保导航骨架完整。
- 持续同步节点与提示词草稿到 docs/contracts/pipeline-node-draft.json / prompt-draft.json 作为后端契约。
- 录制 Chrome DevTools AI 流程（新增节点、维护模板、查看变量/日志占位）并纳入测试。

## Impact
- 前端新增 SideNav + Tabs 布局、节点动作列表组件、模板 hub 及占位视图；Pinia 契约与文档同步更新。
- 后端可依据契约文件实现真实接口；调试日志与变量面板为后续实时功能预留结构。

## Open Questions
- 变量面板默认是否需要真实 Redis 数据源或可先用 Mock？
- 日志流如后端暂未准备，是否允许回退到轮询或保留空状态？
