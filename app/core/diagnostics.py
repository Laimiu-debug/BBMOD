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
    dependency: str | None = None

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
    report.issues.extend(diagnose_mods(installed).issues)

    if log_rows is not None:
        _check_runtime(log_rows, installed, report)
    return report


def diagnose_mods(installed: list[ModInfo]) -> DiagnosisReport:
    """MOD-only preflight, shared by diagnosis and file transactions."""
    report = DiagnosisReport()
    installed_ids = {r.mod_id for m in installed for r in m.registrations}
    for mod in installed:
        _check_mod(mod, installed_ids, report)
    _check_requirement_versions(installed, report)
    _check_known_conflicts(installed, report)
    _check_file_overlaps(installed, report)
    _check_preload_manifests(installed, report)
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
        if not reg.numeric_version_ok and not has_modern:
            report.issues.append(Issue(
                severity="error", source=src,
                title=f"版本号 “{reg.version}” 不合法：旧版 mod_hooks 要求纯数字",
                detail=f"mod {reg.mod_id} 以旧 API 注册，mod_hooks v21.1 会直接拒绝加载"
                       f"（游戏日志报 “not using a numeric version”）。",
                fix="安装 Modern Hooks 的旧 API 兼容层；不要自行改写版本号。",
                dependency='mod_modern_hooks',
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
            dependency='mod_modern_hooks',
        ))

    if mod.api in ('legacy', 'mixed') and 'mod_hooks' not in installed_ids and not is_hooks_itself:
        report.issues.append(Issue('error', src, '需要 Modding Script Hooks 框架，但未安装',
            'Modern Hooks 不能单独提供全部旧版 hooks 接口。',
            '安装 Modding Script Hooks 或启用已包含它的汉化包。', 'mod_hooks'))
    if mod.uses_msu and 'mod_msu' not in installed_ids and not is_hooks_itself:
        report.issues.append(Issue('error', src, '需要 MSU 框架，但未安装',
            '脚本使用 MSU 接口。', '先安装 MSU 及其框架前置。', 'mod_msu'))

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
            dependency=target,
        ))

    # 4. 声明互斥（conflictWith / 队列 '!' token）
    for conflict in mod.declared_conflicts:
        target = requirement_target(conflict) or conflict
        if target in installed_ids:
            # Version-qualified conflicts must only reject matching versions.
            # The concrete check is performed with the complete set below.
            if conflict.strip() != target:
                continue
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


def _check_requirement_versions(installed, report):
    from .dependency_versions import satisfies
    versions = {reg.mod_id: reg for mod in installed for reg in mod.registrations}
    modern = 'mod_modern_hooks' in versions
    for mod in installed:
        for error in mod.analysis_errors:
            report.issues.append(Issue('warning', mod.file_name, '无法完整分析 MOD', error,
                                       '检查压缩包是否完整，必要时重新下载。'))
        for requirement in mod.requirements:
            target = requirement_target(requirement)
            registration = versions.get(target)
            if registration is None:
                continue
            api = 'modern' if modern and registration.version_is_string else registration.api
            result = satisfies(requirement, registration.version, api)
            if result is False:
                report.issues.append(Issue('error', mod.file_name, f'前置版本不满足：{target}',
                    f'要求 {requirement}；当前 {registration.version}', '选择符合要求的前置版本。', target))
            elif result is None:
                report.issues.append(Issue('warning', mod.file_name, f'前置版本需人工确认：{target}',
                    f'要求 {requirement}；当前 {registration.version}。暂不支持自动比较此格式。',
                    '查看作者的版本要求。', target))
        for conflict in mod.declared_conflicts:
            target = requirement_target(conflict)
            if target == conflict.strip() or target not in versions:
                continue
            reg = versions[target]
            result = satisfies(conflict, reg.version, 'modern' if modern else reg.api)
            if result is True:
                report.issues.append(Issue('error', mod.file_name, f'声明冲突：{conflict}',
                    f'当前 {target} {reg.version} 命中冲突范围。', '升级前置或二选一禁用。'))


def _check_known_conflicts(installed, report):
    from .modstore import load_index
    index = load_index()
    registered = {r.mod_id: m for m in installed for r in m.registrations}
    if 'mod_swifter' in registered and 'mod_autopilot' in registered:
        report.issues.append(Issue('error', registered['mod_autopilot'].file_name,
            'Swifter 与旧版 Autopilot 不能同时启用',
            '两者都改写战斗行动流程，原作声明互不兼容。', '加速与旧版自动战斗只保留一个。'))
    stars = [m for m in installed if '显星互斥' in index.get(m.file_name, {}).get('tags', [])]
    if len(stars) > 1:
        report.issues.append(Issue('error', stars[-1].file_name, '两种显星 MOD 不能同时启用',
            '、'.join(m.file_name for m in stars), '轻度显星和显星显属性带评价只保留一个。'))
    # The two complete translations replace the same game and UI scripts.
    fox = [m for m in installed if m.file_name.startswith(('data狐狸汉化', 'data_fox_zhcn'))]
    own = [m for m in installed if 'BBMOD_L10N.json' in m.entries or m.file_name == 'mod_bbmod_zhcn.zip']
    if fox and own:
        report.issues.append(Issue('error', fox[0].file_name, '狐狸汉化与 BBMOD 独立汉化不能同时启用',
            '两套汉化覆盖相同游戏脚本和界面。', '在汉化管理中选择一种汉化。'))
    owners = {}
    for mod in installed:
        for reg in mod.registrations:
            owners.setdefault(reg.mod_id, []).append(mod)
    for ident, mods in owners.items():
        if len(mods) > 1 and ident not in FRAMEWORK_IDS:
            report.issues.append(Issue('error', mods[-1].file_name, f'MOD 重复注册：{ident}',
                '、'.join(m.file_name for m in mods), '同一个 MOD 只启用一个版本。'))


# ---------------- 覆盖冲突 ----------------

OVERLAP_ROOTS = ('scripts/', 'ui/', 'gfx/', 'brushes/', 'sounds/', 'music/', 'preload/')
RE_SQUIRREL_SOURCE = re.compile(r'\.(?:c?nut)$')


def _overlap_key(entry: str) -> str:
    return RE_SQUIRREL_SOURCE.sub('.squirrel', entry.replace('\\', '/').lower())


def _check_file_overlaps(installed: list[ModInfo], report: DiagnosisReport) -> None:
    """按挂载顺序（文件名排序）两两求交集：后挂载者覆盖先挂载者的同名文件。"""
    ordered = sorted(installed, key=lambda m: m.file_name.lower())
    framework_srcs = {
        m.file_name for m in installed
        if any(r.mod_id in FRAMEWORK_IDS for r in m.registrations)
    }
    keyed = [[(e, _overlap_key(e)) for e in m.entries] for m in ordered]
    mounted = [{k for e, k in entries if e.lower().startswith(OVERLAP_ROOTS)} for entries in keyed]
    present = [{k for _, k in entries} for entries in keyed]
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            a, b = ordered[i], ordered[j]
            if not a.entries or not b.entries or mounted[i].isdisjoint(present[j]):
                continue
            overlap = [e for e, k in keyed[j] if k in mounted[i]]
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
    from .preload_merge import FILENAME, MARKER
    if any(m.file_name == FILENAME and MARKER in m.entries for m in installed):
        return
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
                fix="通过新版管理器安装或切换 MOD 时会自动生成并集清单包。",
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
