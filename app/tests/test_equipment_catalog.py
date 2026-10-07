import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTextBrowser

from core.equipment_catalog import attributes, detail_html, load_equipment, load_equipment_icons, matches
from core.item_inspector import catalog, rolls_for, HoverLog, MARKER
from ui.equipment_catalog import EquipmentCatalog
from ui.inspector_page import InspectorPage

ROOT = Path(__file__).resolve().parents[1]


def by_id(identifier):
    return next(item for item in load_equipment()['items'].values() if item['id'] == identifier)


@pytest.fixture(scope='module')
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(qt_app):
    widget = EquipmentCatalog()
    yield widget
    if widget._dialog is not None: widget._dialog.close()
    widget.close()
    widget.deleteLater()
    qt_app.processEvents()


def test_equipment_facts_and_named_catalog_provenance():
    data = load_equipment()
    assert data['game_version'] == '1.5.2.3'
    assert data['named_catalog_sha256'] == hashlib.sha256((ROOT / 'data/item_inspector/catalog.json').read_bytes()).hexdigest()
    named = {item['id']: item for item in data['items'].values() if item['rarity'] == 'named'}
    assert len(named) == len(catalog()) == 94
    for identifier, item in catalog().items():
        assert all(named[identifier]['base'][key] == value for key, value in item['base'].items())
    sword = attributes(by_id('weapon.greatsword'))
    assert [row.display for row in sword[:5]] == ['85–100', '100%', '25%', '72', '-12']
    armor = attributes(by_id('armor.body.noble_mail'))
    assert [row.display for row in armor[:5]] == ['—', '—', '—', '160', '-15']
    shield = attributes(by_id('shield.kite_shield'))
    assert [row.display for row in shield[3:7]] == ['48', '-16', '15', '25']
    assert by_id('weapon.lightbringer_sword')['rarity'] == 'legendary'


def test_named_ranges_are_actual_shared_rolls_not_a_simulated_item():
    for item in load_equipment()['items'].values():
        if item['rarity'] != 'named': continue
        rows = attributes(item)
        for roll in rolls_for(item):
            expected = (roll.format(tuple(min(x[i] for x in roll.options) for i in range(len(roll.keys))))
                        + ' ～ ' + roll.format(tuple(max(x[i] for x in roll.options) for i in range(len(roll.keys)))))
            assert any(row.display == expected and row.rule != '固定基础值' for row in rows)
    sword = by_id('weapon.named_greatsword')
    penetration = attributes(sword)[2]
    assert penetration.baseline == '25%' and penetration.display == '33% ～ 41%'
    assert penetration.sort_key == pytest.approx((.33, .41))
    html = detail_html(sword, '1.5.2.3')
    assert '随机抽取两组强化词条' in html and '未抽中保留基础值' in html
    assert '&lt;unsafe&gt;' in detail_html({**sword, 'zh': '<unsafe>'}, '1.5.2.3')


def type_search(page, text):
    rows = page.table.rowCount()
    page.search.setText(text)
    assert page.table.rowCount() == rows and page._search_timer.isActive()
    for _ in range(100):
        if not page._search_timer.isActive():
            return
        QTest.qWait(20)
    pytest.fail('search debounce did not fire')


def test_bilingual_search_filters_and_zero_results(page):
    total = page.table.rowCount()
    assert total > 94
    type_search(page, 'GreatSWORD')
    assert page.table.rowCount() >= 2
    english_ids = {page.items[page.table.item(row, 0).data(Qt.UserRole)]['id']
                   for row in range(page.table.rowCount())}
    assert {'weapon.greatsword', 'weapon.named_greatsword'} <= english_ids
    type_search(page, '巨剑')
    assert page.table.rowCount() >= 2
    page.rarity.setCurrentIndex(page.rarity.findData('named'))
    shown = {page.items[page.table.item(row, 0).data(Qt.UserRole)]['id']:
             (page.table.item(row, 0).text(), page.table.item(row, 2).text())
             for row in range(page.table.rowCount())}
    assert shown['weapon.named_greatsword'] == ('巨剑', '红装')
    page.group.setCurrentIndex(page.group.findData('shield'))
    assert not page.table.rowCount() and not page.detail_button.isEnabled()
    assert '没有匹配' in page.count.text() and page.selected_key() is None
    page.reset_filters()
    assert page.table.rowCount() == total and page.detail_button.isEnabled()
    assert matches(by_id('weapon.named_greatsword'), '红装 greatsword', 'two_handed', 'named')


