"""自研汉化管线：读取参考语料（狐狸汉化 zip 明文 .nut）建立字符串库，
应用我们的覆盖表后重新打包为自有品牌的汉化包。

- 语料判据：字符串值含 CJK 字符 → 已翻译的用户可见文本（m.Name/m.Description/…）
- 覆盖表：{文件路径: {字段名: 新值}}，构建时对源码做定向字面量替换
- 品牌标记：成品 zip 根部带 BBMOD_L10N.json（同时供软件识别"我们的汉化包"）
- 字体：可选用自选中文字体替换 gfx/fonts/main.ttf（fonts.css 已把全部字族指向它）
"""
from __future__ import annotations

import datetime
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

BRAND_META = "BBMOD_L10N.json"
FONT_ENTRY = "gfx/fonts/main.ttf"
OUTPUT_PREFIX = "BBMOD汉化"

# 任意 KEY <-/= "含CJK的字面量"（KEY 允许 this.m.X / m.X / 裸标识符）
RE_FIELD = re.compile(r'((?:this\.)?(?:m\.)?[A-Za-z_][A-Za-z0-9_]*)\s*(?:<-|=)\s*"((?:[^"\\]|\\.)*)"')
RE_CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


def has_cjk(s: str) -> bool:
    return bool(RE_CJK.search(s))


@dataclass
class StringEntry:
    file: str
    key: str  # 如 m.Name（统一去掉 this. 前缀）
    value: str

    @property
    def id(self) -> tuple[str, str]:
        return (self.file, self.key)


def extract_strings(zip_path: Path | str) -> list[StringEntry]:
    """从参考语料 zip 提取全部已翻译字符串条目（值含 CJK）。"""
    out: list[StringEntry] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.endswith(".nut"):
                continue
            try:
                if zf.getinfo(name).file_size > 1024 * 1024:
                    continue
                text = zf.read(name).decode("utf-8", errors="replace")
            except (OSError, zipfile.BadZipFile):
                continue
            for m in RE_FIELD.finditer(text):
                key = m.group(1)
                if key.startswith("this."):
                    key = key[len("this."):]
                value = m.group(2)
                if has_cjk(value):
                    out.append(StringEntry(file=name, key=key, value=value))
    return out


def _sq_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def apply_override(text: str, key: str, new_value: str) -> tuple[str, bool]:
    """把源码中 key 的字符串字面量替换为新值（保留原缩进与赋值形式）。

    同一 key 在一个文件中出现多次时全部替换（同名属性赋值语义相同）。
    """
    pattern = re.compile(
        r'((?:this\.)?(?:m\.)?' + re.escape(key) + r'\s*(?:<-|=)\s*")((?:[^"\\]|\\.)*)(")'
    )
    new_text, n = pattern.subn(lambda m: m.group(1) + _sq_escape(new_value) + m.group(3), text)
    return new_text, n > 0


def is_bbmod_l10n(zip_path: Path | str) -> bool:
    """是否为我们构建的汉化包（含品牌标记）。"""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return BRAND_META in zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def is_reference_l10n(zip_path: Path | str) -> bool:
    """是否为狐狸汉化类参考包（含中文字体 + 全量翻译脚本树）。"""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            return FONT_ENTRY in names and any(n.endswith("scripts/config/strings.nut") for n in names)
    except (zipfile.BadZipFile, OSError):
        return False


def build_localization(
    reference_zip: Path | str,
    overrides: dict[str, dict[str, str]],
    out_path: Path | str,
    font_path: Path | str | None = None,
    brand_note: str = "",
    source_note: str = "狐狸汉化 20260624",
) -> dict:
    """构建自有汉化包：参考语料 + 覆盖表（+ 可选自选字体）→ 重新打包。

    返回构建统计。overrides: {zip内文件路径: {字段名: 新值}}
    """
    reference_zip = Path(reference_zip)
    out_path = Path(out_path)
    applied = 0
    missing: list[str] = []
    with zipfile.ZipFile(reference_zip) as src, zipfile.ZipFile(
        out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
    ) as dst:
        file_overrides = overrides or {}
        for item in src.infolist():
            if item.is_dir():
                continue
            data = src.read(item.filename)
            if item.filename.endswith(".nut") and item.filename in file_overrides:
                text = data.decode("utf-8", errors="replace")
                for key, new_value in file_overrides[item.filename].items():
                    text, ok = apply_override(text, key, new_value)
                    if ok:
                        applied += 1
                    else:
                        missing.append(f"{item.filename}:{key}")
                data = text.encode("utf-8")
            elif font_path and item.filename == FONT_ENTRY:
                data = Path(font_path).read_bytes()
            # 复制压缩属性但重置时间戳，避免"假重打包"歧义
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(info, data)
        meta = {
            "brand": "BBMOD 汉化",
            "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "reference": source_note,
            "overrides_applied": applied,
            "font_replaced": bool(font_path),
            "note": brand_note,
        }
        dst.writestr(BRAND_META, json.dumps(meta, ensure_ascii=False, indent=2))
    return {"applied": applied, "missing": missing, "out": str(out_path), "entries": len(zipfile.ZipFile(out_path).namelist())}


def find_localization_zips(data_dir: Path) -> list[Path]:
    """data 目录中所有汉化类 zip（我们构建的 + 参考包）。"""
    out: list[Path] = []
    for f in sorted(data_dir.glob("*.zip")):
        if is_bbmod_l10n(f) or is_reference_l10n(f):
            out.append(f)
    return out
