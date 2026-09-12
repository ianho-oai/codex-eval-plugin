'use strict';
// Each visible task/configuration average has equal weight. Compute in raw units,
// before log-axis clipping, so changing the scale never changes the statistic.
function modelMedians(rows, x, y) {
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const median = values => {
    const sorted = [...values].sort((a,b)=>a-b), middle = Math.floor(sorted.length/2);
    return sorted.length%2 ? sorted[middle] : (sorted[middle-1]+sorted[middle])/2;
  };
  const groups = new Map();
  for (const row of rows.filter(r=>finite(r[x])&&finite(r[y]))) {
    const key = JSON.stringify([row.provider,row.model,row.effort||'default']);
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(row);
  }
  return [...groups.values()].map(group=>{
    // Include selected results with missing axis telemetry in the pass/fail badge.
    const first=group[0];
    const all=rows.filter(r=>r.provider===first.provider&&r.model===first.model&&(r.effort||'default')===(first.effort||'default'));
    const successes=all.reduce((n,r)=>n+(r.successes??r.completion??0),0);
    const attempts=all.reduce((n,r)=>n+(r.attempts??1),0);
    const expected=all.reduce((n,r)=>n+(r.expected_attempts??r.attempts??1),0);
    return ({
    provider:group[0].provider, model:group[0].model, effort:group[0].effort||'default', median:true,
    point_count:group.length,
    task_count:new Set(group.map(r=>JSON.stringify([r.task_id,r.difficulty]))).size,
    successes, attempts, expected_attempts:expected,
    result_status:attempts<expected?'pending':successes===attempts?'passed':successes===0?'failed':'mixed',
    [x]:median(group.map(r=>r[x])), [y]:median(group.map(r=>r[y]))
  });});
}
function medianStatusLabel(r){
  return `${r.successes}/${r.attempts} runs passed${r.attempts<r.expected_attempts?`, ${r.expected_attempts-r.attempts} pending`:''}`;
}
if (typeof module !== 'undefined' && module.exports) module.exports = {modelMedians, medianStatusLabel};
