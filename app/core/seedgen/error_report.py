"""Capture one search session's failure before its live log can be replaced."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re

from ..gamelog import iter_rows
from ..support_report import redact
from .log_watcher import RE_SCRIPT_ERROR_TEXT

MAX_LOG_BYTES = 2 * 1024 * 1024
_SESSION = re.compile(rb'BBMODSeedSession:\s*([A-Za-z0-9_.:-]+)')
_SESSION_LE = re.compile('BBMODSeedSession:'.encode('utf-16-le')
                         + rb'(?:\s\x00)*((?:[A-Za-z0-9_.:-]\x00)+)')
_SESSION_BE = re.compile('BBMODSeedSession:'.encode('utf-16-be')
                         + rb'(?:\x00\s)*((?:\x00[A-Za-z0-9_.:-])+)')
_START_ERROR = re.compile(r'BBMODSeedStart:\s*error\b', re.I)
_SECRET_KEY = re.compile(
    r'password|passwd|token|secret|api[_-]?key|authorization|cookie|private[_-]?key', re.I)


def _decode(raw, encoding=''):
    encoding = encoding or ('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    return raw.decode(encoding, errors='replace')


def _markers(raw, encoding):
    pattern = {'utf-16-le': _SESSION_LE, 'utf-16-be': _SESSION_BE}.get(encoding, _SESSION)
    return list(pattern.finditer(raw))


def _owned_slice(raw, session_id, encoding):
    markers = _markers(raw, encoding)
    if not markers:
        return raw, False
    matching = [i for i, marker in enumerate(markers)
                if marker[1].decode(encoding) == session_id]
    if not matching:
        return None, False
    index = matching[-1]
    row_prefix = '<div class="row'.encode(encoding)
    newline = '\n'.encode(encoding)
    start = raw.rfind(row_prefix, 0, markers[index].start())
    if start < 0:
        preceding = raw.rfind(newline, 0, markers[index].start())
        start = preceding + len(newline) if preceding >= 0 else 0
    end = len(raw)
    if index + 1 < len(markers):
        next_start = markers[index + 1].start()
        end = raw.rfind(row_prefix, start, next_start)
        if end < start:
            preceding = raw.rfind(newline, start, next_start)
            end = preceding + len(newline) if preceding >= 0 else next_start
    return raw[start:end], start > 0 or end < len(raw)


def _fresh_log(path, baseline, session_id):
    old = baseline.get('logs', {}).get(str(path))
    with path.open('rb') as stream:
        stat = os.fstat(stream.fileno())
        length = min(stat.st_size, 4096)
        head = stream.read(length)
        encoding = ('utf-16-le' if head.startswith(b'\xff\xfe') else
                    'utf-16-be' if head.startswith(b'\xfe\xff') else 'utf-8')
        prefix = hashlib.sha256(head).hexdigest()
        current = {'size': stat.st_size, 'mtime': stat.st_mtime_ns,
                   'prefix': prefix, 'length': length}
        if current == old or stat.st_mtime < baseline.get('started', 0) - 2:
            return None, False, '日志未在本次启动后更新', encoding
        offset = 0
        if old and old['size'] and stat.st_size >= old['size']:
            stream.seek(0)
            if hashlib.sha256(stream.read(old['length'])).hexdigest() == old['prefix']:
                offset = old['size']
        stream.seek(offset)
        ownership_head = stream.read(min(64 * 1024, stat.st_size - offset))
        offset = max(offset, stat.st_size - MAX_LOG_BYTES)
        if encoding.startswith('utf-16'):
            offset += offset % 2
        stream.seek(offset)
        raw = stream.read(min(MAX_LOG_BYTES, stat.st_size - offset))
    if not raw:
        return None, False, '没有本次启动的新日志内容', encoding
    if not _markers(raw, encoding):
        owners = _markers(ownership_head, encoding)
        if owners and owners[-1][1].decode(encoding) != session_id:
            return None, False, '日志标记属于其他刷种子会话', encoding
    owned, sliced = _owned_slice(raw, session_id, encoding)
    if owned is None:
        return None, False, '日志标记属于其他刷种子会话', encoding
    if str(path) not in baseline.get('logs', {}) and not _markers(owned + ownership_head, encoding):
        return None, False, '启动时未登记该日志，且未找到匹配的会话标记', encoding
    return owned, offset > 0 or sliced, '', encoding


def _failure(raw, name, encoding):
    text = _decode(raw, encoding)
    if name.lower().endswith(('.html', '.htm')):
        errors = [row.text.strip() for row in iter_rows(text)
                  if row.level == 'critical'
                  or (row.level == 'error' and row.tag.strip().upper() in {'SQ', 'SCRIPT ERROR'})
                  or re.match(r'BBMODSeedStart:\s*error\b', row.text.strip())]
    else:
        errors = [line.strip() for line in text.splitlines()
                  if RE_SCRIPT_ERROR_TEXT.search(line) or _START_ERROR.search(line)]
    return errors[-1] if errors else ''


def snapshot_seed_failure(*, session_id, paths, baseline, metadata, error=''):
    """Return immutable bytes/metadata for a fresh failure, or None on clean stop.

    ``paths`` is ordered with the active log first. An explicit failure still
    produces a report when no readable session log exists. Shutdown rows do not
    cancel a search error that occurred while the game process was still alive.
    """
    reasons = []
    for path in dict.fromkeys(Path(value) for value in paths):
        try:
            raw, partial, reason, encoding = _fresh_log(path, baseline, str(session_id))
        except OSError as exc:
            raw, partial, reason = None, False, f'日志无法读取（{type(exc).__name__}）'
        if raw is None:
            reasons.append(f'{path.name}：{reason}')
            continue
        detected = _failure(raw, path.name, encoding)
        if error or detected:
            return {
                'session_id': str(session_id), 'error': str(error or detected),
                'metadata': deepcopy(metadata), 'raw': raw, 'partial_log': partial,
                'log_name': path.name, 'log_error': '', 'log_encoding': encoding,
                'captured_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            }
    if not error:
        return None
    return {
        'session_id': str(session_id), 'error': str(error),
        'metadata': deepcopy(metadata), 'raw': b'', 'partial_log': False,
        'log_name': '', 'log_encoding': 'utf-8',
        'log_error': '; '.join(reasons)[:1800] or '没有可用的游戏日志路径',
        'captured_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }


def redact_seed_text(text):
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----',
                  '[私钥已隐藏]', str(text), flags=re.S)
    text = re.sub(r'\bBearer\s+[^\s<>"\']+', 'Bearer [已隐藏]', text, flags=re.I)
    text = re.sub(
        r'''(?ix)(\b(?:password|passwd|token|access_token|refresh_token|secret|api[_-]?key|authorization|cookie)\b["']?\s*[:=]\s*)(?:"[^"\n]*"|'[^'\n]*'|[^\s,;<>]+)''',
        r'\1[已隐藏]', text)
    return redact(text)


def safe_metadata(value):
    if isinstance(value, dict):
        return {redact_seed_text(key): '[已隐藏]' if _SECRET_KEY.search(str(key))
                else safe_metadata(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_metadata(item) for item in value]
    if isinstance(value, str):
        # Bound each untrusted field before running regex redaction or JSON encoding.
        value = value if len(value) <= 4000 else value[:4000] + '[后续已省略]'
        return redact_seed_text(value)
    return value


class _Stacks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.active = 0
        self.parts = []
        self.length = 0
        self.stacks = []

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            self.depth += 1
            if 'stacktrace-container' in (dict(attrs).get('class') or '').split():
                self.active = self.depth
                self.parts, self.length = [], 0
        if self.active and tag in ('br', 'tr', 'td', 'div'):
            self.handle_data('\n')

    def handle_data(self, text):
        if self.active and self.length < 8000:
            self.parts.append(text[:8000 - self.length])
            self.length += len(self.parts[-1])

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.active == self.depth:
                self.stacks.append(''.join(self.parts).strip())
                self.stacks = self.stacks[-8:]
                self.active = 0
            self.depth = max(0, self.depth - 1)


def seed_diagnostic(snapshot, identity):
    metadata = safe_metadata(snapshot.get('metadata', {}))
    text = _decode(snapshot.get('raw', b''), snapshot.get('log_encoding', ''))
    rows = iter_rows(text) if snapshot.get('log_name', '').endswith(('.html', '.htm')) else []
    lines = [str(row) for row in rows] if rows else text.splitlines()
    errors = [i for i, line in enumerate(lines)
              if RE_SCRIPT_ERROR_TEXT.search(line) or _START_ERROR.search(line)][-12:]
    indexes = set(range(max(0, len(lines) - 40), len(lines)))
    for index in errors:
        indexes.update(range(max(0, index - 3), min(len(lines), index + 12)))
    context = '\n'.join(lines[index][:2000] for index in sorted(indexes))[:24000]
    stacks = _Stacks()
    stacks.feed(text)
    if stacks.active and stacks.parts:
        stacks.stacks.append(''.join(stacks.parts).strip())
    progress = metadata.get('progress', {})
    if not isinstance(progress, dict):
        progress = {}
    loop = progress.get('loop_idx', metadata.get('loop_idx', '未知'))
    hits = progress.get('hits', metadata.get('hits', '未知'))
    elapsed = metadata.get('elapsed_seconds', '未知')
    startup = json.dumps(metadata.get('startup', {}), ensure_ascii=False)[:2000]
    body = (
        f'种子搜索错误\n本地记录编号：{identity}\n会话：{snapshot["session_id"]}\n'
        f'错误：{str(snapshot.get("error", ""))[:4000]}\n'
        f'快照时间（UTC）：{snapshot.get("captured_at", "")}\n'
        f'搜索轮次：{loop}\n命中数量：{hits}\n运行时长：{elapsed} 秒\n启动状态：{startup}\n'
        '配置、搜索轮次、时长与本次运行环境：\n'
        + json.dumps(metadata, ensure_ascii=False, indent=2)[:16000]
        + '\n\n日志快照：最多保留本次会话末尾 2 MB。'
        + ('已截取部分日志。' if snapshot.get('partial_log') else '')
        + '\n' + snapshot.get('log_error', '')
        + '\n日志上下文：\n' + context
        + '\n\nSquirrel 调用堆栈：\n' + '\n\n'.join(stacks.stacks)[-14000:]
    )
    version = str(snapshot.get('metadata', {}).get('game_version', ''))
    trusted_version = f'游戏版本：{version}\n' if re.fullmatch(r'(?:\d{1,3}\.){2,3}\d{1,3}', version) else ''
    return trusted_version + redact_seed_text(body), metadata
