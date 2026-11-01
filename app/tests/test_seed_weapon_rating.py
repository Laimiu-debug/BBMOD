from itertools import combinations
import subprocess

import pytest
from PySide6.QtWidgets import QApplication

from core.paths import resource_path
from core.seedgen.config_emitter import NAMED_ATTRS, SeedGenConfig, render_lair_row, write_configs
from core.seedgen.log_watcher import SeedResult
from core.seedgen.presentation import format_seed, highlights
from core.seedgen.weapon_rating import (
    eligible_affixes, emit_weapon_rating, rate_weapon, rate_weapon_line,
)
from core.seedgen.weapons import WeaponRequirement as W, weapon_filter_condition as rule
from ui.seed_weapon_filter import SeedWeaponFilter


def test_scores_distinguish_affix_usefulness_from_roll_quality():
    best = rate_weapon('weapon.named_javelin', {'RegularDamage': 100, 'DirectDamageAdd': 100})
    low = rate_weapon('weapon.named_javelin', {'RegularDamage': 0, 'DirectDamageAdd': 0})
    other = rate_weapon('weapon.named_javelin', {'AmmoMax': 100, 'FatigueOnSkillUse': 100})
    assert (best.score, best.quality) == (100, 100)
    assert (low.score, low.quality) == (50, 0)
    assert (other.score, other.quality) == (42, 100)
    mixed = rate_weapon('weapon.named_javelin', {'RegularDamage': 75, 'DirectDamageAdd': 100})
    assert (mixed.score, mixed.quality) == (93, 88)
    assert rate_weapon('weapon.named_javelin', {'DirectDamageAdd': 100, 'RegularDamage': 75}) == type(mixed)(93, 88, tuple(reversed(mixed.affixes)))


def test_fatigue_burden_is_reversed_and_skill_saving_is_forward():
    identifier = 'weapon.named_greatsword'
    best = rate_weapon(identifier, {'StaminaModifier': 0, 'FatigueOnSkillUse': 100})
    worst = rate_weapon(identifier, {'StaminaModifier': 100, 'FatigueOnSkillUse': 0})
    assert best.quality == 100 and worst.quality == 0
    assert best.score > worst.score
    assert best.affixes == (('StaminaModifier', 100), ('FatigueOnSkillUse', 100))


@pytest.mark.parametrize('identifier,rolls', [
    ('weapon.unknown', {'RegularDamage': 50, 'DirectDamageAdd': 50}),
    ('armor.named_coat', {'RegularDamage': 50, 'DirectDamageAdd': 50}),
    ('weapon.named_javelin', {}), ('weapon.named_javelin', {'RegularDamage': 50}),
    ('weapon.named_javelin', {'RegularDamage': 50, 'Condition': 50}),
    ('weapon.named_javelin', {'RegularDamage': -1, 'DirectDamageAdd': 50}),
    ('weapon.named_javelin', {'RegularDamage': 101, 'DirectDamageAdd': 50}),
    ('weapon.named_javelin', {'RegularDamage': True, 'DirectDamageAdd': 50}),
    ('weapon.named_javelin', {'RegularDamage': 50.5, 'DirectDamageAdd': 50}),
    ('weapon.named_javelin', {'RegularDamage': 50, 'StaminaModifier': 50}),
])
def test_missing_unknown_or_ineligible_affixes_are_not_scored(identifier, rolls):
    assert rate_weapon(identifier, rolls) is None


@pytest.mark.parametrize('rolls', [
    '', '(RegularDamage:100%)', '(RegularDamage:100%|RegularDamage:100%)',
    '(RegularDamage:100%|DirectDamageAdd:100%|AmmoMax:50%)',
    '(RegularDamage:100%|DirectDamageAdd:100%garbage)',
    '(RegularDamage:NaN%|DirectDamageAdd:100%)',
])
def test_partial_or_ambiguous_log_records_do_not_invent_a_score(rolls):
    assert rate_weapon_line('ItemInfo(RangedWeapon): weapon.named_javelin' + rolls + ' MinDamage:50') is None


def test_old_logs_gain_both_scores_without_modifying_raw_records():
    lines = [
        'ItemInfo(RangedWeapon): weapon.named_javelin(RegularDamage:75%|DirectDamageAdd:100%) MinDamage:40 MaxDamage:60',
        'ItemInfo(TwoHanded): weapon.named_greatsword(StaminaModifier:0%|FatigueOnSkillUse:100%) MinDamage:85',
        'ItemInfo(Armor): armor.named_coat(StaminaModifier:50%|Condition:75%) Armor:250',
        'ItemInfo(OneHanded): weapon.unknown MinDamage:30',
    ]
    record = SeedResult('RATEDWEAPN', 1, lines=lines.copy(), done=True)
    text = format_seed(record)
    assert '红武最高实用93分（roll 88%）' in highlights(record)
    assert '实用词条 93/100；roll 品质 88%' in text
    assert '疲劳品质 100%；技能疲劳品质 100%' in text
    assert '暂不评分' in text
    assert record.lines == lines


