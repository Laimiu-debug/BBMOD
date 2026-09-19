"""Equipment workspace and a non-activating, click-through game overlay."""
from html import escape
import time

from PySide6.QtCore import Qt, QTimer, QSize, QPoint, QRect
from PySide6.QtGui import QCursor, QGuiApplication, QPainter, QPixmap, QColor, QPen, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QFrame, QKeySequenceEdit, QSlider, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from core.paths import resource_path
from core.game import find_log_write_paths
from core.item_inspector import HoverLog, HoverSession, appraise, catalog
from core.inspector_mod import change, FILENAME, VERSION as READER_VERSION, installed_version
from .global_hotkey import DEFAULT, GlobalHotkey
from .game_foreground import GameForeground
from .equipment_catalog import EquipmentCatalog
from .workers import Worker
from .theme import style_button


def result_html(result, compact=False):
    css = '<style>body{color:#e8d9b6;} h2{color:#e6b079;margin:6px 0;} p{margin:8px 0;} .muted{color:#c7b38e;} th{color:#c7b38e;font-weight:normal;} .value{font-size:125%;font-weight:bold;color:#fff0c6;}</style>'
    if not result:
        crest = resource_path('assets/crest-painted.png').as_uri()
        return css + ('<p align="center"><img src="' + crest + '" width="56" height="56"></p>'
            '<h2 align="center">装备鉴定</h2><p align="center">等待一件值得传颂的装备</p><hr>'
            '<p>把鼠标移到游戏中的装备图标，查看这件红装的属性与原版随机范围。</p>'
            '<p class="muted">已经停留在图标上时，移出后再移入即可。</p>')
    text = css + ('' if compact else '<p align="center" class="muted">◆　装 备 鉴 定　◆</p>') + '<h2 align="center">' + escape(result['title']) + '</h2>'
    if result.get('english'):
        text += '<p align="center" class="muted">' + escape(result['english']) + '</p>'
        text += '<p align="center">' + escape(result.get('instance', '')) + '</p>'
    text += '<hr>'
    if result['rows']:
        text += '<table width="100%" cellspacing="0" cellpadding="7"><tr><th align="left" width="43%">装备属性 / 本件</th><th align="left">原版红装范围</th></tr>'
        for row in result['rows']:
            if compact and row['state'] in ('未抽中', '可能未抽中'):
                continue
            score = row['score']
            quality = f'区间位置 {score}%' if score is not None else row['state']
            meter = ''
            if score is not None:
                score = max(0, min(100, score))
                cells = (f'<td width="{score}%" bgcolor="#a59962" style="font-size:2px;">&nbsp;</td>' if score else '')
                cells += (f'<td width="{100-score}%" bgcolor="#4d4233" style="font-size:2px;">&nbsp;</td>' if score < 100 else '')
                meter = '<table width="100%" height="5" cellspacing="0" cellpadding="0"><tr>' + cells + '</tr></table>'
            text += ('<tr><td>' + escape(row['label']) + '<br><span class="value">' + escape(row['value']) + '</span></td><td>'
                     + escape(row['range']) + '<br><span class="muted">' + escape(quality) + '</span>' + meter + '</td></tr>')
        text += '</table>'
    if compact:
        unchanged = [row['label'] for row in result['rows'] if row['state'] in ('未抽中', '可能未抽中')]
        if unchanged:
            text += f'<p class="muted">另有 {len(unchanged)} 项属性未强化 · 完整明细见装备鉴定</p>'
        brief = ('按原版 1.5.2.3 对照，区间位置并非实战评分。' if result.get('valid') else result['message'])
        if result.get('valid') and '附件' in result['message']: brief += ' 已还原护甲附件之前的数值。'
        return text + '<hr><p class="muted">' + escape(brief) + '</p>'
    return text + '<hr><p>' + escape(result['message']) + '</p><p class="muted">原版 1.5.2.3 · 不含角色技能加成<br>区间位置表示随机数值高低，不代表爆率或交易价格。</p>'


