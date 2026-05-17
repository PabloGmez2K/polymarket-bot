# Measurement Layer Prior Art Addendum — 2026-05-17

**Mode:** LOG_ONLY research addendum.  
**Scope:** strategic validation before pushing `5343b3f Add source parity audit framework`.  
**Authority:** no trading action, no city mode change, no whitelist, no env vars, no
DB writes, no scheduler change, no Truth Pipeline, no Fase C, no BUY/SELL/SKIP.

## Executive Verdict

**Recommendation:** `KEEP_FRAMEWORK_AS_NEW` + `BUILD_METAR_VISUALCROSSING_RESEARCH_SPIKE`.

`tools/source_parity_audit.py` is new enough to keep as a standalone
measurement-layer gate. It overlaps with existing source/settlement tooling in
inputs and vocabulary, but not in its core job: measuring whether the bot's
Open-Meteo daily max matches Polymarket's settlement source for exact markets.

The practical unlock is not another source-text audit. Source text tells us
Polymarket settles Beijing on `WU/ZBAA`; it does not give the settled daily max
without either WU data or a station-equivalent observation layer. The most
realistic next spike is a read-only station-observation comparator using:

1. Aviation Weather METAR for recent station observations.
2. Visual Crossing historical station data for backfill / post-resolution
   validation.
3. Gamma-derived exact settlement as the label when WU direct data is absent.

Do **not** promote Beijing/Jeddah on Open-Meteo or source text alone.

## Part A — Internal Novelty Review

| Tool / doc | What it already does | What it does not do | Relationship to `source_parity_audit.py` |
|---|---|---|---|
| `tools/forecast_accuracy_audit.py` | Audits forecast accuracy and NOAA observed proxy coverage; has explicit ICAO-only proxy audit cases. | Does not compare Open-Meteo against WU/ICAO settlement highs or Gamma-derived exact settlement. | Adjacent measurement audit, not duplicate. |
| `tools/settlement_fidelity_probe.py` | Read-only probe for active/past markets: Open-Meteo forecast, NOAA observed proxy where available, Gamma/market metadata. Its doc says WU forecast/status remains pending. | Does not infer exact settlement from Gamma slugs and does not issue source parity PASS/FAIL criteria for promotion gates. | Upstream exploratory probe; parity framework is a stricter dossier layer. |
| `tools/source_fidelity_resolver.py` | Parses Gamma/source text and compares external settlement source type/ICAO/WRH/WU mentions against internal mapping. Separates WRH and NCEI as non-equivalent datasets. | Confirms "what source is named", not whether bot measurement matches the named source numerically. | Complementary. Source fidelity must pass before parity, but does not replace parity. |
| Istanbul WRH tools: `tools/weather_gov_wrh_client.py`, `tools/wrh_polymarket_parity_report.py`, `docs/source_audits/istanbul_wrh_parity_report.md` | Fetches WRH/Synoptic station data for a known WRH site, compares exact outcomes for Istanbul, and keeps WRH separate from NOAA/NCEI. | City-specific WRH path; not WU/ICAO generic; outcome parity rather than Open-Meteo-vs-settlement delta framework. | Good pattern to reuse later for station fetchers, but not a replacement. |
| Active city source fidelity docs | Confirm Gamma source text for active cities, usually WU/ICAO, and compare to internal WU/NOAA fields. | Do not prove Open-Meteo/NOAA proxy parity against settlement source. | Evidence input, not parity gate. |
| `tools/source_parity_audit.py` | Generic LOG_ONLY dossier: Open-Meteo archive vs WU CSV if provided; Gamma-derived exact settlement; median/max/% delta metrics; PASS/FAIL/INSUFFICIENT verdicts; no bot import. | Does not yet fetch WU directly or provide an alternative station-observed daily high. | New measurement-layer gate. Keep standalone for now. |

### Duplication / Merge Assessment

No immediate merge recommended.

- Merging into `source_fidelity_resolver.py` would mix two different questions:
  "what source settles the market?" vs. "does our measurement match that source?"
- Merging into `settlement_fidelity_probe.py` would bury a promotion gate inside
  a broader exploratory probe.
- Istanbul WRH code is useful prior art for a future station fetcher interface,
  but its weather.gov/WRH/Synoptic path is not WU/ZBAA.

**Name and location:** correct. `tools/source_parity_audit.py` belongs under
`tools/` as a manual LOG_ONLY audit tool; dossiers belong under
`docs/source_audits/`. If future station fetchers proliferate, the next
abstraction should be shared helper modules, not a tool rename.

## Part B — External Prior Art

