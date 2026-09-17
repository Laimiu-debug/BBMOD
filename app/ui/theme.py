"""Shared parchment, iron and heraldry styling for BBMOD."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt, QRect
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPalette, QPixmap, QLinearGradient
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QPushButton, QTableWidget, QWidget, QStyleOption, QStyle
import random

from core.paths import resource_path

INK, MUTED, RED, GREEN, GOLD = "#382f23", "#74644c", "#923e32", "#3e6549", "#d7ba7a"
_ICONS = {
 "camp": '<path d="m3 25 13-21 13 21ZM16 4v21m-7 0 7-12 7 12M5 28h22"/>',
 "shield": '<path d="M16 3c4 3 8 4 12 4l-2 13c-2 5-6 8-10 10C12 28 8 25 6 20L4 7c4 0 8-1 12-4Z"/><path d="m10 11 12 12m0-12L10 23"/>',
 "book": '<path d="M16 8c-4-3-8-4-13-3v21c5-1 9 0 13 3 4-3 8-4 13-3V5c-5-1-9 0-13 3Zm0 0v21M7 11l5 1m-5 5 5 1m8-6 5-1m-5 7 5-1"/>',
 "compass": '<circle cx="16" cy="16" r="12"/><path d="m21 10-3 9-8 3 3-9ZM16 1v4m15 11h-4M16 31v-4M1 16h4"/>',
 "refresh": '<path d="M26 13A11 11 0 0 0 7 7l-3 4m0-8v8h8m-6 8a11 11 0 0 0 19 6l3-4m0 8v-8h-8"/>',
 "folder": '<path d="M3 9V5h10l4 4h12v17H3Zm0 4h26"/>',
 "download": '<path d="M16 3v17m-6-6 6 6 6-6M5 22v6h22v-6"/>',
 "play": '<path d="m10 5 17 11-17 11Z"/>',
 "stop": '<rect x="7" y="7" width="18" height="18" rx="1"/>',
 "check": '<path d="m5 17 7 7L28 7"/>',
 "close": '<path d="m8 8 16 16m0-16L8 24"/>',
 "save": '<path d="M5 3h19l5 5v21H3V3Zm4 0v9h14V3M9 29V18h14v11"/>',
 "warning": '<path d="m16 3 14 25H2Zm0 8v8m0 4v1"/>',
 "copy": '<path d="M11 9h17v20H11ZM5 23H3V3h18v2"/>',
}


def crest() -> QIcon:
    return QIcon(str(resource_path("assets/crest-painted.png")))


def icon(name: str, color: str = INK, size: int = 24) -> QIcon:
    body = _ICONS.get(name, _ICONS["shield"])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
    <defs><linearGradient id="metal" x2="0.3" y2="1"><stop stop-color="#ddc99b"/><stop offset=".42" stop-color="#ac9060"/><stop offset=".55" stop-color="#695439"/><stop offset="1" stop-color="#c0a570"/></linearGradient></defs>
    <circle cx="20" cy="21" r="18" fill="#211b15"/>
    <circle cx="20" cy="19" r="17" fill="url(#metal)" stroke="#443523" stroke-width="1.5"/>
    <circle cx="20" cy="19" r="14" fill="#453d30" stroke="#d5bc85" stroke-width=".7"/>
    <g transform="translate(7 6) scale(.81)" fill="none" stroke="#e3d0a3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>'''
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    pix.setDevicePixelRatio(2)
    return QIcon(pix)


def style_button(button: QPushButton, glyph: str, primary: bool = False) -> None:
    button.setIcon(icon(glyph, "#f6e6c5" if primary else INK))
    button.setCursor(Qt.PointingHandCursor)
    if primary:
        button.setProperty("primary", True)


def style_table(table: QTableWidget) -> None:
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(38)
    table.horizontalHeader().setMinimumSectionSize(64)


class ParchmentSurface(QWidget):
    """Cached, uneven grain on the dark timber surrounding the paper panels."""
    def __init__(self) -> None:
        super().__init__()
        self.grain = QPixmap(160, 160)
        self.grain.fill(Qt.transparent)
        painter = QPainter(self.grain)
        randomizer = random.Random(365360)
        for _ in range(260):
            x, y = randomizer.randrange(160), randomizer.randrange(160)
            painter.setPen(QColor(190, 158, 111, randomizer.randrange(3, 17)))
            painter.drawLine(x, y, x + randomizer.randrange(4, 65), y)
        painter.end()

    def paintEvent(self, event) -> None:
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)
        painter.drawTiledPixmap(self.rect(), self.grain)
        for x in range(0, self.width(), 76):
            painter.setPen(QColor(10, 8, 6, 55))
            painter.drawLine(x, 0, x, self.height())
            painter.setPen(QColor(180, 140, 85, 18))
            painter.drawLine(x + 2, 0, x + 2, self.height())
        painter.end()


class CampHeader(QWidget):
    """Painted camp vignette with a dark title area and riveted brass frame."""
    def __init__(self):
        super().__init__()
        self.setObjectName("campHeader")
        self.setFixedHeight(108)
        self.art = QPixmap(str(resource_path("assets/camp-painted.png")))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#28241e"))
        if not self.art.isNull():
            scene = self.art.scaledToHeight(self.height() + 22, Qt.SmoothTransformation)
            painter.drawPixmap(self.width() - scene.width(), -10, scene)
        shade = QLinearGradient(self.width() - (self.height() + 22) * 3, 0,
                                self.width() - self.height() * 1.3, 0)
        shade.setColorAt(0, QColor("#28241e"))
        shade.setColorAt(.45, QColor(40, 36, 30, 100))
        shade.setColorAt(1, QColor(40, 36, 30, 10))
        painter.fillRect(self.rect(), shade)
        painter.setPen(QColor("#0f100d"))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.setPen(QColor("#9e8053"))
        painter.drawRect(self.rect().adjusted(2, 2, -3, -3))
        painter.setPen(QColor("#504332"))
        painter.drawRect(self.rect().adjusted(5, 5, -6, -6))
        for x in (8, self.width() - 9):
            for y in (8, self.height() - 9):
                painter.setPen(QColor("#211b14"))
                painter.setBrush(QColor("#b89a61"))
                painter.drawEllipse(x - 2, y - 2, 5, 5)
        painter.end()


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    font_id = QFontDatabase.addApplicationFont(str(resource_path("localization/NotoSansSC-Regular.ttf")))
    families = QFontDatabase.applicationFontFamilies(font_id)
    family = families[0] if families else "Microsoft YaHei UI"
    title_id = QFontDatabase.addApplicationFont(str(resource_path("assets/Cinzel.ttf")))
    title_families = QFontDatabase.applicationFontFamilies(title_id)
    title_family = title_families[0] if title_families else family
    app.setFont(QFont(family, 10))
    app.setWindowIcon(crest())
    pal = QPalette()
    for role, color in {
        QPalette.Window: "#e7d8b9", QPalette.WindowText: INK,
        QPalette.Base: "#f4e9d2", QPalette.AlternateBase: "#eadebf",
        QPalette.Text: INK, QPalette.Button: "#dac8a4", QPalette.ButtonText: INK,
        QPalette.Highlight: "#825c38", QPalette.HighlightedText: "#fff4dc",
        QPalette.ToolTipBase: "#302b24", QPalette.ToolTipText: "#f3e2bd",
        QPalette.PlaceholderText: "#8a795e",
    }.items():
        pal.setColor(role, QColor(color))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor("#9b8b70"))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#9b8b70"))
    app.setPalette(pal)
    app.setStyleSheet(STYLESHEET.replace('"Microsoft YaHei UI"', f'"{family}"')
        .replace('font-family:Georgia', f'font-family:"{title_family}"')
        .replace('__ASSETS__', resource_path('assets').as_posix()))


STYLESHEET = """
QWidget { color:#382f23; font-family:"Microsoft YaHei UI"; font-size:13px; }
QMainWindow, #windowRoot { background:#23251f; }
QLabel { background:transparent; }
#sidebar { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #30332a,stop:1 #191d18); border-right:2px solid #827048; }
#sidebar QLabel { color:#d6c39c; }
#brandName { font-family:Georgia; font-size:32px; font-weight:bold; color:#edd7a5; }
#brandSubtitle { font-size:13px; color:#b49f75; }
#sidebarFooter { color:#a89a7a; font-size:11px; }
#navButton { text-align:left; padding:15px 14px; border:1px solid transparent; border-left:3px solid transparent; background:transparent; color:#c8bd9f; font-size:14px; }
#navButton:hover { background:#383c2f; color:#f6e8c8; border-color:#615a40; }
#navButton:checked { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6f382e,stop:1 #402c25); border:1px solid #976743; border-left:3px solid #d2b678; color:#ffedc9; font-weight:bold; }
#workspace { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #d8c59f,stop:1 #b9a47d); }
#pageHeading { font-size:25px; font-weight:bold; color:#312c22; }
#pageEyebrow { font-family:Georgia; font-size:11px; color:#79623e; }
#pageSubtitle, #muted { color:#756347; font-size:12px; }
#gameBar { background:#c0ac85; border-top:1px solid #ad986f; border-bottom:1px solid #a08a62; }
#gamePath { background:transparent; border:none; color:#51452f; font-size:11px; padding:0; }
#versionBadge { background:#514c36; color:#f4dfad; padding:5px 12px; border:1px solid #80734c; border-radius:2px; font-size:11px; }
#mainFooter { color:#746044; font-size:11px; }
QGroupBox { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #eadcc0,stop:1 #e3d2b0); border:1px solid #aa9368; border-radius:3px; margin-top:16px; padding:20px 13px 12px; font-weight:bold; }
QGroupBox::title { subcontrol-origin:margin; subcontrol-position:top left; left:15px; top:5px; padding:0 7px; color:#665032; }
QPushButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #eddfbf,stop:1 #d4bf93); border:1px solid #ad9368; border-radius:2px; padding:7px 11px; min-height:20px; }
QPushButton:hover { background:#f1e4c7; border-color:#785c35; }
QPushButton:pressed { background:#bfaa7f; }
QPushButton:focus { border:2px solid #9d702f; padding:6px 10px; }
QPushButton:disabled { background:#d6c8ad; color:#958467; border-color:#c1b191; }
QPushButton[primary="true"] { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #8c493a,stop:1 #66362d); border:1px solid #54291f; color:#fff0cf; font-weight:bold; padding:8px 16px; }
QPushButton[primary="true"]:hover { background:#995343; border-color:#bd9360; }
QPushButton[primary="true"]:disabled { background:#99816c; border-color:#8e7a62; color:#d0bda0; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background:#f3e7cd; border:1px solid #b39d75; border-radius:2px; padding:6px 8px; min-height:20px; selection-background-color:#86623c; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border:2px solid #997239; padding:5px 7px; }
QComboBox::drop-down { border-left:1px solid #c2ad85; width:23px; }
QComboBox::down-arrow { image:url(__ASSETS__/chevron-down.svg); width:10px; height:7px; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image:url(__ASSETS__/chevron-up.svg); width:9px; height:6px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image:url(__ASSETS__/chevron-down.svg); width:9px; height:6px; }
QComboBox QAbstractItemView { background:#f3e7cd; color:#382f23; selection-background-color:#825c38; selection-color:#fff4dc; }
QTableWidget, QTableView, QListWidget { background:#f4e9d2; alternate-background-color:#ece0c4; border:1px solid #b29b71; selection-background-color:#825c38; selection-color:#fff4dc; outline:0; }
QTableWidget::item { padding:6px 9px; border-bottom:1px solid #e2d3b4; }
QTableWidget::item:selected { background:#825c38; color:#fff4dc; }
QHeaderView::section { background:#d4c09a; color:#625033; padding:9px 8px; border:none; border-bottom:1px solid #a98d5e; border-right:1px solid #c3ad83; font-size:12px; font-weight:bold; }
QTableCornerButton::section { background:#d4c09a; border:none; }
QListWidget::item { padding:11px 13px; border-bottom:1px solid #ddcdae; }
QListWidget::item:selected { background:#6f5137; color:#ffedc9; }
QTabWidget::pane { border:1px solid #aa9368; background:#e7d8b9; top:-1px; }
QTabBar::tab { background:#baa47d; border:1px solid #a38b60; color:#605036; padding:10px 18px; margin-right:3px; }
QTabBar::tab:selected { background:#e7d8b9; border-bottom:1px solid #e7d8b9; color:#612f25; font-weight:bold; }
QTabBar::tab:hover:!selected { background:#d2be97; }
QCheckBox { spacing:8px; background:transparent; }
QCheckBox::indicator { width:15px; height:15px; border:1px solid #967b4f; background:#f2e4c6; }
QCheckBox::indicator:checked { background:#6f5137; border:1px solid #967b4f; image:url(__ASSETS__/check.svg); }
QTextEdit { background:#f4e9d2; border:1px solid #b29b71; padding:6px; }
QScrollBar:vertical { background:#ddcdae; width:11px; margin:0; }
QScrollBar::handle:vertical { background:#a58a5f; min-height:25px; border-radius:3px; margin:2px; }
QScrollBar:horizontal { background:#ddcdae; height:11px; margin:0; }
QScrollBar::handle:horizontal { background:#a58a5f; min-width:25px; border-radius:3px; margin:2px; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
QSplitter::handle { background:#b9a37a; width:5px; }
QToolTip { background:#2c3027; color:#f1dfb8; border:1px solid #aa8e53; padding:7px; }
QMessageBox, QDialog { background:#e7d8b9; }
QProgressBar { border:1px solid #a38a5e; background:#c9b58e; text-align:center; min-height:18px; }
QProgressBar::chunk { background:#7b4b33; }
"""

# Material treatment shared by all workspaces; compact rules keep the expedition usable at 1080×720.
STYLESHEET += """
#workspace { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #373028,stop:.5 #241f19,stop:1 #393127); }
#sidebar { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #27231c,stop:.5 #3b3125,stop:1 #201d18); border-right:5px solid #120f0c; }
#navButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #494034,stop:.12 #372f25,stop:.86 #28231c,stop:1 #181612); border:1px solid #655438; border-top:1px solid #8f7752; border-bottom:3px solid #171410; color:#cfbd94; padding:12px 10px; }
#navButton:hover { background:#4c4030; border-color:#b29662; }
#navButton:checked { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #713e2d,stop:.12 #82402e,stop:.75 #56291f,stop:1 #321c16); border:1px solid #c09a5e; border-left:3px solid #e1bf77; border-bottom:3px solid #21150f; color:#ffedbd; }
#pageHeading { color:#efdbac; font-size:27px; }
#pageEyebrow { color:#bba176; font-size:10px; letter-spacing:2px; }
#pageSubtitle { color:#c4b392; font-size:12px; }
#brandName { color:#efddad; font-size:30px; }
#versionBadge { background:rgba(29,27,22,190); border:1px solid #968052; color:#e8d3a0; font-size:9px; padding:4px 7px; }
#gameBar { background:#29251e; border:1px solid #716043; }
#gameBar QLabel, #gamePath { color:#c7b795; }
#gameBar QPushButton { padding:3px 9px; min-height:18px; }
#mainFooter { color:#a5967b; }
QGroupBox { border:10px solid #5b4931; border-image:url(__ASSETS__/panel-frame.svg) 12 12 12 12 stretch stretch; border-radius:0; margin-top:13px; padding:15px 8px 8px; }
QGroupBox::title { color:#eddbb2; background:#403426; border:1px solid #9f8354; left:15px; top:1px; padding:2px 10px; }
QPushButton { border:1px solid #867046; border-top:1px solid #e2cda1; border-bottom:3px solid #76603e; border-radius:0; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #e1cda2,stop:.45 #cdb27e,stop:.52 #c3a673,stop:1 #b99b65); }
QPushButton[primary="true"] { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #a66141,stop:.15 #88472f,stop:1 #57291f); border:1px solid #be9259; border-bottom:3px solid #381b13; }
QHeaderView::section { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #65543b,stop:.5 #463c2e,stop:1 #332e24); color:#e7d0a0; border-bottom:2px solid #ac8952; border-right:1px solid #736041; padding:8px; }
QTableWidget, QTableView, QListWidget { background:#eee0bd; alternate-background-color:#e2cea4; border:2px solid #8a7046; }
QTableWidget::item { border-bottom:1px solid #cbb78e; }
QTableWidget::item:selected { background:#755035; color:#fff0ce; }
QTextEdit { background:#f0e3c7; border:1px solid #ad9161; }
#runStatus { color:#685035; font-size:11px; }
#seedFilters { padding:9px 3px 3px; }
#seedPage QComboBox, #seedPage QSpinBox, #seedPage QDoubleSpinBox, #seedPage QLineEdit { padding:3px 5px; min-height:18px; }
#seedPage QPushButton { padding:4px 8px; min-height:18px; }
#seedPage QPushButton[primary="true"] { padding:4px 10px; }
#filterTabs::pane { border:1px solid #a58a57; background:rgba(244,229,196,90); }
#filterTabs QTabBar::tab { padding:4px 12px; background:#bda477; color:#4b3b24; border:1px solid #988053; }
#filterTabs QTabBar::tab:selected { background:#eddbb4; color:#743e29; border-bottom-color:#eddbb4; }
#filterTabs QTabBar::tab:disabled { background:#c4b187; color:#8d7b5a; }
#sharePanel { background:#d7c096; border:2px solid #9c8053; border-top:2px solid #e3cb94; }
#sharePanel QTextEdit { border:1px solid #ac905c; padding:3px 5px; }
#seedPage QCheckBox { font-size:12px; }
#localizationControls { padding:9px 3px 3px; }
#localizationManager QPushButton { padding:4px 8px; min-height:18px; }
#localizationManager QHeaderView::section { padding:5px 8px; }
"""
