# Customer starter prompt

Choose either route below. Both use the same [evaluation workflow](plugins/codex-eval-plugin/skills/evaluate/WORKFLOW.md), CLI, task catalog, and dashboard. The plugin provides convenient installation and `$evaluate` discovery; it is optional when using the repository directly.

## Install the plugin

With the Codex CLI installed, run:

```sh
codex plugin marketplace add ianho-oai/codex-eval-plugin --ref master
codex plugin add codex-eval-plugin@codex-eval
```

If `codex plugin --help` is unavailable, update your Codex CLI before continuing. The package is self-contained; a separate repository clone is unnecessary. Start a Codex task in your own project and paste:

```text
$evaluate

Help me compare Codex against Claude Code, GitHub Copilot, or both on representative tasks from my team's software workflows.

Read the evaluation workflow bundled with this installed plugin and follow it from discovery to results. Use that package's CLI, task references, and dashboard. Preserve any provider, task, effort, or budget choices I give you. If I haven't selected the comparison providers or discovery sources, help me choose them first. Obtain the approvals required by the workflow before accessing private sources or starting paid execution.

Ask me for the customer context you need to begin.
```

Select the plugin's **evaluate** skill if Codex asks you to resolve `$evaluate`. If it is not visible after installation, restart Codex and try again. Use the guide bundled with your installed version; do not substitute newer repository instructions into an already approved run.

## Use an existing repository checkout

No plugin installation is needed. Open this evaluation-kit checkout in Codex and paste:

```text
Help me run a customer evaluation comparing Codex with Claude Code, GitHub Copilot, or both.

Read plugins/codex-eval-plugin/skills/evaluate/WORKFLOW.md and follow that shared process. Use ./eval from this checkout for validation, execution, reports, and the bundled dashboard. Keep customer files under an ignored evaluations/ directory. Ask which customer workflows and sources to use; opening this evaluation-kit repo does not mean it is the customer repository to benchmark. Preserve my explicit choices and obtain the approvals required by the workflow.
```

Python 3.11+ and the task runtime are required. The workflow checks the native CLIs and credentials for selected providers; do not paste keys into chat. For expectations see the [product overview](OVERVIEW.md); for manual commands and setup problems see the [CLI reference](docs/CLI_REFERENCE.md) and [troubleshooting](docs/TROUBLESHOOTING.md).
