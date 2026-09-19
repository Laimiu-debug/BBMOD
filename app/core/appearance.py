"""Validated desktop typography preferences, independent of game localization."""
from dataclasses import asdict, dataclass

DEFAULT_SIZE = 12
MIN_SIZE = 10
MAX_SIZE = 18
SETTINGS_KEY = 'appearance'


@dataclass(frozen=True)
class Appearance:
    font_family: str = ''  # Empty selects the bundled Chinese font.
    font_size: int = DEFAULT_SIZE  # Points, as used by Qt and Windows font dialogs.

    def to_dict(self):
        return asdict(self)


def normalize_appearance(value) -> Appearance:
    if not isinstance(value, dict):
        return Appearance()
    family = value.get('font_family', '')
    if not isinstance(family, str) or len(family) > 200 or any(ord(c) < 32 for c in family):
        family = ''
    size = value.get('font_size', DEFAULT_SIZE)
    if type(size) is not int:
        size = DEFAULT_SIZE
    return Appearance(family.strip(), min(MAX_SIZE, max(MIN_SIZE, size)))
