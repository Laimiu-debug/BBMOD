"""Read game HTML logs and converted TXT logs, including incremental writes."""
from __future__ import annotations

import codecs
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


@dataclass
class LogRow:
    level: str
    time: str
    tag: str
    text: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.time} {self.tag} | {self.text}"


class _Rows(HTMLParser):
    """Emit at the text cell's closing tag, without waiting for the whole document."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[LogRow] = []
        self.depth = 0
        self.row: dict[str, str] | None = None
        self.field = ""
        self.field_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br" and self.field:
            self.parts.append("\n")
        if tag != "div":
            return
        self.depth += 1
        classes = (dict(attrs).get("class") or "").split()
        if "row" in classes:
            self.row = {"level": next((c for c in classes if c in
                {"debug", "info", "warning", "error", "critical"}), "info"), "time": "", "tag": ""}
            self.field = ""
        if self.row is not None and not self.field:
            for field in ("time", "tag", "text"):
                if field in classes:
                    self.field, self.field_depth, self.parts = field, self.depth, []
                    break

    def handle_data(self, data):
        if self.field:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != "div":
            return
        if self.field and self.depth == self.field_depth:
            self.row[self.field] = "".join(self.parts)
            if self.field == "text":
                self.rows.append(LogRow(**self.row))
                self.row = None
            self.field, self.parts = "", []
        self.depth = max(0, self.depth - 1)

    def take(self) -> list[LogRow]:
        rows, self.rows = self.rows, []
        return rows


def iter_rows(html_text: str) -> list[LogRow]:
    parser = _Rows()
    parser.feed(html_text)
    return parser.take()


def load_log(path: Path) -> list[LogRow]:
    reader = IncrementalLogReader(path)
    rows = []
    while True:
        offset = reader.offset
        rows.extend(reader.read_new())
        if reader.offset == offset:
            break
    return rows + reader.finish()


class IncrementalLogReader:
    """Bounded reads, streaming Unicode, and detection of truncation/replacement.

    TXT blank lines remain explicit delimiters. HTML formatting whitespace is
    ignored. A partial TXT line is only consumed on newline or explicit finish.
    """
    CHUNK_SIZE = 256 * 1024
    MAX_LINE_LENGTH = 256 * 1024

    def __init__(self, path: Path) -> None:
        self.path = path
        self.generation = -1
        self.reset()

    @property
    def offset(self) -> int:
        return self._offset

    def reset(self) -> None:
        self.generation += 1
        self._offset = 0
        self._prefix = b""
        self._anchor = b""
        self._decoder = None
        self._encoding_head = b""
        self._html = _Rows() if self.path.suffix.lower() in {".html", ".htm"} else None
        self._buffer = ""
        self.error = ""

    def _text(self, text: str) -> list[LogRow]:
        if self._html is not None:
            self._html.feed(text)
            return self._html.take()
        self._buffer += text
        lines = self._buffer.split("\n")
        self._buffer = lines.pop()
        if len(self._buffer) > self.MAX_LINE_LENGTH:
            self.error = "日志中有过长且未换行的文本，请检查文件格式"
            self._buffer = ""
        return [LogRow("info", "", "TXT", line.rstrip("\r")) for line in lines]

    def read_new(self) -> list[LogRow]:
        try:
            with self.path.open("rb") as stream:
                stream.seek(0, 2)
                size = stream.tell()
                stream.seek(0)
                prefix = stream.read(len(self._prefix))
                stream.seek(max(0, self._offset - len(self._anchor)))
                anchor = stream.read(len(self._anchor))
                if size < self._offset or prefix != self._prefix or anchor != self._anchor:
                    self.reset()
                stream.seek(self._offset)
                chunk = stream.read(self.CHUNK_SIZE)
                self._offset = stream.tell()
                stream.seek(0)
                self._prefix = stream.read(min(8192, self._offset))
                stream.seek(max(0, self._offset - 64))
                self._anchor = stream.read(min(64, self._offset))
        except OSError as error:
            self.error = str(error)
            return []
        self.error = ""
        if not chunk:
            return []
        if self._decoder is None:
            self._encoding_head += chunk
            if len(self._encoding_head) < 3:
                return []
            encoding = "utf-16" if self._encoding_head.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
            self._decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
            chunk, self._encoding_head = self._encoding_head, b""
        return self._text(self._decoder.decode(chunk))

    def finish(self) -> list[LogRow]:
        """Call only at a known EOF (import or stopped game), never on a live pause."""
        tail = self._decoder.decode(b"", final=True) if self._decoder else self._encoding_head.decode("utf-8-sig", errors="replace")
        rows = self._text(tail)
        if self._html is None and self._buffer:
            rows.append(LogRow("info", "", "TXT", self._buffer.rstrip("\r")))
        self._buffer, self._encoding_head = "", b""
        return rows
