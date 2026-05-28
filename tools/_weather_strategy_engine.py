"""Private helper for bot_brain.py --scope weather_strategy.

V1 invariants:
  LIVE_POLICY_ELIGIBLE = false (hardcoded)
  P&L_CANONICAL_CONFIRMED = false (canonical_source=none until Outcome Resolver deployed)
  autoexecute = false
  disclaimer = LOG_ONLY / NO_ACTION

No BUY/SELL/SKIP. No BANKROLL mutations. No DB writes. No Railway writes.
No Truth Pipeline activation. No env vars. No Phase 2 runtime changes.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_V1_DISCLAIMER = (
    "LOG_ONLY / NO_ACTION. V1 read-only. LIVE_POLICY_ELIGIBLE=false. "
    "No trading authorization, no BANKROLL mutation, no BUY/SELL/SKIP, "
    "no city-mode, no env var, no DB/Railway write, no Truth Pipeline activation."
)

VERDICT_KEEP_ACCUMULATING = "KEEP_ACCUMULATING_UNTIL_TRIGGER"
VERDICT_TRUTH_GAP = "TRUTH_GAP_BLOCKS_DECISION"
VERDICT_EXIT_CANDIDATE = "EXIT_POLICY_DESIGN_CANDIDATE"
VERDICT_COHORT_CANDIDATE = "COHORT_REVIEW_CANDIDATE"
VERDICT_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"


# ── IO helpers ────────────────────────────────────────────────────────────────

def _read_json(path: Path) -> tuple[Any, bool]:
    if not path.exists():
        return None, False
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), True
    except Exception:
        return None, False


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], bool]:
    if not path.exists():
        return [], False
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except Exception:
                continue
        return rows, True
    except Exception:
        return [], False


# ── P&L extraction ────────────────────────────────────────────────────────────

def _get_pnl_value(record: dict[str, Any]) -> float | None:
    """Extract diagnostic P&L from record top-level or close_context.pnl_cash."""
    for key in ("pnl", "realized_pnl", "pnl_cash"):
        v = record.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    cc = record.get("close_context")
    if isinstance(cc, dict):
        for key in ("pnl_cash", "pnl", "realized_pnl"):
            v = cc.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
    return None


# ── Match key derivation ──────────────────────────────────────────────────────

_SUPPORTED_CONDITIONS = frozenset({"exact", "at_or_above", "at_or_below"})

_QUESTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "exact": re.compile(
        r"be\s+(\d+(?:\.\d+)?)\s*°?([CF])\s+on\b",
        re.IGNORECASE,
    ),
    "at_or_above": re.compile(
        r"be\s+(\d+(?:\.\d+)?)\s*°?([CF])\s+or\s+higher\b",
        re.IGNORECASE,
    ),
    "at_or_below": re.compile(
        r"be\s+(\d+(?:\.\d+)?)\s*°?([CF])\s+or\s+below\b",
        re.IGNORECASE,
    ),
}


def derive_match_key_from_lifecycle_record(record: dict[str, Any]) -> dict[str, Any]:
    """Derive a BSR match key from lifecycle record fields conservatively.

    Uses city/date/condition first; question only for threshold+unit extraction.
    Returns:
      derived_match_key: str | None
      match_key_derivation_status: "derived" | "failed_closed"
      derivation_failure_reason: str | None
    Fails closed on any ambiguity.
    """
    city = str(record.get("city") or "").strip()
    date = _record_date(record).strip()
    condition = str(record.get("condition") or "").strip()
    question = str(record.get("question") or "").strip()

    def _fail(reason: str) -> dict[str, Any]:
        return {
            "derived_match_key": None,
            "match_key_derivation_status": "failed_closed",
            "derivation_failure_reason": reason,
        }

    if not city:
        return _fail("city_absent")
    if not date:
        return _fail("date_absent")
    if not condition:
        return _fail("condition_absent")
    if condition not in _SUPPORTED_CONDITIONS:
        return _fail(f"condition_unsupported:{condition}")
    if not question:
        return _fail("question_absent_cannot_extract_threshold")

    pattern = _QUESTION_PATTERNS[condition]
    m = pattern.search(question)

    if not m:
        for other_cond, other_pat in _QUESTION_PATTERNS.items():
            if other_cond != condition and other_pat.search(question):
                return _fail(
                    f"condition_contradiction:record_condition={condition}_question_implies={other_cond}"
                )
        return _fail("threshold_not_extractable_from_question")

    threshold_str = m.group(1)
    unit = m.group(2).upper()

    try:
        threshold_f = float(threshold_str)
        threshold_display = str(int(threshold_f)) if threshold_f == int(threshold_f) else threshold_str
    except ValueError:
        return _fail("threshold_parse_error")

    date_iso = date[:10] if len(date) >= 10 else date
    derived = f"{city}|{date_iso}|{condition}|{threshold_display}|{unit}"
    return {
        "derived_match_key": derived,
        "match_key_derivation_status": "derived",
        "derivation_failure_reason": None,
    }


# ── Experiment registry probes ────────────────────────────────────────────────

def _probe_phase2(data_dir: Path) -> dict[str, Any]:
    """Phase 2 is always PHASE2_STATE_NOT_MACHINE_READABLE in V1.

    No canonical machine-readable state persisted for exact/NO shadow experiment.
    Trigger T+30 = 2026-06-09. Any supporting artifacts are non-canonical.
    """
    path = data_dir / "exact_no_qt_match_evaluations_log_only.jsonl"
    rows, ok = _read_jsonl(path)
    result: dict[str, Any] = {
        "key": "PHASE_2",
        "status": "PHASE2_STATE_NOT_MACHINE_READABLE",
        "description": (
            "Phase 2 Recalibration general: exact/NO global shadow experiment (SHADOW_EXACT_NO_GLOBAL). "
            "Mixed-condition slice included. T+30 = 2026-06-09 (30 days from 2026-05-10 shadow activation). "
            "Exact slice protected/affected by: historical bugs (Seoul active during pause, "
            "match_key=None in lifecycle records), Phase 2 gate drift, S341. "
            "No canonical machine-readable state persisted in V1."
        ),
        "canonical_state": None,
        "trigger": "T+30 = 2026-06-09 (30 days from 2026-05-10 shadow activation)",
        "trigger_date": "2026-06-09",
        "decision_candidate": "Outcome Resolver R1 CODE after T+30 + Opus design + Pablo approval",
        "live_promotion_authorized": False,
        "shadow_exact_no_global_active": True,
        "mixed_condition_included": True,
        "exact_slice_protected": True,
        "exact_slice_known_issues": [
            "match_key_absent_in_lifecycle_records",
            "historical_gate_drift_Phase2_S341",
            "Seoul_active_during_pause_incident",
        ],
    }
    if ok and rows:
        non_seoul = [r for r in rows if str(r.get("city", "")).casefold() != "seoul"]
        result["supporting_artifact"] = {
            "path": str(path),
            "present": True,
            "row_count": len(rows),
            "non_seoul_rows": len(non_seoul),
            "note": (
                "LOG_ONLY supporting evidence only. "
                "Not canonical Phase 2 state. "
                "Do not recompute Phase 2 from this artifact."
            ),
        }
    else:
        result["supporting_artifact"] = {
            "path": str(path),
            "present": ok,
            "note": "LOG_ONLY artifact absent or empty.",
        }
    return result


def _probe_surviving_cohorts(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "bot_signal_evaluations.jsonl"
    rows, ok = _read_jsonl(path)
    if not ok:
        return {
            "key": "SURVIVING_COHORTS_BY_SIDE",
            "status": "DATA_GAP",
            "description": "Signal evaluations with side field (forward from 2026-05-26 Sesion 398)",
            "artifact": str(path),
            "artifact_present": False,
            "gap_reason": "artifact_not_found_locally",
            "trigger": "Read from Railway /app/data/bot_signal_evaluations.jsonl for live state",
            "decision_candidate": "CANDIDATE_FOR_CANARY_REVIEW once forward rows accumulate with outcomes",
        }
    rows_with_side = [r for r in rows if r.get("side")]
    status = "ACCUMULATING" if rows_with_side else ("DATA_GAP" if not rows else "ACCUMULATING")
    return {
        "key": "SURVIVING_COHORTS_BY_SIDE",
        "status": status,
        "description": "Signal evaluations with side field (forward from 2026-05-26 Sesion 398)",
        "artifact": str(path),
        "artifact_present": True,
        "row_count": len(rows),
        "rows_with_side": len(rows_with_side),
        "trigger": "n_forward_rows_with_recorded_side > 0 and calibration-safe outcomes link",
        "decision_candidate": "CANDIDATE_FOR_CANARY_REVIEW once threshold met",
    }


def _probe_directional_no(data_dir: Path) -> dict[str, Any]:
    """Directional NO forward calibration (at_or_above / at_or_below), separate from exact/NO."""
    path = data_dir / "blocked_signals_resolutions.jsonl"
    rows, ok = _read_jsonl(path)
    _desc = (
        "Passive forward calibration of directional NO signals "
        "(at_or_above / at_or_below). Separate from exact/NO. "
        "No live promotion authorized. SHADOW_EXACT_NO_GLOBAL protects exact/NO."
    )
    if not ok:
        return {
            "key": "DIRECTIONAL_NO_FORWARD",
            "status": "ARTIFACT_MISSING",
            "description": _desc,
            "artifact": str(path),
            "artifact_present": False,
            "gap_reason": "artifact_not_found_locally",
            "trigger": "Read from Railway /app/data/blocked_signals_resolutions.jsonl",
            "decision_candidate": "directional NO CANARY_CANDIDATE when WR>=55% n>=30 via Cohort Intelligence",
            "live_promotion_authorized": False,
            "shadow_exact_no_global_active": True,
        }
    directional = [
        r for r in rows
        if str(r.get("condition", "")).strip() in {"at_or_above", "at_or_below"}
        and str(r.get("side", "")).strip().upper() == "NO"
    ]
    resolved = [r for r in directional if r.get("win_for_trader") is not None]
    if not directional:
        status = "NO_MATCHING_ROWS_OBSERVED"
    elif resolved:
        status = "ACCUMULATING_RESOLVED_SAMPLE"
    else:
        status = "ACCUMULATING_UNRESOLVED"
    return {
        "key": "DIRECTIONAL_NO_FORWARD",
        "status": status,
        "description": _desc,
        "artifact": str(path),
        "artifact_present": True,
        "total_bsr_rows": len(rows),
        "directional_no_rows": len(directional),
        "resolved_rows": len(resolved),
        "trigger": "WR>=55% n>=30 (calibration-unique outcomes) for Cohort Intelligence candidacy",
        "decision_candidate": "directional NO CANARY_CANDIDATE when threshold met",
        "live_promotion_authorized": False,
        "shadow_exact_no_global_active": True,
    }


def _probe_price_filter(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "price_filter_counterfactual_log_only.jsonl"
    rows, ok = _read_jsonl(path)
    if not ok:
        return {
            "key": "PRICE_FILTER_COUNTERFACTUAL",
            "status": "DATA_GAP",
            "description": "LOG_ONLY captures of price_out_of_range skips for active/canary cities",
            "artifact": str(path),
            "artifact_present": False,
            "gap_reason": "artifact_not_found_locally",
            "trigger": "Read from Railway /app/data/price_filter_counterfactual_log_only.jsonl",
            "decision_candidate": "REVIEW_PRICE_POLICY if resolved counterfactuals accumulate with edge",
            "live_promotion_authorized": False,
            "exact_no_excluded": True,
        }
    if not rows:
        return {
            "key": "PRICE_FILTER_COUNTERFACTUAL",
            "status": "DATA_GAP",
            "description": "LOG_ONLY captures of price_out_of_range skips for active/canary cities",
            "artifact": str(path),
            "artifact_present": True,
            "row_count": 0,
            "gap_reason": "artifact_present_but_empty",
            "trigger": "Sufficient resolved counterfactuals with edge data",
            "decision_candidate": "REVIEW_PRICE_POLICY if resolved counterfactuals accumulate with edge",
            "live_promotion_authorized": False,
            "exact_no_excluded": True,
        }
    # Rich stats — field is edge_pct (not edge) in Railway schema v1
    unique_cycles = len({str(r.get("cycle_id", "")) for r in rows if r.get("cycle_id")})
    unique_eval_keys = len({str(r.get("eval_key", "")) for r in rows if r.get("eval_key")})
    cities: dict[str, int] = {}
    for r in rows:
        c = str(r.get("city", ""))
        if c:
            cities[c] = cities.get(c, 0) + 1
    # Token candidates via token_id_yes / token_id_no (eval_key acts as identity if no token_id)
    token_candidates: set[str] = set()
    for r in rows:
        if r.get("token_id_yes"):
            token_candidates.add(str(r["token_id_yes"]))
        if r.get("token_id_no"):
            token_candidates.add(str(r["token_id_no"]))
    # edge_pct is the correct field name in the Railway schema
    rows_with_edge = [r for r in rows if r.get("edge_pct") is not None]
    try:
        edge_above_5pp = sum(1 for r in rows_with_edge if float(r.get("edge_pct", 0)) >= 5.0)
    except (TypeError, ValueError):
        edge_above_5pp = 0
    # Independent candidates after dedupe by eval_key
    deduped_candidates = len({str(r.get("eval_key", i)) for i, r in enumerate(rows)})
    # Outcomes linked
    outcomes_resolved = sum(
        1 for r in rows
        if r.get("win_for_trader") is not None
        or str(r.get("outcome_link_status", "")).lower() in ("resolved", "confirmed")
    )
    if outcomes_resolved > 0:
        status = "READY_FOR_OFFLINE_REVIEW"
    else:
        status = "ACCUMULATING_NO_RESOLVED_OUTCOMES"
    return {
        "key": "PRICE_FILTER_COUNTERFACTUAL",
        "status": status,
        "description": "LOG_ONLY captures of price_out_of_range skips for active/canary cities",
        "artifact": str(path),
        "artifact_present": True,
        "row_count": len(rows),
        "unique_cycles": unique_cycles,
        "unique_eval_keys": unique_eval_keys,
        "cities": cities,
        "token_candidates_unique": len(token_candidates),
        "rows_with_edge_pct": len(rows_with_edge),
        "edge_pct_above_5pp": edge_above_5pp,
        "deduped_candidates_by_eval_key": deduped_candidates,
        "outcomes_resolved": outcomes_resolved,
        "trigger": (
            "outcomes_resolved > 0 for READY_FOR_OFFLINE_REVIEW; "
            "offline review requires edge_pct data + Opus design + Pablo approval"
        ),
        "decision_candidate": "REVIEW_PRICE_POLICY if resolved counterfactuals accumulate with edge",
        "live_promotion_authorized": False,
        "exact_no_excluded": True,
        "note": "price_out_of_range policy unchanged. No promotion authorized in V1.",
    }


def _probe_denver_kbkf(data_dir: Path) -> dict[str, Any]:
    policy_path = data_dir / "runtime_policy_effective_view.json"
    data, ok = _read_json(policy_path)
    _description = (
        "Source aligned to Buckley SFB (KBKF) in commit 1421035. "
        "ICAO-only, no NOAA IDs, no OBSERVED_AUDIT_CITIES. "
        "Historical evidence pre-deploy contaminated by fallback geocoding."
    )
    if not ok:
        return {
            "key": "DENVER_KBKF",
            "status": "DATA_GAP",
            "description": _description,
            "artifact": str(policy_path),
            "artifact_present": False,
            "gap_reason": "runtime_policy_view_not_found_locally",
            "trigger": "Read from Railway to verify Denver effective_mode after KBKF patch",
            "decision_candidate": "ACCUMULATING_FORWARD_EVIDENCE once clean KBKF observations accumulate",
        }
    cities_raw = data.get("cities") if isinstance(data, dict) else None
    effective_mode = None
    if isinstance(cities_raw, dict):
        denver = cities_raw.get("Denver") or cities_raw.get("denver")
        effective_mode = denver.get("effective_mode") if isinstance(denver, dict) else None
    elif isinstance(cities_raw, list):
        for entry in cities_raw:
            if isinstance(entry, dict) and str(entry.get("city", "")).casefold() == "denver":
                effective_mode = entry.get("effective_mode")
                break
    return {
        "key": "DENVER_KBKF",
        "status": "ACCUMULATING",
        "description": _description,
        "artifact": str(policy_path),
        "artifact_present": True,
        "effective_mode_in_snapshot": effective_mode,
        "trigger": "Forward KBKF observations accumulate and source_fidelity audit passes",
        "decision_candidate": "ACCUMULATING_FORWARD_EVIDENCE — no canary/active promotion yet",
    }


def _probe_traders_intelligence(data_dir: Path) -> dict[str, Any]:
    census_path = data_dir / "directional_trader_census.json"
    summary_path = data_dir / "traders_intelligence_daily_summary_state.json"
    census, census_ok = _read_json(census_path)
    summary, summary_ok = _read_json(summary_path)
    if not census_ok and not summary_ok:
        return {
            "key": "TRADERS_INTELLIGENCE",
            "status": "DATA_GAP",
            "description": "Trader-vs-bot gap alarm; directional trader census and daily summary",
            "artifacts": [str(census_path), str(summary_path)],
            "artifact_present": False,
            "gap_reason": "neither_census_nor_summary_found",
            "trigger": "Gap alarm WATCH_SOURCE or ACTION threshold",
            "decision_candidate": "MAPPING_PATCH if gap>=3 days or n>=5 operable or markets_seen>=15",
        }
    alarm_state = summary.get("alarm_state") if isinstance(summary, dict) else None
    census_list = census if isinstance(census, list) else (census.get("traders", []) if isinstance(census, dict) else [])
    return {
        "key": "TRADERS_INTELLIGENCE",
        "status": "ACCUMULATING",
        "description": "Trader-vs-bot gap alarm; directional trader census and daily summary",
        "artifacts": [str(census_path), str(summary_path)],
        "artifact_present": True,
        "census_present": census_ok,
        "summary_present": summary_ok,
        "alarm_state": alarm_state,
        "census_entries": len(census_list),
        "trigger": "Gap alarm WATCH_SOURCE→ACTION threshold; >=3 days gap or n>=5 operable",
        "decision_candidate": "MAPPING_PATCH if threshold met",
    }


def _probe_pnl_bankroll(data_dir: Path) -> dict[str, Any]:
    bankroll_path = data_dir / "bankroll_readiness_state.json"
    lifecycle_path = data_dir / "trade_lifecycle.json"
    bankroll, bankroll_ok = _read_json(bankroll_path)
    lifecycle, lifecycle_ok = _read_json(lifecycle_path)
    br_composite = bankroll.get("composite") if isinstance(bankroll, dict) else None
    br_status = bankroll.get("status") if isinstance(bankroll, dict) else None
    lifecycle_records = 0
    if isinstance(lifecycle, dict):
        records = lifecycle.get("records", [])
        lifecycle_records = len(records) if isinstance(records, list) else 0
    return {
        "key": "PNL_BANKROLL",
        "status": "ACCUMULATING" if bankroll_ok else "DATA_GAP",
        "description": (
            "P&L and BANKROLL readiness. canonical_source=none in V1 until Outcome Resolver deployed. "
            "polymarket_api_pnl is external observability only, never canonical source."
        ),
        "artifacts": [str(bankroll_path), str(lifecycle_path)],
        "bankroll_readiness_present": bankroll_ok,
        "lifecycle_present": lifecycle_ok,
        "canonical_source": "none",
        "pnl_canonical_confirmed": False,
        "bankroll_composite": br_composite,
        "bankroll_status": br_status,
        "lifecycle_record_count": lifecycle_records,
        "trigger": "Outcome Resolver R1 CODE (blocked until T+7d + Opus design + Pablo approval)",
        "decision_candidate": "BANKROLL_REVIEW once canonical P&L source established",
    }


def _probe_exits_sl(data_dir: Path) -> dict[str, Any]:
    lifecycle_path = data_dir / "trade_lifecycle.json"
    lifecycle, lifecycle_ok = _read_json(lifecycle_path)
    if not lifecycle_ok:
        return {
            "key": "EXITS_SL",
            "status": "DATA_GAP",
            "description": (
                "SL_intra guard v10.6.40 + exit patterns in trade_lifecycle. "
                "Guard skips SL_intra exact+days<=1; telegram+review one-shot."
            ),
            "artifact": str(lifecycle_path),
            "artifact_present": False,
            "gap_reason": "trade_lifecycle_not_found_locally",
            "sl_intra_guard": "DEPLOYED v10.6.40",
            "kill_switch": "SL_INTRA_HAZARD_MONITOR_LOG_ONLY env var",
            "trigger": "n>=5 guarded SL or 2026-05-21 for A8 verdict",
            "decision_candidate": "EXIT_POLICY_DESIGN_CANDIDATE if SL pattern confirmed",
        }
    records = lifecycle.get("records", []) if isinstance(lifecycle, dict) else []
    sl_records = [
        r for r in (records if isinstance(records, list) else [])
        if isinstance(r, dict) and "sl" in str(
            (r.get("close_context") or {}).get("close_reason", "") or r.get("close_reason", "")
        ).lower()
    ]
    return {
        "key": "EXITS_SL",
        "status": "ACCUMULATING" if records else "DATA_GAP",
        "description": (
            "SL_intra guard v10.6.40 + exit patterns in trade_lifecycle. "
            "Guard skips SL_intra exact+days<=1; telegram+review one-shot."
        ),
        "artifact": str(lifecycle_path),
        "artifact_present": True,
        "lifecycle_records": len(records if isinstance(records, list) else []),
        "sl_related_records": len(sl_records),
        "sl_intra_guard": "DEPLOYED v10.6.40",
        "trigger": "n>=5 guarded SL for A8 verdict review",
        "decision_candidate": "EXIT_POLICY_DESIGN_CANDIDATE if SL pattern confirms bleeding",
    }


# ── Experiment registry orchestrator ─────────────────────────────────────────

def _build_experiment_registry(data_dir: Path) -> dict[str, Any]:
    entries = [
        _probe_phase2(data_dir),
        _probe_surviving_cohorts(data_dir),
        _probe_directional_no(data_dir),
        _probe_price_filter(data_dir),
        _probe_denver_kbkf(data_dir),
        _probe_traders_intelligence(data_dir),
        _probe_pnl_bankroll(data_dir),
        _probe_exits_sl(data_dir),
    ]
    _gap_statuses = {
        "DATA_GAP", "PHASE2_STATE_NOT_MACHINE_READABLE", "ARTIFACT_MISSING",
    }
    _accumulating_statuses = {
        "ACCUMULATING", "ACCUMULATING_UNRESOLVED", "ACCUMULATING_RESOLVED_SAMPLE",
        "ACCUMULATING_NO_RESOLVED_OUTCOMES",
    }
    gap_count = sum(1 for e in entries if e.get("status") in _gap_statuses)
    ready_count = sum(1 for e in entries if e.get("status") in ("READY", "READY_FOR_OFFLINE_REVIEW"))
    accumulating_count = sum(1 for e in entries if e.get("status") in _accumulating_statuses)
    return {
        "experiments": entries,
        "total": len(entries),
        "gap_count": gap_count,
        "ready_count": ready_count,
        "accumulating_count": accumulating_count,
    }


# ── Trade Truth Ledger ────────────────────────────────────────────────────────

def _record_date(r: dict[str, Any]) -> str:
    """Return first non-empty date string from a record, or empty string."""
    for key in ("date_iso", "date"):
        val = str(r.get(key, "")).strip()
        if val:
            return val
    ts = str(r.get("ts_utc", "")).strip()
    return ts[:10] if len(ts) >= 10 else ""


def _find_nearest_date(records: list[dict[str, Any]], target_date: str) -> str | None:
    dates: list[str] = []
    for r in records:
        val = _record_date(r)
        if val:
            dates.append(val[:10])
    if not dates:
        return None
    try:
        target = datetime.strptime(target_date[:10], "%Y-%m-%d")
        return min(dates, key=lambda d: abs((datetime.strptime(d[:10], "%Y-%m-%d") - target).days))
    except Exception:
        return dates[0] if dates else None


def _classify_lifecycle_record(
    record: dict[str, Any],
    resolutions: list[dict[str, Any]],
) -> dict[str, Any]:
    identity = (
        record.get("id")
        or record.get("position_key")
        or record.get("eval_key")
        or record.get("match_key")
        or record.get("token_id")
    )
    pnl_value = _get_pnl_value(record)
    has_pnl = pnl_value is not None

    cc = record.get("close_context") or {}
    close_action = cc.get("close_action") or record.get("close_action")
    close_reason = cc.get("close_reason") or cc.get("close_subtype") or record.get("close_reason")

    # ── Join logic: exact match_key first, then derived ───────────────────────
    record_mk = record.get("match_key")
    matched_resolution: dict[str, Any] | None = None
    derived_mk_result: dict[str, Any] | None = None
    join_method: str

    def _has_outcome(r: dict[str, Any]) -> bool:
        return r.get("win_for_trader") is not None or bool(r.get("outcome"))

    if record_mk:
        candidate = next(
            (r for r in resolutions if r.get("match_key") and r.get("match_key") == record_mk),
            None,
        )
        if candidate and _has_outcome(candidate):
            matched_resolution = candidate
            join_method = "exact_match_key"
        elif candidate:
            join_method = "exact_match_key_present_unresolved"
        else:
            join_method = "exact_match_key_present_no_bsr_match"
    else:
        derived_mk_result = derive_match_key_from_lifecycle_record(record)
        if derived_mk_result["match_key_derivation_status"] == "derived":
            derived_mk = derived_mk_result["derived_match_key"]
            bsr_matches = [r for r in resolutions if r.get("match_key") == derived_mk]
            if len(bsr_matches) == 1 and _has_outcome(bsr_matches[0]):
                matched_resolution = bsr_matches[0]
                join_method = "derived_match_key"
            elif len(bsr_matches) == 1:
                join_method = "derived_match_key_bsr_unresolved"
            elif len(bsr_matches) > 1:
                join_method = "BLOCKED_ambiguous_bsr_matches"
            else:
                join_method = "BLOCKED_derived_key_no_bsr_match"
        else:
            join_method = "BLOCKED_no_match_key"

    outcome_resolved = matched_resolution is not None and _has_outcome(matched_resolution)

    # ── Classification ────────────────────────────────────────────────────────
    if not identity:
        classification, reason = "unresolved", "missing_identity"
    elif outcome_resolved:
        classification, reason = "market_outcome_observed", "outcome_observed_via_bsr"
    elif has_pnl:
        classification, reason = "pnl_diagnostic", "pnl_present_outcome_unresolved"
    else:
        classification, reason = "diagnostic_only", "no_pnl_no_outcome"

    provenance_level = (
        "market_outcome_observed" if outcome_resolved
        else ("pnl_diagnostic" if has_pnl else "identity_only")
    )

    # ── Market truth fields (populated only when outcome observed) ────────────
    market_truth_fields: dict[str, Any] = {}
    if outcome_resolved and matched_resolution is not None:
        raw_outcome = str(matched_resolution.get("outcome") or "").strip().lower()
        if raw_outcome in ("yes", "true", "1"):
            mo = "YES"
        elif raw_outcome in ("no", "false", "0"):
            mo = "NO"
        else:
            mo = "unresolved"
        bot_side = str(record.get("side") or "").strip().upper()
        bot_aligned: bool | None = (bot_side == mo) if mo in ("YES", "NO") and bot_side in ("YES", "NO") else None
        market_truth_fields = {
            "market_outcome_observed": mo,
            "market_outcome_observed_source": matched_resolution.get("resolution_source") or None,
            "market_id": str(matched_resolution.get("market_id") or "").strip() or None,
            "condition_id": str(matched_resolution.get("condition_id") or "").strip() or None,
            "market_truth_canonical": False,
            "weather_truth_available": False,
            "pnl_counterfactual_status": "R1_REQUIRED_FOR_CASH_COUNTERFACTUAL",
        }
        if bot_aligned is not None:
            market_truth_fields["bot_side_aligned_with_observed_outcome"] = bot_aligned

    # ── Outcome join gap ──────────────────────────────────────────────────────
    outcome_join_gap: str | None
    if not identity:
        outcome_join_gap = "identity_missing"
    elif outcome_resolved:
        outcome_join_gap = None
    elif record_mk:
        outcome_join_gap = "bsr_match_found_outcome_unresolved" if join_method == "exact_match_key_present_unresolved" else "bsr_match_not_found"
    elif derived_mk_result:
        if derived_mk_result["match_key_derivation_status"] == "derived":
            outcome_join_gap = "bsr_match_not_found_for_derived_key"
        else:
            reason_str = derived_mk_result.get("derivation_failure_reason") or "unknown"
            outcome_join_gap = f"match_key_derivation_failed:{reason_str}"
    else:
        outcome_join_gap = "match_key_absent_in_lifecycle_record"

    # ── Diagnostic evidence flags ─────────────────────────────────────────────
    evidence_flags: list[str] = []
    if has_pnl and "stop" in str(close_reason or "").lower():
        evidence_flags.append("DIAGNOSTIC_EXIT_DAMAGE_EVIDENCE_PRESENT")
    entry_ctx = record.get("entry_context") or record.get("latest_entry_context") or {}
    if entry_ctx.get("edge_pct") is not None or entry_ctx.get("our_prob") is not None:
        evidence_flags.append("DIAGNOSTIC_ALPHA_LOSS_EVIDENCE_PRESENT")
    if identity and not outcome_resolved:
        evidence_flags.append("UNRESOLVED_BY_OUTCOME_JOIN_GAP")
    token_id = str(record.get("token_id") or "").strip()
    if not token_id:
        evidence_flags.append("SOURCE_OR_EPOCH_GAP")

    # ── Result ────────────────────────────────────────────────────────────────
    result: dict[str, Any] = {
        "classification": classification,
        "reason": reason,
        "city": record.get("city"),
        "date": _record_date(record) or None,
        "condition": record.get("condition"),
        "side": record.get("side"),
        "has_identity": bool(identity),
        "has_pnl": has_pnl,
        "pnl_value": pnl_value,
        "close_action": close_action,
        "close_reason": close_reason,
        "outcome_resolved": outcome_resolved,
        "provenance_level": provenance_level,
        "diagnostic_evidence_flags": evidence_flags,
        "join_method": join_method,
        "outcome_join_gap": outcome_join_gap,
    }
    result.update(market_truth_fields)

    if derived_mk_result is not None:
        result["derived_match_key"] = derived_mk_result["derived_match_key"]
        result["match_key_derivation_status"] = derived_mk_result["match_key_derivation_status"]
        if derived_mk_result.get("derivation_failure_reason"):
            result["derivation_failure_reason"] = derived_mk_result["derivation_failure_reason"]

    gaps = []
    if not identity:
        gaps.append("MISSING_IDENTITY")
    if not has_pnl:
        gaps.append("MISSING_PNL_DIAGNOSTIC")
    if not outcome_resolved:
        gaps.append("OUTCOME_NOT_RESOLVED")
    if gaps:
        result["diagnostic_gaps"] = gaps

    return result


def _lookup_city_date(
    lifecycle: Any,
    lifecycle_ok: bool,
    lifecycle_path: Path,
    city: str,
    date: str | None,
    resolutions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    city_cf = city.casefold()
    resolutions = resolutions or []
    if not lifecycle_ok:
        return {
            "city": city,
            "date_requested": date,
            "status": "DATA_GAP",
            "gap_reason": "trade_lifecycle_not_found_locally",
            "nearest_match": None,
            "note": "Verify with: tools/railway_safe.ps1 ssh 'cat /app/data/trade_lifecycle.json'",
        }
    records = lifecycle.get("records", []) if isinstance(lifecycle, dict) else []
    city_records = [
        r for r in (records if isinstance(records, list) else [])
        if isinstance(r, dict) and r.get("city", "").casefold() == city_cf
    ]
    if not city_records:
        return {
            "city": city,
            "date_requested": date,
            "status": "UNRESOLVED_PNL_DISCREPANCY",
            "reason": "no_records_for_city",
            "nearest_match": None,
        }
    if date is None:
        return {
            "city": city,
            "date_requested": None,
            "status": "FOUND_NO_DATE_FILTER",
            "record_count": len(city_records),
        }
    date_records = [r for r in city_records if date in _record_date(r)]
    if date_records:
        enriched = []
        for r in date_records[:3]:
            cl = _classify_lifecycle_record(r, resolutions)
            entry_ctx = r.get("entry_context") or r.get("latest_entry_context") or {}
            rec: dict[str, Any] = {
                "city": r.get("city"),
                "date": _record_date(r),
                "condition": r.get("condition"),
                "side": r.get("side"),
                "pnl_value": cl.get("pnl_value"),
                "close_action": cl.get("close_action"),
                "close_reason": cl.get("close_reason"),
                "classification": cl.get("classification"),
                "provenance_level": cl.get("provenance_level"),
                "diagnostic_gaps": cl.get("diagnostic_gaps"),
                "diagnostic_evidence_flags": cl.get("diagnostic_evidence_flags"),
                "join_method": cl.get("join_method"),
                "outcome_join_gap": cl.get("outcome_join_gap"),
            }
            for _bridge_field in (
                "derived_match_key", "match_key_derivation_status", "derivation_failure_reason",
                "market_outcome_observed", "market_outcome_observed_source",
                "market_id", "condition_id", "market_truth_canonical", "weather_truth_available",
                "bot_side_aligned_with_observed_outcome", "pnl_counterfactual_status",
            ):
                _v = cl.get(_bridge_field)
                if _v is not None:
                    rec[_bridge_field] = _v
            if entry_ctx.get("edge_pct") is not None:
                rec["entry_edge_pct"] = entry_ctx["edge_pct"]
            if entry_ctx.get("our_prob") is not None:
                rec["entry_our_prob"] = entry_ctx["our_prob"]
            if entry_ctx.get("forecast_max") is not None:
                rec["entry_forecast_max"] = entry_ctx["forecast_max"]
            enriched.append(rec)
        return {
            "city": city,
            "date_requested": date,
            "status": "FOUND",
            "record_count": len(date_records),
            "records": enriched,
        }
    nearest = _find_nearest_date(city_records, date)
    return {
        "city": city,
        "date_requested": date,
        "status": "UNRESOLVED_PNL_DISCREPANCY",
        "reason": "date_not_found_in_city_records",
        "nearest_match": nearest,
        "note": "Do not hardcode absence. Verify with Railway snapshot before concluding.",
    }


def _build_trade_truth_ledger(
    data_dir: Path,
    city: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    lifecycle_path = data_dir / "trade_lifecycle.json"
    evals_path = data_dir / "bot_signal_evaluations.jsonl"
    resolutions_path = data_dir / "blocked_signals_resolutions.jsonl"

    lifecycle, lifecycle_ok = _read_json(lifecycle_path)
    _evals, evals_ok = _read_jsonl(evals_path)
    resolutions, resolutions_ok = _read_jsonl(resolutions_path)

    artifacts_present = {
        "trade_lifecycle": lifecycle_ok,
        "bot_signal_evaluations": evals_ok,
        "blocked_signals_resolutions": resolutions_ok,
    }
    _note_provenance = (
        "NOAA/Open-Meteo/postmortem = diagnostic only, not eligible for live. "
        "polymarket_api_pnl = external observability, never canonical source. "
        "data/runtime_import = dev fixture, eligible_for_learning=false. "
        "Outcome Resolver (pending CODE) required for canonical P&L."
    )

    city_date_lookup: dict[str, Any] | None = None
    if city:
        city_date_lookup = _lookup_city_date(
            lifecycle, lifecycle_ok, lifecycle_path, city, date, resolutions
        )

    if not any(artifacts_present.values()):
        return {
            "status": "DATA_GAP",
            "artifacts_present": artifacts_present,
            "total_records": 0,
            "unresolved_count": 0,
            "diagnostic_count": 0,
            "market_outcome_observed_count": 0,
            "pnl_canonical_confirmed": False,
            "canonical_source": "none",
            "gap_reason": "no_trading_artifacts_found_locally",
            "note_provenance": _note_provenance,
            "city_date_lookup": city_date_lookup,
        }

    records = lifecycle.get("records", []) if isinstance(lifecycle, dict) else []
    records_list = records if isinstance(records, list) else []
    entries = [
        _classify_lifecycle_record(r, resolutions)
        for r in records_list
        if isinstance(r, dict)
    ]
    unresolved = [e for e in entries if e["classification"] == "unresolved"]
    diagnostic = [e for e in entries if e["classification"] in ("diagnostic_only", "pnl_diagnostic")]
    confirmed = [e for e in entries if e["classification"] == "market_outcome_observed"]

    # Dynamic join key analysis based on actual lifecycle data
    lc_with_match_key = sum(1 for r in records_list if isinstance(r, dict) and r.get("match_key"))
    lc_with_eval_key = sum(1 for r in records_list if isinstance(r, dict) and r.get("eval_key"))
    lc_with_token_id = sum(1 for r in records_list if isinstance(r, dict) and r.get("token_id"))
    lc_with_id = sum(1 for r in records_list if isinstance(r, dict) and r.get("id"))
    join_key_analysis = {
        "lifecycle_to_postmortem": (
            "KEYS_PRESENT_NOT_VALIDATED_AGAINST_POSTMORTEM" if lc_with_token_id > 0 or lc_with_id > 0
            else "BLOCKED_no_id_or_token_id"
        ),
        "lifecycle_to_resolutions": (
            f"PARTIAL_{lc_with_match_key}_records_have_match_key" if lc_with_match_key > 0
            else "BLOCKED_match_key_absent_in_all_records"
        ),
        "lifecycle_to_evaluations": (
            f"PARTIAL_{lc_with_eval_key}_records_have_eval_key" if lc_with_eval_key > 0
            else "BLOCKED_eval_key_absent_in_all_records"
        ),
        "records_with_match_key": lc_with_match_key,
        "records_with_eval_key": lc_with_eval_key,
        "records_with_token_id": lc_with_token_id,
        "records_with_id": lc_with_id,
        "outcome_resolution_available": False,
        "trigger_to_unlock_outcome_resolution": (
            "Outcome Resolver R1 CODE: backfill match_key in lifecycle records "
            "or implement token_id->market_outcome lookup via Polymarket API"
        ),
    }

    return {
        "status": "LOADED" if entries else "EMPTY",
        "artifacts_present": artifacts_present,
        "total_records": len(entries),
        "unresolved_count": len(unresolved),
        "diagnostic_count": len(diagnostic),
        "market_outcome_observed_count": len(confirmed),
        "pnl_canonical_confirmed": False,
        "canonical_source": "none",
        "join_key_analysis": join_key_analysis,
        "sample_unresolved": [
            {k: e[k] for k in ("classification", "reason", "city", "date", "condition", "side") if k in e}
            for e in unresolved[:3]
        ],
        "note_provenance": _note_provenance,
        "city_date_lookup": city_date_lookup,
    }


# ── Epoch and Regime Attribution ──────────────────────────────────────────────

def _build_epoch_attribution(data_dir: Path, repo_root: Path) -> dict[str, Any]:
    manifest_path = data_dir / "policy_epochs_manifest.json"
    if not manifest_path.exists():
        contexto_path = repo_root / "CONTEXTO.md"
        contexto_note = "not_readable"
        if contexto_path.exists():
            try:
                text = contexto_path.read_text(encoding="utf-8", errors="replace")
                contexto_note = f"readable ({len(text.splitlines())} lines) — diagnostic only, not canonical epoch source"
            except Exception:
                contexto_note = "read_error"
        return {
            "status": "EPOCH_MANIFEST_GAP",
            "manifest": str(manifest_path),
            "manifest_present": False,
            "gap_reason": "policy_epochs_manifest_not_created_v1_by_design",
            "note": (
                "V1 degrades gracefully. Do not infer epoch from CONTEXTO.md or session history alone. "
                "Do not assert regime change if bugs/source mismatch/gates could explain drawdown."
            ),
            "regime_change_safe_to_assert": False,
            "contexto_diagnostic": contexto_note,
        }
    manifest, ok = _read_json(manifest_path)
    return {
        "status": "MANIFEST_LOADED",
        "manifest": str(manifest_path),
        "manifest_present": True,
        "entries": len(manifest) if isinstance(manifest, list) else 1,
    }


# ── Verdict Packet ────────────────────────────────────────────────────────────

def _build_verdict_packet(
    registry: dict[str, Any],
    ledger: dict[str, Any],
    epoch: dict[str, Any],
) -> dict[str, Any]:
    gap_count = registry.get("gap_count", 0)
    total = registry.get("total", 8)
    accumulating_count = registry.get("accumulating_count", 0)
    unresolved_count = ledger.get("unresolved_count", 0)
    ledger_status = ledger.get("status", "DATA_GAP")
    epoch_status = epoch.get("status", "EPOCH_MANIFEST_GAP")

    # V1 invariant: pnl_canonical_confirmed=false — blocks LIVE eligibility, NOT diagnostic verdicts.
    # EPOCH_MANIFEST_GAP is by design in V1 — does NOT block diagnostic verdicts.
    pnl_canonical_confirmed = False

    # Diagnostic verdict logic:
    #   TRUTH_GAP_BLOCKS_DECISION  — unresolved ledger entries block the conclusion
    #   INSUFFICIENT_EVIDENCE      — no meaningful data at all
    #   KEEP_ACCUMULATING_UNTIL_TRIGGER — evidence accumulating, no critical issues
    has_unresolved = unresolved_count > 0
    all_data_absent = ledger_status == "DATA_GAP" and gap_count >= total

    if has_unresolved:
        verdict = VERDICT_TRUTH_GAP
        verdict_reason = (
            f"unresolved_ledger_entries={unresolved_count}; "
            f"registry_gaps={gap_count}/{total}; ledger_status={ledger_status}"
        )
    elif all_data_absent:
        verdict = VERDICT_INSUFFICIENT
        verdict_reason = (
            f"all_registry_DATA_GAP ({gap_count}/{total}) and ledger_DATA_GAP: "
            "no evidence to form diagnostic conclusion"
        )
    elif accumulating_count >= 2:
        verdict = VERDICT_KEEP_ACCUMULATING
        verdict_reason = (
            f"accumulating_count={accumulating_count}/{total}; "
            f"ledger_status={ledger_status}; "
            f"epoch_status={epoch_status} (by-design V1, does not block diagnostics); "
            f"registry_gaps={gap_count}/{total}; "
            "pnl_canonical_confirmed=false (V1 live-blocker, not diagnostic blocker)"
        )
    else:
        verdict = VERDICT_INSUFFICIENT
        verdict_reason = (
            f"accumulating_count={accumulating_count} < 2 threshold; "
            f"ledger_status={ledger_status}"
        )

    _gap_statuses = {"DATA_GAP", "PHASE2_STATE_NOT_MACHINE_READABLE", "ARTIFACT_MISSING"}
    _accumulating_statuses = {
        "ACCUMULATING", "ACCUMULATING_UNRESOLVED", "ACCUMULATING_RESOLVED_SAMPLE",
        "ACCUMULATING_NO_RESOLVED_OUTCOMES",
    }
    gaps_listed = [
        e["key"] for e in registry.get("experiments", [])
        if e.get("status") in _gap_statuses
    ]

    # Per-line diagnostic breakdown
    lines_with_evidence = [
        {
            "key": e["key"],
            "status": e.get("status"),
            "trigger": e.get("trigger"),
        }
        for e in registry.get("experiments", [])
        if e.get("status") in _accumulating_statuses or e.get("status") in ("READY", "READY_FOR_OFFLINE_REVIEW")
    ]
    lines_blocked = [
        {
            "key": e["key"],
            "status": e.get("status"),
            "blocker_trigger": e.get("trigger") or e.get("decision_candidate"),
        }
        for e in registry.get("experiments", [])
        if e.get("status") in _gap_statuses
    ]

    return {
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "pnl_canonical_confirmed": pnl_canonical_confirmed,
        "live_policy_eligible": False,
        "live_blocked_reason": (
            "V1_invariant: canonical_source=none. "
            "Outcome Resolver R1 CODE pending. BANKROLL $25 HOLD. Fase C not authorized."
        ),
        "autoexecute": False,
        "requires_opus_ratification_before_policy_design": True,
        "disclaimer": _V1_DISCLAIMER,
        "registry_gap_count": gap_count,
        "registry_gaps": gaps_listed,
        "unresolved_ledger_entries": unresolved_count,
        "epoch_status": epoch_status,
        "lines_with_diagnostic_evidence": lines_with_evidence,
        "lines_blocked_by_truth_gap": lines_blocked,
        "available_verdicts_v1": [
            VERDICT_KEEP_ACCUMULATING,
            VERDICT_TRUTH_GAP,
            VERDICT_EXIT_CANDIDATE,
            VERDICT_COHORT_CANDIDATE,
            VERDICT_INSUFFICIENT,
        ],
    }


# ── Public entry point ────────────────────────────────────────────────────────

def build_weather_strategy_result(
    data_dir: Path,
    repo_root: Path,
    city: str | None = None,
    date: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build V1 read-only weather strategy decision packet.

    Always returns LIVE_POLICY_ELIGIBLE=false. Never mutates any state.
    """
    now = now or datetime.now(timezone.utc)
    registry = _build_experiment_registry(data_dir)
    ledger = _build_trade_truth_ledger(data_dir, city=city, date=date)
    epoch = _build_epoch_attribution(data_dir, repo_root)
    packet = _build_verdict_packet(registry, ledger, epoch)
    return {
        "matches_found": True,
        "schema_version": "bot_brain_weather_strategy_v1",
        "generated_at": now.isoformat(),
        "city_filter": city,
        "date_filter": date,
        "weather_experiment_registry": registry,
        "trade_truth_ledger": ledger,
        "epoch_and_regime_attribution": epoch,
        "weather_strategy_verdict_packet": packet,
    }
