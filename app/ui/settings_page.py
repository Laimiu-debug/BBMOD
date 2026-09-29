"""Desktop font preferences with draft preview and explicit, immediate apply."""
from copy import deepcopy

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFontComboBox, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from core.appearance import Appearance, MAX_SIZE, MIN_SIZE, SETTINGS_KEY
from .theme import apply_theme, css_family, resolve_appearance, style_button


class SettingsPage(QWidget):
    applied = Signal()
    crash_reports_requested = Signal()
    crash_upload_changed = Signal()

    def __init__(self, settings, updates=None):
        super().__init__()
        self.setObjectName('settingsPage')
        self.settings = settings
        self.saved = resolve_appearance(settings.get(SETTINGS_KEY))
        root = QVBoxLayout(self)
        web_box = QGroupBox('官网联动')
        web_layout = QVBoxLayout(web_box)
        enable_web = QPushButton('启用「用 BBMOD 打开」')
        enable_web.clicked.connect(self.enable_web_links)
        web_layout.addWidget(enable_web)
        self.web_status = QLabel('启用后，官网作品会在本软件中打开安装预览，网页种子可导入本地收藏。移动 EXE 后需重新启用。')
        self.web_status.setWordWrap(True)
        web_layout.addWidget(self.web_status)
        root.addWidget(web_box)
        crash_box = QGroupBox('游戏错误报告')
        crash_layout = QVBoxLayout(crash_box)
        from core.crash_reports import AUTO_UPLOAD_KEY
        self.auto_crash_upload = QCheckBox('自动上传疑似闪退报告')
        self.auto_crash_upload.setObjectName('autoCrashUpload')
        self.auto_crash_upload.setChecked(settings.get(AUTO_UPLOAD_KEY, False) is True)
        self.auto_crash_upload.toggled.connect(self._save_crash_upload)
        crash_layout.addWidget(self.auto_crash_upload)
        self.crash_hint = QLabel('默认关闭。从 BBMOD 启动并保持管理器运行，检测到疑似异常退出时保存日志。'
                                '开启后会自动将脱敏日志、MOD 清单及版本发送到官网，仅管理员可见，不上传存档。'
                                '断网保留报告，最多尝试 3 次；关闭后停止后续自动提交，已发送的请求无法撤回。')
        self.crash_hint.setWordWrap(True)
        crash_layout.addWidget(self.crash_hint)
        self.crash_reports_button = QPushButton('查看已保存的错误报告…')
        self.crash_reports_button.clicked.connect(self.crash_reports_requested.emit)
        crash_layout.addWidget(self.crash_reports_button)
        root.addWidget(crash_box)
        if updates is not None:
            from .update_card import UpdateCard
            self.updates = UpdateCard(updates)
            root.addWidget(self.updates)
        box = QGroupBox('界面文字')
        content = QVBoxLayout(box)
        scope = QLabel('调整 BBMOD 管理器的字体和字号。点击应用后立即生效，下次打开仍会保留。')
        scope.setWordWrap(True)
        content.addWidget(scope)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.family = QFontComboBox()
        self.family.setObjectName('interface_font_family')
        self.family.setWritingSystem(QFontDatabase.SimplifiedChinese)
        self.family.setFontFilters(QFontComboBox.ScalableFonts)
        self.family.setEditable(False)
        self.family.setMaxVisibleItems(12)
        self.family.setMinimumContentsLength(20)
        self.family.setSizeAdjustPolicy(QFontComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.family.setAccessibleName('界面字体')
        self.family.setToolTip('选择本机可用的中文字体；包含软件自带的 Noto Sans SC。')
        form.addRow('字体', self.family)
        self.size = QSpinBox()
        self.size.setObjectName('interface_font_size')
        self.size.setRange(MIN_SIZE, MAX_SIZE)
        self.size.setSuffix(' 号')
        self.size.setAccessibleName('界面字号')
        self.size.setToolTip('推荐 12–14 号；大字号下可滚动查看较长的页面。')
        form.addRow('字号', self.size)
        content.addLayout(form)
        hint = QLabel('默认 12 号，比旧版更大。这里仅调整软件界面，游戏内字体由汉化包提供。')
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        content.addWidget(hint)
        root.addWidget(box)

        preview_box = QGroupBox('字体预览')
        preview_layout = QVBoxLayout(preview_box)
        self.preview = QFrame()
        self.preview.setObjectName('fontPreview')
        sample = QVBoxLayout(self.preview)
        sample.setContentsMargins(18, 16, 18, 16)
        self.sample_heading = QLabel('为下一场战役做好准备')
        self.sample_body = QLabel('佣兵兄弟已整备完毕，准备出发。\n中文 English · ABCDEFG123 · 红武器伤害 75%')
        for label in (self.sample_heading, self.sample_body):
            label.setWordWrap(True)
            sample.addWidget(label)
        preview_layout.addWidget(self.preview)
        root.addWidget(preview_box)
        actions = QHBoxLayout()
        self.reset_button = QPushButton('恢复推荐')
        self.reset_button.setObjectName('font_reset')
        self.reset_button.clicked.connect(lambda: self._load(resolve_appearance(None)))
        actions.addWidget(self.reset_button)
        actions.addStretch()
        self.apply_button = QPushButton('应用字体')
        self.apply_button.setObjectName('font_apply')
        style_button(self.apply_button, 'check', primary=True)
        self.apply_button.clicked.connect(self.apply)
        actions.addWidget(self.apply_button)
        root.addLayout(actions)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setObjectName('workspaceHint')
        root.addWidget(self.status)
        root.addStretch()
        self.family.currentFontChanged.connect(self._preview)
        self.size.valueChanged.connect(self._preview)
        self._load(self.saved)

    def enable_web_links(self):
        from core.web_links import register_protocol
        try:
            register_protocol()
        except (OSError, ValueError) as exc:
            self.web_status.setText(str(exc))
        else:
            self.web_status.setText('已启用。可以在官网点击「用 BBMOD 打开」。')

    def _save_crash_upload(self, enabled):
        from core.crash_reports import AUTO_UPLOAD_KEY
        previous = self.settings.get(AUTO_UPLOAD_KEY, False)
        try:
            self.settings.set(AUTO_UPLOAD_KEY, enabled)
        except OSError as exc:
            self.settings.data[AUTO_UPLOAD_KEY] = previous
            with QSignalBlocker(self.auto_crash_upload):
                self.auto_crash_upload.setChecked(previous is True)
            self.crash_hint.setText('设置未保存：' + str(exc))
            return
        self.crash_upload_changed.emit()

    def _load(self, preferences):
        with QSignalBlocker(self.family), QSignalBlocker(self.size):
            self.family.setCurrentFont(QFont(preferences.font_family))
            self.size.setValue(preferences.font_size)
        self._preview()

    def draft(self):
        return Appearance(self.family.currentFont().family(), self.size.value())

    def _preview(self, *_):
        draft = self.draft()
        base = f'font-family:{css_family(draft.font_family)}; font-size:{draft.font_size}pt;'
        self.sample_body.setStyleSheet(base)
        self.sample_heading.setStyleSheet(base + ' font-weight:bold;')
        self.apply_button.setEnabled(draft != self.saved)
        self.status.setText('预览中，点击「应用字体」保存。' if draft != self.saved else
                            f'当前已应用：{self.saved.font_family} · {self.saved.font_size} 号')

    def apply(self):
        draft = self.draft()
        existed = SETTINGS_KEY in self.settings.data
        previous = deepcopy(self.settings.get(SETTINGS_KEY))
        try:
            self.settings.set(SETTINGS_KEY, draft.to_dict())
        except OSError as error:
            if existed:
                self.settings.data[SETTINGS_KEY] = previous
            else:
                self.settings.data.pop(SETTINGS_KEY, None)
            self.status.setText(f'字体未应用，无法保存设置：{error}')
            return
        self.saved = apply_theme(QApplication.instance(), draft)
        self._load(self.saved)
        self.status.setText(f'已保存并应用：{self.saved.font_family} · {self.saved.font_size} 号，无需重启。')
        self.applied.emit()
