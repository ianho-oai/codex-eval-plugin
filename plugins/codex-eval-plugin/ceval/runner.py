"""Sequential, sealed execution with immutable attempt records and separate grading."""
from __future__ import annotations

import json
import os
import platform
import random
import shlex
import shutil
import signal
import sys
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from .core import (EvalError, allowed_changes, child, copy_tree, digest, load_suite, now,
                   read_json, redact, require, tree, write_json)
from .telemetry import normalize


def clean_env():
    # Deliberate allowlist: no subscription auth, alternate API base URLs, proxy keys,
    # cloud credentials, GH tokens, or customization variables inherited from caller.
    return {k: v for k, v in os.environ.items() if k in (
        'PATH', 'SYSTEMROOT', 'WINDIR', 'TMPDIR', 'TEMP', 'TMP', 'LANG', 'LC_ALL',
        # Preserve host-managed egress and certificate configuration.
        'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
        'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
        'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE')}


def execute(argv, cwd, env, timeout, stdin=None):
    start = time.monotonic()
    p = None
    try:
        p = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, start_new_session=True)
        out, err = p.communicate(stdin, timeout=timeout)
        return {'exit_code': p.returncode, 'stdout': redact(out), 'stderr': redact(err),
                'seconds': time.monotonic()-start, 'timed_out': False}
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
        return {'exit_code': 124, 'stdout': redact(out), 'stderr': redact(err),
                'seconds': time.monotonic()-start, 'timed_out': True}
    except (OSError, ValueError) as e:
        return {'exit_code': 127, 'stdout': '', 'stderr': type(e).__name__,
                'seconds': time.monotonic()-start, 'timed_out': False}
    except KeyboardInterrupt:
        if p and p.poll() is None:
            os.killpg(p.pid, signal.SIGKILL)
            out, err = p.communicate()
            return {'exit_code': 130, 'stdout': redact(out), 'stderr': redact(err),
                    'seconds': time.monotonic()-start, 'timed_out': False, 'interrupted': True}
        raise
    except BaseException:
        if p and p.poll() is None:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
        raise


def docker_base(ex, name, network='none'):
    return ['docker', 'run', '--rm', '--name', name, '--init', '--read-only',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=256',
            '--cpus', str(ex['cpus']), '--memory', f"{ex['memory_mb']}m", '--network', network,
            '--tmpfs', '/tmp:rw,exec,nosuid,size=512m', '--user', f'{os.getuid()}:{os.getgid()}',
            '--env', 'HOME=/tmp/home', '--workdir', '/workspace']


def cleanup_container(name):
    execute(['docker', 'rm', '-f', name], None, clean_env(), 15)


def grade(task, candidate, suite):
    ex = suite['execution']
    name = 'ceval-grade-' + uuid.uuid4().hex[:16]
    if ex['mode'] == 'docker':
        argv = docker_base(ex, name)
        argv += ['--mount', f'type=bind,src={candidate},dst=/workspace,readonly',
                 '--mount', f"type=bind,src={task['root']/ 'grader'},dst=/grader,readonly", ex['image']]
        replacements = {'{candidate}': '/workspace', '{grader}': '/grader'}
        cwd = None
    else:
        argv, cwd = [], candidate
        replacements = {'{candidate}': str(candidate), '{grader}': str(task['root'] / 'grader')}
    for arg in task['spec']['grader']:
        for src, dst in replacements.items():
            arg = arg.replace(src, dst)
        argv.append(arg)
    try:
        env = clean_env()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        return execute(argv, cwd, env, suite['limits']['grader_seconds'])
    finally:
        if ex['mode'] == 'docker':
            cleanup_container(name)


def validate_graders(path):
    path, s, tasks, pricing, seal = load_suite(path)
    checks = []
    for task in tasks:
        outcomes = {}
        for fixture in ('baseline', 'oracle'):
            with tempfile.TemporaryDirectory(prefix='ceval-verify-') as td:
                candidate = Path(td) / 'candidate'
                copy_tree(task['root'] / fixture, candidate)
                r = grade(task, candidate, s)
                outcomes[fixture] = {k: r[k] for k in ('exit_code', 'seconds', 'timed_out', 'stdout', 'stderr')}
        # Exit 1 is a deliberate assertion failure; crashes/timeouts are invalid fixtures.
        require(outcomes['baseline']['exit_code'] == 1 and outcomes['oracle']['exit_code'] == 0,
                f"Invalid grader for {task['spec']['id']}: baseline={outcomes['baseline']['exit_code']}, oracle={outcomes['oracle']['exit_code']}; inspect runtime/dependencies and grader")
        checks.append({'task': task['spec']['id'], **outcomes})
    require(load_suite(path)[4] == seal, 'Inputs changed during validation')
    write_json(path.parent / 'validation.json', {'seal': seal, 'checked_at': now(), 'checks': checks})
    return checks


