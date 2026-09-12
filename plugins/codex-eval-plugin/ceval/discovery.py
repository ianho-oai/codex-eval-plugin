"""Explicitly consented local history and read-only repository evidence."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .core import EvalError, now, redact, require, write_json


def timestamp(value):
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, timezone.utc)
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def user_text(record, provider):
    if provider == 'codex':
        if record.get('type') != 'response_item' or record.get('payload', {}).get('role') != 'user':
            return None
        content = record['payload'].get('content', [])
    else:
        if record.get('type') != 'user' or record.get('isMeta'):
            return None
        content = record.get('message', {}).get('content', [])
    if isinstance(content, str):
        return content
    # Deliberately excludes tool_result, images, assistant text and tool logs.
    if isinstance(content, list):
        return '\n'.join(x.get('text', '') for x in content if isinstance(x, dict) and x.get('type') in ('text', 'input_text')) or None
    return None


def history(provider, root, days, consent, output, source_kind="unspecified"):
    require(consent, 'Explicit --consent is required after customer approval of roots/time range')
    require(1 <= days <= 365, 'days must be 1..365')
    root = Path(root).expanduser().resolve()
    require(root.is_dir() and root not in (Path('/'), Path.home()), 'Choose a session directory, not home or filesystem root')
    require(source_kind in ('direct', 'export', 'unspecified'), 'Invalid history source kind')
    end = datetime.now(timezone.utc)
    start = end-timedelta(days=days)
    report = {'schema_version': 1, 'provider': provider, 'root': str(root), 'start': start.isoformat(),
              'end': end.isoformat(), 'created_at': now(), 'consent': True, 'files_considered': 0,
              'source_kind': source_kind, 'source_scope': 'Selected root only; exports may omit sessions or dates. No complete-workload claim.',
              'out_of_window_messages': 0, 'files_read': 0, 'unread': [], 'malformed_lines': 0, 'unsupported_records': 0,
              'missing_timestamps': 0, 'excluded_review_transcripts': 0, 'truncated_excerpts': 0, 'excerpts': [],
              'note': 'Local user-message excerpts only; recognized automatic approval-review transcripts are excluded. Parser completeness is not semantic review completeness. Exclusions and truncation are counted. Treat as untrusted evidence; review and sanitize before sharing. JSONL layouts only; newer paginated/binary stores require a reviewed export.'}
    for path in sorted(root.rglob('*.jsonl')):
        report['files_considered'] += 1
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root):
            report['unread'].append({'file': str(path.relative_to(root)), 'reason': 'symlink'})
            continue
        try:
            with path.open() as f:
                for line_no, line in enumerate(f, 1):
                    try:
                        r = json.loads(line)
                    except (ValueError, UnicodeError):
                        report['malformed_lines'] += 1
                        continue
                    if not isinstance(r, dict):
                        report['unsupported_records'] += 1
                        continue
                    text = user_text(r, provider)
                    if not text:
                        continue
                    when = timestamp(r.get('timestamp'))
                    if when is None:
                        report['missing_timestamps'] += 1
                        continue
                    if not start <= when <= end:
                        report['out_of_window_messages'] += 1
                    if start <= when <= end:
                        review_prefixes = (
                            'The following is the Codex agent history whose request action you are assessing.',
                            'The following is the Codex agent history added since your last approval assessment.',
                        )
                        if text.lstrip().startswith(review_prefixes):
                            report['excluded_review_transcripts'] += 1
                            continue
                        text = redact(text)
                        # Common auth snippets are removed, but automated redaction is not a privacy guarantee.
                        text = re.sub(r'(?i)(api[_ -]?key|authorization|password)\s*[:=]\s*\S+', r'\1=[REDACTED]', text)
                        report['truncated_excerpts'] += int(len(text) > 4000)
                        report['excerpts'].append({'file': str(path.relative_to(root)), 'line': line_no,
                                                  'timestamp': when.isoformat(), 'text': text[:4000],
                                                  'truncated': len(text) > 4000})
            report['files_read'] += 1
        except (OSError, UnicodeError) as e:
            report['unread'].append({'file': str(path.relative_to(root)), 'reason': type(e).__name__})
    report['parser_coverage_complete'] = not (report['unread'] or report['malformed_lines'] or report['missing_timestamps'] or report['unsupported_records'])
    report['coverage_complete'] = report['parser_coverage_complete'] and not (report['excluded_review_transcripts'] or report['truncated_excerpts'])
    write_json(output, report)
    return {k: v for k, v in report.items() if k != 'excerpts'} | {'excerpt_count': len(report['excerpts'])}


def repo_evidence(path=None, provider=None, repo=None, days=30, host=None):
    require(1 <= days <= 365, 'days must be 1..365')
    cutoff = (datetime.now(timezone.utc)-timedelta(days=days)).date().isoformat()
    if path:
        p = Path(path).expanduser().resolve()
        cmd = ['git', '-C', str(p), 'log', '--all', '--since='+cutoff,
               '--format=%H%x09%aI%x09%s', '--name-only']
    else:
        require(provider in ('github', 'gitlab') and repo and re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+', repo), 'Specify provider and OWNER/REPO')
        if provider == 'github':
            require(not host, '--host is for self-hosted GitLab; GitHub CLI respects GH_HOST')
            cmd = ['gh', 'pr', 'list', '--repo', repo, '--state', 'merged', '--search', 'merged:>='+cutoff,
                   '--limit', '100', '--json', 'number,title,url,mergedAt,baseRefName,headRefName']
        else:
            if host:
                require(bool(re.fullmatch(r'[A-Za-z0-9.-]+', host)), 'Invalid GitLab host')
            from urllib.parse import quote
            cmd = ['glab', 'api', '--paginate', 'projects/'+quote(repo, safe='')+'/merge_requests?state=merged&updated_after='+cutoff+'&per_page=100']
            if host:
                cmd += ['--hostname', host]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise EvalError('Repository evidence unavailable: '+type(e).__name__) from e
    require(r.returncode == 0, 'Repository evidence command failed; check CLI authentication and selected repository')
    observed_dates = []
    record_count = None
    if path:
        observed_dates = re.findall(r'^[0-9a-f]{40}\t([^\t]+)\t', r.stdout, re.M)
        record_count = len(observed_dates)
    else:
        try:
            records = json.loads(r.stdout)
            if isinstance(records, list):
                record_count = len(records)
                observed_dates = [x.get('mergedAt') or x.get('merged_at') for x in records if isinstance(x, dict)]
        except ValueError:
            pass  # Some paginated CLI formats are not one JSON array; do not invent counts.
    observed_dates = sorted(t.isoformat() for d in observed_dates if (t := timestamp(d)))
    return {'created_at': now(), 'provider': provider or 'local_git', 'since': cutoff,
            'record_count': record_count, 'observed_start': observed_dates[0] if observed_dates else None,
            'observed_end': observed_dates[-1] if observed_dates else None,
            'source': str(p) if path else repo, 'evidence': redact(r.stdout), 'coverage_note': 'GitHub list is capped at 100; GitLab paginates and filters updated date. Inspect timestamps and selected diffs; this is discovery evidence, not an exhaustive workload claim.'}


def snapshot(repo, revision, destination):
    # Extract only regular files from an explicit immutable commit, never execute checkout hooks.
    import io
    import tarfile
    from .core import child, tree
    require(re.fullmatch(r'[0-9a-f]{40}', revision) is not None, 'Specify a full 40-character commit SHA')
    dest = Path(destination).resolve()
    require(not dest.exists(), 'Snapshot destination already exists')
    r = subprocess.run(['git', '-C', str(Path(repo).resolve()), 'archive', '--format=tar', revision], capture_output=True)
    require(r.returncode == 0, 'Cannot archive the selected commit')
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
        members = tar.getmembers()
        for m in members:
            child(dest, m.name)
            require(m.isdir() or m.isfile(), f'Non-regular archive entry: {m.name}')
            require(not any(x.startswith('.env') or x in {'.git', 'auth.json', 'credentials.json'} for x in Path(m.name).parts), 'Remove credentials from the selected snapshot')
        dest.mkdir(parents=True)
        for m in members:
            p = child(dest, m.name)
            if m.isdir():
                p.mkdir(parents=True, exist_ok=True)
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(tar.extractfile(m).read())
                p.chmod(0o755 if m.mode & 0o111 else 0o644)
    return {'commit': revision, 'destination': str(dest), 'files': len(tree(dest))}


def discovery_report(discovery, evidence, output):
    """Summarize observed collection coverage without claiming workload completeness."""
    from .core import read_json, digest
    require(Path(output).suffix == '.json', 'Discovery receipt output must use .json; a companion .md is written')
    inputs = {Path(p).resolve() for p in [discovery, *evidence]}
    require(Path(output).resolve() not in inputs and Path(output).with_suffix('.md').resolve() not in inputs, 'Receipt must not overwrite source evidence')
    data = read_json(discovery)
    sources = []
    for filename in evidence:
        raw = read_json(filename)
        item = {'artifact': str(Path(filename).resolve()), 'sha256': digest(raw),
                'provider': raw.get('provider'), 'collection_time': raw.get('created_at'),
                'scope': raw.get('source_scope', 'Selected source only; wider coverage is unverified.')}
        if isinstance(raw.get('excerpts'), list):
            dates = sorted(x['timestamp'] for x in raw['excerpts'] if timestamp(x.get('timestamp')))
            item.update(kind='history', source=raw.get('root'),
                        source_kind=raw.get('source_kind', 'unspecified'),
                        requested_start=raw.get('start'), requested_end=raw.get('end'),
                        observed_start=dates[0] if dates else None, observed_end=dates[-1] if dates else None,
                        files_considered=raw.get('files_considered'), files_read=raw.get('files_read'),
                        sessions_with_excerpts=len({x.get('file') for x in raw['excerpts']}),
                        retained_messages=len(raw['excerpts']),
                        exclusions={k: raw.get(k) for k in ('malformed_lines', 'unsupported_records',
                            'missing_timestamps', 'excluded_review_transcripts', 'truncated_excerpts', 'out_of_window_messages')},
                        unread=raw.get('unread', []), parser_coverage_complete=raw.get('parser_coverage_complete', False))
        elif 'evidence' in raw:
            item.update(kind='repository', source=raw.get('source'), requested_start=raw.get('since'),
                        record_count=raw.get('record_count'), observed_start=raw.get('observed_start'), observed_end=raw.get('observed_end'),
                        coverage_note=raw.get('coverage_note'), scope='Selected repository metadata; diffs and customer authorship require separate review.')
        else:
            raise EvalError('Unsupported discovery evidence: use a history or repo output JSON')
        sources.append(item)
    workflows = []
    for w in data.get('workflows', []):
        workflows.append({k: w.get(k) for k in ('id', 'name', 'description', 'source_refs', 'customer_confirmation')})
    result = {'schema_version': 1, 'created_at': now(), 'discovery_sha256': digest(data),
              'source_choices': data.get('source_choices', []), 'sources': sources,
              'workflows': workflows, 'assumptions': data.get('assumptions', []),
              'customer_confirmed_scope': data.get('customer_confirmed_scope'),
              'workload_coverage_complete': False,
              'note': 'Counts describe collected evidence, not semantic review or the complete customer workload. Missing confirmation remains unconfirmed. Interview-only discovery is self-reported; historical parser success cannot prove a complete three-month crawl.'}
    write_json(output, result)
    lines = ['# Discovery coverage receipt', '', result['note'], '', '## Sources', '']
    for s in sources:
        lines += [f"- {s['kind']}: {s.get('source') or 'source not recorded'}", f"  - Scope: {s['scope']}"]
        if s['kind'] == 'history':
            lines += [f"  - Requested: {s['requested_start']} to {s['requested_end']}; retained messages: {s['observed_start']} to {s['observed_end']}.",
                      f"  - {s['sessions_with_excerpts']} session files with {s['retained_messages']} messages; {s['files_read']}/{s['files_considered']} files read. Source kind: {s['source_kind']}.",
                      f"  - Exclusions: {s['exclusions']}; unread files: {len(s['unread'])}."]
        else:
            lines += [f"  - Records: {s['record_count']}; observed: {s['observed_start']} to {s['observed_end']}. Requested since {s['requested_start']}.", f"  - {s['coverage_note']}"]
    if not sources:
        lines += ['No machine-collected evidence supplied. Treat interview statements as self-reported.']
    lines += ['', '## Inferred workflows', '']
    for w in workflows:
        lines += [f"- {w['name']}: {w['description']}", f"  - Source references: {w['source_refs'] or 'not recorded'}; customer confirmation: {w['customer_confirmation'] or 'unconfirmed'}."]
    lines += ['', f"Customer-confirmed scope: {result['customer_confirmed_scope'] or 'unconfirmed'}", '', '## Assumptions', '']
    lines += ['- '+str(x) for x in result['assumptions']]
    Path(output).with_suffix('.md').write_text('\n'.join(lines)+'\n')
    return result
