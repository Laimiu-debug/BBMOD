"""Small, versioned public seed format shared by the desktop and the Hub."""
from dataclasses import asdict
import hashlib
import json
import re

from .config_emitter import ORIGIN_LABELS
from .log_watcher import SeedResult
from .presentation import brothers, metric, named_count

MAX_SHARE_BYTES = 64 * 1024
LEVELS = ("combat_difficulty", "economic_difficulty", "budget_difficulty")
LINE_PREFIXES = ("TeamInfo:", "CharInfo:", "Trait:", "LairInfo:", "NamedInfo:",
                 "SettlementInfo:", "BuildInfo:", "AttachedInfo:", "ItemInfo(")


def seed_key(result: SeedResult) -> str:
    # Seeds are case-sensitive. Search round is not part of a campaign's identity.
    identity = [result.seed, result.origin, result.game_version, *[getattr(result, k) for k in LEVELS]]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=True).encode()).hexdigest()


def share_payload(result: SeedResult, note="") -> dict:
    value = {"schema_version": 1, "record": asdict(result), "note": note.strip()}
    validate_share(value)
    return value


def validate_share(value) -> tuple[SeedResult, str]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "record", "note"} or type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("不支持的种子分享格式")
    if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_SHARE_BYTES:
        raise ValueError("种子档案超过 64 KB")
    data, note = value["record"], value["note"]
    if not isinstance(data, dict) or set(data) != set(SeedResult.__dataclass_fields__):
        raise ValueError("种子档案字段不完整")
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
