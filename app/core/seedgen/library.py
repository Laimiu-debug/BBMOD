"""Durable local seed history. A new expedition never clears this database."""
from contextlib import closing
from collections.abc import Iterable
import json
from pathlib import Path
import sqlite3
import time

from .log_watcher import SeedResult
from .protocol import seed_key
from ..site_config import canonical_site_url


class SeedLibrary:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS seeds (
                identity TEXT PRIMARY KEY, record TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                share_url TEXT NOT NULL DEFAULT '')""")
            if 'deleted_at' not in {row[1] for row in db.execute('PRAGMA table_info(seeds)')}:
                db.execute('ALTER TABLE seeds ADD COLUMN deleted_at TEXT')
            db.execute("""CREATE TABLE IF NOT EXISTS seed_share_state (
                id INTEGER PRIMARY KEY CHECK(id=1), not_before REAL NOT NULL,
                reason TEXT NOT NULL DEFAULT '')""")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def all(self, *, deleted=False) -> list[SeedResult]:
        with closing(self._connect()) as db:
            where = 'IS NOT NULL' if deleted else 'IS NULL'
            return [SeedResult(**json.loads(row[0])) for row in db.execute(f"SELECT record FROM seeds WHERE deleted_at {where} ORDER BY rowid")]

    def is_deleted(self, result):
        with closing(self._connect()) as db:
            row = db.execute('SELECT deleted_at FROM seeds WHERE identity=?', (seed_key(result),)).fetchone()
            return bool(row and row[0])

    def delete(self, identities):
        """Move to the recoverable local trash; public shares remain independent."""
        with closing(self._connect()) as db, db:
            before = db.total_changes
            db.executemany('UPDATE seeds SET deleted_at=CURRENT_TIMESTAMP WHERE identity=? AND deleted_at IS NULL',
                           [(key,) for key in set(identities)])
            return db.total_changes - before

    def restore(self, identities):
        with closing(self._connect()) as db, db:
            before = db.total_changes
            db.executemany('UPDATE seeds SET deleted_at=NULL WHERE identity=? AND deleted_at IS NOT NULL',
                           [(key,) for key in set(identities)])
            return db.total_changes - before

    def save(self, result: SeedResult) -> SeedResult:
        return self.save_many([result])[0][0]

    def save_many(self, results: Iterable[SeedResult]) -> list[tuple[SeedResult, bool]]:
        """Save one batch atomically, returning each merged record and trash state.

        Input order and duplicates retain the same behavior as consecutive saves.
        Existing public links, creation order, and trash state are preserved.
        """
        results = list(results)
        if not results:
            return []
        identities = [seed_key(result) for result in results]
        unique = list(dict.fromkeys(identities))
        saved = []
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            existing = {}
            # Fetch history once per bounded group instead of one query for
            # every result. Keep sequential merge semantics within this batch.
            for start in range(0, len(unique), 500):
                keys = unique[start:start + 500]
                rows = db.execute('SELECT identity, record, deleted_at FROM seeds WHERE identity IN (' +
                                  ','.join('?' for _ in keys) + ')', keys)
                existing.update((identity, (SeedResult(**json.loads(raw)), bool(deleted)))
                                for identity, raw, deleted in rows)
            pending = {}
            for result, identity in zip(results, identities):
                old, deleted = existing.get(identity, (None, False))
                if old is not None:
                    if (old.done and not result.done) or (old.done == result.done and len(old.lines) >= len(result.lines)):
                        saved.append((old, deleted))
                        continue
                existing[identity] = result, deleted
                pending[identity] = result
                saved.append((result, deleted))
            # JSON reads the primitive/list/dict dataclass fields directly;
            # deepcopying all log lines before serialization adds no isolation
            # to this synchronous write, and is expensive for large batches.
            db.executemany("INSERT INTO seeds(identity, record) VALUES (?, ?) ON CONFLICT(identity) DO UPDATE SET record=excluded.record",
                [(identity, json.dumps({name: getattr(result, name) for name in SeedResult.__dataclass_fields__},
                                       ensure_ascii=False)) for identity, result in pending.items()])
        return saved

    def shared_url(self, result: SeedResult) -> str:
        with closing(self._connect()) as db:
            row = db.execute("SELECT share_url FROM seeds WHERE identity=?", (seed_key(result),)).fetchone()
            return canonical_site_url(row[0]) if row else ""

    def mark_shared(self, result: SeedResult, url: str):
        self.save(result)
        with closing(self._connect()) as db, db:
            db.execute("UPDATE seeds SET share_url=? WHERE identity=?", (url, seed_key(result)))

    def share_cooldown(self):
        """Keep server cooldowns across cancellation, new batches and restarts."""
        with closing(self._connect()) as db:
            row = db.execute('SELECT not_before, reason FROM seed_share_state WHERE id=1').fetchone()
            return (max(0, row[0] - time.time()), row[1]) if row else (0, '')

    def defer_sharing(self, seconds, reason='上传间隔'):
        until = time.time() + max(0, seconds)
        with closing(self._connect()) as db, db:
            db.execute("""INSERT INTO seed_share_state(id,not_before,reason) VALUES (1,?,?)
                ON CONFLICT(id) DO UPDATE SET not_before=excluded.not_before, reason=excluded.reason
                WHERE excluded.not_before >= seed_share_state.not_before""", (until, reason))
