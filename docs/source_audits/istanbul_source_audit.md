# Istanbul Source Audit Package

Generated: 2026-05-14

Status: `SOURCE_CONFIRMED_LTFM / APPROVE_WRH_ONLY_AS_SHADOW_SOURCE`

> LOG_ONLY human review package. This package does not authorize execution,
> policy edits, city-mode changes, automation, bankroll changes, or Phase C.

## Scope

This package captures the runtime evidence that made Istanbul a City Intelligence
candidate, the Polymarket source metadata now confirmed for recent markets, and
the technical source-support review still required before any later
observed-audit decision.

No runtime data was copied into this repo. Evidence below is summarized from
read-only Railway checks against `/app/data` on 2026-05-14.

## Verdict

`SOURCE_CONFIRMED_LTFM / APPROVE_WRH_ONLY_AS_SHADOW_SOURCE`

Istanbul has strong trader/resolution evidence, mature shadow evidence, and
Polymarket Gamma API metadata confirming the intended source as NOAA at
Istanbul Airport via `weather.gov/wrh/timeseries?site=LTFM`.

This does not authorize city-mode changes, policy changes, trading decisions,
bankroll changes, Phase C, active/canary promotion, observed-audit inclusion, or
promotion gates. Opus verdict: WRH/weather.gov timeseries is not approved as a
primary source equivalent to NCEI. It is approved only as a separate shadow
source when Polymarket explicitly cites
`weather.gov/wrh/timeseries?site=<ICAO>`.

## Runtime Trader Evidence

Source: `/app/data/intelligence/traders_operational_questions_report.json`

- `generated_at`: `2026-05-14T20:00:43+00:00`
- `blocked_resolutions`: `/app/data/blocked_signals_resolutions.jsonl`
- Istanbul in `trader_winning_not_observed`:
  - `trader_wins`: `22`
  - `trader_n`: `22`
  - `trader_wr_pct`: `100.0`
  - `observed_by_us`: `false`
- Istanbul in `trader_winning_bot_gap`:
  - `classification`: `TRADER_WINNING_BOT_INSUFFICIENT_N`
  - `trader_wins`: `22`
  - `trader_n`: `22`
  - `bot_n`: `0`

Source: `/app/data/blocked_signals_resolutions.jsonl`

- Istanbul rows: `22`
- `resolved=true`: `22`
- `win_for_trader=true`: `22`
- Note: the `22` also matches shadow `markets_seen`, but the trader WR sample is
  sourced from blocked resolved rows, not from shadow counters.

## Shadow Evidence

Source: `/app/data/runtime_import/shadow_city_tracking.json`

- `markets_seen`: `22`
- `edge_hits`: `7`
- `cycles_seen`: `12`
- `best_edge_pct`: `37.9`
- `best_ev`: `2.17`
- `last_seen_at`: `2026-05-12T08:01:18.912211+00:00`
- `last_question`: `Will the highest temperature in Istanbul be 26°C on May 12?`
- `last_side`: `FILTERED`

## Policy State

Runtime snapshot evidence:

- `ACTIVE_TRADING_CITIES`: `Shanghai,Tokyo,Buenos Aires,Ankara`
- `CANARY_TRADING_CITIES`: not set
- `BLOCKED_CITIES`: `London,Paris,Atlanta,Chicago`
- Istanbul was not present in current inspected `auto_canary_cities`,
  `auto_shadow_cities`, or `auto_blocked_cities`.
- Runtime report marks `observed_by_us=false`.

Local source reference:

- Istanbul is not in local `OBSERVED_AUDIT_CITIES`.
- Istanbul is present in local source mappings as an ICAO/WU source candidate.

## Current Source Mapping

Source: `bot.py`

- City: `Istanbul`
- Station name: `Istanbul Airport`
- ICAO: `LTFM`
- Latitude: `41.2622`
- Longitude: `28.7278`
- WU URL template: `https://www.wunderground.com/history/daily/LTFM/date/{date}`
- Timezone: `Europe/Istanbul`

Missing source fields:

- `noaa_station_id`: absent
- `noaa_daily_station_id`: absent

WRH metadata:

- `weather_gov_timeseries_site`: `LTFM`
- `observed_dataset`: `weather_gov_wrh_timeseries` for any future WRH shadow
  records.
- This metadata is not currently consumed by runtime.

Existing local comment notes Istanbul/LTFM as ICAO-only and states LTFM is absent
from the NOAA ISD history used by the system. Treat this as local historical
context, not as final manual source verification.

## Polymarket Gamma API Evidence

Lookup method:

- `GET https://gamma-api.polymarket.com/markets/slug/<slug>`
- The older `GET /markets?slug=<slug>` pattern returned no rows for these
  closed Istanbul markets during the read-only check.

