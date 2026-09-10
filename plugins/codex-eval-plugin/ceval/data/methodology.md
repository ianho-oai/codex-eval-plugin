# Evaluation contract

## What is controlled

Native `codex exec --json` and `claude -p --output-format stream-json` are API-authenticated agent loops. A task/model/effort/repeat is one fresh invocation with no automated retry. The suite fixes task snapshots, prompt, permitted edits, grader, CLI versions, image, resource limits, trial order, repeats, and pricing. It disables optional skill/plugin/MCP integrations. Docker agents see only candidate files; graders and oracle snapshots are absent. Graders run separately without network or credentials. Docker's agent network is `bridge`, so the host must apply the desired API egress allowlist. Agent tools can access credentials within their own process/container; use dedicated evaluation keys and trusted task dependencies. This kit is not a hostile-code security boundary.

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

OpenAI's aggregated turn events may omit cache-write counts and per-request context size. Estimate at the standard global short-context rate and retain an upper envelope allowing 2x input/cache rates, 1.5x output rates, and unknown writes charged at the cache-write price. Do not present this range as exact. No special service tier, regional processing, external tool surcharge, or enterprise discount is included. Recheck `rates.json` links before freezing; prices are stored with the run. Unknown cost stops further paid calls. The stop threshold uses the upper envelope between calls, so a single invocation can overshoot it. Claude's native max-budget setting is also supplied; provider billing controls are required for a hard cap.

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

The run CLI defaults to five concurrent attempts. Dispatch follows the seeded pending-cell order; completion order depends on latency. Use `--workers 1` for sequential timing, or `--workers 5 --slot-pool evaluations/shared-workers` across batches to share five total slots. Agree on the concurrency before execution. Each invocation records the worker count and scheduler hash. Cost thresholds and unknown spend stop new dispatch; all in-flight attempts finish and are retained, so thresholds can overshoot by all active calls.

## Rate-limit recovery

Native rate-limit errors may retry up to three times by default, with 30/60/120-second backoff and longer provider hints honored. This is transport recovery within one evaluation repeat, using fresh workspaces and signed trial records. Cost/tokens aggregate across trials; latency includes automatic retry waits. Unavailable trial costs stay null with known spend exposed separately. Known-spend thresholds cannot enforce a hard cap on unreported retry charges. Retry exhaustion and unrelated unknown spend stop dispatch. Verifier failures and auth/quota errors never receive this automatic recovery.
