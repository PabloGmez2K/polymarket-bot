# Ankara / Paris Unblock Review

- Date: `2026-04-12`
- Scope: read-only structural audit of `Ankara` and `Paris`
- Canonical rule used: `blocked` must mean structural source/resolution guardrail, not PnL history or tactical pause
- Current session preflight note: `python tools/system_alignment_check.py --decision-mode operational` was rerun at `2026-04-12T16:28:22+00:00` and returned `ok=6`, `warning=1`, `error=1` because `runtime_policy_effective_view` was `6.2h` old vs the `6.0h` SLO. This document remains read-only and uses the latest repo artifacts already available in `data/` and `docs/`.

## Verdict

| City | Verdict | Why |
| --- | --- | --- |
| Ankara | move to `shadow` | Current artifacts show NOAA configured, no documented forecast/settlement mismatch, no broken resolution mechanism, and `0` recent `blocked_city` rows in the latest `10` and `12` cycle windows. The remaining blocker is `market_visibility`, which is not a canonical reason for hard block. |
| Paris | move to `shadow` | Current artifacts show NOAA configured, no documented forecast/settlement mismatch, no broken resolution mechanism, and `0` recent `blocked_city` rows in the latest `10` and `12` cycle windows. The remaining blocker is `market_visibility`, which is not a canonical reason for hard block. |

## Current Manual Blocked Value

From `data/runtime_import/policy_env_snapshot.json` pulled at `2026-04-12T10:16:19.3168566+00:00`:

- Current `BLOCKED_CITIES`: `London,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`

If both `Ankara` and `Paris` move to `shadow`, the exact resulting value would be:

- Proposed `BLOCKED_CITIES`: `London,Tel Aviv,Wellington,Toronto,Madrid,Singapore`

## Evidence By Question

### Ankara

1. `noaa_station_id` in `RESOLUTION_ICAO`?
   Yes. `bot.py` declares `RESOLUTION_ICAO["Ankara"]` with:
   - `icao="LTAC"`
   - `noaa_station_id="17128099999"`
   - `noaa_daily_station_id="TUM00017130"`

2. Documented mismatch between forecast source and settlement source?
   No evidence found in current artifacts. `docs/blocked-cities-rationale-latest.md` says `London` is the only city with an explicit still-documented mismatch memo (`Weather Underground vs Open-Meteo`). No equivalent memo was found for `Ankara`.

3. Evidence that the resolution mechanism is broken or unvalidated?
   No direct evidence of a broken mechanism. The city-intelligence layer does not classify `Ankara` under `source_fidelity`; it classifies it as:
   - `docs/city_validation_ledger_latest.md`: `building`, `observe_with_source_caution`, bottleneck `market_visibility`
   - `docs/city_promotion_gate_latest.md`: `watch_closely`, bottleneck `market_visibility`
   - `data/city_validation_ledger.json`: `settlement_fidelity.score=3`, `risk=medium`, rationale `icao | wu_url | noaa_station`

4. Do recent `blocked_city` skips show real markets being suppressed, or is the bucket already `0`?
   The recent blocked bucket is already `0`.
   - Last `12` cycles in `data/runtime_import/skip_log.jsonl`: `0` `blocked_city` rows for `Ankara`, but `66` total Ankara rows across `2026-04-08T23:00`, `2026-04-09T16:00`, `2026-04-09T23:00`, `2026-04-10T08:00`, `2026-04-10T16:00`, `2026-04-10T23:00`
   - Last `10` cycles: `0` `blocked_city` rows, but `55` total Ankara rows across `2026-04-09T16:00`, `2026-04-09T23:00`, `2026-04-10T08:00`, `2026-04-10T16:00`, `2026-04-10T23:00`
   - `data/runtime_import/cycles_history.jsonl` also shows visible Ankara markets on `2026-04-07T23:00`, `2026-04-08T08:00`, and `2026-04-10T08:00`

