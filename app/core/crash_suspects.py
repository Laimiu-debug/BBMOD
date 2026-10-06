"""Infer which installed MODs a game error points at, from the error and its call stack.

The game reports Squirrel errors with the failing message followed by call-stack
rows such as ``Function: onUpdate -> scripts/skills/x.nut : 42``. Every script
path is mapped to the ZIPs that ship it; when several ZIPs ship the same file the
one mounted last (file-name order) is the copy the game actually ran. The result
is a ranked hint, never proof: a MOD can also break vanilla code it hooks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .gamelog import LogRow
from .modinfo import ModInfo

RE_SCRIPT_PATH = re.compile(
    r'((?:scripts|ui|gfx|brushes|sounds|music|preload)/[^\s"\'<>|:*?]+?\.(?:c?nut|js|css|html))', re.I)
# Stack frames follow the error row; stop at the next unrelated error.
STACK_ROWS = 15
MAX_ERRORS = 20
# Frameworks wrap almost every call, so their frames say little about the cause.
FRAMEWORK_IDS = {'mod_hooks', 'mod_modern_hooks', 'mod_msu'}
FRAMEWORK_WEIGHT = 0.25


@dataclass
class Suspect:
    file_name: str
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {'file_name': self.file_name, 'score': round(self.score, 2), 'reasons': self.reasons[:5]}


def path_key(path: str) -> str:
    """Same normalization as overlap diagnostics: .nut and .cnut are one script."""
    return re.sub(r'\.(?:c?nut)$', '.squirrel', path.replace('\\', '/').lower())


def error_stacks(rows: list[LogRow]) -> list[tuple[LogRow, list[str]]]:
    """Each distinct error row with the script paths of its message and call stack."""
    result, seen, frames = [], set(), set()
    for index, row in enumerate(rows):
        # Stack frames are logged as error rows too; they belong to the error above.
        if row.level not in ('error', 'critical') or index in frames:
            continue
        key = row.text[:120]
        if key in seen:
            continue
        paths = RE_SCRIPT_PATH.findall(row.text)
        for offset, follow in enumerate(rows[index + 1:index + 1 + STACK_ROWS], index + 1):
            found = RE_SCRIPT_PATH.findall(follow.text)
            if follow.level in ('error', 'critical') and not found and not follow.text.lstrip().startswith(('Function', 'Variables')):
                break
            frames.add(offset)
            paths.extend(found)
        seen.add(key)
        result.append((row, list(dict.fromkeys(paths))))
        if len(result) >= MAX_ERRORS:
            break
    return result


class Attribution:
    """Index of installed MODs by shipped script path and registered id."""

    def __init__(self, mods: list[ModInfo]):
        ordered = sorted(mods, key=lambda m: m.file_name.lower())
        self.providers: dict[str, list[str]] = {}
        for mod in ordered:
            for entry in mod.entries:
                self.providers.setdefault(path_key(entry), []).append(mod.file_name)
        self.frameworks = {m.file_name for m in ordered
                           if any(r.mod_id in FRAMEWORK_IDS for r in m.registrations)}
        ids = {}
        for mod in ordered:
            for identity in [r.mod_id for r in mod.registrations] + [mod.package_id]:
                # Short ids such as "ui" would match ordinary words.
                if identity and len(identity) >= 5:
                    ids[identity] = mod.file_name
        self.ids = ids
        self.id_pattern = (re.compile(r'(?<![\w.])(' + '|'.join(map(re.escape, sorted(ids, key=len, reverse=True))) + r')(?![\w])')
                           if ids else None)

    def owner(self, path: str) -> str:
        """The ZIP whose copy of ``path`` the game runs, or '' for vanilla files."""
        providers = self.providers.get(path_key(path))
        return providers[-1] if providers else ''

    def suspects(self, rows: list[LogRow], limit: int = 5) -> list[Suspect]:
        found: dict[str, Suspect] = {}

        def add(name, weight, reason):
            suspect = found.setdefault(name, Suspect(name))
            if name in self.frameworks:
                weight *= FRAMEWORK_WEIGHT
            suspect.score += weight
            if reason not in suspect.reasons:
                suspect.reasons.append(reason)

        for row, paths in error_stacks(rows):
            message = row.text.strip().splitlines()[0][:80] if row.text.strip() else row.tag
            if self.id_pattern:
                for identity in dict.fromkeys(self.id_pattern.findall(row.text)):
                    add(self.ids[identity], 2.0, f'报错信息提到 {identity}：{message}')
            for position, path in enumerate(paths):
                providers = self.providers.get(path_key(path))
                if not providers:
                    continue
                winner = providers[-1]
                # The innermost frame is where the error was raised.
                weight = 3.0 if position == 0 else 1.0 / position
                add(winner, weight, f'报错调用栈经过 {path}：{message}')
                for loser in providers[:-1]:
                    add(loser, weight * 0.5, f'{path} 被 {winner} 覆盖，可能互相冲突')
        return sorted(found.values(), key=lambda s: (-s.score, s.file_name.lower()))[:limit]


def find_suspects(rows: list[LogRow], mods: list[ModInfo], limit: int = 5) -> list[Suspect]:
    return Attribution(mods).suspects(rows, limit)


def describe(suspects: list[dict]) -> str:
    """Plain-text section for reports and dialogs."""
    if not suspects:
        return '未能从报错定位到具体 MOD：调用栈只涉及原版脚本或日志未记录调用栈。'
    lines = ['可能相关的 MOD（根据报错和调用栈自动推断，仅供参考）：']
    for index, suspect in enumerate(suspects, 1):
        lines.append(f'{index}. {suspect["file_name"]}')
        lines.extend('   · ' + reason for reason in suspect['reasons'][:3])
    return '\n'.join(lines)
