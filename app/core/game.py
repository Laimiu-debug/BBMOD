"""游戏定位与状态检测：Steam 库检测链、版本读取、日志路径、进程管理、基座档案检查。

战场兄弟 Steam AppID = 365360，游戏为 32 位构建（win32/BattleBrothers.exe），
官方档案 data_001.dat ~ data_010.dat 是无加密 ZIP 容器（PhysicsFS 挂载）。
"""
from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
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
    if not vdf.exists():
        return libs
    try:
        text = vdf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return libs
    for m in re.finditer(r'"path"\s+"([^"]+)"', text):
        p = Path(m.group(1).replace("\\\\", "\\"))
        if p.exists() and p not in libs:
            libs.append(p)
    return libs


def locate_game(manual_hint: str | None = None) -> GameInfo | None:
    """检测链：手动指定 → 注册表+libraryfolders.vdf 扫描 → 常见盘符兜底。"""
    candidates: list[Path] = []
    if manual_hint:
        root = Path(manual_hint)
        exe = root / 'win32' / EXE_NAME
        if not exe.is_file() or not (root / 'data').is_dir():
            return None
        return GameInfo(root=root, exe=exe, version=read_file_version(exe), data_dir=root / 'data')
    steam = find_steam_root()
    if steam:
        for lib in list_steam_libraries(steam):
            manifest = lib / "steamapps" / f"appmanifest_{APP_ID}.acf"
            game_dir = lib / "steamapps" / "common" / GAME_DIRNAME
            if manifest.exists() and game_dir.exists():
                candidates.append(game_dir)
            elif game_dir.exists():
                candidates.append(game_dir)
    # 兜底：扫常见盘符的默认 Steam 库位置
    for drive in ("C:", "D:", "E:", "F:", "G:"):
        p = Path(drive, "SteamLibrary", "steamapps", "common", GAME_DIRNAME)
        if p.exists():
            candidates.append(p)
        p = Path(drive, "Program Files (x86)", "Steam", "steamapps", "common", GAME_DIRNAME)
        if p.exists():
            candidates.append(p)

    for root in candidates:
        exe = root / "win32" / EXE_NAME
        if exe.exists():
            return GameInfo(
                root=root,
                exe=exe,
                version=read_file_version(exe),
                data_dir=root / "data",
            )
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


def find_log_write_path() -> Path | None:
    r"""定位游戏实际写盘目录（Documents\Battle Brothers，含 OneDrive 重定向）。

    优先解析 log.html 首部的 "Using write path:" 行（游戏自述的权威来源），
    找不到再探测两个候选目录。
    """
    candidates = [
        Path.home() / "Documents" / "Battle Brothers",
        Path.home() / "OneDrive" / "Documents" / "Battle Brothers",
    ]
    for c in candidates:
        log = c / "log.html"
        if log.exists():
            try:
                head = log.read_bytes()[:8192]
                m = re.search(rb"Using write path:\s*([^<\r\n]+)", head)
                if m:
                    p = Path(m.group(1).decode("utf-8", errors="replace").strip())
                    if p.exists():
                        return p
            except OSError:
                pass
            return c
    for c in candidates:
        if c.exists():
            return c
    return None


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


def launch_game(game: GameInfo, via_steam: bool = True) -> bool:
    """启动游戏。默认走 steam://run/365360（保证 Steamworks/DLC 正常初始化）。"""
    if via_steam:
        try:
            os.startfile(f"steam://run/{APP_ID}//")  # noqa: SIM115 - Windows 专用
            return True
        except OSError:
            pass
    try:
        subprocess.Popen([str(game.exe)], cwd=str(game.exe.parent))
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
