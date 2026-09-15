"""M5 验收：配置生成器 + 日志解析器 + 编排器真机往返（不启动游戏进程）。

编排测试只做 prepare → 校验注入 → stop_and_restore → 比对初始状态，不 launch。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import game as game_mod
from core.gamelog import LogRow
from core.modmanager import ModManager
from core.seedgen.config_emitter import (
    BroCondition, CommonConfig, OriginConfig, SeedGenConfig, emit_common,
)
from core.seedgen.log_watcher import SeedLogParser
from core.seedgen.orchestrator import SeedGenOrchestrator

PAYLOAD = Path(__file__).resolve().parents[1] / "seedgen" / "payload"


def balanced(text: str) -> bool:
    """剥离注释与字符串字面量后检查括号配平（Squirrel 方言：# 与 // 都是行注释）。"""
    import re as _re
    cleaned = []
    for line in text.splitlines():
        line = _re.sub(r'"(?:[^"\\]|\\.)*"', '""', line)
        line = _re.sub(r"(#|//).*$", "", line)
        cleaned.append(line)
    s = "\n".join(cleaned)
    return s.count("[") == s.count("]") and s.count("{") == s.count("}") and s.count("(") == s.count(")")


def test_emitters() -> None:
    cfg = SeedGenConfig(
        common=CommonConfig.preset("bro_map"),
        origins={
            "scenario.militia": OriginConfig(
                conditions=[
                    BroCondition("TeamScore", [0.78], comment="队伍平均分"),
                    BroCondition("RoleScore", [0.83, 1, "RoleMelee"]),
                    BroCondition("RoleTraitScore", [0.80, 1, "RoleGuard", "trait.iron_lungs"]),
                ],
                max_roles={"RoleMelee": 3, "RoleGuard": 2},
            )
        },
    )
    common_text = emit_common(cfg.common)
    assert "GenerateBrotherMode = true" in common_text and "OnlyPrintMatchingSettlement = true" in common_text
    print("✓ config_common 生成（模式 bro_map）")

    template = (PAYLOAD / "seed_generator" / "config_role_condition.nut").read_text(encoding="utf-8")
    from core.seedgen.config_emitter import emit_role_conditions
    out = emit_role_conditions(template, cfg)
    assert "[BroOutput.TeamScore, 0.78],  # 队伍平均分" in out
    assert "[BroOutput.RoleScore, 0.83, 1, Role.RoleMelee]," in out
    assert '[BroOutput.RoleTraitScore, 0.8, 1, Role.RoleGuard, "trait.iron_lungs"],' in out
    assert 'MaxRoleArray["scenario.militia"][Role.RoleMelee] = 3;' in out
    # 未自定义的起源保持模板原文
    assert 'BroOutputConditionArray["scenario.early_access"]' in out
    # 方括号配平（粗检 Squirrel 语法）
    assert balanced(out), "role 输出括号不平衡"
    print("✓ config_role_condition 起源定制（农民团 3 条件 + 名额），其余起源保持原文")

    map_tpl = (PAYLOAD / "seed_generator" / "config_map_condition.nut").read_text(encoding="utf-8")
    from core.seedgen.config_emitter import emit_map_conditions
    cfg2 = SeedGenConfig(map_conditions=[["SettlementNum", 24, "PortNum", 9], ["ProductsValue", 10000]])
    out2 = emit_map_conditions(map_tpl, cfg2)
    assert "[MapOutput.SettlementNum, 24, MapOutput.PortNum, 9]," in out2
    assert balanced(out2), "map 输出括号不平衡"
    print("✓ config_map_condition 自定义")

    lair_tpl = (PAYLOAD / "seed_generator" / "config_lair_condition.nut").read_text(encoding="utf-8")
    from core.seedgen.config_emitter import emit_lair_conditions
    cfg3 = SeedGenConfig(lair_conditions=[["NamedNumber", 45], ["NamedAttrValue", "one_hand", 1, "DirectDamageAdd", 70]])
    out3 = emit_lair_conditions(lair_tpl, cfg3)
    assert "[LairOutput.NamedNumber, 45]," in out3
    assert "[LairOutput.NamedAttrValue, \"one_hand\", 1, NamedAttr.DirectDamageAdd, 70]," in out3
    print("✓ config_lair_condition 自定义")


