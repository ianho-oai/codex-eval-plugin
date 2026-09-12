# Designing both kinds of hard task

For each discovered workflow, propose a focused hard task and a separate repository-reasoning hard task alongside easy and medium tasks. Both remain `difficulty: hard`; use `difficulty_rationale` and the two- or three-sentence `human_summary` to explain the distinction. This is an authoring convention, not a calibrated public benchmark difficulty rating. Respect explicit customer limits and disclose any missing coverage.

## What makes the additional task different

A focused hard task tests a demanding bounded change, such as reliable restart recovery or graceful service shutdown. A repository-reasoning hard task requires understanding how several modules jointly implement behavior and making a change without breaking those relationships. Keep the focused task; do not merely rename or enlarge it.

Build a coherent fixture with public entrypoints, meaningful module boundaries, existing behavior, and regression checks. The solution should require tracing a real interaction: for example, planning affects execution and cache invalidation, corrections affect multiple projections and checkpoints, or permissions must survive query planning and cached execution. Adapt these patterns to the customer's workflow rather than reusing the same three examples universally. Frontend work can exercise state, routing, validation, persistence, and derived views through pure logic without launching a browser.

Before approval, explain which modules interact, which observable rules must hold together, and why a local fix alone is insufficient. Add more distinct tasks when needed to represent different workflow behaviors, while keeping the proposed task count and execution cost visible. More files, boilerplate, obscure instructions, artificial sleeps, or a slow environment do not establish greater difficulty. Set a feasible shared time limit from the work involved; do not guarantee a five- or ten-minute duration.

## Sources and verification

Search the local benchmark catalog for relevant ideas. A good original task is preferable to a weak citation. For original designs, record `provenance.kind: original`, explain the workflow need in `rationale`, and use empty `sources` and, when appropriate, `benchmark_refs`. For benchmark-inspired designs, retain exact source links and describe the adaptation. Neither kind is an official benchmark result.

Choose representative work without optimizing for a provider win. Supply enough public requirements and context to make the task solvable. Keep setup self-contained, with bundled fixtures, in-process fakes, and a single lightweight deterministic grader command. Challenge the grader with a known-good solution, an independently valid alternative, the broken baseline, and plausible partial fixes that miss a cross-module rule. Follow the existing task-quality review loop; preserve genuine failures rather than weakening sound checks.

The `portfolio` CLI generates three seed slots per workflow. Expand its proposal with the additional hard task and register each approved authored directory in `suite.tasks`; passing the CLI's minimum coverage validation alone does not prove this design policy was followed. Show the full task/model/effort count before execution approval. Apply this guidance to new proposals or explicitly approved revisions, never by changing a running suite's frozen tasks or scores.
