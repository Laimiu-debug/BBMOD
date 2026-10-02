"""Only public BBMOD identifiers can be opened through the desktop URL handler."""
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
import uuid

from .site_config import SITE_ORIGIN
from .online_catalog import _request
from .seedgen.protocol import MAX_SHARE_BYTES, validate_share


def parse_link(value):
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError('网页链接无效。')
    parts = urlsplit(value)
    if (parts.scheme != 'bbmod' or parts.netloc not in {'mods', 'seeds', 'profiles'}
            or parts.query or parts.fragment or not parts.path.startswith('/')):
        raise ValueError('只支持 BBMOD 的 MOD、种子或共享方案链接。')
    identity = parts.path[1:]
    try:
        if str(uuid.UUID(identity)) != identity:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError('作品或种子编号无效。') from None
    return parts.netloc, identity


def fetch_seed(identity):
    parse_link('bbmod://seeds/' + identity)
    with _request(SITE_ORIGIN + '/api/v1/seeds/' + identity + '/') as response:
        raw = response.read(MAX_SHARE_BYTES + 1)
    if len(raw) > MAX_SHARE_BYTES:
        raise ValueError('种子档案超过大小限制。')
    return validate_share(json.loads(raw))


def register_protocol():
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        raise ValueError('请在 Windows 单文件版中启用网页联动。')
    import winreg
    executable = str(Path(sys.executable).resolve())
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\bbmod') as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'URL:BBMOD')
        winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\bbmod\shell\open\command') as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, f'"{executable}" --open-url "%1"')


def retarget_protocol(current: Path, target: Path):
    """Keep an existing opt-in URL handler working after a versioned rename."""
    if sys.platform != 'win32':
        return
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r'Software\Classes\bbmod\shell\open\command', 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except FileNotFoundError:
        return
    with key:
        command, kind = winreg.QueryValueEx(key, '')
        if kind == winreg.REG_SZ and command == f'"{current}" --open-url "%1"':
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, f'"{target}" --open-url "%1"')
