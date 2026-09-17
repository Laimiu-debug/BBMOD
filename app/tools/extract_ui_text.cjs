/* Extract original JS string positions. Parsing is only development tooling. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const acorn = require('../build/full-l10n/node/node_modules/acorn');
const work = path.resolve(__dirname, '../build/full-l10n');
const root = path.join(work, 'original');
const files = {};
const review = [];
function walkFiles(dir) {
    return fs.readdirSync(dir, {withFileTypes:true}).flatMap(e => e.isDirectory() ? walkFiles(path.join(dir,e.name)) : [path.join(dir,e.name)]);
}
function visible(node, ancestors) {
    const s = node.value;
    const plain = s.replace(/<[^>]*(?:>|$)/g, '').replace(/\[\/?[^\]]*\]/g, '');
    if (!/[A-Za-z]/.test(plain)) return false;
    if (/^[\s]*(?:[a-z][\w.-]*-[\w.-]+)(?:[\s"'\/>]|$)/.test(s)) return false;
    if (s===' x ' || s===' not allowed for: ') return false;
    const parent = ancestors[ancestors.length - 1];
    if (parent.type === 'Property' && parent.key === node) return false;
    if (parent.type === 'MemberExpression' || parent.type === 'BinaryExpression' && ['==','===','!=','!==','in'].includes(parent.operator)) return false;
    if (/^(?:coui:|https?:|gfx\/|ui\/|sounds\/|music\/|#|\.)/.test(s)) return false;
    if (/^[\w.\-/]+\.(?:png|jpg|ogg|wav|js|css|html|ttf)$/.test(s)) return false;
    const call = [...ancestors].reverse().find(n => n.type === 'CallExpression');
    const method = call && call.callee.type === 'MemberExpression' ? call.callee.property.name : '';
    const child = call ? (ancestors[ancestors.indexOf(call)+1] || node) : null;
    const arg = call ? call.arguments.indexOf(child) : -1;
    if (/^(?:log\w*|error|warn|debug|trigger|on|off|addClass|removeClass|toggleClass|find|data|attr|css|bindTooltip|createAssetButton)$/.test(method || '')) return false;
    if (arg===0 && /^(?:text|html|setText|createTextButton|createTextButtonWithLabel|createTabTextButton|createDialog|createPopupDialog|addPopupDialogButton|changeButtonText|createAppearanceControlDIV)$/.test(method || '')) return true;
    if (arg===1 && method==='createVolumeControlDIV') return true;
    if (parent.type === 'Property' && /^(?:text|title|description|label|placeholder)$/.test(parent.key.name || parent.key.value)) return true;
    if (s.includes('<') && /[A-Za-z]/.test(plain) && !/^["'][^>]+(?:>|$)/.test(s)) return true;
    if (/[\s]/.test(s) && /^[\s(A-Z]/.test(s) && !s.includes('::') && !/^(?:use strict|Failed|Invalid|Backpack|Stash [|\-]|Paperdoll|[a-z].*-|.* -> )/.test(s)) return true;
    if (!/[_./]|[a-z][A-Z]/.test(s)) review.push({source:s, file:currentFile, method, context:currentCode.slice(Math.max(0,node.start-70),Math.min(currentCode.length,node.end+35))});
    return false;
}
let currentFile='', currentCode='';
for (const file of walkFiles(path.join(root,'ui')).filter(p=>p.endsWith('.js') && !p.includes(`${path.sep}extern${path.sep}`) && !p.includes(`${path.sep}thirdparty${path.sep}`) && !p.includes(`${path.sep}libs${path.sep}`))) {
    currentFile=path.relative(root,file).replaceAll('\\','/');
    currentCode=fs.readFileSync(file,'utf8');
    if (/jquery|velocity|knockout|coherent|bbcode/i.test(path.basename(file))) continue;
    const ast=acorn.parse(currentCode,{ecmaVersion:2020,allowReturnOutsideFunction:true});
    const patches=[];
    function visit(node,ancestors) {
        if (!node || !node.type) return;
        if (node.type==='Literal' && typeof node.value==='string' && visible(node,ancestors)) {
            patches.push({start:Buffer.byteLength(currentCode.slice(0,node.start)),end:Buffer.byteLength(currentCode.slice(0,node.end)),source:node.value});
        }
        for (const value of Object.values(node)) {
            if (Array.isArray(value)) value.forEach(v=>visit(v,[...ancestors,node]));
            else if (value && typeof value==='object' && value.type) visit(value,[...ancestors,node]);
        }
    }
    visit(ast,[]);
    if (patches.length) files[currentFile]={sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),patches};
}
fs.writeFileSync(path.join(work,'ui-inventory.json'),JSON.stringify(files,null,2));
fs.writeFileSync(path.join(work,'ui-review.json'),JSON.stringify(review,null,2));
console.log(JSON.stringify({files:Object.keys(files).length,strings:Object.values(files).reduce((n,f)=>n+f.patches.length,0),review:review.length}));
