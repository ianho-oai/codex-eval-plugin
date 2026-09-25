# Task design

Read when converting approved workflows into runnable tasks. See `benchmarks.json` for the dated public source index, and `examples/` for three small original harness-validation tasks. New suites copy all three as Basic fixtures; they are not substitutes for a customer's representative portfolio or an official benchmark score.

## Evaluation objective

Measure verified correctness, time, tokens, and cost on representative customer engineering work. Use two tiers in new schema 3 suites: **Basic** spans the former easy/medium/hard range; **Hard** targets the former harder-1/harder-2 style. Supply explicit requirements and enough repository context to make tasks feasible without optimizing for a high pass rate. Hard work should expose differences in investigation, implementation and verification across interacting components. Avoid ambiguous requirements, surprise acceptance criteria, unsolvable tasks, and artificial timing thresholds. Default to no timeout unless explicitly requested. Verify feasibility with a known-good solution and independent valid alternative; apply the same fixed behavioral checks to every model and retain genuine failures.

Environment provisioning belongs outside the measured task. If an explicitly selected environment uses Docker, the container should already be ready before the agent starts; implementing Docker integration is not part of success unless the customer's workflow specifically calls for it. Default local execution remains unchanged.

## Self-contained task contract

Default to small, trusted local fixtures that run with one ordinary test command using an existing runtime. Prefer `python3 -m unittest`, already-installed `pytest`, `node --test`, or the language's available lightweight runner. Include all task data; use temporary directories, in-memory storage, injected clocks, fixed seeds, and in-process service fakes. No network access is needed by the task or grader. Provider API calls belong to the evaluation harness.

Do not introduce Docker, Xcode builds, simulators/devices, SwiftUI/UIKit UI testing, macOS app automation or permission dialogs, browser downloads, hosted services, or extra plugins. Do not ask customers to pick one of these setups. An explicit request for platform/integration evaluation can change this scope; ordinary discovery mentioning iOS or frontend work does not.

For iOS work, test extracted validation, formatting, routing state, parsing, or sync logic. Use a pure Swift package only when its compiler/test tooling is already available; otherwise adapt the behavior to an available runtime and disclose the language change. Do not claim extracted logic tests measure UI rendering, platform APIs, or native app builds. For frontend work, prefer state/event/markup logic with existing tools. Replace real service clients with supplied in-process fakes; use local files or SQLite instead of a server database.

Hard tasks can involve several modules, cancellation, recovery, migrations, and compatibility. Keep setup as simple as Basic tasks. Adapt benchmark methods and acceptance criteria rather than importing their infrastructure. Before paid execution, the grader must run on this device with the baseline failing for the intended defect and the oracle passing. Missing runtimes/dependencies are setup failures: simplify the task or resolve the small prerequisite before freezing, without escalating into platform installation.

## Portfolio

Propose three Basic and five distinct Hard tasks per workflow by default. The CLI seeds all eight slots; the skill adapts their focus to customer evidence and authors the actual tasks. Follow [hard-task design](../../skills/evaluate/references/hard-task-design.md). Use original tasks when suitable benchmark references do not exist. Respect explicitly narrower customer scope.

Record workflow frequency, languages/frameworks, pain points, deliverables, source provenance and testable success criteria in `discovery.json`. `portfolio DISCOVERY --suite SUITE` registers workflows in a new schema 3 suite. Validation, planning, approval and execution enforce at least three Basic and five Hard tasks per workflow. A workflow's explicitly requested `difficulties` subset requires one task per selected tier instead. Legacy schema 1/2 keep their old meanings and coverage; explicit smoke suites remain exempt. Do not silently relabel old `hard` as new Hard or rewrite signed evidence. Default to one iteration per task/model/effort, review the full first-round matrix, then seek approval for two additional rounds if wanted.

| Tier | Design | Example frontend workflow |
| --- | --- | --- |
| Basic | Bounded implementation or integration; enough regression checks to establish calibration | Filter/sort/paginate with state preservation, or a bounded async controller repair |
| Hard | Substantive repository investigation and implementation across interacting components and observable invariants | Repair an editor's shared state, persistence, routing and derived views across restart/recovery while preserving existing public behavior |

The five Hard designs should test different customer behaviors, not cosmetic variants. Counts and labels alone do not establish difficulty. Small synthetic tasks remain adaptations; neither the Hard label nor a benchmark citation establishes equality with public benchmark difficulty. The bundled async controller is a compact Basic harness fixture.

## Finding task inspiration

