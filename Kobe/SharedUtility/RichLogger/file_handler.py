from __future__ import annotations  # 使用内置 future 特性启用注解延迟解析；避免循环导入导致类型检查卡住【内置（Built-in）】
import logging  # 使用标准库模块 logging 导入核心 API；稍后构造 FileHandler 负责写日志文件【内置（Built-in）】
from pathlib import Path  # 使用标准库类 Path 管理文件路径；方便跨平台生成日志目录【内置（Built-in）】
LOG_DIR = Path(__file__).resolve().parent / "logs"  # 使用 Path 组合出 logs 目录的绝对路径；确保定位到 RichLogger 模块旁【内置（Built-in）】
APP_LOG_PATH = LOG_DIR / "app.log"  # 使用 Path 拼接 app.log 文件路径；记录全局日志入口【内置（Built-in）】
ERROR_LOG_PATH = LOG_DIR / "error.log"  # 使用 Path 拼接 error.log 文件路径；专门存放错误级别日志【内置（Built-in）】
def _ensure_log_dir() -> Path:  # 定义辅助函数 _ensure_log_dir；保证日志目录存在后返回路径【内置（Built-in）/ 辅助（Helper）】
    LOG_DIR.mkdir(parents=True, exist_ok=True)  # 在对象 LOG_DIR 上调用 mkdir 创建目录；parents=True 支持递归创建【内置（Built-in）】
    return LOG_DIR  # 返回目录 Path；供调用者复用路径而无需重复计算【内置（Built-in）】
def build_app_file_handler(level: int = logging.DEBUG) -> logging.Handler:  # 定义函数 build_app_file_handler；支持自定义日志级别（默认 DEBUG）【内置（Built-in）/ 工厂（Factory）】
    _ensure_log_dir()  # 调用辅助函数确保 logs 目录就绪；防止写文件时报错【流程控制（Control）】
    handler = logging.FileHandler(APP_LOG_PATH, mode="a", encoding="utf-8")  # 使用标准库类 FileHandler 打开 app.log；追加模式并统一 UTF-8 编码【内置（Built-in）】
    handler.setLevel(level)  # 在对象 handler 上调用 setLevel 设置级别；支持记录 DEBUG 级别的详细日志【配置（Config）】
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))  # 使用标准库类 Formatter 设定统一日志格式；levelname 左对齐 8 字符增强可读性【配置（Config）】
    return handler  # 返回配置好的 FileHandler；供 RichLoggerManager 附加到全局 logger【返回（Return）】
def build_error_file_handler() -> logging.Handler:  # 定义函数 build_error_file_handler；专门构建错误级别文件处理器【内置（Built-in）/ 工厂（Factory）】
    _ensure_log_dir()  # 再次确保目录存在；避免多线程场景中的竞态【流程控制（Control）】
    handler = logging.FileHandler(ERROR_LOG_PATH, mode="a", encoding="utf-8")  # 使用 FileHandler 指向 error.log；仅记录高优先级日志【内置（Built-in）】
    handler.setLevel(logging.ERROR)  # 在 handler 上设置最低级别为 ERROR；过滤掉 INFO/DEBUG 等低级别【配置（Config）】
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))  # 复用统一 Formatter；便于对比控制台输出【配置（Config）】
    return handler  # 返回 ERROR 文件处理器；将由门面类挂载触发写盘【返回（Return）】