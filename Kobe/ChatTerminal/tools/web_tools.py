"""
网络工具模块
提供网络搜索和网页访问功能
"""

import asyncio
import aiohttp
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus, urlparse
import re
from bs4 import BeautifulSoup

# 全局信号量：限制并发搜索数量为3，避免DuckDuckGo限流
_search_semaphore = asyncio.Semaphore(3)


async def web_search(query: str, num_results: int = 5) -> str:
    """
    使用DuckDuckGo进行网络搜索
    
    Args:
        query: 搜索关键词
        num_results: 返回结果数量（默认5）
    
    Returns:
        搜索结果
    """
    # 使用信号量限制并发数
    async with _search_semaphore:
        try:
            # 使用 ddgs 搜索库（同步的，在线程中运行）
            from ddgs import DDGS
            
            def _search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=num_results))
            
            # 在线程池中运行同步代码，避免阻塞事件循环
            results = await asyncio.to_thread(_search)
            
            if not results:
                return f"搜索 '{query}' 未找到结果"
            
            # 格式化输出
            output = [f"搜索 '{query}' 的结果:\n"]
            for i, result in enumerate(results, 1):
                title = result.get('title', '无标题')
                url = result.get('href', '')
                snippet = result.get('body', '无摘要')
                
                output.append(f"{i}. {title}")
                output.append(f"   {url}")
                output.append(f"   {snippet}\n")
            
            return "\n".join(output)
        
        except ImportError:
            return "错误: 未安装 ddgs 库，请运行: pip install ddgs"
        except Exception as e:
            return f"错误: 搜索失败 - {str(e)}"


async def fetch_webpage(
    url: str,
    extract_text: bool = True,
    follow_links: bool = False,
    max_depth: int = 1,
    max_links: int = 3,
    # 新增：正文抽取与返回格式控制
    readability: bool = True,
    return_format: str = "text",  # text | markdown
    strip_selectors: Optional[List[str]] = None,
    keep_selectors: Optional[List[str]] = None,
    max_chars: int = 5000,
    _visited: set = None,
    _current_depth: int = 0,
) -> str:
    """
    获取网页内容，支持递归爬取链接
    
    Args:
        url: 网页URL
        extract_text: 是否提取纯文本（默认True）
        follow_links: 是否跟随页面内链接继续爬取（默认False）
        max_depth: 最大爬取深度，1=仅当前页，2=当前页+链接页（默认1）
        max_links: 每个页面最多跟随多少个链接（默认3）
        _visited: 内部使用，已访问URL集合
        _current_depth: 内部使用，当前深度
    
    Returns:
        网页内容或错误信息
    
    说明：
    - 默认只爬取当前页面（相当于原来的行为）
    - 如需深入了解，设置 follow_links=True 和 max_depth=2
    - 建议 max_depth 不超过 2，避免内容过多
    - 只跟随同域名链接，避免爬取范围过大
    """
    # 初始化访问集合
    if _visited is None:
        _visited = set()
    
    try:
        # 如果已访问或超过深度，跳过
        if url in _visited or _current_depth >= max_depth:
            return ""
        
        _visited.add(url)
        
        # 验证URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return f"错误: 无效的URL - {url}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 使用aiohttp异步发送请求
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '').lower()
                
                if 'text/html' not in content_type and 'text/plain' not in content_type:
                    return f"[深度 {_current_depth + 1}] 错误: 不支持的内容类型 - {content_type}"
                
                # 读取原始字节内容以评估大小
                raw_bytes = await response.read()
                
                # 检查大小
                content_length = len(raw_bytes)
                if content_length > 1024 * 1024:  # 1MB限制
                    return f"[深度 {_current_depth + 1}] 错误: 网页过大 ({content_length / 1024 / 1024:.2f}MB)"
                
                # 解码为文本
                try:
                    charset = response.charset or 'utf-8'
                except Exception:
                    charset = 'utf-8'
                html_text = raw_bytes.decode(charset, errors='ignore')
                
                # 解析HTML
                soup = BeautifulSoup(html_text, 'html.parser')
        
        # 处理解析结果
        results = []
        
        if extract_text:
            # 可配置的移除/保留选择器
            default_strip = ['script', 'style', 'nav', 'footer', 'header', 'noscript', 'aside', 'form', 'svg']
            selectors_to_strip = strip_selectors if strip_selectors is not None else default_strip
            for node in soup(selectors_to_strip):
                try:
                    node.decompose()
                except Exception:
                    continue

            # 标题
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else "无标题"

            # Readability 优先（如安装）
            text_payload = None
            if readability:
                try:
                    from readability import Document  # type: ignore
                    doc = Document(html_text)
                    short_title = doc.short_title() or title_text
                    cleaned_html = doc.summary(html_partial=True)
                    cleaned_soup = BeautifulSoup(cleaned_html, 'html.parser')
                    text_payload = cleaned_soup.get_text(separator='\n', strip=True)
                    title_text = short_title or title_text
                except Exception:
                    text_payload = None

            # fallback：main/article/body
            if not text_payload:
                main_content = soup.find('main') or soup.find('article') or soup.body
                if main_content:
                    text_payload = main_content.get_text(separator='\n', strip=True)
                else:
                    text_payload = soup.get_text(separator='\n', strip=True)

            # 行清理与长度限制
            lines = [line.strip() for line in text_payload.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)
            if max_chars and len(cleaned_text) > max_chars:
                cleaned_text = cleaned_text[:max_chars] + "\n\n...(内容过长，已截断)"

            # 返回格式（目前 text；markdown 可后续增强）
            depth_marker = f"[深度 {_current_depth + 1}]" if follow_links else ""
            results.append(f"{depth_marker} 网页标题: {title_text}\nURL: {url}\n\n内容:\n{cleaned_text}")
        else:
            # 返回原始HTML
            html = response.text
            if len(html) > 5000:
                html = html[:5000] + "\n\n...(内容过长，已截断)"
            depth_marker = f"[深度 {_current_depth + 1}]" if follow_links else ""
            results.append(f"{depth_marker} 网页HTML ({url}):\n\n{html}")
        
        # 如果需要跟随链接且未达到最大深度
        if follow_links and _current_depth + 1 < max_depth:
            # 提取页面中的链接
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                
                # 转换为绝对URL
                if href.startswith('/'):
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                elif href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                    continue
                elif not href.startswith('http'):
                    # 相对路径
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                
                # 只跟随同域名链接
                if urlparse(href).netloc == parsed.netloc and href not in _visited:
                    links.append(href)
                
                if len(links) >= max_links:
                    break
            
            # 并发爬取链接
            if links:
                results.append(f"\n{'='*60}\n找到 {len(links)} 个相关链接，并发爬取...\n{'='*60}\n")
                
                # 创建并发任务
                tasks = [
                    fetch_webpage(
                        link,
                        extract_text=extract_text,
                        follow_links=follow_links,
                        max_depth=max_depth,
                        max_links=max_links,
                        _visited=_visited,
                        _current_depth=_current_depth + 1
                    )
                    for link in links
                ]
                
                # 并发执行
                sub_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for sub_result in sub_results:
                    if isinstance(sub_result, str) and sub_result:
                        results.append(f"\n{sub_result}")
                    elif isinstance(sub_result, Exception):
                        results.append(f"\n[错误] {str(sub_result)}")
        
        return "\n".join(results)
    
    except asyncio.TimeoutError:
        return f"[深度 {_current_depth + 1}] 错误: 请求超时 - {url}"
    except aiohttp.ClientError as e:
        return f"[深度 {_current_depth + 1}] 错误: 无法访问网页 - {str(e)}"
    except Exception as e:
        return f"[深度 {_current_depth + 1}] 错误: 获取网页时出错 - {str(e)}"


