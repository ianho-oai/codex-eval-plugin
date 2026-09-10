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
    const key = JSON.stringify([row.provider,row.model]);
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(row);
  }
  return [...groups.values()].map(group=>({
    provider:group[0].provider, model:group[0].model, median:true,
    point_count:group.length,
    task_count:new Set(group.map(r=>JSON.stringify([r.task_id,r.difficulty]))).size,
    efforts:[...new Set(group.map(r=>r.effort||'default'))].sort((a,b)=>['default','none','low','medium','high','xhigh','max'].indexOf(a)-['default','none','low','medium','high','xhigh','max'].indexOf(b)),
    successes:group.reduce((count,r)=>count+(r.successes??r.completion??0),0),
    [x]:median(group.map(r=>r[x])), [y]:median(group.map(r=>r[y]))
  }));
}
if (typeof module !== 'undefined' && module.exports) module.exports = {modelMedians};
