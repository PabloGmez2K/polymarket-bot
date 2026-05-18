# METAR Resolution Source Verification

Generated: `2026-05-18T10:28:14+00:00`

## Scope

LOG_ONLY METAR/AviationWeather resolution source verification. This compares official Polymarket/Gamma outcomes with hypothetical METAR-derived outcomes and does not authorize source policy changes, BUY/SELL/SKIP, promotion, scheduler changes, Telegram runtime alerts, env vars, DB writes, BANKROLL, Fase C, Truth Pipeline, whitelist, or city mode changes.

Question: If we had used METAR/AviationWeather as resolution source, would the official Polymarket/Gamma outcome have been the same?

## Gate

- Rows evaluated: 113
- Status counts: `{"MATCH": 34, "MISMATCH": 6, "NO_DATA": 73}`

## City States

| City | State | Compared | Match | Mismatch | Agree % | Median abs delta C | Max abs delta C | No snapshot | Insufficient | Unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Amsterdam | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Ankara | INSUFFICIENT_SAMPLE | 1 | 0 | 1 | 0.0 | 1.0 | 1.0 | 0 | 0 | 0 |
| Atlanta | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Beijing | INSUFFICIENT_SAMPLE | 2 | 2 | 0 | 100.0 | 0.5 | 1.0 | 0 | 0 | 0 |
| Buenos Aires | INSUFFICIENT_SAMPLE | 2 | 2 | 0 | 100.0 | 1.5 | 2.0 | 0 | 0 | 0 |
| Chengdu | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Chongqing | INSUFFICIENT_SAMPLE | 2 | 2 | 0 | 100.0 | 0.5 | 1.0 | 0 | 0 | 0 |
| Dallas | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Guangzhou | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Helsinki | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Hong Kong | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Houston | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Istanbul | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Jakarta | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Jeddah | INSUFFICIENT_SAMPLE | 4 | 4 | 0 | 100.0 | 2.5 | 5.0 | 0 | 0 | 0 |
| Karachi | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Kuala Lumpur | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| London | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Los Angeles | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Lucknow | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Madrid | INSUFFICIENT_SAMPLE | 4 | 3 | 1 | 75.0 | 0.5 | 0.9 | 0 | 0 | 0 |
| Miami | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Milan | INSUFFICIENT_SAMPLE | 3 | 2 | 1 | 66.67 | 1.1 | 2.1 | 0 | 0 | 0 |
| Moscow | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Munich | INSUFFICIENT_SAMPLE | 1 | 1 | 0 | 100.0 | 1.3 | 1.3 | 0 | 0 | 0 |
| New York City | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Paris | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| San Francisco | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Sao Paulo | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Seattle | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Seoul | INSUFFICIENT_SAMPLE | 4 | 3 | 1 | 75.0 | 1.0 | 2.0 | 0 | 0 | 0 |
| Shanghai | INSUFFICIENT_SAMPLE | 3 | 3 | 0 | 100.0 | 1.0 | 1.0 | 0 | 0 | 0 |
| Shenzhen | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Singapore | INSUFFICIENT_SAMPLE | 2 | 1 | 1 | 50.0 | 0.55 | 1.1 | 0 | 0 | 0 |
| Taipei | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Tel Aviv | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Tokyo | INSUFFICIENT_SAMPLE | 5 | 5 | 0 | 100.0 | 1.0 | 1.0 | 0 | 0 | 0 |
| Toronto | INSUFFICIENT_SAMPLE | 4 | 3 | 1 | 75.0 | 0.5 | 1.1 | 0 | 0 | 0 |
| Warsaw | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Wellington | INSUFFICIENT_SAMPLE | 3 | 3 | 0 | 100.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| Wuhan | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |

## Alerts

- None.

## Sample Rows

