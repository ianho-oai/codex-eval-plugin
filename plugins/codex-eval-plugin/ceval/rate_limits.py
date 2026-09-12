"""Bounded retries for explicit native transient failures, retaining each trial."""
import json
import fcntl
import re
import time
from pathlib import Path

from .core import read_json, write_json, digest, require, now
from . import runner as engine

MAX_RETRIES = 3
BASE_DELAY = 30
SUM_FIELDS = ('cost_usd', 'cost_lower_usd', 'cost_upper_usd', 'input_tokens',
              'uncached_input_tokens', 'output_tokens', 'cache_read_tokens',
              'cache_write_tokens', 'reasoning_tokens', 'turns', 'tool_calls',
              'agent_seconds', 'grader_seconds', 'provider_duration_ms',
              'provider_api_duration_ms', 'invalid_event_lines')


def messages(directory):
    """Inspect only native error fields, never task text or model/tool messages."""
    path = Path(directory) / 'events.jsonl'
    if not path.exists():
        return []
    found = []
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get('type')
        if kind == 'turn.completed' or (kind == 'result' and event.get('subtype') == 'success' and not event.get('is_error')):
            found.clear()  # Native recovery already succeeded; do not repeat its work.
        elif kind in ('error', 'turn.failed'):
            found.append(json.dumps(event.get('error', event.get('message', event))))
        elif kind == 'result' and event.get('is_error'):
            found.append(json.dumps(event.get('errors', event.get('error', event.get('result', '')))))
    return found


def transient_reason(row, directory):
    if row.get('status') != 'provider_error':
        return None
    errors = ' '.join(messages(directory)).lower()
    if any(term in errors for term in ('insufficient_quota', 'credit balance', 'billing hard limit',
                                      'invalid_api_key', 'authentication_error', 'permission_denied',
                                      'does not exist', 'model_not_found', 'not have access')):
        return None
    if re.search(r'rate[ _-]?limit|too many requests|\b429\b', errors):
        return 'rate_limit'
    if re.search(r'\b(?:model|server|service) is (?:temporarily )?at capacity\b|'
                 r'\boverloaded_error\b|\b(?:server|service) (?:is )?(?:temporarily )?overloaded\b', errors):
        return 'capacity'
    return None


def is_rate_limited(row, directory):
    return transient_reason(row, directory) == 'rate_limit'


