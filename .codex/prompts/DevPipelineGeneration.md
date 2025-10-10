workflow:
  name: DevPipelineGeneration
  description: 将输入内容拆解为最小可执行开发步骤的YAML格式指令集
  language: zh-CN

params:
  OUTPUT_DIR_PATH: "D:/AI_Projects/CodexFeatured/DevPlans"
  COUNT_3D: "001"  # 动态三位编号（见 naming_rules.count_3d.generation）
  INTENT_TITLE_2_4: "InitialSetup"  # 从任务意图动态生成（见 naming_rules.intent_title_2_4.generation）
  SUBDIR_NAME: "${COUNT_3D}_${INTENT_TITLE_2_4}"
  DEMAND_FILENAME: "DemandDescription.md"
  TASKS_FILENAME: "Tasks.md"
  demand_path_template: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${DEMAND_FILENAME}"
  tasks_path_template: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${TASKS_FILENAME}"


assumptions:
  - 用户提示词的核心目的恒为“从需求文档生成工程化任务清单”。
  - 输出语言必须为中文，结构清晰且可执行，可直接指导开发实施。

objectives:
  - 将需求文档内容拆解为最小可执行开发步骤的YAML格式指令集
  - 明确任务依赖、验收标准、注释规范引用与交付产出。
  - 用于将开发说明文档转化为最小可执行的 YAML 格式开发任务清单
  - 可直接接入 Codex CLI / Cursor AGENTS / Cognitive Workflow

input_behavior: |
  - 输入可能是自然语言描述的开发构想、项目说明、README、注释、模块设计文档等
  - 必须自动推断任务顺序与依赖关系
  - 输入未定义的部分必须跳过，不得凭空补充
  

response_behavior: |
  - 直接输出YAML结构，无任何解释说明
  - 不添加提示文字，不加“以下是步骤：”或“这是结果”
  - 若某一步骤需要其他先决条件，请在sub_step中标明依赖
  - 全文只允许存在 Step + sub_steps 结构，不允许自由段落

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

io:
  
  codebase_map_script: "CodexFeatured/Scripts/CodebaseStructure.py"
  codebase_structure_doc: "CodexFeatured/Common/CodebaseStructure.yaml"
  dev_constitution: "CodexFeatured/Common/BackendConstitution.yaml"
  code_comment_standard: "CodexFeatured/Common/CodeCommentStandard.yaml"
  best_practices: "CodexFeatured/Common/BestPractise.yaml"


steps:

  - id: check_docs
    name: 文档状态检查与目标定位
    actions:
      - 运行 io.codebase_map_script
      - 读取 io.codebase_structure_doc
      - 扫描 ${OUTPUT_DIR_PATH} 按 ^\d{3}.+ 找最大编号目录
        - 拼接路径: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}"
      - 读取需求文档并验证存在性
        - 需求文档: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${DEMAND_FILENAME}"
 
    purpose: 精确定位并获取需求文档内容。

  - id: load_policies
    name: 规范加载与调研
    actions:
      - 读取 io.dev_constitution 并严格遵守
      - 读取 io.code_comment_standard 并抽取关键要求
      - 读取 io.best_practices 并浏览其中官方链接
      - 调研社区最佳实践（GitHub/StackOverflow/开发者博客）
    purpose: 加载规范，最小可执行开发步骤的YAML格式指令集须符合要求

  - id: write_output
    name: 当前最大编号目录生成 "${TASKS_FILENAME}"
    actions:
      - 写入完整最小可执行开发步骤的YAML格式指令集
    acceptance:
      - "任务文件路径与 params.tasks_path_template 对齐"
      - "输出为合法 UTF-8 YAML（无 BOM）"
      - "内容符合 io.dev_constitution 规范、与官方最佳实践一致"
      - "须包含需求文档解析得到的功能、结构、接口与 DoD"

 
 
