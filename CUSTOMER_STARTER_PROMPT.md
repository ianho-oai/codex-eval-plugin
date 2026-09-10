# Customer starter prompt

With **Codex Eval** installed, open your project in Codex and paste the prompt below. Select the plugin's **evaluate** skill if Codex asks you to resolve `$evaluate`.

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
