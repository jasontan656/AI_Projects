"""
RichLogger
简要: 统一初始化日志与异常堆栈展示的轻量封装。

导出函数
- init_logging(level: str = "INFO"): 配置根 logger、控制台与文件处理器。
- install_traceback(): 安装统一异常钩子，保证未捕获异常以一致格式输出到日志。
- get_console(): 返回一个简易的控制台输出函数，用于结构化打印信息。

说明
- 仅依赖 Python 标准库 logging，不额外引入三方库，满足 BackendConstitution 约束。
- 格式化中携带时间、级别、模块/行号，便于排查。
"""

from .logger import init_logging, install_traceback, get_console

__all__ = ["init_logging", "install_traceback", "get_console"]

