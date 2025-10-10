# TestSituationCoverageDiscovery — RichLogger 模块

目的：基于项目规范与模块设计，系统性梳理 RichLogger 的可测场景与验证要点，形成可执行的测试清单与运行指引，指导后续自动化/模拟测试落地。

— 输入校验 — 已收到的被测模块参数为 `RichLogger`（非空），流程可继续。

## 模块画像（来自 index.yaml 与代码走查）
- 位置：`Kobe/SharedUtility/RichLogger`
- 公开 API：
  - `init_console(options: dict | None) -> Console`
  - `get_console() -> Console`
  - `init_logging(level: str | None, markup: bool = True, logfile: str | None = None) -> None`
  - `install_traceback(show_locals: bool = False, width: int | None = None, theme: str | None = None) -> None`
- 设计要点：
  - Console：单例、带锁的幂等初始化，支持 `no_color`/`theme`/`width`，可从 `styles.toml` 合并主题。
  - Logging：以 `RichHandler` 为终端处理器，message-only 控制台格式；可选文件输出（结构化时间/等级/记录器/消息）。幂等安装，避免重复 handler。
  - Traceback：`rich.traceback.install`，与 Console 共享上下文，支持 `show_locals`/`width`/`theme`。
  - CLI：`SharedUtility/RichLogger/cli.py` 演示级命令，可切换等级/颜色/主题并触发示例异常。
- 关系：被 `Kobe` 与 `SharedUtility/TaskQueue` 使用；不直接依赖外部服务（无 DB/消息中间件耦合）。

## 规范与约束（对齐项目宪章与最佳实践）
- BackendConstitution（2025-10-10）：
  - Python 3.10；统一使用 `logging`，禁止 `print` 作为日志；应用入口 `Kobe.main:app`；建议在导入期初始化统一日志与富 traceback。
  - 虚拟环境：`Kobe/.venv`；运行配置优先从 `.env` 与环境变量读取。
- SimulationTestingConstitution：
  - 在本地、可复现、隔离外部依赖的前提下，模拟真实运行路径；显式断言期望输出；测试步骤“准备-执行-断言”清晰可读。
- BestPractise 索引：
  - 采用 `rich`（Console/Traceback/Logging）、标准库 `logging`；如需 CLI 演示可用 `argparse`/`Typer`（本模块已用 argparse）。
- CodeCommentStandard：
  - 源码采用“行动-意图-结果”的叙述式注释风格；本文档同样以“目的/步骤/断言/风险”组织用例，保证可读性。

## 测试范围与不测内容
- 测：Console/Logging/Traceback/CLI 的功能、边界、幂等性、并发安全、环境变量与文件输出、异常可读性。
- 不测：外部中间件（Redis/Mongo/RabbitMQ）与 Web 框架 FastAPI/Celery 的集成正确性（它们在本模块中仅通过日志侧面受益）。

## 覆盖矩阵（场景→要点）
- 功能正确性
  - Console：首次/重复初始化；`no_color`、`theme`、`width`；`styles.toml` 的覆盖与缺省行为；`get_console()` 懒加载。
  - Logging：只装配一个 `RichHandler`；等级解析（参数/`LOG_LEVEL`/`RICH_LOG_LEVEL`）；`markup` 开关；文件输出格式与编码。
  - Traceback：`show_locals`/`width`/`theme` 生效；多次安装无副作用。
  - CLI：参数解析、日志输出、`--boom` 触发异常路径、退出码。
- 设计意图与使用方式
  - 在 `Kobe.main` 导入期调用 `init_logging` + `install_traceback`；业务侧统一 `logging.getLogger(__name__)` 取用。
- 交互/并发
  - 多线程同时调用 `init_console` 的原子性；日志风暴下 handler 数量保持 1；Console 单例稳定。
- 故意制造错误
  - 无效 `theme` 回退默认；不可写 `logfile` 时的失败模式；非法等级字符串回退 INFO；非 TTY 或 `no_color=True` 关闭 ANSI。
- 压力与健壮性
  - 10万条日志写入（控制台与文件）性能与内存观察；并发 10/50 线程日志洪峰；安装/卸载（重复 init）稳定性。
- 预期效果验证
  - 控制台仅 message；文件包含 `asctime|level|name|message`；异常栈富渲染可读。
- “数据库读写结果验证”：本模块无 DB；以“文件日志写入/读取校验”替代覆盖此类场景。

## 用例清单（可直接据此补齐/扩展自动化）

