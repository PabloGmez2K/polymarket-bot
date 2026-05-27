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
    assert ledger["settlement_confirmed_count"] == 0


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
    assert directional["live_promotion_authorized"] is False
    assert directional["shadow_exact_no_global_active"] is True


# ── 9. Provenance — diagnostic evidence stays diagnostic ─────────────────────

def test_settlement_confirmed_marked_as_diagnostic_not_live(tmp_path: Path) -> None:
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
    # Even with settlement_confirmed, pnl_canonical_confirmed stays false in V1
    assert ledger["settlement_confirmed_count"] == 1
    assert ledger["pnl_canonical_confirmed"] is False
    # And live_policy_eligible stays false
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
