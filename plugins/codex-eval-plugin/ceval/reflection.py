"""Deterministic failure triage for the host agent; never an automatic grader."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import math
from uuid import uuid4

from .core import child, digest, now, read_json, require, EvalError, write_json
from .progress import progress


def _review(root, minimum, failure_rate):
    snapshot = progress([root])['runs'][0]
    result = dict(snapshot, tasks=[], needs_review=False)
    if not snapshot['outcomes_available']:
        result['review_state'] = 'awaiting_checkpoint'
        return result
    info = read_json(root / 'run.json')
    rows = read_json(root / 'results.json')['rows'] if (root / 'results.json').exists() else []
    if (len(rows) != snapshot['finished'] or
            (info.get('updated_at') or info.get('created_at')) != snapshot['checkpoint_at']):
        result['review_state'] = 'awaiting_checkpoint'
        return result
    cells = {c['cell_id']: c for c in info['schedule']}
    by_task = defaultdict(list)
    seen = set()
    for row in rows:
        cell_id = row['cell_id']
        require(cell_id in cells and cell_id not in seen, 'Invalid reflection result identity')
        require(all(row.get(k) == v for k, v in cells[cell_id].items()), 'Reflection cell mismatch')
        seen.add(cell_id)
        if not (info.get('simulation') and row.get('simulation')):
            folder = child(root / 'attempts', cell_id)
            require(read_json(folder / 'result.json') == row and
                    read_json(folder / 'result.sha256.json').get('sha256') == digest(row),
                    'Reflection result integrity check failed')
        by_task[row['task_id']].append(row)
    scheduled = Counter(c.get('task_id') for c in info['schedule'])
    for task_id, task_rows in sorted(by_task.items()):
        passed = sum(bool(r.get('valid')) and r.get('completion') == 1 for r in task_rows)
        failed = sum(bool(r.get('valid')) and r.get('completion') != 1 for r in task_rows)
        errors = len(task_rows) - passed - failed
        scorable = passed + failed
        fraction = failed / scorable if scorable else None
        signals = []
        if errors:
            signals.append('infrastructure_error')
        if scorable >= minimum and failed and fraction >= failure_rate:
            signals.append('frequent_task_failures')
        lanes = defaultdict(Counter)
        evidence = []
        for row in task_rows:
            lane = (row['provider'], row['model'], row.get('effort', 'default'))
            lanes[lane][row['status']] += 1
            if (not row.get('valid') or row.get('completion') != 1) and len(evidence) < 3:
                evidence.append({'cell_id': row['cell_id'], 'status': row['status'],
                                 'provider': row['provider'], 'model': row['model'],
                                 'effort': row.get('effort'), 'result_sha256': digest(row),
                                 'attempt_dir': None if info.get('simulation') else
                                 str(child(root / 'attempts', row['cell_id']))})
        result['tasks'].append({
            'task_id': task_id, 'scheduled': scheduled[task_id], 'finished': len(task_rows),
            'scorable': scorable, 'passed': passed, 'failed': failed,
            'infrastructure_errors': errors, 'failure_rate': fraction,
            'signals': signals, 'needs_review': bool(signals), 'evidence': evidence,
            'lanes': [{'provider': k[0], 'model': k[1], 'effort': k[2], 'statuses': dict(v)}
                      for k, v in sorted(lanes.items())]})
    result['needs_review'] = any(t['needs_review'] for t in result['tasks'])
    result['review_state'] = 'review_required' if result['needs_review'] else 'no_trigger'
    result['seal'] = info.get('seal')
    return result


def reflect(run_dirs, minimum=3, failure_rate=0.5, pause_on_review=False):
    require(type(minimum) is int and minimum >= 1, '--min-attempts must be positive')
    require(type(failure_rate) in (int, float) and math.isfinite(failure_rate)
            and 0 < failure_rate <= 1, '--failure-rate must be greater than 0 and at most 1')
    roots = list(dict.fromkeys(Path(p).resolve() for p in run_dirs))
    # Verify every input before writing any pause request.
    runs = [_review(root, minimum, failure_rate) for root in roots]
    for root, result in zip(roots, runs):
        result['pause_request'] = 'not_requested'
        if not pause_on_review:
            continue
        if not result['needs_review']:
            result['pause_request'] = 'not_needed'
        elif result.get('simulation'):
            result['pause_request'] = 'synthetic_no_action'
        elif result['recorded_state'] != 'running':
            result['pause_request'] = 'run_not_active'
        else:
            target = child(root, 'stop-requested.json')
            request = {'reason': 'task_quality_review', 'requested_at': now(),
                       'requested_by': 'codex-eval reflect --pause-on-review',
                       'seal': result['seal'],
                       'task_ids': [t['task_id'] for t in result['tasks'] if t['needs_review']]}
            try:
                with target.open('x') as f:
                    json.dump(request, f, indent=2)
                    f.write('\n')
                result['pause_request'] = 'requested'
            except FileExistsError:
                result['pause_request'] = 'already_requested'
    return {'schema_version': 1, 'observed_at': now(), 'runs': runs,
            'needs_review': any(r['needs_review'] for r in runs),
            'policy': {'min_scorable_attempts_per_task': minimum, 'failure_rate': failure_rate},
            'note': 'Review signals are hypotheses, not proof of defective tasks or invalid scores. '
                    'Inspect the visible contract, grader, runtime, and preserved candidate evidence. '
                    'No API calls, candidate execution, score changes, or automatic task edits. '
                    'Pause requests drain active work and can be observed after additional dispatch.'}


def clear_review_pause(run_dir, reviewer, reason):
    """Archive a reviewed pause under the runner lock; do not start any jobs."""
    require(reviewer.strip() and reason.strip(), 'Provide --by and a nonempty --reason')
    root = Path(run_dir).resolve()
    require((root / 'run.json').is_file(), 'Run manifest is missing')
    lock = child(root, '.run-lock')
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise EvalError('Runner is active or locked; wait for it to drain before clearing review.') from exc
    try:
        info = read_json(root / 'run.json')
        require(info.get('state') == 'stopped' and info.get('active_cells') == 0,
                'Run must be stopped with zero active cells')
        target = child(root, 'stop-requested.json')
        request = read_json(target)
        require(request.get('reason') == 'task_quality_review' and
                request.get('requested_by') == 'codex-eval reflect --pause-on-review' and
                request.get('seal') == info.get('seal'),
                'Only a matching task-quality review pause can be cleared')
        receipt = child(root, 'quality-reviews') / (uuid4().hex + '.json')
        write_json(receipt, {'reviewed_at': now(), 'reviewed_by': reviewer,
                            'reason': reason, 'pause_request': request})
        require(read_json(target) == request, 'Pause changed during review; left in place')
        target.unlink()
        return {'cleared': True, 'receipt': str(receipt), 'resumed': False,
                'note': 'No work started or scores changed. Resume only the identical approved suite.'}
    finally:
        lock.rmdir()