class EquipmentSheet(QWidget):
    """Dark inventory leather with a restrained iron edge, shared by both views."""
    def __init__(self, parent=None, flags=Qt.Widget):
        super().__init__(parent, flags)
        self.background_opacity = 1.0
        self.leather = QPixmap(str(resource_path('assets/game-ui/dialog_panel_01.png')))
        self.setObjectName('equipmentSheet')
        self.setStyleSheet('#equipmentSheet{background:transparent;} '
            '#equipmentSheet QTextBrowser {background:transparent;color:#e8d9b6;border:none;padding:0;} '
            '#equipmentSheet QLabel {background:transparent;color:#c7b38e;}')

    def sizeHint(self):
        return QSize(820, 540)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(self.background_opacity)
        painter.fillRect(self.rect(), QColor('#211c16'))
        painter.drawPixmap(self.rect().adjusted(5, 5, -5, -5), self.leather)
        painter.setPen(QPen(QColor('#777064'), 2)); painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        painter.setPen(QPen(QColor('#171714'), 1)); painter.drawRect(self.rect().adjusted(4, 4, -5, -5))
        for x in (9, self.width() - 10):
            for y in (9, self.height() - 10):
                painter.setBrush(QColor('#84745b')); painter.setPen(QColor('#28241f')); painter.drawEllipse(x-2, y-2, 4, 4)
        painter.end()


class InspectorOverlay(EquipmentSheet):
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                         Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(self.styleSheet() + '#equipmentSheet QTextBrowser{font-size:10pt;} #equipmentSheet QLabel{font-size:9pt;}')
        root = QVBoxLayout(self); root.setContentsMargins(16, 16, 16, 16)
        self.age = QLabel('等待悬停'); root.addWidget(self.age)
        self.content = QTextBrowser(); self.content.setOpenExternalLinks(False); root.addWidget(self.content)
        self.hint = QLabel(); self.hint.setWordWrap(True); root.addWidget(self.hint)
        self.content.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.age.setText('当前悬停装备')
        self.age.hide()
        self._plans_key = None
        self._plans = []

    def follow_cursor(self, avoid):
        point = QCursor.pos()
        screen = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
        rect = screen.availableGeometry().adjusted(8, 8, -8, -8)
        key = (rect.getRect(), avoid.getRect(), self.content.font().toString())
        if key != self._plans_key:
            self._plans_key, self._plans = key, []
            for region in tooltip_regions(rect, avoid):
                width = min(360, region.width())
                if width < 260: continue
                self.content.document().setTextWidth(width - 36)
                height = int(self.content.document().size().height()) + 72
                if height <= region.height(): self._plans.append((region, QSize(width, height)))
        choices = []
        for region, size in self._plans:
            position = tooltip_position(point, size, region)
            panel = QRect(position, size)
            # Prefer the closest free side, keeping the cursor itself exposed.
            dx = max(panel.left() - point.x(), 0, point.x() - panel.right())
            dy = max(panel.top() - point.y(), 0, point.y() - panel.bottom())
            if not panel.contains(point): choices.append((dx*dx + dy*dy, panel))
        if not choices:
            self.hide()
            return False
        panel = min(choices, key=lambda choice: choice[0])[1]
        self.content.document().setTextWidth(panel.width() - 36)
        self.setGeometry(panel)
        self.show()
        return True

    def present(self, result, shortcut, avoid):
        self.content.setHtml(result_html(result, compact=True))
        self._plans_key = None
        self.hint.setText(shortcut + ' 暂停提示 · 移开鼠标自动收起')
        return self.follow_cursor(avoid)


def tooltip_position(point, size, bounds):
    x, y = point.x() + 24, point.y() + 20
    if x + size.width() > bounds.right() + 1: x = point.x() - size.width() - 24
    if y + size.height() > bounds.bottom() + 1: y = point.y() - size.height() - 20
    return QPoint(max(bounds.left(), min(x, bounds.right() - size.width() + 1)),
                  max(bounds.top(), min(y, bounds.bottom() - size.height() + 1)))


def tooltip_regions(bounds, avoid):
    """Free sides of the actual native tooltip, including a 10 px safety gap."""
    blocked = avoid.adjusted(-10, -10, 10, 10).intersected(bounds)
    if blocked.isEmpty(): return [bounds]
    return [region for region in (
        QRect(blocked.right() + 1, bounds.top(), bounds.right() - blocked.right(), bounds.height()),
        QRect(bounds.left(), bounds.top(), blocked.left() - bounds.left(), bounds.height()),
        QRect(bounds.left(), blocked.bottom() + 1, bounds.width(), bounds.bottom() - blocked.bottom()),
        QRect(bounds.left(), bounds.top(), bounds.width(), blocked.top() - bounds.top())
    ) if not region.isEmpty()]


