# Project context

**When to read:** Changing the evaluation contract or package architecture.
**When to update:** Ownership, architecture, or compatibility boundaries change.

## Architecture and source of truth

The plugin is a self-contained distribution of the evaluation kit. It exposes exactly one explicit-only skill, which loads the shared [evaluation workflow](../plugins/codex-eval-plugin/skills/evaluate/WORKFLOW.md). Repository users read that same guide and invoke `./eval`; the wrapper imports the packaged CLI. There is no separate repository engine or generated dashboard.

Keep the skill entrypoint, starter prompt and READMEs short: explain how to start and link to the maintained procedure. Change workflow policy in the shared guide or its focused references, not in parallel copies of the customer prompt. Product overviews describe the experience; CLI documentation describes commands.

| Concern | Maintained resource |
| --- | --- |
| Discovery, customer choices, task and run approvals, execution, results | [Shared workflow](../plugins/codex-eval-plugin/skills/evaluate/WORKFLOW.md) |
| Task construction and Basic/Hard coverage | [Task design](../plugins/codex-eval-plugin/ceval/data/task-design.md), [Hard design](../plugins/codex-eval-plugin/skills/evaluate/references/hard-task-design.md), `ceval/catalog.py` and suite/task schemas |
| Counterexamples, review signals and bounded repairs | [Task review](../plugins/codex-eval-plugin/skills/evaluate/references/task-review.md) |
| Optional Copilot authentication, permissions and model checks | [Copilot setup](../plugins/codex-eval-plugin/skills/evaluate/references/copilot.md) |
| First round and optional two-round follow-up | [Staged repeats](../plugins/codex-eval-plugin/skills/evaluate/references/staged-repeats.md) |
| Metrics, grouping, retry accounting and pricing | [Methodology](../plugins/codex-eval-plugin/ceval/data/methodology.md) |
| Host-side live progress | [Progress view](../plugins/codex-eval-plugin/skills/evaluate/references/progress-view.md) |
| Manual command options and run receipts | [CLI reference](../docs/CLI_REFERENCE.md) and version-matched CLI help |
| Distribution and validation | [Release guide](release.md), [Validation](../VALIDATION.md) |

## Engineering invariants

- Customer data, credentials, repository snapshots and raw results stay in ignored evaluation directories. Exports contain original code, synthetic examples and public-source references.
- The host agent designs tasks and interprets evidence. Native provider CLIs perform evaluated coding work; deterministic verifiers decide scores. No model generates dashboards or scores after approval.
- Keep tasks, settings, CLI versions, pricing and engine contents frozen for approved execution. Preserve existing engines while runs are active or pending. Changed inputs require a new validated revision and approval within the customer's actual authorization.
- Preserve schema 1/2 and historical difficulty meanings. New schema 3 suites use Basic/Hard; reference inspiration does not establish official benchmark-equivalent difficulty. Initialized examples are harness checks, not a completed customer portfolio.
- Native harnesses and effort labels differ. Preserve failures, missing telemetry, trial provenance and concurrency caveats; a combined view alone does not prove experimental parity.
- Dashboard projections never rewrite signed evidence. Current-card Codex estimates retain original costs and pricing provenance; Claude native cost and Copilot usage valuation retain their distinct meanings. Keep static reports and full spend accounting separate from display projections.
- Local trusted-fixture execution does not enforce grader secrecy or host isolation. Preserve host controls and configured native sandboxing; do not route around provider access restrictions.

General coding and maintenance of this repository must not trigger a customer evaluation. Keep the explicit-only invocation policy in `skills/evaluate/agents/openai.yaml`. Updating the packaged guide does not update an already installed copy or authorize additional inference.
