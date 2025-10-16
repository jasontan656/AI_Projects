import asyncio  # 使用标准库模块 asyncio 导入异步锁与信号量工具；随后控制客户端初始化并发
import json  # 使用标准库模块 json 导入序列化函数；随后用于调试型字符串化输出
import os  # 使用标准库模块 os 访问环境变量；随后读取 EXA_API_KEY
from typing import Any, Dict, List, Optional, Tuple  # 使用标准库模块 typing 导入类型标注；随后提升可读性

try:  # 尝试导入依赖库 exa_py；若失败进入异常分支【条件分支（Branch）/ 异常处理（Exception）】
    from exa_py import Exa  # 使用依赖库模块 exa_py 导入 Exa 客户端类；用于发起 Exa 搜索
except ImportError:  # 捕获导入失败异常；条件成立进入分支【条件分支（Branch）/ 异常处理（Exception）】
    Exa = None  # 使用赋值把 None 绑定给占位名 Exa；提醒后续逻辑依赖缺失

_EXA_CLIENT: Optional["Exa"] = None  # 使用赋值把 None 绑定给模块级变量 _EXA_CLIENT；存放复用的 Exa 客户端
_EXA_CLIENT_KEY: Optional[str] = None  # 使用赋值把 None 绑定给 _EXA_CLIENT_KEY；记录当前客户端使用的 API Key
_EXA_CLIENT_LOCK = asyncio.Lock()  # 在 asyncio 模块上调用 Lock 构建异步锁；保护客户端初始化过程
_EXA_SEMAPHORE = asyncio.Semaphore(2)  # 在 asyncio 模块上调用 Semaphore 创建并发限制；避免同时大量调用 Exa API


async def _ensure_client() -> "Exa":  # 定义异步函数 _ensure_client；返回有效的 Exa 客户端实例
    global _EXA_CLIENT, _EXA_CLIENT_KEY  # 声明在本作用域中修改模块级变量 _EXA_CLIENT 与 _EXA_CLIENT_KEY
    if Exa is None:  # 判断 Exa 是否为 None；若依赖缺失则进入分支【条件分支（Branch）/ 异常处理（Exception）】
        raise RuntimeError("未安装 exa_py 库，请执行 pip install exa_py")  # 抛出运行时错误提示安装依赖；提醒调用方
    api_key = os.getenv("EXA_API_KEY")  # 使用标准库函数 os.getenv 读取 EXA_API_KEY；获取运行时凭证
    if not api_key:  # 判断是否缺少 API Key；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        raise RuntimeError("未配置 EXA_API_KEY 环境变量")  # 抛出运行时错误提示缺少配置；阻止继续调用
    async with _EXA_CLIENT_LOCK:  # 使用异步上下文管理器获取锁；确保客户端初始化过程串行化【并发控制（Concurrency）/ 锁（Lock）】
        if _EXA_CLIENT is None or _EXA_CLIENT_KEY != api_key:  # 判断是否需要新建客户端；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
            _EXA_CLIENT = Exa(api_key=api_key)  # 调用依赖库类 Exa 构造客户端；使用当前 API Key
            _EXA_CLIENT_KEY = api_key  # 使用赋值把 api_key 记录到 _EXA_CLIENT_KEY；便于后续校验复用
        return _EXA_CLIENT  # 返回已经就绪的 Exa 客户端；供调用方复用


def _sanitize_query(query: str) -> str:  # 定义函数 _sanitize_query；用于清洗用户输入的查询词
    cleaned = query.strip()  # 在字符串对象 query 上调用方法 strip 去除首尾空白；提升搜索准确度
    return cleaned  # 返回净化后的查询字符串；供上游继续使用


