"""Tests focales para bot_brain.py --scope weather_strategy (V1).

Invariantes V1:
  - LIVE_POLICY_ELIGIBLE = false siempre
  - P&L_CANONICAL_CONFIRMED = false siempre
  - autoexecute = false siempre
  - 8 experimentos en registry
  - EPOCH_MANIFEST_GAP cuando no existe manifest
  - Madrid sintético: May 25 con solo May 21 → UNRESOLVED_PNL_DISCREPANCY
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.bot_brain import build_brain_report, main, render_markdown
from tools._weather_strategy_engine import (
    build_weather_strategy_result,
    derive_match_key_from_lifecycle_record,
    VERDICT_TRUTH_GAP,
    VERDICT_KEEP_ACCUMULATING,
    VERDICT_INSUFFICIENT,
)

NOW = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)

EXPECTED_EXPERIMENT_KEYS = {
    "PHASE_2",
    "SURVIVING_COHORTS_BY_SIDE",
    "DIRECTIONAL_NO_FORWARD",
    "PRICE_FILTER_COUNTERFACTUAL",
    "DENVER_KBKF",
    "TRADERS_INTELLIGENCE",
    "PNL_BANKROLL",
    "EXITS_SL",
}


def _data_dir(tmp_path: Path) -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return tmp_path, data_dir


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# ── 1. LIVE_POLICY_ELIGIBLE invariant ────────────────────────────────────────

def test_v1_always_not_live(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    assert packet["live_policy_eligible"] is False
    assert packet["autoexecute"] is False
    assert packet["pnl_canonical_confirmed"] is False


def test_v1_not_live_via_build_brain_report(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    report = build_brain_report("weather_strategy", repo_root=repo_root, data_dir=data_dir, now=NOW)
    packet = report["results"]["weather_strategy_verdict_packet"]
    assert packet["live_policy_eligible"] is False
    assert packet["pnl_canonical_confirmed"] is False
    assert "LOG_ONLY" in packet["disclaimer"]


# ── 2. Experiment registry — 8 experiments always present ────────────────────

def test_registry_has_8_experiments(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    assert registry["total"] == 8
    keys = {e["key"] for e in registry["experiments"]}
    assert keys == EXPECTED_EXPERIMENT_KEYS


# ── 3. All gaps when no artifacts ─────────────────────────────────────────────

def test_all_data_gaps_when_no_artifacts(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    # Most should be DATA_GAP without artifacts; DENVER and TRADERS_INTELLIGENCE may
    # be ACCUMULATING if their fixture files exist locally, but gap count > 0
    assert registry["gap_count"] > 0
    # Ledger also gap
    assert result["trade_truth_ledger"]["status"] == "DATA_GAP"


# ── 4. EPOCH_MANIFEST_GAP ─────────────────────────────────────────────────────

def test_epoch_manifest_gap_when_no_manifest(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    epoch = result["epoch_and_regime_attribution"]
    assert epoch["status"] == "EPOCH_MANIFEST_GAP"
    assert epoch["regime_change_safe_to_assert"] is False


def test_epoch_manifest_loaded_when_file_exists(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    manifest_path = data_dir / "policy_epochs_manifest.json"
    _write_json(manifest_path, [{"epoch": "A"}, {"epoch": "B"}])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    epoch = result["epoch_and_regime_attribution"]
    assert epoch["status"] == "MANIFEST_LOADED"
    assert epoch["entries"] == 2


# ── 5. Ledger unresolved — trade without identity → UNRESOLVED ────────────────

def test_ledger_marks_record_without_identity_as_unresolved(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Record with no id/eval_key/match_key
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"city": "Madrid", "date_iso": "2026-05-21", "side": "NO", "pnl": -0.50},
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    ledger = result["trade_truth_ledger"]
    assert ledger["unresolved_count"] == 1
    assert ledger["sample_unresolved"][0]["classification"] == "unresolved"


def test_ledger_classifies_pnl_without_outcome_as_pnl_diagnostic(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "t1", "city": "Madrid", "date_iso": "2026-05-21", "side": "NO", "pnl": -0.50},
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    ledger = result["trade_truth_ledger"]
    assert ledger["diagnostic_count"] == 1
    assert ledger["market_outcome_observed_count"] == 0


# ── 6. Verdict global — required fields ──────────────────────────────────────

def test_verdict_packet_has_required_fields(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    assert "verdict" in packet
    assert "pnl_canonical_confirmed" in packet
    assert "live_policy_eligible" in packet
    assert "autoexecute" in packet
    assert "disclaimer" in packet
    assert "registry_gap_count" in packet
    assert "epoch_status" in packet
    from tools._weather_strategy_engine import (
        VERDICT_KEEP_ACCUMULATING, VERDICT_TRUTH_GAP,
        VERDICT_EXIT_CANDIDATE, VERDICT_COHORT_CANDIDATE, VERDICT_INSUFFICIENT,
    )
    assert packet["verdict"] in {
        VERDICT_KEEP_ACCUMULATING, VERDICT_TRUTH_GAP,
        VERDICT_EXIT_CANDIDATE, VERDICT_COHORT_CANDIDATE, VERDICT_INSUFFICIENT,
    }


def test_verdict_insufficient_when_no_artifacts(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    # No artifacts at all → all DATA_GAP + ledger DATA_GAP → INSUFFICIENT_EVIDENCE
    # pnl_canonical_confirmed=false is a live-blocker, NOT a diagnostic blocker in V1
    assert packet["verdict"] == VERDICT_INSUFFICIENT
    assert packet["pnl_canonical_confirmed"] is False
    assert packet["live_policy_eligible"] is False


# ── 7. Madrid synthetic — UNRESOLVED_PNL_DISCREPANCY with nearest_match ──────

def test_madrid_may25_unresolved_when_only_may21_in_fixture(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Fixture: Madrid May 21 present, May 25 absent
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "t1", "city": "Madrid", "date_iso": "2026-05-21", "side": "NO", "pnl": 0.98},
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    lookup = result["trade_truth_ledger"]["city_date_lookup"]
    assert lookup["status"] == "UNRESOLVED_PNL_DISCREPANCY"
    assert lookup["nearest_match"] == "2026-05-21"
    assert lookup["date_requested"] == "2026-05-25"


def test_madrid_may21_found_when_exact_date_in_fixture(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "t1", "city": "Madrid", "date_iso": "2026-05-21", "side": "NO", "pnl": 0.98},
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-21", now=NOW)
    lookup = result["trade_truth_ledger"]["city_date_lookup"]
    assert lookup["status"] == "FOUND"


def test_madrid_lookup_data_gap_when_no_lifecycle(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    lookup = result["trade_truth_ledger"]["city_date_lookup"]
    # trade_lifecycle.json absent → DATA_GAP, not UNRESOLVED_PNL_DISCREPANCY
    assert lookup["status"] == "DATA_GAP"
    assert lookup["nearest_match"] is None


def test_madrid_unresolved_lookup_live_still_blocked(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "t1", "city": "Madrid", "date_iso": "2026-05-21", "side": "NO", "pnl": 0.98},
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    lookup = result["trade_truth_ledger"]["city_date_lookup"]
    # City/date lookup is UNRESOLVED_PNL_DISCREPANCY (May 25 not found, nearest May 21)
    assert lookup["status"] == "UNRESOLVED_PNL_DISCREPANCY"
    # The record IS classified in the ledger (not a ledger-level unresolved entry)
    # so unresolved_count=0 → verdict is NOT forced to TRUTH_GAP
    # Live is always blocked regardless of diagnostic verdict
    assert packet["live_policy_eligible"] is False
    assert packet["pnl_canonical_confirmed"] is False


# ── 8. DIRECTIONAL_NO_FORWARD is not exact/NO ────────────────────────────────

def test_directional_no_separate_from_exact_no(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Write resolutions with exact/NO (should NOT count as directional_no_rows)
    # and at_or_above/NO (should count)
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {"match_key": "k1", "city": "Tokyo", "condition": "exact", "side": "NO", "win_for_trader": True},
        {"match_key": "k2", "city": "Tokyo", "condition": "at_or_above", "side": "NO", "win_for_trader": True},
        {"match_key": "k3", "city": "Tokyo", "condition": "at_or_below", "side": "NO", "win_for_trader": False},
    ])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    directional = next(e for e in registry["experiments"] if e["key"] == "DIRECTIONAL_NO_FORWARD")
    # Only at_or_above and at_or_below count, not exact
    assert directional["directional_no_rows"] == 2
    assert directional["resolved_rows"] == 2
    assert directional["status"] == "ACCUMULATING_RESOLVED_SAMPLE"
    assert directional["live_promotion_authorized"] is False
    assert directional["shadow_exact_no_global_active"] is True


# ── 8b. DIRECTIONAL_NO_FORWARD status taxonomy ───────────────────────────────

def test_directional_no_artifact_missing_when_no_file(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    directional = next(e for e in registry["experiments"] if e["key"] == "DIRECTIONAL_NO_FORWARD")
    assert directional["status"] == "ARTIFACT_MISSING"
    assert directional["artifact_present"] is False


def test_directional_no_no_matching_rows_when_exact_only(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # BSR has exact/NO only — no at_or_above or at_or_below
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {"match_key": "k1", "city": "Tokyo", "condition": "exact", "side": "NO", "win_for_trader": True},
        {"match_key": "k2", "city": "Paris", "condition": "exact", "side": "YES", "win_for_trader": False},
    ])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    directional = next(e for e in registry["experiments"] if e["key"] == "DIRECTIONAL_NO_FORWARD")
    assert directional["status"] == "NO_MATCHING_ROWS_OBSERVED"
    assert directional["artifact_present"] is True
    assert directional["directional_no_rows"] == 0


def test_directional_no_accumulating_unresolved(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # at_or_above rows with no resolved outcome
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {"match_key": "k1", "city": "Tokyo", "condition": "at_or_above", "side": "NO"},
        {"match_key": "k2", "city": "Paris", "condition": "at_or_below", "side": "NO"},
    ])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    directional = next(e for e in registry["experiments"] if e["key"] == "DIRECTIONAL_NO_FORWARD")
    assert directional["status"] == "ACCUMULATING_UNRESOLVED"
    assert directional["directional_no_rows"] == 2
    assert directional["resolved_rows"] == 0


# ── 9. Provenance — diagnostic evidence stays diagnostic ─────────────────────

def test_market_outcome_observed_marked_as_diagnostic_not_live(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Trade with resolved outcome (win_for_trader known)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [{"id": "t1", "match_key": "k1", "city": "Seoul", "date_iso": "2026-05-10", "side": "NO"}]
    })
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {"match_key": "k1", "city": "Seoul", "win_for_trader": True}
    ])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    ledger = result["trade_truth_ledger"]
    # BSR join via exact match_key → market_outcome_observed classification
    assert ledger["market_outcome_observed_count"] == 1
    assert ledger["pnl_canonical_confirmed"] is False
    # settlement_confirmed label no longer used
    assert "settlement_confirmed" not in str(ledger)
    assert result["weather_strategy_verdict_packet"]["live_policy_eligible"] is False


def test_pnl_canonical_confirmed_always_false_v1(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Even with a full manifest and all data present, V1 keeps pnl_canonical_confirmed=false
    _write_json(data_dir / "policy_epochs_manifest.json", [{"epoch": "A"}])
    _write_json(data_dir / "trade_lifecycle.json", {"records": []})
    _write_jsonl(data_dir / "bot_signal_evaluations.jsonl", [])
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    assert result["weather_strategy_verdict_packet"]["pnl_canonical_confirmed"] is False


# ── 10. CLI integration ───────────────────────────────────────────────────────

def test_main_weather_strategy_json(tmp_path: Path, capsys) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    exit_code = main([
        "--scope", "weather_strategy",
        "--format", "json",
        "--repo-root", str(repo_root),
        "--data-dir", str(data_dir),
        "--now", NOW.isoformat(),
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    out = json.loads(captured.out)
    assert out["scope_type"] == "weather_strategy"
    assert out["results"]["weather_strategy_verdict_packet"]["live_policy_eligible"] is False


def test_main_weather_strategy_markdown(tmp_path: Path, capsys) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    exit_code = main([
        "--scope", "weather_strategy",
        "--format", "md",
        "--repo-root", str(repo_root),
        "--data-dir", str(data_dir),
        "--now", NOW.isoformat(),
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "LIVE_POLICY_ELIGIBLE=false" in captured.out
    assert "Weather Strategy" in captured.out


def test_main_weather_strategy_with_city_date(tmp_path: Path, capsys) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [{"id": "t1", "city": "Madrid", "date_iso": "2026-05-21", "side": "NO"}]
    })
    exit_code = main([
        "--scope", "weather_strategy",
        "--city", "Madrid",
        "--date", "2026-05-25",
        "--repo-root", str(repo_root),
        "--data-dir", str(data_dir),
        "--now", NOW.isoformat(),
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    out = json.loads(captured.out)
    lookup = out["results"]["trade_truth_ledger"]["city_date_lookup"]
    assert lookup["status"] == "UNRESOLVED_PNL_DISCREPANCY"
    assert lookup["nearest_match"] == "2026-05-21"


# ── 11. pnl_cash in close_context recognized as P&L diagnostic ───────────────

def test_pnl_cash_in_close_context_recognized(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Real Railway schema: pnl_cash lives inside close_context, not at top level
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {
                "id": "real-id-123",
                "city": "Madrid",
                "date": "2026-05-25",
                "condition": "exact",
                "side": "NO",
                "close_context": {"close_action": "SELL", "close_reason": "sl_intra", "pnl_cash": -13.94},
            }
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    ledger = result["trade_truth_ledger"]
    assert ledger["diagnostic_count"] == 1
    assert ledger["unresolved_count"] == 0
    lookup = ledger["city_date_lookup"]
    assert lookup["status"] == "FOUND"
    assert lookup["records"][0]["pnl_value"] == -13.94
    assert lookup["records"][0]["close_action"] == "SELL"
    assert lookup["records"][0]["classification"] == "pnl_diagnostic"


def test_pnl_cash_top_level_also_recognized(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [{"id": "t1", "city": "Seoul", "date": "2026-05-10", "pnl_cash": 1.23}]
    })
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    assert result["trade_truth_ledger"]["diagnostic_count"] == 1


# ── 12. date field (not date_iso) finds record ────────────────────────────────

def test_date_field_not_date_iso_finds_record(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Record uses 'date' field, date_iso is empty/absent (real Railway schema)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "r1", "city": "Madrid", "date": "2026-05-25", "date_iso": "", "side": "NO",
             "close_context": {"pnl_cash": -13.94}}
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    lookup = result["trade_truth_ledger"]["city_date_lookup"]
    assert lookup["status"] == "FOUND"
    assert lookup["records"][0]["date"] == "2026-05-25"


# ── 13. Diagnostic verdict emitted while LIVE_POLICY_ELIGIBLE=false ──────────

def test_diagnostic_verdict_keep_accumulating_with_live_false(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Provide enough evidence for accumulating verdict
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "t1", "city": "Paris", "date": "2026-05-20", "close_context": {"pnl_cash": -2.19}},
            {"id": "t2", "city": "Tokyo", "date": "2026-05-21", "close_context": {"pnl_cash": 1.50}},
        ]
    })
    _write_json(data_dir / "bankroll_readiness_state.json", {"status": "WATCH", "composite": 0.4})
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    # With lifecycle + bankroll present, accumulating_count >= 2 → KEEP_ACCUMULATING
    assert packet["verdict"] == VERDICT_KEEP_ACCUMULATING
    # V1 invariants always hold even with positive diagnostic verdict
    assert packet["live_policy_eligible"] is False
    assert packet["pnl_canonical_confirmed"] is False
    assert packet["autoexecute"] is False


def test_truth_gap_when_ledger_has_unresolved_entries(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Records with no identity → unresolved
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"city": "Paris", "date": "2026-05-20"},  # no id
        ]
    })
    _write_json(data_dir / "bankroll_readiness_state.json", {"status": "WATCH"})
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    assert packet["verdict"] == VERDICT_TRUTH_GAP
    assert packet["unresolved_ledger_entries"] == 1
    assert packet["live_policy_eligible"] is False


# ── 14. Phase 2 always PHASE2_STATE_NOT_MACHINE_READABLE ─────────────────────

def test_phase2_always_not_machine_readable_when_no_file(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    p2 = next(e for e in registry["experiments"] if e["key"] == "PHASE_2")
    assert p2["status"] == "PHASE2_STATE_NOT_MACHINE_READABLE"
    assert p2["canonical_state"] is None
    assert p2["live_promotion_authorized"] is False
    assert "2026-06-09" in p2["trigger"]


def test_phase2_not_machine_readable_even_with_log_only_file(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Provide the LOG_ONLY artifact — Phase 2 must still be NOT_MACHINE_READABLE
    _write_jsonl(data_dir / "exact_no_qt_match_evaluations_log_only.jsonl", [
        {"city": "Paris", "condition": "exact", "side": "NO", "eval_key": "k1"},
        {"city": "Tokyo", "condition": "exact", "side": "NO", "eval_key": "k2"},
    ])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    p2 = next(e for e in registry["experiments"] if e["key"] == "PHASE_2")
    assert p2["status"] == "PHASE2_STATE_NOT_MACHINE_READABLE"
    # Supporting artifact info is present but clearly marked as non-canonical
    assert p2["supporting_artifact"]["present"] is True
    assert p2["supporting_artifact"]["row_count"] == 2
    assert "not canonical" in p2["supporting_artifact"]["note"].lower()


# ── 15. FOUND lookup includes enriched record detail ─────────────────────────

def test_found_lookup_includes_enriched_detail(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {
                "id": "tok123",
                "city": "Seoul",
                "date": "2026-05-15",
                "condition": "exact",
                "side": "YES",
                "close_context": {"close_action": "SELL", "close_reason": "sl_intra", "pnl_cash": 2.50},
            }
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, city="Seoul", date="2026-05-15", now=NOW)
    lookup = result["trade_truth_ledger"]["city_date_lookup"]
    assert lookup["status"] == "FOUND"
    assert lookup["record_count"] == 1
    rec = lookup["records"][0]
    assert rec["city"] == "Seoul"
    assert rec["date"] == "2026-05-15"
    assert rec["condition"] == "exact"
    assert rec["side"] == "YES"
    assert rec["pnl_value"] == 2.50
    assert rec["close_action"] == "SELL"
    assert rec["classification"] == "pnl_diagnostic"
    assert rec["provenance_level"] == "pnl_diagnostic"


# ── 16. Madrid May 25 — stop_loss enriched diagnostic flags ──────────────────

def test_madrid_may25_enriched_stop_loss_flags(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {
                "id": "tok52089",
                "city": "Madrid",
                "date": "2026-05-25",
                "condition": "exact",
                "side": "NO",
                "token_id": "tok52089",
                "entry_context": {"edge_pct": 38.4, "our_prob": 80.9, "forecast_max": 31.5},
                "close_context": {
                    "close_action": "SELL",
                    "close_reason": "stop_loss",
                    "pnl_cash": -13.94,
                },
            }
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    lookup = result["trade_truth_ledger"]["city_date_lookup"]
    assert lookup["status"] == "FOUND"
    rec = lookup["records"][0]
    assert rec["pnl_value"] == -13.94
    assert rec["close_action"] == "SELL"
    assert rec["close_reason"] == "stop_loss"
    flags = rec.get("diagnostic_evidence_flags", [])
    assert "DIAGNOSTIC_EXIT_DAMAGE_EVIDENCE_PRESENT" in flags
    assert "DIAGNOSTIC_ALPHA_LOSS_EVIDENCE_PRESENT" in flags
    assert "UNRESOLVED_BY_OUTCOME_JOIN_GAP" in flags
    # token_id present so no SOURCE_OR_EPOCH_GAP
    assert "SOURCE_OR_EPOCH_GAP" not in flags
    # No question field → derivation fails → BLOCKED_no_match_key
    assert rec.get("join_method") == "BLOCKED_no_match_key"
    assert rec.get("match_key_derivation_status") == "failed_closed"
    assert "question_absent" in (rec.get("derivation_failure_reason") or "")
    assert rec.get("entry_edge_pct") == 38.4
    assert rec.get("entry_our_prob") == 80.9
    assert rec.get("entry_forecast_max") == 31.5


def test_madrid_no_alpha_flag_when_no_entry_context(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {
                "id": "tok1",
                "city": "Madrid",
                "date": "2026-05-25",
                "token_id": "tok1",
                "close_context": {"close_action": "SELL", "close_reason": "stop_loss", "pnl_cash": -5.0},
            }
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    rec = result["trade_truth_ledger"]["city_date_lookup"]["records"][0]
    flags = rec.get("diagnostic_evidence_flags", [])
    assert "DIAGNOSTIC_EXIT_DAMAGE_EVIDENCE_PRESENT" in flags
    assert "DIAGNOSTIC_ALPHA_LOSS_EVIDENCE_PRESENT" not in flags


# ── 17. Ledger join_key_analysis ─────────────────────────────────────────────

def test_ledger_join_key_analysis_blocked_when_no_keys(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Records with id but no match_key or eval_key (real Railway schema)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "t1", "token_id": "tok1", "city": "Madrid", "date": "2026-05-25"},
            {"id": "t2", "token_id": "tok2", "city": "Seoul", "date": "2026-05-10"},
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    jka = result["trade_truth_ledger"]["join_key_analysis"]
    assert jka["lifecycle_to_postmortem"] == "KEYS_PRESENT_NOT_VALIDATED_AGAINST_POSTMORTEM"
    assert "BLOCKED" in jka["lifecycle_to_resolutions"]
    assert "BLOCKED" in jka["lifecycle_to_evaluations"]
    assert jka["records_with_match_key"] == 0
    assert jka["records_with_eval_key"] == 0
    assert jka["records_with_token_id"] == 2
    assert jka["outcome_resolution_available"] is False


def test_ledger_join_key_partial_when_some_records_have_match_key(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "t1", "match_key": "mk1", "city": "Seoul"},
            {"id": "t2", "city": "Paris"},
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    jka = result["trade_truth_ledger"]["join_key_analysis"]
    assert jka["records_with_match_key"] == 1
    assert "PARTIAL_1" in jka["lifecycle_to_resolutions"]


# ── 18. Price filter — edge_pct field and rich stats ─────────────────────────

def test_price_filter_edge_pct_counted(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_jsonl(data_dir / "price_filter_counterfactual_log_only.jsonl", [
        {
            "cycle_id": "2026-05-27T00:00", "eval_key": "Shanghai|2026-05-27|at_or_above|32|C",
            "city": "Shanghai", "edge_pct": 8.5, "token_id_yes": "tok_y1", "token_id_no": "tok_n1",
        },
        {
            "cycle_id": "2026-05-27T00:00", "eval_key": "Shanghai|2026-05-27|at_or_above|30|C",
            "city": "Shanghai", "edge_pct": 3.0, "token_id_yes": "tok_y2", "token_id_no": "tok_n2",
        },
        {
            "cycle_id": "2026-05-27T00:00", "eval_key": "Tokyo|2026-05-27|exact|30|C",
            "city": "Tokyo", "edge_pct": 12.0,
        },
    ])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    pf = next(e for e in registry["experiments"] if e["key"] == "PRICE_FILTER_COUNTERFACTUAL")
    assert pf["row_count"] == 3
    assert pf["unique_cycles"] == 1
    assert pf["unique_eval_keys"] == 3
    assert pf["rows_with_edge_pct"] == 3
    assert pf["edge_pct_above_5pp"] == 2  # 8.5 and 12.0 qualify
    assert pf["outcomes_resolved"] == 0
    assert pf["status"] == "ACCUMULATING_NO_RESOLVED_OUTCOMES"
    assert pf["live_promotion_authorized"] is False


def test_price_filter_no_edge_field_counts_zero(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    # Records have no edge_pct field at all
    _write_jsonl(data_dir / "price_filter_counterfactual_log_only.jsonl", [
        {"cycle_id": "c1", "eval_key": "Paris|2026-05-01|exact|30|C", "city": "Paris"},
    ])
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    pf = next(e for e in registry["experiments"] if e["key"] == "PRICE_FILTER_COUNTERFACTUAL")
    assert pf["rows_with_edge_pct"] == 0
    assert pf["edge_pct_above_5pp"] == 0


# ── 19. Verdict packet — opus ratification flag and diagnostic lines ──────────

def test_verdict_packet_has_opus_ratification_flag(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    assert packet.get("requires_opus_ratification_before_policy_design") is True


def test_verdict_packet_has_diagnostic_lines(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {"records": [
        {"id": "t1", "city": "Paris", "date": "2026-05-20", "close_context": {"pnl_cash": -2.0}},
    ]})
    _write_json(data_dir / "bankroll_readiness_state.json", {"status": "WATCH"})
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    assert "lines_with_diagnostic_evidence" in packet
    assert "lines_blocked_by_truth_gap" in packet
    # With lifecycle + bankroll, at least EXITS_SL and PNL_BANKROLL are accumulating
    evidence_keys = {e["key"] for e in packet["lines_with_diagnostic_evidence"]}
    assert "EXITS_SL" in evidence_keys
    assert "PNL_BANKROLL" in evidence_keys
    # PHASE_2 and DIRECTIONAL_NO (no BSR file) should be in blocked
    blocked_keys = {e["key"] for e in packet["lines_blocked_by_truth_gap"]}
    assert "PHASE_2" in blocked_keys


# ── 20. Phase 2 extended description ─────────────────────────────────────────

def test_phase2_extended_description_has_t30_and_mixed_condition(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    registry = result["weather_experiment_registry"]
    p2 = next(e for e in registry["experiments"] if e["key"] == "PHASE_2")
    assert p2.get("trigger_date") == "2026-06-09"
    assert p2.get("mixed_condition_included") is True
    assert p2.get("exact_slice_protected") is True
    assert isinstance(p2.get("exact_slice_known_issues"), list)
    assert any("match_key" in issue for issue in p2["exact_slice_known_issues"])


# ── 21. MARKET_TRUTH_LEDGER_JOIN_BRIDGE_V1 — derive_match_key unit tests ──────

def test_derive_match_key_exact_success() -> None:
    record = {
        "city": "Madrid",
        "date": "2026-05-25",
        "condition": "exact",
        "question": "Will the highest temperature in Madrid be 32°C on May 25?",
    }
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "derived"
    assert r["derived_match_key"] == "Madrid|2026-05-25|exact|32|C"
    assert r["derivation_failure_reason"] is None


def test_derive_match_key_at_or_above_success() -> None:
    record = {
        "city": "Tokyo",
        "date": "2026-06-01",
        "condition": "at_or_above",
        "question": "Will the highest temperature in Tokyo be 30°C or higher on June 1?",
    }
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "derived"
    assert r["derived_match_key"] == "Tokyo|2026-06-01|at_or_above|30|C"


def test_derive_match_key_at_or_below_success() -> None:
    record = {
        "city": "Paris",
        "date": "2026-06-02",
        "condition": "at_or_below",
        "question": "Will the highest temperature in Paris be 20°C or below on June 2?",
    }
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "derived"
    assert r["derived_match_key"] == "Paris|2026-06-02|at_or_below|20|C"


def test_derive_match_key_empty_question_failed_closed() -> None:
    record = {"city": "Madrid", "date": "2026-05-25", "condition": "exact", "question": ""}
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "failed_closed"
    assert r["derived_match_key"] is None
    assert "question_absent" in r["derivation_failure_reason"]


def test_derive_match_key_no_question_field_failed_closed() -> None:
    record = {"city": "Madrid", "date": "2026-05-25", "condition": "exact"}
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "failed_closed"
    assert "question_absent" in r["derivation_failure_reason"]


def test_derive_match_key_city_absent_failed_closed() -> None:
    record = {"date": "2026-05-25", "condition": "exact", "question": "Will the highest temperature in Madrid be 32°C on May 25?"}
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "failed_closed"
    assert "city_absent" in r["derivation_failure_reason"]


def test_derive_match_key_date_absent_failed_closed() -> None:
    record = {"city": "Madrid", "condition": "exact", "question": "Will the highest temperature in Madrid be 32°C on May 25?"}
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "failed_closed"
    assert "date_absent" in r["derivation_failure_reason"]


def test_derive_match_key_condition_absent_failed_closed() -> None:
    record = {"city": "Madrid", "date": "2026-05-25", "question": "Will the highest temperature in Madrid be 32°C on May 25?"}
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "failed_closed"
    assert "condition_absent" in r["derivation_failure_reason"]


def test_derive_match_key_contradiction_failed_closed() -> None:
    # condition=exact but question says "or higher"
    record = {
        "city": "Paris",
        "date": "2026-06-01",
        "condition": "exact",
        "question": "Will the highest temperature in Paris be 25°C or higher on June 1?",
    }
    r = derive_match_key_from_lifecycle_record(record)
    assert r["match_key_derivation_status"] == "failed_closed"
    assert "contradiction" in r["derivation_failure_reason"]
    assert "at_or_above" in r["derivation_failure_reason"]


# ── 22. Bridge join — Madrid exact full success (Tarea 5 item 1) ──────────────

def test_bridge_madrid_exact_success(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [{
            "id": "tok52089",
            "city": "Madrid",
            "date": "2026-05-25",
            "condition": "exact",
            "side": "NO",
            "question": "Will the highest temperature in Madrid be 32°C on May 25?",
            "close_context": {"close_action": "SELL", "close_reason": "stop_loss", "pnl_cash": -13.94},
        }]
    })
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {
            "match_key": "Madrid|2026-05-25|exact|32|C",
            "outcome": "Yes",
            "market_id": "2336912",
            "condition_id": "cond123",
            "resolution_source": "polymarket_market_price",
            "win_for_trader": False,
        }
    ])
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    lookup = result["trade_truth_ledger"]["city_date_lookup"]
    assert lookup["status"] == "FOUND"
    rec = lookup["records"][0]
    assert rec["derived_match_key"] == "Madrid|2026-05-25|exact|32|C"
    assert rec["join_method"] == "derived_match_key"
    assert rec["market_outcome_observed"] == "YES"
    assert rec["bot_side_aligned_with_observed_outcome"] is False
    assert rec["market_truth_canonical"] is False
    assert rec["weather_truth_available"] is False
    assert rec["pnl_counterfactual_status"] == "R1_REQUIRED_FOR_CASH_COUNTERFACTUAL"
    # No overasserted labels
    assert "settlement_confirmed" not in str(rec)
    # No P&L counterfactual cash
    assert "hold_pnl_estimate" not in rec
    assert "EXIT_LIMITED_LOSS" not in str(rec)
    assert "EXIT_DESTROYED_ALPHA" not in str(rec)


def test_bridge_at_or_above_success(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [{
            "id": "t1",
            "city": "Tokyo",
            "date": "2026-06-01",
            "condition": "at_or_above",
            "side": "YES",
            "question": "Will the highest temperature in Tokyo be 30°C or higher on June 1?",
        }]
    })
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {
            "match_key": "Tokyo|2026-06-01|at_or_above|30|C",
            "outcome": "No",
            "market_id": "m1",
            "condition_id": "c1",
            "resolution_source": "polymarket_market_price",
            "win_for_trader": False,
        }
    ])
    result = build_weather_strategy_result(data_dir, repo_root, city="Tokyo", date="2026-06-01", now=NOW)
    rec = result["trade_truth_ledger"]["city_date_lookup"]["records"][0]
    assert rec["derived_match_key"] == "Tokyo|2026-06-01|at_or_above|30|C"
    assert rec["join_method"] == "derived_match_key"
    assert rec["market_outcome_observed"] == "NO"
    assert rec["bot_side_aligned_with_observed_outcome"] is False  # YES bet, NO outcome


def test_bridge_at_or_below_success(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [{
            "id": "t1",
            "city": "Paris",
            "date": "2026-06-02",
            "condition": "at_or_below",
            "side": "NO",
            "question": "Will the highest temperature in Paris be 20°C or below on June 2?",
        }]
    })
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {
            "match_key": "Paris|2026-06-02|at_or_below|20|C",
            "outcome": "Yes",
            "market_id": "m2",
            "condition_id": "c2",
            "resolution_source": "polymarket_market_price",
            "win_for_trader": True,
        }
    ])
    result = build_weather_strategy_result(data_dir, repo_root, city="Paris", date="2026-06-02", now=NOW)
    rec = result["trade_truth_ledger"]["city_date_lookup"]["records"][0]
    assert rec["derived_match_key"] == "Paris|2026-06-02|at_or_below|20|C"
    assert rec["join_method"] == "derived_match_key"
    assert rec["market_outcome_observed"] == "YES"
    assert rec["bot_side_aligned_with_observed_outcome"] is False  # NO side, YES outcome


# ── 23. Bridge join — no match → fail closed ──────────────────────────────────

def test_bridge_no_bsr_match_blocked(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [{
            "id": "t1",
            "city": "Seoul",
            "date": "2026-06-01",
            "condition": "exact",
            "side": "NO",
            "question": "Will the highest temperature in Seoul be 28°C on June 1?",
        }]
    })
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {"match_key": "Seoul|2026-06-01|exact|30|C", "outcome": "Yes", "win_for_trader": True}
    ])
    result = build_weather_strategy_result(data_dir, repo_root, city="Seoul", date="2026-06-01", now=NOW)
    rec = result["trade_truth_ledger"]["city_date_lookup"]["records"][0]
    assert rec["join_method"] == "BLOCKED_derived_key_no_bsr_match"
    assert rec.get("market_outcome_observed") is None


# ── 24. postmortem label corrected (Tarea 4 / Tarea 5 item 7) ─────────────────

def test_lifecycle_to_postmortem_honest_label(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [
            {"id": "t1", "token_id": "tok1", "city": "Madrid", "date": "2026-05-25"},
            {"id": "t2", "token_id": "tok2", "city": "Seoul", "date": "2026-05-10"},
        ]
    })
    result = build_weather_strategy_result(data_dir, repo_root, now=NOW)
    jka = result["trade_truth_ledger"]["join_key_analysis"]
    assert jka["lifecycle_to_postmortem"] == "KEYS_PRESENT_NOT_VALIDATED_AGAINST_POSTMORTEM"


# ── 25. BSR observed never elevates live/canonical (Tarea 5 item 8) ──────────

def test_bsr_observed_outcome_never_elevates_live_or_canonical(tmp_path: Path) -> None:
    repo_root, data_dir = _data_dir(tmp_path)
    _write_json(data_dir / "trade_lifecycle.json", {
        "records": [{
            "id": "tok52089",
            "city": "Madrid",
            "date": "2026-05-25",
            "condition": "exact",
            "side": "NO",
            "question": "Will the highest temperature in Madrid be 32°C on May 25?",
            "close_context": {"close_action": "SELL", "close_reason": "stop_loss", "pnl_cash": -13.94},
        }]
    })
    _write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [
        {
            "match_key": "Madrid|2026-05-25|exact|32|C",
            "outcome": "Yes",
            "market_id": "2336912",
            "condition_id": "cond123",
            "resolution_source": "polymarket_market_price",
            "win_for_trader": False,
        }
    ])
    result = build_weather_strategy_result(data_dir, repo_root, city="Madrid", date="2026-05-25", now=NOW)
    packet = result["weather_strategy_verdict_packet"]
    rec = result["trade_truth_ledger"]["city_date_lookup"]["records"][0]
    # V1 invariants hold regardless of observed outcome
    assert packet["live_policy_eligible"] is False
    assert packet["pnl_canonical_confirmed"] is False
    assert rec["market_truth_canonical"] is False
    # No CONFIRMED_MISSED_OPPORTUNITY anywhere in the output
    assert "CONFIRMED_MISSED_OPPORTUNITY" not in str(result)
    assert "LIVE_POLICY_ELIGIBLE=true" not in str(result)
    assert "P&L_CANONICAL_CONFIRMED=true" not in str(result)
