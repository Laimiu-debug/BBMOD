"""Windows RegisterHotKey, with explicit ownership and conflict reporting."""
import ctypes
from ctypes import wintypes
import sys
from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

DEFAULT = 'Ctrl+Alt+D'


def parse_shortcut(value):
    sequence = QKeySequence(value, QKeySequence.PortableText)
    if sequence.count() != 1 or sequence.isEmpty():
        raise ValueError('请录入一个快捷键组合，例如 Ctrl+Alt+D 或 F8。')
    combination = sequence[0]
    key, flags = combination.key(), combination.keyboardModifiers()
    if flags & Qt.MetaModifier or key == Qt.Key_F12:
        raise ValueError('Windows 键组合和 F12 由系统保留，请换一个快捷键。')
    modifiers = (0x0002 if flags & Qt.ControlModifier else 0) | (0x0001 if flags & Qt.AltModifier else 0) | (0x0004 if flags & Qt.ShiftModifier else 0)
    if Qt.Key_F1 <= key <= Qt.Key_F24:
        virtual_key = 0x70 + int(key) - int(Qt.Key_F1)
    else:
        if not modifiers & 3:
            raise ValueError('字母、数字和方向键请搭配 Ctrl 或 Alt，避免占用游戏操作；也可以使用 F8 等功能键。')
        special = {Qt.Key_Space: 0x20, Qt.Key_Tab: 0x09, Qt.Key_Return: 0x0D, Qt.Key_Escape: 0x1B,
            Qt.Key_Backspace: 0x08, Qt.Key_Delete: 0x2E, Qt.Key_Insert: 0x2D, Qt.Key_Home: 0x24,
            Qt.Key_End: 0x23, Qt.Key_PageUp: 0x21, Qt.Key_PageDown: 0x22, Qt.Key_Left: 0x25,
            Qt.Key_Up: 0x26, Qt.Key_Right: 0x27, Qt.Key_Down: 0x28}
        virtual_key = int(key) if Qt.Key_A <= key <= Qt.Key_Z or Qt.Key_0 <= key <= Qt.Key_9 else special.get(key)
        if virtual_key is None or flags & (Qt.KeypadModifier | Qt.GroupSwitchModifier):
            raise ValueError('请使用字母、数字、功能键或方向键组合。')
    return sequence.toString(QKeySequence.PortableText), modifiers, virtual_key


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, owner):
        super().__init__(); self.owner = owner

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.owner.identifier:
                self.owner.activated.emit()
                return True, 0
        return False, 0


class GlobalHotkey(QObject):
    activated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.identifier = 0xBB42
        self.registered = False
        self.current = ''
        self.filter = _Filter(self)
        self.api = None
        if sys.platform == 'win32':
            self.api = ctypes.WinDLL('user32', use_last_error=True)
            self.api.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.api.RegisterHotKey.restype = wintypes.BOOL
            self.api.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self.api.UnregisterHotKey.restype = wintypes.BOOL
        QApplication.instance().installNativeEventFilter(self.filter)

    def set_shortcut(self, shortcut):
        shortcut, modifiers, key = parse_shortcut(shortcut)
        if self.registered and shortcut == self.current: return
        if self.api is None:
            raise ValueError('全局快捷键仅支持 Windows，可在页面开启或暂停悬停提示。')
        identifier = 0xBB43 if self.identifier == 0xBB42 else 0xBB42
        if not self.api.RegisterHotKey(None, identifier, modifiers | 0x4000, key):
            raise ValueError('快捷键已被其他程序占用，请换一个组合，或关闭另一个 BBMOD 窗口。')
        # Keep the old binding alive until the replacement has succeeded.
        self.clear()
        self.identifier = identifier
        self.registered, self.current = True, shortcut

    def clear(self):
        if self.registered:
            self.api.UnregisterHotKey(None, self.identifier)
        self.registered, self.current = False, ''

    def shutdown(self):
        self.clear()
        QApplication.instance().removeNativeEventFilter(self.filter)
