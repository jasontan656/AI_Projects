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
      - 在 ${OUTPUT_DIR_PATH} 中枚举所有*.md文件（不含子目录）
      - 找出唯一 target_file_name 格式匹配文件名

  - id: load_policies
    name: 规范加载与调研
    actions:
      - 读取 io.simulation_testing_constitution 并严格遵守
      - 读取 io.kobe_root_index 按 relation 自顶向下遍历直至所有 index.yaml 读取完毕  # 目的：了解项目模块依赖关系和开发意图
      - 读取 io.test_excute 加载测试计划
  
  - id: execute_pipeline
    name: 完成测试计划要求
    actions:
        - 依据任务列表完成开发测试
        - 按 acceptance 验证结果

    acceptance:
      - 符合 io.simulation_testing_constitution 的规范要求
      
