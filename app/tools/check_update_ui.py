"""Render the actual update dialog using clearly labelled sample release metadata."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from core.app_updates import Release, RELEASES_URL
from core.settings import Settings
from ui.theme import apply_theme
from ui.update_service import UpdateService
from ui.update_dialog import UpdateDialog


def main():
    output = ROOT/'build/review/updates'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-update-ui-') as temporary:
        os.environ['APPDATA'] = temporary
        app = QApplication([]);apply_theme(app)
        service = UpdateService(Settings(), automatic=False)
        service.status = '演示版本记录，仅用于界面检查。'
        service.releases = [Release('v0.3.0-rc.5', '演示新版', '演示更新说明（非已发布版本）\n\n支持自动检查与手动下载。\n下载后校验文件，点击重启更新。', '2026-09-17', True,
                                    RELEASES_URL+'/tag/v0.3.0-rc.5', RELEASES_URL+'/download/v0.3.0-rc.5/BBMOD.exe', 75540000, 'a'*64),
                            Release('v0.3.0-rc.4', '当前版本', '版本管理与自动检查更新。', '2026-09-17', True, RELEASES_URL+'/tag/v0.3.0-rc.4')]
        dialog = UpdateDialog(service);dialog.show()
        report = []
        for width, height in ((860,620), (660,500)):
            dialog.resize(width,height);app.processEvents()
            assert (dialog.width(),dialog.height()) == (width,height)
            for button in (dialog.check,dialog.download,dialog.close_buttons.button(QDialogButtonBox.Close)):
                assert dialog.rect().contains(button.mapTo(dialog,button.rect().bottomRight()))
            assert dialog.grab().save(str(output/f'version-center-{width}.png'))
            report.append({'size':[width,height], 'controls_in_bounds':True})
        (output/'ui-validation.json').write_text(json.dumps({'game_started':False,'renders':report},indent=2),encoding='utf-8')
        print(json.dumps(report));dialog.close();service.shutdown()

if __name__ == '__main__':
    main()
