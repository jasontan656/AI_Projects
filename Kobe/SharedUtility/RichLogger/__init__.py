"""Kobe.SharedUtility.RichLogger package public API (action-narrative commented)."""

# 暴露初始化与获取 API——对外仅提供稳定入口，隐藏内部实现细节
from .console import init_console, get_console  # 导出 Console 初始化与获取函数，确保调用方不感知模块内部组织
from .logger import init_logging  # 导出日志初始化函数，让调用方一站式启用富文本终端日志
from .traceback_setup import install_traceback  # 导出 Traceback 安装函数，便于统一异常渲染行为

__all__ = [  # 定义公开符号清单，约束外部可用 API，维持稳定契约
    "init_console",
    "get_console",
    "init_logging",
    "install_traceback",
]

