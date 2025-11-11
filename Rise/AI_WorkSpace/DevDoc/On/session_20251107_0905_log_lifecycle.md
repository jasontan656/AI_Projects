# 日志生命周期策略（session_20251107_0905）

## 背景
- 当前日志输出分散在 console（Rich）与 `var/logs/` 文件，前者对开发者友好，后者用于追踪历史。但随着多次重启，`rise-info.log/rise-error.log` 持续累积，排查时需手动寻找最新片段，易被旧内容干扰。
- Console 会显示 warning，但 `var/logs` 中未必同步；此外，当多个实例并存时，很难确保大家参照同一份“最新日志”。
- 用户期望：每次项目启动即建立干净的日志上下文，关闭时清理旧日志文件，确保下一次启动从空白状态开始，便于协同排查。

## 目标
1. **启动阶段**：统一生成一份“同步日志”（例如 `var/logs/current.log`），记录 warning/summary，并在启动前清空旧日志文件夹；必要时保留上一轮日志以便回溯。
2. **运行阶段**：继续保留 debug 级别 `rise-info.log`/`rise-error.log`，但所有对协作有意义的 warning/summary 同步写入 `current.log`，避免“我看得到你看不到”。
3. **关闭阶段**：在 uvicorn/shutdown hook 中安全终止 logger 并根据策略清理旧日志（如仅保留最近一次运行的归档 zip 或 `previous.log`）。
4. **防御**：若应用异常退出，仍能找到最新日志；清理过程若失败，不影响主流程。

## 实施计划
### 1. 日志目录规范
- 目录结构：
  ```
  var/logs/
    ├── current.log        # 当前运行的同步日志（warning/summary）
    ├── rise-info.log      # 详细 info/debug
    ├── rise-error.log     # stacktrace/error
    └── archive/
         └── 2025-11-07T08-58-00Z.zip  # 关闭时打包的历史日志
  ```
- 启动前：
  1. 若 `archive` 不存在则创建。
  2. 将 `current.log`、`rise-info.log`、`rise-error.log`（若存在）压缩成 `archive/<timestamp>.zip`，方便回溯。
  3. 清空 `var/logs/` 根目录（仅保留 `archive/`）。

### 2. logging 配置调整
- 在 `project_utility/logging.py` 中新增 `SyncLogHandler`：
  - 级别：WARNING 及以上。
  - 输出格式：`[2025-11-07 08:59:01][WARNING][context] 中文/英文摘要`。
  - 作用：所有 warning/error 自动同步到 `current.log`，并在 console 提供中文摘要，确保双方看到一致信息。
- Console Formatter：加入关键 warning 的中文说明，如 `task_runtime.disabled -> 任务队列降级，Redis 未连接`。
- 维持现有 Rich 面板，但默认只在 DEBUG 级别打印。

### 3. 启动/关闭钩子
- 在 `interface_entry/bootstrap/app.py`：
  - 启动前（`create_app` 开始处）调用 `initialize_log_workspace()`：实现归档、清理与 `current.log` 的 handler 注册。
  - Lifespan 结束或 `SIGTERM` 时调用 `finalize_log_workspace()`：
    - 强制 flush handler。
    - 根据配置决定是否删除 `current.log`（默认保留最新一次；可通过 env `LOG_CLEANUP_MODE=purge` 来在关闭时直接删除所有日志）。
- 若进程异常崩溃，`finalize` 可能没执行，所以上述 handler 需在 `atexit` 注册以尽可能收尾。

### 4. 成功路径 / 核心流程
1. `create_app()` 调用 `initialize_log_workspace()`：
   - 归档旧日志 -> 清空目录 -> 注册 `SyncLogHandler`。
   - 控制台打印 `日志目录已重置`。
2. 服务运行：
   - warning/error 同步写入 `var/logs/current.log`，同时输出中文摘要，INFO/DEBUG 仍写 `rise-info.log`。
3. 关闭（正常终止）：
   - 执行 `finalize_log_workspace()`：flush -> 可选删除 -> 输出 `日志清理完成`。
   - `current.log` 连同 `rise-info/error` 自动归档成 zip，供下次调试。

### 5. 失败模式与防御
- **归档失败**：如果 zip 操作遇到权限/IO 错误，记录 warning 但不阻断启动；继续使用旧日志文件（在 `current.log` 首行提示归档失败）。
- **清空失败**：若无法删除旧文件，尝试重命名；最终至少保证 `current.log` 是新的。
- **异常退出**：`atexit` hook 保底调用 `finalize_log_workspace()`；若仍失败，手动提醒用户下次启动前清理 `var/logs`。

### 6. GIVEN / WHEN / THEN
1. **清理策略生效**
   - GIVEN `var/logs` 内存在旧日志
   - WHEN 重启服务
   - THEN 启动日志记录 `日志目录已归档`，`current.log` 仅包含本次运行输出。
2. **Warning 同步**
   - GIVEN Redis 未连接导致 `task_runtime.disabled`
   - WHEN warning 产生
   - THEN console 输出中文摘要，同时 `var/logs/current.log` 写入相同信息。
3. **关闭清理**
   - GIVEN 设置 `LOG_CLEANUP_MODE=purge`
   - WHEN 服务正常停止
   - THEN `var/logs` 目录仅剩 `archive/<timestamp>.zip`，无残留 current/info/error 文件。

## 防御与后续
- 后续可拓展为“保留最近 N 次归档”或“只在 develop 环境清理，生产环境保留完整日志”。
- 若启用了集中式日志（ELK/CloudWatch），依然推荐保留本地 `current.log`，方便本地快速 diff。
- Console 摘要的文案需要持续维护，确保业务团队能够快速理解 warning 的影响及下一步动作。
