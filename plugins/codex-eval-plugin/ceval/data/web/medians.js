'use strict';
// Display projection only: retain native billing fields in reports and exports.
function chartCostRows(rows) {
  return rows.map(r=>r.provider==='copilot'?{...r,cost_usd:r.copilot_usage_value_usd??null}:r);
}
function costPerVerifiedSuccess(rows) {
  // Input costs are means over recorded repeats; reconstruct totals before dividing.
  const completed=rows.filter(r=>(r.attempts??1)>0);
  const successes=completed.reduce((n,r)=>n+(r.successes??r.completion??0),0);
  if(!successes||completed.some(r=>typeof r.cost_usd!=='number'||!Number.isFinite(r.cost_usd)||r.cost_usd<0))return null;
  const total=completed.reduce((n,r)=>n+r.cost_usd*(r.attempts??1),0);
  return Number.isFinite(total)?total/successes:null;
}
// Each visible task/configuration average has equal weight. Compute in raw units,
// before log-axis clipping, so changing the scale never changes the statistic.
function modelMedians(rows, x, y, grouping = 'model-effort') {
  const byModel = grouping === 'model';
  const groupKey = row => JSON.stringify([row.provider,row.model,...(byModel?[]:[row.effort||'default'])]);
  const scoreX = x === 'average_score', scoreY = y === 'average_score';
  const successCostX = x === 'cost_per_success_usd', successCostY = y === 'cost_per_success_usd';
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const median = values => {
    const sorted = [...values].sort((a,b)=>a-b), middle = Math.floor(sorted.length/2);
    return sorted.length%2 ? sorted[middle] : (sorted[middle-1]+sorted[middle])/2;
  };
  const groups = new Map();
  for (const row of rows.filter(r=>(scoreX||successCostX||finite(r[x]))&&(scoreY||successCostY||finite(r[y])))) {
    const key = groupKey(row);
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(row);
  }
  return [...groups.values()].map(group=>{
    // Include selected results with missing axis telemetry in the pass/fail badge.
    const first=group[0];
    const all=rows.filter(r=>groupKey(r)===groupKey(first));
    const successes=all.reduce((n,r)=>n+(r.successes??r.completion??0),0);
    const attempts=all.reduce((n,r)=>n+(r.attempts??1),0);
    const expected=all.reduce((n,r)=>n+(r.expected_attempts??r.attempts??1),0);
    const successCost=successCostX||successCostY?costPerVerifiedSuccess(all):null;
    return ({
    provider:first.provider, model:first.model, effort:byModel?null:first.effort||'default', median:true,
    grouping:byModel?'model':'model-effort', efforts:[...new Set(all.map(r=>r.effort||'default'))],
    point_count:group.length,
    task_count:new Set(group.map(r=>JSON.stringify([r.task_id,r.difficulty]))).size,
    successes, attempts, expected_attempts:expected,
    result_status:attempts<expected?'pending':successes===attempts?'passed':successes===0?'failed':'mixed',
    [x]:scoreX?(attempts>0?100*successes/attempts:null):successCostX?successCost:median(group.map(r=>r[x])),
    [y]:scoreY?(attempts>0?100*successes/attempts:null):successCostY?successCost:median(group.map(r=>r[y]))
  });});
}
function medianStatusLabel(r){
  return `${r.successes}/${r.attempts} runs passed${r.attempts<r.expected_attempts?`, ${r.expected_attempts-r.attempts} pending`:''}`;
}
function medianMeetsScore(r,minimumPercent){
  return minimumPercent<=0 || (r.attempts>0 && r.successes*100>=minimumPercent*r.attempts);
}
if (typeof module !== 'undefined' && module.exports) module.exports = {modelMedians, medianStatusLabel, medianMeetsScore, chartCostRows};
