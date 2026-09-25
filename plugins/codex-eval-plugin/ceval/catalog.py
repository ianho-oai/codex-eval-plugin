"""Offline task inspiration lookup and per-workflow difficulty coverage."""
import re
from collections import Counter
from .core import DATA, ID, read_json, require, write_json

TIERS = ('basic', 'hard')
LEGACY_TIERS = ('easy', 'medium', 'hard')
TIER_GUIDANCE = {
    'basic': 'A representative calibration task spanning the former easy/medium/hard range: bounded implementation or integration with explicit behavior and regression checks.',
    'hard': 'Former harder-1/harder-2 style: substantive repository investigation and implementation across interacting components, state transitions, recovery, and compatibility. Require observable cross-module invariants, not just more edge cases, files, or setup.',
}
DEFAULT_SLOTS = (
    ('basic', 'localized-repair'),
    ('basic', 'bounded-feature'),
    ('basic', 'component-integration'),
    ('hard', 'repository-repair'),
    ('hard', 'feature-integration'),
    ('hard', 'state-recovery-compatibility'),
    ('hard', 'cross-module-consistency'),
    ('hard', 'customer-critical-path'),
)


def examples(query='', workflow=None, limit=10, include_inventory=False):
    cards = read_json(DATA/'task-examples.json')['examples']
    if include_inventory:
        reviewed_ids = {c.get('inventory_id') for c in cards}
        cards += [e for e in read_json(DATA/'task-inventory.json')['tasks']
                  if e['id'] not in reviewed_ids and e.get('source_status') == 'fetched']
    tokens = set(re.findall(r'[a-z0-9]+', query.lower())) - {'the', 'and', 'for', 'with', 'to', 'a', 'i', 'we'}
    ranked = []
    for card in cards:
        tags = card.get('workflow_tags', [])
        if workflow and workflow not in tags:
            continue
        fields = [card['title'], ' '.join(tags), card.get('what_it_tests', ''),
                  card.get('how_it_tests', ''), ' '.join(card.get('test_signals', []))]
        words = set(re.findall(r'[a-z0-9]+', ' '.join(fields).lower()))
        hits = tokens.intersection(words)
        if tokens and not hits:
            continue
        score = len(hits) * 10 + (2 if card.get('inspection') == 'reviewed_design_card' else 0)
        ranked.append((score, card['id'], card))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return {'query': query, 'workflow': workflow, 'matches': len(ranked),
            'examples': [c for _, _, c in ranked[:limit]],
            'note': 'Customer difficulty is assigned when adapting tasks, not copied from benchmark labels. Indexed entries require source inspection. No suitable match: create an original task and explain why.'}


def normalized_workflows(items, allowed_tiers=TIERS):
    require(isinstance(items, list) and bool(items), 'Discovery must list at least one workflow')
    workflows, ids = [], set()
    for item in items:
        require(isinstance(item, dict), 'Each workflow needs id, name, and description')
        require(set(item) >= {'id', 'name', 'description'}, 'Each workflow needs id, name, and description')
        require(isinstance(item['id'], str) and ID.fullmatch(item['id']) and item['id'] not in ids, 'Invalid or duplicate workflow id')
        require(all(isinstance(item[k], str) and item[k].strip() for k in ('name', 'description')), 'Workflow name and description cannot be empty')
        ids.add(item['id'])
        workflow = {k: item[k] for k in ('id', 'name', 'description')}
        if 'difficulties' in item:
            tiers = item['difficulties']
            require(isinstance(tiers, list) and bool(tiers)
                    and all(isinstance(t, str) and t in allowed_tiers for t in tiers)
                    and len(tiers) == len(set(tiers)), 'Workflow difficulties must be unique values from: '+', '.join(allowed_tiers))
            workflow['difficulties'] = list(tiers)
        workflows.append(workflow)
    return workflows


