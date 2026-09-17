"""种子生成器配置生成器：GUI 配置状态 → seed_generator/config_*.nut。

策略（外科手术式编辑，保证与原版语义一致）：
- config_common.nut：整体生成（结构简单、全量可控）
- config_role/map/lair_condition.nut：默认原样复制 payload 模板；
  仅当用户自定义某起源 / 条件数组时，用数据模型重新渲染对应块，其余块保留原文。

.nut 条件行的参数布局（来自原版注释与判定器实现）：
  人物: [类型, 阈值, 数量, 职业枚举, ("trait.x")*]   （RoleTraitScoreIndex: [类型, 索引, 阈值, 职业, trait*]）
  地图: [指标, 值, 指标, 值, ...]（>= 满足，PortMeanDis/MeanDis/ConnectedRoad 为 <=）
  红装: [类型, ...类型专属参数]
"""
from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from .traits import validate_traits

ROLES = {
    "RoleMelee": 0, "RoleRange": 1, "RoleGuard": 2, "RoleThrow": 3,
    "RoleLeader": 4, "RoleDuel": 5, "RolePolearm": 6, "RoleInitiative": 7,
    "RoleUseless": 8,
}
ROLE_LABELS = {
    "RoleMelee": "近战", "RoleRange": "远程", "RoleGuard": "盾卫", "RoleThrow": "柄投",
    "RoleLeader": "队长", "RoleDuel": "决斗", "RolePolearm": "长柄", "RoleInitiative": "主动",
}

BRO_OUTPUT = {
    "TeamScore": 0, "RoleScore": 1, "AnyRoleScore": 2, "RoleAttr": 3,
    "RoleTraitScore": 4, "RoleTraitScoreIndex": 5,
    "BrotherFilter": 6,
}
BRO_OUTPUT_LABELS = {
    "TeamScore": "队伍平均分", "RoleScore": "指定职业分", "AnyRoleScore": "不限职业分",
    "RoleAttr": "11级预估属性", "RoleTraitScore": "职业分+特性", "RoleTraitScoreIndex": "指定兄弟分+特性",
    "BrotherFilter": "属性与人物特质",
}

# RoleAttr reads eight projected level-11 attributes in this exact order.
ATTRIBUTES = {
    "Hitpoints": "生命", "Bravery": "决心", "Stamina": "疲劳上限",
    "MeleeSkill": "近战命中", "RangedSkill": "远程命中",
    "MeleeDefense": "近战防御", "RangedDefense": "远程防御", "Initiative": "先攻",
}
SCORE_EXPLANATION = (
    "队伍平均分 = 每名开局兄弟分配职业后的评分之和 ÷ 兄弟人数。\n"
    "例如三人评分为 0.9、0.8、0.7，平均分就是 0.8。职业名额会影响分配结果。\n\n"
    "个人评分由初始属性、11级预估属性和特性共同计算。近战职业的权重为："
    "近战命中35%、近战防御30%、疲劳上限20%、生命10%、决心5%。\n"
    "每项属性都先按脚本规定的上下基准换算，再按权重相加；初始属性和特性另有加减分。"
    "因此分数可以低于0或超过1，0.8无法直接换算成近战数值、胜率或百分位。\n\n"
    "只想找90+近战的兄弟，选择「属性与特质」，将近战命中设为90即可。"
    "11级属性按每级都选择提升该属性估算，不包含装备和额外加点特技。"
)

