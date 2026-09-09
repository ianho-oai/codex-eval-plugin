from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import __version__
from .core import DATA, EvalError, digest, load_suite, now, read_json, require, tree, write_json
from .discovery import history, repo_evidence, snapshot
from .report import report, serve
from .runner import clean_env, execute, preflight, run, schedule, validate_graders


def load_local_keys():
    """Read API keys from the invoking directory without executing shell code."""
    path = Path.cwd() / '.env.local'
    if not path.is_file():
        return
    for number, line in enumerate(path.read_text().splitlines(), 1):
        match = re.match(r'^\s*(?:export\s+)?(OPENAI_API_KEY|ANTHROPIC_API_KEY)\s*=\s*(.*)$', line)
        if not match or match[1] in os.environ:
            continue
        try:
            values = shlex.split(match[2], comments=True)
        except ValueError:
            raise EvalError(f'Invalid API key assignment in .env.local line {number}') from None
        require(len(values) <= 1, f'Invalid API key assignment in .env.local line {number}')
        if values:
            os.environ[match[1]] = values[0]


def initialize(destination, mode, image):
    dest = Path(destination).resolve()
    require(not dest.exists(), 'Destination exists; choose a new evaluation directory')
    dest.mkdir(parents=True)
    shutil.copytree(DATA / 'examples', dest / 'tasks')
    shutil.copy2(DATA / 'rates.json', dest / 'rates.json')
    catalog = read_json(DATA / 'models.json')
    s = {'schema_version': 1, 'name': dest.name, 'tasks': ['tasks/'+p.name for p in sorted((dest/'tasks').iterdir()) if p.is_dir()],
         'matrix': [{'provider': m['provider'], 'model': m['id'], 'efforts': [m['default_effort']]} for m in catalog['models'] if m.get('default')],
         'repeats': 3, 'seed': 42, 'pricing': 'rates.json',
         'limits': {'agent_seconds': 600, 'grader_seconds': 60, 'spend_stop_usd': 20, 'claude_max_turns': 50},
         'execution': {'mode': mode, 'image': image or '', 'codex_bin': 'codex', 'claude_bin': 'claude',
                       'codex_version': '0.153.4', 'claude_version': '2.1.220', 'cpus': 2, 'memory_mb': 4096}}
    write_json(dest / 'suite.json', s)
    write_json(dest / 'discovery.json', {'schema_version': 1, 'state': 'awaiting_customer_discovery',
               'source_choices': [], 'history_consents': [], 'repository_scopes': [], 'workflows': [],
               'assumptions': ['Included tasks are original harness examples; replace with approved customer tasks.'],
               'portfolio_approved': False})
    (dest / '.gitignore').write_text('*\n')
    return {'suite': str(dest/'suite.json'), 'next': 'Complete discovery and replace examples. Pin image and CLI versions, then validate --check-graders, plan, and approve.'}


def models(provider, refresh):
    if not refresh:
        return read_json(DATA / 'models.json')
    require(provider in ('codex', 'claude'), '--refresh requires --provider')
    key_name = 'OPENAI_API_KEY' if provider == 'codex' else 'ANTHROPIC_API_KEY'
    require(bool(os.environ.get(key_name)), f'{key_name} is missing; set it securely in the invoking terminal')
    endpoint = 'https://api.openai.com/v1/models' if provider == 'codex' else 'https://api.anthropic.com/v1/models?limit=1000'
    headers = {'Authorization': 'Bearer '+os.environ[key_name]} if provider == 'codex' else {'x-api-key': os.environ[key_name], 'anthropic-version': '2023-06-01'}
    found = []
    try:
        while endpoint:
            with urllib.request.urlopen(urllib.request.Request(endpoint, headers=headers), timeout=30) as r:
                payload = json.load(r)
            found.extend(x['id'] for x in payload.get('data', []))
            # Anthropic model listing paginates; OpenAI's /models does not.
            if provider == 'claude' and payload.get('has_more'):
                from urllib.parse import quote
                endpoint = 'https://api.anthropic.com/v1/models?limit=1000&after_id='+quote(payload['last_id'], safe='')
            else:
                endpoint = None
    except urllib.error.HTTPError as e:
        raise EvalError(f'Model listing rejected: HTTP {e.code}; no auth or endpoint fallback attempted') from e
    except (OSError, ValueError) as e:
        raise EvalError('Model listing unavailable: '+type(e).__name__) from e
    return {'provider': provider, 'checked_at': now(), 'models': sorted(found),
            'note': 'Account-visible IDs, not proof of Codex/Claude Code support. Review exact IDs and published pricing before editing a suite.'}


