"""mod zip 静态分析器：对任意第三方 mod 生效，不依赖预置元数据。

分析维度：
- 入口脚本与注册信息（mod id / 版本 / 名称 / API 代际：legacy mod_hooks v21.1 vs Modern Hooks）
- 依赖（require）与声明冲突（conflictWith）
- 遮蔽路径分类（影响世界地图/角色/物品/纯资源）——用于"影响种子/地图生成"检测
- preload 清单、内嵌 zip（双层打包）、.cnut 编译脚本标记
- legacy 版本格式预检（mod_hooks v21.1 拒绝非纯数字版本）
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# 单个 .nut 最大扫描字节数 / 单 zip 总扫描上限（防止大型 mod 拖慢分析）
MAX_SCAN_BYTES_PER_FILE = 512 * 1024
MAX_SCAN_BYTES_TOTAL = 8 * 1024 * 1024

# ---------------- 正则：mod 注册与依赖 ----------------
# 参数可为：字符串字面量（双/单引号，允许内嵌另一种引号）、符号引用（::X.ID / ID）、数字字面量
_ARG = r"(\"(?:[^\"]*)\"|'(?:[^']*)'|::?[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*|-?\d[\d.]*)"
# legacy: mods_registerMod("mod_x", 1.2, "Name") 或 mods_registerMod(::X.ID, ::X.Version, ::X.Name)
RE_LEGACY_REG = re.compile(
    r"\bmods_registerMod\s*\(\s*" + _ARG + r"\s*,\s*" + _ARG + r"\s*(?:,\s*" + _ARG + r"\s*)?[,)]"
)
# modern: ::Hooks.register("mod_x", "1.2.3", "Name")，同样允许符号引用
RE_MODERN_REG = re.compile(
    r"\bHooks\.register\s*\(\s*" + _ARG + r"\s*,\s*" + _ARG + r"\s*(?:,\s*" + _ARG + r"\s*)?[,)]"
)
RE_SYMBOL_ONLY = re.compile(r"^::?[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
RE_NUMBER_ONLY = re.compile(r"^-?\d[\d.]*$")
# 字符串赋值（符号表来源）：ID = "x" / ::EIMO.Name <- "End's …"（允许内嵌另一种引号）
RE_STRING_ASSIGN = re.compile(
    r"(?:::)?([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*(?:<-|=)\s*(?:\"(?P<v_d>[^\"]*)\"|'(?P<v_s>[^']*)')"
)


def _assign_value(m: re.Match) -> str:
    return m.group("v_d") if m.group("v_d") is not None else m.group("v_s")
RE_REQUIRE = re.compile(r"\.require\(\s*[\"']([^\"']+)[\"']")
RE_CONFLICT = re.compile(r"\.conflictWith\(\s*[\"']([^\"']+)[\"']")
# legacy 队列依赖串：mods_queue(<id|null|符号>, "mod_a(>=1.0), >mod_b, !mod_c", fn)
RE_QUEUE_LEGACY = re.compile(
    r"\bmods_queue\s*\(\s*(?:[\"'][^\"']*[\"']|null|::?[\w.]+)\s*,\s*[\"']([^\"']+)[\"']"
)
# modern 队列：mod.queue(">mod_msu", fn)
RE_QUEUE_MODERN = re.compile(r"\.queue\(\s*[\"']([^\"']+)[\"']")
# 队列依赖 token：[>!]?id(版本比较)
RE_QUEUE_TOKEN = re.compile(r"^([>!]?)([A-Za-z_][\w.]*)\s*(\([^)]*\))?$")

# API 代际标记
RE_MODERN_MARKERS = re.compile(r"::Hooks\.|\.require\(|\.conflictWith\(|\.asVersionString\(|::MSU\.")
RE_LEGACY_MARKERS = re.compile(
    r"\bmods_registerMod\b|\bmods_queue\b|\bmods_hookClass\b|\bmods_hookExactClass\b|\bmods_override\b|\bmods_addField\b|\bmods_hookNewObject"
)

# 版本格式：mod_hooks v21.1 要求非负纯数字（"1.1.3" 会被拒绝）
RE_NUMERIC_VERSION = re.compile(r"^\d+(\.\d+)?$")

# ---------------- 遮蔽路径 → 影响分类 ----------------
SHADOW_RULES: list[tuple[str, str]] = [
    # (分类, 路径前缀或全路径) —— 顺序即优先级
    ("hooks", "scripts/!mods_preload/"),
    ("world_map", "scripts/config/world"),
    ("world_map", "scripts/config/settlements"),
    ("world_map", "scripts/config/tactical_constants"),
    ("world_map", "scripts/entity/world/"),
    ("world_map", "scripts/scenarios/"),
    ("world_map", "scripts/factions/"),
    ("brothers", "scripts/entity/tactical/humans/"),
    ("brothers", "scripts/entity/tactical/player"),
    ("brothers", "scripts/skills/traits/"),
    ("brothers", "scripts/skills/backgrounds/"),
    ("items", "scripts/items/"),
    ("skills", "scripts/skills/"),
    ("scripts_other", "scripts/"),
    ("fonts", "gfx/fonts/"),
    ("gfx", "gfx/"),
    ("gfx", "brushes/"),
    ("ui", "ui/"),
    ("sounds", "sounds/"),
    ("sounds", "music/"),
    ("preload_manifest", "preload/"),
]

# 这些分类意味着会干扰刷种子的 RNG 对齐（种子生成器要求移除）
SEED_SENSITIVE_CATEGORIES = {"world_map", "brothers", "items"}

CATEGORY_LABELS = {
    "hooks": "钩子入口",
    "world_map": "世界地图/场景生成",
    "brothers": "角色生成/特性",
    "items": "物品装备",
    "skills": "技能",
    "scripts_other": "其他脚本",
    "fonts": "字体",
    "gfx": "图形资源",
    "ui": "界面",
    "sounds": "音频",
    "preload_manifest": "预载清单",
}


@dataclass
class Registration:
    mod_id: str
    version: str
    name: str | None
    api: str  # 'legacy' | 'modern'

    @property
    def numeric_version_ok(self) -> bool:
        """legacy 注册的版本必须是非负数字，否则 mod_hooks v21.1 加载即拒。"""
        if self.api != "legacy":
            return True
        return bool(RE_NUMERIC_VERSION.match(self.version.strip()))


@dataclass
class ModInfo:
    path: Path
    file_name: str
    size: int = 0
    entry_count: int = 0
    entries: list[str] = field(default_factory=list)
    preload_scripts: list[str] = field(default_factory=list)
    registrations: list[Registration] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    declared_conflicts: list[str] = field(default_factory=list)
    queue_deps: list[str] = field(default_factory=list)
    categories: dict[str, list[str]] = field(default_factory=dict)
    preload_manifests: list[str] = field(default_factory=list)
    nested_zips: list[str] = field(default_factory=list)
    cnut_count: int = 0
    nut_count: int = 0
    api: str = "unknown"  # legacy | modern | mixed | resource | unknown
    analysis_errors: list[str] = field(default_factory=list)

    @property
    def primary_id(self) -> str:
        """用于展示/关联的 mod 标识：优先注册 id，否则按文件名推断。"""
        if self.registrations:
            return self.registrations[0].mod_id
        stem = self.file_name
        for suffix in (".zip", ".rar", ".disabled"):
            if stem.lower().endswith(suffix):
                stem = stem[: -len(suffix)]
        return stem

    @property
    def seed_sensitive_paths(self) -> list[str]:
        """会干扰刷种子 RNG 对齐的具体遮蔽路径（样例）。"""
        out: list[str] = []
        for cat in SEED_SENSITIVE_CATEGORIES:
            out.extend(self.categories.get(cat, [])[:3])
        return out

    @property
    def is_resource_only(self) -> bool:
        return bool(self.categories) and set(self.categories) <= {"gfx", "sounds", "fonts", "ui", "preload_manifest"}


def classify_path(entry: str) -> str | None:
    norm = entry.replace("\\", "/")
    for cat, prefix in SHADOW_RULES:
        if norm.startswith(prefix):
            return cat
    return None


def analyze_zip(path: Path | str) -> ModInfo:
    path = Path(path)
    info = ModInfo(path=path, file_name=path.name, size=path.stat().st_size if path.exists() else 0)
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        info.analysis_errors.append(f"无法读取 zip：{e}")
        return info

    with zf:
        # 第一阶段：收集条目分类 + 全部明文 .nut 文本（总量封顶）+ 符号表
        scanned = 0
        modern_hit = legacy_hit = False
        symbols: dict[str, str] = {}
        by_suffix: dict[str, set[str]] = {}
        texts: list[str] = []
        for entry in zf.namelist():
            norm = entry.replace("\\", "/")
            if norm.endswith("/"):
                continue
            info.entries.append(norm)
            info.entry_count += 1

            cat = classify_path(norm)
            if cat:
                info.categories.setdefault(cat, []).append(norm)

            if norm.startswith("scripts/!mods_preload/") and (norm.endswith(".nut") or norm.endswith(".cnut")):
                info.preload_scripts.append(norm)
            if norm.startswith("preload/") and norm.endswith(".txt"):
                info.preload_manifests.append(norm)
            if norm.lower().endswith(".zip"):
                info.nested_zips.append(norm)
            if norm.endswith(".cnut"):
                info.cnut_count += 1
            elif norm.endswith(".nut"):
                info.nut_count += 1

            if norm.endswith(".nut") and scanned < MAX_SCAN_BYTES_TOTAL:
                try:
                    if zf.getinfo(entry).file_size > MAX_SCAN_BYTES_PER_FILE:
                        continue
                    text = zf.read(entry).decode("utf-8", errors="replace")
                except (OSError, zipfile.BadZipFile):
                    continue
                scanned += len(text)
                texts.append(text)
                for m in RE_STRING_ASSIGN.finditer(text):
                    key, val = m.group(1), _assign_value(m)
                    symbols[key] = val
                    if "." in key:
                        by_suffix.setdefault(key[key.rindex("."):], set()).add(val)
                if RE_MODERN_MARKERS.search(text):
                    modern_hit = True
                if RE_LEGACY_MARKERS.search(text):
                    legacy_hit = True

        # 第二阶段：解析注册/依赖（符号引用跨文件解析）
        for text in texts:
            _extract_markers(text, info, symbols, by_suffix)

    if modern_hit and legacy_hit:
        info.api = "mixed"
    elif modern_hit:
        info.api = "modern"
    elif legacy_hit:
        info.api = "legacy"
    elif info.registrations:
        info.api = info.registrations[0].api
    elif info.entry_count and info.is_resource_only:
        info.api = "resource"
    elif info.entry_count and info.preload_scripts == [] and not info.nut_count:
        info.api = "resource" if info.cnut_count == 0 else "unknown"
    return info


def _resolve(arg: str, symbols: dict[str, str], by_suffix: dict[str, set[str]]) -> str:
    """参数解析：引号字面量去引号；数字直接用；符号按 全名→裸属性名→唯一后缀 链查找。"""
    arg = arg.strip()
    if not arg:
        return ""
    if len(arg) >= 2 and arg[0] in "\"'" and arg[-1] == arg[0]:
        return arg[1:-1]
    if RE_NUMBER_ONLY.match(arg):
        return arg
    if RE_SYMBOL_ONLY.match(arg):
        sym = arg.lstrip(":")
        if sym in symbols:
            return symbols[sym]
        # ::X.ID → 裸属性名 ID（表内 ID = "x" 定义不带表名）
        bare = sym.split(".")[-1]
        if bare in symbols:
            return symbols[bare]
        # 唯一后缀匹配：任意 *.ID 定义值唯一时采用
        suffix = "." + bare
        vals = by_suffix.get(suffix)
        if vals and len(vals) == 1:
            return next(iter(vals))
    return ""


def _parse_queue_string(s: str, info: ModInfo) -> None:
    """解析 legacy 队列依赖串："mod_a(>=1.0), >mod_b, !mod_c"。

    无前缀=依赖、'>'=之后加载、'!'=互斥。
    """
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        m = RE_QUEUE_TOKEN.match(tok)
        if not m:
            continue
        flag, ident, cmp_raw = m.groups()
        if flag == ">":
            if ident not in info.queue_deps:
                info.queue_deps.append(ident)
        elif flag == "!":
            if ident not in info.declared_conflicts:
                info.declared_conflicts.append(ident)
        else:
            req = ident + (cmp_raw or "")
            if req not in info.requirements:
                info.requirements.append(req)


def _extract_markers(text: str, info: ModInfo, symbols: dict[str, str], by_suffix: dict[str, set[str]]) -> None:
    for m in RE_LEGACY_REG.finditer(text):
        mod_id = _resolve(m.group(1) or "", symbols, by_suffix)
        version = _resolve(m.group(2) or "", symbols, by_suffix)
        name = _resolve(m.group(3) or "", symbols, by_suffix) or None
        if not mod_id:
            continue
        reg = Registration(mod_id=mod_id, version=version, name=name, api="legacy")
        if not any(r.mod_id == reg.mod_id for r in info.registrations):
            info.registrations.append(reg)
    for m in RE_MODERN_REG.finditer(text):
        mod_id = _resolve(m.group(1) or "", symbols, by_suffix)
        version = _resolve(m.group(2) or "", symbols, by_suffix)
        name = _resolve(m.group(3) or "", symbols, by_suffix) or None
        if not mod_id:
            continue
        reg = Registration(mod_id=mod_id, version=version, name=name, api="modern")
        if not any(r.mod_id == reg.mod_id for r in info.registrations):
            info.registrations.append(reg)
    for m in RE_REQUIRE.finditer(text):
        if m.group(1) not in info.requirements:
            info.requirements.append(m.group(1))
    for m in RE_CONFLICT.finditer(text):
        if m.group(1) not in info.declared_conflicts:
            info.declared_conflicts.append(m.group(1))
    for m in RE_QUEUE_LEGACY.finditer(text):
        _parse_queue_string(m.group(1), info)
    for m in RE_QUEUE_MODERN.finditer(text):
        tok = m.group(1).strip()
        # 跳过函数体首参误匹配（如 queue(function() …)）已由正则排除；">x" 形式拆前缀
        dep = tok.lstrip(">").strip()
        if dep and dep not in info.queue_deps:
            info.queue_deps.append(dep)


def requirement_target(req: str) -> str:
    """'mod_msu >= 1.2.6' / 'mod_msu(>=1.0.0)' → 'mod_msu'（用于依赖缺失比对）。"""
    return re.split(r"\s*[<>=~^(\s]+", req, maxsplit=1)[0].strip()
