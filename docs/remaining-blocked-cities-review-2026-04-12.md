# Remaining Blocked Cities Review

- Date: `2026-04-12`
- Scope: read-only structural audit of `Madrid`, `Toronto`, `Wellington`, `Singapore`, and `Tel Aviv`
- Out of scope: `London` remains excluded because its structural `Weather Underground vs Open-Meteo` mismatch is already documented as valid
- Methodology reference: `docs/ankara-paris-unblock-review-2026-04-12.md`
- Canonical rule used: `blocked` must mean structural source/resolution guardrail, not PnL history or tactical pause
- Current session preflight note:
  - `python tools/system_alignment_check.py --decision-mode operational` first failed by staleness, so the session refreshed `data/runtime_import/` with `tools/railway_runtime_snapshot_pull.ps1`
  - after refreshing the snapshot and regenerating `docs/runtime_policy_effective_view_latest.md`, preflight still returned `ok=6`, `warning=1`, `error=1`, but now because `blocking_operational_collision_count=1`
  - the blocker is `London` (`env=blocked`, `runtime=auto_canary`), which is out of scope for this document
  - this review remains read-only and uses the fresh snapshot pulled at `2026-04-12T16:37:18.9123748+00:00`

## Verdict

| City | Verdict | Why |
| --- | --- | --- |
| Madrid | move to `shadow` | `noaa_station_id` exists, no documented forecast/settlement mismatch was found, no broken resolution mechanism was found, and recent rows are already behaving like `shadow` rows rather than `blocked_city`. The remaining explanation is inherited historical caution, not a current structural guardrail. |
| Toronto | keep `blocked` | `noaa_station_id` is still absent from `RESOLUTION_ICAO`, which is itself a canonical structural criterion. Recent `blocked_city` rows are actively suppressing real Toronto markets in the latest `10-12` cycle windows. |
| Wellington | move to `shadow` | `noaa_station_id` exists, no documented mismatch was found, no broken resolution mechanism was found, and recent rows are already behaving like `shadow` rows filtered by normal funnel reasons. The current block reads as inherited from the loss audit, not as a structural guardrail. |
| Singapore | keep `blocked` | `noaa_station_id` is still absent from `RESOLUTION_ICAO`, which is itself a canonical structural criterion. Recent `blocked_city` rows are actively suppressing real Singapore markets in the latest `10-12` cycle windows. |
| Tel Aviv | move to `shadow` | `noaa_station_id` exists, no documented mismatch was found, no broken resolution mechanism was found, and recent rows are already behaving like `shadow` rows rather than `blocked_city`. The current block reads as inherited historical caution, not as a structural guardrail. |

## Current Manual Blocked Value

From `data/runtime_import/policy_env_snapshot.json` pulled at `2026-04-12T16:37:50.1056707+00:00`:

- Current `BLOCKED_CITIES`: `London,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`

If only the recommendations in this document are applied, the exact resulting value would be:

- Proposed `BLOCKED_CITIES`: `London,Paris,Toronto,Singapore,Ankara`

## Evidence By City

### Madrid

1. `noaa_station_id` in `RESOLUTION_ICAO`?
   Yes. `bot.py` declares `RESOLUTION_ICAO["Madrid"]` with:
   - `icao="LEMD"`
   - `noaa_station_id="08221099999"`
   - `noaa_daily_station_id="SPE00120278"`

2. Documented mismatch between forecast source and settlement source?
   No. The current canonical docs keep `London` as the only city with an explicit documented mismatch memo. No equivalent source/settlement mismatch memo was found for `Madrid`.

3. Evidence that the resolution mechanism is broken or unvalidated?
   No direct evidence of a broken resolution mechanism was found.
   - `data/city_validation_ledger.json` still includes `Madrid` with `settlement_fidelity.score=3`, `risk=medium`, rationale `icao | wu_url | noaa_station`
   - `CONTEXTO.md` mentions a historical `Bug #3` for Madrid, but that is a trading duplication / stop-loss bug, not a source-resolution failure

4. Do recent `blocked_city` skips show real markets being suppressed, or is the bucket already `0`?
   The recent blocked bucket is already `0`.
   - Last `12` cycles: `0` `blocked_city` rows and `77` total Madrid rows
   - Last `10` cycles: `0` `blocked_city` rows and `55` total Madrid rows
   - Recent Madrid rows are normal `shadow`-style filters: `price_out_of_range=42`, `date_out_of_range_past=33`, `condition_filtered=2`
   - Latest examples in `skip_log.jsonl` show `city_mode=shadow` on `2026-04-12T09:45`

