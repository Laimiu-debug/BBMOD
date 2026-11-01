"""Benchmark matched-result delivery, Qt and SQLite with isolated temporary profiles.

An optional baseline directory contains worldmap.exe, runtime.nut, brothers.nut,
camps.nut, library.py and seed_poll_worker.py. Rules are shared and unchanged.
Memory measurement additionally uses psutil. No game is launched or user history
opened; the Qt page stays offscreen.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import statistics
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtWidgets import QApplication
from core.seedgen.config_emitter import (BroCondition, CampaignConfig, CommonConfig,
    OriginConfig, SeedGenConfig, brother_condition)
from core.seedgen.offline import OfflineSeedSearch, fingerprint
from core.seedgen.orchestrator import StopLimits
from core.settings import Settings
from core.worldmap.engine import Components
import ui.seedgen_page as page_module


def config(origin, kind, count):
    condition = (brother_condition(1, {}, total_min=9,
        required=['trait.iron_lungs', 'trait.sure_footing'], star_ranges={'MeleeSkill': (3, 3)})
        if kind == 'rare' else BroCondition('TeamScore', [-100]))
    cfg = SeedGenConfig(common=CommonConfig.preset('bro_only'), campaign=CampaignConfig(origin=origin),
        origins={origin: OriginConfig(conditions=[condition])})
    rng = random.Random(20261022)
    cfg.common.debug_seeds = [''.join(rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=10)) for _ in range(count)]
    return cfg


def digest(records):
    value = hashlib.sha256()
    for record in records:
        value.update(json.dumps(asdict(record), ensure_ascii=True, sort_keys=True,
            separators=(',', ':')).encode('utf-8') + b'\n')
    return value.hexdigest()


def core(cfg):
    search = OfflineSeedSearch()
    search.prepare(cfg)
    started = time.perf_counter()
    try:
        search.launch()
        while not search.stop_reason:
            added, _ = search.poll()
            if time.perf_counter()-started > 180:
                raise TimeoutError('Core search')
            if not added:
                time.sleep(.001)
    finally:
        search.stop_and_restore()
    elapsed = time.perf_counter()-started
    if search.script_error:
        raise RuntimeError(search.script_error)
    return dict(seconds=elapsed, seeds=search.progress.loop_idx, hits=len(search.results),
        seeds_per_second=search.progress.loop_idx/elapsed, result_sha256=digest(search.results))


def desktop(cfg, app):
    temporary_root = Path('H:/codex/tmp') if Path('H:/codex').is_dir() else None
    with tempfile.TemporaryDirectory(prefix='bbmod-brother-bench-', dir=temporary_root) as folder:
        settings = Settings.__new__(Settings)
        settings.path, settings.data = Path(folder)/'settings.json', {}
        context = SimpleNamespace(game=None, settings=settings,
            data_changed=SimpleNamespace(emit=lambda: None), set_seedgen_active=lambda value: None)
        page = page_module.SeedGenPage(context)
        page.origin_combo.setCurrentIndex(page.origin_combo.findData(cfg.campaign.origin))
        page._current_config = lambda: cfg
        page._limits = StopLimits()
        batches = []
        save = page.library.save_many

        def save_many(values):
            values = list(values)
            batches.append(len(values))
            return save(values)

        page.library.save_many = save_many
        try:
            started = time.perf_counter()
            page.start()
            search = page.orch
            if search is None:
                raise RuntimeError('Search failed to launch')
            while page.orch is not None:
                app.processEvents()
                if time.perf_counter()-started > 180:
                    raise TimeoutError('Desktop search')
                time.sleep(.001)
            elapsed = time.perf_counter()-started
            if search.script_error:
                raise RuntimeError(search.script_error)
            assert page.library.all() == page.results == search.results
            assert page.table.rowCount() <= page_module.LIBRARY_PAGE_SIZE
            return dict(seconds=elapsed, seeds=search.progress.loop_idx, hits=len(search.results),
                seeds_per_second=search.progress.loop_idx/elapsed, result_sha256=digest(page.results),
                saved=len(page.results), save_batches=len(batches),
                median_live_batch=statistics.median(batches[:-1]) if len(batches) > 1 else 0)
        finally:
            if page.orch is not None:
                page.stop()
            page.close()
            page.deleteLater()
            app.processEvents()


def memory(cfg):
    import psutil
    search = OfflineSeedSearch()
    search.prepare(cfg)
    checkpoints = []
    started = time.perf_counter()
    try:
        search.launch()
        child = psutil.Process(search._process.pid)
        checkpoint = 500
        while not search.stop_reason:
            search.poll()
            if search.progress.loop_idx >= checkpoint and child.is_running():
                try:
                    info = child.memory_info()
                    record = dict(loops=search.progress.loop_idx, seconds=time.perf_counter()-started,
                        rss=info.rss, private=getattr(info, 'private', info.rss))
                    if record['loops'] < len(cfg.common.debug_seeds):
                        checkpoints.append(record)
                        print(json.dumps(dict(kind='memory-progress', **record)), flush=True)
                    checkpoint += 500
                except psutil.NoSuchProcess:
                    pass
            if time.perf_counter()-started > 180:
                raise TimeoutError('Memory search')
            time.sleep(.01)
    finally:
        search.stop_and_restore()
    if search.script_error:
        raise RuntimeError(search.script_error)
    assert not search.results
    return dict(seeds=search.progress.loop_idx, seconds=time.perf_counter()-started, checkpoints=checkpoints)


def load_class(name, path, class_name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', default='scenario.lone_wolf')
    parser.add_argument('--count', type=int, default=10000)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--memory', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.count < 100 or not 1 <= args.repeats <= 10:
        parser.error('At least 100 seeds and 1..10 repeats required')
    current = Components.locate()
    variants = {'after': (current, page_module.SeedLibrary, page_module.SeedPollWorker)}
    if args.baseline:
        folder = args.baseline.resolve()
        variants = {'before': (Components(folder/'worldmap.exe', folder/'runtime.nut', current.rules),
            load_class('core.seedgen._benchmark_old_library', folder/'library.py', 'SeedLibrary'),
            load_class('_benchmark_old_worker', folder/'seed_poll_worker.py', 'SeedPollWorker')), **variants}
    app = QApplication.instance() or QApplication([])
    cases = []
    fingerprints = {name: fingerprint(values[0]) for name, values in variants.items()}
    for trial in range(1 if args.memory else args.repeats):
        for kind in ('rare',) if args.memory else ('rare', 'all'):
            cfg = config(args.origin, kind, args.count)
            if args.memory:
                cfg.origins[args.origin].conditions = [BroCondition('TeamScore', [100])]
            for name in list(variants)[::1 if trial % 2 == 0 else -1]:
                components, library, worker = variants[name]
                with ExitStack() as stack:
                    stack.enter_context(patch.object(Components, 'locate', return_value=components))
                    stack.enter_context(patch.object(page_module, 'SeedLibrary', library))
                    stack.enter_context(patch.object(page_module, 'SeedPollWorker', worker))
                    for path in ('memory',) if args.memory else ('core', 'desktop'):
                        result = memory(cfg) if args.memory else core(cfg) if path == 'core' else desktop(cfg, app)
                        case = dict(variant=name, trial=trial, origin=args.origin, condition=kind, path=path, **result)
                        cases.append(case)
                        print(json.dumps({k: v for k, v in case.items() if k != 'checkpoints'}), flush=True)
    summaries = []
    if not args.memory:
        for path in ('core', 'desktop'):
            for kind in ('rare', 'all'):
                group = [c for c in cases if c['path'] == path and c['condition'] == kind]
                assert len({c['result_sha256'] for c in group}) == 1, 'Result changed between runs or variants'
                summaries.append(dict(path=path, condition=kind,
                    median_seeds_per_second={name: statistics.median(c['seeds_per_second']
                        for c in group if c['variant'] == name) for name in variants}))
    report = dict(schema=1, fingerprints=fingerprints, cases=cases, summaries=summaries,
        database_round_trip_matches=None if args.memory else True,
        game_launched=False, user_database_modified=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(output=str(args.output), summaries=summaries)), flush=True)


if __name__ == '__main__':
    main()
