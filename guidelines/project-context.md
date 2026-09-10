# Project context

**When to read:** Before changing the evaluation contract.
**When to update:** When behavior, assumptions, or verified limitations change.

## Contract

Customer discovery combines interview, opt-in local history, and selected repository/PR/MR evidence. The single skill designs customer-specific tasks; the CLI freezes, validates, approves, executes, grades, normalizes, resumes, and displays them. No AI is used to construct dashboards or to decide scores after approval.

Compare native Codex and Claude Code agents using API-key authentication. Their built-in prompts and tool implementations differ; this is a product-and-model comparison, not a controlled model-only experiment. Deterministic orchestration does not imply deterministic inference. Use repeated trials and retain every scheduled cell.

Default execution is local, using self-contained trusted task fixtures, clean candidate directories, a separate verifier process, and existing lightweight test runners. Do not add Docker, platform SDKs/simulators, SwiftUI/UIKit UI tests, desktop integrations, browser downloads, or external services during ordinary discovery/task design. For native-app workflows, extract representative logic and disclose the narrower coverage and any language adaptation. Difficulty comes from behavior and interacting modules. Local execution cannot enforce held-out-test secrecy or host isolation; do not label it hermetic. Docker remains an explicitly requested advanced option, with pinned images and separate verifier containers.

Scores are binary. Infrastructure errors and interrupted attempts score zero in the all-attempt summary but are separately categorized. Scorable success rates exclude infrastructure-invalid rows and always display their count. Missing usage is null. With an explicit spend stop, unknown spend unrelated to authorized rate-limit retries pauses execution because the threshold cannot be enforced from missing telemetry. By default no spend stop is configured, and missing telemetry is retained without stopping dispatch.

The spend threshold is checked before queue dispatch. In-flight calls can overshoot it; provider-side limits remain necessary for a hard billing cap. No automatic provider fallback or silent model substitution. Explicit rate-limit failures have bounded automatic retries; other failures do not.

Current official sources expose OpenAI 5.6 Sol/Terra/Luna and GPT-6 Astra. Model IDs and pricing are dated snapshots; account access must be probed and reviewed before use. A user-run Claude Sonnet 5 smoke test passed and its saved results were verified locally. The agent session's Anthropic endpoint remains restricted; user-terminal success does not establish agent-session access. See VALIDATION.md for measured coverage.

New customer suites use schema 2: declare workflows and cover every workflow at easy/medium/hard difficulty. Task provenance names a catalog source and adaptation or explains an original design. Offline catalog scope and refresh instructions live in `ceval/data/catalog.md`. Schema 1 remains readable for historical runs; smoke suites are explicitly exempt from customer portfolio coverage.

The skill is explicit-only: `skills/evaluate/agents/openai.yaml` disables implicit invocation, and its entrypoint requires a user request for Codex-versus-other-agent evaluation tests. General coding/testing and plugin maintenance do not trigger it. Local history skips recognized automatic approval-review transcripts and reports truncation and parser completeness separately; none of these counters proves exhaustive semantic workflow review.

The dashboard is chart-first: “Workflow evaluation,” X-axis/Y-axis selectors limited to shared total-cost/end-to-end-latency/token metrics on a separate row, grouped model checkboxes, task checkboxes grouped by difficulty, provider-colored points when any repeat passes and grey points when none pass, without an outcome filter, toggleable model-name point labels without connectors, and six-field hover/focus popups (model, task, difficulty, pass/fail, total cost, end-to-end latency). A task summary table lists descriptions, difficulty, and development type; model summary tables, summary cards, combined-run badges, and explanatory footer sections are omitted. New runs snapshot task descriptions; older runs use matching local definitions when available. Detailed telemetry/provenance remains in reports and exports. Codex is blue300 (#339cff) from the OpenAI developer palette; Claude stays orange.


New runs default to three repeats (including smoke). Chart points are arithmetic means within a run/task/provider/model/effort; failures remain included, missing values remain null, and mixed/partial outcomes disclose pass/repeat counts. Never average separate runs or effort configurations. Task tables use authored `human_summary` text, with a concise metadata fallback for older runs. Select-all toggles operate globally and by difficulty/provider.

`configure` selects models, task IDs, and repeats before validation/approval; optional suite `selection.task_ids` narrows execution while keeping the complete designed portfolio. `dashboard --scope` stays within the supplied simulation directory or run, combining both providers there. Default unscoped dashboards still discover all live evaluation runs.

Each axis has an independent logarithmic toggle. Nonpositive measurements are explicitly counted as unplottable on log axes; values are never shifted or silently changed. Provider checkbox groups use the same blue/orange palette as successful points.

The run CLI defaults to a five-worker queue with immediate refill. `--workers 1` restores sequential execution; shared `--slot-pool` directories enforce a combined limit across batches. Scheduler metadata records workers, implementation hash and concurrency caveat. A single coordinator writes checkpoints; stop requests, unknown spend and budget thresholds drain active work before stopping.

New suites expand every selected model across its catalog-supported efforts. `configure --all-efforts` expands existing suites; repeated `--effort` narrows to levels supported by every selected model. Customer plans disclose capability exclusions, and model labels include effort. One-repeat quick sweeps are supported without changing the three-repeat general default.

### Default model sweep and spend policy

New evaluations default to all cataloged GPT-5.6 models and GPT-6 Astra, plus all cataloged Claude models, across every supported single-agent effort level. Preflight lists the exact matrix and repeats, announces **no spend stop**, and tells the customer to specify otherwise before approval. Limited-access models are included; unavailable lanes remain visible.

`configure SUITE --all-models --all-efforts --no-spend-stop` restores these defaults. Select alternatives with repeated `--model PROVIDER:MODEL` / `--effort LEVEL` flags. Set an optional stop with `--spend-stop-usd AMOUNT`. A null `limits.spend_stop_usd` disables both the scheduler spend stop and Claude's native budget flag; missing costs remain null and do not stop dispatch in this mode. Time limits, turn limits, bounded rate-limit retries, and explicit pause requests still apply. Existing approved suites retain their frozen settings.