def export_plugin(output):
    root = Path(__file__).resolve().parent.parent
    require((root / '.codex-plugin' / 'plugin.json').exists(), 'Export from the source plugin or extracted plugin ZIP')
    all_files = tree(root)
    files = [p for p in all_files if Path(p).parts[0] in {'.codex-plugin', 'bin', 'ceval', 'skills'} or p in {'pyproject.toml', 'README.md', 'LICENSE', 'Dockerfile'}]
    require(len([p for p in files if p.endswith('/SKILL.md')]) == 1, 'Plugin must contain exactly one skill')
    out = Path(output).resolve()
    require(not out.is_relative_to(root), 'Export outside the plugin source directory')
    out.mkdir(parents=True, exist_ok=True)
    target = out / f'codex-eval-plugin-{__version__}.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(files):
            info = zipfile.ZipInfo('codex-eval-plugin/'+rel, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if rel == 'bin/codex-eval' else 0o100644) << 16
            z.writestr(info, (root / rel).read_bytes())
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(checksum+'  '+target.name+'\n')
    return {'zip': str(target), 'sha256': checksum, 'files': len(files)}


def self_check():
    for p in DATA.rglob('*.json'):
        read_json(p)
    root = Path(__file__).resolve().parent.parent
    manifest = read_json(root / '.codex-plugin' / 'plugin.json') if (root / '.codex-plugin').exists() else None
    if manifest:
        require(manifest['version'] == __version__, 'Version mismatch')
        require(len(list((root / 'skills').rglob('SKILL.md'))) == 1, 'Exactly one skill required')
        require(manifest['repository'] == 'https://github.com/ianho-oai/codex-eval-plugin', 'Repository metadata mismatch')
    for name in ('index.html', 'app.js', 'style.css'):
        require((DATA / 'web' / name).is_file(), 'Missing dashboard asset')
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)/'example'
        initialize(p, 'local', None)
        _, s, tasks, _, seal = load_suite(p/'suite.json')
    return {'version': __version__, 'task_examples': len(tasks), 'scheduled_example_cells': len(schedule(s, tasks)),
            'status': 'passed', 'note': 'Structure validation only. Run validate --check-graders and unit/integration tests for behavior.'}


def smoke(provider, output, model=None, binary=None):
    """One-command live check using only the bundled original, trusted slug task."""
    destination = Path(output).resolve()
    require(not destination.exists(), 'Smoke output exists; choose a new directory to preserve the earlier run')
    key = 'OPENAI_API_KEY' if provider == 'codex' else 'ANTHROPIC_API_KEY'
    require(bool(os.environ.get(key)), f'{key} is missing. Set it securely in the same terminal, then rerun this command.')
    exe = binary or shutil.which('codex' if provider == 'codex' else 'claude')
    require(bool(exe), f'{provider} CLI is not installed or is not on PATH')
    v = execute([exe, '--version'], None, clean_env(), 30)
    import re
    match = re.search(r'\b\d+\.\d+\.\d+\b', v['stdout'])
    require(v['exit_code'] == 0 and match is not None, 'Cannot resolve native CLI version; pass --binary with the installed executable path')
    initialize(destination/'suite', 'local', None)
    path = destination/'suite/suite.json'
    s = read_json(path)
    selected_model = model or ('gpt-5.6-luna' if provider == 'codex' else 'claude-sonnet-5')
    s.update(tasks=['tasks/slug-normalization'], repeats=1,
             matrix=[{'provider':provider, 'model':selected_model, 'efforts':['default' if 'haiku' in selected_model else 'medium']}])
    s['execution'][provider+'_bin'] = exe
    s['execution'][provider+'_version'] = match.group()
    s['limits'].update(agent_seconds=120, spend_stop_usd=5)
    write_json(path,s)
    checks = validate_graders(path)
    seal=load_suite(path)[4]
    write_json(path.parent/'approval.json', {'seal':seal,'approved_at':now(),
               'approved_by':'Explicit CLI smoke command for bundled trusted fixture',
               'validation_digest':digest(read_json(path.parent/'validation.json'))})
    result=run(path,destination/'run')
    report(destination/'run')
    rows=read_json(destination/'run/results.json')['rows']
    return {'output':str(destination/'run'), 'state':result['state'], 'stop_reason':result.get('stop_reason'),
            'rows':[{k:r.get(k) for k in ('task_id','model','completion','status','latency_seconds','input_tokens','output_tokens','cost_usd','cost_source')} for r in rows],
            'note':'Live trusted-local development smoke test, not a hermetic benchmark. Dashboard: codex-eval dashboard '+str(destination/'run')}


