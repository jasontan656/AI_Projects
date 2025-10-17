#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# 添加脚本目录到路径
sys.path.append(str(Path(__file__).parent))

from batch_process_workflow import TelegramKnowledgeWorkflow, DEFAULT_KB_ROOT, DEFAULT_ORGANIZED_ROOT

def run_continuous_workflow():
    """运行连续工作流，处理所有文件"""
    print("🚀 启动连续工作流...")
    print("📝 这将处理所有Telegram聊天文件并提取业务知识")
    print("⏱️  预计需要较长时间，请耐心等待...")
    print("🔄 按Ctrl+C可以随时中断\n")
    
    workflow = TelegramKnowledgeWorkflow(
        kb_root=Path(DEFAULT_KB_ROOT),
        organized_root=Path(DEFAULT_ORGANIZED_ROOT),
        max_lines_per_batch=500  # 每批次500行，平衡速度和内存
    )
    
    try:
        result = workflow.run_workflow_cycle()
        
        if result.get("success"):
            print("\n✅ 工作流执行成功完成！")
            return True
        else:
            print(f"\n❌ 工作流执行失败: {result.get('error', 'Unknown error')}")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️  用户中断了工作流执行")
        return False

def run_test_workflow():
    """运行测试工作流，只处理少量文件"""
    print("🧪 启动测试工作流...")
    print("📝 这将处理前5个文件作为测试\n")
    
    workflow = TelegramKnowledgeWorkflow(
        kb_root=Path(DEFAULT_KB_ROOT),
        organized_root=Path(DEFAULT_ORGANIZED_ROOT),
        max_lines_per_batch=300
    )
    
    result = workflow.run_workflow_cycle(max_files=5)
    
    if result.get("success"):
        print("\n✅ 测试工作流执行完成！")
        return True
    else:
        print(f"\n❌ 测试工作流执行失败: {result.get('error', 'Unknown error')}")
        return False

def run_batch_workflow():
    """运行批量工作流，处理指定数量的批次"""
    print("📦 启动批量工作流...")
    
    try:
        batch_count = int(input("请输入要处理的批次数量 (建议10-50): "))
    except ValueError:
        batch_count = 10
        print(f"输入无效，使用默认值: {batch_count}")
    
    print(f"📝 这将处理 {batch_count} 个批次\n")
    
    workflow = TelegramKnowledgeWorkflow(
        kb_root=Path(DEFAULT_KB_ROOT),
        organized_root=Path(DEFAULT_ORGANIZED_ROOT),
        max_lines_per_batch=400
    )
    
    result = workflow.run_workflow_cycle(max_batches=batch_count)
    
    if result.get("success"):
        print("\n✅ 批量工作流执行完成！")
        return True
    else:
        print(f"\n❌ 批量工作流执行失败: {result.get('error', 'Unknown error')}")
        return False

def show_status():
    """显示当前处理状态"""
    from kb_tools import cmd_state_get, cmd_kb_load_index, list_ordered_chat_files
    
    kb_root = Path(DEFAULT_KB_ROOT)
    organized_root = Path(DEFAULT_ORGANIZED_ROOT)
    
    print("📊 当前状态:")
    print("-" * 40)
    
    try:
        # 获取状态
        state = cmd_state_get(kb_root)
        index = cmd_kb_load_index(kb_root)
        all_files = list_ordered_chat_files(organized_root)
        files_done = set(state.get("filesDone", []))
        
        print(f"📁 总文件数: {len(all_files)}")
        print(f"✅ 已完成: {len(files_done)}")
        print(f"⏳ 待处理: {len(all_files) - len(files_done)}")
        print(f"📋 知识库服务数: {len(index.get('services', []))}")
        
        current_file = state.get("lastProcessedFile")
        if current_file:
            print(f"🔄 当前处理: {Path(current_file).name}")
            print(f"📍 当前偏移: {state.get('lastOffsetLine', 0)} 行")
        else:
            print("🔄 当前处理: 无")
            
    except Exception as e:
        print(f"❌ 获取状态失败: {e}")

def main():
    print("=" * 60)
    print("🤖 Telegram 业务知识提取工作流控制台")  
    print("=" * 60)
    
    while True:
        print("\n请选择操作:")
        print("1. 📊 查看当前状态")
        print("2. 🧪 运行测试工作流 (处理前5个文件)")
        print("3. 📦 运行批量工作流 (指定批次数)")
        print("4. 🚀 运行连续工作流 (处理所有文件)")
        print("5. 🚪 退出")
        
        try:
            choice = input("\n请输入选项 (1-5): ").strip()
            
            if choice == "1":
                show_status()
            elif choice == "2":
                run_test_workflow()
            elif choice == "3":
                run_batch_workflow()
            elif choice == "4":
                confirm = input("⚠️  这将处理大量文件，确定继续吗? (y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    run_continuous_workflow()
                else:
                    print("已取消操作")
            elif choice == "5":
                print("👋 再见！")
                break
            else:
                print("❌ 无效选项，请重新选择")
                
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 执行出错: {e}")

if __name__ == "__main__":
    main()
