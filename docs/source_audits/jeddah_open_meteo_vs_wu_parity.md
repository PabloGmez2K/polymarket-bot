# Jeddah Open-Meteo vs WU/OEJN Source Parity Audit

Generated: `2026-05-17T17:15:02+00:00`

**Verdict:** **INSUFFICIENT_DATA**

> LOG_ONLY source-parity dossier. This does not authorize BUY/SELL/SKIP, whitelist, canary/active promotion, scheduler changes, env vars, DB writes, BANKROLL changes, Fase C, or Truth Pipeline activation.

## Objective

Compare Jeddah Open-Meteo proxy daily maximum temperature against the Polymarket settlement source, Weather Underground OEJN, before any Opus promotion review.

## Sources Used

- City/ICAO: `Jeddah` / `OEJN`
- Open-Meteo archive: `temperature_2m_max`, lat `21.6796`, lon `39.1565`, timezone `Asia/Riyadh`
- Weather Underground settlement source: `https://www.wunderground.com/history/daily/sa/jeddah/OEJN`
- WU data status: `missing_fetcher`
- Blocked signals source: `data\runtime_import_derived\blocked_signals_resolutions.jsonl`
- Gamma settlement derivation: `INSUFFICIENT_DATA`

## Aggregate Metrics

| Metric | Value |
|---|---:|
| n compared | 0 |
| median delta C | None |
| median abs delta C | None |
| p95 abs delta C | None |
| max abs delta C | None |
| pct abs delta >= 1C | None |
| pct abs delta >= 2C | None |

## Opus Criteria

| Criterion | Status |
|---|---|
| WU n >= 30 | NOT_MET |
| median abs delta <= 0.5C | NOT_MET |
| pct abs delta >= 1C <= 10.0% | NOT_MET |
| max abs delta <= 2.0C | NOT_MET |
| blocked days >= 10/11 match WU outcome | 0/0 comparable |

Reasons:
- unreliable_derivations=1
- n_dates_compared=1 < 20
- median_abs_delta_c=1.0 > 0.5
- pct_abs_delta_ge_1c=100.0 > 10.0

## Day By Day

| Date | Open-Meteo max C | WU high C | Delta C | Status |
|---|---:|---:|---:|---|
| 2026-03-18 | 39.8 | None | None | wu_fetcher_missing |
| 2026-03-19 | 31.0 | None | None | wu_fetcher_missing |
| 2026-03-20 | 29.4 | None | None | wu_fetcher_missing |
| 2026-03-21 | 31.0 | None | None | wu_fetcher_missing |
| 2026-03-22 | 33.0 | None | None | wu_fetcher_missing |
| 2026-03-23 | 33.5 | None | None | wu_fetcher_missing |
| 2026-03-24 | 30.6 | None | None | wu_fetcher_missing |
| 2026-03-25 | 35.1 | None | None | wu_fetcher_missing |
| 2026-03-26 | 27.8 | None | None | wu_fetcher_missing |
| 2026-03-27 | 26.0 | None | None | wu_fetcher_missing |
| 2026-03-28 | 29.0 | None | None | wu_fetcher_missing |
| 2026-03-29 | 31.0 | None | None | wu_fetcher_missing |
| 2026-03-30 | 34.2 | None | None | wu_fetcher_missing |
| 2026-03-31 | 34.5 | None | None | wu_fetcher_missing |
| 2026-04-01 | 40.5 | None | None | wu_fetcher_missing |
| 2026-04-02 | 37.4 | None | None | wu_fetcher_missing |
| 2026-04-03 | 37.8 | None | None | wu_fetcher_missing |
| 2026-04-04 | 33.0 | None | None | wu_fetcher_missing |
| 2026-04-05 | 31.8 | None | None | wu_fetcher_missing |
| 2026-04-06 | 33.7 | None | None | wu_fetcher_missing |
| 2026-04-07 | 32.2 | None | None | wu_fetcher_missing |
| 2026-04-08 | 35.5 | None | None | wu_fetcher_missing |
| 2026-04-09 | 30.7 | None | None | wu_fetcher_missing |
| 2026-04-10 | 30.1 | None | None | wu_fetcher_missing |
| 2026-04-11 | 30.4 | None | None | wu_fetcher_missing |
| 2026-04-12 | 29.9 | None | None | wu_fetcher_missing |
| 2026-04-13 | 31.4 | None | None | wu_fetcher_missing |
| 2026-04-14 | 34.5 | None | None | wu_fetcher_missing |
| 2026-04-15 | 36.0 | None | None | wu_fetcher_missing |
| 2026-04-16 | 38.0 | None | None | wu_fetcher_missing |
| 2026-04-17 | 41.2 | None | None | wu_fetcher_missing |
| 2026-04-18 | 42.0 | None | None | wu_fetcher_missing |
| 2026-04-19 | 38.0 | None | None | wu_fetcher_missing |
| 2026-04-20 | 35.4 | None | None | wu_fetcher_missing |
| 2026-04-21 | 34.0 | None | None | wu_fetcher_missing |
| 2026-04-22 | 31.6 | None | None | wu_fetcher_missing |
| 2026-04-23 | 32.5 | None | None | wu_fetcher_missing |
| 2026-04-24 | 36.0 | None | None | wu_fetcher_missing |
| 2026-04-25 | 36.1 | None | None | wu_fetcher_missing |
| 2026-04-26 | 35.6 | None | None | wu_fetcher_missing |
| 2026-04-27 | 36.2 | None | None | wu_fetcher_missing |
| 2026-04-28 | 34.2 | None | None | wu_fetcher_missing |
| 2026-04-29 | 33.4 | None | None | wu_fetcher_missing |
| 2026-04-30 | 32.6 | None | None | wu_fetcher_missing |
| 2026-05-01 | 35.0 | None | None | wu_fetcher_missing |
| 2026-05-02 | 36.0 | None | None | wu_fetcher_missing |
| 2026-05-03 | 42.1 | None | None | wu_fetcher_missing |
| 2026-05-04 | 41.0 | None | None | wu_fetcher_missing |
| 2026-05-05 | 34.4 | None | None | wu_fetcher_missing |
| 2026-05-06 | 33.0 | None | None | wu_fetcher_missing |
| 2026-05-07 | 34.3 | None | None | wu_fetcher_missing |
| 2026-05-08 | 35.0 | None | None | wu_fetcher_missing |
| 2026-05-09 | 36.6 | None | None | wu_fetcher_missing |
| 2026-05-10 | 36.2 | None | None | wu_fetcher_missing |
| 2026-05-11 | 36.3 | None | None | wu_fetcher_missing |
| 2026-05-12 | 38.0 | None | None | wu_fetcher_missing |
| 2026-05-13 | 35.7 | None | None | wu_fetcher_missing |
| 2026-05-14 | 38.4 | None | None | wu_fetcher_missing |
| 2026-05-15 | 40.5 | None | None | wu_fetcher_missing |
| 2026-05-16 | 38.7 | None | None | wu_fetcher_missing |

