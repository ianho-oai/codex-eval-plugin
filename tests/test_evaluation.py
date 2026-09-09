import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'plugins/codex-eval-plugin'))
from ceval.cli import initialize, main, export_plugin, demo
from ceval.core import DATA, EvalError, child, digest, load_suite, read_json, tree, write_json, allowed_changes
from ceval.telemetry import normalize
from ceval.runner import schedule, validate_graders, execute, clean_env, run, native_argv
from ceval.discovery import history, user_text, timestamp
from ceval.report import dataset, summarize, csv_text


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.suite_dir = self.root/'suite'
        initialize(self.suite_dir, 'local', None)
        self.path = self.suite_dir/'suite.json'
        self.s = read_json(self.path)
        self.s['matrix'] = [{'provider':'codex','model':'gpt-5.6-sol','efforts':['medium']}]
        self.s['repeats'] = 1
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        write_json(self.path,self.s)

    def approve(self):
        validate_graders(self.path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['approve',str(self.path),'--by','Unit test fixture']),0)


class SuiteTests(Workspace):
    def test_all_baselines_fail_all_oracles_pass(self):
        checks = validate_graders(self.path)
        self.assertEqual(len(checks),3)
        self.assertTrue(all(c['baseline']['exit_code']==1 and c['oracle']['exit_code']==0 for c in checks))

    def test_seeded_schedule_covers_cartesian_product(self):
        self.s['repeats']=4
        self.s['matrix'].append({'provider':'claude','model':'claude-sonnet-5','efforts':['low','high']})
        self.save()
        _,s,t,_,_=load_suite(self.path)
        cells=schedule(s,t)
        self.assertEqual(len(cells),36)
        self.assertEqual(len({c['cell_id'] for c in cells}),36)
        self.assertEqual(cells,schedule(s,t))
        s['seed']+=1
        self.assertNotEqual(cells,schedule(s,t))

    def test_approval_invalidated_by_task_pricing_and_matrix(self):
        _,_,_,_,before=load_suite(self.path)
        prompt=self.suite_dir/'tasks/async-search/instruction.md'
        prompt.write_text(prompt.read_text()+'\nChanged behavior')
        after=load_suite(self.path)[4]
        self.assertNotEqual(before,after)
        rates=read_json(self.suite_dir/'rates.json');rates['models']['gpt-5.6-sol']['input']=999
        write_json(self.suite_dir/'rates.json',rates)
        self.assertNotEqual(after,load_suite(self.path)[4])

    def test_refuse_unapproved_run(self):
        with self.assertRaises(EvalError):run(self.path,self.root/'run')

    def test_refuse_symlinks_secrets_and_traversal(self):
        with self.assertRaises(EvalError):child(self.root,'../escape')
        with self.assertRaises(EvalError):child(self.root,'/tmp/escape')
        f=self.suite_dir/'tasks/slug-normalization/baseline/.env'
        f.write_text('secret')
        with self.assertRaises(EvalError):load_suite(self.path)
        f.unlink();f.symlink_to('/etc/hosts')
        with self.assertRaises(EvalError):load_suite(self.path)

    def test_forbidden_changes_detect_deletions_and_new_files(self):
        p=self.suite_dir/'tasks/slug-normalization/baseline'
        before=tree(p)
        (p/'slug.py').unlink();(p/'config.txt').write_text('bad')
        changed,denied=allowed_changes(before,p,['slug.py'])
        self.assertEqual(changed,['config.txt','slug.py'])
        self.assertEqual(denied,['config.txt'])

    def test_duplicate_lane_negative_budget_and_mutable_image_rejected(self):
        self.s['matrix']*=2;self.save()
        with self.assertRaises(EvalError):load_suite(self.path)
        self.s['matrix']=self.s['matrix'][:1];self.s['limits']['spend_stop_usd']=-1;self.save()
        with self.assertRaises(EvalError):load_suite(self.path)
        self.s['limits']['spend_stop_usd']=1;self.s['execution']['mode']='docker';self.s['execution']['image']='latest';self.save()
        with self.assertRaises(EvalError):load_suite(self.path)

    def test_shortcut_mutants_fail(self):
        # Exercise actual verifiers against behavior-breaking candidate variants.
        _,s,tasks,_,_=load_suite(self.path)
        from ceval.runner import grade
        for task in tasks:
            target=self.root/task['spec']['id']
            shutil.copytree(task['root']/'oracle',target)
            if task['spec']['id']=='slug-normalization':
                (target/'slug.py').write_text('def slugify(text): return "hello-world"\n')
            elif task['spec']['id']=='facet-filter':
                p=target/'filter.cjs';p.write_text(p.read_text().replace("(maxPrice === undefined || p.price <= maxPrice)", 'true'))
            else:
                p=target/'search.cjs';p.write_text(p.read_text().replace('mine === generation','true'))
            self.assertEqual(grade(task,target,s)['exit_code'],1,task['spec']['id'])


