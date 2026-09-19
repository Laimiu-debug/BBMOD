"""Compare the Python analyzer with original Squirrel randomizers offline.

The real engine supplies Math.round; this offline check explicitly assumes the
nearest-integer convention floor(x + 0.5). It is not in-game acceptance.
"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.item_inspector import appraise, catalog, MARKER


def literal(value):
    if isinstance(value, dict): return '{' + ','.join('[' + json.dumps(k) + ']=' + literal(v) for k,v in value.items()) + '}'
    if isinstance(value, list): return '[' + ','.join(map(literal, value)) + ']'
    return json.dumps(value, ensure_ascii=False)


def body(path):
    text = path.read_text('utf8'); start = text.index('{', text.index('function randomizeValues'))
    level = 0
    for end in range(start, len(text)):
        level += (text[end] == '{') - (text[end] == '}')
        if level == 0: return text[start:end+1]
    raise ValueError(path)


def main():
    items = catalog()
    output = ROOT / 'build/review/inspector-rules'; output.mkdir(parents=True, exist_ok=True)
    functions = {}
    for folder, kind, name in [('weapons','weapon','named_weapon'),('armor','armor','named_armor'),
                              ('helmets','helmet','named_helmet'),('shields','shield','named_shield')]:
        functions[kind] = body(ROOT / f'build/full-l10n/decompiled/scripts/items/{folder}/named/{name}.nut')
    text = '''::mods_hookNewObject <- function(path,callback) {};
::logInfo <- function(text) { print(text+"\\n"); };
::logWarning <- function(text) { throw text; };
::Const <- {Items={ItemType={Named=1,RangedWeapon=2}}};
::Math <- {rand=function(a,b) { return a+(::rand() % (b-a+1)); },
    round=function(v) { return ::floor(v+0.5); },floor=function(v) { return ::floor(v); },
    min=function(a,b) { return a<b?a:b; }};
dofile(vargv[0]);
local randomizers = {FUNCTIONS};
local items = ITEMS;
foreach(id,spec in items) {
    for(local i=0;i<100;i++) {
        local item={m=clone spec["base"],Math=::Math,Const=::Const,ranged=spec.ranged,
            isItemType=function(t) {return t==1 || this.ranged;}};
        item.m.Condition <- item.m.ConditionMax;
        item.m.Ammo <- item.m.AmmoMax;
        item.m.ID <- id;item.m.Name <- spec.en;
        randomizers[spec.kind].call(item);
        ::BBMODItemInspector.read(item);
        ::BBMODItemInspector.emit(",\\\"kind\\\":\\\"item\\\",\\\"token\\\":1" + ::BBMODItemInspector.Snapshot);
    }
}
'''.replace('FUNCTIONS', ','.join(kind + '=function() ' + code for kind,code in functions.items())).replace('ITEMS', literal(items))
    script = output / 'original-rules.nut'; script.write_text(text, encoding='utf8')
    process = subprocess.run([str(ROOT / 'build/full-l10n/tools/bin/sq.exe'), str(script),
        str(ROOT / 'data/item_inspector/bridge.nut')], capture_output=True, timeout=40)
    (output / 'squirrel.log').write_bytes(process.stdout + process.stderr)
    assert not process.returncode and not process.stderr, process.stderr.decode(errors='replace')
    events = [json.loads(row.split(MARKER,1)[1]) for row in process.stdout.decode('utf8').splitlines() if MARKER in row]
    invalid = []
    for event in events:
        result = appraise(event, items)
        if not result.get('valid'): invalid.append({'event':event,'result':result})
    report = {'count':len(events),'types':len({x['id'] for x in events}), 'invalid':invalid,
              'engine_api':'stubbed; original game randomizers executed in offline Squirrel'}
    (output / 'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({**report,'invalid':len(invalid)},ensure_ascii=False))
    assert len(events) == 9400 and not invalid


if __name__ == '__main__': main()
