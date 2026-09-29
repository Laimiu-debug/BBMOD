"""Conservative checks for explicit numeric dependency comparisons."""
from decimal import Decimal
import re
from .modinfo import requirement_target

_VERSION = r'\d+(?:\.\d+)*(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?'


def _semantic(value):
    core, _, pre = value.partition('-')
    parts = tuple(map(int, core.split('.')))
    # Preserve the existing conservative handling of abbreviated prereleases.
    if pre and len(parts) != 3:
        return None
    parts += (0,) * max(0, 3 - len(parts))
    labels = tuple((0, int(p)) if p.isdigit() else (1, p) for p in pre.split('.')) if pre else ()
    return parts, not bool(pre), labels


def satisfies(requirement, version, api='modern'):
    """True/False for supported comparisons, None when the syntax is unknown."""
    target = requirement_target(requirement)
    expression = requirement[len(target):].strip().strip('()').strip()
    if not expression:
        return True
    if not re.fullmatch(_VERSION, version):
        return None
    parts = re.findall(r'(>=|<=|==|!=|>|<|=)\s*(' + _VERSION + ')', expression)
    remainder = re.sub(r'(>=|<=|==|!=|>|<|=)\s*' + _VERSION, '', expression)
    if not parts or remainder.strip(' ,&'):
        return None
    for operator, wanted in parts:
        if api == 'legacy':
            if version.count('.') > 1 or wanted.count('.') > 1 or '-' in version + wanted:
                return None
            actual, required = Decimal(version), Decimal(wanted)
        else:
            actual, required = _semantic(version), _semantic(wanted)
            if actual is None or required is None:
                return None
        if not {'>=': actual >= required, '<=': actual <= required, '>': actual > required,
                '<': actual < required, '=': actual == required, '==': actual == required,
                '!=': actual != required}[operator]:
            return False
    return True
