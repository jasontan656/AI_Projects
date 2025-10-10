"""Test Rich Progress with nested progress bars and live status updates.

模拟场景：
- 主进度条：60秒总时长，按秒更新
- 多个并发任务（例如同时爬取多个网站）
- 每个子任务随机开始时间和持续时长
- 所有任务在60秒内完成
- 实时更新状态文本（当前 URL、速度、进度等）
- 原地更新显示（不滚动输出）
"""

from __future__ import annotations

import random
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from Kobe.SharedUtility.RichLogger import get_console


def simulate_timed_download_task(
    task_name: str,
    start_delay: float,
    duration: float,
    progress: Progress,
    task_id: int,
    start_time: datetime,
) -> None:
    """基于时间的下载任务模拟
    
    Args:
        task_name: 任务名称
        start_delay: 延迟开始时间（秒）
        duration: 任务持续时间（秒）
        progress: Progress 对象
        task_id: 任务ID
        start_time: 主进度条开始时间
    """
    urls = [
        "/api/users",
        "/data/products",
        "/content/articles",
        "/images/photo.jpg",
        "/docs/manual.pdf",
        "/static/bundle.js",
        "/assets/logo.png",
    ]
    
    # 等待开始
    if start_delay > 0:
        progress.update(task_id, description=f"{task_name} [dim](等待中...)[/]")
        time.sleep(start_delay)
    
    # 开始执行任务
    progress.update(task_id, description=f"{task_name} [yellow](启动中...)[/]")
    
    # 转换为步数（每0.1秒更新一次）
    total_steps = int(duration * 10)
    progress.update(task_id, total=total_steps)
    
    for step in range(total_steps):
        time.sleep(0.1)
        
        # 随机选择当前处理的URL和速度
        current_url = random.choice(urls)
        speed = random.randint(200, 2000)
        completed_percent = int((step + 1) / total_steps * 100)
        
        # 计算已用时间
        elapsed = (datetime.now() - start_time).total_seconds()
        
        progress.update(
            task_id,
            advance=1,
            description=f"{task_name} [cyan]{current_url}[/] ({speed}KB/s) - {completed_percent}%"
        )
    
    # 任务完成
    progress.update(task_id, description=f"{task_name} [green][OK][/] 完成")


def simulate_download_task(task_name: str, total_items: int, progress: Progress, task_id: int) -> None:
    """模拟单个下载/爬取任务，更新进度条和状态（用于简单测试）"""
    urls = [
        "/api/users",
        "/data/products",
        "/content/articles",
        "/images/photo.jpg",
        "/docs/manual.pdf",
    ]
    
    for i in range(total_items):
        # 模拟不同速度的任务执行
        time.sleep(random.uniform(0.05, 0.15))
        
        # 更新进度条
        current_url = random.choice(urls)
        speed = random.randint(100, 1000)
        progress.update(
            task_id,
            advance=1,
            description=f"[cyan]{task_name}[/] {current_url} ({speed}KB/s)"
        )


