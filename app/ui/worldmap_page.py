"""Independent seed atlas and a terrain-aware trade-route preview."""
from __future__ import annotations

import json
import math
import threading

from PySide6.QtCore import QPointF, QRectF, Qt, QThread, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QProgressBar, QPushButton, QSpinBox, QTextBrowser,
    QSplitter, QTableWidget, QTableWidgetItem, QToolTip, QVBoxLayout, QWidget,
)

from core.io_util import atomic_write_json
from core.worldmap.engine import MapSolver, SolveCancelled
from core.worldmap.model import CAMP_PROFILE_LABEL, PROFILE_LABEL, OFFICIAL_ORIGINS, WorldMap, adjacent
from core.seedgen.config_emitter import ORIGIN_LABELS, DIFFICULTY_LABELS, BUDGET_LABELS
from core.worldmap.routes import Route, RoutePlanner
from core.worldmap.trade import GOODS, goods_label, opportunities, prices, town_advice, offer_reason
from core.worldmap.localization import place_label, town_label, building_label, site_label, town_traits
from core.worldmap.loot import KINDS, camp_detail, camp_position, item_label, item_rating
from .theme import style_button, style_table
from .readable_combo import ReadableComboBox as QComboBox
from .active_tabs import ActivePageTabs

COLORS = ('#111b1d', '#27424b', '#73815b', '#4e675d', '#8a8161', '#3e5743', '#788778',
          '#617258', '#786b44', '#626960', '#b8a071', '#b1a76a', '#c2c6b8', '#81735b',
          '#929676', '#99976c', '#c1af7e', '#bd9f6a', '#80926c')


class MapJob(QThread):
    done = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.stop = threading.Event()

    def run(self):
        try:
            value = self.function(self.stop)
        except SolveCancelled:
            self.cancelled.emit()
        except Exception as error:
            if self.stop.is_set(): self.cancelled.emit()
            else: self.failed.emit(str(error))
        else:
            if not self.stop.is_set():
                self.done.emit(value)
            else:
                self.cancelled.emit()


