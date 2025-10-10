"""快速启动样式演示的脚本"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 现在可以导入了
from Kobe.SimulationTest.RichLogger_testplan.demo_beautiful_styles import (
    demo_combined_dashboard,
    demo_log_styles,
    demo_progress_styles,
    demo_table_styles,
    demo_panel_styles,
)

if __name__ == "__main__":
    print("\n选择要查看的演示：")
    print("1. 综合仪表盘（最漂亮，推荐）")
    print("2. 日志样式")
    print("3. 进度条样式")
    print("4. 表格样式")
    print("5. 面板样式")
    print("6. 全部演示")
    
    choice = input("\n请输入选项 (1-6，默认1): ").strip() or "1"
    
    demos = {
        "1": ("综合仪表盘", demo_combined_dashboard),
        "2": ("日志样式", demo_log_styles),
        "3": ("进度条样式", demo_progress_styles),
        "4": ("表格样式", demo_table_styles),
        "5": ("面板样式", demo_panel_styles),
    }
    
    if choice == "6":
        print("\n开始全部演示...\n")
        for name, func in demos.values():
            print(f"\n{'='*60}")
            print(f"演示: {name}")
            print(f"{'='*60}\n")
            func()
            input("\n按 Enter 继续下一个...")
    elif choice in demos:
        name, func = demos[choice]
        print(f"\n开始演示: {name}\n")
        func()
    else:
        print("无效选项，使用默认演示")
        demo_combined_dashboard()

