"""
Setup script for kobe-mcp-server - Root directory version
"""
import sys
from pathlib import Path
from setuptools import setup

setup(
    name="kobe-mcp-server",
    version="1.0.1",
    description="Kobe MCP Server for Codex",
    author="Kobe",
    py_modules=["mcp_server_codex"],
    install_requires=[
        "mcp>=1.17.0",
        "aiohttp>=3.13.0",
    ],
    entry_points={
        "console_scripts": [
            "kobe-mcp-server=mcp_server_codex:main_wrapper",
        ],
    },
    python_requires=">=3.10",
)


