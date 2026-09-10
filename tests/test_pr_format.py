import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('pr_format', Path(__file__).resolve().parents[1] / '.github/scripts/check_pr_format.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PullRequestFormatTests(unittest.TestCase):
    def test_complete_description_and_docs_only_validation(self):
        body = '## Summary\nClarify setup.\n## Validation\nReviewed links and commands.\n## Risks\nNone'
        self.assertEqual(module.missing_sections(body), [])

    def test_empty_template_comments_and_missing_section_fail(self):
        body = '## Summary\n<!-- explain -->\n## Validation\nTBD\n'
        self.assertEqual(module.missing_sections(body), ['Summary', 'Validation', 'Risks'])

    def test_duplicate_sections_fail(self):
        body = '## Summary\nA\n## Summary\nB\n## Validation\nChecked\n## Risks\nNone'
        self.assertEqual(module.missing_sections(body), ['Summary'])
