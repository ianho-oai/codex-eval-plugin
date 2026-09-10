# Validation coverage

As of 2026-09-09. This is a functional first release; no comparative model-performance claim is made.

| Surface | Evidence |
| --- | --- |
| Core CLI | 30 focused offline tests pass in approximately 6 seconds, including local API-key loading, environment precedence, automatic run discovery, and integrity checks across combined results |
| Example graders | All three baselines fail; all three known-good solutions pass; behavioral shortcut mutants fail |
| Native adapters | Both adapters exercise subprocess execution, workspace reset, external grading, telemetry normalization, result integrity, and resume using offline protocol emulators |
| Real Codex | GPT-5.6 Luna and GPT-5.6 Sol each completed the original slug-normalization task through Codex CLI 0.153.4, using API-key billing, and passed the independent grader; Sol used the one-command smoke workflow |
| Real Claude Code | User-run Claude Sonnet 5 smoke test through Claude Code 2.1.220 passed the independent slug-normalization grader; saved results were inspected locally |
| Dark dashboard | Browser inspection verified the charcoal/white theme, all three live model results together, provider filtering, and axis changes; earlier checks cover failure labels, synthetic-data warning, and missing metrics |
| Export and installation | ZIP bytes and checksum reproduce; the extracted plugin runs independently; Codex successfully installed the plugin from the repository marketplace into a temporary validation profile |
| Docker execution | Implemented with an immutable image requirement and separate agent/grader containers; live Docker execution has not been validated on the restricted development host |

The real Codex smoke test took 56.79 seconds end to end and reported 137,284 input / 3,337 output tokens. Standard-rate estimated cost was $0.00993. Native sandbox helper errors occurred before the task was completed through other available native tools; this measures development-host validation, not representative latency or cost. Raw artifacts remain local and ignored.

The subsequent GPT-5.6 Sol one-command smoke test also passed: 97.75 seconds, 132,391 input / 2,720 output tokens, and $0.16307 standard-rate estimated cost. These two small validation runs used separate sealed suites and do not constitute a controlled model comparison.

An earlier attempt was interrupted while the CLI could not use the host-managed network proxy. The environment allowlist was fixed to preserve managed proxy and certificate settings. No alternate endpoint or auth fallback was introduced.

The user-run Claude Sonnet 5 smoke test passed in 14.99 seconds with 4 native turns, 8,926 total input tokens (including 6,340 cache-read and 2,579 cache-write tokens), 649 output tokens, and $0.02208425 reported by Claude Code. This was a separate trusted-local smoke run, not a controlled comparison with the Codex runs. The agent session still has restricted Anthropic egress; successful user-terminal execution does not change that restriction.

## Run Claude validation

In a permitted terminal with Claude Code and `ANTHROPIC_API_KEY` configured in the environment or current directory's ignored `.env.local` (choose a fresh output directory for subsequent runs):

```sh
./eval smoke --provider claude --output evaluations/claude-smoke
./eval dashboard evaluations/claude-smoke/run
```

The command checks the installed version and capabilities, runs one original trusted-local task, and writes measured results to `evaluations/claude-smoke/run`. Pass `--model` to test a specific account-visible model. Keep secrets out of chat and Git. Share only sanitized results if further debugging is needed.

## 0.2.0 task catalog and portfolio coverage — 2026-09-09

- 35 offline tests pass, including per-workflow tier enforcement, provenance validation, catalog integrity/search, original-task fallback, and legacy suite compatibility.
- `./eval self-check` passes. Standalone ZIP extraction passes self-check and offline example lookup without the source repository.
- The catalog contains 1,658 mechanically indexed task records from seven pinned public dataset sources, all fetched, plus 46 original design cards across 13 families. This verifies reference inventory/format, not upstream benchmark execution or exhaustive verifier quality.
- The new catalog does not imply a new cross-provider result. Customer simulations and their native-run evidence remain in ignored local evaluation directories.

