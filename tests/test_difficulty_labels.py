import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/codex-eval-plugin'))

from ceval.core import EvalError, digest, read_json, write_json
from ceval.report import dataset, dashboard_dataset, report


class DifficultyLabelTests(unittest.TestCase):
    def fixture(self, root):
        rows = []
        for task, completion in [('deep-task', 0), ('other-task', 1)]:
            row = {'cell_id': task, 'task_id': task, 'difficulty': 'hard',
                   'provider': 'claude', 'model': 'fixture-model', 'effort': 'high',
                   'repeat': 1, 'completion': completion, 'valid': True,
                   'status': 'passed' if completion else 'failed',
                   'cost_usd': .25, 'latency_seconds': 12}
            folder = root / 'attempts' / task
            write_json(folder / 'result.json', row)
            write_json(folder / 'result.sha256.json', {'sha256': digest(row)})
            rows.append(row)
        write_json(root / 'results.json', {'rows': rows})
        write_json(root / 'run.json', {'seal': 'fixture-seal', 'suite': {'name': 'fixture'},
                                      'schedule': rows, 'task_summaries': rows})
        return {'schema_version': 1, 'run_seal': 'fixture-seal',
                'requested_by': 'Fixture reviewer', 'reason': 'Separate harder tasks',
                'tasks': [{'task_id': 'deep-task', 'from': 'hard', 'to': 'harder'}]}

    def test_labels_reach_views_and_exports_without_changing_evidence_or_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'run'
            receipt = self.fixture(root)
            before = dataset(root, comparison=True)
            evidence = {p: p.read_bytes() for p in root.rglob('*.json')}
            write_json(root / 'difficulty-labels.json', receipt)
            after = dataset(root, comparison=True)
            for key in ('rows', 'tasks', 'averages', 'accounting_rows'):
                for old, new in zip(before[key], after[key]):
                    expected = dict(old)
                    if old['task_id'] == 'deep-task':
                        expected.update(difficulty='harder', recorded_difficulty='hard')
                    self.assertEqual(new, expected)
            self.assertEqual(after['summary'], before['summary'])
            self.assertEqual(after['run'], before['run'])
            report(root)
            for name in ('results.csv', 'accounting.csv'):
                rows = list(csv.DictReader(io.StringIO((root / name).read_text())))
                self.assertEqual(rows[0]['difficulty'], 'harder')
                self.assertEqual(rows[0]['recorded_difficulty'], 'hard')
            for path, original in evidence.items():
                self.assertEqual(path.read_bytes(), original)
            (root / 'difficulty-labels.json').unlink()
            self.assertEqual(dataset(root, comparison=True), before)

    def test_receipt_is_scoped_to_one_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / 'first', Path(tmp) / 'second'
            receipt = self.fixture(first)
            self.fixture(second)
            write_json(first / 'difficulty-labels.json', receipt)
            combined = dashboard_dataset([first, second], scope=True)
            rows = [r for r in combined['rows'] if r['task_id'] == 'deep-task']
            self.assertEqual([r['difficulty'] for r in rows], ['harder', 'hard'])

    def test_stale_unknown_duplicate_or_invalid_labels_are_rejected(self):
        variants = [
            {'run_seal': 'different-seal'},
            {'tasks': [{'task_id': 'missing', 'from': 'hard', 'to': 'harder'}]},
            {'tasks': [{'task_id': 'deep-task', 'from': 'easy', 'to': 'harder'}]},
            {'tasks': [{'task_id': 'deep-task', 'from': 'hard', 'to': 'invalid'}]},
            {'tasks': [{'task_id': 'deep-task', 'from': 'hard', 'to': 'harder'}] * 2},
        ]
        for changes in variants:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                receipt = self.fixture(root)
                write_json(root / 'difficulty-labels.json', {**receipt, **changes})
                with self.assertRaises(EvalError):
                    dataset(root)

    def test_labels_do_not_bypass_original_integrity_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = self.fixture(root)
            write_json(root / 'difficulty-labels.json', receipt)
            path = root / 'attempts/deep-task/result.json'
            write_json(path, {**read_json(path), 'completion': 1})
            with self.assertRaisesRegex(EvalError, 'Result integrity check failed'):
                dataset(root)