def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None
) -> str:
    """
    发送HTTP请求
    
    Args:
        url: 请求URL
        method: 请求方法（GET, POST, PUT, DELETE等）
        headers: 请求头
        data: 请求数据（POST/PUT时使用）
    
    Returns:
        响应内容
    """
    try:
        method = method.upper()
        if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD']:
            return f"错误: 不支持的HTTP方法 - {method}"
        
        # 默认headers
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        if headers:
            default_headers.update(headers)
        
        # 发送请求
        response = requests.request(
            method=method,
            url=url,
            headers=default_headers,
            json=data if data else None,
            timeout=15
        )
        
        # 格式化响应
        output = [
            f"HTTP {method} {url}",
            f"状态码: {response.status_code} {response.reason}",
            f"\n响应头:",
        ]
        
        for key, value in response.headers.items():
            output.append(f"  {key}: {value}")
        
        output.append("\n响应内容:")
        
        # 根据内容类型处理
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'application/json' in content_type:
            try:
                import json
                json_data = response.json()
                output.append(json.dumps(json_data, indent=2, ensure_ascii=False))
            except:
                output.append(response.text[:2000])
        else:
            content = response.text[:2000]
            if len(response.text) > 2000:
                content += "\n\n...(内容过长，已截断)"
            output.append(content)
        
        return "\n".join(output)
    
    except requests.Timeout:
        return f"错误: 请求超时 - {url}"
    except requests.RequestException as e:
        return f"错误: HTTP请求失败 - {str(e)}"
    except Exception as e:
        return f"错误: 发送请求时出错 - {str(e)}"


def check_website_status(url: str) -> str:
    """
    检查网站状态
    
    Args:
        url: 网站URL
    
    Returns:
        网站状态信息
    """
    try:
        import time
        
        start_time = time.time()
        response = requests.head(url, timeout=10, allow_redirects=True)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        output = [
            f"网站状态检查: {url}",
            f"状态码: {response.status_code} {response.reason}",
            f"响应时间: {response_time:.2f}ms",
            f"最终URL: {response.url}",
            f"\n服务器信息:",
            f"  Server: {response.headers.get('Server', '未知')}",
            f"  Content-Type: {response.headers.get('Content-Type', '未知')}",
            f"  Content-Length: {response.headers.get('Content-Length', '未知')}",
        ]
        
        if response.status_code == 200:
            output.append("\n✅ 网站正常访问")
        elif 300 <= response.status_code < 400:
            output.append("\n🔄 网站重定向")
        elif 400 <= response.status_code < 500:
            output.append("\n⚠️ 客户端错误")
        elif response.status_code >= 500:
            output.append("\n❌ 服务器错误")
        
        return "\n".join(output)
    
    except requests.Timeout:
        return f"❌ 网站无响应（超时）: {url}"
    except requests.RequestException as e:
        return f"❌ 无法访问网站: {str(e)}"
    except Exception as e:
        return f"错误: 检查网站时出错 - {str(e)}"


if __name__ == "__main__":
    # 测试异步函数
    async def test():
        print("测试网络搜索:")
        result = await web_search("Python programming")
        print(result)
        
        print("\n测试网页获取:")
        result = await fetch_webpage("https://www.python.org")
        print(result)
        
        print("\n测试网站状态:")
        print(check_website_status("https://www.google.com"))
    
    # 运行异步测试
    asyncio.run(test())

