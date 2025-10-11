workflow:
  name: DevExcute
  description: 执行开发任务列表 Tasks.md 
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

objectives:
  - 定位并解析 Tasks.md，按顺序逐项执行开发步骤完成功能开发。

io:
  codebase_map_script: "CodexFeatured/Scripts/CodebaseStructure.py"
  codebase_structure_doc: "CodexFeatured/Common/CodebaseStructure.yaml"
  dev_constitution: "CodexFeatured/Common/BackendConstitution.yaml"
  code_comment_standard: "CodexFeatured/Common/CodeCommentStandard.yaml"
  best_practices: "CodexFeatured/Common/BestPractise.yaml"

research_policy:
  - 官方规范与实现方式须优先于其他来源。
  - 吸收社区共识（GitHub/StackOverflow/技术博客）以补充实践细节。

steps:
  - id: check_docs
    name: 加载任务清单
    actions:
      - 运行 io.codebase_map_script
      - 读取 io.codebase_structure_doc
      - 扫描 ${OUTPUT_DIR_PATH} 按 ^\d{3}.+ 找最大编号目录
        - 拼接路径: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}"
      - 读取需求文档并验证存在性
        - 需求文档: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${DEMAND_FILENAME}"
        - 任务列表: "${OUTPUT_DIR_PATH}/${SUBDIR_NAME}/${TASKS_FILENAME}"
      - 读取目标 task.md 并解析生成任务清单
      
      
  - id: load_policies
    name: 规范加载与调研
    actions:
      - 读取 io.dev_constitution 并严格遵守
      - 读取 io.best_practices 并浏览其中官方链接
      - 调研社区最佳实践（GitHub/StackOverflow/开发者博客）
    purpose: 加载开发规范学习了解当前任务最佳实践


  - id: execute_pipeline
    name: 实现业务功能
    actions:
        - 依据任务列表完成开发
        - 按 acceptance 验证结果

    acceptance:
      - 符合 io.dev_constitution 与官方最佳实践
      - 符合 io.code_comment_standard 的注释要求
      - 符合 io.dev_constitution 的技术栈约束


  - id: self_check
    name: 规范对齐验证
    actions:
      - 读取当前流程的所有约束源（io 声明的规范文件）
      - 读取上一步输出的文件
      - 对比发现偏差（语气/路径/约束/覆盖）
      - 发现偏差立即修正并重写文件
      - 验证修正结果，最多3轮
    acceptance: 生成物与约束源完全对齐