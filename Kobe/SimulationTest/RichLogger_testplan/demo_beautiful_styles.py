"""Rich 精美样式展示 - 各种漂亮的样式组合演示

展示内容：
- 日志输出样式
- 进度条样式
- 表格样式
- 面板样式
- 状态显示
"""

from __future__ import annotations

import time
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from Kobe.SharedUtility.RichLogger import get_console


def demo_log_styles():
    """演示 1: 精美的日志输出样式"""
    console = get_console()
    
    console.print("\n[bold magenta]═" * 35 + "═[/]")
    console.print("[bold magenta]    演示 1: 精美日志输出样式    [/]")
    console.print("[bold magenta]═" * 35 + "═[/]\n")
    
    # 样式组合 1: 现代简约风格
    console.print("[dim]2024-10-10 14:00:00[/] [bold cyan]INFO[/]     Starting application...")
    console.print("[dim]2024-10-10 14:00:01[/] [bold green]SUCCESS[/] Database connected [green][+][/]")
    console.print("[dim]2024-10-10 14:00:02[/] [bold yellow]WARNING[/] Cache miss, loading from DB")
    console.print("[dim]2024-10-10 14:00:03[/] [bold red]ERROR[/]   Connection timeout [red]x[/]")
    
    console.print()
    
    # 样式组合 2: 带图标的彩色风格
    console.print("[cyan]>[/]  [bold]信息[/]: 系统正在初始化...")
    console.print("[green]+[/]  [bold]成功[/]: 所有模块加载完成")
    console.print("[yellow]![/]  [bold]警告[/]: 内存使用率达到 80%")
    console.print("[red]x[/]  [bold]错误[/]: 无法连接到远程服务器")
    
    console.print()
    
    # 样式组合 3: 渐变效果（通过不同亮度）
    console.print("[bright_blue on black] INFO [/] [bright_white]Application started[/]")
    console.print("[bright_green on black] PASS [/] [white]All tests passed[/]")
    console.print("[bright_yellow on black] WARN [/] [white]Deprecated API usage[/]")
    console.print("[bright_red on black] FAIL [/] [white]Assertion failed[/]")
    
    time.sleep(2)


