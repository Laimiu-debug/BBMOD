"""Replay a stopped seed log through the real background reader, GUI and SQLite.

All writes use a temporary profile. No game launch, MOD changes, uploads, or
writes to the user's seed database are performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from core.game import GameInfo
from core.gamelog import IncrementalLogReader
from core.seedgen.log_watcher import SeedLogParser
from core.seedgen.orchestrator import SeedGenOrchestrator
from core.settings import Settings
from ui.seedgen_page import SeedGenPage, LIBRARY_PAGE_SIZE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    source = args.log.resolve(strict=True)
    before = source.stat()
    with source.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as content:
        marker = re.search(rb'BBMODSeedSession: ([a-f0-9]{32})', content)
        if marker is None:
            raise RuntimeError('A BBMOD session marker is required')
        session_id = marker.group(1).decode()
        expected = sum(1 for _ in re.finditer(rb'Seed: [A-Za-z]{10} LoopIdx:', content))
        origin = re.search(rb'Origin:(scenario\.[\w_]+)', content).group(1).decode()
        digest = hashlib.sha256(content).hexdigest()
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='bbmod-seed-replay-') as temporary:
        profile = Path(temporary)
        settings = Settings.__new__(Settings)
        settings.path = profile / 'settings.json'
        settings.data = {'seed_campaign': {'origin': origin}}
        game = GameInfo(profile / 'unused-game', profile / 'unused-game.exe', '1.5.2.3', profile / 'unused-data')
        ctx = SimpleNamespace(game=game, settings=settings,
                              data_changed=SimpleNamespace(emit=lambda: None), set_seedgen_active=lambda _: None)
        page = SeedGenPage(ctx)
        session = SeedGenOrchestrator(game, profile)
        session._session_id = session_id
        reader = IncrementalLogReader(source)
        log_parser = SeedLogParser(session_id=session_id)
        session._reader, session._parser = reader, log_parser
        session._readers = {source: (reader, log_parser)}
        session.state.stage = 'running'
        session._started_at = time.monotonic()
        page.orch = session
        loop = QEventLoop()
        heartbeat = QTimer()
        heartbeat.setInterval(20)
        started = previous = time.perf_counter()
        gaps = []
        complete = False

        def sample():
            nonlocal previous, complete
            now = time.perf_counter()
            gaps.append(now - previous)
            previous = now
            if reader.offset >= before.st_size and len(page.results) == expected:
                complete = True
                loop.quit()
            elif now - started > 45:
                loop.quit()

        heartbeat.timeout.connect(sample)
        heartbeat.start()
        page._start_polling()
        try:
            loop.exec()
            elapsed = time.perf_counter() - started
            if not complete:
                raise RuntimeError(f'Replay timed out: saved {len(page.results)}/{expected}, bytes {reader.offset}')
            if not page.shutdown_polling():
                raise RuntimeError('Reader did not stop')
            assert len(session.results) == expected
            assert page.library.all() == page.results
            assert page.table.rowCount() <= LIBRARY_PAGE_SIZE
            after = source.stat()
            assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Log changed during replay'
            report = {
                'source_log': str(source), 'source_bytes': before.st_size, 'source_sha256': digest,
                'origin': origin, 'records_saved_and_verified': expected,
                'latest_round': max(record.loop_idx for record in session.results),
                'old_one_chunk_per_second_minimum_seconds': math.ceil(before.st_size / reader.CHUNK_SIZE),
                'background_read_save_and_render_seconds': round(elapsed, 3),
                'maximum_gui_heartbeat_gap_seconds': round(max(gaps, default=0), 3),
                'visible_rows': page.table.rowCount(), 'page_size': LIBRARY_PAGE_SIZE,
                'database_round_trip_matches': True, 'game_launched': False, 'user_database_modified': False,
            }
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False, indent=2))
        finally:
            heartbeat.stop()
            page.shutdown_polling()
            page.orch = None
            page.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
