"""种子生成器结果解析：把 log.html 的 SQ 日志行组装为种子结果块。

行协议（function_print_info.nut / function_main_loop.nut）：
  "Seed: NAME LoopIdx:N BroOutputType:x [MapOutputType:y] [LairOutputType:z]"  → 块开始
  "TeamInfo: ..." / "CharInfo: i ..." / "Trait: ..." / "LairInfo: ..." /
  "NamedInfo: ..." / "SettlementInfo: ..." / "BuildInfo: ..." / "AttachedInfo: ..." /
  "    ItemInfo(类型): ..."                                                    → 块内容
  "CRLF"                                                                      → 块结束
  "LoopIdx: N(命中数) 最高队伍分 平均分 ..."                                    → 进度
"""
from __future__ import annotations

import re
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..gamelog import IncrementalLogReader, LogRow
from .mod_origins import validate_mod_environment

RE_SEED_HEAD = re.compile(
    r"^Seed:\s+(\S+)\s+LoopIdx:(\d+)(?:\s+BroOutputType:(-?\d+))?"
    r"(?:\s+MapOutputType:(-?\d+))?(?:\s+LairOutputType:(-?\d+))?"
)
RE_LOOP_PROGRESS = re.compile(r"^LoopIdx:\s+(\d+)\((\d+)\)\s*(.*)$")
RE_TEAM_SCORE = re.compile(r"^TeamInfo:\s*([+-]?\d+(?:\.\d+)?)\b")


@dataclass
class SeedResult:
    seed: str
    loop_idx: int
    bro_output_type: int = -1
    map_output_type: int = -1
    lair_output_type: int = -1
    lines: list[str] = field(default_factory=list)
    done: bool = False
    origin: str = ""
    combat_difficulty: int | None = None
    economic_difficulty: int | None = None
    budget_difficulty: int | None = None
    game_version: str = ""
    dlc_mask: int | None = None
    mods: list[dict[str, str]] = field(default_factory=list)

    @property
    def team_score(self) -> float | None:
        for ln in self.lines:
            if ln.startswith("TeamInfo:"):
                m = RE_TEAM_SCORE.match(ln)
                if m:
                    return float(m.group(1))
        return None

    @property
    def brothers(self) -> list[str]:
        return [ln for ln in self.lines if ln.startswith("CharInfo:")]

    @property
    def named_items(self) -> list[str]:
        return [ln.strip() for ln in self.lines if "ItemInfo(" in ln]

    @property
    def lairs(self) -> list[str]:
        return [ln for ln in self.lines if ln.startswith("LairInfo:")]


@dataclass
class Progress:
    loop_idx: int = 0
    hits: int = 0
    best_team_score: str = ""
    detail: str = ""
    phase: str = ""


@dataclass
class StartupStatus:
    stage: str = "waiting"  # waiting | loaded | requested | generating | error
    detail: str = ""