class Cooldown:
    """Provider-wide backoff shared by threads and processes using the same pool."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _state(self, provider, delay=None):
        require(provider in ('codex', 'claude'), 'Invalid cooldown provider')
        with (self.path / 'cooldown.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            file = self.path / f'cooldown-{provider}.json'
            state = read_json(file) if file.exists() else {}
            until = state.get('until', 0)
            if delay is not None:
                until = max(until, time.time() + delay)
                write_json(file, {'until': until, 'provider': provider, 'updated_at': now()})
            return max(0, until - time.time())

    def remaining(self, provider):
        return self._state(provider)

    def defer(self, provider, delay):
        return self._state(provider, delay)

    def wait(self, provider, stop_file):
        before = time.monotonic()
        while self.remaining(provider) > 0:
            if stop_file.exists():
                return time.monotonic() - before, True
            time.sleep(min(.25, self.remaining(provider)))
        return time.monotonic() - before, stop_file.exists()


def retry_delay(directory, retry_number, base_delay):
    hints = []
    for message in messages(directory):
        for value, unit in re.findall(r'try again in\s+([\d.]+)\s*(ms|milliseconds?|s|seconds?|m|minutes?)\b', message, re.I):
            scale = .001 if unit.lower().startswith('m') and unit.lower() not in ('m','minute','minutes') else 60 if unit.lower() in ('m','minute','minutes') else 1
            hints.append(float(value) * scale)
        for value in re.findall(r'retry[_-]after["\s:]+([\d.]+)', message, re.I):
            hints.append(float(value))
    return min(3600, max([min(base_delay * 2 ** (retry_number - 1), 300), *hints]))


def records(directory, previous=None):
    directory = Path(directory)
    result = []
    if previous and previous.get('retry_attempts'):
        for item in previous['retry_attempts']:
            folder = directory / item['directory']
            require(folder.resolve().is_relative_to(directory.resolve()), 'Retry path escapes attempt')
            row = read_json(folder / 'result.json')
            require(digest(row) == item['sha256'], 'Stored retry result was modified')
            result.append((row, folder))
    elif previous:
        # Archive the exact signed legacy row. Its native logs remain at the root.
        folder = directory / 'retries' / '000'
        write_json(folder / 'result.json', previous)
        write_json(folder / 'result.sha256.json', {'sha256': digest(previous)})
        result.append((previous, folder))
    else:
        for folder in sorted((directory / 'retries').glob('[0-9][0-9][0-9]')):
            if (folder / 'result.json').exists():
                row = read_json(folder / 'result.json')
                require(read_json(folder / 'result.sha256.json')['sha256'] == digest(row), 'Stored retry result was modified')
                result.append((row, folder))
    return result


def rollup(trials, directory, wait_seconds, exhausted=False, paused=False):
    rows = [r for r, _ in trials]
    final = dict(rows[-1])
    final['runtime_diagnostics'] = list(dict.fromkeys(
        code for row in rows for code in row.get('runtime_diagnostics', [])))
    for field in SUM_FIELDS:
        values = [r.get(field) for r in rows]
        final[field] = sum(values) if all(v is not None for v in values) else None
    latencies = [r.get('latency_seconds') for r in rows]
    final['latency_seconds'] = sum(latencies) + wait_seconds if all(v is not None for v in latencies) else None
    final['retry_count'] = len(rows) - 1
    final['retry_wait_seconds'] = wait_seconds
    final['known_cost_usd'] = sum(r.get('cost_usd') or 0 for r in rows)
    final['known_cost_upper_usd'] = sum(r.get('cost_upper_usd') or 0 for r in rows)
    unknown = [r for r in rows if r.get('cost_upper_usd') is None and not r.get('not_started')]
    final['rate_limit_cost_incomplete'] = bool(unknown) and all(r.get('rate_limited') for r in unknown)
    final['transient_cost_incomplete'] = bool(unknown) and all(r.get('transient_reason') or r.get('rate_limited') for r in unknown)
    final['transient_retries_exhausted'] = exhausted
    final['rate_limit_retries_exhausted'] = exhausted and bool(rows[-1].get('rate_limited'))
    final['retry_paused'] = paused
    final['retry_attempts'] = [{'directory': str(folder.relative_to(directory)), 'sha256': digest(row),
                              'status': row['status']} for row, folder in trials]
    if len(rows) > 1:
        final['model_usage_by_trial'] = [r.get('model_usage', {}) for r in rows]
        final['model_usage'] = {}
        final['cost_source'] = 'retry_aggregate' if final['cost_usd'] is not None else 'incomplete_retry_usage'
        final['cost_note'] = 'Includes all reported trial costs. Missing retry usage remains unknown.'
    final['telemetry_complete'] = all(final.get(k) is not None for k in ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cost_usd'))
    return final


def attempt(cell, task, suite, pricing, directory, preflight_result, *, previous=None,
            max_retries=MAX_RETRIES, base_delay=BASE_DELAY, cooldown=None):
    directory = Path(directory)
    cooldown = cooldown or Cooldown(directory.parent.parent / 'cooldowns')
    stop_file = directory.parent.parent / 'stop-requested.json'
    trials = records(directory, previous)
    wait_seconds = previous.get('retry_wait_seconds', 0) if previous else 0
    if previous and not previous.get('retry_attempts') and transient_reason(previous, directory):
        # Store the classification beside, without changing the archived legacy row.
        old, folder = trials[-1]
        reason = transient_reason(previous, directory)
        old = dict(old, rate_limited=reason == 'rate_limit', transient_reason=reason)
        folder = directory / 'retries' / 'legacy-classified'
        write_json(folder / 'result.json', old)
        write_json(folder / 'result.sha256.json', {'sha256': digest(old)})
        trials[-1] = (old, folder)
    while True:
        if trials:
            last, last_dir = trials[-1]
            if not (last.get('transient_reason') or last.get('rate_limited')):
                return rollup(trials, directory, wait_seconds)
            delay = retry_delay(directory if previous and len(trials) == 1 and not previous.get('retry_attempts') else last_dir, len(trials), base_delay)
            cooldown.defer(cell['provider'], delay)
            if len(trials) - 1 >= max_retries:
                return rollup(trials, directory, wait_seconds, exhausted=True)
            if (directory.parent.parent / 'stop-requested.json').exists():
                return rollup(trials, directory, wait_seconds, paused=True)
            write_json(directory / 'retry-state.json', {'state':'backoff','retry':len(trials),'delay_seconds':delay,'updated_at':now()})
            print(f"Transient provider error: {cell['model']} / {cell['task_id']}; retry {len(trials)}/{max_retries} after shared cooldown.", flush=True)
        waited, stopped = cooldown.wait(cell['provider'], stop_file)
        wait_seconds += waited
        if stopped:
            if trials:
                return rollup(trials, directory, wait_seconds, paused=True)
            return {**cell, **engine.normalize(cell['provider'], '', cell['model'], pricing),
                    'status': 'interrupted', 'completion': 0, 'valid': False,
                    'simulation': False, 'not_started': True, 'retry_paused': True}
        folder = directory / 'retries' / f'{len(trials):03d}'
        if (folder / 'result.json').exists():
            row = read_json(folder / 'result.json')
            require(read_json(folder / 'result.sha256.json')['sha256'] == digest(row), 'Stored retry result was modified')
            trials.append((row, folder))
            continue
        if (folder / 'started.json').exists():
            # A crash with unreported usage is not evidence of a rate limit.
            row = {**cell, **engine.normalize(cell['provider'], '', cell['model'], pricing),
                   'status':'interrupted','completion':0,'valid':False,'simulation':False}
            write_json(folder / 'result.json', row)
            write_json(folder / 'result.sha256.json', {'sha256':digest(row)})
            trials.append((row, folder))
            return rollup(trials, directory, wait_seconds)
        write_json(folder / 'started.json', {'cell':cell,'started_at':now()})
        row = engine.attempt(cell, task, suite, pricing, folder, preflight_result)
        row['transient_reason'] = transient_reason(row, folder)
        row['rate_limited'] = row['transient_reason'] == 'rate_limit'
        write_json(folder / 'result.json', row)
        write_json(folder / 'result.sha256.json', {'sha256':digest(row)})
        trials.append((row, folder))
        write_json(directory / 'retry-state.json', {'state':row['transient_reason'] or 'finished','trials':len(trials),'updated_at':now()})
