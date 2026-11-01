"""Native result serialization compatibility and repeated-object reclamation."""
import json
import subprocess

import pytest

from core.seedgen.config_emitter import CampaignConfig, CommonConfig, SeedGenConfig
from core.seedgen.offline import job_source
from core.worldmap.engine import Components


def run_script(components, path, seed='ABCDEFGHIJ', stage='complete'):
    result = subprocess.run([str(components.binary.resolve()), str(components.rules.resolve()),
        str(path.resolve()), str(seed), stage], capture_output=True, timeout=15,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    return [json.loads(line) for line in result.stdout.splitlines()]


@pytest.fixture
def components():
    value = Components.locate()
    if not value.binary.is_file():
        pytest.skip('Independent runtime not built')
    return value


def test_native_json_preserves_legacy_values_and_random_state(components, tmp_path):
    source = components.bootstrap.read_text('utf-8')
    helpers = source[source.index('::jsonQuote <-'):source.index('::include("scripts/config/world")')]
    script = tmp_path/'json.nut'
    script.write_text(helpers + r'''
local values=[null,true,false,0,2147483647,(-2147483647-1),1.23456789,0.00000001234567,
    -0.0,1.0e20,"中文\t引号\"和反斜线\\\n换行\r末行",
    {empty={},list=[null,false,1.23456789],text="中文",control="a\x01b"}];
::_mapSeed("ABCDEFGHIJ");local before=::_mapDraws();
foreach(value in values)print("["+::jsonEncode(value)+","+::_mapJSONEncode(value)+"]\n");
print("["+before+","+::_mapDraws()+"]\n");
''', encoding='utf-8')
    for old, new in run_script(components, script):
        assert new == old


def test_background_construction_does_not_leave_a_cycle_per_instance(components, tmp_path):
    cfg = SeedGenConfig(common=CommonConfig.preset('bro_only'), campaign=CampaignConfig(origin='scenario.militia'))
    job = tmp_path/'job.nut'
    job.write_text(job_source(cfg, components, count=1) + '''
for(local i=0;i<20;i++)::new("scripts/skills/backgrounds/farmhand_background");
::collectgarbage();
for(local i=0;i<200;i++)::new("scripts/skills/backgrounds/farmhand_background");
print(::_mapJSONEncode({kind="binding-gc",unreachable=::collectgarbage()})+"\\n");
''', encoding='utf-8')
    rows = run_script(components, components.bootstrap, str(job.resolve()), 'brothers')
    row = next(row for row in rows if row.get('kind') == 'binding-gc')
    assert row['unreachable'] == 0
