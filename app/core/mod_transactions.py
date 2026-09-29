"""Journaled changes to installed MOD files, with verified recovery after failure."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid


def digest(path):
    if not path.exists():
        return None
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.bbmod-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class ModTransaction:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.directory = self.root / 'bbmod_disabled' / 'operations'
        self.journal = self.directory / 'pending.json'

    def target(self, relative):
        path = self.root / relative
        parent = path.parent.resolve()
        allowed = {self.root / 'data', self.root / 'bbmod_disabled'}
        metadata = path in {self.root / 'bbmod_disabled' / name for name in ('online-catalog.json', 'profiles.json')}
        if path == self.root / 'bbmod_localizations' / 'profiles.json':
            metadata = True
            allowed.add(self.root / 'bbmod_localizations')
        if (parent not in allowed or path.is_symlink() or path.resolve().parent != parent
                or (not metadata and path.suffix.lower() not in {'.zip', '.rar'})):
            raise ValueError('MOD 操作路径无效。')
        return path

    def apply(self, changes, *, keep_backups=False):
        if self.journal.exists():
            raise ValueError('上次 MOD 操作尚未恢复，请先点击「恢复上次操作」。')
        if self.directory.resolve() != self.directory:
            raise ValueError('MOD 恢复目录不能是符号链接。')
        self.directory.mkdir(parents=True, exist_ok=True)
        transaction = uuid.uuid4().hex
        staging = self.directory / transaction
        staging.mkdir()
        entries = []
        committed = False
        try:
            for index, (destination, source) in enumerate(changes.items()):
                relative = str(Path(destination).relative_to(self.root))
                target = self.target(relative)
                before = digest(target)
                backup = staging / f'{index}.before'
                if before is not None:
                    shutil.copyfile(target, backup)
                    if digest(backup) != before:
                        raise OSError('备份校验失败，未修改 MOD。')
                after = None
                if source is not None:
                    staged = staging / f'{index}.after'
                    shutil.copyfile(source, staged)
                    after = digest(staged)
                entries.append({'path': relative, 'before': before, 'after': after})
            record = {'transaction': transaction, 'entries': entries}
            atomic_json(self.journal, record)
            if keep_backups:
                atomic_json(staging / 'completed.json', record)
            for index, entry in enumerate(entries):
                target = self.target(entry['path'])
                if digest(target) != entry['before']:
                    raise OSError('MOD 文件已被其他程序更改，已停止操作。')
                if entry['after'] is None:
                    target.unlink(missing_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(staging / f'{index}.after', target)
            self.journal.unlink()
            committed = True
            return staging if keep_backups else None
        except Exception:
            if self.journal.exists():
                self.recover()
            raise
        finally:
            if not self.journal.exists() and not (committed and keep_backups):
                shutil.rmtree(staging)

    def recover(self):
        if not self.journal.exists():
            return
        if self.directory.resolve() != self.directory or self.journal.is_symlink():
            raise ValueError('MOD 恢复目录不能是符号链接。')
        record = json.loads(self.journal.read_text(encoding='utf-8'))
        if not isinstance(record, dict) or not isinstance(record.get('entries'), list):
            raise ValueError('MOD 恢复记录损坏，请保留备份。')
        transaction = record.get('transaction', '')
        if not isinstance(transaction, str) or len(transaction) != 32 or any(c not in '0123456789abcdef' for c in transaction):
            raise ValueError('MOD 恢复记录损坏，请保留备份。')
        staging = self.directory / transaction
        if staging.resolve() != staging:
            raise ValueError('MOD 备份目录无效。')
        entries = record['entries']
        # Validate every file before restoring any of them.
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or not {'path', 'before', 'after'} <= entry.keys():
                raise ValueError('MOD 恢复记录不完整，请保留备份。')
            if (staging / f'{index}.before').is_symlink():
                raise ValueError('MOD 恢复备份不能是符号链接。')
            current = digest(self.target(entry['path']))
            if current not in (entry['before'], entry['after']):
                raise OSError('文件已被外部修改，已保留当前文件和恢复备份。')
            if entry['before'] is not None and digest(staging / f'{index}.before') != entry['before']:
                raise OSError('恢复备份校验失败。')
        for index, entry in enumerate(entries):
            target = self.target(entry['path'])
            if digest(target) == entry['before']:
                continue
            if entry['before'] is None:
                target.unlink(missing_ok=True)
            else:
                staged = staging / f'{index}.restore'
                shutil.copyfile(staging / f'{index}.before', staged)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, target)
        self.journal.unlink()
        # Manual recovery retains the verified backups for inspection.
