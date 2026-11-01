"""Run a self-contained headless solver. No installed-game or session imports."""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from ..io_util import atomic_write_bytes
from ..paths import app_root
from .model import PROFILE, WorldMap, campaign_key, validate_seed


class SolveCancelled(Exception):
    pass


@dataclass(frozen=True)
class Components:
    binary: Path
    bootstrap: Path
    rules: Path

    @classmethod
    def locate(cls):
        override = os.environ.get('BBMOD_WORLDMAP_HOME')
        root = Path(override) if override else app_root()/'worldmap'
        candidate = cls(root/'worldmap.exe', root/'runtime.nut', root/'rules')
        if override or candidate.binary.is_file():
            return candidate
        root = app_root()/'build/offline-map'
        return cls(root/'bin/worldmap.exe', app_root()/'native/worldmap/runtime.nut', root/'rules')

    def fingerprint(self) -> str:
        digest = hashlib.sha256()
        for path in (self.binary, self.bootstrap, self.bootstrap.with_name('camps.nut'),
                     self.bootstrap.with_name('actors.nut'),
                     self.rules/'origin_alignment.nut', self.rules/'manifest.json', self.rules/'index.nut'):
            if not path.is_file():
                raise FileNotFoundError('离线地图组件尚未准备好，请先构建解算器与规则包。')
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        manifest = json.loads((self.rules/'manifest.json').read_text('utf-8'))
        if manifest.get('game_version') != '1.5.2.3' or manifest.get('profile', PROFILE) != PROFILE:
            raise ValueError('离线规则包版本不受支持。')
        return digest.hexdigest()


@dataclass(frozen=True)
class SolveResult:
    world: WorldMap
    elapsed: float
    generation_seconds: float
    cached: bool
    fingerprint: str


def default_cache() -> Path:
    override = os.environ.get('BBMOD_WORLDMAP_CACHE')
    if override:
        return Path(override)
    # This workstation stores generic caches off the system drive.
    if Path('H:/codex').is_dir():
        return Path('H:/codex/cache/bbmod/worldmap')
    return Path(os.environ.get('LOCALAPPDATA', Path.home()/'.cache'))/'BBMOD/worldmaps'


class MapSolver:
    def __init__(self, components: Components | None = None, cache: Path | None = None):
        self.components = components or Components.locate()
        self.cache = default_cache() if cache is None else Path(cache)

    def solve(self, seed: str, *, use_cache=True, include_camps=False, cancelled: threading.Event | None = None,
              timeout=90, origin='scenario.militia', combat=2, economic=2, budget=2) -> SolveResult:
        seed = validate_seed(seed)
        config_key = campaign_key(origin, combat, economic, budget)
        started = time.perf_counter()
        components = self.components
        fingerprint = components.fingerprint()
        # NTFS filenames are case-insensitive; seed codes are not.
        seed_key = hashlib.sha256(seed.encode('ascii')).hexdigest()
        profile_key = f'campaign-v2-{hashlib.sha256(config_key.encode()).hexdigest()[:20]}' if include_camps else 'map'
        cache_path = self.cache/fingerprint/profile_key/(seed_key+'.json.gz')
        if cancelled is not None and cancelled.is_set():
            raise SolveCancelled()
        if use_cache and cache_path.is_file():
            try:
                value = json.loads(gzip.decompress(cache_path.read_bytes()))
                if value['fingerprint'] == fingerprint and value['map']['seed'] == seed:
                    world = WorldMap.from_dict(value['map'])
                    if include_camps and world.campaign is None:
                        raise ValueError('营地缓存不完整。')
                    if include_camps and campaign_key(world.campaign.origin, world.campaign.combat,
                            world.campaign.economic, world.campaign.budget) != config_key:
                        raise ValueError('营地缓存的开局配置不匹配。')
                    return SolveResult(world, time.perf_counter()-started, 0, True, fingerprint)
            except (OSError, EOFError, ValueError, KeyError, TypeError):
                pass  # A damaged cache is disposable; reconstruct from the seed.
        stage = 'campaign:'+config_key if include_camps else 'complete'
        command = [str(components.binary.resolve()), str(components.rules.resolve()),
                   str(components.bootstrap.resolve()), seed, stage]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=components.rules.parent, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            while True:
                if cancelled is not None and cancelled.is_set():
                    raise SolveCancelled()
                if time.perf_counter()-started > timeout:
                    raise TimeoutError('离线地图解算超时，可重新尝试。')
                try:
                    stdout, stderr = process.communicate(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode:
                raise RuntimeError('地图解算失败：'+stderr.decode('utf-8', errors='replace')[-1500:])
            records = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            if not records:
                raise ValueError('解算器未返回完整地图。')
            value = records[0]
            if value.get('stage') != 'complete' or value.get('seed') != seed:
                raise ValueError('解算器返回了不完整或不匹配的地图。')
            compute_seconds = float(value['seconds'])
            if include_camps:
                campaign = records[-1]
                if campaign.get('kind') != 'offline-camps' or campaign.get('seed') != seed:
                    raise ValueError('解算器未能完成营地与红装生成。')
                value['campaign'] = campaign
                compute_seconds = float(campaign['seconds'])
            world = WorldMap.from_dict(value)
            if include_camps and campaign_key(world.campaign.origin, world.campaign.combat,
                    world.campaign.economic, world.campaign.budget) != config_key:
                raise ValueError('解算器返回了其他开局配置的营地。')
            if cancelled is not None and cancelled.is_set():
                raise SolveCancelled()
            if use_cache:
                payload = json.dumps(dict(fingerprint=fingerprint, map=world.to_dict()),
                                     ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                atomic_write_bytes(cache_path, gzip.compress(payload, mtime=0))
            return SolveResult(world, time.perf_counter()-started, compute_seconds, False, fingerprint)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