| Repo / source | Forecast layer | Observed / settlement layer | Distinguishes forecast vs settlement? | WU/ICAO solution? | Notes |
|---|---|---|---|---|---|
| `suislanchez/polymarket-kalshi-weather-bot` | Open-Meteo 31-member GFS ensemble for probabilities. README lists Open-Meteo GFS ensemble as weather source. | NWS API observed temperatures for settlement; code has station IDs like `KNYC`, `KORD`, `KMIA`, `KLAX`, `KDEN`. Settlement code reads Polymarket outcome prices for market resolution. | Partially: forecast via Open-Meteo, observed via NWS/API and Polymarket resolution. | No WU-specific resolver found; US-airport/NWS oriented. | Useful pattern: station-level NWS observations, but not enough for Beijing/ZBAA. Sources: GitHub README and raw `backend/data/weather.py`. |
| `Tsukamg/polymarket-weather-trading-engine` | README says 3 forecast sources: ECMWF global, HRRR/GFS for US, and METAR airport reality checks. APIs list Open-Meteo, Aviation Weather METAR, Gamma, Visual Crossing. | README explicitly says Polymarket resolves on airport METAR stations and uses Visual Crossing for historical temps / resolution helpers. | Yes, at least conceptually: forecast/model layer plus METAR "reality checks" and Visual Crossing post-game temps. | Strongest public hint for our problem: airport station mapping + METAR + Visual Crossing, though not direct WU. | Best prior-art match for a research spike. |
| `MusicBoiyzzz/Polymarket-Weather-Bot` | README/about says NWS forecast scans. | README is mostly a Windows download wrapper; no transparent settlement layer in visible docs. | Not enough evidence. | No. | Treat as low-confidence prior art; do not copy. |
| `MoonsatProtocol/Polymarket-Weather-Bot` | NWS gridpoint hourly forecasts; raw `src/nws.ts` merges NWS forecast and recent station observations into daily max. | NWS station observations using station IDs `KLGA`, `KORD`, `KMIA`, `KDAL`, `KSEA`, `KATL`; strategy matches forecast temp to Polymarket bucket. | Yes for US NWS station path, but implementation blends observed/forecast in one daily max map. | No WU-specific resolver; US-station NWS only. | Useful station-observation design, not global enough for Beijing/Jeddah. |
| `erickdronski/kalshi-polymarket-trader` | README says 7 NWP model ensemble: NBM, GFS, ECMWF, ICON, NAM, HRRR, RAP plus NWS/NOAA official forecasts and bias correction. | Pass 3 pulls actual station temperatures from NWS; CLV and calibration are tracked post-settlement. Scripts are private. | Yes, architecturally. | No visible WU/ICAO implementation. | Confirms serious weather bots use live station observations as late-stage veto/exit evidence. |
| `yangyuan-zhen/PolyWeather` | README describes a production weather-intelligence stack; city decision cards use METAR, DEB, model cluster, and AI airport read before mapping to Polymarket buckets. | Mentions settlement sources/history in docs center, but exact resolver code was not audited in this addendum. | Yes conceptually: station/airport read vs market buckets. | Unknown for WU direct; likely station-centric. | Relevant design signal, not enough to import claims. |
| PolymarketWeather public article | Describes public bots: Open-Meteo GFS ensemble for `suislanchez`; Visual Crossing for `alteregoeth-ai/weatherbot`; multi-source PolyWeather including METAR/TAF, Open-Meteo, regional agencies, NOAA. | Secondary source, not code. | Yes in narrative. | Mentions station-level coordinates and multi-source systems, not WU direct. | Useful map of ecosystem, but lower authority than repo code. |

External pattern: public weather bots mostly optimize **forecast probability** and
**airport/station observation**, not WU scraping. The better designs separate
city-center forecasts from station observations and add veto/late-read layers.
None of the reviewed public repos provides a clean WU/ZBAA historical daily-high
solution we can safely adopt as-is.

## Part C — Measurement Layer Unlock Options