def _normalize_results(payload: Any) -> List[Dict[str, Any]]:  # 定义函数 _normalize_results；标准化 Exa 返回结构
    if hasattr(payload, "results"):  # 检查 payload 是否包含 results 属性；条件成立进入分支【条件分支（Branch）/ 检测（Detection）】
        return list(getattr(payload, "results") or [])  # 使用内置函数 list 将属性 results 转为列表；保证统一类型
    if isinstance(payload, dict):  # 判断 payload 是否为字典；条件成立进入分支【条件分支（Branch）/ 类型检测（Type Check）】
        return list(payload.get("results") or [])  # 使用字典方法 get 提取 results；缺省返回空列表
    if isinstance(payload, list):  # 判断 payload 是否为列表；条件成立进入分支【条件分支（Branch）/ 类型检测（Type Check）】
        return payload  # 直接返回原列表；保持原状
    return []  # 返回空列表；兜底处理未知结构


def _render_entry(index: int, item: Any, include_contents: bool) -> str:  # 定义函数 _render_entry；格式化单条搜索结果
    title = getattr(item, "title", None)  # 使用内置函数 getattr 获取属性 title；兼容对象或字典
    if title is None and isinstance(item, dict):  # 判断 title 是否缺失且 item 为字典；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        title = item.get("title")  # 在字典 item 上调用 get 读取 title；补齐标题
    url = getattr(item, "url", None)  # 使用 getattr 获取属性 url；收集链接
    if url is None and isinstance(item, dict):  # 判断 url 是否缺失且 item 为字典；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        url = item.get("url")  # 在字典 item 上调用 get 读取 url；补齐链接
    snippet_source = "text" if include_contents else "snippet"  # 使用条件表达式选择字段名；决定返回全文或摘要
    snippet = getattr(item, snippet_source, None)  # 使用 getattr 获取指定字段内容；优先兼容对象形式
    if snippet is None and isinstance(item, dict):  # 判断 snippet 是否缺失且 item 为字典；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        snippet = item.get(snippet_source)  # 在字典 item 上调用 get 读取字段；补齐内容
    published = getattr(item, "published_date", None)  # 使用 getattr 获取发布时间；可能缺省
    if published is None and isinstance(item, dict):  # 判断 published 是否缺失且 item 为字典；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        published = item.get("published_date")  # 在字典 item 上调用 get 获取发布时间；补齐信息
    lines: List[str] = []  # 使用赋值把空列表绑定给 lines；收集格式化文本
    lines.append(f"{index}. {title or '未提供标题'}")  # 在列表 lines 上调用 append 追加标题行；包含结果序号
    if url:  # 判断 url 是否存在；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        lines.append(f"   链接: {url}")  # 在列表 lines 上调用 append 追加链接行；提供访问入口
    if published:  # 判断 published 是否存在；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        lines.append(f"   时间: {published}")  # 在列表 lines 上调用 append 追加时间行；标注发布时间
    if snippet:  # 判断 snippet 是否存在；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        summary = snippet[:1200] + ("..." if len(snippet) > 1200 else "")  # 使用切片截取前1200字符；超长时追加省略号
        lines.append(f"   摘要: {summary}")  # 在列表 lines 上调用 append 追加摘要行；展示核心内容
    return "\n".join(lines)  # 使用字符串方法 join 将行列表拼接；生成最终文本


def _render_results(items: List[Dict[str, Any]], include_contents: bool) -> str:  # 定义函数 _render_results；汇总所有条目文本
    if not items:  # 判断是否为空列表；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        return "Exa 搜索未返回结果"  # 返回提示文本说明空结果；避免返回空字符串
    rendered = [  # 使用列表字面量构建渲染结果列表；每项来源于 _render_entry
        _render_entry(idx, item, include_contents)  # 调用 _render_entry 获取格式化文本；包含序号与内容
        for idx, item in enumerate(items, start=1)  # 使用内置函数 enumerate 为列表生成索引；从1开始编号【循环（Loop）/ 迭代（Iteration）】
    ]
    return "\n\n".join(rendered)  # 使用 join 拼接每个条目；中间用空行分隔


def _render_debug(payload: Any) -> str:  # 定义函数 _render_debug；当无法解析时输出结构化 JSON
    try:  # 尝试序列化 payload；若失败进入异常分支【条件分支（Branch）/ 异常处理（Exception）】
        return json.dumps(payload, ensure_ascii=False, indent=2)  # 调用 json.dumps 序列化为 JSON；保留中文字符
    except Exception:  # 捕获任意异常；条件成立进入分支【条件分支（Branch）/ 异常处理（Exception）】
        return str(payload)  # 使用内置函数 str 回退到字符串表示；保证返回值类型合理


