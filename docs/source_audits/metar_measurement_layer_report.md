# METAR Measurement Layer Report

Generated: `2026-05-17T22:21:44+00:00`

**Verdict:** **METAR_PARITY_INSUFFICIENT_DATA**

> LOG_ONLY METAR/AviationWeather measurement-layer report. This does not authorize runtime integration, promotion, scheduler changes, env vars, DB writes, BUY/SELL/SKIP, BANKROLL, Fase C, Truth Pipeline, or canonical source changes.

## Metrics

| Metric | Value |
|---|---:|
| n rows | 19 |
| n compared METAR-WU | 0 |
| coverage pct | 94.7 |
| median abs METAR-WU delta C | None |
| max abs METAR-WU delta C | None |
| pct abs METAR-WU delta >= 1C | None |
| median abs METAR-Open-Meteo delta C | None |
| max abs METAR-Open-Meteo delta C | None |

## Operational Readout

### By Wave

| Wave | Stations | Rows | Coverage | Real gaps | Waiting local close | Coverage status | Parity status counts |
|---|---:|---:|---:|---:|---:|---|---|
| Wave 1 | 10/10 | 11 | 100.0 | 0 | 0 | COVERAGE_HEALTHY | {'WAITING_WU_OR_GAMMA': 10} |
| Wave 2 | 7/7 | 8 | 87.5 | 0 | 1 | WAITING_LOCAL_DAY_CLOSE | {'WAITING_LOCAL_DAY_CLOSE': 1, 'WAITING_WU_OR_GAMMA': 6} |

### By City

| City | Stations | Coverage | Compared | Max METAR-WU | Max METAR-OM | Real gaps | Waiting local close | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Ankara | LTAC | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Beijing | ZBAA | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Buenos Aires | SABE, SAEZ | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Chongqing | ZUCK | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Jeddah | OEJN | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Madrid | LEMD | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Milan | LIMC | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Munich | EDDM | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Seoul | RKSI | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Shanghai | ZSPD, ZSSS | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Singapore | WSSS | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Tokyo | RJAA, RJTT | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Toronto | CYYZ | 50.0 | 0 | None | None | 0 | 1 | WAITING_LOCAL_DAY_CLOSE |
| Wellington | NZWN | 100.0 | 0 | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |

### By Station

| City | ICAO | Coverage | Compared | Median METAR-WU | Max METAR-WU | Max METAR-OM | Real gaps | Waiting local close | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Ankara | LTAC | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Beijing | ZBAA | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Buenos Aires | SABE | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Buenos Aires | SAEZ | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Chongqing | ZUCK | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Jeddah | OEJN | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Madrid | LEMD | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Milan | LIMC | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Munich | EDDM | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Seoul | RKSI | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Shanghai | ZSPD | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Shanghai | ZSSS | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Singapore | WSSS | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Tokyo | RJAA | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Tokyo | RJTT | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |
| Toronto | CYYZ | 50.0 | 0 | None | None | None | 0 | 1 | WAITING_LOCAL_DAY_CLOSE |
| Wellington | NZWN | 100.0 | 0 | None | None | None | 0 | 0 | WAITING_WU_OR_GAMMA |

### LOG_ONLY Alerts

- `LUCKNOW_COMPARABLE_DAYS_WATCH` Lucknow: Lucknow comparable-days watch: n=0/30; outside Wave 1 until threshold is met.

## Future Criteria

- rolling n >= 30
- median abs METAR-WU delta <= 0.3C
- max abs METAR-WU delta <= 1.0C
- coverage >= 80.0%

Reasons:
- n_compared_metar_wu=0 < 30
- median_abs_metar_wu_delta_c=None
- max_abs_metar_wu_delta_c=None

## Rows

| City | ICAO | Date | METAR | WU/Gamma | Delta | Coverage | Coverage status | Open-Meteo | METAR-OM | Status |
|---|---|---|---:|---:|---:|---|---|---:|---:|---|
| Toronto | CYYZ | 2026-05-16 | 21.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Toronto | CYYZ | 2026-05-17 | None | None | None | False | waiting_local_day_close | None | None | missing_wu_or_metar |
| Munich | EDDM | 2026-05-17 | 16.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Madrid | LEMD | 2026-05-17 | 22.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Milan | LIMC | 2026-05-17 | 21.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Ankara | LTAC | 2026-05-16 | 20.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Wellington | NZWN | 2026-05-17 | 14.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Jeddah | OEJN | 2026-05-16 | 40.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Tokyo | RJAA | 2026-05-16 | 24.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Tokyo | RJTT | 2026-05-16 | 25.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Seoul | RKSI | 2026-05-17 | 25.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Buenos Aires | SABE | 2026-05-16 | 16.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Buenos Aires | SAEZ | 2026-05-16 | 14.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Singapore | WSSS | 2026-05-17 | 32.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Beijing | ZBAA | 2026-05-13 | 28.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Beijing | ZBAA | 2026-05-16 | 22.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Shanghai | ZSPD | 2026-05-16 | 26.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Shanghai | ZSSS | 2026-05-16 | 29.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |
| Chongqing | ZUCK | 2026-05-16 | 22.0 | None | None | True | coverage_ok | None | None | missing_wu_or_metar |

## Guardrail

This report is informational only. It does not write runtime state, does not change rankings or gates, and does not promote METAR to canonical or trading use.
