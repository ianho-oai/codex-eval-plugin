# Project context

**When to read:** Before changing the evaluation contract.
**When to update:** When behavior, assumptions, or verified limitations change.

## Contract

Customer discovery combines interview, opt-in local history, and selected repository/PR/MR evidence. The single skill designs customer-specific tasks; the CLI freezes, validates, approves, executes, grades, normalizes, resumes, and displays them. No AI is used to construct dashboards or to decide scores after approval.

Compare native Codex and Claude Code agents using API-key authentication. Their built-in prompts and tool implementations differ; this is a product-and-model comparison, not a controlled model-only experiment. Deterministic orchestration does not imply deterministic inference. Use repeated trials and retain every scheduled cell.

Default execution uses a pinned Docker image shared by both products, clean writable candidate copies, separate verifier containers, no hidden grader/solution mounts in agent containers, and fixed CPU/memory limits. Local execution is an explicitly selected trusted-code development mode; it cannot provide held-out-test secrecy or host isolation. Do not label local runs hermetic.

Scores are binary. Infrastructure errors and interrupted attempts score zero in the all-attempt summary but are separately categorized. Scorable success rates exclude infrastructure-invalid rows and always display their count. Missing usage is null. Unknown spend pauses execution because a spend threshold cannot be enforced from missing telemetry.

The spend threshold is checked between sequential calls. A single call can overshoot it; provider-side limits remain necessary for a hard billing cap. No automatic provider fallback, retries, or silent model substitution.

Current official sources expose OpenAI 5.6 Sol/Terra/Luna and GPT-6 Astra. Model IDs and pricing are dated snapshots; account access must be probed and reviewed before use. A user-run Claude Sonnet 5 smoke test passed and its saved results were verified locally. The agent session's Anthropic endpoint remains restricted; user-terminal success does not establish agent-session access. See VALIDATION.md for measured coverage.
