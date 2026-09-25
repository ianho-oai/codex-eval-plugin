# Customer starter prompt

**This is the entry point for a customer evaluation.** Follow the installation step, then copy the kickoff prompt into Codex. No separate clone or manual CLI workflow is required. For background, see the [walkthrough](OVERVIEW.md); for setup errors, see [troubleshooting](docs/TROUBLESHOOTING.md).

## 1. Install the plugin from GitHub

The [repository](https://github.com/ianho-oai/codex-eval-plugin) includes the complete plugin in [`plugins/codex-eval-plugin/`](https://github.com/ianho-oai/codex-eval-plugin/tree/master/plugins/codex-eval-plugin): its skill, evaluation CLI, benchmark catalog, and local dashboard.

Run these commands in your terminal with the Codex CLI installed:

```sh
codex plugin marketplace add ianho-oai/codex-eval-plugin --ref master
codex plugin add codex-eval-plugin@codex-eval
```

The first command adds this GitHub repository as a plugin source; the second installs **Codex Eval** from it. You do not need to clone the repository separately. If `codex plugin --help` is unavailable, update your Codex CLI before continuing.

You can also ask Codex to perform that setup by pasting:

```text
Install the Codex Eval plugin from https://github.com/ianho-oai/codex-eval-plugin using:
codex plugin marketplace add ianho-oai/codex-eval-plugin --ref master
codex plugin add codex-eval-plugin@codex-eval
Confirm whether installation succeeded. Do not start paid evaluations yet.
```

## 2. Start your evaluation

After installation, open your own project in a new Codex task and paste the prompt below. Select the plugin's **evaluate** skill if Codex asks you to resolve `$evaluate`. If it is not visible, restart Codex and try again.

The evaluation needs Python 3.11+, the native CLIs for your selected providers, and their credentials. Choose Claude Code, GitHub Copilot, or both to compare with Codex. Copilot uses its own login or fine-grained GitHub token; see the [guided Copilot setup](plugins/codex-eval-plugin/skills/evaluate/references/copilot.md). The plugin will help you check the task-specific toolchain and execution environment before paid runs; do not paste API keys into chat.

```text
$evaluate

I want to run evaluation tests comparing Codex against Claude Code and/or GitHub Copilot on tasks that represent my team's actual software development workflows. Use the Codex Eval plugin to guide me from discovery through to a local results dashboard.

Reference https://github.com/ianho-oai/codex-eval-plugin for setup, usage, and troubleshooting guidance. The plugin lives in plugins/codex-eval-plugin/ within that repository. Follow the installed plugin's evaluate skill and use its bundled CLI, benchmark catalog, and dashboard rather than rebuilding the evaluation system. If the repository documentation differs from my installed version, resolve that before preparing the evaluation.

First let me choose Codex + Claude Code, Codex + GitHub Copilot, or all three. If I already chose, preserve that choice. Use repeated configure --provider flags for exactly those harnesses, or exact --model selections; bare --all-models resets to Codex + Claude. For Copilot, guide me through the installed CLI/version, personal versus organization access, explicit account selection or Copilot Requests token in ignored .env.local, and a small approved smoke for each uncertain model/effort. Do not assume gh auth login selects the Copilot account. Disclose no credit cap by default and keep GitHub usage valuation separate from additional invoice charges. Configure credentials only for selected providers.

Then ask which discovery methods I want to combine:
1. Describe my workflows in conversation.
2. Review selected local Codex or Claude Code sessions, usually from the last three months (90 days).
3. Review repositories and selected GitHub pull requests or GitLab merge requests.

Ask concise follow-up questions. Get my permission for specific history or repository sources before reading them. Let me say “build the proposal now” whenever I want to end discovery.

For each workflow, use just two tiers: Basic (the former easy/medium/hard range) and Hard (the former harder-1/harder-2 style). Propose three Basic and five distinct Hard tasks by default. Focus the Hard tasks on substantive repository investigation/repair, feature integration, and state/recovery/compatibility, adapted to my actual work. Require tracing interacting modules and preserving related behaviors, not just searching more files or adding edge cases or infrastructure. Use DeepSWE and other relevant public task references for engineering inspiration, without claiming equivalent difficulty or official benchmark results. Retain the repo's offline reference collection and inspect relevant source tasks. Add tasks when distinct behaviors need coverage and preserve any narrower scope I explicitly request. Show task counts before approval. Make tasks feasible with clear requirements and enough context, but do not make them easier to target high pass rates. Compare verified correctness, time, tokens, and cost, keeping genuine failures visible. Prepare the environment before timed execution. Include a short, human-readable workflow description, objective pass/fail checks, and relevant inspiration from the plugin's benchmark catalog with original source links. Create original tasks when no suitable example fits, especially for repository reasoning; explain their original design instead of forcing a benchmark citation. Do not select tasks to favor a provider. Before approval, show the generated discovery coverage receipt: sources and dates actually inspected, sample/export limitations, exclusions, inferred workflows, and what I have confirmed. Do not call selected historical examples a complete three-month review. Ask me to approve the task proposal.

Keep every task self-contained and runnable on my consumer device using an existing simple test runner such as unittest, pytest, or Node tests. Use bundled fixtures and in-process fakes. Do not introduce Docker, Xcode builds, iOS simulators, SwiftUI/UIKit UI tests, macOS app integrations, browser downloads, or external services, and do not ask me to choose between those setups. For iOS workflows, test representative application logic with an available runtime and explain any adaptation. Make harder tasks involve richer behavior and multiple modules, while keeping the setup simple. Validate the grader locally before paid runs.

Build and validate the approved tasks. For the providers I selected, default to cataloged GPT-5.6 models and GPT-6 Astra in Codex, and (only if selected) cataloged default Claude models, including Fable 5.1, Opus 5, Sonnet 5, and Haiku 4.5. Exclude Mythos unless I explicitly request it after access verification. Include every supported single-agent effort level; Fable uses low, medium, high, xhigh, and max. Use no spend stop and no agent or grader timeout for all selected providers, unless I specify otherwise. At preflight, show me the exact matrix, repeat count, and timeout, tell me these defaults, and ask me to specify otherwise if I want different models, efforts, or a spend limit. Keep unavailable models visible. Confirm the execution environment, and configure API keys securely without pasting them into chat. Check the installed CLI against each model's known minimum version; Fable 5.1 requires Claude Code 2.1.251 or newer. Run the bundled doctor with --check-model-access against my selected providers using the execution credentials, and compare exact model IDs with account-visible models for Codex/Claude; use the documented Copilot model-picker and smoke path because its doctor cannot list account models before final approval. If a CLI is outdated, ask me to upgrade, then locate and pin the upgraded executable; an upgrade may affect a different installation. If the host blocks the listing, give me the exact command to run and inspect its output. Confirm uncertain native support with a small approved task before a broad sweep. Get my approval of the final execution plan before making paid calls.

Include all supported reasoning/effort levels for each selected model and show that full matrix in the plan. Run one iteration per task/model/effort first, with five concurrent attempts in total, refilling each free slot immediately. Complete the entire approved first-round matrix before offering repeats; do not repeat early-finishing configurations while other first runs remain queued. Reconcile any blocked or missing combinations explicitly. After presenting first-round results, actual known spend and missing-cost caveats, ask whether I want exactly two additional rounds of the same configurations, bringing the total to three, for consistency and averaging. Show their exact scope and estimated additional cost, and wait for approval before running them. After the approved two-attempt follow-up, report the mean and median from all three raw observations per task/provider/model/effort, with passed/3 shown separately; preserve the original first-round evidence and do not average two run summaries. Do not launch three rounds upfront or automatically add repeats. Share the slot limit across batches. Explain how concurrency affects latency and how in-flight calls can exceed a spend threshold.

After approval, use the bundled CLI to execute and grade the tasks headlessly. Its automatic readiness gate runs a bounded edit-and-test probe using the first configured model/effort for each provider in the actual launch environment before dispatching the matrix. Include these probes and their separately reported costs in the approved plan. If one fails, inspect the receipts and correct the launch context without weakening sandbox settings. Use bounded automatic retries for explicit native rate-limit/capacity failures with a shared provider cooldown; preserve all trial costs and stop on exhaustion. Exclude explicit rate-limit error attempts from comparison results for every provider; after recovery compare the measured non-rate-limited attempt. Keep all raw trials and costs for accounting, report rate-limit-only combinations as unmeasured, and retain genuine coding failures. Do not retry genuine coding failures. While tests run, use the available visualize skill and its live companion to show progress inside Codex: completed/remaining attempts, active workers, and pass/fail/error counts from the bundled progress command. Keep one view updated from real checkpoints; fall back to text progress if unavailable, without installing extra dependencies or changing the tested agents. Then open the prebuilt local dashboard with all selected providers combined. Show mean cost, latency, and token usage, while retaining individual attempts, pass counts, failures, and missing metrics. Keep my data and credentials out of Git.

Own an ongoing design, challenge, observe, diagnose, and repair loop. Before paid runs, map grader checks to visible requirements; ask which correct solutions could be rejected and which wrong ones could pass. Test an independent valid alternative, the oracle, baseline, and a few targeted broken candidates based on those assumptions, without trying to enumerate every possible edge case. Agree the permitted repair scope with me in the final plan. After launch, keep observing progress and reflect: investigate any infrastructure error, at least 50% failures after three scorable attempts for a task, and unfamiliar anomalies even below those thresholds. Diagnose setup, task, grader, or candidate defects from local evidence. For a defective test, pause affected work, preserve original results and costs, validate a corrected sealed revision, and rerun every affected configuration fairly. Apply repairs covered by my explicit authorization and obtain approval for uncovered changes. Keep genuine coding failures; do not weaken sound checks or retry until success. Limit corrective revisions to two per task, review final failures, and continue through the expected result count or clearly report what prevents completion.

Continue through to results without unnecessary check-ins. If something is blocked, tell me exactly what is needed and provide any command I must run myself.

Begin with the discovery choices.
```
