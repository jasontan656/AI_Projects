#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

# 导入kb_tools的函数
sys.path.append(str(Path(__file__).parent))
from kb_tools import (
    DEFAULT_KB_ROOT, cmd_init_kb, cmd_state_get, cmd_state_update,
    cmd_chat_read_lines, cmd_kb_load_index, cmd_kb_upsert_service,
    cmd_kb_append_markdown, cmd_kb_upsert_pricing, cmd_kb_save_index,
    cmd_log_append, slugify
)

def extract_business_info_from_lines(lines: List[str], chat_id: str = "unknown") -> Dict[str, Any]:
    """从聊天记录行中提取业务相关信息"""
    services = {}  # slug -> service_info
    
    # 解析聊天头信息
    chat_name = "unknown"
    if lines and lines[0]:
        try:
            header = json.loads(lines[0])
            if header.get("_kind") == "chat_header":
                chat_name = header.get("name", "unknown")
                chat_id = str(header.get("id", chat_id))
        except json.JSONDecodeError:
            pass
    
    # 分析消息内容寻找业务信息
    for line in lines[1:]:  # 跳过头部
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            if msg.get("_kind") != "message":
                continue
                
            text = msg.get("text", "")
            # 处理text可能是list的情况
            if isinstance(text, list):
                text = " ".join([str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in text])
            text = str(text)
            
            date = msg.get("date", "")
            msg_id = msg.get("id")
            
            # 检测业务相关关键词
            if any(keyword in text.lower() for keyword in [
                "passport", "护照", "签证", "visa", "申请", "application", 
                "材料", "document", "requirement", "process", "办理", 
                "价格", "price", "费用", "cost", "consultation", "咨询"
            ]):
                # 确定服务类型
                service_name = ""
                aliases = []
                
                if "chinese passport" in text.lower() or "中国护照" in text:
                    service_name = "中国护照申请"
                    aliases = ["Chinese Passport", "中国护照"]
                elif "passport" in text.lower() or "护照" in text:
                    service_name = "护照申请服务"
                    aliases = ["passport", "护照"]
                elif "consultation" in text.lower() or "咨询" in text:
                    service_name = "法律咨询服务"  
                    aliases = ["consultation", "咨询", "法律咨询"]
                else:
                    service_name = "签证服务"
                    aliases = ["visa", "签证"]
                
                # 为服务创建条目
                slug = slugify(service_name)
                if slug not in services:
                    services[slug] = {
                        "name": service_name,
                        "slug": slug,
                        "aliases": aliases,
                        "categories": ["visa"] if "visa" in service_name.lower() or "签证" in service_name else ["document"],
                        "description": f"从聊天记录中提取的{service_name}相关信息",
                        "materials": [],
                        "processes": [],
                        "prices": [],
                        "notes": [],
                        "evidence": [],
                        "chat_id": chat_id,
                        "sources": []
                    }
                
                service = services[slug]
                
                # 提取材料要求
                if any(word in text.lower() for word in ["requirement", "document", "材料", "需要", "need"]):
                    if "father consent" in text.lower():
                        service["materials"].append("父亲同意书")
                    if "notarized" in text.lower() or "公证" in text:
                        service["materials"].append("公证文件")
                    if "affidavit" in text.lower():
                        service["materials"].append("宣誓书")
                    if "paternity" in text.lower():
                        service["materials"].append("亲子关系证明")
                
                # 提取价格信息
                if "free" in text.lower() or "免费" in text:
                    service["prices"].append({
                        "currency": "PHP",
                        "amount": "0",
                        "effective_date": date[:10] if date else datetime.now().strftime("%Y-%m-%d"),
                        "conditions": "免费面谈咨询",
                        "notes": "需要预约办公室",
                        "evidence": {
                            "file": f"dialogs/-------_{chat_id}.jsonl",
                            "message_ids": [msg_id] if msg_id else [],
                            "dates": [date[:10]] if date else []
                        }
                    })
                elif "pay" in text.lower() or "付费" in text:
                    service["prices"].append({
                        "currency": "PHP",
                        "amount": "未知",
                        "effective_date": date[:10] if date else datetime.now().strftime("%Y-%m-%d"),
                        "conditions": "在线咨询",
                        "notes": "付费在线咨询服务",
                        "evidence": {
                            "file": f"dialogs/-------_{chat_id}.jsonl",
                            "message_ids": [msg_id] if msg_id else [],
                            "dates": [date[:10]] if date else []
                        }
                    })
                
                # 提取注意事项
                if any(word in text.lower() for word in ["might not accept", "embassy", "不接受", "可能"]):
                    service["notes"].append("大使馆可能因父亲同意问题拒绝申请")
                
                if any(word in text.lower() for word in ["not married", "未婚", "not legally"]):
                    service["notes"].append("父母未婚状态可能影响申请")
                
                # 添加证据
                service["evidence"].append({
                    "file": f"dialogs/-------_{chat_id}.jsonl",
                    "message_id": msg_id,
                    "date": date[:10] if date else datetime.now().strftime("%Y-%m-%d"),
                    "text": text[:200] + "..." if len(text) > 200 else text
                })
                
        except json.JSONDecodeError:
            continue
    
    return {"services": services, "chat_id": chat_id, "chat_name": chat_name}

