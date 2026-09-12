# Evaluation contract

## What is controlled

Native `codex exec --json` and `claude -p --output-format stream-json` are API-authenticated agent loops. Each task/model/effort/repeat starts from fresh candidate files; only explicit rate-limit or temporary capacity failures receive bounded transport retries. The suite fixes task snapshots, prompt, permitted edits, grader, CLI/runtime versions, trial order, repeats, and pricing. Optional skills/plugins/MCP integrations are disabled.

Default tasks run locally with existing lightweight test runners, bundled data, and in-process service fakes. Task and grader behavior requires no network, application integrations, Docker, platform SDKs, or simulators. Only the coding-agent provider calls require API access. Graders run separately with sanitized environment variables and reside outside the candidate workspace. Local execution is for trusted tasks and cannot enforce grader secrecy or host isolation. If Docker is explicitly requested, use a pinned image with separate agent/verifier mounts; apply host egress controls separately.

Native product harnesses, built-in tools, prompts, tokenizers, and effort meanings differ. Therefore this compares Codex/model configurations with Claude Code/model configurations, not just base model intelligence. Native service load, provider caching, and inference remain nondeterministic. A clean invocation does not guarantee a cold provider cache. Preserve per-repeat rows and use the disclosed seeded order; never cherry-pick the fastest success. Sequential execution reduces contention but does not eliminate provider-side variation.

## Metrics

| Field | Meaning |
| --- | --- |
| completion | 1 only when native invocation succeeds, allowed edit checks pass, and the private verifier exits 0; otherwise 0 |
| valid / status | Distinguish behavioral failures and timeouts from provider, setup, or grader infrastructure errors |
| latency_seconds | Monotonic time for candidate preparation, native invocation, result capture, and grading; excludes global preflight |
| agent_seconds | Entire native headless subprocess including startup and tool work |
| grader_seconds | External verifier subprocess time |
| input_tokens | Total input including cache read/write tokens; Codex reports total input, Claude reports uncached separately |
| uncached_input_tokens | Input excluding cache reads (and, for Claude, cache writes); inspect provider/cache details before cross-provider use |
| output_tokens | Native output token total, including reasoning where provider accounting includes it |
| cache_read_tokens / cache_write_tokens | Native counts; missing stays null |
| reasoning_tokens | Native reported reasoning output, null when not available; never added again to output cost |
| turns / turn_unit | Codex completed conversation turns versus Claude native num_turns; not equivalent model-call counts |
| tool_calls | Completed Codex command/file-change items; Claude assistant tool-use blocks. Native tools differ. |
| cost_usd / cost_source | Claude reported total_cost_usd, or dated OpenAI standard-rate estimate |
| cost_lower_usd / cost_upper_usd | OpenAI standard-short estimate and conservative long-context/cache-write rate envelope, not an invoice guarantee |

OpenAI's aggregated turn events may omit cache-write counts and per-request context size. Estimate at the standard global short-context rate and retain an upper envelope allowing 2x input/cache rates, 1.5x output rates, and unknown writes charged at the cache-write price. Do not present this range as exact. No special service tier, regional processing, external tool surcharge, or enterprise discount is included. Recheck `rates.json` links before freezing; prices are stored with the run. There is no spend stop by default. With an explicit spend threshold, unrelated unknown cost pauses dispatch and known costs use the upper envelope; all in-flight invocations can overshoot the threshold. Claude's native max-budget setting is supplied only when a spend stop is configured. Provider billing controls are required for a hard cap.

All-attempt success rate counts every recorded attempt. Scorable success rate excludes infrastructure-invalid attempts and always reports their count. Pending/unstarted scheduled cells are shown separately. Cost per success includes measured spend from failed attempts; it stays null when any attempt's cost is missing or there are no successes. Wilson 95% intervals are descriptive, with independent-trial assumptions; a tiny portfolio cannot establish broad statistical superiority.

## Approval and integrity

