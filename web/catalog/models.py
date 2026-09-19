import uuid
from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from .storage import DesktopStorage

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
    original_author = models.CharField('原作者署名', max_length=200, blank=True)
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
        result['uploader'] = self.owner.first_name or self.owner.username
        result['original_author'] = self.original_author
        result['author'] = self.original_author or result['uploader']
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


class DesktopRelease(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.CharField('版本号', max_length=40, unique=True)
    notes = models.TextField('更新说明', max_length=10000)
    file = models.FileField('Windows 程序', storage=DesktopStorage(), upload_to='releases/')
    sha256 = models.CharField(max_length=64)
    size = models.PositiveBigIntegerField()
    prerelease = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=[('draft', '未公开'), ('published', '已公开'), ('withdrawn', '已撤回')], default='draft')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def filename(self):
        return f'BBMOD-{self.version}.exe'

    @property
    def channel_label(self):
        return '测试版' if self.prerelease else '稳定版'


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


class SharedSeed(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fingerprint = models.CharField(max_length=64, unique=True)
    seed = models.CharField(max_length=10, db_index=True)
    origin = models.CharField(max_length=50, db_index=True)
    game_version = models.CharField(max_length=30, blank=True)
    combat_difficulty = models.SmallIntegerField(null=True, blank=True)
    economic_difficulty = models.SmallIntegerField(null=True, blank=True)
    budget_difficulty = models.SmallIntegerField(null=True, blank=True)
    record = models.JSONField()
    note = models.CharField(max_length=1000, blank=True)
    ports = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    named = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    melee = models.SmallIntegerField(null=True, blank=True, db_index=True)
    blocked = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']


class SharedSeedBrother(models.Model):
    seed = models.ForeignKey(SharedSeed, on_delete=models.CASCADE, related_name='brothers')
    melee = models.SmallIntegerField(null=True)
    ranged = models.SmallIntegerField(null=True)
    defense = models.SmallIntegerField(null=True)
    # Delimiters make membership exact, including on SQLite.
    traits = models.CharField(max_length=2000, blank=True)


class SeedUploadBudget(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    since = models.DateTimeField(auto_now_add=True, db_index=True)


class SiteVisitor(models.Model):
    """A first-party browser identifier, not a person, IP or device fingerprint."""
    token_hash = models.CharField(max_length=64, unique=True)
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(db_index=True)
    page_views = models.PositiveBigIntegerField(default=1)


class Suggestion(models.Model):
    class Kind(models.TextChoices):
        FEATURE = 'feature', '功能建议'
        BUG = 'bug', '问题反馈'
        OTHER = 'other', '其他想法'

    class Status(models.TextChoices):
        NEW = 'new', '待查看'
        REVIEWING = 'reviewing', '处理中'
        DONE = 'done', '已完成'
        CLOSED = 'closed', '暂不采纳'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField('建议类型', max_length=15, choices=Kind.choices)
    title = models.CharField('一句话概括', max_length=100)
    details = models.TextField('详细说明', max_length=5000)
    version = models.CharField('相关版本', max_length=60, blank=True)
    nickname = models.CharField('怎么称呼你', max_length=40, blank=True)
    contact = models.CharField('联系方式', max_length=150, blank=True)
    status = models.CharField('处理状态', max_length=15, choices=Status.choices, default=Status.NEW, db_index=True)
    internal_notes = models.TextField('内部备注', max_length=5000, blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    @property
    def reference(self):
        return self.id.hex[:12].upper()


class SuggestionBudget(models.Model):
    # Short-lived keyed hashes only; never persist the visitor's IP address.
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    since = models.DateTimeField(auto_now_add=True, db_index=True)
