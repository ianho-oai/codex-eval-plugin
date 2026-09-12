# Changelog

## 0.9.7 — 2026-09-12

- Readiness checks tolerate text diagnostic messages and malformed nested event fields while still requiring successful shell execution evidence. A provider notice no longer crashes the gate before a later successful command is inspected.

## 0.9.6 — 2026-09-12

- Gate customer matrices on a bounded native edit-and-test check in the actual launch environment, preserving separate probe evidence, costs and failures.
- Retry recognized temporary capacity errors alongside rate limits, with cumulative ceilings and provider cooldowns shared across worker pools; retain every trial and unknown charge.
- Add `discovery-report` JSON/Markdown coverage receipts for dates, sampled/exported sources, exclusions, inferred workflows and customer confirmation.
- Enable logarithmic scales on both dashboard axes by default.

## 0.9.5 — 2026-09-12

- Include measured retry charges in report known-spend subtotals when the full attempt cost is unavailable. Keep missing-cost counts and cost-per-success uncertainty, avoid double counting complete costs, and preserve signed run evidence.

## 0.9.4 — 2026-09-12

- Default new customer suites and smoke runs to one iteration per task/model/effort. Keep the full default model/effort sweep and explicit repeat overrides.
- Present first-round results and costs before asking for two additional consistency rounds. Document separately approved follow-up runs and careful pooled reporting without mutating original evidence.

## 0.9.3 — 2026-09-11

- Treat Codex reconnect notices followed by terminal completion as recovered events. Still require a successful native process and deterministic grader; failed turns, trailing errors, and unfinished turns remain unsuccessful.
- Preserve original event evidence and usage. Add regression coverage for recovered rate limits, terminal failures, incomplete streams, and a verified pass without duplicate outer retries. Historical signed results and active frozen engines remain unchanged.

## 0.9.2 — 2026-09-11

- Make task quality an adaptive design, challenge, observe, diagnose, and repair loop. Use contract-driven counterexamples, sustained run observation, and bounded fair reruns under explicit repair scope. Keep initial authoring lightweight and preserve genuine failures.
- Clarify supported execution-context checks and terminal handoff when nested native sandboxing is unavailable; preserve sandbox policy and separate affected timing evidence.
- Accept valid dataclass-based Python candidates in the bundled slug grader by using normal import registration, with a regression test. Add targeted grader-design examples without treating them as exhaustive rules.

## 0.9.1 — 2026-09-11

- Keep local candidate and private agent-home directories beneath each attempt, preserve installed toolchain paths in Codex shells, and disable login-shell initialization without inheriting credentials.
- Record native helper/sandbox diagnostics separately from task scores and flag them during reflection, including otherwise passing attempts. Keep timeout, forbidden-file, and behavioral outcomes unchanged.
- Clarify the shared task deadline and backup-file cleanup requirements. Add regression coverage for environment setup, runtime warnings, and successful grading after agent timeout.
- Replace private run diaries and machine-specific operating notes with reusable customer and release documentation. Keep historical evidence in ignored evaluation directories.

## 0.9.0 — 2026-09-10

- Add deterministic `reflect` triage for per-task failure clusters and infrastructure errors, with optional graceful review pauses and an audited `review-clear` command. Preserve results, original user stops, and fixed grading.
- Add host-agent task-quality reflection: check visible contracts against independent valid alternatives, investigate early failures, and repair defective tasks through bounded, newly approved revisions with every affected lane rerun. Update the starter prompt and customer documentation.
- Keep active evaluation engines frozen and document feature-branch/PR releases for the protected default branch.

## 0.8.9 — 2026-09-10

- Make the customer flow and required inputs explicit in the README. Add a pull-request template, owner routing, and a lightweight description-format check.

## 0.8.8 — 2026-09-10

- Show the median controls, legend, and points only with two or more selected tasks; single-task views retain normal contrast.

- Group median diamonds by provider, model, and reasoning effort. Label each with its model and effort, and show the single effort in hover details. Preserve filters, focus behavior, and raw-unit median calculations.

## 0.8.7 — 2026-09-10

- Add read-only `progress RUN_DIR ...` checkpoint summaries and host-side visualize/live progress guidance during evaluation runs, with text fallback when unavailable. Preserve the headless harness and one-skill plugin.

## 0.8.6 — 2026-09-10

