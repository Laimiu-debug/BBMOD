from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import uuid

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox

from core.game import GameInfo
from core.modmanager import ModManager
from ui.game_session import GameSession
from ui.saves_page import SavesPage


class Context(QObject):
    data_changed = Signal()
    game_changed = Signal()
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    def __init__(self, root, directory):
        super().__init__()
        self.mm = ModManager(root)
        self.mm.data.mkdir(parents=True)
        self.game = GameInfo(root, root/'win32/BattleBrothers.exe', '1.5.2.3', self.mm.data)
        self.settings = SimpleNamespace(get=lambda key, default=None: str(directory) if key == 'savegames_directory' else default)
        self.management_busy = self.seedgen_active = False
        self.game_session = GameSession(probe=lambda: False)
        self.game_session.observe(False)
    def set_management_busy(self, active):
        self.management_busy = active
        self.management_changed.emit(active)


@pytest.fixture
def view(tmp_path):
    app = QApplication.instance() or QApplication([])
    directory = tmp_path/'savegames'
    directory.mkdir()
    (directory/'campaign.sav').write_bytes(b'\xbb\x00\x02\x41\x00\x00\x00' + b'fixture' * 100)
    ctx = Context(tmp_path/'game', directory)
    mods = SimpleNamespace(online=SimpleNamespace(address=QLineEdit('https://bbmod.com')),
                           profile_origin=lambda: 'https://bbmod.com', _can_modify=lambda: True)
    page = SavesPage(ctx, mods)
    yield app, page
    if page.runner.worker:
        page.runner.worker.wait(5000)
    app.processEvents()
    ctx.game_session.shutdown()
    page.close()


def settle(app, page):
    for _ in range(300):
        app.processEvents()
        if not page.ctx.management_busy:
            if page.runner.worker:
                page.runner.worker.wait(3000)
            return
        QTest.qWait(10)
    pytest.fail('Save UI worker did not finish')


def test_local_save_selection_and_game_operation_locks(view):
    _, page = view
    assert page.local_table.rowCount() == 1 and page.share_btn.isEnabled()
    page.ctx.game_session.observe(True)
    assert not page.share_btn.isEnabled() and not page.import_btn.isEnabled()
    page.ctx.game_session.observe(False)
    page.ctx.mm.transaction.journal.parent.mkdir(parents=True)
    page.ctx.mm.transaction.journal.write_text('{}')
    page.refresh()
    assert not page.share_btn.isEnabled() and not page.import_btn.isEnabled()
    assert page.recover_btn.isEnabled()


def test_gallery_search_is_readable_without_game_and_source_change_clears_links(view):
    app, page = view
    identity = str(uuid.uuid4())
    response = {'page': 1, 'pages': 1, 'total': 1, 'items': [{'id': identity, 'name': '<b>战团</b>',
        'note': '第 100 天', 'dlcs': [], 'mod_count': 2, 'total_size': 1024, 'game_version': '1.5.2.3',
        'page_path': f'/saves/{identity}/'}]}
    page.ctx.mm = None
    with patch('ui.saves_page.shared_saves.fetch_saves', return_value=response):
        page.load_catalog()
        settle(app, page)
    assert page.online_table.item(0, 0).text() == '<b>战团</b>'
    assert '<b>战团</b>' in page.details.toPlainText()
    assert not page.restore_btn.isEnabled()
    assert page.copy_btn.isEnabled()
    page.copy_link()
    assert app.clipboard().text() == 'https://bbmod.com/saves/' + identity + '/'
    page._source_changed()
    assert page.selected_online() is None and not page.copy_btn.isEnabled()


def test_cancelled_restore_preview_does_not_change_game_or_save_files(view):
    app, page = view
    identity = str(uuid.uuid4())
    with patch('ui.saves_page.shared_saves.fetch_save', return_value={'name': '战团', 'mods': []}), \
            patch('ui.saves_page.shared_saves.preview_restore', return_value={
                'mods': {'download': [], 'disable': []}, 'target': str(page.directory()/'new.sav')}), \
            patch('ui.saves_page.preview_dialog', return_value=False), \
            patch('ui.saves_page.shared_saves.restore') as restore:
        page.import_link(identity)
        settle(app, page)
    restore.assert_not_called()
    assert list(page.directory().glob('*.sav')) == [page.directory()/'campaign.sav']
