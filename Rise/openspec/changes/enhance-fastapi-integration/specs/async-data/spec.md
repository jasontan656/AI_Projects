## ADDED Requirements

### Requirement: Asynchronous Repository Interfaces
Prompt 与 Pipeline Node 仓储 MUST 提供真正的异步接口（例如基于 Motor），业务服务和路由不得再通过 `run_in_threadpool` 调用同步 PyMongo 方法。

#### Scenario: Prompt creation without threadpool
- **GIVEN** 调用 `POST /api/prompts`
- **WHEN** handler 写入 Mongo
- **THEN** 代码路径不触发 `run_in_threadpool` 或同步阻塞调用
- **AND** Mongo 操作通过 `await repository.create(...)` 完成。

### Requirement: Background Processing for Slow IO
涉及审计记录、版本快照等潜在长耗时操作 MUST 通过 FastAPI `BackgroundTasks` 或异步任务调度执行，主请求在任务入队失败时返回明确错误。

#### Scenario: Audit written via background task
- **GIVEN** 成功创建节点触发审计
- **WHEN** handler 返回 201 响应
- **THEN** 审计写入在后台任务中执行，不阻塞主请求
- **AND** 若任务入队失败，API 返回 500 并附带 `AUDIT_ENQUEUE_FAILED` 错误码。
