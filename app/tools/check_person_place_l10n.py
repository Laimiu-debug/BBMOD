"""Execute person/place and courier methods from original and packaged CNUT.

No game is started and no game installation or save is modified. Engine roster,
world, stream and native %variable% interpolation boundaries are fixtures. All
names/title joining, title grants, recipient caching, contract state templates,
variable preparation and serialization methods execute actual bytecode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from core.cnut import Cnut
from core.l10n_tokens import validate_translation

WORK = APP / "build/full-l10n"
HARNESS = APP / "tests/person_place_harness.nut"
FILES = (
    "scripts/config/strings.cnut",
    "scripts/tools/tag_collection.cnut",
    "scripts/entity/tactical/actor.cnut",
    "scripts/factions/settlement_faction.cnut",
    "scripts/factions/city_state_faction.cnut",
    "scripts/contracts/contract.cnut",
    "scripts/contracts/contracts/deliver_item_contract.cnut",
)
MARKER = "BBMOD_PERSON_PLACE_PASS"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def execute(root: Path, output: Path, label: str) -> dict[str, str]:
    preamble = "::InputRoot <- " + json.dumps(root.as_posix()) + ";\n"
    preamble += "::InputFiles <- " + json.dumps(FILES) + ";\n"
    runner = output / (label + ".nut")
    runner.write_text(preamble + HARNESS.read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run([str(WORK / "tools/bin/sq.exe"), str(runner)],
                            capture_output=True, timeout=45)
    stdout = result.stdout.decode("utf-8", errors="strict")
    stderr = result.stderr.decode("utf-8", errors="replace")
    (output / (label + "-stdout.txt")).write_text(stdout, encoding="utf-8")
    (output / (label + "-stderr.txt")).write_text(stderr, encoding="utf-8")
    if result.returncode or stderr.strip() or MARKER not in stdout.splitlines():
        raise RuntimeError(f"{label} bytecode execution failed: {(stdout + stderr)[-3500:]}")
    texts = {}
    for line in stdout.splitlines():
        if line.startswith("TEXT|"):
            _, key, encoded = line.split("|", 2)
            if key in texts:
                raise ValueError("Duplicate executed output key: " + key)
            texts[key] = bytes.fromhex(encoded).decode("utf-8")
    return texts


def static_checks(original: Cnut, current: Cnut, filename: str) -> dict:
    before = {f["path"]: f for f in original.functions}
    after = {f["path"]: f for f in current.functions}
    if before.keys() != after.keys():
        raise ValueError("Function layout changed: " + filename)
    protected_methods = {"onSerialize", "onDeserialize", "setName", "setTitle", "getNameOnly"}
    if filename.endswith("actor.cnut"):
        protected_methods.update({"getName", "getTitle"})
    protected_literals = {"RecipientName", "RecipientID", "Distance", "Offer", "Running", "Running_Thieves",
                          "contract.deliver_item", "selection", "scripts/entity/tactical/humans/councilman",
                          "scripts/entity/tactical/humans/vizier"}
    methods, changed_literals = [], []
    for path, left in before.items():
        right = after[path]
        if (left["name"] != right["name"] or left["instructions"] != right["instructions"]
                or len(left["literals"]) != len(right["literals"])):
            raise ValueError(f"Instructions/function shape changed: {filename}:{path}")
        for source, translated in zip(left["literals"], right["literals"]):
            if (not isinstance(source, str) or source in protected_literals
                    or left["name"] in protected_methods) and source != translated:
                raise ValueError(f"Protected logic or ID changed: {filename}:{path}:{source!r}")
            if source != translated:
                changed_literals.append({"function": left["name"], "path": path,
                                         "source": source, "translation": translated})
        if left["name"] in protected_methods:
            methods.append({"name": left["name"], "path": path, "literals_and_instructions": "unchanged"})
    return {"file": filename, "functions": len(before), "instructions": "unchanged",
            "critical_ids": "unchanged", "protected_methods": methods,
            "changed_literal_count": len(changed_literals)}


def check_execution(original: dict[str, str], current: dict[str, str]) -> list[dict]:
    if original.keys() != current.keys():
        raise ValueError("Original/package execution cases differ")
    for key, source in original.items():
        if (key.endswith((".state_id", ".screen_id", ".creation_path", ".name_only", ".recipient_id", ".roundtrip",
                          ".restored_state", ".contract_type", ".offer_screen", ".type", ".id"))
                or ".variable.objective" in key):
            if current[key] != source:
                raise ValueError("Runtime ID/raw name changed: " + key)
        if key.endswith(".template"):
            issues = validate_translation(source, current[key])
            if issues:
                raise ValueError(f"Template tokens changed: {key}: {issues}")
    cases = []
    for key in sorted(original):
        if not key.endswith(".sentence"):
            continue
        prefix = key.removesuffix(".sentence")
        variable_prefix = prefix.rsplit(".", 1)[0] + ".variable."
        cases.append({"id": prefix, "source_template": original[prefix + ".template"],
                      "package_template": current[prefix + ".template"],
                      "source_before_ui": original[key], "package_before_ui": current[key],
                      "source_variables": {name.removeprefix(variable_prefix): value for name, value in original.items()
                                           if name.startswith(variable_prefix)},
                      "package_variables": {name.removeprefix(variable_prefix): value for name, value in current.items()
                                            if name.startswith(variable_prefix)},
                      "interpolation": "fixture %key% substitution of executed template and variables"})
    if len(cases) != 20:
        raise ValueError(f"Expected 20 state/legacy-cache sentences, got {len(cases)}")
    for kind in ("settlement", "city_state"):
        if original[kind + ".roundtrip"] != "true" or current[kind + ".roundtrip"] != "true":
            raise ValueError("Serialization roundtrip failed: " + kind)
        for key in original:
            if key.startswith(kind + ".serialized.") and key.endswith(".type"):
                value_key = key.removesuffix(".type") + ".value"
                if original[key] != "String" and original[value_key] != current[value_key]:
                    raise ValueError("Serialized numeric/ID field changed: " + value_key)
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--original-root", type=Path, default=WORK / "original")
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "status": "failed", "game_started": False,
              "game_visual_acceptance": "not_performed", "ui_runtime_executed": False,
              "text_source": "actual original and package CNUT; no localization catalog lookup",
              "fixture_boundaries": {"input_names": {"settlement": "Edmund", "city_state": "Jamil Ibn Sahr"},
                  "input_places": {"settlement": "Sommerstad", "city_state": "Al-Hazif"},
                  "name_generation": "explicit original-language fixture inputs; vizier.generateName not simulated",
                  "world_clock_rosters_sprites_streams": "offline fixtures; no engine/game/save access"},
              "native_template_interpolation": "unavailable in standalone VM; explicit token fixture only",
              "actual_bytecode_execution": "not_run", "static_extraction": "not_run"}
    try:
        package = args.package.resolve(strict=True)
        report.update(package=str(package), package_sha256=digest(package.read_bytes()))
        sources, checks = [], []
        with tempfile.TemporaryDirectory(prefix="bbmod-person-place-") as temporary:
            temp = Path(temporary)
            roots = {name: temp / name for name in ("original", "package")}
            with zipfile.ZipFile(package) as archive:
                for filename in FILES:
                    source = (args.original_root / filename).read_bytes()
                    present = filename in archive.namelist()
                    current = archive.read(filename) if present else source
                    for label, data in (("original", source), ("package", current)):
                        target = roots[label] / filename
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                    checks.append(static_checks(Cnut(source, encrypted=True), Cnut(current, encrypted=True), filename))
                    sources.append({"file": filename, "package_member": present,
                                    "package_execution_source": "package" if present else "inherited original bytecode",
                                    "source_sha256": digest(source), "package_sha256": digest(current)})
            for root in roots.values():
                result = subprocess.run([str(WORK / "tools/bin/bbsq.exe"), "-d", *(str(root / name) for name in FILES)],
                                        capture_output=True, timeout=45)
                if result.returncode:
                    raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
            report.update(static_extraction="passed", bytecode_files=sources, logic_checks=checks)
            original = execute(roots["original"], output, "original")
            current = execute(roots["package"], output, "package")
            cases = check_execution(original, current)
            dialogues = []
            for key in sorted(original):
                if not key.endswith(".prepared"):
                    continue
                prefix = key.removesuffix(".prepared")
                dialogues.append({"id": prefix, "source_template": original[prefix + ".template"],
                    "package_template": current[prefix + ".template"],
                    "source_variables_applied": original[key], "package_variables_applied": current[key],
                    "unresolved_variables": sorted(set(re.findall(r"%[A-Za-z_]+%", current[key]))),
                    "branch_selection": "not executed; all real createScreens branches retained",
                    "interpolation": "fixture only; actual onPrepareVariables values substituted"})
            if len(dialogues) != 2:
                raise ValueError("Expected real Task and TaskSouthern screen templates")
            report.update(status="passed", actual_bytecode_execution="passed", sentence_cases=cases,
                          dialogue_cases=dialogues,
                          executed_outputs={key: {"source": original[key], "package": current[key]} for key in original},
                          cache_and_serialization="real courier/base-contract/tag-collection methods executed; unchanged IDs and cache roundtrip")
    except Exception as exc:
        report["error"] = str(exc)
    target = output / "validation.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # This compact companion is the UI test input; it is deliberately pre-UI.
    if report["status"] == "passed":
        (output / "ui-sentences.json").write_text(json.dumps({"schema_version": 1,
            "package_sha256": report["package_sha256"], "game_started": False,
            "cases": report["sentence_cases"], "dialogue_cases": report["dialogue_cases"]},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "game_started", "actual_bytecode_execution", "static_extraction")}
                     | {"report": str(target), "error": report.get("error", "")}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
