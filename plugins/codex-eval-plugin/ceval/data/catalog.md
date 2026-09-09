# Public task reference catalog

Snapshot: 2026-09-09. Search works offline and requires no dependencies or credentials.

## Coverage

| Dataset | Indexed tasks | Pinned source |
| --- | ---: | --- |
| deepswe | 113 | [https://github.com/datacurve-ai/deep-swe](https://github.com/datacurve-ai/deep-swe/tree/0b9fabbb63b9104d678fe965e1632f2dd9eaa2ea) |
| terminal-bench | 89 | [https://github.com/harbor-framework/terminal-bench-2](https://github.com/harbor-framework/terminal-bench-2/tree/2fd12b88aafdd04a52c298e3940bcb189f9766d6) |
| aider-polyglot | 225 | [https://github.com/Aider-AI/polyglot-benchmark](https://github.com/Aider-AI/polyglot-benchmark/tree/7e0611e77b54e2dea774cdc0aa00cf9f7ed6144f) |
| swe-bench-pro | 731 | [https://github.com/scaleapi/SWE-bench_Pro-os](https://github.com/scaleapi/SWE-bench_Pro-os/tree/ca10a60a5fcae51e6948ffe1485d4153d421e6c5) |
| swe-lancer | 198 | [https://github.com/openai/preparedness](https://github.com/openai/preparedness/tree/51052cede8cc608f95bb00346635e03759013e5a) |
| featurebench | 200 | [https://github.com/LiberCoders/FeatureBench](https://github.com/LiberCoders/FeatureBench/tree/aa464e99aa61c5c47ad1c595671fa6ec7c499232) |
| gso | 102 | [https://github.com/gso-bench/gso-bench.github.io](https://github.com/gso-bench/gso-bench.github.io/tree/4907255406d698753efec71c0c8c427608e8683a) |

Total: **1658 task metadata records**. The companion file contains **46 detailed original design cards across 13 families**. SWE-bench, SWE-bench Multimodal, TestGenEval, BigCodeBench, LiveCodeBench, and EvalPlus contribute methodology cards; their entire task datasets are not indexed.

## What is stored

- `task-inventory.json`: task identifiers, short titles, original prompt/verifier links, source revisions and hashes, heuristic workflow tags, and test signals. Mechanical indexing is explicitly labeled. No full upstream prompts, tests, or solution patches are bundled.
- `task-examples.json`: original summaries of what is tested, how it is graded, adaptation guidance, and evidence scope. Some cards use task instructions and selected verifier sources; others use published methodology only. Inclusion does not certify verifier quality or execute the upstream benchmark.
- `benchmarks.json`: family-level methodology and licensing reminders.

The seven dataset scopes differ: SWE-Lancer includes 198 implementation tasks (manager-choice tasks excluded); FeatureBench includes the 200-task full v1.1 split (overlapping lite/fast splits excluded). The catalog covers major public examples, not every benchmark or an objective “top” ranking. Review upstream licenses before importing code.

## Use and refresh

```sh
./eval examples --query "frontend editor focus" --limit 5
./eval examples --query "database migration" --inventory --limit 10
./eval portfolio evaluations/customer/discovery.json --suite evaluations/customer/suite.json --output evaluations/customer/portfolio.json
```

The portfolio is a proposal scaffold. The skill writes original tasks and verifiers, explains source adaptations, and seeks customer approval. Every workflow requires all three difficulty tiers. If search does not find a suitable example, write an original task with an explicit rationale.

Maintainers can rerun `python3 scripts/crawl_benchmarks.py` from the source repository. It retrieves pinned public sources with the GitHub CLI and Python standard library, caches raw research only under ignored `evaluations/benchmark-research/`, and emits metadata. Refresh revisions deliberately, review the resulting diff, and separately update curated cards. The crawler is not needed by the exported plugin.
