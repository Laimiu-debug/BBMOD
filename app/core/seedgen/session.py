"""Durable, recoverable file transaction for one seed-generation session."""
from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path, PurePosixPath


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FileSession:
    def __init__(self, game_root: Path) -> None:
        self.game_root = Path(game_root).resolve()
        self.data = self.game_root / "data"
        self.root = self.game_root / "bbmod_seedgen_session"
        if self.root.is_symlink() or self.data.is_symlink():
            raise ValueError("刷种子暂不支持 data 或会话目录为符号链接")
        self.manifest = self.root / "session.json"
        self.preserved: list[Path] = []

    @property
    def active(self) -> bool:
        return self.manifest.is_file()

    def _path(self, base: Path, relative: str) -> Path:
        rel = PurePosixPath(relative)
        if not relative or rel.is_absolute() or ".." in rel.parts or ":" in relative or "\\" in relative:
            raise ValueError("会话包含不安全的相对路径")
        target = base.joinpath(*rel.parts)
        if not target.resolve().is_relative_to(base.resolve()) or target.suffix.lower() == ".dat":
            raise ValueError("会话路径越界或指向官方档案")
        return target

    def begin(self, payload: dict[str, bytes]) -> None:
        if self.active:
            raise RuntimeError("请先恢复未结束的刷种子会话")
        if not self.data.is_dir():
            raise FileNotFoundError("游戏 data 目录不存在")
        self.root.mkdir(exist_ok=True)
        originals: dict[str, dict] = {}
        # Include every active mod and every loose payload file before any game write.
        paths = {p.name for p in self.data.glob("*.zip")} | {p.name for p in self.data.glob("*.rar")}
        mod_names = sorted(paths)
        paths |= set(payload)
        created_dirs = set()
        for name in sorted(paths):
            target = self._path(self.data, name)
            backup = self._path(self.root / "originals", name)
            if target.exists():
                if not target.is_file():
                    raise ValueError(f"目标不是文件：{target}")
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                originals[name] = {"sha256": digest(backup)}
            else:
                originals[name] = {"sha256": None}
            for directory in target.parents:
                if directory == self.data:
                    break
                if not directory.exists():
                    created_dirs.add(directory.relative_to(self.data).as_posix())
        journal = {
            "schema": 1, "game_root": str(self.game_root), "originals": originals,
            "mods": mod_names, "injected": {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()},
            "created_dirs": sorted(created_dirs),
        }
        pending = self.manifest.with_suffix(".tmp")
        pending.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
        pending.replace(self.manifest)
        # The journal and verified original copies now cover every subsequent mutation.
        for name in mod_names:
            self._path(self.data, name).unlink()
        for name, content in payload.items():
            target = self._path(self.data, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def restore(self) -> int:
        if not self.active:
            return 0
        journal = json.loads(self.manifest.read_text(encoding="utf-8"))
        if journal.get("schema") != 1 or journal.get("game_root") != str(self.game_root):
            raise ValueError("会话清单与当前游戏不匹配")
        # Verify all backups before restoring any file.
        for name, original in journal["originals"].items():
            if original["sha256"] is not None:
                backup = self._path(self.root / "originals", name)
                if not backup.is_file() or digest(backup) != original["sha256"]:
                    raise RuntimeError(f"原文件备份丢失或校验失败，已保留会话：{name}")
        for name, original in journal["originals"].items():
            target = self._path(self.data, name)
            current = digest(target) if target.is_file() else None
            if current == original["sha256"]:
                continue
            expected = journal["injected"].get(name)
            if current is not None and current != expected:
                # Preserve a partially written payload or concurrent user modification.
                preserved = self._path(self.root / "preserved", name)
                if preserved.exists():
                    preserved = preserved.with_name(preserved.name + "." + uuid.uuid4().hex[:8])
                preserved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, preserved)
                self.preserved.append(preserved)
            if original["sha256"] is None:
                if target.exists():
                    target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self._path(self.root / "originals", name), target)
        for relative in sorted(journal["created_dirs"], key=lambda value: len(PurePosixPath(value).parts), reverse=True):
            directory = self._path(self.data, relative)
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        count = len(journal["mods"])
        self.manifest.unlink()
        backups = (self.root / "originals").resolve()
        if backups.exists():
            if not backups.is_relative_to(self.root.resolve()) or backups == self.root.resolve():
                raise ValueError("备份清理路径越界")
            shutil.rmtree(backups)
        if not any(self.root.iterdir()):
            self.root.rmdir()
        return count
