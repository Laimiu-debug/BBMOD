"""Consistent SQLite snapshot plus immutable uploaded files; no credentials in stdout."""
import json
import sqlite3
import tarfile
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from catalog.models import Release


class Command(BaseCommand):
    help = '备份数据库和全部版本文件，输出至持久卷 backups 目录。'
    def handle(self, *args, **kwargs):
        destination = settings.DATA_DIR / 'backups'
        destination.mkdir(exist_ok=True)
        archive_path = destination / f'bbmod-hub-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.tar.gz'
        with tempfile.TemporaryDirectory() as temp:
            snapshot = Path(temp) / 'db.sqlite3'
            with closing(sqlite3.connect(settings.DATABASES['default']['NAME'])) as source, closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
                rows = target.execute('SELECT archive, cover FROM catalog_release').fetchall()
            try:
                with tarfile.open(archive_path, 'x:gz') as out:
                    out.add(snapshot, arcname='db.sqlite3')
                    for paths in rows:
                        for name in paths:
                            if name:
                                path = Path(settings.MEDIA_ROOT) / name
                                if not path.is_file() or not path.resolve().is_relative_to(Path(settings.MEDIA_ROOT).resolve()):
                                    raise CommandError('备份缺少上传文件或路径无效。')
                                out.add(path, arcname='private/' + name)
            except Exception:
                archive_path.unlink(missing_ok=True)
                raise
        self.stdout.write(str(archive_path))