def schedule(s, tasks):
    cells = []
    selected = s.get('selection', {}).get('task_ids')
    for t in tasks:
        if selected is not None and t['spec']['id'] not in selected:
            continue
        for m in s['matrix']:
            for effort in m['efforts']:
                for repeat in range(1, s['repeats']+1):
                    c = {'task_id': t['spec']['id'], 'provider': m['provider'], 'model': m['model'],
                         'effort': effort, 'repeat': repeat}
                    c['cell_id'] = digest(c)[:20]
                    cells.append(c)
    random.Random(s['seed']).shuffle(cells)
    return cells


def native_argv(provider, binary, model, effort, seconds, max_turns, budget, docker=False):
    if provider == 'codex':
        return [binary, '-a', 'never', 'exec', '--json', '--ephemeral', '--ignore-user-config',
                '--skip-git-repo-check', '--color', 'never', '--model', model,
                '--sandbox', 'danger-full-access' if docker else 'workspace-write',
                '-c', f'model_reasoning_effort="{effort}"', '-c', 'model_provider="openai"',
                '-c', 'forced_login_method="api"', '-c', 'web_search="disabled"',
                '-c', 'project_doc_max_bytes=0', '-c', 'features.multi_agent=false',
                '-c', 'features.apps=false', '-c', 'features.plugins=false', '-c', 'features.skills=false',
                '-c', 'shell_environment_policy.inherit="none"',
                '-c', 'shell_environment_policy.exclude=["*KEY*","*TOKEN*","*SECRET*"]',
                '-c', 'shell_environment_policy.set={PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"}', '-']
    return [binary, '-p', '--bare', '--no-session-persistence', '--output-format', 'stream-json',
            '--verbose', '--model', model, *(['--effort', effort] if effort != 'default' else []), '--max-turns', str(max_turns),
            *(['--max-budget-usd', str(budget)] if budget is not None else []), '--setting-sources', '', '--settings', '{}',
            '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--disable-slash-commands',
            '--tools', 'Bash,Read,Edit,Write,Glob,Grep', '--allowedTools', 'Bash,Read,Edit,Write,Glob,Grep',
            '--permission-mode', 'dontAsk']


def execution_summary(s):
    stop = s['limits']['spend_stop_usd']
    return {
        'message': 'Default: all cataloged GPT-5.6 models and GPT-6 Astra, plus all cataloged Claude models, at every supported single-agent effort level. No spend stop by default. Specify different models, efforts, or a spend stop before approving if you want a narrower run.',
        'selected_matrix': s['matrix'],
        'execution_mode': s['execution']['mode'],
        'task_setup': 'Default tasks use self-contained local fixtures and existing simple test runners. No Docker, simulators, GUI applications, or external services are required unless explicitly requested.',
        'repeats': s['repeats'],
        'spend_stop_usd': stop,
        'spend_policy': 'No spend stop; missing cost remains visible and does not stop dispatch.' if stop is None else f'Stop dispatch at known spend of ${stop:g}; missing cost may pause execution.',
        'overrides': 'configure SUITE --model PROVIDER:MODEL --effort LEVEL --spend-stop-usd AMOUNT; use --all-models --all-efforts --no-spend-stop to restore defaults.',
        'availability': 'Catalog membership does not establish account access. Unavailable models remain visible as failures; no silent substitution.'}


def preflight(s):
    ex = s['execution']
    summary = execution_summary(s)
    print(summary['message'], file=sys.stderr, flush=True)
    for lane in s['matrix']:
        print(f"  {lane['provider']}:{lane['model']} — {', '.join(lane['efforts'])}", file=sys.stderr, flush=True)
    print(f"Selected: {s['repeats']} repeat(s). {summary['spend_policy']}", file=sys.stderr, flush=True)
    print(f"Execution: {summary['execution_mode']}. {summary['task_setup']}", file=sys.stderr, flush=True)
    result = {'execution_summary': summary}
    for provider in sorted({m['provider'] for m in s['matrix']}):
        binary = ex[provider + '_bin']
        def invoke(args):
            name = 'ceval-probe-' + uuid.uuid4().hex[:16]
            if ex['mode'] == 'docker':
                cmd = docker_base(ex, name) + [ex['image'], binary] + args
            else:
                cmd = [binary] + args
            try:
                return execute(cmd, None, clean_env(), 30)
            finally:
                if ex['mode'] == 'docker':
                    cleanup_container(name)
        ver = invoke(['--version'])
        expected = ex[provider + '_version']
        ok = ver['exit_code'] == 0 and expected in ver['stdout'].split()
        capability = invoke(['exec', '--help'] if provider == 'codex' else ['--help']) if ok else None
        flags = ('--json', '--ephemeral', '--ignore-user-config') if provider == 'codex' else ('--bare', '--strict-mcp-config', '--effort')
        if capability:
            ok = capability['exit_code'] == 0 and all(flag in capability['stdout'] for flag in flags)
        key = 'OPENAI_API_KEY' if provider == 'codex' else 'ANTHROPIC_API_KEY'
        ok = ok and bool(os.environ.get(key))
        result[provider] = {'ok': ok, 'version': ver['stdout'].strip(), 'required_version': expected,
                            'key_present': bool(os.environ.get(key)),
                            'diagnostic': '' if ok else 'Missing key, CLI/version/capability mismatch, or unavailable execution image; run doctor.'}
    return result


