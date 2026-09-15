"""BBMOD 管理器入口。--selftest：无界面自检（打包后验证用）。"""
from __future__ import annotations

import os
import sys
import traceback


def selftest() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow, apply_dark_palette

    app = QApplication([])
    apply_dark_palette(app)
    w = MainWindow()
    w.show()
    QTimer.singleShot(6000, app.quit)
    app.exec()
    errors = w.dashboard.report.error_count if w.dashboard.report else -1
    print(f"selftest: installed={w.mods.table.rowCount()} l10n_entries={len(w.l10n.entries)} diag_errors={errors}")
    ok = w.mods.table.rowCount() >= 0 and len(w.l10n.entries) > 0 and errors >= 0
    return 0 if ok else 1


def main() -> int:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow, apply_dark_palette

    app = QApplication(sys.argv)
    apply_dark_palette(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.excepthook = lambda t, v, tb: traceback.print_exception(t, v, tb)
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(main())
