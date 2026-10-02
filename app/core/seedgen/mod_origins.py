"""Explicit adapters for origin mods; only the selected origin package is loaded."""
import hashlib
import json
import re
import zipfile

from ..modinfo import analyze_zip

AFEI_ORIGIN = "scenario.afeix_expedition"
AFEI_MOD = "mod_afeix_expedition"
AFEI_SCENARIO = "scripts/scenarios/world/afeix_expedition_scenario.nut"


def validate_mod_environment(mods):
    if not isinstance(mods, list) or len(mods) > 16:
        raise ValueError("MOD 环境信息无效")
    ids = set()
    for mod in mods:
        if (not isinstance(mod, dict) or set(mod) != {"id", "name", "version", "sha256"}
                or any(not isinstance(v, str) for v in mod.values())
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,95}", mod["id"])
                or not re.fullmatch(r"[0-9a-f]{64}", mod["sha256"])
                or not 1 <= len(mod["name"]) <= 80 or not 1 <= len(mod["version"]) <= 32
                or any(ord(c) < 32 for c in mod["name"] + mod["version"])
                or mod["id"] in ids):
            raise ValueError("MOD 名称、版本或文件校验值无效")
        ids.add(mod["id"])
    return ids


def emit_mod_environment(mods, game_version=""):
    validate_mod_environment(mods)
    encoded = json.dumps(mods, ensure_ascii=False, separators=(',', ':'))
    return ("::SeedGenerator.ModEnvironment <- " + json.dumps(encoded, ensure_ascii=False) + ";\n"
            + "::SeedGenerator.ModGameVersion <- " + json.dumps(game_version) + ";\n")


def origin_payload(data_dir, origin, hooks_bytes):
    """Resolve an enabled package before the session changes any game files."""
    if origin != AFEI_ORIGIN:
        return {}, []
    candidates = []
    for path in sorted(data_dir.glob("*.zip")):
        info = analyze_zip(path)
        if any(reg.mod_id == AFEI_MOD for reg in info.registrations):
            candidates.append((path, info))
    if not candidates:
        raise ValueError("请先在 MOD 军械库安装并启用阿飞远征团主包，再刷阿飞起源种子")
    if len(candidates) != 1:
        raise ValueError("检测到多个阿飞远征团主包，请只启用一个版本后再刷种子")
    path, info = candidates[0]
    if info.analysis_errors:
        raise ValueError("阿飞主包无法读取：" + "；".join(info.analysis_errors))
    reg = next(reg for reg in info.registrations if reg.mod_id == AFEI_MOD)
    if not reg.numeric_version_ok or reg.api != "legacy":
        raise ValueError("当前阿飞主包不支持 Legacy Hooks，请使用兼容版本")
    with zipfile.ZipFile(path) as archive:
        if AFEI_SCENARIO not in archive.namelist():
            raise ValueError("当前阿飞主包没有受支持的阿飞远征团起源，请更新主包")
        if archive.testzip() is not None:
            raise ValueError("阿飞主包校验失败，请重新安装")
    content = path.read_bytes()
    # Name collisions with the generator's own files must fail before mutation.
    if path.name.lower() == "mod_hooks.zip":
        raise ValueError("阿飞主包文件名不能占用 mod_hooks.zip")
    mods = [
        {"id": AFEI_MOD, "name": "阿飞远征团", "version": info.package_version or reg.version,
         "sha256": hashlib.sha256(content).hexdigest()},
        {"id": "mod_hooks", "name": "Legacy Modding Script Hooks", "version": "21.1",
         "sha256": hashlib.sha256(hooks_bytes).hexdigest()},
    ]
    return {path.name: content}, mods