## 0.2.1 invocation and history fixes — 2026-09-09

- 36 offline tests pass. Skill validation, self-check, and standalone ZIP extraction pass; the exported invocation policy sets `allow_implicit_invocation: false`.
- Local history verification confirms known automated review transcripts are excluded, retained excerpt truncation is counted, and parser completeness is reported separately.
- Three customer simulations exercised interview, recent public PR, and local-history discovery. Their source evidence, approvals, paid results, and observer findings remain in ignored `evaluations/customer-simulations/`. Prepared comparison lanes use the same frozen 0.2.0 runner as the completed trials; the source plugin advances independently.
- Anthropic execution remains blocked by this host's explicit endpoint policy. A frozen-runner script is prepared for the user's terminal; no cross-provider result is claimed.

## 0.2.2 dashboard simplification — 2026-09-09

- 36 offline tests, JavaScript syntax validation, and plugin self-check pass; the standalone ZIP exports successfully.
- Browser review verified the chart-first layout, model-name labels, six-field point popups, keyboard activation/Escape, task/provider/outcome filtering, alternate axes, missing-measurement empty state, and zero removed summary tables. No console errors were observed.
- Typography stays offline with OpenAI Sans when installed and system fallbacks. Codex uses blue300 from the checked official OpenAI developer palette; Claude retains orange.
- UI simplification does not alter source runs, grading, prices, metrics, CSV, or report data. Frozen comparison engines remain in their original evaluation directories.

## 0.2.3 dashboard controls and task descriptions — 2026-09-09

- 37 offline tests pass, including run-time task-description snapshots, matching legacy definitions, combined source attribution, baseline/oracle checks, and unchanged signed result records.
- Self-check, JavaScript syntax, export, and extracted standalone self-check pass.
- Browser review verified all 21 points and 10 deduplicated task summaries; task checkboxes grouped by difficulty; arbitrary model combinations; table filtering; separate axis row; five shared metrics; larger rounded tick labels; label toggle without connectors; six-field popup; and consistent grey for all four failures. No browser console errors observed.
- Descriptions for older runs come from matching local task definitions when available; new runs snapshot descriptions. This release does not rerun or alter paid evaluations.

## 0.3.0 configurable repeated evaluations — 2026-09-09

- 40 offline tests pass, including model/task/repeat selection, approval invalidation, invalid-selection rollback, scoped dashboards, separate-run averages, partial repeats, failure-inclusive means, and missing telemetry. Self-check, JavaScript syntax, export, and extracted standalone self-check pass.
- Browser checks verify global/difficulty bulk selections, nested groups, provider-colored checkboxes, short summary fallback, independent log axes, finite coordinates, and clear mean labels. No console errors observed.
- Three new customer-role simulations prepared nine tasks with authored two-sentence summaries. Nine starting baselines fail, nine oracles pass, and sixteen targeted mutants are rejected. Evidence and fictional dialogues are ignored/local.
- The expanded live plan has 108 Codex attempts and 54 Claude attempts (three repeats for six models across nine tasks). The v0.3.0 engine and suites are frozen separately. Codex execution was attempted, then paused after repeated connection timeouts: one timeout and one interrupted attempt are retained, with unknown usage/cost. Both WebSocket and HTTPS connection probes also timed out. Fresh terminal-run commands are prepared; Claude requires the user-terminal command because this session's host disallows Anthropic. Completion and current coverage must be read from local round2 results; preparation alone is not a live result.

## 0.4.0 five-slot queue — 2026-09-10

