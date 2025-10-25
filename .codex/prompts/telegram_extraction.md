---
description: Execute the knowledge base cleaning workflow by processing ALL files defined in AnalysisList.md
version: 2.0
output_location: "D:\\AI_Projects\\.TelegramChatHistory\\Workspace\\VisaAchknowlegeBase"
---

# 服务知识库数据清洗工作流

**执行模式：**
- 在当前session中直接执行所有操作，不创建外部脚本
- 逐个处理文件，全部操作在session内部完成
- **所有生成文档使用英文**（文档正文、frontmatter、摘要、流程等全部英文）
- **唯一例外：** 证据来源章节保留中文原文引用
- 不要向用户询问确认，自动连续执行直到所有文件标记为 `[x]`

## 核心机制

处理 `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md` 中的所有文件，基于全局已有知识进行增量式分析和更新。

**核心Schemas：** `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\StructureRelation.yaml` - 业务关系定义  
**业务文档模板：** `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\VisaServiceFileStructure_template.md`  
**工作清单：** `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md` - 包含所有待处理文件
**NONE-USER-INERACTION-WORK-FLOW** - DO NOT REPORT TO USE NEITHER TO ASK USER FOR ANY CONFIRMATION. SILENTLY CONTINUE UNTIL TASK ALL DONE.
---

## 工作目录

- **源文件：** `D:\AI_Projects\.TelegramChatHistory\KB\services\` （只读）
- **输出目录：** `D:\AI_Projects\.TelegramChatHistory\Workspace\VisaAchknowlegeBase\`
- **工作清单：** `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md`

**输出结构：**
```
VisaAchknowlegeBase/
├── Index.yaml
├── PresetServiceCollections.yaml
├── AmbiguousTermsDictionary.yaml
├── DepartmentA/${service}.md
├── DepartmentB/${service}.md
├── DepartmentC/${service}.md
└── {NewDetectedDepartment}/${service}.md
```

说明：部门名称由源数据决定，可能包括但不限于：政府部门（移民局、劳工部、外交部等）、商业机构、服务类别等。

---

## 执行流程

### 步骤1：加载工作清单

读取 `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md`，提取所有状态为 `[ ]` 的文件路径。

**如果所有文件都是 `[x]`：** 工作流完成，进入最终审核阶段。

---

### 步骤2：逐个处理文件

对每个状态为 `[ ]` 的文件，按以下流程处理：

#### 2.1 重新加载全局知识（每个文件处理前必执行）

**重要：每次处理新文件前都必须重新读取这些文件，因为上一个文件可能已更新它们。**

读取以下文件构建最新的全局知识：

1. **重新读取** `D:\AI_Projects\.TelegramChatHistory\Workspace\VisaAchknowlegeBase\Index.yaml` - 获取最新的部门和业务列表
2. **重新读取** `D:\AI_Projects\.TelegramChatHistory\Workspace\VisaAchknowlegeBase\PresetServiceCollections.yaml` - 获取最新的组合列表
3. **重新读取** `D:\AI_Projects\.TelegramChatHistory\Workspace\VisaAchknowlegeBase\AmbiguousTermsDictionary.yaml` - 获取最新的歧义词列表
4. **重新读取** `D:\AI_Projects\.TelegramChatHistory\Workspace\VisaAchknowlegeBase\` 下所有已生成业务文档的frontmatter - 重新构建全局文件生产图谱：`文件名 → [producer业务列表]`

**第一个文件特殊处理：** 如果这些文件不存在或为空，跳过对应读取。

#### 2.2 读取当前源文件

读取当前待处理文件的完整内容。

#### 2.3 拆分、识别和提取业务内容

**步骤A：拆分业务**

分析源文件描述了几个业务（单一业务 或 多个业务）。一个源文件可能包含多个独立业务。

**步骤B：对每个识别出的业务执行以下操作**

**B1. 提取源文件的原始内容：**

从当前源文件中提取以下所有可用信息（字段名称可能略有不同，灵活匹配）：

- 业务名称（frontmatter中的name/title字段）
- 别名列表（aliases字段）
- 摘要/描述/简介部分的完整文字
- 材料/要求/需求部分的内容
- 办理流程/步骤/过程部分的内容
- AI提取的办理步骤列表（如果存在）
- 价格/费用/成本表格或列表的所有行
- AI提取的注意事项/风险/限制列表（如果存在）
- AI提取的聊天证据/对话记录列表（如果存在）
- 证据引用/来源引用部分的所有内容
- 文件底部的数据来源、提取时间、文件路径等元信息

**B2. 生成英文业务标识：**

基于源文件的业务名称，生成准确的英文标识：

- **name:** 完整的英文业务名称，保留关键特征词
  - 示例：Task A Renewal, Document B Application, Permit C Cancellation, Service D Processing
- **slug:** URL友好的短标识，使用连字符连接，全小写
  - 示例：task-a-renewal, document-b-application, permit-c-cancellation
- **命名原则：** 
  - 使用"动词+核心名词"结构（apply/renew/cancel/process/file/submit + 具体对象名称）
  - 保留专有名词和编号（如：9G、AEP、I-Card、Form1234等）
  - 避免过于泛化的词，必须包含能区分该业务的特征词
  - 禁止单独使用：processing、application、service、handling作为完整名称
  - 如果是组合业务，用"and"连接（如：task-a-and-task-b-combo）

**B3. 分析业务属性：**

1. **检查重复：** 对比Index中所有业务名称，判断是否为同一业务
2. **提取文件关系：**
   - 列出此业务需要的输入文件
   - 查询文件生产图谱：有producer → `documents_can_produce`，无producer → `documents_must_provide`
   - 列出此业务产出的输出文件
3. **推导背景前提：** 
   - 地理前提（客户必须在本地 / 可远程 / 特定地点）
   - 关系前提（从业务性质推断必要关系，如：婚姻类业务→已婚，工作类业务→有雇主）
   - 业务前提（需要什么前置状态或文件）
4. **识别部门归属：** 判断去哪里办理，单一部门=独立任务，跨部门=拆分或组合
5. **识别组合关系：** 是否发现"套餐"、"全套"、"一条龙"等固定组合模式
6. **检查歧义：** 业务名是否与已有业务产生歧义

#### 2.4 批量创建新业务文档

对所有标记为"创建新业务"的业务，执行以下步骤：

**步骤1：读取模板文件**

完整读取 `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\VisaServiceFileStructure_template.md`。这是214行的完整模板，包含所有章节结构。

**步骤2：准备内容映射**

将步骤2.3提取的源文件内容映射到模板结构：

**源内容 → 模板章节映射规则：**

- **摘要/描述/简介** → 翻译为英文（如果是中文）→ 填入模板的 `## 摘要` 章节（5-10句话）
- **材料/要求/需求** → 翻译并分类为"必须提供"和"可产出" → 填入 `## 需要准备的文件` 的对应子章节
- **办理流程/步骤 + AI提取的办理步骤** → 翻译（如需）并结构化为有序步骤 → 填入 `## 办理流程` 的"第1步"、"第2步"、"第3步"...
- **价格/费用/成本表格或列表** → 保留表格格式，转换为标准表格 → 填入 `## 价格与费用` 的表格
- **AI提取的注意事项/风险/限制** → 翻译（如需）并分类为"办理限制"、"时间要求"、"风险提示"、"特殊情况" → 填入 `## 注意事项` 的对应子分类
- **AI提取的聊天证据/对话记录** → 保留原文（通常是中文）→ 填入 `## 证据来源`，格式：`**消息 ${ID}** (${时间}): ${原文引用}`
- **数据来源、提取时间、文件路径** → 填入模板底部的 `**文档信息**` 部分

