## MODIFIED Requirements

### Requirement: Project overview and scope
- SHALL: openspec/project.md 定义 Up 为面向运维/工程团队的工作流编排 GUI，强调节点脚本化、模板复用、变量审查与实时调试等核心使命。

#### Scenario: Document core mission
- **GIVEN** 团队成员阅读 openspec/project.md
- **THEN** 文档概述节点动作脚本、模板中心、变量可视化、日志调试、合同优先协作等目标。

### Requirement: Module and layout coverage
- SHALL: 文档罗列 Nodes、Prompts、Workflow、Variables、Logs、Settings 六大模块，并推荐 SideNav + 顶部标签组合的主工作区布局。

#### Scenario: Reference workspace layout
- **GIVEN** 新成员查阅布局建议
- **THEN** 文档展示侧边栏 + 主面板 ASCII 草图，并说明各模块职责和默认选中 Nodes 标签。

### Requirement: Tech stack alignment
- SHALL: 文档锁定 Vue 3 + Vite + Pinia + Element Plus + Codemirror + VueFlow 的前端栈，并记录配套库（VueUse、Axios、WebSocket/SSE、uuid/nanoid 等）。

#### Scenario: Review tech stack
- **GIVEN** 成员评估技术选型
- **THEN** 文档列出上述框架及用途，确保与实际实现和 docs/contracts 契约保持一致。

### Requirement: Collaboration and contract conventions
- SHALL: 文档强调合同优先、Chrome DevTools AI 回归测试、docs/contracts/*.json 快照同步、与 FastAPI 后端联调的流程。

#### Scenario: Align with backend contract
- **GIVEN** 后端工程师阅读协作约定
- **THEN** 文档提示在更新 Pinia schema 时需同步刷新契约文件并提前沟通 API 变化。
