"""Searchable starting-trait choices; one rule per trait prevents contradictions."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.seedgen.traits import traits, validate_traits
from .theme import style_table


class SeedTraitDialog(QDialog):
    def __init__(self, required=(), excluded=(), match='all', parent=None):
        super().__init__(parent)
        self.setWindowTitle('开局人物特质')
        self.resize(720, 570)
        self.setMinimumSize(560, 420)
        layout = QVBoxLayout(self)
        description = QLabel('属性和特质由同一名兄弟满足；人数使用主界面的「至少满足人数」。\n'
                             '排除项只约束计入人数的兄弟，不限制其他队员。起源可能限制能出现的特质。')
        description.setWordWrap(True)
        layout.addWidget(description)
        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索特质名称、英文或说明，例如铁肺、巨人')
        controls.addWidget(self.search, 1)
        self.match = QComboBox()
        self.match.addItem('必选特质须全部具备', 'all')
        self.match.addItem('必选特质具备任意一项', 'any')
        self.match.setCurrentIndex(self.match.findData(match))
        controls.addWidget(self.match)
        layout.addLayout(controls)
        self.table = QTableWidget(0, 2)
        style_table(self.table)
        self.table.setHorizontalHeaderLabels(['人物特质（悬停查看说明）', '筛选要求'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 152)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.choices = {}
        self.search_text = []
        for row, item in enumerate(traits().values()):
            self.table.insertRow(row)
            name = item.name + ('（巨人）' if item.id == 'trait.huge' else '')
            label = QTableWidgetItem(f'{name} · {item.english}')
            label.setData(Qt.UserRole, item.id)
            label.setToolTip(item.description)
            self.table.setItem(row, 0, label)
            choice = QComboBox()
            for title, value in (('不限', 'ignore'), ('必须具备', 'required'), ('不能拥有', 'excluded')):
                choice.addItem(title, value)
            choice.setCurrentIndex(1 if item.id in required else 2 if item.id in excluded else 0)
            choice.setAccessibleName(name+'筛选要求')
            choice.setToolTip(item.description)
            self.table.setCellWidget(row, 1, choice)
            self.choices[item.id] = choice
            self.search_text.append(f'{name} {item.english} {item.id} {item.description}'.casefold())
        layout.addWidget(self.table, 1)
        self.error = QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset)
        self.buttons.button(QDialogButtonBox.Ok).setText('应用条件')
        self.buttons.button(QDialogButtonBox.Cancel).setText('取消')
        self.buttons.button(QDialogButtonBox.Reset).setText('清空条件')
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Reset).clicked.connect(self.clear)
        layout.addWidget(self.buttons)
        self.search.textChanged.connect(self._search)

    def _search(self, text):
        text = text.strip().casefold()
        for row, source in enumerate(self.search_text):
            self.table.setRowHidden(row, text not in source)

    def selection(self):
        required = [key for key, choice in self.choices.items() if choice.currentData() == 'required']
        excluded = [key for key, choice in self.choices.items() if choice.currentData() == 'excluded']
        match = self.match.currentData()
        required, excluded = validate_traits(required, excluded, match)
        return required, excluded, match

    def _accept(self):
        try:
            self.selection()
        except ValueError as error:
            self.error.setText(str(error))
            return
        self.accept()

    def clear(self):
        for choice in self.choices.values():
            choice.setCurrentIndex(0)
        self.match.setCurrentIndex(0)
        self.error.clear()
