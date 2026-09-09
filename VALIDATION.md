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
