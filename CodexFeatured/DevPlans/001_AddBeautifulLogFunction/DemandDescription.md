# 开发需求 — 终端美化输出与错误可读性（仅使用 Rich）

## 功能需求

- 终端输出统一美化：信息/成功/警告/错误/调试五类等级，统一时间戳、对齐与缩进；长文本自动换行并保持对齐。
- 仅终端范围：本阶段仅关注“终端展示”，不做文件日志、JSON 结构化、审计/安全/性能日志等能力（后续迭代）。
- 错误可读性：启用富文本堆栈 Pretty Traceback，含异常类型、消息、文件:行号、代码片段与帧路径折叠；可选显示局部变量。
- 主题与可读性：提供内置主题，关键等级具备颜色/强调样式，对比度不低于 4.5:1；支持 `--no-color`/无颜色终端回退。
- 兼容性：在 Windows Terminal/PowerShell、WSL、Git Bash 下正确渲染；宽度自适应，支持软换行。
- 配置能力：等级、颜色开关、Traceback 参数（最大帧数/是否显示局部变量）、控制台宽度、主题选择可配置。
- 依赖约束：第三方依赖仅允许 Rich；可使用标准库（如 logging、argparse、os、sys）。

## 技术选型

- 语言/运行时：Python 3.10+
- 第三方库：`rich>=13.x`（仅此一项）
- 标准库：`logging`（用于等级与消息来源对接到终端）、`traceback`/`sys`、`os`、`datetime`。
- 渲染组件：`rich.console.Console`、`rich.theme.Theme`、`rich.panel`、`rich.table`、`rich.logging.RichHandler`、`rich.traceback.install`。
- 禁用/限制：不引入 `loguru`、`colorama`、`Typer/Click` 等额外依赖；CLI 仅采用轻量自实现或现有入口对接。
- 不在本阶段实现：文件轮转、JSON 结构化落盘、审计/安全/性能/追踪日志、异步写盘/压缩归档等。

## 模块/目录结构

```text
Kobe/SharedUtility/RichLogger/
  __init__.py            # 对外 API（初始化、获取 Console、开关 Traceback/Handler）
  console.py             # Console 单例、主题加载与宽度/颜色配置
  logging_setup.py       # 安装 RichHandler、等级映射、格式模板（仅输出到终端）
  traceback_setup.py     # 安装 rich.traceback（是否显示局部变量、最大帧、路径折叠）
  styles.toml            # 主题与等级样式（保证对比度≥4.5:1）
  README.md              # 说明与示例（非强制，开发者文档）
```

- 设计约束：
  - 仅输出到终端 Console，不创建任何文件句柄或持久化落盘行为。
  - 主题与样式集中管理（`styles.toml`），可替换但需通过对比度校验。
  - 初始化过程幂等（重复安装不会产生重复 Handler/Hook）。

## 接口约定

- `init_console(options)`：根据选项创建/配置 Console（宽度、颜色开关、主题）。
- `install_rich_logging(level, markup=True, show_time=True)`：安装 `RichHandler` 至根 logger，仅指向 Console；不得创建文件 Handler。
- `install_rich_traceback(show_locals=False, max_frames=50, theme=None)`：启用 Pretty Traceback，控制帧数、变量显示与主题。
- `get_console()`：返回全局 Console 实例，用于打印结构化终端内容（表格/面板/高亮文本）。
- 配置输入（任选其一）：
  - CLI 入口（现有程序中）：`--log-level`、`--no-color`、`--traceback-locals`、`--traceback-max-frames`、`--console-width`、`--theme`。
  - 环境变量：`RICH_LOG_LEVEL`、`RICH_NO_COLOR=0|1`、`RICH_TB_LOCALS=0|1`、`RICH_TB_MAX_FRAMES`、`RICH_CONSOLE_WIDTH`、`RICH_THEME`。

## 依赖策略与准入标准

- 当前阶段仅允许依赖：`rich>=13`；除此之外禁止引入第三方依赖。标准库优先：`logging`、`argparse`、`json`、`pathlib`、`traceback`、`sys`、`os`、`datetime`。
- 适用性说明：本需求聚焦“终端可视化与日志可读性提升”，Rich 与标准库即可满足本迭代目标；结构化 JSON、日志轮转与归档等高级能力暂不纳入。
- 与开发宪章一致性：遵循 BackendConstitution 中对 Python 3.10 与统一日志设施（Kobe/SharedUtility/RichLogger）的约束。
- 兼容性要求：对外接口不暴露 Rich 具体类型；通过抽象封装 Console/Handler，保留后续替换或扩展空间。
- 依赖准入门槛（未来如需新增）：
  - 价值明确且可量化（维护/性能/安全/可观测）。
  - 官方/社区最佳实践背书（参考 Common/BestPractise.md 中的官方文档）。
  - 具备迁移与退场策略（可替代方案、影响评估、回滚方案）。
  - 不引入非必要运行时耦合，体积与冷启动影响可接受。



## 验收标准补充

- 依赖约束：工程依赖仅包含 `rich` 与标准库，静态导入扫描无其他第三方引用。
- 可配置关闭渲染：支持 `--no-color` 或环境变量关闭彩色输出，关闭后功能仍可用。
- 抽象封装：日志与控制台封装遵循抽象层，外部模块不直接依赖 Rich 具体类型。
- 文档更新：README/使用说明明确依赖策略与后续扩展路径。

## 范围与限制补充

- 不纳入：`structlog`、`Typer/Click`、异步/跨进程日志、日志轮转/压缩/归档、JSON 结构化落盘等。
- 如未来引入上述依赖，需按“依赖准入门槛”流程评审，并同步更新本开发需求与验收标准。

## 验收标准（DoD）

- 终端美化：
  - 日志等级映射清晰（DEBUG/INFO/SUCCESS/WARNING/ERROR），颜色与图标一致，禁用颜色时无 ANSI 残留。
  - 长消息自动换行，列对齐不破版；表格/面板用于关键数据的高可读展示。
  - 主题颜色对比度不低于 4.5:1，并可通过配置更换主题。
- 错误可读性：
  - 抛出异常时展示 Rich Pretty Traceback，包含异常类型、消息、至少前/后关键帧文件:行号与代码片段。
  - 可通过开关显示局部变量；路径折叠规则对第三方库目录生效，项目代码路径默认展开。
- 依赖约束：
  - 项目新增第三方依赖仅包含 Rich；不引入其他第三方 TUI/日志库。
- 兼容与回退：
  - 在 Windows PowerShell、WSL、Git Bash 终端均可正确渲染；`--no-color` 或非彩色终端下正常纯文本回退。
- 配置与幂等：
  - 重复初始化不产生重复 Handler；`log level`、`no-color`、`traceback.*` 等配置可通过 CLI 或环境变量生效（后者优先级低于 CLI）。

## 非目标/范围外

- 文件日志（含轮转/压缩/留存）、JSON 结构化日志、审计/安全/性能/追踪日志、异步/多进程写盘。
- 引入或绑定额外 CLI 框架（Typer/Click 等）。
- 分布式/集中式日志汇聚与观测性方案。
