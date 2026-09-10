# Codex Eval · 0.3.0

One skill for workflow discovery, task design, and approved headless Codex versus Claude Code evaluation. The CLI and dark local dashboard are bundled and run without third-party Python packages.

## Install in Codex

```sh
codex plugin marketplace add ianho-oai/codex-eval-plugin
codex plugin add codex-eval-plugin@codex-eval
```

Invoke the **evaluate** skill and choose interview, approved local session history, selected repositories, or a combination. API keys are needed only for live runs; never paste them in chat.

## Run the bundled CLI

```sh
python3 bin/codex-eval self-check
python3 bin/codex-eval demo --output ./demo
python3 bin/codex-eval dashboard ./demo
```

Python 3.11+ on macOS/Linux is required; sample graders also use Node.js 18+. Customer comparisons default to a pinned Docker image. See [task design](ceval/data/task-design.md), [methodology](ceval/data/methodology.md), and the [full repository guide](https://github.com/ianho-oai/codex-eval-plugin).

After setting a provider key securely in the invoking terminal, run one original trusted-local fixture:

```sh
python3 bin/codex-eval smoke --provider claude --output ./claude-smoke
python3 bin/codex-eval dashboard ./claude-smoke/run
```

Use `--provider codex` for an OpenAI smoke test. API keys are loaded from `.env.local` in the current directory; exported environment variables take precedence. Only `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are loaded, with no shell execution or variable expansion. `--binary PATH` pins a native executable when your normal command is an updater/launcher. Native product versions and model IDs must support the documented flags. Host API restrictions still apply. No Claude live result is implied by passing offline adapter tests.

Use `python3 bin/codex-eval dashboard` to show every live run under `evaluations/`, with automatic refresh every 15 seconds. Pass a different workspace directory if needed. A live run inside `evaluations/` also opens the entire workspace. Synthetic demos remain separate unless opened explicitly. The dashboard verifies original artifacts and retains failures, pending counts, and source provenance; separate smoke tests do not establish a controlled benchmark.

## Find representative tasks

```sh
python3 bin/codex-eval examples --query "frontend editor focus" --limit 5
python3 bin/codex-eval portfolio evaluations/customer/discovery.json --suite evaluations/customer/suite.json --output evaluations/customer/portfolio.json
```

The [offline catalog](ceval/data/catalog.md) bundles 1,658 public task references and 46 detailed design examples. New customer suites require easy/medium/hard tasks per discovered workflow, with original source links and adaptation notes or an explicit original-design rationale.

Keep one suite per directory: `validation.json` and `approval.json` belong to that directory. For separately approved provider suites, use separate directories with identical task snapshots; do not put two suite JSON files beside the same approval receipt.

The `evaluate` skill is explicit-only (`allow_implicit_invocation: false`). Invoke `$evaluate` when asking to run evaluation tests comparing Codex against another coding agent. Ordinary coding, unit tests, general benchmarks, and plugin maintenance do not trigger it. The current execution adapters support Codex and Claude Code.

## Concurrent execution

`./eval run SUITE --output RUN_DIR --workers 5` keeps up to five attempts active and starts the next queued attempt as soon as a slot opens. The default is five; use `--workers 1` for sequential timing. Add `--resume` for an existing identical sealed run. Completed attempts are verified and skipped.

To cap multiple batches at five attempts **in total**, give each the same `--workers 5 --slot-pool evaluations/shared-workers` arguments. Each attempt has an isolated workspace; only the coordinator writes shared results. Pool leases release automatically if a process exits.

Agree on concurrency before running. Concurrent work can contend for CPU and network, so latency may differ from sequential measurements. The worker count and scheduler hash are recorded in run metadata. Unknown spend or a spend threshold stops dispatch; already-active calls finish and are saved. A threshold may overshoot by the cost of all in-flight calls.

For a graceful pause, create `RUN_DIR/stop-requested.json` (for example, containing `{}`). The runner drains active attempts; remove that file before resuming.
