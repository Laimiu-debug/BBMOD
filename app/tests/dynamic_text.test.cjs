// Test the shipped UI assets, including text split by the game's BBCode markup.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('../build/browser-check/node_modules/jsdom');
const assets = path.resolve(process.argv[2]);
const dom = new JSDOM(`<body>
<div id="switch">Switch to 小刀</div>
<div id="hint">Quickly switch to another item from your bag.</div>
<div id="cost">Costs <b><span style="color:#ff0000">4</span></b> AP to switch.</div>
<div id="split">Switch to <b>Knife</b></div>
<div id="dialogue">你在<span>Weissenwacht</span>遇见<b>阿德勒 议员</b>，他代表<b>家族 格里蒙德</b>。</div>
<div id="vizier">你遇见<b>Jamil Ibn Sahr the Vizier of War</b>。</div>
<input id="name" value="Adler the Councilman">
<div contenteditable="true">阿德勒 议员</div>
<div data-bbmod-translate="off">House Grimmund</div>
</body>`, {runScripts:'outside-only'});
const w = dom.window;
for (const file of ['dictionary.js','place_names.js','name_forms.js','runtime.js']) {
    w.eval(fs.readFileSync(path.join(assets,file),'utf8'));
}
w.BBMODL10N.start();
const t = w.BBMODL10N.translate, doc = w.document;
assert.equal(doc.querySelector('#switch').textContent,'换用小刀');
assert.equal(doc.querySelector('#hint').textContent,'快速换用背包中的另一件装备。');
assert.equal(doc.querySelector('#cost').textContent,'花费 4 点行动点（切换装备）。');
assert.equal(doc.querySelector('#cost b span').textContent,'4');
assert.equal(doc.querySelector('#cost b span').style.color,'rgb(255, 0, 0)');
assert.equal(doc.querySelector('#split').textContent,'换用 小刀');
assert.equal(doc.querySelector('#dialogue').textContent,'你在魏森哨堡遇见议员阿德勒，他代表格里蒙德家族。');
assert.equal(doc.querySelector('#name').value,'Adler the Councilman');
assert.equal(doc.querySelector('[contenteditable]').textContent,'阿德勒 议员');
assert.equal(doc.querySelector('[data-bbmod-translate]').textContent,'House Grimmund');
assert.equal(t('Switch to Knife'),'换用小刀');
assert.equal(t('Switch to Dagger'),'换用匕首');
assert.equal(t('Switch to Hunting Bow'),'换用猎弓');
assert.equal(t('Switch to 自定义装备'),'换用自定义装备');
assert.equal(t('Costs 4 AP to switch.'),'切换装备消耗 4 行动点。');
assert.equal(t('s'),'s');
assert.equal(t('items.weapons.knife'),'items.weapons.knife');
assert.equal(t('player_House Grimmund_id'),'player_House Grimmund_id');
assert.equal(t('UnknownName the Councilman'),'UnknownName the Councilman');
assert.equal(t('my_Adler the Councilman_id'),'my_Adler the Councilman_id');
assert.equal(t('UnknownName Ibn Sahr the Vizier of War'),'UnknownName Ibn Sahr the Vizier of War');
assert.equal(t('Jamil UnknownFamily the Vizier of War'),'Jamil UnknownFamily the Vizier of War');
assert.equal(t('my_Jamil Ibn Sahr the Vizier of War_id'),'my_Jamil Ibn Sahr the Vizier of War_id');
let checked = 0;
for (const [source,target] of Object.entries(w.BBMOD_NAME_FORMS)) {
    assert.equal(t(source),target,source);
    assert.equal(t('你遇见「'+source+'」。'),'你遇见「'+target+'」。',source);
    assert.equal(t(target),target,'idempotent: '+source);
    checked++;
}
// Cover every name/title combination without shipping a large cross product.
const parts = w.BBMOD_SOUTHERN_NAME_PARTS;
let southernChecked = 0;
for (const [given,givenZh] of Object.entries(parts.given)) {
    for (const [family,familyZh] of Object.entries(parts.family)) {
        for (const [title,titleZh] of Object.entries(parts.titles)) {
            const source = given+' '+family+' '+title;
            const target = titleZh+givenZh+'·'+familyZh;
            assert.equal(t(source),target,source);
            assert.equal(t('你遇见「'+source+'」。'),'你遇见「'+target+'」。',source);
            assert.equal(t(target),target,'idempotent: '+source);
            southernChecked++;
        }
    }
}
assert.equal(doc.querySelector('#vizier').textContent,
    '你遇见'+parts.titles['the Vizier of War']+parts.given.Jamil+'·'+parts.family['Ibn Sahr']+'。');
doc.querySelector('#switch').firstChild.nodeValue = 'Switch to Dagger';
setTimeout(() => {
    assert.equal(doc.querySelector('#switch').textContent,'换用匕首');
    console.log(JSON.stringify({name_forms:checked,southern_name_forms:southernChecked,quick_swap:'passed',split_markup:'passed',
        dynamic_updates:'passed',saved_names_and_inputs:'unchanged',game_started:false}));
    dom.window.close();
},30);
