# Codex Eval Plugin

Evaluate **Codex against Claude Code** on tasks that represent your software development workflows. One skill handles discovery and task design; a bundled CLI runs the approved comparisons and opens a local dashboard.

## Start here: the customer starter prompt

**Open [CUSTOMER_STARTER_PROMPT.md](CUSTOMER_STARTER_PROMPT.md).** It is the customer entry point: install the plugin from this repository, then copy the evaluation prompt into a new Codex task in your project.

The file contains both installation commands and a copy-ready kickoff prompt. You do not need to clone this repository or assemble CLI commands yourself. The complete plugin is bundled in [`plugins/codex-eval-plugin/`](plugins/codex-eval-plugin/).

### What happens next

1. **Discover your workflows.** Choose a conversation, selected local Codex/Claude Code history from the last 90 days, selected repositories/PRs/MRs, or a combination. You can stop discovery and request the proposal at any point.
2. **Approve representative tasks.** Review easy, medium, and hard tasks for each workflow, short descriptions, objective checks, and benchmark inspiration links or an original-design rationale.
3. **Review the execution plan.** The skill builds self-contained fixtures and validates the starting code and known-good solutions. Review the exact models, efforts, repeats, CLI versions, pricing, and limits before paid calls.
4. **Run and compare.** The fixed CLI executes, grades, and records every attempt. The prebuilt dashboard combines both providers, with cost/latency/token plots, filters, independent log axes, and task summaries.

Tasks use existing lightweight test runners such as unittest, pytest, or Node tests. Difficulty comes from coding work; ordinary tasks do not require Docker, iOS simulators, desktop-app integrations, or external services. The aim is achievable, correct results whose time and cost can be compared. Actual failures remain recorded.

### Defaults to review before running

- **Models:** cataloged GPT-5.6 Sol/Terra/Luna and GPT-6 Astra; Claude Fable 5.1, Opus 5, Sonnet 5, and Haiku 4.5.
- **Effort:** every catalog-supported single-agent level for each model. Provider effort labels are not equivalent compute budgets.
- **Repeats:** three per task/model/effort; request one for a quick sweep.
- **Concurrency:** five attempts total, starting the next as soon as a slot opens.
- **Spend:** no spend stop by default. Set an optional threshold or narrow models, tasks, and efforts before approval.

The example matrix is **3 tasks × 36 model/effort configurations × 3 repeats = 324 scheduled attempts**. Catalog inclusion does not guarantee account access. Doctor checks local prerequisites and known CLI minimum versions; it does not authenticate model access. See [provider troubleshooting](docs/TROUBLESHOOTING.md) before a large sweep.

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

Before final approval, run `./eval doctor SUITE --check-model-access` to compare selected IDs with account-visible models. If the CLI is outdated, ask the customer to upgrade, locate the upgraded executable, and update the exact pin before validation. Listing success does not establish native effort support; blocked checks stay unresolved until the customer supplies results.
