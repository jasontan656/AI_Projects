# CLI 控制台单面板方案（session_20251107_1150）

## 背景
- 先前在 `project_utility/logging.py` 增加 `ConsoleDashboardHandler`，利用 Rich `Layout` 将状态面板与告警面板上下堆叠，但运行中仍出现两块 Panel 并在状态刷新时反复重绘，终端输出 “跳屏”、“闪烁”。
- `_render_feed` 在 `Group` 不可用时直接访问 `Panel.renderable`，导致 `AttributeError` 及告警日志；同时 capability 列表为动态增删，导致列宽与内容频繁重算。
- 用户目标：**只保留一个运行面板**，内部先显示固定 slot，再在下方顺序插入错误/运行日志 Panel，整体布局绝不重新分配列；警告/错误仍需去噪并展示 “(+N suppressed)”。

## 目标
1. 控制台输出只有一个 Rich Panel；面板内部包含固定的“核心状态行”与“告警堆栈”两部分。
2. 所有核心 slot（启动流程、TaskRuntime、KnowledgeSnapshot、Mongo/Redis/RabbitMQ/Telegram Webhook…）在启动阶段即占位，仅更新文案/颜色，不再新增/删除行，避免 Rich 重新计算布局。
3. 告警、错误、运行提示以面板底部堆叠形式输出：每条信息独立 Panel，按时间顺序向下追加，保留去噪/计数。
4. 保障降级/关闭路径：在非 TTY 或 `_runtime_shutting_down()` 时自动退回 `_RichConsoleHandler`，防止 interpreter 退出阶段出现 `ImportError`。

## 设计方案
### 1. 新的 renderable 结构
- 使用 `rich.console.Group` 管理两个子区块：
  - **状态区**：`Table.grid` 预置 `_CORE_STATUS_TEMPLATE`（startup、knowledge_snapshot、task_runtime）与 `_CAPABILITY_TEMPLATE`（mongo、redis、rabbitmq、telegram_webhook），每行三列（标签/状态/说明）。行数固定；额外 capability 统一追加至 “其他依赖” 子表，但仍在同一 Panel 内，不增减列。
  - **输出区**：将 `_alerts` 映射为 `List[Panel]`，每条 Panel 标题取自 `_level_label`，`border_style` 由 `_panel_style` 决定；`Group` 顺序即时间顺序。若 `Group` 不可用则退化为 `Table.grid` 单列排布。
- 将两个区块组合为 `Group(status_panel_renderable, feed_panel_renderable)`，再统一包裹在 `Panel`（标题如 “运行面板”）。`Live.update()` 始终传入同一个 Panel 引用，只替换其内部 Text/Group 内容。

### 2. 状态更新策略
- `_set_core_status(slot, status, detail)` 仅修改模板中的字典，不再插入新 key。
- `_set_capability_status()` 先查 `_CAPABILITY_TEMPLATE`；若未覆盖，则写入 `_extra_capabilities`，并在状态区末尾以 “其他依赖” 表格一次性渲染，避免逐条插行。
- `_apply_state()` 增加 Telegram backlog、Redis backfill 等 hooks 时，只允许变更 `detail` 文案，严禁 `pop` 行。

### 3. 告警堆栈策略
- `_alerts` 改为 `OrderedDict[str, _DashboardAlert]`（key=logger+message+capability+request_id），依旧 60 秒内合并并 `count += 1`。
- `_render_feed()` 仅依赖 `_alerts` 的存量 Panel；若告警列表为空，则在 Panel 内渲染 “暂无告警”。
- 设定 `_max_alerts = 8`；超过时 `popitem(last=False)`，并在 `self._logger.info("dashboard.feed_evicted", extra={"removed": key})` 记录，方便运维查证。

### 4. Handler 生命周期
- 在 `__init__` 中如果任一 Rich 组件不可用（Console、Group、Panel、Table、Text），直接回退 `_RichConsoleHandler`；不要保留一个 `self._live=None` 的半成品 handler。
- `close()` 必须检查 `_live.started` 再调用 `stop()`（Rich 0.13+ 允许重复 stop，但最好用 `if self._live.is_started:` 做防御）；`atexit.register(self.close)` 保留。
- `_runtime_shutting_down()` 或非 TTY：`_build_rich_console_handlers()` 应返回 `_RichConsoleHandler` + `_RichAlertHandler` 组合。

## Success Path & Core Workflow
1. **启动阶段**：`ConsoleDashboardHandler` 构建单一 Panel → 状态区显示 `starting...`/`pending` → `Live.update()` 输出静态面板，无多余闪烁。
2. **探针回报**：`capability.state_changed` 更新对应 slot 文案/颜色，面板位置不变；新告警以 Panel 方式附加到底部，`(+N suppressed)` 通过 Text 行展示。
3. **运行期间**：`_max_alerts` 保证 feed 至多 8 条；旧消息自动淘汰但状态行始终保留完整 snapshot。
4. **退出流程**：`lifespan finally` → `ConsoleDashboardHandler.close()` → `Live.stop()` 停止刷新 → TTY 释放，日志中不再出现 `ImportError` 或 `Unclosed session`。

## Failure Modes & Defensive Behaviors
- **非 TTY / CI 输出**：检测 `console.is_terminal`，若为 False，直接返回 `_RichConsoleHandler`，并记录 `dashboard.disabled`（理由=not_tty）。
- **Rich 组件缺失**：若 `Group/Layout` 任一 import 失败，handler 自动降级，避免运行期间才触发 ImportError。
- **告警爆量**：`_max_alerts` + `feed_evicted` 日志作为 backpressure；必要时可进一步写入 `var/logs/current.log`。
- **异常渲染**：`_render_view`/`_render_feed` 全程包 `try/except`，一旦 Rich 抛异常则回退到 `_RichConsoleHandler` 并输出 `dashboard.render_error`。
- **状态字典污染**：所有 slot 更新通过 `_set_core_status/_set_capability_status` 完成，内部复制 template，避免共享引用被外部修改。

## 约束与验收（GIVEN / WHEN / THEN）
1. **单面板输出**
   - GIVEN 启动 Uvicorn \
   - WHEN Rich handler 初始化完成 \
   - THEN 控制台仅显示一个 Panel，标题“运行面板”或等效文案，不再出现左右/上下两个 panel。
2. **无闪烁刷新**
   - GIVEN 后台每秒产生日志 \
   - WHEN 状态/警告刷新 \
   - THEN 面板位置/行数保持不变，终端不会因为重绘而跳动或插入空行。
3. **告警堆叠**
   - GIVEN 同一 warning 在 30 秒内重复触发 3 次 \
   - WHEN handler 输出告警区 \
   - THEN 只出现一条对应 Panel，并在正文中附带 “(+2 suppressed)”。
4. **降级路径**
   - GIVEN 服务在 CI（非 TTY）环境运行 \
   - WHEN 日志初始化 \
   - THEN 直接启用 `_RichConsoleHandler`，不创建 `Live`，控制台无 “Live render failed” 之类报错。
5. **关闭流程**
   - GIVEN 进程收到 `Ctrl+C` \
   - WHEN lifespan `finally` 执行 \
   - THEN `ConsoleDashboardHandler.close()` 已停止 `Live`，退出日志中无 `ImportError: sys.meta_path is None` 或 `RuntimeWarning: coroutine close was never awaited`。

---
该文档确保 CLI 控制台遵循“单面板 + 垂直堆叠”范式，并覆盖终端差异、告警去噪与退出安全等边界情形，为后续实现与回归测试提供统一蓝本。***
