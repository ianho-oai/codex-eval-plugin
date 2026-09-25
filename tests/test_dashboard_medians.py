import subprocess
import unittest
from pathlib import Path


class DashboardMedianTests(unittest.TestCase):
    def test_cost_per_success_uses_total_spend_including_failures_and_all_repeats(self):
        script = r'''
const assert=require('node:assert/strict');
const {modelMedians,chartCostRows}=require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=extra=>({provider:'codex',model:'one',effort:'low',task_id:'a',cost_usd:2,latency_seconds:10,successes:1,attempts:1,...extra});
const rows=[row({attempts:3,successes:2}),row({effort:'high',cost_usd:10,successes:0}),
 row({task_id:'b',effort:'high',cost_usd:4,latency_seconds:null}),
 row({task_id:'pending',cost_usd:null,attempts:0,successes:0,expected_attempts:3}),
 row({provider:'copilot',cost_usd:null,copilot_usage_value_usd:6})];
const original=JSON.stringify(rows),projected=chartCostRows(rows);
const grouped=modelMedians(projected,'cost_per_success_usd','average_score','model');
const [m,copilot]=grouped;
assert.equal(m.cost_per_success_usd,20/3); // (2*3 + 10 + 4) / (2 + 0 + 1), not a mean of ratios.
assert.equal(m.average_score,60);assert.equal(m.attempts,5);assert.equal(m.expected_attempts,8);
assert.equal(copilot.cost_per_success_usd,6); // Native valuation, not null cost_usd.
assert.deepEqual(modelMedians(projected,'average_score','cost_per_success_usd','model'),grouped);
const [paired]=modelMedians(projected,'latency_seconds','cost_per_success_usd','model');
assert.equal(paired.cost_per_success_usd,20/3); // Missing latency must not drop cost or passes.
assert.equal(paired.latency_seconds,10);
const split=modelMedians(projected,'cost_per_success_usd','average_score');
assert.equal(split[0].cost_per_success_usd,3);assert.equal(split[1].cost_per_success_usd,14);
for(const unknown of [row({cost_usd:null}),row({cost_usd:NaN}),row({cost_usd:-1})]){
 assert.equal(modelMedians([row({}),unknown],'cost_per_success_usd','average_score')[0].cost_per_success_usd,null);
}
assert.equal(modelMedians([row({successes:0})],'cost_per_success_usd','average_score')[0].cost_per_success_usd,null);
assert.equal(modelMedians([row({cost_usd:0})],'cost_per_success_usd','cost_per_success_usd')[0].cost_per_success_usd,0);
assert.equal(modelMedians([row({attempts:0,successes:0,cost_usd:null})],'cost_per_success_usd','average_score')[0].cost_per_success_usd,null);
assert.equal(JSON.stringify(rows),original);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)

    def test_model_grouping_pools_efforts_keeps_providers_and_counts_missing_results(self):
        script = r'''
const assert=require('node:assert/strict');
const {modelMedians,medianMeetsScore}=require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=extra=>({provider:'codex',model:'one',effort:'low',task_id:'a',cost_usd:1,latency_seconds:10,successes:1,attempts:1,...extra});
const rows=[row({}),row({effort:'high',cost_usd:9,latency_seconds:90,successes:1,attempts:3}),
 row({effort:'max',cost_usd:null,latency_seconds:null,successes:0,attempts:1}),
 row({effort:'max',task_id:'b',cost_usd:null,latency_seconds:null,successes:0,attempts:0,expected_attempts:2}),
 row({provider:'copilot',cost_usd:30}),row({model:'two',cost_usd:50})];
