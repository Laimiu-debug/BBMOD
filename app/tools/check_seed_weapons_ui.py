"""Render the real weapon-filter page in an isolated profile; no game launch."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from core.seedgen.log_watcher import SeedResult
from ui.main_window import MainWindow, apply_dark_palette
from ui.workers import Worker


def main():
    output = ROOT / 'build/review/seed-weapons'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-weapons-ui-') as temporary:
        os.environ['APPDATA'] = temporary
        app = QApplication([])
        apply_dark_palette(app)
        window = MainWindow(auto_updates=False)
        window.show()
        deadline = time.monotonic() + 30
        while any(worker.isRunning() for worker in window.findChildren(Worker)):
            assert time.monotonic() < deadline, 'UI worker did not finish'
            QTest.qWait(25)
        window.select_page(3)
        page = window.seedgen
        page.mode_combo.setCurrentText('只找红装')
        filt = page.weapon_filter
        filt.kind.setFocus()
        QTest.keyClick(filt.kind, Qt.Key_Down)
        filt.weapon.setCurrentIndex(filt.weapon.findData('weapon.named_javelin'))
        filt.count.setValue(2)
        filt.damage.setValue(75)
        filt.penetration.setValue(75)
        # A clearly marked fixture exercises result layout, not game acceptance.
        record = SeedResult('UI_FIXTURE', 1, done=True, lines=[
            'ItemInfo(RangedWeapon): weapon.named_javelin(RegularDamage:75%|DirectDamageAdd:100%) MinDamage:40 MaxDamage:60 DirectDamage:0.45 AmmoMax:5'])
        page._accept_results([record])
        page.format_combo.setCurrentIndex(page.format_combo.findData('detail'))
        page.table.selectRow(0)
        report = []
        for width, height in ((1360, 880), (1080, 720)):
            window.resize(width, height)
            app.processEvents()
            assert (window.width(), window.height()) == (width, height)
            for widget in (filt.kind, filt.weapon, filt.count, filt.damage, filt.penetration, page.start_btn, page.export_btn):
                window.page_scrolls[3].ensureWidgetVisible(widget, 4, 4)
                QTest.qWait(40)
                assert widget.isVisible()
                assert window.rect().contains(widget.mapTo(window, widget.rect().bottomRight()))
                assert widget.visibleRegion().contains(widget.rect().adjusted(1, 1, -1, -1)), widget.objectName()
                assert widget.height() >= widget.fontMetrics().height() + 4, (width, widget.objectName(), widget.height(), widget.fontMetrics().height(), filt.height(), filt.stack.height())
            assert '红标枪：伤害品质 75%' in page.detail_label.toPlainText()
            assert window.grab().save(str(output / f'weapons-{width}.png'))
            report.append({'size':[width,height], 'controls_reachable_by_scrolling':True})
        window.close()
        result = {'game_started':False, 'fixture_data_used':True, 'layouts':report, 'weapon_types':50,
                  'config': page._current_config().lair_conditions}
        (output / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
