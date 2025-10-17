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
import signal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

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
    sys.exit(0)
from rich.layout import Layout
from rich import box

# 初始化
console = Console()
load_dotenv()

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
                console.print(f"[red]读取业务文档失败: {rel_path} - {e}[/red]")
        
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
      "action": "create_business_file",  // 注意：改为create_business_file
      "department": "BureauOfImmigration",
      "slug": "business-1-slug",
      "name": "Business 1 Name",
      "business_name": "Business 1 Name",  // 添加此字段用于报告
      "content": "完整的markdown文档内容（包含frontmatter和正文）"
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

请直接输出JSON，不要包含其他文字。
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
            console.print(f"[red]AI API 调用失败: {e}[/red]")
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
                console.print(f"[red]执行指令失败 ({action_type}): {e}[/red]")
    
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
        dept = action["department"]
        slug = action["slug"]
        content = action["content"]
        
        dept_dir = OUTPUT_DIR / dept
        dept_dir.mkdir(exist_ok=True)
        
        file_path = dept_dir / f"{slug}.md"
        
        if file_path.exists():
            return
        
        # 验证并修复frontmatter格式
        content = self._validate_and_fix_frontmatter(content, file_path.name)
        
        file_path.write_text(content, encoding="utf-8")
        self.completed_businesses[slug] = f"{dept}/{slug}.md"
    
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
        
        dept = action["department"]
        
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
        
        # 添加或更新业务
        for task in action.get("add_tasks", []):
            # 检查是否已存在（通过name精确匹配）
            existing_index = None
            for i, t in enumerate(index["department_structure"][dept]["solo_tasks"]):
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
                index["department_structure"][dept]["solo_tasks"][existing_index] = full_task
            else:
                # 添加新业务
                index["department_structure"][dept]["solo_tasks"].append(full_task)
        
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
            
            try:
                # 检查中断
                if interrupted:
                    break
                
                # 构建提示词
                prompt = kb_builder.build_prompt(file_path)
                
                # 检查中断
                if interrupted:
                    break
                
                # 调用 AI
                console.print(f"[dim](API请求中...)[/dim]", end=" ")
                api_start_time = time.time()
                result = kb_builder.call_ai(prompt)
                api_elapsed = time.time() - api_start_time
                
                # 提取 token 使用信息
                round_tokens = result.get("usage", {})
                prompt_tokens = round_tokens.get("prompt_tokens", 0)
                completion_tokens = round_tokens.get("completion_tokens", 0)
                round_total_tokens = round_tokens.get("total_tokens", 0)
                
                # 计算本轮费用
                round_cost = (prompt_tokens / 1_000_000 * PRICE_PER_1M_INPUT + 
                             completion_tokens / 1_000_000 * PRICE_PER_1M_OUTPUT)
                
                # 累计统计
                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                total_tokens += round_total_tokens
                total_cost += round_cost
                
                console.print(
                    f"[dim]({api_elapsed:.1f}s)[/dim]"
                )
                
                # 执行指令（静默执行）
                actions = result.get("actions", [])
                for action in actions:
                    action_type = action.get("action")
                    try:
                        # 兼容旧格式和新格式
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
                        console.print(f"\n[red]指令失败: {action_type} - {action_error}[/red]")
                
                # 标记完成
                analysis_list.mark_completed(next_file)
                
                # 记录日志
                log_file = LOG_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.stem}.json"
                log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                
                # 统计
                success_count += 1
                task_elapsed = time.time() - task_start_time
                
                # 紧凑的报告 - 使用两行表格
                created_files = [a for a in actions if a.get("action") in ["create_business", "create_business_file"]]
                updated_files = [a for a in actions if a.get("action") in ["update_business", "update_business_file"]]
                combinations = result.get("combinations_detected", [])
                relations = result.get("relations_updated", 0)
                
                # 第一行：文件操作和识别
                report_table = Table(box=box.MINIMAL, show_header=True, padding=(0, 1), expand=False)
                report_table.add_column("创建", style="green", no_wrap=True)
                report_table.add_column("更新", style="yellow", no_wrap=True)
                report_table.add_column("组合", style="blue", no_wrap=True)
                report_table.add_column("关联", style="magenta", no_wrap=True)
                
                created_names = ", ".join([a.get('business_name', a.get('name', 'Unknown'))[:20] for a in created_files]) or "-"
                updated_names = ", ".join([a.get('business_name', a.get('name', 'Unknown'))[:20] for a in updated_files]) or "-"
                combo_str = f"{len(combinations)}" if combinations else "-"
                relation_str = f"{relations}" if relations > 0 else "-"
                
                report_table.add_row(
                    f"{len(created_files)}: {created_names}",
                    f"{len(updated_files)}: {updated_names}",
                    combo_str,
                    relation_str
                )
                
                # 第二行：Token和费用
                token_table = Table(box=box.MINIMAL, show_header=True, padding=(0, 1), expand=False)
                token_table.add_column("输入↓", style="cyan", justify="right")
                token_table.add_column("输出↑", style="yellow", justify="right")
                token_table.add_column("总计", style="magenta", justify="right")
                token_table.add_column("费用", style="green", justify="right")
                token_table.add_column("时间", style="dim", justify="right")
                token_table.add_column("累计Token", style="magenta", justify="right")
                token_table.add_column("累计费用", style="green", justify="right")
                
                token_table.add_row(
                    f"{prompt_tokens:,}",
                    f"{completion_tokens:,}",
                    f"{round_total_tokens:,}",
                    f"${round_cost:.4f}",
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
                console.print(f" [bold red]✗[/bold red] {str(e)[:100]}")
                error_count += 1
                # 标记为失败但继续，避免无限重试同一个文件
                analysis_list.mark_completed(next_file)  # 先标记完成，避免卡住
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
        sys.exit(0)
    except Exception as e:
        console.print(f"\n\n[red]发生错误: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)

