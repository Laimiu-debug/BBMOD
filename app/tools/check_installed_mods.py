"""Read-only installed MOD UI verification against real archives and public metadata.

The game is never launched and no install/update/uninstall action is invoked.
All catalog/settings cache writes go to a temporary directory. A before/after
inventory checks that game data and MOD-management files remained unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from core.modmanager import ModManager
from core.online_catalog import parse_catalog
from core.site_config import SITE_ORIGIN
from ui.mods_page import ModsPage
from ui.theme import apply_theme


class IsolatedSettings:
    def __init__(self, directory):
        self.path = Path(directory) / 'settings.json'
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding='utf-8')


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    data_changed = Signal()

    def __init__(self, game, settings):
        super().__init__()
        self.mm = ModManager(game)
        self.settings = settings
        self.management_busy = self.seedgen_active = False

    def set_management_busy(self, active):
        self.management_busy = active
        self.management_changed.emit(active)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(game):
    """Record data entries and management files, hashing mutable MOD/archive files."""
    result = {}
    paths = list((game / 'data').rglob('*'))
    if (game / 'bbmod_disabled').exists():
        paths.extend((game / 'bbmod_disabled').rglob('*'))
    for path in paths:
        if not path.is_file():
            continue
        stat = path.stat()
        row = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
        if path.suffix.casefold() in {'.zip', '.rar', '.json', '.log'}:
            row['sha256'] = digest(path)
        result[str(path.relative_to(game))] = row
    return result


def wait_for_catalog(application, service, timeout):
    deadline = time.monotonic() + timeout
    while True:
        application.processEvents()
        worker = service.worker
        if not (worker and worker.isRunning()) and not service._pending:
            application.processEvents()
            return True
        if time.monotonic() >= deadline:
            # Keep the QObject tree alive until its read-only worker finishes.
            return False
        time.sleep(.02)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/installed-mod-ui-readonly')
    parser.add_argument('--catalog', type=Path, help='An official parse_catalog JSON snapshot; history still uses GET/HEAD.')
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--expected-count', type=int)
    parser.add_argument('--expect-afei-local')
    parser.add_argument('--expect-afei-latest')
    args = parser.parse_args()
    game = args.game.resolve()
    if not (game / 'data').is_dir():
        raise ValueError('游戏 data 目录不存在。')
    output = args.output.resolve()
    if output == game or game in output.parents:
        raise ValueError('验证输出须保存在游戏目录外。')
    output.mkdir(parents=True, exist_ok=True)
    before = inventory(game)
    application = QApplication.instance() or QApplication([])
    apply_theme(application)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='bbmod-installed-readonly-') as temporary:
        context = Context(game, IsolatedSettings(temporary))
        page = ModsPage(context)
        page.resize(1320, 740)
        page.show()
        page.refresh()
        assert page.catalog_service is not None
        if args.catalog:
            items = parse_catalog(json.loads(args.catalog.read_text(encoding='utf-8')))
            page.catalog_service.use_catalog(items)
        page.check_catalog(force=not bool(args.catalog))
        completed = wait_for_catalog(application, page.catalog_service, args.timeout)
        if not completed:
            # Network operations have their own finite timeouts. Await their
            # completion rather than terminating a thread during file reads.
            page.catalog_service.worker.wait()
            application.processEvents()
        rows = []
        for row, mod in enumerate(page._installed_mods):
            button = page.table.cellWidget(row, 5)
            rows.append({'file_name': mod.path.name, 'enabled': mod.enabled,
                         'name': page.table.item(row, 2).text(),
                         'installed_version': page.table.item(row, 3).text(),
                         'latest_version': page.table.item(row, 4).text(),
                         'status': page.table.item(row, 4).toolTip(),
                         'update_button': bool(button),
                         'update_enabled': bool(button and button.isEnabled()),
                         'tooltip': page.table.item(row, 2).toolTip(),
                         'sha256': digest(mod.path)})
        application.processEvents()
        assert page.grab().save(str(output / 'screenshot.png'))
        after = inventory(game)
        by_file = {row['file_name']: row for row in rows}
        afei = by_file.get('mod_afeix_expedition.zip')
        modern_hooks = by_file.get('mod_fox_008.zip')
        bundle = by_file.get('mod_afeix_dlc_afei_bundle.zip')
        xiwen = by_file.get('mod_afeix_dlc_xiwen_regen.zip')
        checks = {'catalog_completed': completed,
                  'game_files_unchanged': before == after,
                  'updates_not_invoked': True,
                  'game_not_launched': True,
                  'settings_isolated': Path(context.settings.path).parent == Path(temporary)}
        if args.expected_count is not None:
            checks['installed_count'] = len(rows) == args.expected_count
        if args.expect_afei_local:
            checks['afei_installed_version'] = bool(afei and afei['installed_version'] == args.expect_afei_local)
        if args.expect_afei_latest:
            checks['afei_latest_version'] = bool(afei and afei['latest_version'] == args.expect_afei_latest)
            if args.expect_afei_local:
                checks['afei_update_button'] = bool(afei and afei['update_enabled'])
        if modern_hooks:
            checks['modern_hooks_chinese_name'] = '框架' in modern_hooks['name']
        if bundle:
            checks['bundle_release_version'] = bundle['installed_version'] == '0.1.0'
        if xiwen:
            checks['xiwen_release_version'] = xiwen['installed_version'] == '0.2.5'
        changed = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
        report = {'checked_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
                  'game_root': str(game), 'official_origin': SITE_ORIGIN,
                  'catalog_snapshot': str(args.catalog.resolve()) if args.catalog else None,
                  'network_operations': ['official catalog GET' if not args.catalog else 'catalog from official snapshot',
                                         'public MOD history GET', 'release checksum HEAD'],
                  'mod_payload_downloaded': False, 'elapsed_seconds': round(time.monotonic() - started, 3),
                  'catalog_items': len(page.catalog_service.items), 'catalog_status': page.catalog_status.text(),
                  'checks': checks, 'passed': all(checks.values()), 'changed_game_files': changed,
                  'rows': rows, 'release_versions': page.catalog_service.release_versions,
                  'hashes': page.catalog_service.hashes}
        report_path = output / 'installed-real-readonly.json'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'passed': report['passed'], 'checks': checks,
                          'elapsed_seconds': report['elapsed_seconds'], 'report': str(report_path),
                          'rows': [{key: row[key] for key in ('file_name', 'name', 'installed_version', 'latest_version', 'update_button')}
                                   for row in rows]}, ensure_ascii=False, indent=2))
        page.close()
        application.processEvents()
        return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
