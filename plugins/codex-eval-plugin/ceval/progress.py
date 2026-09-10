"""Small read-only checkpoint snapshots for host-side progress visualization."""
from pathlib import Path

from .core import child, digest, now, read_json, require


def progress(run_dirs):
    runs = []
    for root in dict.fromkeys(Path(value).resolve() for value in run_dirs):
        manifest = root / 'run.json'
        if not manifest.exists():
            runs.append({'run_dir': str(root), 'name': root.name,
                         'recorded_state': 'awaiting_start', 'checkpoint_at': None,
                         'scheduled': None, 'finished': 0, 'remaining': None,
                         'active_at_checkpoint': None, 'passed': None, 'failed': None,
                         'errors': None, 'outcomes_available': False})
            continue
        # run.json is atomically replaced. Results may be one checkpoint ahead;
        # only attach outcomes when their count matches this manifest snapshot.
        info = read_json(manifest)
        scheduled = len(info['schedule'])
        finished = info.get('completed_cells')
        rows_file = root / 'results.json'
        rows = read_json(rows_file)['rows'] if rows_file.exists() else []
        if finished is None:
            finished = len(rows)
        require(0 <= finished <= scheduled, 'Invalid checkpoint completion count')
        available = len(rows) == finished
        passed = failed = errors = None
        if available:
            cells = {cell['cell_id']: cell for cell in info['schedule']}
            seen = set()
            for row in rows:
                cell_id = row['cell_id']
                require(cell_id in cells and cell_id not in seen, 'Invalid progress result identity')
                require(all(row.get(k) == v for k, v in cells[cell_id].items()), 'Progress cell mismatch')
                seen.add(cell_id)
                if not (info.get('simulation') and row.get('simulation')):
                    receipt = read_json(child(root / 'attempts', cell_id) / 'result.sha256.json')
                    require(receipt.get('sha256') == digest(row), 'Progress result integrity check failed')
            passed = sum(bool(row.get('valid')) and row.get('completion') == 1 for row in rows)
            failed = sum(bool(row.get('valid')) and row.get('completion') != 1 for row in rows)
            errors = len(rows) - passed - failed
        runs.append({'run_dir': str(root), 'name': info.get('suite', {}).get('name', root.name),
                     'recorded_state': info.get('state', 'unknown'),
                     'checkpoint_at': info.get('updated_at') or info.get('created_at'),
                     'scheduled': scheduled, 'finished': finished, 'remaining': scheduled-finished,
                     'active_at_checkpoint': info.get('active_cells'),
                     'passed': passed, 'failed': failed, 'errors': errors,
                     'outcomes_available': available, 'simulation': bool(info.get('simulation')),
                     'stop_reason': info.get('stop_reason')})
    return {'schema_version': 1, 'observed_at': now(), 'runs': runs,
            'note': 'Saved checkpoints, not process liveness. Remaining includes active work. '
                    'Active slots can include retry backoff. Null means unavailable. '
                    'Counts cover the original schedule, including results hidden by dashboard view receipts.'}