const original=JSON.stringify(rows);
const grouped=modelMedians(rows,'cost_usd','average_score','model');
assert.equal(grouped.length,3);
const m=grouped[0];
assert.equal(m.cost_usd,5);assert.equal(m.average_score,40);
assert.equal(m.grouping,'model');assert.equal(m.effort,null);
assert.deepEqual(m.efforts,['low','high','max']);
assert.equal(m.point_count,2);assert.equal(m.attempts,5);assert.equal(m.expected_attempts,7);
assert.equal(medianMeetsScore(m,40),true);assert.equal(medianMeetsScore(m,41),false);
assert.equal(grouped[1].provider,'copilot');assert.equal(grouped[1].average_score,100);
const swapped=modelMedians(rows,'average_score','cost_usd','model');
assert.deepEqual(swapped,grouped);
const measured=modelMedians(rows,'cost_usd','latency_seconds','model');
assert.equal(measured[0].cost_usd,5);assert.equal(measured[0].latency_seconds,50);
const split=modelMedians(rows,'cost_usd','average_score','model-effort');
assert.equal(split.length,4);assert.equal(split[0].cost_usd,1);assert.equal(split[1].cost_usd,9);
assert.deepEqual(modelMedians(rows,'cost_usd','average_score'),split);
assert.equal(JSON.stringify(rows),original);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)

    def test_score_axes_are_symmetric_including_missing_and_pending_results(self):
        script = r'''
const assert=require('node:assert/strict');
const {modelMedians}=require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=extra=>({provider:'codex',model:'one',effort:'high',task_id:'a',latency_seconds:10,...extra});
const rows=[row({successes:1,attempts:1}),row({task_id:'b',latency_seconds:90,successes:1,attempts:3}),
  row({task_id:'c',latency_seconds:null,successes:0,attempts:1}),
  row({task_id:'d',latency_seconds:null,successes:0,attempts:0,expected_attempts:2})];
const [x]=modelMedians(rows,'average_score','latency_seconds');
const [y]=modelMedians(rows,'latency_seconds','average_score');
assert.deepEqual(x,y);assert.equal(y.average_score,40);assert.equal(y.latency_seconds,50);
const [both]=modelMedians(rows,'average_score','average_score');
assert.equal(both.average_score,40);assert.equal(both.point_count,4);
const zero=modelMedians([row({completion:0})],'latency_seconds','average_score')[0];
assert.equal(zero.average_score,0);
const pending=modelMedians([row({successes:0,attempts:0})],'latency_seconds','average_score')[0];
assert.equal(pending.average_score,null);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)

    def test_chart_costs_include_copilot_usage_without_modifying_billing_evidence(self):
        script = r'''
const assert=require('node:assert/strict');
const {chartCostRows,modelMedians}=require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=extra=>({provider:'copilot',model:'one',task_id:'a',cost_usd:null,completion:1,...extra});
const rows=[row({copilot_usage_value_usd:2}),row({task_id:'b',copilot_usage_value_usd:0}),
 row({task_id:'c',copilot_usage_value_usd:null,completion:0}),
 row({provider:'codex',cost_usd:7}),row({provider:'claude',cost_usd:4})];
const original=JSON.stringify(rows),display=chartCostRows(rows);
assert.equal(display[0].cost_usd,2);assert.equal(display[1].cost_usd,0);assert.equal(display[2].cost_usd,null);
assert.equal(display[3].cost_usd,7);assert.equal(display[4].cost_usd,4);
assert.equal(JSON.stringify(rows),original);
const [m]=modelMedians(display,'cost_usd','average_score');
assert.equal(m.cost_usd,1);assert.equal(m.average_score,100*2/3);
assert.equal(m.attempts,3);assert.equal(m.point_count,2);
assert.equal(JSON.stringify(rows),original);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)

    def test_average_score_weights_completed_attempts_and_keeps_y_median(self):
        script = r'''
const assert = require('node:assert/strict');
const {modelMedians} = require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=extra=>({provider:'codex',model:'one',effort:'high',task_id:'a',latency_seconds:10,...extra});
const rows=[row({successes:1,attempts:1,expected_attempts:3}),
  row({task_id:'b',latency_seconds:90,successes:1,attempts:3}),
  row({task_id:'c',latency_seconds:null,successes:0,attempts:1}),
  row({task_id:'d',latency_seconds:null,successes:0,attempts:0,expected_attempts:2})];
const original=JSON.stringify(rows),[m]=modelMedians(rows,'average_score','latency_seconds');
assert.equal(m.average_score,40); // 2/5 completed, not mean or median of task pass rates.
assert.equal(m.latency_seconds,50);assert.equal(m.attempts,5);assert.equal(m.expected_attempts,9);
assert.equal(JSON.stringify(rows),original);
const groups=modelMedians([row({completion:0}),row({model:'other',completion:1}),
  row({effort:'low',successes:0,attempts:0,expected_attempts:3})],'average_score','latency_seconds');
assert.equal(groups[0].average_score,0);assert.equal(groups[1].average_score,100);
assert.equal(groups[2].average_score,null); // Pending-only groups are unknown, never zero.
assert.deepEqual(modelMedians([row({latency_seconds:null,completion:1})],'average_score','latency_seconds'),[]);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)

    def test_minimum_score_uses_all_completed_results_without_changing_median(self):
        script = r'''
const assert = require('node:assert/strict');
const {modelMedians,medianMeetsScore} = require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const base={provider:'claude',model:'one',effort:'low',task_id:'a'};
const rows=[{...base,cost_usd:1,latency_seconds:10,successes:1,attempts:1,expected_attempts:2},
  {...base,task_id:'b',cost_usd:9,latency_seconds:90,successes:0,attempts:1,expected_attempts:1},
  {...base,task_id:'c',cost_usd:null,latency_seconds:null,successes:1,attempts:2,expected_attempts:2}];
