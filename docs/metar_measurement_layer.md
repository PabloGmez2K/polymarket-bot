# METAR Measurement Layer

METAR/AviationWeather is approved only as a LOG_ONLY experimental measurement layer for selected Weather Underground/ICAO cities. It is useful evidence because Polymarket settlement pages cite Weather Underground airport histories, but it is not independent truth: METAR is probably an upstream-equivalent observation feed for WU at ICAO stations.

## Methodology

`tools/metar_shadow_fetch.py` fetches read-only AviationWeather METAR observations for one ICAO/date, reconstructs the local-day observed temperatures, and derives `tmax_c`/`tmin_c` only when coverage is materially complete. If coverage is thin, the output status is `insufficient_metar_coverage` and no TMAX/TMIN is invented.

`tools/metar_parity_report.py` reads those local LOG_ONLY files plus optional WU, Gamma-derived settlement, and Open-Meteo CSV inputs. It reports rolling METAR-vs-WU deltas, coverage, and informational METAR-vs-Open-Meteo deltas. It does not connect to runtime or promotion gates.

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

## What LOG_ONLY Does

- Collects local JSON files under `data/metar_shadow/`.
- Preserves raw METAR text, timestamps, parsed temperatures, coverage, and derived TMAX/TMIN when coverage is sufficient.
- Produces Markdown/CSV reports for measurement-layer review.
- Emits only informational labels such as `A_METAR_PARITY_DRIFT`, `A_METAR_COVERAGE_GAP`, and `A_METAR_VS_OM_DELTA` for future monitoring design.

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
