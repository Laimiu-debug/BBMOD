"""mod 仓库：内置合集 + 外部导入文件夹。

仓库根目录下的 zip/rar 自动经 modinfo 静态分析，并按文件名匹配
data/mod_index.json 中的预置元数据（分类/中文名/说明）作增强。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .modinfo import ModInfo, analyze_zip
from .paths import resource_path

# 内置元数据索引（随软件分发）：文件名 → {category, name_cn, note}
INDEX_FILE = resource_path("data/mod_index.json")

CATEGORIES = ["框架", "基础功能", "作弊", "汉化", "其他"]


def load_index() -> dict[str, dict]:
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@dataclass
class RepoEntry:
    info: ModInfo
    root: Path
    category: str = "其他"
    name_cn: str = ""
    note: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.name_cn or (self.info.registrations[0].name if self.info.registrations else self.info.primary_id)

    @property
    def seed_sensitive(self) -> bool:
        return bool(self.info.seed_sensitive_paths)


class ModStore:
    def __init__(self, roots: list[Path]) -> None:
        self.roots = [Path(r) for r in roots if Path(r).exists()]
        self._index = load_index()

    def add_root(self, root: Path) -> bool:
        root = Path(root)
        if root.exists() and root not in self.roots:
            self.roots.append(root)
            return True
        return False

    def scan(self) -> list[RepoEntry]:
        """扫描所有仓库根目录（含一层子目录，如 基础功能MOD/）。"""
        entries: list[RepoEntry] = []
        seen: set[Path] = set()
        for root in self.roots:
            pattern_dirs = [root] + [d for d in root.iterdir() if d.is_dir()] if root.exists() else []
            for d in pattern_dirs:
                for f in sorted(d.glob("*.zip")) + sorted(d.glob("*.rar")):
                    if f in seen:
                        continue
                    seen.add(f)
                    entries.append(self._make_entry(f, root))
        return entries

    def _make_entry(self, f: Path, root: Path) -> RepoEntry:
        info = analyze_zip(f)
        meta = self._index.get(f.name, {})
        category = meta.get("category") or self._infer_category(info, f, root)
        return RepoEntry(
            info=info,
            root=root,
            category=category,
            name_cn=meta.get("name_cn", ""),
            note=meta.get("note", ""),
            tags=meta.get("tags", []),
        )

    @staticmethod
    def _infer_category(info: ModInfo, f: Path, root: Path) -> str:
        # 依目录名推断
        for part in f.parent.parts:
            if "作弊" in part:
                return "作弊"
            if "汉化" in part:
                return "汉化"
            if "基础功能" in part:
                return "基础功能"
        if any(r.mod_id in ("mod_modern_hooks", "mod_msu", "mod_hooks") for r in info.registrations):
            return "框架"
        return "其他"
