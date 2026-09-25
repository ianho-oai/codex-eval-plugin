# Codex Eval

A customer-owned evaluation kit comparing Codex with Claude Code, GitHub Copilot, or both. The plugin bundles one skill, the shared workflow guide, the CLI, reference tasks, and the local dashboard. It is an installation and discovery layer; repository and plugin users run the same engine.

## Start an evaluation

With the plugin installed, invoke `$evaluate` in your customer project and describe the workflows and providers you want to compare. The skill reads the [shared evaluation workflow](skills/evaluate/WORKFLOW.md), which owns discovery, task design, setup, approvals, execution, and results review.

For installation instructions, see the [customer starter prompt](https://github.com/ianho-oai/codex-eval-plugin/blob/master/CUSTOMER_STARTER_PROMPT.md). Once installed, use the workflow bundled with that version. Installing this plugin does not authorize history access or paid runs.

You can also use this package directly without installing the skill. Ask Codex to read `skills/evaluate/WORKFLOW.md` and use its bundled CLI. From this package directory:

```sh
python3 bin/codex-eval self-check
python3 bin/codex-eval --help
```

The source repository's `./eval` wrapper calls the same CLI. Keep the workflow, catalogs, CLI and dashboard from one package version together. Existing approved runs retain their frozen engines and evidence.

Python 3.11+ is required; the bundled example graders also need Node.js 18+. Native CLIs and credentials are needed only for selected providers. The orchestration and dashboard need no third-party Python packages.

## Explore without provider calls

```sh
python3 bin/codex-eval demo --output ./demo
python3 bin/codex-eval dashboard ./demo
```

Demo results are synthetic. These commands do not establish live model access or comparative performance. Customer setup and paid smoke checks follow the shared workflow.

## Reference map

| Resource | Purpose |
| --- | --- |
| [Evaluation workflow](skills/evaluate/WORKFLOW.md) | Authoritative guided process for installed and direct use |
| [Copilot setup](skills/evaluate/references/copilot.md) | Explicit GitHub account/token, CLI pinning, model/effort smoke checks and billing |
| [Task design](ceval/data/task-design.md) / [Hard tasks](skills/evaluate/references/hard-task-design.md) | Authoring customer-relevant Basic/Hard tasks and verifiers |
| [Benchmark catalog](ceval/data/catalog.md) | Offline references and source adaptation |
| [Methodology](ceval/data/methodology.md) | Metrics, pricing, aggregation, comparison limits and evidence |
| [Staged repeats](skills/evaluate/references/staged-repeats.md) | First-round review and separately approved follow-up observations |
| `python3 bin/codex-eval COMMAND --help` | Options supported by this exact installed version |

Customer discovery, credentials, fixtures and results belong in ignored customer-owned directories, never in the plugin package. Reports verify saved evidence; success comes from deterministic graders. Missing telemetry remains unknown. See the shared workflow for the complete execution contract.