def test_complete_affixes_can_be_rated_without_recorded_final_stats():
    record = SeedResult('OLDLOGRATD', 1, done=True, lines=[
        'ItemInfo(RangedWeapon): weapon.named_javelin(RegularDamage:75%|DirectDamageAdd:100%)'])
    assert '实用词条 93/100；roll 品质 88%' in format_seed(record)


@pytest.mark.parametrize('requirements,total,match', [
    ([], 0, 'all'), ([], True, 'all'), ([], 201, 'all'),
    ([W()], 0, 'custom'), ([['weapon', 1]], 0, 'all'), ([W()] * 21, 0, 'all'),
])
def test_invalid_compound_filter_is_rejected(requirements, total, match):
    with pytest.raises(ValueError):
        rule(requirements, total, match)


@pytest.mark.parametrize('key,value', [('score', -1), ('score', 101), ('quality', True), ('quality', 1.5)])
def test_invalid_score_threshold_is_rejected(key, value):
    with pytest.raises(ValueError):
        W(**{key: value})


_HARNESS = r'''
::SeedGenerator <- {};
::include <- function(path) { dofile(path + ".nut"); };
include("seed_generator/config_lair_condition");
include("seed_generator/function_lair_output_check");
local S = ::SeedGenerator;
local LairOutput = S.LairOutput;
S.Const <- {Items={ItemType={Helmet=1,Armor=2,Shield=4,MeleeWeapon=8,TwoHanded=16,OneHanded=32,RangedWeapon=64}}};
S.Math <- {round=function(n){return floor(n+0.5);},rand=function(a,b){throw "scoring must not draw RNG";}};
S.NamedIndexDict <- {};
S.named_total_num <- 0;
S.lair_info_list <- [];
S.logError <- function(e){throw e;};
::cases <- 0;
function item(id, first=0, roll1=100, second=3, roll2=100, flags=64) {
    local index=::SeedGenerator.NamedIndexDict.len();
    ::SeedGenerator.NamedIndexDict[index] <- [first,roll1,0,100,second,roll2,0,100];
    return {m={ID=id,NamedInitIndex=index},Flags=flags,
        isItemType=function(flag){return (this.Flags & flag)!=0;}};
}
function run(rule, items, expected) {
    local S=::SeedGenerator;
    local lair=array(S.LairInfoEntryNum,0);
    local lair2=array(S.LairInfoEntryNum,0);
    lair[S.LairInfoEntry.NamedItemsList]=items.slice(0,items.len()/2);
    lair2[S.LairInfoEntry.NamedItemsList]=items.slice(items.len()/2);
    S.LairOutputConditionArray=[rule]; S.lair_info_list=[lair,lair2]; S.named_total_num=items.len();
    local actual=S.lairOutoutCheck();
    if(actual!=expected) throw "compound case "+::cases+" expected "+expected+" got "+actual;
    ::cases++;
}
function score(id, a, x, b, y, useful, quality) {
    local weapon=item(id,a,x,b,y);
    local actual=::SeedGenerator.rateNamedWeapon(weapon);
    if(actual==null || actual[0]!=useful || actual[1]!=quality)
        throw "score mismatch "+id+" "+a+":"+x+" "+b+":"+y;
    ::cases++;
}
'''


def _run_squirrel(tmp_path, source):
    sq = resource_path('build/full-l10n/tools/bin/sq.exe')
    if not sq.is_file():
        pytest.skip('Offline Squirrel interpreter unavailable')
    write_configs(resource_path('seedgen/payload'), tmp_path, SeedGenConfig())
    script = tmp_path / 'weapon_rating.nut'
    script.write_text(_HARNESS + source + '\nprint("RATING_PASS cases="+::cases+"\\n");\n', encoding='utf-8')
    result = subprocess.run([str(sq), str(script)], cwd=tmp_path, capture_output=True, timeout=25)
    assert result.returncode == 0 and not result.stderr and b'RATING_PASS' in result.stdout, (result.stdout + result.stderr).decode(errors='replace')
    return result.stdout


def test_all_original_affix_pairs_agree_between_native_filter_and_display(tmp_path):
    assert resource_path('seedgen/payload/seed_generator/config_weapon_rating.nut').read_text('utf-8') == emit_weapon_rating()
    cases = []
    for identifier, keys in eligible_affixes().items():
        for first, second in combinations(keys, 2):
            for x, y in [(0, 0), (0, 100), (50, 50), (100, 0), (100, 100), (75, 38)]:
                rating = rate_weapon(identifier, {first: x, second: y})
                cases.append(f'score("{identifier}",{NAMED_ATTRS[first]},{x},{NAMED_ATTRS[second]},{y},{rating.score},{rating.quality});')
    output = _run_squirrel(tmp_path, '\n'.join(cases))
    assert f'cases={len(cases)}'.encode() in output