def demo(output):
    """Deterministic synthetic data for dashboard QA only, never a benchmark result."""
    import random
    rng = random.Random(31)
    out = Path(output)
    require(not out.exists(), 'Demo destination exists')
    rows = []
    for task, difficulty in [('facet-filter', 'medium'), ('async-search', 'hard'), ('slug-normalization', 'easy')]:
        for provider, model in [('codex', 'gpt-5.6-sol'), ('claude', 'claude-sonnet-5')]:
            for repeat in range(1, 4):
                completed = rng.random() > .25
                r = {'cell_id': str(len(rows)), 'task_id': task, 'difficulty': difficulty, 'provider': provider,
                     'model': model, 'effort': 'medium', 'repeat': repeat, 'completion': int(completed),
                     'status': 'passed' if completed else 'failed', 'valid': True, 'simulation': True,
                     'execution_mode': 'synthetic', 'latency_seconds': rng.uniform(20, 180),
                     'agent_seconds': rng.uniform(15, 120), 'grader_seconds': 0.1,
                     'cost_usd': rng.uniform(.05, 1), 'cost_source': 'synthetic', 'input_tokens': rng.randrange(2000, 30000),
                     'output_tokens': rng.randrange(300, 9000), 'cache_read_tokens': rng.randrange(100, 2000),
                     'cache_write_tokens': None, 'reasoning_tokens': None, 'turns': 1 if provider == 'codex' else rng.randrange(2, 20),
                     'turn_unit': 'codex_conversation_turn' if provider == 'codex' else 'claude_native_turn', 'tool_calls': rng.randrange(1, 20)}
                rows.append(r)
    rows[-1].update(cost_usd=None, status='provider_error', valid=False, completion=0)
    write_json(out/'run.json', {'schema_version': 1, 'simulation': True, 'created_at': now(), 'state': 'complete',
                               'suite': {'name': 'DEMO — synthetic data'}, 'schedule': [{'cell_id': r['cell_id']} for r in rows]})
    write_json(out/'results.json', {'schema_version': 1, 'rows': rows})
    return {'output': str(out.resolve()), 'simulation': True, 'rows': len(rows)}


