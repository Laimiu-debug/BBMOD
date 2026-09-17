"""Creates only isolated browser-QA accounts. Refuses production and populated databases."""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from catalog.models import AuthorProfile


class Command(BaseCommand):
    help = '在空的本地预览数据库创建测试账号；严禁用于服务器部署。'
    def handle(self, *args, **kwargs):
        if not settings.DEBUG or 'preview' not in str(settings.DATA_DIR).lower() or User.objects.exists():
            raise CommandError('仅允许 DEBUG=1、路径包含 preview 的空数据库。')
        User.objects.create_superuser('preview_admin', password='Preview-Admin-9834')
        author = User.objects.create_user('preview_author', password='Preview-Author-9834', first_name='离线测试作者')
        AuthorProfile.objects.create(user=author)
        self.stdout.write('已创建隔离测试账号；不会创建或公开 MOD。')
