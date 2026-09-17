import json
from pathlib import Path
import subprocess

import pytest

from core.paths import resource_path
from core.seedgen.config_emitter import (
    CommonConfig, OriginConfig, SeedGenConfig, attribute_condition, brother_condition,
    emit_role_conditions, render_bro_row,
)
from core.seedgen.log_watcher import SeedResult
from core.seedgen.presentation import brothers, format_seed
from core.seedgen.traits import traits, validate_traits


def test_catalog_uses_reviewed_names_and_real_trait_identifiers():
    choices = traits()
    assert len(choices) == 58
    assert choices['trait.iron_lungs'].name == '铁肺'
    assert choices['trait.huge'].name == '高大'
    assert 'trait.tiny' in choices['trait.huge'].incompatible
    catalog = json.loads(resource_path('localization/full_catalog.json').read_text(encoding='utf-8'))
    translations = {entry['source']:entry['translation'] for entry in catalog['entries'].values()}
    assert all(choice.name == translations[choice.english] for choice in choices.values())


def test_trait_validation_blocks_conflicts_and_invalid_ids():
    with pytest.raises(ValueError, match='同时要求'):
        validate_traits(['trait.huge'], ['trait.huge'])
    with pytest.raises(ValueError, match='不能同时具备'):
        validate_traits(['trait.huge', 'trait.tiny'], [])
    assert validate_traits(['trait.huge', 'trait.tiny'], [], 'any')[0] == ['trait.huge', 'trait.tiny']
    with pytest.raises(ValueError, match='不支持'):
        validate_traits(['trait.fake"], print(1)'], [])
    assert validate_traits(['trait.iron_lungs']*2, [])[0] == ['trait.iron_lungs']
    with pytest.raises(ValueError):
        brother_condition(0, {}, ['trait.huge'])
    with pytest.raises(ValueError):
        brother_condition(1, {'MeleeSkill':-10}, ['trait.huge'])


def test_trait_only_and_attribute_rules_are_emitted_as_one_condition():
    condition = brother_condition(2, {'MeleeSkill':90}, ['trait.iron_lungs'], ['trait.clumsy'])
    line = render_bro_row(condition)
    assert line == '[BroOutput.BrotherFilter, 2, [-100, -100, -100, 90, -100, -100, -100, -100], ["trait.iron_lungs"], ["trait.clumsy"], true],'
    assert brother_condition(1, {'MeleeSkill':90}).type == 'RoleAttr'
    assert brother_condition(1, {}, [], ['trait.asthmatic']).type == 'BrotherFilter'
    cfg = SeedGenConfig(origins={'scenario.militia':OriginConfig(conditions=[condition])})
    template = resource_path('seedgen/payload/seed_generator/config_role_condition.nut').read_text(encoding='utf-8')
    generated = emit_role_conditions(template, cfg)
    assert line in generated
    assert generated.split('BroOutputConditionArray["scenario.lone_wolf"]')[1] == template.split('BroOutputConditionArray["scenario.lone_wolf"]')[1]


def test_brother_only_mode_actually_runs_the_brother_checker():
    cfg = CommonConfig.preset('bro_only')
    assert cfg.GenerateBrotherMode and not cfg.GenerateSettlementMode
    assert not cfg.MatchingBrotherGenerateSettlement and not cfg.PrintLairInfo
    map_cfg = CommonConfig.preset('map_only')
    assert map_cfg.GenerateSettlementMode and not map_cfg.GenerateBrotherMode


def test_result_details_keep_traits_attached_to_the_right_brother():
    result = SeedResult('TESTSEED01', 1, lines=[
        'Trait: orphan',
        'CharInfo: 0 Melee:0.9 MeleeSkill:60(90)3',
        'Trait: trait.iron_lungs trait.huge trait.iron_lungs',
        'CharInfo: 1 Guard:0.7 MeleeSkill:50(75)1',
        'Trait: trait.clumsy trait.unknown_mod_trait',
    ])
    assert brothers(result)[0].traits == ['trait.iron_lungs', 'trait.huge']
    assert brothers(result)[1].traits == ['trait.clumsy', 'trait.unknown_mod_trait']
    text = format_seed(result)
    assert '特质：铁肺、高大' in text
    assert '特质：笨拙、trait.unknown_mod_trait' in text


