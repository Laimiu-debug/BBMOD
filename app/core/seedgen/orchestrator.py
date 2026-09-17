"""刷种子全自动编排：快照 → 净化 → 注入 → 启动 → 监控 → 停止 → 恢复。

安全设计：
- 注入前 stash 全部 mod（RNG 对齐要求游戏纯净）；记录每个写入 data 的文件；
- 结束时只删除注入清单内的文件、恢复快照；任何异常路径都先走清理；
- 官方 data_*.dat 永不触碰。
"""
from __future__ import annotations

import tempfile
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path

from .. import game as game_mod
from ..game import GameInfo
from ..modmanager import ModManager
from .config_emitter import SeedGenConfig, write_configs
from .log_watcher import Progress, SeedLogParser, SeedResult
from ..gamelog import IncrementalLogReader
from .session import FileSession


@dataclass
class SessionState:
    stage: str = "idle"  # idle | prepared | running | finished | restored
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StopLimits:
    hits: int = 0
    minutes: int = 0

    def __post_init__(self):
        if any(type(value) is not int or value < 0 for value in (self.hits, self.minutes)):
            raise ValueError("自动停止的数量和分钟数必须是非负整数；0 表示不限")

    @property
    def description(self) -> str:
        conditions = [f"找到 {self.hits} 条"] if self.hits else []
        if self.minutes:
            conditions.append(f"运行 {self.minutes} 分钟")
        return " 或 ".join(conditions) + "后停止" if conditions else "持续搜索，可随时停止"


