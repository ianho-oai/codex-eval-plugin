# Codex Eval

One skill for workflow discovery, task design, and approved headless Codex versus Claude Code and/or GitHub Copilot evaluation. The CLI and dark local dashboard are bundled and run without third-party Python packages.

GitHub Copilot CLI is an opt-in experimental provider. Read [Copilot setup and limits](skills/evaluate/references/copilot.md) before selecting it. Copilot uses account billing rather than the direct-model API rate card; unknown currency cost remains null.

## Start with the customer prompt

**Open the [customer setup and starter prompt](https://github.com/ianho-oai/codex-eval-plugin/blob/master/CUSTOMER_STARTER_PROMPT.md).** This is the entry point: follow its GitHub installation instructions, then paste the kickoff prompt into a new Codex task in your project. No separate repository clone is required.

The prompt invokes the one **evaluate** skill, offers the three discovery methods, and guides task approval, setup, execution, and the combined dashboard. The commands below are a manual reference for installed or extracted plugins. See the [walkthrough](https://github.com/ianho-oai/codex-eval-plugin/blob/master/OVERVIEW.md) and [troubleshooting](https://github.com/ianho-oai/codex-eval-plugin/blob/master/docs/TROUBLESHOOTING.md).

## Run the bundled CLI

```sh
python3 bin/codex-eval self-check
python3 bin/codex-eval demo --output ./demo
python3 bin/codex-eval dashboard ./demo
```

Python 3.11+ on macOS/Linux is required; sample graders also use Node.js 18+. Customer comparisons default to local execution with self-contained tasks and existing simple test runners. Use unittest, already-installed pytest, Node tests, or an equivalent available runner. iOS workflows should test extracted logic without Xcode, simulators, or SwiftUI/UIKit UI setup. Docker is an explicit advanced option. See [task design](ceval/data/task-design.md), [methodology](ceval/data/methodology.md), and the [full repository guide](https://github.com/ianho-oai/codex-eval-plugin).

After setting a provider key securely in the invoking terminal, run one original trusted-local fixture:

```sh
python3 bin/codex-eval smoke --provider claude --output ./claude-smoke
python3 bin/codex-eval dashboard ./claude-smoke/run
```

Use `--provider codex` for an OpenAI smoke test or `--provider copilot --model gpt-6-astra --effort low --copilot-account YOUR_LOGIN` for native Copilot login. Omit `--copilot-account` to use the dedicated `COPILOT_GITHUB_TOKEN` instead. Copilot smoke tests have no credit cap by default; an optional `--copilot-max-ai-credits 30` is a soft cap. Credentials are loaded from `.env.local` in the current directory; exported environment variables take precedence. Only `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `COPILOT_GITHUB_TOKEN` are loaded, with no shell execution or variable expansion. `--binary PATH` pins a native executable when your normal command is an updater/launcher. Native product versions and model IDs must support the documented flags. Host API restrictions still apply. Offline adapter tests do not establish live provider access.

Use `python3 bin/codex-eval dashboard` to show every live run under `evaluations/`, with automatic refresh every 15 seconds. Pass a different workspace directory if needed. A live run inside `evaluations/` also opens the entire workspace. Synthetic demos remain separate unless opened explicitly. The dashboard verifies original artifacts and retains failures, pending counts, and source provenance; separate smoke tests do not establish a controlled benchmark.

## Find representative tasks

```sh
python3 bin/codex-eval examples --query "frontend editor focus" --limit 5
python3 bin/codex-eval portfolio evaluations/customer/discovery.json --suite evaluations/customer/suite.json --output evaluations/customer/portfolio.json
```

The [offline catalog](ceval/data/catalog.md) bundles 1,658 public task references and 46 detailed design examples. New schema 3 customer suites default to three Basic and five Hard tasks per discovered workflow (explicit scope reductions are supported), with original source links and adaptation notes or an explicit original-design rationale.

Keep one suite per directory: `validation.json` and `approval.json` belong to that directory. For separately approved provider suites, use separate directories with identical task snapshots; do not put two suite JSON files beside the same approval receipt.

The `evaluate` skill is explicit-only (`allow_implicit_invocation: false`). Invoke `$evaluate` when asking to run evaluation tests comparing Codex against another coding agent. Ordinary coding, unit tests, general benchmarks, and plugin maintenance do not trigger it. The current execution adapters support Codex, Claude Code, and opt-in local GitHub Copilot.

## Concurrent execution

Before paid execution, the skill audits acceptance checks against visible requirements and tests an independent valid implementation. During execution, `python3 bin/codex-eval reflect RUN_DIR` flags per-task failure clusters and infrastructure errors for host-agent review. Add `--pause-on-review` to request a graceful pause. After review, `review-clear RUN_DIR --by NAME --reason TEXT` can clear only a drained review-owned pause; it never starts work. Defective tests need a new validated, approved revision and fair reruns; original outcomes stay intact. See [task-quality review](skills/evaluate/references/task-review.md).

`python3 bin/codex-eval run SUITE --output RUN_DIR --workers 5` keeps up to five attempts active and starts the next queued attempt as soon as a slot opens. The default is five; use `--workers 1` for sequential timing. Add `--resume` for an existing identical sealed run. Completed attempts are verified and skipped.

To cap multiple batches at five attempts **in total**, give each the same `--workers 5 --slot-pool evaluations/shared-workers` arguments. Each attempt has an isolated workspace; only the coordinator writes shared results. Pool leases release automatically if a process exits.

Agree on concurrency before running. Concurrent work can contend for CPU and network, so latency may differ from sequential measurements. The worker count and scheduler hash are recorded in run metadata. When an explicit spend stop is configured, unrelated unknown spend or reaching that threshold stops dispatch; already-active calls finish and are saved. A threshold may overshoot by the cost of all in-flight calls.

For a graceful pause, create `RUN_DIR/stop-requested.json` (for example, containing `{}`). The runner drains active attempts; remove that file before resuming.

### Rate-limit retries

Explicit native rate-limit, capacity, connection and temporary service failures retry up to three times with 30/60/120-second backoff (longer provider retry hints are honored). Configure with `--transient-retries 3 --retry-delay 30`, or disable using `--transient-retries 0`. Each retry uses a fresh workspace and retains signed raw evidence. A retrying job keeps its worker slot during backoff; other workers continue, and the combined active/retrying job limit stays five.

Retries belong to the same task/model/repeat. Full accounting includes every trial and retry wait. Comparison reports and chart metrics exclude explicit rate-limit error trials under the documented methodology; other transient recovery costs stay included. Missing transient-error usage stays null, with `known_cost_usd` reported separately. The spend stop uses known amounts and cannot cap unreported retry charges. Unrelated unknown usage pauses execution only when a spend stop is configured; otherwise missing costs remain null and execution continues. Exhausted retries stop new work and drain active calls. `--resume` retries previously transient-failed cells only while their configured retry allowance remains. Verifier failures, auth/quota errors, and unrelated provider errors are not automatically retried.

## Effort sweeps

New suites include all catalog-supported single-agent effort levels per model. Before approval, expand an existing suite with `python3 bin/codex-eval configure SUITE --all-efforts --repeats 1` for a quick sweep. Repeated `--effort low --effort high` selects narrower levels supported by every selected model. Default repeats are one; ask before two additional rounds; charts label each model and effort separately.

### Default model sweep and spend policy

New evaluations default to all cataloged GPT-5.6 models and GPT-6 Astra, plus cataloged default Claude models, across every supported single-agent effort level. Preflight lists the exact matrix and repeats, announces **no spend stop**, and tells the customer to specify otherwise before approval. Limited-access models are included; unavailable lanes remain visible.

`configure SUITE --all-models --all-efforts --no-spend-stop` restores these defaults. Select alternatives with repeated `--model PROVIDER:MODEL` / `--effort LEVEL` flags. Set an optional stop with `--spend-stop-usd AMOUNT`. A null `limits.spend_stop_usd` disables both the scheduler spend stop and Claude's native budget flag; missing costs remain null and do not stop dispatch in this mode. Time limits, turn limits, bounded rate-limit retries, and explicit pause requests still apply. Existing approved suites retain their frozen settings.

Fable 5.1 (`claude-fable-5-1`) is a default model with `low`, `medium`, `high`, `xhigh`, and `max` effort. Mythos is excluded from new suites and `configure --all-models`; it requires explicit selection and verified account/native CLI support. Check available models and CLI versions before approving the matrix.

Evaluation tasks must be feasible with clear requirements and supplied context. Compare verified correctness, cost, latency, and token use together; do not simplify Hard tasks to target a high pass rate or a provider win. Keep requirements explicit, provide enough context, and allow reasonable execution time. Difficulty increases coding work within a simple prepared environment; provisioning is outside the timed task. Expected success is a design target, while actual pass/fail remains determined by the same fixed checks for every model.

Doctor without `--check-model-access` checks local requirements and known model minimum CLI versions; account checks require that flag. Fable 5.1 requires Claude Code 2.1.251 or newer. Update the CLI and pin the actual version in a newly validated/approved suite before retrying. An unavailable Mythos model ID or account requires a separate access check; there is no automatic model substitution.

Before final approval, run `python3 bin/codex-eval doctor SUITE --check-model-access` to compare selected IDs with account-visible models. If the CLI is outdated, ask the customer to upgrade, locate the upgraded executable, and update the exact pin before validation. Listing success does not establish native effort support; blocked checks stay unresolved until the customer supplies results.

The dashboard has identical, stable X/Y dropdowns: task cost, latency, tokens, average score, and cost per verified success. **Median focus** groups by model × effort or by model with efforts pooled within each provider. Ordinary metrics use medians of measured task/configuration averages; score uses passed/completed runs, and cost per verified success uses total completed cost including failures divided by passes. Missing costs or zero passes make the latter unavailable. Filters, grouping, and the score-pie checkbox persist in the URL. Hover shows coverage and values; compact metric definitions sit below the diagram. See [methodology](ceval/data/methodology.md) for denominators and cross-run limitations.

Codex dashboard costs recalculate from the packaged `ceval/data/rates.json` every refresh; exports retain original costs and current pricing provenance. Signed results, frozen accounting, and static reports remain unchanged. Claude uses native reported cost; Copilot Task cost uses native dollar usage valuation, not invoice charges, through a display-only projection. Copilot credits remain separate in raw results/CSV and are not axis options.

During evaluation runs in Codex desktop, the skill uses the available visualize/live skills to show checkpoint progress in the task sidebar. `bin/codex-eval progress RUN_DIR [RUN_DIR ...]` supplies finished/remaining attempts, active-at-checkpoint slots, and pass/fail/error counts. The host agent refreshes the view while observing the run; CLI/text progress remains available without visualization skills. No extra dependencies enter the evaluated agents.

Ordinary median controls require at least two selected tasks, and diamonds appear only in Median focus. Aggregate outcome axes force grouped mode even for one task; score axes use a fixed linear 0–100% scale. Labels follow the selected grouping.

## Customer readiness and coverage receipts

Customer runs automatically perform a native edit-and-test check in the actual execution environment before matrix dispatch. New suites, smoke tests, and readiness checks have no agent/grader timeout unless explicitly configured. The first configured model/effort per provider is checked, using the same sandbox and shared slots. Failures block the matrix. Signed probe trials and JSON receipts live under `execution-checks/`; their known costs are separate from model averages and included in spend stops. Pending resumes check again; completed resumes do not. Inspect interrupted probe evidence rather than blindly retrying.

`run --transient-retries 3 --retry-delay 30` covers explicit native rate-limit, capacity, connection, and temporary service errors. `--rate-limit-retries` remains an alias. Provider-wide cooldowns are shared by batches using the same `--slot-pool`, with exponential delay and provider hints capped at one hour. Retry ceilings are cumulative per cell and apply invocation-wide. Verifier failures, auth/quota errors and unsupported models are not retried.

Use `history --source-kind direct|export` and `discovery-report DISCOVERY --evidence HISTORY_OR_REPO_JSON --output coverage.json` to generate a JSON/Markdown coverage receipt. Repeat evidence arguments for combined sources or omit for interview-only discovery. The receipt distinguishes requested dates from observed records, states collection limits and exclusions, and displays workflow source references and customer confirmation from discovery.json. A selected export is never presented as a complete three-month crawl.

Both dashboard axes default to logarithmic scale; either can be switched off independently.

### Select evaluation harnesses

Use `configure SUITE --provider codex --provider copilot --all-efforts` for the catalog defaults of those harnesses; add `--provider claude` for all three. Repeated provider flags replace the selection and cannot combine with exact `--model` flags. Copilot defaults are Astra, Sol and Terra; other catalog models remain available through `--model`. Bare `--all-models` restores Codex + Claude defaults. Configure only the selected providers’ credentials, verify their installed executables, then validate and approve the exact matrix. Copilot model access still requires its separate documented smoke checks.
