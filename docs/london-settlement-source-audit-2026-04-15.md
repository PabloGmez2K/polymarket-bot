# London Settlement/Source Audit

- Date: `2026-04-15`
- Scope: read-only review of `London` after fixing the city-intelligence warning model
- Inputs used:
  - `data/runtime_import/runtime_import_manifest.json`
  - `data/runtime_import/city_policy_state.json`
  - `data/city_validation_ledger.json`
  - `data/city_promotion_gate.json`
  - `data/runtime_import/shadow_city_tracking.json`
  - `data/runtime_import/postmortem.json`
  - `docs/blocked-signals-wr-baseline-2026-04-13.md`
  - fresh `settlement_fidelity_probe.py --city London`

## Verdict

Keep `London` in the structural blocked bucket.

The new evidence does **not** show that London is fixed. What it shows is:

- the analytic warning was previously modeled wrong
- runtime policy still contains a conflicting `auto_canary` overlay for London
- the source/settlement revalidation is still incomplete because Weather Underground settlement is not automated in the probe

## What Changed Today

`city intelligence` now respects the canonical mode priority from `AGENTS.md`:

- `blocked` wins over `auto_canary`
- London is read as `policy_mode=blocked`
- London carries `structural_block_guardrail=weather_underground_openmeteo_mismatch`
- London bottleneck is now `source_fidelity`, not `trader_discovery`

## Fresh Evidence

### 1. Runtime drift is real

Fresh runtime snapshot shows:

- `cross_policy_mode=blocked`
- `runtime_policy_mode=auto_canary`
- `drift_flags=["policy_divergence"]`

So the immediate operational issue is not "London is healthy now". It is "runtime auto-promotion is colliding with a manually blocked city".

### 2. Settlement/source evidence is still not strong enough to reopen

Fresh London-only settlement probe found:

- `10` London markets
- `10/10` with Open-Meteo
- `0/10` with NOAA observed
- Weather Underground settlement remains `pending_not_automated`

This means we still do **not** have fresh automated evidence strong enough to overturn the historical WU-vs-Open-Meteo mismatch memo.

### 3. Shadow/edge signal exists, but it is not enough to trust source fidelity

Fresh shadow tracking for London shows:

- `markets_seen=128`
- `edge_hits=2`
- `cycles_seen=41`
- `best_edge_pct=28.4`

That is enough to explain why the runtime overlay promoted London, but not enough to prove that the structural block is obsolete.

### 4. Historical outcomes still lean conservative

Current local artifacts still point to caution:

- blocked-signals baseline keeps London at `33.3% (1/3)` for exact/range quality-trader signals
- runtime postmortem/trade artifacts still show repeated London losses in the historical sample
- the freshest live London trade in runtime import is one `RESOLVED_WIN`, but that is nowhere near enough to erase the prior mismatch memo

## Best Next Step

Without touching trading core, the clean next move is:

1. remove or neutralize the London `auto_canary` runtime overlay so runtime stops contradicting manual `blocked`
2. only after that, run a dedicated London settlement revalidation with a real WU-backed read path or a manual sampled comparison

Until that happens, London should be interpreted as:

- analytically: `blocked with runtime drift`
- operationally: `do not use as monetization candidate`
