"""生成 data/mod_index.json：扫描合集自动分析 + 预置人工标注（分类/中文名/互斥标签）。

用法：python tools/gen_index.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.modinfo import analyze_zip, requirement_target

COLLECTION = (Path(__file__).resolve().parents[2] / "其他mod"
              / "1.5.2.3游戏版本-原版汉化+MOD精选总集-2026-7月版" / "狐狸汉化精选MOD合集")
OUT = Path(__file__).resolve().parents[1] / "data" / "mod_index.json"

# 人工标注（探索报告结论）：文件名关键片段 → 元数据
CURATED: list[tuple[str, dict]] = [
    ("mod_modern_hooks", {"name_cn": "Modern Hooks 框架", "category": "框架",
                          "note": "新 API 根框架，把原版/DLC 注册为伪 mod；多数新 mod 的依赖", "tags": ["必需"]}),
    ("mod_msu-", {"name_cn": "MSU 1.9.0（汉化版）", "category": "框架",
                  "note": "模组开发标准与工具库，依赖 Modern Hooks；很多功能 mod 的前置", "tags": ["MSU依赖"]}),
    ("data狐狸汉化", {"name_cn": "狐狸汉化（内嵌旧版 hooks v21.1）", "category": "汉化",
                      "note": "全量脚本翻译+中文字体+内嵌 mod_hooks 21.1；需英文原版基座", "tags": ["基座"]}),
    ("zbigmap013", {"name_cn": "战利品管理 EIMO 9.06（MSU 汉化版）", "category": "基础功能",
                    "note": "智能战利品/修理/回购；内嵌 zbigmap007 快速切换道具，安装时自动解出", "tags": ["MSU依赖", "内嵌zip"]}),
    ("zbigmap043", {"name_cn": "地图/战斗加速 Swifter（MSU 汉化版）", "category": "基础功能",
                    "note": "F1-F4 战斗加速、地图加速；互斥 06 战斗加速/quickier 系列", "tags": ["MSU依赖", "互斥"]}),
    ("zbigmap060", {"name_cn": "自动战斗（MSU）", "category": "基础功能", "note": "MSU 系自动战斗", "tags": ["MSU依赖"]}),
    ("zbigmap033", {"name_cn": "自定义武将底座 MSU2.4", "category": "基础功能", "note": "", "tags": ["MSU依赖"]}),
    ("zbigmap046", {"name_cn": "战前准备（MSU 汉化版）", "category": "基础功能", "note": "战前整备界面", "tags": ["MSU依赖"]}),
    ("zbigmap012", {"name_cn": "发现传奇地点 Ctrl+U", "category": "基础功能", "note": "揭秘传奇地点位置"}),
    ("zbigmap050", {"name_cn": "可移除护甲配件（U）", "category": "基础功能", "note": ""}),
    ("轻度显星", {"name_cn": "轻度显星（仅成长星）", "category": "基础功能",
                  "note": "显星类互斥：与显星显属性带评价二选一", "tags": ["显星互斥"]}),
    ("显星显属性带评价", {"name_cn": "显星显属性带评价", "category": "作弊",
                          "note": "会写入存档；显星类互斥（与轻度显星二选一）", "tags": ["显星互斥", "影响存档"]}),
    ("EIF.zip", {"name_cn": "精灵种族 EIF", "category": "基础功能",
                 "note": "新雇佣兵 20% 概率为精灵（+4 先攻，女声语音）；影响角色生成", "tags": ["影响种子"]}),
    ("军团外套", {"name_cn": "军团外套 Company Tabards", "category": "基础功能",
                 "note": "含 preload 预载清单（多 mod 共存需合并）；注册版本号 1.5.2024 会被旧 hooks 拒绝", "tags": ["preload清单"]}),
    ("营地显示人物11级上限", {"name_cn": "营地显示人物11级上限头像", "category": "基础功能",
                              "note": "纯资源；含 preload 预载清单", "tags": ["preload清单"]}),
    ("骨板显示器", {"name_cn": "骨板显示器", "category": "基础功能", "note": "含 preload 预载清单", "tags": ["preload清单"]}),
    ("mod_沙匪起源", {"name_cn": "沙匪起源 Desert Bandits", "category": "基础功能", "note": "新开局起源"}),
    ("刺客之王起源", {"name_cn": "刺客之王起源 Hassassin", "category": "基础功能", "note": "起源+专属武器装备"}),
    ("m0d_03_", {"name_cn": "铠甲损坏标识", "category": "基础功能", "note": ""}),
    ("m0d_22_", {"name_cn": "详细阵亡人员情报", "category": "基础功能", "note": "Better Obituary"}),
    ("m0d_24_", {"name_cn": "自由布阵", "category": "基础功能", "note": "战前自由布阵"}),
    ("CompareBros", {"name_cn": "兵员对比 CompareBros", "category": "基础功能", "note": ""}),
    ("战场敌人战斗属性", {"name_cn": "战场敌人属性提示", "category": "基础功能", "note": ""}),
    ("显示视野范围", {"name_cn": "显示视野范围", "category": "基础功能", "note": ""}),
    ("宝藏地图", {"name_cn": "宝藏地图（红装位置提示）", "category": "基础功能", "note": ""}),
    ("职业属性能力范围显示", {"name_cn": "职业属性能力范围显示", "category": "基础功能",
                              "note": "新 API，需 Modern Hooks", "tags": ["需ModernHooks"]}),
    ("显示红装属性范围", {"name_cn": "红装属性区间显示", "category": "基础功能", "note": ""}),
    ("显示营地红装", {"name_cn": "显示营地红装", "category": "基础功能", "note": ""}),
    ("显示城市交易价格比例", {"name_cn": "城市交易价格/状态提示", "category": "基础功能", "note": ""}),
    ("显示城市据点状态", {"name_cn": "显示据点状态", "category": "基础功能", "note": ""}),
    ("神殿治疗永久伤残", {"name_cn": "神殿治疗永久伤残", "category": "基础功能", "note": ""}),
    ("回购-原价买回物品", {"name_cn": "原价回购物品", "category": "基础功能", "note": ""}),
    ("商店出售红盾", {"name_cn": "商店出售红盾", "category": "基础功能", "note": ""}),
    ("重命名英文使用-1.5倍雇佣新人", {"name_cn": "1.5倍雇佣新人", "category": "基础功能", "note": ""}),
    ("犬舍可购买狼", {"name_cn": "犬舍可购买狼", "category": "基础功能", "note": "纯覆盖，无注册"}),
    ("1W制作不老泉", {"name_cn": "1W 制作不老泉", "category": "作弊", "note": "配方覆盖"}),
    ("5W出技能药水", {"name_cn": "5W 出技能药水", "category": "作弊", "note": "配方覆盖"}),
    ("轻松制作遗忘药水", {"name_cn": "轻松制作遗忘药水", "category": "作弊", "note": "配方覆盖"}),
    ("炼金配方可见", {"name_cn": "炼金配方全开", "category": "作弊", "note": ""}),
    ("自动暂停-合集版", {"name_cn": "自动暂停（可配置）", "category": "基础功能", "note": ""}),
    ("玩家控制宠物", {"name_cn": "玩家控制宠物", "category": "基础功能", "note": "攻击快捷键 1"}),
    ("猎头触发特效", {"name_cn": "猎头触发特效（VSE）", "category": "基础功能", "note": ""}),
    ("武器皮肤包", {"name_cn": "武器皮肤包", "category": "作弊", "note": "美化向；会改变种子", "tags": ["改种子"]}),
    ("SHIFT+E-多功能修改器", {"name_cn": "BBForge 多功能修改器", "category": "作弊", "note": "游戏内兵员编辑器（SHIFT+E）"}),
    ("无限竞技场次数", {"name_cn": "无限竞技场次数", "category": "作弊", "note": "cnut 整文件覆盖"}),
    ("先知永远是旗手", {"name_cn": "先知永远是旗手", "category": "作弊", "note": ""}),
    ("角斗士13人", {"name_cn": "角斗士 13 人", "category": "作弊", "note": "名额+1"}),
    ("随从上限变为10个", {"name_cn": "随从上限 10", "category": "作弊", "note": ""}),
    ("25%商店红装", {"name_cn": "25% 商店红装（必出红装）", "category": "作弊", "note": ""}),
    ("按Y随时献祭", {"name_cn": "按 Y 随时献祭（达库尔专用）", "category": "作弊", "note": "rar 包，需解压安装"}),
    ("mod_（战术命中要素", {"name_cn": "战术命中要素显示", "category": "基础功能", "note": "cnut 编译"}),
]


def categorize(path: Path) -> str:
    for part in path.parts:
        if "高强度作弊" in part:
            return "作弊"
    return "基础功能"


def main() -> None:
    index: dict[str, dict] = {}
    zips: list[Path] = []
    for sub in COLLECTION.iterdir():
        if sub.is_dir():
            zips += list(sub.glob("*.zip")) + list(sub.glob("*.rar"))
        elif sub.suffix.lower() in (".zip", ".rar"):
            zips.append(sub)

    for f in sorted(zips, key=lambda p: p.name.lower()):
        entry: dict = {}
        if f.suffix.lower() == ".zip":
            info = analyze_zip(f)
            deps = sorted({requirement_target(r) for r in info.requirements} - {"vanilla"})
            entry = {
                "category": categorize(f),
                "mod_ids": [r.mod_id for r in info.registrations],
                "api": info.api,
                "deps": deps,
                "seed_sensitive": bool(info.seed_sensitive_paths),
                "size_kb": info.size // 1024,
            }
        for key, meta in CURATED:
            if key.lower() in f.name.lower():
                entry.update({k: v for k, v in meta.items() if k in ("name_cn", "note", "tags")})
                if "category" in meta:
                    entry["category"] = meta["category"]
                break
        index[f.name] = entry

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写入 {len(index)} 条 → {OUT}")


if __name__ == "__main__":
    main()
