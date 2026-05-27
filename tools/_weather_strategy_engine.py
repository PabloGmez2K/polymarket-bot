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


# ── Experiment registry probes ────────────────────────────────────────────────

def _probe_phase2(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "exact_no_qt_match_evaluations_log_only.jsonl"
    rows, ok = _read_jsonl(path)
    if not ok:
        return {
            "key": "PHASE_2",
            "status": "DATA_GAP",
            "description": "Pre-Edge LOG_ONLY exact/no-QT-match evaluations",
            "artifact": str(path),
            "artifact_present": False,
            "gap_reason": "artifact_not_found_locally",
            "trigger": "T+7d sano (~2026-05-31); Outcome Resolver R1 CODE requires Opus design + Pablo approval",
            "decision_candidate": "Outcome Resolver R1 CODE blocked on T+7d + Opus design",
        }
    non_seoul = [r for r in rows if str(r.get("city", "")).casefold() != "seoul"]
    status = "ACCUMULATING" if rows else "DATA_GAP"
    return {
        "key": "PHASE_2",
        "status": status,
        "description": "Pre-Edge LOG_ONLY exact/no-QT-match evaluations",
        "artifact": str(path),
        "artifact_present": True,
        "row_count": len(rows),
        "non_seoul_clean": len(non_seoul),
        "trigger": "T+7d sano (~2026-05-31) + Opus design + Pablo approval",
        "decision_candidate": "Outcome Resolver R1 CODE",
    }


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
    if not ok:
        return {
            "key": "DIRECTIONAL_NO_FORWARD",
            "status": "DATA_GAP",
            "description": (
                "Passive forward calibration of directional NO signals "
                "(at_or_above / at_or_below). Separate from exact/NO. "
                "No live promotion authorized. SHADOW_EXACT_NO_GLOBAL protects exact/NO."
            ),
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
    status = "ACCUMULATING" if resolved else ("ACCUMULATING" if directional else "DATA_GAP")
    return {
        "key": "DIRECTIONAL_NO_FORWARD",
        "status": status,
        "description": (
            "Passive forward calibration of directional NO signals "
            "(at_or_above / at_or_below). Separate from exact/NO. "
            "No live promotion authorized. SHADOW_EXACT_NO_GLOBAL protects exact/NO."
        ),
        "artifact": str(path),
        "artifact_present": True,
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
    return {
        "key": "PRICE_FILTER_COUNTERFACTUAL",
        "status": "ACCUMULATING" if rows else "DATA_GAP",
        "description": "LOG_ONLY captures of price_out_of_range skips for active/canary cities",
        "artifact": str(path),
        "artifact_present": True,
        "row_count": len(rows),
        "trigger": "Sufficient resolved counterfactuals with edge data",
        "decision_candidate": "REVIEW_PRICE_POLICY if resolved counterfactuals accumulate with edge",
        "live_promotion_authorized": False,
        "exact_no_excluded": True,
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
        "artifact_note": "runtime_policy_effective_view.json is a dev fixture (data/runtime_import). Not live production state.",
        "effective_mode_in_fixture": effective_mode,
        "trigger": "Forward KBKF observations accumulate and source_fidelity audit passes",
        "decision_candidate": "ACCUMULATING_FORWARD_EVIDENCE — no canary/active promotion yet",
    }


def _probe_traders_intelligence(data_dir: Path) -> dict[str, Any]:
    census_path = data_dir / "directional_trader_census.json"
    summary_path = data_dir / "_tmp_traders_intelligence_daily_summary_v1_ready_state.json"
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
        if isinstance(r, dict) and "sl" in str(r.get("close_reason", "")).lower()
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
    gap_count = sum(1 for e in entries if e.get("status") == "DATA_GAP")
    ready_count = sum(1 for e in entries if e.get("status") == "READY")
    accumulating_count = sum(1 for e in entries if e.get("status") == "ACCUMULATING")
    return {
        "experiments": entries,
        "total": len(entries),
        "gap_count": gap_count,
        "ready_count": ready_count,
        "accumulating_count": accumulating_count,
    }


# ── Trade Truth Ledger ────────────────────────────────────────────────────────

def _lookup_city_date(
    lifecycle: Any,
    lifecycle_ok: bool,
    lifecycle_path: Path,
    city: str,
    date: str | None,
) -> dict[str, Any]:
    city_cf = city.casefold()
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
        return {
            "city": city,
            "date_requested": date,
            "status": "FOUND",
            "record_count": len(date_records),
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
    identity = record.get("id") or record.get("eval_key") or record.get("match_key")
    has_pnl = record.get("pnl") is not None or record.get("realized_pnl") is not None
    matched_resolution = next(
        (r for r in resolutions if r.get("match_key") and r.get("match_key") == record.get("match_key")),
        None,
    )
    outcome_resolved = matched_resolution is not None and matched_resolution.get("win_for_trader") is not None

    if not identity:
        classification, reason = "unresolved", "missing_identity"
    elif outcome_resolved:
        classification, reason = "settlement_confirmed", "outcome_resolved_diagnostic"
    elif has_pnl:
        classification, reason = "pnl_diagnostic", "pnl_present_outcome_unresolved"
    else:
        classification, reason = "diagnostic_only", "no_pnl_no_outcome"

    return {
        "classification": classification,
        "reason": reason,
        "city": record.get("city"),
        "date": _record_date(record) or None,
        "side": record.get("side"),
        "has_identity": bool(identity),
        "has_pnl": has_pnl,
        "outcome_resolved": outcome_resolved,
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
        city_date_lookup = _lookup_city_date(lifecycle, lifecycle_ok, lifecycle_path, city, date)

    if not any(artifacts_present.values()):
        return {
            "status": "DATA_GAP",
            "artifacts_present": artifacts_present,
            "total_records": 0,
            "unresolved_count": 0,
            "diagnostic_count": 0,
            "settlement_confirmed_count": 0,
            "pnl_canonical_confirmed": False,
            "canonical_source": "none",
            "gap_reason": "no_trading_artifacts_found_locally",
            "note_provenance": _note_provenance,
            "city_date_lookup": city_date_lookup,
        }

    records = lifecycle.get("records", []) if isinstance(lifecycle, dict) else []
    entries = [
        _classify_lifecycle_record(r, resolutions)
        for r in (records if isinstance(records, list) else [])
        if isinstance(r, dict)
    ]
    unresolved = [e for e in entries if e["classification"] == "unresolved"]
    diagnostic = [e for e in entries if e["classification"] in ("diagnostic_only", "pnl_diagnostic")]
    confirmed = [e for e in entries if e["classification"] == "settlement_confirmed"]

    return {
        "status": "LOADED" if entries else "EMPTY",
        "artifacts_present": artifacts_present,
        "total_records": len(entries),
        "unresolved_count": len(unresolved),
        "diagnostic_count": len(diagnostic),
        "settlement_confirmed_count": len(confirmed),
        "pnl_canonical_confirmed": False,
        "canonical_source": "none",
        "sample_unresolved": [
            {k: e[k] for k in ("classification", "reason", "city", "date", "side") if k in e}
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
    unresolved_count = ledger.get("unresolved_count", 0)
    ledger_status = ledger.get("status", "DATA_GAP")
    epoch_status = epoch.get("status", "EPOCH_MANIFEST_GAP")

    # V1 invariant: pnl_canonical_confirmed=false until Outcome Resolver produces canonical source
    pnl_canonical_confirmed = False

    # Critical gaps block any positive verdict
    has_critical_gap = (
        not pnl_canonical_confirmed
        or ledger_status == "DATA_GAP"
        or epoch_status == "EPOCH_MANIFEST_GAP"
        or gap_count >= 4
    )

    if has_critical_gap or unresolved_count > 0:
        verdict = VERDICT_TRUTH_GAP
        verdict_reason = (
            f"pnl_canonical_confirmed=false (canonical_source=none); "
            f"registry_gaps={gap_count}/{registry.get('total', 8)}; "
            f"ledger_status={ledger_status}; "
            f"epoch_status={epoch_status}; "
            f"unresolved_ledger_entries={unresolved_count}"
        )
    else:
        accumulating = registry.get("accumulating_count", 0)
        verdict = VERDICT_KEEP_ACCUMULATING if accumulating >= 2 else VERDICT_INSUFFICIENT
        verdict_reason = f"accumulating_count={accumulating}"

    gaps_listed = [e["key"] for e in registry.get("experiments", []) if e.get("status") == "DATA_GAP"]

    return {
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "pnl_canonical_confirmed": pnl_canonical_confirmed,
        "live_policy_eligible": False,
        "autoexecute": False,
        "disclaimer": _V1_DISCLAIMER,
        "registry_gap_count": gap_count,
        "registry_gaps": gaps_listed,
        "unresolved_ledger_entries": unresolved_count,
        "epoch_status": epoch_status,
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