class InspectorPage(QWidget):
    def __init__(self, ctx, *, register_hotkey=True):
        super().__init__()
        self.ctx = ctx
        self.items = catalog()
        self.latest = None
        self.latest_identifier = None
        self.received_at = 0
        self.hover = HoverSession()
        self.active_reader = None
        self.presented = None
        self.foreground = GameForeground()
        self.tooltip_rect = self.foreground.map_bounds
        self._worker = None
        self.readers = [HoverLog(folder / 'log.html') for folder in find_log_write_paths()]
        self.overlay = InspectorOverlay()
        self.hotkey = GlobalHotkey(self)
        self.hotkey.activated.connect(self.toggle_overlay)
        prefs = ctx.settings.get('item_inspector', {})
        self.preferences = dict(prefs) if isinstance(prefs, dict) else {}
        workspace = QVBoxLayout(self)
        self.sections = QTabWidget()
        self.catalog_page = EquipmentCatalog()
        self.sections.addTab(self.catalog_page, '装备表格')
        appraisal = QWidget()
        appraisal.setObjectName('equipmentAppraisal')
        appraisal.setStyleSheet('#equipmentAppraisal QLabel#workspaceHint { color:#625033; }')
        scroll = QScrollArea(); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True); scroll.setWidget(appraisal)
        self.sections.addTab(scroll, '装备鉴定')
        self.catalog_page.appraisal_requested.connect(lambda: self.sections.setCurrentIndex(1))
        workspace.addWidget(self.sections)
        root = QVBoxLayout(appraisal)
        intro = QLabel('让 BBMOD 在后台运行，鼠标悬停红装即可查看随机范围，移开自动收起。快捷键用于暂停 / 恢复提示；此页保留上次结果。')
        intro.setWordWrap(True); intro.setObjectName('workspaceHint'); root.addWidget(intro)
        setup = QGroupBox('开始鉴定'); layout = QVBoxLayout(setup)
        steps = QLabel('1. 退出游戏，安装或更新读取 MOD。\n2. 启动游戏，使用窗口化或无边框窗口。\n3. 鼠标移入红装图标，提示跟随鼠标显示。')
        steps.setWordWrap(True); layout.addWidget(steps)
        buttons = QHBoxLayout()
        self.install = QPushButton('安装 / 修复读取 MOD'); self.install.clicked.connect(lambda: self.change_mod(False))
        self.remove = QPushButton('移除读取 MOD'); self.remove.clicked.connect(lambda: self.change_mod(True))
        buttons.addWidget(self.install); buttons.addWidget(self.remove); layout.addLayout(buttons)
        self.mod_status = QLabel(); self.mod_status.setWordWrap(True); layout.addWidget(self.mod_status)
        self.enabled = QCheckBox('悬停红装时自动显示')
        self.enabled.setChecked(self.preferences.get('enabled', True) is not False)
        layout.addWidget(self.enabled)
        key = self.preferences.get('shortcut', DEFAULT)
        self.shortcut = QKeySequenceEdit(QKeySequence(key if isinstance(key, str) else DEFAULT))
        self.shortcut.setMaximumSequenceLength(1)
        self.shortcut.setToolTip('点击后按下需要的组合，例如 Ctrl+Shift+Q 或 F8；点击应用后生效。')
        self.apply_key = QPushButton('应用快捷键'); self.apply_key.clicked.connect(self.apply_hotkey)
        row = QHBoxLayout(); row.addWidget(QLabel('暂停 / 恢复')); row.addWidget(self.shortcut, 1); row.addWidget(self.apply_key)
        self.open_button = QPushButton(); self.open_button.clicked.connect(self.toggle_overlay)
        layout.addLayout(row)
        self.key_status = QLabel(); self.key_status.setWordWrap(True); layout.addWidget(self.key_status)
        self.opacity = QSlider(Qt.Horizontal); self.opacity.setRange(50, 100)
        value = self.preferences.get('opacity', 90)
        self.opacity.setValue(value if type(value) is int else 90)
        self.opacity_label = QLabel()
        opacity_row = QHBoxLayout(); opacity_row.addWidget(self.opacity_label); opacity_row.addWidget(self.opacity, 1)
        layout.addLayout(opacity_row)
        self.opacity.valueChanged.connect(self.apply_opacity)
        self.apply_opacity(save=False)
        self.setup_toggle = QPushButton('读取 MOD 与快捷键设置'); self.setup_toggle.setCheckable(True)
        style_button(self.setup_toggle, 'settings')
        toolbar = QHBoxLayout(); toolbar.addWidget(self.setup_toggle, 1); toolbar.addWidget(self.open_button)
        root.addLayout(toolbar)
        root.addWidget(setup)
        self.setup_toggle.toggled.connect(setup.setVisible)
        self.setup_toggle.setChecked(True)
        style_button(self.open_button, 'shield', primary=True)
        note = QLabel('读取 MOD 只记录你悬停查看的装备数值，不创建装备、不修改存档。独占全屏请改为无边框或窗口化；未知 MOD 装备只显示识别结果。')
        note.setWordWrap(True); note.setObjectName('workspaceHint'); root.addWidget(note)
        latest_row = QHBoxLayout()
        self.age = QLabel('尚未读取装备'); self.age.setObjectName('workspaceHint'); latest_row.addWidget(self.age, 1)
        self.browse_button = QPushButton('在装备表格中查看'); self.browse_button.setEnabled(False)
        self.browse_button.clicked.connect(self.browse_latest)
        latest_row.addWidget(self.browse_button); root.addLayout(latest_row)
        self.result = QTextBrowser(); self.result.setOpenExternalLinks(False)
        sheet = EquipmentSheet(); sheet.setMaximumWidth(820); sheet_layout = QVBoxLayout(sheet)
        sheet_layout.setContentsMargins(28, 24, 28, 24)
        self.result.setMinimumHeight(360); self.result.setHtml(result_html(None)); sheet_layout.addWidget(self.result)
        root.addWidget(sheet, 1, Qt.AlignHCenter)
        if ctx.game and installed_version(ctx.game.data_dir / FILENAME) >= READER_VERSION: self.setup_toggle.setChecked(False)
        self.enabled.toggled.connect(self.apply_enabled)
        self.apply_enabled(save=False)
        if register_hotkey: self.apply_hotkey(save=False)
        self.timer = QTimer(self); self.timer.setInterval(80); self.timer.timeout.connect(self.poll); self.timer.start()
        self.follow_timer = QTimer(self); self.follow_timer.setInterval(33)
        self.follow_timer.timeout.connect(self.sync_overlay); self.follow_timer.start()
        ctx.game_changed.connect(self.refresh_mod)
        ctx.management_changed.connect(self.refresh_controls)
        ctx.session_changed.connect(self.refresh_controls)
        ctx.data_changed.connect(self.refresh_mod)
        self.refresh_mod()

    def apply_hotkey(self, *_args, save=True):
        try:
            self.hotkey.set_shortcut(self.shortcut.keySequence().toString(QKeySequence.PortableText))
            self.key_status.setText(self.hotkey.current + ' · 暂停 / 恢复自动悬停提示')
            if save:
                self.preferences['shortcut'] = self.hotkey.current
                self.save_preferences()
            self.presented = None
        except (ValueError, OSError) as error:
            self.key_status.setText(str(error) + (' 当前仍使用 ' + self.hotkey.current if self.hotkey.current else ' 自动悬停仍可使用。'))

    def save_preferences(self):
        try: self.ctx.settings.set('item_inspector', dict(self.preferences))
        except OSError: self.key_status.setText('本次设置已生效，但保存失败；重启后需重新设置。')

    def apply_enabled(self, *_args, save=True):
        self.open_button.setText('暂停悬停提示' if self.enabled.isChecked() else '开启悬停提示')
        if not self.enabled.isChecked(): self.overlay.hide(); self.presented = None
        if save:
            self.preferences['enabled'] = self.enabled.isChecked()
            self.save_preferences()

    def apply_opacity(self, *_args, save=True):
        value = self.opacity.value()
        self.overlay.background_opacity = value / 100
        self.overlay.update()
        self.opacity_label.setText(f'背景不透明度 {value}%')
        if save:
            self.preferences['opacity'] = value
            self.save_preferences()

    def refresh_controls(self, *_):
        busy = self.ctx.management_busy or self.ctx.seedgen_active or bool(self._worker and self._worker.isRunning())
        self.install.setEnabled(not busy and self.ctx.game is not None)
        self.remove.setEnabled(not busy and self.ctx.game is not None)

    def refresh_mod(self):
        path = self.ctx.game.data_dir / FILENAME if self.ctx.game else None
        version = installed_version(path) if path else 0
        self.mod_status.setText(f'读取 MOD v{version} 已安装，支持自动悬停。安装后需重启游戏。' if version >= READER_VERSION else
                                f'读取 MOD v{version} 需要更新：旧版可能漏读装备属性。退出游戏后点击安装 / 修复，再重新启动游戏。' if version else
                                '请先安装读取 MOD；仅安装在当前选择的游戏目录。')
        self.refresh_controls()

    def change_mod(self, remove):
        if not self.ctx.game or self.ctx.management_busy or self.ctx.seedgen_active:
            return
        self.ctx.set_management_busy(True)
        game = self.ctx.game
        worker = Worker(lambda: change(game, remove=remove))
        worker.setParent(self); self._worker = worker
        worker.done.connect(self._mod_done)
        worker.failed.connect(self.mod_status.setText)
        worker.finished.connect(self._mod_finished)
        worker.finished.connect(worker.deleteLater)
        self.mod_status.setText('正在处理读取 MOD…'); worker.start()

    def _mod_done(self, message):
        self.ctx.data_changed.emit()
        self.mod_status.setText(message)

    def _mod_finished(self):
        self._worker = None
        self.ctx.set_management_busy(False)

    def toggle_overlay(self):
        self.enabled.setChecked(not self.enabled.isChecked())

    def browse_latest(self):
        if self.latest_identifier and self.catalog_page.show_item(self.latest_identifier):
            self.sections.setCurrentIndex(0)

    def sync_overlay(self):
        event = self.hover.current(time.monotonic())
        if (not event or not self.enabled.isChecked() or self.ctx.seedgen_active
                or not self.foreground(self.ctx.game)):
            self.overlay.hide(); self.presented = None
            return
        avoid = self.tooltip_rect(self.hover.bounds)
        if avoid is None:
            self.overlay.hide(); self.presented = None
            return
        if self.presented != event['seq']:
            try: result = appraise(event, self.items)
            except ValueError:
                self.overlay.hide(); self.presented = None; return
            self.overlay.present(result, self.hotkey.current or '页面按钮', avoid)
            self.presented = event['seq']
        else:
            self.overlay.follow_cursor(avoid)

    def poll(self):
        if self.ctx.seedgen_active:
            self.overlay.hide(); self.hover.reset(); self.presented = None
        for reader in self.readers:
            generation = reader.generation
            events = reader.poll()
            if reader.generation != generation and reader is self.active_reader:
                self.hover.reset(); self.overlay.hide(); self.presented = None
                self.latest = None; self.received_at = 0; self.latest_identifier = None
                self.browse_button.setEnabled(False)
                self.result.setHtml(result_html(None))
                self.overlay.content.setHtml(result_html(None))
                self.age.setText('游戏日志已更新，等待新的悬停信息')
                self.overlay.age.setText('等待新的悬停信息')
            for event in events:
                try:
                    if reader is not self.active_reader:
                        self.hover.reset(); self.active_reader = reader
                    self.hover.accept(event, time.monotonic())
                    if event.get('kind') == 'hover': continue
                    first_reading = self.latest is None
                    self.latest = appraise(event, self.items)
                    self.latest_identifier = event['id']
                    self.browse_button.setEnabled(self.latest['supported'])
                    if first_reading: self.setup_toggle.setChecked(False)
                    self.received_at = time.monotonic()
                    html = result_html(self.latest)
                    self.result.setHtml(html)
                except ValueError as error:
                    self.hover.reset(); self.overlay.hide(); self.presented = None
                    self.latest = None; self.latest_identifier = None; self.received_at = 0
                    self.browse_button.setEnabled(False)
                    self.result.setHtml(result_html({'title': event.get('name', '装备读取失败'),
                        'rows': [], 'message': str(error)}))
                    self.age.setText(str(error))
        if self.received_at:
            seconds = int(time.monotonic() - self.received_at)
            text = '最近一次悬停 · ' + ('刚刚' if seconds < 2 else f'{seconds} 秒前')
            self.age.setText(text)
        self.sync_overlay()

    def shutdown(self):
        self.timer.stop(); self.follow_timer.stop(); self.hotkey.shutdown(); self.overlay.close()