def test_named_types_keep_real_colors_and_correct_script_identity():
    expected = {
        'armor.head.gold_and_black_turban': '黑金缠头盔',
        'armor.head.golden_feathers': '金羽盔',
        'armor.head.red_and_gold_band_helmet': '红金饰带盔',
        'shield.named_red_white': '红白盾',
        'weapon.named_orc_axe': '裂颅斧',
        'weapon.named_orc_cleaver': '断头斩刀',
        'weapon.named_goblin_heavy_bow': '强化荒野短弓',
        'weapon.named_goblin_pike': '锯齿长枪',
        'weapon.named_two_handed_mace': '双手钉锤',
        'weapon.named_two_handed_spiked_mace': '双手尖刺钉锤',
    }
    for identifier, name in expected.items():
        assert catalog()[identifier]['zh'] == by_id(identifier)['zh'] == name
    assert not matches(by_id('armor.head.gold_and_black_turban'), '金羽盔')
    assert not matches(by_id('armor.head.golden_feathers'), '黑金缠头盔')


def test_game_name_search_finds_all_matching_types_without_renaming_them(page):
    type_search(page, '夜幕披衣')
    shown = {page.items[page.table.item(row, 0).data(Qt.UserRole)]['id']:
             page.table.item(row, 0).text() for row in range(page.table.rowCount())}
    # The same name component can legitimately be rolled by multiple types.
    assert shown == {'armor.body.black_leather': '黑色皮甲',
                     'armor.body.named_noble_mail_armor': '贵族锁甲'}
    assert matches(by_id('armor.body.named_noble_mail_armor'), 'Nightcloak')
    assert matches(by_id('weapon.named_greatsword'), '红巨剑')
    assert not matches(by_id('weapon.greatsword'), '红巨剑')
    html = detail_html(by_id('armor.body.named_noble_mail_armor'), '1.5.2.3')
    assert '游戏名称示例' in html and '夜幕披衣' in html and '可由玩家改名' in html


def test_naming_refresh_uses_ids_and_keeps_numeric_facts(tmp_path):
    from copy import deepcopy
    from tools.equipment_names import naming_fields, naming_sources, refresh_named_names
    from tools.build_equipment_catalog import refresh_names
    names, terms, translation_hash, naming_hash = naming_sources()
    item_data = json.loads((ROOT / 'data/item_inspector/catalog.json').read_text('utf-8'))
    before = deepcopy(item_data)
    # Reversing the naming registry must never swap turban and feathered types.
    reverse = dict(reversed(list(names.items())))
    for identifier, expected in [('armor.head.gold_and_black_turban', '黑金缠头盔'),
                                 ('armor.head.golden_feathers', '金羽盔')]:
        source = item_data['items'][identifier]['source']
        assert naming_fields(identifier, source, reverse, terms)['zh'] == expected
    with pytest.raises(ValueError, match='source changed'):
        naming_fields('armor.head.gold_and_black_turban',
                      names['armor.head.golden_feathers']['source'], names, terms)
    assert refresh_named_names(item_data) == before
    assert before['translation_sha256'] == translation_hash
    assert before['naming_sha256'] == naming_hash
    for record in item_data['items'].values():
        assert record['name_mode'] == 'random'
        assert all(name['zh'] == terms[name['en']] for name in record['name_pool'])
    equipment = load_equipment()
    assert refresh_names(deepcopy(equipment)) == equipment


def test_numeric_sort_keeps_row_identity_and_detail_after_filter(page):
    page.group.setCurrentIndex(page.group.findData('armor'))
    assert page.table.isColumnHidden(3) and page.table.isColumnHidden(8)
    page.table.sortItems(6, Qt.DescendingOrder)
    keys = [page.table.item(row, 6).sort_key for row in range(page.table.rowCount())]
    assert keys == sorted(keys, reverse=True)
    page.table.selectRow(3)
    selected = page.selected_key()
    page.refresh()
    assert page.selected_key() == selected
    page.show_detail()
    assert page.items[selected]['zh'] in page._dialog.findChild(QTextBrowser).toPlainText()
    page._dialog.close()
    assert page.show_item('weapon.named_greatsword')
    assert not page.table.isColumnHidden(3) and page.items[page.selected_key()]['id'] == 'weapon.named_greatsword'


