"""游戏定位与状态检测：Steam 库检测链、版本读取、日志路径、进程管理、基座档案检查。

战场兄弟 Steam AppID = 365360，游戏为 32 位构建（win32/BattleBrothers.exe），
官方档案 data_001.dat ~ data_010.dat 是无加密 ZIP 容器（PhysicsFS 挂载）。
"""
from __future__ import annotations

import ctypes
import html
import os
import re
import shutil
import subprocess
import zipfile
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

APP_ID = "365360"
GAME_DIRNAME = "Battle Brothers"
SUPPORTED_VERSION = "1.5.2.3"
EXE_NAME = "BattleBrothers.exe"

# 官方档案号 → DLC 名称（002/005/007/009 官方留空）
OFFICIAL_ARCHIVES: dict[str, str | None] = {
    "data_001.dat": None,  # 本体
    "data_003.dat": "Lindwurm",
    "data_004.dat": "Beasts & Exploration",
    "data_006.dat": "Warriors of the North",
    "data_008.dat": "Blazing Deserts",
    "data_010.dat": "Of Flesh and Faith",
}

# ZIP 日期仅作元数据提示，不能据此认定汉化、重打包或 RNG 改动。
_REPACK_YEAR_THRESHOLD = 2024


@dataclass
class GameInfo:
    root: Path
    exe: Path
    version: str | None
    data_dir: Path

    @property
    def version_ok(self) -> bool:
        return self.version == SUPPORTED_VERSION


@dataclass
class BaseArchiveStatus:
    """data_001.dat 的可读性和日期信息；不验证是否为官方原始内容。"""

    path: Path
    entry_count: int = 0
    recent_entries: int = 0
    repacked: bool = False
    newest_year: int | None = None
    read_error: str | None = None

    @property
    def summary(self) -> str:
        if self.read_error:
            return "无法读取"
        return "日期较新（未校验内容）" if self.repacked else "可读取（未校验内容）"

    @property
    def warning(self) -> str | None:
        if self.read_error:
            return f"无法读取游戏档案 {self.path.name}：{self.read_error}"
        if self.repacked:
            return (
                f"{self.path.name} 中 {self.recent_entries}/{self.entry_count} 个条目的日期"
                f"为 {_REPACK_YEAR_THRESHOLD} 年或之后。日期不能证明游戏经过汉化或重打包，"
                "也不能证明种子受到影响；本检查未比对官方文件内容。"
            )
        return None


def find_steam_root() -> Path | None:
    """从注册表读取 Steam 安装路径（HKCU 优先，HKLM 兜底）。"""
    try:
        import winreg

        for hive, sub in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        ):
            try:
                with winreg.OpenKey(hive, sub) as key:
                    value, _ = winreg.QueryValueEx(key, "SteamPath" if hive == winreg.HKEY_CURRENT_USER else "InstallPath")
                    p = Path(str(value))
                    if p.exists():
                        return p
            except OSError:
                continue
    except ImportError:
        pass
    return None


def list_steam_libraries(steam_root: Path) -> list[Path]:
    """解析 libraryfolders.vdf 枚举全部 Steam 库（含主库）。"""
    libs = [steam_root]
    vdf = steam_root / "steamapps" / "libraryfolders.vdf"
    try:
        text = vdf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return libs
    for m in re.finditer(r'"path"\s+"([^"]+)"', text):
        p = Path(m.group(1).replace("\\\\", "\\"))
        try:
            if p not in libs and p.is_dir():
                libs.append(p)
        except OSError:
            # Steam may retain libraries on disconnected or inaccessible drives.
            continue
    return libs


def _inspect_game(root: Path) -> GameInfo | None:
    """An unavailable candidate must not prevent the application from opening."""
    exe = root / "win32" / EXE_NAME
    data_dir = root / "data"
    try:
        if not exe.is_file() or not data_dir.is_dir():
            return None
    except OSError:
        return None
    return GameInfo(root=root, exe=exe, version=read_file_version(exe), data_dir=data_dir)


