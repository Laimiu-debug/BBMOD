(() => {
  'use strict';
  const $ = id => document.getElementById(`atlas-${id}`);
  if (!$('form')) return;
  const colors = ['#111b1d','#27424b','#73815b','#4e675d','#8a8161','#3e5743','#788778','#617258','#786b44','#626960','#b8a071','#b1a76a','#c2c6b8','#81735b','#929676','#99976c','#c1af7e','#bd9f6a','#80926c'];
  const canvas = $('canvas'), ctx = canvas.getContext('2d');
  let world = null, image = null, roads = null, selectedTown = 0, selectedCamp = -1, selectedLoot = -1;
  let scale = 1, offset = [0, 0], stops = [], route = null, offer = null, dragging = null;
  let mapController = null, routeController = null, mapSequence = 0, routeSequence = 0, drawPending = false;
  const text = (id, value) => { $(id).textContent = value; };
  const point = xy => [xy[0]*4+2, (world.height-1-xy[1])*4+4-(xy[0]&1)*2];
  const screenPoint = xy => { const p = point(xy); return [p[0]*scale+offset[0], p[1]*scale+offset[1]]; };
  const adjacent = (x,y,d) => [[x,y+1],[x+1,y+(x&1)],[x+1,y-1+(x&1)],[x,y-1],[x-1,y-1+(x&1)],[x-1,y+(x&1)]][d];
  const size = () => [canvas.clientWidth, canvas.clientHeight];
  function scheduleDraw() {
    if (!drawPending) { drawPending = true; requestAnimationFrame(() => { drawPending = false; draw(); }); }
  }
  function buildImage() {
    image = document.createElement('canvas'); image.width = world.width*4+4; image.height = world.height*4+8;
    const paint = image.getContext('2d'); paint.fillStyle = '#1c292b'; paint.fillRect(0,0,image.width,image.height);
    const trade = $('mode').value === 'trade';
    for (let y=0; y<world.height; y++) for (let x=0; x<world.width; x++) {
      const color = colors[world.rows[y][x][0]];
      if (trade) {
        const grey = Math.round(parseInt(color.slice(1,3),16)*.25+parseInt(color.slice(3,5),16)*.55+parseInt(color.slice(5),16)*.2);
        paint.fillStyle = `rgb(${grey},${grey},${Math.round(grey*.95)})`;
      } else paint.fillStyle = color;
      const p = point([x,y]); paint.fillRect(p[0]-2,p[1]-2,4,4);
    }
    roads = new Path2D();
    for (let y=0; y<world.height; y++) for (let x=0; x<world.width; x++) for (let d=0; d<3; d++) {
      if (!(world.rows[y][x][4] & (1<<d))) continue;
      const a = adjacent(x,y,d);
      if (a[0]<0 || a[1]<0 || a[0]>=world.width || a[1]>=world.height) continue;
      const p=point([x,y]), q=point(a); roads.moveTo(...p); roads.lineTo(...q);
    }
  }
  function fit() {
    if (!image) return;
    const [w,h]=size(); scale=Math.max(.2,Math.min((w-24)/image.width,(h-24)/image.height));
    offset=[(w-image.width*scale)/2,(h-image.height*scale)/2]; scheduleDraw();
  }
  function center(xy) {
    const p=point(xy), [w,h]=size(); offset=[w/2-p[0]*scale,h/2-p[1]*scale]; scheduleDraw();
  }
  function zoom(factor, anchor) {
    if (!world) return;
    const [w,h]=size(), a=anchor || [w/2,h/2], next=Math.min(10,Math.max(.25,scale*factor));
    offset=[a[0]-(a[0]-offset[0])*next/scale,a[1]-(a[1]-offset[1])*next/scale]; scale=next; scheduleDraw();
  }
  function draw() {
    const [w,h]=size(), dpr=window.devicePixelRatio || 1;
    if (canvas.width!==Math.round(w*dpr) || canvas.height!==Math.round(h*dpr)) {canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#1c292b';ctx.fillRect(0,0,w,h);
    if (!world || !image) return;
    ctx.save();ctx.translate(...offset);ctx.scale(scale,scale);ctx.imageSmoothingEnabled=false;ctx.drawImage(image,0,0);
    if ($('roads').checked) {ctx.strokeStyle='#d9b26b';ctx.lineWidth=1.2/scale;ctx.stroke(roads);}
    if (route && route.tiles.length) {
      ctx.beginPath();route.tiles.forEach((xy,i) => {const p=point(xy);if (i) ctx.lineTo(...p); else ctx.moveTo(...p);});
      ctx.strokeStyle='#5ce4b5';ctx.lineWidth=3.2/scale;ctx.stroke();
    }
    ctx.restore();
    const font=Number($('font').value), used=[];
    const label = (name,xy,color,priority=false) => {
      const p=screenPoint(xy); if (p[0]<-150 || p[1]<-30 || p[0]>w+150 || p[1]>h+30) return;
      ctx.font=`600 ${font}px "Microsoft YaHei",sans-serif`;ctx.textBaseline='top';
      const width=ctx.measureText(name).width+10, x=Math.max(3,Math.min(w-width-3,p[0]+9)), y=Math.max(3,Math.min(h-font-9,p[1]-font/2));
      const box=[x,y,width,font+7];
      if (!priority && used.some(r => x<r[0]+r[2]+3 && x+width+3>r[0] && y<r[1]+r[3]+3 && y+font+10>r[1])) return;
      used.push(box);ctx.fillStyle='rgba(20,25,20,.9)';ctx.fillRect(...box);ctx.fillStyle=color;ctx.fillText(name,x+5,y+2);
    };
    for (const camp of world.camps) {
      if (!$('camps').checked && !camp.count && camp.index!==selectedCamp) continue;
      const p=screenPoint(camp.xy);ctx.beginPath();ctx.moveTo(p[0],p[1]-5);ctx.lineTo(p[0]+5,p[1]);ctx.lineTo(p[0],p[1]+5);ctx.lineTo(p[0]-5,p[1]);ctx.closePath();
      ctx.fillStyle=camp.index===selectedCamp?'#fff1a2':camp.count?'#ff817a':'#b8aa89';ctx.fill();
    }
    for (const town of world.towns) {
      const p=screenPoint(town.xy);ctx.beginPath();ctx.arc(...p,town.index===selectedTown?6:4.5,0,Math.PI*2);ctx.fillStyle='#edce80';ctx.fill();ctx.strokeStyle='#17211d';ctx.lineWidth=2;ctx.stroke();
    }
    if (world.player) {const p=screenPoint(world.player);ctx.fillStyle='#9dd1ff';ctx.beginPath();ctx.arc(...p,4,0,Math.PI*2);ctx.fill();}
    if (selectedCamp>=0) {
      const camp=world.camps[selectedCamp],p=screenPoint(camp.xy);ctx.beginPath();ctx.arc(...p,12,0,Math.PI*2);ctx.strokeStyle='#fff1a2';ctx.lineWidth=2.5;ctx.stroke();label(camp.name,camp.xy,'#fff1a2',true);
    }
    if (world.towns[selectedTown]) label(world.towns[selectedTown].name,world.towns[selectedTown].xy,'#fff5cf',true);
    for (const town of world.towns) if (town.index!==selectedTown) label(town.name,town.xy,'#f3e4b8');
    if ($('regions').checked) for (const r of world.regions) label(r.name,r.xy,'#bcc8b1');
    for (let i=0;i<stops.length;i++) {const p=screenPoint(world.towns[stops[i]].xy);ctx.fillStyle='#5ce4b5';ctx.beginPath();ctx.arc(p[0],p[1]-15,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='#10291f';ctx.font='bold 13px sans-serif';ctx.textAlign='center';ctx.fillText(String(i+1),p[0],p[1]-22);ctx.textAlign='left';}
  }
  function switchTab(name) {
    for (const button of document.querySelectorAll('[data-tab]')) {const chosen=button.dataset.tab===name;button.setAttribute('aria-selected',String(chosen));button.tabIndex=chosen?0:-1;$(`${button.dataset.tab}-panel`).hidden=!chosen;}
  }
  function rowButton(container, title, description, action) {
    const button=document.createElement('button'), strong=document.createElement('strong'), span=document.createElement('span');
    button.type='button';strong.textContent=title;span.textContent=description;button.append(strong,span);button.addEventListener('click',action);container.append(button);return button;
  }
  function selectTown(index, focus=false) {
    selectedTown=index;const town=world.towns[index];text('town-name',town.name);text('town-traits',town.traits.join(' · '));
    text('town-sites',`设施：${[...town.buildings,...town.sites].filter(label=>label!=='其他建筑').join('、') || '无'}\n特产：${town.produce.join('、') || '无贸易特产'}`);text('town-advice',town.advice);
    $('market').replaceChildren();for (const good of town.market) {const row=document.createElement('tr');for(const value of [good.good,good.buy,good.sell]) {const cell=document.createElement('td');cell.textContent=String(value);row.append(cell);}$('market').append(row);}
    for (const [i,button] of [...$('towns').children].entries()) button.setAttribute('aria-pressed',String(i===index));
    if (focus) center(town.xy);scheduleDraw();
  }
  function fillLoot() {
    const kind=$('loot-kind').value, query=$('loot-search').value.trim().toLowerCase();$('loot').replaceChildren();
    const filtered=world.loot.filter(item => (!kind || item.kind===kind) && `${item.name} ${world.camps[item.camp].name}`.toLowerCase().includes(query));
    text('loot-count',`开局红装 ${filtered.length} / ${world.loot.length} 件`);
    for (const item of filtered) {
      const rating=item.score===null?'':` · 实用 ${item.score}/100 · roll ${item.quality}%`;
      const button=rowButton($('loot'),item.name+rating,`${item.kind_label} · ${world.camps[item.camp].name}`,()=>selectLoot(item.index));button.dataset.loot=String(item.index);button.setAttribute('aria-pressed',String(item.index===selectedLoot));
    }
    if (!filtered.length) {const p=document.createElement('p');p.className='atlas-empty';p.textContent='没有符合条件的红装。';$('loot').append(p);}
  }
  function selectLoot(index) {
    const item=world.loot[index];selectedLoot=index;selectedCamp=item.camp;text('loot-detail',item.detail);center(world.camps[item.camp].xy);
    for (const button of $('loot').querySelectorAll('button')) button.setAttribute('aria-pressed',String(button.dataset.loot===String(index)));
  }
  function selectCamp(index) {
    selectedCamp=index;switchTab('loot');const item=world.loot.find(i=>i.camp===index);
    if (item) {$('loot-kind').value='';$('loot-search').value='';selectedLoot=item.index;fillLoot();selectLoot(item.index);const button=$('loot').querySelector(`[data-loot="${item.index}"]`);if (button) button.scrollIntoView({block:'nearest'});}
    else {selectedLoot=-1;text('loot-detail',world.camps[index].detail);center(world.camps[index].xy);fillLoot();}
  }
  function populate() {
    $('towns').replaceChildren();$('route-town').replaceChildren();
    for (const town of world.towns) {
      rowButton($('towns'),town.name,`${town.traits.join(' · ')}｜${town.produce.join('、') || '无贸易特产'}`,()=>selectTown(town.index,true));
      const option=document.createElement('option');option.value=String(town.index);option.textContent=town.name;$('route-town').append(option);
    }
    $('offers').replaceChildren();
    for (const [index,o] of world.offers.entries()) {
      const button=rowButton($('offers'),`${o.good} · 毛利 ${o.profit} 克朗/件 · ${(o.roi*100).toFixed(0)}%`,`${world.towns[o.source].name} → ${world.towns[o.target].name}｜买 ${o.buy} / 卖 ${o.sell}`,()=>{
        offer=o;stops=[o.source,o.target];text('offer-reason',o.reason);for (const b of $('offers').children)b.setAttribute('aria-pressed',String(b===button));updateRoute();
      });button.dataset.offer=String(index);
    }
    selectedTown=0;selectedCamp=-1;selectedLoot=-1;stops=[];route=null;offer=null;fillLoot();selectTown(0);updateStops();summary();text('offer-reason','');text('loot-detail','选择红装查看属性和营地位置。');text('route-status','');
  }
  function updateStops() {
    $('stops').replaceChildren();for (const index of stops) {const li=document.createElement('li');li.textContent=world.towns[index].name;$('stops').append(li);}scheduleDraw();
  }
  function dropOffer() {offer=null;text('offer-reason','');for(const button of $('offers').children)button.setAttribute('aria-pressed','false');}
  function addStop(index) {
    if (!world) return;
    if(stops.length>=12){text('route-status','一条路线最多十二站。');return;}
    dropOffer();stops.push(index);switchTab('trade');updateRoute();
  }
  const cookie = name => document.cookie.split(';').map(v=>v.trim()).find(v=>v.startsWith(`${name}=`))?.slice(name.length+1) || '';
  async function request(url, options, controller) {
    const deadline=Date.now()+180000;
    for(;;) {
      const response=await fetch(url,{...options,signal:controller.signal,credentials:'same-origin',headers:{'Accept':'application/json',...options.headers}});
      const data=await response.json();
      if(response.status===202 && Date.now()<deadline) {
        await new Promise((resolve,reject)=>{const done=()=>{controller.signal.removeEventListener('abort',abort);resolve();};const timer=setTimeout(done,3000);const abort=()=>{clearTimeout(timer);reject(new DOMException('Aborted','AbortError'));};controller.signal.addEventListener('abort',abort,{once:true});});continue;
      }
      if (!response.ok || response.status===202) throw new Error(data.message || '请求未完成，请稍后再试。');return data;
    }
  }
  async function updateRoute() {
    updateStops();route=null;summary();const sequence=++routeSequence;if(routeController)routeController.abort();
    if(stops.length<2){text('route-status','');return;}
    text('route-status','正在计算道路与地形行程…');const controller=routeController=new AbortController(), seed=world.seed;
    try {
      const value=await request(`/api/v1/worldmaps/${encodeURIComponent(seed)}/route/`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':decodeURIComponent(cookie('bbmod_csrftoken'))},body:JSON.stringify({stops,road_only:$('road-only').checked})},controller);
      if(sequence!==routeSequence || world.seed!==seed)return;
      route=value;text('route-status','');summary();scheduleDraw();
    } catch(error) {if(error.name!=='AbortError' && sequence===routeSequence){text('route-status',error.message);summary();}}
  }
  function numeric(id, min, max) {return Math.max(min,Math.min(max,Number($(id).value)||0));}
  function summary() {
    if(!route){text('route-summary',stops.length<2?'添加两座城镇以计算行程。':'路线尚未计算完成。');return;}
    const quantity=numeric('quantity',1,999), cost=numeric('cost',0,10000), expense=route.hours/24*cost;
    const lines=[`${stops.length} 站 · 约 ${route.hours.toFixed(1)} 小时（${(route.hours/24).toFixed(2)} 天）`, `道路 ${route.road_steps} 格 · 战团行程开销 ${expense.toFixed(0)} 克朗`];
    if(offer)lines.push(`${offer.good} × ${quantity}：采购 ${offer.buy*quantity} → 售出 ${offer.sell*quantity}`,`毛利 ${offer.profit*quantity} · 扣行程开销后 ${(offer.profit*quantity-expense).toFixed(0)} 克朗`);
    for(const leg of route.legs) lines.push(`${world.towns[leg.source].name} → ${world.towns[leg.target].name}：${leg.hours.toFixed(1)} 小时`);
    text('route-summary',lines.join('\n'));
  }
  async function loadMap(event) {
    if(event)event.preventDefault();const seed=$('seed').value.trim();
    if(!/^[A-Za-z0-9]{10}$/.test(seed)){text('status','请输入十位英文字母或数字，保留大小写。');return;}
    const sequence=++mapSequence;if(mapController)mapController.abort();if(routeController)routeController.abort();routeSequence++;
    const controller=mapController=new AbortController();$('form').querySelector('button').disabled=true;text('status','正在解算完整地图、营地与红装；首次需等待，已解算的种子可直接打开…');
    try {
      const value=await request(`/api/v1/worldmaps/${encodeURIComponent(seed)}/`,{},controller);if(sequence!==mapSequence)return;
      world=value;$('workspace').hidden=false;buildImage();populate();fit();
      text('status',`${world.seed} · ${world.towns.length} 座城镇 · ${world.camps.length} 处营地 · ${world.loot.length} 件红装`);
      const url=new URL(location.href);url.searchParams.set('seed',world.seed);history.replaceState(null,'',url);
    } catch(error){if(error.name!=='AbortError' && sequence===mapSequence)text('status',error.message);}
    finally{if(sequence===mapSequence)$('form').querySelector('button').disabled=false;}
  }
  $('form').addEventListener('submit',loadMap);
  $('fit').addEventListener('click',fit);$('in').addEventListener('click',()=>zoom(1.3));$('out').addEventListener('click',()=>zoom(1/1.3));
  for(const id of ['roads','regions','camps','font'])$(id).addEventListener('change',scheduleDraw);
  $('mode').addEventListener('change',()=>{if(world){buildImage();scheduleDraw();}});
  for(const button of document.querySelectorAll('[data-tab]')) {
    button.addEventListener('click',()=>switchTab(button.dataset.tab));
    button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const buttons=[...document.querySelectorAll('[data-tab]')],index=buttons.indexOf(button),next=event.key==='Home'?0:event.key==='End'?2:(index+(event.key==='ArrowRight'?1:2))%3;switchTab(buttons[next].dataset.tab);buttons[next].focus();});
  }
  $('loot-kind').addEventListener('change',()=>world&&fillLoot());$('loot-search').addEventListener('input',()=>world&&fillLoot());
  $('add-town').addEventListener('click',()=>addStop(selectedTown));$('route-add').addEventListener('click',()=>addStop(Number($('route-town').value)));
  $('undo').addEventListener('click',()=>{dropOffer();stops.pop();updateRoute();});$('reverse').addEventListener('click',()=>{dropOffer();stops.reverse();updateRoute();});
  $('clear').addEventListener('click',()=>{dropOffer();stops=[];updateRoute();});$('road-only').addEventListener('change',updateRoute);
  $('quantity').addEventListener('input',summary);$('cost').addEventListener('input',summary);
  $('export').addEventListener('click',()=>{
    if(!route){text('route-status','先生成一条路线再导出。');return;}
    const blob=new Blob([JSON.stringify({seed:world.seed,profile:world.profile,camp_profile:world.camp_profile,route,stop_names:stops.map(i=>world.towns[i].name)},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`BBMOD-${world.seed}-商路.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  function local(event){const rect=canvas.getBoundingClientRect();return[event.clientX-rect.left,event.clientY-rect.top];}
  function nearest(p) {
    let found=null,best=14;const check=(type,entries)=>{for(const entry of entries){const q=screenPoint(entry.xy),distance=Math.hypot(p[0]-q[0],p[1]-q[1]);if(distance<best){best=distance;found={type,index:entry.index};}}};
    check('town',world.towns);check('camp',world.camps.filter(c=>$('camps').checked||c.count||c.index===selectedCamp));return found;
  }
  canvas.addEventListener('pointerdown',event=>{if(!world || event.button!==0)return;dragging={id:event.pointerId,start:local(event),offset:[...offset],moved:false};canvas.setPointerCapture(event.pointerId);});
  canvas.addEventListener('pointermove',event=>{if(!dragging || dragging.id!==event.pointerId)return;const p=local(event),dx=p[0]-dragging.start[0],dy=p[1]-dragging.start[1];if(Math.hypot(dx,dy)>5)dragging.moved=true;if(dragging.moved){offset=[dragging.offset[0]+dx,dragging.offset[1]+dy];scheduleDraw();}});
  canvas.addEventListener('pointerup',event=>{if(!dragging || dragging.id!==event.pointerId)return;const click=!dragging.moved;dragging=null;if(canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);if(click){const hit=nearest(local(event));if(hit?.type==='town'){switchTab('town');selectTown(hit.index);}else if(hit)selectCamp(hit.index);}});
  canvas.addEventListener('pointercancel',()=>{dragging=null;});
  canvas.addEventListener('dblclick',event=>{if(!world)return;const hit=nearest(local(event));if(hit?.type==='town')addStop(hit.index);});
  canvas.addEventListener('wheel',event=>{if(!world)return;event.preventDefault();zoom(event.deltaY<0?1.15:1/1.15,local(event));},{passive:false});
  canvas.addEventListener('keydown',event=>{if(!world)return;if(['+','=','-','Home'].includes(event.key)){event.preventDefault();if(event.key==='Home')fit();else zoom(event.key==='-'?1/1.3:1.3);}else if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();offset[0]+=event.key==='ArrowLeft'?30:event.key==='ArrowRight'?-30:0;offset[1]+=event.key==='ArrowUp'?30:event.key==='ArrowDown'?-30:0;scheduleDraw();}});
  new ResizeObserver(()=>{if(world){if(selectedCamp>=0)center(world.camps[selectedCamp].xy);scheduleDraw();}}).observe(canvas);
  switchTab('town');loadMap();
})();
