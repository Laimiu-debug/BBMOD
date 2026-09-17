"""Validated starting-trait choices shared by filters and result presentation."""
from dataclasses import dataclass
from functools import lru_cache
import json

from ..paths import resource_path

@dataclass(frozen=True)
class Trait:
    id: str
    name: str
    english: str
    description: str
    incompatible: tuple[str, ...]

@lru_cache(maxsize=1)
def traits() -> dict[str, Trait]:
    data = json.loads(resource_path('data/seed_traits.json').read_text(encoding='utf-8'))
    return {row['id']: Trait(**{**row, 'incompatible':tuple(row['incompatible'])}) for row in data['traits']}

def trait_name(trait_id: str) -> str:
    item = traits().get(trait_id)
    return item.name if item else trait_id

def validate_traits(required, excluded, match='all') -> tuple[list[str], list[str]]:
    available = traits()
    if match not in ('all', 'any'):
        raise ValueError('请选择特质的全部或任意匹配方式')
    if any(not isinstance(items, (list, tuple)) for items in (required, excluded)):
        raise ValueError('特质条件必须是列表')
    if any(not isinstance(value, str) or value not in available for value in (*required, *excluded)):
        raise ValueError('特质条件包含不支持的开局特质')
    required, excluded = list(dict.fromkeys(required)), list(dict.fromkeys(excluded))
    if set(required) & set(excluded):
        raise ValueError('同一个特质不能同时要求具备和排除')
    if match == 'all':
        for index, first in enumerate(required):
            for second in required[index+1:]:
                if second in available[first].incompatible or first in available[second].incompatible:
                    raise ValueError(f'「{trait_name(first)}」与「{trait_name(second)}」不能同时具备，请改为任意匹配或调整选择')
    return required, excluded
