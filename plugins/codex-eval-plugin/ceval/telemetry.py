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
        usage = [e.get('usage', {}) for e in completed]
        result.update(input_tokens=total(usage, 'input_tokens'), output_tokens=total(usage, 'output_tokens'),
                      cache_read_tokens=total(usage, 'cached_input_tokens'),
                      cache_write_tokens=total(usage, 'cache_creation_input_tokens'),
                      reasoning_tokens=total(usage, 'reasoning_output_tokens'),
                      turns=len(completed) if completed else None, turn_unit='codex_conversation_turn',
                      tool_calls=sum(e.get('type') == 'item.completed' and e.get('item', {}).get('type') in ('command_execution', 'file_change') for e in ev) if ev else None,
                      provider_success=bool(completed) and not any(e.get('type') in ('turn.failed', 'error') for e in ev))
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
                              cost_upper_usd=upper_input*2+out_cost*1.5,
                              cost_source='estimated_rate_card',
                              cost_note='Standard global short-context estimate. Upper envelope allows long-context rates and unknown cache writes; native turn aggregates cannot identify request tiers. Reasoning is included in output cost.')
    else:
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
