workflow:
  name: TestSituationCoverageDiscovery
  description: 测试计划前置输入文档生成（为 TestPipelineGeneration 提供可执行依据）
  language: zh-CN


用户输入作为被测试模块命令参数传入——在继续执行提示词之前你必须检查其不为空。
用户输入：$ARGUMENTS

objectives:
  - 理解项目开发意图和使用方式
  - 明确任务依赖、验收标准
  - 调研该模块的 HTTP 端点列表、依赖服务（RabbitMQ/Redis/MongoDB）及其管理接口
  - 调研真实功能验证场景：
      * 从官方入口调用（HTTP端点/CLI命令/消息队列），禁止直接import内部函数
      * 验证真实服务状态变化（数据库记录/队列消息/缓存键的实际增删改查）
      * 逐步加压测试（小数据量→大数据量、单进程→多进程、正常并发→高并发）
      * 异常恢复测试（中断重试、超时处理、资源不足场景）
  - 调研服务状态查询方法（RabbitMQ Management API、redis-cli、pymongo）
  - 调研适用的测试工具栈：pytest生态、HTTP客户端库、超时控制库、报告生成库

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
    purpose: 加载开发规范, 学习官方推荐实现, 学习测试工具最佳实践（pytest/requests/structlog）

  - id: codebase_scan
    name: 目标代码库扫描
    actions:
      - 扫描: $ARGUMENTS 中所有代码文件
      - 扫描: D:/AI_Projects/CodexFeatured/DevPlans 了解开发历史

  - id: write_output
    name: 写入目标目录
    path: ${OUTPUT_DIR_PATH}
    filename: ${file_name}
    format: "可执行测试计划输入（非建议报告）"
    tone: "指令性（必须测试X）而非描述性（可选配置X）"
    coverage_rule: "列出所有配置分支的测试要求（如：测试 Redis 开启场景 + Redis 关闭场景）"
    acceptance:
      - 符合 io.dev_constitution 与官方最佳实践
      - 符合 io.simulation_testing_constitution 的规范
      - **所有测试场景必须从模块官方入口发起，禁止直接导入内部函数**
      - **所有测试必须验证真实服务状态变化（不使用mock）**
      - **必须包含逐步加压的测试场景设计（数据量递增、并发递增）**
      - 所有可配置项必须明确测试覆盖方案（不能只说"可选"）
      - 工具栈为指定项（不能用"建议"一词）

  - id: self_check
    name: 规范对齐验证
    actions:
      - 读取当前流程的所有约束源（io 声明的规范文件）
      - 读取上一步输出的文件
      - 对比发现偏差（语气/路径/约束/覆盖）
      - 发现偏差立即修正并重写文件
      - 验证修正结果，最多3轮
    acceptance: 生成物与约束源完全对齐