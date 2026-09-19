"""Compact camp-loot filters, with independent total and weapon criteria."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QSpinBox, QStackedWidget, QWidget

from core.seedgen.weapons import WEAPON_CHOICES, weapon_condition


def number(low, high, value, name, suffix=''):
    widget = QSpinBox()
    widget.setObjectName(name)
    widget.setRange(low, high)
    widget.setValue(value)
    widget.setSuffix(suffix)
    return widget


class SeedWeaponFilter(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        layout = QGridLayout(self)
        layout.setContentsMargins(8, 6, 8, 4)
        layout.setSpacing(6)
        self.kind = QComboBox()
        self.kind.setObjectName('lair_filter_kind')
        self.kind.addItem('红装总数', 'total')
        self.kind.addItem('指定红武器', 'weapon')
        self.stack = QStackedWidget()
        total = QWidget()
        total_layout = QGridLayout(total)
        total_layout.setContentsMargins(0, 0, 0, 0)
        self.total = number(1, 200, 20, 'named_total', ' 件')
        total_layout.addWidget(QLabel('全地图红装至少'), 0, 0)
        total_layout.addWidget(self.total, 0, 1)
        total_layout.setColumnStretch(2, 1)
        self.stack.addWidget(total)
        weapon = QWidget()
        grid = QGridLayout(weapon)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(4)
        self.weapon = QComboBox()
        self.weapon.setObjectName('named_weapon')
        self.weapon.setMaxVisibleItems(12)
        for key, label in WEAPON_CHOICES.items():
            self.weapon.addItem(label, key)
        self.count = number(1, 200, 1, 'named_weapon_count', ' 件')
        self.damage = number(-1, 100, -1, 'named_damage_roll', '%')
        self.penetration = number(-1, 100, -1, 'named_penetration_roll', '%')
        for widget in (self.damage, self.penetration):
            widget.setSpecialValueText('不限')
            widget.setToolTip('0% 也要求出现该加成；不限则不要求该加成。100% 为该加成的满随机值。')
        grid.addWidget(QLabel('武器类型'), 0, 0)
        grid.addWidget(self.weapon, 0, 1)
        grid.addWidget(QLabel('至少'), 0, 2)
        grid.addWidget(self.count, 0, 3)
        grid.addWidget(QLabel('伤害品质 ≥'), 1, 0)
        grid.addWidget(self.damage, 1, 1)
        grid.addWidget(QLabel('穿甲品质 ≥'), 1, 2)
        grid.addWidget(self.penetration, 1, 3)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(3, 1)
        self.stack.addWidget(weapon)
        layout.addWidget(self.kind, 0, 0, Qt.AlignTop)
        layout.addWidget(self.stack, 0, 1)
        layout.setColumnStretch(1, 1)
        self._restore(settings.get('seed_lair_filter', {}))
        self.kind.currentIndexChanged.connect(self._changed)
        self.weapon.currentIndexChanged.connect(self._changed)
        for widget in (self.total, self.count, self.damage, self.penetration):
            widget.valueChanged.connect(self._changed)
        self._refresh()

    def _restore(self, values):
        if not isinstance(values, dict):
            return
        for widget, key in ((self.kind, 'kind'), (self.weapon, 'weapon')):
            index = widget.findData(values.get(key))
            if index >= 0:
                widget.setCurrentIndex(index)
        for widget, key in ((self.total, 'total'), (self.count, 'count'),
                            (self.damage, 'damage'), (self.penetration, 'penetration')):
            value = values.get(key)
            if type(value) is int and widget.minimum() <= value <= widget.maximum():
                widget.setValue(value)

    def _refresh(self):
        by_weapon = self.kind.currentData() == 'weapon'
        self.stack.setCurrentIndex(1 if by_weapon else 0)
        self.kind.setToolTip(
            '统计生成时营地中的红武器，每件须同时满足所选品质。100% 为该加成的满随机值；位置和属性见结果详情。'
            if by_weapon else '统计生成时营地中的全部红装，位置可在结果详情的营地记录里核对。')

    def _changed(self, *_):
        self._refresh()
        self.settings.set('seed_lair_filter', {
            'kind': self.kind.currentData(), 'weapon': self.weapon.currentData(),
            'total': self.total.value(), 'count': self.count.value(),
            'damage': self.damage.value(), 'penetration': self.penetration.value(),
        })

    def conditions(self):
        if self.kind.currentData() == 'total':
            return [['NamedNumber', self.total.value()]]
        return [weapon_condition(self.weapon.currentData(), self.count.value(),
                                 self.damage.value() if self.damage.value() >= 0 else None,
                                 self.penetration.value() if self.penetration.value() >= 0 else None)]
