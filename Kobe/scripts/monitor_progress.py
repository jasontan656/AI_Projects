#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加脚本目录到路径
sys.path.append(str(Path(__file__).parent))
from kb_tools import (
    DEFAULT_KB_ROOT, DEFAULT_ORGANIZED_ROOT, cmd_state_get, cmd_kb_load_index, 
    list_ordered_chat_files
)

def show_progress():
    """显示处理进度"""
    kb_root = Path(DEFAULT_KB_ROOT)
    organized_root = Path(DEFAULT_ORGANIZED_ROOT)
    
    try:
        # 获取状态
        state = cmd_state_get(kb_root)
        index = cmd_kb_load_index(kb_root)
        all_files = list_ordered_chat_files(organized_root)
        files_done = set(state.get("filesDone", []))
        
        # 计算进度
        total_files = len(all_files)
        completed_files = len(files_done)
        pending_files = total_files - completed_files
        progress_percent = (completed_files / total_files * 100) if total_files > 0 else 0
        
        # 当前处理状态
        current_file = state.get("lastProcessedFile")
        current_offset = state.get("lastOffsetLine", 0)
        
        # 知识库统计
        services_count = len(index.get("services", []))
        
        # 读取最新日志
        logs_dir = kb_root / "logs"
        latest_log = None
        if logs_dir.exists():
            log_files = list(logs_dir.glob("run-*.jsonl"))
            if log_files:
                latest_log_file = max(log_files, key=lambda x: x.stat().st_mtime)
                try:
                    with open(latest_log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            latest_log = json.loads(lines[-1].strip())
                except:
                    pass
        
        print("="*60)
        print("AI驱动的Telegram业务知识提取 - 进度监控")
        print("="*60)
        print(f"总体进度: {completed_files}/{total_files} ({progress_percent:.1f}%)")
        print(f"待处理文件: {pending_files}")
        print(f"知识库服务数: {services_count}")
        
        # 显示token统计
        token_stats = state.get("tokens_cumulative", {})
        if token_stats.get("total_tokens", 0) > 0:
            print(f"累积Token使用: {token_stats['total_tokens']:,}")
        print()
        
        if current_file:
            file_name = Path(current_file).name
            print(f"当前处理: {file_name}")
            print(f"处理偏移: {current_offset} 行")
        else:
            print("当前处理: 无（可能已完成或等待中）")
        
        print()
        
        if latest_log:
            print("最新处理记录:")
            timestamp = latest_log.get("timestamp", "Unknown")
            file_name = Path(latest_log.get("file", "")).name
            processed_lines = latest_log.get("processed_lines", 0)
            updated_services = latest_log.get("updated_services", [])
            new_prices = latest_log.get("new_prices", 0)
            ai_extraction = latest_log.get("ai_extraction", False)
            business_found = latest_log.get("business_found", False)
            
            print(f"时间: {timestamp[:19]}")
            print(f"文件: {file_name}")
            print(f"处理行数: {processed_lines}")
            print(f"AI分析: {'是' if ai_extraction else '否'}")
            print(f"发现业务: {'是' if business_found else '否'}")
            print(f"更新服务: {len(updated_services)}")
            print(f"新增价格: {new_prices}")
            
            if updated_services:
                print(f"服务列表: {', '.join(updated_services)}")
            
            # 显示token使用
            batch_tokens = latest_log.get("tokens_this_batch", {})
            cumulative_tokens = latest_log.get("tokens_cumulative", {})
            if batch_tokens.get("total_tokens", 0) > 0:
                print(f"本次Token: {batch_tokens['total_tokens']:,}")
            if cumulative_tokens.get("total_tokens", 0) > 0:
                print(f"累积Token: {cumulative_tokens['total_tokens']:,}")
        
        print()
        print("="*60)
        
        # 返回进度信息用于脚本判断
        return {
            "total_files": total_files,
            "completed_files": completed_files,
            "pending_files": pending_files,
            "progress_percent": progress_percent,
            "current_processing": current_file is not None,
            "services_count": services_count
        }
        
    except Exception as e:
        print(f"获取进度失败: {e}")
        return None

if __name__ == "__main__":
    show_progress()
