# Candidate Source Onboarding Audit — Jeddah / Chongqing / Amsterdam

**Generated:** 2026-05-15  
**Source:** Source Onboarding Scanner v0.2 — Railway live run, outputs `/tmp` only  
**Classification:** MONETIZATION_RELEVANT / RISK_CONTROL / NORMAL / LOG_ONLY / docs-only  
**Status:** HUMAN_AUDIT_PENDING — no operational action authorized

---

## Executive Summary

Three cities reached `source_audit_status=READY_FOR_HUMAN_SOURCE_AUDIT` in the
v0.2 scanner: **Jeddah**, **Chongqing**, and **Amsterdam**.

**None of these cities are authorized for active or canary trading.**

Key points:
- `source_audit_status=READY_FOR_HUMAN_SOURCE_AUDIT` means the source/mapping
  material is ready for a human to read — it does NOT mean the city is ready for
  operational promotion.
- `operational_action=NO_ACTION / LOG_ONLY` for all three.
- Primary blockers: missing `noaa_station_id`, insufficient shadow cycles/edge
  hits, and (for Amsterdam) trader evidence too thin for promotion gates.
- No auto-promotion. Any move toward canary/active requires a full Opus source
  review plus satisfaction of all promotion gates (shadow evidence, NOAA,
  mapping, policy).

---

## Summary Table

| City        | primary_status                   | Trader evidence           | Shadow evidence                         | mapping_status       | source_discovery_status | source_audit_status          | missing_inputs                                | next_best_action                                         | operational_action       |
|-------------|----------------------------------|---------------------------|----------------------------------------|----------------------|-------------------------|------------------------------|-----------------------------------------------|----------------------------------------------------------|--------------------------|
| Jeddah      | SOURCE_CONFIRMED_WAITING_SHADOW  | TRADER_EVIDENCE_READY (7/8, WR 87.5%) | SHADOW_EVIDENCE_PARTIAL cycles=6 edge_hits=4 best_edge=30.2% | MAPPING_ICAO_ONLY    | SOURCE_TEXT_AVAILABLE   | READY_FOR_HUMAN_SOURCE_AUDIT | noaa_station_id, shadow_cycles_or_edges       | Wait for shadow cycles/edge_hits to meet threshold       | NO_ACTION / LOG_ONLY     |
| Chongqing   | SOURCE_CONFIRMED_WAITING_SHADOW  | TRADER_EVIDENCE_READY (24/25, WR 96.0%) | SHADOW_EVIDENCE_PARTIAL cycles=9 edge_hits=1 best_edge=28.8% | MAPPING_ICAO_ONLY    | SOURCE_TEXT_AVAILABLE   | READY_FOR_HUMAN_SOURCE_AUDIT | noaa_station_id, shadow_cycles_or_edges       | Wait for shadow cycles/edge_hits to meet threshold       | NO_ACTION / LOG_ONLY     |
| Amsterdam   | WAITING_EVIDENCE                 | TRADER_EVIDENCE_READY (10/10 blocked WR 100%, n small) | SHADOW_EVIDENCE_PARTIAL cycles=2 edge_hits=1 best_edge=58.2% | MAPPING_ICAO_ONLY    | SOURCE_TEXT_AVAILABLE   | READY_FOR_HUMAN_SOURCE_AUDIT | noaa_station_id, shadow_cycles_or_edges       | Wait for stronger trader or blocked-resolution evidence  | NO_ACTION / LOG_ONLY     |

---

## City Detail

### Jeddah

**Why interesting:**  
Strong trader signal (7/8 wins, WR 87.5%) with shadow leak present (6 cycles,
4 edge hits, best edge 30.2%). Source text is available and mapping resolves to
ICAO-only. Bot has seen it; not yet observed by us.

**Source / mapping:**  
`mapping_status=MAPPING_ICAO_ONLY` — internal RESOLUTION_ICAO has an ICAO
entry, but no `noaa_station_id` and no Weather Underground / WRH site defined.
`source_discovery_status=SOURCE_TEXT_AVAILABLE` — slugs, market_ids, and
condition_ids are present, so Gamma could be queried if `gamma_check_recommended`
were set (currently false).

**What's missing:**  
- `noaa_station_id` — required before any observed audit or promotion path.
- Shadow cycles/edge_hits below threshold (6 cycles, 4 hits; need more to
  satisfy shadow evidence gate).

**Trigger to advance:**  
- Shadow cycles increase to threshold AND `noaa_station_id` identified via
  human Gamma/ICAO lookup → triggers Opus source review request.
- If source ambiguity or mismatch appears during audit: escalate to Opus before
  any patch.

**What is NOT permitted:**  
No observed audit enrollment. No canary or active trading. No RESOLUTION_ICAO
patch. No env var change. No auto-promotion. No Telegram runtime action.

---

### Chongqing

**Why interesting:**  
Exceptionally strong trader evidence (24/25 wins, WR 96.0%) — highest of the
three candidates. Shadow is partial but accumulating (9 cycles, 1 edge hit,
best edge 28.8%). Source and identifiers available.

**Source / mapping:**  
`mapping_status=MAPPING_ICAO_ONLY` — ICAO entry exists, no `noaa_station_id`,
no WRH site. `source_discovery_status=SOURCE_TEXT_AVAILABLE` — identifiers
present for a future Gamma read.

