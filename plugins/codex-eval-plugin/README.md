# Codex Eval · 0.9.2

One skill for workflow discovery, task design, and approved headless Codex versus Claude Code evaluation. The CLI and dark local dashboard are bundled and run without third-party Python packages.

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

Use `--provider codex` for an OpenAI smoke test. API keys are loaded from `.env.local` in the current directory; exported environment variables take precedence. Only `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are loaded, with no shell execution or variable expansion. `--binary PATH` pins a native executable when your normal command is an updater/launcher. Native product versions and model IDs must support the documented flags. Host API restrictions still apply. No Claude live result is implied by passing offline adapter tests.

Use `python3 bin/codex-eval dashboard` to show every live run under `evaluations/`, with automatic refresh every 15 seconds. Pass a different workspace directory if needed. A live run inside `evaluations/` also opens the entire workspace. Synthetic demos remain separate unless opened explicitly. The dashboard verifies original artifacts and retains failures, pending counts, and source provenance; separate smoke tests do not establish a controlled benchmark.

## Find representative tasks

```sh
python3 bin/codex-eval examples --query "frontend editor focus" --limit 5
python3 bin/codex-eval portfolio evaluations/customer/discovery.json --suite evaluations/customer/suite.json --output evaluations/customer/portfolio.json
```

The [offline catalog](ceval/data/catalog.md) bundles 1,658 public task references and 46 detailed design examples. New customer suites require easy/medium/hard tasks per discovered workflow, with original source links and adaptation notes or an explicit original-design rationale.

Keep one suite per directory: `validation.json` and `approval.json` belong to that directory. For separately approved provider suites, use separate directories with identical task snapshots; do not put two suite JSON files beside the same approval receipt.

The `evaluate` skill is explicit-only (`allow_implicit_invocation: false`). Invoke `$evaluate` when asking to run evaluation tests comparing Codex against another coding agent. Ordinary coding, unit tests, general benchmarks, and plugin maintenance do not trigger it. The current execution adapters support Codex and Claude Code.

## Concurrent execution

Before paid execution, the skill audits acceptance checks against visible requirements and tests an independent valid implementation. During execution, `python3 bin/codex-eval reflect RUN_DIR` flags per-task failure clusters and infrastructure errors for host-agent review. Add `--pause-on-review` to request a graceful pause. After review, `review-clear RUN_DIR --by NAME --reason TEXT` can clear only a drained review-owned pause; it never starts work. Defective tests need a new validated, approved revision and fair reruns; original outcomes stay intact. See [task-quality review](skills/evaluate/references/task-review.md).

`python3 bin/codex-eval run SUITE --output RUN_DIR --workers 5` keeps up to five attempts active and starts the next queued attempt as soon as a slot opens. The default is five; use `--workers 1` for sequential timing. Add `--resume` for an existing identical sealed run. Completed attempts are verified and skipped.

To cap multiple batches at five attempts **in total**, give each the same `--workers 5 --slot-pool evaluations/shared-workers` arguments. Each attempt has an isolated workspace; only the coordinator writes shared results. Pool leases release automatically if a process exits.

Agree on concurrency before running. Concurrent work can contend for CPU and network, so latency may differ from sequential measurements. The worker count and scheduler hash are recorded in run metadata. When an explicit spend stop is configured, unrelated unknown spend or reaching that threshold stops dispatch; already-active calls finish and are saved. A threshold may overshoot by the cost of all in-flight calls.

For a graceful pause, create `RUN_DIR/stop-requested.json` (for example, containing `{}`). The runner drains active attempts; remove that file before resuming.

### Rate-limit retries

Explicit native rate-limit failures retry up to three times with 30/60/120-second backoff (longer provider retry hints are honored). Configure with `--rate-limit-retries 3 --retry-delay 30`, or disable using `--rate-limit-retries 0`. Each retry uses a fresh workspace and retains signed raw evidence. A retrying job keeps its worker slot during backoff; other workers continue, and the combined active/retrying job limit stays five.

Retries belong to the same task/model/repeat. Reported cost and tokens include every trial; latency includes trial execution plus retry waits. Missing rate-limit usage stays null, with `known_cost_usd` reported separately. The spend stop uses known amounts and cannot cap unreported retry charges. Unrelated unknown usage pauses execution only when a spend stop is configured; otherwise missing costs remain null and execution continues. Exhausted retries stop new work and drain active calls. `--resume` retries previously rate-limited cells only while their configured retry allowance remains. Verifier failures, auth/quota errors, and unrelated provider errors are not automatically retried.

## Effort sweeps

New suites include all catalog-supported single-agent effort levels per model. Before approval, expand an existing suite with `python3 bin/codex-eval configure SUITE --all-efforts --repeats 1` for a quick sweep. Repeated `--effort low --effort high` selects narrower levels supported by every selected model. General default repeats remain three; charts label each model and effort separately.

### Default model sweep and spend policy

New evaluations default to all cataloged GPT-5.6 models and GPT-6 Astra, plus cataloged default Claude models, across every supported single-agent effort level. Preflight lists the exact matrix and repeats, announces **no spend stop**, and tells the customer to specify otherwise before approval. Limited-access models are included; unavailable lanes remain visible.

`configure SUITE --all-models --all-efforts --no-spend-stop` restores these defaults. Select alternatives with repeated `--model PROVIDER:MODEL` / `--effort LEVEL` flags. Set an optional stop with `--spend-stop-usd AMOUNT`. A null `limits.spend_stop_usd` disables both the scheduler spend stop and Claude's native budget flag; missing costs remain null and do not stop dispatch in this mode. Time limits, turn limits, bounded rate-limit retries, and explicit pause requests still apply. Existing approved suites retain their frozen settings.

Fable 5.1 (`claude-fable-5-1`) is a default model with `low`, `medium`, `high`, `xhigh`, and `max` effort. Mythos is excluded from new suites and `configure --all-models`; it requires explicit selection and verified account/native CLI support. Check available models and CLI versions before approving the matrix.

Evaluation tasks should be achievable by the selected models, with cost, latency, and token use as the primary comparison after verifying correctness. Keep requirements explicit, provide enough context, and allow reasonable execution time. Difficulty increases coding work within a simple prepared environment; provisioning is outside the timed task. Expected success is a design target, while actual pass/fail remains determined by the same fixed checks for every model.

Doctor without `--check-model-access` checks local requirements and known model minimum CLI versions; account checks require that flag. Fable 5.1 requires Claude Code 2.1.251 or newer. Update the CLI and pin the actual version in a newly validated/approved suite before retrying. An unavailable Mythos model ID or account requires a separate access check; there is no automatic model substitution.

Before final approval, run `python3 bin/codex-eval doctor SUITE --check-model-access` to compare selected IDs with account-visible models. If the CLI is outdated, ask the customer to upgrade, locate the upgraded executable, and update the exact pin before validation. Listing success does not establish native effort support; blocked checks stay unresolved until the customer supplies results.

Dashboard diamonds show one median per model × reasoning-effort combination across selected task/configuration averages. **Median focus** at the top right fades the task points and enlarges medians. Filters and axis selections update the medians; hover reveals their sample coverage.

During evaluation runs in Codex desktop, the skill uses the available visualize/live skills to show checkpoint progress in the task sidebar. `bin/codex-eval progress RUN_DIR [RUN_DIR ...]` supplies finished/remaining attempts, active-at-checkpoint slots, and pass/fail/error counts. The host agent refreshes the view while observing the run; CLI/text progress remains available without visualization skills. No extra dependencies enter the evaluated agents.

Median controls, legend, and diamonds appear only when at least two task checkboxes are selected. With zero or one selected task, points retain normal contrast even if Median focus was previously enabled. Selecting multiple tasks restores the prior focus preference. Median labels include model and effort.
