"""BBMOD 管理器入口。--selftest：无界面自检（打包后验证用）。"""
from __future__ import annotations

import os
import sys
import traceback


def selftest() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from core.l10n_compat import hooks_assets
    from core.seedgen.traits import traits
    from core.seedgen.weapons import NAMED_WEAPONS, WEAPON_CHOICES
    from core.version import VERSION
    from ui.main_window import MainWindow, apply_dark_palette

    app = QApplication([])
    app.setApplicationVersion(VERSION)
    apply_dark_palette(app)
    w = MainWindow(auto_updates=False)
    w.show()
    QTimer.singleShot(6000, app.quit)
    app.exec()
    errors = w.dashboard.report.error_count if w.dashboard.report else -1
    manager_ready = w.l10n.sections.count() == 2 and w.l10n.management.choice.count() >= 3
    guidance_ready = (bool(w.l10n.management.current_name.text())
                      and w.l10n.management.advanced_panel.isHidden())
    hooks_ready = len(hooks_assets()) == 4
    trait_count = len(traits())
    weapon_count = len(NAMED_WEAPONS)
    weapons_ready = w.seedgen.weapon_filter.weapon.count() == len(WEAPON_CHOICES)
    ports_ready = all(getattr(w.seedgen, name, None) is not None
                      and getattr(w.seedgen, name).objectName() == name
                      for name in ('north_south_ports', 'arena_port'))
    updater_ready = hasattr(w, 'updates') and w.updates.reply is None and not w.updates.timer.isActive()
    settings_ready = w.tabs.count() == 7 and w.settings_page.family.count() > 0
    equipment_ready = (w.inspector.sections.count() == 2 and w.inspector.sections.currentIndex() == 0
                       and w.inspector.catalog_page.table.rowCount() > 94)
    launch_ready = (w.l10n.management.session is w.ctx.game_session
                    and w.ctx.game_session.state in {'idle', 'running'})
    sharing_ready = (hasattr(w.seedgen, 'publish_all_btn') and hasattr(w.seedgen, 'share_progress')
                     and not w.seedgen._share_active and not w.seedgen.cancel_share_btn.isEnabled())
    seed_copy_ready = w.seedgen.copy_codes_btn.objectName() == 'copySeedCodes'
    print(f"equipment_catalog: {'ready' if equipment_ready else 'missing'} entries={w.inspector.catalog_page.table.rowCount()}")
    print(f"game_launch_feedback: {'ready' if launch_ready else 'missing'} state={w.ctx.game_session.state}")
    print(f"localization_guidance: {'ready' if guidance_ready else 'missing'}")
    print(f"seed_share_queue: {'ready' if sharing_ready else 'missing'}")
    print(f"seed_code_copy: {'ready' if seed_copy_ready else 'missing'}")
    print(f"selftest: installed={w.mods.table.rowCount()} l10n_entries={len(w.l10n.entries)} diag_errors={errors} l10n_manager={'ready' if manager_ready else 'missing'} legacy_hooks={'ready' if hooks_ready else 'missing'} seed_traits={trait_count} seed_weapons={weapon_count if weapons_ready else 0} seed_ports={'ready' if ports_ready else 'missing'} version={VERSION} updater={'ready' if updater_ready else 'missing'} font_settings={'ready' if settings_ready else 'missing'}")
    ok = settings_ready and len(w.l10n.entries) > 0 and not w.windowIcon().isNull() and manager_ready and guidance_ready and hooks_ready and trait_count == 58
    if w.ctx.game:
        ok = ok and errors >= 0
    return 0 if ok and updater_ready and weapons_ready and weapon_count == 50 and ports_ready and equipment_ready and launch_ready and sharing_ready and seed_copy_ready else 1


def main() -> int:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow, apply_dark_palette
    from core.version import VERSION

    app = QApplication(sys.argv)
    app.setApplicationVersion(VERSION)
    apply_dark_palette(app)
    window = MainWindow()
    window.show()
    return app.exec()


def check_updates_selftest() -> int:
    """Verify frozen Qt networking without a window, game access or user settings."""
    import json
    import tempfile
    from PySide6.QtCore import QCoreApplication, QTimer
    from core.settings import Settings
    from ui.update_service import UpdateService
    with tempfile.TemporaryDirectory(prefix='bbmod-frozen-update-') as temporary:
        os.environ['APPDATA'] = temporary
        app = QCoreApplication([])
        service = UpdateService(Settings(), automatic=False)
        result = {'success': False, 'game_started': False}
        def finished():
            if not service.busy:
                result.update(success=bool(service.preferences.get('last_check')),
                              releases=len(service.releases), status=service.status)
                app.quit()
        service.changed.connect(finished)
        QTimer.singleShot(30000, app.quit)
        QTimer.singleShot(0, service.check)
        app.exec()
        service.changed.disconnect(finished)
        service.shutdown()
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['success'] else 1


if __name__ == "__main__":
    sys.excepthook = lambda t, v, tb: traceback.print_exception(t, v, tb)
    if '--apply-update' in sys.argv:
        from pathlib import Path
        from core.app_updates import install_request
        result = install_request(Path(sys.argv[sys.argv.index('--apply-update') + 1]), verify_mode='--verify-update' in sys.argv)
        raise SystemExit(0 if result['status'] == 'installed' else 1)
    if '--check-updates-selftest' in sys.argv:
        raise SystemExit(check_updates_selftest())
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(main())
