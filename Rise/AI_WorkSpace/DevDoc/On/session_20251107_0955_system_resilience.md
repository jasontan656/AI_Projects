# 系统运行自愈与观测升级方案（session_20251107_0955）

## 背景
- 近期在 `src/interface_entry/bootstrap/app.py` 引入 `CapabilityRegistry` 后，启动探针依旧只执行一次；若 Redis/RabbitMQ 失败，`get_task_runtime()` 会永久返回 `DisabledTaskRuntime`，导致任务与快照逻辑无法在依赖恢复后自动重启。
- `var/logs/current.log` 与 `rise-info.log` 持续输出 `knowledge.redis_unavailable`、`task_runtime.disabled` 以及 `py.warnings` 中的 `RuntimeWarning: coroutine 'RobustConnection.close' was never awaited`、`Unclosed client session`，显示 Lifespan 与 logging 仍存在资源释放瑕疵。
- Docker 侧尚未提供与 `.env` 匹配的 Compose 设置，容器化部署时 Mongo/Redis/RabbitMQ 仍指向 `localhost` 而不可达。
- Console 输出依赖 Rich 的逐行 handler，无法满足“面板式起停状态 + 去噪 Warning/Error”的可视化要求。

## 目标
1. 探针必须支持后台重试与状态切换通知，自动拉起/停止 `TaskRuntime`、Redis 缓存同步等依赖组件。
2. 清理 Warning 与 RuntimeWarning 噪音：避免重复记录 `knowledge.redis_unavailable`、`task_runtime.disabled`，并确保 aiohttp、aio-pika 等资源在 Lifespan 中被优雅关闭。
3. 提供与本地后端一致的 Docker Compose 镜像及 `.env` 约定，确立健康检查脚本和启动顺序。
4. 设计 Rich Console 面板：启动阶段显示 `starting...`，完成后切换为 `OK`，并在面板底部按需附加去噪后的 Warning/Error。

## 能力探针自愈与通知
- **事件驱动**：在 `src/interface_entry/runtime/capabilities.py` 中新增监听接口，例如 `register_listener(name, callback)`；`set_state` 发现 `status` 变化时通过 `asyncio.get_running_loop().call_soon_threadsafe` 触发回调，避免阻塞 Probe。
- **RuntimeSupervisor**（建议置于 `src/interface_entry/bootstrap/app.py` 或 `src/interface_entry/runtime/supervisors.py`）：
  - 监听 `redis`、`rabbitmq`、`mongo` 状态，选择性调用 `await task_runtime.start()` / `await task_runtime.stop()`；同时通知 `KnowledgeSnapshotService` 重新执行 `_sync_to_redis`。
  - 提供 `await supervisor.wait_until("redis", status="available", timeout=60)` 供其他模块在冷启动时串联依赖顺序。
- **Probe Backoff**：`CapabilityProbe` 增加 `base_interval`、`max_interval`、`multiplier` 字段；`_start_capability_monitors()` 根据这些字段使用指数退避并带 jitter（例如 `random.uniform(0.5,1.5)`）调度下一次探测，防止持续写日志。
- **API 降级行为**：
  - `src/interface_entry/http/dependencies.py` 内的 repository 解析器在 `registry.is_available("mongo")` 为 False 时直接抛 `service_unavailable_error`，并记录 `detail`。
  - Telegram webhook、任务提交路由在 capability 为 `degraded`/`unavailable` 时回传 503，同时提示 `Retry-After`。

## Warning 降噪与 RuntimeWarning 处理
- **Redis Sync 防抖**（`src/business_service/knowledge/snapshot_service.py:264-314`）：
  - 在 `_sync_to_redis` 前读取 `CapabilityRegistry`；若 Redis 状态非 `available`，直接返回 `{"status": "skipped"}`。仅当状态从 `available -> unavailable` 或 `available -> degraded` 时输出一次 warning，避免每次定时任务都刷屏。
  - 新增 `RedisSyncBackfill` 任务：当 capability 从 `unavailable` 恢复时，监听器触发一次 `_sync_to_redis(snapshot, reason="backfill_after_recovery")`，保证資料最終一致。
