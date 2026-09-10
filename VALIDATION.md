# Validation guide

Use these checks before sharing a release. Keep run logs, screenshots, provider responses, and measured results in ignored `evaluations/` directories. This repository documents the validation procedure; it does not publish comparative model results.

## Offline release checks

```sh
python3 -m unittest discover -s tests -v
./eval self-check
./eval export --output dist
```

The tests cover deterministic grading, synthetic baseline/known-good solutions, native protocol emulators, telemetry, sealed-input integrity, scheduling, and reporting. Protocol emulators do not establish live provider access or model performance.

Extract the exported ZIP into a fresh directory and run its `bin/codex-eval self-check` without the parent repository. Check that the archive contains exactly one skill and only intended plugin files. For dashboard changes, use synthetic fixtures to review filters, axes, labels, missing metrics, keyboard interactions, and browser errors.

## Live provider checks

Check the exact executable, version pin, credentials, and selected model IDs before approving execution:

```sh
./eval doctor SUITE --check-model-access
```

Model listings establish visibility, not inference or effort support. An approved smoke run can check one native configuration in an environment permitted to reach the provider. For example, with credentials configured securely:

```sh
./eval smoke --provider claude --output evaluations/claude-smoke
./eval dashboard evaluations/claude-smoke/run
```

Use a fresh output directory for each check and `--model` for a specific model. Preserve native responses, grader outcomes, usage, and missing telemetry locally. A smoke test is not a controlled cross-model comparison. See [provider troubleshooting](docs/TROUBLESHOOTING.md) for compatibility failures and recovery.

## Evidence boundaries

- Record offline, browser, live-provider, and Docker coverage separately; leave unavailable checks explicit.
- Confirm results through the independent grader and saved artifacts. Agent claims, account listings, or a running checkpoint do not prove successful completion.
- Local execution does not enforce host isolation or held-out-test secrecy. Docker execution needs separate validation with pinned images.
- Changed tasks, CLI pins, settings, or pricing require new validation and approval. Preserve earlier suites, results, and costs.
