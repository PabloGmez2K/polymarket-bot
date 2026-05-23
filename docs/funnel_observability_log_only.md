# Funnel Observability LOG_ONLY

**Status:** IMPLEMENTED / LOG_ONLY / DIGEST WIRED.
**Decision source:** Opus strategic decision after live throughput evidence pack, cycle 366 (`2026-05-21T11:38:47Z`): `CODE_LOG_ONLY_METRICS_FIRST + SOURCE_ONBOARDING_FIRST`.

This document records the implemented narrow observability patch for the weather-market funnel. It does not authorize trading, change policy, or change any filter.

## Implementation Status

The LOG_ONLY funnel observability patch is already committed in `bot.py`.

Implemented pieces:

- Output paths: `FUNNEL_OBSERVABILITY_LOG_ONLY_FILE` and `FUNNEL_OBSERVABILITY_LATEST_FILE`.
- `count_discovered_markets_unique(...)` for top-of-funnel market dedupe.
- `build_funnel_observability_record(...)` for per-cycle counter normalization.
- `write_funnel_observability_log_only(...)` as a best-effort/no-throw writer.
- Discovery hook after `all_markets` is collected.
- Cycle hook beside `cycle_summary.json` and `cycles_history.jsonl`.
- Daily Bot Digest compact read-only block from `funnel_observability_log_only.jsonl`.
- Focused tests in `tests/test_funnel_observability.py`.

This status update is documentation-only. It does not reopen the semantic design.

## Objective

Make the funnel visible per cycle before changing universe, city modes, exact/range filters, canary scope, BANKROLL, sizing, scheduler, source policy, or BUY/SELL/SKIP behavior.

The missing top-of-funnel metric is:

`discovered_markets_unique`

Definition: unique Polymarket weather markets discovered during a cycle before bot filters. Prefer stable market identifiers in this order:

1. `condition_id`
2. `market_id`
3. `market_slug`
4. fallback composite: `city|date|condition|threshold|threshold_high|unit|question`

Do not count token sides separately. One temperature market should count once even if YES/NO tokens both exist.

## Canonical Stages

The per-cycle funnel should be emitted in this order:

| Stage | Meaning | Current source / future source |
| --- | --- | --- |
| `discovered` | Unique markets fetched/discovered before filters. | New `discovered_markets_unique`. |
| `prefiltered` | Markets that survive parsing and early prefilters; legacy alias is `markets_evaluated`. | `cycles_history.scan.markets_evaluated`. |
| `city_window_skipped` | Same-day markets outside allowed city/time routing window. | `cycles_history.scan.city_window_skipped`. |
| `price_out_of_range` | Markets rejected by price bounds. | `scan.slot_metrics.reject_reasons.price_out_of_range`. |
| `date_out_of_range` | Markets rejected by date window, split past/future if available. | `date_out_of_range_past` and future equivalent when present. |
| `condition_filtered` | Markets rejected because condition is outside `ALLOWED_CONDITIONS`. | `scan.condition_filtered` / reject reason. |
| `policy/source blocked` | Markets blocked by city mode, source, allowlist, settlement risk, shadow/non-tradable policy, or equivalent. | `fuera_allowlist`, `blocked_city`, `settlement_risk`, shadow policy fields when present. |
| `edge` | Markets with modeled edge above threshold before final selection. | `scan.with_edge`. |
| `shadow_edge` | Edge markets observed but not tradeable because city/source/policy mode is non-buy. | `scan.shadow`; detail should include city and reason. |
| `selected` | Markets selected for attempted trade path. | `scan.selected`. |
| `real_buy` | Real executed BUY orders. | `len(cycles_history.buys)` and execution recorder. |

These are observability names only. They do not imply that an item should advance to the next stage.

## Minimum Per-Cycle Fields

Recommended JSON object per cycle:

```json
{
  "schema_version": 1,
  "ts_utc": "2026-05-21T11:38:47Z",
  "cycle_number": 366,
  "logic_cycle_number": 360,
  "logic_series": "10.6",
  "mode": "REAL",
  "log_only": true,
  "trading_authorization": "NO_ACTION",
  "discovered_markets_unique": 330,
  "prefiltered": 22,
  "city_window_skipped": 154,
  "price_out_of_range": 121,
  "date_out_of_range": {
    "past": 33,
    "future": 0
  },
  "condition_filtered": 11,
  "policy_source_blocked": {
    "total": 4,
    "fuera_allowlist": 4,
    "blocked_city": 0,
    "settlement_risk": 0,
    "shadow_only_mode": 0
  },
  "edge": 2,
  "shadow_edge": 4,
  "selected": 2,
  "real_buy": 2,
  "execution_rejects": {},
  "sample_shadow_edges": [
    {
      "city": "Hong Kong",
      "edge_pct": 54.45,
      "reason": "shadow_or_non_buy_policy"
    }
  ]
}
```

Optional but useful fields:

- `discovered_markets_by_city`
- `discovered_markets_by_condition`
- `reject_reasons`
- `same_day_reject_reasons`
- `execution_reject_reasons`
- `shadow_edge_by_city`
- `blocked_edge_by_city`
- `top_price_out_of_range_by_city`
- `source_risk_by_city`

## Artifact Format

The implementation writes append-only JSONL:

`data/funnel_observability_log_only.jsonl`

Each line is one cycle. It also writes a compact latest snapshot:

`data/funnel_observability_latest.json`

The JSONL writer is best-effort and no-throw. I/O errors must not stop a cycle. The writer must not be read by trading decision code.

## Joining Evaluation And Resolution Artifacts

Existing artifacts:

- `bot_signal_evaluations.jsonl`
- `blocked_signals_resolutions.jsonl`

Join key:

`eval_key` in `bot_signal_evaluations.jsonl` equals `match_key` in `blocked_signals_resolutions.jsonl`.

Recommended join:

```text
left = bot_signal_evaluations by eval_key
right = blocked_signals_resolutions by match_key
join where left.eval_key == right.match_key
```

Use the join to explain trader-vs-bot gaps and post-settlement outcomes, not to authorize trades. Minimum joined fields:

- `eval_key` / `match_key`
- `cycle_id`
- `city`
- `date_iso` / `date`
- `condition`
- `threshold`
- `unit`
- `decision_gate`
- `skip_or_block_reason`
- `would_buy`
- `bot_edge_pct_at_signal`
- `bot_evaluation_join_status`
- `reason_blocked`
- `city_mode_at_record_time`
- `win_for_trader`
- `settlement_fidelity_status`

Interpretation guardrail:

- `captured` means the bot's evaluation was observed.
- `missing` means there was no matched live evaluation row.
- Neither state changes whitelist, city mode, source policy, or BUY/SELL/SKIP.

## Trading Authorization Guardrails

The implemented patch remains fail-closed:

- `log_only=true`
- `trading_authorization="NO_ACTION"`
- no changes to `ACTIVE_TRADING_CITIES`, `CANARY_TRADING_CITIES`, `BLOCKED_CITIES`, `auto_*_cities`, whitelist, BANKROLL, sizing, scheduler, source policy, exact/range filters, guards, DB, env vars, Railway runtime, Fase C, or BUY/SELL/SKIP
- no automatic promotion from `shadow_edge`, `edge`, or any joined settlement outcome
- any city mode change requires later human confirmation

## Daily Digest / Telegram Compact View

Implemented compact block in `tools/daily_bot_digest.py`:

```text
Funnel LOG_ONLY:
window=2026-05-22T08:00:47Z -> 2026-05-23T08:00:47Z cycles=9
discovered=2970 prefiltered=246 edge=0 shadow_edge=7 selected=0 BUY=0
skips: city_window=1155 price=1228 date_past=330 condition=234
LOG_ONLY: No BANKROLL, no BUY/SELL/SKIP, no Fase C.
```

If `discovered_markets_unique` is unavailable, show `discovered=?` and mark the cycle `baseline_partial=true`.

Telegram preview includes the same LOG_ONLY metrics in a compact 24h section.

## Read-Only Baseline, 7 Days

