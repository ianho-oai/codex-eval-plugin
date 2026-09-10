# Customer starter prompt

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

The evaluation needs Python 3.11+, the native Codex and Claude Code CLIs, and provider API keys. The plugin will help you check the task-specific toolchain and execution environment before paid runs; do not paste API keys into chat.

```text
$evaluate

I want to run evaluation tests comparing Codex against Claude Code on tasks that represent my team's actual software development workflows. Use the Codex Eval plugin to guide me from discovery through to a local results dashboard.

Start by asking which discovery methods I want to combine:
1. Describe my workflows in conversation.
2. Review selected local Codex or Claude Code sessions, usually from the last 30 days.
3. Review repositories and selected GitHub pull requests or GitLab merge requests.

Ask concise follow-up questions. Get my permission for specific history or repository sources before reading them. Let me say “build the proposal now” whenever I want to end discovery.

For each workflow, propose easy, medium, and hard tasks. Include a short, human-readable workflow description, objective pass/fail checks, and relevant inspiration from the plugin's benchmark catalog with original source links. Create original tasks when no suitable example fits. Ask me to approve the task proposal.

Build and validate the approved tasks. Help me choose available models, confirm the execution environment and spend threshold, and configure API keys securely without pasting them into chat. Get my approval of the final execution plan before making paid calls.

Use three repeats per task/model and five concurrent attempts in total, refilling each free slot immediately. Share the slot limit across batches. Explain how concurrency affects latency and how in-flight calls can exceed a spend threshold.

After approval, use the bundled CLI to execute and grade the tasks headlessly, then open the prebuilt local dashboard with both providers combined. Show mean cost, latency, and token usage, while retaining individual attempts, pass counts, failures, and missing metrics. Keep my data and credentials out of Git.

Continue through to results without unnecessary check-ins. If something is blocked, tell me exactly what is needed and provide any command I must run myself.

Begin with the discovery choices.
```
