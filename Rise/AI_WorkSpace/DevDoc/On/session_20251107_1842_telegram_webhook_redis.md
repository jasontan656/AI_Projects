# Telegram Webhook 连续重试与 Redis 7.2 升级开发方案（2025-11-07 18:42 CST）

## 0. 用户约束与背景
- 使用者要求 Telegram 渠道保持“持续重试”策略，不允许在 webhook 不可达时直接中止启动。
- 公网暴露依赖 ngrok 会话，`WEB_HOOK` / `ngrokPublicUrl` 同步配置于 `.env:55-62`，需要在应用内识别隧道状态。
- Redis 由 Docker 直接拉取镜像，当前 `docker-compose.yml:44-58` 指向 `redis:7.2-alpine`，但代码 `src/foundational_service/persist/redis_queue.py:106-139` 尚未兼容 Redis 7.2+ 新的 `XAUTOCLAIM` 回包格式，导致 `ValueError` 并停摆整个 `persist.worker`。
- 最新日志（`var/logs/current.log` 2025-11-07 18:38-18:41）持续出现 `startup.telegram_backlog.*` 以及 backlog 检测告警，说明 webhook 检测逻辑缺乏可观测细节，且默认保留 backlog 造成后续洪峰。

## 1. 设计目标
1. **持续重试但可观测**：不改变持续重试策略，但在 Interface Layer 内必须输出详尽上下文、区分“链接不可达”与“Telegram backlog 超标”两种态。
2. **ngrok 依赖可视化**：通过 Foundational Service 层提供 `public_url_probe`，将隧道健康度注入 `CapabilityRegistry`，避免 webhook 健康与公网连通性混淆。
3. **Redis 队列可继续升级**：修复 `XAUTOCLAIM` 解包并在 Compose 层锁定 `redis:7.2.4-alpine3.20`，确保未来升级时不会再因协议细节把 `persist.worker` 掀翻。
4. **日志=业务证据**：所有自动重试/降级路径都要在日志 message 中包含异常类型（不只 `extra`），以便 1 人团队无需结构化日志平台也能定位问题。

## 2. 架构调整总览
| 关注点 | 层级 | 调整方向 |
| --- | --- | --- |
| Telegram backlog 探针 | Interface / Entry (`src/interface_entry/bootstrap/app.py:600-739`) | 拆成「链路检测」+「backlog 策略」，将异常注入 `CapabilityRegistry`，并把 `_handle_pending_updates` 的异常摘要直接写入 `log.error` message。 |
| ngrok 公网探测 | Foundational Service | 新建 `interface_entry.runtime.capabilities.PublicEndpointProbe`，定时 `HEAD <WEB_HOOK>`，失败时写入 `capability=public_endpoint` 状态并触发 `RuntimeSupervisor` retry。 |
| Redis Stream auto-claim | Foundational Service (`redis_queue.py:106-139`) | 容错 2/3/4 元组回包，记录 `deleted` 数量，升级 Compose 镜像并为 `persist.worker` 加上启动前 `PING` 校验。 |
| Backlog 决策策略 | Business Service (conversation) & Interface | backlog>0 时仍保持“保留更新”，但在 `telemetry` 内记录 `pending_update_count`、`decision=keep`，再由业务层根据 `message.date` 过滤陈旧消息。参考社区推荐在 webhook 重新注册时使用 `drop_pending_updates` 以清空堆积，必要时通过 `deleteWebhook+setWebhook(drop_pending_updates=True)` 组合处理citeturn0search0turn0search1。 |

## 3. 方案细节
### 3.1 Telegram webhook 连续重试（Interface Layer）
1. **拆分探针**：
   - `webhook_transport_probe`: 仅调用 `get_webhook_info`，失败时标记 `status="transient-error"` 并记录异常 repr；恢复后写入 `startup.telegram_backlog.recovered`。
   - `backlog_policy`: 读取 `pending_update_count`，>0 时 `CapabilityRegistry.set_state("telegram_backlog", CapabilityState(status="warning", detail=f"pending={pending}", ttl=60))`。
2. **日志增强**：`log.error("startup.telegram_backlog.unexpected_error: %s", repr(exc), extra=...)`，确保 message 自带异常摘要。
3. **守护式重试**：在 `RuntimeSupervisor` 内注册 `webhook_transport_probe`，失败时以指数退避（1s→90s）重复，直到打通。与用户约束一致：永不 hard fail，但也不会静默。
4. **backlog 时间窗过滤**：在 `interface_entry.telegram.routes` 里将 `update.message.date` 与最近“应用启动时间”对比，旧消息直接打入 `telemetry.backlog_drop_count`，避免 ngrok 恢复后“旧指令”误触发。该策略需与 Business Service 层 `conversation.service.process_update` 联动，在 `behavior_telegram_inbound` 前加入 `if update.date < startup_timestamp: return IgnoredUpdate`。

### 3.2 ngrok 公网探测
1. **Probe 定义**：新增 `PublicEndpointProbe`（Foundational Service），读取 `app.state.public_url`，执行 `asyncio.to_thread(requests.head, public_url, timeout=3)`。
2. **异常处理**：
   - 证书/SSL 错误：记录 `status="insecure"`，提示检查 ngrok TLS。
   - 连接超时：`status="down"`， detail= `errno`。
