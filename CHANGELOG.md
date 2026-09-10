# Changelog

## 0.7.2 — 2026-09-10

- Verify the four Codex model rate cards against official Standard global API pricing; record source dates and Sol promotional-price timing.
- Read native Codex `cache_write_input_tokens` and apply its separate rate. Derive corrected historical dashboard/report estimates from native events and each run's original pricing, retaining signed results and recorded costs.
- Read long-context envelope multipliers from the frozen rate card instead of hardcoding them.

## 0.7.1 — 2026-09-10

- Remove run-stop banners from the dashboard. Preserve stop reasons in CLI reports and saved run data; retain synthetic-data and data-loading error notices.

## 0.7.0 — 2026-09-10

- Default to all cataloged GPT-5.6 / GPT-6 Astra and Claude models, including limited-access Claude lanes, with all supported single-agent efforts. Preflight displays the exact selected matrix and override guidance.
- Default spend stop to null; omit Claude native budget flags and continue through missing cost telemetry when no stop is set. Preserve explicit finite spend stops and add `--spend-stop-usd` / `--no-spend-stop` selectors.
- Keep existing approved simulation inputs frozen.

## 0.6.0 — 2026-09-10

- Default new suites to all catalog-supported model efforts; add `configure --all-efforts` and repeatable `--effort` selectors with capability validation.
- Include effort in chart labels and hover details so reasoning configurations remain distinguishable.
- Document all-effort evaluation plans and one-repeat quick sweeps; preserve three repeats as the general default.

## 0.5.0 — 2026-09-10

- Automatically retry explicit native rate-limit failures up to three times, with 30/60/120-second backoff and longer provider retry hints respected. Add `--rate-limit-retries` and `--retry-delay`.
- Preserve signed raw trials and combine retry cost, tokens, and elapsed/backoff time into the original evaluation repeat; keep unavailable retry costs null and expose known spend separately.
- Resume eligible rate-limited cells without repeating completed successes; pause after retry exhaustion and keep unrelated unknown-spend stops.

## 0.4.1 — 2026-09-10

- Default Codex and Claude Code session discovery to three months (90 days), with matching CLI help, skill instructions, and customer starter prompt. Explicit `--days` values remain supported.

## 0.4.0 — 2026-09-10

- Run up to five attempts concurrently by default with immediate slot refill, configurable using `run --workers`.
- Share a bounded worker pool across batches using `--slot-pool`; checkpoint each completed attempt, preserve deterministic dispatch order and verified resume, and drain in-flight work on pause or spend stops.
- Record scheduler settings and implementation hash with each invocation; retain the exact task and native-agent engine inputs.

## 0.3.1 — 2026-09-10

- Color averaged dashboard points blue for Codex or orange for Claude when at least one repeat passes; keep points grey when no repeats pass. Preserve exact pass counts and averaged measurements.

## 0.3.0 — 2026-09-09

- Add independent logarithmic axis toggles with explicit zero-value handling and clearer nested, provider-colored checkboxes.
- Add select-all and group toggles for task/difficulty and model/provider selections.
- Add authored two-to-three sentence workflow summaries, separate from detailed agent instructions.
- Plot per-run/task/model/effort averages across repeats, include failed attempts, preserve missing measurements, and show pass/repeat counts. All new runs, including smoke runs, default to three repeats.
- Add `configure` for explicit model IDs, task IDs, and repeat counts; preserve full task portfolios and invalidate prior approvals when execution settings change.
- Add `dashboard --scope` for independent simulation dashboards and write per-task averages alongside reports.

## 0.2.3 — 2026-09-09

- Add model checkboxes and task checkboxes grouped by difficulty, supporting any combination.
- Add a filtered task summary table with descriptions, difficulty, and development type; snapshot descriptions for new runs and recover available older definitions.
- Remove the outcome filter and use consistent grey for failed attempts.
- Add a top-right label toggle and remove label connector lines.
- Put axis selectors on a separate row and limit them to shared total cost, end-to-end latency, input/output tokens, and cache-read tokens; enlarge axis text and use rounded, comma-formatted tick intervals.

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