def test_actual_compound_checker_matches_totals_types_overlap_and_scores(tmp_path):
    source = '''
local j=item("weapon.named_javelin");
local a=item("weapon.named_throwing_axe");
local sword=item("weapon.named_greatsword",0,100,3,100,8|16);
local armor=item("armor.named_coat",0,100,3,100,2);
local d=item("weapon.named_javelin",0,100,6,100);
local p=item("weapon.named_javelin",3,100,6,100);
local weak=item("weapon.named_javelin",0,75,3,100);
local noAffix=item("weapon.named_javelin",6,100,8,100);
local unknown=item("weapon.mod_unknown");
'''
    cases = [
        (rule([W('weapon.named_javelin'), W('weapon.named_throwing_axe')], 3), '[j,a,armor]', 0),
        (rule([W('weapon.named_javelin'), W('weapon.named_throwing_axe')], 4), '[j,a,armor]', -1),
        (rule([W('weapon.named_javelin'), W('weapon.named_throwing_axe')]), '[j,sword]', -1),
        (rule([W('weapon.named_javelin'), W('weapon.named_throwing_axe')], 3, 'any'), '[j,sword,armor]', 0),
        (rule([W('weapon.named_javelin'), W('weapon.named_throwing_axe')], 4, 'any'), '[j,sword,armor]', -1),
        (rule([W('weapon.named_javelin', 2), W('weapon.named_throwing_axe')], match='any'), '[j,sword]', -1),
        (rule([W('weapon.named_javelin', 2), W('weapon.named_throwing_axe')], match='any'), '[j,a]', 0),
        (rule([W('weapon'), W('weapon.named_javelin')]), '[j]', -1),
        (rule([W('weapon'), W('weapon.named_javelin')]), '[j,a]', 0),
        (rule([W('weapon.named_javelin'), W('weapon')]), '[j,a]', 0),
        (rule([W('weapon'), W('range'), W('weapon.named_javelin')]), '[j,a,sword]', 0),
        (rule([W('weapon'), W('range'), W('weapon.named_javelin')]), '[j,a]', -1),
        (rule([W('weapon', 2)]), '[j,armor]', -1),
        (rule([W('two_hand')]), '[sword]', 0),
        (rule([W('one_hand')]), '[sword]', -1),
        (rule([W('range')]), '[sword]', -1),
        (rule([W(damage=75, penetration=75)]), '[d,p]', -1),
        (rule([W(damage=75, penetration=75)]), '[weak]', 0),
        (rule([W(damage=0)]), '[noAffix]', -1),
        (rule([W(damage=0)]), '[item("weapon.named_javelin",0,0,6,0)]', 0),
        (rule([W(damage=100), W(penetration=100)]), '[j]', -1),
        (rule([W(damage=100), W(penetration=100)]), '[j,d]', 0),
        (rule([W(damage=100), W(damage=100, penetration=100)]), '[j,d]', 0),
        (rule([W(score=93, quality=88)]), '[weak]', 0),
        (rule([W(score=94)]), '[weak]', -1),
        (rule([W(quality=89)]), '[weak]', -1),
        (rule([W(damage=100, quality=100)]), '[weak,p]', -1),
        (rule([W(score=0)]), '[unknown]', -1),
        (rule([W()]), '[unknown]', 0),
        (rule([W(quality=0)]), '[item("weapon.named_javelin",0,100,0,100)]', -1),
        (rule([W(quality=0)]), '[item("weapon.named_javelin",0,100,4,100)]', -1),
        (rule([W(score=100, quality=100, count=2)]), '[j,a]', 0),
        (rule([W(count=2), W(count=2)]), '[j,item("weapon.named_javelin"),a,item("weapon.named_throwing_axe")]', 0),
        (rule([W(count=2)]), '[j,j]', -1),
    ]
    for condition, items, expected in cases:
        source += f'run({render_lair_row(condition).rstrip(",")},{items},{expected});\n'
    output = _run_squirrel(tmp_path, source)
    assert f'cases={len(cases)}'.encode() in output


def test_filter_migration_validation_and_limit():
    app = QApplication.instance() or QApplication([])
    class Settings:
        def __init__(self, value): self.value = value
        def get(self, key, default=None): return self.value
        def set(self, key, value): self.value = value
    settings = Settings({'kind': 'weapon', 'weapon': 'weapon.named_javelin', 'count': 2,
                         'total': 30, 'damage': 75, 'penetration': 100})
    widget = SeedWeaponFilter(settings)
    assert widget.conditions() == [rule([W('weapon.named_javelin', 2, 75, 100)])]
    assert not widget.total_enabled.isChecked()
    widget.total_enabled.setChecked(True)
    assert widget.conditions() == [rule([W('weapon.named_javelin', 2, 75, 100)], 30)]
    widget.rows[0].weapon.setEditText('不存在的自定义脚本')
    with pytest.raises(ValueError): widget.conditions()
    widget.weapons_enabled.setChecked(False)
    assert widget.conditions() == [['NamedNumber', 30]]  # Disabled invalid row is ignored.
    widget.total_enabled.setChecked(False)
    with pytest.raises(ValueError, match='至少启用'): widget.conditions()
    widget.total_enabled.setChecked(True)
    widget.weapons_enabled.setChecked(True)
    widget.rows[0].weapon.setCurrentIndex(0)
    for _ in range(25): widget.add_requirement()
    assert len(widget.rows) == 20 and not widget.add.isEnabled()
    assert len(SeedWeaponFilter(settings).rows) == 20
    widget.close()
    app.processEvents()
