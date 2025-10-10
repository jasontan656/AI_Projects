"""Basic unit tests for RichLogger components (action-narrative comments)."""

import logging  # 引入日志库，用于断言处理器安装数量与等级行为
import unittest  # 引入 unittest 测试框架，组织测试用例与断言

from Kobe.SharedUtility.RichLogger import (  # 从公共 API 导入被测函数，模拟真实使用方式
    get_console,
    init_console,
    init_logging,
)


class TestRichLogger(unittest.TestCase):  # 定义测试用例集合，按功能分组断言行为
    def test_console_idempotent_and_no_color(self):  # 验证 Console 初始化幂等与禁色开关生效
        c1 = init_console({"no_color": True, "theme": "default"})  # 首次初始化禁色
        c2 = get_console()  # 通过获取接口拿到同一实例
        self.assertIs(c1, c2)  # 断言单例一致，保证幂等语义
        self.assertIs(c2.no_color, True)  # 断言禁色配置已生效

    def test_logging_installed_once(self):  # 验证 RichHandler 不会重复附加
        init_logging(level="DEBUG")  # 第一次初始化日志
        init_logging(level="DEBUG")  # 第二次重复调用不应叠加处理器
        root = logging.getLogger()  # 取得根 logger
        rh = [h for h in root.handlers if h.__class__.__name__ == "RichHandler"]  # 过滤 RichHandler 列表
        self.assertEqual(len(rh), 1)  # 断言仅存在一个 RichHandler，满足幂等初始化要求
