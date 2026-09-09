'use strict';
const $ = id => document.getElementById(id);
const metrics = {
  cost_usd:'Total cost · USD', latency_seconds:'End-to-end latency · s',
  input_tokens:'Total input tokens', output_tokens:'Output tokens', cache_read_tokens:'Cache read tokens'
};
let data = null;
const modelSelections=new Map(),taskSelections=new Map();
const taskKey=r=>JSON.stringify([r.task_id,r.difficulty]);
const modelKey=r=>JSON.stringify([r.provider,r.model]);
const defined = x => typeof x === 'number' && Number.isFinite(x);
const money = x => defined(x) ? '$'+x.toFixed(4) : 'Unavailable';
const num = x => defined(x) ? new Intl.NumberFormat('en',{maximumFractionDigits:1}).format(x) : '—';
function el(tag,text,className){const e=document.createElement(tag); if(text !== undefined)e.textContent=text;if(className)e.className=className;return e;}
function option(select,value,label){const o=el('option',label);o.value=value;select.append(o);}
for(const [key,label] of Object.entries(metrics)){option($('x'),key,label);option($('y'),key,label);}
$('x').value='cost_usd';$('y').value='latency_seconds';
function filtered(){return data.rows.filter(r=>taskSelections.get(taskKey(r))&&modelSelections.get(modelKey(r)));}
const colors={codex:'#339cff',claude:'#eaa582'};
const pointColor=r=>r.completion===1?(colors[r.provider]||'#ccc'):'#a3a3a3';
function hideDetails(){ $('tooltip').hidden=true; }
function details(r,dot){
  const popup=$('tooltip');popup.replaceChildren();popup.style.setProperty('--point-color',pointColor(r));
  const list=el('dl');
  for(const [label,value] of [['Model',r.model],['Task',r.task_id],['Difficulty',r.difficulty||'Unavailable'],['Result',r.completion===1?'Pass':'Fail'],['Total cost',money(r.cost_usd)],['End-to-end latency',defined(r.latency_seconds)?num(r.latency_seconds)+' s':'Unavailable']]){
    list.append(el('dt',label),el('dd',value,label==='Model'?'model':undefined));
  }
  popup.append(list);popup.hidden=false;
  const anchor=dot.getBoundingClientRect(),wrap=$('plot').parentElement.getBoundingClientRect();
  const fixed=getComputedStyle(popup).position==='fixed',bounds=fixed?{left:0,top:0,width:innerWidth,height:innerHeight}:wrap;
  let left=anchor.right-bounds.left+14,top=anchor.top-bounds.top-popup.offsetHeight/2;
  if(left+popup.offsetWidth>bounds.width-8)left=anchor.left-bounds.left-popup.offsetWidth-14;
  popup.style.left=Math.max(8,Math.min(left,bounds.width-popup.offsetWidth-8))+'px';
  popup.style.top=Math.max(8,Math.min(top,bounds.height-popup.offsetHeight-8))+'px';
}
function svg(tag,attrs={},text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;}
function plot(rows){
  hideDetails();const root=$('plot');root.replaceChildren();const x=$('x').value,y=$('y').value;
  const points=rows.filter(r=>defined(r[x])&&defined(r[y]));
  if(!points.length){root.append(svg('text',{x:600,y:260,'text-anchor':'middle',class:'empty'},'No measured points for these filters and axes.'));return;}
  const scale = key => {
    const peak=Math.max(...points.map(r=>r[key]),0),raw=(peak||1)*1.1/5;
    const magnitude=10**Math.floor(Math.log10(raw)),fraction=raw/magnitude;
    let step=([1,2,5,10].find(n=>n>=fraction)||10)*magnitude;
    if(key.endsWith('_tokens'))step=Math.max(1,step);
    const count=Math.max(1,Math.ceil(peak*1.1/step));
    return {step,count,max:count*step};
  };
  const sx=scale(x),sy=scale(y),maxX=sx.max,maxY=sy.max;
  const tick = (key,value,step) => {
    const decimals=Math.max(0,-Math.floor(Math.log10(step)));
    const formatted=new Intl.NumberFormat('en',{maximumFractionDigits:Math.min(8,decimals)}).format(value);
    return key==='cost_usd'?'$'+formatted:formatted;
  };
  const left=120,right=1160,top=30,bottom=485;
  for(let i=0;i<=sx.count;i++){
    const a=left+(right-left)*i/sx.count;
    root.append(svg('line',{x1:a,x2:a,y1:top,y2:bottom,class:'grid'}),svg('text',{x:a,y:bottom+30,'text-anchor':'middle',class:'tick'},tick(x,sx.step*i,sx.step)));
  }
  for(let i=0;i<=sy.count;i++){
    const b=bottom-(bottom-top)*i/sy.count;
    root.append(svg('line',{x1:left,x2:right,y1:b,y2:b,class:'grid'}),svg('text',{x:left-14,y:b+6,'text-anchor':'end',class:'tick'},tick(y,sy.step*i,sy.step)));
  }
  root.append(svg('text',{x:630,y:545,'text-anchor':'middle',class:'axis-label'},metrics[x]),svg('text',{transform:'translate(20 260) rotate(-90)','text-anchor':'middle',class:'axis-label'},metrics[y]));
  const labelLayer=svg('g'),pointLayer=svg('g');root.append(labelLayer,pointLayer);
  for(const r of points){
    const px=left+r[x]/maxX*(right-left),py=bottom-r[y]/maxY*(bottom-top),color=pointColor(r);
    if($('labels').checked)labelLayer.append(svg('text',{x:px+12,y:py+4,fill:color,class:'model-label'},r.model));
    const dot=svg('circle',{cx:px,cy:py,r:7,fill:color,class:'point',tabindex:0,role:'button','aria-label':`${r.model}, ${r.task_id}, ${r.difficulty}, ${r.completion===1?'Pass':'Fail'}`,'aria-describedby':'tooltip'});
    dot.addEventListener('pointerenter',()=>details(r,dot));dot.addEventListener('pointerleave',()=>{if(document.activeElement!==dot)hideDetails();});
    dot.addEventListener('focus',()=>details(r,dot));dot.addEventListener('blur',hideDetails);
    dot.addEventListener('click',()=>details(r,dot));dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();details(r,dot);}if(e.key==='Escape')hideDetails();});
    pointLayer.append(dot);
  }
}
function modelSummary(){
  const boxes=[...$('model-options').querySelectorAll('input')],count=boxes.filter(b=>b.checked).length;
  $('models-summary').textContent=count===0?'No models':count===boxes.length?'All models':`${count} model${count===1?'':'s'}`;
}
function buildModels(){
  const models=[...new Map(data.rows.map(r=>[modelKey(r),{provider:r.provider,model:r.model}])).values()].sort((a,b)=>(a.provider==='codex'?-1:1)-(b.provider==='codex'?-1:1)||a.provider.localeCompare(b.provider)||a.model.localeCompare(b.model));
  const keys=models.map(modelKey),current=[...$('model-options').querySelectorAll('input')].map(b=>b.value);
  if(JSON.stringify(keys)===JSON.stringify(current))return;
  $('model-options').replaceChildren();
  for(const provider of [...new Set(models.map(m=>m.provider))]){
    const group=el('fieldset'),legend=el('legend',provider==='codex'?'Codex':provider==='claude'?'Claude Code':provider,provider==='codex'?'codex-key':'claude-key');group.append(legend);
    for(const model of models.filter(m=>m.provider===provider)){
      const key=modelKey(model);if(!modelSelections.has(key))modelSelections.set(key,true);
      const label=el('label',undefined,'model-option'),input=el('input');input.type='checkbox';input.value=key;input.checked=modelSelections.get(key);input.style.accentColor=colors[provider]||'#aaa';
      input.addEventListener('change',()=>{modelSelections.set(key,input.checked);modelSummary();render();});
      label.append(input,el('span',model.model));group.append(label);
    }
    $('model-options').append(group);
  }
  modelSummary();
}
function buildTasks(){
  const rank={easy:0,medium:1,hard:2};
  const tasks=[...new Map(data.rows.map(r=>[taskKey(r),r])).values()].sort((a,b)=>(rank[a.difficulty]??3)-(rank[b.difficulty]??3)||a.task_id.localeCompare(b.task_id));
  const keys=tasks.map(taskKey),current=[...$('task-options').querySelectorAll('input')].map(b=>b.value);
  if(JSON.stringify(keys)===JSON.stringify(current))return;
  $('task-options').replaceChildren();
  const summary=()=>{const boxes=[...$('task-options').querySelectorAll('input')],count=boxes.filter(b=>b.checked).length;$('tasks-summary').textContent=count===0?'No tasks':count===boxes.length?'All tasks':`${count} task${count===1?'':'s'}`;};
  for(const difficulty of [...new Set(tasks.map(t=>t.difficulty))]){
    const group=el('fieldset');group.append(el('legend',difficulty?difficulty[0].toUpperCase()+difficulty.slice(1):'Unspecified'));
    for(const task of tasks.filter(t=>t.difficulty===difficulty)){
      const key=taskKey(task);if(!taskSelections.has(key))taskSelections.set(key,true);
      const label=el('label',undefined,'model-option'),input=el('input');input.type='checkbox';input.value=key;input.checked=taskSelections.get(key);
      input.addEventListener('change',()=>{taskSelections.set(key,input.checked);summary();render();});
      label.append(input,el('span',task.task_id));group.append(label);
    }
    $('task-options').append(group);
  }
  summary();
}
function taskTable(rows){
  const body=$('task-summaries');body.replaceChildren();
  const visible=new Set(rows.map(r=>JSON.stringify([r.source_run||'',taskKey(r)]))),seen=new Set();
  const tasks=(data.tasks||[]).filter(t=>visible.has(JSON.stringify([t.source_run||'',taskKey(t)])));
  for(const task of tasks.sort((a,b)=>a.task_id.localeCompare(b.task_id))){
    const key=JSON.stringify([task.task_id,task.difficulty,task.use_case,task.description]);if(seen.has(key))continue;seen.add(key);
    const row=el('tr');for(const value of [task.task_id,task.description||'Not recorded',task.difficulty||'Not recorded',task.use_case||'Not recorded'])row.append(el('td',value));body.append(row);
  }
  if(!seen.size){const row=el('tr'),cell=el('td','No tasks selected.');cell.colSpan=4;row.append(cell);body.append(row);}
}
function render(){if(data){const rows=filtered();plot(rows);taskTable(rows);}}
async function load(){
  try{
    const r=await fetch('/api/results');if(!r.ok)throw new Error(`Results request failed (${r.status})`);
    const next=await r.json(),unchanged=data&&JSON.stringify(data)===JSON.stringify(next);data=next;
    const simulated=data.run.simulation||data.rows.some(r=>r.simulation);
    $('banner').hidden=!simulated&&!data.run.stop_reason;
    $('banner').textContent=simulated?'Demo data — synthetic interface fixtures.':`Run stopped: ${data.run.stop_reason}.`;
    if(unchanged)return;
    buildModels();buildTasks();
    render();
  }catch(e){$('banner').hidden=false;$('banner').textContent=e.message;}
}
for(const id of ['x','y','labels'])$(id).addEventListener('change',render);
document.addEventListener('keydown',e=>{if(e.key==='Escape'){hideDetails();$('models-menu').open=false;$('tasks-menu').open=false;}});
window.addEventListener('resize',hideDetails);document.addEventListener('pointerdown',e=>{if(!e.target.closest('.point'))hideDetails();if(!e.target.closest('#models-menu'))$('models-menu').open=false;if(!e.target.closest('#tasks-menu'))$('tasks-menu').open=false;});
load();setInterval(load,15000);
