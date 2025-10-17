#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import traceback
from dotenv import load_dotenv

# 导入Rich美化组件
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn, 
    TimeRemainingColumn, MofNCompleteColumn, TimeElapsedColumn
)
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout

# 加载环境变量
load_dotenv(Path(__file__).parent.parent / ".env")

# 导入OpenAI
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# 导入kb_tools的函数
sys.path.append(str(Path(__file__).parent))
from kb_tools import (
    DEFAULT_KB_ROOT, DEFAULT_ORGANIZED_ROOT, cmd_init_kb, cmd_state_get, cmd_state_update,
    cmd_queue_get_next_file, cmd_chat_read_lines, cmd_kb_load_index, 
    cmd_kb_upsert_service, cmd_kb_append_markdown, cmd_kb_upsert_pricing, 
    cmd_kb_save_index, cmd_log_append, slugify, list_ordered_chat_files
)

# 导入RichLogger
sys.path.append(str(Path(__file__).parent.parent))
from SharedUtility.RichLogger.logger import RichLoggerManager

class AIBusinessExtractor:
    """使用AI大模型进行业务信息提取"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.1,  # 低温度确保一致性
            max_tokens=4000,
            stream_usage=True,  # 启用token使用统计
        )
        self.total_tokens_used = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "interaction_time": 0.0
        }
        
        # 系统提示词，专门用于业务信息提取
        self.system_prompt = """你是一个专业的信息提取专家，从Telegram聊天记录中深度分析和提取有价值的信息。

什么是有用的信息？
- 任何需要办理、处理、申请的事项
- 任何提到价格、费用、收费的内容
- 任何提到流程、步骤、材料、要求的内容
- 任何提到文件、证件、证明的内容
- 闲聊中透露的业务细节、办理经验、注意事项
- 客户咨询、代理回答中涉及的具体操作
- 即使看起来是闲聊，但提到了具体业务名称、价格、材料的内容

核心任务：
1. **覆盖性捕获**：深度分析聊天记录，提取所有可能有用的信息，宁可多提取不要遗漏
2. **业务拆分**：如果聊天描述了一整套流程，拆分为每个独立的办理事项
3. **文件详细度**：提取文件的类型、数量、是否会被收走等细节
4. **保留上下文**：提取完整的对话上下文，不要只提取关键词

识别原则：
- **语义理解**：理解对话意图，不仅看关键词
- **高召回率**：宁可错提取也不要遗漏（提纯是后续步骤）
- **细节敏感**：注意数量（3张）、类型（原件/复印件）、消耗性（收走/归还）
- **组合识别**：如果提到"全套"、"套餐"、"一起办"，识别可能的组合

有用信息的线索：
- 动词：办理、申请、处理、准备、提交、缴费、拍摄、填写、认证、公示
- 名词：文件、材料、证件、证明、照片、表格、合同、公示
- 价格：任何数字+货币的组合（1000 PHP、500 RMB）
- 要求：需要、必须、要求、准备、提供
- 流程：第一步、然后、接下来、之后、最后
- 时间：几天、一周、一个月、工作日
- 限制：不能、必须、只有、除非

文件信息提取：
- 原件（original）：护照原件、签证原件、身份证原件
- 复印件（copy）：复印件、照片、扫描件
- 数量：3张、2份、一式三份
- 消耗性判断：
  - 提到"收走"、"不归还"、"交上去" → consumable: true
  - 提到"借用"、"查看后归还"、"只是验证" → consumable: false

业务拆分示例：
- 聊天提到"办9G需要AEP、移民局申请、拍照"
- 拆分为：AEP申请、移民局9G申请、证件照拍摄
- 每个都是独立业务，同时记录它们可能构成组合

返回JSON格式：
{
  "has_business_content": boolean,
  "businesses": [
    {
      "business_name": "业务名称（使用聊天中最常见的称呼）",
      "business_type": "solo_task",
      "aliases": ["别名1", "别名2"],
      "description": "业务详细描述（5-10句话）",
      
      "input_files": [
        {
          "document_name": "文件名称",
          "document_type": "original/copy",
          "quantity": 数字,
          "consumable_in_this_task": boolean,
          "required": boolean,
          "notes": "文件详细要求说明"
        }
      ],
      
      "output_files": [
        {
          "document_name": "产出文件名称",
          "document_type": "original/copy",
          "quantity": 数字
        }
      ],
      
      "processes": ["步骤1详细说明", "步骤2详细说明"],
      
      "prices": [
        {
          "currency": "PHP",
          "amount": "金额",
          "effective_date": "YYYY-MM",
          "conditions": "适用条件",
          "notes": "备注",
          "evidence_message_ids": [消息ID]
        }
      ],
      
      "notes": ["注意事项1", "注意事项2"],
      
      "evidence_messages": [
        {
          "message_id": 消息ID,
          "date": "日期",
          "text_summary": "消息关键内容摘要"
        }
      ]
    }
  ],
  
  "potential_combinations": [
    {
      "combination_name": "组合业务名称",
      "description": "组合业务说明",
      "included_businesses": ["业务1", "业务2", "业务3"],
      "reasoning": "为什么这些业务可能是固定组合"
    }
  ]
}

