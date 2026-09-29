from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout, QPushButton, QFileDialog, QMessageBox


class SupportDialog(QDialog):
    def __init__(self, text, parent=None, *, editing=False):
        super().__init__(parent)
        self.setWindowTitle('预览诊断报告')
        self.resize(760, 560)
        layout = QVBoxLayout(self)
        hint = QLabel('已隐藏常见个人路径、邮件和 IP。请检查并删除不想分享的内容；只有加入反馈并点击提交后才会发送。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlainText(text)
        layout.addWidget(self.editor)
        actions = QHBoxLayout()
        export = QPushButton('导出 TXT…')
        export.clicked.connect(self.export)
        attach = QPushButton('保存修改' if editing else '继续填写并提交…')
        attach.clicked.connect(self.accept)
        close = QPushButton('关闭')
        close.clicked.connect(self.reject)
        for button in (export, attach, close):
            actions.addWidget(button)
        layout.addLayout(actions)

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, '导出诊断报告', 'BBMOD-诊断报告.txt', '文本 (*.txt)')
        if path:
            try:
                Path(path).write_text(self.editor.toPlainText(), encoding='utf-8-sig')
            except OSError as exc:
                QMessageBox.warning(self, '导出失败', str(exc))
