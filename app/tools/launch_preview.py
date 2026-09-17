"""Launch this workspace's isolated preview, never Steam's regular installation."""
from __future__ import annotations
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def launch():
    from core.game import GameInfo, OFFICIAL_ARCHIVES
    from core.l10n import PACKAGE_NAME, package_manifest
    from core.native_font import launch_localized
    game_root=ROOT/'build/full-l10n/game-check'
    data=game_root/'data'
    # A missing or contaminated preview must not fall back to locate_game(),
    # because that would open the user's ordinary Steam/Fox installation.
    if not (game_root/'win32/BattleBrothers.exe').is_file():
        raise FileNotFoundError('独立测试副本尚未准备好。')
    guard_name='mod_zz_bbmod_preview_guard.zip'
    allowed={*OFFICIAL_ARCHIVES,PACKAGE_NAME,guard_name}
    unexpected=[p.name for p in data.iterdir() if p.is_file() and p.suffix.lower() in {'.zip','.dat'} and p.name not in allowed]
    if unexpected:
        raise ValueError('测试目录还含有其他模组，暂未启动：'+ '、'.join(unexpected))
    manifest=package_manifest(data/PACKAGE_NAME)
    if not manifest:
        raise FileNotFoundError('测试目录尚未安装独立汉化包。')
    # The preview uses a temporary campaign with saving disabled, because the
    # original game chooses the same Documents save folder for every copy.
    with zipfile.ZipFile(data/guard_name) as z:
        guard=json.loads(z.read('BBMOD_PREVIEW_GUARD.json'))
        if guard.get('script_sha256')!=hashlib.sha256(z.read('scripts/states/world_state.cnut')).hexdigest():
            raise ValueError('测试保护文件校验不一致。')
        if set(guard.get('disabled_functions',[]))!={'autosave','saveCampaign'}:
            raise ValueError('测试保护文件不完整。')
    if guard['package_sha256']!=hashlib.sha256((data/PACKAGE_NAME).read_bytes()).hexdigest():
        raise ValueError('测试包已更新，请先重新准备对应的测试保护文件。')
    os.environ['BBMOD_PREVIEW_TITLE']='BBMOD 独立汉化测试（开发中，不保存进度） | Battle Brothers 1.5.2.3'
    game=GameInfo(game_root,game_root/'win32/BattleBrothers.exe','1.5.2.3',data)
    if manifest.get('place_name_display') == 'launcher_session':
        return launch_localized(game,ROOT/'build/preview-runtime',place_package=data/PACKAGE_NAME)
    return launch_localized(game,ROOT/'build/preview-runtime')


if __name__=='__main__':
    try: launch()
    except Exception as error:
        ctypes.windll.user32.MessageBoxW(None,str(error),'BBMOD 独立测试启动未完成',0x10)
        raise SystemExit(1)