**如果源文件缺少某些信息：**
- 优先从聊天证据中推导和提取
- 如果完全无法获取，在该章节写"No information available in source data"
- 不使用"To be determined"或"Pending verification"等待定占位符

**步骤3：填充frontmatter**

使用步骤2.3的分析结果和提取内容填充：

```yaml
name: "${英文业务名称}"
slug: "${url-friendly-slug}"
type: "solo_task"  # 或 "combo_package"
department: "${部门文件夹名}"

documents_must_provide: ["${文件1}", "${文件2}"]
documents_can_produce:
  - document: "${文件3}"
    producer: "${业务名称}"
    path: "${部门文件夹}/${业务文件名}.md"

documents_output: ["${输出文件1}", "${输出文件2}"]

related_businesses:
  - name: "${业务名称1}"
    path: "${部门文件夹}/${文件名}.md"
    reason: "可产出本业务需要的${文件名}"

aliases: ["${中文原名}", "${中文别名1}", "${中文别名2}"]
updated_at: "${今天日期 YYYY-MM-DD}"
```

**步骤4：填充正文所有章节**

按模板结构逐章节填充，使用步骤2映射的实际内容：

- `## 摘要` - 5-10句英文描述
- `## 背景前提` - 根据业务性质推导的前提条件
- `## 需要准备的文件` - 分类列出必须提供和可产出的文件
- `## 办理后获得的文件` - 列出产出文件及其用途
- `## 办理流程` - 结构化的步骤（第1步、第2步...）
- `## 价格与费用` - 保留源文件的价格表格
- `## 注意事项` - 分类列出（办理限制、时间要求、风险提示、特殊情况）
- `## 常见问题` - 根据证据推导或留空
- `## 证据来源` - 保留中文引用，按消息ID和时间排序

**重要原则：**
- 所有章节必须有实际内容，不允许使用"To be determined"或"Pending verification"等占位符
- 如果源文件某部分内容缺失，在该章节写"No information available in source data"
- 证据来源部分必须保留中文原文

**步骤5：保存文档**

