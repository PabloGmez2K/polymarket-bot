# London City-Intelligence Warning Review

- Date: `2026-04-15`
- Scope: verify why `city intelligence` treated `London` as low-priority background work and whether that warning should be corrected
- Guardrails: no changes to `bot.py`, live policy, runtime state, trading logic, or NOAA core

## Diagnosis

`London` was being flattened by the generic ledger heuristic:

- `n_reference_traders < 3` forced `bottleneck=trader_discovery`
- `recommendation=insufficient_evidence` then fell through to `gate_status=background_watch`
- that story contradicted the canonical blocked rationale, which still treats London as the only city with an explicit documented structural settlement/source mismatch

In other words, the warning was not saying "London is proven fixed". It was saying "the generic city-intelligence funnel forgot that London is a special blocked case".

## What Was Corrected

Analytic tooling was updated so that:

- cities with an explicit structural blocked guardrail do not degrade to `trader_discovery` before that guardrail is considered
- `London` now carries a `structural_block_guardrail` in the ledger with reason `weather_underground_openmeteo_mismatch`
- the promotion gate now surfaces that case as `blocked_with_signal` instead of `background_watch`

Validated on the London case:

- expected bottleneck: `source_fidelity`
- expected gate: `blocked_with_signal`
- expected priority: `soon`

## Important Runtime Note

The current full local regeneration of `city_validation_ledger.py` is fail-closed today because `data/runtime_import/city_policy_state.json` no longer matches the byte count recorded in `data/runtime_import/runtime_import_manifest.json`.

That is a separate operational issue. It should not be confused with the London warning-modeling fix.

## Next Step

Run a read-only London settlement/source revalidation once the runtime manifest is refreshed or explicitly accepted:

1. keep the block if the WU-vs-Open-Meteo mismatch still appears in fresh resolved samples
2. downgrade to `shadow` only if the structural mismatch no longer holds up under fresh evidence
