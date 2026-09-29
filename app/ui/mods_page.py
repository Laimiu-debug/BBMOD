"""MOD 管理页：已安装列表（启停/卸载/顺序）+ 仓库（分类安装）+ profile。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from core.modinfo import CATEGORY_LABELS, analyze_zip
from .app_context import AppContext
from .workers import Worker
from .theme import GREEN, MUTED, style_button, style_table
from PySide6.QtGui import QColor


class ModsPage(QWidget):
    choose_game_requested = Signal()
    profiles_requested = Signal(bool)
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self._installed_infos: dict[str, object] = {}

        root = QVBoxLayout(self)
        tabs = self.sections = QTabWidget()
        tabs.addTab(self._build_installed_tab(), "已安装（启用 / 禁用）")
        tabs.addTab(self._build_repo_tab(), "仓库（内置合集 / 外部导入）")
        from .online_mods import OnlineModsPage
        self.online = OnlineModsPage(ctx, self._can_modify, self)
        tabs.addTab(self.online, "在线军械库")
        from .profile_sharing import ProfileSharing
        self.sharing = ProfileSharing(self)
        root.addWidget(tabs, 1)
        ctx.management_changed.connect(self.update_controls)
        ctx.session_changed.connect(self.update_controls)
        self.update_controls()

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
        self.share_profile_btn = QPushButton('分享方案')
        self.import_profile_btn = QPushButton('导入共享方案')
        self.manage_profiles_btn = QPushButton('方案管理')
        self.disable_btn.setToolTip('保留安装文件，暂停加载，之后可重新启用。')
        self.uninstall_btn.setToolTip('删除安装文件并移出已安装列表，再次使用需重新安装。')
        for button, glyph in ((self.refresh_btn, "refresh"), (self.disable_btn, "stop"),
                (self.enable_btn, "play"), (self.uninstall_btn, "close"),
                (self.open_dir_btn, "folder"), (self.save_profile_btn, "save"),
                (self.apply_profile_btn, "check")):
            style_button(button, glyph)
        for b, fn in (
            (self.refresh_btn, self.refresh),
            (self.disable_btn, lambda: self._on_disable(False)),
            (self.enable_btn, lambda: self._on_disable(True)),
            (self.uninstall_btn, self.uninstall),
            (self.open_dir_btn, self._open_dir),
        ):
            b.clicked.connect(fn)
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        self.status_label = QLabel("—")
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.PlainText)
        lay.addLayout(toolbar)
        profile_bar = QHBoxLayout()
        for button, callback in ((self.save_profile_btn, self.save_profile),
                (self.apply_profile_btn, self.apply_profile),
                (self.share_profile_btn, lambda: self.sharing.share()),
                (self.import_profile_btn, lambda: self.profiles_requested.emit(True)),
                (self.manage_profiles_btn, lambda: self.profiles_requested.emit(False))):
            button.clicked.connect(callback)
            profile_bar.addWidget(button)
        self.share_profile_btn.setToolTip('分享保存的 MOD 组合，只上传网站缺失的文件。')
        self.import_profile_btn.setToolTip('浏览网站现有方案，选择后预览并应用；也支持链接导入。')
        style_button(self.share_profile_btn, 'save')
        style_button(self.import_profile_btn, 'download')
        profile_bar.addStretch(1)
        lay.addLayout(profile_bar)
        lay.addWidget(self.status_label)

        filters = QHBoxLayout()
        self.installed_search = QLineEdit()
        self.installed_search.setPlaceholderText('搜索已安装 MOD 名称、文件名或 ID…')
        self.state_filter = QComboBox()
        self.state_filter.addItems(['全部状态', '已启用', '已禁用'])
        self.recover_btn = QPushButton('恢复上次操作')
        self.recover_btn.clicked.connect(self.recover)
        filters.addWidget(self.installed_search, 1)
        filters.addWidget(self.state_filter)
        filters.addWidget(self.recover_btn)
        lay.addLayout(filters)
        self.empty_box = QWidget()
        empty = QHBoxLayout(self.empty_box)
        self.empty_label = QLabel('还没有安装 MOD，从在线军械库挑选或导入 ZIP。')
        self.empty_label.setWordWrap(True)
        self.online_empty_btn = QPushButton('浏览在线 MOD')
        self.online_empty_btn.clicked.connect(self.open_online)
        self.import_zip_btn = QPushButton('导入 ZIP…')
        self.import_zip_btn.clicked.connect(self.import_zip)
        empty.addWidget(self.empty_label, 1)
        empty.addWidget(self.online_empty_btn)
        empty.addWidget(self.import_zip_btn)
        lay.addWidget(self.empty_box)

        self.table = QTableWidget(0, 5)
        style_table(self.table)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setHorizontalHeaderLabels(["状态", "文件名", "名称 / 标识", "API", "影响种子"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(1, 340)
        lay.addWidget(self.table, 1)
        self.table.itemSelectionChanged.connect(self.update_controls)
        self.installed_search.textChanged.connect(self.filter_installed)
        self.state_filter.currentTextChanged.connect(self.filter_installed)
        return w

    def refresh(self) -> None:
        mm = self.ctx.mm
        mods = mm.scan() if mm else []
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.setRowCount(len(mods))
        self._installed_infos.clear()
        for i, m in enumerate(mods):
            self._installed_infos[m.path.name] = m.info
            state = QTableWidgetItem("已启用" if m.enabled else "已禁用")
            state.setForeground(QColor(GREEN if m.enabled else MUTED))
            ids = ", ".join(f"{r.mod_id} v{r.version}" for r in m.info.registrations) or "（未注册/纯覆盖）"
            if m.info.package_id:
                version = f' v{m.info.package_version}' if m.info.package_version else ''
                contents = f'；内含：{ids}' if m.info.registrations else ''
                ids = f'{m.info.package_name}{version}（包 ID：{m.info.package_id}）{contents}'
            seed = "有影响" if m.info.seed_sensitive_paths else "—"
            self.table.setItem(i, 0, state)
            filename = QTableWidgetItem(m.path.name)
            filename.setData(Qt.UserRole, m.enabled)
            self.table.setItem(i, 1, filename)
            identity = QTableWidgetItem(ids)
            identity.setToolTip(ids)
            self.table.setItem(i, 2, identity)
            self.table.setItem(i, 3, QTableWidgetItem(m.info.api))
            seed_item = QTableWidgetItem(seed)
            if m.info.seed_sensitive_paths:
                seed_item.setForeground(QColor("#8b601f"))
            self.table.setItem(i, 4, seed_item)
        enabled = sum(1 for m in mods if m.enabled)
        self.status_label.setText(f"共 {len(mods)} 个：启用 {enabled} · 禁用 {len(mods) - enabled}（挂载顺序即文件名排序）")
        self.table.blockSignals(False)
        self.filter_installed()
        self.empty_box.setVisible(not mods)
        self.empty_label.setText('还没有安装 MOD，从在线军械库挑选或导入 ZIP。' if mm else '先选择游戏目录，再安装 MOD。')
        self.recover_btn.setVisible(bool(mm and mm.transaction.journal.exists()))
        self._filter_repo()
        self.online.render()
        self.update_controls()

    def filter_installed(self, *_):
        query = self.installed_search.text().strip().casefold()
        state = self.state_filter.currentText()
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            text = ' '.join(self.table.item(row, col).text() for col in (1, 2)).casefold()
            self.table.setRowHidden(row, bool(query and query not in text)
                                   or (state != '全部状态' and self.table.item(row, 0).text() != state))
        self.update_controls()

    def _selected_mods(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes() if not self.table.isRowHidden(index.row())})
        return [(item.text(), bool(item.data(Qt.UserRole))) for row in rows
                if (item := self.table.item(row, 1)) is not None]

    def update_controls(self, *_):
        selected = self._selected_mods()
        available = bool(self.ctx.mm) and not self.ctx.management_busy and not self.ctx.seedgen_active
        pending = bool(self.ctx.mm and self.ctx.mm.transaction.journal.exists())
        self.enable_btn.setEnabled(available and not pending and any(not state for _, state in selected))
        self.disable_btn.setEnabled(available and not pending and any(state for _, state in selected))
        self.uninstall_btn.setEnabled(available and not pending and bool(selected))
        self.import_zip_btn.setEnabled(not self.ctx.management_busy and not self.ctx.seedgen_active)
        self.recover_btn.setEnabled(available)
        for button in (self.save_profile_btn, self.apply_profile_btn, self.share_profile_btn):
            button.setEnabled(available and not pending)
        self.import_profile_btn.setEnabled(not self.ctx.management_busy and not self.ctx.seedgen_active)

    def profile_origin(self):
        from core.app_updates import SITE_ORIGIN
        from core.online_catalog import site_origin
        return site_origin(self.online.address.text() or SITE_ORIGIN)

    def open_online(self, query=''):
        self.sections.setCurrentIndex(2)
        self.online.search.setText(query if isinstance(query, str) else '')
        if not self.online.items:
            self.online.refresh()

    def import_zip(self):
        if not self.ctx.mm:
            self.choose_game_requested.emit()
        if not self._can_modify():
            return
        paths, _ = QFileDialog.getOpenFileNames(self, '选择 MOD ZIP', '', 'MOD ZIP (*.zip)')
        if not paths:
            return
        try:
            self.ctx.mm.install_many([Path(path) for path in paths])
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, '安装失败', str(exc))
        self.refresh()
        self.ctx.data_changed.emit()

    def recover(self):
        if not self._can_modify():
            return
        try:
            self.ctx.mm.transaction.recover()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, '恢复失败', str(exc))
        self.refresh()
        self.ctx.data_changed.emit()

    def _on_disable(self, enable: bool) -> None:
        if not self._can_modify():
            return
        names = [name for name, enabled in self._selected_mods() if enabled != enable]
        if not names:
            return
        try:
            self.ctx.mm.set_enabled_many(names, enable)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, '操作失败', str(exc))
        self.refresh()
        self.ctx.data_changed.emit()

    def uninstall(self) -> None:
        if not self._can_modify():
            return
        selected = self._selected_mods()
        if not selected:
            return
        names = '\n'.join(f"{name}（{'已启用' if enabled else '已禁用'}）" for name, enabled in selected)
        if QMessageBox.question(self, '卸载 MOD', f'卸载以下 {len(selected)} 个 MOD？\n\n{names}\n\n'
                '将删除安装文件并移出已安装列表，再次使用需要重新安装。\n'
                '没有剩余安装副本时，关联汉化方案也会移除；方案中的其他安装文件保留。\n仓库原包和游戏存档保留。',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        if not self._can_modify():
            return
        errors = []
        for name, enabled in selected:
            try:
                self.ctx.mm.uninstall(name, from_disabled=not enabled)
            except (OSError, ValueError) as exc:
                errors.append(f'{name}: {exc}')
        if errors:
            QMessageBox.warning(self, '部分卸载失败', '\n'.join(errors))
        self.refresh()
        self.ctx.data_changed.emit()

    def _open_dir(self) -> None:
        from core import game as game_mod
        if self.ctx.game:
            game_mod.open_folder(self.ctx.game.data_dir)

    def save_profile(self) -> None:
        if not self._can_modify():
            return
        name, ok = QInputDialog.getText(self, "保存方案", "方案名称：")
        if ok and name.strip():
            name = name.strip()
            if name in self.ctx.mm.load_profiles() and QMessageBox.question(self, '覆盖方案',
                    f'用当前启用的 MOD 覆盖「{name}」？原方案及其分享关联将被替换。',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            if not self._can_modify():
                return
            try:
                self.ctx.mm.save_profile(name)
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, '保存失败', str(error))
                return
            self.ctx.data_changed.emit()
            self.status_label.setText(f"已保存方案「{name}」")

    def apply_profile(self) -> None:
        if not self._can_modify():
            return
        profiles = self.ctx.mm.load_profiles()
        if not profiles:
            QMessageBox.information(self, "应用方案", "还没有保存过方案")
            return
        name, ok = QInputDialog.getItem(self, "应用方案", "选择方案：", list(profiles), 0, False)
        if ok:
            if profiles[name].get('shared_id'):
                self.sharing.import_link(profiles[name]['shared_id'], origin=profiles[name].get('shared_origin'))
                return
            try:
                plan = self.ctx.mm.preview_profile(name)
                message = '将启用：\n' + ('\n'.join(plan['enable']) or '无') + '\n\n将禁用：\n' + ('\n'.join(plan['disable']) or '无')
                if QMessageBox.question(self, '预览方案变更', message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                    return
                if not self._can_modify():
                    return
                en, dis = self.ctx.mm.apply_profile(name, expected=plan)
            except (KeyError, OSError, ValueError) as e:
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
        style_button(self.repo_refresh_btn, "refresh")
        style_button(self.import_btn, "folder")
        style_button(self.install_btn, "download", primary=True)
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
        style_table(self.repo_table)
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
        if hasattr(self, "_repo_worker") and self._repo_worker.isRunning():
            return
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
        installed = self.ctx.mm.installation_states() if self.ctx.mm else {}
        self._filtered_repo_entries = rows
        self.repo_table.setRowCount(len(rows))
        for i, e in enumerate(rows):
            state = installed.get(e.info.file_name.casefold())
            mark = f'（{state}）' if state else ''
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
        if not self._can_modify():
            return
        rows = {idx.row() for idx in self.repo_table.selectedIndexes()}
        if not rows:
            QMessageBox.information(self, "安装", "先在列表中选择要安装的 mod（可多选）")
            return
        entries = [self._filtered_repo_entries[r] for r in sorted(rows)]
        try:
            installed = self.ctx.mm.install_many([entry.info.path for entry in entries])
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "安装失败", str(exc))
            return
        self.repo_status.setText(f"已安装 {len(installed)} 个文件")
        self.refresh()
        self.refresh_repo()
        self.ctx.data_changed.emit()

    def _can_modify(self) -> bool:
        if not self.ctx.mm or getattr(self.ctx, 'management_busy', False) or getattr(self.ctx, 'seedgen_active', False):
            return False
        from core.game import is_game_running
        if is_game_running():
            QMessageBox.information(self, '游戏运行中', '请关闭游戏后再更改 MOD 或汉化配置。')
            return False
        return True
