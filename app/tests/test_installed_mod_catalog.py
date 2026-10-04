import hashlib
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from core.installed_mod_catalog import (read_local_sha256, receipt_needs_hash,
                                        resolve_installed_mod)
from core.modinfo import ModInfo, Registration
from core.site_config import SITE_ORIGIN


def mod(name='mod_example.zip', *, ids=('mod_example',), version='1.0.0', api='modern'):
    info = ModInfo(path=Path(name), file_name=name)
    info.registrations = [Registration(ident, version, 'Example', api) for ident in ids]
    return info


def release(name='mod_example.zip', *, ids=('mod_example',), version='1.1.0',
            title='示例 MOD', sha='b' * 64):
    ident = str(uuid.uuid4())
    return {'id': ident, 'version': version, 'file_name': name, 'sha256': sha,
            'page_path': f'/mods/{ident}/', 'metadata': {'title': title, 'mod_ids': list(ids)}}


def receipt(info, item, *, version='1.0.0', sha='a' * 64, origin=SITE_ORIGIN):
    return {info.file_name: {'id': item['id'], 'version': version,
                            'sha256': sha, 'origin': origin}}


def test_display_prefers_online_chinese_name_and_keeps_local_version_and_ids():
    info = mod()
    item = release()
    result = resolve_installed_mod(info, [item], local_index={info.file_name: {'name_cn': '离线名称'}})
    assert result.display_name == '示例 MOD'
    assert result.installed_version == '1.0.0'
    assert result.latest_version == '1.1.0'
    assert result.update_available and result.status == '有更新'
    assert result.update_url == SITE_ORIGIN + item['page_path']
    assert result.catalog_item is item
    assert 'mod_example' in result.tooltip and '脚本版本 1.0.0' in result.tooltip
    assert info.file_name in result.search_text


def test_offline_index_name_survives_no_network_and_renamed_single_registration():
    index = {'mod_example.zip': {'name_cn': '示例中文名', 'mod_ids': ['mod_example']}}
    assert resolve_installed_mod(mod(), local_index=index).display_name == '示例中文名'
    assert resolve_installed_mod(mod('renamed.zip'), local_index=index).display_name == '示例中文名'
    online = release(title='English title')
    assert resolve_installed_mod(mod(), [online], local_index=index).display_name == '示例中文名'


def test_ambiguous_index_registration_does_not_invent_a_name():
    index = {'one.zip': {'name_cn': '独立版', 'mod_ids': ['mod_example']},
             'two.zip': {'name_cn': '另一版', 'mod_ids': ['mod_example']}}
    assert resolve_installed_mod(mod('renamed.zip'), local_index=index).display_name == 'Example'


def test_package_identity_keeps_bundled_hooks_out_of_matching():
    info = mod('localization.zip', ids=('mod_hooks',), version='21.1', api='legacy')
    info.package_id = 'bbmod.independent.zh-CN'
    info.package_name = 'BBMOD 独立汉化'
    info.package_version = '2026.10.03'
    hooks = release('hooks.zip', ids=('mod_hooks',), title='旧版 Hooks')
    result = resolve_installed_mod(info, [hooks], local_index={})
    assert result.display_name == 'BBMOD 独立汉化'
    assert result.installed_version == '2026.10.03'
    assert result.catalog_item is None and not result.update_available
    package = release('other-name.zip', ids=(info.package_id,), version='2026.10.04')
    result = resolve_installed_mod(info, [hooks, package], local_index={})
    assert result.matched_by == 'package_id' and result.catalog_item is package


def modern_hooks_fixture(name='mod_fox_008.zip'):
    info = mod(name, ids=())
    info.registrations = [Registration('Modern Hooks', '0.6.0', None, 'modern'),
                          Registration('vanilla', '', 'Vanilla', 'modern'),
                          Registration('dlc', '1.0.0', None, 'modern'),
                          Registration('mod_modern_hooks', '0.6.0', 'Modern Hooks', 'modern')]
    return info


def test_real_modern_hooks_placeholders_and_alias_do_not_hide_framework_name_or_version():
    info = modern_hooks_fixture()
    item = release(info.file_name, ids=('mod_modern_hooks',), version='0.6.1', title='现代 Hooks 框架')
    result = resolve_installed_mod(info, [item], local_index={})
    assert result.catalog_item is item and result.matched_by == 'file_name'
    assert result.display_name == '现代 Hooks 框架'
    assert result.installed_version == '0.6.0' and result.update_available
    assert 'Vanilla' in result.tooltip and 'dlc' in result.tooltip
    assert resolve_installed_mod(info, local_index={}).display_name == 'Modern Hooks'


