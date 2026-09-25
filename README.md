# Codex Eval Plugin

Evaluate **Codex against Claude Code, GitHub Copilot, or both** on tasks that represent your software development workflows. One skill handles discovery and task design; a bundled CLI runs the approved comparisons and opens a local dashboard.

**GitHub Copilot CLI is also available as an opt-in experimental provider.** See the [Copilot setup and limits](plugins/codex-eval-plugin/skills/evaluate/references/copilot.md). It uses Copilot account authentication and billing; headless editing and grading were verified with CLI 1.0.88. Each customer must still check their own account and model access.

## Start here: the customer starter prompt

**Open [CUSTOMER_STARTER_PROMPT.md](CUSTOMER_STARTER_PROMPT.md).** It is the customer entry point: install the plugin from this repository, then copy the evaluation prompt into a new Codex task in your project.

The file contains both installation commands and a copy-ready kickoff prompt. You do not need to clone this repository or assemble CLI commands yourself. The complete plugin is bundled in [`plugins/codex-eval-plugin/`](plugins/codex-eval-plugin/).

## The flow at a glance

**Install → describe your work → approve tasks → approve the run plan → run and review → compare results.**

| Step | What the agent does | What you provide or decide |
| --- | --- | --- |
| 1. Discover | Learns the workflows and shows a coverage receipt with actual sources, dates, sampling limits, and confirmed scope. | Describe your work, allow selected local session history from the last 90 days, share selected repositories/PRs/MRs, or combine these. You can end discovery at any point. |
| 2. Propose | Proposes three Basic and five distinct Hard tasks per workflow (eight by default), emphasizing repository investigation, feature integration, and recovery/compatibility, with short descriptions, acceptance checks, and benchmark inspiration or original-design rationale. | Approve the task list or ask for changes. |
| 3. Prepare | Builds self-contained fixtures, checks starting-code failure and valid solutions, and audits graders against visible requirements. Checks CLI compatibility and model access. | Provide API keys securely and handle any required CLI upgrade or account-access step. |
| 4. Agree the run | Shows the exact models, reasoning efforts, repeats, concurrency, and spend policy. | Approve the plan before paid calls; narrow the selection or set a spend stop if wanted. |
| 5. Execute and adapt | First checks a real native edit-and-test operation, then monitors results, retries transient capacity/rate-limit errors within bounds, diagnoses unexpected behavior, and repairs demonstrated test defects in a fresh revision with fair reruns. Preserves original evidence and genuine coding failures. | Usually nothing. Approve repairs outside the agreed scope; handle a blocked provider command if needed. |
| 6. Compare | Opens the prebuilt dashboard after the first round and reports results and costs. | Explore comparisons, then decide whether to approve two additional rounds for consistency and averaging. No extra rounds run automatically. |

### Have these ready

- **Codex with the plugin installed:** follow the [starter prompt](CUSTOMER_STARTER_PROMPT.md), then start a task in your own project.
- **Workflows to evaluate:** a short description is enough to begin. History and repository access are optional and scoped by you.
- **Credentials for selected providers:** OpenAI/Anthropic API keys for Codex/Claude; explicit Copilot login or a dedicated GitHub token for Copilot. Keep keys in your environment or an ignored `.env.local`; never paste them into chat or commit them.
- **Local tools:** Python 3.11+, native CLIs for the selected providers, and the runtime for your tasks. The bundled examples also need Node.js 18+. The agent checks readiness and flags upgrades.

The main checkpoints for you are **task approval** and **run-plan approval**. After that, the CLI handles execution and grading. Tests use lightweight local runners such as unittest, pytest, or Node tests; ordinary evaluations do not require Docker, iOS simulators, or desktop-app integrations. Actual failures remain recorded.

### Defaults to review before running

- **Models:** cataloged GPT-5.6 Sol/Terra/Luna and GPT-6 Astra; Claude Fable 5.1, Opus 5, Sonnet 5, and Haiku 4.5.
- **Effort:** every catalog-supported single-agent level for each model. Provider effort labels are not equivalent compute budgets.
- **Repeats:** one per task/model/effort first. After reviewing results and costs, optionally approve two additional rounds for consistency and averaging.
- **Concurrency:** five attempts total, starting the next as soon as a slot opens.
- **Spend:** no spend stop by default. Set an optional threshold or narrow models, tasks, and efforts before approval.

The example matrix is **3 tasks × 36 model/effort configurations × 1 repeat = 108 scheduled attempts**. Catalog inclusion does not guarantee account access. Doctor checks local prerequisites and CLI versions; `doctor --check-model-access` also checks Codex/Claude IDs against account-visible models. Copilot requires the documented model-picker and approved smoke checks. See [provider troubleshooting](docs/TROUBLESHOOTING.md) before a large sweep.

## Under the hood: the CLI commands

