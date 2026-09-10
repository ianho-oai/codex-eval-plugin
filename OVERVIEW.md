# Product walkthrough

**Begin with the [customer starter prompt](CUSTOMER_STARTER_PROMPT.md).** It contains installation instructions and the prompt to paste into a new Codex task. The workflow happens in Codex chat; the dashboard is for results.

## Customer experience and implementation

| Stage | Customer experience | Underlying functionality |
| --- | --- | --- |
| Start | Follow the starter prompt to install from this repository and invoke `$evaluate`. | One exportable plugin bundles one skill, the CLI, task references, schemas, and dashboard. No repository clone is required for customer installation. |
| Discover | Combine a conversation, selected local sessions from the last 90 days, or selected repositories/PRs/MRs. Ask to build the proposal whenever ready. | The agent asks follow-ups; CLI helpers extract consented evidence into ignored customer files. The CLI does not independently infer workflows. |
| Approve tasks | Review easy/medium/hard coverage per workflow, plain-language summaries, acceptance checks, and source links. | The skill adapts examples from the local benchmark catalog or explains an original design. Tasks are freshly authored, not official benchmark reproductions. |
| Prepare | Review self-contained tasks using available lightweight test runners. | Each task has instructions, baseline files, allowed changes, a separate grader, and a known-good solution. Validation checks that baseline fails and solution passes. Environment preparation precedes timed execution. |
| Approve execution | Review exact model/effort combinations, repeats, versions, pricing, and any limits. Configure keys securely. | A sealed approval binds tasks, settings, pricing, and engine inputs. Doctor checks local prerequisites and known model minimum CLI versions; model access still requires live verification. Changed inputs require renewed validation and approval. |
| Run | Let the CLI complete the approved matrix and report actionable blockers. | A five-worker queue refills immediately. Each attempt gets a fresh workspace, native Codex or Claude Code execution, separate grading, and saved evidence. Explicit rate limits receive bounded retries. |
| Compare | Explore cost, latency, and tokens for both providers in one dashboard, or scope a dashboard to each workflow. | The dashboard reads saved artifacts and refreshes every 15 seconds. Each point averages repeats within the same run/task/model/effort. Raw attempts remain available. |

## Current defaults

- All cataloged GPT-5.6 models and GPT-6 Astra, plus Claude Fable/Opus/Sonnet/Haiku/Mythos, at every supported single-agent effort level.
- Three repeats; one repeat is available for quick sweeps.
- Five concurrent attempts, with a shared pool available across batches.
- No spend stop. Optional thresholds stop new dispatch; active calls can overshoot them.
- Local execution, bundled fixtures, and existing simple frameworks. Docker is an explicitly requested advanced option. Native-app workflows test representative logic without requiring GUI automation or platform simulators.

The objective is achievable tasks with verified correctness, followed by comparison of time, cost, and tokens. Genuine failures are retained; graders are not weakened to force success.

## What is deterministic

Task snapshots, settings, seeded schedule, orchestration code, and behavioral checks are fixed. Concurrent completion order, model outputs, cache behavior, and observed timing can vary. Codex and Claude Code have different native harnesses, prompts, and tokenizers, so this compares product/model configurations.

Completion requires successful provider execution, allowed changes, and a passing separate grader. Agent assertions alone never count. Infrastructure errors are distinguished from scorable task failures; missing metrics remain null. Claude cost comes from native telemetry; OpenAI cost is estimated from frozen rates and available usage, with uncertainty retained.

Local mode runs trusted fixtures on the customer's host. It does not enforce grader secrecy or host isolation. Difficulty should come from software behavior and interacting modules, with setup already prepared.

## Dashboard

The chart comes first, with provider/model and difficulty/task checkbox groups, select-all controls, toggleable model labels, and independent logarithmic axes. Hover details show model/effort, task, difficulty, pass count, cost, and end-to-end latency. The task table uses short workflow descriptions.

Codex is blue and Claude orange when at least one repeat passes; groups with no successful repeat are grey. A point averages only its own run/task/model/effort group, including failed attempts. Missing metrics and pending attempts remain explicit. Combining separate runs does not establish that their settings are comparable.

## Files and ownership

| Location | Purpose |
| --- | --- |
| [Customer starter prompt](CUSTOMER_STARTER_PROMPT.md) | Customer entry point and kickoff instructions |
| `plugins/codex-eval-plugin/` | Complete standalone plugin |
| `evaluations/<customer>/` | Ignored discovery, tasks, suites, receipts, and run evidence |
| `.env.local` | Ignored provider keys; exported values take precedence |
| `tests/` | Offline tests and native-protocol emulators |
| `dist/` | Standalone versioned ZIPs and checksums |

## Validation and limitations

See [VALIDATION.md](VALIDATION.md) for dated test results and live-provider evidence. Passing offline tests does not establish model availability. Fable/Mythos simulation attempts have exposed CLI compatibility and model-access errors; [troubleshooting](docs/TROUBLESHOOTING.md) explains the findings and recovery. Do not interpret these as failures to implement the software task.

Use the [CLI reference](docs/CLI_REFERENCE.md) for manual operation, selectors, retries, and dashboard commands. Use the [starter prompt](CUSTOMER_STARTER_PROMPT.md) to begin a customer evaluation.