def attempt(cell, task, s, pricing, directory, preflight_result):
    started = time.monotonic()
    row = {**cell, 'difficulty': task['spec']['difficulty'], 'use_case': task['spec']['use_case'],
           'started_at': now(), 'completion': 0, 'status': 'infrastructure_error', 'valid': False,
           'simulation': False, 'execution_mode': s['execution']['mode'], 'changed_files': [],
           'agent_seconds': None, 'grader_seconds': None, 'latency_seconds': None,
           'exit_code': None, 'grader_exit_code': None,
           **normalize(cell['provider'], '', cell['model'], pricing)}
    directory.mkdir(parents=True, exist_ok=True)
    if not preflight_result['ok']:
        row['diagnostic'] = preflight_result['diagnostic']
        row['latency_seconds'] = time.monotonic()-started
        row['not_started'] = True
        return row
    ex = s['execution']
    name = 'ceval-agent-' + uuid.uuid4().hex[:16]
    with tempfile.TemporaryDirectory(prefix='ceval-cell-') as td:
        candidate = Path(td) / 'candidate'
        copy_tree(task['root'] / 'baseline', candidate)
        before = tree(candidate)
        env = clean_env()
        key = 'CODEX_API_KEY' if cell['provider'] == 'codex' else 'ANTHROPIC_API_KEY'
        env[key] = os.environ['OPENAI_API_KEY' if cell['provider'] == 'codex' else key]
        config_home = Path(td) / 'agent-home'
        config_home.mkdir()
        env['CODEX_HOME' if cell['provider'] == 'codex' else 'CLAUDE_CONFIG_DIR'] = str(config_home)
        env['DISABLE_AUTOUPDATER'] = '1'
        native = native_argv(cell['provider'], ex[cell['provider']+'_bin'], cell['model'], cell['effort'],
                             s['limits']['agent_seconds'], s['limits']['claude_max_turns'],
                             s['limits']['spend_stop_usd'], ex['mode'] == 'docker')
        if ex['mode'] == 'docker':
            cmd = docker_base(ex, name, 'bridge') + ['--mount', f'type=bind,src={candidate},dst=/workspace',
                  '--env', key, '--env', 'CODEX_HOME=/tmp/codex', '--env', 'CLAUDE_CONFIG_DIR=/tmp/claude',
                  '--env', 'DISABLE_AUTOUPDATER=1', ex['image']] + native
            cwd = None
        else:
            cmd, cwd = native, candidate
        # No oracle or tests in the agent prompt. The same text is used across all lanes.
        prompt = (task['root'] / 'instruction.md').read_text()
        prompt += '\n\nImplement the requested behavior in this workspace. Allowed changed paths: ' + ', '.join(task['spec']['allowed_paths']) + '. Finish without asking follow-up questions.\n'
        write_json(directory / 'invocation.json', {'argv': cmd, 'prompt_sha256': digest(prompt), 'key_env': key})
        try:
            r = execute(cmd, cwd, env, s['limits']['agent_seconds'], prompt)
        finally:
            if ex['mode'] == 'docker':
                cleanup_container(name)
        (directory / 'events.jsonl').write_text(r['stdout'])
        (directory / 'stderr.txt').write_text(r['stderr'])
        row.update(normalize(cell['provider'], r['stdout'], cell['model'], pricing))
        row.update(agent_seconds=r['seconds'], exit_code=r['exit_code'])
        try:
            changed, denied = allowed_changes(before, candidate, task['spec']['allowed_paths'])
            row['changed_files'] = changed
            # Retain the candidate, but never overwrite sealed task sources.
            copy_tree(candidate, directory / 'candidate')
            if denied:
                row.update(status='forbidden_changes', valid=True, diagnostic='Edits outside allowed paths: '+', '.join(denied))
            else:
                g = grade(task, candidate, s)
                (directory / 'grader.stdout.txt').write_text(g['stdout'])
                (directory / 'grader.stderr.txt').write_text(g['stderr'])
                row.update(grader_seconds=g['seconds'], grader_exit_code=g['exit_code'])
                if r.get('interrupted'):
                    row.update(status='interrupted', valid=False)
                elif r['timed_out']:
                    row.update(status='timeout', valid=True)
                elif r['exit_code'] != 0 or not row['provider_success']:
                    row.update(status='provider_error', valid=False)
                elif g['exit_code'] not in (0, 1) or g['timed_out']:
                    row.update(status='grader_error', valid=False)
                else:
                    row.update(completion=int(g['exit_code'] == 0), valid=True,
                               status='passed' if g['exit_code'] == 0 else 'failed')
        except EvalError as e:
            row.update(status='invalid_candidate', valid=True, diagnostic=str(e))
    row['latency_seconds'] = time.monotonic()-started
    return row


