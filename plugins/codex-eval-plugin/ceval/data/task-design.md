# Task design

Read when converting approved workflows into runnable tasks. See `benchmarks.json` for the dated public source index, and `examples/` for three small original harness-validation tasks. They demonstrate easy/medium/hard mechanics; they are not substitutes for a customer's representative portfolio or an official benchmark score.

## Portfolio

Record workflow frequency, languages/frameworks, pain points, deliverable, source provenance, difficulty, and testable success criteria in `discovery.json`. Aim for a meaningful spread across workflows and difficulties. Avoid over-weighting many small tasks merely because they are cheap. Use repeated trials (default 3) and document any sampling choices. A task should have enough context for a headless agent to finish without clarification.

| Difficulty | Design | Example frontend workflow |
| --- | --- | --- |
| Easy | Localized behavior with clear inputs/outputs | Fix accessible labels, empty state, or formatting; validate semantic DOM and regressions |
| Medium | Several interacting constraints | Filter/sort/paginate correctly while preserving state and immutability |
| Hard | Multi-stage or cross-module behavior | Async search with cancellation, stale results, keyboard navigation, disposal, and backward compatibility |

Hard customer tasks should include repository-scale integration where the workflow warrants it. Merely adding more edge cases to a small function is not equivalent to DeepSWE's long-horizon scope. The included async controller is a compact validation example.

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

- Prove the starting snapshot fails and the oracle passes. The CLI checks both, but this alone is not sufficient proof of grader quality.
- Add mutants/adversarial candidates: no-op, hardcoded example output, deny-all, ignored filter, unsafe path, removed regression test, stale async response. Check public behavior, not implementation symbols.
- Use a pristine verifier container. Do not run candidate-supplied tests as the sole acceptance criterion. Test-authoring tasks need mutation/coverage goals plus independent behavioral checks; a new test file alone is not completion.
- Pin clocks, random seeds, data, ports, dependencies, language/runtime, and image digest. Install build/test dependencies into the image before timed trials. Do not download them inside a timed task.
- For browser tests, bundle the browser and fixed viewport; assert keyboard, accessibility, layout, and observable behavior with deterministic checks. Screenshot aesthetics are outside binary completion unless an explicit measurable criterion is defined.
- Freeze before all lanes. Never repair a task after seeing which provider failed without versioning and rerunning all affected lanes under a newly approved suite.
- A historical PR can leak the answer through commit history. `snapshot` strips Git history. Do not put solutions, grader paths, benchmark answer keys, or private discovery transcripts in the agent workspace.

## Repositories

Read-only `repo` discovery collects titles and metadata. Use selected `gh pr view --json ...`, `gh pr diff`, or the customer's `glab mr` equivalent for details after scope approval. Preserve a source link and commit SHA. Clone/fetch only the named customer repository with existing scoped credentials; do not enumerate unrelated repositories. `snapshot --repo PATH --commit FULL_SHA --output TASK/baseline` exports regular files; remove agent configuration files and inspect for customer secrets before evaluation. Git submodules and LFS assets need explicit materialization and review; archive alone does not supply them.