| City | Date | Condition | ICAO | Official | METAR | Status | Delta C | Reason |
|---|---:|---|---|---:|---:|---:|---:|---|
| Dallas | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Toronto | 2026-04-12 | exact | CYYZ | Yes | Yes | MATCH | -0.1 |  |
| Dallas | 2026-04-12 | range |  | Yes | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| New York City | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Seattle | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Toronto | 2026-04-12 | exact | CYYZ | No | No | MATCH | -1.1 |  |
| Sao Paulo | 2026-04-12 | exact |  | Yes | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Seattle | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Seattle | 2026-04-12 | range |  | Yes | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Madrid | 2026-04-12 | exact | LEMD | Yes | Yes | MATCH | -0.1 |  |
| Atlanta | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Moscow | 2026-04-12 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Ankara | 2026-04-08 | exact | LTAC | Yes | No | MISMATCH | 1.0 |  |
| Tokyo | 2026-04-10 | exact | RJTT | No | No | MATCH | 1.0 |  |
| Tokyo | 2026-04-09 | exact | RJAA | No | No | MATCH | -1.0 |  |
| Hong Kong | 2026-04-09 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Milan | 2026-04-08 | exact | LIMC | No | No | MATCH | -2.1 |  |
| Miami | 2026-04-08 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Seoul | 2026-04-13 | exact | RKSI | No | Yes | MISMATCH | 0.0 |  |
| Shenzhen | 2026-04-13 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Wellington | 2026-04-13 | exact | NZWN | Yes | Yes | MATCH | 0.0 |  |
| Seoul | 2026-04-13 | exact | RKSI | No | No | MATCH | -1.0 |  |
| Seoul | 2026-04-13 | exact | RKSI | No | No | MATCH | 1.0 |  |
| Hong Kong | 2026-04-13 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Taipei | 2026-04-13 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |

## Pilot Caveats — Mismatch Review (2026-05-18)

Visual Crossing backfill pilot: 26 snapshots generated (all `vc_source=obs`), 0 NO\_SNAPSHOT remaining.
Global result after backfill: **34 MATCH / 6 MISMATCH / 0 NO\_SNAPSHOT / 73 NO\_DATA**.
All cities with data remain `INSUFFICIENT_SAMPLE` (n < 20 each; SOURCE\_UNDER\_TEST requires n ≥ 20).
All 6 mismatches are on `condition=exact`. No mismatches on `at_or_above` or `at_or_below`.

### Mismatch classifications

| City | Date | ICAO | VC tmax | Threshold | Official | Delta C | Classification |
|---|---:|---|---:|---:|---:|---:|---|
| Ankara | 2026-04-08 | LTAC | 10.0 | 9°C | Yes | +1.0 | LIKELY_SOURCE_DIFFERENCE |
| Seoul | 2026-04-13 | RKSI | 20.0 | 20°C | No | 0.0 | LIKELY_SOURCE_DIFFERENCE |
| Toronto | 2026-04-13 | CYYZ | 21.1 | 21°C | No | +0.1 | POSSIBLE_MAPPING_ISSUE |
| Milan | 2026-04-13 | LIMC | 14.9 | 16°C | Yes | -1.1 | DATA_QUALITY (source JSONL) |
| Madrid | 2026-04-18 | LEMD | 27.9 | 28°C | No | -0.1 | SEMANTIC_EXACT_UNCERTAIN |
| Singapore | 2026-04-19 | WSSS | 31.9 | 33°C | Yes | -1.1 | LIKELY_SOURCE_DIFFERENCE |

### Notes per mismatch

- **Ankara**: VC aggregates 4 stations (incl. rural TUM\* stations) under rain; official source likely measured ~9°C at LTAC directly.
- **Seoul**: All four exact markets (19, 20, 21, 22°C) resolved No, implying official tmax was outside that range. VC 20.0°C differs from official source by ≥ 1°C.
- **Toronto**: `CYYZ` is absent from `vc_stations` — VC used nearby stations (AV116, CXTO, etc.), not the airport itself. Station mapping may differ from official source.
- **Milan**: Source JSONL row for `exact|16` has `outcome=Yes` but `close_price=0.0` (internally inconsistent — a Yes-token worth $0 implies No resolution). The mismatch is likely a data artifact; `exact|15=Yes` with VC tmax 14.9 → round(14.9)=15 is a MATCH.
- **Madrid**: `exact|27=No` AND `exact|28=No` simultaneously. Consistent only if official source reported a non-integer value (e.g., 27.9°C) and Polymarket resolved by strict integer equality, not `round()`. The verifier's `round(27.9)=28` assumption may overcount Yes for borderline `.9` values.
- **Singapore**: VC aggregates WSAP + WSSL + WSSS (3 stations) in rain; official source measured 33°C at WSSS directly. Multi-station tropical average suppressed the peak.

### Guard

This pilot does not authorize a source switch, source policy change, city mode change, whitelist update, or any trading/scheduler/Telegram/BANKROLL/Fase C/BUY/SELL/SKIP action.
Next step: accumulate n ≥ 20 per city before escalating to SOURCE\_UNDER\_TEST classification.

## Operational Note

This report is evidence for manual review only. It does not change trading, DB, env vars, source policy, city modes, whitelist, scheduler, Telegram runtime, BANKROLL, Fase C, Truth Pipeline, or BUY/SELL/SKIP behavior.
