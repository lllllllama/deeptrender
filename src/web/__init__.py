"""
Web 可视化模块

提供 Flask API 和静态前端界面。
"""

from .app import create_app, run_server

__all__ = ["create_app", "run_server"]