- Remove the comparison arrows, legend, and pairing assets. Preserve median diamonds, Median focus, and model-only median labels.

## 0.8.5 — 2026-09-10

- Add source-backed Claude-to-Codex dotted comparison arrows in Median focus only, with exact model pairings, filter/log-axis handling, and documented comparison limitations.

- Simplify median marker labels to model names only; retain median context in the legend, tooltip, and accessible description.

## 0.8.4 — 2026-09-10

- Add one median diamond per provider/model across the selected task/configuration averages, updating with filters and axes. Tooltip discloses coverage and selected-axis values.
- Add a top-right Median focus switch that fades individual points/labels and emphasizes medians. Preserve raw-unit calculations under log axes, include real zeros/failures, and report medians that cannot appear on log scales.

## 0.8.3 — 2026-09-10

- Exclude Mythos from default model sweeps. Require account-model checks and exact CLI-path/version verification in the evaluation skill, including an upgrade request when needed.
- Add `doctor --check-model-access`: compare exact IDs with authenticated provider listings, distinguish listed/unlisted/unprobed states, and return nonzero on failed checks without making inference calls.
- Support explicit, reversible report-view receipts for confirmed CLI-version errors and customer-selected model exclusions. Preserve signed outcomes and native evidence; replacement attempts use new suites and output directories.

## 0.8.2 — 2026-09-10

- Make the customer starter prompt the primary entry point throughout README, plugin documentation, and the rewritten product walkthrough. Move manual commands into a CLI reference and add provider troubleshooting.
- Detect Fable's minimum Claude Code version (2.1.251) before invoking it, retain an unstarted infrastructure result, and allow compatible model lanes to proceed. Expose account access as unprobed rather than implying doctor verifies entitlement.
- Update new-suite and optional Docker build Claude version defaults; preserve frozen inputs and document recovery from provider compatibility errors.

## 0.8.1 — 2026-09-10

- Frame task design around achievable, verified completion and comparing time, tokens, and cost. Keep environment provisioning outside measured tasks; scale difficulty through coding work with clear requirements and reasonable time limits.

## 0.8.0 — 2026-09-10

- Default new suites to local execution and self-contained tasks using existing lightweight test runners. Remove Docker/image setup from the default customer flow.
- Guide iOS/frontend discovery toward testable application logic and bundled fixtures; exclude simulator, desktop-app, browser-installation, and external-service setup unless explicitly requested.
- Include the task-design policy in portfolio scaffolds and preflight; preserve easy/medium/hard behavior coverage with simple environments.

## 0.7.3 — 2026-09-10

- Make permanent Fable 5.1 and Mythos 5.1 defaults explicit in the customer starter prompt and repository/plugin documentation, with all five supported efforts. Add a regression assertion for both default lanes.

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
- Clarify suite-directory ownership and task precedence requirements.

## 0.2.0 — 2026-09-09

- Bundle 1,658 pinned public task references and 46 detailed design examples across 13 benchmark families.
- Add offline `examples` search and `portfolio` scaffolding.
- Require three difficulty tiers per discovered workflow in new customer suites, with validated benchmark inspiration or original-design rationale.
- Preserve legacy suites and explicit developer smoke tests.

## 0.1.1 — 2026-09-09

- Automatically combine all live runs under the evaluation workspace, refresh every 15 seconds, and preserve original result integrity and source provenance. Use a Codex-inspired charcoal/white theme with orange Claude points.
- Add offline, export, browser, and provider-smoke validation procedures.

## 0.1.0 — 2026-09-09

- Created the standalone single-skill plugin, native headless CLI adapters, discovery helpers, explicit suite approval, seeded matrix execution, checkpoints, grading, native telemetry normalization, dated pricing, CSV reporting, and reusable dark dashboard.
- Added public-source methodology references for Datacurve DeepSWE, SWE-bench, Terminal-Bench/Harbor, and Aider Polyglot. Added three original easy/medium/hard harness examples.
- Added reproducible ZIP export, source installation metadata, lightweight CI, project guidance, and focused offline tests. No customer history, credentials, raw runs, or internal sources are distributed.
- Load API keys from the current directory's ignored `.env.local`, preserving exported environment variables without executing shell code.
- Document baseline/oracle checks, offline tests, and provider smoke validation separately; see VALIDATION.md for the reusable validation procedure.
- Use new run directories after task/protocol changes and keep prior approved releases available for reproducibility.
