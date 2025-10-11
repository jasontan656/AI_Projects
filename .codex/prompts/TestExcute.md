workflow:
  name: TestExcute
  description: Execute the test plan.
  language: zh-CN

  objectives:
  - 执行测试计划并汇报结果

repo_root: 'D:/AI_Projects'

params:
  OUTPUT_DIR_PATH: 'D:/AI_Projects/Kobe/SimulationTest'
  file_name: '${unique_filename}'
  target_file_name: '${unique_filename}_testplan.md'

io:
  codebase_map_script: 'CodexFeatured/Scripts/CodebaseStructure.py'
  codebase_structure_doc: 'CodexFeatured/Common/CodebaseStructure.yaml'
  simulation_testing_constitution: 'CodexFeatured/Common/SimulationTestingConstitution.yaml'
  kobe_root_index: 'Kobe/index.yaml'
  test_excute: '.codex/prompts/TestExcute.md'

steps:
  - id: detect_testplan_filename
    name: 解析TestPlan文件名
    actions:
      - 在 ${OUTPUT_DIR_PATH} 匹配唯一 *_testplan.md 文件（不含子目录）

  - id: prepare_environment
    name: 准备测试环境
    actions:
      - 检测 ${OUTPUT_DIR_PATH}/${unique_filename}_testplan/requirements.txt 是否存在
      - 执行 pip install -r requirements.txt（使用虚拟环境或全局环境）
      - 验证关键库可导入：pytest, requests, redis, pymongo
    timeout: 120
    on_failure: 终止执行并报告依赖安装失败

  - id: load_policies
    name: 规范加载与调研
    actions:
      - 读取 io.simulation_testing_constitution 并严格遵守
      - 读取 io.kobe_root_index 按 relation 自顶向下遍历直至所有 index.yaml 读取完毕  # 目的：了解项目模块依赖关系和开发意图
      - 读取 io.test_excute 加载测试计划
  
  - id: execute_pipeline
    name: 完成测试计划要求
    actions:
      - 依据任务列表实现测试：使用 pytest 框架组织测试用例
      - 使用 requests/redis/pymongo 客户端，禁止 import 被测模块
      - 使用 pytest-timeout 实现10秒超时保护（@pytest.mark.timeout(10)）
      - 使用 pytest-json-report 和 pytest-html 生成报告
      - 使用 psutil 记录资源占用，使用 structlog 生成结构化日志
      - 按 acceptance 验证结果

    acceptance:
      - 符合 io.simulation_testing_constitution 的规范要求
      
  - id: self_check
    name: 规范对齐验证
    actions:
      - 读取当前流程的所有约束源（io 声明的规范文件）
      - 读取上一步输出的文件
      - 对比发现偏差（语气/路径/约束/覆盖）
      - 发现偏差立即修正并重写文件
      - 验证修正结果，最多3轮
    acceptance: 生成物与约束源完全对齐