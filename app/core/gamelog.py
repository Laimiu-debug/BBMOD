"""游戏 log.html 解析：结构化行提取 + 增量读取。

log.html 是无换行的单行 HTML，每条日志形如：
  <div class="row {level}"><div class="entry-container"><div class="time">HH:MM:SS</div>
  <div class="tag">Tag</div><div class="text">TEXT</div></div></div>
错误行额外带 stacktrace-container。SQ tag 的行来自脚本 logInfo（种子生成器结果也走这里）。
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

RE_ROW = re.compile(
    r'<div class="row (debug|info|warning|error|critical)">'
    r'<div class="entry-container"><div class="time">([^<]*)</div>'
    r'<div class="tag">([^<]*)</div>'
    r'<div class="text">([^<]*)</div>'
)


@dataclass
class LogRow:
    level: str  # debug | info | warning | error | critical
    time: str
    tag: str  # Platform | Core | IO | SQ | Script Error | hooks | ATTENTION | ...
    text: str

    def __str__(self) -> str:  # 诊断/调试用
        return f"[{self.level}] {self.time} {self.tag} | {self.text}"


def iter_rows(html_text: str) -> list[LogRow]:
    """全量解析（诊断用）。"""
    return [
        LogRow(level=m.group(1), time=m.group(2), tag=m.group(3), text=html.unescape(m.group(4)))
        for m in RE_ROW.finditer(html_text)
    ]


def load_log(path: Path) -> list[LogRow]:
    try:
        text = path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return []
    return iter_rows(text)


class IncrementalLogReader:
    """增量读取器：跟踪字节偏移，只返回上次调用之后的新行（刷种子实时监控用）。

    游戏会持续向文件追加；文件被新会话截断时自动重置。
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._offset = 0
        self._buffer = ""

    @property
    def offset(self) -> int:
        return self._offset

    def reset(self) -> None:
        self._offset = 0
        self._buffer = ""

    def read_new(self) -> list[LogRow]:
        try:
            size = self.path.stat().st_size
        except OSError:
            return []
        if size < self._offset:  # 文件被截断 → 新会话
            self.reset()
        try:
            with self.path.open("rb") as f:
                f.seek(self._offset)
                chunk = f.read().decode("utf-8", errors="replace")
        except OSError:
            return []
        self._offset = size
        self._buffer += chunk

        rows: list[LogRow] = []
        consumed = 0
        for m in RE_ROW.finditer(self._buffer):
            rows.append(
                LogRow(level=m.group(1), time=m.group(2), tag=m.group(3), text=html.unescape(m.group(4)))
            )
            consumed = m.end()
        self._buffer = self._buffer[consumed:]
        return rows
