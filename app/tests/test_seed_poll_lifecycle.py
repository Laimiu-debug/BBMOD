"""Verify the reader stops before restore and queued old batches stay isolated."""
import time
from types import SimpleNamespace

from core.game import GameInfo
from core.gamelog import IncrementalLogReader
from core.seedgen.log_watcher import SeedLogParser
from core.seedgen.orchestrator import SeedGenOrchestrator, StopLimits
from test_seed_live_ui import app, page


def session_at(tmp_path, records):
    directory = tmp_path / 'logs'
    directory.mkdir()
    session = SeedGenOrchestrator(GameInfo(tmp_path, tmp_path / 'game.exe', '1.5.2.3', tmp_path / 'data'), tmp_path,
                                  log_directory=directory)
    path = directory / 'log.txt'
    path.write_text('BBMODSeedSession: ' + session._session_id + '\n' + ''.join(
        f'Seed: SEED{i:06d} LoopIdx:{i} Origin:scenario.lone_wolf\nCRLF\n' for i in range(records)), encoding='utf-8')
    reader, parser = IncrementalLogReader(path), SeedLogParser(session_id=session._session_id)
    session._reader, session._parser = reader, parser
    session._readers = {path: (reader, parser)}
    session.state.stage = 'running'
    session._started_at = time.monotonic()
    return session


def wait_for_parsed(session):
    deadline = time.monotonic() + 2
    while not session.results and time.monotonic() < deadline:
        time.sleep(0.01)
    assert session.results


def test_stop_saves_batch_not_yet_delivered_to_gui_and_ignores_queued_signal(page, app, tmp_path):
    session = session_at(tmp_path, 20)
    page.orch = session
    page._start_polling()
    worker = page._poll_worker

    def restore():
        assert not worker.isRunning()
        return 2

    session.stop_and_restore = restore
    try:
        wait_for_parsed(session)  # The GUI has not processed its queued signal.
        assert page.results == []
        page.stop()
        assert page.orch is None and len(page.results) == 20
        message = page.progress_label.text()
        app.processEvents()
        assert len(page.results) == 20 and page.progress_label.text() == message
    finally:
        page.shutdown_polling()


def test_automatic_limit_stops_reader_before_restoring(page, app, tmp_path):
    session = session_at(tmp_path, 20)
    session.limits = StopLimits(hits=1)
    page.orch = session
    page._start_polling()
    worker = page._poll_worker
    restored = []

    def restore():
        assert not worker.isRunning()
        restored.append(True)
        return 2

    session.stop_and_restore = restore
    try:
        deadline = time.monotonic() + 2
        while page.orch is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert restored == [True] and page.orch is None
        assert len(page.library.all()) == 20
    finally:
        page.shutdown_polling()


def test_changing_log_directory_stops_old_reader_and_preserves_pending_batch(page, app, tmp_path, monkeypatch):
    session = session_at(tmp_path, 20)
    new_directory = tmp_path / 'new-logs'
    new_directory.mkdir()
    (new_directory / 'log.txt').write_text('BBMODSeedSession: ' + session._session_id +
        '\nSeed: NEWLOG0000 LoopIdx:21 Origin:scenario.lone_wolf\nCRLF\n', encoding='utf-8')
    monkeypatch.setattr('core.seedgen.orchestrator.game_mod.find_log_write_paths', lambda preferred=None: [preferred])
    page.orch = session
    page._start_polling()
    old_worker = page._poll_worker
    try:
        wait_for_parsed(session)
        page._set_log_directory(new_directory)
        assert not old_worker.isRunning() and page._poll_worker is not old_worker
        assert len(page.results) == 20
        deadline = time.monotonic() + 2
        while len(page.results) < 21 and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert len(page.results) == 21 and page.results[-1].seed == 'NEWLOG0000'
        assert session.log_path == new_directory / 'log.txt'
    finally:
        page.shutdown_polling()
        page.orch = None


def test_failed_reader_shutdown_leaves_directory_and_settings_untouched(page, tmp_path):
    changed = []
    page.orch = SimpleNamespace(set_log_directory=lambda folder: changed.append(folder))
    page._poll_worker = SimpleNamespace(stop=lambda: False)
    previous = page._log_directory
    try:
        page._set_log_directory(tmp_path)
        assert page._log_directory == previous and changed == []
        assert 'seed_log_directory' not in page.ctx.settings.data
    finally:
        page._poll_worker = None
        page.orch = None
