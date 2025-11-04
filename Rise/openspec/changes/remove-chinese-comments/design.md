## Context
代码结构在多处沿用中文注释补充运行时行为。随着 snake_case 与其它风格统一，注释语言也需要保持一致，以便未来 lint/文档工具（wemake-python-styleguide 等）落地。

## Decisions
- 在 spec 中新增约束：仓库内代码注释应使用英文；非 ASCII 内容仅限业务常量、用户文案等，而非代码注释。
- 清理过程中优先将关键说明翻译成英文，若属于冗余注释则直接移除。
- 编译检查使用 `python3 -m compileall app.py shared_utility telegram_api`，验证缩进/语法未受影响。

## Alternatives
- **保持现状**：继续允许中文注释，放弃统一；不利于跨团队合作并阻碍自动化风格检查。
- **引入多语言注释规范**：成本较高，且与既定英文主导的项目规范冲突。
