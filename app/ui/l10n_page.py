"""一键汉化页：状态检测 + 翻译表编辑器（搜索/覆盖）+ 构建/安装/卸载自有汉化包。"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import l10n
from core.modmanager import ModManager
from .app_context import AppContext
from .workers import Worker

OVERRIDES_FILE = "l10n_overrides.json"


class L10nPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.entries: list[l10n.StringEntry] = []
        self.overrides: dict[str, dict[str, str]] = self._load_overrides()
        self._loading = False

        root = QVBoxLayout(self)

        # 状态 + 操作
        status_box = QGroupBox("汉化状态")
        sl = QHBoxLayout(status_box)
        self.status_label = QLabel("检测中…")
        sl.addWidget(self.status_label, 1)
        self.refresh_btn = QPushButton("重新检测")
        self.uninstall_btn = QPushButton("卸载汉化")
        self.refresh_btn.clicked.connect(self.refresh_status)
        self.uninstall_btn.clicked.connect(self.uninstall)
        sl.addWidget(self.refresh_btn)
        sl.addWidget(self.uninstall_btn)
        self.pick_ref_btn = QPushButton("选择参考语料包…")
        self.pick_ref_btn.clicked.connect(self.pick_reference)
        sl.addWidget(self.pick_ref_btn)
        root.addWidget(status_box)

        # 翻译表
        editor_box = QGroupBox("翻译表（语料来自参考包，可直接修改生成我们自己的版本）")
        el = QVBoxLayout(editor_box)
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索中文文本 / 文件名…")
        self.search.textChanged.connect(self._filter)
        self.build_btn = QPushButton("构建汉化包并安装")
        self.build_btn.clicked.connect(self.build_and_install)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.build_btn)
        el.addLayout(bar)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["文件", "字段", "文本（双击修改 = 覆盖）", "状态"])
        self.table.setColumnWidth(0, 360)
        self.table.setColumnWidth(1, 110)
        self.table.horizontalHeader().stretchLastSection()
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.itemChanged.connect(self._on_edit)
        el.addWidget(self.table, 1)
        self.count_label = QLabel("—")
        el.addWidget(self.count_label)
        root.addWidget(editor_box, 1)

    # ---------------- 覆盖持久化 ----------------

    def _overrides_path(self) -> Path:
        return self.ctx.settings.path.parent / OVERRIDES_FILE

    def _load_overrides(self) -> dict:
        try:
            return json.loads(self._overrides_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_overrides(self) -> None:
        p = self._overrides_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.overrides, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------------- 状态 ----------------

    def refresh_status(self) -> None:
        if not self.ctx.game:
            self.status_label.setText("未找到游戏")
            return
        found = l10n.find_localization_zips(self.ctx.game.data_dir)
        if not found:
            self.status_label.setText("未安装任何汉化（点击下方「构建汉化包并安装」一键完成）")
        else:
            parts = []
            for f in found:
                kind = "BBMOD 自有汉化" if l10n.is_bbmod_l10n(f) else "参考汉化包（第三方）"
                parts.append(f"{f.name} —— {kind}")
            self.status_label.setText("已安装：\n" + "\n".join(parts))

        ref = self.ctx.fox_reference_zip
        if not ref:
            self.count_label.setText(
                "未找到参考语料包（data狐狸汉化*.zip）。请将包含它的合集文件夹与本软件放在一起，"
                "或点「选择参考语料包…」手动指定。"
            )
            self.build_btn.setEnabled(False)
            return
        self.build_btn.setEnabled(True)

        def extract():
            return l10n.extract_strings(ref)

        self._extract_worker = Worker(extract, self)
        self._extract_worker.done.connect(self._show_entries)
        self._extract_worker.failed.connect(lambda e: self.count_label.setText(f"语料读取失败：{e}"))
        self._extract_worker.start()

    def pick_reference(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "选择参考汉化包（data狐狸汉化*.zip）", "", "ZIP (*.zip)")
        if f:
            self.ctx.settings.set("fox_reference_zip", f)
            self.refresh_status()

    def _show_entries(self, entries: list) -> None:
        self.entries = entries
        self._filter()

    def _filter(self) -> None:
        self._loading = True
        try:
            kw = self.search.text().strip().lower()
            rows = [e for e in self.entries if not kw or kw in e.value.lower() or kw in e.file.lower()]
            self.table.setRowCount(min(len(rows), 800))
            for i, e in enumerate(rows[:800]):
                self.table.setItem(i, 0, QTableWidgetItem(e.file))
                self.table.setItem(i, 1, QTableWidgetItem(e.key))
                overridden = self.overrides.get(e.file, {}).get(e.key)
                item = QTableWidgetItem(overridden if overridden is not None else e.value)
                if overridden is not None:
                    item.setForeground(Qt.darkYellow)
                self.table.setItem(i, 2, item)
                state = QTableWidgetItem("已覆盖" if overridden is not None else "")
                if overridden is not None:
                    state.setForeground(Qt.darkYellow)
                self.table.setItem(i, 3, state)
            self.count_label.setText(
                f"共 {len(self.entries)} 条语料，当前显示 {min(len(rows), 800)} 条"
                f"（仅前 800 条，用搜索缩小范围）· 覆盖 {sum(len(v) for v in self.overrides.values())} 条"
            )
        finally:
            self._loading = False

    def _on_edit(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 2 or not self.entries:
            return
        row = item.row()
        if row >= len(self.entries):
            return
        e = self.entries[row]
        new = item.text()
        if new == e.value:
            self.overrides.get(e.file, {}).pop(e.key, None)
            if e.file in self.overrides and not self.overrides[e.file]:
                del self.overrides[e.file]
        else:
            self.overrides.setdefault(e.file, {})[e.key] = new
        self._save_overrides()
        state_item = self.table.item(row, 3)
        if state_item is not None:
            state_item.setText("已覆盖" if item.text() != e.value else "")
            state_item.setForeground(Qt.darkYellow)

    # ---------------- 构建 / 安装 / 卸载 ----------------

    def build_and_install(self) -> None:
        ref = self.ctx.fox_reference_zip
        if not ref or not ref.exists():
            QMessageBox.warning(self, "缺少语料", "参考语料包不存在，请点「选择参考语料包…」指定")
            return
        out = self.ctx.settings.path.parent / f"{l10n.OUTPUT_PREFIX}_{Path(ref.stem).stem}.zip"

        def build():
            result = l10n.build_localization(
                ref, self.overrides, out, brand_note="BBMOD 管理器构建",
                source_note=Path(ref).name,
            )
            # 安装前先移除现有汉化（同目录多份会互相遮蔽）
            if self.ctx.game:
                for f in l10n.find_localization_zips(self.ctx.game.data_dir):
                    self.ctx.mm.disable(f.name)
            written = self.ctx.mm.install(out, overwrite=True)
            return result, written

        self._build_worker = Worker(build, self)
        self._build_worker.done.connect(self._after_build)
        self._build_worker.failed.connect(lambda e: QMessageBox.warning(self, "构建失败", str(e)))
        self._build_worker.start()
        self.build_btn.setEnabled(False)

    def _after_build(self, payload) -> None:
        result, written = payload
        self.build_btn.setEnabled(True)
        QMessageBox.information(
            self, "完成",
            f"已构建并安装自有汉化包：\n{result['out']}\n"
            f"条目 {result['entries']} · 应用覆盖 {result['applied']} 条"
            + (f"\n未命中 {len(result['missing'])} 条" if result["missing"] else ""),
        )
        self.refresh_status()
        self.ctx.data_changed.emit()

    def uninstall(self) -> None:
        found = l10n.find_localization_zips(self.ctx.game.data_dir) if self.ctx.game else []
        if not found:
            QMessageBox.information(self, "卸载汉化", "当前没有安装汉化")
            return
        for f in found:
            try:
                self.ctx.mm.uninstall(f.name)
            except (FileNotFoundError, OSError) as e:
                QMessageBox.warning(self, "卸载失败", f"{f.name}: {e}")
        self.refresh_status()
        self.ctx.data_changed.emit()
