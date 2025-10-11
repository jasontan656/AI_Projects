workflow:
  name: DevFuncDemandsWrite
  description: 自包含的自动化"开发需求文档撰写"工作流契约（YAML 精简版）,生成的的需求文档将被 DevPipelineGeneration 工作流消费，拆解为可执行开发步骤。
  language: zh-CN
  downstream_consumer: DevPipelineGeneration

  objectives:
  - 将用户提供的需求诉求攥写为结构化需求描述文档（富含功能域/功能范围/数据需求/性能要求/边界条件）
  - 脑补补足用户未明确的需求细节（基于场景分析的合理假设）
  - 需求文档须聚焦"要做什么"，不涉及"怎么做"的技术实现细节
  - 最终输出完整且无歧义的需求文档，供 DevPipelineGeneration 工作流消费并拆解为技术实现步骤

params:
  OUTPUT_DIR_PATH: "D:/AI_Projects/CodexFeatured/DevPlans"
  COUNT_3D: "{{RUNTIME_GENERATE}}"  # 动态三位编号（见 naming_rules.count_3d.generation）
  INTENT_TITLE_2_4: "{{RUNTIME_GENERATE}}"  # 【运行时强制生成】基于用户意图应用 naming_rules.intent_title_2_4.generation
  SUBDIR_NAME: "${COUNT_3D}_${INTENT_TITLE_2_4}"
  FILENAME: "DemandDescription.md"
  path_template: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${FILENAME}"

naming_rules:
  count_3d:
    description: "三位递增编号，从 001 开始；运行时动态计算。"
    examples:
      - "001"
      - "042"
      - "123"
    regex: "^\\d{3}$"
    generation:
      - "列出 ${OUTPUT_DIR_PATH} 下匹配 ^\\\d{3}_.+ 的子目录"
      - "提取前3位编号；取最大值+1；左侧零填充至3位"
      - "如不存在任何编号目录，则使用 001"
      - "若冲突则继续递增直到找到可用编号"
  intent_title_2_4:
    description: "用 2-4 个英文词，PascalCase（UpperCamelCase）；不含下划线/连字符/空格；禁止缩写与过短词。"
    examples:
      - "InitialSetup"
      - "UserOnboarding"
      - "PaymentGatewayIntegration"
    anti_examples:
      - "Init"
      - "user_setup"
      - "AI"
      - "Initial-Setup"
    regex: "^[A-Z][a-z]+(?:[A-Z][a-z]+){1,3}$"
    words_range: "2-4"
    min_word_len: 3
    generation:
      - "基于当前任务意图/标题提取 2-4 个核心英文词（名词/动词）"
      - "移除停用词（the, a, an, of, for, with, and, to, in）"
      - "同义词归一化，优先采用行业常用术语"
      - "转为 PascalCase，去分隔符拼接"
      - "每个词长度 ≥ 3，避免缩写/首字母词"
      - "如语义歧义，兜底使用 GeneralTask"


assumptions:
  - 用户提示词的核心目的恒为“撰写开发需求文档”。
  - 输出语言必须为中文，结构清晰、需求颗粒细度覆盖最小落地无死角。


research_policy:
  - 官方规范与实现方式须优先于其他来源。
  - 吸收社区共识（GitHub/StackOverflow/技术博客）以补充实践细节。

style:
  conventions:
    - 路径模板与引用统一使用正斜杠 "/"（示例/模板）；平台特定示例可使用本地分隔符
    - 数值范围统一使用 ASCII 连字符 "-"（如 2-4, 10-20），不使用短破折号/长破折号
    - 标题编号样式统一为 "## N. 标题"（如 "## 1. 项目背景与目标"）

  sections_template:
    - "1. 项目背景与目标"
    - "2. 业务场景分析"
    - "3. 功能需求描述"
    - "4. 数据需求描述"
    - "5. 性能与质量要求"
    - "6. 异常场景与边界条件"
    - "7. 安全与合规要求"
    - "8. 可观测性要求"
    - "9. 范围与非目标"
    - "10. 项目约束说明"
    - "11. 交付与验收标准"

