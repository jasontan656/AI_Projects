# Tasks

1. 更新 `openspec/changes/update-project-goal/specs/project-context/spec.md` 与相关 `tasks.md`，确保模块/技术栈描述与最新 `project.md` 一致并修复编码问题。
2. 重写 `openspec/changes/add-node-draft-ui/specs/agent-workspace/spec.md`，纳入 SideNav + Tab 布局、节点动作入口，以及与集中模板 Hub 的职责边界；同步校正对应 `proposal.md`/`tasks.md` 中的陈述。
3. 修订 `openspec/changes/compose-node-actions/specs/pipeline-node-management/spec.md` 及 `tasks.md`，明确 `actions` 契约字段、LLM gating 行为和模板预览要求，并移除控制字符。
4. 对上述三个变更的 `proposal.md` 或 `design.md` 进行最小必要更新，引用新的模块/术语，并添加需要的验证步骤描述。
5. 运行 `openspec validate align-openspec-standards --strict` 以及受影响变更的校验，确保文档一致性。
