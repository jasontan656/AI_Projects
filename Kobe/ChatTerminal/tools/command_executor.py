"""
命令执行模块
支持PowerShell和CMD命令执行
"""

import subprocess
from typing import Literal

# 输出长度限制（字符数）
MAX_OUTPUT_LENGTH = 8000  # 约2000个token，避免消耗过多上下文


def execute_command(command: str, shell: Literal["powershell", "cmd"] = "powershell") -> str:
    """
    执行系统命令
    
    Args:
        command: 要执行的命令
        shell: 使用的shell类型（powershell或cmd）
    
    Returns:
        命令执行结果（stdout和stderr）
    """
    try:
        if shell == "powershell":
            # 使用PowerShell执行
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
        else:
            # 使用CMD执行
            result = subprocess.run(
                ["cmd", "/c", command],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
        
        output = []
        
        # 处理stdout并检查是否需要截断
        if result.stdout:
            stdout_size = len(result.stdout)
            if stdout_size > MAX_OUTPUT_LENGTH:
                truncated_stdout = result.stdout[:MAX_OUTPUT_LENGTH]
                output.append(
                    f"输出（已截断）:\n{truncated_stdout}\n\n"
                    f"⚠️ 输出过大已截断\n"
                    f"- 实际大小: {stdout_size:,} 字符（约 {stdout_size//4:,} tokens）\n"
                    f"- 已显示: {MAX_OUTPUT_LENGTH:,} 字符\n"
                    f"💡 建议: 将结果重定向到文件，例如: {command} > output.txt"
                )
            else:
                output.append(f"输出:\n{result.stdout}")
        
        # 处理stderr
        if result.stderr:
            stderr_size = len(result.stderr)
            if stderr_size > MAX_OUTPUT_LENGTH:
                truncated_stderr = result.stderr[:MAX_OUTPUT_LENGTH]
                output.append(f"错误（已截断）:\n{truncated_stderr}\n[...截断]")
            else:
                output.append(f"错误:\n{result.stderr}")
        
        if result.returncode != 0:
            output.append(f"返回码: {result.returncode}")
        
        return "\n".join(output) if output else "命令执行完成，无输出"
    
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时（30秒）"
    except Exception as e:
        return f"错误: 执行命令时出错 - {str(e)}"


if __name__ == "__main__":
    # 测试
    print(execute_command("Get-Location"))
    print(execute_command("dir", "cmd"))

