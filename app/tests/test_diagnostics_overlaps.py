from pathlib import Path
import random
import re

from core.diagnostics import DiagnosisReport, FRAMEWORK_IDS, Issue, _check_file_overlaps
from core.modinfo import ModInfo, Registration


def reference_overlaps(installed):
    report = DiagnosisReport()
    ordered = sorted(installed, key=lambda m: m.file_name.lower())
    framework_srcs = {m.file_name for m in installed if any(r.mod_id in FRAMEWORK_IDS for r in m.registrations)}
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            a, b = ordered[i], ordered[j]
            if not a.entries or not b.entries:
                continue
            def key(entry):
                return re.sub(r'\.(?:c?nut)$', '.squirrel', entry.replace('\\', '/').lower())
            roots = ('scripts/', 'ui/', 'gfx/', 'brushes/', 'sounds/', 'music/', 'preload/')
            set_a = {key(e) for e in a.entries if e.lower().startswith(roots)}
            overlap = [e for e in b.entries if key(e) in set_a]
            if not overlap:
                continue
            script_overlap = [e for e in overlap if e.startswith("scripts/") and "/!mods_preload/" not in e]
            base_pack = a.file_name in framework_srcs or b.file_name in framework_srcs
            if not script_overlap and not base_pack:
                continue
            report.issues.append(Issue(
                severity="info" if base_pack else "warning", source=b.file_name,
                title=f"将覆盖 {a.file_name} 的 {len(overlap)} 个文件（{'脚本' if script_overlap else '资源'}覆盖）",
                detail=f"后挂载者生效。示例：{', '.join(e for e in (script_overlap or overlap)[:3])}"))
    return report.issues


def test_overlap_report_matches_pairwise_reference():
    rng = random.Random(7)
    pool = ['scripts/items/sword.nut', 'scripts/items/sword.cnut', 'Scripts/Items/Axe.nut', 'scripts\\skills\\a.nut',
            'scripts/!mods_preload/mod.nut', 'ui/screens/main.js', 'gfx/icon.png', 'sounds/hit.wav', 'readme.txt',
            'brushes/x.brush', 'preload/p.nut', 'music/theme.ogg', 'scripts/ai/plan.nut']
    reported = 0
    for _ in range(40):
        mods = []
        for index in range(rng.randint(0, 7)):
            entries = rng.sample(pool, rng.randint(0, 6))
            registrations = [Registration('mod_msu', '1.0', None, 'legacy')] if rng.random() < 0.2 else []
            mods.append(ModInfo(path=Path(f'm{index}.zip'), file_name=f'{rng.choice("abcAB")}{index}.zip',
                                entries=entries, registrations=registrations))
        report = DiagnosisReport()
        _check_file_overlaps(mods, report)
        assert report.issues == reference_overlaps(mods)
        reported += bool(report.issues)
    assert reported >= 10
