import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch
from test_evaluation import Workspace
from ceval.core import write_json, read_json, load_suite, digest, EvalError
from ceval.parallel import run
from ceval.rate_limits import is_rate_limited, retry_delay
from ceval.report import dataset


class RetryTests(Workspace):
    def test_recovered_retry_retains_runtime_review_signal(self):
        from ceval.reflection import reflect
        self.prepare()
        calls = []
        def attempt(cell, task, suite, pricing, directory, pf):
            calls.append(directory)
            first = len(calls) == 1
            row = self.result(cell, directory, rate=first)
            row['runtime_diagnostics'] = ['filesystem_sandbox_helper_failed'] if first else []
            return row
        with patch('ceval.runner.preflight', return_value={'codex': {'ok': True}}), patch('ceval.runner.attempt', side_effect=attempt), contextlib.redirect_stdout(io.StringIO()):
            run(self.path, self.root / 'run', retry_delay=0)
        original = (calls[0] / 'result.json').read_bytes()
        row = read_json(self.root / 'run/results.json')['rows'][0]
        self.assertEqual((row['status'], row['completion']), ('passed', 1))
        self.assertEqual(row['runtime_diagnostics'], ['filesystem_sandbox_helper_failed'])
        review = reflect([self.root / 'run'])
        self.assertTrue(review['needs_review'])
        self.assertIn('runtime_diagnostic', review['runs'][0]['tasks'][0]['signals'])
        self.assertEqual((calls[0] / 'result.json').read_bytes(), original)

    def prepare(self):
        self.s['tasks'] = ['tasks/slug-normalization']
        self.save()
        write_json(self.suite_dir / 'approval.json', {'seal':load_suite(self.path)[4]})

    def result(self, cell, directory, rate=False, cost=.1, status=None):
        Path(directory).mkdir(parents=True, exist_ok=True)
        (Path(directory)/'events.jsonl').write_text(json.dumps({'type':'error','message':'Rate limit exceeded, try again in 10ms'}) if rate else '')
        return {**cell,'status':status or ('provider_error' if rate else 'passed'), 'completion':0 if rate or status else 1,
                'valid':not rate,'simulation':False,'cost_usd':cost,'cost_upper_usd':cost,'cost_lower_usd':cost,
                'latency_seconds':1,'input_tokens':10 if cost is not None else None,'output_tokens':1}

    def test_rate_limit_retries_preserve_cost_time_and_single_repeat(self):
        self.prepare()
        calls=[]
        def attempt(cell, task, suite, pricing, directory, pf):
            calls.append(directory)
            return self.result(cell,directory,rate=len(calls)<3)
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.runner.attempt',side_effect=attempt), contextlib.redirect_stdout(io.StringIO()):
            info=run(self.path,self.root/'run',retry_delay=0)
        self.assertEqual(info['state'],'complete')
        rows=dataset(self.root/'run')['rows'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['retry_count'],2)
        self.assertEqual(rows[0]['completion'],1)
        self.assertAlmostEqual(rows[0]['cost_usd'],.3)
        self.assertGreaterEqual(rows[0]['latency_seconds'],3)
        self.assertEqual(len(rows[0]['retry_attempts']),3)
        self.assertEqual(len(set(calls)),3)

    def test_resume_rate_error_keeps_original_and_unknown_cost(self):
        self.prepare()
        calls=[]
        def attempt(cell, task, suite, pricing, directory, pf):
            calls.append(directory)
            return self.result(cell,directory,rate=len(calls)==1,cost=None if len(calls)==1 else .1)
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.runner.attempt',side_effect=attempt), contextlib.redirect_stdout(io.StringIO()):
            first=run(self.path,self.root/'run',rate_limit_retries=0,retry_delay=0)
            original=read_json(calls[0]/'result.json')
            info=run(self.path,self.root/'run',resume=True,rate_limit_retries=3,retry_delay=0)
        self.assertEqual(first['stop_reason'],'rate_limit_retries_exhausted')
        self.assertEqual(info['state'],'complete')
        self.assertEqual(len(calls),2)
        self.assertEqual(read_json(calls[0]/'result.json'),original)
        row=dataset(self.root/'run')['rows'][0]
        self.assertIsNone(row['cost_usd'])
        self.assertFalse(row['telemetry_complete'])
        self.assertTrue(row['rate_limit_cost_incomplete'])
        self.assertEqual(row['known_cost_usd'],.1)

    def test_exhaustion_is_bounded_and_not_restarted_on_resume(self):
        self.prepare()
        def attempt(cell, task, suite, pricing, directory, pf):return self.result(cell,directory,rate=True)
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.runner.attempt',side_effect=attempt) as mock, contextlib.redirect_stdout(io.StringIO()):
            info=run(self.path,self.root/'run',rate_limit_retries=2,retry_delay=0)
            resumed=run(self.path,self.root/'run',resume=True,rate_limit_retries=2,retry_delay=0)
        self.assertEqual(mock.call_count,3)
        self.assertEqual(resumed['stop_reason'],'rate_limit_retries_exhausted')
        self.assertEqual(info['stop_reason'],'rate_limit_retries_exhausted')

    def test_verifier_failure_never_retries_even_with_rate_words(self):
        self.prepare()
        def attempt(cell, task, suite, pricing, directory, pf):return self.result(cell,directory,rate=True,status='failed')
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.runner.attempt',side_effect=attempt) as mock, contextlib.redirect_stdout(io.StringIO()):
            run(self.path,self.root/'run',retry_delay=0)
        self.assertEqual(mock.call_count,1)

    def test_only_native_transient_error_fields_trigger_retry(self):
        self.prepare();p=self.root/'events.jsonl'
        r={'status':'provider_error'}
        p.write_text(json.dumps({'type':'item.completed','item':{'text':'rate limit'}}))
        self.assertFalse(is_rate_limited(r,self.root))
        p.write_text(json.dumps({'type':'error','message':'429 insufficient_quota'}))
        self.assertFalse(is_rate_limited(r,self.root))
        p.write_text(json.dumps({'type':'result','is_error':True,'errors':['rate_limit_error; retry_after: 90']}))
        self.assertTrue(is_rate_limited(r,self.root))
        self.assertEqual(retry_delay(self.root,1,30),90)
        self.assertEqual(retry_delay(self.root,3,30),120)
        p.write_text(json.dumps({'type':'error','message':'rate limit exceeded'})+'\n'+json.dumps({'type':'turn.completed','usage':{}}))
        self.assertFalse(is_rate_limited(r,self.root))

    def test_retry_evidence_tampering_is_rejected(self):
        self.prepare()
        def attempt(cell, task, suite, pricing, directory, pf):return self.result(cell,directory)
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.runner.attempt',side_effect=attempt), contextlib.redirect_stdout(io.StringIO()):
            run(self.path,self.root/'run',retry_delay=0)
        raw=next((self.root/'run/attempts').glob('*/retries/000/result.json'))
        row=read_json(raw);row['cost_usd']=0;write_json(raw,row)
        with self.assertRaisesRegex(EvalError,'Retry result integrity'):
            dataset(self.root/'run')
