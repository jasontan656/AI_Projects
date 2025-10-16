"""工具模块聚合"""  # 声明模块文档字符串；说明本模块聚合工具函数

from .command_executor import execute_command  # 使用模块导入语句从同项目模块 command_executor 导入函数 execute_command；暴露命令执行能力
from .file_operations import read_file, write_file, list_directory, search_files  # 使用模块导入语句一次性引入文件操作函数；提供读写与目录遍历
from .code_runner import run_python_code, run_powershell_code  # 使用模块导入语句引入代码执行函数；供终端调用
from .web_tools import web_search, fetch_webpage, http_request, check_website_status  # 使用模块导入语句引入网络工具函数；提供搜索与站点检测
from .exa_tools import exa_search  # 使用模块导入语句引入新建的 exa_search 函数；提供 Exa MCP 搜索能力
from .playwright_tools import playwright_capture  # 使用模块导入语句引入 playwright_capture 函数；提供浏览器自动化抓取能力

__all__ = [  # 使用赋值把导出列表绑定给 __all__；控制模块对外可见符号
    "execute_command",  # 在列表中列出命令执行函数；方便快捷导入
    "read_file",  # 在列表中列出文件读取函数；对外暴露
    "write_file",  # 在列表中列出文件写入函数；对外暴露
    "list_directory",  # 在列表中列出目录遍历函数；对外暴露
    "search_files",  # 在列表中列出文件搜索函数；对外暴露
    "run_python_code",  # 在列表中列出 Python 代码执行函数；对外暴露
    "run_powershell_code",  # 在列表中列出 PowerShell 代码执行函数；对外暴露
    "web_search",  # 在列表中列出 DuckDuckGo 搜索函数；对外暴露
    "fetch_webpage",  # 在列表中列出网页抓取函数；对外暴露
    "http_request",  # 在列表中列出 HTTP 请求函数；对外暴露
    "check_website_status",  # 在列表中列出站点状态检测函数；对外暴露
    "exa_search",  # 在列表中新增 Exa 搜索函数；对外暴露
    "playwright_capture",  # 在列表中新增 Playwright 页面抓取函数；对外暴露
]  # 本行执行后结束列表定义；供 from 模块 import * 使用【集合（Collection）/ 导出（Export）】

