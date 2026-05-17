# METAR Measurement Layer Report

Generated: `2026-05-17T18:56:43+00:00`

**Verdict:** **METAR_PARITY_WATCH_MORE_DATA**

> LOG_ONLY METAR/AviationWeather measurement-layer report. This does not authorize runtime integration, promotion, scheduler changes, env vars, DB writes, BUY/SELL/SKIP, BANKROLL, Fase C, Truth Pipeline, or canonical source changes.

## Metrics

| Metric | Value |
|---|---:|
| n rows | 1 |
| n compared METAR-WU | 1 |
| coverage pct | 100.0 |
| median abs METAR-WU delta C | 0.2 |
| max abs METAR-WU delta C | 0.2 |
| pct abs METAR-WU delta >= 1C | 0.0 |
| median abs METAR-Open-Meteo delta C | 0.4 |
| max abs METAR-Open-Meteo delta C | 0.4 |

## Future Criteria

- rolling n >= 30
- median abs METAR-WU delta <= 0.3C
- max abs METAR-WU delta <= 1.0C
- coverage >= 80.0%

Reasons:
- n_compared_metar_wu=1 < 30

## Rows

| City | ICAO | Date | METAR | WU/Gamma | Delta | Coverage | Open-Meteo | METAR-OM | Status |
|---|---|---|---:|---:|---:|---|---:|---:|---|
| Beijing | ZBAA | 2026-05-13 | 28.0 | 28.2 | -0.2 | True | 27.6 | 0.4 | compared |

## Guardrail

This report is informational only. It does not write runtime state, does not change rankings or gates, and does not promote METAR to canonical or trading use.
