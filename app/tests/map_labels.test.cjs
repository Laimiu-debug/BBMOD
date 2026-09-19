const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require(path.resolve(process.argv[2]));
const assets = path.resolve(process.argv[3]);
const dom = new JSDOM('<body><div id="world"><button id="map-click">Map</button></div></body>', {runScripts:'outside-only'});
const w = dom.window, calls = [], drawn = [], transforms = [];
const context = { clearRect(){drawn.length=0;}, save(){}, restore(){}, rotate(){},
    translate(x,y){transforms.push([x,y]);}, strokeText(){}, fillText(text){drawn.push(text);} };
w.HTMLCanvasElement.prototype.getContext = () => context;
w.WorldScreen = function(){};
w.WorldScreen.prototype.onConnection = function(handle){this.mSQHandle=handle;this.mContainer=[w.document.querySelector('#world')];};
w.WorldScreen.prototype.onDisconnection = function(){this.mSQHandle=null;};
w.SQ = {call(handle, method, data){calls.push([handle,method,data]);}};
for(const file of ['dictionary.js','place_names.js','runtime.js','map_labels.js']) w.eval(fs.readFileSync(path.join(assets,file),'utf8'));
const screen = new w.WorldScreen();
screen.onConnection(123);
assert.equal(calls.length,0);
screen.bbmodMapLabelsInitialize();
assert.equal(calls[0][0],123);
assert.equal(calls[0][1],'bbmodMapLabelsReady');
assert.equal(calls[0][2].ready,true);
assert.equal(screen.bbmodMapCanvas.parentNode,w.document.body);
const frame = Object.freeze({width:1920,height:1080,labels:[
    Object.freeze({text:'Wiesendorf',x:240,y:120,size:20,region:false,r:1,g:1,b:1,a:1}),
    Object.freeze({text:'Stormy Sea',x:480,y:320,size:40,region:true,r:1,g:1,b:1,a:.6}),
    Object.freeze({text:'<img src=x onerror=alert(1)>',x:500,y:600,size:20,region:false})]});
screen.bbmodMapLabelsFrame(frame);
assert.equal(drawn[0], w.BBMOD_PLACE_NAMES.names['Stormy Sea']);
assert.equal(drawn[1], '维森多夫');
assert.equal(drawn[2], '<img src=x onerror=alert(1)>');
assert.equal(w.document.querySelector('img'), null);
assert.equal(screen.bbmodMapCanvas.width,1920);
assert.equal(screen.bbmodMapCanvas.height,1080);
assert.equal(frame.labels[0].text,'Wiesendorf');
screen.bbmodMapLabelsClear();
assert.deepEqual(drawn,[]);
screen.bbmodMapLabelsFrame({width:1280,height:720,labels:[]});
assert.deepEqual(drawn,[]);
assert.equal(screen.bbmodMapCanvas.width,1280);
screen.onDisconnection();
assert.equal(w.document.querySelector('canvas'),null);
assert.equal(calls.length,1);
dom.window.close();
console.log(JSON.stringify({status:'passed',canonical_names_unchanged:true,resize:true,disconnect:true,text_not_html:true}));
