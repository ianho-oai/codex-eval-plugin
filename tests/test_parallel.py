"""Behavior checks for slot refill, shared limits, recovery, and spend stops."""
import contextlib
import io
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/codex-eval-plugin'))
from test_evaluation import Workspace
from ceval.core import write_json, load_suite, read_json, EvalError
from ceval.parallel import run, Slots


class ParallelTests(Workspace):
    def prepare(self, repeats=3):
        self.s['repeats'] = repeats
        self.save()
        write_json(self.suite_dir / 'approval.json', {'seal': load_suite(self.path)[4]})

    def row(self, cell, cost=0.01):
        return {**cell, 'status': 'passed', 'completion': 1, 'valid': True,
                'simulation': False, 'cost_upper_usd': cost, 'cost_usd': cost}

    def test_five_slots_refill_before_slowest_finishes_and_resume_skips(self):
        self.prepare()
        guard = threading.Lock()
        sixth = threading.Event()
        active = peak = started = 0
        def attempt(cell, *args):
            nonlocal active, peak, started
            with guard:
                started += 1; index = started; active += 1; peak = max(peak, active)
                if index == 6: sixth.set()
            if index == 1:
                self.assertTrue(sixth.wait(5), 'Queue waited for the whole first wave')
            else:
                time.sleep(0.12)
            with guard: active -= 1
            return self.row(cell)
        output = self.root / 'run'
        with patch('ceval.runner.preflight', return_value={'codex': {'ok': True}}), patch('ceval.runner.attempt', side_effect=attempt) as mocked, contextlib.redirect_stdout(io.StringIO()):
            info = run(self.path, output, workers=5)
            self.assertEqual(info['state'], 'complete')
            self.assertEqual(peak, 5)
            self.assertEqual(mocked.call_count, 9)
            run(self.path, output, resume=True, workers=5)
            self.assertEqual(mocked.call_count, 9)
        self.assertEqual(len(read_json(output / 'results.json')['rows']), 9)

    def test_unknown_spend_stops_refill_and_drains_active(self):
        self.s['limits']['spend_stop_usd'] = 20
        self.prepare()
        two_started = threading.Event()
        guard = threading.Lock()
        count = 0
        def attempt(cell, *args):
            nonlocal count
            with guard:
                count += 1; index = count
                if count == 2: two_started.set()
            self.assertTrue(two_started.wait(5))
            if index == 2: time.sleep(0.15)
            return self.row(cell, None if index == 1 else 0.01)
        with patch('ceval.runner.preflight', return_value={'codex': {'ok': True}}), patch('ceval.runner.attempt', side_effect=attempt), contextlib.redirect_stdout(io.StringIO()):
            info = run(self.path, self.root / 'run', workers=2)
        self.assertEqual(count, 2)
        self.assertEqual(info['stop_reason'], 'unknown_spend')
        self.assertEqual(info['completed_cells'], 2)
        self.assertEqual(info['active_cells'], 0)

    def test_no_spend_stop_finishes_with_high_and_unknown_costs(self):
        self.prepare(repeats=2)
        costs = iter([None, 500, None, 500, 500, None])
        def attempt(cell, *args):
            return self.row(cell, next(costs))
        with patch('ceval.runner.preflight', return_value={'codex': {'ok': True}}), patch('ceval.runner.attempt', side_effect=attempt), contextlib.redirect_stdout(io.StringIO()):
            info = run(self.path, self.root / 'unlimited', workers=1)
        self.assertEqual(info['state'], 'complete')
        self.assertEqual(info['completed_cells'], 6)
        rows = read_json(self.root / 'unlimited/results.json')['rows']
        self.assertEqual(sum(r['cost_usd'] is None for r in rows), 3)

    def test_pool_shared_between_dispatchers_and_releases_slots(self):
        first = Slots(self.root / 'pool', 5)
        second = Slots(self.root / 'pool', 5)
        leases = [first.acquire() for _ in range(5)]
        try:
            self.assertIsNone(second.acquire())
            first.release(leases.pop())
            borrowed = second.acquire()
            self.assertIsNotNone(borrowed)
            second.release(borrowed)
            with self.assertRaises(EvalError): Slots(self.root / 'pool', 3)
        finally:
            for lease in leases: first.release(lease)

    def test_pause_drains_without_starting_more_and_resume_keeps_evidence(self):
        self.prepare()
        output = self.root / 'run'
        def attempt(cell, *args):
            write_json(output / 'stop-requested.json', {'reason': 'pause'})
            return self.row(cell)
        with patch('ceval.runner.preflight', return_value={'codex': {'ok': True}}), patch('ceval.runner.attempt', side_effect=attempt), contextlib.redirect_stdout(io.StringIO()):
            info = run(self.path, output, workers=1)
        self.assertEqual(info['stop_reason'], 'paused')
        self.assertEqual(info['completed_cells'], 1)
        self.assertFalse((output / '.run-lock').exists())

    def test_bad_worker_count_launches_nothing(self):
        self.prepare()
        for value in [0, -1, 33, True]:
            with self.assertRaises(EvalError): run(self.path, self.root / 'run', workers=value)

    def test_native_adapters_and_real_graders_under_queue(self):
        from test_evaluation import RunnerTests
        self.s['tasks'] = ['tasks/slug-normalization']
        self.s['matrix'] = []
        for provider, model in [('codex', 'gpt-5.6-sol'), ('claude', 'claude-sonnet-5')]:
            self.s['execution'][provider + '_bin'] = RunnerTests.fake_binary(self, provider)
            self.s['matrix'].append({'provider': provider, 'model': model, 'efforts': ['medium']})
        self.prepare(repeats=3)
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test-key','ANTHROPIC_API_KEY':'test-key'}), contextlib.redirect_stdout(io.StringIO()):
            info = run(self.path, self.root / 'run', workers=5)
        self.assertEqual(info['state'], 'complete')
        rows = read_json(self.root / 'run/results.json')['rows']
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r['completion'] == 1 and r['scheduling_workers'] == 5 for r in rows))
