"""Validate an immutable, locally staged snapshot before atomic activation."""
import hashlib
import json
from pathlib import Path
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from catalog.wiki_store import SNAPSHOT_PATTERN, ASSET_PATTERN


class Command(BaseCommand):
    help = '验证百科快照与图片哈希，原子切换当前资料版本；保留上一版以便回退。'

    def add_arguments(self, parser):
        parser.add_argument('snapshot')
        parser.add_argument('--check-only',action='store_true')

    def handle(self,*args,**options):
        edition=options['snapshot']
        if not SNAPSHOT_PATTERN.fullmatch(edition):raise CommandError('资料版本格式无效。')
        root=Path(settings.WIKI_ROOT);release=root/'releases'/edition
        try:
            manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
            if manifest.get('snapshot')!=edition or not manifest.get('complete_source'):
                raise ValueError('不是完整快照')
            if set(manifest['files'])!={'wiki.sqlite3','styles.css','report.json'}:
                raise ValueError('快照文件清单无效')
            for name,digest in manifest['files'].items():
                if hashlib.sha256((release/name).read_bytes()).hexdigest()!=digest:raise ValueError('快照文件校验失败：'+name)
            for name in manifest['assets']:
                if not ASSET_PATTERN.fullmatch(name):raise ValueError('图片路径无效')
                if hashlib.sha256((root/'assets'/name).read_bytes()).hexdigest()!=name.split('.')[0]:raise ValueError('图片校验失败')
            with sqlite3.connect((release/'wiki.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('数据库完整性校验失败')
                report=json.loads(db.execute("SELECT value FROM metadata WHERE key='report'").fetchone()[0])
                if report['snapshot']!=edition or report.get('missing_pages'):raise ValueError('来源记录不完整')
                if report.get('missing_images') or report.get('media_errors'):raise ValueError('图片获取未完成')
        except (OSError,ValueError,KeyError,sqlite3.Error) as exc:
            raise CommandError(str(exc)) from exc
        if not options['check_only']:
            previous=root/'current.json'
            if previous.exists():(root/'previous.json').write_bytes(previous.read_bytes())
            staged=root/'current.json.part'
            staged.write_text(json.dumps({'snapshot':edition}),encoding='utf-8')
            staged.replace(previous)
        self.stdout.write(('已验证：' if options['check_only'] else '已启用：')+edition)
