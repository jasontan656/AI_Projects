#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
服务知识库增量式关联构建脚本

功能：
- 扫描 KB/services 目录下的所有 .md 文件
- 使用 AnalysisList.md 维护处理进度
- 逐个处理文件，调用 AI 进行整合和关联推理
- 执行 AI 返回的 JSON 指令，更新知识库
- 使用 rich 美化终端输出
"""

import os
import sys
import json
import yaml
import time
import re
import math
import signal
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live

# 全局中断标志
interrupted = False

def signal_handler(sig, frame):
    """处理 Ctrl+C 信号，立即中断"""
    global interrupted
    interrupted = True
    console = Console()
    console.print("\n\n[bold yellow]收到中断信号，正在终止...[/bold yellow]")
    console.print("[dim]如果 API 调用正在进行，将在超时后终止[/dim]")
    logger.info("收到用户中断信号，脚本终止")
    sys.exit(0)
from rich.layout import Layout
from rich import box

# 初始化
console = Console()
load_dotenv()

# 配置日志系统
def setup_logger():
    """配置日志记录器"""
    # 日志文件路径（与脚本同目录）
    script_dir = Path(__file__).parent
    log_file = script_dir / f"process_kb_services_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 创建 logger
    logger = logging.getLogger('kb_processor')
    logger.setLevel(logging.DEBUG)
    
    # 文件处理器（详细日志）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=50*1024*1024,  # 50MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 详细格式
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    # 记录启动信息
    logger.info("="*80)
    logger.info(f"知识库处理脚本启动 - 日志文件: {log_file.name}")
    logger.info("="*80)
    
    return logger

logger = setup_logger()

# 配置路径
BASE_DIR = Path(__file__).parent.parent.parent
KB_SERVICES_DIR = BASE_DIR / ".TelegramChatHistory" / "KB" / "services"
WORKSPACE_DIR = BASE_DIR / ".TelegramChatHistory" / "Workspace"
WORKPLAN_DIR = WORKSPACE_DIR / ".WorkPlan"
OUTPUT_DIR = WORKSPACE_DIR / "VisaAchknowlegeBase"

ANALYSIS_LIST = WORKPLAN_DIR / "AnalysisList.md"
TEMPLATE_FILE = WORKPLAN_DIR / "VisaServiceFileStructure_template.md"
RELATION_FILE = WORKPLAN_DIR / "StructureRelation.yaml"
INDEX_FILE = OUTPUT_DIR / "Index.yaml"
COLLECTIONS_FILE = OUTPUT_DIR / "PresetServiceCollections.yaml"
AMBIGUOUS_FILE = OUTPUT_DIR / "AmbiguousTermsDictionary.yaml"

# 日志目录
LOG_DIR = WORKPLAN_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# OpenAI 配置
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL_MINI", "gpt-4o-mini-2024-07-18")

# 多轮与Token硬编码限制
MAX_MULTI_ROUNDS = 3  # 选择→补充（可选）→最终
SELECTION_LIMIT_PER_ROUND = 5  # 每轮最多可选文件数
SELECTION_TOTAL_LIMIT = 10     # 全流程最多可选文件总数
TOKEN_CAP = 390_000            # 发送前估算token上限，超过则报错停止


class AnalysisListManager:
    """管理 AnalysisList.md 的读写"""
    
    def __init__(self, list_file: Path):
        self.list_file = list_file
        self.processed_files = set()
        self.pending_files = []
        self._load()
    
    def _load(self):
        """加载 AnalysisList.md"""
        if not self.list_file.exists():
            console.print("[yellow]AnalysisList.md 不存在，将创建新文件[/yellow]")
            return
        
        content = self.list_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("[x]"):
                # 已处理
                file_path = line[3:].strip()
                self.processed_files.add(file_path)
            elif line.startswith("[ ]"):
                # 待处理
                file_path = line[3:].strip()
                self.pending_files.append(file_path)
    
    def get_next_file(self) -> Optional[str]:
        """获取下一个待处理文件"""
        if self.pending_files:
            return self.pending_files[0]
        return None
    
    def mark_completed(self, file_path: str):
        """标记文件为已完成"""
        content = self.list_file.read_text(encoding="utf-8")
        
        # 替换 [ ] 为 [x]
        pattern = re.escape(f"[ ] {file_path}")
        replacement = f"[x] {file_path}"
        content = content.replace(f"[ ] {file_path}", f"[x] {file_path}")
        
        self.list_file.write_text(content, encoding="utf-8")
        
        # 更新内存状态
        if file_path in self.pending_files:
            self.pending_files.remove(file_path)
        self.processed_files.add(file_path)
    
    def add_new_file(self, file_path: str):
        """添加新文件到列表"""
        content = self.list_file.read_text(encoding="utf-8")
        
        # 在文件清单部分末尾添加
        new_line = f"[ ] {file_path}\n"
        
        # 找到最后一个文件行的位置
        lines = content.split("\n")
        insert_pos = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("[") and ".md" in lines[i]:
                insert_pos = i + 1
                break
        
        lines.insert(insert_pos, f"[ ] {file_path}")
        content = "\n".join(lines)
        
        self.list_file.write_text(content, encoding="utf-8")
        self.pending_files.append(file_path)
    
    def sync_with_directory(self, directory: Path):
        """同步目录中的文件到列表，每次只添加一个新文件
        
        Returns:
            (added_file, remaining_new_count, deleted_count)
        """
        all_files = list(directory.glob("*.md"))
        all_file_paths = {str(f.resolve()) for f in all_files}
        
        known_files = self.processed_files | set(self.pending_files)
        
        # 找出新文件和已删除文件
        new_files = sorted(all_file_paths - known_files)
        deleted_files = known_files - all_file_paths
        
        # 移除已删除的文件
        if deleted_files:
            for deleted in deleted_files:
                if deleted in self.pending_files:
                    self.pending_files.remove(deleted)
                self.processed_files.discard(deleted)
            self._save()
        
        # 只添加一个新文件
        added_file = None
        if new_files:
            added_file = new_files[0]
            self.add_new_file(added_file)
        
        return (added_file, len(new_files), len(deleted_files))


class KnowledgeBaseBuilder:
    """知识库构建器"""
    
    def __init__(self):
        self.completed_businesses = {}  # {slug: path}
        self._load_completed_businesses()
    
    def _load_completed_businesses(self):
        """加载已完成的业务列表"""
        if not OUTPUT_DIR.exists():
            return
        
        for dept_dir in OUTPUT_DIR.iterdir():
            if dept_dir.is_dir() and not dept_dir.name.startswith("."):
                for md_file in dept_dir.glob("*.md"):
                    # 提取 slug
                    slug = md_file.stem
                    rel_path = md_file.relative_to(OUTPUT_DIR)
                    self.completed_businesses[slug] = str(rel_path)
    
    def _format_business_documents(self) -> str:
        """格式化所有已完成业务的完整文档内容"""
        if not self.completed_businesses:
            return "（暂无已生成业务）"
        
        formatted_docs = []
        for slug, path in self.completed_businesses.items():
            file_path = OUTPUT_DIR / path
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    formatted_docs.append(f"""
{'='*80}
业务文件: {path}
Slug: {slug}
{'='*80}

