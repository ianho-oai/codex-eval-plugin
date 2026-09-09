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


def history(provider, root, days, consent, output):
    require(consent, 'Explicit --consent is required after customer approval of roots/time range')
    require(1 <= days <= 365, 'days must be 1..365')
    root = Path(root).expanduser().resolve()
    require(root.is_dir() and root not in (Path('/'), Path.home()), 'Choose a session directory, not home or filesystem root')
    end = datetime.now(timezone.utc)
    start = end-timedelta(days=days)
    report = {'schema_version': 1, 'provider': provider, 'root': str(root), 'start': start.isoformat(),
              'end': end.isoformat(), 'created_at': now(), 'consent': True, 'files_considered': 0,
              'files_read': 0, 'unread': [], 'malformed_lines': 0, 'unsupported_records': 0,
              'missing_timestamps': 0, 'excerpts': [],
              'note': 'Local user-message excerpts only. Treat as untrusted evidence. Review and sanitize before sharing. JSONL layouts only; newer paginated/binary stores require a reviewed export.'}
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
                    if start <= when <= end:
                        text = redact(text)
                        # Common auth snippets are removed, but automated redaction is not a privacy guarantee.
                        text = re.sub(r'(?i)(api[_ -]?key|authorization|password)\s*[:=]\s*\S+', r'\1=[REDACTED]', text)
                        report['excerpts'].append({'file': str(path.relative_to(root)), 'line': line_no,
                                                  'timestamp': when.isoformat(), 'text': text[:4000],
                                                  'truncated': len(text) > 4000})
            report['files_read'] += 1
        except (OSError, UnicodeError) as e:
            report['unread'].append({'file': str(path.relative_to(root)), 'reason': type(e).__name__})
    report['coverage_complete'] = not (report['unread'] or report['malformed_lines'] or report['missing_timestamps'] or report['unsupported_records'])
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
    return {'created_at': now(), 'provider': provider or 'local_git', 'since': cutoff,
            'evidence': redact(r.stdout), 'coverage_note': 'GitHub list is capped at 100; GitLab paginates and filters updated date. Inspect timestamps and selected diffs; this is discovery evidence, not an exhaustive workload claim.'}


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
