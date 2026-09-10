"""Offline native-process checks for runtime setup and preserved failures."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/codex-eval-plugin'))
from ceval.runner import attempt, native_argv, runtime_diagnostics


HELPER_WARNING = ('WARNING: proceeding, even though we could not create PATH aliases: '
                  'Refusing to create helper binaries under temporary dir "/tmp" (codex_home: test)')
SANDBOX_ERROR = ('ERROR codex_core::tools::router: error=apply_patch verification failed: '
                 'fs sandbox helper failed with status exit status: 101: thread main panicked\n'
                 'failed to open synthetic bubblewrap mount registry lock /tmp/test/lock: '
                 'Read-only file system (os error 30)')


class RuntimeEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task_root = self.root / 'task'
        (self.task_root / 'baseline').mkdir(parents=True)
        (self.task_root / 'baseline/inventory_cli.py').write_text('broken\n')
        (self.task_root / 'instruction.md').write_text('Write the fixed inventory output.')
        self.task = {'root': self.task_root, 'spec': {
            'id': 'inventory', 'difficulty': 'easy', 'use_case': 'CLI',
            'allowed_paths': ['inventory_cli.py'],
            'grader': [sys.executable, '-c',
                       'from pathlib import Path; raise SystemExit(0 if Path("inventory_cli.py").read_text() == "fixed\\n" else 1)']}}
        self.tools = self.root / 'custom tools "quoted"'
        self.tools.mkdir()
        tool = self.tools / 'ceval-test-tool'
        tool.write_text('#!' + sys.executable + '\nprint("fixed")\n')
        tool.chmod(0o700)
        self.binary = self.root / 'offline-codex'
        self.binary.write_text('#!' + sys.executable + '\n' + '''import json, os, stat, subprocess, sys, time
from pathlib import Path
prompt = sys.stdin.read()
setting = next(a for a in sys.argv if a.startswith('shell_environment_policy.set='))
shell_path = json.loads(setting.split('{PATH=', 1)[1][:-1])
mode = sys.argv[sys.argv.index('--model') + 1]
assert 'GITHUB_TOKEN' not in os.environ and 'OPENAI_BASE_URL' not in os.environ
output = subprocess.check_output(['ceval-test-tool'], env={'PATH': shell_path}, text=True)
Path('inventory_cli.py').write_text(output)
home = Path(os.environ['CODEX_HOME'])
print(json.dumps({'type': 'test.environment', 'cwd': str(Path.cwd()), 'home': str(home),
                  'home_mode': stat.S_IMODE(home.stat().st_mode), 'prompt': prompt}), flush=True)
''' + f'print({HELPER_WARNING!r}, file=sys.stderr, flush=True)\n'
            + f'print({SANDBOX_ERROR!r}, file=sys.stderr, flush=True)\n'
            + '''if mode == 'backup':
    Path('inventory_cli.py.orig').write_text('backup')
if mode == 'timeout':
    time.sleep(10)
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 100,
                  'cached_input_tokens': 20, 'output_tokens': 10}}), flush=True)
''')
        self.binary.chmod(0o700)
        self.suite = {'execution': {'mode': 'local', 'codex_bin': str(self.binary)},
                      'limits': {'agent_seconds': 5, 'grader_seconds': 5,
                                 'claude_max_turns': 10, 'spend_stop_usd': None}}

    def run_attempt(self, model='pass'):
        cell = {'cell_id': model, 'task_id': 'inventory', 'provider': 'codex',
                'model': model, 'effort': 'medium', 'repeat': 1}
        directory = self.root / 'attempts' / model
        with patch.dict(os.environ, {'PATH': str(self.tools), 'OPENAI_API_KEY': 'test-key',
                                     'GITHUB_TOKEN': 'excluded', 'OPENAI_BASE_URL': 'excluded'}):
            result = attempt(cell, self.task, self.suite, {}, directory, {'ok': True})
        return result, directory

    def test_private_scratch_custom_toolchain_and_runtime_diagnostics(self):
        row, directory = self.run_attempt()
        self.assertEqual((row['status'], row['completion'], row['valid']), ('passed', 1, True))
        self.assertEqual(row['runtime_diagnostics'], ['helper_binaries_refused_in_temp',
                         'filesystem_sandbox_helper_failed', 'bubblewrap_registry_lock_failed'])
        env = json.loads((directory / 'events.jsonl').read_text().splitlines()[0])
        home, candidate = Path(env['home']), Path(env['cwd'])
        self.assertEqual(home.parent, candidate.parent)
        self.assertEqual(home.parent.parent, directory.resolve())
        self.assertEqual(env['home_mode'], 0o700)
        self.assertFalse(home.parent.exists())
        self.assertEqual((directory / 'candidate/inventory_cli.py').read_text(), 'fixed\n')
        self.assertIn('.orig and .rej', env['prompt'])
        self.assertIn('Finish within 5 seconds', env['prompt'])
        argv = json.loads((directory / 'invocation.json').read_text())['argv']
        self.assertEqual(argv[argv.index('--sandbox') + 1], 'workspace-write')
        self.assertIn('shell_environment_policy.inherit="none"', argv)
        self.assertIn('allow_login_shell=false', argv)
        self.assertNotIn('excluded', str(argv))

    def test_timeout_candidate_passes_grader_but_stays_timeout_and_cost_missing(self):
        self.suite['limits']['agent_seconds'] = 2
        row, directory = self.run_attempt('timeout')
        self.assertEqual((row['status'], row['completion'], row['valid']), ('timeout', 0, True))
        self.assertEqual(row['grader_exit_code'], 0)
        self.assertIsNone(row['cost_usd'])
        self.assertFalse(row['telemetry_complete'])
        self.assertTrue((directory / 'candidate/inventory_cli.py').exists())
        self.assertFalse(list(directory.glob('ceval-cell-*')))

    def test_backup_is_preserved_and_still_forbidden(self):
        row, directory = self.run_attempt('backup')
        self.assertEqual((row['status'], row['completion']), ('forbidden_changes', 0))
        self.assertIsNone(row['grader_exit_code'])
        self.assertTrue((directory / 'candidate/inventory_cli.py.orig').exists())
        self.assertFalse((directory / 'grader.stdout.txt').exists())
        self.assertFalse(list(directory.glob('ceval-cell-*')))

    def test_diagnostics_do_not_match_generic_task_failures(self):
        self.assertEqual(runtime_diagnostics('Task uses a sandbox; read-only file system; helper failed.'), [])
        self.assertEqual(runtime_diagnostics(''), [])

    def test_shell_path_serialization_preserves_special_characters(self):
        value = '/tools with spaces/"quotes"/back\\slash:/usr/bin'
        with patch.dict(os.environ, {'PATH': value}):
            argv = native_argv('codex', 'codex', 'test', 'medium', 5, 10, None)
        setting = next(a for a in argv if a.startswith('shell_environment_policy.set='))
        self.assertEqual(json.loads(setting.split('{PATH=', 1)[1][:-1]), value)
        self.assertNotIn('shell_environment_policy.inherit="all"', argv)


if __name__ == '__main__':
    unittest.main()
