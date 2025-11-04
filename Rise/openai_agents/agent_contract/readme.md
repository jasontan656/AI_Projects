---

# 🧩 UnifiedCS · Command-based Conversational Orchestration System

*(Unified Conversation System for Rise AI Agents)*

---

## 📘 1. 系统定位（What this is）

**UnifiedCS** 是一套基于 **命令式多阶段执行（Command-driven multi-stage orchestration）** 的 AI 工作流框架。
它让语言模型（LLM）不再“自由生成回答”，而是按阶段执行一系列“系统指令块（Stage Execution Command）”，
每个阶段都是一个 **明确定义的命令任务**，输入/输出由统一契约（contract）约束，
并通过缓存文件（`cached_state.json`）在各阶段之间传递上下文。

该系统由 **Rise AI Orchestrator** 调用，用于政府服务类场景（如签证咨询、文件处理、流程说明等），
具备**低复杂度单机构路径**与**高复杂度多机构路径**两种语义分支。

---

## ⚙️ 2. 系统组成（File Structure）

```
UnifiedCS/
│
├── stage_manifest.yaml          ← 流程路线图（执行顺序与分支逻辑）
├── stage_runtime_contract.md    ← 全局运行契约（输入输出格式与拼接规则）
├── exmaple_cache_states.json    ← 缓存示例（仓库提供样例，实际运行时请生成 cached_state.json）
│
├── prompt_base_system.md        ← Base Persona（角色人格与全局规则）
│
├── prompt_stage1_judgement.md   ← Stage 1：用户询问分类
├── prompt_stage2_agency_catalog.md ← Stage 2：机构检测与复杂度判断
│
├── prompt_stage3-1_templatefill.md     ← Stage 3-1（Low）：语义匹配字典类别（原 category_select）
├── prompt_stege3-1_semantic_analysis.md ← Stage 3-1（High）：多机构语义分析（文件名含拼写 stege）
│
├── prompt_stage3-2_templatefill.md     ← Stage 3-2：服务匹配与模板骨架生成（原 service_select）
└── prompt_stage3-2_semnatic_analysis.md ← Stage 3-2（High）：多机构整合回答（文件名含拼写 semnatic）

```

---

## 🧠 3. 运行机制（How it works）

整个系统通过 **“Stage → Cache → Stage”** 的循环方式工作。
每一轮执行时，AI 并不是“思考上一轮”，而是**读取缓存（cached_state.json）中被注入的上下文数据**，
完成单次任务，再输出结构化 JSON，写回缓存。

### 🔄 流程示意

```
User Input
   ↓
judgement_v1 → agency_detect_v1 → (low) category_select_v1 → service_select_v1
                                ↘ (high) semantic_analysis_v1 → service_select_v1 → multi_agency_service_answer_v1
   ↓
Output to user
```

---

## 🧱 4. 核心文件作用说明

| 文件                              | 功能                | 类比概念                 |
| ------------------------------- | ----------------- | -------------------- |
| **stage_runtime_contract.md**   | 定义每阶段 I/O 拼接与验证标准 | 接口协议（API Contract）   |
| **stage_manifest.yaml**         | 控制阶段顺序与分支路由       | 状态机配置（State Machine） |
| **cached_state.json** / **exmaple_cache_states.json** | 存放上下文、执行结果、阶段输出；仓库内提供 `exmaple_cache_states.json` 作为示例样本 | 内存快照（Runtime Cache）  |
| **prompt_*.md**                 | 每阶段的执行指令（Command）；文件名以仓库当前实际命名为准 | 函数体 / API Handler    |
| **prompt_base_system.md**       | AI 的人格与全局行为规则     | System-level Policy  |

---

## 🔧 5. 数据流说明

1. **User Prompt → Stage1 (`judgement_v1`)**

   * 模型判断是否为有效咨询。
   * 若 `inquiry=false` → 直接回复。
   * 若 `true` → 进入机构检测。

2. **Stage2 (`agency_detect_v1`)**

   * 加载知识库索引，识别机构。
   * 判断 `complexity=low` 或 `high`。

3. **Low Complexity Path**

   * `category_select_v1`：匹配关键词 → 找到对应字典类别。
   * `service_select_v1`：锁定唯一服务（serviceKey），从 cache 生成模板骨架；最终渲染需结合外部流程完成。

