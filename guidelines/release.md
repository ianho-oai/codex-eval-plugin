# Release

**When to read:** Publishing or exporting the plugin.
**When to update:** Distribution, licensing, or versioning changes.

The repository and plugin version together, starting at 0.1.0. Update `ceval.__version__`, plugin manifest, package metadata, and CHANGELOG together. Export uses stable ZIP timestamps and a file allowlist. Customer data and generated results never enter the plugin. `./eval export` writes a ZIP and SHA-256 checksum. Verify an extracted ZIP works without the parent repository.

Run tests, self-check, synthetic oracle/baseline validation, and dashboard review. Record live provider coverage separately. Commit coherent reviewed changes and tag releases only when authorized. Public source repository: https://github.com/ianho-oai/codex-eval-plugin.

Ian's workflow for this project: continue making coherent local commits and synchronized version bumps as features/fixes are completed. Give a concise push reminder with `git push origin master` at release checkpoints; Ian performs pushes. Keep evaluation engines frozen while paid runs are active. If the product advances before a prepared comparison lane runs, preserve the exact approved engine for that lane rather than changing its inputs silently.
