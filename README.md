# Codex Eval Plugin

Customer-owned, end-to-end headless evaluations of **Codex** and **Claude Code**.

One Codex skill discovers the customer's workflows and designs representative tasks. A dependency-free Python CLI takes over after approval: freeze → run → grade → collect metrics → display a prebuilt local dashboard.

## Start here

```sh
./eval self-check
./eval demo --output evaluations/demo
./eval dashboard evaluations/demo
```

Open **http://127.0.0.1:8765**. The dark dashboard has task/provider/difficulty/outcome filters, configurable scatter-plot axes, point details, every attempt, and CSV export. Demo points are explicitly synthetic.

Python 3.11+ is required. The three original example graders also use Node.js 18+. The orchestration and dashboard have no Python/npm runtime dependencies.

## Customer workflow

1. Invoke the plugin's **evaluate** skill. Combine an interview, explicitly selected local session history, and selected GitHub/GitLab repository/PR/MR evidence. Stop discovery whenever there is enough to propose tasks.
2. Review the proposed use cases and easy/medium/hard tasks. Approve the portfolio.
3. The skill builds frozen task snapshots, behavioral graders, and known-good solutions. Review the concrete matrix, limits, environment, and pricing; approve once.
4. Run the deterministic CLI. View results in the fixed dashboard; no per-customer frontend or orchestration generation.

### Run a real evaluation

```sh
./eval init evaluations/customer
# Complete discovery and replace example tasks with approved customer tasks.
# Build a toolchain image once, including each task's test/build dependencies:
docker build -t codex-eval:0.1.0 plugins/codex-eval-plugin
./eval image-pin evaluations/customer/suite.json --image codex-eval:0.1.0

# Set OPENAI_API_KEY and ANTHROPIC_API_KEY in your environment or ignored .env.local.
# Keys are read only from the invoking process; never put them in the suite or chat.
./eval models
./eval doctor evaluations/customer/suite.json
./eval validate evaluations/customer/suite.json --check-graders
./eval plan evaluations/customer/suite.json
# After the customer approves the displayed plan:
./eval approve evaluations/customer/suite.json --by 'Customer reviewer'
./eval run evaluations/customer/suite.json --output evaluations/customer-run
./eval report evaluations/customer-run
./eval dashboard evaluations/customer-run
```

The starter matrix covers the public OpenAI 5.6 Sol/Terra/Luna and GPT-6 Astra models, plus the current Claude Fable/Opus/Sonnet/Haiku lineup, using a dated catalog. Edit `matrix` to choose explicit model IDs, effort settings, and repeats. Default sample matrix: **3 tasks × 8 configurations × 3 repeats = 72 calls**. Do a small smoke run first. Account access and native-agent support are checked separately; unavailable lanes are never silently removed. `models --refresh --provider codex|claude` lists account-visible IDs without modifying the suite. Restricted models are catalogued separately.

For trusted-code development without Docker, use `init ... --mode local`, pin local CLI versions/paths, and follow the same commands. Local mode cannot guarantee host or grader isolation and is labeled as such in results. If a CLI launcher downloads or updates at runtime, pin the resolved native binary instead.

### CLI map

| Command | Purpose |
| --- | --- |
| `init DIRECTORY` | Create a customer-owned suite and discovery record |
| `history --provider ... --consent --output FILE` | Read approved JSONL user-message history, default last 30 days |
| `repo --path PATH --output FILE` | Read local Git workflow evidence |
| `repo --provider github --repo OWNER/REPO --output FILE` | Read merged PR metadata through `gh` |
| `repo --provider gitlab --repo GROUP/REPO --host HOST --output FILE` | Read MR metadata through `glab` |
| `snapshot --repo PATH --commit FULL_SHA --output TASK/baseline` | Export a regular-file snapshot without Git history |
| `benchmarks`, `models` | Inspect dated methodology/model catalogs |
| `validate SUITE --check-graders` | Verify schema, paths, baseline failure, and oracle success |
| `plan SUITE`, `approve SUITE --by NAME` | Review and seal exact inputs |
| `run SUITE --output RUN [--resume]` | Run or resume the identical sealed matrix |
| `report RUN`, `dashboard RUN` | Summarize, export CSV, and serve localhost UI |
| `export --output dist` | Produce a reproducible standalone plugin ZIP and checksum |

