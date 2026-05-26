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

## Metrics

For closed/resolved rows the report emits:

- `n_closed`, `wins`, `losses`, `wr_observed`
- `avg_our_prob`
- `calibration_gap = avg_our_prob - wr_observed`
- `pnl_simulated_unit`
- `pnl_real_reported_noncanonical` when a trade lifecycle join is available
- `last_seen`, `gate_current`, `verdict`

## Manual Verdicts

The report emits only:

- `INSUFFICIENT_SAMPLE`
- `KEEP_SHADOW`
- `REVIEW_BLOCK_LIVE`
- `CANDIDATE_FOR_CANARY_REVIEW`
- `REVIEW_OPUS`

Initial v1 gates:

- `REVIEW_BLOCK_LIVE`: `n_closed >= 10` and (`wr_observed <= 0.40` or `calibration_gap >= 0.20`) and negative P&L.
- `CANDIDATE_FOR_CANARY_REVIEW`: shadow cohort with `n_closed >= 10`, `wr_observed >= 0.60`, `calibration_gap <= 0.10`, and positive simulated P&L.
- `INSUFFICIENT_SAMPLE`: minimum sample not reached.

These are report-only recommendations. They do not authorize BUY/SELL/SKIP,
BANKROLL changes, sizing, guards, scheduler changes, whitelist changes, city
modes, env vars, Fase C, or auto-promotion.

## Opus Trigger

Open Opus review only when `directional NO` globally, or any directional NO
subcohort, reaches `CANDIDATE_FOR_CANARY_REVIEW` in the daily digest/report.
