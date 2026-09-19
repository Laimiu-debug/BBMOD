const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('../build/browser-check/node_modules/jsdom');
const folder = path.resolve(process.argv[2]);
const inputs = JSON.parse(fs.readFileSync(path.join(folder,'inputs.json'),'utf8'));
const allowed = new Set(inputs.allowed);
const dom = new JSDOM('<body></body>',{runScripts:'outside-only'});
const w = dom.window;
for (const name of ['dictionary.js','place_names.js','name_forms.js','runtime.js']) {
    w.eval(fs.readFileSync(path.join(folder,name),'utf8'));
}
const node = w.document.createElement('div');
let findings = [], credits = 0;
for (const row of inputs.entries) {
    if (row.credit) { credits++; continue; }
    const display = w.BBMODL10N.translate(row.text);
    // Decode HTML entities and strip markup/variables before detecting prose.
    // JSDOM has neither resource loading nor in-page script execution enabled.
    node.innerHTML = display;
    const plain = node.textContent.replace(/\[img\][\s\S]*?\[\/img\]|\[[^\]\n]*\]|\[(?:color|font|size)=|%[A-Za-z0-9_]+%/g,'');
    const words = (plain.match(/[A-Za-z][A-Za-z'-]*/g) || []).filter(word => !allowed.has(word));
    if (words.length) findings.push({id:row.id,words,excerpt:plain.slice(0,240)});
}
const report = {displayed_entries:inputs.entries.length-credits,preserved_credits:credits,findings};
fs.writeFileSync(path.join(folder,'display.json'),JSON.stringify(report,null,2));
dom.window.close();
console.log(JSON.stringify({displayed_entries:report.displayed_entries,findings:findings.length}));