const original=JSON.stringify(rows),[m]=modelMedians(rows,'cost_usd','latency_seconds');
assert.equal(m.cost_usd,5);assert.equal(m.latency_seconds,50);
assert.equal(m.successes,2);assert.equal(m.attempts,4);
assert.equal(medianMeetsScore(m,50),true);assert.equal(medianMeetsScore(m,51),false);
assert.equal(medianMeetsScore({successes:0,attempts:0},0),true);
assert.equal(medianMeetsScore({successes:0,attempts:0},1),false);
assert.equal(medianMeetsScore({successes:3,attempts:3,expected_attempts:5},100),true);
assert.equal(JSON.stringify(rows),original);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)

    def test_medians_pool_visible_configurations_keep_pairs_and_preserve_zero(self):
        script = r'''
const assert = require('node:assert/strict');
const {modelMedians} = require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=(cost,time,extra={})=>({provider:'codex',model:'one',task_id:'a',effort:'low',cost_usd:cost,latency_seconds:time,completion:0,...extra});
const rows=[row(0,100),row(2,6),row(4,4,{task_id:'b',completion:1}),row(100,0),row(null,999),row(999,null)];
const original=JSON.stringify(rows);
const [m]=modelMedians(rows,'cost_usd','latency_seconds');
assert.equal(m.cost_usd,3);assert.equal(m.latency_seconds,5);
assert.equal(m.point_count,4);assert.equal(m.task_count,2);assert.equal(m.successes,1);
assert.equal(m.effort,'low');assert.equal(JSON.stringify(rows),original);
const selected=modelMedians(rows.filter(r=>r.task_id==='b'),'cost_usd','latency_seconds');
assert.equal(selected[0].cost_usd,4);assert.equal(selected[0].point_count,1);
const groups=modelMedians([row(1,9),row(3,7),row(90,1),row(20,40,{provider:'claude'}),row(30,50,{model:'two'})],'cost_usd','latency_seconds');
assert.equal(groups.length,3);assert.equal(groups[0].cost_usd,3);assert.equal(groups[0].latency_seconds,7);
assert.equal(groups[1].cost_usd,20);assert.equal(groups[2].cost_usd,30);
assert.deepEqual(modelMedians([row(null,4),row(4,NaN)],'cost_usd','latency_seconds'),[]);
const zeros=modelMedians([row(0,4),row(4,0)],'cost_usd','latency_seconds');
assert.equal(zeros[0].cost_usd,2);assert.equal(zeros[0].latency_seconds,2);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)

    def test_efforts_never_share_a_median_and_missing_effort_uses_default(self):
        script = r'''
const assert = require('node:assert/strict');
const {modelMedians} = require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=(effort,cost,time,extra={})=>({provider:'codex',model:'same',effort,task_id:'a',cost_usd:cost,latency_seconds:time,completion:1,...extra});
const groups=modelMedians([row('low',0,20),row('low',4,40,{task_id:'b'}),row('high',100,1000),row('high',200,2000),row(undefined,8,80),row('default',12,120),row('none',30,300),row('low',999,999,{provider:'claude'})],'cost_usd','latency_seconds');
assert.equal(groups.length,5);
const low=groups.find(g=>g.provider==='codex'&&g.effort==='low');
assert.equal(low.cost_usd,2);assert.equal(low.latency_seconds,30);assert.equal(low.point_count,2);
const high=groups.find(g=>g.effort==='high');
assert.equal(high.cost_usd,150);assert.equal(high.latency_seconds,1500);
assert.equal(groups.find(g=>g.effort==='default').cost_usd,10);
assert.equal(groups.find(g=>g.effort==='none').cost_usd,30);
assert.equal(groups.find(g=>g.provider==='claude').cost_usd,999);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)

    def test_status_counts_repeats_missing_metrics_and_pending(self):
        script = r'''
const assert = require('node:assert/strict');
const {modelMedians,medianStatusLabel} = require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=extra=>({provider:'codex',model:'one',effort:'low',task_id:'a',cost_usd:1,latency_seconds:2,completion:1,...extra});
const status=rows=>modelMedians(rows,'cost_usd','latency_seconds')[0];
assert.equal(status([row({}),row({task_id:'b'})]).result_status,'passed');
assert.equal(status([row({completion:0}),row({completion:0,task_id:'b'})]).result_status,'failed');
const mixed=status([row({successes:2,attempts:3,expected_attempts:3}),row({completion:0,cost_usd:null})]);
assert.equal(mixed.result_status,'mixed');assert.equal(mixed.successes,2);assert.equal(mixed.attempts,4);
assert.equal(mixed.point_count,1);assert.equal(medianStatusLabel(mixed),'2/4 runs passed');
const pending=status([row({successes:1,attempts:1,expected_attempts:3})]);
assert.equal(pending.result_status,'pending');assert.equal(medianStatusLabel(pending),'1/1 runs passed, 2 pending');
assert.equal(status([row({}),row({model:'other',completion:0})]).result_status,'passed');
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)
