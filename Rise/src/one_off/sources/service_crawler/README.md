# ServiceCrewler Toolkit

## 当前状态
- 目录位置：`D:\AI_Projects\Rise\shared_utility\service_crawler`
- 已迁入脚本：
  1. `fetch_visas.py` – 使用 Playwright/HTTP 抓取政府网站签证/服务入口并生成 `visas.json`。
  2. `list_visas.py`（保留在原仓库，可选） – 快速查看 `visas.json` 抓取结果。
  3. `fetch_forms.py` – 抓取每个服务页面的正文、附件、表格与 checklist。
  4. `rename_attachments.py` – LLM+规则重命名附件，保证后续处理使用统一命名。
  5. `dedupe_pdfs.py` – 清理重复/历史附件。
  6. `build_pdfsum.py` – 解析附件/PDF 并生成 `PDFSUM` 摘要。
  7. `rewrite_md.py` – 按 `mdtemplate` 重写业务说明 Markdown，统一结构与 placeholder。
  8. `modify_yaml.py` – 批量修复/补齐 Markdown 或 YAML 中的字段（slug、别名、占位符等）。
  9. `update_prices.py` – 抓取/整合价格表，生成 `BI_price`/`pricetemp` 等中间数据。
  10. `convert_yaml.py` – 将最终 Markdown + PDFSUM/价格转成 YAML（骨架+字段对象）。
  11. `build_pdfsum.py` – 生成 PDFSUM；`show_info.py` – 输出模板/提示词信息；
  12. 配置/资源：`service_dirs.json`、`template_head.txt`、`visas.json`、`service_yaml_template.yaml`（仍在 Workspace 目录）。

## 目标能力
打造一条可复用的链路工具，支持“指定任意政府网站 → 结构化采集 → 重写 → YAML 骨架”闭环，具体阶段：
1. **站点解析**：Playwright/HTTP 抓取服务导航、详情与价目信息；可配置目标 URL 列表。
2. **目录初始化**：为每个服务创建标准目录+占位 Markdown（套用 `mdtemplate`），并复制模板头部 placeholder。
3. **数据采集**：按服务运行 Playwright，抓正文、价目、附件，落地到本地临时 TXT/附件目录。
4. **附件处理**：运行 `rename_attachments.py` → `dedupe_pdfs.py`，确保附件规范且无重复。
5. **结构化重写**：
   - `rewrite_md.py`：将抓取内容写入模板化 Markdown。
   - `build_pdfsum.py` + `modify_yaml.py`：解析附件、生成 PDFSUM 并为 Markdown 补齐字段。
6. **润色与补充**：调用 LLM 根据 PDFSUM/抓取结果对 Markdown 做增量补充或校验。
7. **YAML 输出**：`convert_yaml.py` 读入最终 Markdown、PDFSUM、价格信息，输出符合骨架的 YAML，用于客服占位符替换。

## 待对齐节点与挑战
1. **配置解耦**：目前脚本仍写死 `D:/AI_Projects/TelegramChatHistory/Workspace/...` 路径；后续需要通过配置文件/环境变量注入，便于切换站点或工作区。
2. **Playwright 调度**：`fetch_forms.py`/`fetch_visas.py` 尚针对 BI 网站编写，需要抽象为“站点配置 + 选择器 + URL 规则”才能在新站点复用。
3. **目录自动化**：现阶段由人工创建服务目录、复制模板；需要新增脚本（或扩展 `fetch_forms.py`）自动生成 `service_dirs.json` + 目录骨架。
4. **LLM Prompt 模块化**：`template_head.txt` 仍是 BI 场景提示词，后续需参数化（站点名称、语言、字段映射）。
5. **价格流**：`update_prices.py` 专注 BI Citizens Charter，需要引入站点可配置的抓取器或留接口给手动导入。
6. **日志与断点**：原脚本多依赖终端输出，环节较多时需要统一 Task/Log 机制、失败重试与断点续跑。
7. **包装与调用**：最终需构建 orchestrator（批处理/CLI）串联上述脚本，并接受“站点配置 + 目标目录”作为输入。

## 下一步建议
- 先为新目录下的脚本加入通用 `settings.json`/`.env` 读取逻辑，集中管理路径、站点URL、Playwright profile 等。
- 为抓取阶段补充“目录初始化脚本”（自动按配置创建服务目录、占位 Markdown、`service_dirs.json`）。
- 计划将整条链路写成 `invoke.py`/CLI（或 Prefect/Invoke 任务），按上述顺序依次运行并记录状态。
- 针对不同政府站点，新增 `site_profiles/xxx.yaml`，定义 URL 模式、选择器、价目解析规则等，抓取脚本按 profile 执行。
