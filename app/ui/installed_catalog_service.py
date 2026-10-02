"""Background official catalog and file identity checks for the installed list."""
import hashlib
import json
import os
from pathlib import Path
import re
import time

from PySide6.QtCore import QObject, Signal

from core.catalog_versions import identify_release_versions
from core.online_catalog import fetch_catalog, parse_catalog
from core.site_config import SITE_ORIGIN
from core.installed_mod_catalog import receipt_needs_hash, resolve_installed_mod
from .workers import Worker


class InstalledCatalogService(QObject):
    changed = Signal(object)
    busy_changed = Signal(bool)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.path = Path(settings.path).parent / 'installed-mod-catalog.json'
        self.items, self.release_versions, self.hashes = [], {}, {}
        self.checked_at = 0
        self.worker = None
        self._pending = None
        try:
            if self.path.stat().st_size > 4 * 1024 * 1024:
                raise ValueError('目录缓存过大')
            cache = json.loads(self.path.read_text('utf-8'))
            if cache.get('origin') != SITE_ORIGIN:
                raise ValueError('缓存来源不匹配')
            self.items = parse_catalog(cache)
            versions = cache.get('release_versions', {})
            self.release_versions = {identity: {sha: version for sha, version in mapping.items()
                if re.fullmatch('[a-f0-9]{64}', sha) and isinstance(version, str) and len(version) <= 40}
                for identity, mapping in versions.items() if isinstance(mapping, dict)}
            self.checked_at = float(cache.get('checked_at', 0))
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def snapshot(self, status=''):
        return {'items': self.items, 'hashes': self.hashes, 'release_versions': self.release_versions, 'status': status}

    def use_catalog(self, items):
        self.items = parse_catalog({'schema_version': 1, 'mods': list(items)})
        self.checked_at = time.time()

    def check(self, infos, *, force=False, receipts=None, local_index=None):
        infos = list(infos)
        if self.worker and self.worker.isRunning():
            self._pending = (infos, force, receipts, local_index)
            return
        items, versions, hashes = self.items, self.release_versions, self.hashes
        fetch = force or not items or not 0 <= time.time() - self.checked_at < 300

        def work():
            status = ''
            checked_at = self.checked_at
            active_items = items
            if fetch:
                try:
                    active_items = fetch_catalog(SITE_ORIGIN)
                    checked_at = time.time()
                except Exception as error:
                    status = '官网暂时无法连接，保留已有目录：' + str(error)
            updated_versions = {identity: dict(mapping) for identity, mapping in versions.items()}
            updated_hashes = dict(hashes)
            history_started = time.monotonic()
            for info in infos:
                display = resolve_installed_mod(info, active_items, receipts=receipts,
                                                local_index=local_index)
                if display.catalog_item is None and not receipt_needs_hash(info, receipts):
                    continue
                key = None
                try:
                    path = Path(info.path)
                    key = str(path.resolve())
                    stat = path.stat()
                    cached = updated_hashes.get(key)
                    signature = (stat.st_mtime_ns, stat.st_size, stat.st_dev, stat.st_ino)
                    if (cached and len(cached) >= 5
                            and (cached[0], cached[1], cached[3], cached[4]) == signature):
                        sha256 = cached[2]
                    else:
                        with path.open('rb') as stream:
                            before = os.fstat(stream.fileno())
                            sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
                            read_after = os.fstat(stream.fileno())
                        after = path.stat()
                        def same_signature(value):
                            return (value.st_mtime_ns, value.st_size, value.st_dev, value.st_ino) == signature
                        if not all(same_signature(value) for value in (before, read_after, after)):
                            updated_hashes[key] = None
                            continue
                        updated_hashes[key] = (stat.st_mtime_ns, stat.st_size, sha256, stat.st_dev, stat.st_ino)
                    display = resolve_installed_mod(info, active_items, receipts=receipts,
                                                    local_index=local_index, local_sha256=sha256)
                    item = display.catalog_item
                    if item is None:
                        continue
                    known = updated_versions.setdefault(item['id'], {})
                    known[item['sha256']] = item['version']
                    if sha256 not in known and time.monotonic() - history_started < 20:
                        try:
                            updated_versions[item['id']] = identify_release_versions(SITE_ORIGIN, item, sha256, known)
                        except Exception:
                            pass  # Unknown files stay version-unknown; never guess an update.
                except OSError:
                    if key is not None:
                        updated_hashes[key] = None
                    continue
            return {'items': active_items, 'release_versions': updated_versions, 'hashes': updated_hashes,
                    'checked_at': checked_at, 'status': status or f'官网版本检查完成 · {len(active_items)} 件作品'}

        self.worker = Worker(work, self)
        self.worker.done.connect(self._done)
        self.worker.failed.connect(lambda error: self.changed.emit(self.snapshot('官网版本检查未完成：' + error)))
        self.worker.finished.connect(self._finished)
        self.worker.start()
        self.busy_changed.emit(True)

    def _done(self, result):
        self.items = result['items']
        self.release_versions, self.hashes = result['release_versions'], result['hashes']
        self.checked_at = result['checked_at']
        self.changed.emit(result)
        try:
            from core.online_catalog import _atomic_json
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_json(self.path, {'schema_version': 1, 'origin': SITE_ORIGIN, 'mods': self.items,
                                    'checked_at': self.checked_at, 'release_versions': self.release_versions})
        except OSError:
            pass

    def _finished(self):
        self.busy_changed.emit(False)
        if self._pending:
            infos, force, receipts, local_index = self._pending
            self._pending = None
            self.check(infos, force=force, receipts=receipts, local_index=local_index)
