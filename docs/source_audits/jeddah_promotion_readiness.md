# Jeddah — Promotion Readiness Dossier

**Generated:** 2026-05-17
**Mode:** Sonnet read-only / docs-only
**Authority:** No operational action. No code patch. No env/whitelist/policy change.
**Source data:** Source Onboarding Scanner v0.2, Railway live run snapshot 2026-05-15
(`docs/source_audits/candidate_source_onboarding_audit.md`); `bot.py` RESOLUTION_STATIONS
(v10.6.28, P5 expansion ~2026-04-21).
**Verdict:** **NOT_READY_WAIT_SHADOW** — temporal maturation, not structural block.

**Measurement layer gate (2026-05-17 update):** exact-market promotion review
also requires a source parity dossier before any Opus promotion review. The
pilot dossier `docs/source_audits/jeddah_open_meteo_vs_wu_parity.md` currently
closes as `INSUFFICIENT_DATA` for Gamma-derived exact settlement
(`n_dates_compared=1`) and `WU_FETCHER_MISSING` for direct WU parity. Do not
promote Jeddah on source text alone.

---

## 1. Current State

| Field | Value |
|---|---|
| primary_status | SOURCE_CONFIRMED_WAITING_SHADOW |
| trader_evidence_status | TRADER_EVIDENCE_READY |
| trader_report | wins=7 / n=8, WR=87.5% |
| shadow_cycles | 6 (snapshot 2026-05-15) — Opus note "~7", treat as 6–7 |
| edge_hits | 4 (Opus also cited "4–5") |
| best_edge | 30.2% |
| mapping_status | MAPPING_ICAO_ONLY (scanner v0.2 view) |
| ICAO | **OEJN** (King Abdulaziz Intl) — present in `RESOLUTION_STATIONS` |
| WU site | **WU OEJN defined** (`_wu_history_url("OEJN")` in bot.py v10.6.28) |
| noaa_station_id | Absent (NOAA 2026 vacío para OEJN, ver bot.py comment) |
| source_discovery_status | SOURCE_TEXT_AVAILABLE |
| source_audit_status | READY_FOR_HUMAN_SOURCE_AUDIT |
| operational_action | NO_ACTION / LOG_ONLY |
| Whitelist status | **Present** in `QUALITY_TRADER_CITIES_WHITELIST` (P5 v10.6.28, ~2026-04-21) |
| Active trading | Not in `ACTIVE_TRADING_CITIES`. No real BUY/SELL. |

**Source/settlement clarification (correction vs. v1):**
Jeddah is **not** an "unmapped ICAO-only" city in the structural sense — it has
both `OEJN` ICAO and a defined Weather Underground URL inside
`RESOLUTION_STATIONS` (bot.py v10.6.28). The scanner v0.2 label
`MAPPING_ICAO_ONLY` reflects the *absence of `noaa_station_id`*, which is
expected because NOAA 2026 has no station for OEJN. This blocks the
**NOAA / observed-audit path**, but does not by itself block an
**ICAO-only / WU-based promotion review** if Opus decides that path is
acceptable.

"Promotion" in this dossier = move from shadow/observation into a step where
the city contributes to real operations (currently Jeddah is whitelisted for
quality-trader filtering but does not appear to be producing active BUYs at
relevant throughput; needs Opus confirmation of the exact next step).

---

## 2. Shadow Evidence

- **Cycles observed:** 6 (scanner v0.2 snapshot 2026-05-15). Opus: "~7" — interpret as 6–7.
- **Edge hits:** 4 (Opus: 4–5).
- **edge_hits / cycles ratio:** 4/6 ≈ 0.67 — strong hit density.
- **Best edge:** 30.2%.
- **Signal stability:** Looks stable at this small sample; decay UNKNOWN until n>=10.
- **Runtime live vs snapshot:** All numbers from Railway live scanner run 2026-05-15
  (read-only into `/tmp`). No local-only snapshot. State lives in `/app/data` on Railway.

---

## 3. Comparison with Toronto Pre-Canary Pattern

Toronto entered `QUALITY_TRADER_CITIES_WHITELIST` on 2026-04-14
(`docs/handoffs/condition-filtered-canary-implement-2026-04-14.md`) under the
quality-trader policy. Its admission record is a **WR table**, not a Source
Onboarding Scanner v0.2 shadow audit — the scanner did not exist then.

| Dimension | Toronto pre-canary (2026-04-14) | Jeddah now (2026-05-15) |
|---|---|---|
| cycles | UNKNOWN (no scanner v0.2 record) | 6 (Opus: ~7) |
| edge_hits | UNKNOWN | 4 (Opus: 4–5) |
| best_edge | UNKNOWN | 30.2% |
| Trader/WR evidence used | WR 75% n=4 (whitelist table) | WR 87.5% n=8 |
| Mapping | (not captured in scanner-v2 form) | ICAO OEJN + WU OEJN; no NOAA |
| Gating regime | Quality-trader policy, no n>=10 shadow gate | Scanner v0.2 with shadow gate |