async def exa_search(  # 定义异步函数 exa_search；封装 Exa 搜索逻辑供 LangChain 与 MCP 调用
    query: str,
    *,
    num_results: int = 5,
    search_type: str = "auto",
    include_contents: bool = False,
) -> str:
    cleaned_query = _sanitize_query(query)  # 调用 _sanitize_query 清洗输入查询词；去除无效空白
    if not cleaned_query:  # 判断清洗结果是否为空；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        return "错误: 搜索关键词不能为空"  # 返回错误提示字符串；提醒调用方补充输入
    allowed_types = {"auto", "neural", "keyword"}  # 使用集合字面量定义允许的 search_type；限制输入范围
    if search_type not in allowed_types:  # 判断 search_type 是否在允许集合内；条件不成立进入分支【条件分支（Branch）/ 校验（Validation）】
        allowed = ", ".join(sorted(allowed_types))  # 在集合上调用 sorted 排序；随后使用 join 拼接成提示文本
        return f"错误: search_type 仅支持 {allowed}"  # 返回错误提示字符串；引导调用方调整参数
    safe_results = max(1, min(num_results, 20 if search_type != "keyword" else 10))  # 使用内置函数 min/max 约束返回条数；符合 Exa 限制
    try:  # 尝试获取 Exa 客户端；若失败进入异常分支【条件分支（Branch）/ 异常处理（Exception）】
        client = await _ensure_client()  # 调用 _ensure_client 获取已配置的 Exa 客户端；可能触发异常
    except RuntimeError as error:  # 捕获 _ensure_client 抛出的运行时错误；条件成立进入分支【条件分支（Branch）/ 异常处理（Exception）】
        return f"错误: {error}"  # 返回错误提示字符串；包含具体原因
    async with _EXA_SEMAPHORE:  # 使用异步信号量限制并发；保护 Exa API 调用频率【并发控制（Concurrency）/ 信号量（Semaphore）】
        def _run_search() -> Tuple[Any, bool]:  # 定义内部函数 _run_search；在同步上下文执行 Exa API
            try:  # 尝试调用 Exa API；若失败进入异常分支【条件分支（Branch）/ 异常处理（Exception）】
                if include_contents:  # 判断是否需要返回正文；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
                    response = client.search_and_contents(  # 在 Exa 客户端上调用 search_and_contents；同时检索正文
                        cleaned_query,
                        num_results=safe_results,
                        type=search_type,
                        text=True,
                    )
                else:  # 当无需正文时进入分支【条件分支（Branch）/ 默认（Default）】
                    response = client.search(  # 在 Exa 客户端上调用 search；仅获取摘要
                        cleaned_query,
                        num_results=safe_results,
                        type=search_type,
                    )
                return response, True  # 返回响应对象与成功标记；供上游判断
            except Exception as exc:  # 捕获任意异常；条件成立进入分支【条件分支（Branch）/ 异常处理（Exception）】
                return exc, False  # 返回异常对象与失败标记；供上游处理

        payload, ok = await asyncio.to_thread(_run_search)  # 使用 asyncio.to_thread 将同步调用转移到线程；避免阻塞事件循环
    if not ok:  # 判断调用是否失败；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        return f"错误: Exa 搜索失败 - {type(payload).__name__}: {payload}"  # 返回包含异常类型与信息的提示
    results = _normalize_results(payload)  # 调用 _normalize_results 解析响应；提取统一列表结构
    if not results:  # 判断是否为空结果；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
        debug_dump = _render_debug(payload)  # 调用 _render_debug 序列化原始响应；协助排查
        return f"Exa 搜索未找到匹配内容。\n调试信息:\n{debug_dump}"  # 返回空结果提示与调试信息；帮助诊断
    return _render_results(results, include_contents)  # 调用 _render_results 格式化输出；返回给调用方
