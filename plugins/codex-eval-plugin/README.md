# Codex Eval · 0.1.0

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