def test_modern_hooks_filter_preserves_unrelated_bundle_mods_and_package_identity():
    info = modern_hooks_fixture('renamed.zip')
    hooks = release('framework.zip', ids=('mod_modern_hooks',), title='现代 Hooks 框架')
    bundle = release('fox.zip', ids=('mod_modern_hooks', 'mod_translation'), title='狐狸汉化')
    assert resolve_installed_mod(info, [hooks, bundle], local_index={}).catalog_item is hooks
    assert resolve_installed_mod(info, [bundle], local_index={}).catalog_item is None
    info.registrations.append(Registration('mod_translation', '1.0.0', '汉化', 'modern'))
    result = resolve_installed_mod(info, [hooks, bundle], local_index={})
    assert result.catalog_item is bundle and result.installed_version == '多版本'
    info.package_id = 'bbmod.independent.zh-CN'
    info.package_name = 'BBMOD 独立汉化'
    assert resolve_installed_mod(info, [hooks, bundle], local_index={}).catalog_item is None


def test_vanilla_and_dlc_registrations_are_not_generally_filtered():
    info = mod(ids=('vanilla', 'dlc'), version='1.0.0')
    item = release('other.zip', ids=('vanilla',))
    result = resolve_installed_mod(info, [item], local_index={})
    assert result.catalog_item is None and result.installed_version == '多版本'


@pytest.mark.parametrize('local_ids,remote_ids', [
    (('mod_example',), ('mod_example', 'mod_other')),
    (('mod_example', 'mod_other'), ('mod_example',)),
    (('mod_different',), ('mod_example',)),
])
def test_same_filename_with_conflicting_identity_is_not_associated(local_ids, remote_ids):
    result = resolve_installed_mod(mod(ids=local_ids), [release(ids=remote_ids)], local_index={})
    assert result.catalog_item is None and not result.update_available


def test_renamed_bundle_and_standalone_matching_requires_complete_id_set():
    info = mod('renamed.zip', ids=('mod_example', 'mod_other'))
    standalone = release('standalone.zip')
    bundle = release('bundle.zip', ids=('mod_example', 'mod_other'))
    result = resolve_installed_mod(info, [standalone, bundle], local_index={})
    assert result.catalog_item is bundle
    assert result.installed_version == '多版本' and result.status == '版本待确认'
    assert 'mod_example' in result.tooltip and 'mod_other' in result.tooltip
    duplicate = release('alternative.zip', ids=('mod_example', 'mod_other'))
    assert resolve_installed_mod(info, [bundle, duplicate], local_index={}).catalog_item is None


def test_duplicate_catalog_filename_does_not_choose_arbitrarily():
    assert resolve_installed_mod(mod(), [release(), release()], local_index={}).catalog_item is None


def test_unregistered_resource_uses_exact_filename_but_cannot_claim_an_update():
    info = mod(ids=())
    item = release(ids=())
    result = resolve_installed_mod(info, [item], local_index={})
    assert result.display_name == '示例 MOD'
    assert result.installed_version == '未识别' and result.status == '版本待确认'
    assert not result.update_available


def test_internal_script_revision_does_not_compare_with_release_version():
    info = mod(version='63', api='legacy')
    result = resolve_installed_mod(info, [release(version='0.28.14')], local_index={})
    assert result.installed_version == '63'
    assert result.latest_version == '0.28.14' and result.status == '版本待确认'
    assert not result.update_available
    assert '无法直接比较' in result.tooltip


def test_verified_receipt_connects_script_revision_to_release_version():
    info = mod(version='62', api='legacy')
    item = release(version='0.28.14')
    recorded = receipt(info, item, version='0.28.12', origin='https://bbmod.site')
    assert receipt_needs_hash(info, recorded)
    result = resolve_installed_mod(info, [item], receipts=recorded,
                                   local_sha256='a' * 64, local_index={})
    assert result.installed_version == '0.28.12'
    assert result.version_source == 'receipt' and result.update_available
    assert '脚本版本 62' in result.tooltip


@pytest.mark.parametrize('digest,origin', [('', SITE_ORIGIN), ('c' * 64, SITE_ORIGIN),
                                         ('a' * 64, 'https://foreign.example')])
def test_stale_missing_or_foreign_receipt_does_not_supply_release_version(digest, origin):
    info = mod(version='62', api='legacy')
    item = release(version='0.28.14')
    result = resolve_installed_mod(info, [item], receipts=receipt(info, item, origin=origin),
                                   local_sha256=digest, local_index={})
    assert result.installed_version == '62' and not result.update_available


def test_stale_receipt_cannot_identify_a_different_replacement_mod():
    info = mod('renamed.zip', ids=('mod_unrelated',), version='8.0.0')
    item = release()
    result = resolve_installed_mod(info, [item], receipts=receipt(info, item),
                                   local_sha256='c' * 64, local_index={})
    assert result.catalog_item is None


def test_hash_of_current_release_proves_release_version_without_receipt():
    info = mod(version='63', api='legacy')
    item = release(version='0.28.14')
    result = resolve_installed_mod(info, [item], local_sha256=item['sha256'], local_index={})
    assert result.installed_version == '0.28.14' and result.version_source == 'catalog_hash'
    assert result.status == '已是最新' and not result.update_available


