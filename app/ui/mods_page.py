"""MOD 管理页：已安装列表（启停/卸载/顺序）+ 仓库（分类安装）+ profile。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QItemSelectionModel, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from core.modinfo import CATEGORY_LABELS, analyze_zip
from core.installed_mod_catalog import resolve_installed_mod
from core.modstore import load_index
from core.online_catalog import OnlineInstaller
from core.site_config import SITE_ORIGIN, same_site
from .app_context import AppContext
from .workers import Worker, track, modify_files
from .theme import GREEN, MUTED, style_button, style_table
from PySide6.QtGui import QColor


class ModsPage(QWidget):
    choose_game_requested = Signal()
    profiles_requested = Signal(bool)
    def __init__(self, ctx: AppContext, *, automatic_catalog=False) -> None:
        super().__init__()
        self.ctx = ctx
        self.automatic_catalog = automatic_catalog
        self._installed_infos: dict[str, object] = {}
        self._installed_mods = []
        self._installed_index = load_index()
        self._installed_hashes = {}
        self._installed_release_versions = {}
        self._installed_catalog_items = []
        self._installed_catalog_origin = SITE_ORIGIN
        self._receipts, self._states = {}, {}
        self._scan_worker = self._op_worker = self._repo_worker = None
        self._scan_again = False
        self._pending_op = None
        self._skip_refresh = False
        self._refresh_deferred = False
        self._scan_status = ''
        self._row_buttons_state = None

        root = QVBoxLayout(self)
        tabs = self.sections = QTabWidget()
        tabs.addTab(self._build_installed_tab(), "已安装（启用 / 禁用）")
        tabs.addTab(self._build_repo_tab(), "仓库（内置合集 / 外部导入）")
        from .online_mods import OnlineModsPage
        self.online = OnlineModsPage(ctx, self._can_modify, self)
        self.online.catalog_changed.connect(self._online_catalog_changed)
        self.online.operation_status.connect(self.catalog_status.setText)
        self.cancel_update_btn.clicked.connect(self.online.cancelled.set)
        tabs.addTab(self.online, "在线军械库")
        from .profile_sharing import ProfileSharing
        self.sharing = ProfileSharing(self)
        root.addWidget(tabs, 1)
        ctx.management_changed.connect(self.update_controls)
        ctx.management_changed.connect(self._management_changed)
        ctx.session_changed.connect(self.update_controls)
        self.catalog_service = None
        if getattr(ctx.settings, 'path', None) is not None:
            from .installed_catalog_service import InstalledCatalogService
            self.catalog_service = InstalledCatalogService(ctx.settings, self)
            self.catalog_service.changed.connect(self._catalog_checked)
            self._catalog_checked(self.catalog_service.snapshot('使用已缓存的官网目录' if self.catalog_service.items else '进入军械库后自动检查官网版本'))
        self.refresh_btn.clicked.connect(lambda: self.check_catalog(force=True))
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
        self.bisect_btn = QPushButton('排查问题 MOD')
        self.bisect_btn.setToolTip('游戏闪退或报错但不知道是哪个 MOD 时，每轮只启用一部分，逐步缩小范围。')
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
                (self.manage_profiles_btn, lambda: self.profiles_requested.emit(False)),
                (self.bisect_btn, self.start_bisect)):
            button.clicked.connect(callback)
            profile_bar.addWidget(button)
        self.share_profile_btn.setToolTip('分享保存的 MOD 组合，只上传网站缺失的文件。')
        self.import_profile_btn.setToolTip('浏览网站现有方案，选择后预览并应用；也支持链接导入。')
        style_button(self.share_profile_btn, 'save')
        style_button(self.import_profile_btn, 'download')
        profile_bar.addStretch(1)
        lay.addLayout(profile_bar)
        lay.addWidget(self.status_label)
        self.catalog_status = QLabel('进入军械库后自动检查官网版本')
        self.catalog_status.setWordWrap(True)
        self.catalog_status.setTextFormat(Qt.PlainText)
        catalog_bar = QHBoxLayout()
        catalog_bar.addWidget(self.catalog_status, 1)
        self.cancel_update_btn = QPushButton('取消下载')
        self.cancel_update_btn.setVisible(False)
        style_button(self.cancel_update_btn, 'stop')
        catalog_bar.addWidget(self.cancel_update_btn)
        lay.addLayout(catalog_bar)

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

        self.table = QTableWidget(0, 8)
        style_table(self.table)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setHorizontalHeaderLabels(["状态", "文件名", "名称", "本地版本", "官网版本", "更新", "API", "影响种子"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        for column, width in ((0, 84), (1, 230), (2, 250), (3, 108), (4, 145), (5, 120), (6, 86)):
            self.table.setColumnWidth(column, width)
        # Keep the filename's logical column stable for file operations while
        # placing the name and versions first in the visible table.
        header = self.table.horizontalHeader()
        for position, column in enumerate((2, 3, 4, 5), start=1):
            header.moveSection(header.visualIndex(column), position)
        lay.addWidget(self.table, 1)
        self.table.itemSelectionChanged.connect(self.update_controls)
        self.installed_search.textChanged.connect(self.filter_installed)
        self.state_filter.currentTextChanged.connect(self.filter_installed)
        return w

    @property
    def idle(self) -> bool:
        return (self._scan_worker is None and self._op_worker is None and self._pending_op is None
                and not self._scan_again and not self._refresh_deferred
                # 线程结束与操作收尾是两个排队事件；收尾完成前仍处于管理忙碌状态
                and not getattr(self.ctx, 'management_busy', False))

    def refresh(self) -> None:
        """后台扫描已安装 MOD；扫描期间再次刷新会在结束后补扫一次，文件操作期间则由操作结束时统一刷新。"""
        if self._skip_refresh:
            return
        mm = self.ctx.mm
        self.recover_btn.setVisible(bool(mm and mm.transaction.journal.exists()))
        if self._scan_worker is not None:
            self._scan_again = True
            return
        if self._op_worker is not None or getattr(self.ctx, 'management_busy', False):
            # 其它后台操作（在线安装、方案应用等）可能正在移动 ZIP；结束后再扫描。
            self._refresh_deferred = True
            return
        if not mm:
            self._scan_status = self.status_label.text()
            self._show_installed([], {}, {})
            return
        self.status_label.setText('正在读取已安装 MOD…')
        self._scan_status = self.status_label.text()
        self.empty_box.hide()
        self._start_scan(mm)

    def _start_scan(self, mm) -> None:
        worker = track(self, '_scan_worker', Worker(lambda: self._scan(mm), self))
        worker.done.connect(lambda result: self._scanned(mm, result))
        worker.failed.connect(lambda error: self.status_label.setText('读取已安装 MOD 失败：' + error))
        worker.finished.connect(self._scan_finished)
        worker.start()

    @staticmethod
    def _scan(mm):
        mods = mm.scan()
        try:
            receipts = OnlineInstaller(mm).state()['mods']
        except (OSError, ValueError, TypeError):
            receipts = {}
        return mods, mm.installation_states(mods), receipts

    def _scanned(self, mm, result) -> None:
        if mm is not self.ctx.mm:
            self._scan_again = True
        else:
            self._show_installed(*result)

    def _management_changed(self, busy) -> None:
        if not busy and self._refresh_deferred:
            self._refresh_deferred = False
            self.refresh()

    def _scan_finished(self) -> None:
        if self._pending_op is not None:
            # 操作结束时会重新扫描，这里不必补扫。
            start, self._pending_op = self._pending_op, None
            self._scan_again = False
            start()
            return
        if self._scan_again:
            self._scan_again = False
            if getattr(self.ctx, 'management_busy', False):
                self._refresh_deferred = True
            elif self.ctx.mm:
                self._start_scan(self.ctx.mm)
            else:
                self.refresh()

    def _show_installed(self, mods, states, receipts) -> None:
        mm = self.ctx.mm
        self._installed_mods, self._states, self._receipts = mods, states, receipts
        self._render_installed()
        enabled = sum(1 for m in mods if m.enabled)
        if self.status_label.text() == self._scan_status:
            self.status_label.setText(f"共 {len(mods)} 个：启用 {enabled} · 禁用 {len(mods) - enabled}（挂载顺序即文件名排序）")
        self.empty_box.setVisible(not mods)
        self.empty_label.setText('还没有安装 MOD，从在线军械库挑选或导入 ZIP。' if mm else '先选择游戏目录，再安装 MOD。')
        self.recover_btn.setVisible(bool(mm and mm.transaction.journal.exists()))
        self._filter_repo()
        self.online.set_local_state((receipts, states))
        self.online.render()
        self.update_controls()
        if self.automatic_catalog and self.isVisible():
            self.check_catalog()

    def _operate(self, status, failure, fn, done=None) -> None:
        """后台执行文件操作：期间锁定 MOD 管理，结束后刷新列表并广播。"""
        if self._op_worker is not None or self._pending_op is not None:
            return
        manager = self.ctx.mm
        operation = lambda: modify_files(manager, fn)
        self.ctx.set_management_busy(True)
        self.status_label.setText(status + '…')
        if self._scan_worker is not None:
            # 扫描线程可能正打开这些 ZIP；Windows 上移动被打开的文件会失败，等扫描结束再动手。
            self._pending_op = lambda: self._start_operation(failure, operation, done)
            return
        self._start_operation(failure, operation, done)

    def _start_operation(self, failure, fn, done) -> None:
        def work():
            try:
                return fn(), None
            except (KeyError, OSError, ValueError) as exc:
                return None, str(exc)
        outcome = []
        worker = track(self, '_op_worker', Worker(work, self))
        worker.done.connect(outcome.append)
        worker.failed.connect(lambda error: outcome.append((None, error)))

        def finished():
            self._refresh_deferred = False  # 下面统一刷新一次
            self.ctx.set_management_busy(False)
            self.refresh()
            # 上面刚启动的扫描已看到操作后的文件，广播时不再重复扫描本页。
            self._skip_refresh = True
            try:
                self.ctx.data_changed.emit()
            finally:
                self._skip_refresh = False
            result, error = outcome[0] if outcome else (None, '操作已中断，请刷新后重试。')
            if error is not None:
                QMessageBox.warning(self, failure, error)
            elif done:
                done(result)
        worker.finished.connect(finished)
        worker.start()

    def _installed_catalog(self):
        return self._installed_catalog_items, self._installed_catalog_origin

    def check_catalog(self, *, force=False):
        if self.catalog_service and self._installed_mods:
            self.catalog_status.setText('正在检查官网 MOD 版本…')
            self.catalog_service.check([mod.info for mod in self._installed_mods], force=force,
                                       receipts=self._installed_receipts(), local_index=self._installed_index)

    def _catalog_checked(self, result):
        self.set_installed_catalog(result['items'], SITE_ORIGIN, hashes=result.get('hashes'),
                                   release_versions=result.get('release_versions'))
        if result.get('status') and not self.ctx.management_busy:
            self.catalog_status.setText(result['status'])

    def _online_catalog_changed(self, items, origin):
        if same_site(origin, SITE_ORIGIN):
            if self.catalog_service:
                self.catalog_service.use_catalog(items)
                self.check_catalog()
            else:
                self.set_installed_catalog(items, SITE_ORIGIN)

    def set_installed_catalog(self, items, origin=SITE_ORIGIN, *, hashes=None, release_versions=None):
        self._installed_catalog_items = list(items)
        self._installed_catalog_origin = origin
        if hashes is not None:
            self._installed_hashes.update(hashes)
        if release_versions is not None:
            self._installed_release_versions = release_versions
        self.refresh_installed_metadata()

    def _installed_receipts(self):
        return self._receipts

    def _installed_signature(self, info):
        try:
            stat = info.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return None

    def _installed_hash(self, info):
        cached = self._installed_hashes.get(str(info.path.resolve()))
        if not cached or tuple(cached[:2]) != self._installed_signature(info):
            return None
        if len(cached) >= 5:
            try:
                stat = info.path.stat()
                if tuple(cached[3:5]) != (stat.st_dev, stat.st_ino):
                    return None
            except OSError:
                return None
        return cached[2]

    def refresh_installed_metadata(self, *_):
        """Refresh catalog labels without scanning ZIPs or dropping the selection."""
        self._render_installed(preserve_selection=True)

    def _render_installed(self, *, preserve_selection=False):
        selected = set(self._selected_mods()) if preserve_selection else set()
        mods = self._installed_mods
        catalog, origin = self._installed_catalog()
        receipts = self._installed_receipts()
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.setRowCount(len(mods))
        self._row_buttons_state = None
        self._installed_infos.clear()
        for i, m in enumerate(mods):
            self._installed_infos[m.path.name] = m.info
            state = QTableWidgetItem("已启用" if m.enabled else "已禁用")
            state.setForeground(QColor(GREEN if m.enabled else MUTED))
            display = resolve_installed_mod(m.info, catalog, receipts=receipts,
                local_index=self._installed_index, origin=origin, local_sha256=self._installed_hash(m.info),
                release_versions=self._installed_release_versions)
            seed = "有影响" if m.info.seed_sensitive_paths else "—"
            self.table.setItem(i, 0, state)
            filename = QTableWidgetItem(m.path.name)
            filename.setData(Qt.UserRole, m.enabled)
            self.table.setItem(i, 1, filename)
            identity = QTableWidgetItem(display.display_name)
            identity.setToolTip(display.tooltip)
            identity.setData(Qt.UserRole, display.search_text)
            self.table.setItem(i, 2, identity)
            self.table.setItem(i, 3, QTableWidgetItem(display.installed_version or '未知'))
            latest = QTableWidgetItem(display.latest_version or '—')
            latest.setToolTip((f'官网版本：{display.latest_version}\n' if display.latest_version else '') + display.status)
            self.table.setItem(i, 4, latest)
            self.table.removeCellWidget(i, 5)
            update = QTableWidgetItem('' if display.update_available else display.status)
            update.setToolTip(display.status)
            self.table.setItem(i, 5, update)
            if display.update_available and display.catalog_item:
                button = QPushButton('更新')
                button.setToolTip(f'本地 {display.installed_version} → 官网 {display.latest_version}；下载并更新，旧版自动备份')
                button.setProperty('verifiedFile', bool(self._installed_hash(m.info)))
                button.clicked.connect(lambda checked=False, item=display.catalog_item, source=origin,
                        file_name=m.info.file_name, digest=self._installed_hash(m.info), version=display.installed_version:
                    self.online.update_installed(item, origin=source, current_file_name=file_name,
                        current_sha256=digest, installed_version=version))
                self.table.setCellWidget(i, 5, button)
            self.table.setItem(i, 6, QTableWidgetItem(m.info.api))
            seed_item = QTableWidgetItem(seed)
            if m.info.seed_sensitive_paths:
                seed_item.setForeground(QColor("#8b601f"))
                seed_item.setToolTip('\n'.join(m.info.seed_sensitive_paths))
            self.table.setItem(i, 7, seed_item)
        self.table.blockSignals(False)
        self.filter_installed()
        for row, mod in enumerate(mods):
            if (mod.path.name, mod.enabled) in selected and not self.table.isRowHidden(row):
                self.table.selectionModel().select(self.table.model().index(row, 1),
                    QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.update_controls()

    def filter_installed(self, *_):
        query = self.installed_search.text().strip().casefold()
        state = self.state_filter.currentText()
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            identity = self.table.item(row, 2)
            text = ' '.join((self.table.item(row, 1).text(), identity.text(),
                            str(identity.data(Qt.UserRole) or ''))).casefold()
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
        online_running = bool(hasattr(self, 'online') and self.online.worker and self.online.worker.isRunning())
        rows_enabled = available and not pending and not online_running
        if rows_enabled != self._row_buttons_state:
            self._row_buttons_state = rows_enabled
            for row in range(self.table.rowCount()):
                button = self.table.cellWidget(row, 5)
                if button:
                    button.setEnabled(rows_enabled and bool(button.property('verifiedFile')))
        self.cancel_update_btn.setVisible(bool(hasattr(self, 'online') and self.ctx.management_busy
                                              and self.online.cancel_btn.isEnabled()))
        self.enable_btn.setEnabled(available and not pending and any(not state for _, state in selected))
        self.disable_btn.setEnabled(available and not pending and any(state for _, state in selected))
        self.uninstall_btn.setEnabled(available and not pending and bool(selected))
        self.import_zip_btn.setEnabled(not self.ctx.management_busy and not self.ctx.seedgen_active)
        self.recover_btn.setEnabled(available)
        for button in (self.save_profile_btn, self.apply_profile_btn, self.share_profile_btn, self.bisect_btn):
            button.setEnabled(available and not pending)
        from core.bisect import BISECT_FILE
        bisecting = bool(self.ctx.mm and (self.ctx.mm.disabled_dir / BISECT_FILE).exists())
        self.bisect_btn.setText('继续排查（进行中）' if bisecting else '排查问题 MOD')
        self.import_profile_btn.setEnabled(not self.ctx.management_busy and not self.ctx.seedgen_active)

    def profile_origin(self):
        from core.site_config import SITE_ORIGIN
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
        manager, sources = self.ctx.mm, [Path(path) for path in paths]
        self._operate('正在安装 MOD', '安装失败', lambda: manager.install_many(sources))

    def recover(self):
        if not self._can_modify():
            return
        self._operate('正在恢复上次操作', '恢复失败', self.ctx.mm.transaction.recover)

    def _on_disable(self, enable: bool) -> None:
        if not self._can_modify():
            return
        names = [name for name, enabled in self._selected_mods() if enabled != enable]
        if not names:
            return
        manager = self.ctx.mm
        self._operate('正在启用 MOD' if enable else '正在禁用 MOD', '操作失败',
                      lambda: manager.set_enabled_many(names, enable))

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
        manager = self.ctx.mm

        def work():
            errors = []
            for name, enabled in selected:
                try:
                    manager.uninstall(name, from_disabled=not enabled)
                except (OSError, ValueError) as exc:
                    errors.append(f'{name}: {exc}')
            return errors

        def report(errors):
            if errors:
                QMessageBox.warning(self, '部分卸载失败', '\n'.join(errors))
        self._operate('正在卸载 MOD', '卸载失败', work, report)

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
            self.apply_named_profile(name)

    def apply_named_profile(self, name: str) -> None:
        """预览后应用指定方案；共享方案走网站导入流程。"""
        if not self._can_modify():
            return
        profile = self.ctx.mm.load_profiles().get(name)
        if profile is None:
            QMessageBox.warning(self, "应用失败", f"方案「{name}」已不存在，请刷新后重试。")
            return
        if profile.get('shared_id'):
            self.sharing.import_link(profile['shared_id'], origin=profile.get('shared_origin'))
            return
        try:
            plan = self.ctx.mm.preview_profile(name)
        except (KeyError, OSError, ValueError) as e:
            QMessageBox.warning(self, "应用失败", str(e))
            return
        if not plan['enable'] and not plan['disable']:
            self.status_label.setText(f"当前启用的 MOD 已与「{name}」一致。")
            return
        message = '将启用：\n' + ('\n'.join(plan['enable']) or '无') + '\n\n将禁用：\n' + ('\n'.join(plan['disable']) or '无')
        if QMessageBox.question(self, '预览方案变更', message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        if not self._can_modify():
            return
        manager = self.ctx.mm
        self._operate(f'正在应用「{name}」', '应用失败', lambda: manager.apply_profile(name, expected=plan),
                      lambda counts: self.status_label.setText(f"已应用「{name}」：启用 {counts[0]} · 禁用 {counts[1]}"))

    def restore_last_good(self) -> None:
        from core.modmanager import LAST_GOOD_PROFILE
        if not self.ctx.mm:
            return
        if LAST_GOOD_PROFILE not in self.ctx.mm.load_profiles():
            QMessageBox.information(self, '暂无记录', '还没有正常退出的记录。通过 BBMOD 启动游戏并正常退出后，'
                                    '会自动记录当时启用的 MOD 组合。')
            return
        self.apply_named_profile(LAST_GOOD_PROFILE)

    def start_bisect(self) -> None:
        if not self.ctx.mm:
            self.choose_game_requested.emit()
            return
        from .bisect_dialog import BisectDialog
        dialog = getattr(self, '_bisect_dialog', None)
        if dialog is None:
            dialog = self._bisect_dialog = BisectDialog(self)
            dialog.finished.connect(lambda *_: setattr(self, '_bisect_dialog', None))
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

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
        if self._repo_worker and self._repo_worker.isRunning():
            return
        def scan():
            return self.ctx.store().scan()

        track(self, '_repo_worker', Worker(scan, self))
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
        installed = self._states
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
        manager, sources = self.ctx.mm, [self._filtered_repo_entries[r].info.path for r in sorted(rows)]
        self._operate('正在安装 MOD', '安装失败', lambda: manager.install_many(sources),
                      lambda installed: self.repo_status.setText(f"已安装 {len(installed)} 个文件"))

    def _can_modify(self) -> bool:
        if (not self.ctx.mm or self._op_worker is not None or self._pending_op is not None or getattr(self.ctx, 'management_busy', False)
                or getattr(self.ctx, 'seedgen_active', False)):
            return False
        from core.game import is_game_running
        if is_game_running():
            QMessageBox.information(self, '游戏运行中', '请关闭游戏后再更改 MOD 或汉化配置。')
            return False
        return True
