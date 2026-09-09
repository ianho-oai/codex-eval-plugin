# Task design

Read when converting approved workflows into runnable tasks. See `benchmarks.json` for the dated public source index, and `examples/` for three small original harness-validation tasks. They demonstrate easy/medium/hard mechanics; they are not substitutes for a customer's representative portfolio or an official benchmark score.

## Portfolio

Record workflow frequency, languages/frameworks, pain points, deliverable, source provenance, difficulty, and testable success criteria in `discovery.json`. New customer suites require at least one easy, medium, and hard task for **each** declared workflow. Declare workflows in discovery.json, then use `portfolio DISCOVERY --suite SUITE` to register them. Suite schema 2 enforces this at validation, planning, approval, and execution; legacy schema 1 and explicit developer smoke suites remain supported. Avoid over-weighting many small tasks merely because they are cheap. Use repeated trials (default 3) and document any sampling choices. A task should have enough context for a headless agent to finish without clarification.

| Difficulty | Design | Example frontend workflow |
| --- | --- | --- |
| Easy | Localized behavior with clear inputs/outputs | Fix accessible labels, empty state, or formatting; validate semantic DOM and regressions |
| Medium | Several interacting constraints | Filter/sort/paginate correctly while preserving state and immutability |
| Hard | Multi-stage or cross-module behavior | Async search with cancellation, stale results, keyboard navigation, disposal, and backward compatibility |

Hard customer tasks should include repository-scale integration where the workflow warrants it. Merely adding more edge cases to a small function is not equivalent to DeepSWE's long-horizon scope. The included async controller is a compact validation example.

## Finding task inspiration

The bundled `task-inventory.json` contains 1,658 metadata records from seven pinned public dataset sources. `task-examples.json` contains 46 original design cards across 13 benchmark families. This is a scoped reference library, not an exhaustive ranking or a claim that every verifier was audited. See [catalog coverage](catalog.md).

Search with `examples --query "workflow terms"`; expand to the mechanical inventory with `--inventory`. Explain how you adapt behavior, context, and verification to the customer. Keep benchmark URLs in metadata, outside the evaluated agent's prompt. Methodology-only cards do not identify an upstream task.

Example task metadata additions:

```json
{
  "workflow_id": "frontend",
  "provenance": {
    "kind": "benchmark-inspired",
    "rationale": "Exercise editor focus across interacting components.",
    "sources": [{
      "example_id": "example/deepswe/tasks/quill-shared-toolbar-focus",
      "source_url": "https://github.com/datacurve-ai/deep-swe/blob/0b9fabbb63b9104d678fe965e1632f2dd9eaa2ea/tasks/quill-shared-toolbar-focus/instruction.md",
      "adaptation": "Use the customer's synthetic two-pane editor and independently verify focus and selection preservation."
    }]
  }
}
```

An original task uses `{"kind":"original","rationale":"Why no catalog example fits and what this task exercises","sources":[]}`. Source URLs are validated against the catalog. Difficulty describes customer scope, not an upstream rating.

| Workflow | Easy | Medium | Hard |
| --- | --- | --- | --- |
| API/backend | Repair one validation contract | Integrate pagination, errors, and compatibility | Add streaming/cancellation across service lifecycle and recovery |
| CLI/tooling | Fix flag parsing | Compose config-file and environment precedence | Multi-command migration with rollback and compatibility |
| Data/performance | Correct one transformation | Join heterogeneous inputs and preserve schema | Optimize an integrated pipeline with output equivalence and fixed workload thresholds |
| Test authoring | Catch a focused regression | Cover state transitions and error paths | Kill a defined set of realistic cross-module mutants while preserving valid behavior |
| Frontend | Semantic DOM/empty-state repair | Filter and navigation state integration | Async interaction lifecycle, accessibility, recovery, and regressions |

## Layout

```
tasks/my-task/
  task.json
  instruction.md
  baseline/        # only material the agent may see
  oracle/          # complete known-good snapshot, never mounted to agent
  grader/          # immutable verifier, never mounted to agent
```

`task.json` contains `id`, `use_case`, `difficulty`, `difficulty_rationale`, `benchmark_refs`, `allowed_paths`, and `grader`. See `task.schema.json` for the schema. Grader argv uses `{candidate}` and `{grader}` placeholders and runs with no shell interpolation. Return exit 0 only when every requirement and regression passes, 1 for a behavioral failure, and another code for infrastructure/setup failure. Avoid catching every exception as success or silently skipping dependencies. Print short check results without secrets.

## Verifier quality

State ordering and precedence explicitly, with a conflicting-input example. For example: “lowest to highest: defaults, config, environment, flags; later values override earlier ones. With config=10, environment=20, flags=30, return30.” Avoid relying on a list whose direction can be interpreted differently. Distinguish missing, empty, whitespace, zero, and false when those cases affect success.

- Prove the starting snapshot fails and the oracle passes. The CLI checks both, but this alone is not sufficient proof of grader quality.
- Add mutants/adversarial candidates: no-op, hardcoded example output, deny-all, ignored filter, unsafe path, removed regression test, stale async response. Check public behavior, not implementation symbols.
- Use a pristine verifier container. Do not run candidate-supplied tests as the sole acceptance criterion. Test-authoring tasks need mutation/coverage goals plus independent behavioral checks; a new test file alone is not completion.
- Pin clocks, random seeds, data, ports, dependencies, language/runtime, and image digest. Install build/test dependencies into the image before timed trials. Do not download them inside a timed task.
- For browser tests, bundle the browser and fixed viewport; assert keyboard, accessibility, layout, and observable behavior with deterministic checks. Screenshot aesthetics are outside binary completion unless an explicit measurable criterion is defined.
- Freeze before all lanes. Never repair a task after seeing which provider failed without versioning and rerunning all affected lanes under a newly approved suite.
- A historical PR can leak the answer through commit history. `snapshot` strips Git history. Do not put solutions, grader paths, benchmark answer keys, or private discovery transcripts in the agent workspace.

## Repositories

Read-only `repo` discovery collects titles and metadata. Use selected `gh pr view --json ...`, `gh pr diff`, or the customer's `glab mr` equivalent for details after scope approval. Preserve a source link and commit SHA. Clone/fetch only the named customer repository with existing scoped credentials; do not enumerate unrelated repositories. `snapshot --repo PATH --commit FULL_SHA --output TASK/baseline` exports regular files; remove agent configuration files and inspect for customer secrets before evaluation. Git submodules and LFS assets need explicit materialization and review; archive alone does not supply them.
