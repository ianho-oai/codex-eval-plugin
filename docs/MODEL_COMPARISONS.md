# Model comparisons

Reviewed 2026-09-10. These are candidates for customer evaluations, not universal equivalents or a ranking. Model availability must still pass preflight.

## How to compare

Establish correctness on representative tasks first, then compare cost and end-to-end latency. This follows [OpenAI's model selection guidance](https://developers.openai.com/api/docs/guides/model-selection). Use the same task fixtures, verifier, environment, limits, and repeat policy for each provider. Freeze settings before execution. Reasoning effort names are provider-specific; matching their names does not establish equal compute budgets.

## Default dashboard pairings

| Claude → Codex | Basis |
| --- | --- |
| Fable 5.1 → GPT-5.6 Sol | **Published comparison:** Anthropic's [Fable benchmark table](https://www.anthropic.com/claude/fable) includes Sol. |
| Fable 5.1 → GPT-6 Astra | **Our tier-based selection:** demanding reasoning and coding. |
| Opus 5 → GPT-5.6 Sol | **Our tier-based selection:** complex agentic/professional work. |
| Sonnet 5 → GPT-5.6 Terra | **Our tier-based selection:** balanced capability, speed, and cost. |
| Haiku 4.5 → GPT-5.6 Luna | **Our tier-based selection:** fast or economical high-volume work. |

The tier selections draw on the [Claude model overview](https://platform.claude.com/docs/en/models/overview) and [OpenAI model catalog](https://developers.openai.com/api/docs/models). They describe intended roles, not measured equivalence. Fable has two comparisons because the directly published comparison and the frontier-role comparison answer different questions.

The exportable source of truth is [pairings.js](../plugins/codex-eval-plugin/ceval/data/web/pairings.js), which records exact model IDs, reasons, and source links. Review these sources before adding new model versions; the dashboard never substitutes a different model. Pairings guide interpretation and do not narrow or expand an approved execution matrix.

## Display semantics

Dotted arrows appear only in **Median focus**, from the Claude diamond to the Codex diamond, when both models have visible medians under the current filters and axes. Haiku's arrow is absent if Haiku has no measurements. Exactly coincident medians have no displacement arrow. Switching axes or filters recalculates positions; log axes keep the same raw-unit median calculation.

Each endpoint retains the existing median of selected task/configuration averages, pooling efforts and runs. Coverage can differ between models, so these arrows are descriptive comparisons, not matched-task estimates or significance tests. They do not imply improvement or change pass/fail, data, or execution. Inspect endpoint tooltips for coverage; hover an arrow for its pairing rationale. For a controlled conclusion, evaluate the same approved task portfolio and review failures and missing telemetry alongside latency and cost.