4. **High Complexity Path**

   * `semantic_analysis_v1`：多机构语义比对 → 选出主机构。
   * `service_select_v1`：在多机构上下文中选取服务骨架。
   * `multi_agency_service_answer_v1`：整合多机构服务 → 自动生成最终回答（由 `prompt_stage3-2_semnatic_analysis.md` 执行）。

5. **缓存写回**

   * 每阶段输出 JSON 写入 `stages.<stage_id>` 节点。
   * `nextStep` 控制 orchestrator 路由下一阶段。

---

## 📄 6. 缓存结构说明（`cached_state.json`）

> 提示：仓库当前提供 `exmaple_cache_states.json` 作为缓存示例，请在真实运行时按需生成或维护自己的 `cached_state.json`。

简化示意：

```json
{
  "session_id": "uuid",
  "response_id": "r-001",
  "user_prompt": "I want to extend my tourist visa",
  "inquiry": true,
  "stages": {
    "judgement_v1": {"inquiry": true, "nextStep": "agency_detect_v1"},
    "agency_detect_v1": {"agencyDetected": ["bi"], "complexity": "low"},
    "category_select_v1": {"candidates": {"visa_extension": "Tourist visa extension"}},
    "service_select_v1": {
      "serviceSelection": {
        "serviceKey": "TouristVisaExtension",
        "name": "Tourist Visa Extension",
        "path": "BI/services/visa_extension",
        "matchedField": "key",
        "score": 0.92
      },
      "template": {
        "placeholders": {
          "service_name": "{service_name}",
          "requirements": "{requirements}",
          "price": "{price}"
        },
        "rules": "Arrange placeholders contextually."
      },
      "nextStep": "session_end"
    }
  },
  "nextStep": "session_end"
}
```

---

## 🧩 7. AI 执行视角（What the model actually sees）

每一阶段执行时，AI 接收到的指令由 Orchestrator 拼接：

```
[BASE SYSTEM BLOCK]
+ 
{{input.cached_state}}   ← 运行态上下文（来自 cached_state.json）
+
Stage Command (prompt_stageX.md)
```

模型执行后输出结构化 JSON，
由 orchestrator 验证 → 写回 → 路由下一阶段。

---

## 🚀 8. 为什么这套体系有效

| 设计目标      | 达成方式                                                 |
| --------- | ---------------------------------------------------- |
| **可控**    | 每阶段输出固定结构 JSON，无幻觉，无越权生成。                            |
| **可追踪**   | 每次执行写入缓存（带 `session_id`、`response_id`）。              |
| **可插拔**   | 替换某一阶段文件即可更换任务逻辑。                                    |
| **可扩展**   | 支持复杂分支（low/high complexity）、人工审核、模板扩充。               |
| **多模型兼容** | 通过统一契约，任何支持 function call / response API 的 LLM 都能执行。 |

---

## 🧠 9. 场景示例

**用户问：** “How much to extend a tourist visa in the Philippines?”
**系统内部执行链：**

```
judgement_v1 → agency_detect_v1(BI, low)
→ category_select_v1 → service_select_v1（输出模板骨架）
→ orchestrator 渲染输出 → 回复价格
```

**最终输出：**

```json
{
  "assistantReply": "A 2-month tourist visa extension normally costs about PHP 3,030. You may visit the Bureau of Immigration office to file it in person.",
  "nextStep": "session_end"
}
```

---

## 📦 10. 开发者快速上手

1. 编辑各 `prompt_stage*.md` 以修改逻辑或输出格式。
2. 确保 `stage_manifest.yaml` 路径正确、分支映射无误。
3. 在 Orchestrator 中循环执行：

   ```python
   while state["nextStep"] != "session_end":
       stage = state["nextStep"]
       directive = load_prompt(stage)
       payload = assemble_prompt(state, directive)
       result = call_model(payload)
       state = merge_state(state, result)
   ```
4. 所有执行过程都应遵守 `stage_runtime_contract.md`。

---

## ✅ 11. 总结一句话

> UnifiedCS 是一个 **可编排、可解释、可重放** 的命令式 LLM 执行系统。
> 它将“聊天”转化为“程序”，
> 每一步都是有输入、有约束、有输出的确定性行为。

---

是否要我接着帮你写一个「开发者快速测试用 orchestrator.py（含 load → assemble → call → update → loop）」？
那样这份 README 就能配成一个**完整可跑 Demo 套件**。
