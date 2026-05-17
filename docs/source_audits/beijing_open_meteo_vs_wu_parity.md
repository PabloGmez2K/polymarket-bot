# Beijing Open-Meteo vs WU/ZBAA Source Parity Audit

Generated: `2026-05-17T16:29:53+00:00`

**Verdict:** **WU_FETCHER_MISSING**

> LOG_ONLY source-parity dossier. This does not authorize BUY/SELL/SKIP, whitelist, canary/active promotion, scheduler changes, env vars, DB writes, BANKROLL changes, Fase C, or Truth Pipeline activation.

## Objective

Compare Beijing Open-Meteo proxy daily maximum temperature against the Polymarket settlement source, Weather Underground ZBAA, before any Opus promotion review.

## Sources Used

- City/ICAO: `Beijing` / `ZBAA`
- Open-Meteo archive: `temperature_2m_max`, lat `40.0799`, lon `116.6031`, timezone `Asia/Shanghai`
- Weather Underground settlement source: `https://www.wunderground.com/history/daily/cn/beijing/ZBAA`
- WU data status: `missing_fetcher`
- Blocked signals source: `C:\Projects\polymarket-bot\data\runtime_import_derived\blocked_signals_resolutions.jsonl`

## Aggregate Metrics

| Metric | Value |
|---|---:|
| n compared | 0 |
| median delta C | None |
| median abs delta C | None |
| p95 abs delta C | None |
| pct abs delta >= 1C | None |
| pct abs delta >= 2C | None |

## Opus Criteria

| Criterion | Status |
|---|---|
| n >= 30 | NOT_MET |
| median abs delta <= 0.5C | NOT_MET |
| pct abs delta >= 1C <= 10.0% | NOT_MET |
| blocked days >= 10/11 match WU outcome | 0/0 comparable |

Reasons:
- no reliable WU/ZBAA fetcher exists in repo and no --wu-csv was provided

## Day By Day

| Date | Open-Meteo max C | WU high C | Delta C | Status |
|---|---:|---:|---:|---|
| 2026-03-18 | 11.4 | None | None | wu_fetcher_missing |
| 2026-03-19 | 16.1 | None | None | wu_fetcher_missing |
| 2026-03-20 | 13.6 | None | None | wu_fetcher_missing |
| 2026-03-21 | 15.1 | None | None | wu_fetcher_missing |
| 2026-03-22 | 21.9 | None | None | wu_fetcher_missing |
| 2026-03-23 | 18.0 | None | None | wu_fetcher_missing |
| 2026-03-24 | 19.5 | None | None | wu_fetcher_missing |
| 2026-03-25 | 24.6 | None | None | wu_fetcher_missing |
| 2026-03-26 | 25.1 | None | None | wu_fetcher_missing |
| 2026-03-27 | 21.0 | None | None | wu_fetcher_missing |
| 2026-03-28 | 20.6 | None | None | wu_fetcher_missing |
| 2026-03-29 | 21.8 | None | None | wu_fetcher_missing |
| 2026-03-30 | 16.8 | None | None | wu_fetcher_missing |
| 2026-03-31 | 16.6 | None | None | wu_fetcher_missing |
| 2026-04-01 | 17.2 | None | None | wu_fetcher_missing |
| 2026-04-02 | 18.9 | None | None | wu_fetcher_missing |
| 2026-04-03 | 24.7 | None | None | wu_fetcher_missing |
| 2026-04-04 | 17.1 | None | None | wu_fetcher_missing |
| 2026-04-05 | 18.5 | None | None | wu_fetcher_missing |
| 2026-04-06 | 18.1 | None | None | wu_fetcher_missing |
| 2026-04-07 | 14.8 | None | None | wu_fetcher_missing |
| 2026-04-08 | 20.0 | None | None | wu_fetcher_missing |
| 2026-04-09 | 12.3 | None | None | wu_fetcher_missing |
| 2026-04-10 | 23.5 | None | None | wu_fetcher_missing |
| 2026-04-11 | 20.9 | None | None | wu_fetcher_missing |
| 2026-04-12 | 25.2 | None | None | wu_fetcher_missing |
| 2026-04-13 | 17.8 | None | None | wu_fetcher_missing |
| 2026-04-14 | 17.5 | None | None | wu_fetcher_missing |
| 2026-04-15 | 23.2 | None | None | wu_fetcher_missing |
| 2026-04-16 | 20.1 | None | None | wu_fetcher_missing |
| 2026-04-17 | 21.2 | None | None | wu_fetcher_missing |
| 2026-04-18 | 25.0 | None | None | wu_fetcher_missing |
| 2026-04-19 | 22.2 | None | None | wu_fetcher_missing |
| 2026-04-20 | 21.9 | None | None | wu_fetcher_missing |
| 2026-04-21 | 25.3 | None | None | wu_fetcher_missing |
| 2026-04-22 | 22.4 | None | None | wu_fetcher_missing |
| 2026-04-23 | 23.9 | None | None | wu_fetcher_missing |
| 2026-04-24 | 24.8 | None | None | wu_fetcher_missing |
| 2026-04-25 | 27.3 | None | None | wu_fetcher_missing |
| 2026-04-26 | 24.5 | None | None | wu_fetcher_missing |
| 2026-04-27 | 22.0 | None | None | wu_fetcher_missing |
| 2026-04-28 | 20.0 | None | None | wu_fetcher_missing |
| 2026-04-29 | 23.3 | None | None | wu_fetcher_missing |
| 2026-04-30 | 27.2 | None | None | wu_fetcher_missing |
| 2026-05-01 | 26.5 | None | None | wu_fetcher_missing |
| 2026-05-02 | 23.9 | None | None | wu_fetcher_missing |
| 2026-05-03 | 19.5 | None | None | wu_fetcher_missing |
| 2026-05-04 | 24.6 | None | None | wu_fetcher_missing |
| 2026-05-05 | 28.7 | None | None | wu_fetcher_missing |
| 2026-05-06 | 25.8 | None | None | wu_fetcher_missing |
| 2026-05-07 | 23.5 | None | None | wu_fetcher_missing |
| 2026-05-08 | 26.8 | None | None | wu_fetcher_missing |
| 2026-05-09 | 22.1 | None | None | wu_fetcher_missing |
| 2026-05-10 | 32.5 | None | None | wu_fetcher_missing |
| 2026-05-11 | 30.1 | None | None | wu_fetcher_missing |
| 2026-05-12 | 32.1 | None | None | wu_fetcher_missing |
| 2026-05-13 | 34.5 | None | None | wu_fetcher_missing |
| 2026-05-14 | 32.0 | None | None | wu_fetcher_missing |
| 2026-05-15 | 29.0 | None | None | wu_fetcher_missing |
| 2026-05-16 | 24.4 | None | None | wu_fetcher_missing |

## Blocked Signals Days

| Date | Condition | Strike C | Outcome | WU high C | Expected From WU | Match | Trader | Consensus |
|---|---|---:|---|---:|---|---|---|---|
| 2026-04-18 | exact | 26.0 | No | None | None | None | Entire-Hood | False |
| 2026-04-18 | exact | 27.0 | Yes | None | None | None | Entire-Hood | False |

## Pass/Fail

`WU_FETCHER_MISSING`. This dossier remains LOG_ONLY and requires Opus review before any operational next step.

## Next Trigger For Opus

Provide a reliable WU/ZBAA daily-high dataset or repo-approved WU fetcher, rerun this tool, and ask Opus to review the parity dossier only if the Opus criteria are met.
