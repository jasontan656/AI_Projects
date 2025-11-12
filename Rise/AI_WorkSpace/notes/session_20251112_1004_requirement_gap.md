# session_20251112_1004_requirement_gap

## 用户意图
- 根据最新测试报告（AI_WorkSpace/Reports/session_20251112_0327_testissues.md）补齐相应的业务/技术需求文档，覆盖 Telegram 异步确认、Pipeline 守卫、Workflow Builder API 依赖、PromptEditor/PipelineWorkspace 测试可用性等问题。
- 在输出正式需求前，先完成资料调研、存档，并准备随后的 WRITE MODE。

## 仓库上下文
- Rise 主仓位于 `D:/ai_projects/rise`，FastAPI + aiogram 组成 Telegram Webhook 接入层，Up 管理端在 `D:/AI_Projects/Up` 提供工作流配置 UI。
- 关键文件：
  - `src/business_service/conversation/service.py`：TelegramConversationService，涉及 Issue #1/#2。
  - `src/interface_entry/http/dependencies.py`：FastAPI 依赖工厂（Issue #3 缺口）。
  - `tests/business_service/conversation/test_telegram_queue_runtime.py`、`test_pipeline_guard.py`：失败用例来源。
  - `tests/interface_entry/http/test_pipeline_nodes_api.py`、`test_prompt_api.py`：接口导入失败。
  - Up 端 `tests/unit/PromptEditor.spec.js`、`tests/unit/PipelineWorkspace.spec.js` 依赖 httpClient/Element Plus。

## 技术栈信息
- 后端：Python 3.11、FastAPI 0.118.x、aiogram 3.22、Redis 7.x、MongoDB 7.x、OpenAI SDK 1.105.0、aio-pika、uvicorn。
- 前端：Vue 3 + Vite、Element Plus、Pinia、Codemirror、Vitest。
- 基础设施：Redis/Mongo/RabbitMQ 队列持久化、Telegram Webhook、ngrok/HTTPS 反代。

## 搜索结果（Context7 / Exa / Web）
1. Context7 `/fastapi/fastapi` BackgroundTasks 文档：强调通过 FastAPI 依赖链注入 `BackgroundTasks`，在 webhook 中先快速响应、再由后台任务写日志或调度外部作业，可作为 Issue #1/#3 补救策略依据。
2. Exa：`https://vitest.dev/guide/browser/component-testing`（2025-11-06）与 `https://vitest.dev/guide/mocking`（2025-08-31）提出在 Vitest 中注册全局组件/模拟 fetch、Mock Service Worker，支撑 Issue #4/#5 的测试隔离方案；Vue School 文章强调在测试引导文件中挂载 UI 框架。
3. Web Search：
   - `docs.orum.io/guides/monitor/webhooks/webhook-best-practices`（2025）建议 webhook handler 仅做轻处理并将重活入队，符合 Rise 对 Telegram 异步确认的需求。
   - `github.com/aiogram/aiogram/issues/1397` 讨论 webhook ack 控制及 `handle_in_background` 选项，提醒我们需要在 orchestrator 中显式持久化 ack。
   - `vitest.dev/guide/mocking` 强调 `vi.mock`/`vi.spyOn` 使用规则与 Browser Mode 限制，指导 PromptEditor 测试如何 mock httpClient。

## 架构发现
- TelegramConversationService 当前缺少异步 ack 以及 pipeline 守卫注入，导致 webhook 处理路径与 Redis/RabbitMQ 工作流脱节。
- interface_entry/http 层依赖清单不完整，`get_telegram_client` 未定义使得任何需要 Telegram client 的 API 无法启动，影响 Admin 面板。
- Up 端测试未注入 Element Plus / HTTP mock，造成组件初始化失败；缺少统一的 Vitest bootstrap。

## 文件引用
- `AI_WorkSpace/Reports/session_20251112_0327_testissues.md`
- `src/business_service/conversation/service.py`
- `src/interface_entry/http/dependencies.py`
- `tests/business_service/conversation/test_telegram_queue_runtime.py`
- `tests/interface_entry/http/test_pipeline_nodes_api.py`
- `AI_WorkSpace/notes/session_20251112_0327_violation_alignment.md`

## 违规点与整改思路
- Telegram 异步队列：需恢复 `AsyncResultHandle` 创建、Redis/RabbitMQ 入列（默认方案：在 `TelegramConversationService.enqueue_async_result` 中追加幂等键，若缺少证据，按默认假设实现，可被用户覆盖）。
- Pipeline 守卫：缺失 `pipeline_service_factory` 依赖，建议抽出守卫接口放入 `business_service/pipeline` 并通过 service dataclass 注入。
- HTTP 依赖：`get_telegram_client` 未注册，需将 Telegram runtime 引导集中到 `dependencies.py` 并提供 fallback（默认 assumption）。
- 前端测试：缺 Element Plus 注册 + fetch mock，需在 `tests/setup/vitest.setup.js` 注册组件并在 `PromptEditor.spec.js` 中 mock `requestJson`。

## 2025-11-12 10:45 Tech Stack 摘要补充
- 已将 `session_20251112_0125_violation_alignment_tech.md` 扩展为符合“Tech Stack & Module Summary Command Set”结构：新增 Scenario-to-Module Mapping、Best Practices（含 FastAPI BackgroundTasks、Pinia vs Composable、Vitest 组件测试引用）以及 File/Risks/Decisions 列表。
- Context7 参考：FastAPI BackgroundTasks + DI（turn15mcp__context7__get-library-docs0）支撑异步 ACK 路线；Exa 参考：Pinia vs Composables（turn16mcp__exa__exa_search0）、Vitest Component Testing（turn17mcp__exa__exa_search0）。
- 关键决策：WorkflowSummaryRepository 统一持久化面、RuntimeGateway 统管 sync/async、Up 端 store 仅存状态由 controller/composable 承担副作用、Vitest setup 负责 Element Plus 注册 + fetch mock。