def test_hash_of_current_release_proves_arbitrary_release_label_is_current():
    info = mod(version='63', api='legacy')
    item = release(version='2026.9.27-fox.1')
    result = resolve_installed_mod(info, [item], local_sha256=item['sha256'], local_index={})
    assert result.installed_version == item['version'] and result.status == '已是最新'
    assert not result.update_available
    older = resolve_installed_mod(info, [item], local_sha256='a' * 64, local_index={},
                                  release_versions={item['id']: {'a' * 64: '2026.9.26-fox.1'}})
    assert older.status == '版本待确认' and not older.update_available


def test_known_old_release_hash_resolves_release_version_and_update():
    info = mod(version='62', api='legacy')
    item = release(version='0.28.14')
    histories = {item['id']: {'a' * 64: '0.28.12'}, 'another-work': {'a' * 64: '9.9.9'}}
    result = resolve_installed_mod(info, [item], local_sha256='a' * 64,
                                   release_versions=histories, local_index={})
    assert result.installed_version == '0.28.12' and result.update_available
    unknown = resolve_installed_mod(info, [item], local_sha256='c' * 64,
                                    release_versions=histories, local_index={})
    assert unknown.installed_version == '62' and not unknown.update_available


@pytest.mark.parametrize('source', ['catalog_hash', 'receipt'])
def test_verified_afei_preview_release_enables_update(source):
    info = mod(version='76', api='legacy')
    item = release(version='0.29.0-preview.13')
    recorded = receipt(info, item, version='0.29.0-preview.12') if source == 'receipt' else None
    histories = {item['id']: {'a' * 64: '0.29.0-preview.12'}} if source == 'catalog_hash' else None
    result = resolve_installed_mod(info, [item], local_sha256='a' * 64,
                                   receipts=recorded, release_versions=histories, local_index={})
    assert result.installed_version == '0.29.0-preview.12'
    assert result.version_source == source and result.update_available
    assert result.status == '有更新'


def test_equal_release_versions_with_different_hashes_do_not_claim_an_update():
    info = mod(version='1.1.0')
    result = resolve_installed_mod(info, [release()], local_sha256='c' * 64, local_index={})
    assert result.status == '已是最新' and not result.update_available


@pytest.mark.parametrize('local,latest,status', [
    ('v1.2.0', '1.10.0', '有更新'), ('1.2.0-rc.2', '1.2.0-rc.10', '有更新'),
    ('1.2.0-rc.10', '1.2.0', '有更新'), ('1.2.1', '1.2.0', '本地版本较新'),
    ('0.29.0-preview.2', '0.29.0-preview.13', '有更新'),
    ('0.29.0-preview.13', '0.29.0-rc.1', '有更新'),
    ('0.29.0-preview.13', '0.29.0', '有更新'),
    ('0.29.0-preview.13', '0.29.0-preview.12', '本地版本较新'),
    ('1.2.0', 'v1.2.0', '已是最新'), ('nightly', '1.2.0', '版本待确认'),
    ('1.2', '1.2.1', '版本待确认'),
    ('9' * 5000, '1.2.0', '版本待确认'),
])
def test_release_comparison_is_numeric_and_prerelease_aware(local, latest, status):
    result = resolve_installed_mod(mod(version=local), [release(version=latest)], local_index={})
    assert result.status == status
    assert result.update_available == (status == '有更新')


@pytest.mark.parametrize('path', ['//foreign.example/', '/mods/other/', 'javascript:alert(1)'])
def test_invalid_website_path_never_enables_update(path):
    item = release()
    item['page_path'] = path
    result = resolve_installed_mod(mod(), [item], local_index={})
    assert result.page_path == result.update_url == '' and not result.update_available


def test_receipt_hashes_only_usable_same_site_records():
    info, item = mod(), release()
    assert not receipt_needs_hash(info, {})
    assert not receipt_needs_hash(info, receipt(info, item, origin='https://foreign.example'))
    assert not receipt_needs_hash(info, receipt(info, item, sha='bad'))
    assert not receipt_needs_hash(info, receipt(info, item), origin='javascript:evil')


def test_read_hash_and_missing_files_are_read_only(tmp_path):
    path = tmp_path / 'fixture.zip'
    path.write_bytes(b'local fixture')
    info = ModInfo(path, path.name)
    assert read_local_sha256(info) == hashlib.sha256(b'local fixture').hexdigest()
    assert path.read_bytes() == b'local fixture'
    path.unlink()
    assert read_local_sha256(info) == ''


def test_read_hash_rejects_file_changed_during_read(tmp_path):
    path = tmp_path / 'fixture.zip'
    path.write_bytes(b'first')
    original = hashlib.file_digest
    def changed(source, algorithm):
        digest = original(source, algorithm)
        path.write_bytes(b'replaced with other bytes')
        return digest
    with patch('core.installed_mod_catalog.hashlib.file_digest', side_effect=changed):
        assert read_local_sha256(ModInfo(path, path.name)) == ''
