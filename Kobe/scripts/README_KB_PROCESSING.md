# 服务知识库处理脚本使用说明

## 概述

本脚本实现服务知识库的增量式关联构建，将 `KB/services` 下的源文件整合并建立业务关联网络。

## 核心机制

**叠加光环（Incremental Association Building）**

每处理一个源文件，生成的业务文档会基于所有已处理业务进行关联推理。随着处理文件增多，关联网络自动完善。

```
处理文件1 → 业务A (0个关联)
处理文件2 → 业务B, 发现B需要A的产出 → 建立A→B关联
处理文件3 → 业务C, 发现C产出被A、B需要 → 建立C→A, C→B关联
...每个新业务都基于所有已有业务进行推理
```

## 文件结构

```
Kobe/
├── scripts/
│   ├── process_kb_services.py      # 主脚本
│   ├── run_kb_processing.bat       # Windows 启动脚本
│   └── README_KB_PROCESSING.md     # 本文档
│
.TelegramChatHistory/
├── KB/
│   └── services/                   # 源文件目录（838个md文件）
│
├── Workspace/
│   ├── .WorkPlan/
│   │   ├── AnalysisList.md         # 进度管理（[x]已完成 / [ ]待处理）
│   │   ├── VisaServiceFileStructure_template.md  # 业务文档模板
│   │   ├── StructureRelation.yaml  # 关系推理规则引擎
│   │   └── logs/                   # 处理日志（每个文件一个JSON）
│   │
│   └── VisaAchknowlegeBase/        # 输出目录
│       ├── Index.yaml              # 业务索引
│       ├── PresetServiceCollections.yaml  # 组合业务
│       ├── AmbiguousTermsDictionary.yaml  # 歧义词典
│       ├── BureauOfImmigration/    # 移民局业务
│       ├── DepartmentOfLabor/      # 劳工部业务
│       └── ...                     # 其他部门
```

## 使用方法

### 方法1：使用批处理文件（推荐）

双击运行：
```
Kobe/scripts/run_kb_processing.bat
```

脚本会自动：
1. 激活虚拟环境
2. 检查并安装必要的包
3. 运行处理脚本
4. 显示实时进度

### 方法2：命令行运行

```bash
cd D:\AI_Projects\Kobe
venv\Scripts\activate
python scripts\process_kb_services.py
```

## 工作流程

### 1. 初始化阶段

- 加载 `.env` 配置（API Key、模型等）
- 读取 `AnalysisList.md` 获取已处理文件列表
- 扫描 `KB/services` 目录，同步新文件到列表
- 加载已完成业务摘要（name, slug, input/output files）

### 2. 主循环处理

对于每个待处理文件：

**步骤1：构造上下文包**
```python
上下文 = {
    "当前源文件": 完整内容（含多个数据来源段落）,
    "模板": VisaServiceFileStructure_template.md,
    "关系规则": StructureRelation.yaml,
    "全局知识": {
        "Index.yaml": 当前索引,
        "Collections": 当前组合,
        "AmbiguousTerms": 当前歧义词,
        "已完成业务摘要": [业务1, 业务2, ...]
    }
}
```

**步骤2：调用 AI 进行推理**
- 模型：gpt-4o-mini-2024-07-18
- 温度：0.3（确保稳定性）
- 输出格式：JSON

AI 执行：
1. 整合源文件的多个数据来源段落
2. 应用 StructureRelation.yaml 的规则推理关联
3. 生成完整业务文档（至少100行）
4. 输出结构化指令

**步骤3：执行指令**

脚本解析 JSON 并执行：
- `create_business`: 创建新业务文档
- `update_business`: 回溯更新已有业务（建立双向关联）
- `update_index`: 更新 Index.yaml
- `update_collections`: 更新组合业务
- `update_ambiguous`: 更新歧义词典

**步骤4：记录进度**
- 更新 `AnalysisList.md`：`[ ]` → `[x]`
- 保存处理日志到 `logs/`

### 3. 完成阶段

显示统计信息：
- 成功处理的文件数
- 失败的文件数
- 总业务数量
- 关联更新次数

## 进度管理

### AnalysisList.md 格式

```markdown
## 文件清单

[x] D:\AI_Projects\.TelegramChatHistory\KB\services\9g工签办理.md
[x] D:\AI_Projects\.TelegramChatHistory\KB\services\aep申请.md
[ ] D:\AI_Projects\.TelegramChatHistory\KB\services\icard申请.md
[ ] D:\AI_Projects\.TelegramChatHistory\KB\services\...
```

- `[x]` = 已完成
- `[ ]` = 待处理

### 断点续传

脚本中断后重新运行会：
1. 读取 `AnalysisList.md` 跳过已完成文件
2. 从第一个 `[ ]` 文件继续处理
3. 不会重复处理已完成的文件

### 手动重置进度

如需重新处理某个文件，将其标记改为 `[ ]`：
```markdown
[ ] D:\AI_Projects\.TelegramChatHistory\KB\services\9g工签办理.md
```

## AI 推理规则

脚本使用 `StructureRelation.yaml` 作为推理引擎，教 AI：

### 1. 文件生产链推理
```
对input_files中的每个文件：
  查询已完成业务库 → 
    有业务产出? → documents_can_produce (含producer路径)
    无业务产出? → documents_must_provide
  建立related_businesses双向关联
```

