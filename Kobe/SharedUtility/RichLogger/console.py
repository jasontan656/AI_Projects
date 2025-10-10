"""Console bootstrap and accessors with action-narrative comments.

职责概述：
- 负责全局唯一的 rich.console.Console 初始化、样式加载与获取。
- 支持基于 env/参数的无色输出、主题切换与宽度设置。
- 在多次调用 init_console() 时保持幂等，确保 Console 单例不被重复创建。
"""

from __future__ import annotations  # 启用前向注解兼容以稳固类型提示的解析

import os  # 引入环境变量访问能力，用于读取 no_color/theme 等运行时配置
import threading  # 引入线程原语，确保在多线程场景中单例初始化具备原子性
from typing import Any, Dict, Optional  # 引入类型标注，明确接口契约与调用约束

from rich.console import Console  # 引入 Console 核心类型，承担富文本终端渲染职责
from rich.theme import Theme  # 引入 Theme 类型，用于注册令牌->样式映射的主题
from pathlib import Path  # 引入路径工具，定位包内样式文件 styles.toml


_console_instance: Optional[Console] = None  # 声明 Console 单例占位，默认未初始化表示 None
_console_lock = threading.Lock()  # 准备互斥锁，保证并发调用 init_console() 的互斥与可见性


def _default_themes() -> Dict[str, Dict[str, str]]:  # 定义默认主题集合，提供兜底样式以避免外部样式缺失
    return {  # 返回两套主题以满足“默认/高对比度”的常见可用性需求
        "default": {  # 默认主题：偏温和，适合一般终端背景
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "bold red",
            "debug": "dim white",
        },
        "high_contrast": {  # 高对比度主题：保证 4.5:1 以上的对比度倾向
            "info": "bold bright_cyan",
            "success": "bold bright_green",
            "warning": "bold bright_yellow",
            "error": "bold bright_red",
            "debug": "bold bright_white",
        },
    }


def _load_styles_from_toml(path: Path) -> Dict[str, Dict[str, str]]:  # 从 TOML 文件解析样式映射（极简解析器）
    result: Dict[str, Dict[str, str]] = {"default": {}, "high_contrast": {}}  # 预建结果结构，确保两个命名空间存在
    if not path.is_file():  # 若文件不存在则直接返回空映射，表示不覆盖内置主题
        return {}
    current: Optional[str] = None  # 记录当前解析到的样式节名称，用于将键值落入对应命名空间
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():  # 逐行读取 UTF-8 文本，忽略非法字节
        line = raw.strip()  # 去掉首尾空白，便于解析标记
        if not line or line.startswith("#"):  # 跳过空行与注释行，保持解析稳健
            continue
        if line.startswith("[") and line.endswith("]"):  # 解析节名称，形如 [styles.default]
            header = line.strip("[]")  # 去除方括号，得到节名原文
            if header.startswith("styles."):
                current = header.split(".", 1)[1]  # 提取 styles. 后的主题名，如 default/high_contrast
                if current not in result:
                    result[current] = {}  # 对未知主题名建立命名空间，增强前向兼容
            else:
                current = None  # 非 styles.* 节忽略，避免误解析
            continue
        if current:  # 仅当处于有效节内才解析键值对
            if "=" in line:  # 解析形如 key = "value" 的赋值行
                k, v = line.split("=", 1)  # 按首个等号分割键和值
                key = k.strip()  # 去空白得到 token 名
                val = v.strip().strip('"')  # 去空白并去除双引号，得到样式表达式
                if key:
                    result[current][key] = val  # 记录 token->样式 的映射
    return result  # 返回解析结果，供主题构造时使用


def _select_theme(name: str) -> Theme:  # 将名称解析为 Theme 实例，若外部样式缺失则从内置兜底集中挑选
    themes = _default_themes()  # 取内置主题映射，保障最小可用配置随包分发
    styles_path = Path(__file__).with_name("styles.toml")  # 锁定包同目录下的样式文件路径
    loaded = _load_styles_from_toml(styles_path)  # 解析外部样式定义，允许覆盖/扩展内置主题
    for space, mapping in loaded.items():  # 遍历已加载命名空间，将外部样式合并进来
        if mapping:
            themes[space] = mapping  # 以外部映射覆盖同名主题，遵循“用户配置优先”的原则
    data = themes.get(name) or themes["default"]  # 按名称获取主题条目，找不到则回退默认主题
    return Theme(data)  # 使用 rich.Theme 构造主题对象，供 Console 注册应用


def init_console(options: Optional[Dict[str, Any]] = None) -> Console:  # 提供对外初始化入口，支持参数/环境变量双通道配置
    global _console_instance  # 声明写全局单例，确保函数内更新作用于模块级实例
    if _console_instance is not None:  # 若已初始化则直接返回，保证幂等调用不重复创建对象
        return _console_instance  # 返还现有实例，维持单例模式的可预期行为

    with _console_lock:  # 进入互斥区，确保在多线程并发时只进行一次实例化操作
        if _console_instance is not None:  # 双检锁：二次确认状态避免竞态条件导致的重复初始化
            return _console_instance  # 再次返回已有实例，避免重复构造

        opts = dict(options or {})  # 复制调用方传入选项，避免外部字典共享带来意外副作用
        env_no_color = os.getenv("RICH_NO_COLOR")  # 读取禁用颜色的环境开关，用以兼容 CLI/CI 等场景
        env_theme = os.getenv("RICH_THEME")  # 读取主题名的环境变量，支持外部静默切换主题
        env_width = os.getenv("RICH_WIDTH")  # 读取宽度配置的环境变量，便于在窄终端中压缩输出

        no_color = bool(opts.get("no_color", False) or (env_no_color == "1"))  # 合并禁色开关，命令参数优先于环境
        theme_name = str(opts.get("theme", env_theme or "default"))  # 归一主题名来源，缺省回落 "default"
        width_opt = opts.get("width") or (int(env_width) if env_width and env_width.isdigit() else None)  # 解析宽度数值

        theme = _select_theme(theme_name)  # 基于解析出的主题名构建 Theme 实例，保证样式映射可用

        _console_instance = Console(  # 构造 Console 单例，绑定主题/颜色策略/终端探测逻辑
            width=width_opt,  # 传入目标宽度，None 表示让 rich 自适应终端宽度
            theme=theme,  # 注入主题对象，完成令牌->样式的注册
            no_color=no_color,  # 按需禁止 ANSI 颜色转义，满足“纯文本输出”的需求
        )
        return _console_instance  # 返回创建好的 Console 实例，后续通过 get_console() 统一获取


def get_console() -> Console:  # 提供单例获取接口，若未初始化则以默认策略懒加载
    global _console_instance  # 声明访问模块级单例，保证返回的一致性
    if _console_instance is None:  # 若尚未显式初始化则进行一次默认初始化
        init_console({})  # 调用初始化并使用默认参数，确保下游总能拿到可用实例
    assert _console_instance is not None  # 静态保障：此处必须已被赋值，若为 None 属于逻辑错误
    return _console_instance  # 返回 Console 单例，供调用方进行富文本输出
