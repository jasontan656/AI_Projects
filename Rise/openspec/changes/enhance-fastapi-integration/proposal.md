## Why

- 现有 FastAPI 层主要充当“路由胶水”，依赖注入、生命周期管理和鉴权均由手写逻辑拼凑，难以支撑即将上线的动作式节点配置与多渠道扩展。
- Prompt 与 Pipeline API 通过 `run_in_threadpool` 调用同步 PyMongo，缺少真正的异步数据访问与统一资源管理；在高并发或长耗时场景下隐含阻塞风险。
- 统一的响应模型、错误枚举、身份上下文尚未建立，接口返回结构随 handler 自行定义，前端将无法稳定消费即将新增的动作式流程 API。

## What Changes

- 构建完整的 FastAPI 依赖/生命周期体系：定义可缓存的 `MongoClient`、`PromptService` 等依赖，拆分启动/关闭事件，并将 aiogram、数据库、缓存等资源挂载在 FastAPI lifespan 中集中管理。
- 引入异步数据访问与后台任务：为 Prompt 与 Pipeline Node 仓储提供 Motor 或异步封装，移除 `run_in_threadpool`，并为审计/日志等 IO 使用 FastAPI `BackgroundTasks`。
- 统一 API 契约与安全策略：制定标准的请求/响应模型、错误码和异常处理器；通过依赖注入承载 `ActorContext`、权限校验及租户信息，所有路由使用 Pydantic v2 模型输出结构化响应。

## Impact

- 需要调整 `interface_entry.http` 下的路由、依赖和测试；Prompt/Pipeline API 的实现方式将发生结构性变化。
- Business Service 可能需要提供异步接口或适配器，以支撑新的数据访问层；同时 lifespans 会与 aiogram 启动流程互相协调。
- 前端需依据新的响应/错误模型更新调用逻辑，但获得更稳定的契约；部署侧则可以通过统一的生命周期钩子配置资源监控。
