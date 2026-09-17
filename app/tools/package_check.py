"""Check bundled resources and start the frozen application in an isolated profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from PyInstaller.archive.readers import CArchiveReader


def main() -> int:
    app_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=app_dir / "dist/BBMOD.exe")
    parser.add_argument("--report", type=Path, default=app_dir / "build/review/exe-selftest.json")
    args = parser.parse_args()
    executable = args.exe.resolve(strict=True)
    archive = CArchiveReader(str(executable))
    bundled = {name.replace("\\", "/"): name for name in archive.toc}
    required = ["assets/bbmod.ico", "assets/crest-painted.png", "assets/camp-painted.png",
                "assets/panel-frame.svg", "assets/Cinzel.ttf",
                "localization/catalog.json", "localization/full_catalog.json", "localization/runtime.js",
                "localization/place_names.json", "localization/place_name_pools.cnut",
                "localization/reviewed_place_names.json", "localization/place_session.nut",
                "localization/NotoSansSC-Regular.ttf", "localization/FONT-LICENSE.txt",
                "localization/NotoSerifSC-SemiBold.ttf", "localization/MAP-FONT-LICENSE.txt",
                "native/bin/bbmod_launch.exe", "native/bin/bbmod_han.dll", "seedgen/payload/mod_hooks.zip",
                "data/seed_traits.json", "seedgen/payload/seed_generator/config_role_condition.nut",
                "seedgen/payload/seed_generator/function_brother_output_check.nut"]
    missing = [name for name in required if name not in bundled]
    if missing:
        raise RuntimeError(f"缺少打包资源：{missing}")
    for name in ('data/seed_traits.json', 'seedgen/payload/seed_generator/config_role_condition.nut',
                 'seedgen/payload/seed_generator/function_brother_output_check.nut'):
        if archive.extract(bundled[name]) != (app_dir/name).read_bytes():
            raise RuntimeError('EXE 中的特质筛选资源与源码不一致：'+name)
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
    for name in ('place_names.json', 'place_name_pools.cnut', 'runtime.js', 'reviewed_place_names.json', 'place_session.nut'):
        if archive.extract(bundled['localization/' + name]) != (app_dir / 'localization' / name).read_bytes():
            raise RuntimeError('EXE 中的地名配置或界面组件与当前版本不一致')
    native_hashes = {}
    for name in ('bbmod_launch.exe', 'bbmod_han.dll'):
        raw = archive.extract(bundled['native/bin/' + name])
        if raw != (app_dir / 'build/native' / name).read_bytes():
            raise RuntimeError('EXE 中的原生显示组件与当前构建不一致')
        native_hashes[name] = hashlib.sha256(raw).hexdigest()
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
            "native_components_sha256": native_hashes,
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
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
