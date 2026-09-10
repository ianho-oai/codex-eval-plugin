"""Fixed result model, summaries, CSV, and localhost-only dashboard serving."""
import csv
import io
import hashlib
import json
import math
import os
import re
import statistics
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .core import DATA, EvalError, child, digest, load_suite, read_json, require, write_json


def legacy_summary(spec):
    workflow = spec.get('use_case') or 'the recorded development workflow'
    rationale = (spec.get('difficulty_rationale') or 'The developer must implement the requested behavior and pass the automated checks').strip().rstrip('.')
    return f"This task tests {workflow[0].lower() + workflow[1:]}. {rationale}."


def describe_tasks(tasks):
    return [{'task_id': task['spec']['id'], 'difficulty': task['spec']['difficulty'],
             'use_case': task['spec']['use_case'],
             'description': (task['root'] / 'instruction.md').read_text().strip(),
             'human_summary': task['spec'].get('human_summary') or legacy_summary(task['spec']),
             'difficulty_rationale': task['spec'].get('difficulty_rationale', '')}
            for task in tasks]


def task_summaries(root, run, rows):
    if 'task_summaries' in run:
        return [dict(t, human_summary=t.get('human_summary') or legacy_summary(t)) for t in run['task_summaries']]
    # Older runs did not snapshot descriptions. Use only a matching nearby suite;
    # descriptive metadata never alters signed attempt records or their scores.
    candidates = [root / 'suite.json', root.parent / 'suite.json']
    candidates.extend(sorted(root.parent.glob('*/suite.json')))
    for path in candidates:
        try:
            if path.is_file() and read_json(path) == run.get('suite'):
                _, _, tasks, _, _ = load_suite(path)
                return [dict(t, metadata_source='local_task_definition') for t in describe_tasks(tasks)]
        except (EvalError, OSError, ValueError, KeyError, TypeError):
            continue
    if run.get('simulation'):
        tasks = [{'spec': read_json(p / 'task.json'), 'root': p}
                 for p in sorted((DATA / 'examples').iterdir()) if (p / 'task.json').is_file()]
        return describe_tasks(tasks)
    return list({(r['task_id'], r.get('difficulty')):
                 {'task_id': r['task_id'], 'difficulty': r.get('difficulty'),
                  'use_case': r.get('use_case') or 'Not recorded',
                  'human_summary': legacy_summary(r),
                  'description': 'Task description was not saved with this run.'}
                 for r in rows}.values())


