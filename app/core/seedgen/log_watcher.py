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
from dataclasses import dataclass, field

from ..gamelog import LogRow

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


class SeedLogParser:
    """状态机：喂入 LogRow 流，产出完成的 SeedResult 与 Progress 事件。"""

    def __init__(self) -> None:
        self.current: SeedResult | None = None
        self.results: list[SeedResult] = []
        self.progress: Progress = Progress()
        self._orphan_lines: list[str] = []

    def feed(self, rows: list[LogRow]) -> tuple[list[SeedResult], list[Progress]]:
        """返回 (本轮完成的种子结果, 本轮出现的进度事件)。"""
        new_results: list[SeedResult] = []
        new_progress: list[Progress] = []
        for row in rows:
            text = row.text.strip()
            m = RE_SEED_HEAD.match(text)
            if m:
                # 上一块未闭合（异常中断）也照样收录
                if self.current and not self.current.done:
                    self.current.done = True
                    self.results.append(self.current)
                    new_results.append(self.current)
                self.current = SeedResult(
                    seed=m.group(1),
                    loop_idx=int(m.group(2)),
                    bro_output_type=int(m.group(3) or -1),
                    map_output_type=int(m.group(4) or -1),
                    lair_output_type=int(m.group(5) or -1),
                    origin=(origin.group(1) if (origin := re.search(r"\bOrigin:(\S+)", text)) else ""),
                )
                continue
            if text == "CRLF":
                if self.current and not self.current.done:
                    self.current.done = True
                    self.results.append(self.current)
                    new_results.append(self.current)
                    self.current = None
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
            if self.current is not None:
                self.current.lines.append(text)
            elif text.startswith(("TeamInfo:", "CharInfo:", "LairInfo:", "NamedInfo:", "SettlementInfo:")):
                self._orphan_lines.append(text)
        return new_results, new_progress