Public benchmark infrastructure is not the default customer setup: [SWE-bench uses Docker to run repository tests](https://www.swebench.com/SWE-bench/guides/evaluation/), and [Harbor tasks define an environment alongside instructions and tests](https://www.harborframework.com/docs/tasks). Adapt their coding behaviors and verification ideas into the local task contract above; do not claim those benchmarks have no environment requirements.

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

| Workflow | Basic calibration | Hard repository work |
| --- | --- | --- |
| API/backend | Bounded validation, pagination or cancellation change | Coordinate lifecycle, persistence, recovery and compatibility across services implemented with local fakes |
| CLI/tooling | Configuration precedence or bounded command repair | Multi-command migration with restart-safe rollback and preservation of previous formats |
| Data/performance | Bounded transformation or join | Incremental query maintenance across planning, execution and invalidation, preserving full-recompute equivalence |
| Test authoring | Regression coverage for one component | Detect distinct cross-module semantic faults while accepting independently correct implementations |
| Frontend | Filtering and navigation state integration | Shared editor state, derived views and persistence under cancellation, recovery and compatibility constraints |


## Layout

```
tasks/my-task/
  task.json
  instruction.md
  baseline/        # only material the agent may see
  oracle/          # complete known-good snapshot, never mounted to agent
  grader/          # immutable verifier, never mounted to agent
```

`task.json` also needs a `human_summary` for newly authored tasks: two or three plain-language sentences explaining the development workflow and the behavior under test. Keep detailed implementation requirements in `instruction.md`; the dashboard uses the shorter summary.

`task.json` contains `id`, `use_case`, `difficulty`, `difficulty_rationale`, `benchmark_refs`, `allowed_paths`, and `grader`. See `task.schema.json` for the schema. Grader argv uses `{candidate}` and `{grader}` placeholders and runs with no shell interpolation. Return exit 0 only when every requirement and regression passes, 1 for a behavioral failure, and another code for infrastructure/setup failure. Avoid catching every exception as success or silently skipping dependencies. Print short check results without secrets.

## Verifier quality

State ordering and precedence explicitly, with a conflicting-input example. For example: “lowest to highest: defaults, config, environment, flags; later values override earlier ones. With config=10, environment=20, flags=30, return30.” Avoid relying on a list whose direction can be interpreted differently. Distinguish missing, empty, whitespace, zero, and false when those cases affect success.

- Prove the starting snapshot fails and the oracle passes. The CLI checks both, but this alone is not sufficient proof of grader quality.
- Map every acceptance check to a visible requirement. Test an independently written valid alternative, including different permitted error wording and implementation structure. Exact prose, ordering, exception classes, private helpers, or temporary filenames must not become hidden requirements.
- Prefer a documented public fault-injection interface for storage/recovery tasks. If using standard-library patches, inject before candidate imports and cover permitted I/O alternatives. Verify cleanup and rollback through observable state, not private implementation choices. Ensure targeted broken alternatives still fail after any correction; see the task-quality review reference for examples.
- Add mutants/adversarial candidates: no-op, hardcoded example output, deny-all, ignored filter, unsafe path, removed regression test, stale async response. Check public behavior, not implementation symbols.
- Use an independent verifier process against a fresh candidate directory; keep grader files outside the candidate workspace. Local execution does not enforce isolation. Do not run candidate-supplied tests as the sole acceptance criterion. Test-authoring tasks need mutation/coverage goals plus independent behavioral checks; a new test file alone is not completion.
- Pin clocks, random seeds, data, and the existing dependency/runtime versions. Prefer synchronization events to wall-clock races. Reuse available tooling; do not download dependencies inside timed tasks. If Docker was explicitly requested, pin its image digest separately.
- Use observable state/output assertions for frontend tasks. Browser or platform integration tests require an explicit customer request and an already working setup; screenshot aesthetics are outside the default grading scope.
- Freeze before all lanes. Never repair a task after seeing which provider failed without versioning and rerunning all affected lanes under a newly approved suite.
- A historical PR can leak the answer through commit history. `snapshot` strips Git history. Do not put solutions, grader paths, benchmark answer keys, or private discovery transcripts in the agent workspace.

## Reviewing early failures

For early-run failure patterns, use `reflect` and the [task-quality review workflow](../../skills/evaluate/references/task-review.md). It separates setup problems, contract/grader defects, unrealistic scope, and genuine implementation failures. Correct defects through a new approved revision; preserve original outcomes and rerun all affected configurations fairly. Never optimize a grader merely to make an observed candidate pass.

## Repositories

Read-only `repo` discovery collects titles and metadata. Use selected `gh pr view --json ...`, `gh pr diff`, or the customer's `glab mr` equivalent for details after scope approval. Preserve a source link and commit SHA. Clone/fetch only the named customer repository with existing scoped credentials; do not enumerate unrelated repositories. `snapshot --repo PATH --commit FULL_SHA --output TASK/baseline` exports regular files; remove agent configuration files and inspect for customer secrets before evaluation. Git submodules and LFS assets need explicit materialization and review; archive alone does not supply them.
