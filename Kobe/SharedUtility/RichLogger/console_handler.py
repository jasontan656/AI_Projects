from __future__ import annotations  # 使用内置 future 特性延迟注解解析；避免循环引用时导入顺序出错【内置（Built-in）】
import logging  # 使用标准库模块 logging 提供 Handler 与 Formatter；负责日志核心能力【内置（Built-in）】
from typing import Any, Mapping  # 使用标准库 typing 模块提供 Any/Mapping；用于声明可选的配置参数类型【内置（Built-in）】
from rich.console import Console  # 使用依赖库类 Console 创建富文本终端对象；支持彩色输出【依赖库（Library）】
from rich.logging import RichHandler  # 使用依赖库类 RichHandler 输出富样式日志；兼容标准 logging【依赖库（Library）】

def build_console_handler(  # 定义函数 build_console_handler；返回预配置的控制台处理器供门面调用【内置（Built-in）/ 工厂（Factory）】
    *,  # 使用 * 限定后续参数必须用关键字传递；提高可读性【语法（Syntax）】
    level: int = logging.INFO,  # 声明关键字参数 level 默认 INFO；控制控制台最小等级【配置（Config）】
    console_kwargs: Mapping[str, Any] | None = None,  # 声明可选 console_kwargs；允许调用者透传 Console 的样式配置【扩展（Extension）】
    rich_tracebacks: bool = True,  # 声明 rich_tracebacks 默认 True；输出堆栈时带富文本【体验（Experience）】
    keywords: tuple[str, ...] = (),  # 声明 keywords 关键术语元组；支持高亮重要词汇【体验（Experience）】
) -> logging.Handler:  # 指明函数返回标准库 logging.Handler；保持与 logging 生态一致【类型（Type Hint）】
    handler = RichHandler(  # 实例化 RichHandler；作为核心控制台处理器【依赖库（Library）】
        console=Console(**(console_kwargs or {})),  # 调用 Console 并解包自定义参数；默认创建标准终端对象【依赖库（Library）】
        rich_tracebacks=rich_tracebacks,  # 传入 rich_tracebacks 控制堆栈呈现；保留彩色上下文【配置（Config）】
        keywords=keywords,  # 传入 keywords 用于高亮关键字；提升可读性【体验（Experience）】
    )  # 结束 RichHandler 初始化表达式
    handler.setLevel(level)  # 在 handler 上调用 setLevel 应用最低等级；与全局策略保持一致【配置（Config）】
    handler.setFormatter(logging.Formatter("%(message)s"))  # 在 handler 上设置 Formatter；维持 Rich 默认消息格式【格式（Format）】
    return handler  # 返回配置好的处理器实例；供 RichLoggerManager 统一挂载【返回（Return）】