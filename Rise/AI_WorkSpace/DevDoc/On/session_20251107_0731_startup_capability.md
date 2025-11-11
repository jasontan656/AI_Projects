# Rise 启动级能力降级方案（session_20251107_0731）

## 背景
- **触发点**：`src/interface_entry/bootstrap/app.py` 的自定义 `lifespan` 在 `_verify_telegram_connectivity()` 与 `_handle_pending_updates()` 中强依赖 Telegram HTTP 通路；当公网不可达时抛出 `TelegramWebhookUnavailableError`，使整个 FastAPI 服务无法对外暴露任何 HTTP 接口。
- **现状**：MongoDB、Redis、RabbitMQ 由 `.env` 绑定本机，在 2025-11-07 07:35 CST 通过 `.venv` 内的 `tmp_*_check.py` 逐项验证均处于可用状态，但启动流程缺乏「能力等级」概念，导致局部依赖故障也会引起全局崩溃。
- **目标**：启动阶段主动检测 Mongo/Redis/RabbitMQ/Telegram 四类依赖，写入统一的能力注册表。任何检测失败只关闭对应能力，并在路由/任务入口处返回 `503 Service Unavailable`，其他功能保持运行。

## 能力注册表（Capability Registry）
- 新增 `src/interface_entry/runtime/capabilities.py`：
  - `CapabilityStatus = Literal["available", "degraded", "unavailable"]`。
  - `CapabilityState` 记录 `status`, `detail`, `checked_at`, `ttl_seconds`。
  - `CapabilityRegistry` 负责 `set(name, state)`、`get(name)`、`require(name, hard=True)`；`require` 在 `status == "available"` 时放行，否则抛出封装好的 `HTTPException(status_code=503)`。
- 在 `create_app()` 设置 `app.state.capabilities = CapabilityRegistry()`，并暴露 `register_capability_probe(name, checker, hard=False)` 供启动脚本与后台重试任务共用。

## 启动检测流程
1. **加载 `.env` 与现有 logging**（沿用 `create_app` 既有逻辑）。
2. **运行基础 probe 集合**：
   - `mongo`: 通过 `AsyncIOMotorClient.admin.command("ping")`，若失败 `status="unavailable"` 且 detail 带 stack；Prompt/Workflow 路由会 `require("mongo")`。
   - `redis`: 建立 `Redis.from_url` + `PING`；失败则 TaskRuntime 退化为 in-memory dummy submitter。
   - `rabbitmq`: `aio_pika.connect_robust` 成功即 `available`，失败则 `WorkflowTaskProcessor` 禁用异步作业入口。
   - `telegram_webhook`: `_verify_telegram_connectivity` + `behavior_webhook_startup`，失败只标记 `degraded`，保留手动重试通道。
3. **写入 `app.state.capabilities`**：每个 probe 完成后调用 `registry.set(name, CapabilityState(...))`，并在 log + telemetry 中记录 `startup.capability.{name}`。
4. **后台重试**：对 `status != available` 的能力创建 `asyncio.create_task`，定期按 `ttl` 重新检测并自动恢复状态。

## 服务降级策略
- **依赖注入层（`src/interface_entry/http/dependencies.py`）**：
  - 在 `get_prompt_service`、`get_pipeline_service` 等入口加入 `registry.require("mongo")`，保障数据层不可用时直接返回 503，不进入业务逻辑。
  - `get_task_runtime()` 在初始化时检查 `redis`/`rabbitmq` 能力，若不可用则挂载一个 `NoopTaskRuntime`，其 `submitter` 立即抛出 503，并向日志写入 `task_runtime.disabled`。
- **HTTP 路由**：
  - Telegram webhook (`interface_entry/telegram/routes.py`) 和后台任务控制器 (`foundational_service/persist/controllers.py`) 在 router 层调用 `require`，触发 503。
  - 其余只读接口（如 `/api/prompts`）在 Mongo 可用时正常返回，否则 `ApiResponse` `meta.status="service_unavailable"`。
- **公共应答格式**：新增 `ServiceUnavailableError` 包装，header 中加入 `Retry-After: 30` 并提供 `capability` 字段帮助前端判定是否重试。

