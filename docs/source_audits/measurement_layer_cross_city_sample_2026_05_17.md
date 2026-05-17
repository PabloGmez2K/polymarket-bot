# Measurement Layer Cross-City METAR Sample

Generated: `2026-05-17T18:37:23+00:00`

**Overall verdict:** **METAR_CROSS_CITY_PROMISING**

> LOG_ONLY research dossier. This does not authorize BUY/SELL/SKIP, whitelist, canary/active promotion, city mode changes, scheduler changes, env vars, DB writes, BANKROLL changes, Fase C, or Truth Pipeline activation.

## Objective

Expand the Beijing METAR/AviationWeather spike across existing WU/ICAO cities and compare recent METAR local-day highs against Gamma-derived exact settlement labels.

This sample is for deciding whether METAR deserves a LOG_ONLY implementation workstream. It does not unlock Beijing directly; Beijing still needs its own minimum threshold or continued monitoring.

## Method

- Candidate cities: `Beijing, Jeddah, Shanghai, Tokyo, Buenos Aires, Ankara, Lucknow, Chongqing`
- Date window: `2026-05-03` through `2026-05-16`
- Gamma exact slug sweep: Open-Meteo daily max center +/- `8C`
- METAR source: AviationWeather `/api/data/metar`, local-day max from `temp` at each ICAO
- Settlement label accepted only when Gamma source includes Weather Underground and the expected ICAO, and exactly one exact market resolves YES for that date.

## Aggregate Metrics

| Metric | Value |
|---|---:|
| n total | 58 |
| median abs delta C | 0.0 |
| max abs delta C | 0.0 |
| pct abs delta >= 1C | 0.0 |
| pct abs delta >= 2C | 0.0 |

## Cities Audited

| City | ICAO | Candidate class | Source fidelity | Gamma dates | METAR n | Median | Max | >=1C | >=2C | Pass/Fail | Notes |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Beijing | ZBAA | wu_icao_candidate | NO_SOURCE_FIDELITY_DOC | 10 | 4 | 0.0 | 0.0 | 0.0 | 0.0 | PASS_RECENT_PROMISING | METAR_RECENT_ONLY |
| Jeddah | OEJN | wu_icao_candidate | NO_SOURCE_FIDELITY_DOC | 10 | 10 | 0.0 | 0.0 | 0.0 | 0.0 | PASS_RECENT_PROMISING | METAR_RECENT_ONLY |
| Shanghai | ZSPD | source_fidelity_confirmed | SOURCE_MATCH_CONFIRMED | 14 | 7 | 0.0 | 0.0 | 0.0 | 0.0 | PASS_RECENT_PROMISING | METAR_RECENT_ONLY; NOAA ids present but not used |
| Tokyo | RJTT | source_fidelity_confirmed | SOURCE_MATCH_CONFIRMED | 9 | 4 | 0.0 | 0.0 | 0.0 | 0.0 | PASS_RECENT_PROMISING | METAR_RECENT_ONLY; NOAA ids present but not used |
| Buenos Aires | SAEZ | source_fidelity_confirmed | SOURCE_MATCH_CONFIRMED | 13 | 13 | 0.0 | 0.0 | 0.0 | 0.0 | PASS_RECENT_PROMISING | METAR_RECENT_ONLY; NOAA ids present but not used |
| Ankara | LTAC | source_fidelity_confirmed | SOURCE_MATCH_CONFIRMED | 12 | 7 | 0.0 | 0.0 | 0.0 | 0.0 | PASS_RECENT_PROMISING | METAR_RECENT_ONLY; NOAA ids present but not used |
| Lucknow | VILK | wu_icao_candidate | NO_SOURCE_FIDELITY_DOC | 0 | 0 | None | None | None | None | METAR_INSUFFICIENT_HISTORY | INSUFFICIENT_METAR_HISTORY |
| Chongqing | ZUCK | wu_icao_candidate | NO_SOURCE_FIDELITY_DOC | 13 | 13 | 0.0 | 0.0 | 0.0 | 0.0 | PASS_RECENT_PROMISING | METAR_RECENT_ONLY |

## Day-Level Comparisons

### Beijing / ZBAA

- WU URL template: `https://www.wunderground.com/history/daily/{country}/{city}/ZBAA`
- Source fidelity: `NO_SOURCE_FIDELITY_DOC`
- Verdict: `PASS_RECENT_PROMISING`

| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-05-03 | 22.0 | None | None | 19.5 | 9 | `highest-temperature-in-beijing-on-may-3-2026-22c` | METAR_RECENT_ONLY |
| 2026-05-04 | 26.0 | None | None | 24.6 | 9 | `highest-temperature-in-beijing-on-may-4-2026-26c` | METAR_RECENT_ONLY |
| 2026-05-05 | 30.0 | None | None | 28.7 | 9 | `highest-temperature-in-beijing-on-may-5-2026-30c` | METAR_RECENT_ONLY |
| 2026-05-06 | 26.0 | None | None | 25.8 | 9 | `highest-temperature-in-beijing-on-may-6-2026-26c` | METAR_RECENT_ONLY |
| 2026-05-07 | 25.0 | None | None | 23.5 | 9 | `highest-temperature-in-beijing-on-may-7-2026-25c` | METAR_RECENT_ONLY |
| 2026-05-08 | 28.0 | None | None | 26.8 | 9 | `highest-temperature-in-beijing-on-may-8-2026-28c` | METAR_RECENT_ONLY |
| 2026-05-10 | 33.0 | 33.0 | 0.0 | 32.5 | 9 | `highest-temperature-in-beijing-on-may-10-2026-33c` | compared |
| 2026-05-11 | 31.0 | 31.0 | 0.0 | 30.1 | 9 | `highest-temperature-in-beijing-on-may-11-2026-31c` | compared |
| 2026-05-12 | 33.0 | 33.0 | 0.0 | 32.1 | 9 | `highest-temperature-in-beijing-on-may-12-2026-33c` | compared |
| 2026-05-13 | 33.0 | 33.0 | 0.0 | 34.5 | 9 | `highest-temperature-in-beijing-on-may-13-2026-33c` | compared |

Warnings:
- Beijing/ZBAA: missing METAR local-day highs for 2026-05-03, 2026-05-04, 2026-05-05, 2026-05-06, 2026-05-07, 2026-05-08

### Jeddah / OEJN

- WU URL template: `https://www.wunderground.com/history/daily/{country}/{city}/OEJN`
- Source fidelity: `NO_SOURCE_FIDELITY_DOC`
- Verdict: `PASS_RECENT_PROMISING`

| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-05-05 | 35.0 | 35.0 | 0.0 | 34.4 | 9 | `highest-temperature-in-jeddah-on-may-5-2026-35c` | compared |
| 2026-05-06 | 34.0 | 34.0 | 0.0 | 33.0 | 9 | `highest-temperature-in-jeddah-on-may-6-2026-34c` | compared |
| 2026-05-07 | 34.0 | 34.0 | 0.0 | 34.3 | 9 | `highest-temperature-in-jeddah-on-may-7-2026-34c` | compared |
| 2026-05-08 | 34.0 | 34.0 | 0.0 | 35.0 | 9 | `highest-temperature-in-jeddah-on-may-8-2026-34c` | compared |
| 2026-05-09 | 35.0 | 35.0 | 0.0 | 36.6 | 9 | `highest-temperature-in-jeddah-on-may-9-2026-35c` | compared |
| 2026-05-10 | 34.0 | 34.0 | 0.0 | 36.2 | 9 | `highest-temperature-in-jeddah-on-may-10-2026-34c` | compared |
| 2026-05-11 | 34.0 | 34.0 | 0.0 | 36.3 | 9 | `highest-temperature-in-jeddah-on-may-11-2026-34c` | compared |
| 2026-05-12 | 37.0 | 37.0 | 0.0 | 38.0 | 9 | `highest-temperature-in-jeddah-on-may-12-2026-37c` | compared |
| 2026-05-13 | 37.0 | 37.0 | 0.0 | 35.7 | 9 | `highest-temperature-in-jeddah-on-may-13-2026-37c` | compared |
| 2026-05-14 | 39.0 | 39.0 | 0.0 | 38.4 | 9 | `highest-temperature-in-jeddah-on-may-14-2026-39c` | compared |

### Shanghai / ZSPD

- WU URL template: `https://www.wunderground.com/history/daily/{country}/{city}/ZSPD`
- Source fidelity: `SOURCE_MATCH_CONFIRMED`
- Verdict: `PASS_RECENT_PROMISING`

| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-05-03 | 22.0 | None | None | 21.0 | 9 | `highest-temperature-in-shanghai-on-may-3-2026-22c` | METAR_RECENT_ONLY |
| 2026-05-04 | 24.0 | None | None | 23.0 | 9 | `highest-temperature-in-shanghai-on-may-4-2026-24c` | METAR_RECENT_ONLY |
| 2026-05-05 | 27.0 | None | None | 24.6 | 9 | `highest-temperature-in-shanghai-on-may-5-2026-27c` | METAR_RECENT_ONLY |
| 2026-05-06 | 25.0 | None | None | 23.6 | 9 | `highest-temperature-in-shanghai-on-may-6-2026-25c` | METAR_RECENT_ONLY |
| 2026-05-07 | 30.0 | None | None | 27.4 | 9 | `highest-temperature-in-shanghai-on-may-7-2026-30c` | METAR_RECENT_ONLY |
| 2026-05-08 | 19.0 | None | None | 18.3 | 9 | `highest-temperature-in-shanghai-on-may-8-2026-19c` | METAR_RECENT_ONLY |
| 2026-05-09 | 23.0 | None | None | 21.7 | 9 | `highest-temperature-in-shanghai-on-may-9-2026-23c` | METAR_RECENT_ONLY |
| 2026-05-10 | 24.0 | 24.0 | 0.0 | 23.4 | 9 | `highest-temperature-in-shanghai-on-may-10-2026-24c` | compared |
| 2026-05-11 | 29.0 | 29.0 | 0.0 | 26.7 | 9 | `highest-temperature-in-shanghai-on-may-11-2026-29c` | compared |
| 2026-05-12 | 28.0 | 28.0 | 0.0 | 28.4 | 9 | `highest-temperature-in-shanghai-on-may-12-2026-28c` | compared |
| 2026-05-13 | 26.0 | 26.0 | 0.0 | 24.4 | 9 | `highest-temperature-in-shanghai-on-may-13-2026-26c` | compared |
| 2026-05-14 | 24.0 | 24.0 | 0.0 | 24.8 | 9 | `highest-temperature-in-shanghai-on-may-14-2026-24c` | compared |
| 2026-05-15 | 24.0 | 24.0 | 0.0 | 23.9 | 9 | `highest-temperature-in-shanghai-on-may-15-2026-24c` | compared |
| 2026-05-16 | 26.0 | 26.0 | 0.0 | 25.0 | 9 | `highest-temperature-in-shanghai-on-may-16-2026-26c` | compared |

Warnings:
- Shanghai/ZSPD: incomplete METAR coverage for 2026-05-09 (obs=9, local_hours=19..23)
- Shanghai/ZSPD: missing METAR local-day highs for 2026-05-03, 2026-05-04, 2026-05-05, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-09

### Tokyo / RJTT

- WU URL template: `https://www.wunderground.com/history/daily/{country}/{city}/RJTT`
- Source fidelity: `SOURCE_MATCH_CONFIRMED`
- Verdict: `PASS_RECENT_PROMISING`

| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-05-03 | 23.0 | None | None | 22.3 | 9 | `highest-temperature-in-tokyo-on-may-3-2026-23c` | METAR_RECENT_ONLY |
| 2026-05-05 | 22.0 | None | None | 20.9 | 9 | `highest-temperature-in-tokyo-on-may-5-2026-22c` | METAR_RECENT_ONLY |
| 2026-05-06 | 22.0 | None | None | 20.6 | 9 | `highest-temperature-in-tokyo-on-may-6-2026-22c` | METAR_RECENT_ONLY |
| 2026-05-08 | 26.0 | None | None | 25.0 | 9 | `highest-temperature-in-tokyo-on-may-8-2026-26c` | METAR_RECENT_ONLY |
| 2026-05-09 | 23.0 | None | None | 24.2 | 9 | `highest-temperature-in-tokyo-on-may-9-2026-23c` | METAR_RECENT_ONLY |
| 2026-05-11 | 24.0 | 24.0 | 0.0 | 23.8 | 9 | `highest-temperature-in-tokyo-on-may-11-2026-24c` | compared |
| 2026-05-14 | 24.0 | 24.0 | 0.0 | 24.3 | 9 | `highest-temperature-in-tokyo-on-may-14-2026-24c` | compared |
| 2026-05-15 | 22.0 | 22.0 | 0.0 | 22.0 | 9 | `highest-temperature-in-tokyo-on-may-15-2026-22c` | compared |
| 2026-05-16 | 25.0 | 25.0 | 0.0 | 23.8 | 9 | `highest-temperature-in-tokyo-on-may-16-2026-25c` | compared |

Warnings:
- Tokyo/RJTT: incomplete METAR coverage for 2026-05-09 (obs=9, local_hours=19..23)
- Tokyo/RJTT: missing METAR local-day highs for 2026-05-03, 2026-05-05, 2026-05-06, 2026-05-08, 2026-05-09

