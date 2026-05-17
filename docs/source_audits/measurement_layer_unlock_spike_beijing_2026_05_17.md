# Measurement Layer Unlock Spike: Beijing/ZBAA

Generated: `2026-05-17`

**Mode:** LOG_ONLY research spike.  
**Authority:** no trading, no city modes, no BANKROLL, no env vars, no DB writes,
no scheduler, no runtime integration, no fragile scraping, no push.

## Objective

Find whether any observed station-backed source reproduces Polymarket/Gamma
derived WU/ZBAA settlement for Beijing better than the current Open-Meteo
measurement layer.

Baseline dossier: `docs/source_audits/beijing_open_meteo_vs_wu_parity.md`.

## Source Table

| Source | Runtime availability | Backtest availability | Beijing/ZBAA evidence in this spike | Recommendation |
|---|---|---|---|---|
| Open-Meteo archive/current | Viable today; free API; already used by parity tool. | Viable today over historical windows. | Existing Gamma-derived Beijing dossier fails: 12 compared dates, median abs delta `1.05C`, max abs delta `3.0C`, `58.3%` abs delta >= `1C`. | **Descartar as unlock for Beijing exact WU/ZBAA**. Keep as forecast/proxy only unless a city-specific parity PASS exists. |
| AviationWeather / METAR | Viable for recent station reads. ZBAA is present as METAR/TAF station with `wmoId=54511`, `lat=40.082`, `lon=116.603`. | Limited. Official docs say up to previous 15 days, most endpoints max 400 entries; enough for recent post-resolution checks, not April-scale backtest by itself. | For 2026-05-10..13, METAR local-day max matched Gamma-derived WU/ZBAA exactly on all 4 checked dates. | **Viable for recent runtime/validation spike**, not sufficient alone for long backtest. Best immediate no-key candidate. |
| Visual Crossing historical station data | Viable only with API key/quota. Supports daily `tempmax`, `source`, historical `stations`, `maxStations`, `maxDistance`. | Viable with API key and station constraints; must verify ZBAA appears in `stations`. | Not executed: no API key in scope. Prior art and docs make it the strongest backfill candidate. | **Needs API key**. Test with `maxStations=1`, tight `maxDistance`, `elements=datetime,tempmax,source,stations`. |
| Gamma-derived exact settlement | Not runtime-pre-settlement. | Viable as post-resolution label for exact markets where one YES market can be inferred. | Existing dossier: Open-Meteo fails across April/May. New spot check found May 10..13 settlement labels `33,31,33,33C`. | **Viable as label only**. Use to score providers, not as measurement source. |
| WU direct/manual CSV | Runtime not recommended; WU direct scraping/API path is fragile. Manual CSV is one-off only. | Viable if a trustworthy human/exported WU daily-high CSV is provided. | No direct WU dataset available in repo; existing report is `WU_FETCHER_MISSING`. | **Manual only / no fragile scraping**. |
| Public-repo sources reviewed | Mostly Open-Meteo forecasts plus airport/station observation layers; Tsukamg mentions AviationWeather METAR and Visual Crossing; US-focused repos use NWS stations. | Design prior art only unless code/data is audited per provider. | No public repo reviewed supplies a clean WU/ZBAA historical fetcher. | **Use as design signal**, not as data source. |

## Gamma Comparison

Existing Beijing Open-Meteo vs Gamma-derived settlement:

| Metric | Open-Meteo vs Gamma |
|---|---:|
| Compared dates | 12 |
| Median delta C | -1.05 |
| Median abs delta C | 1.05 |
| Max abs delta C | 3.0 |
| Abs delta >= 1C | 58.3% |
| Abs delta >= 2C | 25.0% |
| Verdict | `SETTLEMENT_GAMMA_PARITY_FAIL` |

Recent AviationWeather/METAR spot check against Gamma-derived WU/ZBAA:

| Date | Gamma settlement C | Open-Meteo C | Open-Meteo delta | AviationWeather METAR max C | METAR delta | Notes |
|---|---:|---:|---:|---:|---:|---|
| 2026-05-10 | 33 | 32.5 | -0.5 | 33 | 0.0 | Gamma slugs 30C..36C found; 33C YES. |
| 2026-05-11 | 31 | 30.1 | -0.9 | 31 | 0.0 | Gamma slugs 29C..34C found; 31C YES. |
| 2026-05-12 | 33 | 32.1 | -0.9 | 33 | 0.0 | Gamma slugs 30C..36C found; 33C YES. |
| 2026-05-13 | 33 | 34.5 | +1.5 | 33 | 0.0 | Gamma slugs 33C..36C found; 33C YES. |

Spot-check metrics:

| Source | n | Median abs delta C | Max abs delta C | Abs delta >= 1C | Readout |
|---|---:|---:|---:|---:|---|
| Open-Meteo | 4 | 0.9 | 1.5 | 25.0% | Better on this window than April, but still not clean enough to override the full failure. |
| AviationWeather/METAR | 4 | 0.0 | 0.0 | 0.0% | Strong recent signal that ZBAA METAR may replicate WU/ZBAA daily highs. |

## Availability Notes

- AviationWeather Data API is official NOAA/AWC machine access. It lists METAR
  as worldwide terminal observations and states the database currently reaches
  up to the previous 15 days. It also documents rate limits and a maximum result
  size, so a runtime/backtest design must cache sparingly and not assume deep
  history.
- Visual Crossing Timeline API supports global historical weather, daily
  `tempmax`, `source`, and station metadata. It can constrain station selection
  via `maxStations` and `maxDistance`, but it requires an API key and must prove
  ZBAA is actually the contributing station.
- Open-Meteo `temperature_2m_max` is a 2m daily max aggregation at coordinates,
  not an airport station settlement source. Beijing already shows that this
  distinction matters.

## Recommendation

**Best unlock candidate:** `AviationWeather / METAR`, but only as a LOG_ONLY
station parity spike first. The May 10..13 result is the first evidence here
that a no-key observed station source can replicate Gamma-derived WU/ZBAA better
than Open-Meteo.

**Best backfill candidate:** `Visual Crossing`, pending API key. It is the
likely way to cover April/early May dates without fragile WU scraping, but it
must be constrained and audited so `ZBAA` appears in returned station metadata.

**Do not unlock Beijing operationally yet.** The METAR sample is only 4 dates,
recent-window only, and does not satisfy the `n >= 20` Gamma or `n >= 30` WU
parity threshold from the source parity framework.

## Next LOG_ONLY Step

Build or run a temporary `station_observation_parity_spike` that:

1. Reads Beijing Gamma-derived exact settlement labels.
2. Fetches AviationWeather METAR local-day max for dates inside the 15-day
   window.
3. Optionally fetches Visual Crossing with a provided key and station
   constraints.
4. Emits JSON under ignored `data/source_audits/` and Markdown under
   `docs/source_audits/`.

Success criterion for a future unlock dossier: one station-backed provider
matches Gamma-derived WU/ZBAA settlement materially better than Open-Meteo over
at least 20 exact settlement dates, or 30 direct WU/manual comparable dates.

## Sources

- Local baseline: `docs/source_audits/beijing_open_meteo_vs_wu_parity.md`
- Local prior art: `docs/source_audits/measurement_layer_prior_art_2026_05_17.md`
- AviationWeather Data API: https://www.connect.aviationweather.gov/data/api/
- Visual Crossing Timeline API: https://www2.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/
- Open-Meteo historical API: https://open-meteo.com/en/docs/historical-weather-api
