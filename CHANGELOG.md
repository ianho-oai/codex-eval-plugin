# Changelog

## 0.1.0 — 2026-09-09

- Created the standalone single-skill plugin, native headless CLI adapters, discovery helpers, explicit suite approval, seeded matrix execution, checkpoints, grading, native telemetry normalization, dated pricing, CSV reporting, and reusable dark dashboard.
- Added public-source methodology references for Datacurve DeepSWE, SWE-bench, Terminal-Bench/Harbor, and Aider Polyglot. Added three original easy/medium/hard harness examples.
- Added reproducible ZIP export, source installation metadata, lightweight CI, project guidance, and focused offline tests. No customer history, credentials, raw runs, or internal sources are distributed.
- Validation: baseline/oracle checks and 25 focused tests passed; real Codex API smoke test passed; Claude Code live execution remains unavailable on the development host. See VALIDATION.md for current coverage.
- Follow-up: run the one-command Claude smoke test on a host with an Anthropic key and permitted egress. Validate a pinned Docker environment before interpreting production comparisons. Roll back by checking out the previous approved release; use new run directories after task/protocol changes.