### Buenos Aires / SAEZ

- WU URL template: `https://www.wunderground.com/history/daily/{country}/{city}/SAEZ`
- Source fidelity: `SOURCE_MATCH_CONFIRMED`
- Verdict: `PASS_RECENT_PROMISING`

| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-05-03 | 17.0 | 17.0 | 0.0 | 16.9 | 9 | `highest-temperature-in-buenos-aires-on-may-3-2026-17c` | compared |
| 2026-05-04 | 22.0 | 22.0 | 0.0 | 20.9 | 9 | `highest-temperature-in-buenos-aires-on-may-4-2026-22c` | compared |
| 2026-05-05 | 24.0 | 24.0 | 0.0 | 23.4 | 9 | `highest-temperature-in-buenos-aires-on-may-5-2026-24c` | compared |
| 2026-05-07 | 21.0 | 21.0 | 0.0 | 19.9 | 9 | `highest-temperature-in-buenos-aires-on-may-7-2026-21c` | compared |
| 2026-05-08 | 13.0 | 13.0 | 0.0 | 12.7 | 9 | `highest-temperature-in-buenos-aires-on-may-8-2026-13c` | compared |
| 2026-05-09 | 13.0 | 13.0 | 0.0 | 12.2 | 9 | `highest-temperature-in-buenos-aires-on-may-9-2026-13c` | compared |
| 2026-05-10 | 16.0 | 16.0 | 0.0 | 14.8 | 9 | `highest-temperature-in-buenos-aires-on-may-10-2026-16c` | compared |
| 2026-05-11 | 17.0 | 17.0 | 0.0 | 16.5 | 9 | `highest-temperature-in-buenos-aires-on-may-11-2026-17c` | compared |
| 2026-05-12 | 22.0 | 22.0 | 0.0 | 20.6 | 9 | `highest-temperature-in-buenos-aires-on-may-12-2026-22c` | compared |
| 2026-05-13 | 15.0 | 15.0 | 0.0 | 14.6 | 9 | `highest-temperature-in-buenos-aires-on-may-13-2026-15c` | compared |
| 2026-05-14 | 17.0 | 17.0 | 0.0 | 16.0 | 9 | `highest-temperature-in-buenos-aires-on-may-14-2026-17c` | compared |
| 2026-05-15 | 18.0 | 18.0 | 0.0 | 17.3 | 9 | `highest-temperature-in-buenos-aires-on-may-15-2026-18c` | compared |
| 2026-05-16 | 14.0 | 14.0 | 0.0 | 13.7 | 9 | `highest-temperature-in-buenos-aires-on-may-16-2026-14c` | compared |

### Ankara / LTAC

- WU URL template: `https://www.wunderground.com/history/daily/{country}/{city}/LTAC`
- Source fidelity: `SOURCE_MATCH_CONFIRMED`
- Verdict: `PASS_RECENT_PROMISING`

| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-05-04 | 8.0 | None | None | 8.7 | 9 | `highest-temperature-in-ankara-on-may-4-2026-8c` | METAR_RECENT_ONLY |
| 2026-05-06 | 15.0 | None | None | 13.6 | 9 | `highest-temperature-in-ankara-on-may-6-2026-15c` | METAR_RECENT_ONLY |
| 2026-05-07 | 19.0 | None | None | 16.8 | 9 | `highest-temperature-in-ankara-on-may-7-2026-19c` | METAR_RECENT_ONLY |
| 2026-05-08 | 22.0 | None | None | 19.6 | 9 | `highest-temperature-in-ankara-on-may-8-2026-22c` | METAR_RECENT_ONLY |
| 2026-05-09 | 21.0 | None | None | 20.1 | 9 | `highest-temperature-in-ankara-on-may-9-2026-21c` | METAR_RECENT_ONLY |
| 2026-05-10 | 23.0 | 23.0 | 0.0 | 20.2 | 9 | `highest-temperature-in-ankara-on-may-10-2026-23c` | compared |
| 2026-05-11 | 22.0 | 22.0 | 0.0 | 19.7 | 9 | `highest-temperature-in-ankara-on-may-11-2026-22c` | compared |
| 2026-05-12 | 24.0 | 24.0 | 0.0 | 20.3 | 9 | `highest-temperature-in-ankara-on-may-12-2026-24c` | compared |
| 2026-05-13 | 22.0 | 22.0 | 0.0 | 20.3 | 9 | `highest-temperature-in-ankara-on-may-13-2026-22c` | compared |
| 2026-05-14 | 22.0 | 22.0 | 0.0 | 21.3 | 9 | `highest-temperature-in-ankara-on-may-14-2026-22c` | compared |
| 2026-05-15 | 17.0 | 17.0 | 0.0 | 15.2 | 9 | `highest-temperature-in-ankara-on-may-15-2026-17c` | compared |
| 2026-05-16 | 20.0 | 20.0 | 0.0 | 18.7 | 9 | `highest-temperature-in-ankara-on-may-16-2026-20c` | compared |

