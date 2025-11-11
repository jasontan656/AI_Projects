# Rich 控制台流式输出回退方案（session_20251107_1300）

## 背景
- 先前两轮尝试把 CLI 控制台改造成 Rich Live 单面板仪表盘，但在现有终端环境中仍出现刷新抖动、面板重复等体验问题，且实现成本过高。
- 用户决定放弃面板化界面，回退到“逐行打印 + 适度美化”的结构化日志，同时保留已有的降噪、上下文字段与退出安全保障。

## 目标
1. 以 `_RichConsoleHandler` 为核心，按事件顺序逐行输出；保留彩色等级、结构化字段，确保非 TTY/TTY 表现一致。
2. console handler 仍需提供告警去噪（60 秒抑制）与 “(+N suppressed)” 计数，避免 Redis/TaskRuntime 降级类日志刷屏。
3. 退出阶段、非 TTY 环境不再依赖 `Live`，彻底消除 `ImportError` / `RuntimeWarning`。

## 成功路径
1. 启动 FastAPI → `configure_logging()` 挂载 `_RichConsoleHandler`（逐行输出）+ `_RichAlertHandler`（聚合 warning）+ 文件 handler。
2. 正常运行时：每条日志以 `[LEVEL][logger] message key=value` 形式打印；`capability.state_changed`、`task_runtime.*` 等关键事件附带 `capability`、`status`。
3. 告警降噪：同一 key 在 60 秒内重复出现仅提醒一次，其后在 warning handler 中追加 “(+N suppressed)”。
4. 退出时：无 Live，无 Panel，`logging.shutdown()` 足以刷写日志，终端不再出现 Rich 相关异常。

## Failure Modes & Defensive Behaviors
- **TTY 缺失**：与当前退回方案一致，Rich handler 不依赖终端特性；若终端不支持颜色，Rich 自动降级。
- **日志刷屏**：告警 key 仍使用 `(logger, message, capability, request_id)`；若 60 秒窗口内重复 > 100 次，可追加 `dashboard.feed_evicted` 日志提醒。
- **结构化字段缺失**：若关键字段为空，逐行格式使用默认 fallback（例如 `capability=unknown`），保证解析器仍能提取信息。

## GIVEN / WHEN / THEN
1. GIVEN CLI 在 Windows/WSL 终端运行  
   WHEN Redis 依赖不可用连续 10 次  
   THEN 控制台只出现一次 `task_runtime.disabled`，随后仅显示 “(+9 suppressed)” 文案。
2. GIVEN 非交互式环境（CI）  
   WHEN FastAPI 启动并写日志  
   THEN 输出保持为单行文本，无 Rich 面板或 Live 控制字符。
3. GIVEN 服务收到 Ctrl+C  
   WHEN 退出流程执行  
   THEN 控制台无 `ImportError`、`RuntimeWarning`，并在文件日志中完整记录 shutdown。

---
本方案确保我们回到稳定、可维护的日志输出模式，同时保留富文本等级与降噪机制，避免在 CLI 仪表盘上投入过多成本。***