MAP_METRICS = {
    "SettlementNum": 0, "PortNum": 1, "CityPortNum": 2, "PortMeanDis": 3, "MeanDis": 4,
    "ArenaPort": 5, "ProductsNum": 6, "ProductsValue": 7, "PortProductsValue": 8,
    "ConnectedNum": 9, "ConnectedRoad": 10, "BuildNum": 11, "AttachedNum": 12,
    "UpperLeftPortNum": 13, "LowerLeftPortNum": 14, "MiddlePortNum": 15,
    "UpperRightPortNum": 16, "LowerRightPortNum": 17, "PortTypeNum": 18,
    "ArmorsmithNum": 19, "WeaponsmithNum": 20, "FletchernNum": 21,
    "ConnectedLargeSettlementsNum": 22, "ConnectedLargeFortNum": 23, "ConnectedPortNum": 24,
    "SwampNum": 25, "SnowNum": 26, "TundraNum": 27, "NoLostLargeSettlements": 28,
    "GemMineNum": 29, "SaltMineNum": 30,
}
MAP_METRIC_LABELS = {
    "SettlementNum": "城市数≥", "PortNum": "港口数≥", "CityPortNum": "城邦港≥",
    "PortMeanDis": "港口聚类均距≤", "MeanDis": "城市均距≤", "ArenaPort": "竞技场港≥",
    "ProductsNum": "特产数≥", "ProductsValue": "特产价值≥", "PortProductsValue": "港城特产价值≥",
    "ConnectedNum": "环线城市≥", "ConnectedRoad": "环线道路≤", "BuildNum": "建筑数≥",
    "AttachedNum": "附属建筑≥", "PortTypeNum": "港口方位类型≥", "ArmorsmithNum": "甲店≥",
    "WeaponsmithNum": "武器店≥", "FletchernNum": "弓弩店≥", "ConnectedLargeSettlementsNum": "环线大城≥",
    "ConnectedLargeFortNum": "环线大堡≥", "ConnectedPortNum": "环线港口≥", "SwampNum": "沼泽城≥",
    "SnowNum": "雪地城≥", "TundraNum": "苔原城≥", "NoLostLargeSettlements": "不丢大城",
    "GemMineNum": "宝石矿≥", "SaltMineNum": "盐矿≥",
}

LAIR_OUTPUT = {"NamedNumber": 0, "NamedAttrValue": 1, "NamedAttrValueBroOutput": 2, "NamedAttrValueStrength": 3}
LAIR_OUTPUT_LABELS = {
    "NamedNumber": "红装总数", "NamedAttrValue": "红装属性roll",
    "NamedAttrValueBroOutput": "红装属性+人物条件", "NamedAttrValueStrength": "红装属性+营地强度",
}
NAMED_ATTRS = {
    "RegularDamage": 0, "ArmorDamageMult": 1, "ChanceToHitHead": 2, "DirectDamageAdd": 3,
    "StaminaModifier": 4, "ShieldDamage": 5, "AmmoMax": 6, "AdditionalAccuracy": 7,
    "FatigueOnSkillUse": 8, "MeleeDefense": 9, "RangedDefense": 10, "Condition": 11,
}
NAMED_ATTR_LABELS = {
    "RegularDamage": "伤害", "ArmorDamageMult": "破甲", "ChanceToHitHead": "爆头率",
    "DirectDamageAdd": "穿甲", "StaminaModifier": "疲劳", "ShieldDamage": "破盾",
    "AmmoMax": "弹药", "AdditionalAccuracy": "命中", "FatigueOnSkillUse": "技能疲劳",
    "MeleeDefense": "近防", "RangedDefense": "远防", "Condition": "耐久",
}

ORIGIN_LABELS = {
    "scenario.early_access": "新战团", "scenario.southern_quickstart": "南方雇佣兵",
    "scenario.trader": "贸易商队", "scenario.militia": "农民团", "scenario.lone_wolf": "独狼",
    "scenario.rangers": "游侠", "scenario.paladins": "圣骑士", "scenario.raiders": "掠夺者",
    "scenario.anatomists": "解剖学者", "scenario.beast_hunters": "猎兽人",
    "scenario.gladiators": "角斗士", "scenario.manhunters": "猎奴人",
    "scenario.cultists": "达库尔信徒", "scenario.deserters": "逃兵（仅慢速）",
    "common": "通用预设（未配置起源）",
}


# ---------------- 配置数据模型 ----------------