Warnings:
- Ankara/LTAC: missing METAR local-day highs for 2026-05-04, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-09

### Lucknow / VILK

- WU URL template: `https://www.wunderground.com/history/daily/{country}/{city}/VILK`
- Source fidelity: `NO_SOURCE_FIDELITY_DOC`
- Verdict: `METAR_INSUFFICIENT_HISTORY`

| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |
|---|---:|---:|---:|---:|---:|---|---|
| n/a |  |  |  |  |  |  | no comparable Gamma/METAR rows |

### Chongqing / ZUCK

- WU URL template: `https://www.wunderground.com/history/daily/{country}/{city}/ZUCK`
- Source fidelity: `NO_SOURCE_FIDELITY_DOC`
- Verdict: `PASS_RECENT_PROMISING`

| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-05-03 | 23.0 | 23.0 | 0.0 | 21.9 | 9 | `highest-temperature-in-chongqing-on-may-3-2026-23c` | compared |
| 2026-05-04 | 28.0 | 28.0 | 0.0 | 24.9 | 9 | `highest-temperature-in-chongqing-on-may-4-2026-28c` | compared |
| 2026-05-05 | 31.0 | 31.0 | 0.0 | 28.3 | 9 | `highest-temperature-in-chongqing-on-may-5-2026-31c` | compared |
| 2026-05-07 | 25.0 | 25.0 | 0.0 | 22.5 | 9 | `highest-temperature-in-chongqing-on-may-7-2026-25c` | compared |
| 2026-05-08 | 19.0 | 19.0 | 0.0 | 17.9 | 9 | `highest-temperature-in-chongqing-on-may-8-2026-19c` | compared |
| 2026-05-09 | 24.0 | 24.0 | 0.0 | 22.1 | 9 | `highest-temperature-in-chongqing-on-may-9-2026-24c` | compared |
| 2026-05-10 | 28.0 | 28.0 | 0.0 | 24.9 | 9 | `highest-temperature-in-chongqing-on-may-10-2026-28c` | compared |
| 2026-05-11 | 29.0 | 29.0 | 0.0 | 27.3 | 9 | `highest-temperature-in-chongqing-on-may-11-2026-29c` | compared |
| 2026-05-12 | 26.0 | 26.0 | 0.0 | 24.4 | 9 | `highest-temperature-in-chongqing-on-may-12-2026-26c` | compared |
| 2026-05-13 | 30.0 | 30.0 | 0.0 | 27.0 | 9 | `highest-temperature-in-chongqing-on-may-13-2026-30c` | compared |
| 2026-05-14 | 29.0 | 29.0 | 0.0 | 28.1 | 9 | `highest-temperature-in-chongqing-on-may-14-2026-29c` | compared |
| 2026-05-15 | 24.0 | 24.0 | 0.0 | 23.2 | 9 | `highest-temperature-in-chongqing-on-may-15-2026-24c` | compared |
| 2026-05-16 | 22.0 | 22.0 | 0.0 | 24.9 | 9 | `highest-temperature-in-chongqing-on-may-16-2026-22c` | compared |

## Conclusion

Verdict: `METAR_CROSS_CITY_PROMISING`.

METAR/AviationWeather deserves a dedicated LOG_ONLY implementation workstream: a standalone station-observation fetcher, cached local-day high reconstruction, and continued Gamma-derived validation by city.

This is not a Beijing unlock. Beijing remains governed by its own sample threshold/monitoring because the cross-city sample only tests whether the station-observation layer is worth productizing.

## Sources

- Local mappings: `bot.py` `RESOLUTION_ICAO`, `RESOLUTION_STATIONS`, `CITY_TIMEZONES`
- Local source-fidelity docs: `docs/source_audits/*_source_fidelity_resolver.md`
- Gamma market API: `https://gamma-api.polymarket.com/markets/slug/{slug}`
- AviationWeather METAR API: `https://aviationweather.gov/api/data/metar`
