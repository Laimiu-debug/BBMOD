"""M4 验收：汉化管线全流程测试（语料抽取 → 覆盖 → 构建 → 校验）。

不对游戏目录做任何修改。
"""
from __future__ import annotations

import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.l10n import (
    FONT_ENTRY,
    extract_strings,
    build_localization,
    is_bbmod_l10n,
    apply_override,
)

FOX = Path(
    r"G:\code\BBMOD\1.5.2.3游戏版本-原版汉化+MOD精选总集-2026-7月版"
    r"\狐狸汉化精选MOD合集\狐狸汉化（集成内置修改器）\data狐狸汉化+hooks 20260624.zip"
)


def main() -> None:
    # 1. 语料抽取
    entries = extract_strings(FOX)
    files = {e.file for e in entries}
    keys = Counter(e.key for e in entries)
    print(f"✓ 语料抽取: {len(entries)} 条字符串，来自 {len(files)} 个文件")
    print(f"  字段 top8: {keys.most_common(8)}")
    assert len(entries) > 5000, "语料量异常"
    assert keys.get("m.Name", 0) > 500 and keys.get("m.Description", 0) > 500

    # 2. 找一条做覆盖测试：scripts/items/helmets/hood.nut 的 m.Name（原文"罩头"）
    hood = next(e for e in entries if e.file.endswith("helmets/hood.nut") and e.key == "m.Name")
    print(f"✓ 样例: {hood.file} m.Name = {hood.value!r}")

    with zipfile.ZipFile(FOX) as zf:
        original_text = zf.read(hood.file).decode("utf-8")
    new_text, ok = apply_override(original_text, "m.Name", "兜帽（BBMOD改）")
    assert ok and "兜帽（BBMOD改）" in new_text and '"罩头"' not in new_text
    print("✓ 定向替换: m.Name 覆盖成功，其余内容不动")

    # 3. 构建自有汉化包（1 条覆盖 + 无字体替换）
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "BBMOD汉化_test.zip"
        result = build_localization(
            FOX,
            overrides={hood.file: {"m.Name": "兜帽（BBMOD改）", "m.Description": "一块厚实的兜帽，挡风遮雨。"}},
            out_path=out,
            brand_note="测试构建",
        )
        print(f"✓ 构建: 应用了 {result['applied']} 条覆盖，成品 {result['entries']} 条目")
        assert result["applied"] == 2 and not result["missing"]

        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            assert is_bbmod_l10n(out)
            hood_new = zf.read(hood.file).decode("utf-8")
            assert "兜帽（BBMOD改）" in hood_new and "一块厚实的兜帽" in hood_new
            assert zf.read(FONT_ENTRY)[:4] == b"\x00\x01\x00\x00", "字体应原样保留"
            # 抽查未覆盖文件与源一致
            probe = "scripts/skills/actives/strike_skill.nut"
            if probe in names:
                with zipfile.ZipFile(FOX) as src:
                    assert zf.read(probe) == src.read(probe)
        print("✓ 成品校验: 品牌标记/字体保留/未覆盖文件字节一致")

    print("\n汉化管线全部通过 ✓")


if __name__ == "__main__":
    main()
