"""资源路径：兼容源码运行与 PyInstaller frozen 两种模式。"""
from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """应用资源根（源码=app/，打包=_MEIPASS/）。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # noqa: SLF001
    return Path(__file__).resolve().parent.parent


def resource_path(rel: str) -> Path:
    return app_root() / rel
