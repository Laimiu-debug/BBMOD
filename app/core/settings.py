"""应用配置持久化：JSON 存于 %APPDATA%/BBMOD/settings.json"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from .io_util import atomic_write_json
from .site_config import canonical_site_origin


def _settings_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "BBMOD"
    return Path.home() / ".bbmod"


class Settings:
    _unread = False  # 上次读取暂时失败；save() 时先与磁盘内容合并

    def __init__(self) -> None:
        self.path = _settings_dir() / "settings.json"
        self.data: dict[str, Any] = {}
        self.load()

    def _read(self) -> dict | None:
        """读取磁盘配置；文件缺失返回 {}，内容损坏返回 None，暂时无法读取（被占用等）抛出 OSError。"""
        for attempt in range(3):
            try:
                text = self.path.read_text(encoding="utf-8")
                break
            except FileNotFoundError:
                return {}
            except UnicodeDecodeError:
                return None
            except PermissionError:
                # Windows: antivirus or another instance briefly holds the file.
                if attempt == 2:
                    raise
                time.sleep(0.05)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def load(self) -> None:
        self._unread = False
        try:
            data = self._read()
        except OSError:
            # Transient failure: the file may be valid, so neither rename nor
            # overwrite it blindly; save() merges with it once readable.
            data, self._unread = {}, True
        if data is None:
            # Keep the unreadable file so the next save cannot silently discard it.
            try:
                os.replace(self.path, self.path.with_name(self.path.name + ".corrupt"))
            except OSError:
                self._unread = True
            data = {}
        if 'online_catalog_url' in data:
            data['online_catalog_url'] = canonical_site_origin(data['online_catalog_url'])
        self.data = data

    def save(self) -> None:
        if self._unread:
            # A failed read must also fail the save, even if replacing the file
            # would be allowed. Keep pending changes in memory until a retry.
            disk = self._read()
            if disk is None:
                os.replace(self.path, self.path.with_name(self.path.name + ".corrupt"))
                disk = {}
            self.data = {**disk, **self.data}
        atomic_write_json(self.path, self.data)
        self._unread = False

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()
