# METAR Measurement Layer

METAR/AviationWeather is approved only as a LOG_ONLY experimental measurement layer for selected Weather Underground/ICAO cities. It is useful evidence because Polymarket settlement pages cite Weather Underground airport histories, but it is not independent truth: METAR is probably an upstream-equivalent observation feed for WU at ICAO stations.

## Methodology

`tools/metar_shadow_fetch.py` fetches read-only AviationWeather METAR observations for one ICAO/date, reconstructs the local-day observed temperatures, and derives `tmax_c`/`tmin_c` only when coverage is materially complete. If coverage is thin, the output status is `insufficient_metar_coverage` and no TMAX/TMIN is invented.

`tools/metar_parity_report.py` reads those local LOG_ONLY files plus optional WU, Gamma-derived settlement, and Open-Meteo CSV inputs. It reports rolling METAR-vs-WU deltas, coverage, informational METAR-vs-Open-Meteo deltas, per-city/per-station operational readout, and JSON alert rows that can be reviewed manually or consumed by a future digest. It does not connect to runtime, Telegram, schedulers, or promotion gates.

The separate Resolution Verification Layer is `tools/metar_resolution_verify.py`.
It asks a narrower question: whether official Polymarket/Gamma outcomes would
have matched hypothetical METAR/AviationWeather outcomes for already-resolved
markets. It consumes `blocked_signals_resolutions.jsonl` plus local METAR
snapshots and remains LOG_ONLY; it is not part of measurement coverage, parity,
runtime trading, source policy, or promotion gates.

## Wave 1 Mapping

| City | ICAO station(s) | Status |
|---|---|---|
| Beijing | ZBAA | Wave 1 |
| Shanghai | ZSPD, ZSSS | Wave 1 |
| Tokyo | RJTT, RJAA | Wave 1 |
| Jeddah | OEJN | Wave 1 |
| Buenos Aires | SABE, SAEZ | Wave 1 |
| Ankara | LTAC | Wave 1 |
| Chongqing | ZUCK | Wave 1 |

Lucknow is outside Wave 1 until it has at least 30 comparable observations. Any city without an ICAO matched to the market sensor is outside scope.

## Wave 2 Mapping

Wave 2 is a LOG_ONLY coverage expansion for canary WU/ICAO gaps identified in
the METAR Coverage & Candidate Expansion Audit. It keeps Wave 1 intact and only
adds manual station metadata to `tools/metar_shadow_fetch.py`, so each station
can be fetched with the existing `--icao` workflow.

| City | ICAO station(s) | Status | Reason |
|---|---|---|---|
| Seoul | RKSI | Wave 2 | Canary WU/ICAO coverage gap |
| Singapore | WSSS | Wave 2 | Canary WU/ICAO coverage gap |
| Toronto | CYYZ | Wave 2 | Canary WU/ICAO coverage gap |
| Wellington | NZWN | Wave 2 | Canary WU/ICAO coverage gap |
| Madrid | LEMD | Wave 2 | Canary WU/ICAO coverage gap |
| Milan | LIMC | Wave 2 | Canary WU/ICAO coverage gap |
| Munich | EDDM | Wave 2 | Canary WU/ICAO coverage gap |

Wave 2 does not authorize trading, promotion, BANKROLL changes, Fase C, Truth
Pipeline changes, env vars, DB writes, scheduler wiring, Telegram runtime
wiring, whitelist changes, or city mode changes. Alerts from Wave 2 remain
manual LOG_ONLY review rows only.

Source-audit queue remains separate and is not Wave 2: Amsterdam, Wuhan, Busan,
Jakarta, and Kuala Lumpur require source-audit work before direct METAR
monitoring expansion.

## What LOG_ONLY Does

- Collects local JSON files under `data/metar_shadow/`.
- Preserves raw METAR text, timestamps, parsed temperatures, coverage, and derived TMAX/TMIN when coverage is sufficient.
- Produces Markdown/CSV reports for measurement-layer review.
- Emits only informational LOG_ONLY alert rows such as `A_METAR_PARITY_DRIFT`, `A_METAR_COVERAGE_GAP`, `A_METAR_VS_OM_DELTA`, and `LUCKNOW_COMPARABLE_DAYS_WATCH`.

## What LOG_ONLY Does Not Do

- No runtime integration.
- No promotion, whitelist, canary, active, or city mode changes.
- No scheduler hooks.
- No DB writes or env vars.
- No BUY/SELL/SKIP.
- No BANKROLL or Fase C.
- No Truth Pipeline.
- No canonical source change.
- No ranking_rows change.
- No replacement for Open-Meteo yet.