- **TaskRuntime 降级日志**：将 `task_runtime.disabled` 移至 capability 监听器，仅在降级/恢复瞬间写日志；`DisabledTaskRuntime.submit` 继续抛 `HTTP 503`，但不重复 warning。
- **aiohttp/aio-pika 资源清理**：
  - 在 `lifespan` `finally` 块中包裹 `try/except asyncio.CancelledError`，确保 `await bootstrap_state.bot.session.close()`、`await task_runtime.stop()`、`await rabbit_publisher.close()` 被执行。
  - 在 `project_utility/logging.py` 引入 `_runtime_shutting_down()`（例如检测 `sys.meta_path is None`），一旦 interpreter 进入退出流程即跳过 Rich Panel/同步 log 写入，避免 `ImportError`。
  - 若仍出现 `py.warnings`，可在 `sitecustomize.py` 中針對 `aiohttp.client` 作專屬 warning filter，亦需記錄一次 “warning suppressed”。

## Docker Compose 与环境契约
- **新增 `docker-compose.yml`**：
  - `mongo`: 使用 `mongodb/mongodb-community-server:7.0`，開啟 `--replSet rs0`，volume `./var/docker/mongo:/data/db`，healthcheck `mongosh --quiet --eval "db.runCommand({ ping: 1 })"`.
  - `redis`: `redis:7.2-alpine`，附加 `appendonly yes`，volume `./var/docker/redis:/data`，healthcheck `redis-cli PING`.
  - `rabbitmq`: `rabbitmq:3.13-management`，映射 `5672` 和 `15672`，healthcheck `rabbitmq-diagnostics ping`.
  - 若開發者不啟動 Docker，可在 `.env` 設置 `MONGODB_HOST_OVERRIDE=host.docker.internal` 等參數，使 `_apply_host_override_env` 將 URI 指向宿主。
- **`.env` 更新**：預設 `MONGODB_URI=mongodb://mongo:27017/?replicaSet=rs0`、`REDIS_URL=redis://redis:6379/0`、`RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/`; 並提供 `*_HOST_OVERRIDE` 以便在 Docker Desktop/WSL 中穿透。
- **健康檢查腳本**：擴展 `tools/docker_db_check.py`，在成功/失敗時輸出 JSON summary，並在 CI pipeline 中先行執行 `docker compose up -d` + 該腳本，確保資料層就緒。

## Rich Console 面板
- 在 `project_utility/logging.py` 新增 `ConsoleDashboardHandler`：
  - 透過 Rich `Live` + `Layout` + `Panel`（参照 `rich.layout.Layout`、`rich.panel.Panel`）創建固定骨架：頂部單一面板預置全部核心狀態 slot（Mongo、Redis、RabbitMQ、Mongo、TaskRuntime、KnowledgeSnapshot、Telegram Webhook 等），只允許改變顏色與文案，不允許增刪 slot，避免啟動時面板閃動。
  - 核心狀態顯示：Logging 初始化、Capability snapshot、TaskRuntime 等在初始渲染就標記 `starting...`；啟動完成時僅更新狀態與顏色（綠=OK、黃=degraded、紅=unavailable），無需重新計算 layout，確保面板位置穩定。
  - Warning/Error 進入 handler 時先經過去噪器（保留 `capability`、`reason`、`request_id`），同一訊息在 60 秒內僅顯示一次，其他計數以 “(+N suppressed)” 形式呈現，並以「逐條 Panel 堆疊」的形式附加在核心面板下方，確保錯誤永遠按時間順序向下延伸，不會與狀態卡並排。
  - 若輸出環境無 TTY 或偵測到 `_runtime_shutting_down()` 為 True，Handler 自動降級成傳統 Rich handler；`Live` 結束必須在 `finalize_log_workspace()` 或 Lifespan `finally` 中對 `ConsoleDashboardHandler.close()` 做 `await`/同步釋放，避免 interpreter 退出期間觸發 `ImportError`。
- Dashboard 任務需在 `finalize_log_workspace()` 或 Lifespan `finally` 裡停止 Live refresh，確保關閉時不再寫入 Panel，避免 `ImportError`.