- All 46 offline tests pass, including five simultaneous attempts, immediate refill before the slowest finishes, shared slot limits, verified resume, graceful pause, unknown-spend draining, and both native protocol emulators with real workspace/grader execution.
- Self-check, skill validation, deterministic export, and the extracted-plugin self-check pass.
- Live round2 queue started additional Codex GitHub/history attempts while reserving one slot for each existing sequential dispatcher. All five slots were occupied; both new lanes produced verified passing results. Native engine/task approvals remain unchanged; the explicitly authorized scheduling upgrade records its own hash and concurrency metadata.
- Live simulations remain in progress. Some Luna calls hit the account token-per-minute limit; these remain provider errors with measured spend, without automatic retries. Concurrent latency can include shared-host contention. No comparative model-performance conclusion is claimed.

## 0.5.0 rate-limit retries — 2026-09-10

- All 52 offline tests pass, including bounded retry exhaustion, resume without repeating successes, signed trial integrity, cost/time aggregation, incomplete retry costs, native-error-only detection, and exclusion of verifier failures and recovered native errors.
- Self-check, skill validation and standalone export pass. Each scheduled repeat retains all native trials; retries do not add extra benchmark samples. Known retry spend is retained separately when total usage is unavailable.
- Stopped round2 Codex runs resumed with the explicitly authorized retry policy around their unchanged frozen native engine. Previously rate-limited Luna tasks returned passing results in interview, GitHub and history lanes. Full runs are still in progress; no overall comparative performance claim is made.

## 0.6.0 effort sweeps — 2026-09-10

- All 53 offline tests pass, including model-specific effort expansion, atomic rejection of unsupported selections, and narrowed effort selection. Self-check, skill validation, and standalone export pass.
- Chrome review confirms effort appears beside model names in chart labels and six-field point details. All four existing dashboard endpoints respond and retain prior results.
- Six new frozen suites cover three existing discovery simulations, four Codex models and two Claude Code models, five single-agent effort levels each, and one repeat: 180 Codex plus 90 Claude Code scheduled attempts. Every baseline fails and every known-good solution passes for all six suites.
- The paid Codex sweep has started and its first xhigh attempt passed the independent grader. Full sweep outcomes are pending; Claude effort sweeps require the user's permitted terminal because this session blocks Anthropic egress. These are trusted-local runs with five shared workers, the existing time/budget limits, and bounded rate-limit retries.
- Installed Codex capability records expose low/medium/high/xhigh/max for these fixed single-agent lanes; ultra changes delegation behavior. Claude Code 2.1.220 advertises the same five effort spellings. Catalog scope notes preserve these limitations rather than assuming raw API controls and native agent modes are interchangeable.

## 0.7.0 defaults and optional spend stop — 2026-09-10

- All 55 offline tests pass. New coverage verifies the complete catalog model/effort default, restoring defaults after narrowing, optional spend limits changing the approval seal, and removing Claude's native budget flag when unlimited.
- A queue test completes all six attempts despite high and missing costs with no spend stop; existing finite-budget and unknown-cost stop tests still pass. Missing costs remain null.
- Self-check, skill validation, reproducible export, and self-check from the extracted standalone ZIP pass. Default sample schedule now contains 369 cells (three tasks, 41 model/effort configurations, three repeats).
- Preflight and plan expose the selected matrix, repeats, spend policy, and override instructions. No new paid calls were needed to validate these configuration changes. Previously frozen paid simulations retain their approved inputs and runner.

## 0.7.1 dashboard stop notices — 2026-09-10

- All 55 tests, self-check, and plugin export pass.
- Refreshed all four Chrome dashboards and confirmed the run-stop banner is hidden and empty while plotted results remain visible. Saved run state and CLI diagnostics are unchanged.

## 0.7.2 Codex pricing audit — 2026-09-10

