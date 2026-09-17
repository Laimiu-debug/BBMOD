"""Durable local seed history. A new expedition never clears this database."""
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

from .log_watcher import SeedResult
from .protocol import seed_key


class SeedLibrary:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS seeds (
                identity TEXT PRIMARY KEY, record TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                share_url TEXT NOT NULL DEFAULT '')""")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def all(self) -> list[SeedResult]:
        with closing(self._connect()) as db:
            return [SeedResult(**json.loads(row[0])) for row in db.execute("SELECT record FROM seeds ORDER BY rowid")]

    def save(self, result: SeedResult) -> SeedResult:
        identity = seed_key(result)
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT record FROM seeds WHERE identity=?", (identity,)).fetchone()
            if row:
                old = SeedResult(**json.loads(row[0]))
                if (old.done and not result.done) or (old.done == result.done and len(old.lines) >= len(result.lines)):
                    return old
            db.execute("INSERT INTO seeds(identity, record) VALUES (?, ?) ON CONFLICT(identity) DO UPDATE SET record=excluded.record",
                       (identity, json.dumps(asdict(result), ensure_ascii=False)))
        return result

    def shared_url(self, result: SeedResult) -> str:
        with closing(self._connect()) as db:
            row = db.execute("SELECT share_url FROM seeds WHERE identity=?", (seed_key(result),)).fetchone()
            return row[0] if row else ""

    def mark_shared(self, result: SeedResult, url: str):
        self.save(result)
        with closing(self._connect()) as db, db:
            db.execute("UPDATE seeds SET share_url=? WHERE identity=?", (url, seed_key(result)))
