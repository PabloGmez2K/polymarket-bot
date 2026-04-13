# Blocked Cities Review

- Date: `2026-04-12`
- Scope: read-only review of `Ankara`, `Miami`, `Paris`, and `Seattle`
- Canonical rule used: `blocked` should mean structural source/resolution guardrail, not tactical pause
- Preflight gate: `python tools/system_alignment_check.py` and `python tools/system_alignment_check.py --decision-mode operational` both closed at `ok=7`, `warning=1`, `error=0`

## Verdict

| City | Verdict | Short reason |
| --- | --- | --- |
| Ankara | insufficient evidence | Has `noaa_station_id` and recent market visibility, but the current ledger still classifies it as `building` with bottleneck `market_visibility`; recent blocked skips fell to zero, so there is no urgent need to unblock on this snapshot alone. |
| Miami | candidata a shadow | Current artifacts no longer show a structural source/resolution reason to keep a hard block: `noaa_station_id` exists, markets are visible repeatedly in recent runtime cycles, source risk is `low`, and recent blocked skips fell to zero in the latest window. |
| Paris | insufficient evidence | Has `noaa_station_id` and some recent market visibility, but the current ledger still says `building` / `observe_with_source_caution` with bottleneck `market_visibility`; recent blocked skips fell to zero, so the evidence is not strong enough to demand an unblock now. |
| Seattle | candidata a shadow | Has `noaa_station_id`, visible markets in the latest runtime cycles, low source risk, and still shows real blocked-skip pressure in the latest window (`11` blocked skips in the last 9 cycles), which means the hard block is still suppressing visible markets without a fresh structural memo. |

## Evidence Notes

### Ankara

- `runtime_policy_effective_view_latest`: still resolves to `blocked` from `BLOCKED_CITIES`, with no runtime contradiction.
- `bot.py` includes `RESOLUTION_ICAO["Ankara"]` with `noaa_station_id="17128099999"`.
- `city_validation_ledger_latest`: `building`, `observe_with_source_caution`, bottleneck `market_visibility`, visibility `16`, source risk `medium`.
- `reference_trader_city_market_cross_latest`: priority `15`, `5` high refs.
- `analyze_skip_log --last-n-cycles 30 --city Ankara`: `88` historical `blocked_city` skips, but `0` in the latest 10-cycle window.
- `cycles_history.jsonl`: visible again on `2026-04-08` and `2026-04-10`.

### Miami

- `runtime_policy_effective_view_latest`: still resolves to `blocked` from `BLOCKED_CITIES`, with no runtime contradiction.
- `bot.py` includes `RESOLUTION_ICAO["Miami"]` with `noaa_station_id="72202012839"`.
- `city_validation_ledger_latest`: `insufficient`, recommendation `insufficient_evidence`, bottleneck `trader_discovery`, source risk `low`.
- `analyze_skip_log --last-n-cycles 30 --city Miami`: `132` historical `blocked_city` skips, but `0` in the latest 12-cycle window.
- `cycles_history.jsonl`: visible repeatedly on `2026-04-07`, `2026-04-08`, `2026-04-09`, `2026-04-10`, and `2026-04-11`.
- `performance.json` and `trade_lifecycle.json` both still contain Miami history, so this is not a dead city.

### Paris

- `runtime_policy_effective_view_latest`: still resolves to `blocked` from `BLOCKED_CITIES`, with no runtime contradiction.
- `bot.py` includes `RESOLUTION_ICAO["Paris"]` with `noaa_station_id="07157099999"`.
- `city_validation_ledger_latest`: `building`, `observe_with_source_caution`, bottleneck `market_visibility`, visibility `9`, source risk `medium`.
- `reference_trader_city_market_cross_latest`: priority `8`, `3` high refs.
- `analyze_skip_log --last-n-cycles 30 --city Paris`: `143` historical `blocked_city` skips, but `0` in the latest 12-cycle window.
- `cycles_history.jsonl`: visible on `2026-04-07` and `2026-04-08`.

### Seattle

- `runtime_policy_effective_view_latest`: still resolves to `blocked` from `BLOCKED_CITIES`, with no runtime contradiction.
- `bot.py` includes `RESOLUTION_ICAO["Seattle"]` with `noaa_station_id="72793024233"`.
- `city_validation_ledger_latest`: `insufficient`, recommendation `insufficient_evidence`, bottleneck `trader_discovery`, visibility `6`, source risk `low`.
- `reference_trader_city_market_cross_latest`: priority `5`, `2` high refs.
- `analyze_skip_log --last-n-cycles 30 --city Seattle`: `143` historical `blocked_city` skips and still `11` blocked skips in the latest 9-cycle window.
- `cycles_history.jsonl`: visible on `2026-04-10` and `2026-04-11`.
- The latest snapshot also shows Seattle markets getting filtered by price/condition, which supports using `shadow` for observation rather than a hard structural block.

## Pending Manual Change If Approved

If Pablo decides to move only the current shadow candidates out of `BLOCKED_CITIES`, the exact pending change would be:

- Current value: `London,Miami,Seattle,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`
- Proposed value: `London,Paris,Tel Aviv,Wellington,Toronto,Madrid,Singapore,Ankara`

This review does not execute that change and does not modify Railway.

## Conclusion

- `Miami` and `Seattle` are the strongest current candidates to stop using `blocked` as a hard guardrail and fall back to canonical `shadow`.
- `Ankara` and `Paris` no longer look dead or NOAA-ineligible, but the current read-only package still reads as evidence-building rather than a clean unblock recommendation.
- No structural source/resolution memo equivalent to `London` was found for any of these four cities in the latest canonical artifacts.
