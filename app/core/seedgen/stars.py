"""Star bounds use the same attribute order as the brother filter."""
def validate_star_filters(total_min=0, total_max=24, star_ranges=None):
    from .config_emitter import ATTRIBUTES

    if any(type(value) is not int or not 0 <= value <= 24 for value in (total_min, total_max)) or total_min > total_max:
        raise ValueError('总星数范围应在0至24之间，且下限不能大于上限')
    if star_ranges is None:
        star_ranges = {}
    if not isinstance(star_ranges, dict):
        raise ValueError('星位条件必须按属性设置')
    normalized = {}
    for key, bounds in star_ranges.items():
        if key not in ATTRIBUTES or not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError('请选择有效属性和星位范围')
        low, high = bounds
        if any(type(value) is not int or not 0 <= value <= 3 for value in bounds) or low > high:
            raise ValueError('每项属性的星数应在0至3之间，且下限不能大于上限')
        if (low, high) != (0, 3):
            normalized[key] = (low, high)
    minimum = sum(normalized.get(key, (0, 3))[0] for key in ATTRIBUTES)
    maximum = sum(normalized.get(key, (0, 3))[1] for key in ATTRIBUTES)
    if minimum > total_max or maximum < total_min:
        raise ValueError('总星数与星位分配互相矛盾，请调整条件')
    return normalized
