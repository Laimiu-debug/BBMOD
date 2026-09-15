"""MOD 管理页：已安装列表（启停/卸载/顺序）+ 仓库（分类安装）+ profile。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from core.modinfo import CATEGORY_LABELS, analyze_zip
from .app_context import AppContext
from .workers import Worker


class ModsPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self._installed_infos: dict[str, object] = {}

        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_installed_tab(), "已安装（游戏 data 目录）")
        tabs.addTab(self._build_repo_tab(), "仓库（内置合集 / 外部导入）")
        root.addWidget(tabs, 1)

    # ---------------- 已安装 ----------------

    def _build_installed_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新")
        self.disable_btn = QPushButton("禁用")
        self.enable_btn = QPushButton("启用")
        self.uninstall_btn = QPushButton("卸载")
        self.open_dir_btn = QPushButton("打开 data 目录")
        self.save_profile_btn = QPushButton("保存为方案")
        self.apply_profile_btn = QPushButton("应用方案")
        for b, fn in (
            (self.refresh_btn, self.refresh),
            (self.disable_btn, lambda: self._on_disable(False)),
            (self.enable_btn, lambda: self._on_disable(True)),
            (self.uninstall_btn, self.uninstall),
            (self.open_dir_btn, self._open_dir),
            (self.save_profile_btn, self.save_profile),
            (self.apply_profile_btn, self.apply_profile),
        ):
            b.clicked.connect(fn)
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        self.status_label = QLabel("—")
        lay.addLayout(toolbar)
        lay.addWidget(self.status_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["状态", "文件名", "Mod ID / 名称", "API", "影响种子"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(1, 340)
        lay.addWidget(self.table, 1)
        return w

    def refresh(self) -> None:
        mm = self.ctx.mm
        if not mm:
            return
        mods = mm.scan()
        self.table.setRowCount(len(mods))
        self._installed_infos.clear()
        for i, m in enumerate(mods):
            self._installed_infos[m.path.name] = m.info
            state = QTableWidgetItem("已启用" if m.enabled else "已禁用")
            state.setForeground(Qt.green if m.enabled else Qt.gray)
            ids = ", ".join(f"{r.mod_id} v{r.version}" for r in m.info.registrations) or "（未注册/纯覆盖）"
            seed = "⚠ 是" if m.info.seed_sensitive_paths else ""
            self.table.setItem(i, 0, state)
            self.table.setItem(i, 1, QTableWidgetItem(m.path.name))
            self.table.setItem(i, 2, QTableWidgetItem(ids))
            self.table.setItem(i, 3, QTableWidgetItem(m.info.api))
            seed_item = QTableWidgetItem(seed)
            if seed:
                seed_item.setForeground(Qt.red)
            self.table.setItem(i, 4, seed_item)
        enabled = sum(1 for m in mods if m.enabled)
        self.status_label.setText(f"共 {len(mods)} 个：启用 {enabled} · 禁用 {len(mods) - enabled}（挂载顺序即文件名排序）")

    def _selected_name(self) -> str | None:
        sel = self.table.selectedItems()
        if not sel:
            return None
        return self.table.item(sel[0].row(), 1).text()

    def _on_disable(self, enable: bool) -> None:
        name = self._selected_name()
        if not name:
            return
        try:
            if enable:
                self.ctx.mm.enable(name)
            else:
                self.ctx.mm.disable(name)
        except (FileNotFoundError, OSError) as e:
            QMessageBox.warning(self, "操作失败", str(e))
        self.refresh()
        self.ctx.data_changed.emit()

    def uninstall(self) -> None:
        name = self._selected_name()
        if not name:
            return
        if QMessageBox.question(self, "卸载", f"卸载 {name}？\n（移入 bbmod_disabled，可随时彻底删除）") != QMessageBox.Yes:
            return
        try:
            self.ctx.mm.uninstall(name)
        except (FileNotFoundError, OSError) as e:
            QMessageBox.warning(self, "操作失败", str(e))
        self.refresh()
        self.ctx.data_changed.emit()

    def _open_dir(self) -> None:
        from core import game as game_mod
        if self.ctx.game:
            game_mod.open_folder(self.ctx.game.data_dir)

    def save_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "保存方案", "方案名称：")
        if ok and name.strip():
            self.ctx.mm.save_profile(name.strip())
            self.status_label.setText(f"已保存方案「{name.strip()}」")

    def apply_profile(self) -> None:
        profiles = self.ctx.mm.load_profiles()
        if not profiles:
            QMessageBox.information(self, "应用方案", "还没有保存过方案")
            return
        name, ok = QInputDialog.getItem(self, "应用方案", "选择方案：", list(profiles), 0, False)
        if ok:
            try:
                en, dis = self.ctx.mm.apply_profile(name)
            except (KeyError, OSError) as e:
                QMessageBox.warning(self, "应用失败", str(e))
            else:
                self.status_label.setText(f"已应用「{name}」：启用 {en} · 禁用 {dis}")
                self.refresh()
                self.ctx.data_changed.emit()

    # ---------------- 仓库 ----------------

    def _build_repo_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        toolbar = QHBoxLayout()
        self.repo_refresh_btn = QPushButton("刷新仓库")
        self.import_btn = QPushButton("导入外部文件夹…")
        self.install_btn = QPushButton("安装所选")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索 mod 名称/文件名…")
        self.repo_refresh_btn.clicked.connect(self.refresh_repo)
        self.import_btn.clicked.connect(self.import_root)
        self.install_btn.clicked.connect(self.install_selected)
        self.search_edit.textChanged.connect(self._filter_repo)
        toolbar.addWidget(self.repo_refresh_btn)
        toolbar.addWidget(self.import_btn)
        toolbar.addWidget(self.install_btn)
        toolbar.addWidget(self.search_edit, 1)
        lay.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        self.cat_list = QListWidget()
        self.cat_list.currentItemChanged.connect(lambda *_: self._filter_repo())
        splitter.addWidget(self.cat_list)
        self.repo_table = QTableWidget(0, 4)
        self.repo_table.setHorizontalHeaderLabels(["名称", "文件名", "分类", "说明"])
        self.repo_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.repo_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.repo_table.setColumnWidth(1, 340)
        splitter.addWidget(self.repo_table)
        splitter.setSizes([160, 700])
        lay.addWidget(splitter, 1)
        self.repo_status = QLabel("—")
        lay.addWidget(self.repo_status)
        return w

    def refresh_repo(self) -> None:
        def scan():
            return self.ctx.store().scan()

        self._repo_worker = Worker(scan, self)
        self._repo_worker.done.connect(self._show_repo)
        self._repo_worker.failed.connect(lambda e: self.repo_status.setText(f"仓库扫描失败：{e}"))
        self._repo_worker.start()

    def _show_repo(self, entries: list) -> None:
        self._repo_entries = entries
        cats = {"全部"}
        for e in entries:
            cats.add(e.category)
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        self.cat_list.addItem("全部")
        for c in sorted(cats - {"全部"}):
            self.cat_list.addItem(c)
        self.cat_list.blockSignals(False)
        self._filter_repo()
        self.repo_status.setText(f"仓库共 {len(entries)} 个 mod（含分类：{'、'.join(sorted(cats - {'全部'}))}）")

    def _filter_repo(self) -> None:
        entries = getattr(self, "_repo_entries", [])
        cat = self.cat_list.currentItem().text() if self.cat_list.currentItem() else "全部"
        kw = self.search_edit.text().strip().lower()
        rows = [
            e for e in entries
            if (cat == "全部" or e.category == cat)
            and (not kw or kw in e.display_name.lower() or kw in e.info.file_name.lower())
        ]
        installed = self.ctx.mm.installed_zip_names() if self.ctx.mm else set()
        self.repo_table.setRowCount(len(rows))
        for i, e in enumerate(rows):
            mark = "（已装）" if e.info.file_name in installed else ""
            self.repo_table.setItem(i, 0, QTableWidgetItem(e.display_name + mark))
            self.repo_table.setItem(i, 1, QTableWidgetItem(e.info.file_name))
            self.repo_table.setItem(i, 2, QTableWidgetItem(e.category))
            note = e.note
            if e.info.requirements:
                note = (note + "；" if note else "") + "依赖：" + "、".join(e.info.requirements)
            self.repo_table.setItem(i, 3, QTableWidgetItem(note))

    def import_root(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择包含 mod zip 的文件夹")
        if d:
            roots = self.ctx.settings.get("extra_repo_roots", [])
            if d not in roots:
                roots.append(d)
                self.ctx.settings.set("extra_repo_roots", roots)
            self.refresh_repo()

    def install_selected(self) -> None:
        rows = {idx.row() for idx in self.repo_table.selectedIndexes()}
        if not rows:
            QMessageBox.information(self, "安装", "先在列表中选择要安装的 mod（可多选）")
            return
        names = [self.repo_table.item(r, 1).text() for r in sorted(rows)]
        store = self.ctx.store()
        ok_count = 0
        messages = []
        for entry in store.scan():
            if entry.info.file_name not in names:
                continue
            try:
                self.ctx.mm.install(entry.info.path)
                ok_count += 1
            except (FileExistsError, OSError) as e:
                messages.append(f"{entry.info.file_name}: {e}")
        if messages:
            QMessageBox.warning(self, "部分失败", "\n".join(messages))
        self.repo_status.setText(f"已安装 {ok_count} 个")
        self.refresh()
        self.refresh_repo()
        self.ctx.data_changed.emit()
