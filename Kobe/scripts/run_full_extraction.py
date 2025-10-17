#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

# 添加脚本目录到路径
sys.path.append(str(Path(__file__).parent))

from ai_powered_extraction import AITelegramWorkflow, DEFAULT_KB_ROOT, DEFAULT_ORGANIZED_ROOT

def main():
    """运行完整的无限制AI提取工作流"""
    
    print("=" * 80)
    print("          AI驱动的Telegram业务知识提取 - 完整运行模式")
    print("=" * 80)
    print("配置:")
    print("  - 无文件数限制 (处理全部2081个文件)")
    print("  - 无AI调用次数限制")
    print("  - 每批次处理500行")
    print("  - 按Ctrl+C可以随时安全中断")
    print("  - 支持断点续传，中断后可继续")
    print("=" * 80)
    print()
    
    # 用户确认
    try:
        confirm = input("是否开始完整提取工作流？这可能需要数小时 (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("已取消操作")
            return
    except KeyboardInterrupt:
        print("\n已取消操作")
        return
    
    print("\n>> 启动完整AI提取工作流...")
    
    # 创建工作流实例
    workflow = AITelegramWorkflow(
        kb_root=Path(DEFAULT_KB_ROOT),
        organized_root=Path(DEFAULT_ORGANIZED_ROOT),
        max_lines_per_batch=500  # 每批次500行，平衡速度和质量
    )
    
    try:
        # 运行无限制工作流（不设max_files和max_ai_calls）
        result = workflow.run_continuous_workflow()
        
        if result.get("success"):
            print("\n" + "=" * 80)
            print("          完整AI提取工作流执行成功完成！")
            print("=" * 80)
            
            stats = result.get("stats", {})
            print(f"最终统计:")
            print(f"  处理文件: {stats.get('files_processed', 0)} 个")
            print(f"  AI调用: {stats.get('ai_calls', 0)} 次")  
            print(f"  提取服务: {stats.get('services_updated', 0)} 个")
            print(f"  添加价格: {stats.get('prices_added', 0)} 条")
            print(f"  执行时间: {result.get('duration', 0):.2f} 秒")
        else:
            print(f"\n工作流执行失败: {result.get('error', 'Unknown error')}")
            return 1
            
    except KeyboardInterrupt:
        print("\n>> 用户中断了工作流")
        print(">> 已保存当前进度，下次运行时会从断点继续")
    except Exception as e:
        print(f"\n>> 工作流异常: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
