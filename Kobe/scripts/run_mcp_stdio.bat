@echo off
setlocal enabledelayedexpansion
cd /d D:\AI_Projects\Kobe
if not exist .\.venv\Scripts\activate.bat (
  echo [ERROR] venv activate.bat not found > SharedUtility\RichLogger\logs\mcp_launcher.log
  exit /b 1
)
call .\.venv\Scripts\activate.bat
echo [INFO] launching mcp_stdio_server at %DATE% %TIME% >> SharedUtility\RichLogger\logs\mcp_launcher.log
python api\mcp_stdio_server.py