**What's missing:**  
- `noaa_station_id` — hard blocker for observed audit / any promotion.
- `shadow_cycles_or_edges` — edge_hits=1 at best_edge=28.8% is below the
  threshold for shadow evidence readiness despite 9 cycles.

**Trigger to advance:**  
- Shadow edge_hits increase (accumulate additional cycles where edge fires) AND
  `noaa_station_id` identified → Opus source review request.
- Note: very strong trader WR makes this the highest-priority candidate for the
  human audit once NOAA and shadow gates are met.

**What is NOT permitted:**  
Same as Jeddah: no observed audit, no canary/active, no RESOLUTION_ICAO patch,
no env vars, no auto-promotion, no Telegram action.

---

### Amsterdam

**Why interesting:**  
Blocked-signal trader evidence shows 10/10 wins (WR 100%), though n=10 is small
and the `trader` direct-signal count is zero (trader evidence comes entirely
from `blocked_signals_resolutions`, not from `signals_crosscheck` direct
entries). Shadow is early (2 cycles, 1 edge hit) but best_edge=58.2% is the
strongest edge value of the three candidates. Slug and condition_id are present.

**Scanner data (live Railway run 2026-05-15):**

```
primary_status: WAITING_EVIDENCE
trader_evidence_status: TRADER_EVIDENCE_READY
trader_report: wins=10 / n=10, WR=100.0%  (blocked_signals path only)
shadow: cycles_seen=2, edge_hits=1, best_edge_pct=58.2
  last_seen_at: 2026-04-24T11:10:44.720158+00:00
mapping_status: MAPPING_ICAO_ONLY
source_discovery_status: SOURCE_TEXT_AVAILABLE
source_audit_status: READY_FOR_HUMAN_SOURCE_AUDIT
source_audit_recommended: true
observation_review_recommended: true
operational_action: NO_ACTION / LOG_ONLY
missing_inputs: noaa_station_id, shadow_cycles_or_edges
market_identifiers:
  slugs: ["highest-temperature-in-amsterdam-on-may-7-2026-17c"]
  market_ids: ["2162243"]
  condition_ids: ["0xb1481910a8827e0a4f5065c590e27f6410648ef152add11c8dadd108d2564ce2"]
source_texts: ["polymarket_market_price", "unknown"]
```

**Source / mapping:**  
`mapping_status=MAPPING_ICAO_ONLY` — ICAO entry present (likely EHAM), no
`noaa_station_id`. `source_text` includes `"unknown"` alongside
`"polymarket_market_price"`, meaning the source reference in at least one
market is ambiguous. This ambiguity would need to be resolved during the Gamma
audit before any further steps.

**What's missing:**  
- `noaa_station_id` — hard blocker.
- Shadow depth: only 2 cycles, last seen 2026-04-24 (3 weeks idle). Needs
  more cycles to confirm signal continuity.
- Primary status is `WAITING_EVIDENCE` (weaker than Chongqing/Jeddah which
  are `SOURCE_CONFIRMED_WAITING_SHADOW`), meaning the overall readiness level
  is lower despite the source audit flag.
- `source_texts` contains `"unknown"` — needs Gamma audit to resolve whether
  the market actually cites a verifiable external source or uses only internal
  price as settlement reference.

**Trigger to advance:**  
- Additional shadow cycles (resume after 2026-04-24 idle period) AND
  `noaa_station_id` identified AND Gamma audit confirms an unambiguous
  verifiable source → Opus review request.
- If `source_texts` resolves to `"unknown"` only: escalate to Opus, do not
  proceed without source confirmation.

**What is NOT permitted:**  
Same as Jeddah/Chongqing. Additionally: do not act on the 100% blocked WR
alone given n=10 and zero direct trader signals.

---

## Promotion Rules

These rules apply to all three candidates:

| Condition | Rule |
|-----------|------|
| `noaa_station_id` missing | Block all: no observed audit, no canary, no active |
| Shadow evidence partial | Wait for more cycles and edge_hits to meet threshold |
| `source_texts` contains `"unknown"` | Must resolve via Gamma before any further action |
| Source ambiguity or mismatch found during audit | Escalate to Opus; no auto-patch |
| Reaches `READY_FOR_HUMAN_SOURCE_AUDIT` + shadow sufficient + NOAA resolved | Prepare Opus review request; no auto-promotion |
| Any promotion decision | Must go through full promotion gate: shadow evidence, NOAA, source match confirmed, Opus sign-off, human approval |

**Priority order for next human review (if/when gates are met):**  
1. Chongqing — strongest trader WR (96%), most shadow cycles (9), NOAA resolution is the only key blocker.  
2. Jeddah — strong WR (87.5%), 4 edge hits.  
3. Amsterdam — highest single edge (58.2%), but thinner evidence base and source ambiguity.

---

## Verification

- Scanner run: read-only, Railway `/app/data` → `/tmp/so_v02b.json` only; no `/app/data` writes.
- No `bot.py`, `tools/*.py`, tests, trading core, BANKROLL, Fase C, env vars, DB, city modes, scheduler, whitelist, promotion gates, observed_vs_forecast, Telegram runtime wiring, or source mappings were touched.
- `git diff --check`: docs-only change, no whitespace errors.
