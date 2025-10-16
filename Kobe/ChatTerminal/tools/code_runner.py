"""
代码执行模块
支持Python和PowerShell代码执行
"""

import subprocess
import sys
import io
from contextlib import redirect_stdout, redirect_stderr


def run_python_code(code: str) -> str:
    """
    执行Python代码
    
    Args:
        code: Python代码字符串
    
    Returns:
        执行结果或错误信息
    """
    try:
        # 创建字符串IO对象来捕获输出
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        # 准备执行环境
        local_vars = {}
        
        # 执行代码
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(code, {"__builtins__": __builtins__}, local_vars)
        
        # 获取输出
        stdout_output = stdout_buffer.getvalue()
        stderr_output = stderr_buffer.getvalue()
        
        result = []
        
        if stdout_output:
            result.append(f"输出:\n{stdout_output}")
        
        if stderr_output:
            result.append(f"错误:\n{stderr_output}")
        
        # 如果有返回值，显示
        if local_vars:
            for key, value in local_vars.items():
                if not key.startswith('_'):
                    result.append(f"{key} = {repr(value)}")
        
        return "\n".join(result) if result else "代码执行完成，无输出"
    
    except SyntaxError as e:
        return f"语法错误: {str(e)}\n行 {e.lineno}: {e.text}"
    except Exception as e:
        return f"运行时错误: {type(e).__name__}: {str(e)}"


def run_powershell_code(code: str) -> str:
    """
    执行PowerShell代码
    
    Args:
        code: PowerShell代码字符串
    
    Returns:
        执行结果或错误信息
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", code],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )
        
        output = []
        if result.stdout:
            output.append(f"输出:\n{result.stdout}")
        if result.stderr:
            output.append(f"错误:\n{result.stderr}")
        if result.returncode != 0:
            output.append(f"返回码: {result.returncode}")
        
        return "\n".join(output) if output else "代码执行完成，无输出"
    
    except subprocess.TimeoutExpired:
        return "错误: 代码执行超时（30秒）"
    except Exception as e:
        return f"错误: 执行PowerShell代码时出错 - {str(e)}"


if __name__ == "__main__":
    # 测试Python代码执行
    python_test = """
import math
result = math.sqrt(16)
print(f"平方根: {result}")
"""
    print("Python测试:")
    print(run_python_code(python_test))
    
    # 测试PowerShell代码执行
    ps_test = """
$date = Get-Date
Write-Host "当前时间: $date"
"""
    print("\nPowerShell测试:")
    print(run_powershell_code(ps_test))

