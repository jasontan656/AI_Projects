## Scope

该设计聚焦于把 FastAPI 作为完整的 Web 层框架使用，涵盖依赖注入、生命周期、异步数据访问、统一响应/错误模型与安全上下文。目标是在不改变业务领域模型的前提下，为即将到来的动作式流程和多渠道扩展提供稳定的后端底座。

## Architecture Overview

1. **依赖注入与生命周期**
   - 新增 `interface_entry.http.dependencies` 子模块，集中定义 `Settings`, `MongoClient`, `PromptService`, `PipelineNodeService`, `ContextBridge` 相关依赖。
   - 使用 FastAPI `lifespan`（或 `@asynccontextmanager`）在应用启动时初始化 Mongo/Motor 客户端、Redis（如启用）、aiogram 组件；在关闭阶段统一释放。
   - 为 aiogram bootstrap 适配新的 FastAPI `AppState`，确保 Telegram runtime 可以复用同一依赖树。

2. **异步数据访问**
   - 为 prompt/pipeline 仓储提供异步接口：若采用 Motor 则直接暴露 async 方法；若继续用 PyMongo，需要封装 `AsyncRepository` 通过线程调度器统一管理，避免在 handler 内裸用 `run_in_threadpool`。
   - Business Service 可通过协议接口（protocol）同时支持同步/异步实现，便于逐步迁移。

3. **统一安全上下文**
   - 定义 `ActorContext` dataclass，包含 `actor_id`、`roles`、`tenant`、`request_id`。
   - 构建 `get_actor_context` 依赖：读取 Header / JWT / 查询参数；若缺失必须返回 401/403，并记录审计日志。
   - 后续动作式流程可在此处插入权限规则或策略配置。

4. **响应与异常模型**
   - 设计 `ApiResponse[T]`、`ApiError` Pydantic 模型，在 handler 中统一返回结构。
   - 注册全局异常处理器：将业务异常（如 `DuplicateNodeNameError`, `KeyError`) 转换成标准错误码和 message。
   - 对成功响应要求统一字段（`data`, `meta`, `errors`），便于前端解析。

5. **后台任务与审计**
   - 对审计、版本记录、日志入库等潜在耗时操作，统一使用 FastAPI `BackgroundTasks` 或自建异步任务队列，避免阻塞主请求。
   - 同时定义最基本的幂等策略，确保任务失败可重试。

6. **测试与可观测**
   - 编写依赖注入与生命周期的集成测试，确保应用在启动/关闭时资源状态正确。
   - 为统一响应模型增加快照测试，防止 future PR 不经意破坏契约。

## Risks / Mitigations

- **异步迁移导致业务阻塞**：先为 prompt/pipeline 提供异步 facade，再逐步迁移调用方；保留同步实现以备回滚。
- **鉴权依赖数据源不统一**：提前与前端/运维确认 header/JWT 格式，提供可配置解析器，并在设计中允许 fallback 到 request_id。
- **背景任务失败**：记录任务结果，必要时输出 Prometheus 指标；同时保持业务主流程在任务提交失败时返回告警。

## Validation Strategy

- 单元测试覆盖依赖注入、ActorContext 解析、统一响应模型。
- 路由集成测试验证 200/4xx/409 等典型场景。
- 运行 `openspec validate enhance-fastapi-integration --strict` 确认文档合规。
