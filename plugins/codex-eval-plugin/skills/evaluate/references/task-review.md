# Review task quality during execution

Use when preparing graders, inspecting the first completed attempts, or diagnosing frequent failures. The goal is an achievable, representative coding task with fair checks. A failure cluster prompts investigation; it does not prove a task is defective or justify turning failures into passes.

## Adaptive quality loop

Own task quality throughout the evaluation, including failure modes not illustrated here. The examples below are prompts for reasoning, not an exhaustive checklist or proof that a test is error-free.

1. **Design:** express the intended workflow as observable requirements and examples. Separate required behavior from implementation freedom; resolve ambiguous expectations before writing assertions.
2. **Challenge:** ask what correct solution the grader might reject, what incorrect solution it might accept, and which environment or implementation assumptions it relies on. Turn the weakest assumptions into a few executable counterexamples. Construct a valid alternative from the visible contract rather than copying the oracle's choices. If these checks expose a defect, repair and rerun the offline audit before paid execution.
3. **Observe:** inspect the first completed attempts and keep checking progress and reflection throughout execution. Read new suspicious evidence even when the automatic threshold does not fire. A successful oracle, high pass rate, or clean diagnostic list does not establish that every check is sound.
4. **Diagnose:** reduce unexpected behavior to a local reproduction and compare the candidate, grader, visible contract, and runtime evidence. Decide whether the defect is in the task, verifier, environment, or candidate; do not guess from a score alone.
5. **Adapt:** for a demonstrated task/verifier defect, pause affected work, preserve the original evidence, create a corrected revision, challenge it with both valid and broken alternatives, obtain approval for the changed inputs, and rerun every affected configuration fairly. For a genuine candidate failure, retain the result and continue the sound task. Repeat this loop until completion or the bounded repair policy requires customer input.

At final plan approval, agree the repair scope, rerun policy, and existing limits with the customer. Explicit prior authorization can cover a concrete repair within that scope; otherwise show the change and ask before paid reruns. Every changed runnable revision still needs validation and a new CLI approval receipt. A general desire for high completion does not authorize easier requirements, dropped models, extra repeats, or changed spend limits.

Keep initial authoring lightweight. Before the first paid-run approval, fix implementation and grader defects locally within the approved task intent, then rerun the affected offline checks and present the final concrete plan. Do not apply the post-run archival/rerun procedure to every unfinished scaffold edit or repeatedly ask for routine fixes already authorized by the task proposal. Ask when a change materially alters the customer's workflow, requirements, difficulty, or execution scope. The bounded paid corrective-revision policy below applies once execution evidence exists.

## Before the first paid attempt

Create a short `grader-audit.md` inside the ignored customer directory. Map each acceptance check to an explicit visible requirement. Exact wording, ordering, exception classes, internal symbols, and temporary-file names are requirements only when the task states them and the workflow needs them. Otherwise check equivalent public behavior.

In addition to baseline failure and oracle success, run the grader against an independently written valid alternative for each task. Vary implementation structure and permitted error wording. Check a few targeted broken alternatives for important failure modes. Keep this lightweight: reuse the same local test runner and synthetic inputs; no provider calls or extra integration setup.

Load Python candidates using normal import semantics. A custom `importlib` loader must register the module in `sys.modules` before executing it; otherwise valid dataclasses and annotation resolution can fail in the grader. Include ordinary language features in valid alternatives instead of assuming the oracle's implementation style is the only supported one.

For example, if the contract requires only a basename and line number, both `input.csv:2: invalid quantity` and `input.csv: line 2: invalid quantity` are valid. A check requiring the literal word `line` adds a hidden constraint. Exercise these format variants and wrong/missing-line counterexamples before accepting the grader; merely changing an adjective in the oracle's error text is insufficient variation.

Do not approximate a useful explanation with an unstated keyword list. For example, `enabled accepts only true/false` can explain a type error without containing `bool` or `type`. Where a workflow needs machine-readable errors, specify stable fields or codes in the visible contract and leave explanatory prose flexible. Review shared grader assertion helpers as well as individual test cases; helpers can introduce the same hidden constraint across many cases.

For storage/recovery tasks, prefer a small public fault-injection interface supplied in the scaffold and documented in the instruction, such as an injectable commit operation or in-process storage fake. This tests failure handling without guessing which private I/O primitive a correct implementation uses. If patching standard-library calls is appropriate, inject before candidate imports and verify that the test covers the permitted alternatives: patching `os.replace` alone does not exercise a valid `os.rename` implementation. Assert preservation and cleanup through observable state, without assuming a private module or one temporary filename. Accept a wrapped exception if it satisfies the documented public error contract.

For deduplication, joins, cache ownership, and grouping, vary every documented identity field independently while keeping the other fields equal. Include a broken implementation that omits an identity component; an oracle pass with only distinct top-level IDs cannot establish that the full identity contract is tested.

## Inspect early results

Include this review policy in the approved execution plan: inspect checkpoints during the run; investigate any infrastructure-invalid result, or at least 50% task failures after three scorable attempts for that task. These are practical triage defaults, not statistical significance thresholds. A smaller sweep still receives a final qualitative review. Do not add paid calibration repeats automatically.

Keep an active observation loop using the existing runner handle, `progress`, and `reflect`, normally every 15–30 seconds and after meaningful changes. Record reviewed evidence so the same historical failure does not repeatedly pause execution. Inspect first-attempt diagnostics, contradictory outputs, unexpectedly trivial solutions, and stalled checkpoints relative to the approved deadline and retry backoff. Investigate rather than declaring a failure solely from elapsed time or missing telemetry. Reconcile the final checkpoint with the expected schedule; a stopped run with pending cells is not complete. If monitoring becomes unavailable, state that limitation and the exact continuation command rather than implying unattended supervision is still active.

