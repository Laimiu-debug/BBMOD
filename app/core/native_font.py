"""Load our Chinese map renderer into a supported, newly launched game."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess

from .paths import resource_path

SUPPORTED_EXE_SHA256 = '345126b48b57719e71c80cd21b778f1a0bfda52295cc136ce3895ef43bbafd6a'

class NativeComponentError(RuntimeError):
    """The font adapter is unavailable; never retry extraction or launch."""


def check_executable(exe: Path) -> None:
    if hashlib.sha256(Path(exe).read_bytes()).hexdigest() != SUPPORTED_EXE_SHA256:
        raise ValueError('当前游戏主程序尚未通过中文地图字体适配验证。当前支持 Steam 原版 1.5.2.3。')

def component_paths() -> dict[str, Path]:
    folder = resource_path('native/bin')
    if not folder.is_dir(): folder = resource_path('build/native')
    files = {'bbmod_launch.exe': folder/'bbmod_launch.exe', 'bbmod_han.dll': folder/'bbmod_han.dll',
             'NotoSerifSC-SemiBold.ttf': resource_path('localization/NotoSerifSC-SemiBold.ttf'),
             'FONT-LICENSE.txt': resource_path('localization/MAP-FONT-LICENSE.txt')}
    license_path = resource_path('native/licenses/LICENSE.txt')
    if not license_path.is_file(): license_path = resource_path('native/vendor/minhook/LICENSE.txt')
    files['MINHOOK-LICENSE.txt'] = license_path
    return files


def missing_components() -> list[str]:
    return [name for name, path in component_paths().items() if not path.is_file()]


def _unavailable(names, folder: Path) -> NativeComponentError:
    return NativeComponentError(
        '中文地名启动组件缺失或校验失败：' + '、'.join(names)
        + '\n位置：' + str(folder)
        + '\n请核对 Windows 安全中心的“保护历史记录”。文件缺失也可能由安装不完整或清理造成，不能仅凭缺失判断为隔离或误报。'
        + '\n本次未继续启动游戏，也未重新释放该组件。中文地名功能保留，等待组件问题处理完成。')


def _assets() -> dict[str, Path]:
    files = component_paths()
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        raise _unavailable(missing, files[missing[0]].parent)
    return files


def _validate_runtime(target: Path, hashes: dict[str, str]) -> None:
    invalid = [name for name, digest in hashes.items()
               if not (target/name).is_file()
               or hashlib.sha256((target/name).read_bytes()).hexdigest() != digest]
    if invalid:
        raise _unavailable(invalid, target)


def _check_previous_copies(parent: Path, hashes: dict[str, str]) -> None:
    # rc.5 included the place dictionary in the cache key. A changed dictionary
    # must not cause an identical missing/quarantined executable to be re-created
    # under a new cache directory. Only inspect receipts for these exact assets.
    for receipt in parent.glob('*/manifest.json'):
        try:
            saved = json.loads(receipt.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(saved, dict) and all(saved.get(name) == digest for name, digest in hashes.items()):
            _validate_runtime(receipt.parent, hashes)


def prepare_runtime(parent: Path, place_data: bytes | None = None) -> Path:
    assets = _assets()
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name,path in assets.items()}
    version = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    cache = Path(parent)/'chinese-font'
    _check_previous_copies(cache, hashes)
    target = cache/version
    if target.exists():
        # Treat incomplete initialization as a failed installation as well.
        # Do not silently repair executable files which disappeared later.
        receipt = target/'manifest.json'
        try:
            saved = json.loads(receipt.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise _unavailable(['manifest.json'], target) from error
        if not isinstance(saved, dict) or any(saved.get(name) != digest for name, digest in hashes.items()):
            raise _unavailable(['manifest.json'], target)
        _validate_runtime(target, hashes)
    else:
        target.mkdir(parents=True, exist_ok=False)
        # Record intent before copying so even an interrupted first extraction
        # is not automatically retried on the next click.
        (target/'manifest.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        for name, source in assets.items():
            with (target/name).open('xb') as stream:
                stream.write(source.read_bytes())
        _validate_runtime(target, hashes)
    if place_data is not None:
        path = _place_data_path(target, place_data)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != place_data:
                raise _unavailable(['place_names.tsv'], path.parent)
        else:
            with path.open('xb') as stream:
                stream.write(place_data)
    return target


def _place_data_path(runtime: Path, data: bytes) -> Path:
    return runtime/'places'/hashlib.sha256(data).hexdigest()/'place_names.tsv'


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
        environment['BBMOD_PLACE_NAMES_PATH'] = str(_place_data_path(runtime, place_data))
        environment['BBMOD_PLACE_NAMES_SHA256'] = hashlib.sha256(place_data).hexdigest()
    try:
        result = subprocess.run([str(runtime/'bbmod_launch.exe'),str(game.exe),str(runtime/'bbmod_han.dll'),
                             str(runtime/'NotoSerifSC-SemiBold.ttf'),str(log)], env=environment,
                            cwd=str(game.exe.parent),capture_output=True,timeout=60,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except OSError as error:
        if not (runtime/'bbmod_launch.exe').is_file() or getattr(error, 'winerror', None) in {225, 226}:
            raise _unavailable(['bbmod_launch.exe'], runtime) from error
        raise
    if result.returncode:
        raise RuntimeError('中文启动未完成，请查看启动记录：'+str(log))
    output = result.stdout.decode('ascii',errors='ignore').strip()
    if not output.isdigit(): raise RuntimeError('启动结果不完整，请查看游戏窗口和启动记录。')
    return {'pid':int(output),'log':str(log)}
