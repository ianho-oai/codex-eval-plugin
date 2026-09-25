# Validation guide

## 0.12.0 release audit — 2026-09-25

- All 151 offline tests passed, including Basic/Hard portfolio counts, legacy suite compatibility, first-round/follow-up scheduling, three-provider configuration, transient recovery, score/grouping symmetry, cost per success, and current-rate Codex dashboard pricing with unchanged signed evidence.
- Self-check, both dashboard JavaScript syntax checks, local Markdown links, and `git diff --check` passed. The reproducible export contains 58 files and exactly one skill, excluding customer data and credentials.
- The extracted ZIP independently passed self-check, Codex + Claude / Codex + Copilot / three-provider configuration, selection preservation in subsequent configuration, and all three bundled baseline-fail/oracle-pass checks.
- Browser validation used a separate synthetic three-provider preview: stable identical dropdowns, score on either axis, grouped cost per success, missing costs, model/effort grouping, saved settings and reload, two-provider filtering, single-task aggregate mode, pie toggles, readable tooltips, and definitions below the chart. No browser console errors were observed. The existing customer dashboard and saved results were preserved.

This audit made no inference calls and does not establish new live model/account availability. Copilot model/effort access still needs the documented customer smoke checks. Dashboard grouping is descriptive; separately approved first and follow-up runs require explicit provenance checks before a pooled three-observation report. New approvals use the updated engine; existing frozen engines and evidence must remain intact.

Use these checks before sharing a release. Keep run logs, screenshots, provider responses, and measured results in ignored `evaluations/` directories. This repository documents the validation procedure; it does not publish comparative model results.

## Offline release checks

```sh
python3 -m unittest discover -s tests -v
./eval self-check
./eval export --output dist
```

The tests cover deterministic grading, synthetic baseline/known-good solutions, native protocol emulators, telemetry, sealed-input integrity, scheduling, and reporting. Protocol emulators do not establish live provider access or model performance.

Extract the exported ZIP into a fresh directory and run its `bin/codex-eval self-check` without the parent repository. Check that the archive contains exactly one skill and only intended plugin files. For dashboard changes, use synthetic fixtures to review filters, axes, labels, missing metrics, keyboard interactions, and browser errors.

## Live provider checks

Check the exact executable, version pin, credentials, and selected model IDs before approving execution:

```sh
./eval doctor SUITE --check-model-access
```

Model listings establish visibility, not inference or effort support. An approved smoke run can check one native configuration in an environment permitted to reach the provider. For example, with credentials configured securely:

```sh
./eval smoke --provider claude --output evaluations/claude-smoke
./eval dashboard evaluations/claude-smoke/run
```

Use a fresh output directory for each check and `--model` for a specific model. Preserve native responses, grader outcomes, usage, and missing telemetry locally. A smoke test is not a controlled cross-model comparison. See [provider troubleshooting](docs/TROUBLESHOOTING.md) for compatibility failures and recovery.

## Evidence boundaries

- Record offline, browser, live-provider, and Docker coverage separately; leave unavailable checks explicit.
- Confirm results through the independent grader and saved artifacts. Agent claims, account listings, or a running checkpoint do not prove successful completion.
- Local execution does not enforce host isolation or held-out-test secrecy. Docker execution needs separate validation with pinned images.
- Changed tasks, CLI pins, settings, or pricing require new validation and approval. Preserve earlier suites, results, and costs.

## Copilot coverage

Copilot remains opt-in and local-only. Offline tests cover provider selection and sealing, explicit native account versus token mode, ignored ambient tokens, CLI path/version pinning, configurable smoke effort and credit limits, native editing with real grading, successful shell receipts for the customer readiness gate, model substitution, telemetry gaps, and nonzero smoke exits. Native usage receipt tests distinguish cumulative root credits from overlapping child totals and keep net invoice cost unknown.

On 2026-09-23, personal native Copilot login with CLI 1.0.88 enabled unattended GPT-6 Astra and GPT-5.6 Sol low-effort HTTP-cache attempts. Independent grading recorded both a pass and a genuine candidate failure. Additional harder-2 tasks use a separate frozen engine and remain customer-owned evidence. Earlier authentication/policy failures remain preserved. These pilots establish native editing/grading compatibility on that account and host, not universal model access or comparative superiority.

An authenticated `models.list` runtime check reported Astra at low/medium/high/xhigh/max and Sol/Terra at none/low/medium/high/xhigh/max. Fifteen scored runtime pilots exercised every additional setting on durable-workflow: twelve passes, two genuine candidate failures at none, and one Terra max timeout. Native OpenTelemetry request attributes confirmed the selected effort levels. Listing support, successful execution, and deterministic task success are separate claims. The broader five-task sweep is separate private evidence; a 600-second Copilot cutoff differs from the historical unlimited Codex run.

Retained live usage receipts were replayed offline through the new parser: they supply tokens and credits absent from JSONL, with top-level credit-derived usage value reported separately from `cost_usd`. Do not rewrite signed historical rows when adding parsing support. The newly guided customer setup is covered with native protocol emulators and real deterministic graders; it does not claim a fresh customer's account was exercised. See the [Copilot reference](plugins/codex-eval-plugin/skills/evaluate/references/copilot.md).

## Copilot integration audit — 2026-09-24

Version 0.11.0 passed 136 offline tests, self-check, JavaScript syntax and diff checks. The tests cover explicit provider selection, model/effort validation, native-account/token isolation, capability rejection, native edit/test readiness, queued Copilot emulation, deterministic grading, resume, separate billing, and missing retry receipts. The extracted 58-file ZIP independently passed self-check, provider configuration, catalog filtering, and all three baseline/oracle grader checks. Chrome verified the three-provider dashboard, Copilot credit/value axes, missing-measurement notices, medians, provider filters and saved-axis reload. Test fixtures are synthetic; this audit made no paid inference calls. The installed CLI 1.0.88 still exposes the required reasoning-effort and usage-output flags. Earlier live coverage is recorded separately above.

Copilot remains opt-in and local-only. Authenticated model listing is not integrated into doctor; use the documented native picker and approved model/effort smoke checks. API-key and Copilot account billing remain separate, and credit-derived usage value is not net invoice cost. Source and ZIP are prepared locally; no Git publication or installed-plugin update is implied.
