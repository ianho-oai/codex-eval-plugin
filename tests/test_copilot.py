"""Synthetic contract tests; these do not claim live Copilot access."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/codex-eval-plugin'))
from ceval.cli import initialize, configure, doctor, load_local_keys, smoke, models, parser
from ceval.core import EvalError, load_suite, read_json, write_json, redact, digest
from ceval.runner import attempt, native_argv, clean_env, preflight
from ceval.telemetry import normalize, copilot_usage
from ceval.rate_limits import Cooldown, transient_reason
from ceval.copilot_auth import selected_account


def event(kind, **data):
    return json.dumps({'type': kind, 'data': data})


class CopilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        initialize(self.root / 'suite', 'local', None, purpose='smoke')
        self.path = self.root / 'suite/suite.json'

    def select(self):
        configure(self.path, ['copilot:gpt-5.4'], efforts=['low'])
        return read_json(self.path)

    def test_opt_in_and_sealed_credit_limit(self):
        self.assertNotIn('copilot', {m['provider'] for m in read_json(self.path)['matrix']})
        s = self.select()
        self.assertIsNone(s['limits']['copilot_max_ai_credits'])
        seal = load_suite(self.path)[4]
        s['limits']['copilot_max_ai_credits'] = 40
        write_json(self.path, s)
        self.assertNotEqual(seal, load_suite(self.path)[4])
        capped_seal = load_suite(self.path)[4]
        s['limits']['copilot_max_ai_credits'] = None
        write_json(self.path, s)
        self.assertNotEqual(capped_seal, load_suite(self.path)[4])
        for value in (0, 29, True):
            s['limits']['copilot_max_ai_credits'] = value
            write_json(self.path, s)
            with self.assertRaises(EvalError):
                load_suite(self.path)

    def test_provider_selection_is_explicit_atomic_and_excludes_unselected_harnesses(self):
        configure(self.path, providers=['codex', 'copilot'], all_efforts=True)
        suite = read_json(self.path)
        self.assertEqual({m['provider'] for m in suite['matrix']}, {'codex', 'copilot'})
        self.assertEqual({m['model'] for m in suite['matrix'] if m['provider'] == 'copilot'},
                         {'gpt-6-astra', 'gpt-5.6-sol', 'gpt-5.6-terra'})
        self.assertIsNone(suite['limits']['copilot_max_ai_credits'])
        configure(self.path, all_efforts=True, repeats=1, no_spend_stop=True)
        self.assertEqual(read_json(self.path)['matrix'], suite['matrix'])
        self.assertEqual(next(m for m in suite['matrix'] if m['provider']=='copilot' and m['model']=='gpt-5.6-sol')['efforts'],
                         ['none','low','medium','high','xhigh','max'])
        before = self.path.read_bytes()
        for options in ({'providers':[]}, {'providers':['unknown']},
                        {'providers':['copilot'], 'selected_models':['codex:gpt-6-astra']}):
            with self.assertRaises(EvalError):
                configure(self.path, **options)
            self.assertEqual(self.path.read_bytes(), before)
        configure(self.path, providers=['codex','claude','copilot'])
        self.assertEqual({m['provider'] for m in read_json(self.path)['matrix']}, {'codex','claude','copilot'})
        configure(self.path, all_models=True)
        self.assertEqual({m['provider'] for m in read_json(self.path)['matrix']}, {'codex','claude'})
        configure(self.path, ['copilot:gpt-6-astra'], efforts=['low'])
        configure(self.path, providers=['copilot'])
        self.assertEqual(read_json(self.path)['matrix'][0]['efforts'], ['low','medium','high','xhigh','max'])
        args = parser().parse_args(['configure', str(self.path), '--provider', 'codex', '--provider', 'copilot'])
        self.assertEqual(args.provider, ['codex','copilot'])

    def test_copilot_reporting_preserves_missing_receipts_and_invoice_unknown(self):
        from ceval.report import average_attempts, summarize, csv_text
        base = {'provider':'copilot', 'model':'gpt-6-astra', 'effort':'low', 'task_id':'a',
                'valid':True, 'completion':1, 'status':'passed', 'cost_usd':None, 'latency_seconds':3,
                'copilot_ai_credits':2, 'copilot_usage_value_usd':.02}
        rows = [base, dict(base, completion=0, copilot_ai_credits=None, copilot_usage_value_usd=None)]
        average = average_attempts(rows, {'suite':{'repeats':2}})[0]
        self.assertIsNone(average['cost_usd'])
        self.assertIsNone(average['copilot_usage_value_usd'])
        self.assertEqual(average['successes'], 1)
        group = summarize(rows, 2)['groups'][0]
        self.assertEqual(group['known_copilot_usage_value_usd'], .02)
        self.assertEqual(group['copilot_usage_value_usd_missing'], 1)
        self.assertEqual(group['cost_missing'], 2)
        self.assertIn('copilot_usage_value_usd', csv_text(rows))
        group = summarize([rows[1]], 1)['groups'][0]
        self.assertIsNone(group['known_copilot_usage_value_usd'])
        from ceval.rate_limits import rollup
        rolled = rollup([(base, self.root/'0'), (rows[1], self.root/'1')], self.root, 0)
        self.assertIsNone(rolled['copilot_usage_value_usd'])
        self.assertEqual(summarize([rolled], 1)['groups'][0]['known_copilot_usage_value_usd'], .02)
        self.assertEqual(summarize([rolled], 1)['groups'][0]['copilot_usage_value_usd_missing'], 1)

    def test_offline_copilot_queue_report_and_resume_preserve_evidence(self):
        from ceval.runner import validate_graders
        from ceval.parallel import run
        from ceval.report import report, dataset
        binary = self.root/'copilot-emulator'
        binary.write_text('#!'+sys.executable+'\n'+'''import json, sys
from pathlib import Path
if '--version' in sys.argv:
 print('GitHub Copilot CLI 1.0.88.')
elif '--help' in sys.argv:
 print('--output-format --no-ask-user --no-custom-instructions --available-tools --disable-builtin-mcps --no-remote-export --max-ai-credits --usage-output-file --reasoning-effort')
else:
 assert '--reasoning-effort' in sys.argv
 Path('slug.py').write_text("import re, unicodedata\\ndef slugify(text):\\n if not isinstance(text,str): raise TypeError()\\n return '-'.join(re.findall('[a-z0-9]+',unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower()))\\n")
 Path(sys.argv[sys.argv.index('--usage-output-file')+1]).write_text(json.dumps({'currentModel':'gpt-6-astra','totalNanoAiu':1000000000,'modelMetrics':{'gpt-6-astra':{'usage':{'inputTokens':100,'outputTokens':20}}}}))
 print(json.dumps({'type':'result','exitCode':0}))
''')
        binary.chmod(0o700)
        configure(self.path, ['copilot:gpt-6-astra'], task_ids=['slug-normalization'], efforts=['low'], copilot_binary=str(binary))
        validate_graders(self.path)
        write_json(self.path.parent/'approval.json', {'seal':load_suite(self.path)[4], 'approved_by':'offline synthetic test',
                    'validation_digest':digest(read_json(self.path.parent/'validation.json'))})
        output = self.root/'run'
        with patch.dict(os.environ, {'COPILOT_GITHUB_TOKEN':'synthetic-offline-token'}, clear=True):
            result = run(self.path, output, workers=2)
            self.assertEqual(result['state'], 'complete')
            before = (output/'results.json').read_bytes()
            run(self.path, output, resume=True, workers=2)
        report(output)
        self.assertEqual(before, (output/'results.json').read_bytes())
        d = dataset(output, comparison=True)
        self.assertEqual(d['rows'][0]['completion'], 1)
        self.assertIsNone(d['averages'][0]['cost_usd'])
        self.assertEqual(d['averages'][0]['copilot_usage_value_usd'], .01)
        self.assertIn('copilot_usage_value_usd', (output/'results.csv').read_text())

    def test_account_reported_efforts_include_none_only_for_copilot(self):
        configure(self.path, ['copilot:gpt-5.6-terra'], efforts=['none','max'])
        s = read_json(self.path)
        self.assertEqual(s['matrix'][0]['efforts'], ['none','max'])
        self.assertIn('none', native_argv('copilot','copilot','gpt-5.6-terra','none',120,50,None))
        with self.assertRaises(EvalError):
            configure(self.path, ['copilot:gpt-6-astra'], efforts=['none'])
        s['matrix'] = [{'provider':'codex','model':'gpt-5.6-terra','efforts':['none']}]
        write_json(self.path,s)
        with self.assertRaises(EvalError):
            load_suite(self.path)

    def test_missing_pin_auto_model_and_docker_rejected(self):
        s = self.select()
        del s['execution']['copilot_version']
        write_json(self.path, s)
        with self.assertRaises(EvalError):
            load_suite(self.path)
        s['execution']['copilot_version'] = '1.0.83'
        s['matrix'][0]['model'] = 'auto'
        write_json(self.path, s)
        with self.assertRaises(EvalError):
            load_suite(self.path)
        with self.assertRaises(EvalError):
            native_argv('copilot', 'copilot', 'gpt-5.4', 'low', 120, 50, None, docker=True)

    def test_usage_and_billing_remain_distinct(self):
        raw = '\n'.join([event('assistant.usage', model='gpt-5.4', inputTokens=100, outputTokens=20,
                              cacheReadTokens=50, cacheWriteTokens=2, cost=1, duration=100),
                         event('tool.execution_start', toolName='edit'),
                         event('session.shutdown', shutdownType='routine', currentModel='gpt-5.4',
                               totalPremiumRequests=1, totalNanoAiu=1000000000, totalApiDurationMs=100)])
        row = normalize('copilot', raw, 'gpt-5.4', {'models': {'gpt-5.4': {'input': 999, 'output': 999}}})
        self.assertTrue(row['provider_success'])
        self.assertEqual((row['input_tokens'], row['output_tokens'], row['turns'], row['tool_calls']), (100, 20, 1, 1))
        self.assertEqual(row['copilot_nano_aiu'], 1000000000)
        self.assertIsNone(row['cost_usd'])
        self.assertIsNone(row['reasoning_tokens'])
        self.assertFalse(row['telemetry_complete'])

    def test_error_truncation_and_model_substitution_cannot_pass(self):
        cases = ['', event('assistant.message', content='Done'), event('session.idle', aborted=True),
                 event('session.shutdown', shutdownType='error'),
                 event('session.error', message='denied')+'\n'+event('session.idle'),
                 event('assistant.usage', model='other')+'\n'+event('session.idle')]
        for raw in cases:
            self.assertFalse(normalize('copilot', raw, 'gpt-5.4', {})['provider_success'], raw)

    def test_cli_result_and_cumulative_checkpoint_without_token_usage(self):
        raw = '\n'.join([
            event('model.call_start', model='gpt-5.4', turnId='0'),
            event('model.call_start', model='gpt-5.4', turnId='1'),
            event('session.usage_checkpoint', totalNanoAiu=1000000000, totalPremiumRequests=1),
            event('session.usage_checkpoint', totalNanoAiu=2000000000, totalPremiumRequests=1),
            event('assistant.idle'),
            json.dumps({'type': 'result', 'exitCode': 0, 'usage': {
                'premiumRequests': 1, 'totalApiDurationMs': 1234, 'sessionDurationMs': 1500}}),
        ])
        row = normalize('copilot', raw, 'gpt-5.4', {})
        self.assertTrue(row['provider_success'])
        self.assertEqual(row['observed_models'], ['gpt-5.4'])
        self.assertEqual(row['turns'], 2)
        self.assertEqual(row['copilot_nano_aiu'], 2000000000)
        self.assertEqual(row['copilot_premium_requests'], 1)
        self.assertEqual(row['provider_api_duration_ms'], 1234)
        self.assertEqual(row['provider_duration_ms'], 1500)
        self.assertIsNone(row['input_tokens'])
        self.assertIsNone(row['cost_usd'])

    def test_cli_result_requires_success_and_same_observed_model(self):
        good = json.dumps({'type': 'result', 'exitCode': 0})
        for raw in [event('assistant.idle'), json.dumps({'type': 'result'}),
                    json.dumps({'type': 'result', 'exitCode': False}),
                    json.dumps({'type': 'result', 'exitCode': 1}),
                    event('model.call_start', model='other')+'\n'+good,
                    event('session.error', message='denied')+'\n'+good,
                    good+'\n'+event('session.abort')]:
            self.assertFalse(normalize('copilot', raw, 'gpt-5.4', {})['provider_success'], raw)

    def test_auth_is_explicit_and_redacted(self):
        token = 'gho_'+'a'*36
        with patch.dict(os.environ, {'COPILOT_GITHUB_TOKEN': token, 'GH_TOKEN': 'not-inherited',
                                     'COPILOT_PROVIDER_BASE_URL': 'not-inherited'}):
            env = clean_env()
            self.assertNotIn('COPILOT_GITHUB_TOKEN', env)
            self.assertNotIn('COPILOT_PROVIDER_BASE_URL', env)
            self.assertNotIn(token, redact(token))
        self.assertEqual(redact(token), '[REDACTED]')

    def test_native_process_and_deterministic_grader(self):
        s = self.select()
        s['limits']['copilot_max_ai_credits'] = 30
        binary = self.root / 'fake-copilot'
        binary.write_text('#!'+sys.executable+'\n'+'''import json, os, sys
from pathlib import Path
assert '--no-ask-user' in sys.argv and '--no-custom-instructions' in sys.argv
assert '--allow-all' not in sys.argv and '--allow-all-paths' not in sys.argv
assert os.environ['HOME'] == os.environ['COPILOT_HOME']
assert 'GH_TOKEN' not in os.environ and 'OPENAI_API_KEY' not in os.environ
assert os.environ['COPILOT_GITHUB_TOKEN'] == 'test-token'
assert '-p' in sys.argv and 'slug' in sys.argv[sys.argv.index('-p')+1]
Path('slug.py').write_text("import re, unicodedata\\ndef slugify(text):\\n if not isinstance(text,str): raise TypeError()\\n return '-'.join(re.findall('[a-z0-9]+',unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower()))\\n")
Path(sys.argv[sys.argv.index('--usage-output-file')+1]).write_text(json.dumps({'currentModel':'gpt-5.4','totalNanoAiu':1000000000,'modelMetrics':{'gpt-5.4':{'usage':{'inputTokens':100,'outputTokens':20}}}}))
print(json.dumps({'type':'result','exitCode':0,'usage':{'premiumRequests':1}}))
''')
        binary.chmod(0o700)
        s['execution']['copilot_bin'] = str(binary)
        task = next(t for t in load_suite(self.path)[2] if t['spec']['id'] == 'slug-normalization')
        cell = {'cell_id':'synthetic', 'task_id':'slug-normalization', 'provider':'copilot',
                'model':'gpt-5.4', 'effort':'low', 'repeat':1}
        with patch.dict(os.environ, {'COPILOT_GITHUB_TOKEN':'test-token', 'GH_TOKEN':'excluded'}):
            row = attempt(cell, task, s, {}, self.root/'attempt', {'ok':True})
        self.assertEqual((row['status'], row['completion'], row['grader_exit_code']), ('passed', 1, 0))
        self.assertIsNone(row['cost_usd'])
        self.assertEqual(row['input_tokens'], 100)
        self.assertEqual(row['copilot_usage_value_usd'], .01)
        argv = read_json(self.root/'attempt/invocation.json')['argv']
        self.assertEqual(argv[argv.index('--max-ai-credits')+1], '30')
        self.assertNotIn('test-token', json.dumps(argv))
        s['limits']['copilot_max_ai_credits'] = None
        with patch.dict(os.environ, {'COPILOT_GITHUB_TOKEN':'test-token'}):
            unlimited = attempt(cell, task, s, {}, self.root/'unlimited', {'ok':True})
        self.assertEqual(unlimited['status'], 'passed')
        argv = read_json(self.root/'unlimited/invocation.json')['argv']
        self.assertNotIn('--max-ai-credits', argv)

    def test_doctor_does_not_claim_account_access(self):
        s = self.select()
        def fake_execute(argv, *_):
            out = 'GitHub Copilot CLI 1.0.88.\n' if '--version' in argv else ' '.join(native_argv('copilot','copilot','gpt-5.4','low',120,50,None))+' --max-ai-credits --usage-output-file'
            return {'exit_code':0,'stdout':out}
        with patch.dict(os.environ, {'COPILOT_GITHUB_TOKEN':'test-token'}), patch('ceval.runner.execute', side_effect=fake_execute):
            result = doctor(s, True)['copilot']
        self.assertTrue(result['runtime_ok'])
        self.assertFalse(result['model_listing_supported'])
        self.assertEqual(result['models']['gpt-5.4']['account_access'], 'not_probed')
        # A missing required receipt flag fails before any paid task is dispatched.
        with patch.dict(os.environ, {'COPILOT_GITHUB_TOKEN':'test-token'}), patch('ceval.runner.execute', side_effect=lambda argv,*a: dict(fake_execute(argv), stdout=fake_execute(argv)['stdout'].replace('--usage-output-file',''))):
            self.assertFalse(doctor(s)['copilot']['runtime_ok'])
        s['execution']['copilot_account'] = 'wrong-account'
        with patch('ceval.runner.execute', side_effect=fake_execute), patch('ceval.runner.selected_account', side_effect=EvalError('Account mismatch')):
            result = doctor(s)['copilot']
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostic'], 'Account mismatch')

    def test_native_account_is_sealed_and_ignores_ambient_tokens(self):
        s = self.select()
        old_seal = load_suite(self.path)[4]
        s['execution']['copilot_account'] = 'personal-user'
        write_json(self.path, s)
        self.assertNotEqual(old_seal, load_suite(self.path)[4])
        account = {'host': 'https://github.com', 'login': 'personal-user'}
        saved = self.root / '.copilot'
        saved.mkdir()
        config = {'lastLoggedInUser': account, 'loggedInUsers': [account],
                  'hooks': {'should-not-copy': True}, 'secret': 'never-copy'}
        (saved/'config.json').write_text('// Native CLI config\n'+json.dumps(config))
        self.assertEqual(selected_account('personal-user', self.root), account)
        with self.assertRaises(EvalError):
            selected_account('other-user', self.root)
        binary = self.root / 'native-copilot'
        binary.write_text('#!'+sys.executable+'\n'+'''import json, os
from pathlib import Path
assert 'COPILOT_GITHUB_TOKEN' not in os.environ
assert 'GH_TOKEN' not in os.environ and 'GITHUB_TOKEN' not in os.environ
c = json.loads((Path(os.environ['COPILOT_HOME'])/'config.json').read_text())
assert os.environ['HOME'] != os.environ['COPILOT_HOME']
assert c['lastLoggedInUser']['login'] == 'personal-user'
assert len(c['loggedInUsers']) == 1
assert c['disableAllHooks'] is True
assert 'hooks' not in c and 'secret' not in c
print(json.dumps({'type':'result','exitCode':0,'usage':{'premiumRequests':1}}))
''')
        binary.chmod(0o700)
        s['execution']['copilot_bin'] = str(binary)
        task = next(t for t in load_suite(self.path)[2] if t['spec']['id'] == 'slug-normalization')
        cell = {'cell_id':'native', 'task_id':'slug-normalization', 'provider':'copilot',
                'model':'gpt-5.4', 'effort':'low', 'repeat':1}
        with patch('ceval.copilot_auth.Path.home', return_value=self.root), patch.dict(os.environ, {
                'COPILOT_GITHUB_TOKEN':'old-token', 'GH_TOKEN':'wrong-account', 'GITHUB_TOKEN':'wrong'}):
            row = attempt(cell, task, s, {}, self.root/'native-attempt', {'ok':True})
        self.assertEqual(row['exit_code'], 0)
        invocation = read_json(self.root/'native-attempt/invocation.json')
        self.assertIsNone(invocation['key_env'])
        self.assertEqual(invocation['copilot_account'], 'personal-user')

    def test_configure_account_token_switch_and_cli_pin(self):
        with patch('ceval.cli.selected_account') as account, patch('ceval.cli.cli_pin', return_value=('/opt/copilot', '1.0.88')):
            configure(self.path, ['copilot:gpt-6-astra'], efforts=['low'],
                      copilot_account='personal-user', copilot_binary='/opt/copilot', copilot_max_ai_credits=40)
            account.assert_called_once_with('personal-user')
        s = read_json(self.path)
        self.assertEqual(s['execution']['copilot_account'], 'personal-user')
        self.assertEqual(s['execution']['copilot_version'], '1.0.88')
        before = load_suite(self.path)[4]
        configure(self.path, copilot_token=True, copilot_no_credit_limit=True)
        s = read_json(self.path)
        self.assertNotIn('copilot_account', s['execution'])
        self.assertIsNone(s['limits']['copilot_max_ai_credits'])
        self.assertNotEqual(before, load_suite(self.path)[4])
        original = self.path.read_bytes()
        with self.assertRaises(EvalError):
            configure(self.path, copilot_max_ai_credits=1)
        self.assertEqual(original, self.path.read_bytes())
        with self.assertRaises(EvalError):
            configure(self.path, ['codex:gpt-6-astra'], copilot_token=True)
        self.assertEqual(original, self.path.read_bytes())

    def test_model_filter_and_smoke_native_auth_effort(self):
        self.assertTrue(all(m['provider'] == 'copilot' for m in models('copilot', False)['models']))
        args = parser().parse_args(['smoke', '--provider', 'copilot', '--output', 'unused',
                                   '--copilot-account', 'personal-user', '--effort', 'low'])
        self.assertEqual(args.copilot_account, 'personal-user')
        def fake_run(path, output):
            suite = read_json(path)
            self.assertEqual(suite['matrix'][0]['efforts'], ['low'])
            self.assertEqual(suite['execution']['copilot_account'], 'personal-user')
            self.assertIsNone(suite['limits']['copilot_max_ai_credits'])
            self.assertIsNone(suite['limits']['agent_seconds'])
            self.assertIsNone(suite['limits']['grader_seconds'])
            self.assertEqual(suite['execution']['copilot_version'], '1.0.88')
            write_json(output/'results.json', {'rows':[]})
            return {'state':'complete'}
        with patch.dict(os.environ, {}, clear=True), patch('ceval.cli.selected_account') as account, \
             patch('ceval.cli.cli_pin', return_value=('/opt/copilot', '1.0.88')), \
             patch('ceval.cli.run', side_effect=fake_run), patch('ceval.cli.report'):
            result = smoke('copilot', self.root/'smoke', 'gpt-6-astra', effort='low', copilot_account='personal-user')
        self.assertEqual(result['state'], 'complete')
        account.assert_called_once_with('personal-user')
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(EvalError, 'copilot-account'):
                smoke('copilot', self.root/'missing-token')

    def test_final_usage_receipt_no_double_counting_or_invoice_claim(self):
        row = normalize('copilot', json.dumps({'type':'result', 'exitCode':0}), 'gpt-6-astra', {})
        receipt = {'currentModel':'gpt-6-astra', 'totalNanoAiu':2000000000,
                   'modelMetrics':{'gpt-6-astra':{'totalNanoAiu':2000000000,
                       'usage':{'inputTokens':100, 'outputTokens':20, 'cacheReadTokens':70}}},
                   'agentMetrics':{'default':{'totalNanoAiu':2000000000}}}
        copilot_usage(row, receipt, 'gpt-6-astra')
        self.assertTrue(row['provider_success'])
        self.assertEqual(row['input_tokens'], 100)
        self.assertEqual(row['copilot_ai_credits'], 2)
        self.assertEqual(row['copilot_usage_value_usd'], .02)
        self.assertIsNone(row['cost_usd'])
        self.assertIsNone(row['reasoning_tokens'])
        receipt['currentModel'] = 'other'
        copilot_usage(row, receipt, 'gpt-6-astra')
        self.assertFalse(row['provider_success'])
        empty = normalize('copilot', '', 'gpt-6-astra', {})
        copilot_usage(empty, {'totalNanoAiu':True}, 'gpt-6-astra')
        self.assertNotIn('copilot_usage_value_usd', empty)
        self.assertFalse(empty['provider_success'])

    def test_cooldown_accepts_copilot_policy_error_does_not_retry(self):
        cooldown = Cooldown(self.root/'cooldown')
        self.assertEqual(cooldown.remaining('copilot'), 0)
        (self.root/'stderr.txt').write_text('Error: Access denied by policy settings')
        row = {'status':'provider_error', 'exit_code':1}
        self.assertIsNone(transient_reason(row, self.root))


if __name__ == '__main__':
    unittest.main()
