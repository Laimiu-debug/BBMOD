"""Exercise font choices, live application, restart persistence and large layouts."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# The Windows backend discovers installed fonts; Qt's generic offscreen backend
# on Windows only exposes application fonts. Keep the native test windows hidden.
os.environ['QT_QPA_PLATFORM'] = 'windows' if os.name == 'nt' else 'offscreen'
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractButton, QCheckBox, QComboBox, QLineEdit, QSpinBox, QTableWidget
from core.appearance import Appearance
from core.settings import Settings
from ui.main_window import MainWindow, apply_dark_palette
from ui.theme import apply_theme, font_families, resolve_appearance
from ui.workers import Worker


def ready(window):
    deadline = time.monotonic() + 35
    while any(worker.isRunning() for worker in window.findChildren(Worker)):
        assert time.monotonic() < deadline
        QTest.qWait(30)
    QTest.qWait(100)


def reachable(scroll, widget):
    scroll.ensureWidgetVisible(widget, 4, 4)
    QTest.qWait(40)
    assert widget.isVisible()
    assert widget.visibleRegion().contains(widget.rect().adjusted(2, 2, -2, -2)), (widget.objectName(), widget.size().toTuple(), scroll.size().toTuple())
    if isinstance(widget, (QAbstractButton, QComboBox, QLineEdit, QSpinBox)):
        padding = 0 if isinstance(widget, QCheckBox) else 4
        if widget.height() < widget.fontMetrics().height()+padding:
            widget.window().grab().save(str(ROOT/'build/review/font-settings/failed-control.png'))
        assert widget.height() >= widget.fontMetrics().height()+padding, (
            type(widget).__name__, widget.objectName(), widget.height(), widget.fontMetrics().height(),
            widget.currentText() if isinstance(widget, QComboBox) else widget.text() if isinstance(widget, QAbstractButton) else '',
            widget.minimumSizeHint().toTuple(), widget.parentWidget().minimumSizeHint().toTuple())


def reload_check():
    app = QApplication([])
    apply_dark_palette(app)
    window = MainWindow(auto_updates=False)
    window.setAttribute(Qt.WA_DontShowOnScreen)
    window.show()
    ready(window)
    actual = window.settings_page.saved.to_dict()
    assert app.font().family() == actual['font_family'] and app.font().pointSize() == actual['font_size']
    window.close()
    print(json.dumps(actual))


def main():
    output = ROOT/'build/review/font-settings'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-font-settings-') as temporary, ExitStack() as guard:
        os.environ['APPDATA'] = temporary
        for name in ('core.game.launch_executable', 'core.game.kill_game'):
            guard.enter_context(patch(name, side_effect=AssertionError('Game actions are forbidden in this UI check')))
        prefs = Settings()
        prefs.set('seed_campaign', {'origin':'scenario.cultists','combat_difficulty':2})
        prefs.set('localization_choices', {'test':'bbmod'})
        preserved = dict(prefs.data)
        app = QApplication([])
        apply_dark_palette(app)
        window = MainWindow(auto_updates=False)
        window.setAttribute(Qt.WA_DontShowOnScreen)
        window.show()
        ready(window)
        page = window.settings_page
        assert window.tabs.count() == 7 and page.size.value() == 12
        QTest.mouseClick(window.nav_buttons[4], Qt.LeftButton)
        assert window.tabs.currentIndex() == 4
        old_font = window.launch_btn.font()
        families = [page.family.itemText(i) for i in range(page.family.count())]
        chosen = next((name for name in ('Microsoft YaHei UI','Microsoft YaHei','微软雅黑','SimSun','宋体') if name in families),
                      next(name for name in families if name != font_families()[0]))
        page.family.setCurrentFont(QFont(chosen))
        page.size.setFocus()
        QTest.keyClick(page.size, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(page.size, '14')
        QTest.keyClick(page.size, Qt.Key_Tab)
        assert page.sample_body.font().pointSize() == 14
        assert window.launch_btn.font() == old_font
        assert 'appearance' not in Settings().data
        reachable(window.page_scrolls[4], page.apply_button)
        QTest.mouseClick(page.apply_button, Qt.LeftButton)
        QTest.qWait(120)
        assert window.launch_btn.font().family() == chosen
        assert window.launch_btn.font().pointSize() == 14
        assert Settings().get('appearance') == {'font_family':chosen,'font_size':14}
        for key,value in preserved.items():
            assert Settings().get(key) == value
        saved = Settings().get('appearance')
        restarted = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--reload-check'],
            capture_output=True, timeout=50, env=dict(os.environ), creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert restarted.returncode == 0, (restarted.stdout+restarted.stderr).decode(errors='replace')
        assert json.loads(restarted.stdout) == saved
        # A moved/removed system font has a deterministic readable fallback.
        assert resolve_appearance({'font_family':'BBMOD Missing Font Fixture','font_size':14}) == Appearance(font_families()[0],14)
        # Failed persistence must not alter the running theme or unrelated state.
        page.size.setValue(15)
        with patch.object(page.settings, 'save', side_effect=OSError('read-only fixture')):
            page.apply()
        assert window.launch_btn.font().pointSize() == 14
        assert page.settings.get('appearance') == saved
        assert '无法保存' in page.status.text()
        page._load(page.saved)

        layouts=[]
        for family,size,width,height in ((font_families()[0],12,1360,880), (chosen,14,1080,720),
                                         (font_families()[0],18,1080,720), (chosen,18,1360,880)):
            page.family.setCurrentFont(QFont(family))
            page.size.setValue(size)
            page.apply()
            window.resize(width,height)
            QTest.qWait(180)
            assert window.size().toTuple() == (width,height), window.size().toTuple()
            for table in window.findChildren(QTableWidget):
                header_font=QFont(table.horizontalHeader().font())
                header_font.setBold(True)
                metrics=QFontMetrics(header_font)
                for column in range(table.columnCount()):
                    label=table.horizontalHeaderItem(column)
                    if label:
                        assert table.columnWidth(column)>=metrics.horizontalAdvance(label.text())+16, (label.text(), table.columnWidth(column))
            for index in range(7):
                window.select_page(index)
                ready(window)
                scroll=window.page_scrolls[index]
                if index==0:
                    important=[window.dashboard.refresh_btn]
                elif index==1:
                    important=[window.mods.disable_btn,window.mods.enable_btn,window.mods.save_profile_btn]
                elif index==2:
                    important=[window.l10n.management.choice]
                elif index==3:
                    seed=window.seedgen
                    seed.sections.setCurrentIndex(0)
                    seed.mode_combo.setCurrentText('只找红装')
                    seed.weapon_filter.kind.setCurrentIndex(1)
                    important=[seed.weapon_filter.kind,seed.weapon_filter.weapon,seed.weapon_filter.count,
                               seed.weapon_filter.damage,seed.weapon_filter.penetration,seed.start_btn]
                elif index==4:
                    important=[page.family,page.size,page.reset_button,page.apply_button]
                elif index==5:
                    window.inspector.sections.setCurrentIndex(0)
                    for widget in (window.inspector.catalog_page.search, window.inspector.catalog_page.group,
                                   window.inspector.catalog_page.rarity, window.inspector.catalog_page.detail_button):
                        reachable(scroll, widget)
                    window.inspector.sections.setCurrentIndex(1)
                    window.inspector.setup_toggle.setChecked(True)
                    QTest.qWait(80)  # Let the new scroll page lay out before locating controls.
                    important=[window.inspector.enabled, window.inspector.shortcut, window.inspector.apply_key,
                               window.inspector.opacity, window.inspector.install, window.inspector.open_button]
                else:
                    important=[window.feedback.title, window.feedback.details, window.feedback.submit_button]
                for widget in important:
                    reachable(window.inspector.sections.widget(1) if index == 5 else scroll,widget)
                if index == 3:
                    seed.sections.setCurrentIndex(1)
                    seed.preview_btn.setChecked(True)
                    QTest.qWait(60)
                    for widget in [seed.publish_btn, seed.publish_all_btn, seed.cancel_share_btn, seed.copy_codes_btn,
                                   seed.library_search, seed.library_view, seed.delete_btn, seed.preview_btn, seed.export_btn]:
                        reachable(scroll, widget)
                    seed.preview_btn.setChecked(False)
                scroll.verticalScrollBar().setValue(0)
                scroll.horizontalScrollBar().setValue(0)
                QTest.qWait(40)
                image=output/f'{width}-{family.replace(" ","_")}-{size}-page{index}.png'
                assert window.grab().save(str(image))
                layouts.append({'family':family,'size':size,'window':[width,height],'page':index,
                                'controls_reachable':True,'vertical_scroll':scroll.verticalScrollBar().maximum(),
                                'horizontal_scroll':scroll.horizontalScrollBar().maximum()})
        # Reset is a preview until the user applies it.
        window.select_page(4)
        QTest.mouseClick(page.reset_button,Qt.LeftButton)
        assert page.draft() == Appearance(font_families()[0],12)
        assert app.font().pointSize() == 18
        page.apply()
        assert app.font().pointSize() == 12 and Settings().get('appearance')['font_size'] == 12
        window.close()
        report={'font_choices':families,'live_apply':True,'preview_without_saving':True,'restart_persistence':True,
                'missing_font_fallback':True,'save_error_keeps_running_font':True,'unrelated_settings_preserved':True,
                'reset_to_recommended':True,'headers_fit_large_fonts':True,'game_started':False,'layouts':layouts}
        (output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'checks':'passed','layouts':len(layouts),'font_choices':len(families),'game_started':False}))


if __name__=='__main__':
    reload_check() if '--reload-check' in sys.argv else main()
