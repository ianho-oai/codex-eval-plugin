"""Fixed result model, summaries, CSV, and localhost-only dashboard serving."""
import csv
import io
import json
import math
import statistics
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .core import DATA, EvalError, digest, read_json, require, write_json


def dataset(root):
    root = Path(root)
    run = read_json(root / 'run.json')
    rows = read_json(root / 'results.json')['rows'] if (root / 'results.json').exists() else []
    for r in rows:
        f = root / 'attempts' / r['cell_id'] / 'result.json'
        if f.exists():
            require(read_json(f) == r and read_json(f.parent / 'result.sha256.json').get('sha256') == digest(r), 'Result integrity check failed')
        else:
            require(run.get('simulation') is True and r.get('simulation') is True, 'Result artifact missing')
    return {'schema_version': 1, 'run': run, 'rows': rows, 'summary': summarize(rows, len(run.get('schedule', [])))}


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


CSV_FIELDS = ['task_id', 'difficulty', 'provider', 'model', 'effort', 'repeat', 'completion', 'status',
              'valid', 'simulation', 'execution_mode', 'latency_seconds', 'agent_seconds', 'grader_seconds',
              'input_tokens', 'uncached_input_tokens', 'output_tokens', 'cache_read_tokens',
              'cache_write_tokens', 'reasoning_tokens', 'turns', 'turn_unit', 'tool_calls', 'cost_usd',
              'cost_lower_usd', 'cost_upper_usd', 'cost_source', 'cost_note']


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
    (Path(root) / 'results.csv').write_text(csv_text(d['rows']))
    return d['summary']


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, root, **kwargs):
        self.root = root
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
                data, mime = json.dumps(dataset(self.root)).encode(), 'application/json'
            elif path == '/results.csv':
                data, mime = csv_text(dataset(self.root)['rows']).encode(), 'text/csv'
            elif path in ('/', '/app.js', '/style.css'):
                p = DATA / 'web' / {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[path]
                data, mime = p.read_bytes(), {'/': 'text/html', '/app.js': 'text/javascript', '/style.css': 'text/css'}[path]
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


def serve(root, port):
    dataset(root)
    server = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, root=Path(root).resolve()))
    print(f'Dashboard: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
