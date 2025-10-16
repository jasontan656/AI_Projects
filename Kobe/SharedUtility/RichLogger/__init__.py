"""RichLogger 门面模块：导出 RichLoggerManager 供全局复用。"""  # 使用模块级文档字符串解释本文件职责；提醒调用者这里仅做门面暴露【文档（Docstring）】
from .logger import RichLoggerManager  # 使用同项目模块导入 RichLoggerManager 类；便于外部直接引用【模块（Module）】

__all__ = ["RichLoggerManager"]  # 定义 __all__ 列表限制公开 API；确保 from RichLogger import * 仅暴露门面类【导出（Export）】