#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import traceback

# 导入kb_tools的函数
sys.path.append(str(Path(__file__).parent))
from kb_tools import (
    DEFAULT_KB_ROOT, DEFAULT_ORGANIZED_ROOT, cmd_init_kb, cmd_state_get, cmd_state_update,
    cmd_queue_get_next_file, cmd_chat_read_lines, cmd_kb_load_index, 
    cmd_kb_upsert_service, cmd_kb_append_markdown, cmd_kb_upsert_pricing, 
    cmd_kb_save_index, cmd_log_append, slugify, list_ordered_chat_files
)

from process_single_chat import extract_business_info_from_lines

class TelegramKnowledgeWorkflow:
    def __init__(self, kb_root: Path = None, organized_root: Path = None, max_lines_per_batch: int = 800):
        self.kb_root = kb_root or Path(DEFAULT_KB_ROOT)
        self.organized_root = organized_root or Path(DEFAULT_ORGANIZED_ROOT)  
        self.max_lines_per_batch = max_lines_per_batch
        self.stats = {
            "files_processed": 0,
            "services_updated": 0,
            "prices_added": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
        
    def log_info(self, message: str):
        """记录信息日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] INFO: {message}")
        
    def log_error(self, message: str, error: Exception = None):
        """记录错误日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ERROR: {message}")
        if error:
            print(f"[{timestamp}] ERROR DETAIL: {str(error)}")
        self.stats["errors"] += 1
        
    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            self.log_info("初始化知识库系统...")
            result = cmd_init_kb(self.kb_root)
            if result.get("ok"):
                self.log_info("知识库初始化成功")
                return True
            else:
                self.log_error(f"知识库初始化失败: {result}")
                return False
        except Exception as e:
            self.log_error("系统初始化异常", e)
            return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取处理队列状态"""
        try:
            # 获取当前状态
            state = cmd_state_get(self.kb_root)
            
            # 获取所有聊天文件
            all_files = list_ordered_chat_files(self.organized_root)
            files_done = set(state.get("filesDone", []))
            
            pending_files = []
            for f in all_files:
                if str(f) not in files_done:
                    pending_files.append(str(f))
            
            # 当前正在处理的文件
            current_file = state.get("lastProcessedFile")
            current_offset = state.get("lastOffsetLine", 0)
            
            return {
                "total_files": len(all_files),
                "completed_files": len(files_done), 
                "pending_files": len(pending_files),
                "current_file": current_file,
                "current_offset": current_offset,
                "pending_list": pending_files[:5]  # 只显示前5个
            }
        except Exception as e:
            self.log_error("获取队列状态失败", e)
            return {}
    
    def process_single_file_batch(self, chat_file: str) -> Dict[str, Any]:
        """处理单个文件的一个批次"""
        try:
            # 1. 获取当前状态
            state = cmd_state_get(self.kb_root)
            
            # 2. 确保状态正确
            if state.get("lastProcessedFile") != chat_file:
                cmd_state_update(self.kb_root, {"lastProcessedFile": chat_file})
                state = cmd_state_get(self.kb_root)  # 重新获取
            
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
                        "prices_added": 0
                    }
                else:
                    return {
                        "success": False,
                        "error": "无法读取文件内容"
                    }
            
            # 4. 提取业务信息
            business_info = extract_business_info_from_lines(lines)
            services = business_info["services"]
            
            updated_services = []
            new_prices = 0
            
            # 5. 处理提取到的服务
            if services:
                for slug, service_info in services.items():
                    try:
                        # 创建/更新服务
                        upsert_result = cmd_kb_upsert_service(self.kb_root, {
                            "name": service_info["name"],
                            "aliases": service_info["aliases"],
                            "categories": service_info["categories"]
                        })
                        
                        if upsert_result.get("ok"):
                            service_slug = upsert_result["slug"]
                            updated_services.append(service_slug)
                            
                            # 写入各种内容
                            self._write_service_content(service_slug, service_info)
                            
                            # 计算价格数量
                            new_prices += len(service_info.get("prices", []))
                            
                    except Exception as e:
                        self.log_error(f"处理服务 {service_info['name']} 时出错", e)
            
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
                "updated_services": updated_services,
                "new_prices": new_prices,
                "next_offset": next_line,
                "eof": eof
            }
            cmd_log_append(self.kb_root, {"jsonl": json.dumps(log_entry, ensure_ascii=False)})
            
            return {
                "success": True,
                "file_completed": eof,
                "lines_processed": len(lines),
                "services_updated": updated_services,
                "prices_added": new_prices,
                "next_offset": next_line
            }
            
        except Exception as e:
            self.log_error(f"处理文件批次 {chat_file} 时出错", e)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _write_service_content(self, service_slug: str, service_info: Dict[str, Any]):
        """写入服务内容到知识库"""
        try:
            # 写入摘要
            if service_info.get("description"):
                summary = f"**{service_info['name']}**\n\n{service_info['description']}\n\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": service_slug,
                    "section": "摘要",
                    "markdown": summary
                })
            
            # 写入材料要求
            if service_info.get("materials"):
                materials_md = "### 所需材料\n" + "\n".join([f"- {m}" for m in service_info["materials"]]) + "\n\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": service_slug,
                    "section": "材料/要求",
                    "markdown": materials_md
                })
            
            # 写入注意事项
            if service_info.get("notes"):
                notes_md = "### 注意事项\n" + "\n".join([f"- {n}" for n in service_info["notes"]]) + "\n\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": service_slug,
                    "section": "办理流程", 
                    "markdown": notes_md
                })
            
            # 写入价格信息
            for price in service_info.get("prices", []):
                cmd_kb_upsert_pricing(self.kb_root, {
                    "slug": service_slug,
                    "entry": price
                })
            
            # 写入证据引用
            if service_info.get("evidence"):
                evidence_md = "### 聊天证据\n"
                for ev in service_info["evidence"][:3]:  # 最多3条证据
                    evidence_md += f"- **消息 {ev['message_id']}** ({ev['date']}): {ev['text']}\n"
                evidence_md += "\n"
                cmd_kb_append_markdown(self.kb_root, {
                    "slug": service_slug,
                    "section": "证据引用",
                    "markdown": evidence_md
                })
                
        except Exception as e:
            self.log_error(f"写入服务内容 {service_slug} 时出错", e)
    
    def run_workflow_cycle(self, max_files: int = None, max_batches: int = None) -> Dict[str, Any]:
        """运行工作流循环"""
        self.stats["start_time"] = datetime.now()
        self.log_info("开始工作流循环执行...")
        
        # 初始化系统
        if not self.initialize_system():
            return {"success": False, "error": "系统初始化失败"}
        
        batch_count = 0
        
        try:
            while True:
                # 检查批次限制
                if max_batches and batch_count >= max_batches:
                    self.log_info(f"达到最大批次限制 {max_batches}，停止处理")
                    break
                
                # 获取下一个文件
                next_file_result = cmd_queue_get_next_file(self.kb_root, self.organized_root)
                next_file = next_file_result.get("path")
                
                if not next_file:
                    self.log_info("所有文件处理完成，工作流结束")
                    break
                
                # 检查文件限制
                if max_files and self.stats["files_processed"] >= max_files:
                    self.log_info(f"达到最大文件限制 {max_files}，停止处理")
                    break
                
                # 显示当前队列状态
                queue_status = self.get_queue_status()
                self.log_info(f"队列状态: 总计 {queue_status.get('total_files', 0)} 文件, "
                             f"已完成 {queue_status.get('completed_files', 0)}, "
                             f"待处理 {queue_status.get('pending_files', 0)}")
                
                # 处理当前文件
                self.log_info(f"开始处理文件: {Path(next_file).name}")
                
                file_completed = False
                while not file_completed:
                    # 处理一个批次
                    batch_result = self.process_single_file_batch(next_file)
                    batch_count += 1
                    
                    if not batch_result.get("success"):
                        self.log_error(f"批次处理失败: {batch_result.get('error', 'Unknown error')}")
                        break
                    
                    # 更新统计
                    self.stats["services_updated"] += len(batch_result.get("services_updated", []))
                    self.stats["prices_added"] += batch_result.get("prices_added", 0)
                    
                    lines_processed = batch_result.get("lines_processed", 0)
                    services_updated = batch_result.get("services_updated", [])
                    prices_added = batch_result.get("prices_added", 0)
                    
                    self.log_info(f"批次 {batch_count}: 处理 {lines_processed} 行, "
                                 f"更新 {len(services_updated)} 服务, 添加 {prices_added} 价格")
                    
                    file_completed = batch_result.get("file_completed", False)
                    
                    # 如果达到批次限制，退出
                    if max_batches and batch_count >= max_batches:
                        break
                
                if file_completed:
                    self.stats["files_processed"] += 1
                    self.log_info(f"文件处理完成: {Path(next_file).name}")
                
                # 短暂暂停，避免过度占用资源
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.log_info("用户中断处理")
        except Exception as e:
            self.log_error("工作流执行异常", e)
            traceback.print_exc()
        
        self.stats["end_time"] = datetime.now()
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        # 最终统计
        self.log_info("=" * 50)
        self.log_info("工作流执行完成！")
        self.log_info(f"执行时间: {duration:.2f} 秒")
        self.log_info(f"处理文件: {self.stats['files_processed']} 个")
        self.log_info(f"更新服务: {self.stats['services_updated']} 个")
        self.log_info(f"添加价格: {self.stats['prices_added']} 条")
        self.log_info(f"执行批次: {batch_count} 次")
        self.log_info(f"错误次数: {self.stats['errors']} 次")
        self.log_info("=" * 50)
        
        return {
            "success": True,
            "stats": self.stats,
            "batch_count": batch_count,
            "duration": duration
        }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Telegram 业务知识提取工作流")
    parser.add_argument("--max-files", type=int, help="最大处理文件数量")
    parser.add_argument("--max-batches", type=int, help="最大处理批次数量") 
    parser.add_argument("--max-lines", type=int, default=800, help="每批次最大行数")
    parser.add_argument("--kb-root", default=str(DEFAULT_KB_ROOT), help="知识库根目录")
    parser.add_argument("--organized-root", default=str(DEFAULT_ORGANIZED_ROOT), help="聊天文件根目录")
    
    args = parser.parse_args()
    
    # 创建工作流实例
    workflow = TelegramKnowledgeWorkflow(
        kb_root=Path(args.kb_root),
        organized_root=Path(args.organized_root),
        max_lines_per_batch=args.max_lines
    )
    
    # 运行工作流
    result = workflow.run_workflow_cycle(
        max_files=args.max_files,
        max_batches=args.max_batches
    )
    
    if result.get("success"):
        print(f"\n工作流成功完成！")
    else:
        print(f"\n工作流执行失败: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
