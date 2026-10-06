"""M3 验收：ModManager 真机往返测试。

流程：记录初始状态 → 安装(含内嵌zip解出) → 禁用/启用 → 卸载 → 全量快照/恢复 → 比对一致性。
结束时游戏 data 目录必须与初始状态完全一致（本测试不留任何痕迹，除审计日志外）。

会修改真实游戏目录，必须显式指定目录并确认：
    python tools/manager_check.py --game <游戏目录> --i-understand-this-modifies-the-game
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import game
from core.modmanager import ModManager

COLLECTION = (Path(__file__).resolve().parents[2] / "其他mod"
              / "1.5.2.3游戏版本-原版汉化+MOD精选总集-2026-7月版" / "狐狸汉化精选MOD合集" / "基础功能MOD")
CONFIRM_FLAG = "--i-understand-this-modifies-the-game"


def sig(mm: ModManager) -> set[str]:
    return {f.name for f in mm.data.iterdir() if f.is_file() and not f.name.startswith("data_")} | {
        f"disabled/{f.name}" for f in (mm.disabled_dir.glob("*") if mm.disabled_dir.exists() else [])
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ModManager 真机往返测试：会在指定游戏的 data 目录安装、禁用、卸载并恢复 MOD。")
    parser.add_argument("--game", type=Path, required=True, help="游戏根目录（包含 data 与 win32）")
    parser.add_argument(CONFIRM_FLAG, dest="confirmed", action="store_true",
                        help="确认允许本工具修改该游戏目录（运行前请关闭游戏并备份 data）")
    parser.add_argument("--collection", type=Path, default=COLLECTION,
                        help="提供测试 MOD 的合集目录（默认：仓库内本地合集）")
    parser.add_argument("--expected-files", type=int, default=6,
                        help="data 目录初始的非 data_*.dat 文件数，也是快照应移出的 MOD 数（默认 6）")
    args = parser.parse_args(argv)
    if not args.confirmed:
        parser.error(f"本工具会修改真实游戏目录；确认已关闭游戏并备份后，追加 {CONFIRM_FLAG}")
    if not (args.collection / "商店出售红盾.zip").is_file():
        parser.error(f"合集目录缺少测试 MOD 商店出售红盾.zip：{args.collection}")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    g = game.locate_game(str(args.game))
    assert g, f"不是有效的游戏目录（需包含 data 与 win32/BattleBrothers.exe）：{args.game}"
    collection = args.collection
    expected = args.expected_files
    mm = ModManager(g.root)
    initial = sig(mm)
    print(f"初始 data 文件: {sorted(initial)}\n")
    assert len(initial) == expected, f"预期本机初始为 {expected} 个文件（可用 --expected-files 调整）"

    # 1. 安装 商店出售红盾.zip（最小 mod，540B）
    written = mm.install(collection / "商店出售红盾.zip")
    assert (mm.data / "商店出售红盾.zip").exists()
    print(f"✓ 安装: {[w.name for w in written]}")

    # 2. 安装 EIMO（内嵌 zip 自动解出）
    eimo = collection / "zbigmap013-战利品管理9.06-MSU汉化版1.4-eimo-239-9-0-6-1656322331.zip"
    if eimo.exists():
        written = mm.install(eimo)
        names = [w.name for w in written]
        assert any("zbigmap007" in n for n in names), "内嵌 zip 未解出"
        print(f"✓ 安装 EIMO + 内嵌解出: {names}")

    # 3. 禁用 → 启用
    mm.disable("商店出售红盾.zip")
    assert not (mm.data / "商店出售红盾.zip").exists() and (mm.disabled_dir / "商店出售红盾.zip").exists()
    mm.enable("商店出售红盾.zip")
    assert (mm.data / "商店出售红盾.zip").exists()
    print("✓ 禁用/启用 往返一致")

    # 4. 卸载测试 mod（移入禁用区后永久删除）
    mm.uninstall("商店出售红盾.zip")
    if eimo.exists():
        mm.uninstall(eimo.name)
        inner = mm.data / "zbigmap007-快速切换道具汉化(兼容控制宠物MOD).zip"
        if inner.exists():
            mm.uninstall(inner.name)
    for name in ("商店出售红盾.zip", eimo.name if eimo.exists() else "", "zbigmap007-快速切换道具汉化(兼容控制宠物MOD).zip"):
        if name and (mm.disabled_dir / name).exists():
            mm.delete_permanently(name, from_disabled=True)
    after_uninstall = sig(mm)
    assert after_uninstall == initial, f"卸载后状态不一致: {after_uninstall ^ initial}"
    print("✓ 卸载后 data 与初始一致")

    # 5. 全量快照 → 恢复
    snap = mm.stash_all_mods()
    assert len(snap.moved) == expected and not list(mm.data.glob("*.zip"))
    print(f"✓ 快照: 移出 {len(snap.moved)} 个 mod")
    restored = mm.restore_snapshot(snap)
    assert restored == expected
    final = sig(mm)
    assert final == initial, f"恢复后状态不一致: {final ^ initial}"
    print("✓ 恢复后 data 与初始完全一致")
    assert not mm.has_orphan_stash()
    print("\n全部通过 ✓（审计日志见 BBMOD_operations.log）")


if __name__ == "__main__":
    main()
