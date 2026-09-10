"""Validate PR prose only; never execute contributor code or shell content."""
import json
import os
import re
from pathlib import Path


REQUIRED = ('Summary', 'Validation', 'Risks')


def missing_sections(body):
    body = re.sub(r'<!--.*?-->', '', body or '', flags=re.S)
    headings = list(re.finditer(r'^##\s+(.+?)\s*$', body, re.M))
    missing = []
    for required in REQUIRED:
        matching = [i for i, h in enumerate(headings) if h[1].casefold() == required.casefold()]
        if len(matching) != 1:
            missing.append(required)
            continue
        i = matching[0]
        end = headings[i+1].start() if i+1 < len(headings) else len(body)
        content = body[headings[i].end():end].strip()
        if not re.search(r'\w', content) or content.casefold() in {'todo', 'tbd'}:
            missing.append(required)
    return missing


if __name__ == '__main__':
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    missing = missing_sections(event['pull_request'].get('body'))
    if missing:
        print('::error::Fill each section exactly once: ' + ', '.join(missing))
        raise SystemExit(1)
    print('PR description includes Summary, Validation, and Risks.')
