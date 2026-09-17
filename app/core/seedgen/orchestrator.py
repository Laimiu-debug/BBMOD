"""刷种子全自动编排：快照 → 净化 → 注入 → 启动 → 监控 → 停止 → 恢复。

安全设计：
- 注入前 stash 全部 mod（RNG 对齐要求游戏纯净）；记录每个写入 data 的文件；
- 结束时只删除注入清单内的文件、恢复快照；任何异常路径都先走清理；
- 官方 data_*.dat 永不触碰。
"""
from __future__ import annotations

import tempfile
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


class SeedGenOrchestrator:
    def __init__(self, game: GameInfo, payload_dir: Path | str) -> None:
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
        log_path = game_mod.find_log_write_path()
        if log_path:
            self._reader = IncrementalLogReader(log_path / "log.html")
            self._reader.reset()
        # Launch the exact installation that received the temporary payload.
        ok = game_mod.launch_game(self.game, via_steam=False)
        if ok:
            self.state.stage = "running"
        return ok

    def poll(self) -> tuple[list[SeedResult], list[Progress]]:
        """轮询新日志行 → (新种子结果, 进度事件)。"""
        if self._reader is None:
            log_path = game_mod.find_log_write_path()
            if not log_path:
                return [], []
            self._reader = IncrementalLogReader(log_path / "log.html")
        if not self._parser.session_seen:
            # A new log may already have grown past the previous file size.
            # Find our unique session marker before accepting any old results.
            self._reader.reset()
        rows = self._reader.read_new()
        new_results, new_progress = self._parser.feed(rows)
        if self._campaign:
            for result in new_results:
                result.combat_difficulty = self._campaign.combat_difficulty
                result.economic_difficulty = self._campaign.economic_difficulty
                result.budget_difficulty = self._campaign.budget_difficulty
        self.results.extend(new_results)
        return new_results, new_progress

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
        restored = self.files.restore()
        self.mm._audit("seedgen-restore", self.files.root, self.game.data_dir)
        self.state.stage = "restored"
        self._injected.clear()
        return restored
