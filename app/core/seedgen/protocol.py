"""Small, versioned public seed format shared by the desktop and the Hub."""
from dataclasses import asdict
import hashlib
import json
import re

from .config_emitter import ORIGIN_LABELS
from .log_watcher import SeedResult
from .presentation import brothers, metric, named_count
from .mod_origins import AFEI_ORIGIN, AFEI_MOD, validate_mod_environment

MAX_SHARE_BYTES = 64 * 1024
LEVELS = ("combat_difficulty", "economic_difficulty", "budget_difficulty")
LINE_PREFIXES = ("TeamInfo:", "CharInfo:", "Trait:", "LairInfo:", "NamedInfo:",
                 "SettlementInfo:", "BuildInfo:", "AttachedInfo:", "ItemInfo(")
ENVIRONMENT_FIELDS = {"dlc_mask", "mods"}


def seed_key(result: SeedResult) -> str:
    # Seeds are case-sensitive. Search round is not part of a campaign's identity.
    identity = [result.seed, result.origin, result.game_version, *[getattr(result, k) for k in LEVELS]]
    if result.mods or result.dlc_mask is not None:
        identity.append({"dlc_mask": result.dlc_mask, "mods": sorted(result.mods, key=lambda mod: mod["id"])})
    return hashlib.sha256(json.dumps(identity, ensure_ascii=True).encode()).hexdigest()


def share_payload(result: SeedResult, note="") -> dict:
    record = asdict(result)
    schema = 2 if result.mods or result.dlc_mask is not None else 1
    if schema == 1:
        for key in ENVIRONMENT_FIELDS:
            record.pop(key)
    value = {"schema_version": schema, "record": record, "note": note.strip()}
    validate_share(value)
    return value


def validate_share(value) -> tuple[SeedResult, str]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "record", "note"} or type(value["schema_version"]) is not int or value["schema_version"] not in (1, 2):
        raise ValueError("不支持的种子分享格式")
    if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_SHARE_BYTES:
        raise ValueError("种子档案超过 64 KB")
    data, note = value["record"], value["note"]
    fields = set(SeedResult.__dataclass_fields__)
    if not isinstance(data, dict) or not fields - ENVIRONMENT_FIELDS <= set(data) <= fields or (value["schema_version"] == 2 and set(data) != fields):
        raise ValueError("种子档案字段不完整")
    data = {"mods": [], "dlc_mask": None, **data}
    if value["schema_version"] == 1 and (data["mods"] or data["dlc_mask"] is not None):
        raise ValueError("包含 MOD 或 DLC 环境的种子档案需要格式版本 2")
    if data["dlc_mask"] is not None and (type(data["dlc_mask"]) is not int or not 0 <= data["dlc_mask"] <= 65535):
        raise ValueError("DLC 配置标记无效")
    ids = validate_mod_environment(data["mods"])
    if data["origin"] == AFEI_ORIGIN and (not {AFEI_MOD, "mod_hooks"} <= ids or data["dlc_mask"] is None):
        raise ValueError("阿飞起源种子缺少主包、框架版本或 DLC 记录，不能公开分享")
    if not isinstance(note, str) or len(note) > 1000 or any(ord(c) < 32 and c not in '\n\t' for c in note):
        raise ValueError("介绍最多 1000 字，不能包含控制字符")
    if not isinstance(data["seed"], str) or not re.fullmatch(r"[A-Za-z]{10}", data["seed"]):
        raise ValueError("种子码必须是 10 个英文字母，区分大小写")
    if not isinstance(data["origin"], str) or data["origin"] not in ORIGIN_LABELS or data["origin"] == "common":
        raise ValueError("请分享记录了开局起源的种子")
    if data["done"] is not True:
        raise ValueError("记录尚未完整，不能公开分享")
    if not isinstance(data["game_version"], str) or not re.fullmatch(r"(?:\d{1,3}\.){2,3}\d{1,3}|", data["game_version"]):
        raise ValueError("游戏版本格式不正确")
    for key in LEVELS:
        if data[key] is not None and (type(data[key]) is not int or data[key] not in (0, 1, 2)):
            raise ValueError("开局难度必须为 0、1、2 或未记录")
    if data['origin'] == AFEI_ORIGIN and (not data['game_version'] or any(data[key] is None for key in LEVELS)):
        raise ValueError("阿飞起源种子缺少游戏版本或开局难度，不能公开分享")
    for key in ("loop_idx", "bro_output_type", "map_output_type", "lair_output_type"):
        if type(data[key]) is not int or not (-1 if key != "loop_idx" else 0) <= data[key] <= 2**53:
            raise ValueError("种子计数格式不正确")
    lines = data["lines"]
    if not isinstance(lines, list) or not 1 <= len(lines) <= 256:
        raise ValueError("档案需要包含完整的种子详情")
    for line in lines:
        if not isinstance(line, str) or len(line) > 2000 or not line.startswith(LINE_PREFIXES) or any(ord(c) < 32 for c in line):
            raise ValueError("档案中包含不支持的记录行")
        if any(len(token) > 12 for token in re.findall(r"\d+", line)):
            raise ValueError("档案中的数值超出范围")
    result = SeedResult(**data)
    people = brothers(result)
    if len(people) > 27:
        raise ValueError("开局兄弟数量超出范围")
    for brother in people:
        if any(not -100 <= n <= 2000 for n in [*brother.initial.values(), *brother.projected.values()]) or len('|'.join(brother.traits)) > 1900:
            raise ValueError("人物属性超出范围")
    if (metric(result, 'SettlementInfo:', 'Port') or 0) > 100 or (named_count(result) or 0) > 1000:
        raise ValueError("地图统计超出范围")
    return result, note.strip()