def process_single_chat_file(chat_file: str, kb_root: Path, max_lines: int = 800) -> str:
    """处理单个聊天文件"""
    
    # 1. 获取状态
    state = cmd_state_get(kb_root)
    
    # 2. 更新状态
    if state.get("lastProcessedFile") != chat_file:
        cmd_state_update(kb_root, {"lastProcessedFile": chat_file})
    
    # 3. 读取聊天内容
    read_result = cmd_chat_read_lines({
        "path": chat_file,
        "start_line": state.get("lastOffsetLine", 0) + 1,
        "max_lines": max_lines
    })
    
    if not read_result.get("lines"):
        return "没有读取到聊天内容"
    
    lines = read_result["lines"]
    next_line = read_result["next_line"]
    eof = read_result["eof"]
    
    # 4. 提取业务信息
    business_info = extract_business_info_from_lines(lines)
    services = business_info["services"]
    chat_id = business_info["chat_id"]
    chat_name = business_info["chat_name"]
    
    if not services:
        # 无业务内容，仅更新偏移
        cmd_state_update(kb_root, {"lastOffsetLine": next_line})
        return f"处理 {Path(chat_file).name}，未发现业务内容，偏移至 {next_line}"
    
    # 5. 加载现有索引
    index = cmd_kb_load_index(kb_root)
    
    updated_services = []
    new_prices = 0
    
    # 6. 处理每个服务
    for slug, service_info in services.items():
        # 创建/更新服务
        upsert_result = cmd_kb_upsert_service(kb_root, {
            "name": service_info["name"],
            "aliases": service_info["aliases"],
            "categories": service_info["categories"]
        })
        
        if upsert_result.get("ok"):
            service_slug = upsert_result["slug"]
            updated_services.append(service_slug)
            
            # 写入摘要
            summary = f"**{service_info['name']}**\n\n{service_info['description']}\n\n"
            cmd_kb_append_markdown(kb_root, {
                "slug": service_slug,
                "section": "摘要",
                "markdown": summary
            })
            
            # 写入材料要求
            if service_info["materials"]:
                materials_md = "### 所需材料\n" + "\n".join([f"- {m}" for m in service_info["materials"]]) + "\n\n"
                cmd_kb_append_markdown(kb_root, {
                    "slug": service_slug,
                    "section": "材料/要求",
                    "markdown": materials_md
                })
            
            # 写入注意事项  
            if service_info["notes"]:
                notes_md = "### 注意事项\n" + "\n".join([f"- {n}" for n in service_info["notes"]]) + "\n\n"
                cmd_kb_append_markdown(kb_root, {
                    "slug": service_slug,
                    "section": "办理流程",
                    "markdown": notes_md
                })
            
            # 写入价格信息
            for price in service_info["prices"]:
                cmd_kb_upsert_pricing(kb_root, {
                    "slug": service_slug,
                    "entry": price
                })
                new_prices += 1
            
            # 写入证据引用
            if service_info["evidence"]:
                evidence_md = "### 聊天证据\n"
                for ev in service_info["evidence"][:3]:  # 最多3条证据
                    evidence_md += f"- **消息 {ev['message_id']}** ({ev['date']}): {ev['text']}\n"
                evidence_md += "\n"
                cmd_kb_append_markdown(kb_root, {
                    "slug": service_slug,
                    "section": "证据引用",
                    "markdown": evidence_md
                })
    
    # 7. 保存索引（重新加载以确保最新状态）
    updated_index = cmd_kb_load_index(kb_root)
    cmd_kb_save_index(kb_root, {"services": updated_index["services"]})
    
    # 8. 更新处理状态
    if eof:
        cmd_state_update(kb_root, {
            "filesDoneAppend": chat_file,
            "lastProcessedFile": None,
            "lastOffsetLine": 0
        })
    else:
        cmd_state_update(kb_root, {"lastOffsetLine": next_line})
    
    # 9. 记录日志
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "file": chat_file,
        "processed_lines": len(lines),
        "updated_services": updated_services,
        "new_prices": new_prices,
        "next_offset": next_line,
        "eof": eof
    }
    cmd_log_append(kb_root, {"jsonl": json.dumps(log_entry, ensure_ascii=False)})
    
    return f"处理 {Path(chat_file).name}，更新服务 {len(updated_services)} 个，新增价格 {new_prices} 条，偏移至 {next_line}"

if __name__ == "__main__":
    # 处理指定的聊天文件
    chat_file = "D:/AI_Projects/.TelegramChatHistory/Organized/dialogs/-------_1689868225.jsonl"
    kb_root = Path(DEFAULT_KB_ROOT)
    
    # 初始化知识库
    cmd_init_kb(kb_root)
    
    try:
        result = process_single_chat_file(chat_file, kb_root, max_lines=800)
        print(result)
    except Exception as e:
        print(f"处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
