workflow:
  name: DevPipelineGeneration
  description: 将读取到的DemandDescription.md解析拆解并攥写为最小可执行开发步骤的YAML格式指令集并写入Task.md
  language: zh-CN

params:
  OUTPUT_DIR_PATH: "D:/AI_Projects/CodexFeatured/DevPlans"
  COUNT_3D: "{{RUNTIME_RESOLVE}}"           # 从目标需求文档内容解析；不直接参与路径拼接
  INTENT_TITLE_2_4: "{{RUNTIME_RESOLVE}}"   # 同上
  DEMAND_FILENAME: "DemandDescription.md"
  TASKS_FILENAME: "Tasks.md"
  demand_path_template: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${DEMAND_FILENAME}"
  tasks_path_template: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${TASKS_FILENAME}"


io:
  
  codebase_map_script: "CodexFeatured/Scripts/CodebaseStructure.py"
  codebase_structure_doc: "CodexFeatured/Common/CodebaseStructure.yaml"
  dev_constitution: "CodexFeatured/Common/BackendConstitution.yaml"
  code_comment_standard: "CodexFeatured/Common/CodeCommentStandard.yaml"
  best_practices: "CodexFeatured/Common/BestPractise.yaml"
  kobe_root_index: "Kobe/index.yaml" 


assumptions:
  - 用户提供的提示词文档 DemandDescription.md 的核心目的恒为“从需求文档生成工程化任务清单”。
  - 输出语言必须为中文，结构清晰且可执行，可直接指导开发实施。

objectives:
  - 将读取到的需求文档 DemandDescription.md内容拆解为最小可执行开发步骤的YAML格式指令集。
  - 明确任务依赖、验收标准、注释规范引用与交付产出。
  - 并将生成文件存储至文中指定的位置。



steps:

  - id: check_docs
    name: 文档状态检查与目标定位
    actions:
      - 运行 io.codebase_map_script 来更新io.codebase_structure_doc
      - 然后读取 io.codebase_structure_doc 项目文件架构
      - 在 ${OUTPUT_DIR_PATH} 下查找包含 ${DEMAND_FILENAME} 的所有子目录，按文件名数字序列倒序遍历
      - 选择目标需求文档（优先：用户最近一次创建/修改的 ${DEMAND_FILENAME}）
      - 读取目标需求文档 target_path，并解析首部“标识信息”提取 COUNT_3D 与 INTENT_TITLE_2_4
      - 设置：
        * target_dir = dirname(target_path)
        * target_tasks_path = "${target_dir}/${TASKS_FILENAME}"
      - 读取 io.kobe_root_index 并自顶向下遍历所有 index.yaml
        - 构建项目能力图谱：已实现模块、可复用组件、基础设施现状
        - 识别需求文档中可能关联的现有模块
      - 从需求文档中提取技术关键点：
        - 识别核心技术
        - 提取性能指标
        - 识别数据流特征
        - 识别核心业务流程
        - 识别主要交付物

  - id: load_policies
    name: 规范加载与技术选型调研
    actions:
      - 读取 io.dev_constitution 并严格遵守
      - 读取 io.code_comment_standard 并抽取关键要求
      - 读取 io.best_practices 并浏览其中官方链接
      - 基于 check_docs 识别的技术关键点进行针对性调研：
        - 对于每个技术挑战点，确定是使用现有模块还是引入新依赖
        - 若需新依赖，调研官方文档验证：
          * 与项目约束的兼容性（异步I/O、Python版本、类型注解）
          * 社区成熟度与维护状态（GitHub stars、最近更新、issue响应）
          * 官方最佳实践与推荐用法
        - 调研社区最佳实践（GitHub/StackOverflow/开发者博客）：
          * 针对需求中的特定场景（如SQL解析、大模型批处理、数据脱敏）
          * 寻找生产级实现参考与常见陷阱
      - 生成技术决策清单：
        - 复用模块清单：列出可直接使用的现有模块及其调用方式
        - 新增依赖清单：库名、版本、选型理由（必须基于官方文档验证）
        - 架构决策：关键技术点的实现策略（如：同步vs异步、批处理vs流式）


  - id: write_output
    name: 在读取需求文档的目录生成任务清单
    path: "{check_docs.target_dir}"
    actions:
      - 基于需求文档、技术决策清单和复用模块清单，拆解为最小可执行步骤
      - 任务清单结构要求：
        - 首要原则，每个 sub_step 必须是人类开发者可手动执行的原子操作
        - 必须包含技术决策说明章节（列出关键技术选型及理由）
        - 对于可复用模块，任务步骤中明确标注模块路径与调用方式
        - 对于新增依赖，在独立步骤中列出 requirements.txt 更新清单
        - 每个 Step 必须包含明确的验收标准（可测试/可验证）
      - 写入"{check_docs.target_tasks_path}"完整最小可执行开发步骤的YAML格式指令集
    acceptance:
      - "目标目录必须等于 {check_docs.target_dir}（DemandDescription.md 所在目录）"
      - "禁止创建新目录与新编号；若目录不存在应报错终止"
      - "输出为合法 UTF-8 YAML（无 BOM）"
      - "内容符合 io.dev_constitution 规范、与官方最佳实践"
      - "须包含需求文档解析得到的功能、结构、接口与 DoD"
      - "必须包含技术决策说明章节，列出关键技术选型、复用模块、新增依赖"
      - "对于性能要求明确的需求，任务步骤中必须包含性能验证步骤"
      - "复用现有模块时，必须标注模块路径与使用示例（从 index.yaml 获取）"
    示例输出的文本结构（重要：必须严格参考此格式与粒度，这是正确的输出标准）:
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

  - id: self_check
    name: 规范对齐验证
    actions:
      - 读取当前流程的所有约束源（io 声明的规范文件）
      - 读取上一步输出的文件
      - 验证业务目标覆盖度：
        - 需求文档的核心功能点是否全部对应到任务步骤中
        - 需求文档声明的交付物是否在任务步骤中有明确的生成步骤
        - 任务步骤是否遵循需求的业务流程顺序
      - 验证技术选型对齐：
        - 所有新增依赖是否符合项目约束（异步兼容、类型注解）
        - 复用模块引用是否正确（路径存在、接口匹配）
        - 技术方案是否基于官方最佳实践
      - 对比发现偏差（语气/路径/约束/覆盖）
      - 发现偏差立即修正并重写文件
      - 验证修正结果，最多3轮
    acceptance: 生成物与约束源完全对齐，且任务步骤完整覆盖需求文档的所有核心功能点与交付物
 