提取要求：
- 深度分析：不要只看明显的业务描述，闲聊中的业务细节也要提取
- 逐个拆分：一个聊天可能包含多个业务，逐个识别
- 文件详细：每个文件的类型、数量、是否消耗都要标注
- 组合识别：如果聊天提到"全套"、"套餐"，识别potential_combinations
- 证据完整：所有信息标注消息ID

如果没有发现业务内容，返回 "has_business_content": false。"""

    def extract_from_lines(self, lines: List[str], chat_id: str = "unknown", file_path: str = "") -> Dict[str, Any]:
        """使用AI从聊天记录中提取业务信息"""
        
        if not lines:
            return {"has_business_content": False, "businesses": []}
        
        # 解析聊天头信息
        chat_name = "unknown"
        if lines[0]:
            try:
                header = json.loads(lines[0])
                if header.get("_kind") == "chat_header":
                    chat_name = header.get("name", "unknown")
                    chat_id = str(header.get("id", chat_id))
            except json.JSONDecodeError:
                pass
        
        # 整理聊天消息为可读格式
        messages_text = []
        messages_data = []  # 保存原始数据用于引用
        
        messages_text.append(f"聊天信息: {chat_name} (ID: {chat_id})")
        messages_text.append("=" * 50)
        
        for i, line in enumerate(lines[1:], 1):
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                if msg.get("_kind") != "message":
                    continue
                
                # 处理文本内容
                text = msg.get("text", "")
                if isinstance(text, list):
                    text = " ".join([
                        str(item.get("text", "")) if isinstance(item, dict) else str(item) 
                        for item in text
                    ])
                text = str(text).strip()
                
                if not text:
                    continue
                    
                date = msg.get("date", "")
                msg_id = msg.get("id")
                from_name = msg.get("from", "Unknown")
                
                # 格式化消息
                formatted_msg = f"[{date}] {from_name} (ID:{msg_id}): {text}"
                messages_text.append(formatted_msg)
                
                # 保存原始数据
                messages_data.append({
                    "id": msg_id,
                    "date": date,
                    "from": from_name,
                    "text": text
                })
                
            except json.JSONDecodeError:
                continue
        
        if len(messages_data) == 0:
            return {"has_business_content": False, "businesses": []}
        
        # 将聊天记录发送给AI分析
        chat_content = "\n".join(messages_text)
        
        # 限制长度防止token超限
        if len(chat_content) > 10000:
            chat_content = chat_content[:10000] + "\n...(内容过长已截断)"
        
        try:
            # 构建提示
            user_prompt = f"""请分析以下Telegram聊天记录，提取业务办理相关信息：

{chat_content}

