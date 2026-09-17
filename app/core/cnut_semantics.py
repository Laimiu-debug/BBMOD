"""Keep Squirrel keys, comparisons and resource arguments out of translations.

The VM stores a property name and its displayed value in the same literal pool.
An unchanged instruction stream alone therefore does not prove a safe patch.
Opcode operand meanings follow the upstream squirrel/sqvm.cpp implementation.
"""
from collections import deque


INTERNAL_ARGUMENTS = {
    'hasFlag', 'getFlag', 'setFlag', 'removeFlag', 'set', 'has', 'get', 'remove',
    'rawset', 'rawget', 'rawdelete', 'rawin', 'addSprite', 'getSprite', 'hasSprite',
    'setBrush', 'setSound', 'setMusic', 'load', 'include', 'inherit', 'setID',
    'setAchievement', 'unlockAchievement', 'setScenario', 'find', 'setScreen',
    'setState', 'getState', 'getScreen', 'hasState', 'increment', 'getAsInt', 'isKindOf',
    'registerConnection', 'notifyBackend', 'asyncCall', 'trigger', 'on', 'off',
    'logInfo', 'logWarning', 'logError', 'logDebug', 'updateAchievement',
    'setString', 'getString', 'setInt', 'getInt', 'setBool', 'getBool',
    'addLabel', 'getLabel', 'spawnAttackEffect',
}

# Contract/event callbacks return the next screen's ID. Some IDs (Overview,
# Success, etc.) also appear as visible titles in the very same literal pool.
INTERNAL_RETURNS = {'getResult', 'getID', 'getType', 'getState', 'onDetermineStartScreen'}
INTERNAL_FIELDS = {'ID', 'id', 'Type', 'type'}


def protected_literals(function: dict) -> set[int]:
    """Trace literal origins through registers and both sides of branches.

If a pooled string has even one program use, preserve the entire literal.
Its display occurrences can still be translated by the UI text adapter.
"""
    instructions = function['instructions']
    literals = function['literals']
    protected = set()
    if not instructions:
        return protected
    states = {0: {}}
    pending = deque([0])
    queued = {0}
    empty = frozenset()

    def literal(index):
        return frozenset([index]) if 0 <= index < len(literals) and isinstance(literals[index], str) else empty

    while pending:
        pc = pending.popleft()
        queued.discard(pc)
        incoming = states[pc]
        state = incoming.copy()
        a1, op, a0, a2, a3 = instructions[pc]
        origin = lambda reg: incoming.get(reg, empty)

        def assign(reg, values=empty):
            if reg == 255:
                return
            if values:
                state[reg] = values
            else:
                state.pop(reg, None)

        if op in (0x08, 0x09):  # PREPCALLK / GETK: immediate property key
            protected.update(literal(a1))
        if op == 0x07:  # PREPCALL: key held in a register
            protected.update(origin(a1))
        if op in (0x0B, 0x0C, 0x0D, 0x0E, 0x23, 0x24, 0x26, 0x29, 0x3A):
            protected.update(origin(a2))
        if op in (0x0B, 0x0D):  # NEWSLOT / SET: value under an internal field
            if {literals[index] for index in origin(a2)} & INTERNAL_FIELDS:
                protected.update(origin(a3))
        if op == 0x17 and a0 != 255 and function['name'] in INTERNAL_RETURNS:
            protected.update(origin(a1))  # RETURN's value register is arg1
        if op in (0x0F, 0x10):  # comparisons may implement IDs and state switches
            protected.update(literal(a1) if a3 else origin(a1))
            protected.update(origin(a2))
        if op in (0x05, 0x06):
            methods = {literals[index] for index in origin(a1)}
            if methods & INTERNAL_ARGUMENTS and a3 > 1:
                protected.update(origin(a2 + 1))

        if op == 0x01:
            assign(a0, literal(a1))
        elif op == 0x04:
            assign(a0, literal(a1)); assign(a2, literal(a3))
        elif op == 0x0A:
            assign(a0, origin(a1))
        elif op == 0x1B:
            assign(a0, origin(a1)); assign(a2, origin(a3))
        elif op in (0x07, 0x08):
            assign(a0, literal(a1) if op == 0x08 else origin(a1))
            assign(a3, origin(a2))
        elif op in (0x0B, 0x0D):
            assign(a0, origin(a3))
        elif op == 0x11:  # concatenation can construct a key or resource name
            assign(a0, origin(a1) | origin(a2))
        elif op in (0x2B, 0x2C):
            assign(a0, origin(a0) | origin(a2))
        elif op == 0x1F:
            assign(a0, origin(a2))
        elif op == 0x18:
            for reg in range(a0, a0 + a1): assign(reg)
        elif op == 0x33:
            for reg in range(a2, a2 + 3): assign(reg)
        elif op in (0x25, 0x27):
            assign(a1)
            if op == 0x27: assign(a0)
        elif op not in (0x00, 0x17, 0x1C, 0x1D, 0x1E, 0x22, 0x31, 0x34, 0x37, 0x38, 0x39, 0x3A, 0x3C):
            assign(a0)

        successors = [pc + 1]
        if op in (0x17, 0x39): successors = []
        elif op == 0x1C: successors = [pc + 1 + a1]
        elif op in (0x1D, 0x1E, 0x2B, 0x2C, 0x33, 0x37):
            successors.append(pc + 1 + a1)
            if op == 0x33: successors.append(pc + 2)
        elif op == 0x34: successors.append(pc + a1)
        for nxt in successors:
            if not 0 <= nxt < len(instructions): continue
            previous = states.get(nxt)
            if previous is None:
                states[nxt] = state.copy()
                changed = True
            else:
                changed = False
                for reg, values in state.items():
                    merged = previous.get(reg, empty) | values
                    if merged != previous.get(reg, empty):
                        previous[reg] = merged
                        changed = True
            if changed and nxt not in queued:
                pending.append(nxt); queued.add(nxt)
    return protected