## What gets measured

- **Completion:** 1 or 0, determined by the external behavioral grader and allowed-change checks.
- End-to-end, native-agent, and grader latency.
- Input/output/cache-read/cache-write/reasoning tokens where available.
- Native turns with their provider-specific unit, plus tool calls.
- Claude Code's reported cost and OpenAI rate-card estimates with pricing provenance and an uncertainty envelope.
- Success rates, infrastructure-invalid counts, pending cells, and cost per verified success including failed-attempt spend.

Missing values remain null. Agent assertions and CLI exit 0 alone do not prove completion. Native harnesses and tokenizers differ; this is a **product/model configuration comparison**. Model outputs and provider caches remain nondeterministic. OpenAI CLI aggregates may not identify exact cache-write or context-tier charges; displayed estimates are not invoices. The spend threshold is checked between calls and can overshoot by one invocation.

Read the [methodology](plugins/codex-eval-plugin/ceval/data/methodology.md) and [task-design guide](plugins/codex-eval-plugin/ceval/data/task-design.md).

## Public benchmark reference library

The plugin bundles original summaries and links to [Datacurve DeepSWE](https://github.com/datacurve-ai/deep-swe), [SWE-bench](https://www.swebench.com/SWE-bench/guides/evaluation/), [Terminal-Bench](https://www.tbench.ai/), [Harbor](https://www.harborframework.com/docs/tasks), and [Aider Polyglot](https://aider.chat/docs/leaderboards/). It does not redistribute benchmark datasets. Imported tasks and source repositories need their own license review. The customer suite is not an official benchmark reproduction.

## Distribution

The complete standalone plugin is in [`plugins/codex-eval-plugin/`](plugins/codex-eval-plugin/). It has exactly one skill and includes its CLI, reference catalog, examples, schemas, and dashboard. No connector, MCP server, or extra runtime skill is required.

Install from the public repository in Codex:

```sh
codex plugin marketplace add ianho-oai/codex-eval-plugin
codex plugin add codex-eval-plugin@codex-eval
```

```sh
./eval export --output dist
# Extract the ZIP, then run without this parent repository:
python3 codex-eval-plugin/bin/codex-eval self-check
```

Source: [ianho-oai/codex-eval-plugin](https://github.com/ianho-oai/codex-eval-plugin). Repository and plugin use the same semantic version. See [CHANGELOG](CHANGELOG.md).

### One-command provider smoke test

The CLI loads `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` from `.env.local` in the current directory. Exported environment variables take precedence. Quoted values and `export KEY=...` are supported; shell commands and variable expansion are never executed.

After securely setting the provider's key in the same terminal:

```sh
./eval smoke --provider claude --output evaluations/claude-smoke
./eval dashboard evaluations/claude-smoke/run
```

Use `--provider codex` for OpenAI. This deliberately runs one small original trusted-local task, records the installed CLI version, checks its grader, and collects live metrics. It does not replace customer discovery or portfolio approval. If your CLI is an updater wrapper, pass `--binary /path/to/native/executable`. Repeated smoke tests require a new output path so earlier results survive.

## Development

```sh
python3 -m unittest discover -s tests -v
./eval self-check
./eval export --output dist
```

Tests use small local fixtures and protocol emulators, with no paid API calls. They cover orchestration, native telemetry shapes, graders, approval invalidation, resume, budget stops, secret exclusion, and standalone packaging. Live-provider coverage is recorded separately in [validation notes](VALIDATION.md). Keep customer data, credentials, history extracts, and generated runs out of Git.
