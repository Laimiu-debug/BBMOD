"""Check bundled resources and start the frozen application in an isolated profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from PyInstaller.archive.readers import CArchiveReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.version import VERSION


def main() -> int:
    app_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=app_dir / f"dist/BBMOD-{VERSION}.exe")
    parser.add_argument("--report", type=Path, default=app_dir / "build/review/exe-selftest.json")
    args = parser.parse_args()
    executable = args.exe.resolve(strict=True)
    archive = CArchiveReader(str(executable))
    bundled = {name.replace("\\", "/"): name for name in archive.toc}
    required = ["assets/equipment/manifest.json", "data/equipment_catalog.json", "assets/game-ui/dialog_panel_01.png", "data/item_inspector/catalog.json", "data/item_inspector/bridge.nut", "data/item_inspector/hover.js", "assets/bbmod.ico", "assets/crest-painted.png", "assets/camp-painted.png",
                "assets/panel-frame.svg", "assets/Cinzel.ttf",
                "localization/catalog.json", "localization/full_catalog.json", "localization/runtime.js",
                "localization/name_order.json", "localization/reviewed_dynamic.json", "localization/reviewed_contextual.json", "localization/reviewed_source_fixes.json",
                "localization/place_names.json", "localization/place_name_pools.cnut",
                "localization/reviewed_place_names.json", "localization/place_session.nut",
                "localization/NotoSansSC-Regular.ttf", "localization/FONT-LICENSE.txt",
                "localization/NotoSerifSC-SemiBold.ttf", "localization/MAP-FONT-LICENSE.txt",
                "localization/map_labels.nut", "localization/map_labels.js", "localization/map_labels.css",
                "seedgen/payload/mod_hooks.zip",
                "data/seed_traits.json", "seedgen/payload/seed_generator/config_role_condition.nut",
                "seedgen/payload/seed_generator/config_map_condition.nut",
                "seedgen/payload/seed_generator/function_map_output_check.nut",
                "seedgen/payload/seed_generator/function_generate_settlement.nut",
                "seedgen/payload/seed_generator/function_brother_output_check.nut",
                "seedgen/payload/seed_generator/config_campaign.nut",
                "seedgen/payload/seed_generator/function_auto_start.nut"]
    missing = [name for name in required if name not in bundled]
    if missing:
        raise RuntimeError(f"缺少打包资源：{missing}")
    retired = [name for name in bundled if name.rsplit('/', 1)[-1] in {'bbmod_launch.exe', 'bbmod_han.dll'}]
    if retired:
        raise RuntimeError('新版不得携带旧注入组件：' + '、'.join(retired))
    python_archive = archive.open_embedded_archive(next(name for name in archive.toc if name.startswith('PYZ')))
    if 'core.native_font' in python_archive.toc:
        raise RuntimeError('新版不得携带旧注入启动代码')
    if 'core.l10n_display' not in python_archive.toc:
        raise RuntimeError('EXE 缺少人物和势力名称显示词库的构建组件')
    if 'core.l10n_context' not in python_archive.toc:
        raise RuntimeError('EXE 缺少按使用场景区分译文的构建组件')
    equipment_icons = json.loads(archive.extract(bundled['assets/equipment/manifest.json']))
    for filename, metadata in equipment_icons['files'].items():
        resource = 'assets/equipment/' + filename
        if resource not in bundled or hashlib.sha256(archive.extract(bundled[resource])).hexdigest() != metadata['sha256']:
            raise RuntimeError('EXE 中的装备图标缺失或校验失败：' + resource)
    for name in ('localization/runtime.js', 'localization/name_order.json', 'localization/reviewed_dynamic.json', 'localization/reviewed_contextual.json', 'localization/reviewed_source_fixes.json', 'localization/reviewed_place_names.json',
                 'assets/equipment/manifest.json', 'assets/bbmod.ico', 'data/equipment_catalog.json', 'data/item_inspector/catalog.json', 'data/item_inspector/bridge.nut', 'assets/game-ui/dialog_panel_01.png', 'data/seed_traits.json', 'seedgen/payload/seed_generator/config_role_condition.nut',
                 'seedgen/payload/seed_generator/config_map_condition.nut',
                 'seedgen/payload/seed_generator/function_map_output_check.nut',
                 'seedgen/payload/seed_generator/function_generate_settlement.nut',
                 'seedgen/payload/seed_generator/function_brother_output_check.nut',
                 'seedgen/payload/seed_generator/config_campaign.nut',
                 'seedgen/payload/seed_generator/function_auto_start.nut',
                 'seedgen/payload/scripts/!mods_preload/mod_seed_generator.nut'):
        if archive.extract(bundled[name]) != (app_dir/name).read_bytes():
            raise RuntimeError('EXE 中的资源与源码不一致：'+name)
    hooks_bytes = archive.extract(bundled['seedgen/payload/mod_hooks.zip'])
    if hooks_bytes != (app_dir / 'seedgen/payload/mod_hooks.zip').read_bytes():
        raise RuntimeError('EXE 中的 MOD 框架与已核验的本地资源不一致')
    catalog = json.loads(archive.extract(bundled["localization/catalog.json"]))
    base_sources = {source for group in catalog['groups'].values() for source in group}
    full_bytes = archive.extract(bundled['localization/full_catalog.json'])
    full_sha256 = hashlib.sha256(full_bytes).hexdigest()
    if full_bytes != (app_dir / 'localization/full_catalog.json').read_bytes():
        raise RuntimeError('EXE 中的完整词库与当前已发布目录不一致')
    full = json.loads(full_bytes)
    policy_bytes = archive.extract(bundled['localization/place_names.json'])
    policy_hash = hashlib.sha256(policy_bytes).hexdigest()
    for name in ('place_names.json', 'place_name_pools.cnut', 'runtime.js', 'reviewed_place_names.json', 'place_session.nut',
                 'map_labels.nut', 'map_labels.js', 'map_labels.css'):
        if archive.extract(bundled['localization/' + name]) != (app_dir / 'localization' / name).read_bytes():
            raise RuntimeError('EXE 中的地名配置或界面组件与当前版本不一致')
    if full.get('translation_stage') != 'complete_draft':
        raise RuntimeError('EXE 未包含完整初译目录')
    policy = json.loads(policy_bytes)
    geographic = set(policy['name_keys'])
    place_review = json.loads(archive.extract(bundled['localization/reviewed_place_names.json']))
    if set(place_review['reviewed_ids']) != geographic or set(place_review['terms']) != {full['entries'][k]['source'] for k in geographic}:
        raise RuntimeError('EXE 中的地名精修词库不完整')
    pending_review = [key for key, entry in full['entries'].items()
                      if key not in geographic and entry['status'] != 'reviewed']
    editorial = full.get('editorial_review', {})
    if pending_review or editorial.get('status') != 'complete' or editorial.get('pending_non_geographic_entries') != 0:
        raise RuntimeError('EXE 中仍有未精修的正文')
    entries = len(base_sources | {entry['source'] for entry in full['entries'].values()})
    if not entries:
        raise RuntimeError("独立词库为空")
    with tempfile.TemporaryDirectory(prefix="bbmod-package-check-") as temporary:
        assert Path(temporary).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
        standalone = Path(temporary) / executable.name
        shutil.copy2(executable, standalone)
        environment = dict(os.environ, APPDATA=str(Path(temporary) / 'profile'), QT_QPA_PLATFORM="offscreen")
        started = time.monotonic()
        result = subprocess.run([str(standalone), "--selftest"], env=environment, cwd=temporary,
                                capture_output=True, timeout=55,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode == 0 and b'l10n_manager=ready' not in result.stdout:
            raise RuntimeError('EXE 没有加载新版汉化管理界面')
        if result.returncode == 0 and b'legacy_hooks=ready' not in result.stdout:
            raise RuntimeError('EXE 中的兼容框架未通过加载校验')
        if result.returncode == 0 and b'seed_traits=58' not in result.stdout:
            raise RuntimeError('EXE 未加载完整的开局特质筛选资源')
        if result.returncode == 0 and b'seed_weapons=50' not in result.stdout:
            raise RuntimeError('EXE 未加载红武器筛选界面和完整类型列表')
        if result.returncode == 0 and b'seed_ports=ready' not in result.stdout:
            raise RuntimeError('EXE 未加载南北港和竞技场港筛选界面')
        if result.returncode == 0 and ('version=' + VERSION).encode() not in result.stdout:
            raise RuntimeError('EXE 中的软件版本与当前发布版本不一致')
        if result.returncode == 0 and b'font_settings=ready' not in result.stdout:
            raise RuntimeError('EXE 未加载字体设置页面')
        if result.returncode == 0 and b'equipment_catalog: ready' not in result.stdout:
            raise RuntimeError('EXE 未加载离线装备表格及独立鉴定页签')
        if result.returncode == 0 and b'game_launch_feedback: ready' not in result.stdout:
            raise RuntimeError('EXE 未加载共享启动状态或未完成游戏进程检查')
        if result.returncode == 0 and b'localization_guidance: ready' not in result.stdout:
            raise RuntimeError('EXE 未加载当前汉化状态与默认收起的高级制作入口')
        if result.returncode == 0 and b'seed_share_queue: ready' not in result.stdout:
            raise RuntimeError('EXE 未加载种子批量分享队列')
        if result.returncode == 0 and b'seed_code_copy: ready' not in result.stdout:
            raise RuntimeError('EXE 未加载常驻种子码复制入口')
        if result.returncode == 0 and b'updater=ready' not in result.stdout:
            raise RuntimeError('EXE 未加载版本管理与更新组件')
        report = {
            "executable": str(executable),
            "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "returncode": result.returncode,
            "seconds": round(time.monotonic() - started, 2),
            "catalog_entries": entries,
            "full_catalog_entries": len(full['entries']),
            "full_catalog_sha256": full_sha256,
            "place_name_policy_sha256": policy_hash,
            "reviewed_geographic_entries": len(place_review['reviewed_ids']),
            "retired_native_components_included": False,
            "retired_native_loader_included": False,
            "font_settings_ready": b'font_settings=ready' in result.stdout,
            "equipment_catalog_ready": b'equipment_catalog: ready' in result.stdout,
            "game_launch_feedback_ready": b'game_launch_feedback: ready' in result.stdout,
            "localization_guidance_ready": b'localization_guidance: ready' in result.stdout,
            "seed_share_queue_ready": b'seed_share_queue: ready' in result.stdout,
            "seed_code_copy_ready": b'seed_code_copy: ready' in result.stdout,
            "equipment_icon_files": len(equipment_icons['files']),
            "hooks_archive_sha256": hashlib.sha256(hooks_bytes).hexdigest(),
            "translation_stage": full['translation_stage'],
            "editorial_review": editorial,
            "standalone_copy_outside_project": True,
            "localization_manager": 'ready' if b'l10n_manager=ready' in result.stdout else 'missing',
            "required_resources": required,
            "stdout": result.stdout.decode(errors="replace"),
            "stderr": result.stderr.decode(errors="replace"),
            "game_acceptance": "pending",
            "seed_trait_choices": 58,
            "seed_weapon_choices": 50,
            "seed_port_filters_ready": b'seed_ports=ready' in result.stdout,
            "updater_ready": b'updater=ready' in result.stdout,
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
