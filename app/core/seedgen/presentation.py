"""Readable seed records and short sharing text, based only on recorded facts."""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .config_emitter import ATTRIBUTES, ORIGIN_LABELS
from .log_watcher import SeedResult

FORMATS = {"种子档案（含详情）": "detail", "弹幕模式（一行一条）": "danmaku", "仅种子码": "seed"}
OPENERS = ["自动开场白", "卡大货了？", "缺大哥？", "跑商发愁？", "想找红装？", "不加开场白"]
ROLES = {"Melee": "近战", "Range": "远程", "Guard": "盾卫", "Throw": "投掷",
         "Leader": "队长", "Duel": "决斗", "Polearm": "长柄", "Initiative": "先攻", "Useless": "待分配"}
ITEMS = {"Armor": "红甲", "Helmet": "红盔", "Shield": "红盾", "OneHanded": "单手红武",
         "TwoHanded": "双手红武", "RangedWeapon": "远程红武"}
_ATTRIBUTE = re.compile(r"\b(" + "|".join(ATTRIBUTES) + r"):(-?\d+)\((-?\d+)\)([0-3])")


@dataclass
class Brother:
    index: int
    role: str
    initial: dict[str, int] = field(default_factory=dict)
    projected: dict[str, int] = field(default_factory=dict)
    stars: dict[str, int] = field(default_factory=dict)


def brothers(result: SeedResult) -> list[Brother]:
    parsed = []
    for line in result.brothers:
        head = re.match(r"CharInfo:\s*(\d+)\s+(\S+?):", line)
        if not head:
            continue
        brother = Brother(int(head[1]) + 1, ROLES.get(head[2], head[2]))
        for key, initial, projected, stars in _ATTRIBUTE.findall(line):
            brother.initial[key] = int(initial)
            brother.projected[key] = int(projected)
            brother.stars[key] = int(stars)
        parsed.append(brother)
    return parsed


def metric(result: SeedResult, line_prefix: str, key: str) -> int | None:
    for line in result.lines:
        if line.startswith(line_prefix):
            match = re.search(r"\b" + re.escape(key) + r":(\d+)\b", line)
            if match:
                return int(match[1])
    return None


def named_count(result: SeedResult) -> int | None:
    total = metric(result, "NamedInfo:", "Sum")
    return total if total is not None else (len(result.named_items) if result.named_items else None)


def highlights(result: SeedResult) -> list[str]:
    facts = []
    ports = metric(result, "SettlementInfo:", "Port")
    if ports is not None:
        facts.append(f"{ports}座港口")
    people = brothers(result)
    melee = sum(b.projected.get("MeleeSkill", -100) >= 90 for b in people)
    ranged = sum(b.projected.get("RangedSkill", -100) >= 90 for b in people)
    if melee:
        facts.append(f"{melee}个预估11级90+近战大哥")
    if ranged:
        facts.append(f"{ranged}个预估11级90+远程好手")
    if not melee and not ranged and people:
        maximum = max((b.projected.get("MeleeSkill", -100) for b in people), default=-100)
        if maximum >= 0:
            facts.append(f"最高预估11级近战{maximum}")
    armor = metric(result, "NamedInfo:", "Armor")
    if armor is None and result.named_items:
        armor = sum("ItemInfo(Armor):" in item for item in result.named_items)
    if armor:
        facts.append(f"{armor}件红甲")
    total = named_count(result)
    if total is not None:
        facts.append(f"共{total}件红装")
    return facts


def opening(result: SeedResult, selection: str) -> str:
    if selection == "不加开场白":
        return ""
    if selection != "自动开场白":
        return selection.strip()
    if any(b.projected.get("MeleeSkill", -100) >= 90 for b in brothers(result)):
        return "缺大哥？"
    if (metric(result, "SettlementInfo:", "Port") or 0) >= 6:
        return "跑商发愁？"
    if (named_count(result) or 0) > 0:
        return "想找红装？"
    return "找新开局？"


def format_seed(result: SeedResult, mode: str = "detail", opener: str = "自动开场白", note: str = "") -> str:
    if mode == "seed":
        return result.seed
    facts = highlights(result)
    origin = ORIGIN_LABELS.get(result.origin, result.origin)
    if mode == "danmaku":
        clauses = ([origin] if origin else []) + facts
        if note.strip():
            clauses.append(" ".join(note.split()))
        description = "，".join(clauses) or "已命中当前条件，详细属性尚未记录"
        return f"{opening(result, opener)}{result.seed} {description}"
    lines = [f"种子：{result.seed}", f"起源：{origin or '日志未记录'}", f"发现于第 {result.loop_idx} 轮",
             "亮点：" + (" · ".join(facts) or "暂无可解析的属性详情")]
    if result.team_score is not None:
        lines.append(f"高级评分：队伍平均 {result.team_score:.2f}（生成器综合评分）")
    if note.strip():
        lines += ["", "补充介绍 / 路线：" + note.strip()]
    people = brothers(result)
    if people:
        lines += ["", "开局兄弟（初始 → 11级预估；按每级提升该属性计算）"]
        for brother in people:
            values = [f"{label} {brother.initial[key]}→{brother.projected[key]}（{brother.stars[key]}星）"
                      for key, label in ATTRIBUTES.items() if key in brother.projected]
            lines.append(f"兄弟{brother.index} · {brother.role}：" + "；".join(values))
    if result.lines:
        lines += ["", "原始记录（便于核对）", *result.lines]
    return "\n".join(lines)


def format_collection(results: list[SeedResult], mode: str, opener: str, notes: dict[str, str]) -> str:
    separator = "\n\n" + "─" * 32 + "\n\n" if mode == "detail" else "\n"
    return separator.join(format_seed(r, mode, opener, notes.get(note_key(r), "")) for r in results) + "\n"


def note_key(result: SeedResult) -> str:
    return f"{result.origin}|{result.seed}"
