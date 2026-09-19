"""Readable seed records and short sharing text, based only on recorded facts."""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .config_emitter import ATTRIBUTES, ORIGIN_LABELS, DIFFICULTY_LABELS, BUDGET_LABELS
from .log_watcher import SeedResult
from .traits import trait_name
from .weapons import NAMED_WEAPONS
from .config_emitter import NAMED_ATTR_LABELS

FORMATS = {"种子档案（含详情）": "detail", "弹幕模式（一行一条）": "danmaku", "仅种子码": "seed"}
OPENERS = ["自动开场白", "卡大货了？", "缺大哥？", "跑商发愁？", "想找红装？", "不加开场白"]
ROLES = {"Melee": "近战", "Range": "远程", "Guard": "盾卫", "Throw": "投掷",
         "Leader": "队长", "Duel": "决斗", "Polearm": "长柄", "Initiative": "先攻", "Useless": "待分配"}
ITEMS = {"Armor": "红甲", "Helmet": "红盔", "Shield": "红盾", "OneHanded": "单手红武",
         "TwoHanded": "双手红武", "RangedWeapon": "远程红武"}
BUILDINGS = {"Build": "建筑总数", "Armorsmith": "铠甲匠", "Weaponsmith": "武器匠",
    "Fletcher": "弓弩匠", "Barber": "理发店", "Kennel": "犬舍", "Tavern": "酒馆",
    "Taxidermist": "标本匠", "Temple": "神殿", "Traininghall": "训练场"}
ATTACHED = {"Attached": "附属地点总数", "Barracks": "设防哨站", "GuardedCheckpoint": "守卫关卡",
    "MilitiaTrainingCamp": "民兵训练营", "StoneWatchTower": "石制瞭望塔", "WoodenWatchTower": "木制瞭望塔",
    "BlastFurnace": "高炉", "GemMine": "宝石矿", "SaltMine": "盐矿", "Brewery": "啤酒坊",
    "Winery": "葡萄酒庄", "ArrowMaker": "制箭坊", "HunterCabin": "猎人小屋",
    "leatherTanner": "制革坊", "LumberCamp": "伐木营地", "MushroomGrove": "蘑菇林", "IronVein": "铁矿脉"}
LAIRS = {"Bandit": "强盗", "Nomad": "游牧民", "Barbarian": "蛮族", "Goblin": "地精",
         "Undead": "亡灵", "Orc": "兽人", "Other": "其他"}
ITEM_ATTRIBUTES = {"Stamina": "疲劳上限修正", "Armor": "护甲", "MinDamage": "最低伤害",
    "MaxDamage": "最高伤害", "ArmorDamage": "破甲效率", "DirectDamage": "无视护甲比例",
    "ChanceToHitHead": "命中头部几率", "AdditionalAccuracy": "命中加成", "AmmoMax": "弹药容量",
    "FatigueOnSkillUse": "技能疲劳修正", "Condition": "耐久", "MeleeDefense": "近战防御", "RangedDefense": "远程防御"}
_ATTRIBUTE = re.compile(r"\b(" + "|".join(ATTRIBUTES) + r"):(-?\d+)\((-?\d+)\)([0-3])")


@dataclass
class Brother:
    index: int
    role: str
    initial: dict[str, int] = field(default_factory=dict)
    projected: dict[str, int] = field(default_factory=dict)
    stars: dict[str, int] = field(default_factory=dict)
    traits: list[str] = field(default_factory=list)


def brothers(result: SeedResult) -> list[Brother]:
    parsed = []
    for line in result.lines:
        if line.startswith('Trait:'):
            if parsed:
                parsed[-1].traits = list(dict.fromkeys(line.removeprefix('Trait:').split()))
            continue
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


