# GitHub Copilot headless setup

Copilot is an optional third evaluation provider, alongside Codex and Claude Code. It runs its own native agent and bills the selected GitHub account. A personal paid Copilot plan can be used; an OpenAI API key does not authenticate Copilot. Setup may need a human login once; approved evaluations then run unattended.

Verified 2026-09-23: stable Copilot CLI **1.0.88**, native login, headless editing and independent grading with GPT-6 Astra and GPT-5.6 Sol at low effort. This establishes compatibility on the tested host/account, not universal access or task success. Recheck the [latest stable release](https://github.com/github/copilot-cli/releases/latest) before a new customer setup. Never update an active sealed run.

## 1. Select providers and check GitHub access

Offer Codex + Claude Code, Codex + Copilot, or all three. Preserve the customer's existing choice. Configure keys only for selected providers. Copilot remains opt-in. Bare `--all-models` restores Codex + Claude; use repeated `--provider` flags or explicit `--model` flags to retain Copilot.

The selected GitHub account needs a Copilot plan with access to the exact requested model. Review [personal Copilot settings](https://github.com/settings/copilot) and [model access](https://docs.github.com/en/copilot/how-tos/copilot-on-github/set-up-copilot/configure-access-to-ai-models). For an organization-funded seat, the administrator must also enable CLI and model policies; see [enterprise administration](https://docs.github.com/en/copilot/how-tos/copilot-cli/administer-copilot-cli-for-your-enterprise). A policy-denied error alone does not establish that the customer uses an enterprise plan.

## 2. Install and identify the executable

Use an existing installation when compatible. Otherwise follow [GitHub's installation guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli). For npm (Node.js 22+), this pins the tested stable version:

```sh
npm install -g @github/copilot@1.0.88
command -v copilot
copilot --version
copilot --help
```

After an upgrade or reinstall, start a fresh terminal and verify the executable path again. Reinstalling does not switch accounts. Use the same path for smoke and suite configuration. This adapter currently supports local macOS/Linux execution on github.com, not Docker or enterprise data-residency hosts.

## 3. Choose one authentication route

**Desktop: native Copilot login (recommended).** In the customer's terminal:

```sh
env -u COPILOT_GITHUB_TOKEN -u GH_TOKEN -u GITHUB_TOKEN copilot login --web-flow
```

Authorize the intended account in the browser. Then start `copilot` with those variables unset, use `/user` to confirm identity, and `/user switch` if needed. This is separate from `gh auth login`; browser sign-out or `gh` account changes alone do not select the evaluation account. Complete browser/device authorization personally if the host requires it. Never paste tokens or device codes into chat.

**Unattended host: dedicated token.** Create a [fine-grained personal token](https://github.com/settings/personal-access-tokens/new) owned by the personal account, with **Account permissions → Copilot Requests**. Classic PATs are unsupported. Use the smallest repository access needed; prepared synthetic fixtures do not require private-repository access. Put it in the invoking directory's ignored `.env.local`:

```dotenv
COPILOT_GITHUB_TOKEN=YOUR_FINE_GRAINED_TOKEN
```

Or set it through the terminal/secret manager. Do not add it to suite JSON. Existing exported variables override `.env.local`. See [GitHub authentication](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli).

The adapter deliberately requires a dedicated token or an explicit native account; it does not silently inherit `gh` authentication. Native mode ignores environment tokens and uses OS credential storage with fresh per-attempt Copilot settings containing only the selected identity. It does not copy credentials, other accounts, hooks, plugins, or user instructions. If the OS credential store is unavailable, use the dedicated token route explicitly. CLI plaintext credential fallback is not imported. BYOK is not a substitute for Copilot entitlement.

## 4. Check exact models and run a smoke test

In Copilot, `/model` shows account-visible choices and supported effort controls. Restart the CLI after changing authentication or upgrading. `EVAL models --provider copilot` is a dated adapter catalog, **not** an authenticated listing. `EVAL doctor SUITE --check-model-access` checks installation/configuration but leaves Copilot access `not_probed`.

Get approval for the exact small smoke scope, unless already authorized. Each command below makes paid inference calls on one bundled edit-and-test fixture, one repeat, 120-second agent timeout, no credit cap by default. The independent grader verifies the edited candidate in the actual launch context. The customer-run readiness gate separately requires a successful native shell-test receipt. Use a new output directory for every attempt.

Native login (replace `YOUR_LOGIN`):

```sh
EVAL smoke --provider copilot --model gpt-6-astra --effort low --copilot-account YOUR_LOGIN --binary /absolute/path/copilot --output evaluations/copilot-astra-smoke
EVAL smoke --provider copilot --model gpt-5.6-sol --effort low --copilot-account YOUR_LOGIN --binary /absolute/path/copilot --output evaluations/copilot-sol-smoke
```

Token mode uses the same commands with `--copilot-account YOUR_LOGIN` omitted. The CLI loads `.env.local` itself; native `copilot` does not automatically load this file. Run only the requested models, not both examples automatically. An optional `--copilot-max-ai-credits 30` sets a soft minimum-30 credit limit; disclose it before running. Do not impose a cap when the customer requested none.

Smoke every selected model/effort combination whose support is uncertain before a broad sweep. One model's pass does not establish another's access. The authenticated CLI 1.0.88 runtime reported Astra at `low`, `medium`, `high`, `xhigh`, `max`, and Sol/Terra at those levels plus `none` on 2026-09-23. The catalog includes these reported settings. Model listing establishes supported configuration, not successful inference; validate each new setting before broad dispatch. The one-off check used the SDK-documented `models.list` RPC; doctor still does not integrate that listing. The adapter uses CLI 1.0.88’s documented `--reasoning-effort` flag and requires `--usage-output-file` support in preflight. Never use `auto` or silently fall back to another model.

## 5. Configure the customer comparison

For provider defaults, use `EVAL configure SUITE --provider codex --provider copilot --all-efforts` (add `--provider claude` for all three). This selects Codex defaults and Copilot Astra/Sol/Terra across catalog-supported efforts. Apply the authentication and binary options below in the same command. Bare `--all-models` resets to Codex + Claude; it does not retain Copilot.

After the designed task portfolio is registered, select **every lane to retain** (configure replaces the selection), pin the installed executable, and choose authentication:

```sh
EVAL configure SUITE --model codex:gpt-6-astra --model copilot:gpt-6-astra --effort low --repeats 1 --copilot-account YOUR_LOGIN --copilot-binary /absolute/path/copilot --copilot-no-credit-limit --no-spend-stop
EVAL doctor SUITE --check-model-access
EVAL validate SUITE --check-graders
EVAL plan SUITE
```

For token mode replace `--copilot-account YOUR_LOGIN` with `--copilot-token`; no token appears on the command line. Add `--model claude:MODEL` to include Claude. To request a soft cap instead, use `--copilot-max-ai-credits 30`. New Copilot configurations default to no credit cap; existing configured limits stay unchanged unless explicitly updated. Account selection, binary/version, limits and model/effort enter the seal.

Review the concrete plan, retain actual customer approval, then use the normal `approve` and `run` commands. Customer suites also run one representative edit-and-test readiness check per provider before dispatch; include that cost in the plan. This gate does not prove all selected models work. Keep the same tasks and grading across providers. Configuration changes require a newly validated and approved run; preserve earlier evidence.

## Troubleshooting before a large run

| Symptom | Next action |
| --- | --- |
| Wrong account or unexpected organization wording | Check `/user`, exported variable **presence** without printing values, `.env.local` precedence, and the frozen account selector. Use native Copilot login for the intended account. |
| `Access denied by policy settings` | Check identity, plan, token permission and exact model access first; check admin CLI/model policy only for an organization seat. Retain it as infrastructure-invalid, not a coding failure. |
| Native account matches but no authentication found | Run in the same OS user/credential-store context as login. If unavailable, explicitly configure token mode. Do not export or copy keychain credentials. |
| Model absent or effort rejected | Inspect `/model`, verify binary/version, and approve a corrected selection; never silently substitute. |
| Works in terminal but not under the agent | Run the same approved smoke in the permitted ordinary terminal. Preserve sandbox and host controls. |
| Flag rejected | Check help for the exact executable; verify it is 1.0.88 or a newly tested version. Do not reuse old `gh copilot` commands or `--deny-tool='*'`. |

The runner allows only its declared local coding tools and disables interactive questions and optional integrations. These permissions do not override GitHub entitlement or provide OS isolation. Use trusted fixtures, not arbitrary untrusted repositories.

## Usage and dollar reporting

Retain `events.jsonl`, `copilot-usage.json`, metadata-only `copilot-otel.jsonl`, invocation and grader receipts for each attempt. Native usage JSON contains cumulative token counts even when JSONL events omit them. New runs ingest that receipt and log model identity, credits and a separate `copilot_usage_value_usd` in JSON/CSV. Do not sum root/model/agent billing totals: they overlap.

GitHub defines 1 AI credit as $0.01. A native `totalNanoAiu` receipt therefore yields credits = value / 1e9 and usage value USD = value / 1e11. This is usage valuation, **not additional invoice cost**; included allowance and billing adjustments remain unknown. `cost_usd` stays null. Never apply direct OpenAI/Anthropic API token prices to Copilot or interpret premium-request multipliers as dollars. Missing usage stays unknown. See [billing units](https://docs.github.com/en/billing/concepts/product-billing/github-copilot-billing) and [native usage contracts](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/usage-and-billing).

The dashboard starts on input tokens versus latency when Copilot is present, unless restoring saved axes. Task-cost plots omit unknown `cost_usd` and disclose missing points. Separate Copilot credit/usage-value axes and tooltips expose the native billing measurements without treating them as invoice cost. Reports and CSV retain these fields; summary known totals disclose missing receipts. An explicit USD spend stop pauses on missing currency cost and cannot enforce a Copilot credit ceiling. GitHub's own billing controls remain separate. Timeouts and numeric credit limits can still be exceeded by in-flight work; no credit cap does not mean free usage or unlimited plan entitlement.
