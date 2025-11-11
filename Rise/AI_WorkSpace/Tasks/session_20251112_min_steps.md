# session_20251112_violation_alignment_min_steps

Step-01 [Business Logic] src/business_logic/workflow/models.py
- 需求来源：DevDoc Module Matrix S1 + Requirements S1-D1
- 改动内容：新建文件承载 WorkflowExecutionContext/RunResult/StageResult dataclass 及 helper，使 orchestrator 文件仅保留流程逻辑。
- 技术栈/上下文：FastAPI 分层 DI [CTX-FASTAPI]; Forem 分层文章 [EXA-FOREM]
- 验证：
  1) 单元测试加载模型并确保 dataclass 可实例化。
  2) 运行 `pytest tests/business_logic/test_workflow_models.py`（或新增）确保导出符号可被 orchestrator 导入。
- 依赖：无
- 预计耗时：25min

Step-02 [Persist] src/foundational_service/persist/workflow_summary_repository.py
- 需求来源：DevDoc S1 Function Summary
- 改动内容：定义 WorkflowSummaryRepository 接口+实现，封装 Redis list (max 20, TTL env) 与 Mongo `$push+$slice` 并发 telemetry。
- 技术栈/上下文：FastAPI DI 资源复用 [CTX-FASTAPI]; Repository 模式文章 [EXA-FOREM]
- 验证：
  1) 集成测试使用 faker Redis/Mongo 验证 append 行为与 TTL。
  2) 观察 telemetry 事件 `workflow.summary.persisted` 是否被触发。
- 依赖：Step-01
- 预计耗时：40min

Step-03 [Business Logic] src/business_logic/workflow/orchestrator.py
- 需求来源：DevDoc S1 Function Summary
- 改动内容：去除 `_persist_summary`，通过 DI 注入 WorkflowSummaryRepository，确保 orchestrator 仅 orchestrate stage。
- 技术栈/上下文：FastAPI DI [CTX-FASTAPI]
- 验证：
  1) 运行现有 workflow 测试确保 stage 顺序不变。
  2) Mock 仓储验证 execute() 会调用 `append_summary` 一次。
- 依赖：Step-02
- 预计耗时：35min

Step-04 [Interface Entry] src/interface_entry/http/dependencies.py & bootstrap/application_builder.py
- 需求来源：DevDoc Module Matrix S1/S2
- 改动内容：注册 WorkflowSummaryRepository、Redis/Mongo 客户端的 lifespan，移除 application_builder 中的直接持久化 wiring。
- 技术栈/上下文：FastAPI lifespan + Depends [CTX-FASTAPI]
- 验证：
  1) 启动 FastAPI 并确保依赖可解析（`uvicorn app:app`）。
  2) 触发 /workflows API，确认日志显示仓储实例注入成功。
- 依赖：Step-02, Step-03
- 预计耗时：30min

Step-05 [Business Service] src/business_service/conversation/config.py
- 需求来源：DevDoc Module Matrix S2
- 改动内容：提炼 `TelegramEntryConfig` dataclass，定义 mode、提示语、容错策略，替换 service 内部散落常量。
- 技术栈/上下文：FastAPI data class DI [CTX-FASTAPI]
- 验证：
  1) 单元测试加载 config，验证 mode 校验。
  2) 运行 Telegram 模拟 update 确认 config 注入 service。
- 依赖：Step-04
- 预计耗时：25min

Step-06 [Business Service] src/business_service/conversation/runtime_gateway.py
- 需求来源：DevDoc S2 Function Summary
- 改动内容：封装同步/异步调度逻辑，仅依赖 TaskRuntime/Orchestrator，返回 `AsyncResultHandle`。
- 技术栈/上下文：FastAPI service layering [CTX-FASTAPI]
- 验证：
  1) 单元测试模拟 sync/async mode，检查 orchestrator 调用次数。
  2) Integration：触发 Telegram webhook，验证 async 路径返回 ack。
- 依赖：Step-05
- 预计耗时：35min

Step-07 [Business Service] src/business_service/conversation/health.py
- 需求来源：DevDoc S2 Function Summary
- 改动内容：实现 ChannelHealthReporter 更新 Redis 健康键并发 telemetry。
- 技术栈/上下文：Telemetry 指南（项目现有）
- 验证：
  1) 单测 stub Redis 客户端，校验写入键名/TTL。
  2) 检查 telemetry bus 是否收到 `channel.health.snapshot`。
- 依赖：Step-05
- 预计耗时：30min

Step-08 [Business Service] src/business_service/conversation/service.py
- 需求来源：DevDoc Module Matrix S2
- 改动内容：接入新 config/runtime_gateway/health，移除全局变量与基础设施耦合。
- 技术栈/上下文：FastAPI service layering [CTX-FASTAPI]
- 验证：
  1) 运行会话相关单测。
  2) 实机 Telegram 回环测试同步+异步入口。
- 依赖：Step-05, Step-06, Step-07
- 预计耗时：45min

Step-09 [Interface Entry] interface_entry/bootstrap/runtime_lifespan.py & runtime/supervisors.py
- 需求来源：DevDoc Module Matrix S2 + Risks
- 改动内容：迁移 application_builder 中 runtime/logging 初始化逻辑，入口仅负责组装。
- 技术栈/上下文：FastAPI lifespan [CTX-FASTAPI]
- 验证：
  1) 启动应用确保 lifespan 事件触发。
  2) 关闭应用检查日志 handlers 被释放。
