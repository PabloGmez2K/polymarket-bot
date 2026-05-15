# Source Fidelity Resolver - Istanbul

Generated: `2026-05-15T06:19:45+00:00`

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
- Outcomes: `{'Yes': 1, 'No': 2}`

## Source Comparison

- Internal source types: `['weather_gov_wrh', 'wunderground']`
- External source types: `['noaa', 'weather_gov_wrh']`
- External WRH sites: `['LTFM']`
- Internal ICAO: `LTFM`
- Internal WRH site: `LTFM`
- WRH/NCEI separation: `separate_not_equivalent`

Reasons:
- `weather_gov_wrh_site_matches:LTFM`

## Internal Mapping

- ICAO: `LTFM`
- Weather.gov WRH site: `LTFM`
- NOAA station ID: `None`
- NOAA daily station ID: `None`
- WU URL: `https://www.wunderground.com/history/daily/LTFM/date/{date}`
- Station label: `Istanbul Airport`

## Market Identifiers

- `highest-temperature-in-istanbul-on-may-13-2026-23c`
- `highest-temperature-in-istanbul-on-may-6-2026-17c`
- `highest-temperature-in-istanbul-on-may-6-2026-20c`
- `highest-temperature-in-istanbul-on-may-7-2026-22c`
- `highest-temperature-in-istanbul-on-may-7-2026-23c`

## Gamma Source Hints

- Gamma fetched: `False`
- Gamma markets parsed: `0`
- types=`['noaa', 'weather_gov_wrh']` wrh_sites=`['LTFM']` station=`Istanbul Airport`

## Limitations

- v0 is read-only and does not update runtime rows or bot mappings.
- Gamma lookup is optional; without --fetch-gamma the resolver uses local evidence and existing source-audit docs only.
- Source text parsing is heuristic and requires human review before any operational interpretation.
- WRH/weather.gov and NOAA NCEI datasets are reported as separate and not interchangeable.

## Warnings

- `missing jsonl: C:\Projects\polymarket-bot\data\blocked_signals_resolutions.jsonl`
