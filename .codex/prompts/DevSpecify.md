workflow:
  name: DevSpecify
  description: 自包含的自动化“开发计划指定与修改”工作流契约（YAML 精简版）
  language: zh-CN

params:
  OUTPUT_DIR_PATH: "D://AI_Projects//CodexFeatured//DevPlans"
  COUNT_3D: "001"  # 动态三位编号（见 naming_rules.count_3d.generation）
  INTENT_TITLE_2_4: "InitialSetup"  # 从任务意图动态生成（见 naming_rules.intent_title_2_4.generation）
  SUBDIR_NAME: "${COUNT_3D}_${INTENT_TITLE_2_4}"
  FILENAME: "DemandDescription.md"
  path_template: "${OUTPUT_DIR_PATH}//${SUBDIR_NAME}//${FILENAME}"

naming_rules:
  count_3d:
    description: "三位编号识别；在本流程用于选择已存在的最大编号目录，而非新建。"
    examples:
      - "001"
      - "042"
      - "123"
    regex: "^\\d{3}$"
    generation:
      - "列出 ${OUTPUT_DIR_PATH} 下匹配 ^\\\d{3}_.+ 的子目录"
      - "提取前3位编号；按降序排序"
      - "选择编号最大的目录作为当前目标"
      - "若不存在任何编号目录，则报错终止"
  intent_title_2_4:
    description: "用 2–4 个英文词，PascalCase（UpperCamelCase）；不含下划线/连字符/空格；禁止缩写与过短词。"
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
      - "基于当前任务意图/标题提取 2–4 个核心英文词（名词/动词）"
      - "移除停用词（the, a, an, of, for, with, and, to, in）"
      - "同义词归一化，优先采用行业常用术语"
      - "转为 PascalCase，去分隔符拼接"
      - "每个词长度 ≥ 3，避免缩写/首字母词"
      - "如语义歧义，兜底使用 GeneralTask"
  subdir_numbering:
    description: "Subfolder numbering policy for DevPlans（本流程只读取，不创建）"
    rules:
      - "Start at 001 and increment sequentially (001, 002, ...)."
      - "On number conflicts, use the next available number."
      - "If the target directory is empty, report error for DevSpecify."

assumptions:
  - 用户提示词的核心目的恒为“指定与修改现有开发需求文档”。
  - 输出语言必须为中文，结构清晰、修改颗粒细度覆盖最小落地无死角。

objectives:
  - 将自然语言诉求转为对目标文档的精确增删改规则。
  - 明确结构/变更决策：仅在显式要求时新增目录树或说明不新增的理由；需修改文件与修改原因。

deliverable_requirements:
  add_structure_or_not:
    if_new_required: "仅在明确提出时：提供目录树（代码块），并给出用途与放置理由。"
    if_not_required: "默认不新增目录/文件，并说明保持现状的理由。"
  modify_existing_files:
    describe:
      - 仓库相对路径与文件名
      - 修改原因（缺陷修复/能力补充/重构/配置变更等）

io:
  user_prompt_path: "CodexFeatured/DevFuncDemandsWrite/PromptDraft.md"
  codebase_map_script: "D:/AI_Projects/CodexFeatured/Scripts/CodebaseStructure.py"
  codebase_structure_doc: "D:/AI_Projects/CodexFeatured/Common/CodebaseStructure.yaml"
  dev_constitution: "CodexFeatured/Common/BackendConstitution.yaml"
  best_practices: "CodexFeatured/Common/BestPractise.yaml"
  kobe_root_index: "Kobe/index.yaml"

research_policy:
  - 官方规范与实现方式须优先于其他来源。
  - 吸收社区共识（GitHub/StackOverflow/技术博客）以补充实践细节。

steps:
  - id: load_prompt
    name: 加载用户提示词
    actions:
      - 读取并理解 io.user_prompt_path
    output: [enhanced_requirements]
    purpose: 语义增强与需求提取。

  - id: check_docs
    name: 文档状态检查与索引遍历（含目标定位）
    actions:
      - 运行 io.codebase_map_script
      - 读取 io.codebase_structure_doc
      - 读取 io.kobe_root_index（作为起点）
      - 自根遍历索引（保持 BFS 或 DFS 一致）：
        - 读取当前 index.yaml 的 module/relations/files/sub_indexes 内容
        - 发现子索引：将 sub_indexes 中的每个路径加入待访问队列并依次读取
        - 发现依赖：将 relations.depends_on（仅限 Kobe/ 内部路径）加入待访问队列并依次读取
        - 构建/合并 index_map（path → module.summary/responsibilities/relations/files）
        - 记录遍历次序 traversal_order
      - 基于 enhanced_requirements 进行影响分析 impact_analysis：
        - 识别受影响模块/目录（affected_modules）
        - 标注增强/修改/新增建议（enhancements/changes/additions）
      - 按 naming_rules.count_3d.generation 查找编号最大目录
      - 拼接目标路径: "${OUTPUT_DIR_PATH}//{编号最大目录}//${FILENAME}"
      - 读取目标文件并验证存在性
  output: [repo_context, index_map, traversal_order, missing_indexes, impact_analysis, target_path, target_document]
  purpose: 自根读取首个索引并按依赖与子索引向下遍历，评估与提示词的影响并定位目标文件。

  - id: load_policies
    name: 规范加载与调研
    actions:
      - 读取 io.dev_constitution 并严格遵守
      - 读取 io.best_practices 并浏览其中官方链接
      - 调研社区最佳实践（GitHub/StackOverflow/开发者博客）
    output: [policy_and_best_practice_summary]
    gate: 完成后进入 write_output。

  - id: write_output
    name: 应用指定修改并写回
    path: "{check_docs 阶段确定的 target_path}"
    include:
      - 具体变更清单（位置/动作/理由）
      - 跨章节引用一致性更新
      - 不新增结构时的理由或新增结构的目录树
    acceptance:
      - 目标路径为 "${OUTPUT_DIR_PATH}//{编号最大目录}//${FILENAME}"
      - 中文输出且结构化清晰
      - 描述正文与 io.dev_constitution 与官方最佳实践一致
      - params.INTENT_TITLE_2_4 匹配 naming_rules.intent_title_2_4.regex