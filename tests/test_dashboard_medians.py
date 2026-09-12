import subprocess
import unittest
from pathlib import Path


class DashboardMedianTests(unittest.TestCase):
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
