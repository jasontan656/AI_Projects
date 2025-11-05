## MODIFIED Requirements

### Requirement: Project overview and scope
- SHALL: `openspec/project.md` 明确 Up 是内部工作流运维 GUI，服务于节点脚本化、模板管理与调试。

#### Scenario: Document core mission
- **GIVEN** 团队成员阅读 `openspec/project.md`
- **THEN** 文档描述节点脚本化、模板复用、变量可视化、实时调试与合同优先等核心目标。

### Requirement: Module and layout coverage
- SHALL: 文档罗列 Nodes、Prompts、Workflow、Variables、Logs、Settings 六大模块，并建议 SideNav + 主面板标签布局。

#### Scenario: Reference workspace layout
- **GIVEN** 新成员查阅布局建议
- **THEN** 文档展示包含侧边栏与主面板的 ASCII 布局草图，以及各模块的职责说明。

### Requirement: Tech stack alignment
- SHALL: 文档固定 Vue 3 + Vite + Pinia + Element Plus + VueFlow + Codemirror 组合，并说明 VueUse、Axios、WebSocket/SSE 等配套。

#### Scenario: Review tech stack
- **GIVEN** 成员评估技术栈
- **THEN** 文档列出上述框架/库及用途，与 `docs/contracts` 与前端实现保持一致。

### Requirement: Collaboration and contract conventions
- SHALL: 文档重申合同优先、Chrome DevTools 回归、`docs/contracts` 快照同步、与 FastAPI 后端对齐的规则。

#### Scenario: Align with backend contract
- **GIVEN** 后端工程师阅读协作约定
- **THEN** 文档提示前端在更新 Pinia schema 时需同步更新 `docs/contracts/*.json` 并提前沟通接口变化。
