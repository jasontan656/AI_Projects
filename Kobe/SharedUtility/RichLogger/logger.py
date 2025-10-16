from __future__ import annotations  # 使用内置 future 特性推迟注解求值；避免同模块互相导入时出循环引用【内置（Built-in）】
import logging  # 使用标准库 logging 模块；负责创建 Logger/Handler 并控制日志流程【内置（Built-in）】
from typing import Any, Mapping  # 使用标准库 typing 中的 Any 与 Mapping；描述可选控制台配置参数类型【内置（Built-in）】
from .console_handler import build_console_handler  # 使用同项目模块函数 build_console_handler；生成 Rich 控制台处理器【模块（Module）】
from .file_handler import build_app_file_handler, build_error_file_handler  # 使用同项目模块两个工厂函数；生成 app.log / error.log 文件处理器【模块（Module）】

class RichLoggerManager:  # 定义门面类 RichLoggerManager；集中负责全局日志初始化【封装（Encapsulation）】
    _root_logger: logging.Logger | None = None  # 使用类型注解声明类属性 _root_logger；缓存全局 logger 避免重复创建【状态（State）】

    @classmethod  # 使用内置装饰器 classmethod；允许通过类直接调用 bootstrap【语法（Syntax）】
    def bootstrap(  # 定义 bootstrap 方法；负责初始化并返回全局 logger【入口（Entry）】
        cls,  # 接收类对象引用；便于访问类属性【参数（Parameter）】
        *,  # 使用 * 强制后续参数以关键字传入；提升可读性【语法（Syntax）】
        console_level: int = logging.INFO,  # 声明控制台默认级别 INFO；允许调用者覆盖【配置（Config）】
        console_kwargs: Mapping[str, Any] | None = None,  # 声明可选控制台样式字典；支持富文本自定义【扩展（Extension）】
    ) -> logging.Logger:  # 指定返回类型为 logging.Logger；保持与标准库兼容【类型（Type Hint）】
        if cls._root_logger:  # 判断是否已存在缓存 logger；若已初始化直接复用【条件分支（Branch）】
            return cls._root_logger  # 返回已缓存的 logger；避免重复构建处理器【返回（Return）】
        logger = logging.getLogger("kobe")  # 调用 logging.getLogger 创建名为 kobe 的记录器；作为全局命名空间【内置（Built-in）】
        logger.handlers.clear()  # 清空 logger 旧的处理器列表；防止叠加重复输出【清理（Cleanup）】
        logger.setLevel(logging.DEBUG)  # 设置记录器基准级别 DEBUG；支持最详细的日志记录【配置（Config）】
        logger.addHandler(build_console_handler(level=console_level, console_kwargs=console_kwargs))  # 附加 Rich 控制台处理器；支持富文本与级别覆盖【模块（Module）】
        logger.addHandler(build_app_file_handler(level=logging.DEBUG))  # 附加 app.log 文件处理器；记录全量 DEBUG+ 日志【模块（Module）】
        logger.addHandler(build_error_file_handler())  # 附加 error.log 文件处理器；仅捕捉 ERROR 级别以上日志【模块（Module）】
        cls._root_logger = logger  # 缓存新建 logger 到类属性；供后续快速复用【状态（State）】
        return logger  # 返回初始化完成的全局 logger；供调用方直接写日志【返回（Return）】

    @classmethod  # 使用内置装饰器 classmethod 让 for_node 可通过类直接调用；方便集中管理【内置（Built-in）】
    def for_node(  # 定义 for_node 方法；作为派生节点 logger 的入口【封装（Encapsulation）】
        cls,  # 接收类本身引用 cls；后续可访问类属性与 bootstrap【参数（Parameter）】
        name: str,  # 接收节点名称字符串；用于生成层级记录器名【参数（Parameter）】
        *,  # 使用 * 强制后续参数仅能以关键字传入；提升调用可读性【语法（Syntax）】
        level: int | None = None,  # 声明可选 level；允许覆盖子节点日志级别【配置（Config）】
        console_kwargs: Mapping[str, Any] | None = None,  # 声明可选 console_kwargs；允许自定义 Console 样式参数【扩展（Extension）】
    ) -> logging.Logger:  # 标注返回类型为 logging.Logger；与标准库接口保持一致【类型（Type Hint）】
        if level is None and console_kwargs is None:  # 判断是否缺少所有定制参数；若全为 None 代表调用方式非法【条件分支（Branch）】
            raise ValueError("for_node() 需要 level 或 console_kwargs 至少一个参数")  # 抛出 ValueError；提醒调用者至少传入一个定制项【错误处理（Error Handling）】
        root = cls.bootstrap()  # 调用类方法 bootstrap；确保全局 logger 已初始化并可复用处理器【模块（Module）】
        logger = logging.getLogger(f"{root.name}.{name}")  # 使用标准库 logging.getLogger 获取层级 Logger；名称形如 kobe.node【内置（Built-in）】
        logger.handlers.clear()  # 清空节点原有处理器；避免重复输出或残留旧配置【清理（Cleanup）】
        node_level = level if level is not None else root.level  # 计算节点实际级别；若未覆盖则沿用全局级别【配置（Config）】
        logger.setLevel(node_level)  # 设置节点 Logger 的级别；确保过滤链条符合预期【配置（Config）】
          # 只要传了 level 或 console_kwargs，都应该添加自己的 handlers
        logger.addHandler(build_console_handler(level=node_level, console_kwargs=console_kwargs))  # 附加控制台处理器；带入覆盖后的级别与样式【模块（Module）】
        logger.addHandler(build_app_file_handler(level=node_level))  # 再附加 app.log 文件处理器；保证节点日志按节点级别写入文件【模块（Module）】
        logger.addHandler(build_error_file_handler())  # 附加 error.log 文件处理器；捕获 ERROR 级别的节点日志【模块（Module）】
        logger.propagate = False  # 设置 propagate=False；防止节点日志重复传递到全局控制台处理器【配置（Config）】
        return logger  # 返回配置完毕的节点 Logger；业务模块可直接调用写日志【返回（Return）】