def test_catalog_opens_without_game_and_hover_never_replaces_browsing(qt_app, tmp_path, monkeypatch):
    class Context(QObject):
        game_changed = Signal()
        management_changed = Signal(bool)
        session_changed = Signal(bool)
        data_changed = Signal()
        game = None
        management_busy = False
        seedgen_active = False
        settings = SimpleNamespace(get=lambda *args: {}, set=lambda *args: None)
    monkeypatch.setattr('ui.inspector_page.find_log_write_paths', lambda: [])
    page = InspectorPage(Context(), register_hotkey=False)
    try:
        page.show(); qt_app.processEvents()
        assert page.sections.currentIndex() == 0 and page.catalog_page.table.rowCount() > 94
        assert not page.install.isEnabled()
        page.catalog_page.search.setText('盾'); page.catalog_page.refresh()
        selection = page.catalog_page.selected_key()
        path = tmp_path / 'log.html'; path.write_text('', encoding='utf-8')
        reader = HoverLog(path); reader.poll(); page.readers = [reader]
        record = {'schema': 1, 'seq': 1, 'kind': 'item', 'token': 1, 'id': 'weapon.named_greatsword',
                  'name': '测试装备', 'named': True, 'attachment': False,
                  'stats': {**catalog()['weapon.named_greatsword']['base'], 'RegularDamage': 102,
                            'RegularDamageMax': 120, 'DirectDamageAdd': .16, 'ConditionMax': 100}}
        path.write_text(MARKER + json.dumps(record), encoding='utf-8'); page.poll()
        assert page.latest['valid'] and page.browse_button.isEnabled()
        assert page.sections.currentIndex() == 0 and page.catalog_page.selected_key() == selection
        assert page.catalog_page.search.text() == '盾'
        page.sections.setCurrentIndex(1); page.browse_button.click()
        assert page.sections.currentIndex() == 0
        assert page.catalog_page.items[page.catalog_page.selected_key()]['id'] == record['id']
        with path.open('a', encoding='utf-8') as stream:
            stream.write(MARKER + json.dumps({**record, 'seq': 2, 'name': '漏读的红装', 'stats': {}}))
        page.poll()
        assert page.latest is None and not page.browse_button.isEnabled()
        assert '字段不完整' in page.age.text()
        assert '漏读的红装' in page.result.toPlainText() and '测试装备' not in page.result.toPlainText()
        path.write_text('new log session', encoding='utf-8'); page.poll()
        assert page.latest is None and not page.browse_button.isEnabled()
    finally:
        page.shutdown(); page.close(); page.deleteLater(); qt_app.processEvents()


def test_catalog_rebuild_reproduces_bundled_facts(tmp_path):
    source = ROOT / 'build/full-l10n/decompiled'
    if not source.is_dir(): pytest.skip('original local script input not available')
    from tools.build_equipment_catalog import build
    result = build(source, tmp_path / 'catalog.json')
    assert result == load_equipment()


def test_original_equipment_icons_cover_named_and_lootable_equipment():
    from PIL import Image
    document = load_equipment_icons()
    items = load_equipment()['items']
    assert set(document['items']) == set(items)
    assert document['catalog_sha256'] == hashlib.sha256((ROOT / 'data/equipment_catalog.json').read_bytes()).hexdigest()
    for key, item in items.items():
        artwork = document['items'][key]
        if item['rarity'] != 'special':
            assert artwork['small'] and artwork['large'], key
        elif not artwork['small']:
            assert not item['loot'] and artwork['reason']
    for name, metadata in document['files'].items():
        path = ROOT / 'assets/equipment' / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata['sha256']
        with Image.open(path) as picture:
            assert list(picture.size) == metadata['size'] and picture.getbbox()
    for source, expected in {
        'scripts/items/weapons/greatsword.nut': 'weapons/melee/sword_two_hand_02_70x70.png',
        'scripts/items/weapons/named/named_greatsword.nut': 'weapons/melee/sword_two_hand_01_named_01_70x70.png',
        'scripts/items/helmets/oriental/nomad_head_wrap.nut': 'helmets/inventory_helmet_southern_16.png',
    }.items():
        artwork = document['items'][source]
        assert document['files'][artwork['small']]['source'] == 'gfx/ui/items/' + expected


def test_table_and_detail_render_equipment_artwork(page, qt_app):
    page.show(); qt_app.processEvents()
    assert page.show_item('weapon.named_greatsword')
    key = page.selected_key()
    cell = page.table.item(page.table.currentRow(), 0)
    assert not cell.icon().isNull() and not cell.icon().pixmap(40, 40).isNull()
    assert page.table.rowHeight(page.table.currentRow()) >= page.table.iconSize().height() + 8
    page.show_detail()
    assert page.artwork[key]['large'] in page._dialog.findChild(QTextBrowser).toHtml()
    page._dialog.close()
    assert page.show_item('weapon.barbarian_drum')
    assert '未提供' in page.table.item(page.table.currentRow(), 0).toolTip()
