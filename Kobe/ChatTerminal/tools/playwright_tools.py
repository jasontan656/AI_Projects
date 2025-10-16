import re  # 使用标准库模块 re 导入正则表达式工具；随后清洗截图文件名
from pathlib import Path  # 使用标准库模块 pathlib 导入 Path 类；随后定位下载目录
from typing import Optional  # 使用标准库模块 typing 导入 Optional 类型；随后标注可选参数
import sys
import asyncio

try:  # 初次尝试导入；失败时使用懒加载在运行时再补充
    from playwright.async_api import (
        async_playwright,
        TimeoutError as PlaywrightTimeoutError,
    )
except ImportError:
    async_playwright = None
    PlaywrightTimeoutError = Exception


def _ensure_playwright_loaded() -> bool:
    """在调用时懒加载 playwright，支持运行中安装后无需重启进程。"""
    global async_playwright, PlaywrightTimeoutError
    if async_playwright is not None and PlaywrightTimeoutError is not Exception:
        return True
    try:
        from playwright.async_api import (
            async_playwright as _async_playwright,
            TimeoutError as _PlaywrightTimeoutError,
        )
        async_playwright = _async_playwright
        PlaywrightTimeoutError = _PlaywrightTimeoutError
        return True
    except ImportError:
        return False


def _capture_via_sync_thread(
    url: str,
    wait_selector: Optional[str],
    wait_ms: int,
    screenshot: bool,
    screenshot_path: Path,
) -> str:
    """在线程中使用 sync_playwright 执行，规避事件循环对子进程的限制（Windows）。"""
    try:
        # 线程内兜底设置 Proactor 策略
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, timeout=wait_ms)
            if wait_selector:
                page.wait_for_selector(wait_selector, timeout=wait_ms)
            page_title = page.title()
            html_content = page.content()
            snippet = html_content[:4000] + ("...\n[内容截断]" if len(html_content) > 4000 else "")
            screenshot_result = ""
            if screenshot:
                page.screenshot(path=str(screenshot_path), full_page=True)
                screenshot_result = f"截图路径: {screenshot_path}"
            context.close()
            browser.close()
            return "\n".join([
                "✅ Playwright 页面采集完成(线程回退)",
                f"目标URL: {url}",
                f"页面标题: {page_title}",
                screenshot_result or "未生成截图",
                "HTML 内容预览（最多4000字符）:",
                snippet,
            ])
    except Exception as e:
        return f"错误: 线程回退执行失败 - {type(e).__name__}: {e}"