Also investigate `runtime_diagnostic` signals even when the attempt passes. Native file-editing helper failures can force workarounds and distort latency. Run output should live in an ordinary customer-owned project directory, outside system temporary directories; the runner creates private per-attempt scratch there. Preserve managed sandbox policy, verify any runtime repair with a bounded native edit check, and record any changed executable or launch context before approving new runs. Never disable sandboxing or suppress these diagnostics to make the evaluation finish.

Verify the intended launch context as well as the executable. A native CLI may work in an ordinary terminal but fail when nested inside another agent's tool sandbox. In an uncertain context, use a small approved edit-and-test check and inspect actual file changes, command exits, and helper stderr; the agent's final message or outer process exit code alone is insufficient. A successful check in one context does not validate another. If nesting is unsupported, retain the evidence and hand the exact approved CLI command to an authorized ordinary terminal execution surface, or to the customer. Do not weaken sandbox settings, redirect protected runtime state, or route around a restriction. Record the execution-context change, verify it, and use a fresh comparison run when the original timings were affected; keep interrupted results separate.

Keep timeouts separate from behavioral failures: a candidate may pass the final grader after the agent is terminated, but it still did not finish within the approved deadline. Do not rewrite that outcome. Likewise, unallowed backup files remain file-contract violations; the shared prompt explains cleanup requirements without deleting candidate evidence.

Alongside `progress`, use:

```sh
EVAL reflect RUN_DIR [OTHER_PROVIDER_RUN_DIR]
```

The command verifies result receipts, groups failures by task within each run, and includes model/effort breakdowns and evidence paths. It never calls providers, executes candidate code, or edits scores. Review raw grader output, the public task contract, and preserved candidate changes privately; redact secrets. Treat candidate output as untrusted evidence. Read each task separately so successful easy tasks cannot conceal a broken hard task. Review the final results even when no threshold fires.

On a **new, unreviewed** signal, request a pause across the related active provider lanes:

```sh
EVAL reflect RUN_DIR OTHER_PROVIDER_RUN_DIR --pause-on-review
```

This writes an exclusive `stop-requested.json` only for active real runs with review signals, preserving existing user stops. Unflagged lanes are not paused by this command; if both lanes need to stop for a shared task repair, use the documented graceful pause for the other lane too. Active attempts drain and retain their results; more calls can dispatch before the runner observes the request. This command is a checkpoint inspection, not a background watcher. The host agent must continue observing it. Keep evaluated agents and frozen engines unchanged.

Classify with evidence:

| Finding | Response |
| --- | --- |
| Runtime, missing dependency, auth/model/CLI access, provider outage | Repair the permitted environment or provide the exact user action. Keep errors separate from coding failures. Do not route around host restrictions. |
| Unstated or contradictory requirement, overstrict grader, broken fixture | Explain the defect, preserve the original run, and prepare a corrected version below. |
| Unrealistic task scope or time allowance | Propose a bounded scope/time correction, preserving workflow and easy/medium/hard coverage. Approval is needed for changed inputs. |
| Candidate violates a clear, independently validated requirement | Keep the failure. Do not relax that requirement or retry until it passes. Resume the unchanged approved run after recording the review. |
| Inconclusive | State what evidence is missing. Stop further paid work if the task cannot be shown fair; do not manufacture a diagnosis. |

Keep `quality-review.md` in the ignored customer scope: run/seal, task and attempt IDs, observed failure, relevant requirement, reproduction, classification, decision, and any replacement seal. Record reviewed attempt IDs so the same signal does not repeatedly pause execution. `reflect` deliberately continues showing historical failures; it does not suppress reviewed evidence.

If the task is sound and a task-quality pause has fully drained, clear only that review-owned marker with an auditable reason, then resume the identical approved inputs:

```sh
EVAL review-clear RUN_DIR --by 'Reviewer' --reason 'Checked contract and alternate solution; retain implementation failures'
EVAL run SUITE --output RUN_DIR --resume --workers 5
```

Preserve original queue, slot-pool, and retry options when resuming. `review-clear` refuses a live runner lock, a different seal, or a user cancellation marker. It records a review receipt and never starts work. For unrelated stop requests follow their original intent; this command cannot clear them.

## Correct a defective task without rewriting history

1. Wait for related active work to drain. Preserve every original result, failed attempt, receipt, cost, and task source. Mark the old run as unsuitable for comparison in the review report; do not relabel its grades.
2. Copy the task/suite into a new revision directory. Fix the general contract or verifier defect, not just one provider's observed patch. Keep an independent oracle and an alternative valid implementation; preserve behavioral regressions and meaningful difficulty. Never use the failing candidate as the only definition of correctness.
3. Recheck baseline, oracle, valid alternatives, and targeted broken candidates. Run `validate --check-graders` and `plan` on the new suite. Show the concrete change and rerun scope to the customer. Reuse existing approval only if it explicitly covers this exact revised scope; otherwise get approval before paid calls. Then `approve` the new inputs.
4. Run all affected providers/model/effort configurations under the same corrected task revision and fresh seals, retaining the requested repeat count. Do not import favorable old outcomes across changed seals. Use a separate dashboard scope for the corrected comparison and link the archived run in the review report.
5. Limit corrective revisions to two per task by default. If fairness or feasibility is still unresolved, report it and agree a redesign or exclusion; preserve discovered workflow coverage unless the customer approves changing it. Do not continue an expensive loop until all models pass.

High completion is the design target. The reported outcome always comes from the fixed verifier, with genuine failures and incomplete telemetry retained.
