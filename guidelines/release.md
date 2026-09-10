# Release

**When to read:** Publishing or exporting the plugin.
**When to update:** Distribution, licensing, or versioning changes.

The repository and plugin version together, starting at 0.1.0. Update `ceval.__version__`, plugin manifest, package metadata, and CHANGELOG together. Export uses stable ZIP timestamps and a file allowlist. Customer data and generated results never enter the plugin. `./eval export` writes a ZIP and SHA-256 checksum. Verify an extracted ZIP works without the parent repository.

Run tests, self-check, synthetic oracle/baseline validation, and dashboard review. Record live provider coverage separately. Commit coherent reviewed changes and tag releases only when authorized. Public source repository: https://github.com/ianho-oai/codex-eval-plugin.

Keep evaluation engines frozen while approved runs are active or pending. If the product advances, preserve the exact approved engine for each lane; changed inputs require new validation and approval. Keep release evidence in ignored evaluation directories. Follow the repository contribution process and obtain explicit authorization before commits, pushes, or tags.
