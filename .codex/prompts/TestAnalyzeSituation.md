workflow:
  name: TestSituationCoverageDiscovery
  description: 执行开发任务列表 Tasks.md 
  language: zh-CN


用户输入作为被测试模块命令参数传入——在继续执行提示词之前你必须检查其不为空。
用户输入：$ARGUMENTS

objectives:
  - 理解项目开发意图和使用方式
  - 明确任务依赖、验收标准
  - 调研该模块可被测试的各类场景 (可能但不限于: 压力测试, 功能测试, 故意制造错误测试, 设计意图使用方式测试, 交互测试, 数据库读写结果验证, 预期效果验证, 功能最佳实践)

repo_root: `D:/AI_Projects`

params:
  OUTPUT_DIR_PATH: 'D:/AI_Projects/Kobe/SimulationTest'
  module_name: '$ARGUMENTS'
  file_name: '${module_name}.md'

io:
  codebase_map_script: 'CodexFeatured/Scripts/CodebaseStructure.py'
  codebase_structure_doc: 'CodexFeatured/Common/CodebaseStructure.yaml'
  dev_constitution: 'CodexFeatured/Common/BackendConstitution.yaml'
  best_practices: 'CodexFeatured/Common/BestPractise.yaml'
  simulation_testing_constitution: 'CodexFeatured/Common/SimulationTestingConstitution.yaml'
  kobe_root_index: 'Kobe/index.yaml'

steps:
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
    name: 写入目标目录
    path: ${OUTPUT_DIR_PATH}
    filename: ${file_name}
    acceptance:
      - 符合 io.dev_constitution 与官方最佳实践
      - 符合 io.code_comment_standard 的注释要求
      - 符合 io.dev_constitution 的技术栈约束
      - 符合 io.simulation_testing_constitution 的规范