## 成功路径与核心流程
1. `create_app()` 初始化 capability probes、RuntimeSupervisor、ConsoleDashboardHandler；Dashboard 立即顯示 `starting...`。
2. `lifespan` 先執行 `_run_initial_capability_checks()`，寫入 capability 狀態並觸發 supervisor；若依賴不可用，`TaskRuntime` 以 Disabled 狀態啟動。
3. Docker 環境透過 Compose 拉起 Mongo/Redis/Rabbit，CI 使用 `tools/docker_db_check.py` 驗證；`.env` 透過 `*_HOST_OVERRIDE` 自動切換宿主或容器位址。
4. 服務運行期間：
   - Capability monitor 根據 probe backoff 重新檢查；狀態切換時 supervisor 啟停 TaskRuntime/Redis 同步。
   - Console 面板實時刷新核心狀態；僅在新的 warning/error 出現時追加一行摘要。
   - `knowledge.snapshot` 等模組透過 capability 查詢決定是否與 Redis 互動，避免產生多餘 warning。
5. Shutdown：`lifespan` 捕捉 `CancelledError` 也會執行 cleanup，Dashboard 停止刷新，`finalize_log_workspace()` 打包日誌並完成退出。

## 失败模式与防御
- **Probe 永遠失敗**：Backoff 機制避免頻繁 IO；同時 dashboard/`/healthz` 會將 detail 顯示在 capability 卡上，提醒運維干預。
- **Docker 健康檢查失敗**：CI 立即失敗並輸出具體命令結果；本地 `docker compose up` 也會因 healthcheck 不通而重啟容器。
- **Console 不是 TTY**：Dashboard handler 自動降級，確保 log 仍可讀。
- **RuntimeSupervisor cancel**：監聽任務需在 `lifespan finally` 中取消並 `await`，防止 “Task was destroyed but it is pending”。
- **Redis backfill 衝突**：若在 backfill 時 capability 再次降級，Supervisor 應立即取消該 backfill 任務並記錄 `backfill.aborted`。

## 约束与验收（GIVEN / WHEN / THEN）
1. **依赖恢复即自愈**
   - GIVEN Redis 在啟動時不可用且 capability=unavailable \
   - WHEN Redis 服務恢復且 probe 再次成功 \
   - THEN Supervisor 自動 `await task_runtime.start()`，`capability.state_changed` 與 Console 面板同步顯示 `redis=available`。
2. **Warning 去噪**
   - GIVEN Redis 在故障期間 Knowledge snapshot 持續觸發同步任務 \
   - WHEN capability 為 `unavailable` \
   - THEN `_sync_to_redis` 直接返回 `status="skipped"`，console 僅在狀態變化時輸出一次 warning。
3. **Docker 契約**
   - GIVEN 開發者執行 `docker compose up -d` \
   - WHEN `tools/docker_db_check.py` 連續三項檢查通過 \
   - THEN FastAPI `.env` 內的 `MONGODB_URI/REDIS_URL/RABBITMQ_URL` 均指向 compose 服務，`/healthz` 顯示 `status=ok`。
4. **Console 面板**
   - GIVEN Uvicorn 啟動 \
   - WHEN 所有 capability 變為 available \
   - THEN Console 面板上方狀態卡從 `starting...` 變為 `OK`，且不再顯示歷史 warning；若之後 Redis 探針失敗，面板底部追加去噪後的告警並顯示 “(+N suppressed)”。
5. **Lifespan Shutdown**
   - GIVEN 有外部信號觸發 `CancelledError` \
   - WHEN Lifespan 進入 `finally` \
   - THEN Telegram bot session、TaskRuntime、Dashboard Live 均完成 `await close()`，log 不再出現 `Unclosed client session` 或 `ImportError`.

## 2025-11-07 18:25 Telegram 外網策略
- `_handle_pending_updates()` 預設調整為「最多 10 次、每次等待 1 秒」。前 9 次失敗不輸出 warning，只在第 10 次仍無法連上 `api.telegram.org` 時才寫一次 `startup.telegram_backlog.unreachable` / `startup.telegram_webhook.degraded`，避免 ngrok 模擬外網時造成大量噪音。
- 可透過 `TELEGRAM_WEBHOOK_MAX_ATTEMPTS` 與 `TELEGRAM_WEBHOOK_RETRY_DELAY` 覆蓋上述參數；若要調整單次 HTTP 超時，沿用 `TELEGRAM_WEBHOOK_TIMEOUT`。

---
本方案覆蓋 capability 自愈、log 去噪、Docker 合規及 console 可視化四個面向，後續可依優先序拆分為多個開發任務並同步調整測試/CI 流程。***
