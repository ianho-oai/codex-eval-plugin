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
from ceval.cli import initialize, main, export_plugin, demo, load_local_keys, parser, configure
from ceval.core import DATA, EvalError, child, digest, load_suite, read_json, tree, write_json, allowed_changes
from ceval.telemetry import normalize
from ceval.runner import schedule, validate_graders, execute, clean_env, run, native_argv, preflight
from ceval.discovery import history, user_text, timestamp
from ceval.report import dataset, dashboard_dataset, summarize, csv_text, average_attempts


class LocalKeyTests(unittest.TestCase):
    def test_cli_loads_local_key_and_preserves_exported_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'.env.local').write_text('export ANTHROPIC_API_KEY="test-local-key" # comment\nOPENAI_API_KEY=local-openai\nUNRELATED=ignored\n')
            def smoke_stub(*args):
                self.assertEqual(os.environ['ANTHROPIC_API_KEY'], 'test-local-key')
                self.assertEqual(os.environ['OPENAI_API_KEY'], 'exported-key')
                self.assertNotIn('UNRELATED', os.environ)
                return {'rows': [{'completion': 1}]}
            with patch('ceval.cli.Path.cwd', return_value=root), patch.dict(os.environ, {'OPENAI_API_KEY': 'exported-key'}, clear=True), patch('ceval.cli.smoke', side_effect=smoke_stub), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['smoke', '--provider', 'claude', '--output', 'unused']), 0)
                self.assertNotIn('test-local-key', output.getvalue())

    def test_no_shell_execution_or_secret_in_parse_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root/'executed'
            with patch('ceval.cli.Path.cwd', return_value=root), patch.dict(os.environ, {}, clear=True):
                (root/'.env.local').write_text(f'ANTHROPIC_API_KEY="$(touch {marker})"\n')
                load_local_keys()
                self.assertFalse(marker.exists())
                self.assertEqual(os.environ.pop('ANTHROPIC_API_KEY'), f'$(touch {marker})')
                (root/'.env.local').write_text('ANTHROPIC_API_KEY="secret-unclosed\n')
                with self.assertRaises(EvalError) as error:
                    load_local_keys()
                self.assertNotIn('secret-unclosed', str(error.exception))


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.suite_dir = self.root/'suite'
        initialize(self.suite_dir, 'local', None, purpose='smoke')
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
    def test_example_grader_accepts_dataclass_based_candidate(self):
        candidate = self.root / 'dataclass-candidate'
        candidate.mkdir()
        (candidate / 'slug.py').write_text('''from __future__ import annotations
from dataclasses import dataclass
import re
import unicodedata

@dataclass(frozen=True)
class Slug:
    value: str

def slugify(text):
    if not isinstance(text, str):
        raise TypeError('Expected text')
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    return Slug('-'.join(re.findall('[a-z0-9]+', normalized))).value
''')
        verifier = DATA / 'examples/slug-normalization/grader/verify.py'
        result = execute([sys.executable, str(verifier), str(candidate)], self.root, clean_env(), 30)
        self.assertEqual(result['exit_code'], 0, result['stderr'] + result['stdout'])

    def test_all_baselines_fail_all_oracles_pass(self):
        checks = validate_graders(self.path)
        self.assertEqual(len(checks),3)
        self.assertTrue(all(c['baseline']['exit_code']==1 and c['oracle']['exit_code']==0 for c in checks))

    def test_configure_models_tasks_and_repeats_is_validated_and_sealed(self):
        self.approve()
        result = configure(self.path, ['codex:gpt-5.6-luna','claude:claude-sonnet-5'], ['slug-normalization'], 3, efforts=['medium'])
        _, suite, tasks, _, seal = load_suite(self.path)
        self.assertEqual(len(tasks), 3)  # Preserve the full portfolio.
        self.assertEqual(len(schedule(suite, tasks)), 6)
        self.assertEqual({c['task_id'] for c in schedule(suite,tasks)}, {'slug-normalization'})
        self.assertNotEqual(read_json(self.suite_dir/'approval.json')['seal'], seal)
        self.assertEqual(result['repeats'], 3)
        before = self.path.read_bytes()
        with self.assertRaises(EvalError):configure(self.path, task_ids=['unknown-task'])
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(EvalError):configure(self.path, selected_models=['codex:unknown-model'])
        self.assertEqual(self.path.read_bytes(), before)
        configure(self.path, all_tasks=True)
        _, suite, tasks, _, _ = load_suite(self.path)
        self.assertEqual(len(schedule(suite,tasks)), 18)

    def test_effort_sweep_expansion_and_unsupported_selection_are_atomic(self):
        configure(self.path, ['codex:gpt-5.6-sol', 'claude:claude-haiku-4-5-20251001'], repeats=1, all_efforts=True)
        _, suite, tasks, _, _ = load_suite(self.path)
        self.assertEqual(suite['matrix'][0]['efforts'], ['low','medium','high','xhigh','max'])
        self.assertEqual(suite['matrix'][1]['efforts'], ['default'])
        self.assertEqual(len(schedule(suite, tasks)), 18)
        before = self.path.read_bytes()
        with self.assertRaises(EvalError): configure(self.path, efforts=['high'])
        self.assertEqual(before, self.path.read_bytes())
        configure(self.path, ['codex:gpt-5.6-sol'], efforts=['low','max'])
        self.assertEqual(load_suite(self.path)[1]['matrix'][0]['efforts'], ['low','max'])
        args = parser().parse_args(['configure', str(self.path), '--all-efforts', '--repeats', '1'])
        self.assertTrue(args.all_efforts)

    def test_default_sweep_and_optional_budget_are_disclosed_and_sealed(self):
        from ceval.runner import execution_summary, native_argv
        dest = self.root/'defaults'
        args = parser().parse_args(['init', str(dest)])
        self.assertEqual(args.mode, 'local')
        initialize(dest, args.mode, None, purpose='smoke')
        _, suite, tasks, _, seal = load_suite(dest/'suite.json')
        catalog = read_json(DATA/'models.json')['models']
        self.assertEqual(suite['matrix'], [{'provider':m['provider'], 'model':m['id'], 'efforts':m['efforts']} for m in catalog if m['default']])
        for model in ('claude-fable-5-1',):
            self.assertIn({'provider':'claude', 'model':model, 'efforts':['low','medium','high','xhigh','max']}, suite['matrix'])
        self.assertNotIn('claude-mythos-5-1', [lane['model'] for lane in suite['matrix']])
        self.assertIsNone(suite['limits']['spend_stop_usd'])
        summary = execution_summary(suite)
        self.assertIn('No spend stop', summary['message'])
        self.assertEqual(summary['selected_matrix'], suite['matrix'])
        configure(dest/'suite.json', spend_stop_usd=12.5)
        self.assertEqual(load_suite(dest/'suite.json')[1]['limits']['spend_stop_usd'], 12.5)
        self.assertNotEqual(load_suite(dest/'suite.json')[4], seal)
        configure(dest/'suite.json', no_spend_stop=True)
        self.assertEqual(load_suite(dest/'suite.json')[4], seal)
        args = parser().parse_args(['configure', str(self.path), '--no-spend-stop'])
        self.assertTrue(args.no_spend_stop)
        self.assertNotIn('--max-budget-usd', native_argv('claude','claude','claude-sonnet-5','high',10,20,None))
        self.assertIn('--max-budget-usd', native_argv('claude','claude','claude-sonnet-5','high',10,20,12.5))
        configure(dest/'suite.json', selected_models=['codex:gpt-5.6-sol'], efforts=['low'])
        configure(dest/'suite.json', all_models=True)
        self.assertEqual(load_suite(dest/'suite.json')[1]['matrix'], suite['matrix'])

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

    def test_codex_native_cache_writes_use_the_write_rate(self):
        usage = {'input_tokens':1000, 'cached_input_tokens':700, 'cache_write_input_tokens':250,
                 'output_tokens':200, 'reasoning_output_tokens':120}
        r = normalize('codex', json.dumps({'type':'turn.completed','usage':usage}), 'gpt-5.6-sol', self.rates)
        self.assertEqual(r['cache_write_tokens'], 250)
        self.assertAlmostEqual(r['cost_usd'], (50*4 + 700*.4 + 250*5 + 200*20)/1e6)
        usage['cache_creation_input_tokens'] = 999  # Native spelling takes precedence.
        self.assertEqual(normalize('codex', json.dumps({'type':'turn.completed','usage':usage}), 'gpt-5.6-sol', self.rates)['cache_write_tokens'], 250)
        usage['cache_write_input_tokens'] = 301
        self.assertIsNone(normalize('codex', json.dumps({'type':'turn.completed','usage':usage}), 'gpt-5.6-sol', self.rates)['cost_usd'])

    def test_cache_write_display_correction_preserves_original_and_retry_unknowns(self):
        from ceval.report import correct_codex_cache_cost
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            usage = {'input_tokens':1000,'cached_input_tokens':700,'cache_write_input_tokens':250,'output_tokens':200}
            original = {'provider':'codex','model':'gpt-5.6-sol','input_tokens':1000,'cache_read_tokens':700,
                        'output_tokens':200,'cache_write_tokens':None,'cost_usd':.00548,'cost_upper_usd':.009,
                        'completion':1,'status':'passed'}
            raw = json.dumps({'type':'turn.completed','usage':usage})
            write_json(folder/'result.json', original)
            (folder/'events.jsonl').write_text(raw)
            corrected = correct_codex_cache_cost(original, folder, self.rates)
            self.assertAlmostEqual(corrected['cost_usd'], .00573)
            self.assertEqual(corrected['recorded_cost_usd'], .00548)
            self.assertEqual(read_json(folder/'result.json'), original)
            self.assertEqual(corrected['completion'], 1)
            trial = folder/'retries/001';trial.mkdir(parents=True)
            write_json(trial/'result.json', original);(trial/'events.jsonl').write_text(raw)
            missing = folder/'retries/000';missing.mkdir()
            write_json(missing/'result.json', dict(original,cost_usd=None,cost_upper_usd=None,input_tokens=None))
            aggregate = dict(original, retry_attempts=[{'directory':'retries/000'},{'directory':'retries/001'}])
            correction = correct_codex_cache_cost(aggregate, folder, self.rates)
            self.assertIsNone(correction['cost_usd'])
            self.assertAlmostEqual(correction['known_cost_usd'], .00573)

    def test_codex_sums_completed_turns(self):
        e={'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':0,'output_tokens':3}}
        r=normalize('codex','\n'.join([json.dumps(e)]*2),'gpt-5.6-luna',self.rates)
        self.assertEqual(r['input_tokens'],20)
        self.assertEqual(r['turns'],2)

    def test_codex_recovered_errors_and_terminal_failure(self):
        complete = {'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':0,'output_tokens':3}}
        warning = {'type':'error','message':'Reconnecting after rate limit exceeded'}
        failed = {'type':'turn.failed','error':{'message':'Retry limit exceeded'}}
        started = {'type':'turn.started'}
        for stream, success in [([warning, complete], True),
                                ([started, warning, warning, complete], True),
                                ([warning], False), ([warning, failed], False),
                                ([complete, warning], False), ([complete, started], False),
                                ([failed, complete], False)]:
            with self.subTest(stream=stream):
                row = normalize('codex', '\n'.join(map(json.dumps, stream)), 'gpt-5.6-luna', self.rates)
                self.assertEqual(row['provider_success'], success)
                if complete in stream:
                    self.assertEqual(row['input_tokens'], 10)
                    self.assertIsNotNone(row['cost_usd'])

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
    def fake_binary(self, provider='codex', prefix_events=()):
        # Offline native protocol emulator. Every filesystem/grade step still runs.
        binary=self.root/provider
        oracle=(DATA/'examples/slug-normalization/oracle/slug.py').read_text()
        events=[{'type':'item.completed','item':{'type':'command_execution'}},
                {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':50,'output_tokens':30}}]
        if provider=='claude':
            events=[{'type':'result','subtype':'success','num_turns':2,'total_cost_usd':.03,
                     'usage':{'input_tokens':50,'cache_read_input_tokens':10,'cache_creation_input_tokens':20,'output_tokens':30}}]
        events = list(prefix_events) + events
        binary.write_text('#!'+sys.executable+'\nimport sys,json\nfrom pathlib import Path\n'
            +"if '--version' in sys.argv: print('codex-cli 0.153.4' if "+repr(provider)+"=='codex' else '2.1.251 (Claude Code)');sys.exit(0)\n"
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
        descriptions = dataset(out)['tasks']
        self.assertEqual(len(descriptions), 1)
        self.assertTrue(descriptions[0]['description'])
        self.assertTrue(descriptions[0]['human_summary'])
        self.assertNotEqual(descriptions[0]['human_summary'], descriptions[0]['description'])
        (self.suite_dir/'tasks/slug-normalization/instruction.md').write_text('Changed after run')
        self.assertEqual(dataset(out)['tasks'], descriptions)

    def test_changed_suite_cannot_resume(self):
        self.prep()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key'}),contextlib.redirect_stdout(io.StringIO()):run(self.path,self.root/'run')
        self.s['repeats']=2;self.save()
        with self.assertRaises(EvalError):run(self.path,self.root/'run',resume=True)

    def test_native_reconnect_recovery_keeps_verified_pass(self):
        from ceval.parallel import run as run_parallel
        self.prep()
        self.fake_binary(prefix_events=[{'type':'error','message':'Reconnecting after rate limit exceeded'}])
        self.approve()
        out = self.root/'run'
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test-key'}), contextlib.redirect_stdout(io.StringIO()):
            run_parallel(self.path, out, retry_delay=0)
        row = read_json(out/'results.json')['rows'][0]
        self.assertEqual(row['status'], 'passed')
        self.assertTrue(row['valid'])
        self.assertEqual(row['completion'], 1)
        self.assertEqual(row['grader_exit_code'], 0)
        self.assertEqual(row['retry_count'], 0)
        self.assertEqual(len(row['retry_attempts']), 1)
        trial = out/'attempts'/row['cell_id']/row['retry_attempts'][0]['directory']
        self.assertIn('Reconnecting', (trial/'events.jsonl').read_text())

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

    def test_old_claude_blocks_fable_but_runs_compatible_model(self):
        self.prep(('claude',))
        binary = Path(self.s['execution']['claude_bin'])
        binary.write_text(binary.read_text().replace('2.1.251', '2.1.220'))
        self.s['execution']['claude_version'] = '2.1.220'
        self.s['matrix'].append({'provider':'claude','model':'claude-fable-5-1','efforts':['medium']})
        self.save(); self.approve()
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY':'test-key'}), contextlib.redirect_stdout(io.StringIO()):
            run(self.path, self.root/'run')
        rows = {r['model']:r for r in read_json(self.root/'run/results.json')['rows']}
        self.assertEqual(rows['claude-sonnet-5']['completion'], 1)
        fable = rows['claude-fable-5-1']
        self.assertTrue(fable['not_started'])
        self.assertIsNone(fable['exit_code'])
        self.assertIn('2.1.251', fable['diagnostic'])
        self.assertFalse(read_json(self.root/'run/preflight.json')['claude']['ok'])

    def test_fable_minimum_version_still_requires_matching_pin(self):
        self.prep(('claude',))
        self.s['matrix'] = [{'provider':'claude','model':'claude-fable-5-1','efforts':['medium']}]
        self.s['execution']['claude_version'] = '2.1.220'
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY':'test-key'}), contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(preflight(self.s)['claude']['ok'])
            self.s['execution']['claude_version'] = '2.1.251'
            pf = preflight(self.s)['claude']
        self.assertTrue(pf['ok'])
        self.assertEqual(pf['models']['claude-fable-5-1']['account_access'], 'not_probed')

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
    def test_known_spend_includes_partial_retry_cost_without_double_counting(self):
        base = {'provider':'codex', 'model':'test', 'effort':'medium', 'completion':1, 'valid':True}
        rows = [dict(base, cost_usd=2, known_cost_usd=2),
                dict(base, cost_usd=None, known_cost_usd=.5),
                dict(base, cost_usd=0, known_cost_usd=9),
                dict(base, cost_usd=None)]
        group = summarize(rows, 4)['groups'][0]
        self.assertEqual(group['known_cost_usd'], 2.5)
        self.assertEqual(group['cost_missing'], 2)
        self.assertIsNone(group['cost_per_success_usd'])

    def test_first_round_schedules_each_lane_once_and_explicit_followup_twice(self):
        dest = self.root/'first-round'
        initialize(dest, 'local', None, purpose='smoke')
        path = dest/'suite.json'
        _, suite, tasks, _, first_seal = load_suite(path)
        first = schedule(suite, tasks)
        expected = sum(len(m['efforts']) for m in suite['matrix']) * len(tasks)
        self.assertEqual(len(first), expected)
        self.assertEqual({c['repeat'] for c in first}, {1})
        self.assertEqual({c['provider'] for c in first}, {'codex', 'claude'})
        configure(path, repeats=2)
        _, followup, tasks, _, second_seal = load_suite(path)
        self.assertNotEqual(first_seal, second_seal)
        self.assertEqual(len(schedule(followup, tasks)), 2 * expected)
        configure(path, all_efforts=True)
        self.assertEqual(read_json(path)['repeats'], 2)

    def test_repeat_averages_include_failures_and_preserve_missing_telemetry(self):
        rows = [{'task_id':'one','provider':'codex','model':'test','effort':'medium',
                 'completion':int(i != 1),'valid':True,'cost_usd':cost,'latency_seconds':latency,
                 'input_tokens':100,'output_tokens':10,'cache_read_tokens':0}
                for i, (cost, latency) in enumerate([(1, 10), (2, 20), (6, 60)])]
        run = {'suite':{'repeats':3}, 'schedule':[dict(r, repeat=i) for i,r in enumerate(rows)]}
        point = average_attempts(rows, run)[0]
        self.assertEqual((point['cost_usd'],point['latency_seconds']), (3, 30))
        self.assertEqual((point['completion'],point['successes'],point['attempts']), (0,2,3))
        self.assertEqual(point['cache_read_tokens'], 0)
        partial = average_attempts(rows[:1], run)[0]
        self.assertEqual((partial['status'],partial['expected_attempts'],partial['completion']), ('pending',3,0))
        rows[1]['cost_usd'] = None
        self.assertIsNone(average_attempts(rows, run)[0]['cost_usd'])
        self.assertEqual(parser().parse_args(['smoke','--provider','codex','--output','unused']).repeats, 1)
        self.assertEqual(read_json(self.path)['repeats'], 1)  # Explicit fixture override survives.

    def test_dashboard_scope_keeps_one_simulation_and_averages_runs_separately(self):
        workspace = self.root/'evaluations'
        for name in ('interview','github'):
            out = workspace/name/'run'
            demo(out)
            manifest = read_json(out/'run.json'); manifest['simulation'] = False
            write_json(out/'run.json', manifest)
            rows = read_json(out/'results.json')['rows']
            for row in rows:
                row['simulation'] = False
                dest = out/'attempts'/row['cell_id']
                write_json(dest/'result.json', row)
                write_json(dest/'result.sha256.json', {'sha256':digest(row)})
            write_json(out/'results.json', {'rows':rows})
        scoped = dashboard_dataset(workspace/'interview'/'run', scope=True)
        combined = dashboard_dataset(workspace/'interview'/'run')
        self.assertEqual(len(scoped['rows']),18)
        self.assertEqual(len(scoped['averages']),6)
        self.assertEqual(len(combined['rows']),36)
        self.assertEqual(len(combined['averages']),12)
        self.assertEqual(len({r['source_run'] for r in combined['averages']}),2)

    def test_combined_dashboard_retains_sources_and_deduplicates_directories(self):
        one, two = self.root/'one', self.root/'two'
        demo(one); demo(two)
        before = (one/'results.json').read_bytes()
        combined = dashboard_dataset([one, two, one])
        self.assertEqual(len(combined['rows']), 36)
        self.assertEqual(combined['summary']['scheduled'], 36)
        self.assertEqual({row['source_run'] for row in combined['rows']}, {str(one.resolve()), str(two.resolve())})
        self.assertEqual(len(combined['run']['sources']), 2)
        self.assertIn('Separate runs', combined['run']['comparison_note'])
        self.assertEqual((one/'results.json').read_bytes(), before)
        self.assertEqual(dashboard_dataset([one]), dataset(one, comparison=True))
        self.assertIn('source_run', csv_text(combined['rows']).splitlines()[0])

    def test_legacy_task_descriptions_use_matching_suite_without_changing_results(self):
        out = self.root/'legacy'
        demo(out)
        manifest = read_json(out/'run.json')
        manifest['suite'] = self.s
        write_json(out/'run.json', manifest)
        before = (out/'results.json').read_bytes()
        tasks = dataset(out)['tasks']
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(t['description'] and t['use_case'] for t in tasks))
        self.assertTrue(all(t['metadata_source'] == 'local_task_definition' for t in tasks))
        self.assertEqual((out/'results.json').read_bytes(), before)
        other = self.root/'other'
        demo(other)
        combined = dashboard_dataset([out, other])
        self.assertEqual({t['source_run'] for t in combined['tasks']}, {str(out.resolve()), str(other.resolve())})

    def test_combined_dashboard_checks_every_source_integrity(self):
        one, two = self.root/'one', self.root/'two'
        demo(one); demo(two)
        row = read_json(two/'results.json')['rows'][0]
        attempt = two/'attempts'/row['cell_id']
        write_json(attempt/'result.json', row)
        write_json(attempt/'result.sha256.json', {'sha256': 'tampered'})
        with self.assertRaises(EvalError):
            dashboard_dataset([one, two])

    def test_workspace_dashboard_discovers_new_live_runs_and_excludes_demo(self):
        workspace = self.root/'evaluations'
        demo(workspace/'demo')
        def live(name):
            root = workspace/name
            demo(root)
            run = read_json(root/'run.json'); run['simulation'] = False
            write_json(root/'run.json', run)
            results = read_json(root/'results.json')
            for row in results['rows']:
                row['simulation'] = False
                attempt = root/'attempts'/row['cell_id']
                write_json(attempt/'result.json', row)
                write_json(attempt/'result.sha256.json', {'sha256': digest(row)})
            write_json(root/'results.json', results)
            return root
        first = live('first')
        write_json(first/'candidate-data/run.json', read_json(first/'run.json'))
        write_json(first/'candidate-data/results.json', {'rows': []})
        self.assertEqual(len(dashboard_dataset(workspace)['rows']), 18)
        live('second')
        combined = dashboard_dataset(first)
        self.assertEqual(len(combined['rows']), 36)
        self.assertEqual(combined['summary']['scheduled'], 36)
        self.assertFalse(any(row['simulation'] for row in combined['rows']))
        expected_failures = 2 * sum(row['completion'] == 0 for row in read_json(first/'results.json')['rows'])
        self.assertEqual(sum(row['completion'] == 0 for row in combined['rows']), expected_failures)

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

class CatalogTests(Workspace):
    def test_catalog_integrity_and_lookup(self):
        from ceval.catalog import examples
        cards = read_json(DATA/'task-examples.json')['examples']
        inventory = read_json(DATA/'task-inventory.json')['tasks']
        refs = {b['id'] for b in read_json(DATA/'benchmarks.json')['benchmarks']}
        ids = [x['id'] for x in cards+inventory]
        self.assertEqual(len(ids), len(set(ids)))
        by_id = {x['id']: x for x in inventory}
        for card in cards:
            self.assertIn(card['benchmark'], refs)
            if card.get('inventory_id'):
                self.assertEqual(card['source_url'], by_id[card['inventory_id']]['source_url'])
            self.assertTrue(card['what_it_tests'] and card['how_it_tests'])
        self.assertEqual(examples('frontend editor focus', limit=1)['examples'][0]['benchmark'], 'deepswe')
        self.assertEqual(examples('unmatchedzzzz')['examples'], [])

    def test_portfolio_scaffolds_every_workflow(self):
        from ceval.catalog import portfolio
        discovery = self.suite_dir/'discovery.json'
        write_json(discovery, {'workflows': [
            {'id':'front','name':'Frontend','description':'Editor focus'},
            {'id':'api','name':'Backend API','description':'Streaming cancellation'}]})
        result = portfolio(discovery, self.path)
        self.assertEqual(result['minimum_tasks'], 6)
        self.assertEqual({(s['workflow_id'], s['difficulty']) for s in result['slots']},
                         {(w,t) for w in ('front','api') for t in ('easy','medium','hard')})
        self.assertEqual(read_json(self.path)['purpose'], 'customer')

    def test_customer_requires_each_tier_for_each_workflow(self):
        self.s.update(purpose='customer', workflows=[{'id':'front','name':'Frontend','description':'UI behavior'}])
        self.save()
        for task in self.s['tasks']:
            path = self.suite_dir/task/'task.json'
            spec = read_json(path); spec['workflow_id'] = 'front'; write_json(path,spec)
        load_suite(self.path)
        self.s['workflows'].append({'id':'api','name':'Backend','description':'API behavior'})
        self.save()
        with self.assertRaisesRegex(EvalError, 'Missing workflow difficulty tiers'):
            load_suite(self.path)

    def test_provenance_links_original_tasks_and_malformed_values(self):
        from ceval.catalog import validate_provenance
        task = read_json(self.suite_dir/self.s['tasks'][0]/'task.json')
        task['benchmark_refs'] = []
        validate_provenance(task)
        card = read_json(DATA/'task-examples.json')['examples'][0]
        task['benchmark_refs'] = [card['benchmark']]
        task['provenance'] = {'kind':'benchmark-inspired','rationale':'Adapt editor behavior','sources':[
            {'example_id':card['id'],'source_url':card['source_url'],'adaptation':'Independent synthetic editor fixture'}]}
        validate_provenance(task)
        task['provenance']['sources'][0]['source_url'] = 'https://example.com/wrong'
        with self.assertRaisesRegex(EvalError, 'original source URL'):
            validate_provenance(task)
        for malformed in ([], None):
            task['provenance'] = malformed
            with self.assertRaises(EvalError): validate_provenance(task)

    def test_legacy_suite_compatibility(self):
        self.s['schema_version'] = 1
        self.s.pop('purpose'); self.s.pop('workflows'); self.save()
        load_suite(self.path)

class HistoryCoverageTests(unittest.TestCase):
    def test_review_transcripts_are_excluded_and_truncation_disclosed(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for text in [
                'The following is the Codex agent history whose request action you are assessing.\n>>> TRANSCRIPT START\nEmbedded tool output\n>>> APPROVAL REQUEST START',
                'The following is the Codex agent history added since your last approval assessment.\n>>> TRANSCRIPT DELTA START\nEmbedded tool output\n>>> APPROVAL REQUEST START',
                'Build a dashboard. ' + 'x'*5000,
            ]:
                records.append({'type':'response_item','timestamp':datetime.now(timezone.utc).isoformat(),
                    'payload':{'role':'user','content':[{'type':'input_text','text':text}]}})
            (root/'session.jsonl').write_text('\n'.join(json.dumps(r) for r in records))
            output = root/'evidence.json'
            result = history('codex', root, 1, True, output)
            self.assertEqual(result['excluded_review_transcripts'], 2)
            self.assertEqual(result['truncated_excerpts'], 1)
            self.assertEqual(result['excerpt_count'], 1)
            self.assertTrue(result['parser_coverage_complete'])
            self.assertFalse(result['coverage_complete'])
            self.assertNotIn('Embedded tool output', output.read_text())