@dataclass
class CommonConfig:
    GenerateSettlementMode: bool = False
    GenerateBrotherMode: bool = True
    MatchingBrotherGenerateSettlement: bool = True
    OnlyPrintMatchingSettlement: bool = False
    PrintLairInfo: bool = True
    PrintLairNamedDetail: bool = True
    OnlyPrintMatchingLair: bool = False
    EnableLowercaseSeed: bool = False
    UseBrotherLevel11RealAttr: bool = True
    FastBrotherGenerateMode: bool = True
    debug_seeds: list[str] = field(default_factory=list)
    debug_mode: bool = False

    @staticmethod
    def preset(mode: str) -> "CommonConfig":
        """五种推荐模式（对应 config_common.nut 顶部注释）。"""
        presets = {
            "map_only": dict(GenerateSettlementMode=True, GenerateBrotherMode=False,
                             OnlyPrintMatchingSettlement=True, PrintLairInfo=False),
            "bro_only": dict(GenerateSettlementMode=False, GenerateBrotherMode=True,
                             MatchingBrotherGenerateSettlement=False,
                             OnlyPrintMatchingSettlement=False, PrintLairInfo=False, PrintLairNamedDetail=False),
            "bro_map": dict(GenerateSettlementMode=False, GenerateBrotherMode=True,
                            MatchingBrotherGenerateSettlement=True, OnlyPrintMatchingSettlement=True),
            "bro_lair": dict(GenerateSettlementMode=False, GenerateBrotherMode=True,
                             MatchingBrotherGenerateSettlement=True, OnlyPrintMatchingSettlement=False,
                             PrintLairInfo=True, PrintLairNamedDetail=True, OnlyPrintMatchingLair=True),
            "all": dict(GenerateSettlementMode=False, GenerateBrotherMode=True,
                        MatchingBrotherGenerateSettlement=True, OnlyPrintMatchingSettlement=True,
                        PrintLairInfo=True, PrintLairNamedDetail=True, OnlyPrintMatchingLair=True),
        }
        return CommonConfig(**presets[mode])


@dataclass
class BroCondition:
    type: str                 # BRO_OUTPUT 键名
    args: list                # 其余参数（数值或 Role 枚举名字符串或 trait id）
    comment: str = ""


def attribute_condition(count: int, thresholds: dict[str, int]) -> BroCondition:
    """Require the same N brothers to satisfy every supplied attribute minimum."""
    if not 1 <= count <= 27:
        raise ValueError("兄弟人数应在1至27之间")
    if not thresholds or any(key not in ATTRIBUTES for key in thresholds):
        raise ValueError("请至少设置一项有效属性")
    if any(not isinstance(value, int) or value < 0 for value in thresholds.values()):
        raise ValueError("属性门槛必须是非负整数")
    return BroCondition("RoleAttr", [count, *(thresholds.get(key, -100) for key in ATTRIBUTES)])


def score_condition(kind: str, score: float, count: int, role: str) -> BroCondition:
    if kind == "TeamScore":
        return BroCondition(kind, [score])
    if kind == "AnyRoleScore":
        # The Squirrel checker consumes pairs, without a role argument.
        return BroCondition(kind, [score, count])
    if kind == "RoleScore" and role in ROLES:
        return BroCondition(kind, [score, count, role])
    raise ValueError("未知评分条件")


def brother_condition(count: int, thresholds: dict[str, int], required=(), excluded=(), match='all') -> BroCondition:
    """Count distinct brothers satisfying the attributes AND the trait rule."""
    required, excluded = validate_traits(required, excluded, match)
    if not required and not excluded:
        return attribute_condition(count, thresholds)
    if type(count) is not int or not 1 <= count <= 27:
        raise ValueError('兄弟人数应在1至27之间')
    if any(key not in ATTRIBUTES for key in thresholds) or any(type(v) is not int or v < 0 for v in thresholds.values()):
        raise ValueError('属性门槛必须是有效属性的非负整数')
    return BroCondition('BrotherFilter', [count, [thresholds.get(key, -100) for key in ATTRIBUTES], required, excluded, match == 'all'])


