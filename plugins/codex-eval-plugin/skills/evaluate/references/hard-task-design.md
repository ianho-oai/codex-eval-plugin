# Designing Basic and Hard tasks

New schema 3 suites have two tiers. **Basic** consolidates the former easy/medium/hard range into calibration work. **Hard** targets the former harder-1/harder-2 style: substantive engineering across a coherent repository. Existing schema 1/2 tasks and historical display labels keep their original meaning; create a newly approved suite for new work.

## Default portfolio

For each discovered customer workflow, propose three Basic and five distinct Hard tasks. The CLI seeds eight slots and enforces these counts. Use these design focuses as prompts, adapting them to customer evidence:

- **Basic localized repair:** fix a bounded defect with clear behavior and regression checks.
- **Basic bounded feature:** add a small customer-relevant capability with explicit acceptance criteria.
- **Basic component integration:** combine a few interacting requirements while preserving existing behavior.
- **Hard investigation/repair:** trace an observable defect through interacting components; repair the cause and preserve related behavior.
- **Hard feature/integration:** add a meaningful capability across existing module boundaries, preserving public interfaces and compatibility.
- **Hard state/recovery/compatibility:** maintain interacting invariants through transitions, interruption, replay, rollback or migration as relevant to the customer's workflow.
- **Hard cross-module consistency:** preserve related invariants across multiple representations, caches, derived state or public entrypoints.
- **Hard customer-critical path:** exercise another consequential end-to-end behavior identified during discovery, distinct from the other tasks.

These eight tasks are a starting portfolio, not a cap. Add tasks when distinct customer behaviors need coverage. Vary the Basic tasks across the former easy/medium/hard range and keep more Hard tasks overall. Review the proposed count and execution matrix before paid runs; do not generate cosmetic duplicates simply to reach a quota.

Do not force irrelevant recovery behavior into a stateless workflow. Substitute another substantive customer-grounded Hard design and explain it. Use unique task IDs and different behavioral contracts, not cosmetic variants. An explicitly requested workflow `difficulties` subset instead seeds/requires one task per selected tier; never infer this reduction just to bypass coverage. Show the concrete task/model/effort/repeat count before execution approval.

## What qualifies as Hard

Require meaningful repository navigation and changes across interacting components, with several related observable rules that must hold together. For example, query planning affects execution and cache invalidation; event corrections affect projections and checkpoints; schema migration affects readers, writers and restart behavior. Frontend tasks can exercise shared state, routing, persistence and derived views through pure logic without installing a browser.

Before approval, explain:

- Which customer behavior and evidence motivated the task.
- Which components interact and why a local patch alone is insufficient.
- Which invariants and regressions the verifier checks, including meaningful failure or compatibility paths.
- What a plausible incomplete fix would miss, and how it is detected.
- What context makes the problem solvable without revealing the implementation.

More files, boilerplate, prompt length, artificial sleeps and slow setup do not establish greater difficulty. Do not target a high success rate by shrinking substantive requirements, and do not tune tasks to a provider win. Success remains the fixed verifier result. Difficulty is a design target, not a claim of measured equivalence to DeepSWE or any public benchmark.

## Reference tasks and verification

Keep using the repo's reference library: 1,658 metadata records and 46 design cards. Search `examples --query 'customer workflow' --inventory`; inspect the original instruction/verifier sources for relevant mechanical-only matches. The [DeepSWE source](https://github.com/datacurve-ai/deep-swe) provides long-horizon repository engineering examples and behavior-focused verification. Its upstream task scope is inspiration; portable synthetic adaptations are not official benchmark reproductions or calibrated scores.

A good original task is preferable to a weak citation. For original designs, use `provenance.kind: original`, explain the workflow need, and leave `sources` and, when appropriate, `benchmark_refs` empty. For benchmark-inspired designs, retain exact catalog source links and a concrete adaptation explanation. Do not copy upstream solutions or imply every indexed verifier was audited.

Keep setup self-contained with an existing lightweight test runner, bundled fixtures and in-process service fakes. Repository complexity belongs in behavior, not provisioning. Default to no agent/grader timeout unless explicitly requested. Before paid execution, require the intended baseline to fail, the oracle and an independently valid alternative to pass, and targeted incomplete fixes to fail. Grade observable requirements rather than matching the oracle's code structure or private names. Follow the adaptive task-quality review loop and preserve genuine failures. Apply changes only to new proposals or newly approved revisions, never to a frozen running suite.
