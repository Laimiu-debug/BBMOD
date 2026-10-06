"""Streaming hashes and durable replace-on-write helpers for local state files."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile


def file_sha256(path) -> str:
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_write_bytes(path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix='.bbmod-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def atomic_write_json(path, value) -> None:
    atomic_write_bytes(path, json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8'))
