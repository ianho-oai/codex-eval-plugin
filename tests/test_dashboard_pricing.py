import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'plugins/codex-eval-plugin'))
from ceval.cli import demo
from ceval.core import DATA, EvalError, digest, read_json, write_json
from ceval.report import dashboard_dataset, dataset, csv_text
from ceval.telemetry import codex_cost


class DashboardPricingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.card = self.root/'rates.json'
        self.rates = read_json(DATA/'rates.json')
        write_json(self.card, self.rates)

    def make_run(self, name):
        root = self.root/name
        demo(root)
        run = read_json(root/'run.json')
        run['simulation'] = False
        write_json(root/'run.json', run)
        rows = read_json(root/'results.json')['rows']
        for index, row in enumerate(rows):
            row['simulation'] = False
            if row['provider'] == 'codex':
                row.update(model='gpt-5.6-sol', input_tokens=1000, cache_read_tokens=700,
                           cache_write_tokens=250, output_tokens=200, cost_usd=99)
            elif index == 1:
                row.update(provider='copilot', cost_usd=None, copilot_usage_value_usd=.25)
            folder = root/'attempts'/row['cell_id']
            write_json(folder/'result.json', row)
            write_json(folder/'result.sha256.json', {'sha256': digest(row)})
        write_json(root/'results.json', {'rows': rows})
        return root

    def test_rate_edit_reprices_single_and_combined_views_without_changing_evidence(self):
        one, two = self.make_run('one'), self.make_run('two')
        before = {p: p.read_bytes() for root in (one, two) for p in root.rglob('*.json')}
        frozen = dataset(one, comparison=True)
        # Exercise the default repo-card lookup, including hot reload between calls.
        with patch('ceval.report.DATA', self.root):
            first = dashboard_dataset(one, scope=True)
            self.rates['models']['gpt-5.6-sol']['output'] *= 2
            write_json(self.card, self.rates)
            second = dashboard_dataset(one, scope=True)
            combined = dashboard_dataset([one, two], scope=True)
        for rows, expected in [(first['rows'], .00573), (second['rows'], .00973), (combined['rows'], .00973)]:
            for row in rows:
                if row['provider'] == 'codex':
                    self.assertAlmostEqual(row['cost_usd'], expected)
                    self.assertEqual(row['recorded_cost_usd'], 99)
                    self.assertEqual(row['cost_source'], 'dashboard_rate_card_estimate')
        for point in second['averages']:
            if point['provider'] == 'codex':
                self.assertAlmostEqual(point['cost_usd'], .00973)
        self.assertNotEqual(first['dashboard_pricing']['sha256'], second['dashboard_pricing']['sha256'])
        self.assertEqual(second['accounting_summary'], frozen['accounting_summary'])
        self.assertEqual(second['accounting_rows'], frozen['accounting_rows'])
        self.assertEqual([r for r in second['rows'] if r['provider'] != 'codex'],
                         [r for r in frozen['rows'] if r['provider'] != 'codex'])
        self.assertIn('dashboard_rate_card_estimate', csv_text(second['rows']))
        self.assertIn('pricing_sha256', csv_text(second['rows']))
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_missing_model_rate_never_falls_back_to_frozen_cost(self):
        root = self.make_run('run')
        del self.rates['models']['gpt-5.6-sol']
        write_json(self.card, self.rates)
        view = dashboard_dataset(root, pricing_path=self.card)
        for row in view['rows']:
            if row['provider'] == 'codex':
                self.assertIsNone(row['cost_usd'])
                self.assertEqual(row['recorded_cost_usd'], 99)
        self.card.write_text('{broken')
        with self.assertRaises(EvalError):
            dashboard_dataset(root, pricing_path=self.card)

    def test_token_accounting_missing_zero_and_invalid_usage(self):
        rate = self.rates['models']['gpt-5.6-sol']
        usage = dict(input_tokens=1000, cache_read_tokens=700, cache_write_tokens=250,
                     output_tokens=200, reasoning_tokens=150)
        self.assertAlmostEqual(codex_cost(usage, rate)['cost_usd'], .00573)
        # Reasoning is already in output; uncached input excludes reads and writes.
        self.assertEqual(codex_cost(usage, rate), codex_cost(dict(usage, reasoning_tokens=999), rate))
        for field in ('input_tokens', 'output_tokens', 'cache_read_tokens'):
            for value in (None, -1, True, float('nan')):
                self.assertIsNone(codex_cost(dict(usage, **{field: value}), rate)['cost_usd'])
        self.assertIsNone(codex_cost(dict(usage, cache_write_tokens=301), rate)['cost_usd'])
        self.assertIsNone(codex_cost(usage, dict(rate, input=-1))['cost_usd'])
        self.assertAlmostEqual(codex_cost(dict(usage, cache_write_tokens=None), rate)['cost_usd'], .00548)
        self.assertEqual(codex_cost(dict.fromkeys(usage, 0), rate)['cost_usd'], 0)


if __name__ == '__main__':
    unittest.main()
