# Codex Eval Plugin

Build a customer-owned Codex versus Claude Code headless evaluation kit. The exportable plugin is `plugins/codex-eval-plugin/` and contains exactly one skill.

- Keep customer sessions, repositories, credentials, raw runs, and results in ignored evaluation directories. Publish only original code, synthetic fixtures, and public-source references.
- Success is a deterministic verifier result, never the agent's claim. Keep failures and missing telemetry visible.
- Freeze tasks, model settings, CLI versions, pricing, and run order before execution. Changed inputs require new approval.
- Run `python3 -m unittest discover -s tests -v`, `./eval self-check`, and `./eval export --output dist` before release. Validate the dashboard in a browser after UI changes.
- Review [project context](guidelines/project-context.md) and [guide index](guidelines/README.md) for design and release conventions.