请返回JSON格式的提取结果。"""
            
            # 调用AI
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # 记录交互开始时间
            interaction_start = time.time()
            
            response = self.llm.invoke(messages)
            result_text = response.content.strip()
            
            # 计算交互耗时
            interaction_duration = time.time() - interaction_start
            
            # 提取并累积token使用统计
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                self.total_tokens_used["input_tokens"] += usage.get("input_tokens", 0)
                self.total_tokens_used["output_tokens"] += usage.get("output_tokens", 0)
                self.total_tokens_used["total_tokens"] += usage.get("total_tokens", 0)
                
                print(f"AI交互完成: 耗时 {interaction_duration:.2f}秒")
                print(f"本次token使用: 输入={usage.get('input_tokens', 0)}, "
                      f"输出={usage.get('output_tokens', 0)}, "
                      f"总计={usage.get('total_tokens', 0)}")
                print(f"累积token使用: 输入={self.total_tokens_used['input_tokens']}, "
                      f"输出={self.total_tokens_used['output_tokens']}, "
                      f"总计={self.total_tokens_used['total_tokens']}")
                
                # 将交互时间添加到token统计中
                self.total_tokens_used["interaction_time"] = self.total_tokens_used.get("interaction_time", 0) + interaction_duration
            
            # 检查响应是否为空
            if not result_text:
                print(f"AI返回空响应，跳过此批次")
                return {"has_business_content": False, "businesses": [], "error": "AI返回空响应"}
            
            # 尝试解析JSON响应
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            # 再次检查清理后的内容
            result_text = result_text.strip()
            if not result_text:
                print(f"清理后AI响应为空，跳过此批次")
                return {"has_business_content": False, "businesses": [], "error": "清理后响应为空"}
            
            # 如果不是JSON格式，尝试智能修复
            if not result_text.startswith("{"):
                # 查找JSON内容
                start_idx = result_text.find("{")
                if start_idx != -1:
                    result_text = result_text[start_idx:]
                else:
                    print(f"AI响应不包含JSON格式，原始内容: {result_text[:200]}")
                    return {"has_business_content": False, "businesses": [], "error": "响应格式错误"}
            
            result = json.loads(result_text)
            
            # 后处理：添加文件信息和完善证据
            if result.get("has_business_content") and result.get("businesses"):
                for business in result["businesses"]:
                    # 为价格添加文件信息
                    for price in business.get("prices", []):
                        # 如果没有消息ID，尝试从消息数据中匹配
                        if not price.get("evidence_message_ids"):
                            price["evidence_message_ids"] = [msg["id"] for msg in messages_data if msg["id"]][:3]
                    
                    # 为证据消息添加文件信息
                    for evidence in business.get("evidence_messages", []):
                        evidence["source_file"] = Path(file_path).name
            
            # 添加聊天基本信息
            result["chat_id"] = chat_id
            result["chat_name"] = chat_name
            result["file_path"] = file_path
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"AI返回的JSON格式错误: {e}")
            print(f"原始响应: {result_text}")
            return {"has_business_content": False, "businesses": [], "error": "JSON解析失败"}
        
        except Exception as e:
            print(f"AI提取失败: {e}")
            return {"has_business_content": False, "businesses": [], "error": str(e)}

class AITelegramWorkflow:
    """基于AI的Telegram业务知识提取工作流"""
    
    def __init__(self, kb_root: Path = None, organized_root: Path = None, max_lines_per_batch: int = 800, model_name: str = None):
        self.kb_root = kb_root or Path(DEFAULT_KB_ROOT)
        self.organized_root = organized_root or Path(DEFAULT_ORGANIZED_ROOT)  
        self.max_lines_per_batch = max_lines_per_batch
        self.selected_model = model_name
        self.extractor = AIBusinessExtractor(model_name)
        self.stats = {
            "files_processed": 0,
            "services_updated": 0,
            "prices_added": 0,
            "ai_calls": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
            "tokens_used": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "session_start": None,
                "total_ai_time": 0.0,
                "ai_interactions": 0
            }
        }
        
        # 初始化Rich控制台和日志
        self.console = Console()
        self.logger = RichLoggerManager.for_node("ai_extraction", level=10)  # DEBUG级别
        
        # 进度追踪
        self.progress_task = None
        self.current_progress = None
        
        # 加载历史token统计
        self._load_historical_tokens()
        
    def log_info(self, message: str, extra_data: Dict[str, Any] = None):
        """记录信息日志"""
        self.logger.info(message)
        if extra_data:
            # 显示额外的结构化信息
            table = Table(title="详细信息", show_header=True, header_style="bold blue")
            table.add_column("项目", style="cyan")
            table.add_column("值", style="green")
            
            for key, value in extra_data.items():
                table.add_row(str(key), str(value))
            
            self.console.print(table)
        
    def log_error(self, message: str, error: Exception = None):
        """记录错误日志"""
        self.logger.error(message)
        if error:
            self.console.print(f"[red]错误详情: {str(error)}[/red]")
        self.stats["errors"] += 1
        
    def log_success(self, message: str, data: Dict[str, Any] = None):
        """记录成功信息"""
        self.console.print(f"[bold green]>> {message}[/bold green]")
        if data:
            for key, value in data.items():
                self.console.print(f"  [cyan]{key}:[/cyan] [yellow]{value}[/yellow]")
                
    def show_banner(self):
        """显示启动横幅"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                   AI业务知识提取工作流                        ║
