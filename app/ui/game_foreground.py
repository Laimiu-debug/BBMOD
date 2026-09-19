"""Foreground identity and cursor bounds only; no game memory access."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import time
from PySide6.QtCore import QRectF
from PySide6.QtGui import QCursor, QGuiApplication


def map_tooltip_bounds(bounds, origin, size, physical_cursor, logical_cursor, scale):
    x, y, width, height, viewport_width, viewport_height = bounds
    # Anchor at the cursor's corresponding physical/logical points so negative
    # monitor origins and per-monitor DPI do not get divided as global offsets.
    return QRectF(logical_cursor.x() + (origin.x + x * size[0] / viewport_width - physical_cursor.x) / scale,
        logical_cursor.y() + (origin.y + y * size[1] / viewport_height - physical_cursor.y) / scale,
        width * size[0] / viewport_width / scale,
        height * size[1] / viewport_height / scale).toAlignedRect()


class GameForeground:
    def __init__(self):
        self.checked = 0
        self.identity = None
        self.path = None
        self.user = self.kernel = None
        if sys.platform != 'win32': return
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        functions = [
            (self.user.GetForegroundWindow, [], wintypes.HWND),
            (self.user.GetWindowThreadProcessId, [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            (self.user.GetClientRect, [wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            (self.user.GetCursorPos, [ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            (self.user.ScreenToClient, [wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            (self.user.ClientToScreen, [wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            (self.kernel.OpenProcess, [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            (self.kernel.CloseHandle, [wintypes.HANDLE], wintypes.BOOL),
            (self.kernel.QueryFullProcessImageNameW, [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL)]
        for function, args, result in functions:
            function.argtypes, function.restype = args, result

    def __call__(self, game):
        if not self.user or not game: return False
        hwnd = self.user.GetForegroundWindow()
        if not hwnd: return False
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        now = time.monotonic()
        if self.identity != (hwnd, pid.value) or now - self.checked > 1:
            self.identity, self.checked, self.path = (hwnd, pid.value), now, None
            process = self.kernel.OpenProcess(0x1000, False, pid.value)
            if process:
                try:
                    buffer = ctypes.create_unicode_buffer(32768); length = wintypes.DWORD(len(buffer))
                    if self.kernel.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(length)):
                        self.path = Path(buffer.value)
                finally:
                    self.kernel.CloseHandle(process)
        if self.path is None or self.path != game.exe: return False
        rect, point = wintypes.RECT(), wintypes.POINT()
        return bool(self.user.GetClientRect(hwnd, ctypes.byref(rect)) and self.user.GetCursorPos(ctypes.byref(point))
            and self.user.ScreenToClient(hwnd, ctypes.byref(point))
            and rect.left <= point.x < rect.right and rect.top <= point.y < rect.bottom)

    def map_bounds(self, bounds):
        if not bounds or not self.identity: return None
        hwnd = self.identity[0]
        rect, origin, cursor = wintypes.RECT(), wintypes.POINT(), wintypes.POINT()
        if not (self.user.GetClientRect(hwnd, ctypes.byref(rect)) and
                self.user.ClientToScreen(hwnd, ctypes.byref(origin)) and self.user.GetCursorPos(ctypes.byref(cursor))):
            return None
        point = QCursor.pos()
        screen = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
        return map_tooltip_bounds(bounds, origin, (rect.right, rect.bottom), cursor, point, screen.devicePixelRatio())
