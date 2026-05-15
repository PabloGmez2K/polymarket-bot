# Source Fidelity Resolver - Shanghai

Generated: `2026-05-15T06:27:24+00:00`

Verdict: `SOURCE_MATCH_CONFIRMED`

> LOG_ONLY / human review only. This package is read-only and does not authorize trading actions, policy edits, city-mode changes, automation, bankroll changes, promotion gates, observed-audit inclusion, or Phase C.

## Scope

- Classification: `NORMAL / LOG_ONLY`.
- Human review is required before any operational interpretation.
- WRH/weather.gov and NOAA NCEI are separate datasets and are not treated as equivalent.

## Local Evidence

- City evidence rows: `3`
- Slugs: `5`
- Market IDs: `0`
- Condition IDs: `0`
- Outcomes: `{'No': 3}`

## Source Comparison

- Internal source types: `['noaa_ncei', 'wunderground']`
- External source types: `['wunderground']`
- External WRH sites: `[]`
- Internal ICAO: `ZSPD`
- Internal WRH site: `None`
- WRH/NCEI separation: `separate_not_equivalent`

Reasons:
- `wunderground_source_text_matches_internal_wu_url`

## Internal Mapping

- ICAO: `ZSPD`
- Weather.gov WRH site: `None`
- NOAA station ID: `58321199999`
- NOAA daily station ID: `CHM00058362`
- WU URL: `https://www.wunderground.com/history/daily/ZSPD/date/{date}`
- Station label: `Pudong`

## Market Identifiers

- `highest-temperature-in-shanghai-on-may-15-2026-20corbelow`
- `highest-temperature-in-shanghai-on-may-15-2026-30corhigher`
- `highest-temperature-in-shanghai-on-may-16-2026-21corbelow`
- `highest-temperature-in-shanghai-on-may-16-2026-31corhigher`
- `lowest-temperature-in-shanghai-on-may-15-2026-14corbelow`

## Gamma Source Hints

- Gamma fetched: `True`
- Gamma markets parsed: `5`
- types=`['wunderground']` wrh_sites=`[]` station=``
- types=`['wunderground']` wrh_sites=`[]` station=``
- types=`['wunderground']` wrh_sites=`[]` station=``
- types=`['wunderground']` wrh_sites=`[]` station=``
- types=`['wunderground']` wrh_sites=`[]` station=``

## Limitations

- v0 is read-only and does not update runtime rows or bot mappings.
- Gamma lookup is optional; without --fetch-gamma the resolver uses local evidence and existing source-audit docs only.
- Source text parsing is heuristic and requires human review before any operational interpretation.
- WRH/weather.gov and NOAA NCEI datasets are reported as separate and not interchangeable.

## Warnings

- `missing jsonl: C:\Projects\polymarket-bot\data\blocked_signals_resolutions.jsonl`
