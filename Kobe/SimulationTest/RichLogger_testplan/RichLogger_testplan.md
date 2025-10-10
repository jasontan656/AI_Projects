---
meta:
  workflow: TestPieplineExcutePlanGenerating
  language: zh-CN
  generated_at: "2025-10-10T00:00:00Z"
  repo_root: "D:/AI_Projects/Kobe"
  source_doc: "Kobe/SimulationTest/RichLogger.md"
  objectives:
    - 将测试计划开发文档内容拆解为最小可执行开发步骤
    - 所有仿真测试产物位于 D:/AI_Projects/Kobe/SimulationTest/${foldername}

context:
  module_path: "Kobe/SharedUtility/RichLogger"
  tests_root: "Kobe/SharedUtility/RichLogger/tests"
  cli_entry: "Kobe/SharedUtility/RichLogger/cli.py"
  app_entry: "Kobe/main.py"
  constitution:
    dev: "D:/AI_Projects/CodexFeatured/Common/BackendConstitution.yaml"
    simulation: "D:/AI_Projects/CodexFeatured/Common/SimulationTestingConstitution.yaml"
    best_practices: "D:/AI_Projects/CodexFeatured/Common/BestPractise.yaml"
  notes:
    - main.py 已在导入时调用 init_logging 和 install_traceback
    - 当前已有基础单测 tests/test_basic.py 可作为回归基线

requirements:
  功能:
    - Console: no_color/theme/width 可配置；支持从 styles.toml 合并主题；幂等初始化与线程安全
    - Logging: 仅装配一个 RichHandler；message-only 控制台；可选 UTF-8 文件 handler（含时间/级别/记录器/消息）
    - Traceback: rich.traceback.install 绑定统一 Console；支持 show_locals/width/theme
    - CLI: 暴露 --level/--no-color/--theme/--boom 开关，演示异常与不同配色
    - 兼容性: 非 TTY/重定向场景禁用 ANSI；环境变量 LOG_LEVEL 与 RICH_LOG_LEVEL 生效且有优先级
  结构:
    - 模块目录: Kobe/SharedUtility/RichLogger/
    - 配置文件: Kobe/SharedUtility/RichLogger/styles.toml（可选）
    - 单测目录: Kobe/SharedUtility/RichLogger/tests/
    - 仿真测试工作区: Kobe/SimulationTest/${foldername}/(test_cases|results|logs)
  接口:
    - init_console(options: dict | None) -> Console
    - get_console() -> Console
    - init_logging(level: str | None, markup: bool = True, logfile: str | None = None) -> None
    - install_traceback(show_locals: bool = False, width: int | None = None, theme: str | None = None) -> None
    - CLI: python -m Kobe.SharedUtility.RichLogger.cli [--level LVL] [--no-color] [--theme THEME] [--boom]
  DoD:
    - 禁止使用 print 输出日志；统一 logging 与 RichHandler（单一实例）
    - Kobe/main.py 导入即完成 init_logging 与 install_traceback（已具备）
    - Console 初始化幂等、线程安全；no_color/theme/width 与 env 合并生效
    - 日志文件 UTF-8 编码，字段顺序为: 时间|级别|记录器|消息
    - 非 TTY/重定向输出不含 ANSI 转义；CI 可稳定运行
    - 单测覆盖功能/边界/并发/非 TTY；RunAll 仿真流程可一键执行并生成 artifacts

