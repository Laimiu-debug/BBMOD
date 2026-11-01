"""Independent roster and campaign searches without an installed-game session."""
from __future__ import annotations

import atexit
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import queue
import secrets
import string
import subprocess
import tempfile
import threading
import time
import weakref

from ..worldmap.engine import Components
from ..worldmap.model import OFFICIAL_ORIGINS, validate_seed
from .config_emitter import (SeedGenConfig, emit_campaign, emit_common,
                             emit_role_conditions, emit_map_conditions, emit_lair_conditions)
from .log_watcher import Progress, SeedResult, StartupStatus

ORIGINS = OFFICIAL_ORIGINS
FAST_ORIGINS = ORIGINS - {'scenario.deserters'}

_ACTIVE = weakref.WeakSet()


@atexit.register
def _close_processes():
    for process in list(_ACTIVE):
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def fingerprint(components=None):
    components = components or Components.locate()
    digest = hashlib.sha256(components.fingerprint().encode('ascii'))
    for path in (components.bootstrap.with_name('brothers.nut'), components.rules/'brothers.nut',
                 components.bootstrap.with_name('search.nut'), components.rules/'search.nut',
                 components.rules/'search-manifest.json', components.rules/'config_map_condition.nut',
                 components.rules/'config_lair_condition.nut',
                 components.rules/'brothers-manifest.json', components.rules/'config_role_condition.nut'):
        if not path.is_file():
            raise FileNotFoundError('缺少独立解算组件，请更新或重新安装 BBMOD。')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def supports(cfg: SeedGenConfig) -> bool:
    return cfg.campaign.origin in ORIGINS


def fast_supports(cfg: SeedGenConfig) -> bool:
    common = cfg.common
    return (cfg.campaign.origin in FAST_ORIGINS and common.FastBrotherGenerateMode and common.GenerateBrotherMode
            and not common.GenerateSettlementMode
            and not common.MatchingBrotherGenerateSettlement and not common.PrintLairInfo)


def job_source(cfg, components, *, hits=0, seconds=0, count=0, seeds=(), return_all=False, prefilter=False):
    cfg.campaign.validate()
    if not supports(cfg):
        raise ValueError('独立解算支持全部官方起源；自制起源请使用游戏解算。')
    seeds = [validate_seed(seed) for seed in seeds]
    template = (components.rules/'config_role_condition.nut').read_text('utf-8')
    parts = [emit_common(cfg.common), emit_campaign(cfg.campaign), emit_role_conditions(template, cfg)]
    if not fast_supports(cfg):
        for name, emit in (('map', emit_map_conditions), ('lair', emit_lair_conditions)):
            parts.append(emit((components.rules/f'config_{name}_condition.nut').read_text('utf-8'), cfg))
    source = '\n'.join('{\n'+'\n'.join(line for line in part.splitlines()
        if not line.strip().startswith('::include('))+'\n}' for part in parts)
    job = dict(seed=''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(10)),
               seeds=seeds, hits=hits, seconds=seconds, count=count, return_all=return_all, prefilter=prefilter)
    # JSON table syntax differs from Squirrel. Only the fixed, validated keys are emitted.
    fields = ','.join(key+'='+json.dumps(value, ensure_ascii=True) for key, value in job.items())
    return source+'\n::SeedGenerator.OfflineJob <- {'+fields+'};\n'


