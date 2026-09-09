#!/usr/bin/env python3
"""Maintainer-only public source crawl. Never executes upstream code; emits metadata only. Dataset files may contain solution fields, which are not emitted."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import io
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'plugins/codex-eval-plugin/ceval/data'
SOURCES = [
    ('deepswe', 'datacurve-ai/deep-swe', '0b9fabbb63b9104d678fe965e1632f2dd9eaa2ea'),
    ('terminal-bench', 'harbor-framework/terminal-bench-2', '2fd12b88aafdd04a52c298e3940bcb189f9766d6'),
    ('aider-polyglot', 'Aider-AI/polyglot-benchmark', '7e0611e77b54e2dea774cdc0aa00cf9f7ed6144f'),
]
DATASETS = [
    ('swe-bench-pro', 'scaleapi/SWE-bench_Pro-os', 'ca10a60a5fcae51e6948ffe1485d4153d421e6c5', 'helper_code/sweap_eval_full_v2.jsonl'),
    ('swe-lancer', 'openai/preparedness', '51052cede8cc608f95bb00346635e03759013e5a', 'project/swelancer/all_swelancer_tasks.csv'),
    ('featurebench', 'LiberCoders/FeatureBench', 'aa464e99aa61c5c47ad1c595671fa6ec7c499232', 'tasks/data/v1.1/tasks_index.json'),
    ('gso', 'gso-bench/gso-bench.github.io', '4907255406d698753efec71c0c8c427608e8683a', 'assets/gso-dataset.json'),
]
TAGS = {
    'frontend-ui': 'dom browser css html toolbar focus layout keyboard accessible ui react editor',
    'backend-api': 'http api request response graphql grpc cookie routing multipart',
    'database-data': 'sql database sqlite query schema import migration data csv json parquet',
    'async-concurrency': 'async cancellation cancel shutdown stream coalescing concurrent queue',
    'devops-build': 'build compile docker nginx deployment packaging install cython git',
    'testing-quality': 'test coverage mutation pytest unittest vitest shard lint',
    'refactoring-migration': 'modernize modernization migration compatibility refactor legacy',
    'performance': 'optimize optimization performance memory cache batching profiling',
    'security-hardening': 'vulnerability sanitize security taint pinning encryption secret',
    'data-science': 'numpy pandas tensor model regression scientific sampling matrix dataset',
    'developer-tooling': 'cli config terminal formatter linter lint shell documentation',
    'parsing-compilers': 'parser parsing grammar compiler interpreter syntax language',
    'algorithms': 'sort search graph tree list buffer number combinator sequence',
    'distributed-systems': 'distributed consensus transaction durability conflict replication crdt',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT/'evaluations/benchmark-research/crawl')
    parser.add_argument('--output', type=Path, default=DATA/'task-inventory.json')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)

    def fetch(repo, revision, path, max_bytes=1_000_000):
        url = f'https://raw.githubusercontent.com/{repo}/{revision}/{path}'
        target = args.cache/hashlib.sha256(url.encode()).hexdigest()
        if target.exists():
            return target.read_text()
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read(max_bytes+1)
        if len(raw) > max_bytes:
            raise ValueError('source exceeds crawl size limit')
        text = raw.decode('utf-8')
        target.write_text(text)
        return text

    jobs, coverage = [], []
    for benchmark, repo, revision in SOURCES:
        tree_path = args.cache/f'{benchmark}-{revision}-tree.json'
        if not tree_path.exists():
            tree_path.write_bytes(subprocess.check_output(['gh', 'api', f'repos/{repo}/git/trees/{revision}?recursive=1']))
        tree = json.loads(tree_path.read_text())
        if tree.get('truncated'):
            raise ValueError(f'Incomplete repository tree: {repo}')
        paths = [p['path'] for p in tree['tree'] if p['type'] == 'blob']
        prompts = [p for p in paths if p.endswith('/instruction.md') or p.endswith('/.docs/instructions.md')]
        for prompt in prompts:
            parent = str(Path(prompt).parent.parent if benchmark == 'aider-polyglot' else Path(prompt).parent)
            candidates = [p for p in paths if p.startswith(parent+'/') and
                          ('/tests/' in p or re.search(r'(?:_test\.(?:py|go)|\.test\.js|Test\.java|_test\.cpp|tests\.rs)$', p))
                          and '/solution/' not in p and Path(p).suffix in {'.py', '.go', '.js', '.java', '.cpp', '.rs', '.patch', '.sh'}]
            candidates.sort(key=lambda p: (0 if p.endswith(('test.patch', 'test_outputs.py')) else 1 if not p.endswith(('test.sh','grader.py')) else 2, p))
            verifier = candidates[0] if candidates else None
            jobs.append((benchmark, repo, revision, prompt, parent, verifier))
        coverage.append({'benchmark': benchmark, 'repository': f'https://github.com/{repo}',
                         'revision': revision, 'task_count': len(prompts), 'scope': 'All task instruction paths at this revision; no solutions downloaded.'})

    def index(job):
        benchmark, repo, revision, prompt, parent, verifier = job
        base = f'https://github.com/{repo}/blob/{revision}/'
        task = parent.split('/')[-1]
        task_id = f'{benchmark}/{parent}'
        entry = {'id': task_id, 'benchmark': benchmark, 'upstream_task': parent,
                 'title': task.replace('-', ' '), 'source_url': base+prompt,
                 'verifier_url': base+verifier if verifier else None,
                 'inspection': 'mechanically_indexed', 'workflow_tags': [], 'test_signals': []}
        try:
            instruction = fetch(repo, revision, prompt)
            test = fetch(repo, revision, verifier) if verifier else ''
            # Search signals, not copied task instructions or solutions.
            words = set(re.findall(r'[a-z]+', (task+' '+instruction).lower()))
            entry['workflow_tags'] = [tag for tag, cues in TAGS.items() if len(words.intersection(cues.split())) >= 2]
            signals = re.findall(r'\b(?:def|func|fn|void)\s+(test\w*|Test\w*)\s*\(', test)
            signals += re.findall(r'\b(?:it|test|TEST_CASE)\s*\(\s*[\'\"]([^\'\"\n]{1,120})', test)
            entry['test_signals'] = list(dict.fromkeys(signals))[:12]
            entry['test_signals_count'] = len(set(signals))
            entry['source_sha256'] = hashlib.sha256(instruction.encode()).hexdigest()
            entry['verifier_sha256'] = hashlib.sha256(test.encode()).hexdigest() if verifier else None
            entry['source_status'] = 'fetched'
        except Exception as error:
            entry['source_status'] = 'unavailable'
            entry['error_type'] = type(error).__name__
        return entry

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        entries = list(pool.map(index, jobs))
    for benchmark, repo, revision, path in DATASETS:
        raw = fetch(repo, revision, path, max_bytes=40_000_000)
        if path.endswith('.jsonl'):
            rows = [json.loads(line) for line in raw.splitlines()]
        elif path.endswith('.csv'):
            rows = [row for row in csv.DictReader(io.StringIO(raw)) if row['variant'] == 'ic_swe']
        else:
            document = json.loads(raw)
            rows = [row for row in document['items'] if row['split'] == 'full'] if benchmark == 'featurebench' else document
        base = f'https://github.com/{repo}/blob/{revision}/'
        for position, row in enumerate(rows, 1):
            ident = row.get('instance_id') or row.get('question_id') or row.get('id')
            objective = row.get('problem_statement') or row.get('preview') or row.get('title') or row.get('api') or ident
            # A short source title plus identifiers; never ship patches or full prompts.
            objective = objective.replace('\\n', '\n').strip('"#* \n')
            title = next((s.strip('#*: "') for s in objective.splitlines() if len(s.strip('#*: "')) > 8), ident)
            title = ' '.join(title.split()[:20])
            url = base+path
            verifier_url = url
            if benchmark == 'swe-bench-pro':
                url += f'#L{position}'
                verifier_url = url
            elif benchmark == 'swe-lancer':
                url = base+f'project/swelancer/issues/{ident}/issue_data.json'
                verifier_url = base+f'project/swelancer/issues/{ident}/test.py'
            elif benchmark == 'featurebench':
                url = base+'tasks/'+row['statement_path'].removeprefix('./')
                verifier_url = 'https://github.com/LiberCoders/FeatureBench/tree/8d4e347ec57546685c5a87e8676bf575db022ea6/featurebench'
            words = set(re.findall(r'[a-z]+', objective.lower()))
            tags = [tag for tag, cues in TAGS.items() if len(words.intersection(cues.split())) >= 2]
            if benchmark == 'gso': tags = sorted(set(tags+['performance']))
            if benchmark == 'swe-lancer': tags = sorted(set(tags+['frontend-ui']))
            signals = row.get('FAIL_TO_PASS', [])
            if isinstance(signals, str):
                try: signals = json.loads(signals)
                except ValueError: signals = []
            entries.append({'id': f'{benchmark}/{ident}', 'benchmark': benchmark, 'upstream_task': ident,
                'title': title, 'source_url': url, 'verifier_url': verifier_url,
                'inspection': 'mechanically_indexed', 'workflow_tags': tags,
                'test_signals': signals[:8], 'source_status': 'fetched',
                'source_sha256': hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest(),
                'verification_scope': 'Source record and test selectors or benchmark harness; task-specific linked files may require further inspection.'})
        coverage.append({'benchmark': benchmark, 'repository': f'https://github.com/{repo}',
            'revision': revision, 'task_count': len(rows),
            'scope': 'Public task records only; full split for FeatureBench and implementation tasks only for SWE-Lancer. No patches, solutions, or full prompts included in inventory.'})
    for source in coverage:
        source['fetched'] = sum(e['benchmark'] == source['benchmark'] and e['source_status'] == 'fetched' for e in entries)
    result = {'schema_version': 1, 'checked_at': '2026-09-09',
              'scope': 'Pinned public task inventory. Titles/tags/test identifiers are retrieval signals, not manually verified task summaries. See task-examples.json for reviewed design cards.',
              'sources': coverage, 'tasks': entries}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'))+'\n')
    print(json.dumps({'output': str(args.output), 'tasks': len(entries), 'sources': coverage,
                      'unavailable': sum(e['source_status'] != 'fetched' for e in entries)}, indent=2))


if __name__ == '__main__':
    main()