class TelemetryTests(unittest.TestCase):
    def setUp(self):self.rates=read_json(DATA/'rates.json')
    def test_codex_cache_subtraction_and_reasoning_not_double_billed(self):
        ev={'type':'turn.completed','usage':{'input_tokens':1000,'cached_input_tokens':700,'output_tokens':200,'reasoning_output_tokens':120}}
        r=normalize('codex',json.dumps(ev),'gpt-5.6-sol',self.rates)
        self.assertAlmostEqual(r['cost_usd'],(300*4+700*.4+200*20)/1e6)
        self.assertGreater(r['cost_upper_usd'],r['cost_usd'])
        self.assertEqual(r['turns'],1)
        self.assertEqual(r['reasoning_tokens'],120)
        self.assertIsNone(r['cache_write_tokens'])

    def test_codex_sums_completed_turns(self):
        e={'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':0,'output_tokens':3}}
        r=normalize('codex','\n'.join([json.dumps(e)]*2),'gpt-5.6-luna',self.rates)
        self.assertEqual(r['input_tokens'],20)
        self.assertEqual(r['turns'],2)

    def test_claude_input_components_and_reported_cost(self):
        e={'type':'result','subtype':'success','num_turns':12,'total_cost_usd':.77,'duration_ms':12000,
           'usage':{'input_tokens':100,'cache_read_input_tokens':200,'cache_creation_input_tokens':300,'output_tokens':50},
           'modelUsage':{'claude-sonnet-5':{'costUSD':.77}}}
        r=normalize('claude',json.dumps(e),'claude-sonnet-5',self.rates)
        self.assertEqual(r['input_tokens'],600)
        self.assertEqual(r['uncached_input_tokens'],100)
        self.assertEqual(r['cost_usd'],.77)
        self.assertEqual(r['cost_source'],'reported_by_claude_code')
        self.assertEqual(r['turns'],12)
        self.assertIsNone(r['reasoning_tokens'])

    def test_unknown_missing_and_invalid_metrics_are_not_zero(self):
        r=normalize('codex','garbage\n{}','unknown',self.rates)
        self.assertIsNone(r['cost_usd']);self.assertIsNone(r['input_tokens']);self.assertEqual(r['invalid_event_lines'],1)
        e={'type':'turn.completed','usage':{'input_tokens':5,'cached_input_tokens':99,'output_tokens':1}}
        self.assertIsNone(normalize('codex',json.dumps(e),'gpt-5.6-sol',self.rates)['cost_usd'])
        e={'type':'result','subtype':'success','total_cost_usd':float('nan')}
        self.assertIsNone(normalize('claude',json.dumps(e),'claude-sonnet-5',self.rates)['cost_usd'])

    def test_error_preserves_native_cost(self):
        e={'type':'result','subtype':'error_max_turns','is_error':True,'total_cost_usd':.4,'num_turns':3}
        r=normalize('claude',json.dumps(e),'claude-sonnet-5',self.rates)
        self.assertFalse(r['provider_success']);self.assertEqual(r['cost_usd'],.4)