## Gamma-Derived Settlement Triage

**Verdict:** **INSUFFICIENT_DATA**

This section infers settlement temperature from resolved Polymarket/Gamma exact markets only. It does not scrape WU and does not replace formal WU parity.

| Metric | Value |
|---|---:|
| blocked exact dates | 2 |
| dates compared | 1 |
| median delta C | 1.0 |
| median abs delta C | 1.0 |
| max abs delta C | 1.0 |
| pct abs delta >= 1C | 100.0 |
| pct abs delta >= 2C | 0.0 |

Reasons:
- unreliable_derivations=1
- n_dates_compared=1 < 20
- median_abs_delta_c=1.0 > 0.5
- pct_abs_delta_ge_1c=100.0 > 10.0

| Date | Open-Meteo max C | Gamma settlement C | Delta C | Status | Evidence |
|---|---:|---:|---:|---|---|
| 2026-04-18 | 42.0 | 41.0 | 1.0 | compared | single YES exact market |
| 2026-04-19 | 38.0 | None | None | unreliable_gamma_derivation | expected exactly one YES exact market, got 0 |

Gamma fetch errors:
- `highest-temperature-in-jeddah-on-april-18-2026-43c`: HTTP Error 404: Not Found
- `highest-temperature-in-jeddah-on-april-19-2026-30c`: HTTP Error 404: Not Found

## Blocked Signals Days

| Date | Condition | Strike C | Outcome | WU high C | Expected From WU | Match | Trader | Consensus |
|---|---|---:|---|---:|---|---|---|---|
| 2026-04-18 | exact | 38.0 | No | None | None | None | Thrifty-Original | False |
| 2026-04-18 | exact | 39.0 | No | None | None | None | Thrifty-Original | False |
| 2026-04-18 | exact | 40.0 | No | None | None | None | Thrifty-Original | False |
| 2026-04-19 | exact | 33.0 | No | None | None | None | Unaware-Engine | False |

## Pass/Fail

`INSUFFICIENT_DATA`. This dossier remains LOG_ONLY and requires Opus review before any operational next step.

## Next Trigger For Opus

Provide a reliable WU/OEJN daily-high dataset or repo-approved WU fetcher, rerun this tool, and ask Opus to review the parity dossier only if the Opus criteria are met.