### 2. 背景前提推理（三步法）
```
- 地理前提: 从业务性质判断（如：签证延期 → 必须在菲律宾）
- 关系前提: 从业务名称推断（如：结婚签证 → 已结婚）
- 业务前提: 从input_files推断（如：需要签证 → 必须有有效护照）
```

### 3. Mandatory 关联识别
```
if output_files被其他业务需要:
  生成回溯更新指令
  双向更新related_businesses
```

## 输出说明

### 业务文档结构

每个生成的业务文档包含：

```markdown
---
name: "9G Work Visa Application"
slug: "9g-work-visa-application"
type: "solo_task"
department: "BureauOfImmigration"

documents_must_provide: ["护照", "照片"]
documents_can_produce:
  - document: "AEP卡"
    producer: "AEP Application"
    path: "DepartmentOfLabor/aep-application.md"

documents_output: ["9G工签", "I-Card"]

related_businesses:
  - name: "AEP Application"
    path: "DepartmentOfLabor/aep-application.md"
    reason: "可产出本业务需要的AEP卡"

aliases: ["9G工签办理", "工签"]
updated_at: "2025-10-17"
---

# 9G Work Visa Application

## Summary
...

## Background Prerequisites
...

## Documents To Prepare
...

## Process
...

## Pricing
...

## Notes
...

## Evidence Sources
...
```

### Index.yaml 结构

```yaml
meta:
  name: "Visa Service Knowledge Base Index"
  last_updated: "2025-10-17"
  total_businesses: 320

departments:
  BureauOfImmigration:
    full_name: "Bureau of Immigration"
    folder_path: "BureauOfImmigration/"
    solo_tasks:
      - name: "9G Work Visa Application"
        path: "BureauOfImmigration/9g-work-visa-application.md"
        type: "solo_task"
      ...
```

## 日志和调试

### 处理日志

每个文件处理完成后，会在 `logs/` 生成 JSON 日志：

```
logs/
├── 20251017_143000_9g工签办理.json
├── 20251017_143520_aep申请.json
└── ...
```

日志包含：
- AI 返回的完整 JSON 响应
- 识别的业务信息
- 执行的所有指令

### 查看日志

```bash
# 查看最新日志
cat .TelegramChatHistory/Workspace/.WorkPlan/logs/*.json | tail -n 100

# 统计创建的业务数
grep -r "create_business" .TelegramChatHistory/Workspace/.WorkPlan/logs/ | wc -l
```

## 常见问题

### Q: 脚本运行很慢？

A: 正常。每个文件需要：
- 读取多个上下文文件（模板、规则、已有业务）
- 调用 AI API（需要几秒到十几秒）
- 执行多个文件操作

预计处理838个文件需要数小时。

### Q: 如何加快处理速度？

A: 可以考虑：
1. 使用更快的模型（但可能影响质量）
2. 减少上下文大小（但可能影响推理准确性）
3. 并行处理（需修改脚本，注意文件冲突）

### Q: 处理失败怎么办？

A: 脚本会：
1. 打印错误信息
2. 不标记该文件为完成
3. 继续处理下一个文件

下次运行时会重新尝试失败的文件。

### Q: 如何验证输出质量？

A: 检查：
1. 业务文档是否完整（至少100行）
2. 关联关系是否准确（related_businesses）
3. Index.yaml 统计是否正确
4. 证据来源是否保留中文原文

### Q: 发现业务文档有错误？

A: 可以：
1. 手动编辑业务文档修正
2. 或将文件标记为 `[ ]` 重新处理
3. 或修改源文件后重新处理

## 配置说明

### .env 配置

```bash
# OpenAI API
OPENAI_API_KEY="sk-..."
OPENAI_MODEL_MINI="gpt-4o-mini-2024-07-18"
```

### 调整处理参数

修改 `process_kb_services.py`：

```python
# AI 调用参数
temperature=0.3        # 降低随机性（0-1）
response_format={"type": "json_object"}  # 强制 JSON 输出

# 模型选择
MODEL = os.getenv("OPENAI_MODEL_MINI", "gpt-4o-mini-2024-07-18")
```

## 最佳实践

1. **定期备份**
   ```bash
   # 备份输出目录
   cp -r .TelegramChatHistory/Workspace/VisaAchknowlegeBase backup/
   ```

2. **监控进度**
   - 查看 Terminal 输出
   - 检查 AnalysisList.md 的 `[x]` 标记数量
   - 查看 Index.yaml 的 total_businesses 数值

3. **分批处理**
   - 可以暂停脚本（Ctrl+C）
   - 下次运行自动从断点继续
   - 适合长时间处理任务

4. **质量检查**
   - 随机抽查生成的业务文档
   - 验证关联关系的准确性
   - 检查证据来源是否完整

## 技术细节

### 依赖包

```
openai>=1.0.0         # OpenAI API 客户端
python-dotenv>=1.0.0  # 环境变量管理
rich>=13.0.0          # 终端美化
pyyaml>=6.0.0         # YAML 解析
```

### 性能指标

- 单文件处理时间：10-30秒
- API 调用耗时：5-20秒
- 文件操作耗时：1-3秒
- 内存占用：< 500MB

### 错误处理

脚本包含完善的错误处理：
- API 调用失败：打印错误，继续下一个
- 文件读写失败：打印警告，继续执行
- JSON 解析失败：记录错误，跳过该文件
- 键盘中断：保存进度，优雅退出

## 联系方式

如有问题或建议，请查看项目文档或联系开发团队。

