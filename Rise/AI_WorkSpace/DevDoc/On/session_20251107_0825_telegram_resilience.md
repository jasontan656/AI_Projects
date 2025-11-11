# Telegram Webhook 弹性改造（session_20251107_0825）

## 背景
- 现有 `src/interface_entry/bootstrap/app.py` 在 FastAPI lifespan 中同步执行 `_verify_telegram_connectivity()` 与 `_handle_pending_updates()`；任一失败会抛出 `TelegramWebhookUnavailableError` 并阻断整个 HTTP 服务。
- 运行环境中 Telegram API 访问需穿越企业出口/代理，`api.telegram.org:443` 并非始终可达；当前代码未提供降级路径，导致前端、其他 API 也被迫离线。
- 同时，Mongo/Redis/RabbitMQ 运行在 docker 网络；`MONGODB_URI` 等变量必须使用容器互联地址（例如 `mongodb://host.docker.internal:27017` 或 Compose service name），否则应用永远连接不到 `localhost`。

## 目标
1. Telegram 探测失败时只将能力标记为 `degraded`，允许 FastAPI 正常启动，其余 API 正常服务。
2. 引入显式的“跳过 Telegram 探测”与“代理配置”开关，便于在受限网络中运行。
3. 对 Mongo/Redis/Rabbit 的 `CapabilityRegistry` 探针读取 docker 环境参数，避免默认 `localhost`。
4. 在文档/脚本层给出检查命令，方便运维验证容器端口、代理配置以及 Telegram webhook 状态。

## 改造方案
### 1. Lifespan 探测与降级
- 将 `capability_registry.run_all_probes()` 提前到 `create_app()`，并把结果写入 `app.state.capabilities`。
- 修改 `_handle_pending_updates()`：捕获所有异常后返回 `{"status": "degraded", "error": str(exc)}`，外层仅调用 `capability_registry.set_state("telegram_webhook", CapabilityState(status="degraded", ...))`，绝不重新 raise。
- 增加 `TELEGRAM_PROBE_MODE` 环境变量：
  - `active`（默认）：执行完整探测；
  - `skip`: 直接写入 `degraded`，跳过任何网络访问；
  - `webhook-only`: 跳过 socket 检查，仅调用 `get_webhook_info()` 验证现有 webhook。
- 若 `capabilities.telegram_webhook` 为 `degraded`，`interface_entry/telegram/routes.py` 在入口 `router.post(webhook_path)` 处返回 `HTTP 503`，而非阻断其它路由。

### 2. Docker 数据库地址调度
- `.env` 中新增：
  ```ini
  MONGODB_URI=mongodb://mongo:27017
  REDIS_URL=redis://redis:6379/0
  RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
  ```
  其中 `mongo/redis/rabbitmq` 对应 docker-compose 服务名；在本地裸机调试时可改成 `host.docker.internal`。
- Capability 探针读取以上 URI，并在日志 `startup.capability` 内记录 `endpoint`；若仍指向 `localhost`，能够快速告警。

### 3. 观测与脚本
- `/healthz/startup` 输出所有 capability 状态，供部署后确认。
- 新增脚本 `tools/telegram_probe.py`：
  ```bash
  python tools/telegram_probe.py --token $TELEGRAM_BOT_TOKEN --webhook $WEB_HOOK --proxy http://proxy:8080
  ```
  功能：调用 `getWebhookInfo`，若失败则打印代理/网络诊断建议。
- 新增脚本 `tools/docker_db_check.py` 验证 docker 网络与端口映射：
  - `docker compose exec mongo mongosh --eval "db.runCommand({ ping: 1 })"`
  - `docker compose exec redis redis-cli PING`
  - `docker compose exec rabbitmq rabbitmq-diagnostics ping`

## Success Path & Core Workflow
1. 启动阶段：
   - `create_app()` 注册 capability probes，依据 `.env` 地址连接 docker 服务。
   - Telegram probe 根据 `TELEGRAM_PROBE_MODE` 选择执行策略；失败写入 `degraded`。
   - Lifespan 完成后 `/healthz` 返回 `status=ok|degraded`。
2. 运行时：
   - `/telegram/webhook` 每次请求先检查 `registry.require("telegram_webhook", hard=False)`，若 `degraded` 则即时 503，日志记录 `capability=telegram_webhook`。
   - 其他 API（prompts/pipelines/workflows）因 Mongo 已在 docker URI 上监听，`capability.require("mongo")` 成功放行。
   - 后台任务通过新的 `tools/telegram_probe.py` 定期巡检，并可在成功后主动把 `capabilities.telegram_webhook` 设置回 `available`。

## Failure Modes & Defensive Behaviors
- **网络仍受限**：`TELEGRAM_PROBE_MODE=skip` 可立即启动；scripts/healthz 仍显示 degraded，提醒运维补齐代理配置。
- **docker 服务改名**： capability probe 日志包含 `endpoint`，若部署时填错 service name，可快速定位。
- **代理认证失败**：`tools/telegram_probe.py` 支持 `--proxy-user/--proxy-pass`；调用失败会提示 407/403 等状态，且在日志内写入 `proxy_error`。
- **脚本未运行**：在 CI/CD 中新增 step 调用 `python tools/docker_db_check.py`; 若失败则阻止部署。

## GIVEN / WHEN / THEN 验收
1. **Telegram 阻断但服务上线**
   - GIVEN `TELEGRAM_PROBE_MODE=skip`
   - WHEN `uvicorn` 启动完成
   - THEN `/healthz` 返回 `status: "degraded"`，`capabilities.telegram_webhook.detail` 为 "probe skipped"，而 `/api/prompts` 正常 200。
2. **代理恢复**
   - GIVEN 运行 `tools/telegram_probe.py --webhook $WEB_HOOK`
   - WHEN 脚本输出 `status=ok`，后台任务调用 `capability_registry.set_state("telegram_webhook", available)`
   - THEN `/healthz` 立即显示 `telegram_webhook.status=available`。
3. **Mongo docker 地址配置错误**
   - GIVEN `.env` 中误填 `MONGODB_URI=mongodb://localhost:27017`
   - WHEN 启动应用
   - THEN capability probe log 输出 `startup.capability` with `status="unavailable"`, `/api/prompts` 返回 503（body: `{ "capability": "mongo" }`）。
4. **脚本巡检失败**
   - GIVEN `tools/docker_db_check.py` 在 CI push 阶段运行
   - WHEN `redis-cli PING` 返回非 `PONG`
   - THEN CI 失败并提示“redis container unreachable”，阻止错误配置上线。

## 防御与后续
- 所有 capability 变更记录在 `var/logs/rise-info.log` 中的 `capability.state_changed`，便于排查回溯。
- 若未来需要更多渠道（如 WhatsApp webhook），可沿用同一 `CapabilityRegistry` 模式：将探针、降级和脚本封装为模板，避免再次出现“某个外部服务阻断导致全站停止”的问题。