def test_log_parser() -> None:
    rows = [
        LogRow("info", "10:00:01", "SQ", "LoopIdx: 5000(3) 0.81 0.74 近战0.76 远程0.72"),
        LogRow("info", "10:00:01", "SQ", "Seed: ABKDEFGHIJ LoopIdx:5100 BroOutputType:1 MapOutputType:0"),
        LogRow("info", "10:00:01", "SQ", "TeamInfo: 0.82 [近战:2 远程:1]"),
        LogRow("info", "10:00:01", "SQ", "CharInfo: 0 近战:0.85 血量:68(102)2星 决心:40(52)1星"),
        LogRow("info", "10:00:01", "SQ", "Trait: 巨人 酒鬼"),
        LogRow("info", "10:00:01", "SQ", "LairInfo: 幽暗森林(兽人营地) 强度120 最近城市:XXX 距离:3-东"),
        LogRow("info", "10:00:01", "SQ", "    ItemInfo(OneHanded): weapon.named_sword (伤害:75%|穿甲:80%)    Stamina:-10"),
        LogRow("info", "10:00:01", "SQ", "CRLF"),
        LogRow("info", "10:00:02", "SQ", "Seed: ZXCASDFGHJ LoopIdx:5200 BroOutputType:0"),
        LogRow("info", "10:00:02", "SQ", "TeamInfo: 0.79 [盾卫:2]"),
        LogRow("info", "10:00:02", "SQ", "CRLF"),
    ]
    parser = SeedLogParser()
    results, progress = parser.feed(rows)
    assert len(results) == 2
    r1 = results[0]
    assert r1.seed == "ABKDEFGHIJ" and r1.loop_idx == 5100 and r1.bro_output_type == 1 and r1.map_output_type == 0
    assert r1.team_score == 0.82 and len(r1.brothers) == 1 and len(r1.named_items) == 1 and len(r1.lairs) == 1
    assert progress and progress[0].loop_idx == 5000 and progress[0].hits == 3
    assert len(parser.results) == 2
    print("✓ 日志解析：种子块组装 / 队伍分 / 兄弟 / 红装 / 营地 / 进度")


def test_orchestrator_roundtrip() -> None:
    g = game_mod.locate_game()
    assert g
    mm = ModManager(g.root)
    initial = {f.name for f in g.data_dir.iterdir()}

    orch = SeedGenOrchestrator(g, PAYLOAD)
    warnings = orch.prepare(SeedGenConfig(common=CommonConfig.preset("bro_lair")))
    print(f"✓ prepare 提示: {warnings}")
    assert not (g.data_dir / "data狐狸汉化+hooks 20260624.zip").exists(), "mod 未被移出"
    assert (g.data_dir / "mod_hooks.zip").exists()
    assert (g.data_dir / "scripts" / "!mods_preload" / "mod_seed_generator.nut").exists()
    assert (g.data_dir / "seed_generator" / "config_common.nut").exists()
    cfg_text = (g.data_dir / "seed_generator" / "config_common.nut").read_text(encoding="utf-8")
    assert "OnlyPrintMatchingLair = true" in cfg_text, "预设模式未生效"
    assert balanced(cfg_text), "写入的 config_common 括号不平衡"
    injected_count = len(orch._injected)
    print(f"✓ 注入 {injected_count} 个文件，配置生效（模式 bro_lair）")

    restored = orch.stop_and_restore()
    after = {f.name for f in g.data_dir.iterdir()}
    assert after == initial, f"恢复不一致: {after ^ initial}"
    assert restored == 6
    print(f"✓ stop_and_restore：恢复 {restored} 个 mod，data 目录与初始完全一致")


if __name__ == "__main__":
    test_emitters()
    test_log_parser()
    test_orchestrator_roundtrip()
    print("\nM5 核心全部通过 ✓（端到端游戏内测试待 UI 联调）")
