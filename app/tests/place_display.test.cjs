const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require(path.resolve(process.argv[2]));
const assets = path.resolve(process.argv[3]);
const source = name => fs.readFileSync(path.join(assets,name),'utf8');
const config = JSON.parse(source('place_names.js').replace(/^window.BBMOD_PLACE_NAMES = /,'').replace(/;\n$/,''));

function session(marker, delayed=false, automatic=false) {
    const dom = new JSDOM('<body><div id="dialogue">护送商队前往Wiesendorf，随后探索Black Monolith。</div><div id="map">Wiesendorf</div><button id="menu">New Campaign</button><input id="Wiesendorf" value="Wiesendorf"><div contenteditable="true">Black Monolith</div><div data-bbmod-translate="off">Wiesendorf</div><div id="title" title="Wiesendorf" data-place-id="Wiesendorf"></div></body>',{runScripts:'outside-only'});
    const w=dom.window, calls=[], pending=[];
    w.MainMenuScreen=function(){};
    w.MainMenuScreen.prototype.onConnection=function(handle){this.mSQHandle=handle;this.connected=(this.connected||0)+1;};
    let queries=0;
    w.SQ={call(handle, method, arg, callback){
        assert.equal(handle,123); calls.push(method);
        if(method==='getRegisteredCSSHooks'||method==='getRegisteredJSHooks') callback([]);
        else {
            assert.equal(method,'bbmodGetPlaceNameSession');
            callback(delayed && queries++===0 ? '' : marker);
        }
    }};
    w.setTimeout=callback=>{pending.push(callback);return pending.length;};
    for(const name of ['mod_hooks.js','dictionary.js','place_names.js','runtime.js']) {
        if(name==='runtime.js' && !automatic) delete w.BBMOD_PLACE_NAMES.mode;
        w.eval(source(name));
    }
    w.BBMODL10N.start();
    const screen=new w.MainMenuScreen();screen.onConnection(123);
    assert.equal(screen.connected,1);
    assert(calls.includes('getRegisteredCSSHooks')&&calls.includes('getRegisteredJSHooks'));
    while(pending.length)pending.shift()();
    assert.equal(dom.window.document.querySelector('#menu').textContent,'新建战役');
    return {dom,w,calls};
}

(async()=>{
    // New ordinary MOD mode translates both launch routes without a native token.
    for(const marker of ['', null, config.session]) {
        const {dom,w,calls} = session(marker, false, true);
        for(const [english,chinese] of Object.entries(config.names)) assert.equal(w.BBMODL10N.translate(english),chinese);
        assert.equal(w.document.querySelector('#dialogue').textContent,'护送商队前往维森多夫，随后探索黑色巨石。');
        assert(!calls.includes('bbmodGetPlaceNameSession'));
        dom.window.close();
    }
    for(const marker of ['',null,'zh-CN:wrong-dictionary']){
        const {dom,w,calls}=session(marker);
        assert.equal(w.document.querySelector('#map').textContent,'Wiesendorf');
        assert.equal(w.document.querySelector('#dialogue').textContent,'护送商队前往Wiesendorf，随后探索Black Monolith。');
        for(const english of Object.keys(config.names)){
            assert.equal(w.BBMODL10N.translate(english),english);
            assert.equal(w.BBMODL10N.translate('前往'+english+'。'),'前往'+english+'。');
        }
        assert.equal(calls.filter(x=>x==='bbmodGetPlaceNameSession').length,8);
        dom.window.close();
    }
    const state=Object.freeze({Name:'Wiesendorf',Destination:'Black Monolith',Region:'Stormy Sea'});
    const before=JSON.stringify(state);
    const {dom,w,calls}=session(config.session,true);
    const t=w.BBMODL10N.translate;
    assert.equal(w.document.querySelector('#map').textContent,'维森多夫');
    assert.equal(w.document.querySelector('#dialogue').textContent,'护送商队前往维森多夫，随后探索黑色巨石。');
    assert.equal(calls.filter(x=>x==='bbmodGetPlaceNameSession').length,2);
    assert.equal(w.document.querySelector('input').value,'Wiesendorf');
    assert.equal(w.document.querySelector('[contenteditable]').textContent,'Black Monolith');
    assert.equal(w.document.querySelector('[data-bbmod-translate="off"]').textContent,'Wiesendorf');
    assert.equal(w.document.querySelector('#title').title,'维森多夫');
    assert.equal(w.document.querySelector('#title').getAttribute('data-place-id'),'Wiesendorf');
    let checked=0;
    for(const [english,chinese] of Object.entries(config.names)){
        assert.equal(t(english),chinese);
        assert.equal(t('前往「'+english+'」，然后返回。'),'前往「'+chinese+'」，然后返回。');
        const identifier='place_id_'+english.replace(/[^A-Za-z0-9_]/g,'_')+'_suffix';
        assert.equal(t(identifier),identifier);
        checked++;
    }
    const added=w.document.createElement('span');added.textContent='前往'+state.Destination;w.document.body.appendChild(added);
    await new Promise(resolve=>setTimeout(resolve,30));
    assert.equal(added.textContent,'前往黑色巨石');
    assert.equal(JSON.stringify(state),before);
    dom.window.close();
    const direct=session('');
    assert.equal(direct.w.BBMODL10N.translate(state.Name),state.Name);
    assert.equal(direct.w.BBMODL10N.translate('前往'+state.Destination),'前往Black Monolith');
    direct.dom.window.close();
    console.log(JSON.stringify({status:'passed',dictionary_entries:checked,launch_modes:['direct','bbmod','direct_again'],canonical_data_unchanged:true,framework_callbacks_preserved:true,wrong_marker_ignored:true}));
})().catch(error=>{console.error(error);process.exitCode=1;});