{content}

""")
                except Exception as e:
                    formatted_docs.append(f"[读取失败: {path} - {e}]\n")
        
        return "\n".join(formatted_docs)
    
    def get_business_summaries(self) -> List[Dict]:
        """获取已完成业务的摘要信息"""
        summaries = []
        
        for slug, rel_path in self.completed_businesses.items():
            full_path = OUTPUT_DIR / rel_path
            if not full_path.exists():
                continue
            
            try:
                content = full_path.read_text(encoding="utf-8")
                # 提取 frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        
                        # 检查frontmatter类型
                        if not isinstance(frontmatter, dict):
                            console.print(f"[dim]跳过无效frontmatter: {rel_path}[/dim]")
                            continue
                        
                        # 安全提取documents_can_produce
                        can_produce_docs = []
                        can_produce = frontmatter.get("documents_can_produce", [])
                        if isinstance(can_produce, list):
                            for item in can_produce:
                                if isinstance(item, dict):
                                    doc = item.get("document")
                                    if doc:
                                        can_produce_docs.append(doc)
                        
                        # 安全提取documents_must_provide
                        must_provide = frontmatter.get("documents_must_provide", [])
                        if not isinstance(must_provide, list):
                            must_provide = []
                        
                        # 安全提取documents_output
                        output_docs = frontmatter.get("documents_output", [])
                        if not isinstance(output_docs, list):
                            output_docs = []
                        
                        summaries.append({
                            "name": frontmatter.get("name", ""),
                            "slug": slug,
                            "department": frontmatter.get("department", ""),
                            "input_files": must_provide + can_produce_docs,
                            "output_files": output_docs,
                            "path": str(rel_path)
                        })
            except Exception as e:
                error_msg = f"读取业务文档失败: {rel_path} - {e}"
                console.print(f"[red]{error_msg}[/red]")
                logger.error(error_msg)
                logger.debug(f"文件路径: {full_path}")
                logger.debug(f"Slug: {slug}")
        
        return summaries
    
    def build_prompt(self, source_file: Path) -> str:
        """构建给 AI 的提示词"""
        
        # 读取所有必要文件
        source_content = source_file.read_text(encoding="utf-8")
        template_content = TEMPLATE_FILE.read_text(encoding="utf-8")
        relation_content = RELATION_FILE.read_text(encoding="utf-8")
        
        index_content = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else "# Empty"
        collections_content = COLLECTIONS_FILE.read_text(encoding="utf-8") if COLLECTIONS_FILE.exists() else "# Empty"
        ambiguous_content = AMBIGUOUS_FILE.read_text(encoding="utf-8") if AMBIGUOUS_FILE.exists() else "# Empty"
        
        business_summaries = self.get_business_summaries()
        
        prompt = f"""# 任务：整合源文件并构建业务关联

**重要：所有生成的业务文档内容必须使用英文。**

## 当前源文件
文件名: {source_file.name}
路径: {source_file}

{source_content}

## 模板
{template_content}

## 关系推理规则引擎
{relation_content}

重点关注以下规则：
- business_hierarchy: 业务层次结构
- file_production_chain: 文件生产链机制
- background_requirements.reasoning_pathway: 背景推理三步法
- optional_to_required_conversion: Optional转Required机制
- document_types: 文件类型和可消耗属性

## 全局知识

### Index.yaml
{index_content}

### PresetServiceCollections.yaml
{collections_content}

### AmbiguousTermsDictionary.yaml
{ambiguous_content}

### 已完成业务文档（{len(business_summaries)}个）

以下是所有已生成的业务文档完整内容，用于判断新业务是否重复、建立文件生产关系：

{self._format_business_documents()}

---

## 执行任务

### 步骤0：业务识别与重复检测

**A. 检查是否与已有业务重复：**

查看"已完成业务摘要"列表，判断源文件描述的业务是否已存在：

1. **完全相同**：业务名称、别名、描述基本一致 → 更新已有文档，不创建新文档
2. **高度相似**：业务名称相似（如"13A Visa Processing"和"13A Marriage Visa Application"都是13A签证）→ 判断是否同一业务的不同叫法，还是确实有细微区别
3. **完全不同**：明确是新业务 → 继续步骤B

**判断标准：**
- 比对业务名称、aliases、summary内容
- 检查input_files和output_files是否高度重叠
- 如果相似度>80%，倾向于更新而非创建

**B. 判断源文件包含几个独立业务：**

**拆分判断标准（满足任一条件即应拆分）：**

1. **命名判断：** 业务名称用"and"、"及"、"和"、"plus"连接多个业务名
   - 示例：`"1 Month Extension and ECC Filing"` → 拆分为2个业务
   - 示例：`"Visa Application and Payment"` → 拆分为2个业务

2. **时序依赖判断：** 证据或描述中明确提到"先...再..."、"first...then..."、"完成X后才能Y"
   - 示例：`"You have to report first 1 month extension to finish. Next is you start to report for ECC."` → 拆分为2个业务

3. **文件生产链判断：** 业务A的输出明确是业务B的必需输入，且两者可独立办理
   - 示例：A产出"completion report" → B需要"completion report" → 拆分为2个独立业务

4. **部门判断：** 涉及不同部门办理的事项必须拆分
   - 示例：移民局业务 + 司法部业务 → 拆分为2个业务

5. **独立性判断：** 每个部分都可以单独作为一个业务被客户购买
   - 示例：客户可以只办延期不办ECC，或已有延期只办ECC → 应拆分

**不拆分的情况：**
- 单一流程的多个步骤（如：提交申请→审核→领取）
- 同一业务的不同材料准备（如：准备护照、准备照片、准备表格）
- 紧密绑定的业务包（如：新生儿出生证明+PSA认证，两者必须一起办理且不可分割）

**重要说明：**
- 所有从源文件提取的业务都应该是`solo_task`（独立业务）
- 即使业务需要很多前置文件，它仍然是独立业务
- 集合服务（composite_business）不是从源文件识别的，而是后期通过PresetServiceCollections定义的
- 例如："13A签证申请"是solo_task，但"13A签证全套服务包"（包含PSA认证+NBI+体检+签证申请）才是composite_business

**输出：**
- `businesses_identified`: 识别出的独立业务数量（全部是solo_task）
- `duplicates_found`: 发现的重复业务列表（需要更新而非创建）
- 对每个识别出的业务，分别执行步骤1-4

**拆分方法：**
- 为每个独立业务生成独立的slug、name和完整文档
- 在frontmatter中建立related_businesses双向关联
- 在documents_can_produce中标注生产者路径

### 步骤1：整合每个业务的内容

**注意：如果步骤0识别出多个业务，需要为每个业务分别整合内容。**

