"""A small edit-and-test gate in the same native launch context as customer runs."""
import copy
import json
import sys
import time
from pathlib import Path

from .core import digest, now, write_json, read_json, require
from . import rate_limits


def probe_task(root, docker=False):
    root = Path(root)
    (root / 'baseline').mkdir(parents=True)
    (root / 'grader').mkdir()
    (root / 'baseline/value.txt').write_text('1\n')
    script = "from pathlib import Path\nassert Path('value.txt').read_text().strip() == '2'\nPath('checked.txt').write_text('ok\\n')\n"
    (root / 'baseline/check.py').write_text(script)
    python = 'python3' if docker else sys.executable
    import shlex
    (root / 'instruction.md').write_text(
        'Execution readiness check. Edit value.txt to contain 2 followed by a newline. '
        f'Run {shlex.quote(python)} check.py in the workspace; it asserts the new value and writes checked.txt. '
        'Do not modify check.py. This checks whether editing and shell execution work here.')
    (root / 'grader/verify.py').write_text(
        "from pathlib import Path\nimport sys\np=Path(sys.argv[1])\n"
        "ok=(p/'value.txt').read_text().strip()=='2' and (p/'checked.txt').is_file() and (p/'checked.txt').read_text().strip()=='ok'\n"
        "raise SystemExit(0 if ok else 1)\n")
    return {'root': root, 'spec': {'id': 'execution-readiness', 'difficulty': 'easy',
            'use_case': 'Native edit and shell execution', 'allowed_paths': ['value.txt', 'checked.txt'],
            'grader': [python, '{grader}/verify.py', '{candidate}']}}


def shell_check_ran(row, folder):
    trials = row.get('retry_attempts', [])
    directory = folder / trials[-1]['directory'] if trials else folder
    path = directory / 'events.jsonl'
    bash = set()
    if not path.exists():
        return False
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        item = event.get('item') or {}
        if (event.get('type') == 'item.completed' and item.get('type') == 'command_execution'
                and item.get('exit_code') == 0 and 'check.py' in str(item.get('command', ''))):
            return True
        content = (event.get('message') or {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if event.get('type') == 'assistant' and block.get('type') == 'tool_use' and block.get('name') == 'Bash' and 'check.py' in str(block.get('input', {}).get('command', '')):
                bash.add(block.get('id'))
            if event.get('type') == 'user' and block.get('type') == 'tool_result' and block.get('tool_use_id') in bash and not block.get('is_error'):
                return True
    return False


def saved_receipts(output):
    receipts = []
    for path in sorted((Path(output) / 'execution-checks').glob('receipt-*.json')):
        receipt = read_json(path)
        for row in receipt['rows']:
            folder = path.parent / row['probe_directory']
            require(folder.resolve().is_relative_to(path.parent.resolve()), 'Execution check path escapes receipts')
            require(digest(read_json(folder/'result.json')) == read_json(folder/'result.sha256.json')['sha256'], 'Execution check result changed')
            # Metadata outside the signed native row points back to the retained evidence.
            stored = read_json(folder/'result.json')
            require({k:v for k,v in row.items() if k != 'probe_directory'} == stored, 'Execution check receipt changed')
            rate_limits.records(folder, stored)
        receipts.append(receipt)
    return receipts


def check(suite, pricing, output, preflight, slots, cooldown, max_retries, base_delay):
    """New receipt on each pending customer-run invocation; never mutate prior probes."""
    root = Path(output)
    checks = root / 'execution-checks'
    checks.mkdir(exist_ok=True)
    receipt = {'created_at': now(), 'ok': True, 'rows': [],
               'scope': 'First configured model and effort per selected provider; not all-model capability proof.'}
    probe_suite = copy.deepcopy(suite)
    probe_suite['limits']['agent_seconds'] = min(120, suite['limits']['agent_seconds'])
    probe_suite['limits']['grader_seconds'] = min(30, suite['limits']['grader_seconds'])
    probe_suite['limits']['claude_max_turns'] = min(8, suite['limits']['claude_max_turns'])
    index = len(list(checks.glob('receipt-*.json'))) + 1
    receipt_path = checks / f'receipt-{index:04d}.json'
    # Persist before making a call: a crash is visible and never silently reused as a pass.
    write_json(receipt_path, dict(receipt, ok=False, state='started'))
    seen = set()
    for lane in suite['matrix']:
        if lane['provider'] in seen:
            continue
        seen.add(lane['provider'])
        provider = lane['provider']
        print(f"Execution check: {provider}:{lane['model']} / {lane['efforts'][0]} (separate from scored tasks).", flush=True)
        folder = checks / f'{index:04d}-{provider}'
        task = probe_task(folder / 'task', suite['execution']['mode'] == 'docker')
        cell = {'cell_id': f'check-{index}-{provider}', 'task_id': task['spec']['id'],
                'provider': provider, 'model': lane['model'], 'effort': lane['efforts'][0], 'repeat': 1}
        lease = None
        while lease is None:
            if (root / 'stop-requested.json').exists():
                receipt.update(ok=False, state='paused')
                write_json(receipt_path, receipt)
                return receipt
            lease = slots.acquire()
            if lease is None:
                time.sleep(.1)
        try:
            row = rate_limits.attempt(cell, task, probe_suite, pricing, folder, preflight[provider],
                                      max_retries=max_retries, base_delay=base_delay, cooldown=cooldown)
        finally:
            slots.release(lease)
        write_json(folder / 'result.json', row)
        write_json(folder / 'result.sha256.json', {'sha256': digest(row)})
        # Grade alone is insufficient if native helper failures were recovered or hidden.
        ok = row.get('completion') == 1 and not row.get('runtime_diagnostics') and shell_check_ran(row, folder)
        receipt['rows'].append(dict(row, probe_directory=folder.name))
        receipt['ok'] = receipt['ok'] and ok
        receipt['state'] = 'started' if receipt['ok'] else 'blocked'
        write_json(receipt_path, receipt)
        if not ok:
            break
        stop = suite['limits']['spend_stop_usd']
        if stop is not None and (row.get('cost_upper_usd') is None or sum(r.get('cost_upper_usd') or 0 for r in receipt['rows']) >= stop):
            receipt.update(ok=False, state='spend_stop')
            write_json(receipt_path, receipt)
            break
    if receipt['ok']:
        receipt['state'] = 'passed'
        write_json(receipt_path, receipt)
    return receipt