def demo_progress_styles():
    """演示 2: 多种进度条样式"""
    console = get_console()
    
    console.print("\n[bold magenta]═" * 35 + "═[/]")
    console.print("[bold magenta]    演示 2: 精美进度条样式    [/]")
    console.print("[bold magenta]═" * 35 + "═[/]\n")
    
    # 样式 1: 渐变绿色进度条
    with Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(complete_style="bold green", finished_style="bold bright_green"),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[status]}[/]"),
        console=console,
    ) as progress:
        task = progress.add_task("渐变绿色风格", total=100, status="处理中...")
        for i in range(100):
            time.sleep(0.02)
            progress.update(task, advance=1)
        progress.update(task, status="[green]完成[/]")
    
    time.sleep(0.5)
    
    # 样式 2: 蓝紫渐变进度条
    with Progress(
        TextColumn("[bold magenta]{task.description}"),
        BarColumn(complete_style="bold blue", finished_style="bold magenta"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("蓝紫渐变风格", total=100)
        for i in range(100):
            time.sleep(0.02)
            progress.update(task, advance=1)
    
    time.sleep(0.5)
    
    # 样式 3: 彩虹多进度条
    with Progress(
        TextColumn("{task.description}"),
        BarColumn(complete_style="bold", finished_style="bold"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        tasks = [
            progress.add_task("[red]红色任务[/]", total=50),
            progress.add_task("[yellow]黄色任务[/]", total=50),
            progress.add_task("[green]绿色任务[/]", total=50),
            progress.add_task("[cyan]青色任务[/]", total=50),
            progress.add_task("[blue]蓝色任务[/]", total=50),
        ]
        
        for i in range(50):
            for task_id in tasks:
                progress.update(task_id, advance=1)
            time.sleep(0.02)


def demo_table_styles():
    """演示 3: 精美表格样式"""
    console = get_console()
    
    console.print("\n[bold magenta]═" * 35 + "═[/]")
    console.print("[bold magenta]    演示 3: 精美表格样式    [/]")
    console.print("[bold magenta]═" * 35 + "═[/]\n")
    
    # 样式 1: 简约边框表格
    table1 = Table(title="[bold cyan]系统状态监控[/]", show_header=True, header_style="bold magenta")
    table1.add_column("服务名称", style="cyan", width=20)
    table1.add_column("状态", justify="center", width=10)
    table1.add_column("CPU", justify="right", style="yellow")
    table1.add_column("内存", justify="right", style="green")
    
    table1.add_row("Web Server", "[green]OK[/]", "23%", "512MB")
    table1.add_row("Database", "[green]OK[/]", "45%", "2.1GB")
    table1.add_row("Cache", "[yellow]WARN[/]", "78%", "1.8GB")
    table1.add_row("Queue", "[red]ERROR[/]", "12%", "256MB")
    
    console.print(table1)
    console.print()
    
    # 样式 2: 无边框表格（极简风格）
    table2 = Table(show_header=True, header_style="bold blue", show_edge=False, show_lines=False)
    table2.add_column("时间", style="dim")
    table2.add_column("操作", style="bold")
    table2.add_column("用户", style="cyan")
    table2.add_column("结果")
    
    table2.add_row("14:23:45", "LOGIN", "admin", "[green]OK[/]")
    table2.add_row("14:24:12", "QUERY", "user01", "[green]OK[/]")
    table2.add_row("14:24:56", "UPDATE", "user02", "[yellow]WAIT[/]")
    table2.add_row("14:25:33", "DELETE", "admin", "[red]FAIL[/]")
    
    console.print(table2)
    
    time.sleep(2)


def demo_panel_styles():
    """演示 4: 精美面板样式"""
    console = get_console()
    
    console.print("\n[bold magenta]═" * 35 + "═[/]")
    console.print("[bold magenta]    演示 4: 精美面板样式    [/]")
    console.print("[bold magenta]═" * 35 + "═[/]\n")
    
    # 样式 1: 成功消息面板
    success_panel = Panel(
        "[bold green][OK][/] 部署成功完成！\n\n"
        "[dim]应用版本:[/] v2.3.1\n"
        "[dim]部署时间:[/] 2024-10-10 14:30:00\n"
        "[dim]服务器:[/] production-01",
        title="[bold green]部署成功[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(success_panel)
    console.print()
    
    # 样式 2: 警告消息面板
    warning_panel = Panel(
        "[bold yellow][!][/] 系统资源警告\n\n"
        "[yellow]CPU 使用率:[/] 85%\n"
        "[yellow]内存使用率:[/] 92%\n"
        "[yellow]建议操作:[/] 清理缓存或扩容",
        title="[bold yellow]警告[/]",
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(warning_panel)
    console.print()
    
    # 样式 3: 信息面板（渐变边框效果）
    info_panel = Panel(
        "[bold cyan]系统信息[/]\n\n"
        "[cyan]>[/] 在线用户: [bold]1,234[/]\n"
        "[cyan]>[/] 活跃连接: [bold]567[/]\n"
        "[cyan]>[/] 请求/秒: [bold]89[/]\n"
        "[cyan]>[/] 平均响应: [bold]23ms[/]",
        title="[bold blue]实时监控[/]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(info_panel)
    
    time.sleep(2)


def demo_combined_dashboard():
    """演示 5: 综合仪表盘（我认为最漂亮的组合）"""
    console = get_console()
    
    console.print("\n[bold magenta]═" * 35 + "═[/]")
    console.print("[bold magenta]    演示 5: 综合实时仪表盘    [/]")
    console.print("[bold magenta]═" * 35 + "═[/]\n")
    
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(
            complete_style="bold cyan",
            finished_style="bold green",
            pulse_style="bold magenta"
        ),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TextColumn("[dim]{task.fields[info]}[/]"),
        console=console,
    ) as progress:
        
        # 创建多个任务
        tasks = [
            progress.add_task(
                "[cyan]数据采集[/]",
                total=100,
                info="正在连接..."
            ),
            progress.add_task(
                "[yellow]数据处理[/]",
                total=100,
                info="等待中..."
            ),
            progress.add_task(
                "[green]结果存储[/]",
                total=100,
                info="等待中..."
            ),
        ]
        
        # 模拟任务执行
        for i in range(100):
            time.sleep(0.05)
            
            # 第一个任务
            if i < 100:
                progress.update(
                    tasks[0],
                    advance=1,
                    info=f"已采集 {i+1}/100 条记录"
                )
            
            # 第二个任务（延迟启动）
            if i >= 30 and i < 100:
                progress.update(
                    tasks[1],
                    advance=1,
                    info=f"处理进度 {min(i-29, 100)}%"
                )
            
            # 第三个任务（最后启动）
            if i >= 60:
                progress.update(
                    tasks[2],
                    advance=1,
                    info=f"存储进度 {min(i-59, 100)}%"
                )
        
        # 完成状态
        progress.update(tasks[0], info="[green][OK] 完成[/]")
        progress.update(tasks[1], info="[green][OK] 完成[/]")
        progress.update(tasks[2], info="[green][OK] 完成[/]")
        time.sleep(1)
    
    # 显示最终结果面板
    result_panel = Panel(
        "[bold green][OK] 所有任务执行完成[/]\n\n"
        "[cyan]>[/] 总记录数: [bold]100[/]\n"
        "[cyan]>[/] 处理成功: [bold green]98[/]\n"
        "[cyan]>[/] 处理失败: [bold red]2[/]\n"
        "[cyan]>[/] 总用时: [bold]5.2秒[/]\n"
        "[cyan]>[/] 平均速度: [bold]19.2 条/秒[/]",
        title="[bold cyan]执行摘要[/]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print("\n")
    console.print(result_panel)


def main():
    """运行所有样式演示"""
    console = get_console()
    
    console.print("\n")
    console.print("[bold white on blue]                                                              [/]")
    console.print("[bold white on blue]          Rich 精美样式展示 - 视觉盛宴                         [/]")
    console.print("[bold white on blue]                                                              [/]")
    
    demos = [
        ("日志输出样式", demo_log_styles),
        ("进度条样式", demo_progress_styles),
        ("表格样式", demo_table_styles),
        ("面板样式", demo_panel_styles),
        ("综合仪表盘（最佳组合）", demo_combined_dashboard),
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        console.print(f"\n[dim]按 Enter 继续查看下一个演示...[/]")
        input()
        
        try:
            demo_func()
        except KeyboardInterrupt:
            console.print("\n[yellow]演示已中断[/]")
            break
    
    console.print("\n[bold green][OK] 所有样式演示完成！[/]")
    console.print("\n[dim]提示: 你可以在测试代码中自由组合这些样式[/]\n")


if __name__ == "__main__":
    main()

