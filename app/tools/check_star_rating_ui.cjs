// Execute the user's unchanged recruit UI with jQuery and a minimal engine bridge.
// This exercises callbacks and DOM updates; it never starts Battle Brothers.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const {JSDOM} = require('../build/browser-check/node_modules/jsdom');
const work = process.argv[2];
const enabled = process.argv[3] !== 'vanilla';
const original = path.resolve(__dirname, '../build/full-l10n/original/ui');
const dom = new JSDOM('<!doctype html><html><body></body></html>', {runScripts: 'outside-only'});
const w = dom.window;
w.eval(fs.readFileSync(path.join(original, 'extern/jquery-2.1.4.min.js'), 'utf8'));
const $ = w.jQuery;
$.fn.createDialog = function(title) { return $('<div><h1></h1><section></section><footer></footer></div>').appendTo(this).find('h1').text(title).end(); };
for (const name of ['findDialogTabContainer','findDialogContentContainer','findDialogFooterContainer','findListScrollContainer']) $.fn[name] = function() { return this; };
$.fn.createList = function() { return $('<div/>').appendTo(this); };
$.fn.createImage = function() { return $('<img/>').appendTo(this); };
$.fn.createTextButton = function(title, cb) { return $('<button/>').text(title).on('click', cb).appendTo(this); };
for (const name of ['bindTooltip','centerImageWithinParent','shakeLeftRight']) $.fn[name] = function() { return this; };
$.fn.enableButton = function(value) { return this.prop('disabled', !value); };
w.WorldTownScreenAssets = function() { this.createDIV = function() {}; this.getValues = () => ({Money: 5000}); };
w.Path = {GFX: 'gfx/', PROCEDURAL: 'procedural/'};
w.Asset = {ICON_ASSET_MONEY: 'money.png', ICON_ASSET_DAILY_MONEY: 'daily.png', ICON_UNKNOWN_TRAITS: 'unknown.png'};
w.TooltipIdentifier = {Assets: {}, CharacterBackgrounds: {}, ElementOwner: {HireScreen: 'hire'}, WorldTownScreen: {HireDialogModule: {}}};
w.Helper = {numberWithCommas: String};
w.XBBCODE = {process: o => ({html: o.text.replace(/\[img\](.*?)\[\/img\]/g, '<img src="$1">').replace(/\[\/?color[^\]]*\]/g, '')})};
const calls = [];
w.SQ = {call: (handle, method, id) => calls.push([handle, method, id])};
vm.runInContext(fs.readFileSync(path.join(work, enabled ? 'world_town_screen_hire_dialog_module.js' : 'original_hire.js'), 'utf8'), dom.getInternalVMContext());
w.eval(fs.readFileSync(path.join(work, 'dictionary.js'), 'utf8'));
w.eval(fs.readFileSync(path.join(work, 'runtime.js'), 'utf8'));
const moduleUI = new w.WorldTownScreenHireDialogModule({});
moduleUI.onConnection('hire-screen');
moduleUI.createDIV($(w.document.body));
const data = {ID: 42, Name: '阿尔内', InitialMoneyCost: 4510, TryoutCost: 476, DailyMoneyCost: 34,
  ImagePath: 'brother.png', BackgroundImagePath: 'background.png', IsTryoutDone: enabled, Traits: [],
  BackgroundText: (enabled ? '[img]gfx/ui/icons/melee_skill.png[/img]67/77 (97)[img]gfx/ui/icons/talent_3.png[/img]\n^近战评价：优秀。\n' : '') + '他曾靠护卫商队谋生。'};
const entry = $('<div/>').data('entry', data);
moduleUI.mSelectedEntry = entry;
moduleUI.updateDetailsPanel(entry);
moduleUI.hireRosterEntry = id => moduleUI.notifyBackendHireRosterEntry(id);
moduleUI.tryoutRosterEntry = id => moduleUI.notifyBackendTryoutRosterEntry(id);
w.BBMODL10N.walk(w.document.body);
assert.equal($('h1').text(), '招募');
assert.equal(moduleUI.mDetailsPanel.CharacterName.text(), '阿尔内');
assert.equal(w.document.body.textContent.includes('67/77 (97)'), enabled);
assert.equal(w.document.body.textContent.includes('近战评价：优秀。'), enabled);
assert.ok(w.document.body.textContent.includes('他曾靠护卫商队谋生。'));
assert.equal($('img[src="gfx/ui/icons/talent_3.png"]').length, enabled ? 1 : 0);
moduleUI.mDetailsPanel.HireButton.trigger('click');
moduleUI.mDetailsPanel.TryoutButton.trigger('click');
if (enabled) {
  $('button').filter(function() { return $(this).text() === '解雇'; }).trigger('click');
  assert.deepEqual(calls, [['hire-screen','onHireRosterEntry',42], ['hire-screen','onTryoutRosterEntry',42], ['hire-screen','onDismissRosterEntry',42]]);
} else {
  assert.equal($('button').length, 3);
  assert.equal(moduleUI.mDetailsPanel.HireButton.text(), '招募');
  assert.equal(moduleUI.mDetailsPanel.TryoutButton.text(), '考察');
  assert.equal(moduleUI.mLeaveButton.text(), '离开');
  assert.equal(moduleUI.mDetailsPanel.CharacterBackgroundTextScrollContainer.text(), data.BackgroundText);
  assert.equal($('img[src="gfx/unknown.png"]').length, 1);
  assert.equal(moduleUI.mDetailsPanel.TryoutButton.hasClass('display-none'), false);
  moduleUI.mLeaveButton.trigger('click');
  assert.deepEqual(calls, [['hire-screen','onHireRosterEntry',42], ['hire-screen','onTryoutRosterEntry',42], ['hire-screen','onLeaveButtonPressed',undefined]]);
  // Original tryout reveals personality traits, not talent stars or ratings.
  data.IsTryoutDone = true;
  data.Traits = [{icon: 'ui/traits/brave.png', id: 'trait.brave'}];
  moduleUI.updateDetailsPanel(entry);
  w.BBMODL10N.walk(w.document.body);
  assert.equal($('img[src="gfx/unknown.png"]').length, 0);
  assert.equal($('img[src="gfx/ui/traits/brave.png"]').length, 1);
  assert.equal(moduleUI.mDetailsPanel.TryoutButton.hasClass('display-none'), true);
  assert.equal(moduleUI.mDetailsPanel.CharacterBackgroundTextScrollContainer.text(), data.BackgroundText);
  assert.equal($('img[src*="talent_"]').length, 0);
}
assert.equal(entry.data('entry'), data);
assert.equal(moduleUI.mDetailsPanel.InitialMoneyCostsText.text(), '4510');
assert.equal(moduleUI.mDetailsPanel.DailyMoneyCostsText.text(), '34');
dom.window.close();
console.log(JSON.stringify({recruit_ui: 'passed', star_mod_enabled: enabled, buttons: enabled ? ['hire','tryout','dismiss'] : ['hire','tryout','leave'], stats_stars_ratings_unchanged: true, chinese_background: true, original_tryout_behavior: enabled ? 'not_applicable' : 'passed', game_started: false}));
