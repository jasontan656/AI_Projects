"""Logging bootstrap using RichHandler with action-narrative comments.

职责概述：
- 以标准库 logging 为核心，安装 rich.logging.RichHandler 作为终端处理器。
- 保证多次初始化不重复附加 handler（幂等）。
- 提供简单等级控制、可选文件持久化与 markup 支持。
"""

from __future__ import annotations  # 启用前向注解，提升类型提示的健壮性

import logging  # 引入标准库日志模块，作为统一日志 API 的背板
import os  # 引入环境变量访问能力，用于解析默认日志等级等外部注入配置
from typing import Optional  # 引入可选类型标注，清晰表达参数的选填语义

from rich.logging import RichHandler  # 引入富文本处理器，实现更友好的终端日志渲染

from .console import get_console  # 引入 Console 单例获取，确保 handler 共享同一 Console 实例


_installed = False  # 声明安装状态标志，控制幂等初始化，避免重复附加 handlers


def _level_from_str(level: str) -> int:  # 提供等级字符串到 logging 等级常量的解析函数
    mapping = {  # 就常用等级建立映射，兼容大小写输入
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return mapping.get(level.upper(), logging.INFO)  # 未识别时回落到 INFO，保证可预测行为


def init_logging(
    level: Optional[str] = None,  # 允许外部覆盖日志等级，默认从环境变量推导
    markup: bool = True,  # 控制 RichHandler 对富文本标记的支持开关
    logfile: Optional[str] = None,  # 可选文件路径，开启时将添加文件处理器实现持久化
) -> None:  # 提供初始化入口，不返回值，仅产生全局副作用（安装 handlers 与基本配置）
    global _installed  # 声明修改模块级安装标记，确保幂等逻辑可见
    if _installed:  # 若已经完成初始化，则直接返回，避免重复添加处理器
        return  # 结束函数，维持幂等与性能

    console = get_console()  # 获取 Console 单例，保证终端输出与其他组件共享渲染上下文

    env_level = os.getenv("LOG_LEVEL") or os.getenv("RICH_LOG_LEVEL")  # 兼容两种环境变量来源，便于迁移与约定收敛
    target_level = _level_from_str(level or env_level or "INFO")  # 解析最终的日志等级，缺省回落 INFO

    root_logger = logging.getLogger()  # 取得根 logger，作为全局日志分发的核心入口
    root_logger.setLevel(target_level)  # 设置根等级，确保下游没有更高门槛导致日志被过滤

    # 清理已存在的等价 RichHandler，避免重复初始化导致重复输出
    for h in list(root_logger.handlers):  # 遍历当前已安装处理器副本，避免迭代期间修改原列表
        if isinstance(h, RichHandler):  # 识别 RichHandler 类型，判断是否为我们期望的终端处理器
            root_logger.removeHandler(h)  # 移除重复处理器，保证最终仅存在一个 RichHandler

    rich_handler = RichHandler(  # 构造 RichHandler 实例，配置富文本解析与行内回溯折叠
        console=console,  # 绑定共享 Console，保证风格/主题一致
        markup=markup,  # 启用/禁用 markup，允许日志中安全使用富文本标记
        rich_tracebacks=True,  # 开启富文本回溯，以提升错误排查的易读性
        tracebacks_suppress=[logging],  # 抑制 logging 自身栈帧噪音，突出业务堆栈
        show_time=True,  # 打开时间列，便于问题追踪
    )

    formatter = logging.Formatter("%(message)s")  # 使用 message-only 格式，交由 RichHandler 负责美化
    rich_handler.setFormatter(formatter)  # 绑定格式器，保持基本字段展示行为一致
    root_logger.addHandler(rich_handler)  # 安装处理器到根 logger，完成终端渲染链路

    if logfile:  # 若启用文件持久化，则额外叠加一个 FileHandler 并使用结构化格式
        file_handler = logging.FileHandler(logfile, encoding="utf-8")  # 打开文件渠道，统一使用 UTF-8 编码
        file_fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",  # 输出时间/等级/记录器名/消息，便于检索
            datefmt="%Y-%m-%d %H:%M:%S",  # 采用固定时间格式，方便跨工具解析
        )
        file_handler.setFormatter(file_fmt)  # 绑定文件格式器，确保文件输出可读可查
        root_logger.addHandler(file_handler)  # 安装文件处理器，完成持久化链路

    _installed = True  # 标记初始化完成，后续再调用将直接返回避免重复

