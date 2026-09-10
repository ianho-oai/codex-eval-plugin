import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'plugins/codex-eval-plugin'))
from ceval.cli import doctor
from ceval.core import EvalError, digest, write_json
from ceval.report import reset_version_errors, exclude_models


class RecoveryTests(unittest.TestCase):
    def test_reset_preserves_originals_and_rejects_task_failures_or_changed_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            row = {'cell_id':'one','provider':'claude','model':'claude-fable-5-1',
                   'status':'provider_error','completion':0,'valid':False}
            run = {'schedule':[{'cell_id':'one'},{'cell_id':'two'}]}
            before = copy.deepcopy((run, row))
            folder = root/'attempts/one';folder.mkdir(parents=True)
            event = {'type':'result','is_error':True,'result':'API Error: 400 Claude Code 2.1.220 does not support this model; version 2.1.251 or newer is required.'}
            events = (json.dumps(event)+'\n').encode()
            (folder/'events.jsonl').write_bytes(events)
            entry = {'cell_id':'one','result_sha256':digest(row), 'events_path':'events.jsonl',
                     'events_sha256':hashlib.sha256(events).hexdigest()}
            receipt = {'requested_by':'Customer','reason':'cli_version_incompatible','attempts':[entry]}
            write_json(root/'reset-version-errors.json',receipt)
            view, rows, archived = reset_version_errors(root,run,[row])
            self.assertEqual(rows,[])
            self.assertEqual(view['schedule'],[{'cell_id':'two'}])
            self.assertEqual(archived[0]['completion'],0)
            self.assertEqual((run,row),before)
            (folder/'events.jsonl').write_bytes(events+b' ')
            with self.assertRaises(EvalError):reset_version_errors(root,run,[row])
            (folder/'events.jsonl').write_bytes(events)
            row['status']='failed';row['valid']=True
            receipt['attempts'][0]['result_sha256']=digest(row)
            write_json(root/'reset-version-errors.json',receipt)
            with self.assertRaises(EvalError):reset_version_errors(root,run,[row])

    def test_model_exclusion_removes_pending_cells_and_preserves_other_models(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fable={'cell_id':'a','provider':'claude','model':'claude-fable-5-1','completion':1}
            mythos={'cell_id':'b','provider':'claude','model':'claude-mythos-5-1','completion':0}
            run={'schedule':[fable,mythos,dict(mythos,cell_id='pending')]}
            write_json(root/'excluded-models.json',{'requested_by':'Customer','reason':'Remove Mythos',
                        'models':[{'provider':'claude','model':'claude-mythos-5-1'}]})
            view, rows, excluded=exclude_models(root,run,[fable,mythos])
            self.assertEqual(rows,[fable]);self.assertEqual(view['schedule'],[fable])
            self.assertEqual(excluded[0]['cell_id'],'b')
            self.assertEqual(len(run['schedule']),3)

    def test_doctor_lists_each_provider_and_does_not_claim_inference_support(self):
        suite={'matrix':[{'provider':'codex'},{'provider':'claude'}]}
        pf={p:{'ok':True,'models':{m:{'ok':True,'account_access':'not_probed'}}}
            for p,m in [('codex','gpt-test'),('claude','claude-test')]}
        def listing(provider,refresh):
            self.assertTrue(refresh)
            return {'checked_at':'now','models':['gpt-test'] if provider=='codex' else []}
        with patch('ceval.cli.preflight',return_value=pf),patch('ceval.cli.models',side_effect=listing) as mocked:
            result=doctor(suite,True)
        self.assertEqual(mocked.call_count,2)
        self.assertTrue(result['codex']['ok']);self.assertFalse(result['claude']['ok'])
        self.assertEqual(result['codex']['models']['gpt-test']['account_access'],'listed')
        self.assertEqual(result['claude']['models']['claude-test']['account_access'],'not_listed')

    def test_blocked_listing_remains_unprobed_and_fails_doctor(self):
        pf={'claude':{'ok':True,'models':{'test':{'account_access':'not_probed'}}}}
        with patch('ceval.cli.preflight',return_value=pf),patch('ceval.cli.models',side_effect=EvalError('Model listing unavailable')):
            result=doctor({'matrix':[{'provider':'claude'}]},True)
        self.assertFalse(result['claude']['ok'])
        self.assertEqual(result['claude']['models']['test']['account_access'],'not_probed')
        self.assertIn('unavailable',result['claude']['model_listing_error'])