def portfolio(discovery, suite=None, output=None):
    data = read_json(suite) if suite else None
    if data is not None:
        require(data.get('schema_version') == 3,
                'New portfolios require a schema 3 suite. Run init in a new directory; do not relabel legacy or frozen tasks in place.')
    workflows = normalized_workflows(read_json(discovery).get('workflows'))
    cells = []
    for workflow in workflows:
        candidates = examples(workflow['name']+' '+workflow['description'], limit=3)['examples']
        slots = [(tier, 'customer-scoped') for tier in workflow['difficulties']] if 'difficulties' in workflow else DEFAULT_SLOTS
        for index, (tier, profile) in enumerate(slots, 1):
            cells.append({'slot_id': f"{workflow['id']}-{index}-{profile}",
                          'workflow_id': workflow['id'], 'workflow': workflow['name'], 'difficulty': tier,
                          'design_focus': profile,
                          'difficulty_guidance': TIER_GUIDANCE[tier],
                          'candidate_inspirations': [{'id': c['id'], 'title': c['title'], 'source_url': c['source_url']} for c in candidates],
                          'original_task_allowed': True})
    result = {'schema_version': 2, 'difficulty_taxonomy': 'basic-hard-v1', 'status': 'proposal_scaffold', 'workflows': workflows,
              'minimum_tasks': len(cells), 'slots': cells,
              'task_design_policy': 'Default to three Basic and five distinct Hard tasks per workflow. Adapt design focuses to customer evidence; do not manufacture unrelated work. Self-contained local fixtures and an existing simple test runner; no heavy setup or external services by default. Use the reference catalog for repository-engineering inspiration, not a claim of benchmark-equivalent difficulty. Supply enough context for solvable tasks without targeting high pass rates or a preferred provider. Verify correctness, cost and latency; no timeout unless explicitly selected.',
              'note': 'Author customer-specific tasks for every slot, explain source adaptations or original rationale, then obtain portfolio and concrete-suite approval.'}
    if suite:
        data.update(purpose='customer', workflows=workflows)
        write_json(suite, data)
    if output:
        write_json(output, result)
    return result


def coverage(suite, tasks):
    if suite.get('schema_version') == 1 or suite.get('purpose') == 'smoke':
        return {'enforced': False, 'reason': 'Legacy suite or explicitly scoped development smoke test', 'missing': []}
    tiers = TIERS if suite.get('schema_version') == 3 else LEGACY_TIERS
    workflows = normalized_workflows(suite.get('workflows'), tiers)
    allowed = {w['id'] for w in workflows}
    present = Counter()
    for task in tasks:
        spec = task.get('spec', task)
        require(spec.get('workflow_id') in allowed, 'Every customer task must reference a discovered workflow_id')
        require('provenance' in spec, 'Every customer task must explain its inspiration or original design')
        present[(spec['workflow_id'], spec['difficulty'])] += 1
    required = [(w['id'], tier) for w in workflows
                for tier in (w['difficulties'] if 'difficulties' in w else
                             [s[0] for s in DEFAULT_SLOTS] if suite.get('schema_version') == 3 else tiers)]
    # Repeat missing entries for unfilled slots, preserving the legacy receipt shape.
    missing = []
    for (workflow_id, tier), count in Counter(required).items():
        missing.extend({'workflow_id': workflow_id, 'difficulty': tier}
                       for _ in range(max(0, count - present[(workflow_id, tier)])))
    return {'enforced': True, 'workflow_count': len(workflows),
            'minimum_tasks': len(required), 'missing': missing}


def validate_provenance(task):
    if 'provenance' not in task:
        return
    provenance = task['provenance']
    require(isinstance(provenance, dict) and set(provenance) == {'kind', 'rationale', 'sources'}, 'Provenance needs kind, rationale, and sources')
    require(provenance['kind'] in ('benchmark-inspired', 'original'), 'Unknown provenance kind')
    require(isinstance(provenance['rationale'], str) and provenance['rationale'].strip(), 'Explain task inspiration or original-design rationale')
    require(isinstance(provenance['sources'], list), 'Provenance sources must be a list')
    if provenance['kind'] == 'original':
        require(not provenance['sources'], 'Original tasks must not claim upstream task sources')
        return
    require(bool(provenance['sources']), 'Benchmark-inspired tasks must cite at least one task example')
    catalog = read_json(DATA/'task-examples.json')['examples'] + read_json(DATA/'task-inventory.json')['tasks']
    by_id = {entry['id']: entry for entry in catalog}
    for source in provenance['sources']:
        require(isinstance(source, dict) and set(source) == {'example_id', 'source_url', 'adaptation'}, 'Each inspiration needs example_id, source_url, and adaptation')
        require(isinstance(source['example_id'], str), 'Inspiration example_id must be a string')
        entry = by_id.get(source['example_id'])
        require(entry is not None and source['source_url'] == entry['source_url'], 'Inspiration must cite the original source URL for its catalog example')
        require(isinstance(source['adaptation'], str) and source['adaptation'].strip(), 'Explain what was adapted for the customer')
        require(entry['benchmark'] in task['benchmark_refs'], 'Inspiration benchmark must appear in benchmark_refs')