io:
  user_prompt_path: "CodexFeatured/DevFuncDemandsWrite/PromptDraft.md"
  codebase_map_script: "D:/AI_Projects/CodexFeatured/Scripts/CodebaseStructure.py"
  codebase_structure_doc: "D:/AI_Projects/CodexFeatured/Common/CodebaseStructure.yaml"
  dev_constitution: "CodexFeatured/Common/BackendConstitution.yaml"
  best_practices: "CodexFeatured/Common/BestPractise.yaml"
  kobe_root_index: "Kobe/index.yaml"


  - id: load_prompt
    name: 加载用户提示词与生成命名
    actions:
      - 读取并理解 io.user_prompt_path
      - 提取用户意图的核心诉求与显式参数
      - 识别用户提供的上下文信息（URL/文件路径/数据源/目标系统等）
      - 应用 naming_rules.intent_title_2_4.generation 从核心诉求生成 INTENT_TITLE_2_4（2-4词PascalCase）
      - 应用 naming_rules.count_3d.generation 扫描 ${OUTPUT_DIR_PATH} 生成 COUNT_3D
    output: [用户核心诉求, 显式参数, 上下文信息, INTENT_TITLE_2_4, COUNT_3D]

  - id: check_docs
    name: 项目现状全面分析
    actions:
      - 运行 io.codebase_map_script
      - 读取 io.codebase_structure_doc
      - 读取 io.kobe_root_index
      - 按 relation 自顶向下遍历直至所有 index.yaml 读取完毕
      - 构建项目能力图谱：
        - 已实现功能模块：名称、职责边界、对外API、使用示例
        - 基础设施现状：数据库/缓存/消息队列/存储的配置与容量
        - 可复用组件：工具函数/中间件/装饰器的路径与用途
        - 项目架构模式：目录组织/模块依赖/命名规范
    output: [项目能力图谱, 技术栈约束清单, 基础设施清单, 可复用组件清单, 架构模式]

  - id: load_policies
    name: 规范与最佳实践加载
    actions:
      - 读取 io.dev_constitution 并提取所有强制约束与禁止项
      - 读取 io.best_practices 并索引官方文档链接
      - 构建规范决策树：每个技术选型点的约束条件与方案
    output: [规范决策树, 官方文档索引]

  - id: enhance_requirements
    name: 场景深度分析与需求补足
    actions:
      - 步骤1：自动识别功能域
        - 基于用户核心诉求，推断功能域类别（不限定具体类型）
        - 功能域识别须包含：主要功能类型、业务价值、典型应用场景
      
      - 步骤2：构建该功能域的需求维度清单
        - 从业务视角提取该功能域的标准需求维度（非技术实现维度）
        - 需求维度须覆盖（但不限于）：
          - 功能范围：业务边界、覆盖场景、包含/排除的功能点
          - 数据需求：数据来源、数据类型、数据结构、数据量级
          - 触发条件：业务触发时机、执行频率、触发方式
          - 性能要求：响应时间要求、吞吐量要求、并发量级、资源约束
          - 质量要求：准确性要求、完整性要求、一致性要求、可用性要求
          - 异常场景：失败定义、重试要求、降级策略、补偿机制
          - 安全要求：数据敏感性、访问控制要求、审计要求
          - 可观测性：需要记录的关键事件、需要监控的业务指标
      
      - 步骤3：主动获取分析所需的外部信息
        - 若用户提供URL：访问并分析目标系统的业务特征（内容类型/数据结构/业务规则）
        - 若用户提供API文档：解析业务接口规范（业务实体/数据格式/业务约束）
        - 若用户提供数据样本：分析业务数据特征（业务字段/数据关系/业务规则）
        - 若用户未提供明确目标：基于功能域的典型业务场景进行合理假设
      
      - 步骤4：为每个需求维度补足完整描述
        - 补足依据优先级：外部分析结果 > 功能域标准做法 > 项目历史需求 > 合理假设
        - 每个需求维度必须包含：
          1. 需求描述（清晰描述业务要求，使用业务语言而非技术术语）
          2. 补足理由（说明为何如此假设，基于什么业务逻辑或场景分析）
          3. 量化指标（若适用，给出具体的业务指标值，如"覆盖90%核心内容"、"支持1000条/秒"）
        - 需求描述须满足：
          - 业务导向：使用业务术语描述需求（如"获取文章内容"而非"爬取HTML"）
          - 需求层面：描述要达到的目标（如"响应时间<500ms"而非"使用异步框架"）
          - 可验收性：需求可转化为验收标准（如"支持100并发"而非"性能要好"）
          - 禁止技术实现：不涉及具体技术选型（如禁止"使用httpx"、"并发20"等实现细节）
      
      - 步骤5：基于项目约束过滤不可行需求
        - 读取项目技术栈约束（从 io.dev_constitution 提取禁止项与强制要求）
        - 若需求与项目约束冲突，调整需求描述或标注约束限制
        - 在需求描述中标注项目约束的影响（如"需使用异步I/O，不支持阻塞操作"）
        - 验证所有需求维度均已覆盖
        - 验证所有需求描述清晰且可验收
        - 验证需求不与项目约束冲突
        - 验证需求描述不含技术实现细节
    
    output: [功能域识别, 需求维度清单, 外部分析报告, 完整需求描述, 项目约束影响说明]

  - id: write_output
    name: 生成完整需求文档
    path: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${FILENAME}"
    include:
      - 用户意图理解（AI对用户诉求的解读与功能域识别）
      - 业务场景分析报告（若有目标系统/API/数据源，包含业务特征分析）
      - 功能需求完整描述（按需求维度组织，使用业务语言，禁止技术实现细节）
      - 数据需求完整描述（数据来源/类型/结构/量级，使用业务术语）
      - 性能与质量要求（响应时间/吞吐量/并发量/准确性，量化指标）
      - 异常场景与边界条件（失败定义/重试要求/边界值）
      - 安全与合规要求（数据敏感性/访问控制/审计）
      - 可观测性要求（需记录的业务事件/需监控的业务指标）
      - 范围与非目标（明确边界）
      - 项目约束说明（技术栈约束对需求的影响）
      - 交付与验收标准（从需求转化为可测试的验收条件）
      - 生成时间与意图信息（INTENT_TITLE_2_4、COUNT_3D）
    
    acceptance:
      - 输出路径符合 params.path_template
      - 中文输出且结构化清晰
      - 需包含 style.sections_template 中定义的章节
      - "功能需求描述"章节必须使用业务语言，禁止出现技术实现细节（如具体库名/框架名/参数值）
      - "数据需求描述"章节必须描述业务数据特征，不涉及存储技术（可说"需持久化存储"，不可说"存入MongoDB"）
      - "性能与质量要求"章节必须给出量化指标，不涉及实现手段（可说"支持100并发"，不可说"使用20个worker"）
      - 所有需求描述可转化为验收标准（可测试/可验证）
      - 文档聚焦"要做什么"，不涉及"怎么做"
      - 文档完整性：DevPipelineGeneration 可基于此文档生成完整的技术实现步骤
      - 所有需求不与 io.dev_constitution 约束冲突
      - params.INTENT_TITLE_2_4 必须从任务意图动态生成且匹配 naming_rules.intent_title_2_4.regex（禁止使用 "InitialSetup" 等通用值，除非任务真的是初始化设置）
    
    downstream_validation:
      - 文档须为 DevPipelineGeneration 工作流提供充分的需求输入
      - DevPipelineGeneration 可基于此文档进行技术选型和实现拆解
      - 文档不包含技术实现决策，为 DevPipelineGeneration 保留技术选型空间

  - id: self_check
    name: 规范对齐验证
    actions:
      - 读取当前流程的所有约束源（io 声明的规范文件）
      - 读取上一步输出的文件
      - 对比发现偏差（语气/路径/约束/覆盖）
      - 发现偏差立即修正并重写文件
      - 验证修正结果，最多3轮
    acceptance: 生成物与约束源完全对齐

