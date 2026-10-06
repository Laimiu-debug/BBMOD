"""Bounded local snapshots of errors produced by a BBMOD game launch."""
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from .crash_suspects import describe, find_suspects
from .gamelog import iter_rows
from .io_util import atomic_write_json
from .support_report import build_report, MAX_REPORT_CHARS
from .version import VERSION

AUTO_UPLOAD_KEY = 'auto_upload_crash_reports'
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_RECORDS = 20
SHUTDOWN = 'shutting down engine core.'


def fingerprint(path):
    try:
        with Path(path).open('rb') as stream:
            stat = os.fstat(stream.fileno())
            length = min(stat.st_size, 4096)
            prefix = hashlib.sha256(stream.read(length)).hexdigest()
        return {'size': stat.st_size, 'mtime': stat.st_mtime_ns, 'prefix': prefix, 'length': length}
    except OSError:
        return None


def begin_session(folders):
    return {'started': time.time(), 'logs': {str(Path(folder) / 'log.html'):
            fingerprint(Path(folder) / 'log.html') for folder in folders}}


def read_session_log(path, session):
    """Ignore unchanged logs and, for append-only logs, all pre-launch rows."""
    current = fingerprint(path)
    old = session['logs'].get(str(path))
    if not current or current == old or current['mtime'] / 1e9 < session['started'] - 2:
        return None
    with path.open('rb') as stream:
        offset = 0
        if old and old['size'] and current['size'] >= old['size']:
            prefix = hashlib.sha256(stream.read(old['length'])).hexdigest()
            if prefix == old['prefix']:
                offset = old['size']
        offset = max(offset, current['size'] - MAX_LOG_BYTES)
        stream.seek(offset)
        raw = stream.read(MAX_LOG_BYTES)
    rows = iter_rows(raw.decode('utf-8-sig', errors='replace'))
    errors = [i for i, row in enumerate(rows) if row.level in ('error', 'critical')]
    if not errors:
        return None
    # A clean shutdown after the last error is not a crash indication.
    if any(SHUTDOWN in row.text.lower() for row in rows[errors[-1] + 1:]):
        return None
    return raw, rows[errors[-1]].text, offset > 0


def session_suspects(manager, raw):
    """Ranked MODs the session's errors point at; empty when unknown."""
    if manager is None:
        return []
    try:
        mods = [mod.info for mod in manager.scan() if mod.enabled]
    except (OSError, ValueError):
        return []
    rows = iter_rows(raw.decode('utf-8-sig', errors='replace'))
    return [suspect.as_dict() for suspect in find_suspects(rows, mods)]


def clean_exit(session, folders):
    """True only when this launch wrote a fresh log that ends with a normal shutdown."""
    candidates = {Path(path) for path in session['logs']}
    candidates.update(Path(folder) / 'log.html' for folder in folders)
    for path in candidates:
        try:
            current = fingerprint(path)
            if (not current or current == session['logs'].get(str(path))
                    or current['mtime'] / 1e9 < session['started'] - 2):
                continue
            with path.open('rb') as stream:
                stream.seek(max(0, current['size'] - 64 * 1024))
                tail = stream.read().decode('utf-8-sig', errors='replace')
        except OSError:
            continue
        rows = iter_rows(tail)
        if rows and any(SHUTDOWN in row.text.lower() for row in rows[-20:]):
            return True
    return False


class ReportStore:
    def __init__(self, root):
        self.root = Path(root)

    def records(self):
        records = []
        for path in self.root.glob('*/record.json'):
            try:
                item = json.loads(path.read_text(encoding='utf-8'))
                if item.get('id') == path.parent.name and item.get('schema') == 1:
                    records.append(item)
            except (OSError, ValueError, AttributeError):
                continue
        return sorted(records, key=lambda item: item['created'], reverse=True)

    def folder(self, identity):
        if len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
            raise ValueError('无效报告编号')
        return self.root / identity

    def save(self, item):
        atomic_write_json(self.folder(item['id']) / 'record.json', item)

    def get(self, identity):
        return json.loads((self.folder(identity) / 'record.json').read_text(encoding='utf-8'))

    def delete(self, identity):
        folder = self.folder(identity)
        # Only remove files owned by this feature, never an arbitrary tree.
        for name in ('record.json', 'record.tmp', 'log.html'):
            (folder / name).unlink(missing_ok=True)
        for stale in folder.glob('.bbmod-*.tmp'):
            stale.unlink(missing_ok=True)
        folder.rmdir()

    def capture(self, ctx, session, folders, automatic=False):
        candidates = {Path(path) for path in session['logs']}
        candidates.update(Path(folder) / 'log.html' for folder in folders)
        fresh = []
        for path in candidates:
            try:
                result = read_session_log(path, session)
                if result:
                    fresh.append((path.stat().st_mtime_ns, path, result))
            except OSError:
                continue
        if not fresh:
            return None
        records = self.records()
        while len(records) >= MAX_RECORDS:
            removable = next((item for item in reversed(records) if item['state'] == 'sent'), None)
            if removable is None:
                raise OSError('已保留 20 份报告，请在错误报告列表中删除不再需要的记录。')
            self.delete(removable['id'])
            records.remove(removable)
        _, source, (raw, error, partial) = max(fresh, key=lambda entry: entry[0])
        identity = uuid.uuid4().hex
        folder = self.folder(identity)
        folder.mkdir(parents=True)
        (folder / 'log.html').write_bytes(raw)
        context = SimpleNamespace(game=ctx.game, mm=ctx.mm, log_dir=lambda: folder)
        from .support_report import redact
        suspects = session_suspects(ctx.mm, raw)
        for suspect in suspects:
            suspect['reasons'] = [redact(reason) for reason in suspect['reasons']]
        prefix = ('疑似异常退出：本次启动产生错误日志，退出后未找到正常关闭记录。\n'
                  '仅凭日志不能确定闪退原因；请结合复现步骤排查。\n'
                  f'本地记录编号：{identity}\n'
                  '日志快照：本次启动的新记录，最多保留末尾 2 MB。\n\n'
                  + describe(suspects) + '\n\n')
        body = prefix + build_report(context, None)
        body = body.replace(str(source.parent), '[日志目录]')
        item = {'schema': 1, 'id': identity, 'created': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'state': 'pending' if automatic else 'manual', 'automatic': automatic,
                'partial_log': partial, 'suspects': suspects, 'attempts': 0, 'next_retry': 0, 'ticket': None, 'posted': False,
                'message': '日志已保存在本机，等待提交。',
                'payload': {'kind': 'bug', 'title': '疑似游戏闪退：' + redact(error)[:80],
                            'details': '从 BBMOD 启动后检测到疑似异常退出。\n请结合附带日志排查。',
                            'version': 'BBMOD desktop ' + VERSION, 'nickname': '', 'contact': '',
                            'diagnostic_report': body[:MAX_REPORT_CHARS]}}
        self.save(item)
        return item
