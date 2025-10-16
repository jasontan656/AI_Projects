"""
Setup script for kobe-mcp-server
"""
import sys
from pathlib import Path
from setuptools import setup

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

setup(
    name="kobe-mcp-server",
    version="1.0.0",
    description="Kobe MCP Server for Codex",
    author="Kobe",
    py_modules=["mcp_stdio_server_codex"],
    package_dir={"": str(Path(__file__).parent)},
    install_requires=[
        "mcp>=1.17.0",
        "aiohttp>=3.13.0",
    ],
    entry_points={
        "console_scripts": [
            "kobe-mcp-server=mcp_stdio_server_codex:main_wrapper",
        ],
    },
    python_requires=">=3.10",
)

