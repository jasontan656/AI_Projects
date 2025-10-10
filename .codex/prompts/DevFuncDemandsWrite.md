workflow:
  name: DevFuncDemandsWrite
  description: 自包含的自动化“开发文档撰写”工作流契约（YAML 精简版）
  language: zh-CN

params:
  OUTPUT_DIR_PATH: "D:/AI_Projects/CodexFeatured/DevPlans"
  COUNT_3D: "001"  # 动态三位编号（见 naming_rules.count_3d.generation）
  INTENT_TITLE_2_4: "InitialSetup"  # 从任务意图动态生成（见 naming_rules.intent_title_2_4.generation）
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
  subdir_numbering:
    description: "DevPlans 子目录编号策略"
    rules:
      - "从 001 开始依次递增（001, 002, ...）"
      - "若发生编号冲突，则采用下一个可用编号"
      - "若目标目录为空，先创建 001 再写入产物"

assumptions:
  - 用户提示词的核心目的恒为“撰写开发需求文档”。
  - 输出语言必须为中文，结构清晰、需求颗粒细度覆盖最小落地无死角。

objectives:
  - 将自然语言诉求转为需求条目、功能规则。
  - 明确结构/变更决策：新增目录树或不新增理由；需修改文件与修改原因。

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
    - "2. 范围与非目标"
    - "3. 核心功能需求（可验收条目）"
    - "4. 结构/变更决策"
    - "5. 需修改的现有文件"
    - "6. 详细规则与约束"
    - "7. 补充建议与细化项"
    - "8. 参考规范与一致性说明"
    - "9. 交付与验收清单"

io:
  user_prompt_path: "CodexFeatured/DevFuncDemandsWrite/PromptDraft.md"
  codebase_map_script: "D:/AI_Projects/CodexFeatured/Scripts/CodebaseStructure.py"
  codebase_structure_doc: "D:/AI_Projects/CodexFeatured/Common/CodebaseStructure.yaml"
  dev_constitution: "CodexFeatured/Common/BackendConstitution.yaml"
  best_practices: "CodexFeatured/Common/BestPractise.yaml"
  kobe_root_index: "Kobe/index.yaml"


steps:
  - id: load_prompt
    name: 加载用户提示词
    actions:
      - 读取并理解 io.user_prompt_path
        - 目的: 语义增强与需求提取。

  - id: enhance_requirements
    name: 语义增强与需求提炼
    actions:
      - 基于用户提示词生成 enhanced_requirements：结构化需求条目、边界、假设与疑点
      

  - id: check_docs
    name: 文档状态检查与索引遍历
    actions:
      - 运行 io.codebase_map_script
      - 读取 io.codebase_structure_doc
        - 目的：了解项目文件结构
      - 读取 io.kobe_root_index
      - 按 relation 自顶向下遍历直至所有 index.yaml 读取完毕
        - 目的：了解项目模块依赖关系和开发意图
      - 基于 enhanced_requirements 进行影响分析 impact_analysis：
        - 目的：识别受影响模块/目录（affected_modules）
        - 标注增强/修改/新增建议（enhancements/changes/additions）

  - id: load_policies
    name: 规范加载与调研
    actions:
      - 读取 io.dev_constitution
        - 目的：加载宪法限制需求规范
      - 读取 io.best_practices 并浏览其中官方链接
        - 目的：调研社区最佳实践（GitHub/StackOverflow/开发者博客）避免自己造轮子
   
   

  - id: write_output
    name: 写入目标文件
    path: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${FILENAME}"
    include:
      - 完整功能条目描述
      - 文件树结构所需变更（Markdown Tree 格式）
      - 补充建议与细化项（弥补初始描述不足）
      - 前言元信息（范围、非目标、验收标准摘要、参考规范）
      - 生成时间与意图信息（INTENT_TITLE_2_4、COUNT_3D）
    acceptance:
      - 输出路径符合 params.path_template
      - 中文输出且结构化清晰
      - 描述正文与 io.dev_constitution 及官方最佳实践一致
      - params.INTENT_TITLE_2_4 匹配 naming_rules.intent_title_2_4.regex
      - 需包含 style.sections_template 中定义的九个章节，编号样式一致
      - 引用的 CodebaseStructure 与 BackendConstitution 文档名应与 io 中配置一致



