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
function details(r){
  const tokens=`Input ${num(r.input_tokens)} · Output ${num(r.output_tokens)} · Cache read ${num(r.cache_read_tokens)} · Cache write ${num(r.cache_write_tokens)} · Reasoning ${num(r.reasoning_tokens)}`;
  $('detail').textContent=`${r.task_id} / ${r.model} / ${r.effort} / repeat ${r.repeat}: ${r.completion?'PASS':'FAIL'} (${r.status}). ${num(r.latency_seconds)}s end to end; ${money(r.cost_usd)} — ${r.cost_source||'unavailable'}. Cost envelope ${money(r.cost_lower_usd)}–${money(r.cost_upper_usd)}. ${tokens}. Turns ${num(r.turns)} (${r.turn_unit||'unknown unit'}). ${r.cost_note||''} ${r.diagnostic||''}${r.source_run?' Source run: '+r.source_run:''}`;
}
function svg(tag,attrs={},text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;}
function plot(rows){
  const root=$('plot');root.replaceChildren();const x=$('x').value,y=$('y').value;
  const points=rows.filter(r=>defined(r[x])&&defined(r[y]));
  $('plotcount').textContent=`${points.length} plotted · ${rows.length-points.length} missing measurements`;
  $('plotnote').textContent=(x==='turns'||y==='turns'?'Turn counts use different native units; compare within each provider. ':'')+'Missing measurements remain in the table. PASS and FAIL are labeled on every point; select a point for provenance.';
  if(!points.length){root.append(svg('text',{x:500,y:210,'text-anchor':'middle',class:'empty'},'No measured points for these filters and axes.'));return;}
  const maxX=Math.max(...points.map(r=>r[x]),.001)*1.18,maxY=Math.max(...points.map(r=>r[y]),.001)*1.16;
  const left=90,right=955,top=28,bottom=370;
  for(let i=0;i<=5;i++){
    const a=left+(right-left)*i/5,b=bottom-(bottom-top)*i/5;
    root.append(svg('line',{x1:a,x2:a,y1:top,y2:bottom,class:'grid'}));
    root.append(svg('line',{x1:left,x2:right,y1:b,y2:b,class:'grid'}));
    root.append(svg('text',{x:a,y:bottom+24,'text-anchor':'middle',class:'tick'},x.includes('cost')?money(maxX*i/5):num(maxX*i/5)));
    root.append(svg('text',{x:left-13,y:b+4,'text-anchor':'end',class:'tick'},y.includes('cost')?money(maxY*i/5):num(maxY*i/5)));
  }
  root.append(svg('text',{x:520,y:426,'text-anchor':'middle',class:'axis-label'},metrics[x]));
  root.append(svg('text',{transform:'translate(18 210) rotate(-90)','text-anchor':'middle',class:'axis-label'},metrics[y]));
  points.forEach(r=>{
    const px=left+r[x]/maxX*(right-left),py=bottom-r[y]/maxY*(bottom-top),color=r.provider==='codex'?'#ececec':'#eaa582';
    const dot=svg('circle',{cx:px,cy:py,r:7,fill:color,class:'point',tabindex:0,role:'button','aria-label':`${r.model} ${r.task_id} repeat ${r.repeat} ${r.completion?'PASS':'FAIL'}`});
    dot.append(svg('title',{},`${r.model} / ${r.effort} / ${r.task_id}: ${r.status}`));
    dot.addEventListener('click',()=>details(r));dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();details(r);}});
    root.append(dot,svg('text',{x:px+10,y:py+3,fill:color,class:'outcome-label'},r.completion?'PASS':'FAIL'));
  });
}
function table(rows){
  const body=$('attempts').querySelector('tbody');body.replaceChildren();
  $('rowcount').textContent=`${rows.length} attempts match the current filters. No failed attempts are hidden by default.`;
  for(const r of rows){
    const tr=el('tr');tr.tabIndex=0;tr.addEventListener('click',()=>details(r));tr.addEventListener('keydown',e=>{if(e.key==='Enter')details(r);});
    const t=el('td',r.task_id);t.append(el('small',r.difficulty||'—'));
    const m=el('td',r.model);m.append(el('small',`${r.provider} / ${r.effort}`));
    if(r.source_run)m.append(el('small',r.source_run));
    const out=el('td');out.append(el('span',r.completion?'PASS':'FAIL','badge'+(r.valid?(r.completion?'':' fail'):' invalid')),el('small',r.status));
    const cost=el('td',money(r.cost_usd));cost.append(el('small',r.cost_source||'unavailable'));
    const turns=el('td',num(r.turns));turns.append(el('small',r.turn_unit==='codex_conversation_turn'?'conversation':'native'));
    tr.append(t,m,el('td',r.repeat),out,el('td',defined(r.latency_seconds)?num(r.latency_seconds)+'s':'—'),cost,el('td',num(r.input_tokens)),el('td',num(r.output_tokens)),el('td',num(r.cache_read_tokens)),turns);body.append(tr);
  }
  if(!rows.length){const tr=el('tr');const td=el('td','No attempts match these filters.','empty-row');td.colSpan=10;tr.append(td);body.append(tr);}
  const groupBody=$('groups').querySelector('tbody');groupBody.replaceChildren();
  const groups=new Map();for(const r of rows){const k=[r.provider,r.model,r.effort].join(' / ');if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r);}
  for(const [key,rs] of groups){const wins=rs.filter(r=>r.completion===1).length,valid=rs.filter(r=>r.valid).length,known=rs.filter(r=>defined(r.cost_usd)),cost=known.reduce((a,r)=>a+r.cost_usd,0);const tr=el('tr');tr.append(el('td',key),el('td',`${wins} / ${rs.length}`),el('td',valid),el('td',rs.length-valid),el('td',money(cost)+(known.length<rs.length?` (${rs.length-known.length} missing)` :'')),el('td',wins&&known.length===rs.length?money(cost/wins):'Unavailable'));groupBody.append(tr);}
}
function render(){
  const rows=filtered();plot(rows);table(rows);
  const wins=rows.filter(r=>r.completion===1).length,invalid=rows.filter(r=>!r.valid).length;
  const costs=rows.filter(r=>defined(r.cost_usd));const stats=[['Verified completion',`${wins} / ${rows.length}`,'Binary outcome · current filters'],['Scheduled / pending',`${data.summary.scheduled} / ${data.summary.pending}`,'Whole run · planned matrix'],['Known total cost',money(costs.reduce((a,r)=>a+r.cost_usd,0)),`${rows.length-costs.length} attempts with unavailable cost`],['Infrastructure invalid',invalid,'Included in all-attempt count']];
  $('stats').replaceChildren(...stats.map(([label,value,note])=>{const box=el('div',undefined,'stat');box.append(el('small',label),el('strong',value),el('p',note));return box;}));
}
async function load(){
  try {
    const r=await fetch('/api/results');if(!r.ok)throw new Error(`Results request failed (${r.status})`);data=await r.json();
    const selected=$('task').value;$('task').replaceChildren();option($('task'),'','All tasks');[...new Set(data.rows.map(r=>r.task_id))].sort().forEach(t=>option($('task'),t,t));$('task').value=selected;
    $('runname').textContent=data.run.suite.name;$('state').textContent=data.run.state||'unknown';
    $('subtitle').textContent='Compare verified task completion, time, tokens, and cost across native coding agents.';
    const simulated=data.run.simulation||data.rows.some(r=>r.simulation);
    $('banner').hidden=!simulated&&!data.run.stop_reason;
    $('banner').textContent=simulated?'DEMO DATA — These points are synthetic interface fixtures. They are not model benchmark results.':`Run stopped: ${data.run.stop_reason}. Pending cells have not been evaluated.`;
    const ex=data.run.suite.execution;
    $('environment').textContent=ex?`Environment: ${ex.mode}. ${ex.mode==='local'?'Trusted local development; host and grader isolation are not guaranteed.':`Image ${ex.image}.`} Codex ${ex.codex_version}; Claude Code ${ex.claude_version}.`:'Synthetic preview; no provider calls were made.';
    if(data.run.sources)$('environment').textContent=data.run.sources.map(s=>`${s.name}: ${s.execution?`${s.execution.mode}; Codex ${s.execution.codex_version}; Claude Code ${s.execution.claude_version}`:'synthetic preview'}`).join(' · ');
    const providers=new Set(data.rows.filter(r=>!r.not_started&&r.provider_success).map(r=>r.provider));
    $('coverage').textContent=[data.run.comparison_note,providers.size<2&&!simulated?'Live validation does not cover both providers. These results cannot establish a Codex-versus-Claude comparison.':''].filter(Boolean).join(' ');
    render();
  }catch(e){$('banner').hidden=false;$('banner').textContent=e.message;$('subtitle').textContent='Results could not be loaded.';}
}
for(const id of ['task','provider','difficulty','outcome','x','y'])$(id).addEventListener('change',render);
$('refresh').addEventListener('click',load);load();
setInterval(load, 15000);
