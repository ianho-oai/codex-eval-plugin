import importlib.util
import pathlib
import random
import re
import sys
import unicodedata

spec = importlib.util.spec_from_file_location('candidate_slug', pathlib.Path(sys.argv[1])/'slug.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    cases = [('Hello World', 'hello-world'), ('  Crème brûlée! ', 'creme-brulee'),
             ('a___b//c', 'a-b-c'), ('---', ''), ('', ''), ('v2.0 Release', 'v2-0-release'),
             ('你好', ''), ('a\tb\nc', 'a-b-c'), ('ÉCOLE', 'ecole')]
    for raw, expected in cases:
        assert module.slugify(raw) == expected, repr(raw)
    for bad in (None, 12, [], {}, b'abc'):
        try:
            module.slugify(bad)
        except TypeError:
            pass
        else:
            raise AssertionError('Non-string accepted')
    rng = random.Random(102)
    for _ in range(80):
        raw = ''.join(rng.choice('abCD012 _-!éø\t') for _ in range(30))
        ascii_text = unicodedata.normalize('NFKD', raw).encode('ascii', 'ignore').decode().lower()
        expected = '-'.join(re.findall('[a-z0-9]+', ascii_text))
        assert module.slugify(raw) == expected
    print('PASS: edge cases, valid inputs, type contract, 80 deterministic generated cases')
except AssertionError as e:
    print('FAIL:', e)
    sys.exit(1)
