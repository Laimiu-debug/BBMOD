"""刷种子全自动编排：快照 → 净化 → 注入 → 启动 → 监控 → 停止 → 恢复。

安全设计：
- 注入前 stash 全部 mod（RNG 对齐要求游戏纯净）；记录每个写入 data 的文件；
- 结束时只删除注入清单内的文件、恢复快照；任何异常路径都先走清理；
- 官方 data_*.dat 永不触碰。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .. import game as game_mod
from ..game import GameInfo
from ..modmanager import ModManager, Snapshot
from .config_emitter import SeedGenConfig, write_configs
from .log_watcher import Progress, SeedLogParser, SeedResult
from ..gamelog import IncrementalLogReader


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
        self._snapshot: Snapshot | None = None
        self._injected: list[Path] = []
        self._created_dirs: list[Path] = []
        self._parser = SeedLogParser()
        self._reader: IncrementalLogReader | None = None
        self.results: list[SeedResult] = []

    # ---------------- 准备 ----------------

    def prepare(self, cfg: SeedGenConfig) -> list[str]:
        """快照 + 净化 + 注入 payload + 写配置。返回给用户的提示列表。"""
        warnings: list[str] = []
        if self.state.stage != "idle":
            raise RuntimeError(f"会话已在 {self.state.stage} 状态，请先 stop_and_restore")
        if game_mod.is_game_running():
            raise RuntimeError("游戏正在运行，请先关闭再开始刷种子")
        if self.game.version and self.game.version != "1.5.2.3":
            warnings.append(f"游戏版本 {self.game.version} ≠ 1.5.2.3，种子生成器按 1.5.2.3 校准，结果可能失真。")
        base = game_mod.check_base_archive(self.game.data_dir)
        if base and base.repacked:
            warnings.append("游戏基座为汉化重打包版，无法通过移除 mod 净化，种子结果可能失真（建议 Steam 校验还原原版）。")
        if self.mm.has_orphan_stash():
            recovered = self.mm.cleanup_stash()
            warnings.append(f"发现上次刷种子遗留的 {recovered} 个 mod，已自动还原到 data 目录。")

        self._snapshot = self.mm.stash_all_mods()
        self._inject_payload()
        write_configs(self.payload_dir, self.game.data_dir, cfg)
        self.state.stage = "prepared"
        self.state.warnings = warnings
        return warnings

    def _inject_payload(self) -> None:
        for item in self.payload_dir.iterdir():
            dst = self.game.data_dir / item.name
            if item.is_file():
                if not dst.exists():
                    shutil.copy2(item, dst)
                    self._injected.append(dst)
            else:
                for f in sorted(item.rglob("*")):
                    if f.is_file():
                        target = dst / f.relative_to(item)
                        if not target.exists():
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, target)
                            self._injected.append(target)
        # 记录 payload 涉及的 data 子目录（恢复后用于自底向上删空壳）
        for f in self._injected:
            for d in f.parents:
                if d.is_relative_to(self.game.data_dir) and d != self.game.data_dir and d not in self._created_dirs:
                    self._created_dirs.append(d)

    # ---------------- 运行 ----------------

    def launch(self) -> bool:
        if self.state.stage != "prepared":
            raise RuntimeError("请先 prepare()")
        log_path = game_mod.find_log_write_path()
        if log_path:
            self._reader = IncrementalLogReader(log_path / "log.html")
            self._reader.reset()
        ok = game_mod.launch_game(self.game)
        if ok:
            self.state.stage = "running"
        return ok

    def poll(self) -> tuple[list[SeedResult], list[Progress]]:
        """轮询新日志行 → (新种子结果, 进度事件)。"""
        if self._reader is None:
            return [], []
        rows = self._reader.read_new()
        new_results, new_progress = self._parser.feed(rows)
        self.results.extend(new_results)
        return new_results, new_progress

    @property
    def progress(self) -> Progress:
        return self._parser.progress

    # ---------------- 结束 ----------------

    def stop_and_restore(self) -> int:
        """停止游戏 → 移除注入 → 恢复 mod 快照。返回恢复的 mod 数。"""
        try:
            if game_mod.is_game_running():
                game_mod.kill_game()
        finally:
            self._cleanup_payload()
            restored = 0
            if self._snapshot is not None:
                restored = self.mm.restore_snapshot(self._snapshot)
            self.state.stage = "restored"
            self._snapshot = None
        return restored

    def _cleanup_payload(self) -> None:
        for f in self._injected:
            try:
                if f.exists():
                    f.unlink()
            except OSError:
                pass
        # 自底向上清理我们创建的空目录
        for d in sorted(self._created_dirs, key=lambda p: len(p.parts), reverse=True):
            try:
                if d.exists() and d != self.game.data_dir and not any(d.iterdir()):
                    d.rmdir()
            except OSError:
                pass
        self._injected.clear()
        self._created_dirs.clear()
