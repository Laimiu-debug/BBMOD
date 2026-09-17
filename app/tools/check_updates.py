"""Read real public releases and optionally verify an EXE download in a temp profile."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QCoreApplication, QTimer
from core.settings import Settings
from ui.update_service import UpdateService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--report', type=Path, default=ROOT/'build/review/public-update-check.json')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='bbmod-public-update-') as temporary:
        os.environ['APPDATA'] = temporary
        app = QCoreApplication([])
        service = UpdateService(Settings(), automatic=False)
        state = {'download_started': False, 'success': False, 'game_started': False}
        def changed():
            if service.busy:
                return
            if not service.releases or (state['download_started'] and not service.downloaded):
                state['error'] = service.status
                app.quit();return
            if args.download and not state['download_started']:
                state['download_started'] = True
                service.download(service.releases[0]);return
            state.update(success=True, release_count=len(service.releases), latest=service.releases[0].tag,
                         check_status=service.status, downloaded_bytes=service.downloaded.stat().st_size if service.downloaded else 0)
            app.quit()
        service.changed.connect(changed)
        QTimer.singleShot(120000, app.quit)
        QTimer.singleShot(0, service.check)
        app.exec()
        service.shutdown()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(state, ensure_ascii=False))
        return 0 if state['success'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
