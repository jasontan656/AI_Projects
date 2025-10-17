#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
无限制运行AI业务知识提取工作流
- 处理所有2081个Telegram聊天文件
- 无文件数量和AI调用次数限制
- 支持断点续传
- 500行/批次的合理配置
"""

import os
import sys
from pathlib import Path

# 添加脚本目录到路径
sys.path.append(str(Path(__file__).parent))

from ai_powered_extraction import AITelegramWorkflow, DEFAULT_KB_ROOT, DEFAULT_ORGANIZED_ROOT

def main():
    """运行无限制的AI提取工作流"""
    
    # 设置控制台编码避免显示问题
    if os.name == 'nt':  # Windows
        os.system('chcp 65001 > nul 2>&1')
    
    print("="*80)
    print("  🤖 AI驱动的Telegram业务知识提取 - 无限制运行模式")
    print("="*80)
    print()
    print("运行配置:")
    print("  ✓ 无文件数量限制 (将处理全部2081个文件)")
    print("  ✓ 无AI调用次数限制")  
    print("  ✓ 每批次500行 (平衡速度与质量)")
    print("  ✓ 支持断点续传")
    print("  ✓ Ctrl+C可随时安全中断")
    print()
    print("预计运行时间: 数小时 (取决于文件内容和网络)")
    print("="*80)
    print()
    
    # 模型选择
    def select_model():
        print("选择AI模型:")
        model_1 = os.getenv("OPENAI_MODEL", "gpt-5-2025-08-07")
        model_2 = os.getenv("OPENAI_MODEL_MINI", "gpt-5-mini-2025-08-07")
        print(f"1. {model_1} (完整版)")
        print(f"2. {model_2} (Mini版)")
        
        while True:
            try:
                choice = input("请选择 (1/2): ").strip()
                if choice == "1":
                    return model_1
                elif choice == "2":
                    return model_2
                else:
                    print("请输入 1 或 2")
            except KeyboardInterrupt:
                print("\n已取消")
                sys.exit(0)
    
    selected_model = select_model()
    print(f"已选择: {selected_model}")
    print()
    
    # 创建工作流实例 - 无任何限制
    workflow = AITelegramWorkflow(
        kb_root=Path(DEFAULT_KB_ROOT),
        organized_root=Path(DEFAULT_ORGANIZED_ROOT),
        max_lines_per_batch=500,  # 只限制批次大小
        model_name=selected_model
    )
    
    try:
        print("🚀 启动无限制AI提取工作流...\n")
        
        # 运行完全无限制的工作流
        result = workflow.run_continuous_workflow(
            max_files=None,        # 无文件限制
            max_ai_calls=None      # 无AI调用限制
        )
        
        if result.get("success"):
            print("\n" + "="*80)
            print("  🎉 完整AI提取工作流执行成功完成！")
            print("="*80)
        else:
            print(f"\n❌ 工作流执行失败: {result.get('error', 'Unknown error')}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断了工作流")
        print("💾 已保存当前进度，下次运行时会从断点继续")
        print("📊 可运行 python scripts/monitor_progress.py 查看进度")
    except Exception as e:
        print(f"\n❌ 工作流异常: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    
    # 显示结束提示
    print("\n" + "="*80)
    if exit_code == 0:
        print("  📋 运行完成，可查看知识库文件:")
        print("     D:/AI_Projects/.TelegramChatHistory/KB/services/")
    print("="*80)
    
    sys.exit(exit_code)