| Option | Source | Runtime viable? | Backtest viable? | Risk | External dependency | Implementation cost | Can unlock Beijing/Jeddah/ICAO-WU? |
|---|---|---:|---:|---|---|---|---|
| 1. Open-Meteo current | Open-Meteo archive/forecast at lat/lon | Yes | Yes | High for exact WU/ICAO; Beijing already failed parity | Free Open-Meteo | Already built | No for Beijing; maybe only for cities with proven parity PASS |
| 2. Gamma-derived settlement historical | Resolved exact markets via Gamma outcome prices and slugs | No for live pre-settlement; yes after resolution | Yes, for exact markets with enough unique dates | Medium: sparse markets, exact-only, slug assumptions, cannot approve live measurement alone | Gamma API | Low/medium, already in framework | Helps detect blockers; can validate historical parity; does not provide live observed source |
| 3. CSV manual WU | Human/exported WU daily highs | No | Yes | Medium: manual, provenance/format drift, not scalable | Human + WU page/export | Low | Can unblock one-off dossiers if data is trustworthy |
| 4. WU-direct fetcher | Weather Underground daily history page/internal data | Maybe, but fragile | Yes if stable | High: no supported public WU historical API; scraping/API drift and ToS risk | WU website/private endpoints | Medium/high | Potentially exact settlement match, but operationally brittle |
| 5. Aviation Weather / METAR station observations | AviationWeather Data API METAR, station info, cache files | Yes for recent observations; docs say prior 15 days | Limited to recent window unless separately archived | Medium: METAR is hourly/recent, daily max reconstruction must handle time zones and missing obs | NOAA AviationWeather, free | Medium | Strong candidate for Jeddah/OEJN and many ICAO stations; Beijing/ZBAA depends on global METAR availability and archive window |
| 6. Visual Crossing historical station data | Visual Crossing Timeline API, station-backed historical obs with `stations`, `source`, `tempmax` | Yes with key | Yes | Medium: commercial interpolation/weighting may not equal WU station high unless constrained by station settings | Visual Crossing API key/quota | Medium | Best practical backtest/live-historical candidate; must parity-check vs Gamma/WU before trusting |
| 7. Meteostat / NOAA ISD when exists | Meteostat station hourly/daily; NOAA ISD/GHCND | Runtime no for immediate live; historical yes | Yes | Medium/high outside US where 2026 gaps exist; Meteostat may model-fill gaps | Meteostat/NOAA | Medium | Useful where station data exists; Beijing/Jeddah currently known to have NOAA gaps in our repo context |
| 8. Multi-source consensus / veto layer | Open-Meteo + METAR/AviationWeather + Visual Crossing + Gamma-derived labels | Yes after components exist | Yes | Medium: more moving parts; must avoid false confidence from correlated sources | Mixed | High | Best long-term unlock: promote only when sources agree or when parity dossier passes |

## Recommended Next Task

Build a **LOG_ONLY station parity research spike**, not a trading integration:

`tools/station_observation_parity_spike.py`

Minimum behavior:

1. Inputs: `--city`, `--icao`, `--lat`, `--lon`, `--tz`, `--dates-csv` or
   `--blocked-jsonl`, `--source aviationweather|visualcrossing`.
2. For AviationWeather: fetch recent METAR observations for an ICAO station and
   compute local-day max temperature with explicit timezone handling.
3. For Visual Crossing: fetch `tempmax`, `source`, and `stations` for the same
   date/station/coordinates; record whether the requested ICAO appears in
   station metadata.
4. Compare against Gamma-derived exact settlement labels where available.
5. Output JSON ignored under `data/source_audits/` and MD under
   `docs/source_audits/`.
6. Keep all copy LOG_ONLY and explicitly forbid promotion/trading.

Pilot order:

1. Beijing/ZBAA: can Visual Crossing or METAR reproduce the Gamma-derived WU
   settlement dates within Opus thresholds?
2. Jeddah/OEJN: enough exact dates are not available locally yet, but use the
   same spike to test whether station observations can produce plausible daily
   highs and whether future Gamma labels can validate them.
3. One active WU/NOAA city with known source text (Tokyo/RJTT or Shanghai/ZSPD)
   as a sanity control.

Success criterion for the spike: identify one station-backed provider that
matches Gamma-derived WU settlement on Beijing materially better than
Open-Meteo. If none does, Beijing stays blocked and exact ICAO/WU promotions
must wait for WU-direct/manual data.

## Sources Reviewed

- `suislanchez/polymarket-kalshi-weather-bot` README and raw code:
  https://github.com/suislanchez/polymarket-kalshi-weather-bot,
  https://raw.githubusercontent.com/suislanchez/polymarket-kalshi-weather-bot/main/backend/data/weather.py,
  https://raw.githubusercontent.com/suislanchez/polymarket-kalshi-weather-bot/main/backend/core/settlement.py
- `Tsukamg/polymarket-weather-trading-engine` README:
  https://github.com/Tsukamg/polymarket-weather-trading-engine
- `MusicBoiyzzz/Polymarket-Weather-Bot` README:
  https://github.com/MusicBoiyzzz/Polymarket-Weather-Bot
- `MoonsatProtocol/Polymarket-Weather-Bot` README and raw code:
  https://github.com/MoonsatProtocol/Polymarket-Weather-Bot,
  https://raw.githubusercontent.com/MoonsatProtocol/Polymarket-Weather-Bot/main/src/nws.ts,
  https://raw.githubusercontent.com/MoonsatProtocol/Polymarket-Weather-Bot/main/src/strategy.ts
- `erickdronski/kalshi-polymarket-trader` README:
  https://github.com/erickdronski/kalshi-polymarket-trader
- `yangyuan-zhen/PolyWeather` README:
  https://github.com/yangyuan-zhen/PolyWeather
- AviationWeather Data API docs:
  https://www.connect.aviationweather.gov/data/api/
- Visual Crossing Timeline Weather API docs:
  https://www2.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/
- Meteostat Python hourly docs:
  https://dev.meteostat.net/python/hourly
- Weather Underground API historical caveat:
  https://en.wikipedia.org/wiki/Weather_Underground_(weather_service)

