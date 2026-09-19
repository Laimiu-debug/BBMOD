import hashlib
import json
import zipfile
from unittest.mock import patch

import pytest
from core.l10n import PACKAGE_ID,PACKAGE_NAME,BRAND_META
from tools import launch_preview


def preview(tmp_path,monkeypatch,session_places=False):
    monkeypatch.setattr(launch_preview,'ROOT',tmp_path)
    root=tmp_path/'build/full-l10n/game-check'
    data=root/'data';data.mkdir(parents=True)
    (root/'win32').mkdir();(root/'win32/BattleBrothers.exe').write_bytes(b'test executable')
    package=data/PACKAGE_NAME
    manifest={'package_id':PACKAGE_ID, 'place_name_display': 'mod_ui'}
    if session_places:manifest['place_name_display']='launcher_session'
    with zipfile.ZipFile(package,'w') as z:z.writestr(BRAND_META,json.dumps(manifest))
    guarded=b'test save guard'
    with zipfile.ZipFile(data/'mod_zz_bbmod_preview_guard.zip','w') as z:
        z.writestr('scripts/states/world_state.cnut',guarded)
        z.writestr('BBMOD_PREVIEW_GUARD.json',json.dumps({'package_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(guarded).hexdigest(),'disabled_functions':['autosave','saveCampaign'], 'automatic_campaign_start': False}))
    return root,data


def test_preview_routes_only_to_its_own_copy(tmp_path,monkeypatch):
    root,data=preview(tmp_path,monkeypatch)
    with patch('core.localization_profiles.LocalizationProfiles.launch',return_value={'pid':123}) as start:
        assert launch_preview.launch()=={'pid':123}
        assert start.call_args.args[0].root==root
        assert start.call_args.args[0].exe==root/'win32/BattleBrothers.exe'


def test_missing_preview_does_not_fall_back_to_steam(tmp_path,monkeypatch):
    monkeypatch.setattr(launch_preview,'ROOT',tmp_path)
    with patch('core.game.launch_executable') as start:
        with pytest.raises(FileNotFoundError,match='测试副本'):launch_preview.launch()
        start.assert_not_called()


def test_preview_rejects_retired_session_loader(tmp_path,monkeypatch):
    root,data=preview(tmp_path,monkeypatch,session_places=True)
    with patch('core.game.launch_executable',return_value={'pid':123}) as start:
        with pytest.raises(ValueError, match='旧启动器'):
            launch_preview.launch()
        start.assert_not_called()


def test_preview_rejects_extra_mods_without_opening_them(tmp_path,monkeypatch):
    root,data=preview(tmp_path,monkeypatch)
    (data/'unrelated.zip').write_bytes(b'not read')
    with patch('core.game.launch_executable') as start:
        with pytest.raises(ValueError,match='其他模组'):launch_preview.launch()
        start.assert_not_called()


def test_changed_package_requires_a_matching_save_guard(tmp_path,monkeypatch):
    root,data=preview(tmp_path,monkeypatch)
    with zipfile.ZipFile(data/PACKAGE_NAME,'a') as z:z.writestr('updated.txt','changed')
    with patch('core.game.launch_executable') as start:
        with pytest.raises(ValueError,match='测试包已更新'):launch_preview.launch()
        start.assert_not_called()
