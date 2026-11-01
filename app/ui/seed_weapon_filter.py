"""Independent total count and multiple named-weapon requirements."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QCompleter, QDialog, QDialogButtonBox, QHeaderView,
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSpinBox, QTableWidget,
    QVBoxLayout, QWidget,
)

from core.seedgen.weapon_rating import RATING_EXPLANATION
from core.seedgen.weapons import WEAPON_CHOICES, WeaponRequirement, weapon_filter_condition
from .readable_combo import ReadableComboBox as QComboBox


def number(low, high, value, name, suffix=''):
    widget = QSpinBox()
    widget.setObjectName(name)
    widget.setRange(low, high)
    widget.setValue(value)
    widget.setSuffix(suffix)
    return widget


class WeaponFilterRow:
    def __init__(self, values, changed):
        self.weapon = QComboBox()
        self.weapon.setObjectName('named_weapon')
        self.weapon.setEditable(True)
        self.weapon.setInsertPolicy(QComboBox.NoInsert)
        for key, label in WEAPON_CHOICES.items():
            self.weapon.addItem(label, key)
        self.weapon.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.weapon.completer().setFilterMode(Qt.MatchContains)
        self.weapon.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.weapon.setToolTip('可输入名称搜索；请从列表选择一种武器或武器类别。')
        self.count = number(1, 200, 1, 'named_weapon_count')
        self.damage = number(-1, 100, -1, 'named_damage_roll', '%')
        self.penetration = number(-1, 100, -1, 'named_penetration_roll', '%')
        self.score = number(-1, 100, -1, 'named_weapon_score')
        self.quality = number(-1, 100, -1, 'named_weapon_quality', '%')
        self.remove = QPushButton('移除')
        self.remove.setObjectName('remove_weapon_requirement')
        self.weapon.setAccessibleName('武器类型')
        self.count.setAccessibleName('武器至少件数')
        for widget, label in ((self.damage, '伤害品质至少'), (self.penetration, '穿甲品质至少'),
                              (self.score, '实用词条评分至少'), (self.quality, 'roll 品质至少')):
            widget.setSpecialValueText('不限')
            widget.setAccessibleName(label)
        for widget in (self.damage, self.penetration):
            widget.setToolTip('0% 也要求抽中该词条；不限则不要求。100% 为该词条的满随机值。')
        self.score.setToolTip('伤穿优先 v1，0–100 分；与本行伤害、穿甲和 roll 门槛由同一件武器同时满足。详见评分说明。')
        self.quality.setToolTip('已抽中两条词条的品质平均值；疲劳减负越多越好。记录不足的武器不通过评分门槛。')
        values = values if isinstance(values, dict) else {}
        index = self.weapon.findData(values.get('weapon'))
        if index >= 0:
            self.weapon.setCurrentIndex(index)
        for key in ('count', 'damage', 'penetration', 'score', 'quality'):
            widget, value = getattr(self, key), values.get(key)
            if type(value) is int and widget.minimum() <= value <= widget.maximum():
                widget.setValue(value)
            widget.valueChanged.connect(changed)
        self.weapon.currentIndexChanged.connect(changed)
        self.weapon.lineEdit().editingFinished.connect(changed)

    def values(self):
        index = self.weapon.currentIndex()
        if index < 0 or self.weapon.currentText() != self.weapon.itemText(index):
            index = self.weapon.findText(self.weapon.currentText(), Qt.MatchFixedString)
        return {'weapon': self.weapon.itemData(index) if index >= 0 else '',
                **{key: getattr(self, key).value()
                   for key in ('count', 'damage', 'penetration', 'score', 'quality')}}

    def requirement(self):
        values = self.values()
        return WeaponRequirement(values['weapon'], values['count'],
                                 *[values[key] if values[key] >= 0 else None
                                   for key in ('damage', 'penetration', 'score', 'quality')])


class SeedWeaponFilter(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings, self.rows, self._restoring = settings, [], True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 4)
        layout.setSpacing(6)
        total_row = QHBoxLayout()
        self.total_enabled = QCheckBox('红装总数至少')
        self.total_enabled.setObjectName('named_total_enabled')
        self.total = number(1, 200, 20, 'named_total', ' 件')
        self.total_enabled.setToolTip('包含营地里的红甲、红盔、红盾和红武；可与下面的武器要求同时启用。')
        total_row.addWidget(self.total_enabled)
        total_row.addWidget(self.total)
        self.explain = QPushButton('评分说明')
        self.explain.clicked.connect(self._explanation)
        weapon_row = total_row
        self.weapons_enabled = QCheckBox('武器要求')
        self.weapons_enabled.setObjectName('named_weapons_enabled')
        self.match = QComboBox()
        self.match.setObjectName('named_weapons_match')
        self.match.addItem('全部满足', 'all')
        self.match.addItem('任一满足', 'any')
        weapon_row.addWidget(self.weapons_enabled)
        weapon_row.addWidget(self.match)
        weapon_row.addStretch()
        self.add = QPushButton('+ 添加武器要求')
        self.add.setObjectName('add_weapon_requirement')
        self.add.clicked.connect(lambda: self.add_requirement())
        weapon_row.addWidget(self.add)
        weapon_row.addWidget(self.explain)
        layout.addLayout(weapon_row)
        self.table = QTableWidget(0, 7)
        self.table.setObjectName('named_weapon_requirements')
        self.table.setProperty('compactHeaders', True)
        self.table.setHorizontalHeaderLabels(['武器类型（可搜索）', '件数 ≥', '伤害 ≥', '穿甲 ≥', '实用分 ≥', 'roll ≥', ''])
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setMinimumHeight(90)
        self.table.setMaximumHeight(180)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(54)
        for column in range(1, 7):
            self.table.setColumnWidth(column, 74 if column == 1 else 78 if column == 6 else 90)
        self.table.horizontalHeaderItem(4).setToolTip('实用词条评分（伤穿优先 v1），0–100 分')
        self.table.horizontalHeaderItem(5).setToolTip('两条词条品质的平均值，0–100%')
        layout.addWidget(self.table)
        self.hint = QLabel()
        self.hint.setObjectName('muted')
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        layout.addStretch()
        self._restore(settings.get('seed_lair_filter', {}))
        self._restoring = False
        for widget in (self.total_enabled, self.weapons_enabled):
            widget.toggled.connect(self._changed)
        self.total.valueChanged.connect(self._changed)
        self.match.currentIndexChanged.connect(self._changed)
        self._refresh()

    def add_requirement(self, values=None):
        if len(self.rows) >= 20:
            return
        row = WeaponFilterRow(values, self._changed)
        index = len(self.rows)
        self.rows.append(row)
        self.table.insertRow(index)
        for column, widget in enumerate((row.weapon, row.count, row.damage, row.penetration,
                                          row.score, row.quality, row.remove)):
            self.table.setCellWidget(index, column, widget)
        row.remove.clicked.connect(lambda: self._remove(row))
        self._changed()
        self.table.scrollToBottom()
        return row

    def _remove(self, row):
        if len(self.rows) <= 1:
            return
        index = self.rows.index(row)
        self.rows.pop(index)
        self.table.removeRow(index)
        self._changed()

    def _restore(self, values):
        values = values if isinstance(values, dict) else {}
        modern = values.get('version') == 2
        self.total_enabled.setChecked(values.get('total_enabled', True) is True if modern
                                      else values.get('kind') != 'weapon')
        self.weapons_enabled.setChecked(values.get('weapons_enabled') is True if modern
                                        else values.get('kind') == 'weapon')
        total = values.get('total')
        if type(total) is int and 1 <= total <= 200:
            self.total.setValue(total)
        if values.get('match') == 'any':
            self.match.setCurrentIndex(1)
        rows = values.get('rows') if modern else [values]
        if not isinstance(rows, list) or not rows:
            rows = [{}]
        for row in rows[:20]:
            self.add_requirement(row)

    def _refresh(self):
        enabled = self.weapons_enabled.isChecked()
        self.total.setEnabled(self.total_enabled.isChecked())
        self.table.setVisible(enabled)
        self.match.setEnabled(enabled)
        self.add.setEnabled(enabled and len(self.rows) < 20)
        for row in self.rows:
            row.remove.setEnabled(len(self.rows) > 1)
        if enabled:
            text = ('各行是独立数量，同一件武器不重复计数。' if self.match.currentData() == 'all'
                    else '满足任意一行的数量及门槛即可。')
            self.hint.setText(('总数也须满足；' if self.total_enabled.isChecked() else '') + text
                              + '不限项不参与筛选。')
            self.hint.setToolTip('每件须同时满足本行所有门槛；评分支持原版 50 种红武。')
        else:
            self.hint.setText('勾选“武器要求”可添加多种红武，并与红装总数同时筛选。'
                              if self.total_enabled.isChecked() else '请至少启用一项筛选条件。')

    def _changed(self, *_):
        if self._restoring:
            return
        self._refresh()
        self.settings.set('seed_lair_filter', {
            'version': 2, 'total_enabled': self.total_enabled.isChecked(),
            'weapons_enabled': self.weapons_enabled.isChecked(), 'total': self.total.value(),
            'match': self.match.currentData(), 'rows': [row.values() for row in self.rows],
        })

    def conditions(self):
        requirements = [row.requirement() for row in self.rows] if self.weapons_enabled.isChecked() else []
        return [weapon_filter_condition(requirements, self.total.value() if self.total_enabled.isChecked() else 0,
                                        self.match.currentData())]

    def _explanation(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('红武评分与组合筛选说明')
        dialog.resize(680, 510)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit(RATING_EXPLANATION)
        text.setReadOnly(True)
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()
