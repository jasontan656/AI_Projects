workflow:
  name: TestDebugging
  description: |
    你现在进入debug模式。你必须严格按照如下流程执行，不得跳过任何步骤。
    核心原则：从源头理解问题，而非仅解决表面现象。
  language: zh-CN

objectives:
  - 你必须从开发意图的角度定位bug的真实根因
  - 你必须判断问题是否源于配置缺失、环境差异、开发覆盖不足或基础设施问题
  - 你必须提供从根本上解决问题的方案，而非临时修补

prohibited_actions:
  - 禁止仅根据报错信息就提出解决方案
  - 禁止跳过文档和项目结构的全面了解
  - 禁止提供最小化修改方案（patch式修复）
  - 禁止忽略操作系统环境差异（Windows vs Linux等）
  - 禁止在未调研官方文档和社区实践前就下结论

steps:
  - id: check_docs
    name: 项目全貌理解（必需步骤）
    mandatory: true
    actions:
      - 你必须运行 io.codebase_map_script 生成最新代码结构
      - 你必须完整读取 io.codebase_structure_doc
      - 你必须读取 io.kobe_root_index
      - 你必须按 relation 自顶向下遍历直至所有 index.yaml 读取完毕
      - 你必须构建项目能力图谱：
        - 已实现功能模块：名称、职责边界、对外API、使用示例
        - 技术栈约束：框架、库、中间件的强制要求与禁止项
        - 基础设施现状：数据库/缓存/消息队列/存储的配置与容量
        - 可复用组件：工具函数/中间件/装饰器的路径与用途
        - 项目架构模式：目录组织/模块依赖/命名规范
      - 你必须找到 ${OUTPUT_DIR_PATH} 内编号最大的文件夹（格式：001_xxx, 002_xxx等）
      - 你必须完整读取该文件夹内的 DemandDescription.md，理解当前开发意图
    output_required:
      - 项目能力图谱（包含上述五个维度）
      - 当前开发阶段和目标
      - bug发生的模块在项目中的角色
      - 该模块依赖的基础设施清单

  - id: load_policies
    name: 规范与最佳实践调研（必需步骤）
    mandatory: true
    actions:
      - 你必须完整读取 io.dev_constitution
      - 你必须完整读取 io.best_practices
      - 你必须使用 web_search 工具，搜索相关技术栈的官方文档
      - 你必须使用 web_search 工具，搜索 GitHub Issues 和 StackOverflow 中的相似问题
      - 特别关注：环境相关配置（如Windows下的Celery配置要求）
    output_required:
      - 官方推荐的配置和实现方式
      - 已知的环境兼容性问题
      - 社区验证过的解决方案

  - id: analyze_issue
    name: 根因分析（必需步骤）
    mandatory: true
    actions:
      - 你必须对照开发意图，判断bug属于以下哪一类：
        1. 配置缺失或不完整（如数据库未启动、环境变量未设置、后端broker不兼容）
        2. 开发功能尚未覆盖（需求已提出但未实现）
        3. 代码逻辑错误（已实现但有bug）
        4. 基础设施不到位（依赖服务未安装/未启动）
        5. 环境差异问题（Windows/Linux/Mac行为不一致）
      - 你必须分析：如果在开发文档中补充此项配置/说明，是否能从根本避免此类问题
    output_required:
      - bug的准确分类（上述5类中的哪一类）
      - 根因的详细描述
      - 是否需要更新开发文档

  - id: propose_solution
    name: 根本性解决方案制定（必需步骤）
    mandatory: true
    actions:
      - 你必须提出从源头解决问题的方案，包括：
        1. 直接修复（如果是代码bug）
        2. 配置补充（如果是配置缺失，需说明在哪个文件添加什么配置）
        3. 文档更新（如果需要在开发文档中补充说明）
        4. 环境适配（如果是环境差异，需提供多环境方案）
      - 你必须说明：为什么这个方案是从根本解决，而非临时修补
    output_required:
      - 具体的修复步骤（可执行的命令或代码）
      - 需要更新的文档清单
      - 验证方案是否有效的测试方法

  - id: report
    name: 调试报告输出（必需格式）
    mandatory: true
    output_format: |
      ## Bug调试报告
      
      ### 1. 项目背景
      - 当前开发意图：[从DemandDescription.md提取]
      - Bug发生模块：[模块名称和在项目中的角色]
      
      ### 2. 根因分析
      - Bug分类：[配置缺失/功能未覆盖/逻辑错误/基础设施/环境差异]
      - 根本原因：[详细描述]
      - 为何会发生：[是否是开发考虑不周/配置文档缺失]
      
      ### 3. 调研发现
      - 官方文档说明：[引用官方推荐方式]
      - 社区实践：[引用GitHub/StackOverflow相关讨论]
      - 环境注意事项：[特别是Windows等特殊环境]
      
      ### 4. 根本性解决方案
      - 方案描述：[如何从源头解决]
      - 具体步骤：[可执行的操作]
      - 文档更新：[需要在哪些文档补充说明]
      - 验证方法：[如何确认修复有效]
      
      ### 5. 预防措施
      - 开发文档需补充的内容
      - 未来避免类似问题的建议
