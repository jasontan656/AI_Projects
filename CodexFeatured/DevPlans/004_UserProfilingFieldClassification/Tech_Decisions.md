# Tech Decisions — 004_UserProfilingFieldClassification

Date: 2025-10-11
Target Dir: D:/AI_Projects/CodexFeatured/DevPlans/004_UserProfilingFieldClassification

Summary
- Intent: UserProfilingFieldClassification
- Count: 004

Standards
- BackendConstitution.yaml: Python 3.10; Logging via `Kobe.SharedUtility.RichLogger`; Validation via Pydantic v2（PyPI 暂无 v3）。
- CodeCommentStandard.yaml: 模块 docstring + 关键行注释已执行（见 `field_ops.py`）。
- BestPractise.yaml: 依赖与官方链接取自其建议，优先官方文档。

Dependencies
- openai>=1.50.0 (installed: 2.3.0)
- sqlparse>=0.5.0 (installed: 0.5.3)
- pydantic>=2.7,<3 (installed: 2.12.0)

Rationale
- LLM 必须：未连接 LLM 时输出空报告，避免不统一的启发式结论进入业务。
- 统一分类：通过预设 Taxonomy 严格约束 `category_key`，杜绝自创分类名，确保跨表一致。
- RichLogger：标准库 logging，减少依赖与运行时耦合。

Artifacts
- Requirements: `Kobe/Requirements.txt`
- Logger: `Kobe/SharedUtility/RichLogger/{__init__.py,logger.py}`
- Pipeline: `Kobe/TempUtility/VisaDBOperation/field_ops.py`
- Outputs:
  - JSON: `D:/AI_Projects/Kobe/TempUtility/VisaDBOperation/field_samples.json`
  - Report: `D:/AI_Projects/Kobe/TempUtility/VisaDBOperation/VisaDatabseDietPlan.md`

Notes
- 未连接大模型：直接报错并以非零状态退出（不生成空报告、不启用任何兜底）。
- 脱敏策略：遮蔽 2–5 个字符，兼顾不可还原与可读性。
- 环境读取：所有脚本优先从 `Kobe/.env` 读取环境变量（不覆盖已设定的进程环境）。
  - 必填/默认项：`OPENAI_MODEL=gpt-4o-mini`（本仓库 `.env` 已内置）。
  - 运行前请设置：`OPENAI_API_KEY`。
  - 入口建议使用包装器：
    - 采集：`python -m Kobe.TempUtility.VisaDBOperation.run_collect_values ...`
    - 分类：`python -m Kobe.TempUtility.VisaDBOperation.run_field_ops ...`
- Prompt 结构（包含四块）：需求、分类列表、判断流程（最小可执行动作命令）、最终返回 JSON 数据格式。

Preset Taxonomy（LLM 只能从以下 category_key 中二选一，不得自创）
- 画像类（profile=true）：
  - `name` 姓名/名称
  - `username` 用户名/账号名
  - `email` 邮箱
  - `phone_number` 电话/手机号
  - `national_id` 身份证/证件号
  - `passport_number` 护照号
  - `physical_address` 物理地址
  - `geo_location` 地理位置
  - `gender` 性别
  - `date_of_birth` 出生日期
  - `device_id` 设备/浏览器ID
  - `organization` 组织/公司/院校
  - `job_title` 职位/头衔
  - `user_message` 用户输入文本
  - `free_text` 自由文本/描述
- 非画像类（profile=false）：
  - `primary_key` 主键ID
  - `foreign_key` 外键ID
  - `system_audit` 系统审计（创建/更新时间等）
  - `timestamp` 时间戳/日期
  - `status_flag` 状态标识/枚举
  - `financial_amount` 金额/价格/余额
  - `quantity` 数量/计数
  - `other` 其它/无法判定

报告生成规则
- 仅输出“用户画像类（<字段>：“<理由>”）”行；非画像类不写入文件，以避免噪点。