`validate --check-graders` produces a receipt for exact task/pricing/runner contents. `approve --by` records the reviewer and seal; it is a local audit record, not a cryptographic proof of human identity. The skill obtains human approval before invoking it. `run` and `--resume` check the seal. Completed attempts have individual hashes, and report verifies them. These hashes detect accidental changes; someone with write access can replace hashes too. Local development mode exposes host files and cannot protect private graders from a malicious candidate. Use Docker mode for isolation comparisons.

Interrupted attempts are not automatically rerun, because a provider call may already have incurred cost. Stop, inspect the run, and create an approved new run if necessary. Only remove a stale `.run-lock` after confirming the old process/container has stopped. Never conflate synthetic `demo` points with live measurements.

## Native references

- [Codex non-interactive mode and JSON usage](https://learn.chatgpt.com/docs/non-interactive-mode)
- [OpenAI pricing](https://developers.openai.com/api/docs/pricing)
- [Claude Code CLI](https://code.claude.com/docs/en/cli-reference)
- [Claude models and exact API IDs](https://platform.claude.com/docs/en/models/overview)
- [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)

Checked 2026-09-09. Refresh exact CLI capability, public model metadata, and account access before customer execution.

## Queue concurrency

The run CLI defaults to five concurrent attempts. Dispatch follows the seeded pending-cell order; completion order depends on latency. Use `--workers 1` for sequential timing, or `--workers 5 --slot-pool evaluations/shared-workers` across batches to share five total slots. Agree on the concurrency before execution. Each invocation records the worker count and scheduler hash. Configured cost thresholds and unknown spend with an explicit threshold stop new dispatch; all in-flight attempts finish and are retained, so thresholds can overshoot by all active calls.

## Rate-limit recovery

Native rate-limit and temporary capacity errors may retry up to three times by default, with 30/60/120-second backoff and longer provider hints honored up to one hour. This is transport recovery within one evaluation repeat, using fresh workspaces and signed trial records. Cost/tokens aggregate across trials; latency includes automatic retry waits. Unavailable trial costs stay null with known spend exposed separately. Known-spend thresholds cannot enforce a hard cap on unreported retry charges. Retry exhaustion stops dispatch. Unrelated unknown spend stops dispatch only when a spend stop is configured. Verifier failures and auth/quota errors never receive this automatic recovery.

### Default model sweep and spend policy

New evaluations default to all cataloged GPT-5.6 models and GPT-6 Astra, plus cataloged default Claude models, across every supported single-agent effort level. Preflight lists the exact matrix and repeats, announces **no spend stop**, and tells the customer to specify otherwise before approval. Limited-access models are included; unavailable lanes remain visible.

`configure SUITE --all-models --all-efforts --no-spend-stop` restores these defaults. Select alternatives with repeated `--model PROVIDER:MODEL` / `--effort LEVEL` flags. Set an optional stop with `--spend-stop-usd AMOUNT`. A null `limits.spend_stop_usd` disables both the scheduler spend stop and Claude's native budget flag; missing costs remain null and do not stop dispatch in this mode. Time limits, turn limits, bounded rate-limit retries, and explicit pause requests still apply. Existing approved suites retain their frozen settings.

### Model medians

Each model has a diamond marker showing the median X and median Y of its currently selected task/configuration averages. The top-right **Median focus** switch fades task points and labels while enlarging the median markers. Turn it off to restore normal contrast; median diamonds remain visible.

Each displayed task/configuration point gets equal weight, pooling selected efforts and saved runs for that model. This is a descriptive median of the plotted averages, not a median of raw attempts or a matched-task leaderboard. The tooltip shows the number of contributing points/tasks, effort levels, and both selected-axis values. Only points with both axis measurements contribute; genuine zeros and failures remain included. Log toggles change placement, not the calculation; nonpositive medians cannot be plotted on log axes and are counted in the plot note.

Customer runs gate dispatch on a bounded native edit-and-test probe per provider in the actual launch context, with separate receipts and costs included in spend checks. Discovery proposals include the CLI-generated coverage receipt and customer-confirmed scope; selected samples and exports never imply a complete lookback crawl. Both dashboard log axes default on. See the evaluate skill and its task-review reference for operational guidance.
