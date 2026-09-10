"""A bounded, work-conserving queue with one writer and optional shared slots."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
import fcntl
import hashlib
import time

from .core import EvalError, require, read_json, write_json, digest, now
from . import runner as engine
from . import rate_limits


class Slots:
    """OS-held leases are released even if a worker process crashes."""
    def __init__(self, path, capacity):
        self.path = Path(path) if path else None
        self.capacity = capacity
        if self.path:
            self.path.mkdir(parents=True, exist_ok=True)
            with (self.path / 'config.lock').open('a') as guard:
                fcntl.flock(guard, fcntl.LOCK_EX)
                config = self.path / 'pool.json'
                if config.exists():
                    require(read_json(config)['capacity'] == capacity,
                            'Shared pool capacity differs; use the same --workers value or a different pool.')
                else:
                    write_json(config, {'capacity': capacity})

    def acquire(self):
        if not self.path:
            return True
        for i in range(self.capacity):
            lease = (self.path / f'{i}.lock').open('a')
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lease
            except BlockingIOError:
                lease.close()
        return None

    @staticmethod
    def release(lease):
        if lease is not True:
            lease.close()


def run(path, output, resume=False, workers=5, slot_pool=None, rate_limit_retries=3, retry_delay=30):
    require(type(workers) is int and 1 <= workers <= 32, 'workers must be between 1 and 32')
    require(type(rate_limit_retries) is int and 0 <= rate_limit_retries <= 10, 'rate-limit-retries must be between 0 and 10')
    require(type(retry_delay) in (int, float) and 0 <= retry_delay <= 3600, 'retry-delay must be between 0 and 3600 seconds')
    path, suite, tasks, pricing, seal = engine.load_suite(path)
    approval = read_json(path.parent / 'approval.json')
    require(approval.get('seal') == seal, 'Suite changed or is not approved. Validate, review, and approve it first.')
    output = Path(output).resolve()
    require(not any(output.is_relative_to(t['root']) or t['root'].is_relative_to(output) for t in tasks),
            'Run output must not overlap task roots')
    if output.exists() and any(output.iterdir()):
        require(resume, 'Output exists; use --resume for the same sealed run, or a new directory')
        require(read_json(output / 'run.json').get('seal') == seal, 'Resume seal mismatch')
    output.mkdir(parents=True, exist_ok=True)
    lock = output / '.run-lock'
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise EvalError('Run is locked; wait for the active runner to finish.') from error
    try:
        return _run(path, output, suite, tasks, pricing, seal, approval, workers, slot_pool, rate_limit_retries, retry_delay)
    finally:
        lock.rmdir()


def _run(path, output, suite, tasks, pricing, seal, approval, workers, slot_pool, rate_limit_retries, retry_delay):
    from .report import describe_tasks
    cells = engine.schedule(suite, tasks)
    lookup = {t['spec']['id']: t for t in tasks}
    slots = Slots(slot_pool, workers)
    manifest = output / 'run.json'
    info = read_json(manifest) if manifest.exists() else {
        'schema_version': 1, 'seal': seal, 'suite': suite, 'pricing': pricing,
        'approval': approval, 'schedule': cells, 'created_at': now(),
        'task_summaries': describe_tasks(tasks), 'simulation': False,
        'host': {'platform': engine.platform.platform(), 'python': engine.platform.python_version()}}
    info.setdefault('scheduling_history', []).append({
        'started_at': now(), 'workers': workers, 'slot_pool': str(Path(slot_pool).resolve()) if slot_pool else None,
        'scheduler_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'rate_limit_retries': rate_limit_retries, 'retry_delay': retry_delay,
        'retry_policy_sha256': hashlib.sha256(Path(rate_limits.__file__).read_bytes()).hexdigest(),
        'policy': 'Refill on completion; drain active attempts on stop. Concurrent latency may include host contention.'})
    info.update(state='running', stop_reason=None)
    write_json(manifest, info)
    pf = engine.preflight(suite)
    write_json(output / 'preflight.json', pf)
    rows = []
    for cell in cells:
        directory = output / 'attempts' / cell['cell_id']
        result = directory / 'result.json'
        if result.exists():
            row = read_json(result)
            require(all(row.get(k) == cell[k] for k in cell), 'Stored result cell identity mismatch')
            require(read_json(directory / 'result.sha256.json').get('sha256') == digest(row), 'Stored result was modified')
            rows.append(row)
        elif (directory / 'started.json').exists():
            row = {**cell, **engine.normalize(cell['provider'], (directory / 'events.jsonl').read_text() if (directory / 'events.jsonl').exists() else '', cell['model'], pricing),
                   'completion': 0, 'valid': False, 'status': 'interrupted', 'simulation': False,
                   'difficulty': lookup[cell['task_id']]['spec']['difficulty'], 'execution_mode': suite['execution']['mode']}
            write_json(result, row)
            write_json(directory / 'result.sha256.json', {'sha256': digest(row)})
            rows.append(row)
    retrying = {r['cell_id'] for r in rows if rate_limit_retries > r.get('retry_count', 0) and
                (r.get('rate_limited') or rate_limits.is_rate_limited(r, output / 'attempts' / r['cell_id']))}
    done = {r['cell_id'] for r in rows} - retrying
    todo = [c for c in cells if c['cell_id'] not in done]
    pending = {}
    stop_reason = 'rate_limit_retries_exhausted' if any(r.get('rate_limit_retries_exhausted') and r['cell_id'] not in retrying for r in rows) else None
    fatal = None

    def checkpoint():
        # Stable report ordering, independent of completion timing.
        order = {c['cell_id']: i for i, c in enumerate(cells)}
        rows.sort(key=lambda r: order[r['cell_id']])
        write_json(output / 'results.json', {'schema_version': 1, 'rows': rows})
        info.update(updated_at=now(), completed_cells=len(rows), scheduled_cells=len(cells),
                    active_cells=len(pending), stop_reason=stop_reason,
                    incomplete_cost_cells=sum(bool(r.get('rate_limit_cost_incomplete')) for r in rows),
                    known_spend_upper_usd=sum(r.get('cost_upper_usd') or r.get('known_cost_upper_usd') or 0 for r in rows))
        write_json(manifest, info)

    checkpoint()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        while pending or (todo and not stop_reason):
            try:
                if not stop_reason:
                    if (output / 'stop-requested.json').exists():
                        stop_reason = 'paused'
                    elif any(r.get('rate_limit_retries_exhausted') and r['cell_id'] not in retrying for r in rows):
                        stop_reason = 'rate_limit_retries_exhausted'
                    elif any(r.get('cost_upper_usd') is None and not r.get('not_started') and r['cell_id'] not in retrying
                             and not (rate_limit_retries and r.get('rate_limit_cost_incomplete')) for r in rows):
                        stop_reason = 'unknown_spend'
                    elif sum(r.get('cost_upper_usd') or r.get('known_cost_upper_usd') or 0 for r in rows) >= suite['limits']['spend_stop_usd']:
                        stop_reason = 'spend_threshold'
                # Consume every ready result before refilling, so known stop conditions win.
                ready = [f for f in pending if f.done()]
                if not ready and not stop_reason and todo and len(pending) < workers:
                    lease = slots.acquire()
                    if lease is not None:
                        try:
                            require(engine.load_suite(path)[4] == seal, 'Sealed inputs changed during execution')
                            cell = todo.pop(0)
                            directory = output / 'attempts' / cell['cell_id']
                            write_json(directory / 'started.json', {'cell': cell, 'started_at': now()})
                            previous = next((r for r in rows if r['cell_id'] == cell['cell_id']), None)
                            future = executor.submit(rate_limits.attempt, cell, lookup[cell['task_id']], suite, pricing, directory, pf[cell['provider']],
                                                     previous=previous, max_retries=rate_limit_retries, base_delay=retry_delay)
                            pending[future] = (cell, directory, lease)
                            checkpoint()
                        except BaseException:
                            slots.release(lease)
                            raise
                        continue
                if pending:
                    ready = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED).done
                    for future in ready:
                        cell, directory, lease = pending.pop(future)
                        try:
                            row = future.result()
                        except Exception as error:
                            row = {**cell, **engine.normalize(cell['provider'], '', cell['model'], pricing),
                                   'completion': 0, 'valid': False, 'status': 'infrastructure_error',
                                   'simulation': False, 'difficulty': lookup[cell['task_id']]['spec']['difficulty'],
                                   'execution_mode': suite['execution']['mode'], 'diagnostic': type(error).__name__}
                        finally:
                            slots.release(lease)
                        row['scheduling_workers'] = workers
                        write_json(directory / 'result.json', row)
                        write_json(directory / 'result.sha256.json', {'sha256': digest(row)})
                        rows[:] = [r for r in rows if r['cell_id'] != cell['cell_id']]
                        rows.append(row)
                        retrying.discard(cell['cell_id'])
                        print(f"{len(rows)}/{len(cells)} {cell['task_id']} {cell['model']} {cell['effort']}: {row['status']}", flush=True)
                        if row.get('rate_limit_retries_exhausted'):
                            stop_reason = 'rate_limit_retries_exhausted'
                        elif row.get('retry_paused'):
                            stop_reason = 'paused'
                        elif row['status'] == 'interrupted':
                            stop_reason = 'interrupted'
                        checkpoint()
                elif not stop_reason:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                stop_reason = 'interrupted'
                print('Stopping new work; waiting for active attempts to finish.', flush=True)
            except Exception as error:
                fatal = error
                stop_reason = 'scheduler_error'
                # Keep draining futures; never drop paid in-flight results.
    info.update(state='stopped' if stop_reason else 'complete', active_cells=0)
    checkpoint()
    if fatal:
        raise fatal
    return info
