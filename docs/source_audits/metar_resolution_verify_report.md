# METAR Resolution Source Verification

Generated: `2026-05-18T08:46:59+00:00`

## Scope

LOG_ONLY METAR/AviationWeather resolution source verification. This compares official Polymarket/Gamma outcomes with hypothetical METAR-derived outcomes and does not authorize source policy changes, BUY/SELL/SKIP, promotion, scheduler changes, Telegram runtime alerts, env vars, DB writes, BANKROLL, Fase C, Truth Pipeline, whitelist, or city mode changes.

Question: If we had used METAR/AviationWeather as resolution source, would the official Polymarket/Gamma outcome have been the same?

## Gate

- Rows evaluated: 113
- Status counts: `{"NO_DATA": 73, "NO_SNAPSHOT": 40}`

## City States

| City | State | Compared | Match | Mismatch | Agree % | Median abs delta C | Max abs delta C | No snapshot | Insufficient | Unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Amsterdam | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Ankara | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 1 | 0 | 0 |
| Atlanta | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Beijing | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 2 | 0 | 0 |
| Buenos Aires | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 2 | 0 | 0 |
| Chengdu | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Chongqing | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 2 | 0 | 0 |
| Dallas | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Guangzhou | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Helsinki | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Hong Kong | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Houston | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Istanbul | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Jakarta | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Jeddah | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 4 | 0 | 0 |
| Karachi | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Kuala Lumpur | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| London | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Los Angeles | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Lucknow | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Madrid | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 4 | 0 | 0 |
| Miami | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Milan | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 3 | 0 | 0 |
| Moscow | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Munich | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 1 | 0 | 0 |
| New York City | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Paris | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| San Francisco | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Sao Paulo | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Seattle | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Seoul | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 4 | 0 | 0 |
| Shanghai | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 3 | 0 | 0 |
| Shenzhen | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Singapore | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 2 | 0 | 0 |
| Taipei | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Tel Aviv | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Tokyo | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 5 | 0 | 0 |
| Toronto | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 4 | 0 | 0 |
| Warsaw | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |
| Wellington | NO_SNAPSHOT | 0 | 0 | 0 | None | None | None | 3 | 0 | 0 |
| Wuhan | NO_DATA | 0 | 0 | 0 | None | None | None | 0 | 0 | 0 |

## Alerts

- None.

## Sample Rows

| City | Date | Condition | ICAO | Official | METAR | Status | Delta C | Reason |
|---|---:|---|---|---:|---:|---:|---:|---|
| Dallas | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Toronto | 2026-04-12 | exact | CYYZ | Yes | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Dallas | 2026-04-12 | range |  | Yes | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| New York City | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Seattle | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Toronto | 2026-04-12 | exact | CYYZ | No | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Sao Paulo | 2026-04-12 | exact |  | Yes | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Seattle | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Seattle | 2026-04-12 | range |  | Yes | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Madrid | 2026-04-12 | exact | LEMD | Yes | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Atlanta | 2026-04-12 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Moscow | 2026-04-12 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Ankara | 2026-04-08 | exact | LTAC | Yes | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Tokyo | 2026-04-10 | exact | RJAA,RJTT | No | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Tokyo | 2026-04-09 | exact | RJAA,RJTT | No | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Hong Kong | 2026-04-09 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Milan | 2026-04-08 | exact | LIMC | No | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Miami | 2026-04-08 | range |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Seoul | 2026-04-13 | exact | RKSI | No | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Shenzhen | 2026-04-13 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Wellington | 2026-04-13 | exact | NZWN | Yes | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Seoul | 2026-04-13 | exact | RKSI | No | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Seoul | 2026-04-13 | exact | RKSI | No | None | NO_SNAPSHOT | None | no_metar_file_for_city_date |
| Hong Kong | 2026-04-13 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |
| Taipei | 2026-04-13 | exact |  | No | None | NO_DATA | None | city_not_in_wave1_or_wave2_mapping |

## Operational Note

This report is evidence for manual review only. It does not change trading, DB, env vars, source policy, city modes, whitelist, scheduler, Telegram runtime, BANKROLL, Fase C, Truth Pipeline, or BUY/SELL/SKIP behavior.