def locate_game(manual_hint: str | None = None) -> GameInfo | None:
    """检测链：手动指定 → 注册表+libraryfolders.vdf 扫描 → 常见盘符兜底。"""
    if manual_hint:
        # Preserve the user's choice even when it is unavailable; do not switch
        # silently to a different installation with different MODs and settings.
        return _inspect_game(Path(manual_hint))
    steam = find_steam_root()
    if steam:
        for lib in list_steam_libraries(steam):
            found = _inspect_game(lib / "steamapps" / "common" / GAME_DIRNAME)
            if found:
                return found
    # 兜底：扫常见盘符的默认 Steam 库位置
    # A bare "D:" is drive-relative on Windows; the slash anchors it at the root.
    for drive in ("C:/", "D:/", "E:/", "F:/", "G:/"):
        for library in ("SteamLibrary", "Program Files (x86)/Steam"):
            found = _inspect_game(Path(drive) / library / "steamapps" / "common" / GAME_DIRNAME)
            if found:
                return found
    return None


def read_file_version(path: Path) -> str | None:
    """用 win32 版本 API 读 PE 文件的 FileVersion（纯 ctypes，无第三方依赖）。"""
    try:
        dll = ctypes.windll.version
        size = dll.GetFileVersionInfoSizeW(str(path), None)
        if not size:
            return None
        data = ctypes.create_string_buffer(size)
        if not dll.GetFileVersionInfoW(str(path), 0, size, data):
            return None

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", ctypes.c_uint32),
                ("dwStrucVersion", ctypes.c_uint32),
                ("dwFileVersionMS", ctypes.c_uint32),
                ("dwFileVersionLS", ctypes.c_uint32),
                ("dwProductVersionMS", ctypes.c_uint32),
                ("dwProductVersionLS", ctypes.c_uint32),
            ]

        value = ctypes.c_void_p()
        length = ctypes.c_uint()
        if not dll.VerQueryValueW(data, "\\", ctypes.byref(value), ctypes.byref(length)):
            return None
        ffi = ctypes.cast(value, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        ms, ls = ffi.dwFileVersionMS, ffi.dwFileVersionLS
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:
        return None


def installed_dlcs(data_dir: Path) -> dict[str, bool]:
    """DLC 安装情况（按官方档案存在性）。"""
    result: dict[str, bool] = {}
    for fname, dlc in OFFICIAL_ARCHIVES.items():
        if dlc:
            result[dlc] = (data_dir / fname).exists()
    return result


def check_base_archive(data_dir: Path) -> BaseArchiveStatus | None:
    """读取 ZIP 目录元数据，不以日期推断修改者、修改内容或种子兼容性。"""
    path = data_dir / "data_001.dat"
    if not path.exists():
        return None
    status = BaseArchiveStatus(path=path)
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            status.entry_count = len(infos)
            years: list[int] = []
            for info in infos:
                y = info.date_time[0]
                years.append(y)
                if y >= _REPACK_YEAR_THRESHOLD:
                    status.recent_entries += 1
            if years:
                status.newest_year = max(years)
    except (zipfile.BadZipFile, OSError) as error:
        status.read_error = str(error)
        return status
    if not status.entry_count:
        status.read_error = "档案为空"
    # repacked 是保留的旧字段名，只表示多数条目日期较新。
    if status.entry_count and status.recent_entries / status.entry_count > 0.5:
        status.repacked = True
    return status


@lru_cache(maxsize=1)
def documents_path() -> Path | None:
    """Ask Windows for Documents, including folders redirected to another drive."""
    if os.name != "nt":
        return None

    class GUID(ctypes.Structure):
        _fields_ = [("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16),
                    ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8)]

    folder = GUID.from_buffer_copy(uuid.UUID("fdd39ad0-238f-46af-adb4-6c85480369c7").bytes_le)
    pointer = ctypes.c_void_p()
    try:
        lookup = ctypes.windll.shell32.SHGetKnownFolderPath
        lookup.argtypes = [ctypes.POINTER(GUID), ctypes.c_uint32, ctypes.c_void_p,
                           ctypes.POINTER(ctypes.c_void_p)]
        lookup.restype = ctypes.c_long
        if lookup(ctypes.byref(folder), 0, None, ctypes.byref(pointer)) == 0:
            return Path(ctypes.wstring_at(pointer))
    except (AttributeError, OSError):
        pass
    finally:
        if pointer.value:
            free = ctypes.windll.ole32.CoTaskMemFree
            free.argtypes = [ctypes.c_void_p]
            free.restype = None
            free(pointer)
    return None


def find_log_write_paths(preferred: Path | None = None) -> list[Path]:
    """All plausible folders; live readers still verify their session marker."""
    documents = documents_path()
    candidates = ([Path(preferred)] if preferred else [])
    if documents:
        candidates.append(documents / GAME_DIRNAME)
    candidates += [Path.home() / "Documents" / GAME_DIRNAME,
                   Path.home() / "OneDrive" / "Documents" / GAME_DIRNAME]
    candidates += [Path(value) / "Documents" / GAME_DIRNAME
                   for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")
                   if (value := os.environ.get(key))]
    unique: dict[str, Path] = {}
    for folder in candidates:
        unique.setdefault(os.path.normcase(str(folder.absolute())), folder)
    for folder in list(unique.values()):
        try:
            with (folder / "log.html").open("rb") as stream:
                head = stream.read(8192).decode("utf-8", errors="replace")
            match = re.search(r"Using write path:\s*([^<\r\n]+)", head)
            if match:
                reported = Path(html.unescape(match[1]).strip())
                if reported.is_absolute() and reported.is_dir():
                    unique.setdefault(os.path.normcase(str(reported.absolute())), reported)
        except OSError:
            continue

    def modified(folder: Path) -> int:
        try:
            return (folder / "log.html").stat().st_mtime_ns
        except OSError:
            return 0

    return sorted(unique.values(), key=lambda folder: (folder == preferred, modified(folder)), reverse=True)


def find_log_write_path() -> Path | None:
    """Best existing folder for diagnostics; generation monitors every candidate."""
    return next((folder for folder in find_log_write_paths() if folder.is_dir()), None)


# ---------------- 进程管理 ----------------

def is_game_running() -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return EXE_NAME.lower() in out.lower()


def launch_executable(game: GameInfo) -> dict:
    """Use the desktop launch path for both ordinary play and seed searches."""
    executable = game.exe.resolve()
    if hasattr(os, 'startfile'):
        # Steam can relaunch its registered installation; copied games must
        # never escape the directory protected by the active MOD transaction.
        steam = find_steam_root()
        registered = []
        for library in list_steam_libraries(steam) if steam else []:
            manifest = library / 'steamapps' / f'appmanifest_{APP_ID}.acf'
            if not manifest.is_file():
                continue
            match = re.search(r'"installdir"\s+"([^"\r\n]+)"',
                              manifest.read_text(encoding='utf-8-sig', errors='replace'))
            common = (library / 'steamapps/common').resolve()
            installed = (common / (match[1] if match else GAME_DIRNAME)).resolve()
            if installed.is_relative_to(common) and installed.is_dir():
                registered.append(installed)
        if registered and game.root.resolve() not in registered:
            raise RuntimeError('当前目录不是 Steam 注册的游戏目录。为防止隔离测试跳到常用游戏，已停止启动。请在 BBMOD 中选择 Steam 已安装的游戏目录：\n' + '\n'.join(map(str, registered)))
        os.startfile(str(executable), cwd=str(executable.parent))
        return {'mode': 'current'}
    environment = dict(os.environ)
    for key in list(environment):
        if key.startswith(('BBMOD_FONT_', 'BBMOD_PLACE_NAMES_')):
            environment.pop(key)
    process = subprocess.Popen([str(executable)], cwd=str(executable.parent), env=environment)
    return {'pid': process.pid, 'mode': 'current'}


def launch_game(game: GameInfo, via_steam: bool = True) -> bool:
    """启动游戏。默认走 steam://run/365360（保证 Steamworks/DLC 正常初始化）。"""
    if via_steam:
        try:
            os.startfile(f"steam://run/{APP_ID}//")  # noqa: SIM115 - Windows 专用
            return True
        except OSError:
            pass
    try:
        launch_executable(game)
        return True
    except OSError:
        return False


def kill_game() -> bool:
    """强制结束游戏进程（刷种子循环无出口，结束进程是唯一停止方式）。"""
    try:
        r = subprocess.run(
            ["taskkill", "/IM", EXE_NAME, "/F", "/T"],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def open_folder(path: Path) -> None:
    if path.exists():
        os.startfile(str(path))  # noqa: SIM115