1) Console 幂等与 `no_color`
- 目的：重复初始化返回同一实例，`no_color=True` 时禁用 ANSI。
- 步骤：调用 `c1=init_console({"no_color":True,"theme":"default"})`；随后 `c2=get_console()`。
- 断言：`c1 is c2`；`c2.no_color is True`；打印 `"[red]x[/]"` 时无 ANSI 序列。

2) Console 主题与样式文件合并
- 目的：`styles.toml` 中的 token 覆盖默认主题；未知主题回退。
- 步骤：临时写入自定义 `styles.toml`（如 `info = "bright_cyan"`），`init_console({"theme":"default"})`；再 `init_console({"theme":"unknown"})`。
- 断言：`console.theme.styles["info"] == "bright_cyan"`；未知主题生效为默认主题（不抛异常）。

3) Console 宽度与环境变量
- 目的：`RICH_WIDTH` 生效；代码参数优先生效。
- 步骤：设 `RICH_WIDTH=100` 后 `init_console({})`；随后 `init_console({"width":80})`。
- 断言：首次宽度为 100；再次仍返回旧实例（保持 100，不因第二次调用改变）。

4) Logging 幂等与单一 RichHandler
- 目的：多次 `init_logging` 仅存在 1 个 `RichHandler`。
- 步骤：`init_logging(level="DEBUG")` 两次；读取 `root.handlers` 过滤 `RichHandler`。
- 断言：数量恒为 1；根日志等级为 DEBUG。

5) Logging 等级来源优先级
- 目的：`level` 参数 > `LOG_LEVEL` > `RICH_LOG_LEVEL` > 默认 INFO。
- 步骤：分别在四种组合下调用 `init_logging(None)` 并断言 `root.level`。
- 断言：符合优先级；非法字符串时回退 INFO。

6) Logging `markup` 开关
- 目的：关闭 `markup` 时原样输出文本；开启时渲染富样式。
- 步骤：`init_logging(markup=False)` 打印 `[bold red]ERR[/]`；切换 `markup=True` 再打同样内容。
- 断言：前者包含原始方括号文本；后者包含渲染后的可见样式（可通过捕获流 + 正则近似判断）。

7) 文件日志格式与编码
- 目的：验证文件格式 `"%(asctime)s | %(levelname)s | %(name)s | %(message)s"` 与 UTF-8 编码。
- 步骤：`init_logging(level="INFO", logfile="test.log")`；写入一条 `logger.info("你好Ω")`；读取文件。
- 断言：一行包含 `YYYY-mm-dd HH:MM:SS | INFO | <logger> | 你好Ω`；文件为 UTF-8 可无损读回。

8) 文件不可写错误路径
- 目的：`logfile` 指向不可写目录时行为可预期（不影响控制台）。
- 步骤：在只读目录或伪造无法创建位置传入 `logfile`。
- 断言：不新增重复 `RichHandler`；进程不崩溃；可记录一条错误提示或通过异常捕获得到明确原因（根据当前实现，建议增强/记录）。

9) Traceback 安装与本地变量展示
- 目的：`install_traceback(show_locals=True)` 后异常展示局部变量。
- 步骤：安装后触发 `ZeroDivisionError` 并 `logger.exception("boom")`。
- 断言：控制台富栈显示，含 `locals`（如 `result` 未赋值而被展示为空/未定义等可读信息）。

10) Traceback 幂等性
- 目的：重复安装不产生重复 hook。
- 步骤：`install_traceback()` 两次，制造一次异常。
- 断言：栈渲染仅出现一次装饰效果（人工/基于输出片段去重检查）。

11) CLI 基本路径
- 目的：CLI 在默认参数下输出各级日志并 0 退出。
- 步骤：`python -m Kobe.SharedUtility.RichLogger.cli`。
- 断言：stdout 含 debug/info/warn/error；进程退出码 0。

12) CLI 自定义等级/颜色/主题
- 目的：参数接入 Console/Logging。
- 步骤：`--level DEBUG --no-color --theme high_contrast`。
- 断言：DEBUG 可见；ANSI 关闭；样式为高对比主题。

13) CLI 异常路径
- 目的：`--boom` 触发示例异常并由 Rich Traceback 渲染。
- 步骤：`python -m Kobe.SharedUtility.RichLogger.cli --boom`。
- 断言：非 0 退出；控制台出现 Rich traceback。

14) 并发：init_console 原子性
- 目的：并发 10/50 线程同时调用 `init_console` 仅创建一个实例。
- 步骤：使用 `ThreadPoolExecutor` 并发调用，收集返回 id。
- 断言：所有返回对象 id 相同；无异常。

15) 并发：日志风暴
- 目的：高负载下 handler 不增长、无异常、吞吐稳定。
- 步骤：多线程各打印 1e4 条 INFO/DEBUG。
- 断言：`RichHandler` 个数仍为 1；过程无未处理异常；耗时在可接受阈值（基线可由 CI 机器实测记录）。

