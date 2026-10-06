"""Desktop sharing and one-step installation of hosted MOD collections."""
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QInputDialog,
                               QLabel, QMessageBox, QTextEdit, QVBoxLayout)

from core.online_catalog import site_origin
from core.shared_profiles import (prepare_share, negotiate, publish_share, fetch_profile,
                                  profile_identity, preview_apply, apply_shared)
from .workers import Worker, track


class ProfileWorker(Worker):
    progress = Signal(str)

    def __init__(self, function, parent):
        super().__init__(lambda: function(self.progress.emit), parent)


def preview_dialog(parent, title, summary, details, action):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(700, 520)
    layout = QVBoxLayout(dialog)
    label = QLabel(summary)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    layout.addWidget(label)
    body = QTextEdit()
    body.setReadOnly(True)
    body.setPlainText(details)
    layout.addWidget(body, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText(action)
    buttons.button(QDialogButtonBox.Cancel).setText('取消')
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    return dialog.exec() == QDialog.Accepted


class ProfileSharing(QObject):
    def __init__(self, page):
        super().__init__(page)
        self.page, self.ctx = page, page.ctx
        self.worker = None

    def _origin(self):
        return self.page.profile_origin()

    def _ready(self):
        if not self.ctx.mm:
            self.page.choose_game_requested.emit()
        if not self.page._can_modify():
            return False
        if self.ctx.mm.transaction.journal.exists():
            QMessageBox.warning(self.page, '请先恢复', '上次 MOD 操作尚未恢复，请先点击「恢复上次操作」。')
            return False
        return True

    def _run(self, title, function, done):
        if self.ctx.management_busy or (self.worker and self.worker.isRunning()):
            return
        self.ctx.set_management_busy(True)
        self.page.status_label.setText(title + '…')
        worker = track(self, 'worker', ProfileWorker(function, self.page))
        result, errors = [], []
        worker.done.connect(result.append)
        worker.failed.connect(errors.append)
        worker.progress.connect(self.page.status_label.setText)

        def finished():
            self.ctx.set_management_busy(False)
            if errors:
                self.page.refresh()
                self.page.status_label.setText('操作未完成：' + errors[0])
                QMessageBox.warning(self.page, title + '失败', errors[0])
            elif result:
                try:
                    done(result[0])
                except (ValueError, OSError) as error:
                    QMessageBox.warning(self.page, title + '失败', str(error))
        worker.finished.connect(finished)
        worker.start()

    def share(self, name=None):
        if not self._ready():
            return
        manager = self.ctx.mm
        profiles = manager.load_profiles()
        if not profiles:
            QMessageBox.information(self.page, '分享方案', '先启用想分享的 MOD，再点击「保存为方案」。')
            return
        if name is None:
            name, ok = QInputDialog.getItem(self.page, '分享方案', '选择要分享的方案：', list(profiles), 0, False)
            if not ok:
                return
        if name not in profiles:
            QMessageBox.warning(self.page, '方案不存在', '请刷新本地方案列表后重试。')
            return
        note, ok = QInputDialog.getMultiLineText(self.page, '方案介绍', '介绍玩法、需要的 DLC 或使用注意事项（选填）：')
        if not ok:
            return
        try:
            origin = self._origin()
        except ValueError as error:
            QMessageBox.warning(self.page, '网站地址无效', str(error))
            return
        version = getattr(getattr(self.ctx, 'game', None), 'version', '') or ''

        def prepare(progress):
            prepared = prepare_share(manager, name, note, version, progress)
            progress('正在核对网站已有的 MOD…')
            return prepared, negotiate(origin, prepared)

        def confirm(result):
            prepared, rows = result
            missing = {r['sha256'] for r in rows if r['status'] == 'missing'}
            sizes = {m['sha256']: m['size'] for m in prepared['manifest']['mods']}
            count = len(rows) - sum(r['status'] == 'missing' for r in rows)
            details = '\n'.join(('需要上传：' if r['status'] == 'missing' else '网站已有：') + r['file_name'] for r in rows)
            if prepared['warnings']:
                details += '\n\n兼容提示：\n' + '\n'.join(prepared['warnings'])
            summary = (f'「{name}」共 {len(rows)} 个 MOD，网站已有 {count} 个。\n'
                       f'只需补传 {len(missing)} 个文件，共 {sum(sizes[s] for s in missing) / 1024**2:.1f} MB。\n'
                       '将公开方案介绍和这些 MOD 的当前文件，其他玩家可下载并应用。')
            if preview_dialog(self.page, '分享前核对', summary, details, '上传并分享') and self._ready():
                self._run('分享方案', lambda progress: publish_share(origin, prepared, progress),
                          lambda link: self._shared(link, manager, name, origin))
            else:
                self.page.status_label.setText('已取消分享，未上传 MOD 文件。')
        self._run('核对共享方案', prepare, confirm)

    def _shared(self, link, manager=None, name=None, origin=None):
        QApplication.clipboard().setText(link)
        warning = ''
        if manager is not None:
            try:
                manager.record_profile_share(name, origin, profile_identity(link, origin))
            except (OSError, ValueError) as error:
                warning = '\n\n本地分享记录未保存：' + str(error) + '\n仍可在「方案管理 → 网站方案」找回此方案。'
        self.page.refresh()
        self.ctx.data_changed.emit()
        self.page.status_label.setText('方案已分享，链接已复制：' + link)
        QMessageBox.information(self.page, '分享成功', '分享链接已复制：\n' + link
            + '\n\n可在「方案管理」随时复制链接，也可直接从「网站方案」浏览并应用。' + warning)

    def import_link(self, value=None, origin=None):
        if not self._ready():
            return
        if value is None:
            value, ok = QInputDialog.getText(self.page, '导入共享方案', '粘贴方案分享链接或方案编号：')
            if not ok or not value.strip():
                return
        try:
            origin = site_origin(origin or self._origin())
            identity = profile_identity(value, origin)
        except ValueError as error:
            QMessageBox.warning(self.page, '方案链接无效', str(error))
            return
        manager = self.ctx.mm

        def read(progress):
            progress('正在读取共享方案并核对本机 MOD…')
            manifest = fetch_profile(origin, identity)
            return manifest, preview_apply(manager, manifest)

        def confirm(result):
            manifest, plan = result
            details = manifest['note'] + '\n\n方案包含：\n' + '\n'.join(
                f"{m['title']} · {m['file_name']}" + (f" · {m['version']}" if m['version'] else '') for m in manifest['mods'])
            details += '\n\n需要下载：\n' + ('\n'.join(plan['download']) or '无，全部复用本机文件')
            details += '\n\n将安装或切换：\n' + ('\n'.join(plan['change']) or '无')
            details += '\n\n将禁用：\n' + ('\n'.join(plan['disable']) or '无')
            current = getattr(getattr(self.ctx, 'game', None), 'version', None)
            if manifest['game_version'] and current != manifest['game_version']:
                details += f"\n\n游戏版本不同或未识别：分享者 {manifest['game_version']}；本机 {current or '未识别'}。请确认兼容性。"
            summary = (f"「{manifest['name']}」· {len(manifest['mods'])} 个 MOD · 需下载 {len(plan['download'])} 个\n"
                       '下载并校验完成后统一应用；方案外的已启用 MOD 将被禁用，同名旧文件保留备份。')
            if preview_dialog(self.page, '预览共享方案', summary, details, '下载并应用') and self._ready():
                self._run('应用共享方案', lambda progress: apply_shared(manager, origin, identity, manifest,
                    expected=plan, progress=progress), self._applied)
            else:
                self.page.status_label.setText('已取消应用，未更改本机 MOD。')
        self._run('读取共享方案', read, confirm)

    def _applied(self, result):
        self.page.refresh()
        self.ctx.data_changed.emit()
        self.page.status_label.setText(f"已应用「{result['name']}」：{result['count']} 个 MOD，下载 {result['downloaded']} 个，禁用 {result['disabled']} 个。")
        message = f"方案已保存为「{result['name']}」。\n操作前的文件备份保存在：\n{result['backup']}"
        if result['warnings']:
            message += '\n\n兼容提示：\n' + '\n'.join(result['warnings'])
        QMessageBox.information(self.page, '方案已应用', message)