3. **触发策略**：
   - 启动后立即运行一次；若失败，`CapabilityRegistry` 将 `telegram_webhook` 标记为 `blocked-by-public-endpoint`。
   - 由 `RuntimeSupervisor` 每 60 秒调度；连续 5 次失败后发出 `log.warning("public_endpoint.unreachable", consecutive_failures=5)`。
4. **运维动作**：在日志/console dashboard 中把 `public_url` 状态放在单独 slot，方便观察 ngrok 熔断。

### 3.3 Redis 7.2 升级 + 队列修复
1. **镜像锁定**：在 `docker-compose.yml` 中将 `redis:7.2-alpine` 替换为 `redis:7.2.4-alpine3.20`，同时在 `var/docker/redis` 增加 `appendonly.aof` 快照备份指引（文档内说明）。
2. **auto_claim 兼容**：
   ```python
   resp = await self._redis.xautoclaim(...)
   # redis-py>=5 返回 (next_id, entries, deleted, errors)
   if isinstance(resp, (list, tuple)):
       next_id = resp[0]
       entries = resp[1] if len(resp) > 1 else []
       deleted = resp[2] if len(resp) > 2 else 0
       errors = resp[3] if len(resp) > 3 else None
   ```
   - 将 `deleted` 计数写入 `log.debug("redis.auto_claim.deleted", deleted=deleted)` 以监控 stream 健康。citeturn1search0
3. **任务恢复**：`persist.worker` 启动时调用 `redis_queue.healthcheck()`（`PING` + `XPENDING`），若失败则记录 capability `task_runtime=degraded` 并 30 秒后重试。
4. **测试策略**：由于生产即测试，升级步骤需在文档中列出顺序：`docker compose pull redis && docker compose up -d redis` → 等待健康检查通过 → 重新启动应用。

## 4. 成功路径（核心流程）
1. 应用启动 → `PublicEndpointProbe` 成功 → `CapabilityRegistry` 标记 `public_endpoint=ok`。
2. `_handle_pending_updates` 首次成功，发现 `pending=0` → 直接注册 webhook → `RuntimeSupervisor` 进入监控态。
3. Redis `auto_claim` 兼容逻辑稳定运行，`persist.worker` 可在任务消费者失联后 60 秒自动接管。
4. 任意时刻 ngrok 慢/Telegram 抖动 → `webhook_transport_probe` 连续失败 → 能见度提升，运维可在 console 面板看到精准状态。

## 5. 失败模式与防御
- **ngrok 会话中断**：`PublicEndpointProbe` 连续失败 5 次 → `CapabilityState(status="critical", detail="public_url down")`，同时触发 `RuntimeSupervisor` 级别警报，提醒手动重启 ngrok。
- **Telegram backlog 激增**：`pending_update_count > BACKLOG_MAX (默认 200)` → 记录 `log.warning("telegram_backlog.saturated", pending=...)`，并建议手动执行 `deleteWebhook+setWebhook(drop_pending_updates=True)` 以清零队列citeturn0search0turn0search1。
- **Redis stream 数据腐化**：`auto_claim` 收到 `errors` 字段时直接 raise，并在日志中输出 `stream_id`，避免静默丢任务；`deleted` 超过阈值（例如 100/min）时触发 `log.warning("redis.stream.trimmed")`，提示是否需要 `XTRIM` 策略。

## 6. 约束与验收 (GIVEN/WHEN/THEN)
1. **GIVEN** ngrok 提供的 `WEB_HOOK` 可访问，**WHEN** `PublicEndpointProbe` 执行 `HEAD`，**THEN** `CapabilityRegistry.get_state("public_endpoint")` 必须在 3 秒内返回 `status="ok"`。
2. **GIVEN** Telegram 端存在 backlog>0，**WHEN** `_handle_pending_updates(interactive=False)` 完成，**THEN** 日志需包含 `pending_update_count`、`decision=keep`，且 `capability_state("telegram_backlog")` 进入 `warning` 并在 backlog 清零后 60 秒自动恢复。
3. **GIVEN** Redis 版本 ≥7.2，**WHEN** `persist.worker` 触发 `auto_claim()`，**THEN** 不得抛出 `ValueError`，并且 `claimed` 的消息会在 1 次循环内被 `_decode_entries` 完整消费。
4. **GIVEN** backlog 清理需求，**WHEN** 运维执行 `setWebhook(drop_pending_updates=True)`，**THEN** 下次 `_probe_telegram_webhook()` 必须在 30 秒内把 `pending_updates` 观测到 0，并输出 `startup.telegram_backlog.cleared`（新增日志）。

## 7. 实施顺序
1. 在 Foundational Service 中新增 `PublicEndpointProbe` 与 `redis_queue` 健康检查，保证 capability pipeline 完整。
2. Refactor `_handle_pending_updates` 功能块，加入日志 message 直接带异常、分层 capability 更新。
3. 升级 docker Redis 镜像并编写 rollout 指南（含快照与回滚步骤）。
4. 为 Business Service `conversation.service` 添加旧消息过滤逻辑，配合 backlog 决策记录。
5. 更新 console dashboard 模板，加入 `public_endpoint`、`telegram_backlog`、`redis_stream` 三个 slot，确保 1 人团队能快速定位核心依赖。