保存到：`D:\AI_Projects\.TelegramChatHistory\Workspace\VisaAchknowlegeBase\${department}\${slug}.md`

确保文件完整，至少100行（包含所有章节结构）。

#### 2.5 批量更新已有业务文档

对所有标记为"更新已有"的业务，执行以下步骤：

1. **读取已有文档：** 从 `VisaAchknowlegeBase\${department}\${slug}.md` 读取完整内容
2. **合并新信息：**
   - 对比新旧内容，识别新增信息
   - 在对应章节追加或更新内容（不要删除已有信息）
   - 如果价格表有新记录，追加到表格中
   - 如果证据来源有新消息，追加到列表末尾
   - 如果发现冲突信息，保留两者并标注来源
3. **更新frontmatter：**
   - 更新 `updated_at` 为今天日期
   - 合并 `aliases` 列表（去重）
   - 更新 `related_businesses`（如有新关联）
4. **保存：** 覆盖原文件

#### 2.6 更新相关业务文档（双向关联）

- 如果新业务产出文件被旧业务需要 → 更新旧业务的 `documents_can_produce` 和 `related_businesses`
- 如果新业务需要文件被旧业务产出 → 更新旧业务的 `related_businesses`

#### 2.7 更新Index.yaml

执行以下操作更新Index.yaml：

1. **检查部门存在性：** 如果新业务的部门在Index.yaml的departments中不存在，创建新部门条目：
   ```yaml
   DepartmentName:
     full_name: "${部门完整名称}"
     folder_path: "${部门文件夹名}/"
     solo_tasks: []
   ```

2. **批量添加新业务：** 将所有新创建的业务添加到对应部门的solo_tasks列表：
   ```yaml
   - name: "${英文业务名}"
     path: "${部门文件夹}/${slug}.md"
     type: "solo_task"
   ```

3. **更新统计信息：**
   - 重新计算 `total_businesses` 为所有部门的solo_tasks总数
   - 更新 `last_updated` 为今天日期（YYYY-MM-DD格式）

4. **保存：** 覆盖原Index.yaml文件

#### 2.8 更新PresetServiceCollections.yaml

**仅当识别到组合关系时：**

创建新组合条目（参考 `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\PresetServiceCollections_template.yaml`）：
```yaml
${组合名称}:
  description, department, type
  documentsRequired（去重后的最底层文件）
  required_tasks, required_paths
```

或更新已有组合。

#### 2.9 更新AmbiguousTermsDictionary.yaml

**如有发现歧义词则启动本步骤：**

打开 `D:\AI_Projects\.TelegramChatHistory\Workspace\VisaAchknowlegeBase\AmbiguousTermsDictionary.yaml`

添加到ambiguous_terms列表：
```yaml
- term: "${ambiguous_term}"
  note: "Could refer to: ${business1}, ${business2}"
```

保存。

#### 2.10 标记文件完成

1. 打开 `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md`
2. 找到当前文件行，将 `[ ]` 改为 `[x]`
3. 保存

#### 2.11 验证标记

1. 重新读取 `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md`
2. 确认当前文件已标记为 `[x]`
3. 如果标记失败，重新执行步骤2.10



---

### 步骤3：继续处理下一个文件

**自动返回步骤2**，处理 `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md` 中下一个状态为 `[ ]` 的文件。

**重复执行**直到所有文件都标记为 `[x]`。

---

## 最终审核阶段

当 `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md` 中所有文件都标记为 `[x]` 后执行：

1. **检查Index完整性** - 所有业务已归类，路径正确
2. **检查双向关联** - 如果A包含B，B也包含A
3. **检查Collections** - documentsRequired计算正确性
4. **补充AmbiguousTermsDictionary** - 扫描所有业务发现遗漏的歧义词

---

## 执行规则

执行过程中必须遵守以下规则：

1. **全局知识同步：** 每处理一个新源文件前，重新读取Index.yaml、PresetServiceCollections.yaml、AmbiguousTermsDictionary.yaml和所有已生成业务文档的frontmatter
2. **双向关联维护：** 当创建或更新业务A与业务B的关联时，必须同时更新A和B两个文档的related_businesses字段
3. **增量更新触发：** 如果新业务的文件产出关系影响已有业务，必须回溯更新所有受影响的已有业务文档
4. **进度验证：** 每次标记文件完成后，立即重新读取AnalysisList.md验证标记成功
5. **证据完整性：** 所有业务信息必须能追溯到源文件的证据来源，证据部分保留中文原文
6. **模板强制执行：** 所有生成的业务文档必须包含模板的全部章节结构，不允许生成简化版或stub文档
7. **内容最小标准：** 每个业务文档至少100行，包含实际内容而非占位符

---

*Execute the complete cleaning workflow by processing ALL files in `D:\AI_Projects\.TelegramChatHistory\Workspace\.WorkPlan\AnalysisList.md` following the defined steps.*
