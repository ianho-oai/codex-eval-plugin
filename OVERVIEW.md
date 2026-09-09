# Product walkthrough

Current local version: 0.1.1. This is a functional first version with real provider smoke tests; a full customer evaluation has not yet been validated end to end.

## The customer experience

| Step | Customer experience | Underlying functionality |
| --- | --- | --- |
| Install | Install the plugin in Codex and invoke its one `evaluate` skill. | The plugin bundles instructions, a Python CLI, public methodology references, schemas, starter tasks, and a fixed dashboard. |
| Discover | Choose an interview, selected local Codex/Claude history, selected repositories/PRs/MRs, or any combination. Stop the interview and request a proposal whenever ready. | The coding agent conducts discovery. CLI helpers extract opted-in user messages and selected Git/GitHub/GitLab evidence; choices and consent are saved in `discovery.json`. |
| Approve the portfolio | Review a table of workflows, task ideas, easy/medium/hard difficulty, acceptance checks, and benchmark inspiration. | The agent draws on original summaries of DeepSWE, SWE-bench, Terminal-Bench/Harbor, and Aider Polyglot. It designs original tasks; this is not a redistributed official benchmark dataset. |
| Build the evaluation | The agent writes tasks and concrete verifiers, then presents the runnable plan. | Each task contains an instruction, starting files, allowed-change rules, a grader, and a known-good solution. Validation requires the starting implementation to fail and the known-good solution to pass. |
| Configure and approve | Supply API keys securely, select models/efforts/repeats, and approve the execution environment and spend threshold. | Keys come from the environment or ignored `.env.local`. `suite.json` specifies the matrix and limits. An approval receipt hashes tasks, settings, pricing, and referenced content so later changes invalidate approval. |
| Run unattended | After final approval, the agent launches the fixed CLI and reports blockers when required. | The runner executes each task × model × effort × repeat in seeded order, creates a fresh workspace, calls native `codex exec` or Claude Code headlessly, collects events, grades the result, and checkpoints progress. It supports resume of the same sealed suite. |
| Inspect results | Open one local dashboard for the evaluation workspace. Select tasks/providers/outcomes and chart axes, inspect individual attempts, or export CSV. | The server discovers saved live runs, verifies original result artifacts, aggregates measurements, and refreshes every 15 seconds. Codex points are white; Claude points are orange. Demos remain separate. |

The experience starts in Codex chat. There is no separate discovery web wizard. The coding agent authors customer tasks; the CLI does not independently infer workflows or generate tasks. After approval, execution and reporting use fixed code.

## What runs underneath

```text
One skill: discovery → proposal → task authoring → customer approval
                                      ↓
                         Frozen suite and task files
                                      ↓
                     Deterministic Python CLI runner
                       ↙                       ↘
              Native Codex CLI          Native Claude Code
                       ↘                       ↙
                        Independent task verifiers
                                      ↓
                Structured results → shared dashboard / CSV
```

- **Success:** binary 1/0 from provider completion, allowed-change checks, and an external deterministic grader. An agent saying “done” is insufficient.
- **Timing:** end-to-end, agent, and grader duration.
- **Usage:** input, output, cache read/write, reasoning, turns, and tool calls where the native product reports them. Missing fields remain unavailable.
- **Cost:** Claude Code's native reported total; OpenAI estimates from the bundled dated rate card. Estimates are not invoices.
- **Failures:** retained in results and cost calculations; infrastructure-invalid results are distinguished from scorable task failures. Unattempted cells remain pending.
- **Determinism:** fixed inputs, orchestration, scheduling, and grading. Model responses, native harness behavior, and provider caches are not deterministic or identical across providers.
- **Environment:** default execution uses a pinned Docker image with separate agent/grader containers. Trusted-local mode supports development smoke tests without promising isolation.
- **Budget:** a stop threshold checked between calls, not a hard billing cap; one call can overshoot it. Unknown cost stops subsequent spending.

## Files and ownership

| Location | Purpose |
| --- | --- |
| `plugins/codex-eval-plugin/` | Exportable plugin, exactly one skill, native adapters, reference catalogs, and dashboard |
| `evaluations/<customer>/` | Ignored customer discovery, suites, tasks, and approval receipts |
| `evaluations/<run>/` | Ignored run schedules, per-attempt artifacts, results, and reports |
| `.env.local` | Ignored API keys; exported environment values take precedence |
| `tests/` | Fast offline tests using original fixtures and emulated native CLI protocols |
| `dist/` | Versioned standalone plugin ZIP and checksum |

## Verified today

- 30 offline tests, CLI self-check, and standalone export pass.
- Luna and Sol each passed a real native Codex smoke test.
- A user-run Claude Sonnet 5 smoke test passed; saved artifacts and the external grader result were inspected locally.
- The dashboard shows all three results together; provider filtering and axis changes were verified in a browser.
- Older interrupted runs remain visible through pending counts rather than disappearing.
- Initial repository publication is verified. Later local changes need the user's next push.

## Still unvalidated or intentionally limited

- A fresh customer's entire install → discovery → task creation → approved matrix journey has not been exercised end to end.
- Only three provider/model smoke configurations have real execution evidence. The full catalog and default 72-call sample matrix have not been run.
- Live Docker isolation has not been validated on this restricted development host.
- The bundled examples are small original fixtures, not yet a portfolio representative of a real customer's repositories.
- Model and pricing catalogs are dated snapshots. Account model discovery is available, but new model IDs and prices require explicit review; they are not silently added to an approved evaluation.
- Combining runs is a convenience for exploration. Different suites may use different tasks, environments, and settings, so combined display alone does not prove a fair benchmark.

Start the combined dashboard from the project directory with `./eval dashboard`. See `README.md` for installation and the full CLI sequence, and `VALIDATION.md` for measured smoke-test results.
