"""Bisect a MOD set to find what makes the game misbehave.

Each round enables only part of the suspects (plus the MODs the user keeps on and
everything those need), the player reproduces the problem, and answers whether
it still happens. When neither half fails alone the problem needs one MOD from
each half: the left half stays enabled while the right half is searched, then
the culprit found there stays enabled while the left half is searched.

State is plain JSON in the disabled folder, so a closed app or game crash can
resume the search or restore the original selection.
"""
from __future__ import annotations

import json
import math

from .mod_transactions import atomic_json

BISECT_FILE = 'bisect.json'
SCHEMA = 1


def dependency_map(mods) -> dict[str, set[str]]:
    """file name -> installed file names it needs (declared and framework requirements)."""
    from .modinfo import requirement_target
    owners = {}
    for mod in mods:
        for registration in mod.info.registrations:
            owners.setdefault(registration.mod_id, mod.path.name)
    needs = {}
    for mod in mods:
        info = mod.info
        ids = {requirement_target(r) for r in info.requirements}
        own = {r.mod_id for r in info.registrations}
        if info.api in ('modern', 'mixed'):
            ids.add('mod_modern_hooks')
        if info.api in ('legacy', 'mixed'):
            ids.add('mod_hooks')
        if info.uses_msu:
            ids.add('mod_msu')
        needs[mod.path.name] = {owners[i] for i in ids - own if i in owners} - {mod.path.name}
    return needs


def closure(names, needs) -> set[str]:
    result, pending = set(names), list(names)
    while pending:
        for need in needs.get(pending.pop(), ()):
            if need not in result:
                result.add(need)
                pending.append(need)
    return result


def start(original, pinned, suspects) -> dict:
    pinned = sorted(set(pinned))
    suspects = sorted(set(suspects) - set(pinned), key=str.lower)
    if not suspects:
        raise ValueError('至少保留一个可疑 MOD 参与排查。')
    return {'schema': SCHEMA, 'original': sorted(original), 'pinned': pinned, 'context': [],
            'suspects': suspects, 'stage': 'baseline', 'found': [], 'queue': [], 'round': 1,
            'history': [], 'result': None}


def halves(state):
    suspects = state['suspects']
    middle = len(suspects) // 2
    return suspects[:middle], suspects[middle:]


def tested(state) -> list[str]:
    """The suspects enabled in the current round (before dependencies are added)."""
    left, right = halves(state)
    return {'baseline': [], 'left': left, 'right': right}.get(state['stage'], [])


def test_set(state, needs) -> set[str]:
    base = set(state['pinned']) | set(state['context']) | set(state['found'])
    return closure(base | set(tested(state)), needs)


def rounds_left(state) -> int:
    if state['stage'] == 'done':
        return 0
    def search(count):
        return math.ceil(math.log2(count)) if count > 1 else 0
    pending = search(len(state['suspects'])) + sum(search(len(frame['suspects'])) for frame in state['queue'])
    return pending + (1 if state['stage'] == 'baseline' else 0)


def _settle(state):
    """Collapse finished searches; resume a deferred half or finish."""
    while state['stage'] != 'done' and len(state['suspects']) <= 1:
        state['found'].extend(state['suspects'])
        if state['queue']:
            frame = state['queue'].pop()
            state['context'], state['suspects'] = frame['context'], frame['suspects']
        else:
            state['stage'], state['result'] = 'done', 'found' if state['found'] else 'inconclusive'
            return
    if state['stage'] != 'done':
        state['stage'] = 'left'


def record(state, failed: bool, enabled_count: int = 0) -> dict:
    """Advance with the player's answer for the current round."""
    if state['stage'] == 'done':
        raise ValueError('排查已经结束。')
    state['history'].append({'round': state['round'], 'stage': state['stage'],
                             'tested': tested(state), 'enabled': enabled_count, 'failed': bool(failed)})
    state['round'] += 1
    left, right = halves(state)
    stage = state['stage']
    if stage == 'baseline':
        if failed:
            # Still failing without any suspect: the cause is outside the tested MODs.
            state['stage'], state['result'] = 'done', 'outside'
            return state
        _settle(state)
    elif stage == 'left':
        if failed:
            state['suspects'] = left
            _settle(state)
        else:
            state['stage'] = 'right'
    elif stage == 'right':
        if failed:
            state['suspects'] = right
        else:
            # Neither half fails alone: search the right half with the left half on.
            state['queue'].append({'context': list(state['context']), 'suspects': left})
            state['context'] = state['context'] + left
            state['suspects'] = right
        _settle(state)
    return state


def load(manager) -> dict | None:
    path = manager.disabled_dir / BISECT_FILE
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as error:
        raise ValueError(f'无法读取上次排查记录：{error}') from error
    if not isinstance(state, dict) or state.get('schema') != SCHEMA:
        raise ValueError('上次排查记录格式无法识别。')
    return state


def save(manager, state) -> None:
    manager.disabled_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(manager.disabled_dir / BISECT_FILE, state)


def clear(manager) -> None:
    (manager.disabled_dir / BISECT_FILE).unlink(missing_ok=True)


def apply_round(manager, state) -> int:
    """Enable exactly this round's set; returns how many MODs are enabled."""
    mods = manager.scan()
    wanted = test_set(state, dependency_map(mods))
    # Dependency checks would reject the deliberately partial sets; closure keeps requirements.
    manager.apply_enabled(wanted, validate=False)
    state['enabled'] = sorted(wanted, key=str.lower)
    save(manager, state)
    return len(wanted)


def restore(manager, state) -> tuple[int, int]:
    """Return to the selection from before the search; skips MODs uninstalled since."""
    installed = {mod.path.name for mod in manager.scan(analyze=False)}
    counts = manager.apply_enabled(set(state['original']) & installed, validate=False)
    clear(manager)
    return counts
