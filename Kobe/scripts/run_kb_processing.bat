@echo off
REM 服务知识库处理脚本启动器
REM 
REM 功能：
REM - 激活 Python 虚拟环境
REM - 运行知识库处理脚本
REM - 保持窗口打开以查看结果

echo ========================================
echo 服务知识库增量式关联构建
echo ========================================
echo.

cd /d "%~dp0.."

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境，请先运行: python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查必要的包
python -c "import openai" 2>nul
if errorlevel 1 (
    echo [提示] 正在安装必要的包...
    pip install openai python-dotenv rich pyyaml
)

REM 运行脚本
echo.
echo 开始处理...
echo.
python scripts\process_kb_services.py

REM 保持窗口打开
echo.
echo ========================================
pause

