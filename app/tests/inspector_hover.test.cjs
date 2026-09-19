// Exercise wrappers against the installed game's unmodified tooltip module.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const listeners = {}, calls = [], pending = [], intervals = [];
const box = {left: 100, top: 100, right: 160, bottom: 160};
let attached = true, shown = true, itemShown = true;
const element = {0: {getBoundingClientRect: () => box}, data: () => true, is: () => itemShown, isInDOM: () => attached};
const container = {0: {getBoundingClientRect: () => ({left:170,top:100,width:320,height:600})},
    is: () => shown, removeClass() { return this; }, addClass() { return this; }};
const context = vm.createContext({console, clearTimeout, innerWidth:1920, innerHeight:1080, $: {fn: {}}, document: {
    documentElement: {contains: () => attached}, addEventListener: (name, fn) => { listeners[name] = fn; }
}, addEventListener: (name, fn) => { listeners[name] = fn; }, setInterval: fn => { intervals.push(fn); },
SQ: {call(handle, name, data, callback) { calls.push({name, data}); if (callback) pending.push(callback); }}});
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../data/item_inspector/hover.js'), 'utf8'), context);
// In main.html TooltipScreen is declared AFTER TooltipModule; lazy hook matters.
vm.runInContext('function TooltipScreen() {} TooltipScreen.prototype.hide = function() { this.hidden = true; };', context);
const tooltip = Object.create(context.TooltipModule.prototype);
Object.assign(tooltip, {mSQHandle: 'test', mContainer: container, mIsVisible: false, mCurrentData: null,
    mCurrentElement: null, buildFromData() {}, setupUITooltip() {}});
const state = () => calls.filter(x => x.name === 'bbmodInspectorHover').at(-1);
const move = (x, y) => listeners.mousemove({clientX: x, clientY: y});
const data = id => ({contentType: 'ui-item', entityId: 5, itemId: id, itemOwner: 'stash'});
function show(id) { move(120, 120); tooltip.showTooltip(element, data(id)); pending.shift()([{text: 'original'}]); }
show(10);
assert.equal(state().data[1], true);
assert.equal(JSON.stringify(state().data[2]), '[170,100,320,600,1920,1080]');
assert.equal(calls.find(x => x.name === 'bbmodInspectorQuery').data[1], 10);
const first = state().data[0];
intervals[0](); assert.equal(state().data[0], first); assert.equal(state().data[1], true);
move(170, 120); assert.equal(state().data[1], false);
intervals[0](); assert.equal(state().data[1], false);
show(11); tooltip.hideUITooltip(); assert.equal(state().data[1], false);
// A callback that resolves after mouseleave must not resurrect the overlay.
tooltip.showTooltip(element, data(12)); tooltip.hideUITooltip();
pending.shift()([{text: 'old reply'}]); assert.equal(state().data[1], false);
// A late item A response cannot replace the live B token.
tooltip.showTooltip(element, data(13)); tooltip.showTooltip(element, data(14));
pending.pop()([{text: 'B'}]); const latest = state().data[0];
pending.shift()([{text: 'A'}]); assert.equal(state().data[0], latest);
tooltip.hideTooltip(); assert.equal(state().data[1], false);
show(15); const screen = new context.TooltipScreen(); screen.mTooltipModule = tooltip;
screen.hide(); assert.equal(screen.hidden, true); assert.equal(state().data[1], false);
show(16); attached = false; intervals[0](); assert.equal(state().data[1], false); attached = true;
show(17); shown = false; intervals[0](); assert.equal(state().data[1], false); shown = true;
show(18); listeners.blur(); assert.equal(state().data[1], false);
show(19); listeners.mouseleave({target:element[0]}); assert.equal(state().data[1], true);
listeners.mouseleave({target:context.document}); assert.equal(state().data[1], false);
show(20); tooltip.notifyBackendQueryTooltipData({contentType: 'tile'}, () => {});
assert.equal(state().data[1], false); assert.equal(calls.at(-1).name, 'onQueryTileTooltipData'); pending.shift();
show(21); tooltip.mEventListener = null; tooltip.onDisconnection(); assert.equal(state().data[1], false);
assert.equal(intervals.length, 1);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../data/item_inspector/hover.js'), 'utf8'), context);
assert.equal(intervals.length, 1); // repeated script load never adds a second poller
console.log('BBMOD_HOVER_UI_PASS: original callbacks, matching tokens, leave, hide, blur, detach, screen hide, heartbeat, duplicate load');