The skill interviews you, designs tasks, and reviews problems. It calls the bundled **`codex-eval` CLI** to validate and seal inputs, schedule native agents, grade their changes, and display results. Task design requires the agent; `init` and `portfolio` only create scaffolding.

The examples below use **`./eval` from this repository's root**. With an installed or extracted plugin, use `python3 /path/to/codex-eval-plugin/bin/codex-eval` instead. Both invoke the same CLI. Run `./eval --help` to list commands or `./eval run --help` for one command's options.

### 1. Prepare the evaluation

```sh
# Create suite.json, discovery.json, rates.json, and example task folders.
./eval init evaluations/customer
```

The agent then records your workflows in `discovery.json`, authors the approved tasks and graders, and pins the installed provider CLI paths and versions in `suite.json`. These discovery helpers support that work:

| Command | What it does |
| --- | --- |
| `history --provider codex --days 90 --consent --output FILE` | Reads local user-message history after you grant access; use `--provider claude` for Claude history. |
| `repo --path PATH --output FILE` | Collects workflow evidence from a selected local Git repository. |
| `discovery-report DISCOVERY --evidence FILE --output FILE` | Writes a source-coverage receipt, including sampling limits and workflow confirmation. |
| `examples --query TEXT` | Searches the bundled task-design catalog. |
| `portfolio DISCOVERY --suite SUITE --output FILE` | Seeds three Basic and five Hard slots per workflow; the agent adapts their focus to the customer and implements the tasks. |

Prefix these commands with `./eval`. `FILE`, `PATH`, `DISCOVERY`, and `SUITE` are placeholders for your chosen paths. History and repository collection are optional, based on your approved discovery scope.

### 2. Configure, validate, and approve

Choose the harnesses before freezing the plan. For Codex + Copilot catalog defaults:

```sh
./eval configure evaluations/customer/suite.json --provider codex --provider copilot --all-efforts
```

Add `--provider claude` for all three, or use repeated `--model PROVIDER:MODEL` flags for exact models. Configure Copilot's explicit account/token and installed executable using the [Copilot setup guide](plugins/codex-eval-plugin/skills/evaluate/references/copilot.md). Copilot remains opt-in; bare `--all-models` restores Codex + Claude defaults.

After the customer tasks are authored:

```sh
# Inspect the bundled model catalog.
./eval models

# Keep the chosen harnesses/models; select efforts, one repeat, and spend policy.
./eval configure evaluations/customer/suite.json \
  --all-efforts --repeats 1 --no-spend-stop

# Check local prerequisites and authenticated model listings; no inference calls.
./eval doctor evaluations/customer/suite.json --check-model-access

# Run local graders: starting code must fail and reference solutions must pass.
./eval validate evaluations/customer/suite.json --check-graders

# Display the exact inputs and scheduled attempt count for review.
./eval plan evaluations/customer/suite.json

# Only after customer approval: record who approved these exact inputs.
./eval approve evaluations/customer/suite.json --by 'Customer reviewer'
```

To narrow the matrix, add repeated `--model PROVIDER:MODEL_ID` flags, and replace `--all-efforts` with repeated `--effort LEVEL` flags. Select tasks with repeated `--task TASK_ID`. Replace `--no-spend-stop` with `--spend-stop-usd AMOUNT` to set a threshold. Changes require validation and approval again. `validate` writes `validation.json`; `approve` writes `approval.json` tied to the input seal, which fingerprints the evaluation inputs.

### 3. Run, monitor, and resume

```sh
# Starts paid provider calls, including native edit-and-test readiness checks.
./eval run evaluations/customer/suite.json \
  --output evaluations/customer/run --workers 5
```

For each scheduled task/model/effort/repeat, the runner prepares a fresh copy of the starting code, invokes the selected native CLI, then runs the separate behavioral grader and checks allowed-file changes. **The grader determines pass/fail.** The runner saves native events, results, timing, and available usage/cost telemetry.

| Native agent | What `run` invokes |
| --- | --- |
| Codex | `codex … exec --json --ephemeral …`: the pinned model and effort, API authentication, and `workspace-write` sandbox in local mode. |
| Claude Code | `claude -p --bare --no-session-persistence --output-format stream-json …`: the pinned model, supported effort setting, turn limit, and configured coding tools. |
| GitHub Copilot | `copilot --prompt … --output-format json …`: the pinned model/effort, explicit account/token, isolated settings, and native usage receipt. Local execution only. |

These are abbreviated command shapes; the [runner implementation](plugins/codex-eval-plugin/ceval/runner.py) builds the full arguments and settings. New suites have no agent or grader timeout; explicit numeric limits are enforced. The CLI queues up to five attempts by default and applies bounded retries for explicit native rate-limit, capacity, connection, and temporary service errors.

In another terminal, inspect saved checkpoints and review signals:

```sh
./eval progress evaluations/customer/run
./eval reflect evaluations/customer/run
```