源文件包含多个数据来源段落，整合单个业务的所有信息：
- 提取该业务相关的"需要文件" → input_files列表
- 提取该业务相关的"产出文件" → output_files列表
- 提取该业务相关的办理步骤 → 流程章节
- 提取该业务相关的价格记录 → 价格表
- 提取该业务相关的注意事项 → 分类到模板的4个子类
- 保留该业务相关的聊天证据（中文原文）→ 证据来源章节

**如果源文件描述的是多个业务：**
- 根据上下文语义将内容分配到对应业务
- 如果某段证据同时涉及两个业务，可在两个业务文档中都引用
- 时序相关的证据（"先A再B"）应该在两个业务中都体现，说明依赖关系

### 步骤2：应用关系规则推理（对每个业务）
基于StructureRelation.yaml的规则：

**文件生产关系推理：**
- 对input_files中的每个文件，查询已完成业务库
- 如果有业务产出此文件 → documents_can_produce（含producer路径）
- 如果无业务产出 → documents_must_provide
- 自动建立related_businesses双向关联

**背景前提推理（三步法）：**
- 地理前提：根据业务性质判断客户是否必须在菲律宾
- 关系前提：从业务名称推断必要关系（结婚/雇佣/家庭等）
- 业务前提：从input_files推断必要前置状态

**识别Mandatory关联：**
- 如果output_files被已有业务需要 → 生成回溯更新指令

**提取业务描述：**
- 从Summary章节提取前150个字符作为description
- 用于Index.yaml的业务摘要显示

### 步骤3：生成完整业务文档（对每个业务）

按模板填充所有章节，确保：
- frontmatter完整（所有字段）
- 所有章节有实际内容（不使用占位符）
- 至少80行（如果是从多业务拆分出来的，内容可能较少，但必须完整）
- 证据来源保留中文原文
- 如果是拆分业务，在related_businesses中明确标注依赖关系

**Frontmatter 格式要求（严格遵守）：**
1. 第1行必须是 `---`（开始标记）
2. 第2-N行是 YAML 键值对（必须包含所有模板字段）
3. 最后一行必须是 `---`（结束标记）
4. 结束标记后必须有空行
5. 然后才是 Markdown 正文（以 `# 业务名称` 开头）
6. **禁止在 frontmatter 内出现 Markdown 标题（#）或段落文本**
7. 如果某个字段为空，使用空数组 `[]` 或空字符串 `""`，不要省略

**命名规范（极其重要）：**
- name：使用清晰的英文动词+名词结构
  - 好：`"1 Month Extension"`, `"ECC Filing"`, `"Tourist Visa Renewal"`
  - 坏：`"Processing"`, `"Application"`, `"Service"` (过于泛化)
- slug：与name对应的URL友好格式
  - 好：`"1-month-extension"`, `"ecc-filing"`, `"tourist-visa-renewal"`
  - 坏：`"processing"`, `"application-service"`, `"visa"` (无法区分)
- 保留专有名词：9G, AEP, ECC, I-Card, NBI等
- 如果业务有编号或特定期限，必须保留：1-month, 6-month, 9a, 9g等

### 步骤4：输出JSON指令

**重要：**
- 如果识别出N个业务，生成N个create_business指令
- 为拆分出的业务建立双向关联（通过related_businesses）
- 在combinations_detected中记录识别出的业务关系

输出格式：
```json
{{
  "source_file": "源文件名",
  "businesses_identified": 2,  // 识别出的业务数量
  "businesses_created": ["business-1-slug", "business-2-slug"],  // 创建的业务slug列表
  "relations_updated": 3,  // 更新的关系数量
  "combinations_detected": [  // 识别出的业务组合或依赖关系
    "business-1-slug requires completion before business-2-slug"
  ],
  "actions": [
    {{
      "action": "create_business_file",
      "department": "BureauOfImmigration",
      "slug": "business-1-slug",
      "name": "Business 1 Name",
      "business_name": "Business 1 Name",
      "content": "---\\nname: \\"Business 1 Name\\"\\nslug: \\"business-1-slug\\"\\ntype: \\"solo_task\\"\\ndepartment: \\"BureauOfImmigration\\"\\n\\ndocuments_must_provide: [\\"file1\\", \\"file2\\"]\\ndocuments_can_produce: []\\ndocuments_output: [\\"output1\\"]\\nrelated_businesses: []\\naliases: []\\nupdated_at: \\"2025-10-18\\"\\n---\\n\\n# Business 1 Name\\n\\n## Summary\\n\\n完整内容..."
    }},
    {{
      "action": "create_business_file",
      "department": "BureauOfImmigration",
      "slug": "business-2-slug",
      "name": "Business 2 Name",
      "business_name": "Business 2 Name",
      "content": "完整的markdown文档内容"
    }},
    {{
      "action": "update_business_file",  // 如果需要更新已有业务
      "path": "BureauOfImmigration/existing-business.md",
      "business_name": "Existing Business",  // 添加此字段用于报告
      "operations": [
        {{
          "section": "related_businesses",
          "operation": "append",
          "value": {{
            "name": "Business 1 Name",
            "path": "BureauOfImmigration/business-1-slug.md",
            "reason": "关联原因说明"
          }}
        }}
      ]
    }},
    {{
      "action": "update_index",
      "department": "BureauOfImmigration",
      "add_tasks": [
        {{
          "name": "Business 1 Name",
          "slug": "business-1-slug",
          "path": "BureauOfImmigration/business-1-slug.md",
          "type": "solo_task",
          "description": "Brief 150-200 char summary from the Summary section"
        }},
        {{
          "name": "Business 2 Name",
          "slug": "business-2-slug",
          "path": "BureauOfImmigration/business-2-slug.md",
          "type": "solo_task",
          "description": "Brief 150-200 char summary from the Summary section"
        }}
      ]
    }}
  ]
}}
```

**关键提醒：**
1. **优先检查重复**：先查看已完成业务文档，判断是更新还是创建
2. 如果发现重复业务，使用update_business_file而非create_business_file
3. 如果拆分，为每个业务生成独立完整的文档
4. **所有业务都是solo_task**：不要设置type为composite_business，集合服务由PresetServiceCollections定义
5. **Index结构**：add_tasks必须包含name、slug、path、type、description（从Summary章节提炼150-200字符的简介）
6. 每个action必须包含business_name字段用于终端报告
7. **所有业务文档内容必须使用英文撰写（除了证据来源的中文引用）**

**Content 字段格式要求（极其重要）：**
- content 必须是完整的 Markdown 文档字符串
- 必须以 `---` 开头（frontmatter 开始）
- frontmatter 必须包含所有模板字段（即使为空也要写 `[]` 或 `""`）
- frontmatter 必须以 `---` 结尾（不要忘记！）
- frontmatter 和正文之间必须有空行
- 正文才开始 `# 业务名称`
- **绝对禁止在 frontmatter 的两个 `---` 之间出现 Markdown 标题或段落文本**

