"""诊断引擎：对已装 mod 集合做冲突/版本/影响面/运行时四类检查，输出结构化问题列表。

设计原则：所有规则基于 modinfo 静态分析即可运行（任意第三方 mod 生效）；
已知 mod 元数据表（M3）只是增强层。运行时日志（上次会话 log.html）作为静态分析的兜底。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .game import GameInfo, check_base_archive, installed_dlcs
from .gamelog import LogRow
from .modinfo import ModInfo, requirement_target

# 伪依赖 id（非真实 mod）
PSEUDO_IDS = {"vanilla", "mod_hooks_21", "game"}

# 框架提供者：这些 id 被依赖时视为"框架"
FRAMEWORK_IDS = {"mod_hooks", "mod_modern_hooks", "mod_msu"}

# 运行时注册成功行：mod_hooks: mod_quickly_swap_items (Quickly swap items) version 2 registered.
RE_RUNTIME_REGISTERED = re.compile(r"([\w.]+)\s+\(([^)]*)\)\s+version\s+([\w.]+)\s+registered")
# 脚本执行失败行：Failed to execute script file "scripts/!mods_preload/xxx.nut". Reason: …
RE_FAILED_SCRIPT = re.compile(r'Failed to execute script file\s*"([^"]+)"')

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Issue:
    severity: str  # error | warning | info
    source: str  # zip 文件名 或 '系统'
    title: str
    detail: str = ""
    fix: str | None = None  # 修复建议

    def sort_key(self) -> tuple:
        return (SEVERITY_ORDER.get(self.severity, 9), self.source)


@dataclass
class DiagnosisReport:
    issues: list[Issue] = field(default_factory=list)
    runtime_registered: list[str] = field(default_factory=list)
    runtime_errors: list[LogRow] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def sorted(self) -> list[Issue]:
        return sorted(self.issues, key=lambda i: i.sort_key())


def diagnose(
    game: GameInfo,
    installed: list[ModInfo],
    log_rows: list[LogRow] | None = None,
) -> DiagnosisReport:
    report = DiagnosisReport()

    _check_system(game, report)
    installed_ids = {r.mod_id for m in installed for r in m.registrations}
    for mod in installed:
        _check_mod(mod, installed_ids, report)

    _check_file_overlaps(installed, report)
    _check_preload_manifests(installed, report)

    if log_rows is not None:
        _check_runtime(log_rows, installed, report)
    return report


# ---------------- 系统级 ----------------

def _check_system(game: GameInfo, report: DiagnosisReport) -> None:
    if game.version and game.version != "1.5.2.3":
        report.issues.append(Issue(
            severity="error", source="系统",
            title=f"游戏版本 {game.version} 与合集目标版本 1.5.2.3 不符",
            detail="内置 MOD 合集与种子生成器均按 1.5.2.3 的脚本行为制作，版本不符时 RNG/汉化可能错位。",
            fix="Steam 校验文件或回退到 1.5.2.3",
        ))
    base = check_base_archive(game.data_dir)
    if base and base.read_error:
        report.issues.append(Issue(
            severity="error", source="系统", title="无法读取游戏基座档案",
            detail=base.warning or "", fix="检查游戏文件是否完整、是否可以读取",
        ))
    elif base and base.repacked:
        report.issues.append(Issue(
            severity="info", source="系统",
            title="游戏档案日期较新（不代表汉化影响种子）",
            detail=base.warning or "",
            fix=None,
        ))
    missing = [name for name, ok in installed_dlcs(game.data_dir).items() if not ok]
    if missing:
        report.issues.append(Issue(
            severity="warning", source="系统",
            title=f"缺少 DLC：{', '.join(missing)}",
            detail="种子生成器按全 DLC 的 RNG 行为校准，缺 DLC 时生成的种子在新战役中不可复现。",
            fix="Steam 安装对应 DLC",
        ))


# ---------------- 单 mod ----------------

def _check_mod(mod: ModInfo, installed_ids: set[str], report: DiagnosisReport) -> None:
    src = mod.file_name
    has_modern = "mod_modern_hooks" in installed_ids

    # 1. legacy 版本格式（mod_hooks v21.1 拒绝非纯数字版本）
    for reg in mod.registrations:
        if not reg.numeric_version_ok:
            report.issues.append(Issue(
                severity="error", source=src,
                title=f"版本号 “{reg.version}” 不合法：旧版 mod_hooks 要求纯数字",
                detail=f"mod {reg.mod_id} 以旧 API 注册，mod_hooks v21.1 会直接拒绝加载"
                       f"（游戏日志报 “not using a numeric version”）。",
                fix="将注册版本改为纯数字（如 1.1.3 → 1.13），或安装 Modern Hooks 后改用新 API",
            ))

    # 2. 现代 API 但无 Modern Hooks
    is_hooks_itself = any(r.mod_id == "mod_modern_hooks" for r in mod.registrations)
    if mod.api in ("modern", "mixed") and not has_modern and not is_hooks_itself:
        report.issues.append(Issue(
            severity="error", source=src,
            title="需要 Modern Hooks 框架，但未安装",
            detail="该 mod 使用 ::Hooks.register / .require 等新 API；"
                   "未装 mod_modern_hooks 时启动即报 “the index 'Hooks' does not exist”。",
            fix="安装 mod_modern_hooks（仓库-框架分类）",
        ))

    # 3. 依赖缺失
    for req in mod.requirements:
        target = requirement_target(req)
        if target in PSEUDO_IDS or target in installed_ids:
            continue
        # 旧 API 的 mod_hooks 依赖由汉化包内嵌提供
        if target == "mod_hooks" and "mod_hooks" in installed_ids:
            continue
        report.issues.append(Issue(
            severity="error", source=src,
            title=f"依赖缺失：{target}",
            detail=f"声明依赖 “{req}”，但当前未安装。",
            fix=f"安装 {target}（或含它的整合包）",
        ))

    # 4. 声明互斥（conflictWith / 队列 '!' token）
    for conflict in mod.declared_conflicts:
        target = requirement_target(conflict) or conflict
        if target in installed_ids:
            report.issues.append(Issue(
                severity="error", source=src,
                title=f"声明互斥的 mod 已同时安装：{target}",
                detail=f"该 mod 显式声明与 {target} 不兼容（conflictWith / '!' 队列标记）。",
                fix=f"二选一：禁用 {src} 或 {target}",
            ))

    # 5. 编译 mod 提示
    if mod.nut_count == 0 and mod.cnut_count > 0:
        report.issues.append(Issue(
            severity="info", source=src,
            title="编译版 mod（仅 .cnut），无法静态分析内部逻辑",
            detail="依赖/冲突/影响面按遮蔽路径启发式判断；以上次启动日志的实际加载结果为准。",
        ))
    # 6. 内嵌 zip
    if mod.nested_zips:
        report.issues.append(Issue(
            severity="warning", source=src,
            title=f"包内含内嵌 zip：{', '.join(Path(n).name for n in mod.nested_zips)}",
            detail="游戏不会挂载 zip 里的 zip，内层包需解出后单独放入 data 目录才能生效。",
            fix="安装时自动解出内层 zip（本软件安装功能已支持）",
        ))
    # 7. 影响种子提示
    if mod.seed_sensitive_paths:
        cats = sorted({c for c in ("world_map", "brothers", "items") if c in mod.categories})
        report.issues.append(Issue(
            severity="info", source=src,
            title=f"影响种子/地图生成（{', '.join(cats)}）",
            detail="该 mod 遮蔽了世界生成/角色/物品相关脚本，会干扰刷种子的 RNG 对齐；"
                   "刷种子时会被自动移除。",
        ))


# ---------------- 覆盖冲突 ----------------

def _check_file_overlaps(installed: list[ModInfo], report: DiagnosisReport) -> None:
    """按挂载顺序（文件名排序）两两求交集：后挂载者覆盖先挂载者的同名文件。"""
    ordered = sorted(installed, key=lambda m: m.file_name.lower())
    framework_srcs = {
        m.file_name for m in installed
        if any(r.mod_id in FRAMEWORK_IDS for r in m.registrations)
    }
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            a, b = ordered[i], ordered[j]
            if not a.entries or not b.entries:
                continue
            set_a = set(a.entries)
            overlap = [e for e in b.entries if e in set_a]
            if not overlap:
                continue
            script_overlap = [e for e in overlap if e.startswith("scripts/") and "/!mods_preload/" not in e]
            base_pack = a.file_name in framework_srcs or b.file_name in framework_srcs
            if not script_overlap and not base_pack:
                continue  # 纯资源覆盖且非框架，通常无害不报
            sev = "info" if base_pack else "warning"
            label = "脚本" if script_overlap else "资源"
            report.issues.append(Issue(
                severity=sev,
                source=b.file_name,
                title=f"将覆盖 {a.file_name} 的 {len(overlap)} 个文件（{label}覆盖）",
                detail=f"后挂载者生效。示例：{', '.join(e for e in (script_overlap or overlap)[:3])}",
            ))


# ---------------- preload 清单 ----------------

def _check_preload_manifests(installed: list[ModInfo], report: DiagnosisReport) -> None:
    holders: dict[str, list[str]] = {}
    for m in installed:
        for manifest in m.preload_manifests:
            holders.setdefault(manifest, []).append(m.file_name)
    for manifest, mods in holders.items():
        if len(mods) > 1:
            report.issues.append(Issue(
                severity="warning", source="系统",
                title=f"{len(mods)} 个 mod 都带 {manifest}，整文件互相覆盖",
                detail=f"{'、'.join(mods)} 各自携带该预载清单，游戏只挂载排序最后那个——其余 mod 的预载资源会失效。",
                fix="使用软件的 preload 合并功能生成并集清单包",
            ))


# ---------------- 运行时日志 ----------------

def _check_runtime(rows: list[LogRow], installed: list[ModInfo], report: DiagnosisReport) -> None:
    # 注册成功 → 实际加载成功的 id
    for row in rows:
        m = RE_RUNTIME_REGISTERED.search(row.text)
        if m:
            report.runtime_registered.append(m.group(1))

    # id/入口脚本名 → zip 文件名 的映射（用于错误归因）
    owner: dict[str, str] = {}
    for mod in installed:
        owner[mod.file_name] = mod.file_name
        for reg in mod.registrations:
            owner[reg.mod_id] = mod.file_name
        for p in mod.preload_scripts:
            owner[p.rsplit("/", 1)[-1]] = mod.file_name

    def attribute(text: str) -> str:
        for key, src in owner.items():
            if key and key in text:
                return src
        return ""

    reported: set[tuple[str, str]] = set()
    last_error_text = ""
    for idx, row in enumerate(rows):
        if row.level not in ("error", "critical"):
            continue
        if row.tag not in ("Script Error", "SQ", "hooks", "Script"):
            continue
        # "Failed to execute" 行是前一条 Script Error 的孪生行（含相同 Reason），只报一次
        if row.tag == "Script" and last_error_text[:40] and last_error_text[:40] in row.text:
            last_error_text = row.text
            continue
        last_error_text = row.text
        src = attribute(row.text)
        # Script Error 行常不点名 mod：看相邻的 "Failed to execute script file" 行取脚本路径归因
        if not src:
            for look in rows[idx + 1: idx + 3]:
                m_failed = RE_FAILED_SCRIPT.search(look.text)
                if m_failed:
                    src = attribute(m_failed.group(1))
                    break
        src = src or "运行时"
        key = (src, row.text[:80])
        if key in reported:
            continue
        reported.add(key)
        report.runtime_errors.append(row)
        report.issues.append(Issue(
            severity="error", source=src,
            title=f"上次启动报错：{row.text[:80]}",
            detail=f"[{row.time}] {row.tag} | {row.text}",
        ))
    # 存档污染提示
    for row in rows:
        if "save file was created with a modified version" in row.text:
            report.issues.append(Issue(
                severity="info", source="系统",
                title="存档带有 mod 标记（用修改版游戏创建）",
                detail="装/卸 mod 后继续玩旧存档可能异常；纯净原版成就党请勿在此存档上继续。",
            ))
            break
