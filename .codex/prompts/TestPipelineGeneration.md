workflow:
  name: TestPieplineExcutePlanGenerating
  description: 将测试计划开发文档拆解为最小可执行开发步骤的YAML格式指令集
  language: zh-CN


objectives:
  - 将测试计划开发文档内容功能需求拆解为最小可执行开发步骤的YAML格式指令集
  - 确保测试计划开发内容都在D:/AI_Projects/Kobe/SimulationTest/${foldername}中创建保存

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
      - 写入完整最小可执行开发步骤的YAML格式指令集
    acceptance:
      - "任务文件路径对齐"
      - "输出为合法 UTF-8 YAML（无 BOM）"
      - "内容符合 io.dev_constitution io.simulation_testing_constitution 规范、与官方最佳实践一致"
      - "须包含需求文档解析得到的功能、结构、接口与 DoD"
      - 可直接接入 Codex CLI / Cursor AGENTS / Cognitive Workflow
    示例输出:
        Step 1:
          title: 初始化用户模块目录结构
          sub_steps:
           - 创建 backend/modules/auth 目录
           - 创建 frontend/components/LoginForm.vue 文件
           - 创建 shared/utils/token.js 工具模块

        Step 2:
          title: 实现邮箱验证码注册逻辑
          sub_steps:
           - 在 backend/modules/auth/service.py 中定义 send_verification_code(email)
           - 实现验证码生成逻辑，使用 random + redis 存储
           - 在 controller 中添加 POST /auth/send-code 接口

        Step 3:
          title: 实现密码登录接口
          sub_steps:
           - 定义 login_user(email, password) 方法
           - 验证用户身份，返回 JWT token
           - 添加 POST /auth/login 接口并接入验证逻辑

        Step 4:
          title: 构建登录态验证中间件
          sub_steps:
           - 在 shared/middleware/token_auth.py 中定义 auth_required 装饰器
           - 在需要保护的接口上添加装饰器
           - 在错误情况下统一返回 401 Unauthorized

        Step 5:
          title: 构建前端登录交互逻辑
          sub_steps:
           - 在 LoginForm.vue 中添加 email、password 输入框
           - 添加验证码输入框与发送按钮
           - 使用 axios 向后端发起登录请求
           - 登录成功后将 token 存入 localStorage
           - 登录失败展示错误信息