**正确示例**：
```
---
name: "Example"
slug: "example"
type: "solo_task"
department: "Dept"

documents_must_provide: ["file1"]
documents_can_produce: []
documents_output: []
related_businesses: []
aliases: []
updated_at: "2025-10-18"
---

# Example

## Summary
完整内容...
```

请直接输出JSON，不要包含其他文字。
"""
        
        return prompt

    # 新增：估算token（粗略：约4字符=1token）
    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        # 使用简单近似，避免引入额外依赖
        return max(1, math.ceil(len(text) / 4))

    # 新增：选择阶段提示（仅目录级信息，不拼接所有业务正文）
    def build_selection_prompt(self, source_file: Path) -> str:
        source_content = source_file.read_text(encoding="utf-8")
        template_content = TEMPLATE_FILE.read_text(encoding="utf-8")
        relation_content = RELATION_FILE.read_text(encoding="utf-8")

        index_content = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else "# Empty"
        collections_content = COLLECTIONS_FILE.read_text(encoding="utf-8") if COLLECTIONS_FILE.exists() else "# Empty"
        ambiguous_content = AMBIGUOUS_FILE.read_text(encoding="utf-8") if AMBIGUOUS_FILE.exists() else "# Empty"

        business_summaries = self.get_business_summaries()

        prompt = f"""# Round 1: Selection and Planning Only

You are a knowledge base construction assistant. Output only valid JSON. Do not create or update files in this round.

Task: Read the source file and the schemas to decide which existing business documents (by path) you need full content for to determine whether to UPDATE existing or CREATE new business documents. You must obey the selection limits strictly.

Limits:
- max_per_round: {SELECTION_LIMIT_PER_ROUND}
- max_total: {SELECTION_TOTAL_LIMIT}

Required JSON output format (business_name is required for each future action candidate you have in mind; you are not outputting actions in this round, but you must plan clear names for later use):
{{
  "source_file": "{source_file.name}",
  "decision_overview": {{
    "tentative_action": "create_or_update_or_split",
    "businesses_identified_estimate": 1,
    "notes": "brief rationale"
  }},
  "requested_business_files": [
    {{ "path": "Department/slug.md", "reason": "similarity or dependency" }}
  ],
  "limit_ack": {{ "max_files_allowed": {SELECTION_LIMIT_PER_ROUND} }}
}}

Source file:
{source_file}

Content:
{source_content}

Template:
{template_content}

Relation Rules (StructureRelation.yaml):
{relation_content}

Global Index (catalog only):
{index_content}

PresetServiceCollections (optional):
{collections_content}

AmbiguousTermsDictionary (optional):
{ambiguous_content}

Existing business summaries (catalog view, no full text):
{json.dumps(business_summaries, ensure_ascii=False)}

Important:
- Only return JSON with the fields described above.
- Do not include any business full content in this round.
- Choose at most {SELECTION_LIMIT_PER_ROUND} items.
 - When the source describes multiple independent tasks (e.g. "X and Y" or sequenced dependencies), plan to split into multiple solo_task documents. Use clear English names and slugs.
"""
        return prompt

    # 工具：从路径推断部门
    @staticmethod
    def _derive_department_from_path(path_str: str) -> Optional[str]:
        try:
            parts = Path(path_str).as_posix().split("/")
            return parts[0] if parts and parts[0] else None
        except Exception:
            return None

    # 工具：从content的frontmatter提取department/slug
    @staticmethod
    def _extract_frontmatter_fields(content: str) -> Tuple[Optional[str], Optional[str]]:
        if not content or not content.startswith("---"):
            return (None, None)
        try:
            lines = content.split("\n")
            end = -1
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    end = i
                    break
            if end == -1:
                return (None, None)
            fm_text = "\n".join(lines[1:end])
            fm = yaml.safe_load(fm_text)
            if isinstance(fm, dict):
                return (fm.get("department"), fm.get("slug"))
        except Exception:
            pass
        return (None, None)

    # 新增：处理阶段提示（仅拼接第一轮选中的若干业务正文，可在第二轮请求更多）
    def build_processing_prompt(self, source_file: Path, selected_paths: List[str], current_round: int, total_selected: int) -> str:
        source_content = source_file.read_text(encoding="utf-8")
        template_content = TEMPLATE_FILE.read_text(encoding="utf-8")
        relation_content = RELATION_FILE.read_text(encoding="utf-8")

        index_content = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else "# Empty"
        collections_content = COLLECTIONS_FILE.read_text(encoding="utf-8") if COLLECTIONS_FILE.exists() else "# Empty"
        ambiguous_content = AMBIGUOUS_FILE.read_text(encoding="utf-8") if AMBIGUOUS_FILE.exists() else "# Empty"

        # 读取被选择的业务正文
        assembled_docs: List[str] = []
        for rel_path in selected_paths:
            file_path = OUTPUT_DIR / rel_path
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    assembled_docs.append(
                        f"\n{'='*80}\nSelected business file: {rel_path}\n{'='*80}\n\n{content}\n"
                    )
                except Exception as e:
                    assembled_docs.append(f"[读取失败: {rel_path} - {e}]\n")
            else:
                assembled_docs.append(f"[未找到: {rel_path}]\n")

        selected_docs_block = "\n".join(assembled_docs)

        # 第2轮允许再要更多；第3轮必须给最终actions。
        allow_additional = current_round < MAX_MULTI_ROUNDS

        guidance = (
            "You may request additional files by returning 'additional_requested_files' (list of paths) if essential to decide create vs update, strictly up to the remaining total limit. Do NOT output actions if you request more."
            if allow_additional else
            "This is the final round. You MUST output final actions. Do NOT request more files."
        )

        remaining_total = max(0, SELECTION_TOTAL_LIMIT - total_selected)

        prompt = f"""# Round {current_round}: Processing

You are a knowledge base construction assistant. Output only valid JSON.

Goal: Using the source file and ONLY the selected existing business documents below, decide whether to UPDATE existing business files or CREATE new ones, then output executable actions (create_business_file, update_business_file, update_index, etc.).

If and only if the selected documents are insufficient and this is not the final round, you may ask for more using 'additional_requested_files' with at most {SELECTION_LIMIT_PER_ROUND} items, and respecting the total limit remaining: {remaining_total}. {guidance}

Expected JSON when producing final actions (each action must include a human-readable business_name for reporting):
{{
  "source_file": "{source_file.name}",
  "businesses_identified": 1,
  "businesses_created": [],
  "relations_updated": 0,
  "combinations_detected": [],
  "actions": [ ... ]
}}

Source file:
{source_file}

Content:
{source_content}

Template:
{template_content}

Relation Rules (StructureRelation.yaml):
{relation_content}

Global Index:
{index_content}

PresetServiceCollections (optional):
{collections_content}

AmbiguousTermsDictionary (optional):
{ambiguous_content}

Selected business documents (full text provided, count={len(selected_paths)}):
{selected_docs_block}

Rules:
- All generated business documents must be in English (except evidence quotes).
- Prefer update over create when similarity is high.
- Respect the frontmatter and content format constraints from the template.
- If this is the final round, do not request more files.
 - If the source implies multiple independent businesses, split into multiple solo_task outputs and provide separate actions with distinct business_name and slug.
