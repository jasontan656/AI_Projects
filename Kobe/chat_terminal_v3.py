#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal AI Assistant V3 - LangChain版本
纯UI展示，配合LangChain后端
简洁、高效、现代化
"""

import sys
import os
import json
import requests
from typing import List, Dict, Any

# 设置Windows控制台UTF-8编码
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich import box

console = Console(force_terminal=True, legacy_windows=False)


class ChatTerminalV3:
    """V3版终端AI助手 - 配合LangChain后端"""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Token 统计（从后端获取）
        self.session_tokens = 0
        self.session_tool_calls = 0
        
        # 检查后端连接
        self._check_backend()
    
    def _check_backend(self):
        """检查后端服务是否运行"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=2)
            if response.status_code == 200:
                console.print("✓ [green]后端服务已连接[/green]")
                console.print(f"🔗 [dim]后端地址: {self.backend_url}[/dim]\n")
                return True
        except requests.exceptions.ConnectionError:
            console.print(Panel(
                "[bold red]无法连接到后端服务[/bold red]\n\n"
                f"[yellow]后端地址:[/yellow] {self.backend_url}\n\n"
                "[cyan]启动命令：[/cyan]\n"
                "[dim]cd Kobe && python app.py[/dim]",
                title="连接错误",
                border_style="red"
            ))
            sys.exit(1)
    
    def _print_user_message(self, message: str):
        """打印用户消息"""
        console.print(f"\n[bold cyan]You:[/bold cyan] {message}")
    
    def _print_assistant_prefix(self):
        """打印AI前缀"""
        console.print(f"\n[bold green]AI:[/bold green] ", end="")
    
    def _stream_chat(self, user_message: str) -> str:
        """
        发送消息并流式接收响应
        
        Returns:
            AI的完整回复内容
        """
        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # 发送流式请求
        try:
            response = requests.post(
                f"{self.backend_url}/api/chat_langchain",
                json={
                    "messages": self.conversation_history,
                    "stream": True
                },
                stream=True,
                timeout=300
            )
            
            if response.status_code != 200:
                console.print(f"\n[red]错误: HTTP {response.status_code}[/red]")
                return ""
            
            # 处理SSE流
            final_content = ""
            content_started = False
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line_text = line.decode('utf-8')
                if not line_text.startswith('data: '):
                    continue
                
                data_str = line_text[6:]  # 移除 "data: " 前缀
                
                try:
                    data = json.loads(data_str)
                    event_type = data.get('type')
                    
                    # 1. 进度事件
                    if event_type == 'progress':
                        action = data.get('action')
                        description = data.get('description', '')
                        timestamp = data.get('timestamp', '')
                        
                        if action == 'thinking':
                            console.print(f"\n[dim cyan]💭 {description}[/dim cyan]")
                        elif action == 'tool_call':
                            console.print(f"[cyan]⚙️  {description}[/cyan]")
                        elif action == 'tool_completed':
                            console.print(f"[green]✓ {description}[/green]")
                        elif action == 'completed':
                            console.print(f"[bold green]✅ {description}[/bold green]\n")
                    
                    # 2. 内容片段（AI回复）
                    elif event_type == 'content_chunk':
                        if not content_started:
                            self._print_assistant_prefix()
                            content_started = True
                        
                        chunk = data.get('content', '')
                        console.print(chunk, end='', style="white")
                        final_content += chunk
                    
                    # 3. 最终结果
                    elif event_type == 'final':
                        final_content = data.get('content', final_content)
                        usage = data.get('usage', {})
                        tool_calls = data.get('tool_calls_count', 0)
                        
                        # 更新会话统计
                        self.session_tokens += usage.get('total_tokens', 0)
                        self.session_tool_calls += tool_calls
                        
                        # 显示统计（如果有token数据）
                        if usage.get('total_tokens', 0) > 0:
                            console.print(f"\n\n[dim]📊 本轮Token: {usage['total_tokens']} | "
                                        f"工具调用: {tool_calls}次[/dim]")
                    
                    # 4. 错误
                    elif event_type == 'error':
                        error_msg = data.get('error', 'Unknown error')
                        console.print(f"\n\n[red]❌ 错误: {error_msg}[/red]")
                        return ""
                
                except json.JSONDecodeError:
                    continue  # 忽略无法解析的行
            
            # 确保换行
            if content_started:
                console.print()
            
            # 添加AI回复到历史
            if final_content:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_content
                })
            
            return final_content
        
        except requests.exceptions.Timeout:
            console.print("\n[red]⏱️  请求超时[/red]")
            return ""
        except requests.exceptions.RequestException as e:
            console.print(f"\n[red]❌ 请求失败: {str(e)}[/red]")
            return ""
        except KeyboardInterrupt:
            console.print("\n\n[yellow]⚠️  已中断[/yellow]")
            return ""
    
    def _print_welcome(self):
        """打印欢迎信息"""
        welcome_panel = Panel(
            "[bold cyan]AI Assistant V3[/bold cyan] - Powered by LangChain\n\n"
            "[dim]可用命令：[/dim]\n"
            "  [cyan]/clear[/cyan]  - 清空对话历史\n"
            "  [cyan]/stats[/cyan]  - 显示会话统计\n"
            "  [cyan]/exit[/cyan]   - 退出程序\n\n"
            "[dim]直接输入消息开始对话[/dim]",
            title="欢迎",
            border_style="cyan",
            box=box.ROUNDED
        )
        console.print(welcome_panel)
    
    def _print_stats(self):
        """打印会话统计"""
        stats_text = Text()
        stats_text.append("📊 会话统计\n\n", style="bold cyan")
        stats_text.append(f"对话轮次: {len(self.conversation_history) // 2}\n", style="white")
        stats_text.append(f"总Token: {self.session_tokens}\n", style="white")
        stats_text.append(f"工具调用: {self.session_tool_calls}次\n", style="white")
        
        console.print(Panel(stats_text, border_style="cyan"))
    
    def _clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        self.session_tokens = 0
        self.session_tool_calls = 0
        console.print("[green]✓ 对话历史已清空[/green]\n")
    
    def run(self):
        """运行交互式终端"""
        self._print_welcome()
        
        while True:
            try:
                # 获取用户输入
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]").strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input == '/exit':
                    console.print("\n[yellow]👋 再见![/yellow]")
                    break
                elif user_input == '/clear':
                    self._clear_history()
                    continue
                elif user_input == '/stats':
                    self._print_stats()
                    continue
                elif user_input.startswith('/'):
                    console.print(f"[red]未知命令: {user_input}[/red]")
                    continue
                
                # 发送消息并获取回复
                self._stream_chat(user_input)
            
            except KeyboardInterrupt:
                console.print("\n\n[yellow]👋 再见![/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red]❌ 发生错误: {str(e)}[/red]")
                continue


def main():
    """主函数"""
    try:
        # 从环境变量或默认值获取后端地址
        import os
        backend_url = os.getenv("KOBE_BACKEND_URL", "http://localhost:8000")
        
        # 创建并运行终端
        terminal = ChatTerminalV3(backend_url=backend_url)
        terminal.run()
    
    except Exception as e:
        console.print(f"[bold red]启动失败: {str(e)}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

