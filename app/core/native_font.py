"""Load our Chinese map renderer into a supported, newly launched game."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess

from .paths import resource_path

SUPPORTED_EXE_SHA256 = '345126b48b57719e71c80cd21b778f1a0bfda52295cc136ce3895ef43bbafd6a'

def check_executable(exe: Path) -> None:
    if hashlib.sha256(Path(exe).read_bytes()).hexdigest() != SUPPORTED_EXE_SHA256:
        raise ValueError('当前游戏主程序尚未通过中文地图字体适配验证。当前支持 Steam 原版 1.5.2.3。')

def _assets() -> dict[str, Path]:
    folder = resource_path('native/bin')
    if not folder.is_dir(): folder = resource_path('build/native')
    files = {'bbmod_launch.exe': folder/'bbmod_launch.exe', 'bbmod_han.dll': folder/'bbmod_han.dll',
             'NotoSerifSC-SemiBold.ttf': resource_path('localization/NotoSerifSC-SemiBold.ttf'),
             'FONT-LICENSE.txt': resource_path('localization/MAP-FONT-LICENSE.txt')}
    license_path = resource_path('native/licenses/LICENSE.txt')
    if not license_path.is_file(): license_path = resource_path('native/vendor/minhook/LICENSE.txt')
    files['MINHOOK-LICENSE.txt'] = license_path
    if not all(p.is_file() for p in files.values()):
        raise FileNotFoundError('缺少中文地图字体组件，请使用完整的 BBMOD 软件包。')
    return files

def prepare_runtime(parent: Path, place_data: bytes | None = None) -> Path:
    assets = _assets()
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name,path in assets.items()}
    if place_data is not None:
        hashes['place_names.tsv'] = hashlib.sha256(place_data).hexdigest()
    version = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    target = Path(parent)/'chinese-font'/version
    target.mkdir(parents=True,exist_ok=True)
    # A persistent private copy outlives a one-file manager's temporary folder.
    for name,source in assets.items():
        path = target/name
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == hashes[name]: continue
        pending = path.with_suffix(path.suffix+'.tmp')
        pending.write_bytes(source.read_bytes())
        pending.replace(path)
    if place_data is not None:
        path = target/'place_names.tsv'
        if not path.exists() or path.read_bytes() != place_data:
            pending = path.with_suffix('.tmp')
            pending.write_bytes(place_data)
            pending.replace(path)
    (target/'manifest.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    return target

def launch_localized(game, runtime_root: Path, *, place_package: Path | None = None) -> dict:
    from .game import is_game_running
    if is_game_running():
        raise RuntimeError('游戏已在运行。请先关闭游戏，再使用“以中文启动”。')
    check_executable(game.exe)
    from .place_display import read_packaged_display
    place_data = read_packaged_display(place_package) if place_package is not None else None
    runtime = prepare_runtime(runtime_root, place_data)
    log = runtime/'last-launch.log'
    log.write_text('',encoding='utf-8')
    environment = dict(os.environ)
    # Never inherit a previous process's language mode; it belongs to this launch.
    for key in ('BBMOD_PLACE_NAMES_PATH', 'BBMOD_PLACE_NAMES_SHA256'):
        environment.pop(key, None)
    if place_data is not None:
        environment['BBMOD_PLACE_NAMES_PATH'] = str(runtime/'place_names.tsv')
        environment['BBMOD_PLACE_NAMES_SHA256'] = hashlib.sha256(place_data).hexdigest()
    result = subprocess.run([str(runtime/'bbmod_launch.exe'),str(game.exe),str(runtime/'bbmod_han.dll'),
                             str(runtime/'NotoSerifSC-SemiBold.ttf'),str(log)], env=environment,
                            cwd=str(game.exe.parent),capture_output=True,timeout=60,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise RuntimeError('中文启动未完成，请查看启动记录：'+str(log))
    output = result.stdout.decode('ascii',errors='ignore').strip()
    if not output.isdigit(): raise RuntimeError('启动结果不完整，请查看游戏窗口和启动记录。')
    return {'pid':int(output),'log':str(log)}
