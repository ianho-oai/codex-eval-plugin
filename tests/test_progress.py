"""Progress reads checkpoints without advancing execution or hiding failures."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/codex-eval-plugin'))
from ceval.core import EvalError, digest, read_json, write_json
from ceval.progress import progress


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'run'
        self.cells = [{'cell_id': str(i), 'provider': 'codex', 'model': 'example'} for i in range(5)]
        self.info = {'suite': {'name': 'Example'}, 'schedule': self.cells,
                     'state': 'running', 'completed_cells': 3, 'active_cells': 1,
                     'updated_at': '2026-09-10T00:00:00Z'}
        self.rows = [dict(self.cells[0], completion=1, valid=True),
                     dict(self.cells[1], completion=0, valid=True),
                     dict(self.cells[2], completion=0, valid=False)]

    def save(self):
        write_json(self.root / 'run.json', self.info)
        write_json(self.root / 'results.json', {'rows': self.rows})
        for row in self.rows:
            write_json(self.root / 'attempts' / row['cell_id'] / 'result.sha256.json', {'sha256': digest(row)})

    def test_mixed_outcomes_pending_includes_active_and_no_mutation(self):
        self.save()
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = progress([self.root, self.root])['runs']
        self.assertEqual(len(result), 1)
        row = result[0]
        self.assertEqual([row[k] for k in ('scheduled', 'finished', 'remaining', 'active_at_checkpoint', 'passed', 'failed', 'errors')], [5, 3, 2, 1, 1, 1, 1])
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, before)

    def test_missing_and_paused_runs_are_not_reported_complete(self):
        missing = progress([self.root])['runs'][0]
        self.assertEqual(missing['recorded_state'], 'awaiting_start')
        self.assertIsNone(missing['scheduled'])
        self.info.update(state='stopped', stop_reason='paused', active_cells=0)
        self.save()
        paused = progress([self.root])['runs'][0]
        self.assertEqual(paused['recorded_state'], 'stopped')
        self.assertEqual(paused['remaining'], 2)
        self.assertEqual(paused['stop_reason'], 'paused')

    def test_checkpoint_race_does_not_invent_outcomes(self):
        self.info['completed_cells'] = 2
        self.save()
        result = progress([self.root])['runs'][0]
        self.assertEqual(result['finished'], 2)
        self.assertFalse(result['outcomes_available'])
        self.assertIsNone(result['passed'])

    def test_modified_outcome_is_rejected(self):
        self.save()
        data = read_json(self.root / 'results.json')
        data['rows'][0]['completion'] = 0
        write_json(self.root / 'results.json', data)
        with self.assertRaises(EvalError):
            progress([self.root])
