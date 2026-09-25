# Codex Eval Plugin

Build a customer-owned headless evaluation kit comparing Codex with Claude Code and optional GitHub Copilot. The exportable plugin is `plugins/codex-eval-plugin/` and contains exactly one skill.

For an explicitly requested customer evaluation, read the shared [evaluation workflow](plugins/codex-eval-plugin/skills/evaluate/WORKFLOW.md) and use `./eval`, which invokes the same CLI distributed by the plugin. Plugin installation is optional when working from this repository. General coding or plugin maintenance does not start an evaluation. Maintain the process in that guide; keep entrypoints and installation instructions as links and short summaries.

- Keep customer sessions, repositories, credentials, raw runs, and results in ignored evaluation directories. Publish only original code, synthetic fixtures, and public-source references.
- Success is a deterministic verifier result, never the agent's claim. Keep failures and missing telemetry visible.
- Freeze tasks, model settings, CLI versions, pricing, and run order before execution. Changed inputs require new approval.
- Run `python3 -m unittest discover -s tests -v`, `./eval self-check`, and `./eval export --output dist` before release. Validate the dashboard in a browser after UI changes.
- Review [project context](guidelines/project-context.md) and [guide index](guidelines/README.md) for design and release conventions.
