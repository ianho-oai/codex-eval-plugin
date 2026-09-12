'use strict';
const $ = id => document.getElementById(id);
const metrics = {
  cost_usd:'Total cost · USD', latency_seconds:'End-to-end latency · s',
  input_tokens:'Total input tokens', output_tokens:'Output tokens', cache_read_tokens:'Cache read tokens'
};
let data = null;
const modelSelections=new Map(),taskSelections=new Map();
const taskKey=r=>JSON.stringify([r.task_id,r.difficulty]);
const modelLabel=r=>`${r.model} · ${r.effort||'default'}`;
const modelKey=r=>JSON.stringify([r.provider,r.model]);
const defined = x => typeof x === 'number' && Number.isFinite(x);
const money = x => defined(x) ? '$'+x.toFixed(4) : 'Unavailable';
const num = x => defined(x) ? new Intl.NumberFormat('en',{maximumFractionDigits:1}).format(x) : '—';
function el(tag,text,className){const e=document.createElement(tag); if(text !== undefined)e.textContent=text;if(className)e.className=className;return e;}
function option(select,value,label){const o=el('option',label);o.value=value;select.append(o);}
for(const [key,label] of Object.entries(metrics)){option($('x'),key,label);option($('y'),key,label);}
$('x').value='cost_usd';$('y').value='latency_seconds';
function filtered(rows=data.averages||data.rows){return rows.filter(r=>taskSelections.get(taskKey(r))&&modelSelections.get(modelKey(r)));}
const colors={codex:'#339cff',claude:'#eaa582'};
const pointColor=r=>(r.successes??r.completion)>0?(colors[r.provider]||'#ccc'):'#a3a3a3';
const resultLabel=r=>r.attempts!==undefined?`${r.status==='pending'?'Pending':r.completion===1?'Pass':'Fail'} · ${r.successes}/${r.attempts} passed${r.attempts<r.expected_attempts?`, ${r.attempts}/${r.expected_attempts} run`:''}`:(r.completion===1?'Pass':'Fail');
function hideDetails(){ $('tooltip').hidden=true; }
function details(r,dot){
  const popup=$('tooltip');popup.replaceChildren();popup.style.setProperty('--point-color',pointColor(r));
  const list=el('dl');
  const formatMetric=key=>key==='cost_usd'?money(r[key]):num(r[key])+(key==='latency_seconds'?' s':'');
  const fields=r.median?[['Model',r.model],['Summary',`Median of ${r.point_count} task/configuration averages`],['Tasks',String(r.task_count)],['Results',medianStatusLabel(r)],['Reasoning effort',r.effort],[metrics[$('x').value],formatMetric($('x').value)],[metrics[$('y').value],formatMetric($('y').value)]]:
    [['Model',modelLabel(r)],['Task',r.task_id],['Difficulty',r.difficulty||'Unavailable'],['Result',resultLabel(r)],['Average cost',money(r.cost_usd)],['Average latency',defined(r.latency_seconds)?num(r.latency_seconds)+' s':'Unavailable']];
  for(const [label,value] of fields){
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
function plot(rows,showMedians){
  hideDetails();const root=$('plot');root.replaceChildren();const x=$('x').value,y=$('y').value;
  const logX=$('log-x').checked,logY=$('log-y').checked;
  const measured=rows.filter(r=>defined(r[x])&&defined(r[y]));
  const focus=showMedians&&$('median-focus').checked;
  const medians=focus?modelMedians(rows,x,y):[];
  root.classList.toggle('median-focus',focus);
  const points=measured.filter(r=>(!logX||r[x]>0)&&(!logY||r[y]>0));
  const medianPoints=medians.filter(r=>(!logX||r[x]>0)&&(!logY||r[y]>0));
  const omitted=measured.length-points.length;
  const omittedMedians=medians.length-medianPoints.length;
  $('plot-note').hidden=!(omitted||omittedMedians);
  $('plot-note').textContent=`${omitted} task point${omitted===1?'':'s'} and ${omittedMedians} median${omittedMedians===1?'':'s'} with zero or negative values cannot appear on a logarithmic axis.`;
  if(!points.length&&!medianPoints.length){root.append(svg('text',{x:600,y:260,'text-anchor':'middle',class:'empty'},measured.length&&omitted?'Log scales require positive values.':'No measured points for these filters and axes.'));return;}
  const scale = (key,log) => {
    const values=[...points,...medianPoints].map(r=>r[key]);
    if(log){
      const low=Math.floor(Math.log10(Math.min(...values))),high=Math.max(low+1,Math.ceil(Math.log10(Math.max(...values))));
      const stride=Math.max(1,Math.ceil((high-low)/6)),ticks=[];
      for(let power=low;power<=high;power+=stride)ticks.push(10**power);
      if(ticks.at(-1)!==10**high)ticks.push(10**high);
      return {ticks,step:null,position:value=>(Math.log10(value)-low)/(high-low)};
    }
    const peak=Math.max(...values,0),raw=(peak||1)*1.1/5;
    const magnitude=10**Math.floor(Math.log10(raw)),fraction=raw/magnitude;
    let step=([1,2,5,10].find(n=>n>=fraction)||10)*magnitude;
    if(key.endsWith('_tokens'))step=Math.max(1,step);
    const count=Math.max(1,Math.ceil(peak*1.1/step)),max=count*step;
    return {step,ticks:Array.from({length:count+1},(_,i)=>i*step),position:value=>value/max};
  };
  const sx=scale(x,logX),sy=scale(y,logY);
  const tick = (key,value,step) => {
    const decimals=Math.max(0,-Math.floor(Math.log10(step||value||1)));
    const formatted=value!==0&&(Math.abs(value)<.00001||Math.abs(value)>=1e8)?value.toExponential(0):new Intl.NumberFormat('en',{maximumFractionDigits:Math.min(8,decimals)}).format(value);
    return key==='cost_usd'?'$'+formatted:formatted;
  };
  const left=120,right=1160,top=30,bottom=485;
  for(const value of sx.ticks){
    const a=left+(right-left)*sx.position(value);
    root.append(svg('line',{x1:a,x2:a,y1:top,y2:bottom,class:'grid'}),svg('text',{x:a,y:bottom+30,'text-anchor':'middle',class:'tick'},tick(x,value,sx.step)));
  }
  for(const value of sy.ticks){
    const b=bottom-(bottom-top)*sy.position(value);
    root.append(svg('line',{x1:left,x2:right,y1:b,y2:b,class:'grid'}),svg('text',{x:left-14,y:b+6,'text-anchor':'end',class:'tick'},tick(y,value,sy.step)));
  }
  root.append(svg('text',{x:630,y:545,'text-anchor':'middle',class:'axis-label'},'Average '+metrics[x].toLowerCase()+(logX?' · log':'')),svg('text',{transform:'translate(20 260) rotate(-90)','text-anchor':'middle',class:'axis-label'},'Average '+metrics[y].toLowerCase()+(logY?' · log':'')));
  const labelLayer=svg('g',{class:'task-label-layer'}),pointLayer=svg('g',{class:'task-point-layer'}),medianLayer=svg('g',{class:'median-layer'});root.append(labelLayer,pointLayer,medianLayer);
  for(const r of [...points,...medianPoints]){
    const px=left+sx.position(r[x])*(right-left),py=bottom-sy.position(r[y])*(bottom-top),color=pointColor(r);
    const label=modelLabel(r),size=focus?13:9;
    if($('labels').checked)(r.median?medianLayer:labelLayer).append(svg('text',{x:px+(r.median?size+7:12),y:py+4,fill:color,class:r.median?'model-label median-label':'model-label'},label));
    const shape=r.median?{d:`M ${px} ${py-size} L ${px+size} ${py} L ${px} ${py+size} L ${px-size} ${py} Z`}:{cx:px,cy:py,r:7};
    const dot=svg(r.median?'path':'circle',{...shape,fill:color,class:r.median?'point median-point':'point',tabindex:0,role:'button','aria-label':r.median?`${modelLabel(r)}, median of ${r.point_count} task/configuration averages, ${medianStatusLabel(r)}`:`${modelLabel(r)}, ${r.task_id}, ${r.difficulty}, ${resultLabel(r)}`,'aria-describedby':'tooltip'});
    dot.addEventListener('pointerenter',()=>details(r,dot));dot.addEventListener('pointerleave',()=>{if(document.activeElement!==dot)hideDetails();});
    dot.addEventListener('focus',()=>details(r,dot));dot.addEventListener('blur',hideDetails);
    dot.addEventListener('click',()=>details(r,dot));dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();details(r,dot);}if(e.key==='Escape')hideDetails();});
    (r.median?medianLayer:pointLayer).append(dot);
    if(r.median){
      const cy=py-size-8,radius=5;
      const badge=svg('g',{class:'median-status','aria-hidden':'true','pointer-events':'none'});
      const fill=r.result_status==='passed'?'#48c78e':r.result_status==='failed'?'#ef6b73':r.result_status==='mixed'?'#ef6b73':'#a3a3a3';
      badge.append(svg('circle',{cx:px,cy,r:radius,fill}));
      if(r.result_status==='mixed')badge.append(svg('path',{d:`M ${px} ${cy-radius} A ${radius} ${radius} 0 0 0 ${px} ${cy+radius} Z`,fill:'#48c78e'}));
      badge.append(svg('circle',{cx:px,cy,r:radius,fill:'none',stroke:'#171717','stroke-width':1}));
      medianLayer.append(badge);
    }
  }
}
function bulkControls(container,selections,update,unit){
  const controls=[];
  function add(parent,choices,title,before){
    const label=el('label',undefined,'model-option bulk-option'),input=el('input');input.type='checkbox';
    label.append(input,el('span',title));parent.insertBefore(label,before);
    controls.push({input,choices});
    input.addEventListener('change',()=>{for(const choice of choices){choice.checked=input.checked;selections.set(choice.value,input.checked);}update();sync();render();});
  }
  function sync(){for(const {input,choices} of controls){const count=choices.filter(c=>c.checked).length;input.checked=count===choices.length&&count>0;input.indeterminate=count>0&&count<choices.length;}}
  const choices=[...container.querySelectorAll('input.choice')];
  add(container,choices,`Select all ${unit}`,container.firstChild);
  for(const group of container.querySelectorAll('fieldset'))add(group,[...group.querySelectorAll('input.choice')],`Select all ${group.querySelector('legend').textContent} ${unit}`,group.querySelector('legend').nextSibling);
  for(const choice of choices)choice.addEventListener('change',sync);
  sync();
}
function modelSummary(){
  const boxes=[...$('model-options').querySelectorAll('input.choice')],count=boxes.filter(b=>b.checked).length;
  $('models-summary').textContent=count===0?'No models':count===boxes.length?'All models':`${count} model${count===1?'':'s'}`;
}
function buildModels(){
  const models=[...new Map(data.rows.map(r=>[modelKey(r),{provider:r.provider,model:r.model}])).values()].sort((a,b)=>(a.provider==='codex'?-1:1)-(b.provider==='codex'?-1:1)||a.provider.localeCompare(b.provider)||a.model.localeCompare(b.model));
  const keys=models.map(modelKey),current=[...$('model-options').querySelectorAll('input.choice')].map(b=>b.value);
  if(JSON.stringify(keys)===JSON.stringify(current))return;
  $('model-options').replaceChildren();
  for(const provider of [...new Set(models.map(m=>m.provider))]){
    const group=el('fieldset'),legend=el('legend',provider==='codex'?'Codex':provider==='claude'?'Claude Code':provider,provider==='codex'?'codex-key':'claude-key');group.dataset.provider=provider;group.append(legend);
    for(const model of models.filter(m=>m.provider===provider)){
      const key=modelKey(model);if(!modelSelections.has(key))modelSelections.set(key,true);
      const label=el('label',undefined,'model-option'),input=el('input');input.type='checkbox';input.className='choice';input.value=key;input.checked=modelSelections.get(key);input.style.accentColor=colors[provider]||'#aaa';
      input.addEventListener('change',()=>{modelSelections.set(key,input.checked);modelSummary();render();});
      label.append(input,el('span',model.model));group.append(label);
    }
    $('model-options').append(group);
  }
  modelSummary();bulkControls($('model-options'),modelSelections,modelSummary,'models');
}
function buildTasks(){
  const rank={easy:0,medium:1,hard:2};
  const tasks=[...new Map(data.rows.map(r=>[taskKey(r),r])).values()].sort((a,b)=>(rank[a.difficulty]??3)-(rank[b.difficulty]??3)||a.task_id.localeCompare(b.task_id));
  const keys=tasks.map(taskKey),current=[...$('task-options').querySelectorAll('input.choice')].map(b=>b.value);
  if(JSON.stringify(keys)===JSON.stringify(current))return;
  $('task-options').replaceChildren();
  const summary=()=>{const boxes=[...$('task-options').querySelectorAll('input.choice')],count=boxes.filter(b=>b.checked).length;$('tasks-summary').textContent=count===0?'No tasks':count===boxes.length?'All tasks':`${count} task${count===1?'':'s'}`;};
  for(const difficulty of [...new Set(tasks.map(t=>t.difficulty))]){
    const group=el('fieldset');group.append(el('legend',difficulty?difficulty[0].toUpperCase()+difficulty.slice(1):'Unspecified'));
    for(const task of tasks.filter(t=>t.difficulty===difficulty)){
      const key=taskKey(task);if(!taskSelections.has(key))taskSelections.set(key,true);
      const label=el('label',undefined,'model-option'),input=el('input');input.type='checkbox';input.className='choice';input.value=key;input.checked=taskSelections.get(key);
      input.addEventListener('change',()=>{taskSelections.set(key,input.checked);summary();render();});
      label.append(input,el('span',task.task_id));group.append(label);
    }
    $('task-options').append(group);
  }
  summary();bulkControls($('task-options'),taskSelections,summary,'tasks');
}
function taskTable(rows){
  const body=$('task-summaries');body.replaceChildren();
  const visible=new Set(rows.map(r=>JSON.stringify([r.source_run||'',taskKey(r)]))),seen=new Set();
  const tasks=(data.tasks||[]).filter(t=>visible.has(JSON.stringify([t.source_run||'',taskKey(t)])));
  for(const task of tasks.sort((a,b)=>a.task_id.localeCompare(b.task_id))){
    const key=JSON.stringify([task.task_id,task.difficulty,task.use_case,task.human_summary]);if(seen.has(key))continue;seen.add(key);
    const row=el('tr');for(const value of [task.task_id,task.human_summary||'A workflow summary was not recorded for this task.',task.difficulty||'Not recorded',task.use_case||'Not recorded'])row.append(el('td',value));body.append(row);
  }
  if(!seen.size){const row=el('tr'),cell=el('td','No tasks selected.');cell.colSpan=4;row.append(cell);body.append(row);}
}
function render(){
  if(!data)return;
  const showMedians=$('task-options').querySelectorAll('input.choice:checked').length>1;
  const focus=showMedians&&$('median-focus').checked;
  $('median-control').hidden=!showMedians;$('median-legend').hidden=!focus;$('task-legend').hidden=focus;
  const rows=filtered();plot(rows,showMedians);taskTable(filtered(data.rows));
}
async function load(){
  try{
    const r=await fetch('/api/results');if(!r.ok)throw new Error(`Results request failed (${r.status})`);
    const next=await r.json(),unchanged=data&&JSON.stringify(data)===JSON.stringify(next);data=next;
    const simulated=data.run.simulation||data.rows.some(r=>r.simulation);
    $('banner').hidden=!simulated;
    $('banner').textContent=simulated?'Demo data — synthetic interface fixtures.':'';
    if(unchanged)return;
    buildModels();buildTasks();
    render();
  }catch(e){$('banner').hidden=false;$('banner').textContent=e.message;}
}
for(const id of ['x','y','labels','median-focus','log-x','log-y'])$(id).addEventListener('change',render);
document.addEventListener('keydown',e=>{if(e.key==='Escape'){hideDetails();$('models-menu').open=false;$('tasks-menu').open=false;}});
window.addEventListener('resize',hideDetails);document.addEventListener('pointerdown',e=>{if(!e.target.closest('.point'))hideDetails();if(!e.target.closest('#models-menu'))$('models-menu').open=false;if(!e.target.closest('#tasks-menu'))$('tasks-menu').open=false;});
load();setInterval(load,15000);