def test_actual_squirrel_checker_matches_distinct_brothers(tmp_path):
    sq = resource_path('build/full-l10n/tools/bin/sq.exe')
    if not sq.is_file():
        pytest.skip('Offline Squirrel interpreter is not installed')
    payload = resource_path('seedgen/payload')
    def row(condition):
        return render_bro_row(condition).rstrip(',')
    combined = row(brother_condition(1, {'MeleeSkill':90, 'MeleeDefense':25}, ['trait.huge','trait.iron_lungs'], ['trait.clumsy']))
    any_two = row(brother_condition(2, {}, ['trait.huge','trait.iron_lungs'], [], 'any'))
    only = row(brother_condition(1, {}, ['trait.iron_lungs']))
    exclude = row(brother_condition(1, {}, [], ['trait.asthmatic']))
    attr = row(attribute_condition(1, {'MeleeSkill':90}))
    harness = '''
::SeedGenerator <- {};
::include <- function(path) { dofile(path + ".nut"); };
include("seed_generator/define_common");
include("seed_generator/config_role_condition");
include("seed_generator/function_brother_output_check");
local S = ::SeedGenerator;
local BroOutput = S.BroOutput;
local world = { m = { CampaignSettings = { StartingScenario = { getID = function() { return "scenario.militia"; } } } } };
local count = 0;
function bro(attack, defense, held) {
    local value = array(7, 0);
    value[5] = [70, 40, 100, attack, 40, defense, 10, 100];
    value[6] = held;
    return value;
}
function run(rule, people, wanted) {
    ::SeedGenerator.BroOutputConditionArray["scenario.militia"] = [rule];
    assert(::SeedGenerator.broOutputCheck(world, [], people, 0) == wanted);
    count++;
}
'''
    harness += f'''
local combined = {combined};
local anyTwo = {any_two};
local only = {only};
local exclude = {exclude};
local attribute = {attr};
local both = ["trait.huge", "trait.iron_lungs"];
run(combined, [bro(90,25,both)], 0);
run(combined, [bro(89,25,both)], -1);
run(combined, [bro(90,24,both)], -1);
run(combined, [bro(95,30,[]),bro(60,10,both)], -1);
run(combined, [bro(95,30,["trait.huge"]),bro(95,30,["trait.iron_lungs"])], -1);
run(combined, [bro(95,30,["trait.huge","trait.iron_lungs","trait.clumsy"])], -1);
run(combined, [bro(95,30,["trait.clumsy"]),bro(95,30,both)], 0);
run(anyTwo, [bro(60,0,both)], -1);
run(anyTwo, [bro(60,0,["trait.huge"]),bro(60,0,["trait.iron_lungs"])], 0);
run(anyTwo, [bro(60,0,["trait.huge"]),bro(60,0,[])], -1);
run(only, [bro(0,-10,["trait.iron_lungs"])], 0);
run(only, [bro(100,50,[])], -1);
run(exclude, [bro(60,0,["trait.asthmatic"])], -1);
run(exclude, [bro(60,0,[])], 0);
run(exclude, [], -1);
run(attribute, [bro(90,0,[])], 0);
assert(count == 16);
print("BBMOD_SEED_TRAITS_PASS cases="+count+"\\n");
'''
    script = tmp_path/'check-traits.nut'
    script.write_text(harness, encoding='utf-8')
    result = subprocess.run([str(sq), str(script)], cwd=payload, capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stderr and b'BBMOD_SEED_TRAITS_PASS cases=16' in result.stdout, (result.stdout+result.stderr).decode(errors='replace')
