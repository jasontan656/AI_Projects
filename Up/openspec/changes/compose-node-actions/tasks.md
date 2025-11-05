# Tasks

- [x] 扩展 pipelineDraft store 与服务层，使节点保存/加载使用 actions[] 并兼容旧 systemPrompt 数据。
- [x] 将节点表单替换为动作列表编辑器，与提示词模板下拉联动。
- [x] 在 promptDraftStore 中暴露模板列表和只读预览供动作选择使用。
- [x] 为动作列表添加“上移/下移”按钮并提供右键快捷菜单打开动作设置。
- [x] 当 allowLLM 关闭时禁用/移除 prompt_append 动作并阻止保存。
- [x] 限制 config 字段至契约允许的键并同步更新 docs/contracts/pipeline-node-draft.json 示例。
- [x] 运行 openspec validate compose-node-actions --strict，确保变更通过校验。
