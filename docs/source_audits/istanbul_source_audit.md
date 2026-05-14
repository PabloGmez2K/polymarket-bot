# Istanbul Source Audit Package

Generated: 2026-05-14

Status: `NEEDS_MANUAL_SOURCE_LOOKUP`

> LOG_ONLY human review package. This package does not authorize execution,
> policy edits, city-mode changes, automation, bankroll changes, or Phase C.

## Scope

This package captures the runtime evidence that made Istanbul a City Intelligence
candidate and the source metadata still missing before any later observed-audit
decision.

No runtime data was copied into this repo. Evidence below is summarized from
read-only Railway checks against `/app/data` on 2026-05-14.

## Verdict

`NEEDS_MANUAL_SOURCE_LOOKUP`

Istanbul has strong trader/resolution evidence and mature shadow evidence, but
the current source mapping is ICAO/WU-only. The package is not ready to support
an observed-audit decision until a human confirms the exact settlement source
and whether a valid NOAA station identifier exists or should remain explicitly
absent.

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

Existing local comment notes Istanbul/LTFM as ICAO-only and states LTFM is absent
from the NOAA ISD history used by the system. Treat this as local historical
context, not as final manual source verification.

## Source And Settlement Risk

Risk: `medium`

Reasons:

- The city has a plausible airport source (`LTFM`) and a WU daily-history URL.
- The current mapping lacks NOAA station IDs, so the observed-audit path cannot
  use the stronger NOAA station contract without a manual exception or explicit
  confirmation that no NOAA-compatible station exists.
- Runtime blocked rows have `settlement_source=unknown` and
  `settlement_fidelity_status=unverified` on newer Istanbul rows.
- Polymarket settlement source must be confirmed against market rules for
  Istanbul, especially whether the intended source is `LTFM`, WU `LTFM`, a NOAA
  weather.gov endpoint, or another named station/source.

## Required Manual Confirmation

Before Istanbul can be promoted from this package to an observed-audit candidate,
a human source audit should confirm:

- The exact Polymarket settlement source used for Istanbul temperature markets.
- Whether the settlement source is Istanbul Airport / `LTFM`.
- Whether the source exposes a stable daily high-temperature record compatible
  with the system's observed-audit process.
- Whether a valid `noaa_station_id` or `noaa_daily_station_id` exists. If not,
  document Istanbul as an explicit ICAO/WU-only case and require a separate
  human decision before observed-audit inclusion.
- Whether recent resolved rows settle consistently with the candidate source.

## Recommended Next Step

Prepare a manual source lookup for Istanbul/LTFM using the latest resolved
Polymarket market rules and source pages. If that lookup confirms the settlement
source and resolves the NOAA-ID absence, open a separate reviewed patch proposal
for source mapping or observed-audit handling.

Do not change city mode, environment variables, trading settings, or `bot.py`
from this package alone.
