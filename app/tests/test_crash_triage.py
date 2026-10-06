"""Suspect attribution, last-known-good selection and guided bisect of MOD sets."""
from html import escape
import itertools
import zipfile
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication

from core import bisect
from core.crash_reports import begin_session, clean_exit, ReportStore
from core.crash_suspects import describe, find_suspects
from core.gamelog import LogRow
from core.modmanager import LAST_GOOD_PROFILE, ModManager
from ui.mods_page import ModsPage
from ui_wait import refreshed, settle_mods


def mod_zip(path, files=None, register=None, requires=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as archive:
        for name in files or ['scripts/' + path.stem + '.nut']:
            archive.writestr(name, '// ' + name)
        if register:
            body = f'::Hooks.register("{register}", "1.0.0", "{register}")'
            body += ''.join(f'.require("{r}")' for r in requires)
            archive.writestr(f'scripts/!mods_preload/{register}.nut', body + ';')
    return path


def html_row(text, level='error', tag='Script Error'):
    return (f'<div class="row {level}"><div class="time">12:00:00</div><div class="tag">{tag}</div>'
            f'<div class="text">{escape(text)}</div></div>')


@pytest.fixture
def manager(tmp_path):
    root = tmp_path / 'game'
    (root / 'data').mkdir(parents=True)
    return ModManager(root)


def infos(manager):
    return [m.info for m in manager.scan() if m.enabled]


def test_stack_paths_point_at_the_copy_the_game_runs(manager):
    shared = 'scripts/skills/perk_shared.nut'
    mod_zip(manager.data / 'a_base.zip', [shared, 'scripts/a_only.nut'])
    mod_zip(manager.data / 'b_patch.zip', [shared])
    mod_zip(manager.data / 'c_other.zip', ['scripts/c_only.nut'], register='mod_other_thing')
    rows = [LogRow('error', '1', 'Script Error', "the index 'getID' does not exist"),
            LogRow('error', '1', 'Script Error', 'Function: onUpdate -> scripts/skills/perk_shared.cnut : 42'),
            LogRow('error', '1', 'Script Error', 'Function: update -> scripts/a_only.nut : 7'),
            LogRow('info', '1', 'SQ', 'unrelated row'),
            LogRow('error', '1', 'hooks', 'mod_other_thing failed to queue')]
    suspects = find_suspects(rows, infos(manager))
    names = [s.file_name for s in suspects]
    # The later-mounted b_patch.zip is the copy that ran; a_base.zip is also involved.
    assert names[0] == 'b_patch.zip'
    assert set(names) == {'a_base.zip', 'b_patch.zip', 'c_other.zip'}
    assert any('被 b_patch.zip 覆盖' in reason for reason in suspects[names.index('a_base.zip')].reasons)
    assert '可能相关的 MOD' in describe([s.as_dict() for s in suspects])


def test_vanilla_only_stack_and_framework_frames_are_not_blamed(manager):
    mod_zip(manager.data / 'mod_msu.zip', ['scripts/msu/wrapper.nut'], register='mod_msu')
    mod_zip(manager.data / 'z_mod.zip', ['scripts/z_mod.nut'])
    rows = [LogRow('error', '1', 'Script Error', 'boom'),
            LogRow('error', '1', 'Script Error', 'Function: wrap -> scripts/msu/wrapper.nut : 1'),
            LogRow('error', '1', 'Script Error', 'Function: tick -> scripts/z_mod.nut : 2')]
    suspects = find_suspects(rows, infos(manager))
    assert [s.file_name for s in suspects] == ['z_mod.zip', 'mod_msu.zip']
    assert find_suspects([LogRow('error', '1', 'Script Error', 'Function: x -> scripts/vanilla.nut : 1')],
                         infos(manager)) == []
    assert '未能从报错定位' in describe([])


def test_capture_records_suspects_and_clean_exit_is_detected(manager, tmp_path):
    mod_zip(manager.data / 'broken.zip', ['scripts/broken.nut'])
    folder = tmp_path / 'logs'
    folder.mkdir()
    log = folder / 'log.html'
    session = begin_session([folder])
    log.write_text(html_row('the index x does not exist') +
                   html_row('Function: run -> scripts/broken.nut : 3'), encoding='utf-8')
    assert not clean_exit(session, [folder])
    store = ReportStore(tmp_path / 'reports')
    item = store.capture(SimpleNamespace(game=None, mm=manager), session, [folder])
    assert item['suspects'][0]['file_name'] == 'broken.zip'
    assert 'broken.zip' in item['payload']['diagnostic_report']

    session = begin_session([folder])
    with log.open('a', encoding='utf-8') as stream:
        stream.write(html_row('Shutting down engine core.', level='info', tag='Engine'))
    assert clean_exit(session, [folder])
    assert not clean_exit(begin_session([folder]), [folder])  # unchanged log proves nothing


def test_last_good_profile_is_reserved_and_skipped_while_bisecting(manager):
    mod_zip(manager.data / 'one.zip')
    mod_zip(manager.disabled_dir / 'two.zip')
    saved = manager.remember_last_good()
    assert saved['enabled'] == ['one.zip'] and saved['automatic']
    assert manager.load_profiles()[LAST_GOOD_PROFILE]['enabled'] == ['one.zip']
    with pytest.raises(ValueError):
        manager.save_profile(LAST_GOOD_PROFILE)
    manager.rename_profile(LAST_GOOD_PROFILE, 'kept')
    assert 'automatic' not in manager.load_profiles()['kept']
    bisect.save(manager, bisect.start(['one.zip'], [], ['one.zip']))
    assert manager.remember_last_good() is None
    assert LAST_GOOD_PROFILE not in manager.load_profiles()


def test_bisect_finds_any_single_mod_or_conflicting_pair():
    names = [f'm{i:02}.zip' for i in range(11)]

    def run(bad):
        state = bisect.start(names + ['fw.zip'], ['fw.zip'], names)
        for _ in range(40):
            if state['stage'] == 'done':
                return state['result'], sorted(state['found'])
            bisect.record(state, bad <= bisect.test_set(state, {}))
        pytest.fail('bisect did not finish')
    for name in names:
        assert run({name}) == ('found', [name])
    for pair in itertools.combinations(names, 2):
        assert run(set(pair)) == ('found', sorted(pair))
    assert run({'fw.zip'}) == ('outside', [])


def test_bisect_rounds_keep_requirements_and_restore_original(manager):
    mod_zip(manager.data / 'hooks.zip', register='mod_modern_hooks')
    mod_zip(manager.data / 'needs_lib.zip', register='mod_needs_lib', requires=['mod_lib'])
    mod_zip(manager.data / 'lib.zip', register='mod_lib')
    mod_zip(manager.data / 'plain.zip')
    mod_zip(manager.disabled_dir / 'off.zip')
    original = manager.installed_zip_names()
    state = bisect.start(original, ['hooks.zip'], original - {'hooks.zip'})
    bisect.apply_round(manager, state)
    assert manager.installed_zip_names() == {'hooks.zip'}
    bisect.record(state, False)
    assert bisect.tested(state) == ['lib.zip']
    bisect.apply_round(manager, state)
    assert manager.installed_zip_names() == {'hooks.zip', 'lib.zip'}
    bisect.record(state, False)  # right half: needs_lib.zip, plain.zip
    bisect.apply_round(manager, state)
    # needs_lib.zip pulls in its requirement even though lib.zip is in the other half.
    assert manager.installed_zip_names() == {'hooks.zip', 'lib.zip', 'needs_lib.zip', 'plain.zip'}
    assert bisect.load(manager)['round'] == state['round']
    bisect.restore(manager, state)
    assert manager.installed_zip_names() == original
    assert bisect.load(manager) is None and (manager.disabled_dir / 'off.zip').exists()


class Context(QObject):
    management_changed = Signal(bool)
    session_changed = Signal(bool)
    data_changed = Signal()

    def __init__(self, manager):
        super().__init__()
        self.mm = manager
        self.management_busy = self.seedgen_active = False
        self.settings = SimpleNamespace(get=lambda key, default=None: default)

    def set_management_busy(self, active):
        self.management_busy = active
        self.management_changed.emit(active)


def test_bisect_dialog_guides_rounds_and_disables_the_culprit(manager, monkeypatch):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr('core.game.is_game_running', lambda: False)
    mod_zip(manager.data / 'mod_msu.zip', register='mod_msu')
    for name in ('alpha', 'beta', 'gamma', 'delta'):
        mod_zip(manager.data / f'{name}.zip')
    page = ModsPage(Context(manager), automatic_catalog=False)
    refreshed(page)
    page.start_bisect()
    dialog = page._bisect_dialog
    checked = {dialog.candidates.item(i).text(): dialog.candidates.item(i).checkState() == Qt.Checked
               for i in range(dialog.candidates.count())}
    assert checked == {'alpha.zip': False, 'beta.zip': False, 'delta.zip': False,
                       'gamma.zip': False, 'mod_msu.zip': True}
    dialog.begin()
    settle_mods(page)
    assert manager.installed_zip_names() == {'mod_msu.zip'} and page.bisect_btn.text().startswith('继续排查')
    culprit = 'gamma.zip'
    for _ in range(10):
        if dialog.state['stage'] == 'done':
            break
        dialog.answer(culprit in manager.installed_zip_names())
        settle_mods(page)
    assert dialog.state["found"] == [culprit] and dialog.stack.currentIndex() == 2, (dialog.state, page.status_label.text())
    dialog.restore_without_found()
    settle_mods(page)
    assert manager.installed_zip_names() == {'mod_msu.zip', 'alpha.zip', 'beta.zip', 'delta.zip'}
    assert bisect.load(manager) is None and '已禁用' not in page.bisect_btn.text()
    assert 'gamma.zip' in page.status_label.text()
    page.close()
    application.processEvents()