"""
        return prompt
    
    def call_ai(self, prompt: str) -> Dict:
        """调用 AI API"""
        global interrupted
        
        # 检查是否已经被中断
        if interrupted:
            raise KeyboardInterrupt("用户中断")
        
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a knowledge base construction assistant. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                timeout=300.0  # 5分钟超时，确保可以被中断
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 添加 token 使用信息
            result["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            return result
        
        except Exception as e:
            error_msg = f"AI API 调用失败: {e}"
            console.print(f"[red]{error_msg}[/red]")
            logger.error(error_msg)
            logger.debug(f"Prompt 长度: {len(prompt)} 字符")
            raise
    
    def execute_actions(self, actions: List[Dict]):
        """执行 AI 返回的指令"""
        for action in actions:
            action_type = action.get("action")
            
            try:
                # 兼容旧格式和新格式
                if action_type in ["create_business", "create_business_file"]:
                    self._create_business(action)
                elif action_type in ["update_business", "update_business_file"]:
                    self._update_business(action)
                elif action_type == "update_index":
                    self._update_index(action)
                elif action_type == "update_collections":
                    self._update_collections(action)
                elif action_type == "update_ambiguous":
                    self._update_ambiguous(action)
                else:
                    console.print(f"[yellow]未知指令类型: {action_type}[/yellow]")
            
            except Exception as e:
                error_msg = f"执行指令失败 ({action_type}): {e}"
                console.print(f"[red]{error_msg}[/red]")
                logger.error(error_msg)
                logger.debug(f"Action 详情: {json.dumps(action, ensure_ascii=False)}")
    
    def _validate_and_fix_frontmatter(self, content: str, filename: str) -> str:
        """验证并修复markdown文档的frontmatter格式
        
        常见问题：
        1. frontmatter没有正确关闭（缺少第二个---）
        2. frontmatter和正文之间缺少空行
        3. frontmatter中的YAML格式错误
        """
        if not content.startswith("---"):
            console.print(f"[yellow]警告: {filename} 没有frontmatter，跳过验证[/yellow]")
            return content
        
        # 查找frontmatter的结束位置
        lines = content.split("\n")
        frontmatter_end = -1
        
        for i in range(1, len(lines)):
            # 寻找第二个 ---
            if lines[i].strip() == "---":
                frontmatter_end = i
                break
        
        if frontmatter_end == -1:
            # 找不到结束符，可能是AI把正文也放在frontmatter里了
            console.print(f"[yellow]警告: {filename} frontmatter未正确关闭，尝试修复...[/yellow]")
            
            # 找到第一个以 # 开头的行（markdown标题）
            content_start = -1
            for i in range(1, len(lines)):
                if lines[i].strip().startswith("#"):
                    content_start = i
                    break
            
            if content_start == -1:
                console.print(f"[red]错误: {filename} 无法找到正文开始位置，使用原内容[/red]")
                return content
            
            # 在标题前插入 ---
            lines.insert(content_start, "---")
            frontmatter_end = content_start
            content = "\n".join(lines)
            console.print(f"[green]已修复: 在第{content_start}行插入frontmatter结束符[/green]")
        
        # 提取frontmatter并验证YAML格式
        try:
            frontmatter_text = "\n".join(lines[1:frontmatter_end])
            frontmatter_data = yaml.safe_load(frontmatter_text)
            
            # 检查frontmatter是否为字典
            if not isinstance(frontmatter_data, dict):
                console.print(f"[red]错误: {filename} frontmatter不是有效的YAML字典[/red]")
                return content
            
            # 验证通过，确保格式规范
            # 重新序列化frontmatter以确保格式正确
            fixed_frontmatter = yaml.dump(frontmatter_data, allow_unicode=True, sort_keys=False, default_flow_style=False)
            body = "\n".join(lines[frontmatter_end + 1:])
            
            # 重新组装文档
            return f"---\n{fixed_frontmatter}---\n{body}"
            
        except yaml.YAMLError as e:
            console.print(f"[red]错误: {filename} frontmatter YAML解析失败: {e}[/red]")
            console.print(f"[dim]尝试使用原内容...[/dim]")
            return content
    
    def _create_business(self, action: Dict):
        """创建新业务文档"""
        content = action["content"]
        dept = action.get("department")
        slug = action.get("slug")
        path_in_action = action.get("path")

        # 允许从 path 或 frontmatter 推断部门与slug
        if not dept and path_in_action:
            dept = self._derive_department_from_path(path_in_action)
        if not slug and path_in_action:
            try:
                slug = Path(path_in_action).stem
            except Exception:
                pass
        if not dept or not slug:
            fm_dept, fm_slug = self._extract_frontmatter_fields(content)
            dept = dept or fm_dept
            slug = slug or fm_slug

        if not dept:
            raise KeyError("action missing 'department' and cannot infer from path/frontmatter")
        if not slug:
            raise KeyError("action missing 'slug' and cannot infer from path/frontmatter")

        # 目标路径优先使用 action.path，其次使用 dept/slug.md
        if path_in_action:
            file_path = OUTPUT_DIR / Path(path_in_action)
            dept_dir = file_path.parent
        else:
            dept_dir = OUTPUT_DIR / dept
            file_path = dept_dir / f"{slug}.md"

        dept_dir.mkdir(exist_ok=True)

        if file_path.exists():
            return

        # 验证并修复frontmatter格式
        content = self._validate_and_fix_frontmatter(content, file_path.name)

        file_path.write_text(content, encoding="utf-8")
        # 记录completed_businesses
        rel_path = str(file_path.relative_to(OUTPUT_DIR)).replace("\\", "/")
        self.completed_businesses[slug] = rel_path
    
    def _update_business(self, action: Dict):
        """更新已有业务文档"""
        path = Path(action["path"])
        file_path = OUTPUT_DIR / path
        
        if not file_path.exists():
            return
        
        content = file_path.read_text(encoding="utf-8")
        
        # 解析 frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2]
                
                # 应用操作
                for op in action.get("operations", []):
                    # 安全获取字段
                    section = op.get("section")
                    operation = op.get("operation")
                    value = op.get("value")
                    
                    if not section or not operation:
                        console.print(f"[yellow]跳过无效操作: {op}[/yellow]")
                        continue
                    
                    if section in frontmatter:
                        if operation == "append":
                            if isinstance(frontmatter[section], list):
                                # 避免重复添加
                                if value not in frontmatter[section]:
                                    frontmatter[section].append(value)
                        elif operation == "replace":
                            frontmatter[section] = value
                
                # 重新组装
                new_content = "---\n" + yaml.dump(frontmatter, allow_unicode=True) + "---" + body
                file_path.write_text(new_content, encoding="utf-8")
    
    def _update_index(self, action: Dict):
        """更新 Index.yaml - 按template结构"""
        if not INDEX_FILE.exists():
            # 创建初始结构
            index = {
                "meta": {
                    "name": "签证服务知识库索引",
                    "schema_reference": "StructureRelation.yaml",
                    "source_path": ".TelegramChatHistory/KB/services",
                    "output_path": str(OUTPUT_DIR),
                    "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    "total_businesses": 0
                },
                "knowledge_base": {
                    "name": "签证服务知识库",
                    "summary": "菲律宾签证、移民、身份文件等业务的完整知识库",
                    "scope": [
                        "签证延期与申请",
                        "移民局业务办理",
                        "劳工部门业务",
                        "司法部业务"
                    ]
                },
                "department_structure": {}
            }
        else:
            index = yaml.safe_load(INDEX_FILE.read_text(encoding="utf-8"))

        # 如果没有提供department，则根据任务条目的path分组后分别处理
        dept = action.get("department")
        if not dept:
            tasks = action.get("add_tasks", []) or []
            groups: Dict[str, List[Dict]] = {}
            for t in tasks:
                p = t.get("path")
                d = self._derive_department_from_path(p) if p else None
                if not d:
                    # 无法推断部门的任务，跳过并记录
                    logger.warning(f"update_index: 无法从任务路径推断部门，已跳过: {t}")
                    continue
                groups.setdefault(d, []).append(t)
            for d, group_tasks in groups.items():
                sub_action = dict(action)
                sub_action["department"] = d
                sub_action["add_tasks"] = group_tasks
                # 递归处理带department的子动作
                self._update_index(sub_action)
            return
        
        # 确保department_structure存在
        if "department_structure" not in index:
            index["department_structure"] = {}
        
        # 确保部门存在
        if dept not in index["department_structure"]:
            # 部门全名映射
            dept_full_names = {
                "BureauOfImmigration": "Bureau of Immigration",
                "DepartmentOfForeignAffair": "Department of Foreign Affairs",
                "DepartmentOfLabor": "Department of Labor and Employment",
                "DepartmentOfJustice": "Department of Justice"
            }
            dept_descriptions = {
                "BureauOfImmigration": "移民局相关业务，包括签证延期、ECC清关、各类移民身份办理等",
                "DepartmentOfForeignAffair": "外交部业务，包括护照认证、文件公证等",
                "DepartmentOfLabor": "劳工部业务，包括工作许可、AEP、外劳证等",
                "DepartmentOfJustice": "司法部业务，包括NBI清关等"
            }

            index["department_structure"][dept] = {
                "full_name": action.get("department_full_name", dept_full_names.get(dept, dept)),
                "description": dept_descriptions.get(dept, ""),
                "folder_path": f"{dept}/",
                "solo_tasks": []
            }
        # 兼容：若部门节点已存在但缺少solo_tasks字段，则补齐
        if "solo_tasks" not in index["department_structure"][dept] or not isinstance(index["department_structure"][dept].get("solo_tasks"), list):
            index["department_structure"][dept]["solo_tasks"] = []
        
        # 添加或更新业务
        for task in action.get("add_tasks", []) or []:
            # 检查是否已存在（通过name精确匹配）
            existing_index = None
            dept_tasks = index["department_structure"][dept]["solo_tasks"]
            for i, t in enumerate(dept_tasks):
                if t.get("name") == task.get("name"):
                    existing_index = i
                    break
            
            # 构建符合template的业务条目
            full_task = {
                "name": task["name"],
                "path": task.get("path", f"{dept}/{task.get('slug', task['name'])}.md"),
                "type": task.get("type", "solo_task"),
                "summary": task.get("description", "")  # AI自己控制长度
            }
            
            if existing_index is not None:
                # 更新已有业务
                dept_tasks[existing_index] = full_task
            else:
                # 添加新业务
                dept_tasks.append(full_task)
        
        # 更新元信息
        total = sum(len(d["solo_tasks"]) for d in index["department_structure"].values())
        index["meta"]["total_businesses"] = total
        index["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        
        # 保存（保持顺序）
        INDEX_FILE.write_text(yaml.dump(index, allow_unicode=True, sort_keys=False, default_flow_style=False), encoding="utf-8")
    
    def _update_collections(self, action: Dict):
        """更新 Collections"""
        if not COLLECTIONS_FILE.exists():
            collections = {"preset_combinations": {}}
        else:
            collections = yaml.safe_load(COLLECTIONS_FILE.read_text(encoding="utf-8"))
        
        name = action["collection_name"]
        collections["preset_combinations"][name] = action["content"]
        
        COLLECTIONS_FILE.write_text(yaml.dump(collections, allow_unicode=True), encoding="utf-8")
    
    def _update_ambiguous(self, action: Dict):
        """更新歧义词典"""
        if not AMBIGUOUS_FILE.exists():
            ambiguous = {"ambiguous_terms": []}
        else:
            ambiguous = yaml.safe_load(AMBIGUOUS_FILE.read_text(encoding="utf-8"))
        
        ambiguous["ambiguous_terms"].extend(action.get("add_terms", []))
        
        AMBIGUOUS_FILE.write_text(yaml.dump(ambiguous, allow_unicode=True), encoding="utf-8")


def main():
    """主流程"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    console.print(Panel.fit(
        "[bold cyan]服务知识库增量式关联构建[/bold cyan]\n"
        f"模型: {MODEL}\n"
        f"源目录: {KB_SERVICES_DIR}\n"
        f"输出目录: {OUTPUT_DIR}\n\n"
        f"[dim]按 Ctrl+C 可立即中断处理[/dim]",
        border_style="cyan"
    ))
    
    # 记录启动参数
    logger.info(f"模型: {MODEL}")
    logger.info(f"源目录: {KB_SERVICES_DIR}")
    logger.info(f"输出目录: {OUTPUT_DIR}")
    
    # 初始化
    analysis_list = AnalysisListManager(ANALYSIS_LIST)
    kb_builder = KnowledgeBaseBuilder()
    
    # 主循环统计
    success_count = 0
    error_count = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    total_cost = 0.0
    round_number = 0
    
    # 计费标准（根据模型调整）
    # gpt-4o-mini-2024-07-18: Input $0.150/1M, Output $0.600/1M
    PRICE_PER_1M_INPUT = 0.150
    PRICE_PER_1M_OUTPUT = 0.600
    
    console.print("\n[cyan]开始持续处理模式...[/cyan]")
    console.print("[dim]脚本会持续监控目录，每次处理一个文件[/dim]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        processing_task = progress.add_task("[cyan]监控中...", total=None)
        
        while True:
            # 检查中断标志
            global interrupted
            if interrupted:
                console.print("\n[yellow]检测到中断信号，正在退出...[/yellow]")
                break
            
            round_number += 1
            
            # 每轮开始前同步目录（只添加一个新文件）
            added_file, remaining_new, deleted_count = analysis_list.sync_with_directory(KB_SERVICES_DIR)
            
            # 统计当前状态
            total_files = len(analysis_list.processed_files) + len(analysis_list.pending_files)
            processed_count = len(analysis_list.processed_files)
            pending_count = len(analysis_list.pending_files)
            
            # 紧凑的状态行
            status_info = (
                f"[cyan]━━━ 回合 {round_number} ━━━[/cyan] "
                f"文件: [green]{processed_count}[/green]✓ [yellow]{pending_count}[/yellow]⏳ "
                f"业务: [blue]{len(kb_builder.completed_businesses)}[/blue] | "
                f"Token: [cyan]{total_prompt_tokens:,}[/cyan]→ [yellow]{total_completion_tokens:,}[/yellow]← "
                f"[magenta]{total_tokens:,}[/magenta]Σ | "
                f"费用: [green]${total_cost:.4f}[/green]"
            )
            console.print(f"\n{status_info}")
            
            if added_file:
                console.print(f"  [dim]新增: {Path(added_file).name}[/dim]", end="")
                if remaining_new > 1:
                    console.print(f" [dim](+{remaining_new - 1} 排队)[/dim]")
                else:
                    console.print()
            if deleted_count > 0:
                console.print(f"  [dim]移除: {deleted_count} 个已删除[/dim]")
            
            # 获取下一个待处理文件
            next_file = analysis_list.get_next_file()
            if not next_file:
                console.print("\n[yellow]当前没有待处理文件，等待5秒后重新扫描...[/yellow]")
                # 使用短间隔检查中断
                for _ in range(50):  # 5秒 = 50 × 0.1秒
                    if interrupted:
                        break
                    time.sleep(0.1)
                continue
            
            file_path = Path(next_file)
            progress.update(processing_task, description=f"[cyan]处理: {file_path.name}")
            
            console.print(f"  [cyan]→[/cyan] {file_path.name}", end=" ")
            task_start_time = time.time()
            logger.info(f"开始处理文件: {file_path.name}")
            
            try:
                # 检查中断
                if interrupted:
                    break

                # ============ 多轮流程 ============
                per_file_prompt_tokens = 0
                per_file_completion_tokens = 0
                per_file_total_tokens = 0
                per_file_cost = 0.0

                # Round 1: 选择阶段
                selection_prompt = kb_builder.build_selection_prompt(file_path)
                # 发送前token预估
                if kb_builder.estimate_tokens(selection_prompt) > TOKEN_CAP:
                    raise RuntimeError("选择阶段提示超出Token上限，已停止以保护会话与日志")

                console.print(f"[dim](选择阶段 API)[/dim]", end=" ")
                r1_start = time.time()
                selection_result = kb_builder.call_ai(selection_prompt)
                r1_elapsed = time.time() - r1_start

                r1_usage = selection_result.get("usage", {})
                r1_prompt_tokens = r1_usage.get("prompt_tokens", 0)
                r1_completion_tokens = r1_usage.get("completion_tokens", 0)
                r1_total_tokens = r1_usage.get("total_tokens", 0)
                per_file_prompt_tokens += r1_prompt_tokens
                per_file_completion_tokens += r1_completion_tokens
                per_file_total_tokens += r1_total_tokens
                per_file_cost += (r1_prompt_tokens / 1_000_000 * PRICE_PER_1M_INPUT + r1_completion_tokens / 1_000_000 * PRICE_PER_1M_OUTPUT)
                console.print(f"[dim]({r1_elapsed:.1f}s)[/dim]", end=" ")

                # 写入选择阶段日志
                sel_log = LOG_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.stem}_selection.json"
                sel_log.write_text(json.dumps(selection_result, ensure_ascii=False, indent=2), encoding="utf-8")

                requested = selection_result.get("requested_business_files", [])
                # 规范化提取路径
                requested_paths: List[str] = []
                for item in requested:
                    if isinstance(item, dict):
                        p = item.get("path")
                        if p:
                            requested_paths.append(p)
                    elif isinstance(item, str):
                        requested_paths.append(item)

                # 截断到本轮上限
                if len(requested_paths) > SELECTION_LIMIT_PER_ROUND:
                    requested_paths = requested_paths[:SELECTION_LIMIT_PER_ROUND]

                # 记录已选集合
                selected_total: Set[str] = set(requested_paths)

                # Round 2: 处理（可追加更多）
                processing_prompt_r2 = kb_builder.build_processing_prompt(file_path, list(selected_total), 2, len(selected_total))
                if kb_builder.estimate_tokens(processing_prompt_r2) > TOKEN_CAP:
                    raise RuntimeError("处理阶段R2提示超出Token上限，已停止以保护会话与日志")

                console.print(f"[dim](处理R2 API)[/dim]", end=" ")
                r2_start = time.time()
                process_result_r2 = kb_builder.call_ai(processing_prompt_r2)
                r2_elapsed = time.time() - r2_start
                r2_usage = process_result_r2.get("usage", {})
                r2_prompt_tokens = r2_usage.get("prompt_tokens", 0)
                r2_completion_tokens = r2_usage.get("completion_tokens", 0)
                r2_total_tokens = r2_usage.get("total_tokens", 0)
                per_file_prompt_tokens += r2_prompt_tokens
                per_file_completion_tokens += r2_completion_tokens
                per_file_total_tokens += r2_total_tokens
                per_file_cost += (r2_prompt_tokens / 1_000_000 * PRICE_PER_1M_INPUT + r2_completion_tokens / 1_000_000 * PRICE_PER_1M_OUTPUT)
                console.print(f"[dim]({r2_elapsed:.1f}s)[/dim]", end=" ")

                # 写入处理R2日志
                r2_log = LOG_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.stem}_r2.json"
                r2_log.write_text(json.dumps(process_result_r2, ensure_ascii=False, indent=2), encoding="utf-8")

                actions = process_result_r2.get("actions", [])
                additional_req = process_result_r2.get("additional_requested_files", [])

                actions_final = actions

                # 如R2未给出actions且请求更多，并且还有额度→R3
                if (not actions_final or len(actions_final) == 0) and additional_req and len(selected_total) < SELECTION_TOTAL_LIMIT:
                    # 追加文件（遵守每轮5个、总共10个）
                    add_paths: List[str] = []
                    for item in additional_req:
                        if isinstance(item, dict):
                            p = item.get("path")
                            if p:
                                add_paths.append(p)
                        elif isinstance(item, str):
                            add_paths.append(item)

                    remaining = max(0, SELECTION_TOTAL_LIMIT - len(selected_total))
                    if remaining > 0:
                        add_paths = add_paths[:min(SELECTION_LIMIT_PER_ROUND, remaining)]
                        for p in add_paths:
                            selected_total.add(p)

                        processing_prompt_r3 = kb_builder.build_processing_prompt(file_path, list(selected_total), 3, len(selected_total))
                        if kb_builder.estimate_tokens(processing_prompt_r3) > TOKEN_CAP:
                            raise RuntimeError("处理阶段R3提示超出Token上限，已停止以保护会话与日志")

                        console.print(f"[dim](处理R3 API)[/dim]", end=" ")
                        r3_start = time.time()
                        process_result_r3 = kb_builder.call_ai(processing_prompt_r3)
                        r3_elapsed = time.time() - r3_start
                        r3_usage = process_result_r3.get("usage", {})
                        r3_prompt_tokens = r3_usage.get("prompt_tokens", 0)
                        r3_completion_tokens = r3_usage.get("completion_tokens", 0)
                        r3_total_tokens = r3_usage.get("total_tokens", 0)
                        per_file_prompt_tokens += r3_prompt_tokens
                        per_file_completion_tokens += r3_completion_tokens
                        per_file_total_tokens += r3_total_tokens
                        per_file_cost += (r3_prompt_tokens / 1_000_000 * PRICE_PER_1M_INPUT + r3_completion_tokens / 1_000_000 * PRICE_PER_1M_OUTPUT)
                        console.print(f"[dim]({r3_elapsed:.1f}s)[/dim]", end=" ")

                        # 写入处理R3日志
                        r3_log = LOG_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.stem}_r3.json"
                        r3_log.write_text(json.dumps(process_result_r3, ensure_ascii=False, indent=2), encoding="utf-8")

                        actions_final = process_result_r3.get("actions", [])

                # 执行指令（静默执行）
                for action in actions_final or []:
                    action_type = action.get("action")
                    try:
                        if action_type in ["create_business", "create_business_file"]:
                            kb_builder._create_business(action)
                        elif action_type in ["update_business", "update_business_file"]:
                            kb_builder._update_business(action)
                        elif action_type == "update_index":
                            kb_builder._update_index(action)
                        elif action_type == "update_collections":
                            kb_builder._update_collections(action)
                        elif action_type == "update_ambiguous":
                            kb_builder._update_ambiguous(action)
                    except Exception as action_error:
                        error_msg = f"指令失败: {action_type} - {action_error}"
                        console.print(f"\n[red]{error_msg}[/red]")
                        logger.error(error_msg)
                        logger.debug(f"失败的 Action: {json.dumps(action, ensure_ascii=False, indent=2)}")

                # 标记完成
                analysis_list.mark_completed(next_file)
                task_elapsed = time.time() - task_start_time
                logger.info(f"文件处理完成: {file_path.name}, 耗时: {task_elapsed:.2f}s")

                # 累计全局统计
                total_prompt_tokens += per_file_prompt_tokens
                total_completion_tokens += per_file_completion_tokens
                total_tokens += per_file_total_tokens
                total_cost += per_file_cost

                # 报告汇总（以最终actions为准）
                created_files = [a for a in (actions_final or []) if a.get("action") in ["create_business", "create_business_file"]]
                updated_files = [a for a in (actions_final or []) if a.get("action") in ["update_business", "update_business_file"]]
                combinations = []
                relations = 0
                # 尝试从R2/R3结果读到的非关键统计字段（若存在）
                for r in [locals().get('process_result_r3'), locals().get('process_result_r2')]:
                    if isinstance(r, dict):
                        if not combinations:
                            combinations = r.get("combinations_detected", []) or []
                        if relations == 0:
                            relations = r.get("relations_updated", 0) or 0

                success_count += 1

                # 终端小结表格
                report_table = Table(box=box.MINIMAL, show_header=True, padding=(0, 1), expand=False)
                report_table.add_column("创建", style="green", no_wrap=True)
                report_table.add_column("更新", style="yellow", no_wrap=True)
                report_table.add_column("组合", style="blue", no_wrap=True)
                report_table.add_column("关联", style="magenta", no_wrap=True)

                def _derive_display_name(a: Dict) -> str:
                    name = a.get('business_name') or a.get('name')
                    if name:
                        return str(name)
                    # 尝试从content frontmatter拉取name
                    content = a.get('content')
                    if isinstance(content, str) and content.startswith('---'):
                        fm_dept, fm_slug = self._extract_frontmatter_fields(content)
                        # 复用frontmatter解析拿到更多字段
                        try:
                            lines = content.split("\n")
                            end = -1
                            for i in range(1, len(lines)):
                                if lines[i].strip() == "---":
                                    end = i
                                    break
                            if end != -1:
                                fm_text = "\n".join(lines[1:end])
                                fm = yaml.safe_load(fm_text)
                                if isinstance(fm, dict):
                                    nm = fm.get('name')
                                    if nm:
                                        return str(nm)
                        except Exception:
                            pass
                    # 再尝试从path/slug推断
                    p = a.get('path')
                    if p:
                        try:
                            return Path(p).stem.replace('-', ' ').title()
                        except Exception:
                            pass
                    slug = a.get('slug')
                    if slug:
                        return str(slug).replace('-', ' ').title()
                    return 'Unknown'

                created_names = ", ".join([_derive_display_name(a)[:20] for a in created_files]) or "-"
                updated_names = ", ".join([_derive_display_name(a)[:20] for a in updated_files]) or "-"
                combo_str = f"{len(combinations)}" if combinations else "-"
                relation_str = f"{relations}" if relations > 0 else "-"

                report_table.add_row(
                    f"{len(created_files)}: {created_names}",
                    f"{len(updated_files)}: {updated_names}",
                    combo_str,
                    relation_str
                )

                token_table = Table(box=box.MINIMAL, show_header=True, padding=(0, 1), expand=False)
                token_table.add_column("输入↓", style="cyan", justify="right")
                token_table.add_column("输出↑", style="yellow", justify="right")
                token_table.add_column("总计", style="magenta", justify="right")
                token_table.add_column("费用", style="green", justify="right")
                token_table.add_column("时间", style="dim", justify="right")
                token_table.add_column("累计Token", style="magenta", justify="right")
                token_table.add_column("累计费用", style="green", justify="right")

                token_table.add_row(
                    f"{per_file_prompt_tokens:,}",
                    f"{per_file_completion_tokens:,}",
                    f"{per_file_total_tokens:,}",
                    f"${per_file_cost:.4f}",
                    f"{task_elapsed:.1f}s",
                    f"{total_tokens:,}",
                    f"${total_cost:.4f}"
                )

                console.print("  [green]✓[/green]", end=" ")
                console.print(report_table)
                console.print("    ", end="")
                console.print(token_table)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                error_msg = str(e)[:100]
                console.print(f" [bold red]✗[/bold red] {error_msg}")
                logger.error(f"处理文件失败: {file_path.name} - {str(e)}")
                logger.debug(f"完整错误信息: {str(e)}")
                error_count += 1
                # 标记为失败但继续，避免无限重试同一个文件
                analysis_list.mark_completed(next_file)  # 先标记完成，避免卡住
                logger.warning(f"已标记文件为完成以避免重试: {next_file}")
                if "--debug" in sys.argv:
                    import traceback
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
                # 等待一下再继续，避免连续出错刷屏
                time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]用户中断，进度已保存[/bold yellow]")
        console.print("[green]已处理的文件进度已记录到 AnalysisList.md[/green]")
        logger.info("用户中断，进度已保存")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n\n[red]发生错误: {e}[/red]")
        logger.critical(f"脚本崩溃: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        console.print(traceback.format_exc())
        sys.exit(1)