plan:
  name: "RichLogger 仿真测试最小可执行开发步骤"
  foldername: "RichLogger_testplan.md"
  steps:
    - id: step_01_prepare_workspace
      title: 初始化仿真测试工作区
      sub_steps:
        - 创建目录 D:/AI_Projects/Kobe/SimulationTest/RichLogger_testplan
        - 创建目录 D:/AI_Projects/Kobe/SimulationTest/RichLogger_testplan/test_cases
        - 创建目录 D:/AI_Projects/Kobe/SimulationTest/RichLogger_testplan/results
        - 创建目录 D:/AI_Projects/Kobe/SimulationTest/RichLogger_testplan/logs
        - 写入占位 README 到上述四级目录说明用途

    - id: step_02_env_bootstrap
      title: 校验虚拟环境与依赖
      sub_steps:
        - 若不存在 D:/AI_Projects/Kobe/.venv 则执行: py -3 -m venv D:/AI_Projects/Kobe/.venv
        - 激活 venv 并安装依赖: pip install -r D:/AI_Projects/Kobe/Requirements.txt
        - 校验命令可用: python -c "import rich,fastapi"

    - id: step_03_extend_unit_tests_console
      title: 覆盖 Console 配置/环境变量/幂等
      sub_steps:
        - 新建文件 Kobe/SharedUtility/RichLogger/tests/test_console_options.py
        - 覆盖要点: no_color/theme/width 与 env(RICH_NO_COLOR/RICH_THEME/RICH_WIDTH) 合并
        - 验证 styles.toml 覆盖主题；缺失文件时 graceful fallback
        - 验证并发下 init_console 仅创建一个实例（10/50 线程）

    - id: step_04_extend_unit_tests_logging
      title: 覆盖 Logging 单一 RichHandler 与文件输出
      sub_steps:
        - 新建文件 Kobe/SharedUtility/RichLogger/tests/test_logging_handlers.py
        - 断言根 logger 仅含 1 个 RichHandler；重复 init_logging 不新增
        - 断言 LOG_LEVEL 与 RICH_LOG_LEVEL 优先级: 参数 > LOG_LEVEL > RICH_LOG_LEVEL > 默认
        - 打开文件 handler: tempfile 路径；断言 UTF-8 编码与“时间|级别|记录器|消息”格式

    - id: step_05_extend_unit_tests_traceback
      title: 覆盖 Traceback 安装与参数
      sub_steps:
        - 新建文件 Kobe/SharedUtility/RichLogger/tests/test_traceback_setup.py
        - 断言 install_traceback 使用统一 Console；参数 show_locals/width/theme 生效

    - id: step_06_cli_scenarios
      title: CLI 行为验证（含异常路径）
      sub_steps:
        - 新建文件 Kobe/SharedUtility/RichLogger/tests/test_cli.py
        - 调用 python -m Kobe.SharedUtility.RichLogger.cli --level DEBUG 捕获退出码 0
        - 传入 --no-color --theme high_contrast；断言输出不含 ANSI 码
        - 传入 --boom 断言抛出 RuntimeError 并包含富文本 traceback

    - id: step_07_non_tty_behavior
      title: 非 TTY/重定向时关闭 ANSI
      sub_steps:
        - 新建文件 Kobe/SharedUtility/RichLogger/tests/test_notty.py
        - 使用 subprocess 将 CLI 输出管道重定向到文件；断言不包含 "/x1b[" 序列

    - id: step_08_stress_script
      title: 压测/并发稳定性脚本
      sub_steps:
        - 新建文件 Kobe/SimulationTest/stress_richlogger.py
        - 内容: 10/50 线程循环 init_console/init_logging 与日志写入，统计耗时与错误
        - 输出: D:/AI_Projects/Kobe/SimulationTest/RichLogger_testplan.md/results/performance_report.json

    - id: step_09_runall_runner
      title: 统一 RunAll 执行器（符合 SimulationTestingConstitution）
      sub_steps:
        - 新建文件 Kobe/SimulationTest/run_local_simulation_tests.py
        - 支持参数: --entry richlogger --scenario all/cli/console/logging/traceback --all
        - 执行顺序: 单测 -> CLI 示例 -> 压测；节点间 30s 超时自动继续
        - 产物: results/report.json, logs/debug.log, logs/error.log

    - id: step_10_wire_in_ci
      title: 本地/CI 统一入口
      sub_steps:
        - 在 README 增加运行说明与示例命令
        - 提供 PowerShell one-liner: python -m unittest discover -s Kobe/SharedUtility/RichLogger/tests -p "test_*.py"
        - 在 CI（如 GitHub Actions/Azure DevOps）中追加非 TTY 断言步骤

    - id: step_11_definition_of_done_checklist
      title: DoD 自检清单
      sub_steps:
        - 无 print 日志；仅 logging + RichHandler（1 个）
        - 非 TTY 无 ANSI；文件日志 UTF-8 且字段齐全
        - 所有新增单测通过（含并发/异常/CLI/非 TTY）
        - RunAll 成功生成 artifacts 并通过成功准则

execution:
  commands:
    - name: 运行单测
      run: python -m unittest discover -s Kobe/SharedUtility/RichLogger/tests -p "test_*.py"
    - name: 运行 CLI 示例
      run: python -m Kobe.SharedUtility.RichLogger.cli --level DEBUG
    - name: 运行 RunAll
      run: python Kobe/SimulationTest/run_local_simulation_tests.py --all

artifacts:
  base_directory: "D:/AI_Projects/Kobe/SimulationTest/RichLogger_testplan.md"
  files:
    - results/report.json
    - results/performance_report.json
    - logs/debug.log
    - logs/error.log

acceptance:
  - 任务文件路径对齐（本文件位于 Kobe/SimulationTest/RichLogger_testplan.md）
  - 输出为合法 UTF-8 YAML（无 BOM）
  - 内容符合 BackendConstitution 与 SimulationTestingConstitution
  - 覆盖需求文档解析得到的功能、结构、接口与 DoD
  - 可接入 Codex CLI / Cursor AGENTS / Cognitive Workflow 执行

---
