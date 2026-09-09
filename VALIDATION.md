# Validation coverage

As of 2026-09-09. This is a functional first release; no comparative model-performance claim is made.

| Surface | Evidence |
| --- | --- |
| Core CLI | 25 focused offline tests pass in approximately 7 seconds |
| Example graders | All three baselines fail; all three known-good solutions pass; behavioral shortcut mutants fail |
| Native adapters | Both adapters exercise subprocess execution, workspace reset, external grading, telemetry normalization, result integrity, and resume using offline protocol emulators |
| Real Codex | GPT-5.6 Luna and GPT-5.6 Sol each completed the original slug-normalization task through Codex CLI 0.153.4, using API-key billing, and passed the independent grader; Sol used the one-command smoke workflow |
| Real Claude Code | Not run: no Anthropic key was found in the development process or project environment files; host policy blocks the Anthropic API endpoint |
| Dark dashboard | Browser inspection verified rendering, task selection, axis changes, failure labels, synthetic-data warning, and missing metrics |
| Export and installation | ZIP bytes and checksum reproduce; the extracted plugin runs independently; Codex successfully installed the plugin from the repository marketplace into a temporary validation profile |
| Docker execution | Implemented with an immutable image requirement and separate agent/grader containers; live Docker execution has not been validated on the restricted development host |

The real Codex smoke test took 56.79 seconds end to end and reported 137,284 input / 3,337 output tokens. Standard-rate estimated cost was $0.00993. Native sandbox helper errors occurred before the task was completed through other available native tools; this measures development-host validation, not representative latency or cost. Raw artifacts remain local and ignored.

The subsequent GPT-5.6 Sol one-command smoke test also passed: 97.75 seconds, 132,391 input / 2,720 output tokens, and $0.16307 standard-rate estimated cost. These two small validation runs used separate sealed suites and do not constitute a controlled model comparison.

An earlier attempt was interrupted while the CLI could not use the host-managed network proxy. The environment allowlist was fixed to preserve managed proxy and certificate settings. No alternate endpoint or auth fallback was introduced.

## Run Claude validation

In a permitted terminal with Claude Code and `ANTHROPIC_API_KEY` already configured:

```sh
./eval smoke --provider claude --output evaluations/claude-smoke
./eval dashboard evaluations/claude-smoke/run
```

The command checks the installed version and capabilities, runs one original trusted-local task, and writes measured results to `evaluations/claude-smoke/run`. Pass `--model` to test a specific account-visible model. Keep secrets out of chat and Git. Share only sanitized results if further debugging is needed.