- 依赖：Step-04, Step-08
- 预计耗时：35min

Step-10 [Frontend Schema] D:\AI_Projects\Up\src\schemas\channelPolicy.js & workflowDraft.js
- 需求来源：DevDoc Module Matrix S3/S4
- 改动内容：抽离 schema/初始状态与校验规则，stores 引用统一结构。
- 技术栈/上下文：Pinia store 结构 [CTX-PINIA]; StudyRaid store composition [EXA-STUDYRAID]
- 验证：
  1) 单元测试 schema 工具函数。
  2) 在 dev server 中加载页面确保默认值正确。
- 依赖：无（可与 Step-11 并行）
- 预计耗时：30min

Step-11 [Frontend Service] D:\AI_Projects\Up\src\services\channelPolicyClient.js
- 需求来源：DevDoc S3 Function Summary
- 改动内容：封装保存/读取 API、注入 operator headers、统一错误处理。
- 技术栈/上下文：Pinia actions 调用服务 [CTX-PINIA]
- 验证：
  1) 使用 Vitest/axios-mock 测试成功/失败分支。
  2) Dev server 中保存一次策略，检查 network 请求。
- 依赖：Step-10
- 预计耗时：35min

Step-12 [Frontend Scheduler] D:\AI_Projects\Up\src\services\channelHealthScheduler.js
- 需求来源：DevDoc Module Matrix S3
- 改动内容：实现轮询+cooldown+退避，支持 start/stop API。
- 技术栈/上下文：Pinia async actions [CTX-PINIA]; StudyRaid async handling [EXA-STUDYRAID]
- 验证：
  1) Vitest 模拟计时器验证 start/stop。
  2) Dev server 观察健康指示刷新与 cooldown UI。
- 依赖：Step-11
- 预计耗时：40min

Step-13 [Frontend Store] D:\AI_Projects\Up\src\stores\channelPolicy.js
- 需求来源：DevDoc S3 Module Matrix
- 改动内容：store 精简为状态+getter，actions 调用 Step-11/12 服务；去除内部节流逻辑。
- 技术栈/上下文：Pinia store best practice [CTX-PINIA]
- 验证：
  1) Pinia 单测验证 actions 仅触发服务 mock。
  2) Dev server 中保存策略，确认健康轮询照常工作。
- 依赖：Step-10, Step-11, Step-12
- 预计耗时：35min

Step-14 [Frontend Service] D:\AI_Projects\Up\src\services\workflowDraftService.js
- 需求来源：DevDoc Module Matrix S4
- 改动内容：封装 workflow CRUD +校验 + SSE 触发入口，供 store/controller 使用。
- 技术栈/上下文：Pinia actions拆分 [CTX-PINIA]
- 验证：
  1) Vitest mock HTTP，验证 save/publish 行为。
  2) Dev server 运行 builder，查看日志输出。
- 依赖：Step-10
- 预计耗时：40min

Step-15 [Frontend Composable] D:\AI_Projects\Up\src\composables\useWorkflowBuilderController.js
- 需求来源：DevDoc S4 Function Summary
- 改动内容：实现加载/保存/发布/SSE 控制与 `teardown`，协调 stores + scheduler。
- 技术栈/上下文：Pinia 组合式模式 [CTX-PINIA]
- 验证：
  1) 组件单测或 e2e 模拟路由进入/离开，确保 teardown 调用。
  2) Dev server 手动操作 builder，确认 controller state 更新。
- 依赖：Step-13, Step-14, Step-16
- 预计耗时：45min

Step-16 [Frontend Service] D:\AI_Projects\Up\src\services\pipelineSseClient.js (或扩展 pipelineService)
- 需求来源：DevDoc S4 Module Matrix
- 改动内容：封装 SSE 订阅/取消、心跳、错误回调，供 controller 调用。
- 技术栈/上下文：Pinia + composable 协作 [CTX-PINIA]
- 验证：
  1) 集成测试使用 mock EventSource，确保 auto-reconnect。
  2) Dev server 中切换 workflow，观察 SSE 释放。
- 依赖：Step-14
- 预计耗时：35min

Step-17 [Frontend View] D:\AI_Projects\Up\src\views\WorkflowBuilder.vue
- 需求来源：DevDoc S4 Module Matrix
- 改动内容：改为只消费 controller state/actions，移除直接 store/SSE 访问；路由守卫里调用 teardown。
- 技术栈/上下文：Pinia 组合式组件 [CTX-PINIA]
- 验证：
  1) E2E/Playwright 操作 builder，确认资源释放。
  2) 手动验证发布/保存提示与 Requirements 提示语一致。
- 依赖：Step-15
- 预计耗时：40min

Step-18 [Validation] Cross-Scenario Tests
- 需求来源：Requirements Acceptance + DevDoc Implementation Decisions
- 改动内容：执行 GIVEN/WHEN/THEN：
  1) Redis/Mongo summary 落地；
  2) Telegram sync/async 模式 + 健康上报；
  3) Channel policy 保存→健康轮询；
  4) Workflow builder 发布/SSE 释放。
- 技术栈/上下文：端到端验证策略
- 验证：
  1) 记录 telemetry、日志、数据库状态。
  2) 前端实际操作 + Chrome DevTools 检查网络与 UI。
- 依赖：Step-01~Step-17
- 预计耗时：60min
