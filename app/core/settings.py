"""应用配置持久化：JSON 存于 %APPDATA%/BBMOD/settings.json"""
from __future__ import annotations

import json
import os
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
    def __init__(self) -> None:
        self.path = _settings_dir() / "settings.json"
        self.data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            data = None
        if not isinstance(data, dict):
            # Keep the unreadable file so the next save cannot silently discard it.
            try:
                os.replace(self.path, self.path.with_name(self.path.name + ".corrupt"))
            except OSError:
                pass
            data = {}
        if 'online_catalog_url' in data:
            data['online_catalog_url'] = canonical_site_origin(data['online_catalog_url'])
        self.data = data

    def save(self) -> None:
        atomic_write_json(self.path, self.data)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()
