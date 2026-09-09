'use strict';
const $ = id => document.getElementById(id);
const metrics = {
  cost_usd:'Total cost · USD', latency_seconds:'End-to-end latency · s', agent_seconds:'Agent latency · s', grader_seconds:'Grader latency · s',
  input_tokens:'Total input tokens', uncached_input_tokens:'Uncached input tokens', output_tokens:'Output tokens',
  cache_read_tokens:'Cache read tokens', cache_write_tokens:'Cache write tokens', reasoning_tokens:'Reasoning tokens',
  turns:'Native turns · units differ', tool_calls:'Native tool calls', cost_upper_usd:'Cost upper envelope · USD'
};
let data = null;
const defined = x => typeof x === 'number' && Number.isFinite(x);
const money = x => defined(x) ? '$'+x.toFixed(4) : 'Unavailable';
const num = x => defined(x) ? new Intl.NumberFormat('en',{maximumFractionDigits:1}).format(x) : '—';
function el(tag,text,className){const e=document.createElement(tag); if(text !== undefined)e.textContent=text;if(className)e.className=className;return e;}
function option(select,value,label){const o=el('option',label);o.value=value;select.append(o);}
for(const [key,label] of Object.entries(metrics)){option($('x'),key,label);option($('y'),key,label);}
$('x').value='cost_usd';$('y').value='latency_seconds';
function filtered(){return data.rows.filter(r=>(!$('task').value||r.task_id===$('task').value)&&(!$('provider').value||r.provider===$('provider').value)&&(!$('difficulty').value||r.difficulty===$('difficulty').value)&&(!$('outcome').value||($('outcome').value==='pass'?r.completion===1:$('outcome').value==='invalid'?!r.valid:r.completion===0)));}
const colors={codex:'#339cff',claude:'#eaa582'};
function hideDetails(){ $('tooltip').hidden=true; }
function details(r,dot){
  const popup=$('tooltip');popup.replaceChildren();popup.style.setProperty('--point-color',colors[r.provider]||'#eee');
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
  const maxX=Math.max(...points.map(r=>r[x]),.001)*1.2,maxY=Math.max(...points.map(r=>r[y]),.001)*1.2;
  const left=100,right=1160,top=30,bottom=485;
  for(let i=0;i<=5;i++){
    const a=left+(right-left)*i/5,b=bottom-(bottom-top)*i/5;
    root.append(svg('line',{x1:a,x2:a,y1:top,y2:bottom,class:'grid'}),svg('line',{x1:left,x2:right,y1:b,y2:b,class:'grid'}));
    root.append(svg('text',{x:a,y:bottom+25,'text-anchor':'middle',class:'tick'},x.includes('cost')?money(maxX*i/5):num(maxX*i/5)));
    root.append(svg('text',{x:left-14,y:b+4,'text-anchor':'end',class:'tick'},y.includes('cost')?money(maxY*i/5):num(maxY*i/5)));
  }
  root.append(svg('text',{x:630,y:545,'text-anchor':'middle',class:'axis-label'},metrics[x]),svg('text',{transform:'translate(20 260) rotate(-90)','text-anchor':'middle',class:'axis-label'},metrics[y]));
  const placed=[],coords=points.map(r=>({r,px:left+r[x]/maxX*(right-left),py:bottom-r[y]/maxY*(bottom-top)}));
  const labelLayer=svg('g'),pointLayer=svg('g');root.append(labelLayer,pointLayer);
  for(const {r,px,py} of coords){
    const color=colors[r.provider]||'#ccc';
    const label=svg('text',{fill:color,class:'model-label'},r.model);labelLayer.append(label);
    const width=label.getComputedTextLength()+4,height=16;let best=null;
    for(let step=0;step<16;step++)for(const sign of (step?[1,-1]:[1]))for(const side of [1,-1]){
      const lx=side===1?px+13:px-width-13,ly=py+4+step*18*sign;
      const box={x:lx,y:ly-12,w:width,h:height};
      if(box.x<left||box.x+width>right||box.y<top||box.y+height>bottom)continue;
      const hits=placed.filter(b=>box.x<b.x+b.w+3&&box.x+box.w+3>b.x&&box.y<b.y+b.h+3&&box.y+box.h+3>b.y).length;
      const covers=coords.filter(p=>p.px>box.x-8&&p.px<box.x+width+8&&p.py>box.y-8&&p.py<box.y+height+8).length;
      const score=hits*10000+covers*1000+step*18+(side===-1?2:0);
      if(!best||score<best.score)best={...box,ly,side,score};
    }
    best=best||{x:px+13,y:py-12,w:width,h:height,ly:py+4,side:1};placed.push(best);
    label.setAttribute('x',best.x);label.setAttribute('y',best.ly);
    if(Math.abs(best.ly-py-4)>18)labelLayer.insertBefore(svg('line',{x1:px,y1:py,x2:best.side===1?best.x-3:best.x+width+3,y2:best.ly-4,stroke:color,class:'leader'}),label);
    const dot=svg('circle',{cx:px,cy:py,r:7,fill:color,class:'point',tabindex:0,role:'button','aria-label':`${r.model}, ${r.task_id}, ${r.difficulty}, ${r.completion===1?'Pass':'Fail'}`,'aria-describedby':'tooltip'});
    dot.addEventListener('pointerenter',()=>details(r,dot));dot.addEventListener('pointerleave',()=>{if(document.activeElement!==dot)hideDetails();});
    dot.addEventListener('focus',()=>details(r,dot));dot.addEventListener('blur',hideDetails);
    dot.addEventListener('click',()=>details(r,dot));dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();details(r,dot);}if(e.key==='Escape')hideDetails();});
    pointLayer.append(dot);
  }
}
function render(){if(data)plot(filtered());}
async function load(){
  try{
    const r=await fetch('/api/results');if(!r.ok)throw new Error(`Results request failed (${r.status})`);
    const next=await r.json(),unchanged=data&&JSON.stringify(data)===JSON.stringify(next);data=next;
    const simulated=data.run.simulation||data.rows.some(r=>r.simulation);
    $('banner').hidden=!simulated&&!data.run.stop_reason;
    $('banner').textContent=simulated?'Demo data — synthetic interface fixtures.':`Run stopped: ${data.run.stop_reason}.`;
    if(unchanged)return;
    const selected=$('task').value;$('task').replaceChildren();option($('task'),'','All tasks');[...new Set(data.rows.map(r=>r.task_id))].sort().forEach(t=>option($('task'),t,t));
    if([...$('task').options].some(o=>o.value===selected))$('task').value=selected;
    render();
  }catch(e){$('banner').hidden=false;$('banner').textContent=e.message;}
}
for(const id of ['task','provider','difficulty','outcome','x','y'])$(id).addEventListener('change',render);
document.addEventListener('keydown',e=>{if(e.key==='Escape')hideDetails();});
window.addEventListener('resize',hideDetails);document.addEventListener('pointerdown',e=>{if(!e.target.closest('.point'))hideDetails();});
load();setInterval(load,15000);
