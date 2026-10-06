"""M1 验证脚本：对真实 mod zip 跑静态分析器，人工核对输出（只读，不修改游戏目录）。

用法：python tools/scan_check.py --game <游戏目录> [--collection <合集目录>]
      python tools/scan_check.py --data <游戏data目录> [--collection <合集目录>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.modinfo import CATEGORY_LABELS, analyze_zip, requirement_target

COLLECTION = (Path(__file__).resolve().parents[2] / "其他mod"
              / "1.5.2.3游戏版本-原版汉化+MOD精选总集-2026-7月版" / "狐狸汉化精选MOD合集" / "基础功能MOD")


def show(path: Path) -> None:
    info = analyze_zip(path)
    print("=" * 100)
    print(f"文件: {path.name}  ({info.size//1024}KB, {info.entry_count} 条目)")
    if info.analysis_errors:
        print(f"  ⚠ 分析错误: {info.analysis_errors}")
    print(f"  API 代际: {info.api}   主ID: {info.primary_id}")
    for r in info.registrations:
        vok = "✓" if r.numeric_version_ok else "✗ 版本格式非法(legacy需纯数字)"
        print(f"  注册: {r.mod_id}  v={r.version}  name={r.name!r}  [{r.api}] {vok}")
    if info.requirements:
        print(f"  依赖: {[requirement_target(r) for r in info.requirements]}")
    if info.declared_conflicts:
        print(f"  声明冲突: {info.declared_conflicts}")
    if info.queue_deps:
        print(f"  queue 依赖: {info.queue_deps}")
    cats = {CATEGORY_LABELS.get(c, c): len(v) for c, v in sorted(info.categories.items())}
    print(f"  遮蔽分类: {cats}")
    if info.preload_scripts:
        print(f"  入口脚本: {[p.split('/')[-1] for p in info.preload_scripts[:6]]}{' …' if len(info.preload_scripts) > 6 else ''}")
    if info.preload_manifests:
        print(f"  ⚠ preload 清单: {info.preload_manifests}")
    if info.nested_zips:
        print(f"  ⚠ 内嵌 zip: {info.nested_zips}")
    if info.cnut_count:
        print(f"  cnut 编译条目: {info.cnut_count}")
    if info.seed_sensitive_paths:
        print(f"  ⚠ 影响种子/地图生成: {info.seed_sensitive_paths}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="对游戏 data 目录及合集中的 MOD ZIP 运行静态分析（只读）。")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--game", type=Path, help="游戏根目录（包含 data 与 win32）")
    target.add_argument("--data", type=Path, help="游戏 data 目录")
    parser.add_argument("--collection", type=Path, default=COLLECTION,
                        help="代表包所在的合集目录（默认：仓库内本地合集，不存在时跳过）")
    args = parser.parse_args(argv)
    if args.game is None and args.data is None:
        parser.error("必须用 --game <游戏目录> 或 --data <游戏data目录> 指定要扫描的游戏")
    args.data = args.data if args.data is not None else args.game / "data"
    if not args.data.is_dir():
        parser.error(f"游戏 data 目录不存在：{args.data}")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    print("\n########## 游戏已装 mod（本机 data 目录）##########\n")
    for z in sorted(args.data.glob("*.zip")):
        show(z)

    print("\n########## 合集框架与代表包 ##########\n")
    if not args.collection.is_dir():
        print(f"合集目录不存在，跳过：{args.collection}")
        return
    keys = ["modern_hooks", "mod_msu", "EIF", "eimo", "军团外套", "骨板", "犬舍", "沙匪"]
    for z in sorted(args.collection.glob("*.zip")):
        if any(k.lower() in z.name.lower() for k in keys):
            show(z)


if __name__ == "__main__":
    main()
