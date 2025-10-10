"""Rich traceback installation helper with action-narrative comments.

职责概述：
- 提供一键安装 rich.traceback 的入口，复用共享 Console 与主题配置。
- 暴露可控参数以适配 CI/本地不同场景的可读性需求。
"""

from __future__ import annotations  # 启用前向注解，增强类型提示兼容性

from typing import Optional  # 引入可选类型提示，以表达参数可省略的语义

from rich.traceback import install as install_rich_traceback  # 引入安装函数，统一异常渲染为富文本

from .console import get_console  # 复用共享 Console，保持渲染上下文一致


def install_traceback(
    show_locals: bool = False,  # 控制是否展示局部变量，便于调试但注意敏感数据暴露风险
    width: Optional[int] = None,  # 控制渲染宽度，None 表示让 rich 自适应终端宽度
    theme: Optional[str] = None,  # 预留主题名参数，目前与 Console 共享主题即可
) -> None:  # 安装富文本回溯，不返回值，仅对解释器产生全局副作用
    console = get_console()  # 获取 Console 单例，确保异常渲染沿用统一主题与输出策略
    install_rich_traceback(  # 调用 rich 提供的安装方法，完成全局异常钩子的注册
        console=console,  # 注入共享 Console，维持输出风格一致性
        show_locals=show_locals,  # 根据参数决定是否展开局部变量，提高排障效率
        width=width,  # 传入宽度参数以优化窄终端阅读体验
        theme=theme,  # 允许下游覆盖主题名以便在极端场景下切换观感
    )

