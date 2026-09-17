"""Import a verified existing desktop release without rebuilding or running it."""
from pathlib import Path
from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from catalog.desktop import create_desktop_release
from catalog.forms import DesktopReleaseForm
from catalog.models import DesktopRelease


class Command(BaseCommand):
    help = '从服务器已有文件导入管理器版本，适合大文件或自动发布脚本。'

    def add_arguments(self, parser):
        parser.add_argument('file', type=Path)
        parser.add_argument('--release-version', required=True)
        parser.add_argument('--admin', required=True)
        parser.add_argument('--notes', type=Path, required=True)
        parser.add_argument('--sha256', required=True)
        parser.add_argument('--publish', action='store_true')

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['admin'], is_superuser=True, is_active=True)
            with options['file'].open('rb') as stream:
                form = DesktopReleaseForm({'version': options['release_version'], 'notes': options['notes'].read_text(encoding='utf-8'),
                                           'publish': options['publish']}, {'file': File(stream, name=options['file'].name)})
                if not form.is_valid():
                    raise CommandError(str(form.errors.as_text()))
                if form.inspection['sha256'] != options['sha256'].lower():
                    raise CommandError('文件 SHA-256 与指定值不符，未导入。')
                existing = DesktopRelease.objects.filter(version=form.cleaned_data['version']).first()
                if existing:
                    if existing.sha256 != form.inspection['sha256']:
                        raise CommandError('同一版本已存在不同文件，不能覆盖。')
                    self.stdout.write(f'已存在相同版本，未修改：{existing.version}')
                    return
                release = create_desktop_release(user, form)
        except (User.DoesNotExist, OSError) as exc:
            raise CommandError('请检查管理员账号、程序文件和更新说明路径。') from exc
        self.stdout.write(f'已导入 {release.filename}：{release.get_status_display()}')
