"""应用配置持久化：JSON 存于 %APPDATA%/BBMOD/settings.json"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
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
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(self.data, dict) and 'online_catalog_url' in self.data:
                self.data['online_catalog_url'] = canonical_site_origin(self.data['online_catalog_url'])
        except (OSError, json.JSONDecodeError):
            self.data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()
