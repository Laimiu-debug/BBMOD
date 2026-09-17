import uuid
from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

CATEGORIES = [(x, x) for x in ['基础功能', '战斗与平衡', '起源与事件', '装备与外观', '汉化', '框架', '其他']]
IMPACTS = [('unknown', '尚未确认'), ('no', '作者声明无影响'), ('yes', '有影响，请阅读说明')]


class AuthorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='author_profile')
    must_change_password = models.BooleanField(default=True)


class Mod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    install_name = models.CharField('安装文件名', max_length=100, unique=True)
    title = models.CharField('作品名称', max_length=100)
    summary = models.CharField('一句话介绍', max_length=240)
    description = models.TextField('详细说明', max_length=20000)
    category = models.CharField('分类', max_length=20, choices=CATEGORIES, default='基础功能')
    source_url = models.URLField('原作或源码链接', blank=True)
    license = models.CharField('分发许可', max_length=200)
    game_version = models.CharField('适用游戏版本', max_length=80, default='1.5.2.3')
    dlc = models.CharField('所需 DLC', max_length=300, blank=True)
    mod_ids = models.TextField('游戏内 MOD ID', max_length=2000, blank=True)
    requires = models.TextField('前置 MOD ID', max_length=2000, blank=True)
    conflicts = models.TextField('冲突 MOD ID', max_length=2000, blank=True)
    save_impact = models.CharField('存档影响', choices=IMPACTS, default='unknown', max_length=10)
    seed_impact = models.CharField('种子影响', choices=IMPACTS, default='unknown', max_length=10)
    compatibility_notes = models.TextField('兼容与安装说明', max_length=5000, blank=True)
    blocked = models.BooleanField(default=False)
    block_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(Lower('install_name'), name='unique_install_name_casefold')]

    def snapshot(self):
        fields = ['title', 'summary', 'description', 'category', 'source_url', 'license', 'game_version', 'dlc',
                  'save_impact', 'seed_impact', 'compatibility_notes']
        result = {f: getattr(self, f) for f in fields}
        result.update({f: [x.strip() for x in getattr(self, f).splitlines() if x.strip()] for f in ['mod_ids', 'requires', 'conflicts']})
        result['author'] = self.owner.first_name or self.owner.username
        return result


class Release(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mod = models.ForeignKey(Mod, on_delete=models.PROTECT, related_name='releases')
    version = models.CharField('版本号', max_length=40)
    notes = models.TextField('更新说明', max_length=10000)
    metadata = models.JSONField(default=dict)
    archive = models.FileField(upload_to='archives/')
    cover = models.FileField(upload_to='covers/', blank=True)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveBigIntegerField()
    inspection = models.JSONField(default=dict)
    status = models.CharField(max_length=15, choices=[('draft', '未公开'), ('published', '已公开'), ('withdrawn', '已撤回')], default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['mod', 'version'], name='unique_mod_version')]


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=200)
    detail = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LoginAttempt(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    failures = models.PositiveIntegerField(default=0)
    since = models.DateTimeField()