class SeedGenOrchestrator:
    def __init__(self, game: GameInfo, payload_dir: Path | str, *,
                 log_directory: Path | None = None, limits: StopLimits | None = None) -> None:
        self.game = game
        self.payload_dir = Path(payload_dir)
        self.mm = ModManager(game.root)
        self.state = SessionState()
        self._injected: list[Path] = []
        self._reader: IncrementalLogReader | None = None
        self.results: list[SeedResult] = []
        self.files = FileSession(game.root)
        self._session_id = uuid.uuid4().hex
        self._parser = SeedLogParser(session_id=self._session_id)
        self._campaign = None
        self.log_directory = log_directory
        self.limits = limits or StopLimits()
        self._started_at: float | None = None
        self._readers: dict[Path, tuple[IncrementalLogReader, SeedLogParser]] = {}
        self._seen: set[tuple[str, str, int]] = set()

    # ---------------- 准备 ----------------

    def prepare(self, cfg: SeedGenConfig) -> list[str]:
        """快照 + 净化 + 注入 payload + 写配置。返回给用户的提示列表。"""
        warnings: list[str] = []
        if self.state.stage != "idle":
            raise RuntimeError(f"会话已在 {self.state.stage} 状态，请先 stop_and_restore")
        if game_mod.is_game_running():
            raise RuntimeError("游戏正在运行，请先关闭再开始刷种子")
        cfg.campaign.validate()
        if self.game.version and self.game.version != "1.5.2.3":
            warnings.append(f"游戏版本 {self.game.version} ≠ 1.5.2.3，种子生成器按 1.5.2.3 校准，结果可能失真。")
        base = game_mod.check_base_archive(self.game.data_dir)
        if base and base.read_error:
            raise RuntimeError(base.warning)
        if self.files.active:
            recovered = self.files.restore()
            warnings.append(f"已恢复上次未结束会话的 {recovered} 个 mod 和原有配置。")
        if self.mm.has_orphan_stash():
            raise RuntimeError("发现旧版暂存目录 bbmod_seedgen_stash。请先恢复其中的 MOD 并检查旧版注入文件，再开始远征。")
        payload = {path.relative_to(self.payload_dir).as_posix(): path.read_bytes()
            for path in self.payload_dir.rglob("*") if path.is_file()}
        with tempfile.TemporaryDirectory(prefix="bbmod-config-") as temporary:
            temporary_root = Path(temporary).resolve()
            if not temporary_root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
                raise ValueError("配置临时目录越界")
            for path in write_configs(self.payload_dir, temporary_root, cfg, self._session_id):
                payload[path.relative_to(temporary_root).as_posix()] = path.read_bytes()
        try:
            self.files.begin(payload)
        except Exception:
            if self.files.active:
                self.files.restore()
            raise
        self._injected = [self.game.data_dir / name for name in payload]
        self.mm._audit("seedgen-prepare", self.game.data_dir, self.files.root)
        self.state.stage = "prepared"
        self._campaign = replace(cfg.campaign)
        self.state.warnings = warnings
        return warnings

    # ---------------- 运行 ----------------

    def launch(self) -> bool:
        if self.state.stage != "prepared":
            raise RuntimeError("请先 prepare()")
        self._discover_readers()
        # Launch the exact installation that received the temporary payload.
        ok = game_mod.launch_game(self.game, via_steam=False)
        if ok:
            self.state.stage = "running"
            self._started_at = time.monotonic()
        return ok

    def _discover_readers(self) -> None:
        for directory in game_mod.find_log_write_paths(self.log_directory):
            for name in ("log.html", "log.txt"):
                path = directory / name
                if path not in self._readers:
                    reader = IncrementalLogReader(path)
                    parser = SeedLogParser(session_id=self._session_id)
                    self._readers[path] = (reader, parser)
                    if self._reader is None:
                        self._reader, self._parser = reader, parser

    def set_log_directory(self, directory: Path | None) -> None:
        self.log_directory = directory
        self._readers.clear()
        self._reader = None
        self._parser = SeedLogParser(session_id=self._session_id)
        self._discover_readers()

    def _collect(self, results: list[SeedResult]) -> list[SeedResult]:
        fresh = []
        for result in results:
            key = (result.origin, result.seed, result.loop_idx)
            if key in self._seen:
                continue
            self._seen.add(key)
            if self._campaign:
                result.combat_difficulty = self._campaign.combat_difficulty
                result.economic_difficulty = self._campaign.economic_difficulty
                result.budget_difficulty = self._campaign.budget_difficulty
            fresh.append(result)
        self.results.extend(fresh)
        return fresh

    def poll(self) -> tuple[list[SeedResult], list[Progress]]:
        """轮询新日志行 → (新种子结果, 进度事件)。"""
        if not self._parser.session_seen:
            self._discover_readers()
        candidates = ([(self._reader, self._parser)] if self._parser.session_seen and self._reader
                      else list(self._readers.values()))
        for reader, parser in candidates:
            generation = reader.generation
            rows = reader.read_new()
            if generation != reader.generation:
                parser = SeedLogParser(session_id=self._session_id)
                self._readers[reader.path] = (reader, parser)
                if reader is self._reader:
                    self._parser = parser
            results, progress = parser.feed(rows)
            if parser.session_seen or results or progress:
                self._reader, self._parser = reader, parser
                return self._collect(results), progress
        return [], []

    @property
    def log_path(self) -> Path | None:
        return self._reader.path if self._reader and self._parser.session_seen else None

    @property
    def checked_log_paths(self) -> list[Path]:
        return list(self._readers)

    @property
    def elapsed_seconds(self) -> int:
        return max(0, int(time.monotonic() - self._started_at)) if self._started_at is not None else 0

    @property
    def stop_reason(self) -> str:
        if self.state.stage != "running":
            return ""
        if self.limits.hits and sum(result.done for result in self.results) >= self.limits.hits:
            return f"已达到 {self.limits.hits} 条命中目标"
        if self.limits.minutes and self.elapsed_seconds >= self.limits.minutes * 60:
            return f"已达到 {self.limits.minutes} 分钟时限"
        return ""

    @property
    def progress(self) -> Progress:
        return self._parser.progress

    @property
    def startup(self):
        return self._parser.startup

    # ---------------- 结束 ----------------

    def stop_and_restore(self) -> int:
        """停止游戏 → 移除注入 → 恢复 mod 快照。返回恢复的 mod 数。"""
        if game_mod.is_game_running():
            if self.state.stage != "running" or not game_mod.kill_game():
                raise RuntimeError("游戏仍在运行。请先关闭游戏，再重试恢复；原文件备份已保留。")
        # Drain output after the process stops, including a final truncated block.
        # A partial record is retained for inspection but does not count as a full hit.
        while self._readers:
            offsets = {path: reader.offset for path, (reader, _) in self._readers.items()}
            self.poll()
            if offsets == {path: reader.offset for path, (reader, _) in self._readers.items()}:
                break
        if self._reader and self._parser.session_seen:
            results, _ = self._parser.feed(self._reader.finish())
            self._collect(results + self._parser.finish())
        restored = self.files.restore()
        self.mm._audit("seedgen-restore", self.files.root, self.game.data_dir)
        self.state.stage = "restored"
        self._injected.clear()
        return restored
