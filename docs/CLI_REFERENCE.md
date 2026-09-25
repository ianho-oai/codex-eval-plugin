# CLI reference

Run directories should live under your project, outside system temporary directories. Local attempts use private scratch beneath their result directory and preserve the installed toolchain PATH. `reflect` also flags native helper/sandbox diagnostic codes independently of pass/fail; investigate those signals before interpreting timings. Missing cost is unknown, including after timeouts, and a known-spend upper estimate does not bound attempts with missing costs.

Codex evaluation shells use `allow_login_shell=false` so login startup scripts do not reactivate unrelated virtual environments or alter task behavior. This uses the supported [Codex configuration](https://developers.openai.com/codex/config-reference/) and preserves managed sandbox requirements. Verify the selected language runtime with the same invocation used by the grader before approving tasks.

Customer entry point: [setup and starter prompt](../CUSTOMER_STARTER_PROMPT.md). The prompt guides discovery and uses these commands after approval. This page is the manual reference for developers and operators. Commands assume the repository root; for an installed or extracted plugin, replace `./eval` with `python3 /path/to/codex-eval-plugin/bin/codex-eval`.

### Run a real evaluation

```sh
./eval init evaluations/customer
# Complete discovery.json.workflows and propose three Basic and five Hard tasks per workflow:
./eval portfolio evaluations/customer/discovery.json --suite evaluations/customer/suite.json --output evaluations/customer/portfolio.json
# Replace example tasks with approved customer tasks, workflow IDs, and provenance.
# Use self-contained fixtures and existing local test runners. No Docker setup.
# Pin local CLI versions/paths and validate the task grader before paid calls.

# Set OPENAI_API_KEY and ANTHROPIC_API_KEY in your environment or ignored .env.local.
# Never put keys in the suite or chat; exported values take precedence over .env.local.
./eval models
./eval doctor evaluations/customer/suite.json
./eval validate evaluations/customer/suite.json --check-graders
./eval plan evaluations/customer/suite.json
# After the customer approves the displayed plan:
./eval approve evaluations/customer/suite.json --by 'Customer reviewer'
./eval run evaluations/customer/suite.json --output evaluations/customer-run
./eval report evaluations/customer-run
./eval dashboard evaluations/customer-run
```

The starter matrix covers the public OpenAI 5.6 Sol/Terra/Luna and GPT-6 Astra models, plus the cataloged Claude Fable/Opus/Sonnet/Haiku lineup, using a dated catalog. Edit `matrix` to choose explicit model IDs, effort settings, and repeats. Default sample matrix: **3 tasks × 36 model/effort configurations × 1 repeat = 108 calls**. There is **no spend stop by default**. Do a small smoke run first. Doctor checks local CLI versions, required flags, keys, and known model minimum versions; account access still needs a live check; unavailable lanes are never silently removed. `models --refresh --provider codex|claude` lists account-visible IDs without modifying the suite. Limited-access models remain included and explicitly marked; account access is not guaranteed.

New suites use local execution by default. Pin existing local CLI versions/paths and use small, self-contained tasks with unittest, already-installed pytest, Node tests, or an equivalent available runner. For iOS workflows, test extracted logic without Xcode, simulators, or SwiftUI/UIKit UI testing. Docker remains available only when explicitly requested with `init ... --mode docker`; it is not part of the default customer flow. Local mode cannot guarantee host or grader isolation and is labeled as such in results. If a CLI launcher downloads or updates at runtime, pin the resolved native binary instead.

New suites and smoke tests default to **no agent or grader timeout** (`limits.agent_seconds: null`, `limits.grader_seconds: null`) for all selected providers. Readiness probes also remain unlimited by default. To impose a limit, set either field to a positive number of seconds in the unapproved suite, then validate and approve it. Explicit numeric readiness limits remain capped at 120 seconds for agents and 30 seconds for graders. Retry attempts each receive the configured limit; retry waiting is additional. Changing an approved limit requires a new suite revision and output directory; it does not extend an in-flight process or rewrite historical timeouts.

### CLI map

| Command | Purpose |
| --- | --- |
| `init DIRECTORY` | Create a customer-owned suite and discovery record |
| `history --provider ... --consent --output FILE` | Read approved JSONL user-message history, default last three months (90 days) |
| `discovery-report DISCOVERY --evidence FILE --output coverage.json` | Generate JSON/Markdown source coverage and workflow confirmation receipt |
| `repo --path PATH --output FILE` | Read local Git workflow evidence |
| `repo --provider github --repo OWNER/REPO --output FILE` | Read merged PR metadata through `gh` |
| `repo --provider gitlab --repo GROUP/REPO --host HOST --output FILE` | Read MR metadata through `glab` |
| `snapshot --repo PATH --commit FULL_SHA --output TASK/baseline` | Export a regular-file snapshot without Git history |
| `examples --query TEXT [--inventory]` | Search offline task design examples and upstream metadata |
| `portfolio DISCOVERY --suite SUITE --output FILE` | Seed three difficulty slots per workflow and register coverage; the skill adds a distinct repository-reasoning hard task before approval |
| `benchmarks`, `models` | Inspect dated methodology/model catalogs |
| `validate SUITE --check-graders` | Verify schema, paths, baseline failure, and oracle success |
| `plan SUITE`, `approve SUITE --by NAME` | Review and seal exact inputs |
| `run SUITE --output RUN [--resume]` | Run or resume the identical sealed matrix |
| `report RUN`, `dashboard RUN` | Summarize, export CSV, and serve localhost UI |
| `export --output dist` | Produce a reproducible standalone plugin ZIP and checksum |

## What gets measured

- **Completion:** 1 or 0, determined by the external behavioral grader and allowed-change checks.
- End-to-end, native-agent, and grader latency.
- Input/output/cache-read/cache-write/reasoning tokens where available.
- Native turns with their provider-specific unit, plus tool calls.
- Claude Code's reported cost and OpenAI rate-card estimates with pricing provenance and an uncertainty envelope.
- Success rates, infrastructure-invalid counts, pending cells, and cost per verified success including failed-attempt spend.

Missing values remain null. Agent assertions and CLI exit 0 alone do not prove completion. Native harnesses and tokenizers differ; this is a **product/model configuration comparison**. Model outputs and provider caches remain nondeterministic. OpenAI CLI aggregates may not identify exact cache-write or context-tier charges; displayed estimates are not invoices. An optional spend threshold is checked before dispatch and can overshoot by the cost of all in-flight calls.

Read the [methodology](../plugins/codex-eval-plugin/ceval/data/methodology.md) and [task-design guide](../plugins/codex-eval-plugin/ceval/data/task-design.md).

## Public benchmark reference library

The plugin bundles original summaries and links to [Datacurve DeepSWE](https://github.com/datacurve-ai/deep-swe), [SWE-bench](https://www.swebench.com/SWE-bench/guides/evaluation/), [Terminal-Bench](https://www.tbench.ai/), [Harbor](https://www.harborframework.com/docs/tasks), and [Aider Polyglot](https://aider.chat/docs/leaderboards/). It does not redistribute benchmark datasets. Imported tasks and source repositories need their own license review. The customer suite is not an official benchmark reproduction.

## Distribution

The complete standalone plugin is in [`plugins/codex-eval-plugin/`](../plugins/codex-eval-plugin/). It has exactly one skill and includes its CLI, reference catalog, examples, schemas, and dashboard. No connector, MCP server, or extra runtime skill is required.

Install from the public repository in Codex:

```sh
codex plugin marketplace add ianho-oai/codex-eval-plugin --ref master
codex plugin add codex-eval-plugin@codex-eval
```

```sh
./eval export --output dist
# Extract the ZIP, then run without this parent repository:
python3 codex-eval-plugin/bin/codex-eval self-check
```

Source: [ianho-oai/codex-eval-plugin](https://github.com/ianho-oai/codex-eval-plugin). Repository and plugin use the same semantic version. See [CHANGELOG](../CHANGELOG.md).

### One-command provider smoke test

The dashboard automatically combines every saved live run under `evaluations/` and refreshes every 15 seconds:

```sh
./eval dashboard
```

You can also pass another evaluation workspace. Existing commands that point to a live run within `evaluations/` expand to the whole evaluation workspace. Synthetic demos stay separate and can be opened explicitly. The combined view retains failures, pending counts, source provenance, and checks of the original result artifacts. It does not rerun models or modify saved results. Separate smoke runs may use different environments and settings.

Dashboard settings update the URL automatically. Bookmark or copy the current URL to restore task/model omissions, X/Y metrics, log scales, labels, Median focus, minimum pass rate, and greyed-out medians after refresh or in another tab on the same server. The view continues to use the latest results; newly discovered tasks/models are included by default. Open `/` without the `view` parameter (or click Codex Eval) to reset the view. CSV export retains the full server dataset, independent of these display filters.

In Median focus, **Group medians by** selects **Model × effort** (default) or **Model**. Model grouping pools effort levels within each provider, keeping Codex, Claude and Copilot separate. Cost/latency medians give equal weight to measured task/configuration averages; score and score pies use passed/completed runs across the whole group, including rows with missing metric telemetry. Pending runs stay excluded from the score denominator. The URL preserves grouping, and muted medians are independent between grouping modes. Task points and exports are unchanged by this selector.

**Cost per verified success · USD** is available on either axis and forces grouped Median focus, including for a single task. It divides total cost of completed runs (including failures) by their total verified passes within the selected provider/model[/effort] group. Repeat-average costs are multiplied by recorded repeat counts before summing; it is neither a median nor an average of per-task ratios. Pending runs are excluded; any missing completed-run cost or zero verified passes makes the group unavailable rather than free. Cost and passes remain included when the other axis has missing telemetry. Codex uses the current repo rate card, Claude its reported cost, and Copilot its native usage valuation. This is descriptive cost per observed pass, not invoice cost or a prediction of retry-until-success spending. The selected metric persists in the URL; source results and exports are unchanged by axis selection.

Codex dashboard costs are recalculated on each refresh using [`ceval/data/rates.json`](../plugins/codex-eval-plugin/ceval/data/rates.json). Edit its model entries (`input`, `cached_input`, `cache_write`, `output`, in USD per million tokens); the running dashboard picks up the change within 15 seconds. Costs are calculated before repeat averages and model medians, after comparison exclusions. Required missing usage or rates stay unavailable. Unknown cache writes use zero for the lower estimate, with uncertainty retained in the upper envelope; reasoning tokens are already included in output. Rates are a saved snapshot, not fetched online automatically.

Claude's reported costs and Copilot's native credit-derived dollar usage values are unchanged by this rate card. Dashboard JSON and its CSV include recalculated Codex costs, original `recorded_cost_usd`, and rate-card path/hash provenance. Signed run files, frozen pricing, spend accounting, and `./eval report` remain unchanged. Synthetic demo costs remain synthetic. Restart the dashboard once after upgrading its code; subsequent rate-card edits need no restart.

The CLI loads `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` from `.env.local` in the current directory. Exported environment variables take precedence. Quoted values and `export KEY=...` are supported; shell commands and variable expansion are never executed.

After securely setting the provider's key in the same terminal:

```sh
./eval smoke --provider claude --output evaluations/claude-smoke
./eval dashboard evaluations/claude-smoke/run
```

Use `--provider codex` for OpenAI. This deliberately runs one small original trusted-local task, records the installed CLI version, checks its grader, and collects live metrics. It does not replace customer discovery or portfolio approval. If your CLI is an updater wrapper, pass `--binary /path/to/native/executable`. Repeated smoke tests require a new output path so earlier results survive.

## Development

```sh
python3 -m unittest discover -s tests -v
./eval self-check
./eval export --output dist
```

Tests use small local fixtures and protocol emulators, with no paid API calls. They cover orchestration, native telemetry shapes, graders, approval invalidation, resume, budget stops, secret exclusion, and standalone packaging. Live-provider coverage is recorded separately in [validation notes](../VALIDATION.md). Keep customer data, credentials, history extracts, and generated runs out of Git.

## Task inspiration library

The plugin bundles 1,658 upstream task records and 46 detailed design cards across 13 benchmark families. Search locally, adapt suitable examples, and cite original sources; original tasks are welcome when no source fits. New schema 3 customer suites enforce three Basic and five Hard tasks per workflow by default. Basic covers the former easy/medium/hard range; Hard targets former harder-1/harder-2 style repository engineering. Legacy suites retain their original meanings. [Coverage, sources, and refresh procedure](../plugins/codex-eval-plugin/ceval/data/catalog.md).

Keep one suite per directory: `validation.json` and `approval.json` belong to that directory. For separately approved provider suites, use separate directories with identical task snapshots; do not put two suite JSON files beside the same approval receipt.

The `evaluate` skill is explicit-only (`allow_implicit_invocation: false`). Invoke `$evaluate` when asking to run evaluation tests comparing Codex against another coding agent. Ordinary coding, unit tests, general benchmarks, and plugin maintenance do not trigger it. The current execution adapters support Codex, Claude Code, and opt-in local GitHub Copilot.

### Dashboard design

For an explicitly requested post-run difficulty correction, place `difficulty-labels.json` in each affected run directory. It is a display receipt, not a new task definition:

```json
{
  "schema_version": 1,
  "run_seal": "COPY_THE_SEAL_FROM_THIS_RUN_JSON",
  "requested_by": "Customer reviewer",
  "reason": "Separate the more demanding repository tasks",
  "tasks": [{"task_id": "TASK_ID", "from": "hard", "to": "harder"}]
}
```

Labels can be `basic`, `easy`, `medium`, `hard`, `harder`, `harder-1`, or `harder-2`. Task IDs and original labels must match the saved task metadata. Reports and dashboards verify the original results first, then apply the receipt to task descriptions, result rows, averages, and CSV exports, retaining `recorded_difficulty`. Saved input definitions, approvals, scores, and raw results stay unchanged. Remove the receipt to restore the original labels; regenerate any report exports afterward. An already-running dashboard server must be restarted when upgrading to code that supports these receipts.

The chart is the main view. Model-name labels use Codex blue (`#339cff`, blue300 in the [OpenAI developer stylesheet](https://developers.openai.com/_astro/PageLayout.BSuKgUPa.css)) and Claude orange. Typography prefers locally installed OpenAI Sans, the family identified in [OpenAI design guidelines](https://openai.com/brand/), with system sans-serif fallbacks; no font download is required. The task-description table remains; model summary tables, explanatory sections, and run-count badges are omitted from the UI. Detailed telemetry and source provenance remain available through CLI reports, JSON, and CSV.

### Choose models, tasks, and repeats

Configure an authored suite before validation and approval. Repeat `--model` and `--task` for any combination:

```sh
./eval configure evaluations/customer/suite.json \
  --model codex:gpt-5.6-sol --model claude:claude-sonnet-5 \
  --task TASK_ID --task ANOTHER_TASK_ID --repeats 1
./eval validate evaluations/customer/suite.json --check-graders
./eval plan evaluations/customer/suite.json
./eval approve evaluations/customer/suite.json --by "Customer reviewer"
./eval run evaluations/customer/suite.json --output evaluations/customer/run
```

`--all-tasks` clears the execution subset; the full declared portfolio stays intact. `--all-models` restores the default catalog matrix. Unknown selections are rejected without modifying the suite. Changes need renewed validation and approval.

All new suites and smoke commands default to one fresh attempt per task/model/effort configuration. Complete and review the first-round matrix before asking approval for exactly two more iterations of the same configurations, giving three observations total. Follow [staged repeats](../plugins/codex-eval-plugin/skills/evaluate/references/staged-repeats.md) to preserve the original run and avoid buying three additional attempts. Charts show arithmetic mean cost, latency, and tokens, including failed attempts. Popups show the pass count; a point is grey only when none of its repeats passes. Partial groups are labelled pending. Missing telemetry stays unavailable rather than becoming zero. Separate runs and effort settings are never averaged together; raw attempts remain in CSV/results, and `report` writes `averages.json`.

Give each customer simulation its own directory and dashboard, combining its provider runs:

```sh
./eval dashboard evaluations/simulations/interview --scope --port 8881
./eval dashboard evaluations/simulations/history --scope --port 8882
./eval dashboard evaluations/simulations/github --scope --port 8883
```

New task designs include `human_summary`: two or three plain-language sentences about the development workflow and what the test exercises. This supplies the table; detailed agent requirements remain in `instruction.md`. Older runs use a concise metadata-based fallback when an authored summary is unavailable.

## Concurrent execution

`./eval run SUITE --output RUN_DIR --workers 5` keeps up to five attempts active and starts the next queued attempt as soon as a slot opens. The default is five; use `--workers 1` for sequential timing. Add `--resume` for an existing identical sealed run. Completed attempts are verified and skipped.

To cap multiple batches at five attempts **in total**, give each the same `--workers 5 --slot-pool evaluations/shared-workers` arguments. Each attempt has an isolated workspace; only the coordinator writes shared results. Pool leases release automatically if a process exits.

Agree on concurrency before running. Concurrent work can contend for CPU and network, so latency may differ from sequential measurements. The worker count and scheduler hash are recorded in run metadata. When an explicit spend stop is configured, unrelated unknown spend or reaching that threshold stops dispatch; already-active calls finish and are saved. A threshold may overshoot by the cost of all in-flight calls.

For a graceful pause, create `RUN_DIR/stop-requested.json` (for example, containing `{}`). The runner drains active attempts; remove that file before resuming.

### Rate-limit retries

Explicit native rate-limit, capacity, connection and temporary service failures retry up to three times with 30/60/120-second backoff (longer provider retry hints are honored). Configure with `--rate-limit-retries 3 --retry-delay 30`, or disable using `--rate-limit-retries 0`. Each retry uses a fresh workspace and retains signed raw evidence. A retrying job keeps its worker slot during backoff; other workers continue, and the combined active/retrying job limit stays five.

Retries belong to the same task/model/repeat. Raw accounting includes every trial and retry wait. Comparison results exclude explicit rate-limit error trials and their retry waits, while retaining genuine coding failures. Missing rate-limit usage stays null, with `known_cost_usd` reported separately. The spend stop uses known amounts and cannot cap unreported retry charges. Unrelated unknown usage pauses execution only when a spend stop is configured; otherwise missing costs remain null and execution continues. Exhausted retries stop new work and drain active calls. `--resume` retries previously transient-failed cells only while their configured retry allowance remains. Verifier failures, auth/quota errors, and unrelated provider errors are not automatically retried.

### Reasoning and effort sweeps

New suites include all catalog-supported effort levels for each model. Refresh capability sources before approval; provider effort labels are not equivalent compute budgets. Use one repeat for a quick sweep:

```bash
./eval configure evaluations/customer/suite.json --all-efforts --repeats 1
```

Use repeated `--effort low --effort high` to narrow levels; each must be supported by every selected model. Apply `--model` and `--task` selectors in the same command when needed. Changed matrices require validation and approval before execution. Default repeats are one per task/provider/model/effort. Complete the entire first-round matrix, review results and costs, then ask permission for exactly two additional attempts per configuration. Do not start extra repeats automatically. Charts keep efforts separate and display the effort beside the model name.

### Default model sweep and spend policy

New evaluations default to all cataloged GPT-5.6 models and GPT-6 Astra, plus cataloged default Claude models, across every supported single-agent effort level. Preflight lists the exact matrix and repeats, announces **no spend stop**, and tells the customer to specify otherwise before approval. Limited-access models are included; unavailable lanes remain visible.

`configure SUITE --all-models --all-efforts --repeats 1 --no-spend-stop` restores these defaults. Select alternatives with repeated `--model PROVIDER:MODEL` / `--effort LEVEL` flags. Set an optional stop with `--spend-stop-usd AMOUNT`. A null `limits.spend_stop_usd` disables both the scheduler spend stop and Claude's native budget flag; missing costs remain null and do not stop dispatch in this mode. Time limits, turn limits, bounded rate-limit retries, and explicit pause requests still apply. Existing approved suites retain their frozen settings.

Fable 5.1 (`claude-fable-5-1`) is a default model with `low`, `medium`, `high`, `xhigh`, and `max` effort. Mythos is excluded from new suites and `configure --all-models`; it requires explicit selection and verified account/native CLI support. Check available models and CLI versions before approving the matrix.

Evaluation tasks should be achievable by the selected models, with cost, latency, and token use as the primary comparison after verifying correctness. Keep requirements explicit, provide enough context, and allow reasonable execution time. Difficulty increases coding work within a simple prepared environment; provisioning is outside the timed task. Expected success is a design target, while actual pass/fail remains determined by the same fixed checks for every model.

Before final approval, run `./eval doctor SUITE --check-model-access` to compare selected IDs with account-visible models. If the CLI is outdated, ask the customer to upgrade, locate the upgraded executable, and update the exact pin before validation. Listing success does not establish native effort support; blocked checks stay unresolved until the customer supplies results.

### Model medians

In **Median focus**, diamonds summarize selected task/configuration averages by **Model × effort** (default) or **Model** with efforts pooled within each provider. Ordinary metrics use medians; average score and cost per verified success use the aggregate definitions above. Turning focus off hides diamonds and restores task contrast. Ordinary median controls require two selected tasks; either aggregate axis forces grouped mode even for one task.

For ordinary metrics, each measured task/configuration point gets equal weight across selected tasks and saved runs within its group. This is a descriptive median of plotted averages, not a median of raw attempts or a matched-task leaderboard. The tooltip discloses contributing points/tasks, effort levels, outcomes, and axis values. Ordinary medians require both ordinary axis measurements; aggregate outcomes include completed rows missing other-axis telemetry. Genuine zeros and failures remain included. Log toggles change placement, not calculation; nonpositive values are counted in the notes below the diagram.

### Task-quality reflection

```sh
./eval reflect evaluations/customer/run
./eval reflect evaluations/customer/codex/run evaluations/customer/claude/run --pause-on-review
./eval review-clear evaluations/customer/run --by 'Reviewer' --reason 'Contract and alternative implementation checked; retain coding failures'
```

`reflect` reads verified checkpoints without calling providers, running candidate code, editing tasks, or changing scores. Defaults flag any infrastructure-invalid result, or at least 50% failures after three scorable attempts for a task. `--min-attempts` and `--failure-rate` customize those triage thresholds. Counts are per task **within each run**, with model/effort status breakdowns and up to three evidence paths. Missing cost alone is not a trigger. A racing checkpoint returns `awaiting_checkpoint`; retry inspection later.

By default it is read-only. `--pause-on-review` writes an exclusive graceful stop request for each flagged, recorded-running real run. Existing stops are preserved; unflagged lanes and synthetic runs are not paused. Active calls drain, and dispatch can continue until the runner observes the marker. This is not a background monitor: the host agent invokes it during observation and investigates new evidence. Historical flags remain visible after review; record reviewed attempt IDs to avoid repeated pauses for the same evidence.

`review-clear` requires a stopped run with zero active cells and no runner lock. It only clears a matching task-quality pause, archives the request and review reason, and never executes work. After a sound-task decision, use the original `run SUITE --output RUN --resume` options. It refuses unrelated user stops and wrong seals. For defective tasks, keep the original run and create a fresh validated, approved revision, then rerun every affected lane. See the [review workflow](../plugins/codex-eval-plugin/skills/evaluate/references/task-review.md).

### In-Codex evaluation progress

```bash
./eval progress evaluations/customer/run
./eval progress evaluations/customer/codex/run evaluations/customer/claude/run
```

This read-only command returns one saved checkpoint per exact run directory, deduplicating repeated paths. It reports scheduled, finished, remaining (including active), active-at-checkpoint, passed, failed, errors, recorded state, and checkpoint timestamp. It preserves original scheduled counts even for results hidden by dashboard view receipts. Outcome receipts are checked; mismatched manifest/result counts temporarily produce null outcome counts. Missing paths show awaiting start with unknown totals. It makes no provider calls and does not resume, pause, or alter execution.

The evaluation skill uses these snapshots with the available visualize/live skills in Codex desktop. It samples about every 15–30 seconds while observing the runner, updates one registered view using apply_patch, and leaves a final checkpoint on completion or stop. The fragment has no network access. A saved running state is not a heartbeat or proof of a live process, and updates do not continue automatically after the observing turn ends. CLI-only environments retain text progress.

Median controls, legend, and diamonds appear only when at least two task checkboxes are selected. With zero or one selected task, points retain normal contrast even if Median focus was previously enabled. Selecting multiple tasks restores the prior focus preference. Median labels include model and effort.

## Optional consistency rounds

New suites and smoke runs default to one iteration per task/model/effort. After reviewing the first round and its costs, the agent asks before two additional rounds. Use a separate, newly approved follow-up suite with `configure SUITE --repeats 2` and a fresh output directory; preserve the original run. See [staged repeats](../plugins/codex-eval-plugin/skills/evaluate/references/staged-repeats.md) for matching conditions, incremental cost estimates, and reporting. Existing explicit repeat settings are preserved.

## Execution readiness and transient recovery

For customer suites, `run` checks a tiny file edit and successful native shell test before matrix dispatch. It uses the first configured model/effort for each selected provider, the same executable, environment, sandbox and shared slot pool, with no timeout by default. Explicit numeric probe limits are capped at 120 seconds for agents and 30 seconds for graders. `plan` discloses these additional calls. `execution-checks/receipt-*.json` and signed per-trial artifacts retain results, diagnostics, cost and token telemetry. `run.json.execution_check_cost` reports known probe cost and missing rows separately from scored attempts. Probe costs count toward spend stops. A failed probe blocks the matrix; diagnose its evidence before resuming. Each pending resume performs a fresh context check; a completed resume does not. An interrupted probe receipt requires evidence reconciliation instead of an automatic new probe. Smoke suites already perform a scoped readiness task.

`--transient-retries N` (default 3; legacy alias `--rate-limit-retries`) limits cumulative additional trials per cell across resumes for explicit native rate limits and recognized native capacity, connection, and temporary service errors. `--retry-delay 30` starts exponential backoff capped at 300 seconds; provider hints can extend a wait up to 3600 seconds. The ceiling is invocation-wide. Provider-wide deadlines are shared through `--slot-pool` across concurrent batches, or locally within a run otherwise. Healthy providers can continue; active calls are not cancelled. Unknown costs stay unknown, every trial is retained, and exhausted retries stop new dispatch. A later higher ceiling must be explicitly approved. Auth/quota/model-access errors, recovered notices and grader failures do not trigger retries.

## Discovery coverage

Use `history --source-kind direct` for original session roots and `--source-kind export` for selected/exported records; the default is `unspecified`. Never infer full coverage from parser success. Then run:

```sh
./eval discovery-report evaluations/customer/discovery.json \
  --evidence evaluations/customer/history.json \
  --evidence evaluations/customer/repository.json \
  --output evaluations/customer/coverage.json
```

Omit evidence arguments for interview-only discovery. The companion `coverage.md` shows requested and observed dates, session/message counts, source scope, exclusions, unread records, assumptions, and workflow confirmation. In discovery.json, record per-workflow `source_refs` and `customer_confirmation`, plus `customer_confirmed_scope` only after the customer actually confirms them. Rerun the report after updating this record. Receipts contain no copied message excerpts and remain private in the ignored evaluation directory.

Dashboard X and Y logarithmic scales are enabled by default; each can be switched off independently. Nonpositive values remain explicitly unplottable on a log axis.

Median diamonds, labels, and their legend appear only with Median focus enabled and multiple tasks selected. Each diamond carries a small green status dot for all observed runs passing, split green/red for mixed results, or red for all failing. Incomplete repeat groups use grey. The tooltip reports exact pass and pending counts; missing axis telemetry does not hide a recorded failure from the badge. Failed task points remain grey unless at least one repeat passes.

The legend follows the active view: normal mode explains provider colors and grey points with no passing runs; Median focus replaces it with provider diamonds and the all-pass, mixed, all-fail, and pending status dots.

### Comparison versus full accounting

Comparison reports, CSVs, chart points, and medians exclude explicit native rate-limit error trials for all selected providers. After recovery, use the non-rate-limited trial's measured cost, tokens, and task latency; exclude the rate-limit trials and their external retry waits. A rate-limit-only cell remains unmeasured and is counted separately, never as a coding failure or a pass. Genuine verifier failures, timeouts, authentication/quota errors, and capacity errors are not excluded by this policy. Preserve original signed results and trials, total elapsed time, unknown charges, and full spend accounting. The reporting view uses `exclude_rate_limits_v1`; `report` writes comparison `results.csv`, separate `accounting.csv`, and `rate-limit-exclusions.json`. `summary.json` includes separate accounting totals and excluded counts. Missing non-rate-limit telemetry remains unknown. Historical mixed capacity/rate-limit backoff cannot be split reliably, so its comparison latency stays unknown. Native internal retries within a successful CLI call remain included when separate trial telemetry is unavailable.

### Explicit workflow scope

New schema 3 workflows default to eight tasks: three `basic` and five distinct `hard`. Basic spans the former easy/medium/hard range; Hard targets the former harder-1/harder-2 style. For an explicitly requested reduction, set a workflow's `difficulties` to a nonempty subset of `["basic", "hard"]`; each selected tier then requires at least one task (for example `["hard"]` seeds one Hard task). Do not set this field merely to bypass the default count. Portfolio generation and validation enforce these counts, while the task review checks substantive difficulty and distinctness. Schema 1/2 keep their legacy labels and coverage. `portfolio --suite` requires a new schema 3 suite; use `init` in a new directory instead of upgrading frozen inputs in place. Provenance and execution checks still apply. Freeze scope before running.

### GitHub Copilot (experimental, opt-in)

Use the [guided Copilot setup](../plugins/codex-eval-plugin/skills/evaluate/references/copilot.md) for personal/organization access, installation, GitHub permissions, credentials, model checks and troubleshooting. Latest verified stable CLI: 1.0.88 (2026-09-23). It has separate authentication from Codex and Claude.

```sh
./eval configure SUITE --model codex:gpt-6-astra --model copilot:gpt-6-astra --effort low --repeats 1 --copilot-account YOUR_LOGIN --copilot-binary /absolute/path/copilot --copilot-no-credit-limit
./eval smoke --provider copilot --model gpt-6-astra --effort low --copilot-account YOUR_LOGIN --binary /absolute/path/copilot --output evaluations/copilot-smoke
```

Configure replaces the model selection, so repeat `--model` for every lane to retain. `--copilot-binary` reads and pins the installed path/version. `--copilot-account LOGIN` requires that active native github.com account; `--copilot-token` removes native selection and uses only `COPILOT_GITHUB_TOKEN` from the environment or invoking directory's ignored `.env.local`. No key goes on the command line or into suite JSON. Native mode ignores stale environment tokens. These settings enter the seal.

New Copilot selections have no credit cap; existing limits are preserved. Use `--copilot-max-ai-credits N` (minimum 30) or `--copilot-no-credit-limit` explicitly. This is separate from `--spend-stop-usd` / `--no-spend-stop`. Smoke runs use one bundled slug fixture, no agent or grader timeout, catalog default effort unless `--effort` is supplied, no credit cap by default, and a new output directory per attempt. In smoke token mode, omit `--copilot-account`; `--copilot-max-ai-credits` remains available.

`models --provider copilot` filters the static catalog; it is not account discovery. `doctor --check-model-access` leaves Copilot access `not_probed`; check `/model` and run the exact approved smoke model/effort before a broad sweep. The catalog includes runtime-reported Astra efforts low through max, and Sol/Terra none plus low through max. These capabilities are a dated account snapshot, not inference proof.

Final native `copilot-usage.json` receipts enrich tokens, model identity, credits and `copilot_usage_value_usd` in new result JSON/CSV. Usage value is calculated from top-level nanoAIU at the documented credit value, not net invoice cost. It never populates `cost_usd` or uses vendor API rates. Missing telemetry remains unknown; use latency/token dashboard axes when dollar cost is absent. Historical signed results remain untouched.

### Select evaluation harnesses

Use `configure SUITE --provider codex --provider copilot --all-efforts` for the catalog defaults of those harnesses; add `--provider claude` for all three. Repeated provider flags replace the selection and cannot combine with exact `--model` flags. Copilot defaults are Astra, Sol and Terra; other catalog models remain available through `--model`. Bare `--all-models` restores Codex + Claude defaults. Configure only the selected providers’ credentials, verify their installed executables, then validate and approve the exact matrix. Copilot model access still requires its separate documented smoke checks.
