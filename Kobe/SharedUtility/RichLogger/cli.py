"""Tiny demo CLI for RichLogger with action-narrative comments.

职责概述：
- 提供最小可运行示例：初始化 Console/Logging/Traceback，并打印示例日志。
- 支持参数/环境变量切换日志等级、颜色开关与是否触发示例异常。
"""

from __future__ import annotations  # 启用前向注解以增强类型提示的可移植性

import argparse  # 引入命令行解析库，构建轻量 CLI 参数网关
import logging  # 引入日志库，演示不同等级的日志输出效果

from . import init_console, init_logging, install_traceback  # 引入对外 API，一站式初始化相关设施


def main() -> int:  # 提供 CLI 入口，返回进程退出码以便脚本调用识别成功/失败
    parser = argparse.ArgumentParser(description="RichLogger demo CLI")  # 构建参数解析器，提供工具用途概述
    parser.add_argument("--level", default=None, help="log level (INFO/DEBUG/...) ")  # 暴露日志等级选项，覆盖环境/默认行为
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")  # 提供禁色开关，兼容无色终端需求
    parser.add_argument("--theme", default=None, help="console theme name")  # 暴露主题名切换，以便现场调优可读性
    parser.add_argument("--boom", action="store_true", help="raise an example exception")  # 提供触发异常的演示开关
    args = parser.parse_args()  # 解析输入参数，形成结构化命名空间供后续使用

    init_console({  # 初始化 Console 单例，基于 CLI 选项覆盖默认策略
        "no_color": bool(args.no_color),  # 将禁色开关透传给 Console，确保演示与预期一致
        "theme": args.theme or "default",  # 指定主题名，缺省回退默认主题
    })
    init_logging(level=args.level, markup=True)  # 初始化日志子系统，开启富文本标记支持以提升演示观感
    install_traceback(show_locals=False)  # 安装富文本回溯，默认不展示局部变量避免示例噪音

    log = logging.getLogger("richlogger.demo")  # 获取命名记录器，区分模块内外日志来源
    log.debug("[debug] Debug info with details")  # 打印 DEBUG 级日志，演示最低等级的开发态信息
    log.info("[info] Hello, [bold green]Rich[/] logger!")  # 打印 INFO 级日志，演示富文本标记的渲染效果
    log.warning("[warning] Something looks [yellow]suspicious[/]")  # 打印 WARNING 级日志，提示潜在风险
    log.error("[error] Recoverable error encountered")  # 打印 ERROR 级日志，模拟可恢复错误

    if args.boom:  # 若用户请求触发示例异常，则构造故意的错误以观察回溯渲染
        raise RuntimeError("Demo exception for rich traceback")  # 抛出运行时异常，验证富文本回溯功能是否生效

    return 0  # 正常结束 CLI，返回零表示成功


if __name__ == "__main__":  # 允许模块直接以脚本方式运行，便于快速本地验证
    raise SystemExit(main())  # 以 SystemExit 方式返回进程码，遵循 Python 脚本惯例