def correct_codex_cache_cost(row, folder, pricing):
    """Derive corrected display costs without rewriting signed execution evidence."""
    if row.get('provider') != 'codex' or row.get('not_started'):
        return row
    trials = row.get('retry_attempts', [])
    if trials:
        corrected = [correct_codex_cache_cost(read_json(child(folder, t['directory'])/'result.json'),
                                             child(folder, t['directory']), pricing) for t in trials]
        if not any(r.get('cost_adjustment') for r in corrected):
            return row
        result = dict(row)
        for key in ('cost_usd', 'cost_lower_usd', 'cost_upper_usd', 'cache_write_tokens'):
            values = [r.get(key) for r in corrected]
            result[key] = sum(values) if all(v is not None for v in values) else None
        result['known_cost_usd'] = sum(r.get('cost_usd') or 0 for r in corrected)
        result['known_cost_upper_usd'] = sum(r.get('cost_upper_usd') or 0 for r in corrected)
        result['cost_evidence'] = [r.get('cost_evidence') for r in corrected]
    else:
        events_path = folder/'events.jsonl'
        if row.get('cache_write_tokens') is not None or not events_path.is_file():
            return row
        from .telemetry import normalize
        raw = events_path.read_text()
        parsed = normalize('codex', raw, row['model'], pricing)
        if parsed['cache_write_tokens'] is None or parsed['cost_usd'] is None:
            return row
        # A correction must describe the same signed token totals, not another call.
        if any(parsed[k] != row.get(k) for k in ('input_tokens', 'output_tokens', 'cache_read_tokens')):
            return row
        result = dict(row)
        for key in ('cost_usd', 'cost_lower_usd', 'cost_upper_usd', 'cache_write_tokens'):
            result[key] = parsed[key]
        result['cost_evidence'] = {'events_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                                   'pricing_sha256': digest(pricing)}
    result.update(recorded_cost_usd=row.get('cost_usd'), cost_adjustment='codex_cache_write_field',
                  cost_source='corrected_rate_card_estimate',
                  cost_note='Display estimate corrected from native cache_write_input_tokens using the original run rate card. Signed run results are unchanged; request-level long-context pricing remains uncertain.')
    return result


def reset_version_errors(root, run, rows):
    """Apply explicit reset receipts to views without rewriting original evidence."""
    receipt = root / 'reset-version-errors.json'
    if not receipt.exists():
        return run, rows, []
    receipt = read_json(receipt)
    require(receipt.get('reason') == 'cli_version_incompatible' and receipt.get('requested_by'),
            'Invalid version-error reset receipt')
    lookup = {r['cell_id']: r for r in rows}
    removed = []
    for entry in receipt['attempts']:
        row = lookup.get(entry['cell_id'])
        require(row is not None and digest(row) == entry['result_sha256'], 'Reset result identity mismatch')
        require(row.get('provider') == 'claude' and row.get('status') == 'provider_error'
                and row.get('completion') == 0 and row.get('valid') is False,
                'Only confirmed provider version errors can be reset')
        events = child(root / 'attempts' / row['cell_id'], entry['events_path']).read_bytes()
        require(hashlib.sha256(events).hexdigest() == entry['events_sha256'], 'Reset evidence changed')
        messages = [json.loads(line) for line in events.decode().splitlines() if line.strip()]
        require(any(m.get('type') == 'result' and m.get('is_error') is True and
                    re.search(r'Claude Code [\d.]+ does not support this model; version [\d.]+ or newer is required', str(m.get('result', '')))
                    for m in messages), 'Reset requires a native CLI version error')
        removed.append(dict(row, reset_reason=receipt['reason'], reset_at=receipt.get('reset_at')))
    ids = {r['cell_id'] for r in removed}
    require(len(ids) == len(removed), 'Duplicate reset attempt')
    view = dict(run, schedule=[c for c in run.get('schedule', []) if c['cell_id'] not in ids])
    return view, [r for r in rows if r['cell_id'] not in ids], removed


def exclude_models(root, run, rows):
    receipt = root / 'excluded-models.json'
    if not receipt.exists():
        return run, rows, []
    receipt = read_json(receipt)
    require(receipt.get('requested_by') and receipt.get('reason'), 'Model exclusion requires a reason and requester')
    excluded = {(m['provider'], m['model']) for m in receipt['models']}
    matches = lambda r: (r.get('provider'), r.get('model')) in excluded
    view = dict(run, schedule=[c for c in run.get('schedule', []) if not matches(c)])
    return view, [r for r in rows if not matches(r)], [dict(r, exclusion_reason=receipt['reason']) for r in rows if matches(r)]


def dataset(root):
    root = Path(root)
    run = read_json(root / 'run.json')
    rows = read_json(root / 'results.json')['rows'] if (root / 'results.json').exists() else []
    for r in rows:
        f = root / 'attempts' / r['cell_id'] / 'result.json'
        if f.exists():
            require(read_json(f) == r and read_json(f.parent / 'result.sha256.json').get('sha256') == digest(r), 'Result integrity check failed')
            for trial in r.get('retry_attempts', []):
                folder = child(f.parent, trial['directory'])
                original = read_json(folder / 'result.json')
                require(digest(original) == trial['sha256'] and read_json(folder / 'result.sha256.json').get('sha256') == trial['sha256'], 'Retry result integrity check failed')
        else:
            require(run.get('simulation') is True and r.get('simulation') is True, 'Result artifact missing')
    descriptions = task_summaries(root, run, rows)
    run, rows, reset_rows = reset_version_errors(root, run, rows)
    run, rows, excluded_rows = exclude_models(root, run, rows)
    rows = [correct_codex_cache_cost(r, root/'attempts'/r['cell_id'], run.get('pricing', {})) for r in rows]
    return {'schema_version': 1, 'run': run, 'rows': rows, 'reset_rows': reset_rows, 'excluded_rows': excluded_rows, 'tasks': descriptions,
            'averages': average_attempts(rows, run), 'summary': summarize(rows, len(run.get('schedule', [])))}


def dashboard_dataset(roots, *, scope=False):
    if isinstance(roots, (str, Path)):
        roots = [roots]
    discovered = []
    for value in roots:
        root = Path(value).resolve()
        if (root/'run.json').is_file():
            # Existing per-run commands also show the whole evaluation workspace.
            workspace = next((p for p in root.parents if p.name == 'evaluations'), None)
            if workspace and not scope and not read_json(root/'run.json').get('simulation'):
                root = workspace
            else:
                discovered.append(root)
                continue
        require(root.is_dir(), f'Dashboard directory does not exist: {root}')
        for directory, directories, files in os.walk(root, followlinks=False):
            directories[:] = sorted(d for d in directories if d not in {'.git', 'node_modules', '.venv', '__pycache__'})
            if 'run.json' not in files:
                continue
            manifest = Path(directory)/'run.json'
            if not manifest.resolve().is_relative_to(root):
                continue
            run = read_json(manifest)
            if not isinstance(run, dict) or not isinstance(run.get('schedule'), list) or not isinstance(run.get('suite'), dict):
                continue
            directories[:] = []  # Candidate workspaces can contain their own run.json files.
            if not run.get('simulation'):
                discovered.append(manifest.parent)
    roots = list(dict.fromkeys(discovered))
    require(bool(roots), 'No live runs found. Run an evaluation first, or pass a demo run directory explicitly.')
    if len(roots) == 1:
        return dataset(roots[0])
    rows, sources, stopped, tasks, averages, reset_rows, excluded_rows = [], [], [], [], [], [], []
    scheduled = 0
    for root in roots:
        data = dataset(root)  # Verify every original artifact before combining views.
        run = data['run']
        source = str(root)
        sources.append({'id': source, 'name': run['suite']['name'],
                        'state': run.get('state'), 'execution': run['suite'].get('execution')})
        rows.extend(dict(row, source_run=source) for row in data['rows'])
        reset_rows.extend(dict(row, source_run=source) for row in data.get('reset_rows', []))
        excluded_rows.extend(dict(row, source_run=source) for row in data.get('excluded_rows', []))
        tasks.extend(dict(task, source_run=source) for task in data['tasks'])
        averages.extend(dict(row, source_run=source) for row in data['averages'])
        scheduled += data['summary']['scheduled']
        if run.get('stop_reason'):
            stopped.append(f"{run['suite']['name']}: {run['stop_reason']}")
    return {'schema_version': 1, 'run': {'suite': {'name': f'{len(sources)} runs · combined results'},
            'state': 'combined', 'sources': sources, 'stop_reason': '; '.join(stopped) or None,
            'comparison_note': 'Separate runs are shown together. Tasks, settings, and environments may differ. Displaying runs together does not establish a controlled benchmark.'},
            'rows': rows, 'reset_rows': reset_rows, 'excluded_rows': excluded_rows, 'tasks': tasks, 'averages': averages, 'summary': summarize(rows, scheduled)}


MEAN_FIELDS = ('cost_usd', 'latency_seconds', 'input_tokens', 'output_tokens', 'cache_read_tokens')


def average_attempts(rows, run):
    key = lambda r: (r.get('task_id'), r.get('provider'), r.get('model'), r.get('effort'))
    scheduled, groups = {}, {}
    for cell in run.get('schedule', []):
        scheduled[key(cell)] = scheduled.get(key(cell), 0) + 1
    for row in rows:
        groups.setdefault(key(row), []).append(row)
    averages = []
    for identity, group in groups.items():
        first = group[0]
        expected = scheduled.get(identity, run.get('suite', {}).get('repeats', len(group)))
        successes = sum(r.get('completion') == 1 for r in group)
        point = {k: first.get(k) for k in ('task_id', 'difficulty', 'provider', 'model', 'effort', 'execution_mode')}
        point.update(attempts=len(group), expected_attempts=expected, successes=successes,
                     completion=int(successes == expected and len(group) == expected),
                     status='pending' if len(group) < expected else 'passed' if successes == len(group) else 'failed',
                     valid=all(r.get('valid') for r in group), simulation=bool(run.get('simulation')))
        for field in MEAN_FIELDS:
            values = [r.get(field) for r in group]
            point[field] = statistics.mean(values) if all(type(v) in (int, float) and math.isfinite(v) for v in values) else None
        averages.append(point)
    return averages


def summarize(rows, scheduled):
    groups = {}
    for r in rows:
        key = (r['provider'], r['model'], r['effort'])
        groups.setdefault(key, []).append(r)
    summary = []
    for (provider, model, effort), group in sorted(groups.items()):
        valid = [r for r in group if r.get('valid')]
        wins = sum(r['completion'] for r in valid)
        costs = [r.get('cost_usd') for r in group]
        known = [x for x in costs if x is not None]
        latencies = [r['latency_seconds'] for r in group if r.get('latency_seconds') is not None]
        n = len(valid)
        # Wilson 95% interval; useful with repeats, never implied precision on one sample.
        z = 1.96
        p = wins/n if n else None
        center = (p+z*z/(2*n))/(1+z*z/n) if n else None
        half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n) if n else None
        summary.append({'provider': provider, 'model': model, 'effort': effort, 'attempts': len(group),
                        'scorable': n, 'infrastructure_invalid': len(group)-n, 'successes': wins,
                        'success_rate_all': wins/len(group), 'success_rate_scorable': p,
                        'success_rate_95_interval': [max(0, center-half), min(1, center+half)] if n else None,
                        'known_cost_usd': sum(known), 'cost_missing': len(costs)-len(known),
                        'cost_per_success_usd': sum(known)/wins if wins and len(known) == len(costs) else None,
                        'median_latency_seconds': statistics.median(latencies) if latencies else None})
    return {'scheduled': scheduled, 'attempted': len(rows), 'pending': max(0, scheduled-len(rows)), 'groups': summary}