- Verified all four bundled Codex model prices, cache-write rates, and long-context multipliers against https://developers.openai.com/api/docs/pricing. Numeric rates were already correct; OpenAI verification dates and model-page references are now recorded separately from Anthropic verification.
- Actual saved Codex 0.153.4 events expose `cache_write_input_tokens`; the previous parser read only `cache_creation_input_tokens`. Corrected the parser while retaining compatibility with that older spelling. Reasoning remains included in output, with cached reads subtracted from total input before charging other input.
- Existing report/dashboard views now derive corrected cache-write estimates from native logs and original per-run rates, after checking signed result integrity and matching input/output/cache-read totals. Corrections retain the recorded cost, evidence hashes, and missing retry costs. Original run files and scores are untouched.
- All 57 tests, self-check, and export pass, including real-field cache-write arithmetic, impossible token partitions, historical corrections, and unknown-cost retry preservation. All four dashboard APIs serve corrected estimates.
- Costs remain Standard global estimates. Native turn totals do not reveal each request's context tier; long-context/cache-write uncertainty is retained as an upper estimate. Fast-mode/regional pricing is outside this fixed rate-card scope.

## 0.7.3 permanent Fable/Mythos defaults — 2026-09-10

- All 57 tests, self-check, and export pass. The default-suite regression explicitly requires Fable 5.1 and Mythos 5.1 with low/medium/high/xhigh/max effort.
- Three additional local simulation suites are prepared with one repeat and no spend stop (90 attempts total), preserving existing suites. Baseline/oracle checks pass and local Claude CLI/key preflight passes. Live execution requires the user's permitted terminal; it has not been launched by this agent session.

## 0.8.0 self-contained local task defaults — 2026-09-10

- All 57 tests pass, including the default-init mode assertion and existing local native-adapter, oracle/baseline, queue, and reporting checks. Self-check, skill validation, and standalone export pass.
- Extracted the release ZIP independently and verified that `init` creates a local suite with no image requirement.
- Updated task design, the single skill, portfolio scaffold guidance, preflight output, customer prompt, and repository/plugin documentation to prefer existing simple test runners and bundled fixtures. Native-app workflows are adapted to testable logic with disclosed coverage limits; Docker/platform integrations require an explicit request.
- No new paid runs were required for this policy/default change. Previously frozen suites and recorded outcomes remain intact; this change does not establish that an existing external iOS task's failures were caused by setup.

## 0.8.1 achievable-task evaluation objective — 2026-09-10

- All 57 tests, self-check, skill validation, and export pass.
- Skill, task design, portfolio guidance, and customer-facing documentation now emphasize achievable tasks, verified completion, and cost/latency/token comparisons. Environment preparation precedes measured tasks; shared objective checks and actual failures remain visible.
- This instruction update does not rerun or relabel existing results.

## 0.8.2 starter-prompt entry point and provider diagnostics — 2026-09-10

- All 59 offline tests pass, including an old-CLI Fable rejection that leaves the compatible Sonnet lane runnable, and a minimum-version check that still enforces the suite's exact CLI pin. CLI self-check, export, extracted standalone self-check, and local documentation-link checks pass.
- README, plugin README, customer prompt, and rewritten OVERVIEW consistently start with the customer starter prompt. Manual commands moved to `docs/CLI_REFERENCE.md`; `docs/TROUBLESHOOTING.md` documents local preflight versus model access and recovery with fresh approved inputs. Corrected stale dashboard-color, environment, spend-stop, and repeat-color documentation.
- Inspected native errors from the additional Fable/Mythos simulations: Claude Code 2.1.220 rejects Fable and requires 2.1.251 or newer; Mythos reports an unknown/inaccessible selected model. These are provider errors, not evidence of coding-task failure. Local key/version/flag preflight in 0.7.3 did not establish per-model support or account access.
- This release checks known model minimum CLI versions and explicitly marks account access as unprobed. New suite and optional Docker build defaults use Claude Code 2.1.251. The installed CLI remains 2.1.220; a live retry with a newer version and Mythos access verification is still outstanding. No new paid calls or live Docker build were performed for this release.
- Existing frozen suites and signed results remain unchanged. Requested a graceful pause for the unfinished affected history batch; its last recorded state remains running, so drain completion is not confirmed.

