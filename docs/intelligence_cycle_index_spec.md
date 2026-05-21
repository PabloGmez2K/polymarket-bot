# Intelligence Cycle Index Mini-Spec

**Status:** DESIGN_DOC_FIRST / NOT APPROVED FOR CODE.

This document defines the narrow shape of a possible future Cycle Index Slim. It is a design guardrail only. It does not approve implementation.

## Objective

Create, if later approved, a small append-only index of pointers per bot cycle:

`data/intelligence/cycle_index.jsonl`

The Cycle Index would help later reviews find the right cycle artifacts without recalculating or reinterpreting trading outcomes. It must not become a new source of truth.

## Relationship With `cycles_history`

`cycles_history.jsonl` remains the canonical cycle history.

Cycle Index would complement it by storing lightweight pointers and already-existing IDs. It must not duplicate full cycle summaries, replace `cycles_history`, or become an input to trading decisions.

## Candidate Hook

If a future CODE prompt explicitly approves implementation, the lowest-risk hook is near the existing `cycle_data` construction and the `cycle_summary.json` / `cycles_history.jsonl` / Funnel writer block in `bot.py`.

This hook is not approved in this document.

## Safe Fields Already Detected

Only fields already present at cycle time should be considered:

- `cycle_id`
- `cycle_number`
- `logic_cycle_number`
- `logic_series`
- `timestamp_utc`
- `mode`
- `eval_key` when it already exists
- `discovered_markets_unique`
- `scan`
- `slot_metrics`
- `buys` as summary/pointers if already present
- `scanned_markets` as summary/pointers if already present
- artifact pointers to existing files such as:
  - `cycle_summary.json`
  - `cycles_history.jsonl`
  - `funnel_observability_log_only.jsonl`
  - `funnel_observability_latest.json`
  - `bot_signal_evaluations.jsonl`
  - `blocked_signals_resolutions.jsonl`

## Prohibited Or Deferred Fields

Do not include these without a new design review:

- `alarms_fired`
- `buy_ids`
- `blocked_signal_keys`
- `shadow_edge_keys`
- interpretive `policy_snapshot`
- scoring
- P&L
- outcome
- decision
- verdict

These fields are either not clearly available per cycle today, would require extra joins, or could create false confidence by mixing pointers with interpretation.

## Rules

- No historical backfill.
- No Telegram.
- No scheduler.
- No new alerts.
- No real DB writes.
- No runtime/env var changes.
- No Railway work.
- No trading semantics.
- No BANKROLL, BUY/SELL/SKIP, city mode, whitelist, guard, stop-loss, Fase C, or Truth Pipeline changes.
- If implemented later, writes must be best-effort/no-throw and never block a cycle.

## Future Gate

Move from this design state to CODE only with explicit user approval and a new prompt.

That future prompt must restate:

- exact fields;
- exact hook;
- no-throw behavior;
- validation scope;
- stop criterion;
- confirmation that Cycle Index is a pointer index, not a new source of truth.