class SeedLogParser:
    """状态机：喂入 LogRow 流，产出完成的 SeedResult 与 Progress 事件。"""

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id
        self.session_seen = session_id is None
        self.startup = StartupStatus()
        self.current: SeedResult | None = None
        self.results: list[SeedResult] = []
        self.progress: Progress = Progress()
        self._seen: set[tuple] = set()
        self.last_activity: float | None = None
        self.dlc_mask: int | None = None
        self.mods: list[dict[str, str]] = []
        self.campaign: tuple[int | None, ...] = (None, None, None)
        self.game_version = ""

    def finish(self, complete: bool = False) -> list[SeedResult]:
        """Preserve a final unfinished block, explicitly labelled as incomplete."""
        current, self.current = self.current, None
        if current is None:
            return []
        current.done = complete
        key = (current.origin, current.seed, current.loop_idx, current.game_version,
               current.combat_difficulty, current.economic_difficulty, current.budget_difficulty,
               current.dlc_mask, json.dumps(sorted(current.mods, key=lambda mod: mod['id']), sort_keys=True))
        if key in self._seen:
            return []
        self._seen.add(key)
        self.results.append(current)
        return [current]

    def feed(self, rows: list[LogRow]) -> tuple[list[SeedResult], list[Progress]]:
        """返回 (本轮完成的种子结果, 本轮出现的进度事件)。"""
        new_results: list[SeedResult] = []
        new_progress: list[Progress] = []
        for row in rows:
            text = row.text.strip()
            if text.startswith("BBMODSeedSession: "):
                self.dlc_mask = None
                self.mods = []
                self.campaign = (None, None, None)
                self.game_version = ""
                if self.session_id is not None:
                    matched = text == f"BBMODSeedSession: {self.session_id}"
                    if matched and not self.session_seen:
                        self.startup = StartupStatus("loaded")
                    elif not matched:
                        self.current = None
                        self.startup = StartupStatus()
                    self.session_seen = matched
                continue
            if not self.session_seen:
                continue
            self.last_activity = time.monotonic()
            if text.startswith("BBMODSeedEnvironment: Difficulty:"):
                match = re.fullmatch(r"BBMODSeedEnvironment: Difficulty:([0-2]),([0-2]),([0-2])", text)
                if match:
                    self.campaign = tuple(int(value) for value in match.groups())
                continue
            if text.startswith("BBMODSeedEnvironment: Game:"):
                version = text.removeprefix("BBMODSeedEnvironment: Game:")
                if re.fullmatch(r"(?:\d{1,3}\.){2,3}\d{1,3}", version):
                    self.game_version = version
                continue
            if text.startswith("BBMODSeedEnvironment: Mods:"):
                try:
                    encoded = text.removeprefix("BBMODSeedEnvironment: Mods:")
                    if len(encoded) > 8192:
                        raise ValueError("MOD 环境记录过长")
                    mods = json.loads(encoded)
                    validate_mod_environment(mods)
                    self.mods = mods
                except (ValueError, TypeError):
                    self.mods = []
                continue
            if text.startswith("BBMODSeedEnvironment: DLC:"):
                value = text.removeprefix("BBMODSeedEnvironment: DLC:")
                if value.isdigit() and int(value) <= 65535:
                    self.dlc_mask = int(value)
                continue
            if text.startswith("BBMODSeedProgress: "):
                match = re.fullmatch(r"BBMODSeedProgress: (\d+)\((\d+)\) ([a-z-]+)", text)
                if match:
                    self.progress.loop_idx = int(match[1])
                    self.progress.hits = int(match[2])
                    self.progress.phase = match[3]
                    new_progress.append(self.progress)
                continue
            if text.startswith("BBMODSeedStart: "):
                stage, _, detail = text.removeprefix("BBMODSeedStart: ").partition(" ")
                if stage in {"requested", "generating", "error"}:
                    self.startup = StartupStatus(stage, detail)
                continue
            m = RE_SEED_HEAD.match(text)
            if m:
                new_results.extend(self.finish())
                self.current = SeedResult(
                    seed=m.group(1),
                    loop_idx=int(m.group(2)),
                    bro_output_type=int(m.group(3) or -1),
                    map_output_type=int(m.group(4) or -1),
                    lair_output_type=int(m.group(5) or -1),
                    origin=(origin.group(1) if (origin := re.search(r"\bOrigin:(\S+)", text)) else ""),
                    dlc_mask=self.dlc_mask,
                    mods=[dict(mod) for mod in self.mods],
                    combat_difficulty=self.campaign[0], economic_difficulty=self.campaign[1],
                    budget_difficulty=self.campaign[2], game_version=self.game_version,
                )
                continue
            if text == "CRLF" or (not text and row.tag == "TXT"):
                new_results.extend(self.finish(complete=True))
                continue
            m = RE_LOOP_PROGRESS.match(text)
            if m:
                self.progress = Progress(
                    loop_idx=int(m.group(1)),
                    hits=int(m.group(2)),
                    detail=m.group(3),
                )
                # 进度行格式：LoopIdx: N(命中) 最高分 平均分 ...
                parts = m.group(3).split()
                if parts:
                    self.progress.best_team_score = parts[0]
                new_progress.append(self.progress)
                continue
            if self.current is not None and text.startswith((
                "TeamInfo:", "CharInfo:", "Trait:", "LairInfo:", "NamedInfo:",
                "SettlementInfo:", "BuildInfo:", "AttachedInfo:", "ItemInfo(",
            )):
                self.current.lines.append(text)
        return new_results, new_progress


def import_seed_log(path: Path) -> list[SeedResult]:
    """Explicit historical import. Unlike live reads, no session marker is required."""
    if path.suffix.lower() not in {".txt", ".html", ".htm"}:
        raise ValueError("请选择种子生成器的 TXT 或 HTML 日志")
    # Surface permission/missing-file errors instead of claiming an empty import.
    with path.open("rb"):
        pass
    reader = IncrementalLogReader(path)
    parser = SeedLogParser()
    while True:
        before = reader.offset
        parser.feed(reader.read_new())
        if reader.error:
            raise OSError(reader.error)
        if reader.offset == before:
            break
    parser.feed(reader.finish())
    parser.finish()
    return parser.results
