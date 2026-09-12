"""Customer-facing readiness gates, shared recovery and honest discovery coverage."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_evaluation import Workspace
from ceval.core import digest, load_suite, read_json, write_json
from ceval.discovery import discovery_report, history
from ceval.execution_check import check, probe_task, shell_check_ran
from ceval.parallel import Slots, run
from ceval.rate_limits import Cooldown, transient_reason


class ReadinessTests(Workspace):
    def test_text_diagnostics_do_not_hide_successful_shell_evidence(self):
        events = [{'type':'error','message':'transient provider notice'},
                  {'type':'item.completed','item':'unexpected text'},
                  {'type':'assistant','message':{'content':[{'type':'tool_use','name':'Bash','input':'unexpected text'}]}}]
        log = self.root / 'events.jsonl'
        log.write_text('\n'.join(json.dumps(e) for e in events))
        self.assertFalse(shell_check_ran({}, self.root))
        events.append({'type':'item.completed','item':{'type':'command_execution','command':'python3 check.py','exit_code':1}})
        log.write_text('\n'.join(json.dumps(e) for e in events))
        self.assertFalse(shell_check_ran({}, self.root))
        events[-1]['item']['exit_code'] = 0
        log.write_text('\n'.join(json.dumps(e) for e in events))
        self.assertTrue(shell_check_ran({}, self.root))

    def test_real_native_probe_requires_edit_test_and_no_helper_failure(self):
        binary = self.root / 'native'
        binary.write_text('#!' + sys.executable + '\n' + '''import json, subprocess, sys
from pathlib import Path
sys.stdin.read()
mode=sys.argv[sys.argv.index('--model')+1]
if mode != 'no-edit':
    Path('value.txt').write_text('2\\n')
    subprocess.run([sys.executable, 'check.py'], check=True)
if mode == 'helper-error':
    print('fs sandbox helper failed with status exit status: 101', file=sys.stderr)
print(json.dumps({'type':'item.completed','item':{'type':'command_execution','command':'python check.py','exit_code':0}}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':0,'cache_write_input_tokens':0,'output_tokens':1}}))
''')
        binary.chmod(0o700)
        self.s['execution']['codex_bin'] = str(binary)
        for model, expected in [('ok',True),('no-edit',False),('helper-error',False)]:
            output=self.root/model;output.mkdir()
            self.s['matrix'][0]['model']=model
            with patch.dict(os.environ, {'OPENAI_API_KEY':'offline-test-key'}):
                receipt=check(self.s,{},output,{'codex':{'ok':True}},Slots(None,1),Cooldown(output/'cooldown'),0,0)
            self.assertEqual(receipt['ok'],expected)
            self.assertEqual(len(receipt['rows']),1)
            self.assertEqual(len(list((output/'execution-checks').glob('receipt-*.json'))),1)
            if model=='helper-error':
                self.assertEqual(receipt['rows'][0]['completion'],1)
                self.assertTrue(receipt['rows'][0]['runtime_diagnostics'])

    def prepare_customer(self):
        self.s['purpose']='customer'
        self.s['workflows']=[{'id':'workflow','name':'Workflow','description':'Synthetic workflow'}]
        for path in (self.suite_dir/'tasks').glob('*/task.json'):
            task=read_json(path);task['workflow_id']='workflow';write_json(path,task)
        self.save()
        write_json(self.suite_dir/'approval.json',{'seal':load_suite(self.path)[4]})

    def test_customer_gate_blocks_matrix(self):
        self.prepare_customer()
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.parallel.execution_check.check', return_value={'ok':False,'rows':[]}) as gate, patch('ceval.runner.attempt') as native, contextlib.redirect_stdout(io.StringIO()):
            result=run(self.path,self.root/'run')
        self.assertEqual(result['stop_reason'],'execution_check_failed')
        self.assertEqual(result['completed_cells'],0)
        native.assert_not_called();gate.assert_called_once()

    def test_shared_cooldown_is_provider_scoped_extends_and_can_pause(self):
        a=Cooldown(self.root/'pool');b=Cooldown(self.root/'pool')
        with patch('ceval.rate_limits.time.time',return_value=100):
            a.defer('codex',30)
            self.assertEqual(b.remaining('codex'),30)
            self.assertEqual(b.remaining('claude'),0)
            b.defer('codex',10)
            self.assertEqual(a.remaining('codex'),30)
            b.defer('codex',60)
            self.assertEqual(a.remaining('codex'),60)
            stop=self.root/'stop';stop.touch()
            _,paused=a.wait('codex',stop)
            self.assertTrue(paused)
        with patch('ceval.rate_limits.time.time',return_value=161):
            self.assertEqual(a.remaining('codex'),0)

    def test_capacity_classifier_ignores_candidate_text_auth_and_recovery(self):
        path=self.root/'events.jsonl';row={'status':'provider_error'}
        for message in ['Selected model is at capacity. Please try a different model.', 'overloaded_error: overloaded']:
            path.write_text(json.dumps({'type':'turn.failed','error':{'message':message}}))
            self.assertEqual(transient_reason(row,self.root),'capacity')
            self.assertIsNone(transient_reason({'status':'failed'},self.root))
        for e in [{'type':'item.completed','item':{'text':'Selected model is at capacity'}},
                  {'type':'error','message':'authentication_error; server is at capacity'}]:
            path.write_text(json.dumps(e));self.assertIsNone(transient_reason(row,self.root))
        path.write_text(json.dumps({'type':'error','message':'Selected model is at capacity'})+'\n'+json.dumps({'type':'turn.completed'}))
        self.assertIsNone(transient_reason(row,self.root))

    def test_export_coverage_receipt_never_claims_full_lookback(self):
        root=self.root/'export';root.mkdir()
        (root/'selected.jsonl').write_text(json.dumps({'type':'response_item','timestamp':'2026-09-10T00:00:00Z','payload':{'role':'user','content':[{'type':'input_text','text':'Fix reporting'}]}})+'\n')
        from datetime import datetime,timezone
        with patch('ceval.discovery.datetime') as clock:
            clock.now.return_value=datetime(2026,9,12,tzinfo=timezone.utc)
            clock.fromisoformat.side_effect=datetime.fromisoformat
            history('codex',root,90,True,self.root/'history.json','export')
        discovery=self.root/'discovery.json'
        write_json(discovery,{'source_choices':['history'],'workflows':[{'id':'reports','name':'Reporting','description':'Reporting logic'}]})
        receipt=discovery_report(discovery,[self.root/'history.json'],self.root/'coverage.json')
        self.assertFalse(receipt['workload_coverage_complete'])
        self.assertEqual(receipt['sources'][0]['retained_messages'],1)
        self.assertEqual(receipt['sources'][0]['source_kind'],'export')
        self.assertNotEqual(receipt['sources'][0]['requested_start'],receipt['sources'][0]['observed_start'])
        self.assertIsNone(receipt['workflows'][0]['customer_confirmation'])
        self.assertNotIn('Fix reporting',(self.root/'coverage.md').read_text())
        interview=discovery_report(discovery,[],self.root/'interview.json')
        self.assertFalse(interview['workload_coverage_complete'])
        self.assertIn('self-reported',(self.root/'interview.md').read_text())

    def test_successful_gate_costs_are_separate_and_completed_resume_is_free(self):
        self.prepare_customer()
        receipt={'ok':True,'state':'passed','rows':[{'cost_usd':.1,'cost_upper_usd':.1}]}
        def result(cell,*args):
            return {**cell,'status':'passed','completion':1,'valid':True,'simulation':False,'cost_usd':.2,'cost_upper_usd':.2}
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.parallel.execution_check.check',return_value=receipt) as gate, patch('ceval.runner.attempt',side_effect=result) as native, contextlib.redirect_stdout(io.StringIO()):
            info=run(self.path,self.root/'run')
            run(self.path,self.root/'run',resume=True)
        gate.assert_called_once()
        self.assertEqual(native.call_count,3)
        self.assertEqual(info['execution_check_cost']['known_cost_usd'],.1)
        self.assertEqual(len(read_json(self.root/'run/results.json')['rows']),3)

    def test_probe_cost_blocks_dispatch_at_spend_limit(self):
        self.s['limits']['spend_stop_usd']=.1
        self.prepare_customer()
        receipt={'ok':True,'state':'passed','rows':[{'cell_id':'check','cost_usd':.1,'cost_upper_usd':.1}]}
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.parallel.execution_check.check',return_value=receipt), patch('ceval.runner.attempt') as native, contextlib.redirect_stdout(io.StringIO()):
            info=run(self.path,self.root/'run')
        self.assertEqual(info['stop_reason'],'spend_threshold')
        native.assert_not_called()

    def test_interrupted_probe_is_not_silently_repeated(self):
        self.prepare_customer()
        output=self.root/'run';output.mkdir()
        write_json(output/'run.json',{'seal':load_suite(self.path)[4]})
        write_json(output/'execution-checks/receipt-0001.json',{'ok':False,'state':'started','rows':[]})
        with patch('ceval.runner.preflight',return_value={'codex':{'ok':True}}), patch('ceval.parallel.execution_check.check') as gate, patch('ceval.runner.attempt') as native, contextlib.redirect_stdout(io.StringIO()):
            info=run(self.path,output,resume=True)
        self.assertEqual(info['stop_reason'],'execution_check_interrupted')
        native.assert_not_called();gate.assert_not_called()
