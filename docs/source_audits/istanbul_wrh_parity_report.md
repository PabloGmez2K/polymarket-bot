# Istanbul WRH Parity Report

Generated: `2026-05-14T22:23:04+00:00`

Verdict: `WRH_PARITY_PARTIAL`

## Scope

LOG_ONLY offline source-parity report. This does not authorize execution, policy changes, city-mode changes, observed-audit inclusion, promotion, or bankroll changes.

- Source is `weather_gov_wrh_synoptic`.
- Observed dataset is `weather_gov_wrh_timeseries`.
- This is separate from NCEI and does not write observed audit data.

## Metrics

- n_compared: `3`
- n_match: `3`
- n_mismatch: `0`
- n_unknown: `0`
- mean_abs_delta: `1.0`
- max_abs_delta: `2.0`
- bias: `-1.0`
- unique_dates_fetched: `2`

## Rows

| Date | Strike C | WRH max C | Expected | Outcome | Match | Source citation | Warnings |
|---|---:|---:|---|---|---|---|---|
| 2026-04-13 | 12.0 | 12.0 | YES | YES | yes | False |  |
| 2026-04-13 | 14.0 | 12.0 | NO | NO | yes | False |  |
| 2026-04-18 | 15.0 | 14.0 | NO | NO | yes | False |  |
