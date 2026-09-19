"""Windows shell identity for the desktop/taskbar icon of the standalone app."""
import ctypes
import sys

APP_ID = 'BBMOD.WarbandManager'


def set_app_identity():
    """Set before creating any top-level Qt window; does not touch the icon cache."""
    if sys.platform != 'win32': return
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
    shell.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
    result = shell.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    if result < 0:
        raise OSError(f'Cannot set BBMOD Windows application identity: {result:#x}')
