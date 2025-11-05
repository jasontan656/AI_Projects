## ADDED Requirements

### Requirement: Centralised FastAPI Lifespan Management
Interface 层 MUST 使用 FastAPI `lifespan` 或 `@app.on_event` 钩子集中初始化并释放核心资源（Mongo/Motor 客户端、Redis 连接、aiogram 会话等），不得在路由函数内部直接创建长生命周期对象。

#### Scenario: Mongo client reused across requests
- **GIVEN** 应用启动时 lifespans 执行
- **WHEN** 两个请求先后访问 Prompt API
- **THEN** 二者复用同一个 Mongo/Motor 客户端实例
- **AND** 应用关闭时客户端被正确关闭且无资源泄漏日志。

### Requirement: Cached Dependency Injection
FastAPI 依赖函数 MUST 使用 `functools.lru_cache` 或等效机制缓存不可变资源（如 `Settings`, `MongoClient`, `PromptService`），并通过 `Depends` 向 handler 暴露，移除现有的手动构造逻辑。

#### Scenario: Prompt service retrieved via dependency
- **GIVEN** handler 通过 `Depends(get_prompt_service)`
- **WHEN** 多次调用创建/更新接口
- **THEN** `get_prompt_service` 只在首次解析时实例化一次
- **AND** 日志中不再出现每请求初始化仓储的警告。