Confirmed slugs:

- `highest-temperature-in-istanbul-on-may-6-2026-20c`
- `highest-temperature-in-istanbul-on-may-6-2026-17c`
- `highest-temperature-in-istanbul-on-may-7-2026-22c`
- `highest-temperature-in-istanbul-on-may-7-2026-23c`
- `highest-temperature-in-istanbul-on-may-13-2026-23c`

All five market descriptions confirm the same resolution source pattern:

- Source authority: `NOAA`
- Station/source name: `Istanbul Airport`
- Source URL: `https://www.weather.gov/wrh/timeseries?site=LTFM`
- Data field: highest reading under the `Temp` column
- Unit handling: switch the table to metric units so it displays degrees Celsius
- Precision: whole degrees Celsius

Relevant source wording from the market metadata:

> This market will resolve to the temperature range that contains the highest
> temperature recorded by NOAA at the Istanbul Airport

> The resolution source for this market will be information from NOAA,
> specifically the highest reading under the `Temp` column

Event metadata also references Istanbul Airport / `LTFM`; for example, the May 6
event notes `NOAA Istanbul Airport (LTFM) readings`, and the May 7 event says
`Official NOAA observations at Istanbul Airport`.

## Source And Settlement Risk

Risk: `low source identity / medium technical support / promotion not approved`

Reasons:

- Polymarket source identity is now confirmed as NOAA at Istanbul Airport via
  `site=LTFM`.
- WRH/weather.gov timeseries is approved only as a distinct shadow dataset,
  `weather_gov_wrh_timeseries`; it must not be mixed with NCEI.
- WRH is not a primary equivalent to NCEI and does not feed ranking, promotion
  gates, city modes, BUY/SELL/SKIP, active/canary eligibility, or
  `OBSERVED_AUDIT_CITIES`.
- The current local mapping still lacks `noaa_station_id` and
  `noaa_daily_station_id`, so the existing observed-audit path must not treat
  WRH as the current NOAA/NCEI station-id contract.
- Runtime blocked rows still carry `settlement_source=unknown` and
  `settlement_fidelity_status=unverified`; the Gamma API evidence resolves the
  source lookup question but does not update runtime row metadata retroactively.
- Local mapping uses a WU URL template for `LTFM`, while Polymarket rules cite
  `weather.gov/wrh/timeseries?site=LTFM`; this difference must be reviewed
  before any observed-audit patch.

## WRH Shadow Source Contract

Approved scope:

- WRH may be stored only as a separate shadow source when a Polymarket market
  explicitly cites `weather.gov/wrh/timeseries?site=<ICAO>`.
- For Istanbul, the explicit site is `LTFM`, the station label is Istanbul
  Airport, and the source column is `Temp`.
- Future WRH observations must carry
  `observed_dataset=weather_gov_wrh_timeseries`.

Not approved:

- No primary-source equivalence with NCEI.
- No mixing WRH rows into NCEI observed datasets.
- No ranking, promotion gates, city modes, active/canary changes,
  BUY/SELL/SKIP changes, or `OBSERVED_AUDIT_CITIES` changes from this verdict.

Re-evaluation criteria:

- `N >= 20` resolved Istanbul markets with observed WRH values recorded.
- Mean absolute delta `|Delta C| <= 0.5` against settlement outcomes.
- No directional bias greater than `0.3 C`.
- Aggregation rule documented for how WRH hourly `Temp` maps to market
  settlement.
- At least one second candidate city with explicit WRH source evidence.

## Required Manual Confirmation

Before Istanbul can be promoted from this package to an observed-audit candidate,
a technical source-support audit should confirm:

- Whether the system can query `weather.gov/wrh/timeseries?site=LTFM` directly
  and extract finalized hourly `Temp` values in Celsius.
- Whether a valid `noaa_station_id` or `noaa_daily_station_id` exists. If not,
  document Istanbul as an explicit `weather.gov`/ICAO source case and require a
  separate human decision before observed-audit inclusion.
- Whether observed-audit tooling can distinguish `weather.gov site=LTFM` from
  the current NOAA station-id contract without weakening existing source
  fidelity checks.
- Whether recent resolved rows settle consistently with the confirmed
  `weather.gov/wrh/timeseries?site=LTFM` source.

## Recommended Next Step

Implementing a future WRH fetcher or observed-audit comparator requires a
separate reviewed patch. This package only records the source decision and the
metadata contract for Istanbul.

Do not change city mode, environment variables, trading settings, promotion
gates, `OBSERVED_AUDIT_CITIES`, or runtime data handling from this package
alone.