def world_details(result: SeedResult) -> list[str]:
    sections = []
    for prefix, title, labels in (
        ("SettlementInfo:", "城镇与交通", {"Settlements": "聚落", "Port": "港口", "CityPort": "城邦港口",
            "Products": "特产总数", "Connected": "连通聚落"}),
        ("BuildInfo:", "城镇建筑", BUILDINGS), ("AttachedInfo:", "附属地点", ATTACHED),
        ("NamedInfo:", "红装数量", {**ITEMS, "Sum": "合计"}),
    ):
        values = [f"{label} {value}" for key, label in labels.items()
                  if (value := metric(result, prefix, key)) is not None]
        if values:
            sections += ["", title, "；".join(values)]
    for line in result.lines:
        if line.startswith("LairInfo:"):
            match = re.match(r"LairInfo:\s*(.*?)\((\w+)\)\s+(\d+)\s+(.+?)\s+([\d.]+)-(.+)$", line)
            if match:
                name, kind, strength, town, distance, direction = match.groups()
                directions = {"upper": "北", "upper_right": "东北", "right": "东", "lower_right": "东南",
                    "lower": "南", "lower_left": "西南", "left": "西", "upper_left": "西北",
                    "N": "北", "NE": "东北", "E": "东", "SE": "东南", "S": "南", "SW": "西南", "W": "西", "NW": "西北",
                    "north": "北", "northeast": "东北", "east": "东", "southeast": "东南", "south": "南", "southwest": "西南", "west": "西", "northwest": "西北"}
                direction = directions.get(direction, directions.get(direction.lower(), direction))
                sections += ["", f"营地：{name}（{LAIRS.get(kind, '未知驻军')}）",
                    f"驻军强度 {strength}；最近聚落 {town}；距离 {distance}，方位 {direction}"]
        elif line.startswith("ItemInfo("):
            match = re.match(r"ItemInfo\((\w+)\):\s*([^\s(]+)(?:\(([^)]*)\))?\s+(.*)", line)
            if match:
                kind, item_id, rolls, fields = match.groups()
                values = []
                for key, value in re.findall(r"(\w+):(-?[\d.]+)", fields):
                    if key not in ITEM_ATTRIBUTES:
                        continue
                    if key in {"ArmorDamage", "DirectDamage"}:
                        value = f"{float(value) * 100:g}%"
                    elif key == "ChanceToHitHead":
                        value += "%"
                    values.append(f"{ITEM_ATTRIBUTES[key]} {value}")
                quality = [f"{NAMED_ATTR_LABELS[key]}品质 {value}%"
                           for key, value in re.findall(r"(\w+):([\d.]+)%", rolls or '')
                           if key in NAMED_ATTR_LABELS]
                title = NAMED_WEAPONS.get(item_id, ITEMS.get(kind, '红装'))
                sections.append(f"{title}：" + ("；".join(quality + values) or "未记录属性"))
    return sections


def format_seed(result: SeedResult, mode: str = "detail", opener: str = "自动开场白", note: str = "") -> str:
    if mode == "seed":
        return result.seed
    facts = highlights(result)
    origin = ORIGIN_LABELS.get(result.origin, result.origin)
    campaign = []
    if result.combat_difficulty in DIFFICULTY_LABELS:
        campaign.append("战斗" + DIFFICULTY_LABELS[result.combat_difficulty])
    if result.economic_difficulty in DIFFICULTY_LABELS:
        campaign.append("经济" + DIFFICULTY_LABELS[result.economic_difficulty])
    if result.budget_difficulty in BUDGET_LABELS:
        campaign.append("资金" + BUDGET_LABELS[result.budget_difficulty])
    if mode == "danmaku":
        clauses = ([origin] if origin else []) + facts
        if campaign:
            clauses.append(" / ".join(campaign))
        if not result.done:
            clauses.append("记录未完整，需核对")
        if note.strip():
            clauses.append(" ".join(note.split()))
        description = "，".join(clauses) or "已命中当前条件，详细属性尚未记录"
        return f"{opening(result, opener)}{result.seed} {description}"
    lines = [f"种子：{result.seed}", f"起源：{origin or '日志未记录'}", f"发现于第 {result.loop_idx} 轮",
             "亮点：" + (" · ".join(facts) or "暂无可解析的属性详情")]
    if campaign:
        lines.insert(2, "开局设置：" + " · ".join(campaign))
    if result.team_score is not None:
        lines.append(f"高级队伍评分：{result.team_score:.2f}（算法的相对评分，不是属性值、百分比或胜率）")
    if not result.done:
        lines.append("记录未完整：日志在本条结束前中断，以下仅展示已收到的数据。")
    if note.strip():
        lines += ["", "补充介绍 / 路线：" + note.strip()]
    people = brothers(result)
    if people:
        lines += ["", "开局兄弟（初始 → 11级预估；按每级提升该属性计算）"]
        for brother in people:
            values = [f"{label} {brother.initial[key]}→{brother.projected[key]}（{brother.stars[key]}星）"
                      for key, label in ATTRIBUTES.items() if key in brother.projected]
            lines.append(f"兄弟{brother.index} · {brother.role}：" + "；".join(values))
            if brother.traits:
                lines.append('特质：' + '、'.join(trait_name(key) for key in brother.traits))
    lines.extend(world_details(result))
    return "\n".join(lines)


def raw_record(result: SeedResult) -> str:
    return f"Seed: {result.seed} LoopIdx:{result.loop_idx} Origin:{result.origin}\n" + "\n".join(result.lines)


def format_collection(results: list[SeedResult], mode: str, opener: str, notes: dict[str, str]) -> str:
    separator = "\n\n" + "─" * 32 + "\n\n" if mode == "detail" else "\n"
    return separator.join(format_seed(r, mode, opener, notes.get(note_key(r), "")) for r in results) + "\n"


def note_key(result: SeedResult) -> str:
    return f"{result.origin}|{result.seed}"