**Caveat:** Apples-to-apples comparison **UNKNOWN** — the gating regime
changed. Toronto's path does not certify Jeddah's path; Opus should decide
whether ICAO-only/WU is acceptable for promotion review on its own merits.

---

## 4. Proposed Promotion Criteria

| # | Criterion | Status | Notes |
|---|---|---|---|
| C1 | `shadow_cycles >= 10` | **PENDING** | 6 observed; ~4 more cycles needed. Primary temporal blocker. |
| C2 | edge_hits at final threshold | **PENDING** | 4 observed; ratio healthy but below final n. |
| C3 | edge_hits / cycles stable | **PENDING** | 0.67 in small sample; reassess at n>=10. |
| C4 | source stable (no `"unknown"` in `source_texts`) | **MET** | Only `polymarket_market_price` seen for Jeddah. |
| C5 | settlement/source not unknown | **PARTIAL** | Source confirmed (WU OEJN, polymarket_market_price); NOAA path absent. Acceptable for ICAO-only path subject to Opus decision. |
| C6 | `noaa_station_id` resolved | **PENDING_FOR_NOAA_PATH** | Hard blocker only for NOAA / observed-audit path. **Not** a hard blocker for an ICAO-only/WU OEJN promotion review. |
| C7 | No recent drift | **UNKNOWN** | No drift logged; not actively monitored for Jeddah. |
| C8 | No policy conflict | **MET** | Already in `QUALITY_TRADER_CITIES_WHITELIST` (P5); no conflict. |
| C9 | No risk blocker | **MET** | Currently LOG_ONLY/shadow; no exposure. |
| C10 | **Opus must decide whether ICAO-only / WU OEJN is acceptable as promotion path** | **OPUS_DECISION_REQUIRED** | Key gating question once shadow accrues. |
| C11 | Opus review required before promotion | **PENDING** | Triggered once C1–C3 land. |

Aggregate gate: **NOT_READY** — primarily because of C1/C2 (temporal shadow
maturation) and C10 (Opus path decision). C6 is **not** treated as an absolute
structural blocker for Jeddah.

---

## 5. What Remains to Observe

Concrete unblockers (no new tooling assumed):

- **Shadow cycles:** ~4 additional cycles to reach n>=10. Accrues passively via scanner.
- **Edge hits:** 1–2 more hits at edge>=25–30% to confirm hit density is not small-sample artifact.
- **Stability:** confirm edge_hits/cycles ratio holds at n>=10.
- **Source drift check:** ensure `source_texts` does not drift to `"unknown"`.
- **`noaa_station_id` (optional, not required for ICAO-only path):** if a NOAA
  station for OEJN becomes available, attach it — strengthens the case but is
  not a prerequisite under the ICAO-only/WU path.

Trigger to reopen:
- `shadow_cycles>=10` reached AND edge ratio still stable, **OR**
- any new drift / source ambiguity flagged by the scanner.

---

## 6. Current Verdict

**NOT_READY_WAIT_SHADOW.**

Rationale (in order of weight):
1. `shadow_cycles < 10` — primary blocker, temporal maturation pending.
2. `edge_hits` below final threshold; ratio looks good but n too small to be confident.
3. Opus decision pending: is the ICAO-only / WU OEJN path acceptable for promotion review (C10)?

Jeddah is **not** structurally blocked the way an unmapped city would be (e.g.
no equivalence to a city lacking both ICAO and WU). It has mapping, source
text, and trader/shadow signal — it simply has not matured yet. The NOAA gap
constrains the audit path, not the promotion candidacy.

---

## 7. Next Trigger

> **Reopen when** `shadow_cycles >= 10` **AND** edge ratio remains stable
> (edge_hits/cycles consistent with current ~0.67, no decay). At that point
> request Opus review specifically to decide whether the **ICAO-only / WU
> OEJN** path is acceptable for promoting Jeddah toward active operation.
> Resolving `noaa_station_id` would strengthen the case but is **not** a
> required precondition for the Opus review under the ICAO-only path, unless
> policy explicitly says otherwise.
> Escalate immediately if `source_texts` drifts to `"unknown"` or other
> ambiguity surfaces.

---

## Verification

- Read-only dossier. No code, tests, env, DB, whitelist, policy, scheduler,
  BANKROLL, Fase C, observed_vs_forecast, Telegram, or source mappings touched.
- Source data: `docs/source_audits/candidate_source_onboarding_audit.md`
  (Railway live scan 2026-05-15), Opus snapshot ("~7 cycles, 4–5 edge_hits,
  best_edge 30.2%"), and `bot.py` RESOLUTION_STATIONS v10.6.28 (Jeddah OEJN +
  WU URL, NOAA vacío para OEJN).
- `git diff --check`: clean.
