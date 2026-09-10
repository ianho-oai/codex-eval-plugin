# Provider troubleshooting

Start a customer evaluation with the [starter prompt](../CUSTOMER_STARTER_PROMPT.md). This page explains setup failures before or during execution.

## Doctor versus model access

`./eval doctor SUITE` checks the configured CLI version, required flags, API-key presence, and cataloged minimum CLI versions. It does **not** make an authenticated inference request. Its per-model `account_access: not_probed` field is explicit: passing doctor is not proof that the account can run a model or every effort level.

Check account-visible IDs with `./eval models --refresh --provider claude` (or `codex`) from a terminal permitted to reach that provider. Confirm exact model IDs and use a small approved selection before a large sweep. The existing `smoke --provider claude` uses its default model and is not a Fable/Mythos access test.

Before final approval, run `./eval doctor SUITE --check-model-access`. It performs the local checks and an authenticated model-list request for each selected provider, compares exact IDs, and exits nonzero on local errors, missing IDs, or failed listing requests. It does not make inference calls or alter the suite. `listed` is not proof of native agent/effort support; confirm uncertain configurations with a small approved task. Missing aliases require explicit verification. If the host blocks requests, have the customer run the command in their permitted terminal and inspect its output.

Check the exact executable path after an upgrade: multiple installations can coexist. An outdated path must be replaced in the new suite pin even when the terminal's default command is current.

## Fable: installed Claude Code is too old

Observed on 2026-09-10: native Claude Code 2.1.220 rejected `claude-fable-5-1`, explicitly requiring **2.1.251 or newer**. This is a provider compatibility error before task execution. The catalog now records that minimum and preflight prevents that lane from launching with an older CLI. Compatible model lanes can still run.

In your terminal:

```sh
claude update
claude --version
```

New suite templates pin 2.1.251; use the actual installed version and binary path when preparing your suite. A newer CLI also requires updating the suite's exact version pin before validation and approval. Updating your terminal command does not update a separately pinned binary or Docker image.

## Mythos: excluded by default

Observed on 2026-09-10: native Claude Code reported that `claude-mythos-5-1` may not exist or the account may lack access. This error does not identify which cause applies. Updating Claude Code is a useful prerequisite, but does not establish or grant Mythos access.

Mythos is excluded from new default suites. Add it only on explicit request after verifying access and native support. After updating, list the account-visible models:

```sh
./eval models --refresh --provider claude
```

Confirm the exact ID and availability for the same key used by the runner. If the model remains unavailable, retain that finding and choose whether to wait for access or approve a narrower matrix. Do not silently replace it with another model or classify it as a failed coding task.

## Recover without losing evidence

1. Stop new dispatch for an affected active run by creating `RUN_DIR/stop-requested.json`; active attempts drain and are saved.
2. Preserve the existing suite, engine, approvals, and results. `--resume` is for identical sealed inputs, not a changed CLI or model configuration. Completed provider-error rows are not automatically rerun.
3. Prepare a new suite directory with copied task fixtures, the updated exact CLI pin, and the intended model/task/effort selection. Validate its graders, review the plan, and approve the new inputs.
4. Run to a new output directory, starting with a small selection. Expand only after confirming support, validating and approving the expanded plan.

Rate-limit responses receive bounded automatic retries. CLI incompatibility, authentication, unavailable-model errors, and failed task checks do not. Updating software does not repair historical results; new attempts supply new evidence.

If the agent's host blocks a provider endpoint, run the supplied command in your own permitted terminal. Keep keys in the environment or ignored `.env.local`; never paste them into chat or logs.

## Resetting confirmed setup errors

An explicit user-requested reset may remove confirmed native CLI-version errors from active report/dashboard comparisons while preserving signed result files and native events. The per-run `reset-version-errors.json` receipt identifies each result and event-log hash, requester, and reason. The reader verifies every original artifact, permits only matching native version errors, and exposes those originals in `reset_rows`. It does not convert failures into passes or retry an old CLI pin.

Explicit model removals use a per-run `excluded-models.json` receipt with provider/model pairs, requester, and reason; these remove that model's points and pending cells from active views. Original records remain accessible in `excluded_rows` and on disk. Removing either receipt restores the original view. A view exclusion does not cancel an active runner; request a graceful pause separately.

Replacement attempts use fresh validated suites, updated pins, new output directories, and the same task/effort settings. Their pending cells count once in the active comparison. Raw evidence and recorded spend remain in the original artifacts even when excluded from the active view.
