"""Total stars and per-attribute talent positions for the same brother."""
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QVBoxLayout,
)

from core.seedgen.config_emitter import ATTRIBUTES
from core.seedgen.stars import validate_star_filters


class SeedStarDialog(QDialog):
    def __init__(self, total_min=0, total_max=24, star_ranges=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('总星数与星位分配')
        self.resize(520, 510)
        layout = QVBoxLayout(self)
        hint = QLabel('总星数、星位、属性和特质均由同一名兄弟满足。\n'
                      '9星只表示总数；可另设近战3星、近防3星、疲劳3星等星位。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        row = QHBoxLayout()
        row.addWidget(QLabel('总星数'))
        self.total_mode = QComboBox()
        for title, key in (('不限', 'any'), ('至少', 'min'), ('恰好', 'exact')):
            self.total_mode.addItem(title, key)
        self.total = QSpinBox()
        self.total.setRange(0, 24)
        self.total.setSuffix(' 星')
        self.total.setValue(total_min)
        self.total_mode.setCurrentIndex(2 if total_min == total_max else 1 if total_min else 0)
        row.addWidget(self.total_mode)
        row.addWidget(self.total)
        nine = QPushButton('9星大哥')
        nine.clicked.connect(self._nine)
        row.addWidget(nine)
        layout.addLayout(row)
        form = QFormLayout()
        self.choices = {}
        for key, label in ATTRIBUTES.items():
            choice = QComboBox()
            choice.addItem('不限', (0, 3))
            for value in (1, 2):
                choice.addItem(f'至少 {value} 星', (value, 3))
            for value in range(4):
                choice.addItem(f'恰好 {value} 星', (value, value))
            bounds = tuple((star_ranges or {}).get(key, (0, 3)))
            for index in range(choice.count()):
                if tuple(choice.itemData(index)) == bounds:
                    choice.setCurrentIndex(index)
                    break
            choice.setAccessibleName(label + '星位')
            self.choices[key] = choice
            form.addRow(label, choice)
        layout.addLayout(form)
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
        self.total_mode.currentIndexChanged.connect(self._mode_changed)
        self._mode_changed()

    def _mode_changed(self, *_):
        self.total.setEnabled(self.total_mode.currentData() != 'any')

    def _nine(self):
        self.total_mode.setCurrentIndex(2)
        self.total.setValue(9)

    def clear(self):
        self.total_mode.setCurrentIndex(0)
        self.total.setValue(0)
        for choice in self.choices.values():
            choice.setCurrentIndex(0)
        self.error.clear()

    def selection(self):
        mode = self.total_mode.currentData()
        low = self.total.value() if mode != 'any' else 0
        high = low if mode == 'exact' else 24
        ranges = {key: choice.currentData() for key, choice in self.choices.items()}
        return low, high, validate_star_filters(low, high, ranges)

    def _accept(self):
        try:
            self.selection()
        except ValueError as error:
            self.error.setText(str(error))
            return
        self.accept()