## 0.8.3 Fable resets, Mythos removal, and account checks — 2026-09-10

- All 63 offline tests, self-check, skill validation, and standalone export checks pass. New tests verify reset evidence hashes and error classification, retention of original outcomes, model exclusion of pending cells, authenticated listing comparison for each selected provider, and unresolved/failed listing states.
- The user-run upgraded CLI check completed: Claude Code 2.1.258 passed the Fable sync-config task; Mythos still returned a provider error. The working executable was in the user's Node installation while the old Homebrew CLI remained 2.1.220.
- At the user's request, reset 40 confirmed Fable CLI-version errors from active comparisons (15 interview, 15 GitHub, 10 history) using explicit hash-checked view receipts. Signed results and native logs remain unchanged. Prepared 40 replacement attempts with identical task/effort combinations, one repeat, the upgraded executable, and five shared workers; these replacements are pending user-terminal execution.
- Removed Mythos from the active views of four runs, including 44 recorded errors and remaining pending Mythos cells. It is excluded from new default suites; explicit opt-in remains possible after account/native support verification. The default example matrix is now 324 attempts.
- All four dashboard APIs verify original records and serve the requested reset/exclusion views. Chrome's combined dashboard visibly retains the successful Fable point, and its model menu contains Fable/Opus/Sonnet with no Mythos.
- `doctor --check-model-access` makes authenticated model-list requests, not inference probes. No new live listing request was made from the restricted agent host. The evaluation skill requires checking listings before final approval, resolving unknown IDs, locating the actual upgraded binary, and asking the customer to run blocked checks in their permitted terminal.

## 0.8.4 model median focus — 2026-09-10

- All 64 tests pass. The median test exercises odd/even groups, zero preservation, missing paired measurements, provider/model separation, selected-task coverage, and unchanged inputs. JavaScript syntax, CLI self-check, export, and extracted standalone self-check pass; the package includes the new median helper.
- Chrome verification on the conversation dashboard shows seven median diamonds, a working top-right Median focus switch, task-point opacity of 0.16 when enabled and 1 when disabled, and median opacity of 1. The Fable tooltip reports sample size, task count, efforts, median cost, and median latency.
- Filtering out hard tasks changed the Fable sample from 15 to 11 plotted averages. After restoring all tasks, switching both axes to log kept the same median cost ($0.2619) and latency (63.2 seconds). Full-page visual review passed; all four live servers serve the new median asset.
- Medians summarize selected displayed averages with equal weight per point, pooling effort levels and runs for the same model. They are descriptive, not raw-attempt medians or matched-task comparisons. The change does not alter evaluation scores or rerun provider calls.

## 0.8.5 median comparison arrows — 2026-09-10

- All 65 tests pass. Added coverage for focus-only pair selection, exact provider/model matching, absent models, no version substitution, directional endpoints, and coincident/nearby medians. JavaScript syntax checks, CLI self-check, plugin export, and extracted standalone entrypoint self-check pass.
- Chrome review on the conversation dashboard: no arrows outside focus; four arrows in focus with the seven measured models; removing Fable reduces the count to two; restoring it restores four. Both logarithmic axes preserve arrow connections. Median labels show model names only. Screenshot review passed with faded task points, clear median diamonds, and dotted arrowheads.
- All four dashboard servers (8879, 8881–8883) restarted and return the bundled pairing asset with JavaScript content type. No paid runs or historical evaluation data changed.
- Pairing provenance and descriptive-median limitations are documented in docs/MODEL_COMPARISONS.md and the exported plugin README. The test of the extracted archive uses its standalone bin/codex-eval entrypoint; this host's Python configuration excludes the current directory from implicit imports.

## 0.8.6 remove comparison arrows — 2026-09-10