╚══════════════════════════════════════════════════════════════╝
        """
        
        panel = Panel(
            banner,
            title="[bold blue]Telegram Business Knowledge Extractor[/bold blue]",
            subtitle=f"[italic]Model: {self.selected_model or os.getenv('OPENAI_MODEL', 'gpt-4o')}[/italic]",
            border_style="blue"
        )
        self.console.print(panel)
    
    def _load_historical_tokens(self):
        """从状态文件加载历史token统计"""
        try:
            state = cmd_state_get(self.kb_root)
            historical_tokens = state.get("tokens_cumulative", {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "first_session": None,
                "last_updated": None
            })
            
            # 累积到当前统计中
            self.stats["tokens_used"]["input_tokens"] = historical_tokens["input_tokens"]
            self.stats["tokens_used"]["output_tokens"] = historical_tokens["output_tokens"] 
            self.stats["tokens_used"]["total_tokens"] = historical_tokens["total_tokens"]
            
            if historical_tokens["first_session"]:
                self.stats["tokens_used"]["session_start"] = historical_tokens["first_session"]
            
            if historical_tokens["total_tokens"] > 0:
                self.console.print(f"[dim]>> 加载历史token统计: 总计 {historical_tokens['total_tokens']} tokens[/dim]")
                
        except Exception as e:
            self.console.print(f"[yellow]>> 无法加载历史token统计: {e}[/yellow]")
    
    def _save_token_statistics(self):
        """保存token统计到状态文件"""
        try:
            # 获取当前状态
            state = cmd_state_get(self.kb_root)
            
            # 更新token统计
            token_data = {
                "input_tokens": self.stats["tokens_used"]["input_tokens"],
                "output_tokens": self.stats["tokens_used"]["output_tokens"],
                "total_tokens": self.stats["tokens_used"]["total_tokens"],
                "first_session": self.stats["tokens_used"]["session_start"] or datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            
            # 保存到状态
            cmd_state_update(self.kb_root, {"tokens_cumulative": token_data})
            
        except Exception as e:
            self.console.print(f"[red]>> 保存token统计失败: {e}[/red]")
        
    def process_single_file_batch(self, chat_file: str) -> Dict[str, Any]:
        """使用AI处理单个文件的一个批次"""
        try:
            # 1. 获取当前状态
            state = cmd_state_get(self.kb_root)
            
            # 2. 确保状态正确
            if state.get("lastProcessedFile") != chat_file:
                cmd_state_update(self.kb_root, {"lastProcessedFile": chat_file})
                state = cmd_state_get(self.kb_root)
            
            # 3. 读取内容
            start_line = state.get("lastOffsetLine", 0) + 1
            read_result = cmd_chat_read_lines({
                "path": chat_file,
                "start_line": start_line,
                "max_lines": self.max_lines_per_batch
            })
            
            lines = read_result.get("lines", [])
            next_line = read_result.get("next_line", start_line)
            eof = read_result.get("eof", False)
            
            if not lines:
                # 没有内容，可能已经到文件末尾
                if eof:
                    cmd_state_update(self.kb_root, {
                        "filesDoneAppend": chat_file,
                        "lastProcessedFile": None, 
                        "lastOffsetLine": 0
                    })
                    return {
                        "success": True,
                        "file_completed": True,
                        "lines_processed": 0,
                        "services_updated": [],
                        "prices_added": 0,
                        "ai_called": False
                    }
                else:
                    return {
                        "success": False,
                        "error": "无法读取文件内容"
                    }
            
            # 4. 使用AI提取业务信息
            self.console.print(f"[yellow]>> 调用AI分析 {len(lines)} 行聊天记录...[/yellow]")
            
            # 显示分析进度
            with self.console.status("[bold yellow]AI正在分析聊天内容...[/bold yellow]") as status:
                extraction_result = self.extractor.extract_from_lines(lines, file_path=chat_file)
                self.stats["ai_calls"] += 1
                
                # 累积token统计
                extractor_tokens = self.extractor.total_tokens_used
                self.stats["tokens_used"]["input_tokens"] += extractor_tokens["input_tokens"]
                self.stats["tokens_used"]["output_tokens"] += extractor_tokens["output_tokens"] 
                self.stats["tokens_used"]["total_tokens"] += extractor_tokens["total_tokens"]
                self.stats["tokens_used"]["total_ai_time"] += extractor_tokens.get("interaction_time", 0)
                self.stats["tokens_used"]["ai_interactions"] += 1
                
                # 重置提取器的token计数器
                self.extractor.total_tokens_used = {
                    "input_tokens": 0,
                    "output_tokens": 0, 
                    "total_tokens": 0,
                    "interaction_time": 0.0
                }
            
            if not extraction_result.get("has_business_content"):
                self.console.print("[dim]>> AI未发现业务内容[/dim]")
                # 更新状态但不创建服务
                if eof:
                    cmd_state_update(self.kb_root, {
                        "filesDoneAppend": chat_file,
                        "lastProcessedFile": None,
                        "lastOffsetLine": 0
                    })
                else:
                    cmd_state_update(self.kb_root, {"lastOffsetLine": next_line})
                
                return {
                    "success": True,
                    "file_completed": eof,
                    "lines_processed": len(lines),
                    "services_updated": [],
                    "prices_added": 0,
                    "ai_called": True,
                    "business_found": False
                }
            
            businesses = extraction_result.get("businesses", [])
            potential_combinations = extraction_result.get("potential_combinations", [])
            updated_businesses = []
            new_prices = 0
            
            # 5. 处理提取到的业务
            for business_data in businesses:
                try:
                    # 创建/更新业务
                    business_name = business_data.get("business_name", "未知业务")
                    aliases = business_data.get("aliases", [])
                    business_type = business_data.get("business_type", "solo_task")
                    
                    upsert_result = cmd_kb_upsert_service(self.kb_root, {
                        "name": business_name,
                        "aliases": aliases,
                        "categories": [business_type]
                    })
                    
                    if upsert_result.get("ok"):
                        business_slug = upsert_result["slug"]
                        updated_businesses.append(business_slug)
                        
                        # 写入各种内容
                        self._write_ai_extracted_content(business_slug, business_data, chat_file)
                        
                        # 计算价格数量
                        new_prices += len(business_data.get("prices", []))
                        
                        self.console.print(f"[green]>> 更新业务: {business_name} ({business_slug})[/green]")
                        
                except Exception as e:
                    self.log_error(f"处理AI提取的业务 {business_data.get('business_name', 'Unknown')} 时出错", e)
            
            # 6. 更新状态
            if eof:
                cmd_state_update(self.kb_root, {
                    "filesDoneAppend": chat_file,
                    "lastProcessedFile": None,
                    "lastOffsetLine": 0
                })
            else:
                cmd_state_update(self.kb_root, {"lastOffsetLine": next_line})
            
            # 7. 记录日志
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "file": chat_file,
                "processed_lines": len(lines),
                "updated_services": updated_businesses,
                "new_prices": new_prices,
                "next_offset": next_line,
                "eof": eof,
                "ai_extraction": True,
                "business_found": len(businesses) > 0,
                "potential_combinations": potential_combinations,
                "tokens_this_batch": {
                    "input_tokens": extractor_tokens["input_tokens"],
                    "output_tokens": extractor_tokens["output_tokens"],
                    "total_tokens": extractor_tokens["total_tokens"],
                    "interaction_time": extractor_tokens.get("interaction_time", 0)
                },
                "tokens_cumulative": {
                    "input_tokens": self.stats["tokens_used"]["input_tokens"],
                    "output_tokens": self.stats["tokens_used"]["output_tokens"],
                    "total_tokens": self.stats["tokens_used"]["total_tokens"]
                }
            }
            cmd_log_append(self.kb_root, {"jsonl": json.dumps(log_entry, ensure_ascii=False)})
            
            return {
            "success": True,
            "file_completed": eof,
            "lines_processed": len(lines),
            "services_updated": updated_businesses,
            "prices_added": new_prices,
            "next_offset": next_line,
            "ai_called": True,
            "business_found": len(businesses) > 0,
            "potential_combinations": potential_combinations,
            "tokens_used": extractor_tokens
            }
            
        except Exception as e:
            self.log_error(f"处理文件批次 {chat_file} 时出错", e)
            return {
                "success": False,
                "error": str(e),
                "ai_called": False
            }
    
    def _write_ai_extracted_content(self, business_slug: str, business_data: Dict[str, Any], source_file: str = ""):
        """写入AI提取的业务内容到知识库"""
        try:
            # 写入源文件路径信息（在文件开头）
            if source_file:
                source_info = f"---\n**数据来源：** `{source_file}`  \n**提取时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": business_slug,
                    "section": "摘要",
                    "markdown": source_info
                })
            
            # 写入业务描述摘要
            description = business_data.get("description", "")
            if description:
                summary = f"**{business_data.get('business_name', '')}**\n\n{description}\n\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": business_slug,
                    "section": "摘要",
                    "markdown": summary
                })
            
            # 写入输入文件（需要的文件）
            input_files = business_data.get("input_files", [])
            if input_files:
                files_md = "### AI提取的需要文件\n"
                for file_info in input_files:
                    doc_name = file_info.get("document_name", "")
                    doc_type = file_info.get("document_type", "")
                    quantity = file_info.get("quantity", 1)
                    consumable = file_info.get("consumable_in_this_task", False)
                    required = file_info.get("required", True)
                    notes = file_info.get("notes", "")
                    
                    files_md += f"- **{doc_name}**\n"
                    files_md += f"  - 类型：{doc_type} × {quantity}\n"
                    files_md += f"  - 必须：{'是' if required else '否'}\n"
                    files_md += f"  - 此业务处理：{'收走不归还' if consumable else '借用后归还'}\n"
                    if notes:
                        files_md += f"  - 说明：{notes}\n"
                    files_md += "\n"
                
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": business_slug,
                    "section": "材料/要求",
                    "markdown": files_md
                })
            
            # 写入输出文件（产出的文件）
            output_files = business_data.get("output_files", [])
            if output_files:
                output_md = "### AI提取的产出文件\n"
                for file_info in output_files:
                    doc_name = file_info.get("document_name", "")
                    doc_type = file_info.get("document_type", "")
                    quantity = file_info.get("quantity", 1)
                    output_md += f"- **{doc_name}** ({doc_type} × {quantity})\n"
                output_md += "\n"
                
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": business_slug,
                    "section": "办理流程",
                    "markdown": output_md
                })
            
            # 写入办理流程
            processes = business_data.get("processes", [])
            if processes:
                processes_md = "### AI提取的办理步骤\n" + "\n".join([f"{i+1}. {p}" for i, p in enumerate(processes)]) + "\n\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": business_slug,
                    "section": "办理流程",
                    "markdown": processes_md
                })
            
            # 写入注意事项
            notes = business_data.get("notes", [])
            if notes:
                notes_md = "### AI提取的注意事项\n" + "\n".join([f"- {n}" for n in notes]) + "\n\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": business_slug,
                    "section": "注意事项",
                    "markdown": notes_md
                })
            
            # 写入价格信息
            for price in business_data.get("prices", []):
                cmd_kb_upsert_pricing(self.kb_root, {
                    "slug": business_slug,
                    "entry": price
                })
            
            # 写入证据引用
            evidence_list = business_data.get("evidence_messages", [])
            if evidence_list:
                evidence_md = "### AI提取的聊天证据\n"
                for ev in evidence_list[:10]:  # 最多10条证据
                    msg_id = ev.get("message_id", "Unknown")
                    date = ev.get("date", "Unknown")
                    text = ev.get("text_summary", "")[:300]
                    evidence_md += f"- **消息 {msg_id}** ({date}): {text}\n"
                evidence_md += "\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": business_slug,
                    "section": "证据引用",
                    "markdown": evidence_md
                })
                
        except Exception as e:
            self.log_error(f"写入AI提取内容到业务 {business_slug} 时出错", e)
    
    def run_continuous_workflow(self, max_files: int = None, max_ai_calls: int = None) -> Dict[str, Any]:
        """运行连续工作流，处理所有文件"""
        self.stats["start_time"] = datetime.now()
        
        # 设置token统计开始时间
        if not self.stats["tokens_used"]["session_start"]:
            self.stats["tokens_used"]["session_start"] = self.stats["start_time"].isoformat()
        
        # 显示启动横幅
        self.show_banner()
        
        # 显示配置信息
        config_table = Table(title="工作流配置", show_header=True, header_style="bold cyan")
        config_table.add_column("配置项", style="yellow")
        config_table.add_column("值", style="green")
        config_table.add_row("最大文件数", str(max_files) if max_files else "无限制")
        config_table.add_row("最大AI调用", str(max_ai_calls) if max_ai_calls else "无限制") 
        config_table.add_row("批次行数", str(self.max_lines_per_batch))
        config_table.add_row("AI模型", self.selected_model or os.getenv('OPENAI_MODEL', 'gpt-4o'))
        config_table.add_row("知识库路径", str(self.kb_root))
        config_table.add_row("历史Token", f"{self.stats['tokens_used']['total_tokens']:,}" if self.stats['tokens_used']['total_tokens'] > 0 else "无")
        config_table.add_row("历史AI时间", f"{self.stats['tokens_used'].get('total_ai_time', 0):.1f}秒" if self.stats['tokens_used'].get('total_ai_time', 0) > 0 else "无")
        
        self.console.print(config_table)
        self.console.print()
        
        self.log_info(">> 开始AI驱动的业务知识提取工作流...")
        
        # 初始化系统
        cmd_init_kb(self.kb_root)
        
        # 获取总文件数用于进度条
        all_files = list_ordered_chat_files(self.organized_root)
        total_files = len(all_files)
        
        # 获取已处理的文件数量
        state = cmd_state_get(self.kb_root)
        files_done = state.get("filesDone", [])
        completed_files = len(files_done)
        
        # 显示恢复信息
        if completed_files > 0:
            self.console.print(f"[yellow]>> 检测到已处理 {completed_files} 个文件，将从上次进度继续...[/yellow]")
        
        # 创建进度条
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console,
            transient=False
        ) as progress:
            
            # 创建主任务，设置已完成的数量
            main_task = progress.add_task(
                "[cyan]处理文件进度", 
                total=max_files if max_files else total_files,
                completed=completed_files
            )
            
            try:
                while True:
                    # 检查AI调用限制
                    if max_ai_calls and self.stats["ai_calls"] >= max_ai_calls:
                        self.console.print(f"[yellow]>> 达到最大AI调用限制 {max_ai_calls}，停止处理[/yellow]")
                        break
                    
                    # 获取下一个文件
                    next_file_result = cmd_queue_get_next_file(self.kb_root, self.organized_root)
                    next_file = next_file_result.get("path")
                    
                    if not next_file:
                        self.console.print("[bold green]>> 所有文件处理完成，工作流结束[/bold green]")
                        break
                    
                    # 检查文件限制
                    if max_files and self.stats["files_processed"] >= max_files:
                        self.console.print(f"[yellow]>> 达到最大文件限制 {max_files}，停止处理[/yellow]")
                        break
                    
                    # 处理当前文件
                    file_name = Path(next_file).name
                    progress.update(main_task, description=f"[cyan]正在处理: {file_name}")
                    
                    self.console.print(f"\n[bold blue]>> 开始处理文件: {file_name}[/bold blue]")
                    
                    file_completed = False
                    while not file_completed:
                        # 处理一个批次
                        batch_result = self.process_single_file_batch(next_file)
                        
                        if not batch_result.get("success"):
                            self.log_error(f"批次处理失败: {batch_result.get('error', 'Unknown error')}")
                            break
                        
                        # 更新统计
                        self.stats["services_updated"] += len(batch_result.get("services_updated", []))
                        self.stats["prices_added"] += batch_result.get("prices_added", 0)
                        
                        lines_processed = batch_result.get("lines_processed", 0)
                        businesses_updated = batch_result.get("services_updated", [])
                        potential_combinations = batch_result.get("potential_combinations", [])
                        prices_added = batch_result.get("prices_added", 0)
                        ai_called = batch_result.get("ai_called", False)
                        business_found = batch_result.get("business_found", False)
                        
                        # 美化批次结果显示
                        if ai_called and business_found:
                            # 获取本批次token使用情况
                            batch_tokens = batch_result.get("tokens_used", {})
                            self.log_success(f"批次完成", {
                                "处理行数": lines_processed,
                                "AI分析": "是",
                                "发现业务": "是",
                                "更新业务": len(businesses_updated),
                                "新增价格": prices_added,
                                "本次Tokens": f"{batch_tokens.get('total_tokens', 0):,}" if batch_tokens else "0",
                                "AI耗时": f"{batch_tokens.get('interaction_time', 0):.2f}秒" if batch_tokens else "0秒"
                            })
                            
                            if businesses_updated:
                                business_text = Text("更新业务: ", style="cyan")
                                for i, business in enumerate(businesses_updated):
                                    if i > 0:
                                        business_text.append(", ")
                                    business_text.append(business, style="green bold")
                                self.console.print(business_text)
                            
                            if potential_combinations:
                                combo_text = Text("识别组合: ", style="yellow")
                                for i, combo in enumerate(potential_combinations):
                                    if i > 0:
                                        combo_text.append(", ")
                                    combo_text.append(combo.get("combination_name", "Unknown"), style="yellow bold")
                                self.console.print(combo_text)
                        else:
                            status_icon = "[AI]" if ai_called else "[SKIP]"
                            status_text = "AI分析完成" if ai_called else "快速跳过"
                            business_status = "未发现业务内容" if ai_called else "非业务文件"
                            self.console.print(f"{status_icon} [dim]{status_text}: {lines_processed}行, {business_status}[/dim]")
                        
                        file_completed = batch_result.get("file_completed", False)
                        
                        # 检查AI调用限制
                        if max_ai_calls and self.stats["ai_calls"] >= max_ai_calls:
                            break
                    
                    if file_completed:
                        self.stats["files_processed"] += 1
                        progress.update(main_task, advance=1)
                        self.console.print(f"[green]>> 文件处理完成: {file_name}[/green]")
                    
                    # 短暂暂停，避免API限制
                    time.sleep(0.5)
                    
            except KeyboardInterrupt:
                self.console.print("\n[red]>> 用户中断处理[/red]")
            except Exception as e:
                self.log_error("工作流执行异常", e)
                traceback.print_exc()
        
        self.stats["end_time"] = datetime.now()
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        # 保存最终token统计
        self._save_token_statistics()
        
        # 显示最终统计表
        self.show_final_statistics(duration)
        
        return {
            "success": True,
            "stats": self.stats,
            "duration": duration
        }
    
    def show_final_statistics(self, duration: float):
        """显示最终统计信息"""
        # 创建结果面板
        stats_table = Table(title="执行结果统计", show_header=True, header_style="bold magenta")
        stats_table.add_column("指标", style="cyan")
        stats_table.add_column("数值", style="green", justify="right")
        stats_table.add_column("单位", style="dim")
        
        # 添加统计行
        stats_table.add_row("执行时间", f"{duration:.2f}", "秒")
        stats_table.add_row("处理文件", str(self.stats['files_processed']), "个")
        stats_table.add_row("AI调用次数", str(self.stats['ai_calls']), "次")
        stats_table.add_row("更新服务", str(self.stats['services_updated']), "个")
        stats_table.add_row("添加价格", str(self.stats['prices_added']), "条")
        stats_table.add_row("错误次数", str(self.stats['errors']), "次")
        stats_table.add_row("", "", "")  # 分隔线
        stats_table.add_row("输入Tokens", f"{self.stats['tokens_used']['input_tokens']:,}", "个")
        stats_table.add_row("输出Tokens", f"{self.stats['tokens_used']['output_tokens']:,}", "个")
        stats_table.add_row("总Tokens", f"{self.stats['tokens_used']['total_tokens']:,}", "个")
        stats_table.add_row("AI交互次数", f"{self.stats['tokens_used'].get('ai_interactions', 0):,}", "次")
        stats_table.add_row("总AI耗时", f"{self.stats['tokens_used'].get('total_ai_time', 0):.1f}", "秒")
        
        # 计算效率指标和成本估算
        if duration > 0:
            files_per_minute = (self.stats['files_processed'] / duration) * 60
            ai_calls_per_minute = (self.stats['ai_calls'] / duration) * 60
            tokens_per_minute = (self.stats['tokens_used']['total_tokens'] / duration) * 60
            ai_time_percent = (self.stats['tokens_used'].get('total_ai_time', 0) / duration) * 100 if duration > 0 else 0
            
            # 简单成本估算 (基于GPT-4o定价)
            estimated_cost = self._estimate_cost()
            
            stats_table.add_row("", "", "")  # 分隔线
            stats_table.add_row("处理速度", f"{files_per_minute:.1f}", "文件/分钟")
            stats_table.add_row("AI调用速度", f"{ai_calls_per_minute:.1f}", "次/分钟")
            stats_table.add_row("Token速度", f"{tokens_per_minute:,.0f}", "个/分钟")
            stats_table.add_row("AI时间占比", f"{ai_time_percent:.1f}", "%")
            if estimated_cost > 0:
                stats_table.add_row("估算成本", f"${estimated_cost:.4f}", "USD")
    
    def _estimate_cost(self) -> float:
        """估算token使用成本 (基于GPT-4o定价)"""
        try:
            model = os.getenv('OPENAI_MODEL', 'gpt-4o').lower()
            
            # 定价表 (每1K tokens的美元价格)
            pricing = {
                'gpt-4o': {'input': 0.0025, 'output': 0.010},
                'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006}, 
                'gpt-4': {'input': 0.03, 'output': 0.06},
                'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
                'gpt-5-2025-08-07': {'input': 0.005, 'output': 0.020},  # GPT-5 估算价格
                'gpt-5-mini-2025-08-07': {'input': 0.0003, 'output': 0.0012}  # GPT-5-mini 估算价格
            }
            
            # 查找匹配的模型定价
            model_pricing = None
            for model_name, prices in pricing.items():
                if model_name in model:
                    model_pricing = prices
                    break
            
            if not model_pricing:
                return 0.0
            
            input_cost = (self.stats['tokens_used']['input_tokens'] / 1000) * model_pricing['input']
            output_cost = (self.stats['tokens_used']['output_tokens'] / 1000) * model_pricing['output']
            
            return input_cost + output_cost
            
        except Exception:
            return 0.0
        
        # 在面板中显示表格
        final_panel = Panel(
            stats_table,
            title="[bold green]>> 工作流执行完成[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print("\n")
        self.console.print(final_panel)

def select_model() -> str:
    """让用户选择AI模型"""
    print("="*60)
    print("  AI模型选择")
    print("="*60)
    
    # 获取可用模型
    model_1 = os.getenv("OPENAI_MODEL", "gpt-5-2025-08-07")
    model_2 = os.getenv("OPENAI_MODEL_MINI", "gpt-5-mini-2025-08-07")
    model_3 = "gpt-4o"
    
    print(f"1. {model_1} (GPT-5完整版，最强能力)")
    print(f"2. {model_2} (GPT-5 Mini版，平衡速度)")
    print(f"3. {model_3} (GPT-4o，高性能快速)")
    print()
    
    while True:
        try:
            choice = input("请选择模型 (1/2/3): ").strip()
            if choice == "1":
                print(f"已选择: {model_1}\n")
                return model_1
            elif choice == "2":
                print(f"已选择: {model_2}\n")
                return model_2
            elif choice == "3":
                print(f"已选择: {model_3}\n")
                return model_3
            else:
                print("请输入 1、2 或 3")
        except KeyboardInterrupt:
            print("\n已取消")
            sys.exit(0)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AI驱动的Telegram业务知识提取工作流")
    parser.add_argument("--max-files", type=int, default=None, help="最大处理文件数量，不指定则无限制")
    parser.add_argument("--max-ai-calls", type=int, default=None, help="最大AI调用次数，不指定则无限制")
    parser.add_argument("--max-lines", type=int, default=500, help="每批次最大行数")
    parser.add_argument("--kb-root", default=str(DEFAULT_KB_ROOT), help="知识库根目录")
    parser.add_argument("--organized-root", default=str(DEFAULT_ORGANIZED_ROOT), help="聊天文件根目录")
    parser.add_argument("--model", type=str, help="指定AI模型，不指定则交互选择")
    
    args = parser.parse_args()
    
    # 设置控制台输出编码避免中文显示问题
    if os.name == 'nt':  # Windows
        os.system('chcp 65001 > nul 2>&1')  # 设置UTF-8编码
    
    # 选择模型
    selected_model = args.model or select_model()
    
    # 创建工作流实例
    workflow = AITelegramWorkflow(
        kb_root=Path(args.kb_root),
        organized_root=Path(args.organized_root),
        max_lines_per_batch=args.max_lines,
        model_name=selected_model
    )
    
    # 运行工作流
    result = workflow.run_continuous_workflow(
        max_files=args.max_files,
        max_ai_calls=args.max_ai_calls
    )
    
    if result.get("success"):
        print(f"\nAI工作流成功完成！")
    else:
        print(f"\nAI工作流执行失败: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
