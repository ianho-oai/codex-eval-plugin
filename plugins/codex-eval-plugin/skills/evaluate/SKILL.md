---
name: evaluate
description: Use only when the user explicitly requests running evaluation tests comparing Codex against another coding agent, such as Claude Code or GitHub Copilot. Do not use for ordinary coding, unit tests, test authoring, general benchmarks, or plugin maintenance.
---

# Evaluate coding workflows

Use this skill only for an explicitly requested comparison of Codex with Claude Code, GitHub Copilot, or both. Ordinary coding, unit tests, and maintenance of this plugin do not start an evaluation. Preserve the existing explicit-only invocation policy.

Read [the evaluation workflow](WORKFLOW.md) before discovery, task design, configuration, or execution. That is the single maintained procedure used by this skill and direct repository users. Follow its customer choices, approval gates, evidence handling, and staged-repeat policy; load supporting references when the workflow calls for them.

Use the CLI, catalog, and dashboard bundled alongside this guide. Resolve `../../bin/codex-eval` from this skill directory and invoke it with Python 3.11+. No repository clone or separately installed evaluation engine is required. Do not replace the workflow with an online copy from another version.

If continuing an existing evaluation, retain its customer-approved scope, saved state, and frozen engine rather than restarting discovery or adding runs. Missing required workflow resources indicate an incomplete package; report that setup problem before paid execution.