@dataclass
class OriginConfig:
    conditions: list[BroCondition] = field(default_factory=list)
    max_roles: dict[str, int] = field(default_factory=dict)  # Role 枚举名 -> 上限


@dataclass
class SeedGenConfig:
    common: CommonConfig = field(default_factory=CommonConfig)
    origins: dict[str, OriginConfig] = field(default_factory=dict)  # 自定义的起源（未含的用模板默认）
    map_conditions: list[list] | None = None   # None=用模板默认；每行 [指标名, 值, ...]
    lair_conditions: list[list] | None = None  # None=用模板默认


# ---------------- config_common.nut：整体生成 ----------------

def emit_common(cfg: CommonConfig) -> str:
    def b(name: str) -> str:
        return "true" if getattr(cfg, name) else "false"

    debug_seeds = ", ".join(f'"{s}"' for s in cfg.debug_seeds)
    return f"""local gt = this.getroottable();

gt.SeedGenerator.CommonConfig <- {{
\tGenerateSettlementMode = {b("GenerateSettlementMode")},
\tGenerateBrotherMode = {b("GenerateBrotherMode")},
\tMatchingBrotherGenerateSettlement = {b("MatchingBrotherGenerateSettlement")},
\tOnlyPrintMatchingSettlement = {b("OnlyPrintMatchingSettlement")},
\tPrintLairInfo = {b("PrintLairInfo")},
\tPrintLairNamedDetail = {b("PrintLairNamedDetail")},
\tOnlyPrintMatchingLair = {b("OnlyPrintMatchingLair")},
\tEnableLowercaseSeed = {b("EnableLowercaseSeed")},
\tUseBrotherLevel11RealAttr = {b("UseBrotherLevel11RealAttr")},
\tFastBrotherGenerateMode = {b("FastBrotherGenerateMode")},
}};

gt.SeedGenerator.DebugConfig <- {{
\tDebugSeed = [{debug_seeds}],
\tDebugMode = {"true" if cfg.debug_mode else "false"},
}};
"""


# ---------------- 条件渲染 ----------------

def _val(v):
    """参数渲染：Role 枚举名 → Role.X；trait/物品 id 等字符串 → 保留引号字面量。"""
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (list, tuple)):
        return '[' + ', '.join(_val(item) for item in v) + ']'
    if isinstance(v, str) and v in ROLES:
        return f"Role.{v}"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def render_bro_row(c: BroCondition) -> str:
    args = ", ".join(_val(a) for a in c.args)
    comment = f"  # {c.comment}" if c.comment else ""
    return f"[BroOutput.{c.type}, {args}],{comment}"


def render_map_row(row: list) -> str:
    return "[" + ", ".join(
        (f"MapOutput.{v}" if isinstance(v, str) and v in MAP_METRICS else str(v)) for v in row
    ) + "],"


def render_lair_row(row: list) -> str:
    out = []
    for v in row:
        if isinstance(v, str) and v in LAIR_OUTPUT:
            out.append(f"LairOutput.{v}")
        elif isinstance(v, str) and v in NAMED_ATTRS:
            out.append(f"NamedAttr.{v}")
        elif isinstance(v, str):
            out.append(f'"{v}"')
        else:
            out.append(str(v))
    return "[" + ", ".join(out) + "],"


# ---------------- 模板外科手术：按起源替换块 ----------------

RE_ORIGIN_BLOCK = re.compile(
    r'(BroOutputConditionArray\["([^"]+)"\] <-\s*\n)(\[.*?\n)(\];)', re.S
)
RE_MAXROLE_BLOCK = re.compile(
    r'(MaxRoleArray\["([^"]+)"\] <- array\(RoleNum, 0\);)((?:\nMaxRoleArray\["\2"\]\[[^\]]+\] = \d+;.*?#[^\n]*)*)',
)


