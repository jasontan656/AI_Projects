"""工具模块聚合"""  # 声明模块文档字符串；说明本模块聚合工具函数

from .file_operations import read_file, write_file, list_directory, search_files  # 使用模块导入语句一次性引入文件操作函数；提供读写与目录遍历
from .code_runner import run_python_code, run_powershell_code  # 使用模块导入语句引入代码执行函数；供终端调用

__all__ = [  # 使用赋值把导出列表绑定给 __all__；控制模块对外可见符号
    "read_file",  # 在列表中列出文件读取函数；对外暴露
    "write_file",  # 在列表中列出文件写入函数；对外暴露
    "list_directory",  # 在列表中列出目录遍历函数；对外暴露
    "search_files",  # 在列表中列出文件搜索函数；对外暴露
    "run_python_code",  # 在列表中列出 Python 代码执行函数；对外暴露
    "run_powershell_code",  # 在列表中列出 PowerShell 代码执行函数；对外暴露
]  # 本行执行后结束列表定义；供 from 模块 import * 使用【集合（Collection）/ 导出（Export）】

