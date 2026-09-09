"""Offline task inspiration lookup and per-workflow difficulty coverage."""
import re
from .core import DATA, ID, read_json, require, write_json

TIERS = ('easy', 'medium', 'hard')
TIER_GUIDANCE = {
    'easy': 'One localized change with explicit behavior, an edge case, and a regression check.',
    'medium': 'Integrate interacting requirements across components; verify state, error paths, and compatibility.',
    'hard': 'A realistic multi-stage or cross-module change; verify lifecycle, failure recovery, integration, and existing behavior. Do not manufacture difficulty through prompt length or extra edge cases alone.',
}


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


def normalized_workflows(items):
    require(isinstance(items, list) and bool(items), 'Discovery must list at least one workflow')
    workflows, ids = [], set()
    for item in items:
        require(isinstance(item, dict), 'Each workflow needs id, name, and description')
        require(set(item) >= {'id', 'name', 'description'}, 'Each workflow needs id, name, and description')
        require(isinstance(item['id'], str) and ID.fullmatch(item['id']) and item['id'] not in ids, 'Invalid or duplicate workflow id')
        require(all(isinstance(item[k], str) and item[k].strip() for k in ('name', 'description')), 'Workflow name and description cannot be empty')
        ids.add(item['id'])
        workflows.append({k: item[k] for k in ('id', 'name', 'description')})
    return workflows


def portfolio(discovery, suite=None, output=None):
    workflows = normalized_workflows(read_json(discovery).get('workflows'))
    cells = []
    for workflow in workflows:
        candidates = examples(workflow['name']+' '+workflow['description'], limit=3)['examples']
        for tier in TIERS:
            cells.append({'workflow_id': workflow['id'], 'workflow': workflow['name'], 'difficulty': tier,
                          'difficulty_guidance': TIER_GUIDANCE[tier],
                          'candidate_inspirations': [{'id': c['id'], 'title': c['title'], 'source_url': c['source_url']} for c in candidates],
                          'original_task_allowed': True})
    result = {'schema_version': 1, 'status': 'proposal_scaffold', 'workflows': workflows,
              'minimum_tasks': len(cells), 'slots': cells,
              'note': 'Author customer-specific tasks for every slot, explain source adaptations or original rationale, then obtain portfolio and concrete-suite approval.'}
    if suite:
        data = read_json(suite)
        data.update(schema_version=2, purpose='customer', workflows=workflows)
        write_json(suite, data)
    if output:
        write_json(output, result)
    return result


def coverage(suite, tasks):
    if suite.get('schema_version') == 1 or suite.get('purpose') == 'smoke':
        return {'enforced': False, 'reason': 'Legacy suite or explicitly scoped development smoke test', 'missing': []}
    workflows = normalized_workflows(suite.get('workflows'))
    allowed = {w['id'] for w in workflows}
    present = set()
    for task in tasks:
        spec = task.get('spec', task)
        require(spec.get('workflow_id') in allowed, 'Every customer task must reference a discovered workflow_id')
        require('provenance' in spec, 'Every customer task must explain its inspiration or original design')
        present.add((spec['workflow_id'], spec['difficulty']))
    missing = [{'workflow_id': w['id'], 'difficulty': tier} for w in workflows for tier in TIERS
               if (w['id'], tier) not in present]
    return {'enforced': True, 'workflow_count': len(workflows), 'minimum_tasks': len(workflows)*3, 'missing': missing}


def validate_provenance(task):
    provenance = task.get('provenance')
    if provenance is None:
        return
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