5. Does the current block match a valid structural criterion, or does it look inherited from a historical loss audit?
   It looks inherited from the historical loss audit.
   - `CONTEXTO.md` records the 10-city block expansion from the loss audit in `v10.5.12`
   - `docs/blocked-cities-rationale-latest.md` explicitly says Madrid remains blocked with debt of explanation, not with a fresh city-specific structural memo

### Toronto

1. `noaa_station_id` in `RESOLUTION_ICAO`?
   No. `bot.py` declares `RESOLUTION_ICAO["Toronto"]` with `icao="CYYZ"` and `wu_url`, but no `noaa_station_id`.

2. Documented mismatch between forecast source and settlement source?
   No explicit mismatch memo was found for `Toronto`.

3. Evidence that the resolution mechanism is broken or unvalidated?
   Yes, in the canonical sense of being not fully validated.
   - `docs/noaa-station-verification-contract.md` still lists `Toronto | CYYZ | BUSCAR ...`
   - `data/city_validation_ledger.json` keeps `Toronto` at `settlement_fidelity.score=2`, `risk=high`, rationale `icao | wu_url`
   - `docs/blocked-cities-rationale-latest.md` says `Toronto` has `no NOAA rows`

4. Do recent `blocked_city` skips show real markets being suppressed, or is the bucket already `0`?
   Yes, the hard block is suppressing real markets now.
   - Last `12` cycles: `110` `blocked_city` rows and `110` total Toronto rows
   - Last `10` cycles: `88` `blocked_city` rows and `88` total Toronto rows
   - Recent examples in `skip_log.jsonl` show Toronto markets still appearing on `2026-04-12T16:00` but being skipped as `blocked_city`
   - `docs/polymarket-universe-price-temporal-audit-2026-04-12.md` also records `Toronto 2026-04-07 -> 7`, which supports current market visibility

5. Does the current block match a valid structural criterion, or does it look inherited from a historical loss audit?
   It matches a valid structural criterion today because `noaa_station_id` is still absent from `RESOLUTION_ICAO`.
   - The city also has historical loss-audit baggage, but unlike Madrid/Wellington/Tel Aviv, the NOAA gate is still unresolved in code

### Wellington

1. `noaa_station_id` in `RESOLUTION_ICAO`?
   Yes. `bot.py` declares `RESOLUTION_ICAO["Wellington"]` with:
   - `icao="NZWN"`
   - `noaa_station_id="93436000488"`
   - `noaa_daily_station_id="NZM00093439"`

2. Documented mismatch between forecast source and settlement source?
   No explicit mismatch memo was found for `Wellington`.

3. Evidence that the resolution mechanism is broken or unvalidated?
   No direct evidence of a broken mechanism was found.
   - `CONTEXTO.md` records a resolved historical trade: `Wellington NO` as `WIN resolución`
   - current runtime artifacts show the city appearing in the market universe and falling through normal filters, not through a structural resolution failure

4. Do recent `blocked_city` skips show real markets being suppressed, or is the bucket already `0`?
   The recent blocked bucket is already `0`.
   - Last `12` cycles: `0` `blocked_city` rows and `143` total Wellington rows
   - Last `10` cycles: `0` `blocked_city` rows and `132` total Wellington rows
   - Recent Wellington rows are normal `shadow`-style filters: `price_out_of_range=76`, `timezone_filter=44`, `condition_filtered=23`
   - Latest examples in `skip_log.jsonl` show `city_mode=shadow` on `2026-04-12T16:00`

5. Does the current block match a valid structural criterion, or does it look inherited from a historical loss audit?
   It looks inherited from the historical loss audit.
   - `CONTEXTO.md` records the 10-city loss-based block expansion
   - `docs/blocked-cities-rationale-latest.md` says Wellington remains a conservative keep with mostly absence-of-proof, not a strong current structural memo

### Singapore

1. `noaa_station_id` in `RESOLUTION_ICAO`?
   No. `bot.py` declares `RESOLUTION_ICAO["Singapore"]` with `icao="WSSS"` and `wu_url`, but no `noaa_station_id`.

2. Documented mismatch between forecast source and settlement source?
   No explicit mismatch memo was found for `Singapore`.

