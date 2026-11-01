"""Preview the real seed UI using isolated, explicitly labelled sample data."""
import argparse
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.seedgen.log_watcher import SeedResult
from ui.seedgen_page import SeedGenPage
from ui.theme import apply_theme


class PreviewSettings:
    def __init__(self, directory):
        self.path = directory / 'settings.json'
        self.values = {'seed_lair_filter': {
            'version': 2, 'total_enabled': True, 'total': 20, 'weapons_enabled': True,
            'match': 'all', 'rows': [
                {'weapon': 'weapon.named_javelin', 'count': 2, 'damage': 75, 'penetration': 75, 'score': 90, 'quality': 80},
                {'weapon': 'weapon.named_greatsword', 'count': 1, 'score': 80},
            ],
        }}
    def get(self, key, default=None):
        return self.values.get(key, default)
    def set(self, key, value):
        self.values[key] = value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshots', type=Path)
    parser.add_argument('--width', type=int, default=1180)
    args = parser.parse_args()
    app = QApplication([])
    apply_theme(app)
    with tempfile.TemporaryDirectory(prefix='bbmod-weapons-') as temporary:
        page = SeedGenPage(SimpleNamespace(game=None, settings=PreviewSettings(Path(temporary))))
        page.mode_combo.setCurrentText('只找红装')
        page.setWindowTitle('BBMOD · 多武器筛选与红武评分预览（示例数据）')
        page.progress_label.setText('界面预览 · 示例数据可操作；可查看评分说明与“我的种子”')
        page._accept_results([SeedResult('DEMORED001', 1, done=True, lines=[
            'NamedInfo: Sum:20 RangedWeapon:2 TwoHanded:1',
            'LairInfo: 示例营地(Bandit) 150 示例城镇 12-N',
            'ItemInfo(RangedWeapon): weapon.named_javelin(RegularDamage:75%|DirectDamageAdd:100%)',
            'ItemInfo(TwoHanded): weapon.named_greatsword(StaminaModifier:0%|FatigueOnSkillUse:100%)',
        ])])
        page.resize(args.width, 860)
        page.show()
        if args.screenshots:
            args.screenshots.mkdir(parents=True, exist_ok=True)
            def capture():
                page.grab().save(str(args.screenshots / f'filters-{args.width}.png'))
                page.sections.setCurrentIndex(1)
                page.preview_btn.setChecked(True)
                page.format_combo.setCurrentIndex(page.format_combo.findData('detail'))
                app.processEvents()
                page.detail_label.verticalScrollBar().setValue(page.detail_label.verticalScrollBar().maximum())
                page.grab().save(str(args.screenshots / f'ratings-{args.width}.png'))
                (args.screenshots / 'sample-record.txt').write_text(page.detail_label.toPlainText(), encoding='utf-8')
                app.quit()
            QTimer.singleShot(250, capture)
        app.exec()
        page.close()


if __name__ == '__main__':
    main()
