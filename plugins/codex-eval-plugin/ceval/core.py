"""Strict suite validation, content-addressed approvals, and safe artifact I/O."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__

DATA = Path(__file__).parent / 'data'
ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,100}$')
IGNORED = {'__pycache__', '.git', 'node_modules', '.venv', '.DS_Store'}
CUSTOMIZATIONS = {'.codex', '.claude', '.agents', '.mcp.json', 'AGENTS.md', 'CLAUDE.md'}


class EvalError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise EvalError(f'Cannot read JSON: {path}') from e


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.write-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def require(test, message):
    if not test:
        raise EvalError(message)


def number(value, name, minimum=0):
    require(type(value) in (int, float) and math.isfinite(value) and value >= minimum,
            f'{name} must be finite and >= {minimum}')


def child(root, relative):
    root = Path(root).resolve()
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(), 'Expected relative path')
    raw = root / relative
    require('..' not in Path(relative).parts, f'Parent traversal forbidden: {relative}')
    require(not any(p.is_symlink() for p in [raw, *list(raw.parents)[:len(Path(relative).parts)-1]]),
            f'Symlink forbidden: {relative}')
    result = raw.resolve()
    require(result.is_relative_to(root), f'Path escapes root: {relative}')
    return result


def tree(path, *, candidate=False):
    path = Path(path)
    require(path.is_dir(), f'Missing directory: {path}')
    result = {}
    for p in sorted(path.rglob('*')):
        rel = p.relative_to(path)
        if any(x in IGNORED for x in rel.parts):
            continue
        require(not p.is_symlink(), f'Symlink forbidden: {rel}')
        if p.is_dir():
            continue
        require(p.is_file(), f'Special file forbidden: {rel}')
        require(p.stat().st_nlink == 1, f'Hard link forbidden: {rel}')
        if not candidate:
            require(not any(x.startswith('.env') or x in {'auth.json', 'credentials.json'} for x in rel.parts),
                    f'Credential-like file forbidden: {rel}')
        result[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def copy_tree(source, target):
    files = tree(source, candidate=True)
    Path(target).mkdir(parents=True, exist_ok=True)
    for rel in files:
        dst = child(target, rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(child(source, rel), dst)


def allowed_changes(before, candidate, patterns):
    after = tree(candidate, candidate=True)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    denied = [k for k in changed if not any(fnmatch.fnmatchcase(k, p) for p in patterns)]
    return changed, denied


def engine_digest():
    return digest(tree(Path(__file__).parent))


def load_suite(path):
    path = Path(path).resolve()
    s = read_json(path)
    fields = {'schema_version', 'name', 'tasks', 'matrix', 'repeats', 'seed', 'execution', 'limits', 'pricing'}
    require(isinstance(s, dict) and s.get('schema_version') in (1, 2), 'Unsupported suite schema')
    if s['schema_version'] == 2:
        fields |= {'purpose', 'workflows'}
    require(set(s) == fields, f'Suite fields must be exactly {sorted(fields)}')
    if s['schema_version'] == 2:
        require(s['purpose'] in ('customer', 'smoke'), 'Suite purpose must be customer or smoke')
        require(isinstance(s['workflows'], list), 'workflows must be a list')
    require(isinstance(s['name'], str) and ID.fullmatch(s['name']), 'Invalid suite name')
    require(type(s['repeats']) is int and 1 <= s['repeats'] <= 100, 'repeats must be 1..100')
    require(type(s['seed']) is int, 'seed must be integer')
    ex = s['execution']
    require(set(ex) == {'mode', 'image', 'codex_bin', 'claude_bin', 'codex_version', 'claude_version', 'cpus', 'memory_mb'}, 'Invalid execution fields')
    require(ex['mode'] in ('docker', 'local'), 'Execution must be docker or local')
    if ex['mode'] == 'docker':
        require(bool(re.fullmatch(r'(?:[^\s]+@)?sha256:[0-9a-f]{64}', ex['image'])), 'Docker image must be an immutable sha256 ID or repo@sha256 digest; run image-pin')
    for provider in ('codex', 'claude'):
        require(isinstance(ex[provider + '_version'], str) and bool(ex[provider + '_version']), 'Pin both CLI versions')
        require(isinstance(ex[provider + '_bin'], str) and bool(ex[provider + '_bin']), 'Specify CLI binaries')
    number(ex['cpus'], 'cpus', 0.1)
    number(ex['memory_mb'], 'memory_mb', 128)
    require(set(s['limits']) == {'agent_seconds', 'grader_seconds', 'spend_stop_usd', 'claude_max_turns'}, 'Invalid limits')
    for k, v in s['limits'].items():
        number(v, k, 1 if k != 'spend_stop_usd' else 0.01)
    require(type(s['limits']['claude_max_turns']) is int, 'claude_max_turns must be integer')
    require(isinstance(s['matrix'], list) and s['matrix'], 'Empty model matrix')
    lanes = set()
    for m in s['matrix']:
        require(isinstance(m, dict) and set(m) == {'provider', 'model', 'efforts'}, 'Invalid model matrix entry')
        require(m['provider'] in ('codex', 'claude'), 'Unsupported provider')
        require(isinstance(m['model'], str) and ID.fullmatch(m['model']), 'Invalid exact model ID')
        require(m['model'] not in {'sonnet', 'opus', 'fable', 'haiku', 'gpt-5.6'}, 'Use full model IDs, not convenience aliases')
        require(isinstance(m['efforts'], list) and m['efforts'], 'Empty effort list')
        for effort in m['efforts']:
            require(effort in ('default', 'low', 'medium', 'high', 'xhigh', 'max'), 'Unsupported effort')
            require((m['provider'], m['model'], effort) not in lanes, 'Duplicate matrix lane')
            lanes.add((m['provider'], m['model'], effort))
    pricing_path = child(path.parent, s['pricing'])
    pricing = read_json(pricing_path)
    require(pricing.get('schema_version') == 1 and isinstance(pricing.get('models'), dict), 'Invalid rate card')
    tasks = []
    require(isinstance(s['tasks'], list) and s['tasks'], 'Empty tasks')
    ids = set()
    for rel in s['tasks']:
        root = child(path.parent, rel)
        t = read_json(root / 'task.json')
        required = {'id', 'use_case', 'difficulty', 'difficulty_rationale', 'benchmark_refs', 'allowed_paths', 'grader'}
        require(isinstance(t, dict) and required <= set(t) <= required | {'workflow_id', 'provenance'}, f'Invalid task fields: {rel}')
        require(isinstance(t['id'], str) and ID.fullmatch(t['id']) and t['id'] not in ids, 'Invalid or duplicate task id')
        ids.add(t['id'])
        require(t['difficulty'] in ('easy', 'medium', 'hard'), 'Difficulty must be easy, medium, hard')
        for k in ('use_case', 'difficulty_rationale'):
            require(isinstance(t[k], str) and bool(t[k].strip()), f'Missing {k}')
        refs = {x['id'] for x in read_json(DATA / 'benchmarks.json')['benchmarks']}
        require(isinstance(t['benchmark_refs'], list) and all(x in refs for x in t['benchmark_refs']), 'Unknown benchmark references')
        from .catalog import validate_provenance
        validate_provenance(t)
        require(t['benchmark_refs'] or (t.get('provenance') or {}).get('kind') == 'original', 'Unreferenced tasks must explain their original design')
        require(isinstance(t['allowed_paths'], list) and t['allowed_paths'], 'Specify allowed edits')
        for p in t['allowed_paths']:
            child(root / 'baseline', p)
        require(isinstance(t['grader'], list) and t['grader'] and all(isinstance(x, str) for x in t['grader']), 'Grader must be argv list')
        require('{candidate}' in ' '.join(t['grader']) and '{grader}' in ' '.join(t['grader']), 'Grader argv must use {candidate} and {grader}')
        require((root / 'instruction.md').is_file() and (root / 'instruction.md').read_text().strip(), 'Missing task instruction')
        for d in ('baseline', 'oracle', 'grader'):
            files = tree(root / d)
            require(bool(files), f'Empty {d}')
            if d == 'baseline':
                require(not any(set(Path(k).parts) & CUSTOMIZATIONS for k in files), 'Remove agent customizations from baseline')
        base = tree(root / 'baseline')
        _, denied = allowed_changes(base, root / 'oracle', t['allowed_paths'])
        require(not denied, f'Oracle edits forbidden files: {denied}')
        tasks.append({'spec': t, 'root': root, 'hash': digest(tree(root))})
    from .catalog import coverage
    portfolio_coverage = coverage(s, tasks)
    require(not portfolio_coverage['missing'], 'Missing workflow difficulty tiers: '+str(portfolio_coverage['missing']))
    frozen = {'suite': s, 'task_hashes': {t['spec']['id']: t['hash'] for t in tasks},
              'pricing': pricing, 'engine': engine_digest(), 'version': __version__}
    return path, s, tasks, pricing, digest(frozen)


def redact(text):
    for k in ('OPENAI_API_KEY', 'CODEX_API_KEY', 'ANTHROPIC_API_KEY'):
        v = os.environ.get(k)
        if v:
            text = text.replace(v, '[REDACTED]')
    return re.sub(r'\bsk-[A-Za-z0-9_-]{12,}', '[REDACTED]', text)