async def playwright_capture(  # 定义异步函数 playwright_capture；为 MCP 与 LangChain 提供页面抓取能力【函数定义（Function Definition）/ 异步（Async）]
    url: str,
    *,
    wait_selector: Optional[str] = None,
    wait_ms: int = 5000,
    screenshot: bool = False,
    screenshot_name: Optional[str] = None,
) -> str:
    # Windows 兜底：确保使用支持子进程的 Proactor 事件循环，避免 asyncio.create_subprocess_* 在部分环境报 NotImplementedError
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    if not _ensure_playwright_loaded():  # 运行时确保依赖已加载；支持后装
        return (
            "错误: 未安装 playwright 库，请先执行 pip install playwright；"
            "如缺浏览器请执行: python -m playwright install chromium"
        )

    downloads_dir = Path(__file__).parent.parent / "downloads"  # 在 Path 对象上拼接 downloads 子目录；统一截图落盘路径
    downloads_dir.mkdir(exist_ok=True)  # 在 Path 对象 downloads_dir 上调用 mkdir 创建目录；允许已存在时跳过

    sanitized_name = screenshot_name or "playwright_capture"  # 使用赋值把默认截图名绑定给 sanitized_name；支持自定义名称
    sanitized_name = re.sub(r"[^A-Za-z0-9._-]", "_", sanitized_name)  # 使用标准库函数 re.sub 清洗文件名；替换非法字符
    screenshot_path = downloads_dir / f"{sanitized_name}.png"  # 在 Path 对象 downloads_dir 上拼接 PNG 文件名；确定截图输出路径

    # Windows 平台：直接使用线程中的同步实现，避免异步路径导致的 NotImplementedError 告警
    if sys.platform == "win32":
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            _capture_via_sync_thread,
            url,
            wait_selector,
            wait_ms,
            screenshot,
            screenshot_path,
        )

    # 非 Windows 平台：保持异步路径
    try:  # 开启异常捕获；确保浏览器资源在异常时正确释放【异常处理（Exception Handling）/ 资源管理（Resource Management）]
        async with async_playwright() as playwright:  # 使用依赖库 async_playwright 创建异步上下文；管理浏览器生命周期【上下文管理（Context Manager）/ Playwright]
            browser = await playwright.chromium.launch(headless=True)  # 在对象 playwright.chromium 上调用 launch 启动无头浏览器；适配服务器环境
            context = await browser.new_context()  # 在浏览器对象 browser 上调用 new_context 创建隔离上下文；避免状态污染
            page = await context.new_page()  # 在上下文对象 context 上调用 new_page 打开新标签页；准备加载目标页面
            try:  # 嵌套 try 块；专注处理页面操作中的异常【异常处理（Exception Handling）/ 页面逻辑（Page Logic）]
                await page.goto(url, timeout=wait_ms)  # 在 page 对象上调用 goto 导航至目标 URL；设置超时时间
                if wait_selector:  # 判断是否提供等待选择器；条件成立进入分支【条件分支（Branch）/ 条件等待（Wait）]
                    await page.wait_for_selector(wait_selector, timeout=wait_ms)  # 在 page 上调用 wait_for_selector 等待元素出现；确保内容就绪
                page_title = await page.title()  # 在 page 上调用 title 获取页面标题；用于结果摘要
                html_content = await page.content()  # 在 page 上调用 content 获取完整 HTML；便于后续截取摘要
                snippet = html_content[:4000] + ("...\n[内容截断]" if len(html_content) > 4000 else "")  # 使用切片截取前 4000 字符；超长时追加提示
                screenshot_result = ""  # 使用赋值把空字符串绑定给 screenshot_result；存储截图信息
                if screenshot:  # 判断是否请求截图；条件成立进入分支【条件分支（Branch）/ 截图（Screenshot）]
                    await page.screenshot(path=str(screenshot_path), full_page=True)  # 在 page 上调用 screenshot 保存全页图像；路径转为字符串
                    screenshot_result = f"截图路径: {screenshot_path}"  # 使用赋值把截图说明绑定给 screenshot_result；便于调用方定位文件
            except PlaywrightTimeoutError as timeout_error:  # 捕获 Playwright 超时异常；条件成立进入分支【异常处理（Exception Handling）/ 超时（Timeout）]
                return f"错误: 页面加载或等待超时 - {timeout_error}"  # 返回包含异常信息的字符串；提示用户调整参数
            except Exception as runtime_error:  # 捕获其他运行时异常；条件成立进入分支【异常处理（Exception Handling）/ 通用（Generic）]
                return f"错误: Playwright 执行失败 - {type(runtime_error).__name__}: {runtime_error}"  # 返回格式化错误信息；帮助诊断问题
            finally:  # finally 分支无论成功与否都会执行；释放 Playwright 资源【资源清理（Resource Cleanup）]
                await context.close()  # 在 context 对象上调用 close 关闭上下文；释放关联资源
                await browser.close()  # 在 browser 对象上调用 close 关闭浏览器进程；避免僵尸进程
    except Exception as outer_error:  # 捕获外层异常；提示浏览器未安装等常见问题
        msg = str(outer_error)
        hint = ""
        if "executable" in msg.lower() or "browser" in msg.lower():
            hint = "；可能未安装浏览器，执行: python -m playwright install chromium"
        return f"错误: Playwright 初始化失败 - {type(outer_error).__name__}: {outer_error}{hint}"

    result_lines = [  # 使用列表字面量收集结果文本；按顺序构造说明
        "✅ Playwright 页面采集完成",  # 在列表中加入成功提示语句；表明任务完成
        f"目标URL: {url}",  # 在列表中加入访问的 URL；方便回溯
        f"页面标题: {page_title}",  # 在列表中加入页面标题；提供上下文
        screenshot_result or "未生成截图",  # 在列表中加入截图说明；若未截图则注明
        "HTML 内容预览（最多4000字符）:",  # 在列表中加入内容标题；提示后续预览
        snippet,  # 在列表中加入实际 HTML 片段；供模型或用户参考
    ]
    return "\n".join(result_lines)  # 使用字符串方法 join 将结果列表拼接为文本；作为最终返回值
