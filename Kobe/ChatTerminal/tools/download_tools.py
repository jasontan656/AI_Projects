"""
下载工具模块
提供文件下载功能
"""

import os
import requests
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Optional


def download_file(url: str, filename: Optional[str] = None, description: str = "") -> str:
    """
    从URL下载文件到本地downloads文件夹
    
    Args:
        url: 文件URL
        filename: 可选的自定义文件名（如果不提供，从URL自动提取）
        description: 可选的文件描述（用于记录）
    
    Returns:
        下载结果信息
    """
    try:
        # 确保downloads目录存在
        downloads_dir = Path(__file__).parent.parent / "downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        # 如果没有指定文件名，从URL提取
        if not filename:
            parsed_url = urlparse(url)
            filename = unquote(os.path.basename(parsed_url.path))
            
            # 如果URL没有文件名，生成一个
            if not filename or filename == '/':
                filename = f"download_{hash(url) % 100000}.file"
        
        # 确保文件名安全
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-'))
        file_path = downloads_dir / filename
        
        # 如果文件已存在，添加序号
        counter = 1
        original_stem = file_path.stem
        original_suffix = file_path.suffix
        while file_path.exists():
            file_path = downloads_dir / f"{original_stem}_{counter}{original_suffix}"
            counter += 1
        
        # 发送请求下载文件
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # 获取文件大小
        file_size = int(response.headers.get('content-length', 0))
        file_size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
        
        # 检查文件大小限制（100MB）
        if file_size > 100 * 1024 * 1024:
            return f"错误: 文件过大 ({file_size_mb:.2f} MB)，超过100MB限制"
        
        # 写入文件
        downloaded = 0
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
        
        # 返回结果
        result = [
            f"✅ 文件下载成功！",
            f"",
            f"文件名: {file_path.name}",
            f"保存路径: {file_path}",
            f"文件大小: {downloaded / 1024:.2f} KB",
        ]
        
        if description:
            result.append(f"描述: {description}")
        
        result.append(f"\n提示：可以使用 read_file 或 extract_document 工具读取此文件")
        
        return "\n".join(result)
    
    except requests.Timeout:
        return "错误: 下载请求超时（30秒）"
    except requests.RequestException as e:
        return f"错误: 下载失败 - {str(e)}"
    except PermissionError:
        return f"错误: 没有写入权限到 {downloads_dir}"
    except Exception as e:
        return f"错误: 下载时出错 - {str(e)}"


if __name__ == "__main__":
    # 测试
    print(download_file(
        "https://www.example.com/sample.pdf",
        filename="test.pdf",
        description="测试PDF文件"
    ))

