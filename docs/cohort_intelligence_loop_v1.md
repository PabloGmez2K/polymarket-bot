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

## Directional NO Forward Capture

Forward capture for directional NO starts at `2026-05-26T16:15:11Z`. The link is
LOG_ONLY and uses the demonstrated live identity path:

- `bot_signal_evaluations.eval_key`
- `signals.json` / resolver `match_key`
- closed Polymarket/Gamma market metadata (`condition_id`, `market_id`,
  `token_id_yes`, `token_id_no`, `market_slug`)

Only `condition in {at_or_above, at_or_below}`, side/outcome `NO`, with a real
`match_key` is eligible for forward directional resolution capture. The resolver
continues to match the closed market by the signal title and writes the resolved
outcome into `blocked_signals_resolutions.jsonl`.

Legacy directional trades in `trade_lifecycle.json` are deliberately not
backfilled into calibration. They can remain visible as executed P&L only, but
promotion gates for directional NO use only forward linked outcomes from the
forward start above.

## Live Side Visibility Forward Epoch

Forward visibility for side-segmented surviving cohorts starts at
`2026-05-26T20:58:28Z`.

From this epoch onward, future `bot_signal_evaluations.jsonl` rows written after
the live evaluator has chosen a side persist the real `side` (`YES` or `NO`),
`city_mode`, `evaluation_source`, `cohort_schema_version` and a stable
`cohort_key`. The writer only records fields already available at that point in
the existing evaluation path; it does not change admission, gates, sizing,
BUY/SELL/SKIP or any risk policy.

`SURVIVING_COHORTS_BY_SIDE` uses only rows at or after this epoch with an
explicit recorded side. It does not reconstruct historical side from old rows.
`exact / NO` remains shadow-protected and is excluded from recovery candidates,
although it can appear in the block for traceability.

## Price Filter Counterfactual

`PRICE_FILTER_COUNTERFACTUAL` starts as a LOG_ONLY forward experiment for
`price_out_of_range` rejects in `city_mode in {active, canary}`. It does not
change the live price range, admission, gates, BUY/SELL/SKIP, sizing, city
modes, BANKROLL, env vars or Fase C.

Cost guard: the writer never adds external forecast/API calls. It only evaluates
rows whose city/date forecast already exists in the current cycle's
`forecast_cache`, caps processing at 40 rows per cycle, and marks all other
sampled rows as `forecast_not_in_existing_cycle_cache`.

The artifact is `data/price_filter_counterfactual_log_only.jsonl`. It persists
the real market identity (`eval_key`/`identity_key`, `market_id`,
`condition_id`, token IDs, market slug when available), city/date/condition,
YES/NO prices, hypothetical side, `our_prob`, `mkt_prob`, `edge_pct`, cohort key
and outcome-link fields. `condition == exact AND side == NO` is always marked
`excluded_protected_exact_no` and is never surfaced as a recovery candidate
because `SHADOW_EXACT_NO_GLOBAL` remains canonical.

The digest/report can emit `CAPTURE_ACTIVE_NO_RESOLUTIONS_YET`, `NO_EDGE_FOUND`,
`INSUFFICIENT_SAMPLE`, `DATA_CAPTURE_BLOCKER` or `REVIEW_PRICE_POLICY`. Raw
hypothetical edge alone never emits `CANDIDATE_FOR_CANARY_REVIEW` and never
authorizes policy changes; outcome-linked evidence must go back to Opus/manual
review.

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
- `directional_forward_seen`
- `directional_forward_resolved_calibration_unique`
- directional forward capture status:
  `CAPTURE_ACTIVE_NO_RESOLUTIONS_YET`, `CALIBRATION_ACCUMULATING`, or
  `DATA_CAPTURE_BLOCKER`

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
