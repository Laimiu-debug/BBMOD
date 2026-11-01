// Run against an extracted, validated package with the actual original pools.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(path.resolve(process.argv[2]));
const folder = path.resolve(process.argv[3]);
const pools = JSON.parse(fs.readFileSync(path.join(folder, 'pools.json'), 'utf8'));
(async () => {
    const browser = await chromium.launch({headless:true, executablePath:process.argv[4]});
    const page = await browser.newPage();
    const errors=[]; page.on('pageerror', e=>errors.push(e.message));
    try {
        await page.setContent('<body><div id="world"></div><div id="labels"></div>' +
            '<input value="Iron Ravens (12)"><div contenteditable="true">Iron Ravens (12)</div>' +
            '<div data-bbmod-translate="off">Iron Ravens (12)</div></body>');
        await page.evaluate(() => {
            window.WorldScreen=function(){};
            WorldScreen.prototype.onDisconnection=function(){};
            window.SQ={call:function(){}};
            window.drawn=[];
            const fill=CanvasRenderingContext2D.prototype.fillText;
            CanvasRenderingContext2D.prototype.fillText=function(text,x,y){drawn.push(text);return fill.call(this,text,x,y);};
        });
        for (const name of ['dictionary.js','place_names.js','name_forms.js','runtime.js','map_labels.js']) {
            await page.addScriptTag({path:path.join(folder,'ui',name)});
        }
        const result=await page.evaluate(pools => {
            const t=BBMODL10N.translate, checks=[];
            function check(input,expected) {
                const actual=t(input); checks.push({input,expected,actual});
                if(actual!==expected || t(actual)!==expected) throw Error(JSON.stringify(checks[checks.length-1]));
            }
            const dict=BBMOD_DICTIONARY;
            pools.original.company.forEach((source,i)=>{
                const expected=BBMOD_ARMY_NAMES.companies[source];
                for(const suffix of ['', ' (1)', ' (12)', '（48）']) check(source+suffix, expected+suffix);
                check(pools.packaged.company[i]+' (12)', expected+' (12)');
            });
            [['Bulwark (12)','壁垒 (12)'], ['Army (24)','军队 (24)'],
             ['Mercenaries (6)','佣兵 (6)'], ['Iron Crown Company (10)','铁冠战团 (10)'],
             ['Wiesendorf Company (12)','维森多夫军队 (12)'],
             ['Wiesendorf 战团 (12)','维森多夫军队 (12)'],
             ['维森多夫 战团 (12)','维森多夫军队 (12)'],
             ['Wiesendorf 军队 (12)','维森多夫军队 (12)'],
             ['Regiment of Al-Hazif (8)',BBMOD_CITY_PLACES['Al-Hazif']+'军团 (8)'],
             ['军团：'+BBMOD_CITY_PLACES['Al-Hazif']+' (8)',BBMOD_CITY_PLACES['Al-Hazif']+'军团 (8)'],
             [' Company',' 战团'], ['Company','战团'],
             ['铁狼战团 (12)','铁狼战团 (12)'], ['DUMING_QA_20261026','DUMING_QA_20261026'],
             ['MyIron Ravens (12)','MyIron Ravens (12)'],['Iron Ravens Elite (12)','Iron Ravens Elite (12)'],
             ['Unknownford Company (12)','Unknownford Company (12)'],
             ['Bulwark Company (12)','壁垒 Company (12)'],
             ['[img]gfx/army.png[/img]','[img]gfx/army.png[/img]'],
             ['Iron Ravens (many)','Iron Ravens (many)'],
             ['Iron Ravens (12）','Iron Ravens (12）'],
             ['  Iron Ravens (12)  ','  铁鸦 (12)  ']].forEach(x=>check(...x));
            const nativeLabel=Object.freeze({text:'Iron Ravens (12)',x:40,y:40,size:16});
            const screen=new WorldScreen();screen.mContainer=[document.getElementById('world')];
            screen.bbmodMapLabelsInitialize();screen.bbmodMapLabelsFrame({width:640,height:480,labels:[nativeLabel]});
            if(drawn[0]!=='铁鸦 (12)'||nativeLabel.text!=='Iron Ravens (12)') throw Error('Map display changed identity or missed translation');
            const labels=document.getElementById('labels');
            ['Iron Ravens (12)','Wiesendorf 战团 (12)','铁狼战团 (12)'].forEach(text=>{
                const node=document.createElement('div');node.textContent=text;labels.appendChild(node);
            });
            BBMODL10N.walk(document.body);
            if(labels.textContent!=='铁鸦 (12)维森多夫军队 (12)铁狼战团 (12)') throw Error('DOM name translation failed');
            for(const node of document.querySelectorAll('input,[contenteditable],[data-bbmod-translate]')) {
                if((node.value||node.textContent)!=='Iron Ravens (12)') throw Error('Editable/protected name changed');
            }
            return {checks:checks.length, map_and_dom:'passed', identity_and_inputs:'unchanged', samples:checks.slice(-22)};
        }, pools);
        assert.deepEqual(errors,[]);
        fs.writeFileSync(path.join(folder,'browser-validation.json'),JSON.stringify({...result, errors},null,2));
        console.log(JSON.stringify({checks:result.checks,map_and_dom:result.map_and_dom,identity_and_inputs:result.identity_and_inputs}));
    } finally { await browser.close(); }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
