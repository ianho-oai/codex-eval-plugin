# Task design

Read when converting approved workflows into runnable tasks. See `benchmarks.json` for the dated public source index, and `examples/` for three small original harness-validation tasks. They demonstrate easy/medium/hard mechanics; they are not substitutes for a customer's representative portfolio or an official benchmark score.

## Evaluation objective

Design for successful completion by the selected models. The primary comparison is the time, tokens, and cost needed to produce a verified correct result. Use realistic, bounded engineering tasks with clear requirements, sufficient context, supplied fixtures, and reasonable time limits. Easy/medium/hard should increase coding effort and behavioral complexity while retaining the same simple setup. Avoid ambiguous requirements, surprise acceptance criteria, intentionally unsolvable tasks, and tight timing thresholds that turn host load into a coding failure. Verify feasibility with a known-good solution before freezing. Keep genuine failures visible and apply the same fixed checks to every model; expected completion is a design target, not an assumed score.

Environment provisioning belongs outside the measured task. If an explicitly selected environment uses Docker, the container should already be ready before the agent starts; implementing Docker integration is not part of success unless the customer's workflow specifically calls for it. Default local execution remains unchanged.

## Self-contained task contract

Default to small, trusted local fixtures that run with one ordinary test command using an existing runtime. Prefer `python3 -m unittest`, already-installed `pytest`, `node --test`, or the language's available lightweight runner. Include all task data; use temporary directories, in-memory storage, injected clocks, fixed seeds, and in-process service fakes. No network access is needed by the task or grader. Provider API calls belong to the evaluation harness.

Do not introduce Docker, Xcode builds, simulators/devices, SwiftUI/UIKit UI testing, macOS app automation or permission dialogs, browser downloads, hosted services, or extra plugins. Do not ask customers to pick one of these setups. An explicit request for platform/integration evaluation can change this scope; ordinary discovery mentioning iOS or frontend work does not.

For iOS work, test extracted validation, formatting, routing state, parsing, or sync logic. Use a pure Swift package only when its compiler/test tooling is already available; otherwise adapt the behavior to an available runtime and disclose the language change. Do not claim extracted logic tests measure UI rendering, platform APIs, or native app builds. For frontend work, prefer state/event/markup logic with existing tools. Replace real service clients with supplied in-process fakes; use local files or SQLite instead of a server database.

Hard tasks can involve several modules, cancellation, recovery, migrations, and compatibility. Keep setup as simple as easy tasks. Adapt benchmark methods and acceptance criteria rather than importing their infrastructure. Before paid execution, the grader must run on this device with the baseline failing for the intended defect and the oracle passing. Missing runtimes/dependencies are setup failures: simplify the task or resolve the small prerequisite before freezing, without escalating into platform installation.

## Portfolio

The agent should propose easy, medium, focused hard, and repository-reasoning hard tasks per workflow by default, expanding the CLI's three seed slots. Both hard types use the current `hard` schema label and distinct difficulty rationales. Follow [hard-task design](../../skills/evaluate/references/hard-task-design.md); use original tasks when suitable benchmark examples do not exist. Respect explicitly narrower customer scope.

Record workflow frequency, languages/frameworks, pain points, deliverable, source provenance, difficulty, and testable success criteria in `discovery.json`. New customer suites require at least one easy, medium, and hard task for **each** declared workflow. Declare workflows in discovery.json, then use `portfolio DISCOVERY --suite SUITE` to register them. Suite schema 2 enforces this at validation, planning, approval, and execution; legacy schema 1 and explicit developer smoke suites remain supported. Avoid over-weighting many small tasks merely because they are cheap. Default to one iteration per task/model/effort. Complete and review the entire first-round matrix, then ask approval for two additional iterations of the same configurations (three total); never add repeats automatically. Document any sampling choices. A task should have enough context for a headless agent to finish without clarification.

| Difficulty | Design | Example frontend workflow |
| --- | --- | --- |
| Easy | Localized behavior with clear inputs/outputs | Fix accessible labels, empty state, or formatting; validate semantic DOM and regressions |
| Medium | Several interacting constraints | Filter/sort/paginate correctly while preserving state and immutability |
| Hard | Multi-stage or cross-module behavior | Async search with cancellation, stale results, keyboard navigation, disposal, and backward compatibility |

Hard customer tasks should include interactions across a small self-contained repository where the workflow warrants it. Merely adding more edge cases to a small function is not equivalent to DeepSWE's long-horizon scope. The included async controller is a compact validation example.

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
