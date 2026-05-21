# Source Onboarding Shadow Plan: Chongqing / Jeddah

**Status:** plan-only / LOG_ONLY / no operational change.  
**Decision source:** Opus strategic decision after live throughput evidence pack, cycle 366 (`2026-05-21T11:38:47Z`): `SOURCE_ONBOARDING_FIRST` in parallel with funnel observability.

This plan does not change city mode. It does not add active/canary/shadow/blocked entries, env vars, whitelist, BANKROLL, scheduler, source mappings, exact/range filters, Fase C, or BUY/SELL/SKIP behavior.

## Current Evidence

Both cities are in the source-onboarding state:

`SOURCE_CONFIRMED_WAITING_SHADOW`

The strategic reason to prioritize them is that they already have strong trader evidence and source audit material, while Hong Kong remains too risky for canary because source risk is medium.

| City | Evidence summary | Current non-action |
| --- | --- | --- |
| Chongqing | Trader evidence `24/25`, WR `96.0%`; prior scanner snapshot had `shadow_cycles=9`, `edge_hits=1`, `best_edge=28.8%`; mapping/source material available; METAR recent sample looked promising in prior measurement docs. | Do not move to canary/active. Do not change city mode. |
| Jeddah | Trader evidence `7/8`, WR `87.5%`; prior scanner snapshot had `shadow_cycles=6`, `edge_hits=4`, `best_edge=30.2%`; `OEJN` / WU path documented; source text available; METAR recent sample looked promising in prior measurement docs. | Do not move to canary/active. Do not change city mode. |

Supporting repo artifacts:

- `docs/source_audits/candidate_source_onboarding_audit.md`
- `docs/source_audits/jeddah_promotion_readiness.md`
- `docs/source_audits/measurement_layer_cross_city_sample_2026_05_17.md`
- `docs/source_audits/metar_resolution_verify_report.md`
- `docs/funnel_observability_log_only.md`

## What Is Still Missing

Shared gaps:

- A clean post-decision funnel baseline with `discovered_markets_unique`.
- Per-city source/onboarding digest that separates source readiness from trading permission.
- Human confirmation that "shadow onboarding" is the desired next operational state for each city.
- A fresh read-only source/onboarding snapshot after the funnel LOG_ONLY patch lands.

Chongqing-specific gaps:

- More shadow edge hits; prior snapshot had many cycles but only one edge hit.
- Confirmation that source text and mapping remain stable and non-ambiguous.
- Confirmation that no source mismatch emerged after the prior scanner/audit.

Jeddah-specific gaps:

- More cycles to pass the shadow sample threshold; prior snapshot was below `shadow_cycles >= 10`.
- Confirmation that the `OEJN` / WU path remains acceptable for review.
- Confirmation that source text does not drift to `unknown`.

## Criterion To Enter Shadow Onboarding Review

This section defines a review gate, not an automatic city-mode change.

A city can be presented for human/Opus shadow-onboarding authorization only when all are true:

1. `primary_status=SOURCE_CONFIRMED_WAITING_SHADOW` remains true.
2. Source text is present and not ambiguous.
3. No source mismatch or settlement fidelity alert exists.
4. Recent shadow/onboarding evidence is refreshed from live artifacts read-only.
5. Funnel LOG_ONLY metrics are available so the review can see where the city is blocked.
6. The proposed action is explicitly `NO_ACTION / LOG_ONLY` until a human confirms the operational step.
7. The review states exactly which repo/env city-mode representation would be changed later, if any.

For this session, the criterion is not executed. No city mode is changed.

## Future Canary Review Criteria

Canary review is a later gate and is not authorized by this plan.

Minimum future criteria:

- At least 7 days of post-instrumentation funnel data.
- `discovered_markets_unique` present, with per-city stage counts.
- Shadow evidence shows repeatable edge, not one-off leakage.
- Source fidelity is confirmed and still current.
- No unresolved source ambiguity or medium/high source-risk flag.
- No execution-reject pattern that would make the opportunity non-actionable.
- Opus explicitly approves canary review for that exact city.
- Human explicitly confirms the city-mode change after Opus review.

This excludes the current Hong Kong case: despite strong live edge (`54.45`) and many shadow hits, source risk remains medium, so it is not a canary move now.

## Risks

- Source risk: WU/ICAO/METAR equivalence can look good in small samples but still fail settlement fidelity.
- Sample risk: trader WR and shadow edges may be small-sample artifacts or stale.
- Funnel blindness: without `discovered_markets_unique`, a city may look absent because of upstream discovery rather than policy.
- Policy leakage: shadow/onboarding language can be misread as permission to trade.
- Regression risk: adding telemetry later must not affect the live scan loop or trade decisions.

## Rollback / Stop Rules

Because this plan makes no operational change, rollback for this session is simply: do not apply a city-mode patch.

If a later authorized shadow-onboarding change is made, rollback should be explicit and human-approved:

- revert only the specific city onboarding/city-mode representation changed in that later task;
- leave historical LOG_ONLY artifacts intact;
- do not delete evidence rows;
- document the reason in the next operational closeout.

Stop immediately if:

- source text becomes `unknown` or ambiguous;
- settlement/source mismatch appears;
- funnel metrics show the city is not actually discoverable;
- any proposed patch touches trading core, BANKROLL, sizing, scheduler, guards, Fase C, or BUY/SELL/SKIP.

## Required Human Confirmation

Human confirmation is required before any of these:

- moving Chongqing or Jeddah into any explicit `shadow`, `canary`, or `active` operational representation;
- changing `ACTIVE_TRADING_CITIES`, `CANARY_TRADING_CITIES`, `BLOCKED_CITIES`, `auto_*_cities`, whitelist, or source policy;
- accepting an ICAO/WU-only path as sufficient for promotion review;
- opening a canary review;
- changing exact/range filters or source gates.

Recommended next sequence:

1. Codex CODE implements funnel metrics LOG_ONLY.
2. Let at least several cycles accumulate; target 7 days for stable review.
3. Opus/human reviews refreshed Chongqing/Jeddah evidence and explicitly decides whether to authorize shadow onboarding.
4. Only after that, a separate operational task applies any approved city-mode/onboarding change.

