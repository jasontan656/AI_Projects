# Proposal: Align OpenSpec With Updated Project Context

## Background
- 2025-11-05 更新的 `openspec/project.md` 重新定义 Up 为“Vue 3 + Pinia + Element Plus”驱动的工作流编排 GUI，并明确必须交付的模块与布局。
- 现有三个进行中的变更（`add-node-draft-ui`、`compose-node-actions`、`update-project-goal`）在此前版本的愿景下撰写，内容与新的项目定位存在偏差和重复职责。

## Audit Findings
- **add-node-draft-ui** – `specs/agent-workspace/spec.md` 仍描述单页面的全屏草稿表单，与最新 SideNav + 多标签布局不符；要求里没有提到节点动作编排或 VueFlow 画布入口，且“自动保存提示词”场景与最新“集中模板 Hub”目标冲突。
- **compose-node-actions** – `specs/pipeline-node-management/spec.md` 含有控制字符、字段命名错误（`actions` 拼写缺失）、缺少与 `docs/contracts/pipeline-node-draft.json` 中配置结构的约束；任务中悬挂“更新 project.md”事项已经由新文档完成但未回填。
- **update-project-goal** – `specs/project-context/spec.md` 与 `tasks.md` 发生字符编码损坏，场景未覆盖必须列出的模块（Workflow、Variables、Logs、Settings），也未强调 VueFlow 作为画布标准。
- **Process gaps** – 现有提案没有统一声明要同步清理历史文案与任务勾选状态，也没有约定如何复核文档与契约的一致性。

## Goals
1. 产出一套一致的标准，确保所有现有变更文档在术语、布局、模块、技术栈上与最新 `project.md` 对齐。
2. 为后续开发提供明确的任务拆分，覆盖文档修订、spec delta 更新、任务状态回填及验证流程。
3. 清理遗留格式/编码问题，避免未来 review 时再出现乱码或不可执行的要求。

## Non-Goals
- 不会在本提案中修改实际前端/后端代码；仅聚焦 OpenSpec 文档、任务与契约。
- 不会引入新的业务模块或路线图项；若未来需要，将通过独立提案处理。

## Approach
1. **Project Context Realignment** – 重写 `specs/project-context/spec.md` 并同步修复 `tasks.md`，明确模块列表、核心目标与合作契约格式；确保引用 VueFlow、Codemirror、合同快照要求，同时即时补充 Variables 与 Logs 模块描述。
2. **Agent Workspace Repartition** – 更新 `specs/agent-workspace/spec.md`，将节点管理、提示词 Hub、变量面板与实时日志入口映射到 SideNav + Tab 结构；删除或改写与集中模板 Hub 相冲突的自动保存条目，加入与节点动作编排协同的场景。
3. **Pipeline Actions Contract** – 修订 `specs/pipeline-node-management/spec.md`，清理非法字符，补充 `actions[].config` 字段要求、LLM gating 行为、动作排序交互（上下移动按钮 + 右键快捷菜单）以及模板预览约束；同步勾掉 `tasks.md` 中已完成但未回填的项目。
4. **Governance Hygiene** – 建立检查清单：对受影响变更的 `proposal.md`/`design.md` 做最小修订（如引用更新后的模块名和交互），补充验证步骤和 `openspec validate` 运行记录。

## Risks & Mitigations
- **文档交叉引用失效**：同步更新内链与术语表，提交前执行全文搜索确认没有旧字段残留。
- **范围蔓延**：优先处理与标准冲突最明显的 3 个变更，若发现新的差异，以增量变更记录在后续提案。
- **信息缺口**：若现有代码与契约不一致，将在实施任务中加入对 `docs/contracts` 的核查步骤。

## Decisions
- Variables 与 Logs 模块本次直接补齐规格要求，避免后续提案重复修订。
- 动作排序允许使用上下移动按钮；右键菜单需保留设置入口以便跳转或打开动作配置。
