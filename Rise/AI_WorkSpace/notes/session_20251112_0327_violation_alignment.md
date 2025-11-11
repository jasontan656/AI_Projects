# 测试计划摘要（session_20251112_0327_violation_alignment）
- **范围**：记录 Rise Workflow 持久化、Telegram 入口、Up 渠道策略、Workflow Builder Controller 四大主场景（S1~S4）及 32 个子场景（D1~D8），对应 Step-01~18。
- **环境**：Rise FastAPI + Redis/Mongo（docker compose）、Up Admin Vite dev server、Telegram aiogram runtime + Mockoon Bot API、Chrome DevTools MCP + Vitest/pytest/newman 组合。
- **风险 & 缓释**：Redis/Mongo/Telegram 依赖不可用需触发降级脚本；Chrome DevTools MCP 需妥善存档日志；Gov Audit backlog>100 需在 24h 内补交。
- **输出**：完整计划位于 `AI_WorkSpace/Test/session_20251112_0327_violation_alignment_testplan.md`，含测试矩阵、环境矩阵、数据策略、报告模版与覆盖校验。
