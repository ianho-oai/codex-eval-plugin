# Codex Eval Plugin

Evaluate **Codex against Claude Code** on tasks that represent your software development workflows. One skill handles discovery and task design; a bundled CLI runs the approved comparisons and opens a local dashboard.

## Start here: the customer starter prompt

**Open [CUSTOMER_STARTER_PROMPT.md](CUSTOMER_STARTER_PROMPT.md).** It is the customer entry point: install the plugin from this repository, then copy the evaluation prompt into a new Codex task in your project.

The file contains both installation commands and a copy-ready kickoff prompt. You do not need to clone this repository or assemble CLI commands yourself. The complete plugin is bundled in [`plugins/codex-eval-plugin/`](plugins/codex-eval-plugin/).

## The flow at a glance

**Install → describe your work → approve tasks → approve the run plan → run and review → compare results.**

| Step | What the agent does | What you provide or decide |
| --- | --- | --- |
| 1. Discover | Learns the workflows and shows a coverage receipt with actual sources, dates, sampling limits, and confirmed scope. | Describe your work, allow selected local session history from the last 90 days, share selected repositories/PRs/MRs, or combine these. You can end discovery at any point. |
| 2. Propose | Proposes easy, medium, focused hard, and repository-reasoning hard tasks per workflow (at least four by default), with short descriptions, acceptance checks, and benchmark inspiration or original-design rationale. | Approve the task list or ask for changes. |
| 3. Prepare | Builds self-contained fixtures, checks starting-code failure and valid solutions, and audits graders against visible requirements. Checks CLI compatibility and model access. | Provide API keys securely and handle any required CLI upgrade or account-access step. |
| 4. Agree the run | Shows the exact models, reasoning efforts, repeats, concurrency, and spend policy. | Approve the plan before paid calls; narrow the selection or set a spend stop if wanted. |
| 5. Execute and adapt | First checks a real native edit-and-test operation, then monitors results, retries transient capacity/rate-limit errors within bounds, diagnoses unexpected behavior, and repairs demonstrated test defects in a fresh revision with fair reruns. Preserves original evidence and genuine coding failures. | Usually nothing. Approve repairs outside the agreed scope; handle a blocked provider command if needed. |
| 6. Compare | Opens the prebuilt dashboard after the first round and reports results and costs. | Explore comparisons, then decide whether to approve two additional rounds for consistency and averaging. No extra rounds run automatically. |

### Have these ready

- **Codex with the plugin installed:** follow the [starter prompt](CUSTOMER_STARTER_PROMPT.md), then start a task in your own project.
- **Workflows to evaluate:** a short description is enough to begin. History and repository access are optional and scoped by you.
- **OpenAI and Anthropic API keys with billing and model access:** keep them in your environment or an ignored `.env.local`; never paste keys into chat or commit them.
- **Local tools:** Python 3.11+, native Codex and Claude Code CLIs, and the runtime for your tasks. The bundled examples also need Node.js 18+. The agent checks readiness and flags upgrades.

The main checkpoints for you are **task approval** and **run-plan approval**. After that, the CLI handles execution and grading. Tests use lightweight local runners such as unittest, pytest, or Node tests; ordinary evaluations do not require Docker, iOS simulators, or desktop-app integrations. Actual failures remain recorded.

### Defaults to review before running

- **Models:** cataloged GPT-5.6 Sol/Terra/Luna and GPT-6 Astra; Claude Fable 5.1, Opus 5, Sonnet 5, and Haiku 4.5.
- **Effort:** every catalog-supported single-agent level for each model. Provider effort labels are not equivalent compute budgets.
- **Repeats:** one per task/model/effort first. After reviewing results and costs, optionally approve two additional rounds for consistency and averaging.
- **Concurrency:** five attempts total, starting the next as soon as a slot opens.
- **Spend:** no spend stop by default. Set an optional threshold or narrow models, tasks, and efforts before approval.

The example matrix is **3 tasks × 36 model/effort configurations × 1 repeat = 108 scheduled attempts**. Catalog inclusion does not guarantee account access. Doctor checks local prerequisites and CLI versions; `doctor --check-model-access` also checks the selected IDs against account-visible models. See [provider troubleshooting](docs/TROUBLESHOOTING.md) before a large sweep.

## Requirements and results

The agent follows an adaptive loop: design observable requirements, challenge its grader with correct and incorrect alternatives, monitor execution, diagnose anomalies, and repair demonstrated defects. It chooses checks for the customer's tasks rather than relying on a fixed edge-case list. The lightweight `reflect` CLI flags infrastructure errors and frequent task failures; the host agent also investigates unexpected evidence below those thresholds. Repairs use fresh validated, approved revisions and fair reruns under the agreed scope. Genuine coding failures stay failures. See [task-quality review](plugins/codex-eval-plugin/skills/evaluate/references/task-review.md). Deterministic CLI evidence supports the agent's diagnosis; it does not certify a test as error-free.

Python 3.11+, native Codex and Claude Code CLIs, provider API keys, and the runtime needed by your selected tasks. Example graders also use Node.js 18+. The orchestration and dashboard have no third-party Python dependencies. Keep keys in the environment or ignored `.env.local`, never in chat or Git.

Completion is **1 or 0**, determined by separate behavioral checks and allowed-file changes. The runner records latency, tokens, native turns/tool calls when available, Claude's reported cost, and OpenAI rate-card estimates. Missing values remain unavailable; provider errors are distinct from task failures. Inputs and grading are fixed, while model outputs and provider caches remain nondeterministic. See the [methodology](plugins/codex-eval-plugin/ceval/data/methodology.md).

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

The versioned export includes exactly one skill, the CLI, catalogs, examples, schemas, and dashboard. Customer data and results stay in ignored evaluation directories. Repository and plugin versions move together; exported ZIPs include a checksum. Public source: [ianho-oai/codex-eval-plugin](https://github.com/ianho-oai/codex-eval-plugin).

## Contributing

Submit changes through a pull request to the default branch (`master`). Complete **Summary**, **Validation**, and **Risks** in the provided template. Explain what changed, how you checked it, and any known risk (or “None”). The PR format check validates these sections; code-owner review routes changes to [@ianho-oai](https://github.com/ianho-oai). New commits require renewed approval under the repository rules.
