"""Check complete sentences by executing original and packaged CNUT offline.

The ZIP is copied and decrypted with bbsq -d, then sq executes its actual
bytecode using the small engine fixtures in tests/reviewed_sentences_harness.nut.
No translated catalog, decompiled source, game process, or game directory is
used as a substitute for package execution. Static checks cover input bytes
and ZIP membership only; they are reported separately from execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from core.l10n_tokens import validate_translation

WORK = APP / "build/full-l10n"
HARNESS = APP / "tests/reviewed_sentences_harness.nut"
FILES = (
    "scripts/config/item_names.cnut",
    "scripts/items/misc/anatomist/necrosavant_potion_item.cnut",
    "scripts/skills/effects/necrosavant_potion_effect.cnut",
    "scripts/skills/actives/coat_with_poison_skill.cnut",
    "scripts/skills/actives/coat_with_spider_poison_skill.cnut",
    "scripts/items/supplies/ammo_item.cnut",
    "scripts/items/supplies/armor_parts_item.cnut",
    "scripts/items/supplies/medicine_item.cnut",
    "scripts/items/tools/smoke_bomb_item.cnut",
    "scripts/skills/actives/throw_smoke_bomb_skill.cnut",
    "scripts/items/tools/holy_water_item.cnut",
    "scripts/skills/traits/arena_fighter_trait.cnut",
    "scripts/skills/traits/arena_pit_fighter_trait.cnut",
    "scripts/skills/traits/arena_veteran_trait.cnut",
    "scripts/ambitions/oaths/oath_ambition.cnut",
    "scripts/ambitions/oaths/oath_of_camaraderie_ambition.cnut",
    "scripts/skills/effects/dazed_effect.cnut",
    "scripts/skills/effects/disarmed_effect.cnut",
    "scripts/skills/traits/old_trait.cnut",
    "scripts/skills/actives/whip_skill.cnut",
)
MARKER = "BBMOD_REVIEWED_SENTENCES_PASS"
COLOR = re.compile(r"\[/?color(?:=[^\]]+)?\]")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compact(value: str) -> str:
    return re.sub(r"\s+", "", COLOR.sub("", value))


def execute(root: Path, label: str, output: Path, sq: Path) -> dict[str, str]:
    preamble = "::InputRoot <- " + json.dumps(root.as_posix()) + ";\n"
    preamble += "::InputFiles <- " + json.dumps(FILES) + ";\n"
    harness = output / (label + ".nut")
    harness.write_text(preamble + HARNESS.read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run([str(sq), str(harness)], capture_output=True, timeout=30)
    stdout = result.stdout.decode("utf-8", errors="strict")
    stderr = result.stderr.decode("utf-8", errors="replace")
    (output / (label + "-stdout.txt")).write_text(stdout, encoding="utf-8")
    (output / (label + "-stderr.txt")).write_text(stderr, encoding="utf-8")
    if result.returncode or stderr.strip() or MARKER not in stdout.splitlines():
        raise RuntimeError(f"{label} bytecode execution failed: {(stdout + stderr)[-2500:]}")
    texts = {}
    for line in stdout.splitlines():
        if line.startswith("TEXT|"):
            _, key, encoded = line.split("|", 2)
            if key in texts:
                raise RuntimeError(f"Duplicate executed text key: {key}")
            texts[key] = bytes.fromhex(encoded).decode("utf-8")
    if not texts:
        raise RuntimeError(f"{label} executed no text cases")
    return texts


def check_sentences(original: dict[str, str], current: dict[str, str]) -> tuple[list[dict], list[dict]]:
    checks, problems = [], []

    def check(name, passed, **details):
        row = {"name": name, "passed": bool(passed), **details}
        checks.append(row)
        if not passed:
            problems.append(row)

    check("identical_execution_case_keys", original.keys() == current.keys(),
          missing=sorted(original.keys() - current.keys()), extra=sorted(current.keys() - original.keys()))
    for key in original.keys() & current.keys():
        issues = validate_translation(original[key], current[key])
        if issues:
            check("protected_tokens." + key, False, issues=issues)
    check("numbers_variables_markup", not any(p["name"].startswith("protected_tokens.") for p in problems))

    def sentence(group, source, expected=None, suffix=None):
        keys = [key for key, text in original.items() if key.startswith(group + ".") and source in text]
        check("case_present." + group + "." + source[:24], len(keys) == 1, matched_keys=keys)
        if len(keys) != 1 or keys[0] not in current:
            return
        key = keys[0]
        actual = compact(current[key])
        check("sentence." + key, actual == expected if expected is not None else actual.endswith(suffix),
              key=key, source=original[key], expected=expected, expected_suffix=suffix, actual=actual)

    lifesteal = "将造成的生命值伤害的25%转化为自身生命值（目标须为相邻且有血液的敌人）"
    for group in ("lifesteal.item", "lifesteal.effect"):
        sentence(group, "Heal [color=", expected=lifesteal)
    sentence("poison.regular", "The next [color=", expected="接下来的4次攻击会使目标中毒。")
    sentence("poison.spider", "The next [color=", expected="接下来的4次攻击会使目标中毒，每回合造成10点伤害。")
    supply_suffixes = {
        "ammo": "单位的箭矢、弩矢和标枪等弹药。战后用于自动补满箭囊。返回世界地图后加入战团的补给库存。",
        "tools": "单位的工具与材料，用于战后修理武器、盔甲、头盔和盾牌。返回世界地图后加入战团的补给库存。",
        "medicine": "单位的草药、药膏、绷带等医疗物资，帮助佣兵恢复战斗中所受的伤。返回世界地图后加入战团的补给库存。",
    }
    for kind, ending in supply_suffixes.items():
        for amount in (1, 50):
            sentence(f"supply.{kind}.{amount}", "A good [color=", expected=f"共{amount}" + ending)
    for group in ("smoke.item", "smoke.skill"):
        sentence(group, "Covers [color=", expected="以烟雾覆盖7格区域，持续一轮；其中任何人都能自由移动，无视控制区")
    sentence("holy_water", "Damage of [color=", expected="伤害：20，持续3回合，对被击中的亡灵目标生效")
    for kind in ("fighter", "pit", "veteran"):
        for won, expected in ((3, "3"), (5, "全部")):
            sentence(f"arena.{kind}.5_{won}", " So far, this character has fought in ",
                     suffix=f"迄今为止，此角色已参加5场比赛，获胜场次：{expected}。")
    for won, ending in ((0, "，但未能取胜。"), (1, "，并赢得了胜利。")):
        sentence(f"arena.pit.1_{won}", " So far, this character has fought in one match",
                 suffix="迄今为止，此角色参加过一场比赛" + ending)
    for days in (1, 3):
        key = f"oath.remaining.{days}"
        expected = f"信守袍泽之誓，持续接下来的{days}天"
        check("sentence." + key, key in current and compact(current[key]) == expected,
              expected=expected, actual=compact(current.get(key, "")))
    for status in ("dazed", "disarmed"):
        for turns, word in ((1, "一"), (2, "两")):
            key = f"log.{status}.{turns}"
            expected = ("Hans使以下目标陷入恍惚：Brigand" if status == "dazed" else "Hans缴械了Brigand") + f"，持续{word}回合"
            check("sentence." + key, key in current and compact(current[key]) == expected,
                  expected=expected, actual=compact(current.get(key, "")))

    context_names = {"Old": "古旧", "Whip": "长鞭", "of the Desert": "·沙漠", "of the North": "·北境"}
    for source, expected in context_names.items():
        keys = [key for key, text in original.items() if key.startswith("item_names.") and text == source]
        check("item_context_present." + source, bool(keys), matched_keys=keys)
        for key in keys:
            check("item_context." + key, current.get(key) == expected, source=source,
                  expected=expected, actual=current.get(key))
    for key, source, expected in (("generic.old", "Old", "年迈"), ("generic.whip", "Whip", "鞭击")):
        check("generic_unchanged." + key, original.get(key) == source and current.get(key) == expected,
              source=original.get(key), expected=expected, actual=current.get(key))
    return checks, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True, help="Actual localization ZIP to validate")
    parser.add_argument("--output", type=Path, default=WORK / "reviewed-sentence-validation")
    parser.add_argument("--original-root", type=Path, default=WORK / "plain", help="Original decrypted CNUT root")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": 1, "status": "failed", "package": str(args.package.resolve()),
        "game_started": False, "game_acceptance": "not_performed",
        "static_extraction": {"status": "not_run", "scope": "ZIP members, hashes and bytecode headers only; not a language acceptance result"},
        "actual_bytecode_execution": {"status": "not_run", "source": "bbsq -d, then sq dofile on extracted CNUT and original CNUT", "engine": "offline fixtures; no game simulation"},
        "static_text_fallback": False,
    }
    try:
        package = args.package.resolve(strict=True)
        original_root = args.original_root.resolve(strict=True)
        bbsq, sq = WORK / "tools/bin/bbsq.exe", WORK / "tools/bin/sq.exe"
        report["package_sha256"] = sha256(package)
        report["tools"] = {path.name: {"path": str(path), "sha256": sha256(path)} for path in (bbsq, sq)}
        report["harness_sha256"] = sha256(HARNESS)
        run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=output)).resolve()
        report["run_directory"] = str(run_dir)
        patched, original = run_dir / "packaged", run_dir / "original"
        files = {}
        with zipfile.ZipFile(package) as archive:
            for name in FILES:
                if archive.namelist().count(name) != 1:
                    raise ValueError(f"Expected one ZIP member: {name}")
                current_path, source_path = patched / name, original / name
                if not current_path.resolve().is_relative_to(patched.resolve()):
                    raise ValueError(f"Unsafe member path: {name}")
                current_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.parent.mkdir(parents=True, exist_ok=True)
                current_path.write_bytes(archive.read(name))
                shutil.copyfile(original_root / name, source_path)
                files[name] = {"package_sha256": sha256(current_path), "original_sha256": sha256(source_path)}
        decrypt = subprocess.run([str(bbsq), "-d", *(str(patched / name) for name in FILES)],
                                 capture_output=True, timeout=40)
        (run_dir / "decrypt-output.txt").write_bytes(decrypt.stdout + decrypt.stderr)
        if decrypt.returncode:
            raise RuntimeError("bbsq -d failed; see decrypt-output.txt")
        for name in FILES:
            for root in (original, patched):
                if (root / name).read_bytes()[:2] != b"\xfa\xfa":
                    raise ValueError(f"Expected decrypted Squirrel bytecode, not source text: {root / name}")
            files[name]["decrypted_package_sha256"] = sha256(patched / name)
        report["static_extraction"].update(status="passed", file_count=len(FILES), files=files)
        source_texts = execute(original, "original", run_dir, sq)
        report["actual_bytecode_execution"]["original"] = "passed"
        translated_texts = execute(patched, "translated", run_dir, sq)
        report["actual_bytecode_execution"].update(status="passed", translated="passed", files=len(FILES),
                                                    source_texts=len(source_texts), translated_texts=len(translated_texts))
        checks, problems = check_sentences(source_texts, translated_texts)
        report.update(status="passed" if not problems else "failed", checks=checks, problems=problems,
                      texts={key: {"source": value, "translation": translated_texts.get(key),
                                   "plain": compact(translated_texts.get(key, ""))} for key, value in sorted(source_texts.items())})
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        report["error"] = str(exc)
        if report["static_extraction"]["status"] == "not_run":
            report["static_extraction"]["status"] = "failed"
        elif report["actual_bytecode_execution"]["status"] == "not_run":
            report["actual_bytecode_execution"]["status"] = "failed"
    report_path = output / "validation.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {key: report[key] for key in ("status", "package", "game_started", "game_acceptance", "actual_bytecode_execution", "static_text_fallback")}
    summary.update(report=str(report_path), static_extraction=report["static_extraction"]["status"],
                   failed_checks=len(report.get("problems", [])), error=report.get("error"))
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