3. Evidence that the resolution mechanism is broken or unvalidated?
   Yes, in the canonical sense of being not fully validated.
   - `docs/noaa-station-verification-contract.md` still lists `Singapore | WSSS | BUSCAR`
   - `bot.py` even keeps a comment that an ISD candidate was confirmed, but it is not actually declared inside `RESOLUTION_ICAO`
   - `docs/blocked-cities-rationale-latest.md` says station verification is still pending

4. Do recent `blocked_city` skips show real markets being suppressed, or is the bucket already `0`?
   Yes, the hard block is suppressing real markets now.
   - Last `12` cycles: `110` `blocked_city` rows and `110` total Singapore rows
   - Last `10` cycles: `88` `blocked_city` rows and `88` total Singapore rows
   - Recent examples in `skip_log.jsonl` show Singapore markets still appearing on `2026-04-12T16:00` but being skipped as `blocked_city`

5. Does the current block match a valid structural criterion, or does it look inherited from a historical loss audit?
   It matches a valid structural criterion today because `noaa_station_id` is still absent from `RESOLUTION_ICAO`.
   - As with Toronto, there is also historical loss-audit baggage, but the missing NOAA declaration is enough on its own to justify a hard block under the project rule

### Tel Aviv

1. `noaa_station_id` in `RESOLUTION_ICAO`?
   Yes. `bot.py` declares `RESOLUTION_ICAO["Tel Aviv"]` with:
   - `icao="LLBG"`
   - `noaa_station_id="40180099999"`
   - `noaa_daily_station_id="ISE00105694"`

2. Documented mismatch between forecast source and settlement source?
   No explicit mismatch memo was found for `Tel Aviv`.

3. Evidence that the resolution mechanism is broken or unvalidated?
   No direct evidence of a broken mechanism was found.
   - current docs do not surface a city-specific source-fidelity or resolution-failure memo
   - `docs/blocked-cities-rationale-latest.md` explicitly says the rationale is mostly inherited manual caution rather than a fresh memo

4. Do recent `blocked_city` skips show real markets being suppressed, or is the bucket already `0`?
   The recent blocked bucket is already `0`.
   - Last `12` cycles: `0` `blocked_city` rows and `44` total Tel Aviv rows
   - Last `10` cycles: `0` `blocked_city` rows and `33` total Tel Aviv rows
   - Recent Tel Aviv rows are normal `shadow`-style filters: `date_out_of_range_past=44`
   - Latest examples in `skip_log.jsonl` show `city_mode=shadow` on `2026-04-11T23:00`

5. Does the current block match a valid structural criterion, or does it look inherited from a historical loss audit?
   It looks inherited from the historical loss audit.
   - `CONTEXTO.md` records the 10-city loss-based block expansion
   - `docs/blocked-cities-rationale-latest.md` says the explanation is mostly inherited manual caution, not a current structural memo

## Structural Conclusion

- `Madrid` does not currently satisfy any valid hard-block criterion:
  - no documented forecast/settlement mismatch
  - NOAA station exists in `RESOLUTION_ICAO`
  - no evidence of broken or unvalidated resolution mechanism

- `Toronto` still satisfies a valid hard-block criterion:
  - `noaa_station_id` is absent from `RESOLUTION_ICAO`

- `Wellington` does not currently satisfy any valid hard-block criterion:
  - no documented forecast/settlement mismatch
  - NOAA station exists in `RESOLUTION_ICAO`
  - no evidence of broken or unvalidated resolution mechanism

- `Singapore` still satisfies a valid hard-block criterion:
  - `noaa_station_id` is absent from `RESOLUTION_ICAO`

- `Tel Aviv` does not currently satisfy any valid hard-block criterion:
  - no documented forecast/settlement mismatch
  - NOAA station exists in `RESOLUTION_ICAO`
  - no evidence of broken or unvalidated resolution mechanism

## Recommendation

- Move `Madrid` from `blocked` to `shadow`
- Keep `Toronto` in `blocked`
- Move `Wellington` from `blocked` to `shadow`
- Keep `Singapore` in `blocked`
- Move `Tel Aviv` from `blocked` to `shadow`

- Resulting `BLOCKED_CITIES`: `London,Paris,Toronto,Singapore,Ankara`

This session does not modify Railway, `bot.py`, thresholds, allowlists, bankroll, or city mode lists.
