import subprocess
import unittest
from pathlib import Path


class DashboardMedianTests(unittest.TestCase):
    def test_medians_pool_visible_configurations_keep_pairs_and_preserve_zero(self):
        script = r'''
const assert = require('node:assert/strict');
const {modelMedians} = require('./plugins/codex-eval-plugin/ceval/data/web/medians.js');
const row=(cost,time,extra={})=>({provider:'codex',model:'one',task_id:'a',effort:'low',cost_usd:cost,latency_seconds:time,completion:0,...extra});
const rows=[row(0,100),row(2,6,{effort:'high'}),row(4,4,{task_id:'b',completion:1}),row(100,0),row(null,999),row(999,null)];
const original=JSON.stringify(rows);
const [m]=modelMedians(rows,'cost_usd','latency_seconds');
assert.equal(m.cost_usd,3);assert.equal(m.latency_seconds,5);
assert.equal(m.point_count,4);assert.equal(m.task_count,2);assert.equal(m.successes,1);
assert.deepEqual(m.efforts,['low','high']);assert.equal(JSON.stringify(rows),original);
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

    def test_comparison_pairs_and_direction_follow_visible_medians(self):
        script = r'''
const assert = require('node:assert/strict');
const {modelPairings,visibleModelComparisons,comparisonArrow} = require('./plugins/codex-eval-plugin/ceval/data/web/pairings.js');
const points=[...new Set(modelPairings.map(p=>p.claude))].map(model=>({provider:'claude',model})).concat([...new Set(modelPairings.map(p=>p.codex))].map(model=>({provider:'codex',model})));
assert.equal(visibleModelComparisons(points,false).length,0);
const pairs=visibleModelComparisons(points,true);
assert.equal(pairs.length,5);
assert(pairs.every(p=>p.from.provider==='claude'&&p.to.provider==='codex'&&p.sources.every(s=>s.startsWith('https://'))));
assert.equal(visibleModelComparisons(points.filter(p=>p.model!=='claude-fable-5-1'),true).length,3);
assert.equal(visibleModelComparisons(points.filter(p=>p.model!=='gpt-5.6-sol'),true).length,3);
assert.deepEqual(visibleModelComparisons([{provider:'codex',model:'claude-fable-5-1'},{provider:'codex',model:'gpt-5.6-sol'}],true),[]);
assert.deepEqual(visibleModelComparisons([{provider:'claude',model:'claude-fable-new'},{provider:'codex',model:'gpt-5.6-sol'}],true),[]);
assert.deepEqual(comparisonArrow({x:0,y:0},{x:100,y:0}),{x1:18,y1:0,x2:82,y2:0});
assert.deepEqual(comparisonArrow({x:0,y:100},{x:0,y:0}),{x1:0,y1:82,x2:0,y2:18});
assert.equal(comparisonArrow({x:1,y:1},{x:1,y:1}),null);
const close=comparisonArrow({x:0,y:0},{x:2,y:2});
assert(close.x1<close.x2&&close.y1<close.y2);
'''
        subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)
