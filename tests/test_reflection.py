"""Failure review never rewrites results or clears unrelated user stops."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/codex-eval-plugin'))
from ceval.core import EvalError, digest, read_json, write_json
from ceval.reflection import reflect, clear_review_pause


class ReflectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'run'
        self.cells = [dict(cell_id=str(i), task_id='hard' if i < 3 else 'easy',
                           provider='codex', model='example', effort='high') for i in range(6)]
        self.rows = [dict(c, valid=True, completion=int(i != 0 and i != 1),
                          status='failed' if i < 2 else 'passed', cost_usd=None)
                     for i, c in enumerate(self.cells)]
        self.info = dict(schedule=self.cells, state='running', seal='seal-one',
                         completed_cells=6, active_cells=0, updated_at='2026-09-10T00:00:00Z')
        self.save()

    def save(self, root=None):
        root = root or self.root
        write_json(root / 'run.json', self.info)
        write_json(root / 'results.json', {'rows': self.rows})
        for row in self.rows:
            folder = root / 'attempts' / row['cell_id']
            write_json(folder / 'result.json', row)
            write_json(folder / 'result.sha256.json', {'sha256': digest(row)})

    def test_task_thresholds_lanes_and_read_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = reflect([self.root, self.root])
        self.assertEqual(len(result['runs']), 1)
        easy, hard = result['runs'][0]['tasks']
        self.assertFalse(easy['needs_review'])  # Missing cost alone is not a trigger.
        self.assertEqual(hard['signals'], ['frequent_task_failures'])
        self.assertEqual(hard['failure_rate'], 2 / 3)
        self.assertEqual(hard['lanes'][0]['statuses'], {'failed': 2, 'passed': 1})
        self.assertEqual(len(hard['evidence']), 2)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertFalse(reflect([self.root], minimum=4)['needs_review'])

    def test_infrastructure_is_separate_from_scorable_failures(self):
        self.rows[0].update(valid=False, status='provider_error')
        self.save()
        hard = reflect([self.root])['runs'][0]['tasks'][1]
        self.assertEqual(hard['scorable'], 2)
        self.assertEqual(hard['infrastructure_errors'], 1)
        self.assertEqual(hard['signals'], ['infrastructure_error'])

    def test_pause_preserves_user_stop_and_never_pauses_synthetic_or_stopped(self):
        stop = self.root / 'stop-requested.json'
        write_json(stop, {'reason': 'user_cancel'})
        self.assertEqual(reflect([self.root], pause_on_review=True)['runs'][0]['pause_request'], 'already_requested')
        self.assertEqual(read_json(stop), {'reason': 'user_cancel'})
        stop.unlink()
        self.info['simulation'] = True
        self.save()
        self.assertEqual(reflect([self.root], pause_on_review=True)['runs'][0]['pause_request'], 'synthetic_no_action')
        self.info.update(simulation=False, state='stopped')
        self.save()
        self.assertEqual(reflect([self.root], pause_on_review=True)['runs'][0]['pause_request'], 'run_not_active')
        self.assertFalse(stop.exists())

    def test_verified_pause_and_audited_clear_do_not_resume(self):
        result = reflect([self.root], pause_on_review=True)['runs'][0]
        self.assertEqual(result['pause_request'], 'requested')
        with self.assertRaises(EvalError):
            clear_review_pause(self.root, 'reviewer', 'Contract is valid')
        self.info.update(state='stopped', active_cells=0)
        self.save()
        before = (self.root / 'results.json').read_bytes()
        receipt = clear_review_pause(self.root, 'reviewer', 'Contract is valid; retain coding failures')
        self.assertFalse(receipt['resumed'])
        self.assertEqual(read_json(Path(receipt['receipt']))['pause_request']['task_ids'], ['hard'])
        self.assertFalse((self.root / 'stop-requested.json').exists())
        self.assertEqual(before, (self.root / 'results.json').read_bytes())
        self.assertEqual(read_json(self.root / 'run.json')['state'], 'stopped')

    def test_clear_refuses_live_lock_other_user_marker_and_wrong_seal(self):
        self.info['state'] = 'stopped'
        self.save()
        lock = self.root / '.run-lock'
        lock.mkdir()
        with self.assertRaises(EvalError):
            clear_review_pause(self.root, 'reviewer', 'done')
        self.assertTrue(lock.exists())
        lock.rmdir()
        for marker in ({'reason': 'user_cancel'},
                       {'reason': 'task_quality_review', 'requested_by': 'codex-eval reflect --pause-on-review', 'seal': 'other'}):
            write_json(self.root / 'stop-requested.json', marker)
            with self.assertRaises(EvalError):
                clear_review_pause(self.root, 'reviewer', 'done')
            self.assertEqual(read_json(self.root / 'stop-requested.json'), marker)
            self.assertFalse(lock.exists())

    def test_all_inputs_verified_before_pause_and_original_result_tamper_rejected(self):
        other = self.root.parent / 'other'
        self.save(other)
        write_json(other / 'attempts/0/result.json', {'completion': 1})
        with self.assertRaises(EvalError):
            reflect([self.root, other], pause_on_review=True)
        self.assertFalse((self.root / 'stop-requested.json').exists())

    def test_missing_and_racing_checkpoints_do_not_trigger(self):
        self.assertFalse(reflect([self.root.parent / 'missing'])['needs_review'])
        self.info['completed_cells'] = 5
        self.save()
        result = reflect([self.root], pause_on_review=True)['runs'][0]
        self.assertEqual(result['review_state'], 'awaiting_checkpoint')
        self.assertFalse((self.root / 'stop-requested.json').exists())
        self.info['completed_cells'] = 6
        self.save()
        from ceval.progress import progress
        snapshot = progress([self.root])
        snapshot['runs'][0]['checkpoint_at'] = 'old'
        with patch('ceval.reflection.progress', return_value=snapshot):
            self.assertEqual(reflect([self.root])['runs'][0]['review_state'], 'awaiting_checkpoint')

    def test_invalid_thresholds(self):
        for args in ({'minimum': 0}, {'minimum': True}, {'failure_rate': 0},
                     {'failure_rate': 1.1}, {'failure_rate': float('nan')}):
            with self.assertRaises(EvalError):
                reflect([self.root], **args)


if __name__ == '__main__':
    unittest.main()
