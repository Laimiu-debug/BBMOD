"""Searchable offline equipment table, available without a game or reader MOD."""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)

from core.equipment_catalog import GROUPS, RARITIES, attributes, detail_html, load_equipment, load_equipment_icons, matches
from core.paths import resource_path
from .theme import icon, style_button, style_table


class StatCell(QTableWidgetItem):
    def __init__(self, attribute):
        super().__init__(attribute.display)
        self.sort_key = (attribute.sort_key is not None, attribute.sort_key or ())
        self.setTextAlignment(Qt.AlignCenter)
        self.setToolTip(f'基础值：{attribute.baseline}\n{attribute.rule}')

    def __lt__(self, other):
        return self.sort_key < other.sort_key


class EquipmentCatalog(QWidget):
    appraisal_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('equipmentCatalog')
        self.setStyleSheet('#equipmentCatalog QLabel#workspaceHint { color:#625033; }')
        document = load_equipment()
        self.game_version, self.items = document['game_version'], document['items']
        self.artwork = load_equipment_icons()['items']
        self.icons = {key: QIcon(str(resource_path('assets/equipment/' + art['small'])))
                      if art.get('small') else icon('book', '#958467', 40)
                      for key, art in self.artwork.items()}
        self.stats = {key: attributes(item) for key, item in self.items.items()}
        self._dialog = None
        root = QVBoxLayout(self)
        hint = QLabel('普通、传奇装备显示基础属性；红装显示抽中词条后的范围。双击装备可查看基础值、更多属性与随机规则。')
        hint.setObjectName('workspaceHint'); hint.setWordWrap(True); root.addWidget(hint)
        filters = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText('搜索装备中文名 / 英文名 / 类型')
        self.search.setClearButtonEnabled(True); self.search.setAccessibleName('搜索装备')
        self.group = QComboBox(); self.group.addItem('全部类型', '')
        for key, label in GROUPS.items(): self.group.addItem(label, key)
        self.group.setAccessibleName('装备类型')
        self.rarity = QComboBox(); self.rarity.addItem('全部品质', '')
        for key, label in RARITIES.items(): self.rarity.addItem(label, key)
        self.rarity.setAccessibleName('装备品质')
        self.reset = QPushButton('重置'); self.reset.clicked.connect(self.reset_filters)
        filters.addWidget(self.search, 1); filters.addWidget(self.group); filters.addWidget(self.rarity); filters.addWidget(self.reset)
        root.addLayout(filters)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(['装备名称', '类型', '品质', '伤害', '破甲效率', '穿甲效率', '护甲 / 耐久', '疲劳负担', '近战防御', '远程防御'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setWordWrap(False)
        self.table.setIconSize(QSize(36, 36))
        self.table.setMinimumHeight(220)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((245, 125, 90, 190, 132, 132, 145, 125, 115, 115)):
            self.table.setColumnWidth(column, width)
        style_table(self.table)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.table.itemDoubleClicked.connect(self.show_detail)
        self.table.itemActivated.connect(self.show_detail)
        root.addWidget(self.table, 1)
        footer = QHBoxLayout()
        self.count = QLabel(); self.count.setObjectName('workspaceHint'); self.count.setWordWrap(True)
        footer.addWidget(self.count, 1)
        self.detail_button = QPushButton('查看装备详情'); style_button(self.detail_button, 'book')
        self.detail_button.clicked.connect(self.show_detail); footer.addWidget(self.detail_button)
        root.addLayout(footer)
        self.search.textChanged.connect(self.refresh)
        self.group.currentIndexChanged.connect(self.refresh)
        self.rarity.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def selected_key(self):
        selected = self.table.selectionModel().selectedRows()
        return self.table.item(selected[0].row(), 0).data(Qt.UserRole) if selected else None

    def refresh(self, *_):
        current = self.selected_key()
        header = self.table.horizontalHeader()
        column, order = header.sortIndicatorSection(), header.sortIndicatorOrder()
        sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.clearSelection()
        filtered = [(key, item) for key, item in self.items.items()
                    if matches(item, self.search.text(), self.group.currentData(), self.rarity.currentData())]
        group = self.group.currentData()
        for index in range(3, 6): self.table.setColumnHidden(index, group in ('armor', 'helmet', 'shield'))
        for index in (8, 9): self.table.setColumnHidden(index, bool(group) and group != 'shield')
        self.table.setRowCount(len(filtered))
        for row, (key, item) in enumerate(filtered):
            for index, value in enumerate((item['zh'], GROUPS[item['group']], RARITIES[item['rarity']])):
                cell = QTableWidgetItem(value); cell.setData(Qt.UserRole, key)
                cell.setToolTip(item['zh'] + '\n' + item['en'] + '\n' + item['category'])
                if index == 0:
                    cell.setIcon(self.icons[key])
                    if self.artwork[key].get('reason'):
                        cell.setToolTip(cell.toolTip() + '\n' + self.artwork[key]['reason'])
                self.table.setItem(row, index, cell)
            for index, attribute in enumerate(self.stats[key][:7], 3):
                self.table.setItem(row, index, StatCell(attribute))
        self.table.setSortingEnabled(True)
        self.table.sortItems(column if sorting else 0, order if sorting else Qt.AscendingOrder)
        row = next((row for row in range(self.table.rowCount())
                    if self.table.item(row, 0).data(Qt.UserRole) == current), 0)
        if filtered: self.table.selectRow(row)
        self.selection_changed()
        self.count.setText((f'显示 {len(filtered)} / {len(self.items)} 条 · 原版 {self.game_version} · 可离线查阅'
                            if filtered else '没有匹配的装备，试试其他名称或重置筛选。'))

    def reset_filters(self):
        for control in (self.search, self.group, self.rarity): control.blockSignals(True)
        self.search.clear(); self.group.setCurrentIndex(0); self.rarity.setCurrentIndex(0)
        for control in (self.search, self.group, self.rarity): control.blockSignals(False)
        self.refresh()

    def selection_changed(self):
        self.detail_button.setEnabled(self.selected_key() is not None)

    def show_item(self, identifier):
        self.reset_filters()
        for row in range(self.table.rowCount()):
            cell = self.table.item(row, 0)
            if self.items[cell.data(Qt.UserRole)]['id'] == identifier:
                self.table.selectRow(row); self.table.scrollToItem(cell)
                return True
        return False

    def show_detail(self, *_):
        key = self.selected_key()
        if key is None: return
        if self._dialog is not None:
            self._dialog.raise_(); return
        item = self.items[key]
        dialog = QDialog(self); dialog.setWindowTitle(item['zh'] + ' · 装备详情')
        dialog.setAttribute(Qt.WA_DeleteOnClose); dialog.resize(880, 640)
        layout = QVBoxLayout(dialog)
        content = QTextBrowser(); content.setOpenExternalLinks(False)
        content.setHtml(detail_html(item, self.game_version, self.artwork[key])); layout.addWidget(content)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText('关闭')
        buttons.rejected.connect(dialog.reject)
        if item['rarity'] == 'named':
            inspect = buttons.addButton('打开装备鉴定', QDialogButtonBox.ActionRole)
            inspect.clicked.connect(lambda: (dialog.accept(), self.appraisal_requested.emit()))
        layout.addWidget(buttons)
        self._dialog = dialog
        dialog.finished.connect(self._detail_closed)
        dialog.open()

    def _detail_closed(self, *_):
        self._dialog = None
