// Render sentences produced by check_person_place_l10n.py through shipped UI assets.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('../build/browser-check/node_modules/jsdom');
const assets = path.resolve(process.argv[2]);
const input = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const dom = new JSDOM('<body><div id="sentences"></div></body>', {runScripts: 'outside-only'});
const w = dom.window;
for (const name of ['dictionary.js', 'place_names.js', 'name_forms.js', 'runtime.js']) {
    w.eval(fs.readFileSync(path.join(assets, name), 'utf8'));
}
const output = [];
for (const row of input.cases) {
    let expected;
    if (row.package_before_ui === '循着盗贼的足迹，夺回货物') {
        expected = row.package_before_ui;
    } else {
        const person = row.id.startsWith('city_state.') ? '阿尔哈齐夫的贾米尔·伊本·萨赫尔' : '索默斯塔德的埃德蒙';
        const days = row.id.includes('.days1.') ? '一天' : '3 天';
        expected = '将货物送给' + person + '，沿路向西行进约' + days;
    }
    const element = w.document.createElement('div');
    element.textContent = row.package_before_ui;
    w.document.querySelector('#sentences').appendChild(element);
    w.BBMODL10N.walk(element);
    assert.equal(element.textContent, expected, row.id);
    w.BBMODL10N.walk(element);
    assert.equal(element.textContent, expected, 'second render: ' + row.id);
    output.push({id: row.id, before: row.package_before_ui, displayed: element.textContent});
}
const dialogueOutput = [];
for (const row of input.dialogue_cases) {
    const city = row.id.startsWith('city_state.');
    const expectedName = city ? '阿尔哈齐夫的贾米尔·伊本·萨赫尔' : '索默斯塔德的埃德蒙';
    const place = city ? '阿尔哈齐夫' : '索默斯塔德';
    const variables = input.cases.find(item => item.id.startsWith(city ? 'city_state.days1.' : 'settlement.days1.')).package_variables;
    const before = row.package_variables_applied;
    const displayed = w.BBMODL10N.translate(before);
    const mentions = before.split(variables.recipient).length - 1;
    assert.ok(mentions > 0, row.id);
    assert.equal(displayed.split(expectedName).length - 1, mentions, row.id);
    assert.ok(!displayed.includes(place + '的' + place + '的'), row.id);
    assert.ok(!displayed.includes(variables.recipient), row.id);
    assert.deepEqual(displayed.match(/%[A-Za-z_]+%/g), before.match(/%[A-Za-z_]+%/g), row.id);
    assert.equal(w.BBMODL10N.translate(displayed), displayed, 'second render: ' + row.id);
    dialogueOutput.push({id: row.id, recipient_mentions: mentions, displayed,
        branch_selection: 'not executed; all supplied branches checked'});
}
const report = {status: 'passed', package_sha256: input.package_sha256,
    actual_bytecode_sentences_rendered: output.length, game_started: false, cases: output, dialogue_cases: dialogueOutput};
if (process.argv[4]) { fs.writeFileSync(process.argv[4], JSON.stringify(report, null, 2) + '\n'); }
console.log(JSON.stringify({status: report.status, actual_bytecode_sentences_rendered: output.length,
    dialogue_templates: dialogueOutput.length, game_started: false}));
dom.window.close();
