import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/codex-eval-plugin'))

from ceval.core import digest, write_json, read_json
from ceval.rate_limits import rollup
from ceval.report import dataset, report


class ComparisonRateLimitTests(unittest.TestCase):
    def fixture(self, root, provider, trials):
        cell = {'cell_id': 'one', 'task_id': 'task', 'provider': provider,
                'model': 'model', 'effort': 'medium', 'repeat': 0}
        folder = root / 'attempts/one'
        records = []
        for i, extra in enumerate(trials):
            row = {**cell, 'status': 'passed', 'valid': True, 'completion': 1,
                   'cost_usd': .25, 'cost_lower_usd': .25, 'cost_upper_usd': .25,
                   'input_tokens': 100, 'output_tokens': 20, 'cache_read_tokens': 0,
                   'cache_write_tokens': 0, 'latency_seconds': 5, **extra}
            p = folder / 'retries' / f'{i:03d}'
            write_json(p / 'result.json', row)
            write_json(p / 'result.sha256.json', {'sha256': digest(row)})
            records.append((row, p))
        aggregate = rollup(records, folder, 30)
        write_json(folder / 'result.json', aggregate)
        write_json(folder / 'result.sha256.json', {'sha256': digest(aggregate)})
        write_json(root / 'results.json', {'rows': [aggregate]})
        write_json(root / 'run.json', {'suite': {'name': 'test', 'repeats': 1},
                                      'schedule': [cell], 'task_summaries': []})
        return aggregate

    def rate(self):
        return {'status': 'provider_error', 'valid': False, 'completion': 0,
                'rate_limited': True, 'transient_reason': 'rate_limit',
                'cost_usd': None, 'cost_upper_usd': None, 'input_tokens': None}

    def test_both_providers_use_measured_retry_and_preserve_accounting(self):
        for provider in ('codex', 'claude'):
            for outcome in ('passed', 'failed'):
                with self.subTest(provider=provider, outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    original = self.fixture(root, provider, [self.rate(), {'status': outcome, 'completion': int(outcome == 'passed')}])
                    before = (root / 'results.json').read_bytes()
                    d = dataset(root, comparison=True)
                    r = d['rows'][0]
                    self.assertEqual(r['status'], outcome)
                    self.assertEqual(r['cost_usd'], .25)
                    self.assertEqual(r['input_tokens'], 100)
                    self.assertEqual(r['latency_seconds'], 5)
                    self.assertEqual(r['excluded_rate_limit_attempts'], 1)
                    self.assertIsNone(d['accounting_rows'][0]['cost_usd'])
                    self.assertEqual(d['accounting_rows'][0]['latency_seconds'], 40)
                    self.assertEqual(dataset(root)['rows'][0], original)
                    summary = report(root)
                    self.assertEqual(summary['accounting']['groups'][0]['known_cost_usd'], .25)
                    self.assertEqual(summary['groups'][0]['cost_missing'], 0)
                    self.assertTrue((root / 'accounting.csv').exists())
                    self.assertEqual(len(read_json(root / 'rate-limit-exclusions.json')), 1)
                    self.assertEqual((root / 'results.json').read_bytes(), before)

    def test_rate_limit_only_is_unmeasured_and_preserves_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, 'claude', [self.rate(), self.rate()])
            d = dataset(root, comparison=True)
            self.assertEqual(d['rows'], [])
            self.assertEqual(d['averages'], [])
            self.assertEqual(d['summary']['scheduled'], 1)
            self.assertEqual(d['summary']['rate_limit_only_cells'], 1)
            self.assertEqual(len(d['rate_limit_exclusions']), 2)
            self.assertEqual(len(d['accounting_rows']), 1)

    def test_other_errors_and_native_recovery_are_not_removed(self):
        for extra in ({'status': 'provider_error', 'transient_reason': 'capacity', 'completion': 0},
                      {'status': 'provider_error', 'completion': 0},
                      {'status': 'failed', 'completion': 0, 'rate_limited': True},
                      {'status': 'passed', 'completion': 1, 'rate_limited': True}):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                original = self.fixture(root, 'codex', [extra])
                d = dataset(root, comparison=True)
                self.assertEqual(d['rows'], [original])
                self.assertEqual(d['rate_limit_exclusions'], [])

    def test_mixed_waits_remain_unknown_and_missing_non_rate_cost_stays_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capacity = {'status': 'provider_error', 'transient_reason': 'capacity',
                        'completion': 0, 'valid': False, 'cost_usd': None}
            self.fixture(root, 'codex', [self.rate(), capacity, {}])
            r = dataset(root, comparison=True)['rows'][0]
            self.assertIsNone(r['latency_seconds'])
            self.assertIsNone(r['cost_usd'])
            self.assertEqual(r['excluded_rate_limit_attempts'], 1)
