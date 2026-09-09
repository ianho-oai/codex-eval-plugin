# Changelog

## 0.2.2 — 2026-09-09

- Simplify the dashboard to a workflow evaluation chart with X-axis/Y-axis controls and model labels.
- Replace inline details with a six-field hover/focus popup; remove summary cards, tables, run badges, and explanatory footer.
- Use OpenAI developer-palette blue for Codex, retain Claude orange, and improve offline typography.

## 0.2.1 — 2026-09-09

- Disable implicit skill invocation; require an explicit request for Codex comparison evaluations.
- Exclude known automatic approval-review transcripts from local workflow discovery and disclose truncation separately from parser completeness.
- Clarify suite-directory ownership and task precedence requirements following three customer simulations.

## 0.2.0 — 2026-09-09

- Bundle 1,658 pinned public task references and 46 detailed design examples across 13 benchmark families.
- Add offline `examples` search and `portfolio` scaffolding.
- Require three difficulty tiers per discovered workflow in new customer suites, with validated benchmark inspiration or original-design rationale.
- Preserve legacy suites and explicit developer smoke tests.

## 0.1.1 — 2026-09-09

- Automatically combine all live runs under the evaluation workspace, refresh every 15 seconds, and preserve original result integrity and source provenance. Use a Codex-inspired charcoal/white theme with orange Claude points.
- Validation: 30 focused tests, self-check, export, and browser checks passed. All three saved provider smoke results are visible together.

## 0.1.0 — 2026-09-09

- Created the standalone single-skill plugin, native headless CLI adapters, discovery helpers, explicit suite approval, seeded matrix execution, checkpoints, grading, native telemetry normalization, dated pricing, CSV reporting, and reusable dark dashboard.
- Added public-source methodology references for Datacurve DeepSWE, SWE-bench, Terminal-Bench/Harbor, and Aider Polyglot. Added three original easy/medium/hard harness examples.
- Added reproducible ZIP export, source installation metadata, lightweight CI, project guidance, and focused offline tests. No customer history, credentials, raw runs, or internal sources are distributed.
- Load API keys from the current directory's ignored `.env.local`, preserving exported environment variables without executing shell code.
- Validation: baseline/oracle checks and 27 focused tests passed; real Codex smoke tests and a user-run Claude Code smoke test passed. See VALIDATION.md for current coverage.
- Follow-up: validate a pinned Docker environment before interpreting production comparisons. Roll back by checking out the previous approved release; use new run directories after task/protocol changes.