Source commands used read-only through `tools/railway_safe.ps1`:

- `railway logs --since 1w --lines 300 --json`
- `railway ssh ls -1 /app/data`
- `railway ssh tail -n 80 /app/data/cycles_history.jsonl`
- `railway ssh wc -l /app/data/bot_signal_evaluations.jsonl`
- `railway ssh head -n 1 /app/data/bot_signal_evaluations.jsonl`
- `railway ssh wc -l /app/data/blocked_signals_resolutions.jsonl`

Baseline window available from `cycles_history.jsonl`:

| Field | Value |
| --- | ---: |
| Window | `2026-05-14T12:00:46Z` to `2026-05-21T12:00:45Z` |
| Cycles | 55 (`cycle_number` 313 to 367) |
| `prefiltered` / `markets_evaluated` | sum 843, avg 15.33, min 0, max 49 |
| `edge` / `with_edge` | sum 19, avg 0.35, min 0, max 3 |
| `selected` | sum 18, avg 0.33, min 0, max 3 |
| `shadow_edge` / `shadow` | sum 50, avg 0.91, min 0, max 4 |
| `condition_filtered` | sum 688, avg 12.51, min 0, max 48 |
| `city_window_skipped` | sum 6237, avg 113.40, min 0, max 286 |
| `real_buy` | 14 |
| `execution_rejects` | `buy_min_size=4` |

Reject reason totals in the same window:

| Reason | Count |
| --- | ---: |
| `price_out_of_range` | 4650 |
| `date_out_of_range_past` | 2079 |
| `condition_filtered` | 688 |
| `below_min_edge` | 67 |
| `timezone_filter` | 66 |
| `fuera_allowlist` | 50 |
| `liquidity_low` | 18 |
| `existing_position` | 8 |
| `sl_city_cooldown` | 5 |
| `buy_min_size` | 4 |
| `kelly_too_low` | 4 |
| `low_exact_gap_risk` | 1 |
| `sold_this_cycle` | 1 |

Additional artifact availability:

- `bot_signal_evaluations.jsonl`: 357 rows, 14 cycles, from `2026-05-19T20:00:55Z` to `2026-05-21T12:00:45Z`.
- `blocked_signals_resolutions.jsonl`: 660 rows.
- Latest logs available through Railway were recent deployment logs only; they confirmed cycle 366 and 367 activity but did not expose historical funnel counters directly.

What was missing for the historical 7-day baseline:

- `discovered_markets_unique` was not present in historical `cycles_history.jsonl` rows from before the implementation.
- The existing `scanned_markets` list is a small sampled list, not raw discovery.
- `bot_signal_evaluations.jsonl` does not cover the full 7-day window; it starts on `2026-05-19T20:00:55Z`.
- Per-city/per-market breakdowns for `price_out_of_range`, `date_out_of_range`, and `policy/source blocked` are incomplete unless reconstructed from skip logs or future structured metrics.

## Implemented Hook Locations

Current implementation locations:

- `bot.py` constants near the runtime artifact paths.
- `bot.py` market discovery / scan loop: counts `discovered_markets_unique`.
- `bot.py` `build_funnel_observability_record(...)`: normalizes stage counters.
- `bot.py` `write_funnel_observability_log_only(...)`: appends JSONL and writes latest snapshot.
- `bot.py` near `cycle_summary` / `cycles_history`: emits one funnel record per cycle.
- `tests/test_funnel_observability.py`: covers market dedupe, counter mapping, partial baseline, JSONL/latest writes, and no-throw I/O failure.

## Future Non-Semantic Extensions

Any future extension must remain LOG_ONLY and require a separate prompt. Candidate non-semantic improvements:

- Optional compact digest copy if explicitly approved.
- Additional per-city/per-reason breakdowns derived only from already collected counters.
- A separate Cycle Index pointer layer, only after its mini-spec is approved for CODE.

Validation for future patch:

- `python -m py_compile bot.py`
- focused tests for funnel counter builder and writer
- `git diff --check`
- `python verify_before_deploy.py` because that future patch would touch code
