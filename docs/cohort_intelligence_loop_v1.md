# Cohort Intelligence Loop v1

LOG_ONLY measurement loop for weather signal cohorts. It turns existing live/shadow
artifacts into manual recommendations for canary review, without changing trading.

## Consumer

`tools/cohort_intelligence_report.py` reads:

- `data/bot_signal_evaluations.jsonl`
- `data/skip_log.jsonl`
- `data/blocked_signals_resolutions.jsonl`
- `data/trade_lifecycle.json`

`tools/daily_bot_observability_run.py` includes the compact summary in the daily
bot digest by default. The section is fail-open: if inputs are missing or the
tool fails, the digest continues.

## Cohorts

Minimum v1 cohorts:

- `exact/NO near-threshold`: `condition=exact`, side `NO`, `abs(forecast-target) < 1.5C`
- `exact/NO far`: `condition=exact`, side `NO`, `abs(forecast-target) >= 1.5C`
- `directional NO`: `condition in {at_or_above, at_or_below}`, side `NO`
- directional NO subcohorts by city, source, and distance band

Current live policy: new executable `condition=exact`, side `NO` signals are
shadow-only globally via `SHADOW_EXACT_NO_GLOBAL`. The near/far split remains a
reporting segment based on distance telemetry; it is no longer an execution
boundary. `PAUSE_WELLINGTON_EXACT_NO` remains as a redundant city-scoped pause.

## Analysis Units

The report intentionally keeps three views separate:

- `raw_signals`: one row per observed evaluation/signal. This is for throughput
  and traceability only; it can include repeated evaluations of the same market.
- `resolved_market_calibration`: one independent resolved market outcome per
  market identity + side + outcome. This is the only view used for WR,
  calibration gap and simulated unit P&L.
- `executed_trade_pnl`: one identifiable executed lifecycle record. This is used
  only for `pnl_real_reported_noncanonical`; it does not feed calibration.

Calibration identity uses the resolver's demonstrated market key first:
`eval_key`/`match_key` (`city|date|condition|threshold|unit`) + side + resolved
outcome. `condition_id` and then `market_id` are fallback identities only,
because live weather artifacts can reuse a condition identifier across multiple
temperature strikes.

The first Cohort Intelligence v1 digest counts for exact/NO were diagnostic raw
counts, not calibration-safe sample sizes. The current report keeps those raw
counts visible while preventing them from driving calibration gates.

## Metrics

For each cohort the report emits:

- `n_seen_raw`, `n_closed_raw`
- `n_closed_calibration_unique`, `wins_calibration`, `losses_calibration`,
  `wr_calibration`
- `avg_our_prob_calibration`
- `calibration_gap = avg_our_prob_calibration - wr_calibration`
- `pnl_simulated_unit_calibration`
- `n_executed_trades_unique`
- `pnl_real_reported_noncanonical` from executed trades only; non-canonical and
  not eligible for BANKROLL/readiness/accounting
- `duplicates_removed_for_calibration`
- `duplicate_diagnostics.top_duplicate_calibration_keys`
- `data_quality_verdict`, `decision_verdict`
- `last_seen`, `gate_current`

## Manual Verdicts

The report emits only:

- `INSUFFICIENT_SAMPLE`
- `KEEP_SHADOW`
- `REVIEW_BLOCK_LIVE`
- `CANDIDATE_FOR_CANARY_REVIEW`
- `REVIEW_OPUS`

Current gates:

- `DATA_QUALITY_BLOCKER`: missing calibration identity or executed-trade
  identity where needed.
- `REVIEW_BLOCK_LIVE`: `n_closed_calibration_unique >= 10` and
  (`wr_calibration <= 0.40` or `calibration_gap >= 0.20`) and negative simulated
  unit P&L.
- `CANDIDATE_FOR_CANARY_REVIEW`: shadow cohort with
  `n_closed_calibration_unique >= 10`, `wr_calibration >= 0.60`,
  `calibration_gap <= 0.10`, and positive simulated unit P&L.
- `INSUFFICIENT_SAMPLE`: calibration-unique minimum sample not reached.

These are report-only recommendations. They do not authorize BUY/SELL/SKIP,
BANKROLL changes, sizing, guards, scheduler changes, whitelist changes, city
modes, env vars, Fase C, or auto-promotion.

## Opus Trigger

Open Opus review only when `directional NO` globally, or any directional NO
subcohort, reaches `CANDIDATE_FOR_CANARY_REVIEW` in the daily digest/report.