- All 64 tests pass; JavaScript syntax, CLI self-check, export, and extracted standalone self-check pass.
- Chrome verification confirms zero comparison arrows in Median focus and seven remaining median diamonds with model-only labels. All four dashboard servers restarted with the updated UI. Removed the pairing asset, route, legend, arrow-only test, and associated feature documentation.

## 0.8.7 host-side evaluation progress — 2026-09-10

- All 68 tests pass. New progress tests cover mixed pass/fail/error outcomes, pending including active work, duplicate run paths, read-only behavior, missing/stopped runs, advancing checkpoint counts, and altered outcome rejection.
- CLI self-check, export, extracted standalone self-check/progress command, and the evaluation skill validator pass. The package retains exactly one evaluation skill with a progress reference; visualization remains optional host-side functionality.
- A read-only check against two saved Fable replacement runs reports 15/15 finished with 13 passes and two genuine failures, and 5/5 with five passes, respectively. No provider calls were made and no saved run was modified.
- Live sidebar updates are performed by the observing host agent via the installed visualize/live skills and apply_patch. This release provides the checkpoint command and workflow instructions; it does not add a background UI watcher or claim updates after the observing turn ends. Dashboard UI is unchanged from the browser-verified 0.8.6 release.

## 0.8.8 medians by model and reasoning effort — 2026-09-10

- All 69 tests pass. Median coverage now verifies distinct low/high/default/none groups, provider separation, zero preservation, paired measurements, and unchanged inputs. JavaScript syntax, CLI self-check, export, and extracted standalone self-check pass.
- Chrome verification shows separate model/effort median labels and a single effort in each tooltip. Zero and one selected task hide the median toggle/legend/points and remove focus fading; selecting a second task restores the control and medians. Restoring all tasks and both log axes works. The Fable low median tooltip reports three task/configuration averages and effort low.
- Dashboard assets update on refresh; saved results and evaluation inputs are unchanged.

## 0.8.9 customer flow and contribution requirements — 2026-09-10

- All 72 tests pass. The PR format validator accepts a completed description and rejects missing, placeholder-only, or duplicate sections; a CLI check also rejects the untouched template. CLI self-check, export, and extracted standalone self-check pass.
- The format workflow uses pull_request_target with read-only contents permission, explicitly checks out the trusted default branch, disables persisted credentials, and reads PR text from the event file. It does not check out or execute contributor branch code.
- GitHub ruleset 22741531 (Pull requests and owner review) was saved as Disabled pending publication of the new workflow/CODEOWNERS files and the owner's decision about their own PRs. It targets the default branch, requires one approval, code-owner review, dismissal of stale approvals, resolved conversations, and the PR format check sourced from GitHub Actions. Force pushes and deletions are restricted. These requirements are prepared, not yet enforced.
- Browser confirms the default branch is master. Repository README now explains the customer steps and required inputs. Publishing local changes remains user-operated; no push was performed.

## 0.9.0 task-quality reflection — 2026-09-10

- All 80 offline tests pass. Eight new cases cover per-task failure thresholds, infrastructure separation, missing costs, checkpoint races, evidence tampering, preserving user stops, safe pause requests, and locked/audited review clearing. Both CLI commands are available in the standalone export; self-check and skill validation pass.
- The source ZIP contains exactly one skill. The extracted plugin passes self-check without the parent repository. No provider calls are made by reflection; the host agent performs semantic diagnosis and any repairs need fresh validated, approved inputs.
- A live customer simulation exposed overly specific error-message checks and storage-fault assumptions. The new guidance requires independent valid alternatives and contract-mapped assertions, including filename/line-number formatting variants. This motivated the workflow but does not establish that every future grader will be correct. Existing live evidence is kept in ignored customer directories; active runs retain their pinned 0.8.9 engine.
- No dashboard assets changed. Browser inspection separately verified the dev-box dashboard on localhost port 8891 displays actual corrected-scope results and task summaries. The ongoing simulation is not a completed cross-provider comparison; Anthropic execution remains restricted in the agent session.
