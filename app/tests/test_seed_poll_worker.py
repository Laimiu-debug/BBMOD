"""Exercise Qt delivery, backpressure and stopping with an actual temporary log."""
from threading import get_ident
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtCore import QEventLoop, QObject, QTimer, Slot
from PySide6.QtWidgets import QApplication

from core.game import GameInfo
from core.seedgen.orchestrator import SeedGenOrchestrator
from ui.seed_poll_worker import SeedPollWorker


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def pump(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def test_background_burst_delivery_waits_for_gui_ack_and_stops(app, tmp_path):
    log = tmp_path / 'log.txt'
    game = GameInfo(tmp_path, tmp_path / 'game.exe', '1.5.2.3', tmp_path / 'data')
    session = SeedGenOrchestrator(game, tmp_path)
    log.write_text('BBMODSeedSession: ' + session._session_id + '\n' + ''.join(
        f'Seed: SEED{i:06d} LoopIdx:{i}\nCRLF\n' for i in range(4000)), encoding='utf-8')
    with patch('core.seedgen.orchestrator.game_mod.find_log_write_paths', return_value=[tmp_path]):
        session._discover_readers()
    batches, thread_ids = [], []
    main_thread = get_ident()
    native_poll = session.poll

    def poll():
        thread_ids.append(get_ident())
        return native_poll()

    session.poll = poll

    class Receiver(QObject):
        @Slot(object)
        def receive(self, records):
            assert get_ident() == main_thread
            batches.append(records)

    receiver = Receiver()
    worker = SeedPollWorker(session)
    worker.batch_ready.connect(receiver.receive)
    worker.start()
    try:
        for _ in range(30):
            pump(20)
            if batches:
                break
        assert len(batches) == 1 and len(batches[0]) == 4000
        assert thread_ids == [thread_ids[0]] and thread_ids[0] != main_thread
        pump(100)
        assert len(batches) == 1  # No second batch while the GUI has not saved it.
        with log.open('a', encoding='utf-8') as stream:
            stream.write('Seed: APPENDED00 LoopIdx:4001\nCRLF\n')
        worker.acknowledge()
        for _ in range(30):
            pump(20)
            if len(batches) > 1:
                break
        assert [r.seed for r in batches[1]] == ['APPENDED00']
    finally:
        assert worker.stop()
    assert not worker.isRunning() and len(session.results) == 4001


def test_background_read_error_is_reported_and_thread_ends(app):
    def fail():
        raise OSError('test log unavailable')

    worker = SeedPollWorker(SimpleNamespace(poll=fail))
    errors = []
    worker.failed.connect(errors.append)
    worker.start()
    assert worker.wait(2000)
    pump(20)
    assert errors == ['test log unavailable']
