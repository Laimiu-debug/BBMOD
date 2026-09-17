"""共享应用上下文：游戏定位、设置、管理器实例与全局刷新信号。"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core import game as game_mod
from core.modmanager import ModManager
from core.modstore import ModStore
from core.settings import Settings

_COLLECTION_DIR = "狐狸汉化精选MOD合集"
_COLLECTION_PARENT_PREFIX = "1.5.2.3游戏版本"


def _collection_candidates() -> list[Path]:
    """合集目录候选：源码位置 + exe 各级父目录扫描（打包后把软件放在仓库内任意层级都能找到）。"""
    out: list[Path] = []
    anchors = [Path(__file__).resolve().parents[2]]
    if getattr(sys, "frozen", False):
        p = Path(sys.executable).parent
        for _ in range(4):
            anchors.append(p)
            p = p.parent
    for base in anchors:
        direct = base / _COLLECTION_DIR
        if direct.exists():
            out.append(direct)
            continue
        for child in base.glob(f"{_COLLECTION_PARENT_PREFIX}*"):
            if (child / _COLLECTION_DIR).exists():
                out.append(child / _COLLECTION_DIR)
    seen: set[Path] = set()
    uniq = []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


class AppContext(QObject):
    game_changed = Signal()
    data_changed = Signal()  # data 目录 mod 增删/启停后广播
    session_changed = Signal(bool)
    management_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        self.game = game_mod.locate_game(self.settings.get("game_path"))
        self.mm = ModManager(self.game.root) if self.game else None
        self.seedgen_active = False
        self.management_busy = False

    def set_management_busy(self, active: bool) -> None:
        self.management_busy = active
        self.management_changed.emit(active)

    def set_seedgen_active(self, active: bool) -> None:
        self.seedgen_active = active
        self.session_changed.emit(active)

    def relocate_game(self, manual: str | None) -> bool:
        g = game_mod.locate_game(manual)
        if g:
            self.game = g
            self.mm = ModManager(g.root)
            if manual:
                self.settings.set("game_path", manual)
            self.game_changed.emit()
            return True
        return False

    def store(self) -> ModStore:
        roots: list[Path] = _collection_candidates()
        extra = self.settings.get("extra_repo_roots", [])
        roots += [Path(r) for r in extra]
        return ModStore(roots)

    def log_dir(self) -> Path | None:
        return game_mod.find_log_write_path()
