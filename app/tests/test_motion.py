from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget
import pytest

from core.settings import Settings
from ui.motion import MotionStack
from ui.settings_page import SettingsPage


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def stack(app):
    app.setProperty('bbmodReduceMotion', False)
    widget = MotionStack()
    for _ in range(3):
        page = QWidget()
        QVBoxLayout(page).addWidget(QLineEdit('draft'))
        widget.addWidget(page)
    widget.resize(400, 300)
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    app.setProperty('bbmodReduceMotion', False)


def test_fast_navigation_keeps_destination_and_drafts(stack):
    editor = stack.widget(0).findChild(QLineEdit)
    editor.setText('unsaved draft')
    stack.setCurrentIndex(1)
    assert stack.currentIndex() == 1
    assert stack._overlay.testAttribute(Qt.WA_TransparentForMouseEvents)
    stack.setCurrentIndex(2)
    stack.setCurrentIndex(0)
    assert stack.currentWidget().findChild(QLineEdit).text() == 'unsaved draft'
    QTest.qWait(250)
    assert stack._overlay is None
    assert stack._animation is None


def test_resize_clears_snapshot_without_changing_page(stack, app):
    stack.setCurrentIndex(1)
    stack.resize(500, 350)
    app.processEvents()
    assert stack._overlay is None
    assert stack.currentIndex() == 1


def test_reduced_motion_switches_immediately(stack, app):
    app.setProperty('bbmodReduceMotion', True)
    stack.setCurrentIndex(2)
    assert stack.currentIndex() == 2
    assert stack._overlay is None


def test_motion_setting_persists_and_handles_write_failure(app, tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    settings = Settings()
    page = SettingsPage(settings)
    page.reduce_motion.setChecked(True)
    assert Settings().get('reduce_motion') is True
    assert app.property('bbmodReduceMotion') is True
    monkeypatch.setattr(settings, 'set', lambda *args: (_ for _ in ()).throw(OSError('disk full')))
    page.reduce_motion.setChecked(False)
    assert page.reduce_motion.isChecked()
    assert settings.get('reduce_motion') is True
    assert app.property('bbmodReduceMotion') is True
    assert '设置未保存' in page.motion_status.text()
    page.close()
    app.setProperty('bbmodReduceMotion', False)
