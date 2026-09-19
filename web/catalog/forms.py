import io
import re
import warnings
import uuid
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from PIL import Image
from app.core.archive_safety import inspect_archive, valid_install_name
from .models import Mod, Release
from .desktop import inspect_desktop, version_key


class ModForm(forms.ModelForm):
    class Meta:
        model = Mod
        fields = ['title', 'summary', 'category', 'description', 'install_name', 'license', 'source_url', 'original_author',
                  'game_version', 'dlc', 'mod_ids', 'requires', 'conflicts', 'save_impact', 'seed_impact', 'compatibility_notes']
        widgets = {k: forms.Textarea(attrs={'rows': 3}) for k in ['description', 'mod_ids', 'requires', 'conflicts', 'compatibility_notes']}
        help_texts = {
            'install_name': '英文、数字、下划线或短横线，以 .zip 结尾。保留需要的加载顺序前缀，创建后不可更改。',
            'license': '例如：原创，允许在本站分发；或填写所采用的开源许可证。',
            'original_author': '转载作品填写原作者，含译者或改作者时一并署名；发布账号会另列为整理发布者。原创作品可留空。',
            'mod_ids': '填写脚本注册的 MOD ID，每行一个；纯资源包可留空。',
            'requires': '每行一个前置 MOD ID，例如 mod_hooks。版本要求请补充到兼容说明。',
            'conflicts': '每行一个冲突 MOD ID。',
            'dlc': '无要求可留空；多个 DLC 用逗号分隔。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields['install_name'].disabled = True

    def clean_install_name(self):
        name = self.cleaned_data['install_name']
        if not valid_install_name(name):
            raise forms.ValidationError('请输入有效 ZIP 文件名，不能使用 data_ 或 bbmod_ 保留前缀。')
        if Mod.objects.filter(install_name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('这个安装文件名已被另一作品使用。')
        return name

    def clean_source_url(self):
        value = self.cleaned_data['source_url']
        if value and not value.lower().startswith(('https://', 'http://')):
            raise forms.ValidationError('仅支持 http 或 https 链接。')
        return value

    def clean(self):
        values = super().clean()
        if values.get('original_author') and not values.get('source_url'):
            self.add_error('source_url', '请为原作者署名补充可核实的原作链接。')
        for name in ['mod_ids', 'requires', 'conflicts']:
            lines = [s.strip() for s in values.get(name, '').splitlines() if s.strip()]
            if len(lines) > 30 or any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', s) for s in lines):
                self.add_error(name, '最多 30 个 ID，只能使用英文、数字、下划线、点和短横线。')
            else:
                values[name] = '\n'.join(dict.fromkeys(lines))
        return values


class ReleaseForm(forms.ModelForm):
    archive = forms.FileField(label='MOD 文件', help_text='上传可直接放入游戏 data 目录的单个 ZIP；最大 100 MB。', widget=forms.ClearableFileInput(attrs={'accept': '.zip'}))
    cover = forms.FileField(label='展示图片', required=False, help_text='可选，PNG、JPEG 或 WebP，最大 5 MB。', widget=forms.ClearableFileInput(attrs={'accept': '.png,.jpg,.jpeg,.webp'}))
    rights = forms.BooleanField(label='这是我制作的作品，或我已取得在本站分发此版本的授权')
    publish = forms.BooleanField(label='上传成功后立即公开', required=False, initial=True)

    class Meta:
        model = Release
        fields = ['version', 'notes', 'archive', 'cover']
        widgets = {'notes': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notes'].required = False

    def clean_notes(self):
        return self.cleaned_data.get('notes') or '本次上传未填写补充更新说明。'

    def clean_version(self):
        value = self.cleaned_data['version']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,39}', value):
            raise forms.ValidationError('版本号使用英文、数字、点或短横线，例如 1.0.0。')
        return value

    def clean_archive(self):
        upload = self.cleaned_data['archive']
        if not upload.name.lower().endswith('.zip'):
            raise forms.ValidationError('请上传 ZIP 文件。')
        try:
            self.inspection = inspect_archive(upload, max_bytes=settings.MAX_MOD_BYTES)
        except (ValueError, OSError) as exc:
            raise forms.ValidationError(str(exc)) from exc
        return upload

    def clean_cover(self):
        upload = self.cleaned_data.get('cover')
        if not upload:
            return None
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError('图片不能超过 5 MB。')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(upload) as img:
                    if img.format not in {'PNG', 'JPEG', 'WEBP'} or img.width * img.height > 16_000_000:
                        raise ValueError('图片格式或尺寸不支持。')
                    img.load()
                    img = img.convert('RGB')
                    img.thumbnail((1600, 1000))
                    buf = io.BytesIO()
                    img.save(buf, 'WEBP', quality=85)
                    return ContentFile(buf.getvalue(), name='cover.webp')
        except Exception as exc:
            raise forms.ValidationError('无法读取图片，请使用不超过 1600 万像素的 PNG、JPEG 或 WebP。') from exc


class QuickModForm(ModForm):
    """Create a work and its first version on one page."""
    def __init__(self, *args, upload_name='', **kwargs):
        data = kwargs.get('data')
        if data is not None:
            data = data.copy()
            if not data.get('title'):
                data['title'] = re.sub(r'[_.]+', ' ', upload_name.rsplit('.', 1)[0])[:100].strip()
            if not data.get('install_name'):
                if valid_install_name(upload_name):
                    data['install_name'] = upload_name
                else:
                    stem = re.sub(r'[^A-Za-z0-9_.-]+', '_', upload_name.rsplit('.', 1)[0]).strip('_.-')
                    proposed = (stem[:90] + '.zip') if stem else ''
                    data['install_name'] = proposed if valid_install_name(proposed) else f'mod_{uuid.uuid4().hex[:12]}.zip'
            for key, default in {'category': '基础功能', 'game_version': '1.5.2.3',
                                 'save_impact': 'unknown', 'seed_impact': 'unknown'}.items():
                if not data.get(key):
                    data[key] = default
            kwargs['data'] = data
        super().__init__(*args, **kwargs)
        self.fields['summary'].label = '介绍'
        self.fields['summary'].widget = forms.Textarea(attrs={'rows': 3, 'placeholder': '它有什么作用？玩家需要知道什么？'})
        for key in ['description', 'license', 'install_name']:
            self.fields[key].required = False

    def clean(self):
        values = super().clean()
        values['description'] = values.get('description') or values.get('summary', '')
        values['license'] = values.get('license') or '上传者确认具备本站分发授权，其他用途请联系作者。'
        return values

    def advanced_fields(self):
        return [self[name] for name in ['description', 'install_name', 'license', 'source_url', 'original_author',
            'game_version', 'dlc', 'mod_ids', 'requires', 'conflicts', 'save_impact', 'seed_impact', 'compatibility_notes']]

    def advanced_errors(self):
        return any(field.errors for field in self.advanced_fields())


class DesktopReleaseForm(forms.Form):
    file = forms.FileField(label='Windows 程序', widget=forms.ClearableFileInput(attrs={'accept': '.exe'}))
    version = forms.CharField(label='版本号', max_length=40, help_text='例如 0.3.0 或 0.3.0-rc.5；rc、beta 等后缀会标为测试版。')
    notes = forms.CharField(label='更新说明', max_length=10000, widget=forms.Textarea(attrs={'rows': 4, 'placeholder': '这次更新了什么？有哪些已知问题？'}))
    publish = forms.BooleanField(label='上传成功后立即公开', required=False, initial=True)

    def clean_version(self):
        value = self.cleaned_data['version'].removeprefix('v')
        try:
            version_key(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return value

    def clean_file(self):
        upload = self.cleaned_data['file']
        self.inspection = inspect_desktop(upload)
        return upload

    def clean(self):
        values = super().clean()
        upload, version = values.get('file'), values.get('version')
        if upload and version:
            match = re.fullmatch(r'BBMOD-(.+)\.exe', upload.name, flags=re.IGNORECASE)
            if match and match.group(1) != version:
                self.add_error('version', '版本号与 EXE 文件名不一致，请核对后上传。')
        return values


class CreateAuthorForm(UserCreationForm):
    first_name = forms.CharField(label='作者显示名称', max_length=100)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = '使用 3 至 40 个小写英文、数字或下划线。'
        self.fields['username'].widget.attrs.update(minlength=3, maxlength=40)

    def clean_username(self):
        name = self.cleaned_data['username'].lower()
        if not re.fullmatch(r'[a-z0-9_]{3,40}', name):
            raise forms.ValidationError('账号使用 3 至 40 个小写英文、数字或下划线。')
        if User.objects.filter(username__iexact=name).exists():
            raise forms.ValidationError('此账号已存在。')
        return name