class MapCanvas(QWidget):
    town_selected = Signal(int)
    town_added = Signal(int)
    camp_selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(260, 180)
        self.setMouseTracking(True)
        self.setAccessibleName('世界地图；滚轮缩放，拖动平移，单击选择城镇，双击加入路线')
        self.world = None
        self.image = None
        self.scale = 1.
        self.offset = QPointF()
        self._drag = None
        self._moved = False
        self.roads = True
        self.facilities = False
        self.regions = False
        self.label_size = 18
        self.trade_view = False
        self.selected = -1
        self.selected_camp = -1
        self.all_camps = False
        self.route = None
        self.stops = []
        self._road_path = QPainterPath()

    def point(self, xy):
        return QPointF(xy[0]*4+2, (self.world.height-1-xy[1])*4+4-(xy[0] & 1)*2)

    def screen_point(self, xy):
        return self.point(xy)*self.scale+self.offset

    def set_world(self, world):
        self.world = world
        self.selected = -1
        self.selected_camp = -1
        self.route = None
        self.stops = []
        path = QPainterPath()
        for y, row in enumerate(world.rows):
            for x, tile in enumerate(row):
                for direction in range(3):
                    other = adjacent(x, y, direction)
                    if tile[4] & (1 << direction) and world.contains(other):
                        path.moveTo(self.point((x, y)))
                        path.lineTo(self.point(other))
        self._road_path = path
        self.make_image()
        self.fit()

    def make_image(self):
        if self.world is None:
            return
        self.image = QImage(self.world.width*4+4, self.world.height*4+8, QImage.Format_RGB32)
        self.image.fill(QColor('#1c292b'))
        painter = QPainter(self.image)
        for y, row in enumerate(self.world.rows):
            for x, tile in enumerate(row):
                color = QColor(COLORS[tile[0]])
                if self.trade_view:
                    value = int(color.red()*.25+color.green()*.55+color.blue()*.2)
                    color = QColor(value, value, int(value*.95))
                color = color.lighter(95+(x*13+y*7) % 11)
                p = self.point((x, y))
                painter.fillRect(QRectF(p.x()-2, p.y()-2, 4, 4), color)
        painter.end()
        self.update()

    def fit(self):
        if self.image is not None:
            self.scale = min((self.width()-24)/self.image.width(), (self.height()-24)/self.image.height())
            self.offset = QPointF((self.width()-self.image.width()*self.scale)/2,
                                  (self.height()-self.image.height()*self.scale)/2)
        self.update()

    def resizeEvent(self, event):
        if self.world is not None and self.world.campaign is not None and self.selected_camp >= 0:
            camp = self.world.campaign.camps[self.selected_camp]
            self.offset = QPointF(event.size().width()/2, event.size().height()/2)-self.point(camp.xy)*self.scale
        elif event.oldSize().isValid():
            self.offset += QPointF((event.size().width()-event.oldSize().width())/2,
                                   (event.size().height()-event.oldSize().height())/2)
        super().resizeEvent(event)

    def zoom(self, factor, anchor=None):
        if self.image is None:
            return
        anchor = anchor or QPointF(self.width()/2, self.height()/2)
        new = max(.25, min(12., self.scale*factor))
        self.offset = anchor-(anchor-self.offset)*(new/self.scale)
        self.scale = new
        self.update()

    def focus_camp(self, index):
        if self.world is None or self.world.campaign is None:
            return
        self.selected_camp = index
        self.scale = max(self.scale, 2.0)
        self.offset = QPointF(self.width()/2, self.height()/2)-self.point(self.world.campaign.camps[index].xy)*self.scale
        self.update()

    def visible_camps(self):
        if self.world is None or self.world.campaign is None:
            return ()
        return tuple(c for c in self.world.campaign.camps if c.items or self.all_camps or c.index == self.selected_camp)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#182123'))
        if self.world is None:
            painter.setPen(QColor('#d7ba7a'))
            painter.drawText(self.rect(), Qt.AlignCenter, '输入种子，展开新世界\n\n无需启动游戏')
            return
        painter.save()
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)
        painter.drawImage(QPointF(), self.image)
        if self.roads:
            painter.setPen(QPen(QColor('#c5a36d'), max(.65, 1.3/self.scale)))
            painter.drawPath(self._road_path)
        if self.route and self.route.tiles:
            path = QPainterPath(self.point(self.route.tiles[0]))
            for xy in self.route.tiles[1:]:
                path.lineTo(self.point(xy))
            painter.setPen(QPen(QColor('#54e2bb'), 3/self.scale))
            painter.drawPath(path)
        painter.restore()
        painter.setRenderHint(QPainter.Antialiasing)
        if self.regions and self.scale > .7:
            painter.setPen(QColor('#e1d5ae'))
            font = QFont(self.font()); font.setPixelSize(max(14, self.label_size-3)); painter.setFont(font)
            for region in self.world.regions:
                p = self.screen_point(region['xy'])
                painter.drawText(p, place_label(region['name']))
        if self.facilities:
            painter.setPen(QColor('#dbb75e'))
            for town in self.world.settlements:
                for site in town.attached:
                    p = self.screen_point(site['xy'])
                    painter.drawRect(QRectF(p.x()-2, p.y()-2, 4, 4))
        font = QFont(self.font()); font.setPixelSize(self.label_size); font.setBold(True); painter.setFont(font)
        labels = []
        towns = sorted(self.world.settlements, key=lambda t: t.index != self.selected)
        for town in towns:
            p = self.screen_point(town.xy)
            if not self.rect().adjusted(-100, -30, 100, 30).contains(p.toPoint()):
                continue
            selected = town.index == self.selected
            color = '#dcac61' if town.culture != 2 else '#db895f'
            if town.military:
                color = '#bf7770'
            painter.setPen(QPen(QColor('#f9df9b') if selected else QColor('#222621'), 2))
            painter.setBrush(QColor(color))
            painter.drawEllipse(p, 6 if selected else 4, 6 if selected else 4)
            if 'building.port' in town.buildings:
                painter.setPen(QPen(QColor('#78cbd8'), 2))
                painter.drawLine(p+QPointF(-4, 7), p+QPointF(4, 7))
            if self.scale >= .65 or selected:
                text = town_label(self.world, town.index)
                text = painter.fontMetrics().elidedText(text, Qt.ElideRight, max(220, self.label_size*12))
                metrics = painter.fontMetrics(); width = metrics.horizontalAdvance(text)
                candidates = [p+QPointF(8, -5), p+QPointF(-width-8, -5),
                              p+QPointF(8, 18), p+QPointF(-width-8, 18), p+QPointF(-width/2, -14)]
                for q in candidates:
                    bounds = QRectF(q.x()-2, q.y()-metrics.ascent()-2, width+4, metrics.height()+4)
                    if not QRectF(self.rect().adjusted(4, 4, -4, -4)).contains(bounds): continue
                    if any(bounds.intersects(old) for old in labels): continue
                    labels.append(bounds)
                    painter.fillRect(bounds, QColor(23, 32, 33, 215))
                    painter.setPen(QPen(QColor('#172021'), 3)); painter.drawText(q+QPointF(1, 1), text)
                    painter.setPen(QColor('#fff0c6')); painter.drawText(q, text)
                    break
            if town.index in self.stops:
                text = str(self.stops.index(town.index)+1)
                painter.setPen(QColor('#5cf0c5'))
                painter.drawText(p+QPointF(-5, -10), text)
        for camp in self.visible_camps():
            p = self.screen_point(camp.xy)
            if not self.rect().adjusted(-20, -20, 20, 20).contains(p.toPoint()):
                continue
            selected = camp.index == self.selected_camp
            painter.setPen(QPen(QColor('#ffe6a0') if selected else QColor('#271b1b'), 2))
            painter.setBrush(QColor('#ee7871' if camp.items else '#9f9a80'))
            shape = QPainterPath(p+QPointF(0, -6)); shape.lineTo(p+QPointF(6, 0))
            shape.lineTo(p+QPointF(0, 6)); shape.lineTo(p+QPointF(-6, 0)); shape.closeSubpath()
            painter.drawPath(shape)
            if selected:
                painter.setBrush(Qt.NoBrush); painter.setPen(QPen(QColor('#ffe6a0'), 2)); painter.drawEllipse(p, 12, 12)
                text = place_label(camp.name)
                bounds = painter.fontMetrics().boundingRect(text).adjusted(-5, -3, 5, 3)
                bounds.moveBottomLeft((p+QPointF(15, -8)).toPoint())
                painter.fillRect(bounds, QColor('#192123')); painter.setPen(QColor('#ffe6a0'))
                painter.drawText(bounds, Qt.AlignCenter, text)
        painter.setPen(QColor('#d7ba7a')); painter.drawText(12, 24, '北 ↑')

    def _near_camp(self, pos):
        for camp in self.visible_camps():
            p = self.screen_point(camp.xy)
            if math.hypot(p.x()-pos.x(), p.y()-pos.y()) < 12:
                return camp.index
        return -1

    def _near_town(self, pos):
        if self.world:
            for town in self.world.settlements:
                p = self.screen_point(town.xy)
                if math.hypot(p.x()-pos.x(), p.y()-pos.y()) < 14:
                    return town.index
        return -1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = event.position()
            self._moved = False

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            delta = event.position()-self._drag
            if abs(delta.x())+abs(delta.y()) > 2:
                self._moved = True
            self.offset += delta
            self._drag = event.position()
            self.update()
        else:
            index = self._near_town(event.position())
            if index >= 0:
                town = self.world.settlements[index]
                goods = '、'.join(goods_label(key) for key in town.produce)
                QToolTip.showText(event.globalPosition().toPoint(), f'{town_label(self.world, index)}\n{goods}\n双击加入路线', self)
            else:
                camp_index = self._near_camp(event.position())
                if camp_index >= 0:
                    camp = self.world.campaign.camps[camp_index]
                    QToolTip.showText(event.globalPosition().toPoint(), f'{place_label(camp.name)}\n红装 {len(camp.items)} 件\n单击查看', self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self._moved:
            camp_index = self._near_camp(event.position())
            if camp_index >= 0:
                self.camp_selected.emit(camp_index)
            else:
                index = self._near_town(event.position())
                if index >= 0:
                    self.town_selected.emit(index)
        self._drag = None

    def mouseDoubleClickEvent(self, event):
        index = self._near_town(event.position())
        if index >= 0:
            self.town_added.emit(index)

    def wheelEvent(self, event):
        self.zoom(1.2 if event.angleDelta().y() > 0 else 1/1.2, event.position())


class WorldMapPage(QWidget):
    def __init__(self, settings, *, solver=None):
        super().__init__()
        self.settings = settings
        self.solver = solver or MapSolver()
        self.world: WorldMap | None = None
        self.planner = None
        self._job = None
        self._route_job = None
        self.stops = []
        self.route: Route | None = None
        saved = settings.get('worldmap_preview', {})
        self._saved = saved if isinstance(saved, dict) else {}
        root = QVBoxLayout(self); root.setContentsMargins(4, 4, 4, 4)
        top = QHBoxLayout()
        top.addWidget(QLabel('种子码'))
        self.seed = QLineEdit(self._saved.get('seed', '46U2HMOORH'))
        self.seed.setMaxLength(32); self.seed.setPlaceholderText('十位种子码，区分大小写')
        self.seed.setAccessibleName('地图种子码'); top.addWidget(self.seed, 1)
        self.solve_button = QPushButton('解算地图'); style_button(self.solve_button, 'compass', primary=True)
        self.solve_button.clicked.connect(self.solve); self.seed.returnPressed.connect(self.solve)
        top.addWidget(self.solve_button)
        self.cancel_button = QPushButton('取消'); self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel); top.addWidget(self.cancel_button)
        root.addLayout(top)
        campaign_row = QHBoxLayout()
        self.origin_combo = QComboBox()
        for origin, label in ORIGIN_LABELS.items():
            if origin in OFFICIAL_ORIGINS: self.origin_combo.addItem(label, origin)
        self.combat_combo, self.economic_combo, self.budget_combo = QComboBox(), QComboBox(), QComboBox()
        controls = (('起源', self.origin_combo, 'origin', 'scenario.militia'),
                    ('战斗', self.combat_combo, 'combat', 2), ('经济', self.economic_combo, 'economic', 2),
                    ('初始资金', self.budget_combo, 'budget', 2))
        for label, combo, key, default in controls:
            if key != 'origin':
                for value, text in (BUDGET_LABELS if key == 'budget' else DIFFICULTY_LABELS).items():
                    combo.addItem(text, value)
            combo.setCurrentIndex(max(0, combo.findData(self._saved.get(key, default))))
            combo.setAccessibleName('地图开局'+label)
            campaign_row.addWidget(QLabel(label)); campaign_row.addWidget(combo, 2 if key == 'origin' else 1)
            combo.currentIndexChanged.connect(self._campaign_changed)
        root.addLayout(campaign_row)
        self.status = QLabel(PROFILE_LABEL+' · 独立计算，无需游戏目录')
        self.status.setWordWrap(True); root.addWidget(self.status)
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.setFixedHeight(5); self.progress.hide()
        root.addWidget(self.progress)
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        left = QWidget(); left_layout = QVBoxLayout(left); left_layout.setContentsMargins(0, 0, 4, 0)
        tools = QHBoxLayout()
        fit = QPushButton('全图'); fit.clicked.connect(lambda: self.canvas.fit()); tools.addWidget(fit)
        plus = QPushButton('+'); plus.setMaximumWidth(36); plus.clicked.connect(lambda: self.canvas.zoom(1.3)); tools.addWidget(plus)
        minus = QPushButton('−'); minus.setMaximumWidth(36); minus.clicked.connect(lambda: self.canvas.zoom(1/1.3)); tools.addWidget(minus)
        self.mode = QComboBox(); self.mode.addItems(['地形图', '商路图']); self.mode.currentIndexChanged.connect(self._view_changed); tools.addWidget(self.mode)
        tools.addStretch(); left_layout.addLayout(tools)
        layers = QHBoxLayout()
        self.road_layer = QCheckBox('道路'); self.road_layer.setChecked(True); layers.addWidget(self.road_layer)
        self.site_layer = QCheckBox('设施'); layers.addWidget(self.site_layer)
        self.region_layer = QCheckBox('地名'); layers.addWidget(self.region_layer)
        for check in (self.road_layer, self.site_layer, self.region_layer):
            check.toggled.connect(self._layers_changed)
        layers.addStretch(); layers.addWidget(QLabel('地图字号'))
        self.label_size = QSpinBox(); self.label_size.setRange(14, 30)
        size = settings.get('worldmap_label_size', 18)
        self.label_size.setValue(size if type(size) is int and 14 <= size <= 30 else 18)
        self.label_size.setAccessibleName('地图文字大小'); self.label_size.setMinimumWidth(62)
        self.label_size.valueChanged.connect(self._label_size_changed); layers.addWidget(self.label_size)
        left_layout.addLayout(layers)
        self.canvas = MapCanvas(); self.canvas.town_selected.connect(self.select_town); self.canvas.town_added.connect(self.add_stop)
        self.canvas.label_size = self.label_size.value()
        self.canvas.camp_selected.connect(self.select_camp)
        left_layout.addWidget(self.canvas, 1)
        legend = QLabel('金点：居民点 · 红点：军事城镇 · 菱形：红装营地\n滚轮缩放 · 拖动平移 · 双击城镇加入路线')
        legend.setToolTip('蓝线：港口 · 绿线：跑商路线 · 红菱形：红装营地\n单击城镇或营地查看详情；双击城镇加入路线。')
        legend.setWordWrap(True); legend.setObjectName('muted'); left_layout.addWidget(legend)
        split.addWidget(left)
        self.tabs = ActivePageTabs(); self.tabs.setMinimumWidth(350)
        self.tabs.setObjectName('mapDetailTabs')
        towns = QWidget(); layout = QVBoxLayout(towns)
        layout.setContentsMargins(6, 6, 6, 6); layout.setSpacing(4)
        self.towns = QTableWidget(0, 3); self.towns.setHorizontalHeaderLabels(['城镇', '特性', '产出'])
        self.towns.setMinimumHeight(100)
        style_table(self.towns); self.towns.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.towns.itemSelectionChanged.connect(self._town_selection); layout.addWidget(self.towns, 1)
        self.detail = QTextBrowser(); self.detail.setPlainText('选择城镇查看特性、设施和买卖建议')
        self.detail.setMinimumHeight(76)
        town_details = ActivePageTabs()
        town_details.setObjectName('mapTownDetails')
        town_details.addTab(self.detail, '城镇详情')
        self.market = QTableWidget(0, 3); self.market.setHorizontalHeaderLabels(['贸易品', '在此买入', '在此卖出'])
        style_table(self.market); self.market.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.market.setMinimumHeight(76)
        town_details.addTab(self.market, '买卖估价')
        layout.addWidget(town_details, 1)
        add = QPushButton('加入跑商路线'); add.clicked.connect(lambda: self.add_stop(self.canvas.selected)); layout.addWidget(add)
        self.tabs.addTab(towns, '城镇与特产')
        trade = QWidget(); layout = QVBoxLayout(trade)
        layout.setContentsMargins(6, 6, 6, 6); layout.setSpacing(4)
        self.offers = QTableWidget(0, 4); self.offers.setHorizontalHeaderLabels(['商品', '产地 → 销地', '单件毛利', '价差率'])
        self.offers.setProperty('compactHeaders', True)
        self.offers.setMinimumHeight(100)
        self.offers.horizontalHeaderItem(3).setToolTip('（估算卖价 − 估算买价）÷ 估算买价')
        style_table(self.offers); self.offers.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.offers.setWordWrap(True)
        for column in (0, 2, 3): self.offers.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.offers.itemSelectionChanged.connect(self._offer_selected)
        self.route_details = route_details = ActivePageTabs()
        route_details.setObjectName('mapRouteDetails')
        route_page = QWidget(); route_layout = QVBoxLayout(route_page)
        options_page = QWidget(); options_layout = QVBoxLayout(options_page)
        offer_page = QWidget(); offer_layout = QVBoxLayout(offer_page)
        for details_layout in (route_layout, options_layout, offer_layout):
            details_layout.setContentsMargins(4, 4, 4, 4); details_layout.setSpacing(4)
        self.offer_detail = QLabel('选择商品查看采购价、销售价与赚钱依据。')
        offer_layout.addWidget(self.offers, 1)
        self.offer_detail.setWordWrap(True); self.offer_detail.setTextFormat(Qt.PlainText); offer_layout.addWidget(self.offer_detail)
        explanation = QLabel('选择商品预览两站路线。基础行情：关系 50、默认起源、无临时事件；库存与实际成交价以游戏为准。')
        explanation.setObjectName('muted'); explanation.setWordWrap(True); options_layout.addWidget(explanation)
        self.stop_list = QListWidget(); self.stop_list.setMinimumHeight(32); self.stop_list.setMaximumHeight(78); self.stop_list.setAccessibleName('按顺序经过的城镇'); route_layout.addWidget(self.stop_list, 1)
        edits = QHBoxLayout()
        for label, callback in [('撤销一站', self.undo), ('反向', self.reverse), ('清空', self.clear_route), ('导出', self.export_route)]:
            button = QPushButton(label); button.clicked.connect(callback); edits.addWidget(button)
        route_layout.addLayout(edits)
        row = QHBoxLayout()
        self.road_only = QCheckBox('仅走连续道路'); self.road_only.toggled.connect(self.preview_route); row.addWidget(self.road_only)
        row.addWidget(QLabel('日开销'))
        self.daily_cost = QDoubleSpinBox(); self.daily_cost.setRange(0, 10000); self.daily_cost.setDecimals(0); self.daily_cost.setSuffix(' 克朗')
        self.daily_cost.valueChanged.connect(self._route_summary); row.addWidget(self.daily_cost, 1); options_layout.addLayout(row)
        quantity_row = QHBoxLayout(); quantity_row.addWidget(QLabel('计划采购'))
        self.quantity = QSpinBox(); self.quantity.setRange(1, 1000); self.quantity.setValue(1); self.quantity.setSuffix(' 件')
        self.quantity.setToolTip('计划采购数量；不表示产地库存。收益按所填数量估算。')
        self.quantity.valueChanged.connect(self._route_summary); quantity_row.addWidget(self.quantity, 1); options_layout.addLayout(quantity_row)
        self.summary = QLabel('双击地图城镇可自定义多站路线。'); self.summary.setWordWrap(True); self.summary.setTextFormat(Qt.PlainText); route_layout.addWidget(self.summary)
        timing = QLabel('行程按白天基础速度估算，计地形与道路；未计夜间、队伍修正、遭遇和海运。')
        timing.setWordWrap(True); timing.setObjectName('muted'); options_layout.addWidget(timing)
        options_layout.addStretch()
        route_details.addTab(offer_page, '商品机会')
        route_details.addTab(route_page, '路线与收益')
        route_details.addTab(options_page, '采购与费用')
        layout.addWidget(route_details, 1)
        self.tabs.addTab(trade, '跑商路线')
        loot = QWidget(); layout = QVBoxLayout(loot)
        layout.setContentsMargins(6, 6, 6, 6); layout.setSpacing(4)
        self.loot_pages = ActivePageTabs()
        self.loot_pages.setObjectName('mapLootDetails')
        loot_list = QWidget(); list_layout = QVBoxLayout(loot_list)
        loot_record = QWidget(); record_layout = QVBoxLayout(loot_record)
        for details_layout in (list_layout, record_layout):
            details_layout.setContentsMargins(4, 4, 4, 4); details_layout.setSpacing(4)
        self.loot_status = QLabel('解算后列出所有营地的开局红装，选择即可在地图定位。')
        self.loot_status.setWordWrap(True); record_layout.addWidget(self.loot_status)
        self.loot_profile = QLabel(self._campaign_label(self._campaign_options()))
        self.loot_profile.setToolTip(CAMP_PROFILE_LABEL)
        self.loot_profile.setWordWrap(True); self.loot_profile.setObjectName('muted'); record_layout.addWidget(self.loot_profile)
        filters = QHBoxLayout()
        self.loot_kind = QComboBox(); self.loot_kind.addItem('全部红装', '')
        for key, name in KINDS.items(): self.loot_kind.addItem(name, key)
        self.loot_kind.currentIndexChanged.connect(self._filter_loot); filters.addWidget(self.loot_kind)
        self.loot_search = QLineEdit(); self.loot_search.setPlaceholderText('查找装备或营地')
        self.loot_search.setAccessibleName('按中文装备名或营地名筛选红装')
        self.loot_search.textChanged.connect(self._filter_loot); filters.addWidget(self.loot_search, 1)
        list_layout.addLayout(filters)
        self.loot_table = QTableWidget(0, 4); self.loot_table.setHorizontalHeaderLabels(['红装', '实用分', 'roll', '营地'])
        self.loot_table.setMinimumHeight(90)
        self.loot_table.setToolTip('单击定位营地；双击打开完整装备档案。')
        self.loot_table.horizontalHeaderItem(1).setToolTip('伤穿优先 v1；仅武器评分，适合比较同类词条')
        self.loot_table.horizontalHeaderItem(2).setToolTip('两条随机武器词条的 roll 品质；不含耐久')
        style_table(self.loot_table)
        for column in (0, 3): self.loot_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Stretch)
        for column in (1, 2): self.loot_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.loot_table.itemSelectionChanged.connect(self._loot_selected); list_layout.addWidget(self.loot_table, 1)
        self.loot_table.cellDoubleClicked.connect(lambda *_: self.loot_pages.setCurrentIndex(1))
        self.all_camps = QCheckBox('同时显示没有红装的营地')
        self.all_camps.toggled.connect(self._camp_layer_changed); list_layout.addWidget(self.all_camps)
        self.loot_detail = QTextBrowser(); self.loot_detail.setPlainText('选择红装，查看所在营地、相邻城镇和具体属性。')
        self.loot_detail.setMinimumHeight(80); record_layout.addWidget(self.loot_detail, 1)
        note = QLabel('按坐标定位营地；随机称号可能变化。')
        note.setToolTip('按所选原版开局生成；部分营地的随机称号不由种子唯一决定。游玩后的委托、刷新和 MOD 可能改变营地及战利品。')
        note.setWordWrap(True); note.setObjectName('muted'); record_layout.addWidget(note)
        self.loot_pages.addTab(loot_list, '红装列表')
        self.loot_pages.addTab(loot_record, '装备档案')
        layout.addWidget(self.loot_pages, 1)
        self.tabs.addTab(loot, '营地红装')
        self._loot = []; self._filtered_loot = []
        split.addWidget(self.tabs); split.setStretchFactor(0, 3); split.setStretchFactor(1, 2)
        root.addWidget(split, 1)
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def activate(self):
        if self.world is None and self._job is None:
            self.solve()

    def solve(self):
        if self._job is not None:
            return
        code = self.seed.text()
        options = self._campaign_options()
        job = self._job = MapJob(lambda stop: self.solver.solve(code, include_camps=True, cancelled=stop, **options), self)
        self._set_campaign_enabled(False)
        self.solve_button.setEnabled(False); self.cancel_button.setEnabled(True); self.progress.show()
        self.status.setText('正在独立解算地图、营地与红装…')
        job.done.connect(lambda value: self._accept_map(value) if not job.stop.is_set() else None)
        job.failed.connect(self._solve_error)
        job.cancelled.connect(lambda: self.status.setText('已取消解算，当前地图已保留。'))
        job.finished.connect(lambda: self._job_finished(job)); job.start()

    def _job_finished(self, job):
        if self._job is job:
            self._job = None
        self.solve_button.setEnabled(True); self.cancel_button.setEnabled(False); self.progress.hide(); job.deleteLater()
        self._set_campaign_enabled(True)
        pending = getattr(self, '_pending_seed', None)
        if pending:
            self._pending_seed = None; self.seed.setText(pending); self.solve()

    def _campaign_options(self):
        return dict(origin=self.origin_combo.currentData(), combat=self.combat_combo.currentData(),
                    economic=self.economic_combo.currentData(), budget=self.budget_combo.currentData())

    @staticmethod
    def _campaign_label(options):
        return (f'{ORIGIN_LABELS[options["origin"]]} · 战斗{DIFFICULTY_LABELS[options["combat"]]} · '
                f'经济{DIFFICULTY_LABELS[options["economic"]]} · 资金{BUDGET_LABELS[options["budget"]]}')

    def _set_campaign_enabled(self, enabled):
        for combo in (self.origin_combo, self.combat_combo, self.economic_combo, self.budget_combo):
            combo.setEnabled(enabled)

    def _campaign_changed(self):
        if hasattr(self, 'status'):
            self.status.setText('开局配置已修改，点击「解算地图」生成对应营地与红装。')

    def _save_preview(self):
        self.settings.set('worldmap_preview', dict(seed=self.world.seed, stops=self.stops, **self._campaign_options()))

    def open_seed(self, seed, *, origin=None, combat=None, economic=None, budget=None, dlc_mask=342, mods=()):
        self.seed.setText(seed)
        if dlc_mask != 342 or mods:
            self._pending_seed = None
            self.status.setText('此档案的 DLC 或 MOD 环境不属于原版全 DLC 独立配置；当前预览无法复现其营地红装。')
            if self._job is not None: self.cancel()
            return
        if origin is not None:
            if origin not in OFFICIAL_ORIGINS or any(type(v) is not int or v not in (0, 1, 2)
                                                    for v in (combat, economic, budget)):
                self.status.setText('此档案缺少完整官方开局配置，或使用了自制起源。请先选择对应的官方起源和难度，再解算。')
                self._pending_seed = None
                if self._job is not None: self.cancel()
                return
            for combo, value in ((self.origin_combo, origin), (self.combat_combo, combat),
                                 (self.economic_combo, economic), (self.budget_combo, budget)):
                combo.setCurrentIndex(combo.findData(value))
        if self._job is not None:
            self._pending_seed = seed; self.cancel()
        elif (self.world is None or self.world.seed != seed or self.world.campaign is None
              or any(getattr(self.world.campaign, key) != value for key, value in self._campaign_options().items())):
            self.solve()

    def _solve_error(self, message):
        self.status.setText(message)

    def cancel(self):
        if self._job is not None:
            self._job.stop.set()

    def _accept_map(self, result):
        saved = self.settings.get('worldmap_preview', {})
        saved = saved if isinstance(saved, dict) else {}
        restore_stops = list(saved.get('stops', [])) if saved.get('seed') == result.world.seed else []
        self.world = result.world; self.planner = RoutePlanner(self.world)
        self.canvas.set_world(self.world); self.clear_route()
        self.status.setText(f'{PROFILE_LABEL} · {len(self.world.settlements)} 座城镇 · 23,800 地块 · '
                            f'{"缓存读取" if result.cached else "独立解算"} {result.elapsed:.2f} 秒')
        self.towns.blockSignals(True); self.towns.setRowCount(len(self.world.settlements))
        for town in self.world.settlements:
            for column, text in enumerate((town_label(self.world, town.index), '、'.join(town_traits(town)), '、'.join(goods_label(key) for key in town.produce))):
                item = QTableWidgetItem(text); item.setToolTip(text+'\n原名：'+self.world.town_name(town.index)); self.towns.setItem(town.index, column, item)
        self.towns.blockSignals(False)
        self._offers = opportunities(self.world)
        self.offers.blockSignals(True); self.offers.setRowCount(min(40, len(self._offers)))
        for row, offer in enumerate(self._offers[:40]):
            source, target = self.world.settlements[offer.source], self.world.settlements[offer.target]
            values = (goods_label(offer.good), town_label(self.world, source.index)+'\n→ '+town_label(self.world, target.index), str(offer.profit), f'{offer.roi:.0%}')
            self.offers.setRowHeight(row, max(78, self.offers.fontMetrics().height()*2+28))
            for column, text in enumerate(values):
                item = QTableWidgetItem(text); item.setToolTip(text+f'\n买入 {offer.buy}，卖出 {offer.sell} 克朗/件')
                self.offers.setItem(row, column, item)
        self.offers.blockSignals(False)
        self.offer_detail.setText('选择商品查看采购价、销售价与赚钱依据。')
        self._loot = [(camp, item) for camp in self.world.campaign.camps for item in camp.items] if self.world.campaign else []
        self._filter_loot()
        self.loot_detail.setPlainText('选择红装，查看所在营地、相邻城镇和具体属性。')
        if self.world.campaign:
            options = {key: getattr(self.world.campaign, key) for key in ('origin', 'combat', 'economic', 'budget')}
            self.loot_profile.setText(self._campaign_label(options))
            self.loot_profile.setToolTip(PROFILE_LABEL+' · '+self._campaign_label(options)+' · 开局营地')
            self.status.setText(self.status.text()+f' · {len(self.world.campaign.camps)} 处营地 · {len(self._loot)} 件红装')
        if restore_stops:
            self.stops = [i for i in restore_stops if type(i) is int and 0 <= i < len(self.world.settlements)]
            self.preview_route()
        if self.world.settlements: self.select_town(0)
        self._save_preview()

    def select_town(self, index):
        if self.world is None or not 0 <= index < len(self.world.settlements): return
        self.canvas.selected = index; self.canvas.update()
        town = self.world.settlements[index]
        sites = '、'.join(site_label(a) for a in town.attached) or '无'
        buildings = '、'.join(building_label(b) for b in town.buildings if b and b not in ('building.crowd', 'building.marketplace')) or '无特殊建筑'
        self.detail.setPlainText(f'{town_label(self.world, index)} · '+ ' · '.join(town_traits(town))
            +f'\n设施：{sites}\n建筑：{buildings}\n\n'+town_advice(self.world, index))
        self.market.setRowCount(len(GOODS))
        for row, key in enumerate(GOODS):
            buy, sell = prices(town, key)
            for column, text in enumerate((goods_label(key)+('（产地）' if key in town.produce else ''), str(buy), str(sell))):
                self.market.setItem(row, column, QTableWidgetItem(text))
        self.towns.blockSignals(True); self.towns.selectRow(index); self.towns.blockSignals(False)

    def _filter_loot(self, *_):
        kind, query = self.loot_kind.currentData(), self.loot_search.text().strip().casefold()
        self._filtered_loot = [(camp, item) for camp, item in self._loot
            if (not kind or item.kind == kind) and (not query or query in
                ' '.join((item_label(item), place_label(camp.name), item.name, item.identifier, camp.name)).casefold())]
        self.loot_table.blockSignals(True); self.loot_table.clearContents(); self.loot_table.setRowCount(len(self._filtered_loot))
        self.loot_table.clearSelection(); self.loot_table.setCurrentCell(-1, -1)
        for row, (camp, item) in enumerate(self._filtered_loot):
            rating = item_rating(item)
            values = (item_label(item), str(rating.score) if rating else '—', f'{rating.quality}%' if rating else '—', place_label(camp.name))
            for column, text in enumerate(values):
                cell = QTableWidgetItem(text); cell.setToolTip(f'{item_label(item)}\n{camp_position(self.world, camp)}\n原名：{item.name}')
                self.loot_table.setItem(row, column, cell)
        self.loot_table.blockSignals(False)
        self.canvas.selected_camp = -1; self.canvas.update()
        self.loot_detail.setPlainText('选择红装，查看所在营地、相邻城镇和具体属性。')
        if self.world and self.world.campaign:
            self.loot_status.setText(f'开局 {len(self._loot)} 件 · 当前 {len(self._filtered_loot)} 件')
            self.loot_pages.setTabText(0, f'红装列表 · {len(self._filtered_loot)}')
        else:
            self.loot_status.setText('当前地图没有营地数据，请使用包含营地的离线组件重新解算。')

    def _loot_selected(self):
        row = self.loot_table.currentRow()
        if 0 <= row < len(self._filtered_loot):
            camp, item = self._filtered_loot[row]
            self.canvas.focus_camp(camp.index)
            self.loot_detail.setPlainText(camp_detail(self.world, camp, item))

    def select_camp(self, index):
        if self.world is None or self.world.campaign is None or not 0 <= index < len(self.world.campaign.camps):
            return
        self.tabs.setCurrentIndex(2)
        self.loot_pages.setCurrentIndex(1)
        camp = self.world.campaign.camps[index]
        self.loot_kind.setCurrentIndex(0); self.loot_search.clear()
        for row, (location, item) in enumerate(self._filtered_loot):
            if location.index == index:
                self.loot_table.selectRow(row); self._loot_selected(); return
        self.loot_table.clearSelection(); self.loot_table.setCurrentCell(-1, -1)
        self.canvas.focus_camp(index); self.loot_detail.setPlainText(camp_detail(self.world, camp))

    def _camp_layer_changed(self, checked):
        self.canvas.all_camps = checked; self.canvas.update()

    def _town_selection(self):
        row = self.towns.currentRow()
        if row >= 0: self.select_town(row)

    def _offer_selected(self):
        row = self.offers.currentRow()
        if self.world is not None and row >= 0:
            offer = self._offers[row]
            self.offer_detail.setText(f'采购 {offer.buy} → 销售 {offer.sell} 克朗/件\n'+offer_reason(self.world, offer))
            self.stops = [offer.source, offer.target]; self.preview_route()

    def add_stop(self, index):
        if self.world is None or not 0 <= index < len(self.world.settlements): return
        if not self.stops or self.stops[-1] != index:
            self.stops.append(index)
        self.tabs.setCurrentIndex(1); self.route_details.setCurrentIndex(1); self.preview_route()

    def undo(self):
        if self.stops: self.stops.pop(); self.preview_route()

    def reverse(self):
        self.stops.reverse(); self.preview_route()

    def clear_route(self):
        self._pending_route = False
        if self._route_job is not None: self._route_job.stop.set()
        self.stops = []; self.route = None; self.canvas.route = None; self.canvas.stops = []
        self.stop_list.clear(); self.canvas.update(); self._route_summary()
        if self.world is not None:
            self._save_preview()

    def preview_route(self):
        if self.world is None: return
        self.stop_list.clear()
        for i, index in enumerate(self.stops): self.stop_list.addItem(f'{i+1}  {town_label(self.world, index)}')
        self.canvas.stops = list(self.stops); self.canvas.route = None; self.canvas.update(); self.route = None
        self._save_preview()
        if self._route_job is not None:
            self._route_job.stop.set()
            self._pending_route = True
            return
        if len(self.stops) < 2:
            self._route_summary(); return
        stops, road_only, planner = tuple(self.stops), self.road_only.isChecked(), self.planner
        self.summary.setText('正在计算可通行路线…')
        job = self._route_job = MapJob(lambda _: planner.plan(stops, road_only=road_only), self)
        self._pending_route = False
        expected_world = self.world
        job.done.connect(lambda route: self._accept_route(route) if self.world is expected_world
                         and not job.stop.is_set() and road_only == self.road_only.isChecked() else None)
        job.failed.connect(lambda message: self.summary.setText(message) if self.world is expected_world and not job.stop.is_set() else None)
        job.finished.connect(lambda: self._route_finished(job)); job.start()

    def _route_finished(self, job):
        if self._route_job is job: self._route_job = None
        job.deleteLater()
        if self._pending_route: self.preview_route()

    def _accept_route(self, route):
        if route.stops != tuple(self.stops): return
        self.route = route; self.canvas.route = route; self.canvas.update(); self._route_summary()

    def _route_summary(self, *_):
        if self.route is None:
            self.summary.setText('选择至少两座城镇，预览沿途地形与行程。'); return
        steps = max(0, len(self.route.tiles)-1)
        expenses = self.route.hours/24*self.daily_cost.value()
        text = f'{len(self.route.stops)} 站 · {steps} 格 · 基础行程 {self.route.hours:.1f} 小时\n道路 {self.route.road_steps} 格 · 按日开销估算 {expenses:.0f} 克朗'
        row = self.offers.currentRow()
        if row >= 0:
            offer = self._offers[row]
            if self.route.stops == (offer.source, offer.target):
                text += f'\n{goods_label(offer.good)}：买入 {offer.buy} → 卖出 {offer.sell}，单件毛利 {offer.profit} 克朗'
                quantity = self.quantity.value()
                text += f'\n{quantity} 件：采购 {offer.buy*quantity} → 回款 {offer.sell*quantity}，毛利 {offer.profit*quantity}；扣行程开销后 {offer.profit*quantity-expenses:.0f} 克朗'
        self.summary.setText(text)

    def _view_changed(self, index):
        self.canvas.trade_view = bool(index); self.canvas.make_image()

    def _layers_changed(self):
        self.canvas.roads = self.road_layer.isChecked(); self.canvas.facilities = self.site_layer.isChecked()
        self.canvas.regions = self.region_layer.isChecked(); self.canvas.update()

    def _label_size_changed(self, value):
        self.canvas.label_size = value; self.canvas.update()
        self.settings.set('worldmap_label_size', value)

    def export_route(self):
        if self.world is None or self.route is None:
            self.summary.setText('请先生成一条有效路线。'); return
        path, _ = QFileDialog.getSaveFileName(self, '导出跑商路线', self.world.seed+'-route.json', '路线 JSON (*.json)')
        if path:
            try:
                atomic_write_json(path, dict(schema=1, seed=self.world.seed, profile=self.world.profile,
                    stops=[town_label(self.world, i) for i in self.route.stops],
                    original_stops=[self.world.town_name(i) for i in self.route.stops], tiles=self.route.tiles,
                    estimated_hours=self.route.hours, road_only=self.road_only.isChecked(),
                    assumptions='白天基础速度；关系50；无事件、随从、起源或队伍修正；不含海运'))
                self.summary.setText('路线已导出：'+path)
            except OSError as error:
                self.summary.setText('导出失败：'+str(error))

    def shutdown(self):
        self._pending_seed = None
        self._pending_route = False
        for job in (self._job, self._route_job):
            if job is not None and job.isRunning():
                job.stop.set(); job.wait(3000)
