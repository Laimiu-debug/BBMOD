// Exercise the patched official control, including IME and input callbacks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require(path.resolve('build/browser-check/node_modules/jsdom'));
const dom = new JSDOM('<body><div id="host"></div></body>', {runScripts: 'outside-only'});
const win = dom.window;
win.eval(fs.readFileSync('build/full-l10n/original/ui/extern/jquery-2.1.4.min.js', 'utf8'));
win.KeyConstants = {Tabulator:9, ArrowLeft:37, ArrowRight:39, ArrowUp:38, ArrowDown:40,
    Zero:48, Z:90, Backspace:8, Delete:46, Space:32, Return:13, Enter:13};
win.eval(fs.readFileSync(process.argv[2], 'utf8'));
let latestLength = -1;
const $ = win.jQuery;
$.fn.shakeLeftRight = function () {};
const field = $('#host').createInput('', 0, 8, 1, (input, length) => { latestLength = length; });
const composing = $.Event('keydown', {which:229, keyCode:229});
field.trigger(composing);
assert.equal(composing.isDefaultPrevented(), false, 'Chinese composition must remain enabled');
field.val('晨星战团').trigger('input');
assert.equal(field.val(), '晨星战团');
assert.equal(latestLength, 4, 'Start button callback receives the committed Chinese length');
field.val('').trigger('input');
assert.equal(latestLength, 0, 'Clearing the name still disables Start');
assert.equal(field.attr('maxlength'), '8');
dom.window.close();
console.log('PASS: Chinese composition, committed input callbacks, empty name and max length');