def emit_role_conditions(template_text: str, cfg: SeedGenConfig) -> str:
    text = template_text
    for origin, oc in cfg.origins.items():
        rows = "\n".join(render_bro_row(c) for c in oc.conditions)
        # 注意：正则第 3 组把数组开符 "[" 一并吞掉，替换块必须补回开符
        block = "[\n" + (rows + "\n" if rows else "")
        found = False

        def sub_block(m: re.Match) -> str:
            nonlocal found
            if m.group(2) == origin:
                found = True
                return m.group(1) + block + m.group(4)
            return m.group(0)

        text = RE_ORIGIN_BLOCK.sub(sub_block, text)
        if not found:
            raise KeyError(f"模板中不存在起源 {origin}")
        if oc.max_roles:
            caps = "\n".join(
                f'MaxRoleArray["{origin}"][Role.{r}] = {n};'
                + (f"  \t# 最多{ROLE_LABELS.get(r, r)}{n}个" if r != "RoleUseless" else "")
                for r, n in oc.max_roles.items()
            )
            # 插到该起源最后一条 MaxRoleArray 上限行之后（Squirrel 后赋值生效，必须放在模板行之后）
            lines = text.splitlines(keepends=True)
            insert_at = None
            for idx, line in enumerate(lines):
                if f'MaxRoleArray["{origin}"] <- array(RoleNum, 0);' in line:
                    insert_at = idx + 1
                elif insert_at is not None and f'MaxRoleArray["{origin}"][' in line:
                    insert_at = idx + 1
                elif insert_at is not None:
                    break
            if insert_at is None:
                raise KeyError(f"模板中不存在 MaxRoleArray[{origin}]")
            lines.insert(insert_at, caps + "\n")
            text = "".join(lines)
    return text


def emit_map_conditions(template_text: str, cfg: SeedGenConfig) -> str:
    if cfg.map_conditions is None:
        return template_text
    rows = "\n".join(render_map_row(r) for r in cfg.map_conditions)
    return re.sub(
        r"(gt\.SeedGenerator\.MapOutputConditionArray <- \[\n).*?(\n\];)",
        lambda m: m.group(1) + rows + m.group(2),
        template_text,
        flags=re.S,
    )


def emit_lair_conditions(template_text: str, cfg: SeedGenConfig) -> str:
    if cfg.lair_conditions is None:
        return template_text
    rows = "\n".join(render_lair_row(r) for r in cfg.lair_conditions)
    return re.sub(
        r"(gt\.SeedGenerator\.LairOutputConditionArray <- \[\n).*?(\n\];)",
        lambda m: m.group(1) + rows + m.group(2),
        template_text,
        flags=re.S,
    )


def write_configs(payload_dir: Path, data_dir: Path, cfg: SeedGenConfig) -> list[Path]:
    """生成 4 个 config_*.nut 写入 data/seed_generator/，返回写入的文件。"""
    import shutil

    src = Path(payload_dir) / "seed_generator"
    dst = Path(data_dir) / "seed_generator"
    dst.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in (
        ("config_common.nut", emit_common(cfg.common)),
        ("config_role_condition.nut", emit_role_conditions((src / "config_role_condition.nut").read_text(encoding="utf-8"), cfg)),
        ("config_map_condition.nut", emit_map_conditions((src / "config_map_condition.nut").read_text(encoding="utf-8"), cfg)),
        ("config_lair_condition.nut", emit_lair_conditions((src / "config_lair_condition.nut").read_text(encoding="utf-8"), cfg)),
    ):
        # 其余 .nut 原样复制
        for f in src.glob("*.nut"):
            if f.name != name and not (dst / f.name).exists():
                shutil.copy2(f, dst / f.name)
        p = dst / name
        p.write_text(text, encoding="utf-8", newline="\n")
        written.append(p)
    return written