def run(path, output, resume=False):
    path, s, tasks, pricing, seal = load_suite(path)
    approval = read_json(path.parent / 'approval.json')
    require(approval.get('seal') == seal, 'Suite changed or is not approved. Validate, review, and approve it first.')
    output = Path(output).resolve()
    require(not any(output.is_relative_to(t['root']) or t['root'].is_relative_to(output) for t in tasks), 'Run output must not overlap task roots')
    if output.exists() and any(output.iterdir()):
        require(resume, 'Output exists; use --resume for the same sealed run, or a new directory')
        require(read_json(output / 'run.json').get('seal') == seal, 'Resume seal mismatch')
    output.mkdir(parents=True, exist_ok=True)
    lock = output / '.run-lock'
    try:
        lock.mkdir()
    except FileExistsError as e:
        raise EvalError('Run is locked. Verify the previous process has stopped before manually removing .run-lock.') from e
    try:
        cells = schedule(s, tasks)
        if not (output / 'run.json').exists():
            from .report import describe_tasks
            write_json(output / 'run.json', {'schema_version': 1, 'seal': seal, 'suite': s, 'pricing': pricing,
                       'approval': approval, 'schedule': cells, 'created_at': now(),
                       'task_summaries': describe_tasks(tasks),
                       'host': {'platform': platform.platform(), 'python': platform.python_version()},
                       'state': 'running', 'simulation': False})
        pf = preflight(s)
        write_json(output / 'preflight.json', pf)
        lookup = {t['spec']['id']: t for t in tasks}
        rows = []
        for c in cells:
            d = output / 'attempts' / c['cell_id']
            f = d / 'result.json'
            if f.exists():
                row = read_json(f)
                require(all(row.get(k) == c[k] for k in c), 'Stored result cell identity mismatch')
                require(read_json(d / 'result.sha256.json').get('sha256') == digest(row), 'Stored result was modified')
                rows.append(row)
            elif (d / 'started.json').exists():
                # A crash may have spent money. Preserve it and do not silently rerun.
                row = {**c, **normalize(c['provider'], (d / 'events.jsonl').read_text() if (d / 'events.jsonl').exists() else '', c['model'], pricing),
                       'completion': 0, 'valid': False, 'status': 'interrupted', 'simulation': False,
                       'difficulty': lookup[c['task_id']]['spec']['difficulty'], 'execution_mode': s['execution']['mode']}
                write_json(f, row)
                write_json(d / 'result.sha256.json', {'sha256': digest(row)})
                rows.append(row)
        done = {r['cell_id'] for r in rows}
        stop_reason = None
        for c in cells:
            if c['cell_id'] in done:
                continue
            if s['limits']['spend_stop_usd'] is not None and any(r.get('cost_upper_usd') is None and not r.get('not_started') for r in rows):
                stop_reason = 'unknown_spend'
                break
            spent = sum(r.get('cost_upper_usd') or 0 for r in rows)
            if s['limits']['spend_stop_usd'] is not None and spent >= s['limits']['spend_stop_usd']:
                stop_reason = 'spend_threshold'
                break
            require(load_suite(path)[4] == seal, 'Sealed inputs changed during execution')
            d = output / 'attempts' / c['cell_id']
            write_json(d / 'started.json', {'cell': c, 'started_at': now()})
            row = attempt(c, lookup[c['task_id']], s, pricing, d, pf[c['provider']])
            write_json(d / 'result.json', row)
            write_json(d / 'result.sha256.json', {'sha256': digest(row)})
            rows.append(row)
            print(f"{len(rows)}/{len(cells)} {c['task_id']} {c['model']} {c['effort']}: {row['status']}", flush=True)
            write_json(output / 'results.json', {'schema_version': 1, 'rows': rows})
            if row['status'] == 'interrupted':
                stop_reason = 'interrupted'
                break
        run_info = read_json(output / 'run.json')
        run_info.update(state='stopped' if stop_reason else 'complete', stop_reason=stop_reason,
                        updated_at=now(), completed_cells=len(rows), scheduled_cells=len(cells))
        write_json(output / 'run.json', run_info)
        write_json(output / 'results.json', {'schema_version': 1, 'rows': rows})
        return run_info
    finally:
        lock.rmdir()