class RunnerTests(Workspace):
    def fake_binary(self, provider='codex'):
        # Offline native protocol emulator. Every filesystem/grade step still runs.
        binary=self.root/provider
        oracle=(DATA/'examples/slug-normalization/oracle/slug.py').read_text()
        events=[{'type':'item.completed','item':{'type':'command_execution'}},
                {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':50,'output_tokens':30}}]
        if provider=='claude':
            events=[{'type':'result','subtype':'success','num_turns':2,'total_cost_usd':.03,
                     'usage':{'input_tokens':50,'cache_read_input_tokens':10,'cache_creation_input_tokens':20,'output_tokens':30}}]
        binary.write_text('#!'+sys.executable+'\nimport sys,json\nfrom pathlib import Path\n'
            +"if '--version' in sys.argv: print('codex-cli 0.153.4' if "+repr(provider)+"=='codex' else '2.1.220 (Claude Code)');sys.exit(0)\n"
            +"if '--help' in sys.argv: print('--json --ephemeral --ignore-user-config --bare --strict-mcp-config --effort');sys.exit(0)\n"
            +"sys.stdin.read()\nPath('slug.py').write_text("+repr(oracle)+")\n"
            +"for e in "+repr(events)+":print(json.dumps(e))\n")
        binary.chmod(0o755)
        return str(binary)

    def prep(self, providers=('codex',)):
        self.s['tasks']=['tasks/slug-normalization']
        self.s['matrix']=[]
        for p in providers:
            self.s['execution'][p+'_bin']=self.fake_binary(p)
            self.s['matrix'].append({'provider':p,'model':'gpt-5.6-sol' if p=='codex' else 'claude-sonnet-5','efforts':['medium']})
        self.save();self.approve()

    def test_native_end_to_end_both_adapters_and_resume(self):
        self.prep(('codex','claude'))
        out=self.root/'run'
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key','ANTHROPIC_API_KEY':'test-key'}),contextlib.redirect_stdout(io.StringIO()):
            result=run(self.path,out)
            first=read_json(out/'results.json')
            again=run(self.path,out,resume=True)
        self.assertEqual(result['state'],'complete')
        self.assertEqual(again['completed_cells'],2)
        self.assertTrue(all(r['completion']==1 for r in first['rows']))
        self.assertEqual(read_json(out/'results.json'),first)
        self.assertEqual(dataset(out)['summary']['attempted'],2)

    def test_changed_suite_cannot_resume(self):
        self.prep()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key'}),contextlib.redirect_stdout(io.StringIO()):run(self.path,self.root/'run')
        self.s['repeats']=2;self.save()
        with self.assertRaises(EvalError):run(self.path,self.root/'run',resume=True)

    def test_modified_result_rejected(self):
        self.prep()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key'}),contextlib.redirect_stdout(io.StringIO()):run(self.path,self.root/'run')
        p=next((self.root/'run/attempts').glob('*/result.json'))
        r=read_json(p);r['completion']=0;write_json(p,r)
        with self.assertRaises(EvalError):run(self.path,self.root/'run',resume=True)
        with self.assertRaises(EvalError):dataset(self.root/'run')

    def test_spend_stop_and_unknown_spend(self):
        self.prep();self.s['repeats']=3;self.s['limits']['spend_stop_usd']=.01;self.save();self.approve()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key'}),contextlib.redirect_stdout(io.StringIO()):
            with patch('ceval.runner.normalize', return_value={'provider_success':True,'cost_usd':.02,'cost_upper_usd':.03}):
                result=run(self.path,self.root/'budget')
        self.assertEqual(result['completed_cells'],1);self.assertEqual(result['stop_reason'],'spend_threshold')
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key'}),contextlib.redirect_stdout(io.StringIO()):
            with patch('ceval.runner.normalize', return_value={'provider_success':True,'cost_usd':None,'cost_upper_usd':None}):
                result=run(self.path,self.root/'unknown')
        self.assertEqual(result['completed_cells'],1);self.assertEqual(result['stop_reason'],'unknown_spend')

    def test_preflight_missing_key_is_visible_not_dropped(self):
        self.prep(('codex','claude'))
        with patch.dict(os.environ,{},clear=True),contextlib.redirect_stdout(io.StringIO()):r=run(self.path,self.root/'run')
        rows=read_json(self.root/'run/results.json')['rows']
        self.assertEqual(len(rows),2)
        self.assertTrue(all(x['status']=='infrastructure_error' and x['completion']==0 and x['not_started'] for x in rows))

    def test_timeout_kills_process_and_preserves_output(self):
        r=execute([sys.executable,'-u','-c','import time;print("before");time.sleep(5)'],None,clean_env(),.1)
        self.assertTrue(r['timed_out']);self.assertEqual(r['exit_code'],124);self.assertIn('before',r['stdout'])

    def test_environment_does_not_inherit_credentials(self):
        with patch.dict(os.environ,{'GITHUB_TOKEN':'secret','OPENAI_API_KEY':'secret','ANTHROPIC_API_KEY':'secret','OPENAI_BASE_URL':'bad'}):
            self.assertNotIn('OPENAI_API_KEY',clean_env());self.assertNotIn('GITHUB_TOKEN',clean_env());self.assertNotIn('OPENAI_BASE_URL',clean_env())

    def test_no_fallback_or_connectors_and_default_haiku_effort(self):
        cmd=native_argv('claude','claude','claude-haiku-4-5-20251001','default',10,20,5)
        self.assertNotIn('--effort',cmd);self.assertNotIn('--fallback-model',cmd)
        self.assertIn('--bare',cmd);self.assertIn('--strict-mcp-config',cmd)
        cmd=native_argv('codex','codex','gpt-5.6-sol','high',10,20,5)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',cmd)


class DiscoveryAndReportTests(Workspace):
    def test_history_requires_consent_and_extracts_only_user_text(self):
        from datetime import datetime,timezone,timedelta
        root=self.root/'history';root.mkdir()
        stamp=datetime.now(timezone.utc).isoformat()
        records=[{'timestamp':stamp,'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':'Fix pagination'}]}},
                 {'timestamp':stamp,'type':'response_item','payload':{'role':'assistant','content':[{'type':'text','text':'PRIVATE'}]}},
                 {'timestamp':(datetime.now(timezone.utc)-timedelta(days=90)).isoformat(),'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':'Old prompt'}]}}]
        (root/'session.jsonl').write_text('\n'.join(map(json.dumps,records)))
        with self.assertRaises(EvalError):history('codex',root,30,False,self.root/'out.json')
        r=history('codex',root,30,True,self.root/'out.json')
        self.assertEqual(r['excerpt_count'],1)
        self.assertEqual(read_json(self.root/'out.json')['excerpts'][0]['text'],'Fix pagination')
        self.assertIsNone(user_text({'type':'user','message':{'content':[{'type':'tool_result','content':'PRIVATE'}]}},'claude'))

    def test_cost_per_success_includes_failures_and_missing_stays_null(self):
        rows=[{'provider':'codex','model':'x','effort':'high','completion':1,'valid':True,'cost_usd':1},
              {'provider':'codex','model':'x','effort':'high','completion':0,'valid':True,'cost_usd':2}]
        self.assertEqual(summarize(rows,3)['groups'][0]['cost_per_success_usd'],3)
        rows[-1]['cost_usd']=None
        self.assertIsNone(summarize(rows,3)['groups'][0]['cost_per_success_usd'])
        self.assertEqual(summarize(rows,3)['pending'],1)

    def test_demo_is_explicit_and_csv_guards_formula_injection(self):
        demo(self.root/'demo')
        d=dataset(self.root/'demo')
        self.assertTrue(d['run']['simulation']);self.assertTrue(all(r['simulation'] for r in d['rows']))
        self.assertIn("'=cmd",csv_text([{'task_id':'=cmd'}]))

    def test_reproducible_standalone_export(self):
        a=export_plugin(self.root/'one');b=export_plugin(self.root/'two')
        self.assertEqual(a['sha256'],b['sha256'])
        with zipfile.ZipFile(a['zip']) as z:
            self.assertEqual(len([n for n in z.namelist() if n.endswith('SKILL.md')]),1)
            self.assertFalse(any('/evaluations/' in n or '/.env' in n or '__pycache__' in n for n in z.namelist()))
            z.extractall(self.root/'extracted')
        r=execute([sys.executable,str(self.root/'extracted/codex-eval-plugin/bin/codex-eval'),'self-check'],None,clean_env(),30)
        self.assertEqual(r['exit_code'],0,r['stderr'])


if __name__ == '__main__':unittest.main()
