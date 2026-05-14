# Istanbul WRH Parity Report

Generated: `2026-05-14T22:23:04+00:00`

Verdict: `WRH_PARITY_PARTIAL`

This verdict is about preliminary outcome parity only. It is not an
observed-audit approval, source promotion, city-mode change, or trading
authorization.

## Scope

LOG_ONLY offline source-parity report. This does not authorize execution, policy changes, city-mode changes, observed-audit inclusion, promotion, or bankroll changes.

- Source is `weather_gov_wrh_synoptic`.
- Observed dataset is `weather_gov_wrh_timeseries`.
- This is separate from NCEI and does not write observed audit data.
- `WRH_PARITY_PASS_PRELIMINARY` means compared outcomes matched; Opus
  re-evaluation gates are evaluated separately below.

## Outcome Parity Metrics

- input_row_n: `3`
- candidate_row_n: `3`
- compared_row_n: `3`
- n_match: `3`
- n_mismatch: `0`
- n_unknown: `0`
- unique_market_n: `0`
- canonical_unique_market_n: `0`
- fallback_estimated_unique_market_n: `3`
- rows_without_canonical_market_id_n: `3`
- unique_market_key_strategy: `canonical condition_id/market_id/slug; fallback estimate date|condition|strike|outcome`
- mean_abs_delta: `1.0`
- max_abs_delta: `2.0`
- bias: `-1.0`
- unique_dates_fetched: `2`

Delta metrics measure the distance between WRH daily max and the market
strike. They are not mismatches when the expected YES/NO outcome still matches
the resolved outcome.

## Opus Re-Evaluation Gate

- OPUS_REEVALUATION_GATE_MET: `False`

Reasons:
- `no_20_demonstrable_unique_markets: canonical_unique_market_n=0, fallback_estimated_unique_market_n=3, required=20`
- `mean_abs_delta_above_threshold: mean_abs_delta=1.0, threshold=0.5`
- `directional_bias_above_threshold: bias=-1.0, max_abs_bias=0.3`
- `missing_second_explicit_wrh_candidate_city`

A zero-mismatch outcome parity result is positive source evidence, but it does
not authorize observed-audit inclusion, promotion gates, city modes,
BUY/SELL/SKIP, BANKROLL, or Phase C changes.

## Runtime Read-Only Follow-Up

Railway `/app/data/blocked_signals_resolutions.jsonl` was checked read-only
after this local report:

- total input rows: `584`
- Istanbul candidate rows: `22`
- n_compared: `22`
- n_match: `22`
- n_unknown: `0`
- mismatches: `0`
- unique market_id no-null: `5`
- unique condition_id no-null: `5`
- unique slug no-null: `5`
- fallback estimated unique key `date|condition|strike|outcome`: approximately `17`
- mean_abs_delta: `0.909`
- max_abs_delta: `3.0`
- bias: `-0.818`
- runtime outcome parity verdict: `WRH_PARITY_PASS_PRELIMINARY`
- runtime Opus gate: `false`

Runtime conclusion: outcome parity is perfect on compared rows, but the Opus
gate remains unmet because there are not 20 demonstrable unique markets,
`mean_abs_delta` is above `0.5`, absolute bias is above `0.3`, and a second WRH
candidate city is still missing.

## Rows

| Date | Strike C | WRH max C | Expected | Outcome | Match | Source citation | Warnings |
|---|---:|---:|---|---|---|---|---|
| 2026-04-13 | 12.0 | 12.0 | YES | YES | yes | False |  |
| 2026-04-13 | 14.0 | 12.0 | NO | NO | yes | False |  |
| 2026-04-18 | 15.0 | 14.0 | NO | NO | yes | False |  |