5. Does the current block match a valid structural criterion, or does it look inherited from a historical loss audit?
   It looks inherited from the historical loss audit, not from a current structural memo.
   - `CONTEXTO.md` records that the 10-city block expansion came from the historical loss audit: `BLOCKED_CITIES` was expanded after a review of losses and WR (`Sesión 62`, line referencing `v10.5.12`)
   - `docs/blocked-cities-rationale-latest.md` classifies `Ankara` as `dudoso y candidato a revision futura`
   - Current artifacts keep pointing to `market_visibility`, not to mismatch, missing NOAA, or a broken resolution path

### Paris

1. `noaa_station_id` in `RESOLUTION_ICAO`?
   Yes. `bot.py` declares `RESOLUTION_ICAO["Paris"]` with:
   - `icao="LFPG"`
   - `noaa_station_id="07157099999"`
   - `noaa_daily_station_id="FRM00007149"`

2. Documented mismatch between forecast source and settlement source?
   No evidence found in current artifacts. `docs/blocked-cities-rationale-latest.md` says `London` is the only city with an explicit still-documented mismatch memo. No equivalent memo was found for `Paris`.

3. Evidence that the resolution mechanism is broken or unvalidated?
   No direct evidence of a broken mechanism. The city-intelligence layer does not classify `Paris` under `source_fidelity`; it classifies it as:
   - `docs/city_validation_ledger_latest.md`: `building`, `observe_with_source_caution`, bottleneck `market_visibility`
   - `docs/city_promotion_gate_latest.md`: `watch_closely`, bottleneck `market_visibility`
   - `data/city_validation_ledger.json`: `settlement_fidelity.score=3`, `risk=medium`, rationale `icao | wu_url | noaa_station`

4. Do recent `blocked_city` skips show real markets being suppressed, or is the bucket already `0`?
   The recent blocked bucket is already `0`.
   - Last `12` cycles in `data/runtime_import/skip_log.jsonl`: `0` `blocked_city` rows for `Paris`, but `121` total Paris rows across `2026-04-08T23:00`, `2026-04-09T08:00`, `2026-04-09T23:00`, `2026-04-10T08:00`, `2026-04-10T16:00`, `2026-04-10T23:00`, `2026-04-11T08:00`, `2026-04-11T16:00`, `2026-04-11T23:00`
   - Last `10` cycles: `0` `blocked_city` rows, but `88` total Paris rows across `2026-04-09T23:00`, `2026-04-10T08:00`, `2026-04-10T16:00`, `2026-04-10T23:00`, `2026-04-11T08:00`, `2026-04-11T16:00`, `2026-04-11T23:00`
   - Recent Paris rows are real market rows filtered by other reasons such as `price_out_of_range` and `date_out_of_range_past`, which is consistent with `shadow`, not with a structural hard block

5. Does the current block match a valid structural criterion, or does it look inherited from a historical loss audit?
   It looks inherited from the historical loss audit, not from a current structural memo.
   - `CONTEXTO.md` records the historical-loss expansion of the 10-city block set
   - `docs/blocked-cities-rationale-latest.md` classifies `Paris` as `dudoso y candidato a revision futura`
   - Current artifacts keep pointing to `market_visibility`, not to mismatch, missing NOAA, or a broken resolution path

## Structural Conclusion

- `Ankara` does not currently satisfy any of the three valid hard-block criteria:
  - no documented forecast/settlement mismatch
  - NOAA station exists in `RESOLUTION_ICAO`
  - no evidence of broken or unvalidated resolution mechanism

- `Paris` does not currently satisfy any of the three valid hard-block criteria:
  - no documented forecast/settlement mismatch
  - NOAA station exists in `RESOLUTION_ICAO`
  - no evidence of broken or unvalidated resolution mechanism

- For both cities, the surviving evidence is `market_visibility` and inherited caution from the historical-loss block expansion. Under the canonical rule, that supports `shadow`, not `blocked`.

## Recommendation

- Move `Ankara` from `blocked` to `shadow`
- Move `Paris` from `blocked` to `shadow`
- Resulting `BLOCKED_CITIES`: `London,Tel Aviv,Wellington,Toronto,Madrid,Singapore`

This session does not modify Railway, `bot.py`, thresholds, allowlists, bankroll, or city mode lists.