class TestProgressLiveUpdates(unittest.TestCase):
    """测试 Rich Progress 的实时更新和嵌套进度条功能"""
    
    def test_single_progress_bar(self) -> None:
        """测试单个进度条的基本功能"""
        console = get_console()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("下载文件", total=10)
            
            for i in range(10):
                time.sleep(0.1)
                progress.update(task, advance=1, description=f"下载文件 ({i+1}/10)")
        
        # 测试通过 - 如果能正常完成就说明基本功能正常
        self.assertTrue(True)
    
    def test_multiple_progress_bars_sequential(self) -> None:
        """测试多个进度条顺序执行"""
        console = get_console()
        
        tasks_config = [
            ("网站 A - 爬取数据", 5),
            ("网站 B - 下载图片", 8),
            ("网站 C - 提取文本", 6),
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            for task_name, total in tasks_config:
                task_id = progress.add_task(task_name, total=total)
                simulate_download_task(task_name, total, progress, task_id)
        
        self.assertTrue(True)
    
    def test_nested_progress_bars_concurrent(self) -> None:
        """测试嵌套进度条 - 并发多任务（核心测试）"""
        console = get_console()
        
        # 模拟同时爬取多个网站 - 使用简单计数方式
        sites = [
            ("[cyan]Website A[/]", 10),
            ("[cyan]Website B[/]", 15),
            ("[cyan]Website C[/]", 8),
            ("[cyan]Website D[/]", 12),
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(complete_style="green", finished_style="bold green"),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TextColumn("[dim]{task.fields[status]}"),
            console=console,
        ) as progress:
            # 创建总体进度任务
            overall = progress.add_task(
                "[bold magenta]总体进度", 
                total=sum(total for _, total in sites),
                status="初始化..."
            )
            
            # 为每个站点创建独立的进度任务
            task_ids = []
            for site_name, total in sites:
                task_id = progress.add_task(
                    site_name, 
                    total=total,
                    status="等待开始"
                )
                task_ids.append((task_id, site_name, total))
            
            # 使用线程池并发执行任务
            def worker(args):
                task_id, site_name, total = args
                progress.update(task_id, status="正在运行...")
                simulate_download_task(site_name, total, progress, task_id)
                progress.update(task_id, status="[green]OK[/] 完成")
                progress.update(overall, advance=total)
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                executor.map(worker, task_ids)
            
            progress.update(overall, status="[green]OK[/] 所有任务完成")
        
        self.assertTrue(True)
    
    def test_60_second_master_progress_with_random_subtasks(self) -> None:
        """测试60秒主进度条 + 随机子任务（真实时间模拟）
        
        注意：此测试需要运行完整60秒，适合最终验收测试
        """
        console = get_console()
        
        # 定义子任务配置：随机开始时间和持续时长
        # 格式：(任务名, 开始延迟秒数, 持续秒数)
        subtasks_config = [
            ("下载任务 A", random.uniform(0, 5), random.uniform(8, 15)),
            ("下载任务 B", random.uniform(2, 10), random.uniform(10, 20)),
            ("下载任务 C", random.uniform(5, 15), random.uniform(5, 12)),
            ("下载任务 D", random.uniform(8, 20), random.uniform(8, 18)),
            ("下载任务 E", random.uniform(10, 25), random.uniform(6, 15)),
        ]
        
        # 确保所有任务都在60秒内完成
        for i, (name, start, duration) in enumerate(subtasks_config):
            if start + duration > 58:  # 留2秒缓冲
                # 调整持续时间
                duration = max(5, 58 - start)
                subtasks_config[i] = (name, start, duration)
        
        TOTAL_DURATION = 60  # 主进度条总时长（秒）
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="bold green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # 创建主进度条（60秒）
            master_task = progress.add_task(
                "[bold magenta]>>> 主进度 <<<",
                total=TOTAL_DURATION * 10  # 每0.1秒更新一次，共600步
            )
            
            # 创建子任务进度条
            subtask_ids = []
            for task_name, start_delay, duration in subtasks_config:
                task_id = progress.add_task(
                    f"{task_name}",
                    total=100,  # 初始值，稍后会更新
                )
                subtask_ids.append((task_id, task_name, start_delay, duration))
            
            # 记录开始时间
            start_time = datetime.now()
            
            # 启动子任务线程
            def run_subtask(args):
                task_id, task_name, start_delay, duration = args
                simulate_timed_download_task(
                    task_name, start_delay, duration, progress, task_id, start_time
                )
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                # 并发提交所有子任务
                futures = [executor.submit(run_subtask, args) for args in subtask_ids]
                
                # 主进度条更新循环
                for step in range(TOTAL_DURATION * 10):
                    time.sleep(0.1)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    progress.update(
                        master_task,
                        advance=1,
                        description=f"[bold magenta]>>> 主进度 <<< {elapsed:.1f}s / {TOTAL_DURATION}s"
                    )
                
                # 等待所有子任务完成
                for future in futures:
                    future.result()
            
            # 确保所有子任务完成
            progress.update(master_task, description="[bold green]>>> 主进度 <<< [OK] 全部完成")
        
        self.assertTrue(True)
    
    def test_15_second_quick_demo(self) -> None:
        """快速演示：15秒主进度条 + 随机子任务（推荐用于日常测试）"""
        console = get_console()
        
        TOTAL_DURATION = 15  # 主进度条总时长（秒）
        
        # 定义子任务配置：随机开始时间和持续时长
        subtasks_config = [
            ("爬虫 A", random.uniform(0, 2), random.uniform(3, 6)),
            ("爬虫 B", random.uniform(1, 4), random.uniform(4, 7)),
            ("爬虫 C", random.uniform(2, 6), random.uniform(3, 5)),
            ("爬虫 D", random.uniform(3, 8), random.uniform(3, 6)),
        ]
        
        # 确保所有任务都在15秒内完成
        for i, (name, start, duration) in enumerate(subtasks_config):
            if start + duration > 14:  # 留1秒缓冲
                duration = max(2, 14 - start)
                subtasks_config[i] = (name, start, duration)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="bold green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # 创建主进度条
            master_task = progress.add_task(
                "[bold magenta]>>> 主进度 <<<",
                total=TOTAL_DURATION * 10
            )
            
            # 创建子任务进度条
            subtask_ids = []
            for task_name, start_delay, duration in subtasks_config:
                task_id = progress.add_task(f"{task_name}", total=100)
                subtask_ids.append((task_id, task_name, start_delay, duration))
            
            start_time = datetime.now()
            
            # 启动子任务线程
            def run_subtask(args):
                task_id, task_name, start_delay, duration = args
                simulate_timed_download_task(
                    task_name, start_delay, duration, progress, task_id, start_time
                )
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                # 并发提交所有子任务
                futures = [executor.submit(run_subtask, args) for args in subtask_ids]
                
                # 主进度条更新循环
                for step in range(TOTAL_DURATION * 10):
                    time.sleep(0.1)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    progress.update(
                        master_task,
                        advance=1,
                        description=f"[bold magenta]>>> 主进度 <<< {elapsed:.1f}s / {TOTAL_DURATION}s"
                    )
                
                # 等待所有子任务完成
                for future in futures:
                    future.result()
            
            progress.update(master_task, description="[bold green]>>> 主进度 <<< [OK] 完成")
        
        self.assertTrue(True)
    
    def test_progress_with_dynamic_status(self) -> None:
        """测试进度条与动态状态文本"""
        console = get_console()
        
        statuses = [
            "[blue]>[/] 正在连接服务器...",
            "[yellow]>>[/] 正在发送请求...",
            "[cyan]>>>[/] 正在接收数据...",
            "[magenta]>>>>[/] 正在保存文件...",
            "[green]>>>>>[/] 验证数据完整性...",
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[yellow]{task.fields[status]}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "数据同步任务",
                total=len(statuses) * 5,
                status=statuses[0]
            )
            
            for status_idx, status in enumerate(statuses):
                progress.update(task, status=status)
                for i in range(5):
                    time.sleep(0.1)
                    progress.update(
                        task, 
                        advance=1,
                        description=f"数据同步任务 [{status_idx * 5 + i + 1}/{len(statuses) * 5}]"
                    )
            
            progress.update(task, status="[green]OK[/] 完成")
        
        self.assertTrue(True)
    
    def test_progress_with_variable_speed(self) -> None:
        """测试不同速度的进度条（模拟网络波动）"""
        console = get_console()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[dim]{task.fields[speed]}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "下载大文件",
                total=100,
                speed="0 KB/s"
            )
            
            for i in range(100):
                # 模拟变化的下载速度
                speed = random.randint(50, 2000)
                delay = 0.3 / (speed / 100)  # 速度越快延迟越短
                time.sleep(delay)
                
                progress.update(
                    task,
                    advance=1,
                    speed=f"{speed} KB/s",
                    description=f"下载大文件 (已完成 {i+1}%)"
                )
        
        self.assertTrue(True)


if __name__ == "__main__":
    # 允许直接运行此测试文件
    unittest.main(verbosity=2)