CSV_FIELDS = ['source_run', 'task_id', 'difficulty', 'provider', 'model', 'effort', 'repeat', 'completion', 'status',
              'valid', 'simulation', 'execution_mode', 'latency_seconds', 'agent_seconds', 'grader_seconds',
              'input_tokens', 'uncached_input_tokens', 'output_tokens', 'cache_read_tokens',
              'cache_write_tokens', 'reasoning_tokens', 'turns', 'turn_unit', 'tool_calls', 'cost_usd',
              'cost_lower_usd', 'cost_upper_usd', 'cost_source', 'cost_note', 'recorded_cost_usd', 'cost_adjustment',
              'retry_count', 'retry_wait_seconds', 'known_cost_usd', 'rate_limit_cost_incomplete', 'rate_limit_retries_exhausted']


def csv_text(rows):
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction='ignore')
    w.writeheader()
    for r in rows:
        # Prevent formula execution when importing customer-controlled strings into Excel.
        w.writerow({k: "'"+v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v for k, v in r.items()})
    return f.getvalue()


def report(root):
    d = dataset(root)
    write_json(Path(root) / 'summary.json', d['summary'])
    write_json(Path(root) / 'averages.json', {'rows': d['averages']})
    (Path(root) / 'results.csv').write_text(csv_text(d['rows']))
    return d['summary']


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, root, scope=False, **kwargs):
        self.root = root
        self.scope = scope
        super().__init__(*args, **kwargs)

    def log_message(self, *args):
        pass

    def do_GET(self):
        host = self.headers.get('Host', '').split(':')[0]
        if host not in ('127.0.0.1', 'localhost'):
            self.send_error(403)
            return
        path = urlparse(self.path).path
        try:
            if path == '/api/results':
                data, mime = json.dumps(dashboard_dataset(self.root, scope=self.scope)).encode(), 'application/json'
            elif path == '/results.csv':
                data, mime = csv_text(dashboard_dataset(self.root, scope=self.scope)['rows']).encode(), 'text/csv'
            elif path in ('/', '/app.js', '/medians.js', '/style.css'):
                p = DATA / 'web' / {'/': 'index.html', '/app.js': 'app.js', '/medians.js': 'medians.js', '/style.css': 'style.css'}[path]
                data, mime = p.read_bytes(), {'/': 'text/html', '/app.js': 'text/javascript', '/medians.js': 'text/javascript', '/style.css': 'text/css'}[path]
            else:
                self.send_error(404)
                return
        except EvalError:
            self.send_error(409, 'Run data unavailable or failed integrity check')
            return
        self.send_response(200)
        self.send_header('Content-Type', mime+'; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)


def serve(root, port, scope=False):
    roots = [root] if isinstance(root, (str, Path)) else root
    roots = [Path(p).resolve() for p in roots]
    dashboard_dataset(roots, scope=scope)
    server = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, root=roots, scope=scope))
    print(f'Dashboard: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
