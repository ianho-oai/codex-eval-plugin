"""Native event normalization. Unknown measurements remain null."""
from __future__ import annotations

import json
import math


def numeric(value):
    return value if type(value) in (float, int) and math.isfinite(value) and value >= 0 else None


def events(text):
    result, invalid = [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                result.append(value)
            else:
                invalid += 1
        except ValueError:
            invalid += 1
    return result, invalid


def total(items, field):
    values = [numeric(x.get(field)) for x in items]
    return sum(values) if values and all(x is not None for x in values) else None


def copilot_usage(row, usage, model):
    """Enrich from the CLI's final receipt, never summing nested billing totals."""
    if not isinstance(usage, dict):
        return
    metrics = usage.get('modelMetrics')
    metrics = metrics if isinstance(metrics, dict) else {}
    observed = set(row.get('observed_models', [])) | set(metrics)
    if isinstance(usage.get('currentModel'), str):
        observed.add(usage['currentModel'])
    row['observed_models'] = sorted(observed)
    if observed - {model}:
        row['provider_success'] = False
    metric = metrics.get(model)
    tokens = metric.get('usage', {}) if isinstance(metric, dict) else {}
    if isinstance(tokens, dict):
        for field, native in [('input_tokens','inputTokens'), ('output_tokens','outputTokens'),
                              ('cache_read_tokens','cacheReadTokens'), ('cache_write_tokens','cacheWriteTokens'),
                              ('reasoning_tokens','reasoningTokens')]:
            value = numeric(tokens.get(native))
            if value is not None:
                row[field] = value
    nano = numeric(usage.get('totalNanoAiu'))
    if nano is not None:
        row.update(copilot_nano_aiu=nano, copilot_ai_credits=nano/1e9,
                   copilot_usage_value_usd=nano/1e11,
                   copilot_usage_value_source='native_totalNanoAiu; 1e9 nanoAIU/credit; USD 0.01/credit; checked 2026-09-23')
    row['copilot_usage_source'] = 'copilot-usage.json'
    row['cost_note'] = 'Native credit-derived usage value is reported separately; included allowance and net invoice cost are unknown. No direct-API pricing.'
    # Included allowance and invoice adjustments are unknown. This does not
    # populate cost_usd or claim that a dollar spend stop can be enforced.


def normalize(provider, text, model, pricing):
    ev, invalid = events(text)
    result = {'input_tokens': None, 'uncached_input_tokens': None, 'output_tokens': None,
              'cache_read_tokens': None, 'cache_write_tokens': None, 'reasoning_tokens': None,
              'turns': None, 'turn_unit': None, 'tool_calls': None, 'cost_usd': None,
              'cost_lower_usd': None, 'cost_upper_usd': None, 'cost_source': 'unavailable',
              'cost_note': '', 'provider_duration_ms': None, 'provider_api_duration_ms': None,
              'provider_success': False, 'model_usage': {}, 'invalid_event_lines': invalid}
    if provider == 'codex':
        completed = [e for e in ev if e.get('type') == 'turn.completed']
        states = [e['type'] for e in ev if e.get('type') in ('turn.started', 'turn.completed', 'turn.failed', 'error')]
        usage = [e.get('usage', {}) for e in completed]
        result.update(input_tokens=total(usage, 'input_tokens'), output_tokens=total(usage, 'output_tokens'),
                      cache_read_tokens=total(usage, 'cached_input_tokens'),
                      cache_write_tokens=total([dict(u, cache_writes=u.get('cache_write_input_tokens', u.get('cache_creation_input_tokens'))) for u in usage], 'cache_writes'),
                      reasoning_tokens=total(usage, 'reasoning_output_tokens'),
                      turns=len(completed) if completed else None, turn_unit='codex_conversation_turn',
                      tool_calls=sum(e.get('type') == 'item.completed' and e.get('item', {}).get('type') in ('command_execution', 'file_change') for e in ev) if ev else None,
                      # Error events can describe recovered stream reconnects.
                      # Require terminal completion; never erase a failed turn.
                      provider_success=bool(states) and states[-1] == 'turn.completed' and 'turn.failed' not in states)
        # Native events currently aggregate a conversation turn, not each model request.
        # Never infer an exact long-context/cache-write charge from this aggregate.
        rate = pricing.get('models', {}).get(model)
        i, o, c, w = (result[k] for k in ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens'))
        if i is not None and c is not None and 0 <= c <= i:
            result['uncached_input_tokens'] = i - c
        if rate and None not in (i, o, c) and 0 <= c <= i and (w is None or 0 <= w <= i-c):
            required = ('input', 'cached_input', 'cache_write', 'output')
            if all(numeric(rate.get(k)) is not None for k in required):
                write = w or 0
                input_cost = ((i-c-write)*rate['input'] + c*rate['cached_input'] + write*rate['cache_write'])/1e6
                out_cost = o*rate['output']/1e6
                upper_input = ((i-c)*max(rate['input'], rate['cache_write']) + c*rate['cached_input'])/1e6
                result.update(cost_usd=input_cost+out_cost, cost_lower_usd=input_cost+out_cost,
                              cost_upper_usd=upper_input*rate.get('long_input_multiplier', 1)+out_cost*rate.get('long_output_multiplier', 1),
                              cost_source='estimated_rate_card',
                              cost_note='Standard global short-context estimate. Upper envelope allows long-context rates and unknown cache writes; native turn aggregates cannot identify request tiers. Reasoning is included in output cost.')
    elif provider == 'copilot':
        # CLI JSONL uses SDK event envelopes. Never interpret its billing multiplier
        # or AI units as dollars, or apply a model vendor's direct-API rate card.
        usage = [e.get('data', {}) for e in ev if e.get('type') == 'assistant.usage']
        shutdowns = [e.get('data', {}) for e in ev if e.get('type') == 'session.shutdown']
        final = shutdowns[-1] if shutdowns else {}
        # CLI 1.0.83 emits a top-level result rather than SDK session.shutdown.
        cli_results = [e for e in ev if e.get('type') == 'result']
        cli_final = cli_results[-1] if cli_results else {}
        cli_usage = cli_final.get('usage') or {}
        checkpoints = [e.get('data', {}) for e in ev if e.get('type') == 'session.usage_checkpoint']
        billing = checkpoints[-1] if checkpoints else {}
        calls = [e.get('data', {}) for e in ev if e.get('type') == 'model.call_start']
        states = [e for e in ev if e.get('type') in ('session.idle', 'session.shutdown', 'session.error', 'session.abort', 'result')]
        terminal = states[-1] if states else {}
        completed = (terminal.get('type') == 'session.idle' and not terminal.get('data', {}).get('aborted')) or (
            terminal.get('type') == 'session.shutdown' and final.get('shutdownType') == 'routine') or (
            terminal.get('type') == 'result' and numeric(terminal.get('exitCode')) == 0)
        observed = {u['model'] for u in usage + calls if isinstance(u.get('model'), str)}
        if final.get('currentModel'):
            observed.add(final['currentModel'])
        result.update(input_tokens=total(usage, 'inputTokens'), output_tokens=total(usage, 'outputTokens'),
                      cache_read_tokens=total(usage, 'cacheReadTokens'), cache_write_tokens=total(usage, 'cacheWriteTokens'),
                      reasoning_tokens=total(usage, 'reasoningTokens'),
                      turns=len(calls) if calls else len(usage) if usage else None, turn_unit='copilot_model_call',
                      tool_calls=sum(e.get('type') == 'tool.execution_start' for e in ev) if ev else None,
                      provider_duration_ms=numeric(cli_usage.get('sessionDurationMs')),
                      provider_api_duration_ms=numeric(cli_usage.get('totalApiDurationMs')) if cli_final else
                                               numeric(final.get('totalApiDurationMs')) if final else total(usage, 'duration'),
                      provider_success=bool(completed) and not any(e.get('type') in ('session.error', 'session.abort') for e in ev)
                                       and not (observed - {model}),
                      model_usage=final.get('modelMetrics') or {}, observed_models=sorted(observed),
                      copilot_premium_requests=numeric(cli_usage.get('premiumRequests', final.get('totalPremiumRequests', billing.get('totalPremiumRequests')))),
                      copilot_nano_aiu=numeric(final.get('totalNanoAiu', billing.get('totalNanoAiu'))),
                      cost_note='Copilot account billing; AI units and request multipliers are not USD. No direct-API price estimate.')
    elif provider == 'claude':
        finals = [e for e in ev if e.get('type') == 'result']
        f = finals[-1] if finals else {}
        u = f.get('usage') or {}
        i, c, w = (numeric(u.get(k)) for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
        result.update(uncached_input_tokens=i, cache_read_tokens=c, cache_write_tokens=w,
                      input_tokens=i+c+w if None not in (i, c, w) else None,
                      output_tokens=numeric(u.get('output_tokens')), reasoning_tokens=None,
                      turns=numeric(f.get('num_turns')), turn_unit='claude_native_turn',
                      tool_calls=sum(b.get('type') == 'tool_use' for e in ev if e.get('type') == 'assistant' for b in e.get('message', {}).get('content', [])) if ev else None,
                      provider_duration_ms=numeric(f.get('duration_ms')),
                      provider_api_duration_ms=numeric(f.get('duration_api_ms')),
                      provider_success=f.get('subtype') == 'success' and not f.get('is_error', False),
                      model_usage=f.get('modelUsage') or {})
        cost = numeric(f.get('total_cost_usd'))
        if cost is not None:
            result.update(cost_usd=cost, cost_lower_usd=cost, cost_upper_usd=cost,
                          cost_source='reported_by_claude_code', cost_note='Native total_cost_usd; provider billing remains authoritative.')
    result['telemetry_complete'] = all(result[k] is not None for k in ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cost_usd'))
    return result