class OfflineSeedSearch:
    independent = True
    log_path = None

    def __init__(self, *, limits=None, components=None, seeds=(), count=0, return_all=False, prefilter=True):
        self.components = components or Components.locate()
        self.limits = limits
        self.seeds = list(seeds)
        self.count = count
        self.return_all = return_all
        self.prefilter = prefilter
        self.prefilter_rejected = 0
        self.campaign_candidates = 0
        self.results = []
        self.records = []
        self.progress = Progress(phase='brothers')
        self.startup = StartupStatus()
        self.stop_reason = ''
        self.script_error = ''
        self._process = None
        self._temporary = None
        self._queue = queue.Queue(maxsize=128)
        self._reader = None
        self._errors = None
        self._stderr = ''
        self._started = None
        self._last_activity = time.monotonic()
        self._cfg = None
        self._finished = False
        self._stopping = False
        self._cancelled = threading.Event()
        self._process_lock = threading.Lock()
        self._campaign_mode = False

    @property
    def elapsed_seconds(self):
        return int(time.monotonic()-self._started) if self._started else 0

    @property
    def silent_seconds(self):
        return int(time.monotonic()-self._last_activity)

    @property
    def seeds_per_second(self):
        elapsed = time.monotonic()-self._started if self._started else 0
        return self.progress.loop_idx/elapsed if elapsed > 0 else 0

    def prepare(self, cfg):
        # Checking the component never discovers or touches an installed game.
        fingerprint(self.components)
        self._cfg = cfg
        self._campaign_mode = not fast_supports(cfg)
        hits = self.limits.hits if self.limits else 0
        seconds = self.limits.minutes*60 if self.limits else 0
        source = job_source(cfg, self.components, hits=hits, seconds=seconds,
            count=self.count, seeds=self.seeds or cfg.common.debug_seeds, return_all=self.return_all)
        temporary_root = Path('H:/codex/tmp') if Path('H:/codex').is_dir() else None
        if temporary_root:
            temporary_root.mkdir(parents=True, exist_ok=True)
        self._temporary = tempfile.TemporaryDirectory(prefix='bbmod-search-', dir=temporary_root)
        self._job = Path(self._temporary.name)/'job.nut'
        self._job.write_text(source, encoding='utf-8')
        return []

    def launch(self):
        if self._cfg is None or self._process is not None:
            raise RuntimeError('独立解算会话尚未准备好，或已经启动。')
        c = self.components
        self._started = time.monotonic()
        if self._campaign_mode:
            self._reader = threading.Thread(target=self._campaign_search, name='bbmod-campaign-search', daemon=True)
            self._reader.start()
            return True
        self._process = subprocess.Popen([str(c.binary.resolve()), str(c.rules.resolve()),
            str(c.bootstrap.resolve()), str(self._job.resolve()), 'brothers'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
            cwd=c.rules.parent, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        _ACTIVE.add(self._process)
        self._reader = threading.Thread(target=self._read, name='bbmod-brothers-output', daemon=True)
        self._errors = threading.Thread(target=self._read_errors, name='bbmod-brothers-errors', daemon=True)
        self._reader.start()
        self._errors.start()
        return True

    def _deadline_reached(self):
        return bool(self.limits and self.limits.minutes
                    and time.monotonic()-self._started >= self.limits.minutes*60)

    def _campaign_job(self, source, stage, loops, hits, best):
        """Run one bounded probe batch or one isolated full campaign."""
        c = self.components
        self._job.write_text(source, encoding='utf-8')
        with self._process_lock:
            if self._cancelled.is_set() or self._deadline_reached():
                return
            process = subprocess.Popen([str(c.binary.resolve()), str(c.rules.resolve()),
                str(c.bootstrap.resolve()), str(self._job.resolve()), stage],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                cwd=c.rules.parent, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self._process = process
            _ACTIVE.add(process)
        timeout = 90.0
        if self.limits and self.limits.minutes:
            timeout = min(timeout, max(.01, self.limits.minutes*60-(time.monotonic()-self._started)))

        def expire():
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass

        watchdog = threading.Timer(timeout, expire)
        watchdog.daemon = True
        watchdog.start()
        self._stderr = ''
        self._errors = threading.Thread(target=self._read_errors, name='bbmod-campaign-errors', daemon=True)
        self._errors.start()
        try:
            for line in process.stdout:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record['kind'] in ('candidate', 'prefilter'):
                    yield record
                elif record['kind'] == 'phase':
                    self._queue.put(dict(kind='progress', loops=loops, hits=hits, best=best,
                        seconds=time.monotonic()-self._started, phase=record['phase']))
            process.wait()
            self._errors.join()
            if process.returncode and not self._cancelled.is_set() and not self._deadline_reached():
                raise RuntimeError(self._stderr or '独立开局解算失败。')
        finally:
            watchdog.cancel()
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            self._errors.join(timeout=5)
            _ACTIVE.discard(process)
            with self._process_lock:
                self._process = None

    def _campaign_search(self):
        """Reject characters in small fast batches before generating any maps."""
        loops = hits = 0
        best = -100.0
        cfg, c = self._cfg, self.components
        seeds = self.seeds or cfg.common.debug_seeds
        alphabet = string.ascii_uppercase + (string.ascii_lowercase if cfg.common.EnableLowercaseSeed else '')
        probe_cfg = None
        if (self.prefilter and not self.return_all and cfg.campaign.origin in FAST_ORIGINS
                and cfg.common.GenerateBrotherMode and cfg.common.FastBrotherGenerateMode):
            probe_cfg = replace(cfg, common=replace(cfg.common, GenerateSettlementMode=False,
                MatchingBrotherGenerateSettlement=False, PrintLairInfo=False))

        def progress(phase='brothers'):
            self._queue.put(dict(kind='progress', loops=loops, hits=hits, best=best,
                                 seconds=time.monotonic()-self._started, phase=phase))

        try:
            self._queue.put(dict(kind='ready'))
            while not self._cancelled.is_set() and not self._deadline_reached():
                size = 64 if probe_cfg else 1
                if seeds:
                    size = min(size, len(seeds)-loops)
                if self.count:
                    size = min(size, self.count-loops)
                if size <= 0:
                    break
                batch = seeds[loops:loops+size] if seeds else [
                    ''.join(secrets.choice(alphabet) for _ in range(10)) for _ in range(size)]
                if probe_cfg:
                    progress()
                    probes = list(self._campaign_job(job_source(probe_cfg, c, seeds=batch,
                        prefilter=True), 'brothers', loops, hits, best))
                    if (len(probes) != len(batch) and not self._cancelled.is_set()
                            and not self._deadline_reached()):
                        raise RuntimeError('人物预筛未返回完整的候选种子。')
                    if any(probe['seed'] != seed for probe, seed in zip(probes, batch)):
                        raise RuntimeError('人物预筛返回了不一致的种子顺序。')
                else:
                    probes = [dict(seed=batch[0], match=0)]
                for probe in probes:
                    if self._cancelled.is_set() or self._deadline_reached():
                        break
                    if probe['match'] < 0:
                        loops += 1
                        self.prefilter_rejected += 1
                        best = max(best, probe['score'])
                        continue
                    self.campaign_candidates += 1
                    progress('map')
                    records = list(self._campaign_job(job_source(cfg, c, seeds=[probe['seed']],
                        return_all=self.return_all), 'search', loops, hits, best))
                    if not records:
                        if self._cancelled.is_set() or self._deadline_reached():
                            break
                        raise RuntimeError('解算器未返回完整的种子结果。')
                    if len(records) != 1 or records[0]['seed'] != probe['seed']:
                        raise RuntimeError('独立开局返回了不一致的种子结果。')
                    candidate = records[0]
                    loops += 1
                    hits += candidate['match'] >= 0
                    best = max(best, candidate['score'])
                    candidate.update(kind='result', loop=loops)
                    if candidate['match'] >= 0 or self.return_all:
                        self._queue.put(candidate)
                    progress('map')
                    if self.limits and self.limits.hits and hits >= self.limits.hits:
                        break
                progress()
                if self.limits and self.limits.hits and hits >= self.limits.hits:
                    break
            if not self._cancelled.is_set():
                self._queue.put(dict(kind='done', loops=loops, hits=hits, best=best,
                                     seconds=time.monotonic()-self._started, phase='brothers' if probe_cfg else 'map'))
        except Exception as exc:
            if not self._cancelled.is_set():
                self._queue.put(dict(kind='error', detail=str(exc)))

    def _read(self):
        try:
            for line in self._process.stdout:
                if line.strip():
                    self._queue.put(json.loads(line))
        except Exception as exc:
            self._queue.put(dict(kind='error', detail=str(exc)))
        finally:
            self._process.stdout.close()

    def _read_errors(self):
        try:
            for line in iter(lambda: self._process.stderr.read(1024), b''):
                self._stderr = (self._stderr+line.decode('utf-8', errors='replace'))[-5000:]
        finally:
            self._process.stderr.close()

    def _consume(self, record, added):
        kind = record['kind']
        self._last_activity = time.monotonic()
        if kind == 'ready':
            self.startup = StartupStatus('generating', '独立解算器已就绪')
        elif kind in ('progress', 'done'):
            self.progress = Progress(record['loops'], record['hits'], str(record['best']), phase=record.get('phase', 'brothers'))
            if kind == 'done':
                self._finished = True
                self.stop_reason = ('已达到命中数量' if self.limits and self.limits.hits
                    and record['hits'] >= self.limits.hits else '已达到运行时限' if self.limits
                    and self.limits.minutes and record['seconds'] >= self.limits.minutes*60
                    else '指定种子已解算完成')
        elif kind == 'result':
            if self.return_all:
                self.records.append(record)
            self.progress.loop_idx = max(self.progress.loop_idx, record['loop'])
            if record['match'] < 0:
                return
            cfg = self._cfg.campaign
            result = SeedResult(seed=validate_seed(record['seed']), loop_idx=record['loop'],
                bro_output_type=record.get('bro_match', record['match']), map_output_type=record.get('map_match', -1),
                lair_output_type=record.get('lair_match', -1), lines=[line.strip() for line in record['lines']],
                done=True, origin=cfg.origin,
                combat_difficulty=cfg.combat_difficulty, economic_difficulty=cfg.economic_difficulty,
                budget_difficulty=cfg.budget_difficulty, game_version='1.5.2.3', dlc_mask=342)
            self.results.append(result)
            added.append(result)
        elif kind == 'error':
            self.script_error = record['detail']
            self.startup = StartupStatus('error', self.script_error)
            self.stop_reason = '独立解算失败，已保留已完成结果'

    def poll(self):
        added = []
        for _ in range(128):
            try:
                record = self._queue.get_nowait()
            except queue.Empty:
                break
            self._consume(record, added)
        p = self._process
        if not self._campaign_mode and p is not None and p.poll() is not None and not self._reader.is_alive() and self._queue.empty():
            if self._errors:
                self._errors.join(timeout=.1)
            if not self._stopping and (p.returncode or not self._finished):
                self.script_error = self.script_error or self._stderr or '解算器未能完成搜索。'
                self.startup = StartupStatus('error', self.script_error)
                self.stop_reason = '独立解算失败，已保留已完成结果'
        return added, []

    def stop_and_restore(self):
        # Interface shared with game searches; the independent path has no game files to restore.
        self._stopping = True
        with self._process_lock:
            self._cancelled.set()
            p = self._process
        if p is not None:
            if p.poll() is None:
                p.kill()
            # Drain while joining: the bounded queue must not lose completed records or deadlock.
            while self._reader and self._reader.is_alive():
                self.poll()
                self._reader.join(timeout=.01)
            self.poll()
            p.wait(timeout=5)
            if self._errors:
                self._errors.join(timeout=5)
            _ACTIVE.discard(p)
            self._process = None
        # The batch thread may not have spawned its first process yet.
        while self._campaign_mode and self._reader and self._reader.is_alive():
            self.poll()
            self._reader.join(timeout=.01)
        self.poll()
        self._process = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
        return 0