def parser():
    p = argparse.ArgumentParser(prog='codex-eval', description='Discover, freeze, run, grade, and compare native coding agents.')
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('init'); a.add_argument('directory'); a.add_argument('--mode', choices=['docker', 'local'], default='docker'); a.add_argument('--image')
    for name in ('plan', 'validate', 'approve', 'doctor'):
        a = sub.add_parser(name); a.add_argument('suite')
        if name == 'validate': a.add_argument('--check-graders', action='store_true')
        if name == 'approve': a.add_argument('--by', required=True)
    a = sub.add_parser('run'); a.add_argument('suite'); a.add_argument('--output', required=True); a.add_argument('--resume', action='store_true')
    a = sub.add_parser('models'); a.add_argument('--provider', choices=['codex', 'claude']); a.add_argument('--refresh', action='store_true')
    sub.add_parser('benchmarks'); sub.add_parser('self-check')
    a = sub.add_parser('history'); a.add_argument('--provider', required=True, choices=['codex', 'claude']); a.add_argument('--root'); a.add_argument('--days', type=int, default=30); a.add_argument('--consent', action='store_true'); a.add_argument('--output', required=True)
    a = sub.add_parser('repo'); a.add_argument('--path'); a.add_argument('--provider', choices=['github', 'gitlab']); a.add_argument('--repo'); a.add_argument('--days', type=int, default=30); a.add_argument('--host'); a.add_argument('--output', required=True)
    a = sub.add_parser('snapshot'); a.add_argument('--repo', required=True); a.add_argument('--commit', required=True); a.add_argument('--output', required=True)
    a = sub.add_parser('report'); a.add_argument('run_dir')
    a = sub.add_parser('dashboard'); a.add_argument('run_dir'); a.add_argument('--port', type=int, default=8765)
    a = sub.add_parser('export'); a.add_argument('--output', default='dist')
    a = sub.add_parser('demo'); a.add_argument('--output', default='evaluations/demo')
    a = sub.add_parser('image-pin'); a.add_argument('suite'); a.add_argument('--image', required=True)
    a = sub.add_parser('smoke'); a.add_argument('--provider', required=True, choices=['codex','claude']); a.add_argument('--output', required=True); a.add_argument('--model'); a.add_argument('--binary')
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        load_local_keys()
        c = a.command
        if c == 'init': result = initialize(a.directory, a.mode, a.image)
        elif c in ('plan', 'validate', 'approve', 'doctor'):
            path, s, tasks, pricing, seal = load_suite(a.suite)
            if c == 'doctor': result = preflight(s)
            elif c == 'validate' and a.check_graders: result = {'checks': validate_graders(a.suite), 'seal': seal}
            elif c == 'approve':
                receipt = read_json(path.parent / 'validation.json')
                require(receipt.get('seal') == seal, 'Run validate --check-graders against these exact inputs first')
                require(bool(a.by.strip()), '--by must identify the approver')
                result = {'seal': seal, 'approved_by': a.by, 'approved_at': now(), 'validation_digest': digest(receipt)}
                write_json(path.parent / 'approval.json', result)
            else:
                result = {'seal': seal, 'suite': s, 'tasks': [t['spec'] for t in tasks],
                          'scheduled_cells': len(schedule(s, tasks)), 'pricing_checked_at': pricing.get('checked_at'),
                          'note': 'Review tasks, limits, CLI versions, exact model IDs, rates, and execution mode before approval. Model support and API access need doctor/live validation.'}
        elif c == 'run': result = run(a.suite, a.output, a.resume)
        elif c == 'models': result = models(a.provider, a.refresh)
        elif c == 'benchmarks': result = read_json(DATA/'benchmarks.json')
        elif c == 'history': result = history(a.provider, a.root or ('~/.codex/sessions' if a.provider == 'codex' else '~/.claude/projects'), a.days, a.consent, a.output)
        elif c == 'repo':
            result = repo_evidence(a.path, a.provider, a.repo, a.days, a.host)
            write_json(a.output, result)
            result = {'output': a.output, 'coverage_note': result['coverage_note']}
        elif c == 'snapshot': result = snapshot(a.repo, a.commit, a.output)
        elif c == 'report': result = report(a.run_dir)
        elif c == 'dashboard': serve(a.run_dir, a.port); return 0
        elif c == 'export': result = export_plugin(a.output)
        elif c == 'self-check': result = self_check()
        elif c == 'demo': result = demo(a.output)
        elif c == 'smoke': result = smoke(a.provider, a.output, a.model, a.binary)
        elif c == 'image-pin':
            s = read_json(a.suite)
            r = execute(['docker', 'image', 'inspect', a.image, '--format', '{{.Id}}'], None, clean_env(), 30)
            require(r['exit_code'] == 0 and r['stdout'].strip().startswith('sha256:'), 'Image must already be built/pulled and inspectable')
            s['execution']['image'] = r['stdout'].strip()
            write_json(a.suite, s)
            result = {'image': s['execution']['image'], 'note': 'Image pin changed. Revalidate and approve before running.'}
        else: raise EvalError('Unknown command')
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        if c == 'smoke' and (not result['rows'] or any(r['completion'] != 1 for r in result['rows'])):
            return 1
        if c == 'run' and result.get('state') != 'complete':
            return 1
        return 0
    except (EvalError, OSError, KeyError, TypeError, ValueError) as e:
        # No raw upstream HTTP bodies or environment dumps.
        from .core import redact
        print('Error: '+redact(str(e)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
