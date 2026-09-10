# Codex Eval Plugin

Evaluate **Codex against Claude Code** on tasks that represent your software development workflows. One skill handles discovery and task design; a bundled CLI runs the approved comparisons and opens a local dashboard.

## Start here: the customer starter prompt

**Open [CUSTOMER_STARTER_PROMPT.md](CUSTOMER_STARTER_PROMPT.md).** It is the customer entry point: install the plugin from this repository, then copy the evaluation prompt into a new Codex task in your project.

The file contains both installation commands and a copy-ready kickoff prompt. You do not need to clone this repository or assemble CLI commands yourself. The complete plugin is bundled in [`plugins/codex-eval-plugin/`](plugins/codex-eval-plugin/).

## The flow at a glance

**Install → describe your work → approve tasks → approve the run plan → follow progress → compare results.**

| Step | What the agent does | What you provide or decide |
| --- | --- | --- |
| 1. Discover | Learns the development workflows you want to evaluate. | Describe your work, allow selected local session history from the last 90 days, share selected repositories/PRs/MRs, or combine these. You can end discovery at any point. |
| 2. Propose | Suggests easy, medium, and hard tasks for each workflow, with short descriptions, acceptance checks, and benchmark inspiration. | Approve the task list or ask for changes. |
| 3. Prepare | Builds self-contained fixtures and checks that starting code fails and known-good solutions pass the grader. Checks CLI compatibility and model access. | Provide API keys securely and handle any required CLI upgrade or account-access step. |
| 4. Agree the run | Shows the exact models, reasoning efforts, repeats, concurrency, and spend policy. | Approve the plan before paid calls; narrow the selection or set a spend stop if wanted. |
| 5. Execute | Runs the approved tasks headlessly, grades them, records metrics, and updates progress inside Codex when visualization is available. | Usually nothing. If a provider or host blocks a call, run the specific command the agent supplies. |
| 6. Compare | Opens the prebuilt local dashboard combining both providers. | Explore task/model filters, cost, latency, tokens, and model × effort medians; inspect failures and export results. |

### Have these ready

- **Codex with the plugin installed:** follow the [starter prompt](CUSTOMER_STARTER_PROMPT.md), then start a task in your own project.
- **Workflows to evaluate:** a short description is enough to begin. History and repository access are optional and scoped by you.
- **OpenAI and Anthropic API keys with billing and model access:** keep them in your environment or an ignored `.env.local`; never paste keys into chat or commit them.
- **Local tools:** Python 3.11+, native Codex and Claude Code CLIs, and the runtime for your tasks. The bundled examples also need Node.js 18+. The agent checks readiness and flags upgrades.

The main checkpoints for you are **task approval** and **run-plan approval**. After that, the CLI handles execution and grading. Tests use lightweight local runners such as unittest, pytest, or Node tests; ordinary evaluations do not require Docker, iOS simulators, or desktop-app integrations. Actual failures remain recorded.

### Defaults to review before running

- **Models:** cataloged GPT-5.6 Sol/Terra/Luna and GPT-6 Astra; Claude Fable 5.1, Opus 5, Sonnet 5, and Haiku 4.5.
- **Effort:** every catalog-supported single-agent level for each model. Provider effort labels are not equivalent compute budgets.
- **Repeats:** three per task/model/effort; request one for a quick sweep.
- **Concurrency:** five attempts total, starting the next as soon as a slot opens.
- **Spend:** no spend stop by default. Set an optional threshold or narrow models, tasks, and efforts before approval.

The example matrix is **3 tasks × 36 model/effort configurations × 3 repeats = 324 scheduled attempts**. Catalog inclusion does not guarantee account access. Doctor checks local prerequisites and CLI versions; `doctor --check-model-access` also checks the selected IDs against account-visible models. See [provider troubleshooting](docs/TROUBLESHOOTING.md) before a large sweep.

## Requirements and results

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