`progress` reads saved counts and state; `reflect` flags patterns for the agent to investigate. Neither command above starts model calls or changes grades. To continue an interrupted run with the same sealed inputs and output directory:

```sh
./eval run evaluations/customer/suite.json \
  --output evaluations/customer/run --workers 5 --resume
```

`--resume` verifies saved evidence, skips completed cells, and continues eligible unfinished work under the retry policy. It can incur additional provider costs.

### 4. Export results and open the dashboard

```sh
# Write summary.json, averages.json, results.csv, and accounting exports.
./eval report evaluations/customer/run

# Show only this customer's runs, combining providers within this directory.
./eval dashboard evaluations/customer --scope --port 8765
```

Open [localhost:8765](http://127.0.0.1:8765). To combine all saved live runs under `evaluations/`, use `./eval dashboard` without `--scope`. Reports and dashboards read and verify existing result artifacts; they do not call models. Missing or invalid artifacts must be resolved or excluded by selecting specific run directories.

See the [CLI reference](docs/CLI_REFERENCE.md) for all options, shared worker pools, retry settings, and additional discovery sources.

## Requirements and results

The agent follows an adaptive loop: design observable requirements, challenge its grader with correct and incorrect alternatives, monitor execution, diagnose anomalies, and repair demonstrated defects. It chooses checks for the customer's tasks rather than relying on a fixed edge-case list. The lightweight `reflect` CLI flags infrastructure errors and frequent task failures; the host agent also investigates unexpected evidence below those thresholds. Repairs use fresh validated, approved revisions and fair reruns under the agreed scope. Genuine coding failures stay failures. See [task-quality review](plugins/codex-eval-plugin/skills/evaluate/references/task-review.md). Deterministic CLI evidence supports the agent's diagnosis; it does not certify a test as error-free.

Python 3.11+, native CLIs for the selected providers, provider credentials, and the runtime needed by your selected tasks. Example graders also use Node.js 18+. The orchestration and dashboard have no third-party Python dependencies. Keep keys in the environment or ignored `.env.local`, never in chat or Git.

Completion is **1 or 0**, determined by separate behavioral checks and allowed-file changes. The runner records latency, tokens, native turns/tool calls when available, Claude's reported cost, and OpenAI rate-card estimates. Comparison results exclude explicit rate-limit error trials; successful retries contribute their measured task metrics. Raw logs and separate accounting retain all attempts and charges. Missing non-rate-limit values remain unavailable; other provider errors are distinct from task failures. Inputs and grading are fixed, while model outputs and provider caches remain nondeterministic. See the [methodology](plugins/codex-eval-plugin/ceval/data/methodology.md).

## Documentation

| Document | Use it for |
| --- | --- |
| **[Customer starter prompt](CUSTOMER_STARTER_PROMPT.md)** | **Install and begin your evaluation in Codex** |
| [Product walkthrough](OVERVIEW.md) | Customer experience and underlying functionality |
| [CLI reference](docs/CLI_REFERENCE.md) | Manual commands, model/task selectors, queues, retries, exports, dashboards |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | CLI compatibility, unavailable models, and safe recovery |
| [Task design](plugins/codex-eval-plugin/ceval/data/task-design.md) | Self-contained fixtures, difficulty tiers, and objective graders |
| [Benchmark catalog](plugins/codex-eval-plugin/ceval/data/catalog.md) | 1,658 public task references and 46 design cards across 13 families |
| [Validation](VALIDATION.md) / [Changelog](CHANGELOG.md) | Verified coverage, limitations, and releases |

## For developers

Clone this repository to develop the plugin or inspect a synthetic demo. These commands are optional developer tools; customer setup starts with the prompt above.

```sh
./eval self-check
./eval demo --output evaluations/demo
./eval dashboard evaluations/demo
```

Open http://127.0.0.1:8765. Demo data is synthetic and separate from live comparisons.

Before releasing:

```sh
python3 -m unittest discover -s tests -v
./eval self-check
./eval export --output dist
```

Keep all local discovery receipts, customer task snapshots, run logs, and results under `evaluations/`; it is ignored by Git. Alternate root `runs/`, `results/`, and `logs/` folders and provider `.env.local` files are also ignored. Use `git status --short` before committing; ignore rules do not remove already-tracked files. Publish only original synthetic fixtures and public benchmark references.

The versioned export includes exactly one skill, the CLI, catalogs, examples, schemas, and dashboard. Customer data and results stay in ignored evaluation directories. Repository and plugin versions move together; exported ZIPs include a checksum. Public source: [ianho-oai/codex-eval-plugin](https://github.com/ianho-oai/codex-eval-plugin).

## Contributing

Submit changes through a pull request to the default branch (`master`). Complete **Summary**, **Validation**, and **Risks** in the provided template. Explain what changed, how you checked it, and any known risk (or “None”). The PR format check validates these sections; code-owner review routes changes to [@ianho-oai](https://github.com/ianho-oai). New commits require renewed approval under the repository rules.