## Future Criteria

Before any separate review, each city/station needs:

- rolling n >= 30 comparable days
- median `|METAR-WU|` <= 0.3C
- max `|METAR-WU|` <= 1.0C
- coverage >= 80%

Meeting those criteria would still only justify human review. It would not automatically authorize trading, promotion, runtime integration, or canonical status.

## Future Alarms

- `A_METAR_PARITY_DRIFT`
- `A_METAR_COVERAGE_GAP`
- `A_METAR_VS_OM_DELTA`
- Lucknow comparable-days watch (track until rolling n>=30)

## Promotion Impact

METAR Measurement Layer is evidence input only. It does not auto-promote.

- Any WU/ICAO `exact` city requires source parity / METAR evidence accumulated under this layer before canary or active promotion review.
- Beijing remains blocked by Open-Meteo divergence (Lucknow KDAL-style bug pattern) but is a candidate for unblock review via METAR parity once thresholds in [Future Criteria](#future-criteria) are met.
- Jeddah needs shadow >=10 cycles AND METAR parity evidence before any Opus promotion review can be requested.
- Wave 1 stations: Beijing, Shanghai, Tokyo, Jeddah, Buenos Aires, Ankara, Chongqing.
- Wave 2 stations: Seoul, Singapore, Toronto, Wellington, Madrid, Milan, Munich.
- Lucknow is out of scope until rolling n>=30 comparable-day observations exist.
- Meeting Future Criteria authorizes human review only, never automatic trading, canary, active, whitelist, or canonical-source change.

## Manual Weekly Tracking

Operational cadence is a manual weekly run. There is no scheduler hook.

Outputs:
- `data/metar_shadow/<ICAO>_<YYYY-MM-DD>.json` (LOG_ONLY, gitignored)
- `data/metar_shadow_report.csv` / `data/metar_shadow_report.json` (LOG_ONLY, gitignored)
- Markdown report via `--md-out` (default `docs/source_audits/metar_measurement_layer_report.md`)

What to inspect each run:
- coverage % per station
- coverage % per city
- parity status per city/station
- median and max `|METAR-WU|` delta
- count of rows with `|delta| >= 1C`
- METAR vs Open-Meteo informational delta
- any `insufficient_metar_coverage` rows
- LOG_ONLY alerts: `A_METAR_PARITY_DRIFT`, `A_METAR_COVERAGE_GAP`, `A_METAR_VS_OM_DELTA`, `LUCKNOW_COMPARABLE_DAYS_WATCH`
- warnings emitted by `metar_shadow_fetch.py` or `metar_parity_report.py`

If WU CSV is not yet supplied, the report verdict will surface `METAR_PARITY_INSUFFICIENT_DATA`. That is expected, not a failure.

## Daily Digest Readout

The existing daily Telegram summary reads the latest
`data/metar_shadow_report.json` only. It does not fetch METAR, does not run
`tools/metar_parity_report.py`, and does not add a scheduler. Refresh remains a
manual trigger:

1. Run `tools/metar_shadow_fetch.py` for the selected station/date set.
2. Run `tools/metar_parity_report.py` to refresh
   `data/metar_shadow_report.json`.
3. Let the next existing daily summary display the compact METAR LOG_ONLY block.

The digest distinguishes a real `A_METAR_COVERAGE_GAP` from an incomplete
station-local day. If a station date has insufficient METAR rows but the local
day has not closed yet, the report marks `WAITING_LOCAL_DAY_CLOSE` and does not
emit `A_METAR_COVERAGE_GAP`. The Toronto/CYYZ 2026-05-17 case is the reference:
hours 0..16 while Toronto local day was still open is waiting, not a coverage
gap; CYYZ 2026-05-16 with hours 0..23 is coverage OK.

## What Stays Prohibited

This layer never authorizes:

- Substituting Open-Meteo in runtime.
- Changing city modes, whitelist, or canary/active membership.
- Automatic promotion of any kind.
- BUY/SELL/SKIP decisions.
- BANKROLL changes or Fase C transitions.
- Truth Pipeline modifications or canonical source swap.
- Scheduler integration or runtime hook.

## Next Codex Task (future, not active)

Pending Opus decision before activation:

- Integrate the METAR LOG_ONLY parity report block into the existing manual / weekly digest or Telegram summary as informational-only content.
- No scheduler wiring until Opus reviews enough Wave 1 data and explicitly approves.