16) 预期效果：终端与文件的“两轨”一致性
- 目的：控制台 message-only；文件含 4 字段。
- 步骤：同一条日志同时输出到终端与文件。
- 断言：终端仅见消息体；文件包含时间/等级/记录器/消息四段并按竖线分隔。

17) 环境变量优先级回归
- 目的：组合测试 `LOG_LEVEL`、`RICH_LOG_LEVEL` 与函数参数的优先级。
- 步骤：矩阵覆盖（空/仅 LOG_LEVEL/仅 RICH_LOG_LEVEL/两者冲突/显式参数）。
- 断言：最终等级符合“参数 > LOG_LEVEL > RICH_LOG_LEVEL > 默认”。

18) 兼容性：非 TTY/CI 环境
- 目的：在非 TTY（如重定向到文件/CI）下输出无 ANSI；`no_color` 强制关闭。
- 步骤：PowerShell 用 `| Out-File` 重定向，或在 CI 设 `TERM`/`CI` 变量。
- 断言：输出不包含 `\x1b[` ANSI 序列。

## 运行与操作手册（PowerShell）
- 准备虚拟环境（如尚未创建）：
  - `py -3 -m venv D:\AI_Projects\Kobe\.venv`
  - `D:\AI_Projects\Kobe\.venv\Scripts\Activate.ps1`
  - `pip install -r D:\AI_Projects\Kobe\Requirements.txt`
- 运行单元测试（当前内置 unittest 用例位于 `SharedUtility/RichLogger/tests/`）：
  - 从 `D:\AI_Projects` 作为工作目录运行（确保可解析 `Kobe.*` 导入）：
  - `python -m unittest discover -s Kobe/SharedUtility/RichLogger/tests -p "test_*.py"`
- 体验 CLI：
  - `python -m Kobe.SharedUtility.RichLogger.cli --level DEBUG`
  - `python -m Kobe.SharedUtility.RichLogger.cli --no-color --theme high_contrast`
  - `python -m Kobe.SharedUtility.RichLogger.cli --boom`（演示异常栈）
- 运行压力测试（示例骨架，建议存为 `Kobe/SimulationTest/stress_richlogger.py`）：
  - 创建 Console/Logging 后多线程打印；统计耗时与错误数；并发度与总量可通过环境变量注入。

## 验收对照（用于评审打勾）
- 对齐 BackendConstitution：
  - [ ] 仅使用 `logging`（无 `print` 日志）；富 traceback 已安装；Python 3.10；虚拟环境一致。
  - [ ] 导入期初始化（`Kobe.main` 已调用），业务侧统一 `logging.getLogger(__name__)`。
- 对齐 SimulationTestingConstitution：
  - [ ] 本地可复现；明确 Arrange/Act/Assert；不依赖外部服务；可在 CI 以非 TTY 模式执行。
- 对齐 BestPractise：
  - [ ] 终端输出用 `rich`；文件输出结构化；CLI 演示路径可用。
- 质量基线：
  - [ ] Console/Logging/Traceback 幂等；
  - [ ] 单一 `RichHandler`；
  - [ ] 主题与无色模式生效；
  - [ ] 大量日志与并发稳定；
  - [ ] 文件日志可读且 UTF-8。

## 风险与改进建议
- `logfile` 不可写时目前未显式记录失败原因，建议在 `init_logging` 捕获并输出一次性警告。
- 主题名非法时回退默认，建议在首次初始化时打印一次提醒（debug 级别）。
- 可考虑增加 `pytest` 下的 `caplog` 基于模式断言，以提升断言粒度与可维护性。

## 参考链接（官方文档与项目资料）
- Rich Console / Logging / Traceback（官方）：
  - https://rich.readthedocs.io/en/stable/console.html
  - https://rich.readthedocs.io/en/stable/logging.html
  - https://rich.readthedocs.io/en/stable/traceback.html
- Python logging（官方）：
  - https://docs.python.org/3/library/logging.html
- 本项目资料：
  - `Kobe/index.yaml` 及各子模块 `index.yaml`
  - `Kobe/SharedUtility/RichLogger/` 源码与 `README.md`
  - `D:/AI_Projects/CodexFeatured/Common/BackendConstitution.yaml`
  - `D:/AI_Projects/CodexFeatured/Common/SimulationTestingConstitution.yaml`
  - `D:/AI_Projects/CodexFeatured/Common/BestPractise.yaml`
  - `D:/AI_Projects/CodexFeatured/Common/CodebaseStructure.yaml`

