"""Chinese atlas labels from BBMOD's reviewed, display-only dictionaries."""
from functools import lru_cache
import json
from pathlib import Path
import re


@lru_cache(maxsize=1)
def compiled_labels():
    from ..paths import resource_path
    path = Path(resource_path('data/worldmap/labels.json'))
    return json.loads(path.read_text('utf-8')) if path.is_file() else None


@lru_cache(maxsize=1)
def term_dictionary():
    if compiled_labels() is not None:
        return compiled_labels()['terms']
    from ..l10n import translated_catalog
    return translated_catalog()


def term_label(source, fallback='未收录译名'):
    if re.search(r'[\u3400-\u9fff]', source):
        return source
    return term_dictionary().get(source, fallback)


@lru_cache(maxsize=1)
def place_dictionary():
    if compiled_labels() is not None:
        return compiled_labels()['places']
    from ..full_l10n import load_full_catalog
    from ..place_display import build_display_data
    from ..place_names import load_policy
    catalog = load_full_catalog()
    return build_display_data(catalog, load_policy(catalog), term_dictionary())[1]


def place_label(name):
    if re.search(r'[\u3400-\u9fff]', name):
        return name
    city = re.fullmatch(r'ORIENTAL CITY\s*#(\d+)', name)
    if city:
        return '南方城邦 ' + city[1]
    return place_dictionary().get(name, term_dictionary().get(name, '未收录地名'))


def town_label(world, index):
    return place_label(world.town_name(index))


BUILDINGS = {
    'alchemist': 'Alchemist', 'arena': 'Arena', 'armorsmith': 'Armorer',
    'armorsmith_oriental': 'Armorer', 'barber': 'Barber',
    'fletcher': 'Fletcher', 'kennel': 'Kennel', 'marketplace': 'Marketplace', 'port': 'Port',
    'tavern': 'Tavern', 'taxidermist': 'Taxidermist', 'taxidermist_oriental': 'Taxidermist',
    'temple': 'Temple', 'training_hall': 'Training Hall', 'weaponsmith': 'Weaponsmith',
    'weaponsmith_oriental': 'Weaponsmith',
}
SUPPLIES = {
    'ammo': 'Ammunition', 'armor_parts': 'Tools and Supplies', 'beer': 'Beer', 'bread': 'Bread',
    'cured_venison': 'Cured Venison', 'dried_fish': 'Dried Fish', 'dried_fruits': 'Dried Fruits',
    'goat_cheese': 'Goat Cheese', 'mead': 'Mead', 'medicine': 'Medical Supplies',
    'pickled_mushrooms': 'Mushrooms', 'roots_and_berries': 'Roots and Berries',
    'smoked_ham': 'Smoked Ham', 'wine': 'Wine',
}


def building_label(identifier):
    return term_label(BUILDINGS.get(identifier.removeprefix('building.'), ''), '其他建筑')


def site_label(site):
    return term_label(site.get('name', ''), '其他设施')


def town_traits(town):
    kind = ('南方城邦' if town.culture == 2 else
            ('军事哨站', '城堡', '要塞')[min(2, max(0, town.size-1))] if town.military else
            ('村庄', '城镇', '大城')[min(2, max(0, town.size-1))])
    traits = [kind]
    if 'building.port' in town.buildings:
        traits.append('港口')
    elif town.coastal:
        traits.append('临海')
    for key in ('arena', 'armorsmith', 'weaponsmith', 'fletcher'):
        if any(b in town.buildings for b in ('building.'+key, 'building.'+key+'_oriental')):
            traits.append(building_label('building.'+key))
    return tuple(traits)
