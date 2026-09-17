"""Publish the checked rc.2 artifacts. Never install or launch the game."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from core.place_display import read_packaged_display

DIST=APP/'dist'
WORK=APP/'build/session-place-names'
BACKUP=WORK/'before/dist'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path,raw):
    assert path.resolve().is_relative_to(DIST.resolve())
    if path.exists():
        backup=BACKUP/path.name
        if backup.exists() and sha(backup)!=sha(path):
            backup=BACKUP/(path.stem+'-'+sha(path)[:16]+path.suffix)
        if not backup.exists():shutil.copy2(path,backup)
        assert sha(backup)==sha(path)
    pending=path.with_suffix(path.suffix+'.pending')
    pending.write_bytes(raw)
    assert pending.read_bytes()==raw
    pending.replace(path)


def main():
    paths={
        'structure':APP/'build/full-l10n/preview-package/validation.json',
        'composed':APP/'build/full-l10n/skill-text-validation/validation.json',
        'canonical_names':APP/'build/full-l10n/place-name-validation/validation.json',
        'display':WORK/'validation/validation.json',
        'compatibility':APP/'build/review/star-rating-compatibility/validation.json',
        'ui_input':WORK/'validation/ui-input.json',
        'frozen':APP/'build/review/place-display-exe-selftest.json',
    }
    reports={k:read(p) for k,p in paths.items()}
    package=APP/'build/full-l10n/preview-package/mod_bbmod_zhcn.zip'
    raw=read_packaged_display(package);package_hash=sha(package)
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(set(archive.namelist()))
        assert not any('preview_guard' in n for n in archive.namelist())
        manifest=json.loads(archive.read('BBMOD_L10N.json'))
    assert manifest['version']=='0.3.0-rc.2'
    assert manifest['place_name_display']=='launcher_session'
    assert manifest['place_name_save_policy']=='original_english_unchanged'
    assert manifest['place_display_sha256']==hashlib.sha256(raw).hexdigest()
    assert manifest['reviewed_place_entries']==2196 and manifest['expanded_place_names']==7723
    assert manifest['entry_count']==15815 and manifest['full_text_entries']==15629
    assert manifest['supports_direct_launch'] and manifest['uses_bbmod_map_font']
    previous=read(BACKUP/'validation.json')
    assert previous['version']=='0.3.0-rc.1'
    catalog=read(APP/'localization/full_catalog.json');catalog_hash=sha(APP/'localization/full_catalog.json')
    assert catalog_hash==previous['full_catalog_sha256']==manifest['full_catalog_sha256']
    assert catalog['editorial_review']['pending_non_geographic_entries']==0
    for name in ('structure','composed','canonical_names','display','compatibility'):
        assert reports[name]['package_sha256']==package_hash,name
    structure=reports['structure']
    assert structure['scripts']==2281 and structure['functions']==19329
    assert structure['javascript_files']==44 and structure['protected_literals']==205339
    assert structure['instructions_unchanged'] and structure['program_literals_validated']
    assert structure['native_squirrel_reader']==structure['javascript_parse']=='passed'
    assert structure['place_name_literals_preserved']==2559 and len(structure['intentional_place_owner_lookups'])==2
    assert structure['framework_files_verified']==manifest['bundled_framework']['files']
    composed=reports['composed']
    assert composed['rendered_texts']==153 and not composed['game_started']
    assert all(composed[k]=='passed' for k in ('native_execution','numbers_variables_markup','damage_percentages','names_and_composed_tooltips'))
    canonical=reports['canonical_names']
    assert canonical['original_name_generation_cases']==3800 and canonical['random_call_counts_unchanged']
    assert canonical['packaged_ui_name_preservation']=='passed' and not canonical['game_started']
    display=reports['display']
    assert display['dictionary_sha256']==manifest['place_display_sha256']
    assert display['bridge_sha256']==manifest['place_display_bridge_sha256']
    assert display['reviewed_places_sha256']==sha(APP/'localization/reviewed_place_names.json')
    assert all(display[k]=='passed' for k in ('native_map_dictionary_all_entries','native_vm_abi_10000_calls',
            'actual_native_render_proxy','native_dictionary_hash_check','pinned_game_code_signatures','squirrel_bridge_with_packaged_framework'))
    assert display['ui']['status']=='passed' and display['ui']['dictionary_entries']==7723
    assert display['ui']['canonical_data_unchanged'] and not display['actual_game_process_executed']
    compatibility=reports['compatibility']
    assert not compatibility['game_started'] and not compatibility['steam_installation_modified']
    assert compatibility['mod_unchanged'] and not compatibility['file_overlaps'] and compatibility['profile_preserves_star_mod']
    assert compatibility['native_stats_stars_ratings']=='passed' and compatibility['ui']['recruit_ui']=='passed'
    assert compatibility['without_star_mod']['ui']['original_tryout_behavior']=='passed'
    assert compatibility['installed_profile_simulation']['switch_back_files_preserved']
    assert not compatibility['installed_profile_simulation']['third_party_translation_contents_read']
    assert reports['ui_input']['status']=='passed' and all(x['returncode']==0 for x in reports['ui_input']['checks'])
    assert reports['ui_input']['runtime_sha256']==sha(APP/'localization/runtime.js')
    frozen=reports['frozen']
    assert frozen['returncode']==0 and frozen['localization_manager']=='ready'
    assert frozen['standalone_copy_outside_project'] and frozen['catalog_entries']==15815
    assert frozen['full_catalog_sha256']==catalog_hash and frozen['reviewed_geographic_entries']==2196
    assert frozen['sha256']==sha(DIST/'BBMOD.exe')
    assert all(digest==sha(APP/'build/native'/file) for file,digest in frozen['native_components_sha256'].items())
    xml=APP/'build/review/place-display-tests.xml'
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    totals={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert totals=={'tests':101,'failures':0,'errors':0,'skipped':0}
    write(DIST/package.name,package.read_bytes())
    write(DIST/'mod_bbmod_zhcn.manifest.json',json.dumps({**manifest,'out':str(DIST/package.name)},ensure_ascii=False,indent=2).encode('utf-8'))
    report={
        'version':manifest['version'],'created_at':datetime.now(timezone.utc).isoformat(),
        'independent_translation':True,'third_party_localization_reused':False,
        'source_scope':'Battle Brothers 1.5.2.3 base game and official DLC extracted corpus',
        'full_catalog_sha256':catalog_hash,'full_catalog_identical_to_rc1':True,
        'editorial_review':catalog['editorial_review'],
        'geographic_editorial_review':{'status':'complete','entries':2196,'expanded_display_names':7723,
                                     'reviewed_places_sha256':display['reviewed_places_sha256']},
        'l10n_package_sha256':package_hash,'place_name_display':'launcher_session',
        'translation_qa':previous['translation_qa'],
        'translation_qa_note':'Non-geographic corpus is byte-identical to the previously reviewed release; geographic display review is separately checked in this release.',
        'offline_script_validation':structure,'composed_skill_text':composed,'place_names':canonical,
        'place_display':display,'star_rating_compatibility':compatibility,'frozen_startup':frozen,
        'offline_regression_tests':{**totals,'deselected':1,'excluded':'orchestrator_roundtrip touches a real game directory'},
        'display_and_input_checks':reports['ui_input'],
        'evidence_files':{str(p.relative_to(APP)):sha(p) for p in [*paths.values(),xml]},
        'host_mod_diagnostics':{'current_stdout':frozen['stdout'],'previous_stdout':previous['frozen_startup']['stdout'],
                              'note':'Read-only host MOD diagnostics; successful EXE selftest does not resolve every third-party dependency.'},
        'game_started_by_this_run':False,'game_acceptance':'not_run_user_requested_offline_only',
        'steam_installation_modified':False,'development_game_copy_updated':False,'saves_modified':False,
        'existing_chinese_save_names':'not_migrated','backups':str(BACKUP.parent),
        'historical_screenshot_note':'Existing PNG files are earlier desktop UI evidence, not acceptance of this game build.'
    }
    write(DIST/'validation.json',json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8'))
    notes='''BBMOD · 战团整备所 — 0.3.0-rc.2

本版功能：地名随启动方式切换
通过 BBMOD 的“启动游戏”或“应用并启动”进入：地图、任务、对话中的地名统一显示中文。
从 Steam 或游戏 EXE 直接进入：三处地名统一显示英文，其余正文仍是中文。
仅打开软件不会改变已经运行的游戏。通过软件启动后可以关闭软件；本次游戏继续显示中文，下次直接启动仍默认英文。
原始名称及存档保持英文，不把中文地名写回游戏数据。旧汉化存档中已经保存的中文名称不会自动恢复。

首次更新
1. 打开新版 BBMOD.exe，指定游戏目录，进入“汉化工坊 → 汉化管理与启动”。
2. 点击“生成 / 更新独立汉化”，或导入本目录同版本的 mod_bbmod_zhcn.zip。
3. 选择方案，核对启用、停用及冲突文件，点击“应用方案”；想同时进入游戏可选“应用并启动”。
4. 此后从软件启动可使用中文地名，直接启动使用英文地名。
此功能需要新版软件和新版汉化包一起使用；更换 EXE 不会自动替换已安装的旧包。

文本与发给朋友
本体和官方 DLC 已提取目录共 15,629 条，13,433 条非地名文本及 2,196 条地名均已独立精修。
地名组合展开为 7,723 个显示名称；合并补充界面文本后编辑器共 15,815 条。
全部依据官方英文独立制作，不复用狐狸译文、术语表和脚本。
可以直接发送 BBMOD.exe，词库、字体、图标、启动组件及公开框架已内置，无需 Python。
朋友需自行安装受支持的 Steam 原版 1.5.2.3 及相应 DLC。第三方 MOD 合集、狐狸汉化和显星 MOD 不包含在 EXE 中。

其他汉化与 MOD
已有汉化可保存为方案，停用文件保存在游戏目录的 bbmod_disabled，方案与备份位于 bbmod_localizations。
第三方汉化沿用各自规则；本功能不能还原直接修改过的游戏本体归档。
星级、属性及评价仍需要原显星 MOD。开启才显示额外信息，停用恢复原版招募行为。
公开的 Modding Script Hooks 21.1 框架署名和来源见 ZIP 内 BBMOD_FRAMEWORK_CREDITS.txt。

离线检查
101 项回归通过。2,281 个 Squirrel 字节码文件、19,329 个函数、205,339 个受保护常量及 44 个 JavaScript 文件检查通过。
153 条技能及动态提示、3,800 个原版名称生成样例、显星 MOD 开关、中文输入和动态界面检查通过。
7,723 个地名的地图和对话译名一致，两种启动模式及再次直接启动通过模拟检查。
原生调用封装完成 1 万次独立 VM 模拟调用，栈平衡和错误清理通过；实际绘字代理保留原始字符串，仅绘制副本取消底板。
包内地名查询脚本与实际框架在离线解释器中通过；独立 EXE 使用临时配置从项目外副本完成自检，内置组件哈希与当前构建一致。
自检仍会报告本机已有 MOD 组合的依赖诊断；通过不代表所有第三方依赖问题已解决。
按用户要求没有启动或加载游戏，没有更新真实游戏、开发测试副本、桌面入口或存档。实际游戏显示与完整流程尚未验收。
详细结果见 validation.json；校验值见 SHA256SUMS.txt。目录中的 PNG 为早先桌面界面截图，不是本版游戏截图。
'''
    write(DIST/'使用说明.txt',notes.encode('utf-8-sig'))
    files=sorted(p for p in DIST.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
    assert not any(p.name.endswith('.pending') for p in files)
    sums=''.join(sha(p)+'  '+p.name+'\n' for p in files)
    write(DIST/'SHA256SUMS.txt',sums.encode('utf-8'))
    for line in sums.splitlines():
        digest,name=line.split('  ',1)
        assert sha(DIST/name)==digest
    print(json.dumps({'version':manifest['version'],'exe_sha256':sha(DIST/'BBMOD.exe'),
                      'package_sha256':sha(DIST/package.name),'distribution_files_verified':len(files),
                      'regressions_passed':101,'game_started':False},ensure_ascii=False))


if __name__=='__main__':main()
