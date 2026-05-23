#!/usr/bin/env python3
"""
Trader vs Bot Gap Report v1 — first consumer of the Market Evidence Ledger.

LOG_ONLY read-only tool. Does not modify bot.py, runtime state, or trading
logic. Output is analysis only; no row in this report authorizes BUY/SELL/SKIP
or policy changes.

Data sources (all read-only, from --data-dir):
  bot_signal_evaluations.jsonl   (BSE) — bot edge evaluations per signal
  blocked_signals_resolutions.jsonl (BSR) — trader signals with outcomes
  signals_crosscheck.jsonl       (SCX) — cycle-level aggregate, context only

Join: BSE.eval_key <-> BSR.match_key  (see docs/instrumentation/bot_evaluation_capture.md)

NOTE on join semantics:
  - join_confidence (HIGH/MEDIUM/LOW/NONE) describes market identity per §3.2 of the
    ledger contract, NOT whether a BSE evaluation was matched.
  - bot_eval_joined (bool) is the separate flag for actual BSE eval_key <-> match_key join.
  - identity_available_rows: BSR rows with condition_id or market_id (Polymarket primary).
  - bot_evaluation_joined_rows: BSR rows with a real BSE eval_key match.
  - bot_evaluation_missing_rows: v2+ BSR rows with match_key but no BSE match.
  - legacy_unjoinable_rows: v1 BSR rows missing key fields (city_mode, reason_blocked).

NOTE on evaluation_stage_status:
  Distinguishes HOW would_buy=False was reached. Three states:
  - POLICY_BLOCKED_BEFORE_EDGE_EVALUATION: our_prob=None; the bot was blocked by a policy
    gate (condition_filtered, shadow_only, city_blocked) BEFORE computing any probability
    or edge. The bot structurally never reached the forecasting/edge step.
  - EDGE_EVALUATED_NO_BUY: our_prob is not None AND bot_edge_pct_at_signal is not None;
    the bot computed probability and edge but found insufficient edge to buy.
  - EDGE_POSITIVE_BUT_POLICY_BLOCKED: our_prob is not None AND a policy gate blocked
    after probability computation (e.g. fuera_allowlist blocks after our_prob is known).
  - UNKNOWN_EVALUATION_STAGE: data insufficient to determine.
  - NOT_AVAILABLE: no BSE join exists.

  A CANDIDATE_FILTERED_WINNER with evaluation_stage_status=POLICY_BLOCKED_BEFORE_EDGE_EVALUATION
  indicates a market selection policy gap, NOT a model prediction failure. The bot never
  assessed whether the trade would have been profitable; the condition policy prevented it.

NOTE on temporal alignment:
  BSE rows are selected by EARLIEST ts_utc per eval_key (first bot evaluation of that
  market). temporal_alignment_status = VERIFIED when BSE ts_utc is before the market
  date_iso (bot evaluated before market resolution day). UNVERIFIED when same-day or
  after. NOT_AVAILABLE when no BSE match.
  Any row with temporal_alignment_status != VERIFIED must carry the flag
  'temporal_alignment_unverified' and fails the gate 'temporal_alignment_verified'.

Classification dimensions (§9.3, docs/market_evidence_ledger_contract.md):
  1. Trader outcome  (win_for_trader)
  2. Bot evaluation  (would_buy from BSE join, UNKNOWN if not joined)
  3. Execution status (derived from city_mode_at_record_time + reason_blocked)

See docs/market_evidence_ledger_contract.md for full schema and gate definitions.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any

SCHEMA_VERSION_OUTPUT = 4  # bumped: qt_gate_sub_reason join from skip_log added

# ---------------------------------------------------------------------------
# Field derivation helpers
# ---------------------------------------------------------------------------

def _derive_execution_status(bsr: dict) -> str:
    mode = bsr.get("city_mode_at_record_time")
    reason = bsr.get("reason_blocked", "")

    if mode == "blocked":
        return "BLOCKED_POLICY"
    if mode == "shadow":
        return "SHADOW_ONLY"
    if mode in ("canary", "active"):
        if reason and "source" in str(reason).lower():
            return "SOURCE_BLOCKED"
        return "BLOCKED_POLICY"
    # No city_mode available (v1 rows or missing field)
    return "UNKNOWN"


def _derive_blocking_gate(bsr: dict) -> str | None:
    mode = bsr.get("city_mode_at_record_time")
    reason = bsr.get("reason_blocked", "")
    detail = bsr.get("block_reason_detail", "")

    if mode in ("blocked", "shadow"):
        return "city_mode"

    if reason == "condition_filtered":
        return "condition_policy"
    if reason in ("fuera_allowlist", "out_of_whitelist"):
        return "condition_policy"
    if reason and "source" in str(reason).lower():
        return "source_fidelity"
    if reason == "mixed":
        detail_lower = str(detail).lower()
        if "blocked_city" in detail_lower or "shadow" in detail_lower:
            return "city_mode"
        if "source" in detail_lower:
            return "source_fidelity"
        if "condition" in detail_lower or "allowlist" in detail_lower:
            return "condition_policy"
        return "insufficient_data"
    if mode is None:
        return None  # v1 row, unknown
    return "none"


def _temporal_alignment_status(bse: dict | None, market_date: str | None) -> str:
    """
    VERIFIED: BSE ts_utc date is strictly before the market date_iso.
    UNVERIFIED: BSE ts_utc is on or after market date, or timestamps are missing.
    NOT_AVAILABLE: no BSE match.
    """
    if bse is None:
        return "NOT_AVAILABLE"
    ts = bse.get("ts_utc", "")
    if not ts or not market_date:
        return "UNVERIFIED"
    try:
        eval_date = ts[:10]  # "YYYY-MM-DD"
        if eval_date < market_date:
            return "VERIFIED"
        return "UNVERIFIED"
    except (TypeError, IndexError):
        return "UNVERIFIED"


# Gates that indicate a policy check runs BEFORE probability/edge computation.
# When decision_gate is one of these AND our_prob is None, the bot never reached
# the forecasting step (condition or city policy blocked first).
_PRE_EVAL_POLICY_GATES = frozenset({
    "condition_filtered",
    "shadow_only",
    "shadow_only_override",
    "city_blocked",
    "source_blocked",
    "city_mode",
})


def _derive_evaluation_stage(bse: dict | None, would_buy: bool | None) -> str:
    """
    Determine at which stage the bot stopped evaluating this market.

    Returns one of:
      POLICY_BLOCKED_BEFORE_EDGE_EVALUATION — policy gate stopped bot before any
        probability/edge calculation (our_prob is None, gate in _PRE_EVAL_POLICY_GATES)
      EDGE_EVALUATED_NO_BUY — bot computed probability and edge; edge insufficient
      EDGE_POSITIVE_BUT_POLICY_BLOCKED — probability computed but policy gate blocked
        before or after edge threshold (our_prob not None, policy gate present)
      UNKNOWN_EVALUATION_STAGE — data insufficient to determine
      NOT_AVAILABLE — no BSE join
    """
    if bse is None:
        return "NOT_AVAILABLE"

    gate = bse.get("decision_gate") or bse.get("skip_or_block_reason") or ""
    our_prob = bse.get("our_prob")
    edge_pct = bse.get("bot_edge_pct_at_signal")

    if our_prob is None and gate in _PRE_EVAL_POLICY_GATES:
        # Policy gate fired before forecasting pipeline ran
        return "POLICY_BLOCKED_BEFORE_EDGE_EVALUATION"

    if our_prob is not None:
        # Probability was computed; check if edge was also calculated
        if edge_pct is not None:
            if would_buy is False:
                return "EDGE_EVALUATED_NO_BUY"
            # would_buy=True shouldn't appear in BSR (those are BUYs, not blocked signals)
            return "UNKNOWN_EVALUATION_STAGE"
        # our_prob present but edge_pct null: probability computed, policy blocked after
        if gate in _PRE_EVAL_POLICY_GATES or "allowlist" in gate or "fuera" in gate:
            return "EDGE_POSITIVE_BUT_POLICY_BLOCKED"
        return "EDGE_EVALUATED_NO_BUY"

    return "UNKNOWN_EVALUATION_STAGE"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify_row(
    win_for_trader: bool | None,
    would_buy: bool | None,
    exec_status: str,
) -> str:
    """Apply §9.4 classification table. Returns learning_classification string."""
    if win_for_trader is None or exec_status == "UNKNOWN" or would_buy is None:
        return "NO_ACTION_INSUFFICIENT_EVIDENCE"

    if win_for_trader:
        if would_buy:
            if exec_status == "SOURCE_BLOCKED":
                return "SOURCE_FIDELITY_BLOCKED"
            if exec_status in ("BLOCKED_POLICY", "SHADOW_ONLY"):
                return "CANDIDATE_MISSED_OPPORTUNITY"
            return "NO_ACTION_INSUFFICIENT_EVIDENCE"
        else:
            return "CANDIDATE_FILTERED_WINNER"
    else:  # trader lost
        if would_buy:
            if exec_status in ("BLOCKED_POLICY", "SHADOW_ONLY", "SOURCE_BLOCKED"):
                return "PROTECTIVE_POLICY_EVIDENCE"
            return "NO_ACTION_INSUFFICIENT_EVIDENCE"
        else:
            if exec_status in ("FILTERED_NO_EDGE", "PRICE_OUT_OF_RANGE", "BLOCKED_POLICY"):
                return "PROTECTIVE_FILTER_EVIDENCE"
            return "NO_ACTION_INSUFFICIENT_EVIDENCE"


def _gates_status(row: dict, bsr: dict | None, bse: dict | None) -> tuple[list, list]:
    """Return (gates_passed, gates_missing) per §5.2 of ledger contract."""
    passed = []
    missing = []

    # Gate 1: market identity joinable with confidence >= MEDIUM
    jc = row.get("join_confidence", "NONE")
    if jc in ("HIGH", "MEDIUM"):
        passed.append("identity_joinable")
    else:
        missing.append("identity_joinable")

    # Gate 2: price comparable — price_bucket known as proxy
    if bsr and bsr.get("price_bucket"):
        passed.append("price_bucket_known")
    else:
        missing.append("price_bucket_known")

    # Gate 3: outcome resolved
    resolved = bsr.get("resolved") if bsr else None
    win = bsr.get("win_for_trader") if bsr else None
    if resolved and win is not None:
        passed.append("outcome_resolved")
    else:
        missing.append("outcome_resolved")

    # Gate 4: actual_execution_status derivable
    if row.get("actual_execution_status") not in ("UNKNOWN", None):
        passed.append("execution_status_known")
    else:
        missing.append("execution_status_known")

    # Gate 5: counterfactual (would_buy from BSE join)
    if row.get("bot_eval_joined") and bse and bse.get("would_buy") is not None:
        passed.append("counterfactual_estimable")
    else:
        missing.append("counterfactual_estimable")

    # Gate 5b: temporal alignment verified (required for CONFIRMED status)
    tal = row.get("temporal_alignment_status", "NOT_AVAILABLE")
    if tal == "VERIFIED":
        passed.append("temporal_alignment_verified")
    else:
        missing.append("temporal_alignment_verified")

    # Gate 6: no blocking data quality issues
    dq = row.get("data_quality_flags", [])
    blocking_dq = [f for f in dq if f in (
        "bot_evaluation_null",
        "settlement_fidelity_unknown",
        "v1_schema_missing_fields",
        "temporal_alignment_unverified",
    )]
    if not blocking_dq:
        passed.append("no_blocking_data_quality")
    else:
        missing.append("no_blocking_data_quality")

    return passed, missing


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def _cutoff_from_days(days: int | None) -> datetime | None:
    if days is None:
        return None
    return datetime.now(tz=timezone.utc) - timedelta(days=days)


def _bsr_date(bsr: dict) -> datetime | None:
    ts = bsr.get("checked_at")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Core report builder
# ---------------------------------------------------------------------------

def _build_skip_qt_index(skip_log_path: str) -> dict[str, str | None]:
    """
    Build index: qt_match_key -> exact_range_gate_reason.

    Key format: city|date_iso|condition|threshold|unit (same as eval_key/match_key).
    Source: skip_log.jsonl extras.qt_match_key + extras.exact_range_gate_reason.

    Per-key strategy: collect all distinct sub-reasons across cycles. If all agree,
    return the single sub-reason. If they conflict (AMBIGUOUS), return None so the
    caller can flag AMBIGUOUS. Conflicts observed on Railway: 0.
    """
    if not os.path.exists(skip_log_path):
        return {}

    per_key: dict[str, set[str]] = {}
    for row in _load_jsonl(skip_log_path):
        extras = row.get("extras") or {}
        k = extras.get("qt_match_key")
        sub = extras.get("exact_range_gate_reason")
        if k and sub:
            per_key.setdefault(k, set()).add(sub)

    result: dict[str, str | None] = {}
    for k, subs in per_key.items():
        result[k] = next(iter(subs)) if len(subs) == 1 else None  # None = ambiguous
    return result


def build_report(data_dir: str, days: int | None = None) -> dict:
    bse_path = os.path.join(data_dir, "bot_signal_evaluations.jsonl")
    bsr_path = os.path.join(data_dir, "blocked_signals_resolutions.jsonl")
    scx_path = os.path.join(data_dir, "signals_crosscheck.jsonl")
    skip_log_path = os.path.join(data_dir, "skip_log.jsonl")

    bsr_all = _load_jsonl(bsr_path)
    bse_all = _load_jsonl(bse_path)
    scx_all = _load_jsonl(scx_path)
    skip_qt_index = _build_skip_qt_index(skip_log_path)
    skip_log_loaded = os.path.exists(skip_log_path)

    cutoff = _cutoff_from_days(days)
    if cutoff:
        bsr_all = [
            r for r in bsr_all
            if (_bsr_date(r) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff
        ]

    # Index BSE by eval_key — keep EARLIEST evaluation per key.
    # Rationale: first bot assessment is closest to when the trader may have signaled;
    # later evaluations may reflect changed market conditions (price drift, new forecasts).
    bse_index: dict[str, dict] = {}
    for row in bse_all:
        k = row.get("eval_key")
        if k:
            existing = bse_index.get(k)
            if existing is None or row.get("ts_utc", "") < existing.get("ts_utc", ""):
                bse_index[k] = row

    scx_all_count = len(scx_all)
    generated_at = datetime.now(tz=timezone.utc).isoformat()
    rows_out = []

    for bsr in bsr_all:
        mk = bsr.get("match_key")
        sv = bsr.get("schema_version")  # None = v1 (no schema_version field)

        # ---- Bot evaluation join (Dimension 2) ----
        # bot_eval_joined = True ONLY when BSE row with matching eval_key exists.
        # This is the actual BSE <-> BSR join. It is SEPARATE from market identity.
        bse = bse_index.get(mk) if mk else None
        bot_eval_joined = bse is not None

        # ---- Market identity confidence per §3.2 ----
        # HIGH  = Polymarket primary identity (condition_id or market_id)
        # MEDIUM = eval_key <-> match_key join (bot eval joined)
        # LOW   = match_key present but no BSE match (market semantically identified)
        # NONE  = v1 row without match_key or primary identity
        has_polymarket_identity = bool(bsr.get("condition_id") or bsr.get("market_id"))
        if has_polymarket_identity:
            join_confidence = "HIGH"
        elif bot_eval_joined:
            join_confidence = "MEDIUM"
        elif mk:
            join_confidence = "LOW"
        else:
            join_confidence = "NONE"

        # ---- Temporal alignment ----
        market_date = bsr.get("date")  # "YYYY-MM-DD"
        tal_status = _temporal_alignment_status(bse, market_date)

        # ---- Evaluation stage ----
        eval_stage = _derive_evaluation_stage(bse, bse.get("would_buy") if bse else None)

        # ---- Data quality flags ----
        dq_flags: list[str] = []
        if sv is None:
            dq_flags.append("v1_schema_missing_fields")
        if bsr.get("settlement_fidelity_status") in ("unverified", "unknown", None):
            dq_flags.append("settlement_fidelity_unknown")
        if bsr.get("bot_evaluation_join_status") == "missing" and not bot_eval_joined:
            dq_flags.append("bot_evaluation_join_missing")
        if not bot_eval_joined and sv is not None:
            dq_flags.append("bot_would_buy_unknown")
        if tal_status == "UNVERIFIED":
            dq_flags.append("temporal_alignment_unverified")

        # ---- Execution status and blocking gate (Dimension 3) ----
        if sv is None:
            exec_status = "UNKNOWN"
            blocking_gate = None
        else:
            exec_status = _derive_execution_status(bsr)
            blocking_gate = _derive_blocking_gate(bsr)

        # ---- Core dimensions ----
        win_for_trader: bool | None = bsr.get("win_for_trader")
        would_buy: bool | None = bse.get("would_buy") if bse else None

        # ---- Quality-trader gate sub-reason (from skip_log join) ----
        # Applies only when reason_blocked="condition_filtered" (QT gate path).
        # Join key: BSR.match_key <-> skip_log.extras.qt_match_key (same format as eval_key).
        # NOT_FOUND means skip_log had no entry for this key (pre-feature or rotated data).
        # AMBIGUOUS means multiple distinct sub-reasons existed for the same key (extremely rare).
        qt_sub_reason: str | None = None
        if bsr.get("reason_blocked") == "condition_filtered" and mk:
            if mk in skip_qt_index:
                raw_sub = skip_qt_index[mk]
                if raw_sub is None:
                    qt_join_status = "AMBIGUOUS"
                    dq_flags.append("qt_sub_reason_ambiguous")
                else:
                    qt_sub_reason = raw_sub
                    qt_join_status = "MATCHED"
            elif skip_log_loaded:
                qt_join_status = "NOT_FOUND"
            else:
                qt_join_status = "SKIP_LOG_MISSING"
        else:
            qt_join_status = "NOT_APPLICABLE"

        # ---- Classification ----
        classification = _classify_row(win_for_trader, would_buy, exec_status)

        out_row: dict[str, Any] = {
            "match_key": mk,
            "city": bsr.get("city"),
            "date": market_date,
            "condition": bsr.get("condition"),
            "trader": bsr.get("trader"),
            # Identity and join status
            "join_confidence": join_confidence,
            "has_polymarket_identity": has_polymarket_identity,
            "bot_eval_joined": bot_eval_joined,
            "bsr_schema_version": sv if sv is not None else "v1_legacy",
            # Dimension 1: trader outcome
            "win_for_trader": win_for_trader,
            "trader_historical_wr": bsr.get("trader_historical_wr"),
            "outcome": bsr.get("outcome"),
            "avg_price_entered": bsr.get("avg_price_entered"),
            "price_bucket": bsr.get("price_bucket"),
            # Dimension 2: bot evaluation
            "bot_would_buy": would_buy,
            "bot_edge_pct": bse.get("bot_edge_pct_at_signal") if bse else None,
            "bot_decision_gate": bse.get("decision_gate") if bse else None,
            "bot_skip_reason": bse.get("skip_or_block_reason") if bse else None,
            "bot_eval_ts_utc": bse.get("ts_utc") if bse else None,
            "bot_evaluation_source": bsr.get(
                "bot_evaluation_source",
                "FIELD_MISSING" if sv is None else "unknown",
            ),
            # Temporal alignment
            "temporal_alignment_status": tal_status,
            # Evaluation stage: HOW would_buy=False was reached (see module docstring)
            "evaluation_stage_status": eval_stage,
            # Dimension 3: execution/block
            "actual_execution_status": exec_status,
            "blocking_gate": blocking_gate,
            "city_mode_at_record_time": bsr.get("city_mode_at_record_time"),
            "reason_blocked": bsr.get("reason_blocked"),
            "block_reason_detail": bsr.get("block_reason_detail"),
            # Polymarket identity
            "condition_id": bsr.get("condition_id"),
            "market_id": bsr.get("market_id"),
            # Resolution
            "resolved": bsr.get("resolved"),
            "resolution_source": bsr.get("resolution_source"),
            "settlement_fidelity_status": bsr.get("settlement_fidelity_status"),
            # Provenance
            "data_quality_flags": dq_flags,
            # Classification
            "learning_classification": classification,
            # Quality-trader gate sub-reason (skip_log join)
            "qt_gate_sub_reason": qt_sub_reason,
            "qt_gate_sub_reason_join_status": qt_join_status,
        }

        gates_passed, gates_missing = _gates_status(out_row, bsr, bse)
        out_row["gates_passed"] = gates_passed
        out_row["gates_missing"] = gates_missing

        rows_out.append(out_row)

    # ---- Summary counts ----
    cls_counts: dict[str, int] = {}
    exec_counts: dict[str, int] = {}
    confirmed_missed = 0
    identity_available = 0
    bot_eval_joined_count = 0
    bot_eval_missing = 0
    legacy_unjoinable = 0
    tal_distribution: dict[str, int] = {}
    eval_stage_distribution: dict[str, int] = {}
    qt_sub_reason_distribution: dict[str, int] = {}
    qt_join_status_distribution: dict[str, int] = {}

    for r in rows_out:
        c = r["learning_classification"]
        cls_counts[c] = cls_counts.get(c, 0) + 1
        e = r["actual_execution_status"]
        exec_counts[e] = exec_counts.get(e, 0) + 1
        if c == "CANDIDATE_MISSED_OPPORTUNITY" and not r["gates_missing"]:
            confirmed_missed += 1
        if r.get("has_polymarket_identity"):
            identity_available += 1
        if r.get("bot_eval_joined"):
            bot_eval_joined_count += 1
        elif r.get("bsr_schema_version") != "v1_legacy":
            bot_eval_missing += 1
        else:
            legacy_unjoinable += 1
        tal = r.get("temporal_alignment_status", "NOT_AVAILABLE")
        tal_distribution[tal] = tal_distribution.get(tal, 0) + 1
        es = r.get("evaluation_stage_status", "NOT_AVAILABLE")
        eval_stage_distribution[es] = eval_stage_distribution.get(es, 0) + 1
        qjs = r.get("qt_gate_sub_reason_join_status", "NOT_APPLICABLE")
        qt_join_status_distribution[qjs] = qt_join_status_distribution.get(qjs, 0) + 1
        if qjs == "MATCHED":
            qsr = r.get("qt_gate_sub_reason") or "UNKNOWN"
            qt_sub_reason_distribution[qsr] = qt_sub_reason_distribution.get(qsr, 0) + 1

    blocking_fields: dict[str, int] = {}
    for r in rows_out:
        for f in r.get("data_quality_flags", []):
            blocking_fields[f] = blocking_fields.get(f, 0) + 1

    # Sample for Opus: rows with actual BSE join and trader win
    sample_for_opus = [
        r for r in rows_out
        if r.get("bot_eval_joined") and r["win_for_trader"] is True
    ][:20]

    report = {
        "schema_version": SCHEMA_VERSION_OUTPUT,
        "generated_at": generated_at,
        "report_type": "trader_vs_bot_gap_report_v1",
        "ledger_contract_ref": "docs/market_evidence_ledger_contract.md",
        "consumer_type": "LOG_ONLY",
        "data_dir": data_dir,
        "days_filter": days,
        "artifact_sources": {
            "bot_signal_evaluations": {
                "path": bse_path,
                "rows_loaded": len(bse_all),
                "unique_eval_keys": len(bse_index),
                "note": "indexed by EARLIEST ts_utc per eval_key",
            },
            "blocked_signals_resolutions": {"path": bsr_path, "rows_loaded": len(bsr_all)},
            "signals_crosscheck": {
                "path": scx_path,
                "rows_loaded": scx_all_count,
                "note": "cycle-level aggregate only — not joined per-market",
            },
            "skip_log": {
                "path": skip_log_path,
                "loaded": skip_log_loaded,
                "unique_qt_match_keys": len(skip_qt_index),
                "note": (
                    "indexed by extras.qt_match_key for quality-trader gate sub-reason join. "
                    "Coverage starts from when exact_range_gate_reason was added to skip_log. "
                    "Rows before that date and rotated entries appear as NOT_FOUND."
                ),
            },
        },
        "summary": {
            "total_bsr_rows": len(rows_out),
            # Honest join breakdown — do NOT confuse identity with BSE eval join
            "identity_available_rows": identity_available,
            "bot_evaluation_joined_rows": bot_eval_joined_count,
            "bot_evaluation_missing_rows": bot_eval_missing,
            "legacy_unjoinable_rows": legacy_unjoinable,
            "temporal_alignment_distribution": tal_distribution,
            "evaluation_stage_distribution": eval_stage_distribution,
            "qt_gate_sub_reason_distribution": qt_sub_reason_distribution,
            "qt_gate_sub_reason_join_status_distribution": qt_join_status_distribution,
            "classification_distribution": cls_counts,
            "execution_status_distribution": exec_counts,
            "confirmed_missed_opportunities": confirmed_missed,
            "blocking_data_quality_fields": blocking_fields,
        },
        "data_gaps": [
            {
                "artifact": "blocked_signals_resolutions.jsonl (v1 rows)",
                "gap_type": "v1_schema_missing_fields",
                "rows_affected": blocking_fields.get("v1_schema_missing_fields", 0),
                "impact": "No city_mode_at_record_time, reason_blocked, or "
                          "bot_evaluation_join_status. Classified as "
                          "NO_ACTION_INSUFFICIENT_EVIDENCE.",
            },
            {
                "artifact": "bot_signal_evaluations.jsonl",
                "gap_type": "bot_would_buy_unknown",
                "rows_affected": blocking_fields.get("bot_would_buy_unknown", 0),
                "impact": "BSR v2+ rows without matching BSE eval_key. "
                          "would_buy cannot be determined; bot evaluation dimension missing.",
            },
            {
                "artifact": "blocked_signals_resolutions.jsonl (settlement)",
                "gap_type": "settlement_fidelity_unknown",
                "rows_affected": blocking_fields.get("settlement_fidelity_unknown", 0),
                "impact": "All settlement_fidelity_status are 'unverified'. "
                          "Gate 'no_blocking_data_quality' fails for all rows.",
            },
            {
                "artifact": "bot_signal_evaluations.jsonl (temporal)",
                "gap_type": "temporal_alignment_unverified",
                "rows_affected": blocking_fields.get("temporal_alignment_unverified", 0),
                "impact": "BSE ts_utc is not strictly before the market date. "
                          "Cannot confirm bot evaluated before market resolution. "
                          "Gate 'temporal_alignment_verified' fails.",
            },
            {
                "artifact": "skip_log.jsonl",
                "gap_type": "qt_sub_reason_partial_coverage",
                "rows_affected": qt_join_status_distribution.get("NOT_FOUND", 0),
                "impact": (
                    "condition_filtered rows before exact_range_gate_reason was instrumented "
                    "in skip_log, or with rotated skip_log entries, cannot have qt_gate_sub_reason "
                    "resolved. These appear as qt_gate_sub_reason_join_status=NOT_FOUND. "
                    "No sub-reason is inferred; learning_classification is unchanged."
                ),
            },
            {
                "artifact": "signals_crosscheck.jsonl",
                "gap_type": "crosscheck_is_aggregate_only",
                "rows_affected": scx_all_count,
                "impact": "signals_crosscheck is a cycle-level city aggregate; "
                          "no per-market eval_key or bot_evaluation. "
                          "Cannot be joined as individual market rows. Context only.",
            },
        ],
        "rows": rows_out,
        "sample_for_opus_review": sample_for_opus,
    }

    return report


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    sep = " | ".join("---" for _ in headers)
    lines = ["| " + " | ".join(headers) + " |", "| " + sep + " |"]
    for r in rows:
        lines.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(lines)


def format_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# Trader vs Bot Gap Report v1",
        "",
        f"**Generated:** {report['generated_at']}  ",
        f"**Type:** `{report['report_type']}` / `{report['consumer_type']}`  ",
        f"**Ledger contract:** `{report['ledger_contract_ref']}`  ",
        f"**Days filter:** {report['days_filter'] or 'all'}",
        "",
        "## Summary — Join Breakdown",
        "",
        f"- BSR rows total: **{s['total_bsr_rows']}**",
        f"- Identity available (condition_id or market_id): **{s['identity_available_rows']}**",
        f"- Bot evaluation joined (BSR.match_key = BSE.eval_key): **{s['bot_evaluation_joined_rows']}**",
        f"- Bot evaluation missing (v2+ BSR, no BSE match): **{s['bot_evaluation_missing_rows']}**",
        f"- Legacy unjoinable (v1 BSR, key fields absent): **{s['legacy_unjoinable_rows']}**",
        f"- Confirmed missed opportunities (all gates passed): **{s['confirmed_missed_opportunities']}**",
        "",
        "> NOTE: 'Identity available' and 'Bot evaluation joined' are independent dimensions.",
        "> A row can have Polymarket identity (condition_id) but no BSE join, and vice versa.",
        "",
        "## Temporal Alignment Distribution",
        "",
    ]
    tal_rows = sorted(s["temporal_alignment_distribution"].items(), key=lambda x: -x[1])
    lines.append(_md_table(["Status", "Count"], [[k, str(v)] for k, v in tal_rows]))
    lines += [
        "",
        "## Evaluation Stage Distribution",
        "> How would_buy=False was reached for bot_eval_joined rows.",
        "> POLICY_BLOCKED_BEFORE_EDGE_EVALUATION = bot never computed probability/edge (our_prob=None).",
        "> EDGE_EVALUATED_NO_BUY = bot computed probability+edge, edge insufficient.",
        "> EDGE_POSITIVE_BUT_POLICY_BLOCKED = probability computed, then policy gate blocked.",
        "",
    ]
    es_rows = sorted(s["evaluation_stage_distribution"].items(), key=lambda x: -x[1])
    lines.append(_md_table(["Evaluation Stage", "Count"], [[k, str(v)] for k, v in es_rows]))
    lines += [
        "",
        "## Quality-Trader Gate Sub-Reason (skip_log join)",
        "> Applies to condition_filtered rows only. Join key: BSR.match_key = skip_log.extras.qt_match_key.",
        "> NOT_FOUND = skip_log had no entry (pre-feature or rotated). NOT_APPLICABLE = not a condition_filtered row.",
        "",
    ]
    qt_join_rows = sorted(
        s["qt_gate_sub_reason_join_status_distribution"].items(), key=lambda x: -x[1]
    )
    lines.append(_md_table(["Join Status", "Count"], [[k, str(v)] for k, v in qt_join_rows]))
    lines += [""]
    qt_sub_rows = sorted(s["qt_gate_sub_reason_distribution"].items(), key=lambda x: -x[1])
    if qt_sub_rows:
        lines += [
            "### Sub-reason breakdown (MATCHED rows only)",
            "",
        ]
        lines.append(_md_table(["Sub-Reason", "Count"], [[k, str(v)] for k, v in qt_sub_rows]))
    lines += [
        "",
        "## Classification Distribution",
        "> Only rows with bot_eval_joined=True have all 3 dimensions classified.",
        "",
    ]
    cls_rows = sorted(s["classification_distribution"].items(), key=lambda x: -x[1])
    lines.append(_md_table(["Classification", "Count"], [[k, str(v)] for k, v in cls_rows]))
    lines += [
        "",
        "## Execution Status Distribution",
        "",
    ]
    exec_rows = sorted(s["execution_status_distribution"].items(), key=lambda x: -x[1])
    lines.append(_md_table(["Execution Status", "Count"], [[k, str(v)] for k, v in exec_rows]))
    lines += [
        "",
        "## Data Gaps",
        "",
    ]
    for gap in report["data_gaps"]:
        lines += [
            f"### `{gap['gap_type']}`",
            f"- **Artifact:** {gap['artifact']}",
            f"- **Rows affected:** {gap['rows_affected']}",
            f"- **Impact:** {gap['impact']}",
            "",
        ]
    lines += [
        "## Blocking Data Quality Fields",
        "",
    ]
    bq = s["blocking_data_quality_fields"]
    if bq:
        lines.append(_md_table(
            ["Field", "Rows"],
            [[k, str(v)] for k, v in sorted(bq.items(), key=lambda x: -x[1])],
        ))
    else:
        lines.append("_None_")
    lines += [
        "",
        "## Sample for Opus Review",
        "_(rows with bot_eval_joined=True and trader win, up to 20)_",
        "",
    ]
    sample = report.get("sample_for_opus_review", [])
    if sample:
        hdrs = [
            "match_key", "win_for_trader", "bot_would_buy",
            "eval_stage", "actual_exec_status", "blocking_gate",
            "temporal_align", "classification",
        ]
        sample_rows = []
        for r in sample:
            sample_rows.append([
                r.get("match_key", ""),
                str(r.get("win_for_trader", "")),
                str(r.get("bot_would_buy", "")),
                r.get("evaluation_stage_status", ""),
                r.get("actual_execution_status", ""),
                str(r.get("blocking_gate", "")),
                r.get("temporal_alignment_status", ""),
                r.get("learning_classification", ""),
            ])
        lines.append(_md_table(hdrs, sample_rows))
    else:
        lines.append("_No rows with bot_eval_joined=True and trader win found._")
    lines += [
        "",
        "---",
        "",
        "_This report is LOG_ONLY. It does not authorize BUY/SELL/SKIP or policy changes._",
        "_Consumer of docs/market_evidence_ledger_contract.md - not a source of truth._",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trader vs Bot Gap Report v1 — LOG_ONLY ledger consumer. "
                    "Reads bot_signal_evaluations.jsonl + blocked_signals_resolutions.jsonl. "
                    "Does not modify bot.py or any runtime artifact."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing the JSONL data files (default: data/)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Filter BSR rows to the last N days (default: all)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Write JSON report to data/intelligence/<filename>. "
             "Must be explicitly requested (not automatic).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print JSON report to stdout",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print Markdown summary to stdout",
    )
    args = parser.parse_args()

    if not args.json_output and not args.markdown and not args.out:
        args.markdown = True

    report = build_report(data_dir=args.data_dir, days=args.days)

    if args.json_output:
        print(json.dumps(report, indent=2, default=str))

    if args.markdown:
        if args.json_output:
            print("\n" + "=" * 60 + "\n")
        print(format_markdown(report))

    if args.out:
        out_path = os.path.join("data", "intelligence", args.out)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"[gap_report] Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