## 观测与接口
- `/healthz` 返回：
  ```json
  {
    "status": "degraded",
    "router": "behavior",
    "capabilities": {
      "mongo": {"status": "available", "checked_at": "2025-11-07T07:35:12Z"},
      "telegram_webhook": {"status": "degraded", "detail": "api.telegram.org timeout"}
    }
  }
  ```
- 新增 `/healthz/startup`（只读取能力注册表，不触发外部 IO），以及 `/healthz/readiness`（实时重跑 probe，用于 K8s readiness）。
- 日志：`log.info("startup.capability", extra={"name": name, "status": status, "detail": detail})`；当狀態變化時再輸出 `capability.state_changed` 方便告警。

## 成功路径（核心工作流）
1. Uvicorn 调用 `create_app()`，初始化日志、Manifest、Aiogram。
2. `app.state.capabilities` 载入 Probe 列表，`asyncio.gather` 并发执行 Mongo/Redis/Rabbit/Rabbit/Telegram 检查。
3. 每个 probe 完成后写入 `CapabilityState` 并在 log/telemetry 中记录。
4. FastAPI lifespan 继续执行 `application_lifespan()`（启动 TaskRuntime 等）；若某硬依赖不可用，`require(hard=True)` 立即让依赖注入层抛 503。
5. 应用开始对外提供 HTTP：
   - 正常服务（如 Prompt CRUD）按需命中 capability 检查。
   - Telegram webhook 若仍 `degraded`，请求会得到 503 + 说明，但其他 API 维持 2xx/4xx 流程。
6. 后台重试任务定期运行，若探测成功则更新 `CapabilityState`，自動解除 503。

## 失败模式与防御
- **Probe 长时间阻塞**：设置 `timeout_seconds` + `asyncio.wait_for`，超时视为失败并记录 detail；避免启动卡死。
- **状态竞争**：`CapabilityRegistry` 内部使用 `asyncio.Lock` 保证 `set/get` 原子性，并在 `checked_at` 上附带 ISO 時間方便比对。
- **硬依赖误伤**：若某能力配置为 `hard=True`，仅当确实没有替代路径时才启用。例如 Mongo 是硬依赖，但 Telegram webhook 属于软依赖，只需 `degraded`。
- **连锁错误**：TaskRuntime 若降级为 Noop，需要在 `conversation_service_module.set_task_queue_accessors` 内做防御，避免调用者无限重试；同時為 API 回傳對應錯誤碼。
- **災復測試**：生產需在無網絡環境下驗證 Telegram probe 失敗時的啟動行為，確保其他行為（如 `/api/prompts`）仍然可叫用。

## 约束与验收（GIVEN/WHEN/THEN）
1. **Mongo 必須為硬依賴**
   - GIVEN MongoDB 進程未啟動
   - WHEN `/api/prompts` 被呼叫
   - THEN API 回傳 `503`， body 包含 `{ "capability": "mongo", "status": "unavailable" }`，且系統仍能回覆 `/healthz`。
2. **Telegram 為軟依賴**
   - GIVEN `api.telegram.org` 無法連通
   - WHEN 啟動 FastAPI
   - THEN `lifespan` 完成並 `/healthz` 顯示 `telegram_webhook: degraded`，`/api/prompts` 正常工作，`/telegram/webhook` 回覆 `503`。
3. **能力自動恢復**
   - GIVEN Redis 初始檢查失敗，registry 記錄 `redis=unavailable`
   - WHEN Redis 後續恢復且背景 probe 重試成功
   - THEN registry 將狀態更新為 `available`，log 產生 `capability.state_changed`，TaskRuntime 自動切換回實際 Redis submitter。
4. **健康檢查輸出一致性**
   - GIVEN 任一能力狀態改變
   - WHEN 調用 `/healthz/startup`
   - THEN HTTP 狀態與 JSON 內容同步更新，不需重新啟動服務即可查詢。

## 待辦 / 後續
- 實作 `capabilities.py`、`NoopTaskRuntime` 與 `/healthz` 擴充。
- 為 Mongo/Redis/Rabbit/Telegram Probe 編寫整合測試，驗證 503 行為與日誌輸出。
- 在部署管線新增 smoke test：啟動時刻強制關閉 Telegram 出口，確保服務仍對外開 HTTP。
