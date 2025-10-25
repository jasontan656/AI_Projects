workflow:
  name: TestPieplineExcutePlanGenerating
  description: 将测试计划开发文档拆解为最小可执行开发步骤的YAML格式指令集
  language: zh-CN


objectives:
  - 读取并解析测试计划开发文档内容
  - 编写包含服务验证、HTTP调用、状态查询、结果断言的完整测试步骤的YAML指令集
  - 在生成文件内声明 "严格禁止在 SimulationTest 外部目录创建任何测试相关文件"
  - 在生成文件内声明 "所有测试脚本、结果、日志必须在 ${foldername} 子目录的规范结构内"
repo_root: 'D:/AI_Projects'

params:
  OUTPUT_DIR_PATH: 'D:/AI_Projects/Kobe/SimulationTest'
  file_name: '${unique_filename}'
  target_file_name: '${unique_filename}_testplan.md'
  foldername: '${unique_filename}_testplan'

io:
  codebase_map_script: 'CodexFeatured/Scripts/CodebaseStructure.py'
  codebase_structure_doc: 'CodexFeatured/Common/CodebaseStructure.yaml'
  dev_constitution: 'CodexFeatured/Common/BackendConstitution.yaml'
  best_practices: 'CodexFeatured/Common/BestPractise.yaml'
  simulation_testing_constitution: 'CodexFeatured/Common/SimulationTestingConstitution.yaml'
  kobe_root_index: 'Kobe/index.yaml'

steps:
  - id: detect_output_filename
    name: 解析输出文件名
    actions:
      - 在 ${OUTPUT_DIR_PATH} 中枚举所有*.md文件（不含子目录）
      - 若文件数量不等于 1 则报错并终止
      - 将唯一文件的文件名保存为变量 unique_filename

  - id: check_docs
    name: 加载文件
    actions:
      - 运行 io.codebase_map_script
      - 读取 io.codebase_structure_doc  # 目的：了解项目文件结构
      - 读取 io.kobe_root_index
      - 按 relation 自顶向下遍历直至所有 index.yaml 读取完毕  # 目的：了解项目模块依赖关系和开发意图

  - id: load_policies
    name: 加载规范并调研
    actions:
      - 读取 io.dev_constitution 并严格遵守
      - 读取 io.simulation_testing_constitution 并严格遵守
      - 读取 io.best_practices 并浏览其中任务相关官方链接
      - 调研社区最佳实践（GitHub/StackOverflow/开发者博客）
    purpose: 加载开发规范, 学习官方推荐实现, 学习当前任务最佳实践

  - id: codebase_scan
    name: 目标代码库扫描
    actions:
      - 扫描: $ARGUMENTS 中所有代码文件
      - 扫描: D:/AI_Projects/CodexFeatured/DevPlans 了解开发历史

  - id: write_output
    name: 写入目标文件
    path: ${OUTPUT_DIR_PATH}
    target: ${target_file_name} 
    actions:
      - 写入完整原子级可执行开发测试步骤的YAML格式指令集
    acceptance:
      - "任务文件路径对齐"
      - "输出为合法 UTF-8 YAML（无 BOM）"
      - "内容符合 io.dev_constitution io.simulation_testing_constitution 规范、与官方最佳实践一致"
      - "须包含需求文档解析得到的功能、结构、接口与 DoD"
      - 可直接接入 Codex CLI / Cursor AGENTS / Cognitive Workflow
      - "所有文件创建路径必须以 D:/AI_Projects/Kobe/SimulationTest/${foldername}/ 开头"
      - "禁止在 SimulationTest 外部创建任何测试文件"
      - "子目录结构必须包含: test_cases/, results/, logs/"
    示例输出:
      Step 1:
      title: 初始化仿真测试工作区
      sub_steps:
       - 创建目录 D:/AI_Projects/Kobe/SimulationTest/${foldername}
       - 创建目录 D:/AI_Projects/Kobe/SimulationTest/${foldername}/test_cases
       - 创建目录 D:/AI_Projects/Kobe/SimulationTest/${foldername}/results
       - 创建目录 D:/AI_Projects/Kobe/SimulationTest/${foldername}/logs
       - 写入 README.md 到工作区说明测试目的

      Step 1.5:
      title: 生成测试依赖清单
      sub_steps:
       - 新建 D:/AI_Projects/Kobe/SimulationTest/${foldername}/requirements.txt
       - 包含: pytest, pytest-asyncio, pytest-timeout, pytest-json-report, pytest-html
       - 包含: requests, redis, pymongo, psutil, click, structlog, pyyaml
       - 包含: timeout-decorator, pytest-benchmark（按需）

      Step 2:
      title: 编写基础测试用例
      sub_steps:
       - 新建 test_basic.py: 禁止 import 被测模块，使用 requests 调用 HTTP 端点
       - 新建 test_integration.py: 使用 redis/pymongo 客户端验证中间件状态变化
       - 新建 test_stress.py: 并发调用 HTTP 端点并统计响应时间
      Step 3:
      title: 实现测试执行器
      sub_steps:
       - 新建文件 D:/AI_Projects/Kobe/SimulationTest/${foldername}/run_local_simulation_tests.py
       - 使用 pytest 作为测试运行器，支持 --scenario（pytest -k）、--all（pytest）
       - 使用 click 实现 CLI 参数解析
       - 使用 readchar + threading.Timer 实现30秒倒计时询问
       - 使用 pytest-json-report 输出到 results/report.json
       - 使用 pytest-html 输出到 results/report.html

      Step 4:
      title: 配置日志记录
      sub_steps:
       - 配置 debug.log 输出到 D:/AI_Projects/Kobe/SimulationTest/${foldername}/logs/debug.log
       - 配置 error.log 输出到 D:/AI_Projects/Kobe/SimulationTest/${foldername}/logs/error.log
       - 确保所有日志为 UTF-8 编码

  - id: self_check
    name: 规范对齐验证
    actions:
      - 读取当前流程的所有约束源（io 声明的规范文件）
      - 读取上一步输出的文件
      - 对比发现偏差（语气/路径/约束/覆盖）
      - 发现偏差立即修正并重写文件
      - 验证修正结果，最多3轮
    acceptance: 生成物与约束源完全对齐