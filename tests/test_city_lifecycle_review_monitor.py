"""Tests for city_lifecycle_review_monitor (LOG_ONLY) — v1.1 strengthened gates."""

import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from city_lifecycle_review_monitor import (
    LOG_ONLY_DISCLAIMER,
    T2_MIN_BEST_EDGE_PCT,
    T2_MIN_CYCLES,
    T2_MIN_EDGE_HITS,
    T3_MIN_BEST_EDGE_PCT_AT_PROMOTION,
    T3_MIN_SHADOW_EDGES_AT_PROMOTION,
    _has_non_range_edge,
    build_canary_trade_metrics,
    build_city_records,
    check_t2_gates,
    check_t3_gates,
    classify_lifecycle_stage,
    main,
    render_markdown,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_inputs(
    active_cities="",
    blocked_cities="",
    canary_cities="",
    auto_canary=None,
    auto_shadow=None,
    shadow_cities=None,
    overrides=None,
    promotion_gate=None,
    trade_lifecycle=None,
):
    return {
        "policy_env": {
            "variables": {
                "ACTIVE_TRADING_CITIES": active_cities,
                "BLOCKED_CITIES": blocked_cities,
                "CANARY_TRADING_CITIES": canary_cities,
            }
        },
        "policy_state": {
            "auto_canary_cities": auto_canary or {},
            "auto_shadow_cities": auto_shadow or {},
        },
        "shadow_tracking": {"cities": shadow_cities or {}},
        "overrides": overrides or {},
        "promotion_gate": promotion_gate,
        "trade_lifecycle": trade_lifecycle,
    }


def _passing_shadow_data(city="TestCity"):
    """Shadow data satisfying all T2 gates including G4 (non-range edge)."""
    return {
        "edge_hits": T2_MIN_EDGE_HITS,
        "best_edge_pct": T2_MIN_BEST_EDGE_PCT + 5,
        "cycles_seen": T2_MIN_CYCLES,
        "recent_edges": [
            {
                "edge_hit": True,
                "question": f"Will the highest temperature in {city} be 25°C on date?",
                "side": "NO",
            }
        ],
    }


def _passing_promo_gate(city, gate_status="review_for_canary"):
    """Minimal promotion_gate dict with runtime available and one city row."""
    return {
        "summary": {"runtime_inputs_status": "available"},
        "cities": [{"city": city, "gate_status": gate_status}],
    }


def _payload_from_inputs(inputs):
    records = build_city_records(inputs)
    return {
        "generated_at": "2026-05-13T00:00:00+00:00",
        "summary": {
            "n_cities": len(records),
            "stage_counts": dict(Counter(r["lifecycle_stage"] for r in records)),
            "transition_counts": dict(Counter(r["transition_proposed"] for r in records)),
        },
        "cities": records,
    }


# ---------------------------------------------------------------------------
# G4: Non-range edge gate
# ---------------------------------------------------------------------------

def test_has_non_range_edge_exact():
    """Exact condition question passes G4."""
    assert _has_non_range_edge([
        {"edge_hit": True, "question": "Will the highest temperature be 25°C on date?"}
    ])


def test_has_non_range_edge_directional():
    """'or higher' directional condition passes G4."""
    assert _has_non_range_edge([
        {"edge_hit": True, "question": "Will temperature be 27°C or higher on May 13?"}
    ])


def test_has_non_range_edge_range_only_fails():
    """Range condition ('between X-Y') fails G4."""
    assert not _has_non_range_edge([
        {"edge_hit": True, "question": "Will the temperature be between 44-45°F on April 3?"}
    ])


def test_has_non_range_edge_all_filtered_fails():
    """All edge_hit=False entries fail G4 even with non-range questions."""
    assert not _has_non_range_edge([
        {"edge_hit": False, "question": "Will the highest temperature be 25°C?"},
        {"edge_hit": False, "question": "Will it be 26°C or higher?"},
    ])


def test_has_non_range_edge_empty_list_fails():
    assert not _has_non_range_edge([])
    assert not _has_non_range_edge(None)


# ---------------------------------------------------------------------------
# check_t2_gates unit tests
# ---------------------------------------------------------------------------

def test_t2_range_only_recent_edges_fail_g4():
    """City with passing stats 1-3 but only range recent edges fails T2."""
    shadow = {
        "edge_hits": T2_MIN_EDGE_HITS,
        "best_edge_pct": T2_MIN_BEST_EDGE_PCT + 10,
        "cycles_seen": T2_MIN_CYCLES,
        "recent_edges": [
            {"edge_hit": True, "question": "Will the temperature be between 44-45°F?", "side": "NO"},
        ],
    }
    passed, failed, _ = check_t2_gates(shadow)
    assert not passed
    assert any("non_range" in f or "range_only" in f for f in failed)


def test_t2_no_recent_edges_fails_g4():
    """City with no recent_edges fails T2 gate 4."""
    shadow = {
        "edge_hits": T2_MIN_EDGE_HITS,
        "best_edge_pct": T2_MIN_BEST_EDGE_PCT + 5,
        "cycles_seen": T2_MIN_CYCLES,
        "recent_edges": [],
    }
    passed, failed, _ = check_t2_gates(shadow)
    assert not passed
    assert any("recent_edges" in f for f in failed)


def test_t2_all_gates_pass_with_non_range_edge():
    """All T2 gates pass when non-range edge is present."""
    passed, failed, details = check_t2_gates(_passing_shadow_data())
    assert passed
    assert failed == []
    assert details["edge_hits"] == T2_MIN_EDGE_HITS


def test_t2_no_shadow_data_fails():
    passed, failed, _ = check_t2_gates(None)
    assert not passed
    assert "no_shadow_data" in failed


def test_t2_partial_stats_reports_specific_failure():
    """check_t2_gates reports which specific gates failed."""
    shadow = {
        "edge_hits": T2_MIN_EDGE_HITS,
        "best_edge_pct": 5.0,  # below threshold
        "cycles_seen": T2_MIN_CYCLES,
        "recent_edges": [{"edge_hit": True, "question": "Will temp be 25°C?"}],
    }
    passed, failed, _ = check_t2_gates(shadow)
    assert not passed
    assert any("best_edge_pct" in f for f in failed)
    assert not any("edge_hits<" in f for f in failed)


# ---------------------------------------------------------------------------
# check_t3_gates unit tests
# ---------------------------------------------------------------------------

def test_t3_no_auto_canary_entry_gives_none():
    proposed, failed, _, _ = check_t3_gates(None, None, False)
    assert proposed == "none"
    assert "no_auto_canary_entry" in failed


def test_t3_low_shadow_edges_gives_none():
    entry = {"shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION - 1, "best_edge_pct": 50}
    proposed, failed, _, _ = check_t3_gates(entry, None, False)
    assert proposed == "none"
    assert any("shadow_edges" in f for f in failed)


def test_t3_low_best_edge_pct_gives_none():
    entry = {"shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION, "best_edge_pct": 10}
    proposed, failed, _, _ = check_t3_gates(entry, None, False)
    assert proposed == "none"
    assert any("best_edge_pct" in f for f in failed)


def test_t3_metrics_pass_no_promo_gate_gives_preliminary():
    """T3 metrics pass but promotion_gate absent → preliminary_review_candidate."""
    entry = {
        "shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION,
        "best_edge_pct": T3_MIN_BEST_EDGE_PCT_AT_PROMOTION + 5,
    }
    proposed, failed, _, notes = check_t3_gates(entry, None, has_promotion_gate=False)
    assert proposed == "preliminary_review_candidate"
    assert "insufficient for active_review" in " ".join(notes)


def test_t3_metrics_pass_observe_runtime_canary_gives_canary_watch_without_sample():
    """T3 metrics pass + promotion_gate observe_runtime_canary → active_review."""
    entry = {
        "shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION + 2,
        "best_edge_pct": T3_MIN_BEST_EDGE_PCT_AT_PROMOTION + 10,
    }
    promo_row = {"city": "Dubai", "gate_status": "observe_runtime_canary"}
    proposed, failed, details, notes = check_t3_gates(entry, promo_row, has_promotion_gate=True)
    assert proposed == "canary_watch"
    assert details.get("promotion_gate_status") == "observe_runtime_canary"
    assert any("canary_closed_trades" in f for f in failed)
    assert "not active-ready" in " ".join(notes)


def test_t3_metrics_pass_with_closed_trade_sample_gives_active_review():
    """active_review requires promotion metrics plus enough closed canary evidence."""
    entry = {
        "shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION + 2,
        "best_edge_pct": T3_MIN_BEST_EDGE_PCT_AT_PROMOTION + 10,
    }
    promo_row = {"city": "Dubai", "gate_status": "observe_runtime_canary"}
    proposed, failed, details, _ = check_t3_gates(
        entry,
        promo_row,
        has_promotion_gate=True,
        canary_metrics={"closed": 5, "wins": 3, "wr_closed": 60.0, "realized_pnl": 0.0},
    )
    assert proposed == "active_review"
    assert failed == []
    assert details["canary_closed_trades"] == 5


def test_t3_metrics_pass_other_gate_status_gives_preliminary():
    """T3 metrics pass but gate_status not in confirm set → preliminary_review_candidate."""
    entry = {
        "shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION + 2,
        "best_edge_pct": T3_MIN_BEST_EDGE_PCT_AT_PROMOTION + 10,
    }
    promo_row = {"city": "Dubai", "gate_status": "review_for_canary"}
    proposed, _, _, _ = check_t3_gates(entry, promo_row, has_promotion_gate=True)
    assert proposed == "preliminary_review_candidate"


# ---------------------------------------------------------------------------
# LA: manual_review_required_pre_canary — must never emit canary_review
# ---------------------------------------------------------------------------

def test_la_t2_satisfied_override_gives_manual_review_pending():
    """LA with T2 gates satisfied (including G4) + override → manual_review_pending."""
    inputs = _make_inputs(
        overrides={
            "Los Angeles": {
                "manual_review_required_pre_canary": True,
                "reason": "OBSERVED_AUDIT-only authorization 2026-05-13",
                "scope": ["pre_canary", "pre_active"],
            }
        },
        shadow_cities={"Los Angeles": _passing_shadow_data("Los Angeles")},
    )
    records = build_city_records(inputs)
    la = next(r for r in records if r["city"] == "Los Angeles")

    assert la["lifecycle_stage"] == "observed_audit"
    assert la["transition_proposed"] == "manual_review_pending"
    assert la["transition_proposed"] != "canary_review"
    assert any("manual_review_required_pre_canary=true" in n for n in la["notes"])
    assert any("OBSERVED_AUDIT does not authorize trading" in n for n in la["notes"])


def test_la_never_canary_review_while_override_active():
    """LA must never emit canary_review regardless of edge_hits level."""
    for edge_hits in [T2_MIN_EDGE_HITS, T2_MIN_EDGE_HITS + 10, T2_MIN_EDGE_HITS + 50]:
        inputs = _make_inputs(
            overrides={
                "Los Angeles": {
                    "manual_review_required_pre_canary": True,
                    "reason": "OBSERVED_AUDIT-only authorization 2026-05-13",
                    "scope": ["pre_canary", "pre_active"],
                }
            },
            shadow_cities={
                "Los Angeles": {
                    "edge_hits": edge_hits,
                    "best_edge_pct": T2_MIN_BEST_EDGE_PCT + 20,
                    "cycles_seen": T2_MIN_CYCLES + 5,
                    "recent_edges": [
                        {
                            "edge_hit": True,
                            "question": "Will the highest temperature in Los Angeles be 25°C?",
                            "side": "NO",
                        }
                    ],
                }
            },
        )
        records = build_city_records(inputs)
        la = next(r for r in records if r["city"] == "Los Angeles")
        assert la["transition_proposed"] != "canary_review", (
            f"LA emitted canary_review with edge_hits={edge_hits} — override not respected"
        )


# ---------------------------------------------------------------------------
# T2 with promotion_gate
# ---------------------------------------------------------------------------

def test_shadow_passing_t2_no_promotion_gate_gives_preliminary():
    """City with all T2 gates passing (G1-G4) but no promotion_gate → preliminary."""
    inputs = _make_inputs(
        shadow_cities={"TestCity": _passing_shadow_data()},
    )
    records = build_city_records(inputs)
    tc = next(r for r in records if r["city"] == "TestCity")
    assert tc["transition_proposed"] == "preliminary_review_candidate"
    assert tc["lifecycle_stage"] == "shadow"


def test_shadow_passing_t2_with_promotion_gate_gives_canary_review():
    """City with all T2 gates passing AND promotion_gate → canary_review."""
    inputs = _make_inputs(
        shadow_cities={"TestCity": _passing_shadow_data()},
        promotion_gate=_passing_promo_gate("TestCity", "review_for_canary"),
    )
    records = build_city_records(inputs)
    tc = next(r for r in records if r["city"] == "TestCity")
    assert tc["transition_proposed"] == "canary_review"


def test_shadow_t2_blocking_gate_status_gives_preliminary():
    """City passing T2 stats but promotion_gate shows blocking status → preliminary."""
    inputs = _make_inputs(
        shadow_cities={"TestCity": _passing_shadow_data()},
        promotion_gate=_passing_promo_gate("TestCity", "background_watch"),
    )
    records = build_city_records(inputs)
    tc = next(r for r in records if r["city"] == "TestCity")
    assert tc["transition_proposed"] == "preliminary_review_candidate"


# ---------------------------------------------------------------------------
# T3 canary → active
# ---------------------------------------------------------------------------

def test_canary_without_promotion_gate_gives_preliminary():
    """Canary city without promotion_gate → preliminary_review_candidate."""
    inputs = _make_inputs(
        auto_canary={
            "Dubai": {
                "shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION + 2,
                "best_edge_pct": T3_MIN_BEST_EDGE_PCT_AT_PROMOTION + 10,
            }
        },
        shadow_cities={"Dubai": _passing_shadow_data("Dubai")},
    )
    records = build_city_records(inputs)
    dubai = next(r for r in records if r["city"] == "Dubai")
    assert dubai["lifecycle_stage"] == "canary"
    assert dubai["transition_proposed"] == "preliminary_review_candidate"


def test_canary_with_observe_runtime_canary_gives_canary_watch_without_sample():
    """Canary city with promotion_gate observe_runtime_canary → active_review."""
    inputs = _make_inputs(
        auto_canary={
            "Dubai": {
                "shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION + 2,
                "best_edge_pct": T3_MIN_BEST_EDGE_PCT_AT_PROMOTION + 10,
            }
        },
        shadow_cities={"Dubai": _passing_shadow_data("Dubai")},
        promotion_gate={
            "summary": {"runtime_inputs_status": "available"},
            "cities": [{"city": "Dubai", "gate_status": "observe_runtime_canary"}],
        },
    )
    records = build_city_records(inputs)
    dubai = next(r for r in records if r["city"] == "Dubai")
    assert dubai["lifecycle_stage"] == "canary"
    assert dubai["transition_proposed"] == "canary_watch"
    assert any("canary_closed_trades" in f for f in dubai["gates_failed"])


def test_canary_low_t3_metrics_gives_none():
    """Canary city with shadow_edges below T3 threshold → none."""
    inputs = _make_inputs(
        auto_canary={
            "Seoul": {
                "shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION - 3,
                "best_edge_pct": 26.4,
            }
        },
        shadow_cities={"Seoul": _passing_shadow_data("Seoul")},
    )
    records = build_city_records(inputs)
    seoul = next(r for r in records if r["city"] == "Seoul")
    assert seoul["lifecycle_stage"] == "canary"
    assert seoul["transition_proposed"] == "none"
    assert any("shadow_edges" in f for f in seoul["gates_failed"])


# ---------------------------------------------------------------------------
# T3: silent_promotion_detected
# ---------------------------------------------------------------------------

def test_silent_promotion_detected_auto_canary_and_blocked():
    """City in auto_canary AND BLOCKED → silent_promotion_detected."""
    inputs = _make_inputs(
        blocked_cities="Paris",
        auto_canary={
            "Paris": {"shadow_edges": 5, "best_edge_pct": 50.4}
        },
        shadow_cities={"Paris": _passing_shadow_data("Paris")},
    )
    records = build_city_records(inputs)
    paris = next(r for r in records if r["city"] == "Paris")
    assert paris["transition_proposed"] == "reporting_drift_blocked_effective"
    assert paris["effective_policy_status"] == "blocked"
    assert paris["operational_action"] == "NO_ACTION_LOG_ONLY"


def test_blocked_effective_wins_over_auto_canary_regardless_of_city_casing():
    inputs = _make_inputs(
        blocked_cities="paris",
        auto_canary={
            "Paris": {"shadow_edges": 5, "best_edge_pct": 50.4}
        },
        shadow_cities={"Paris": _passing_shadow_data("Paris")},
        promotion_gate={
            "summary": {"runtime_inputs_status": "available"},
            "cities": [{"city": "Paris", "gate_status": "observe_runtime_canary"}],
        },
        trade_lifecycle={
            "records": [
                {
                    "city": "Paris",
                    "opened_at": "2026-05-01T00:00:00+00:00",
                    "status": "closed",
                    "close_context": {"pnl_cash": 1.0},
                }
            ]
        },
    )
    records = build_city_records(inputs)
    paris_rows = [r for r in records if r["city"].lower() == "paris"]
    assert len(paris_rows) == 1
    paris = paris_rows[0]
    assert paris["effective_policy_status"] == "blocked"
    assert paris["transition_proposed"] == "reporting_drift_blocked_effective"
    assert paris["transition_proposed"] != "active_review"


# ---------------------------------------------------------------------------
# Incomplete T2 stats
# ---------------------------------------------------------------------------

def test_incomplete_t2_stats_produce_none_with_gates_failed():
    """City with insufficient shadow stats → none + non-empty gates_failed."""
    inputs = _make_inputs(
        shadow_cities={
            "TestCity": {
                "edge_hits": 1,
                "best_edge_pct": 5.0,
                "cycles_seen": 2,
                "recent_edges": [],
            }
        }
    )
    records = build_city_records(inputs)
    tc = next(r for r in records if r["city"] == "TestCity")
    assert tc["transition_proposed"] == "none"
    assert len(tc["gates_failed"]) > 0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_deterministic_output_same_inputs():
    """Two runs with identical inputs produce identical JSON output."""
    inputs = _make_inputs(
        active_cities="Shanghai",
        blocked_cities="London",
        auto_canary={
            "Tokyo": {"shadow_edges": 4, "best_edge_pct": 28.3}
        },
        shadow_cities={
            "Shanghai": _passing_shadow_data("Shanghai"),
            "London": {"edge_hits": 2, "best_edge_pct": 20, "cycles_seen": 5},
            "Tokyo": _passing_shadow_data("Tokyo"),
        },
    )
    records1 = build_city_records(inputs)
    records2 = build_city_records(inputs)
    assert json.dumps(records1, sort_keys=True) == json.dumps(records2, sort_keys=True)


# ---------------------------------------------------------------------------
# Markdown disclaimer
# ---------------------------------------------------------------------------

def test_markdown_contains_full_log_only_disclaimer():
    """Markdown contains full LOG_ONLY disclaimer with required keywords."""
    payload = _payload_from_inputs(_make_inputs())
    md = render_markdown(payload)
    assert "LOG_ONLY" in md
    assert "No BUY" in md
    assert "No BANKROLL" in md
    assert "No Phase C" in md
    assert LOG_ONLY_DISCLAIMER in md


def test_markdown_disclaimer_at_top_and_bottom():
    """LOG_ONLY disclaimer appears as blockquote header and as footer."""
    payload = _payload_from_inputs(_make_inputs())
    md = render_markdown(payload)
    lines = md.splitlines()
    top = next((l for l in lines if "LOG_ONLY" in l and l.startswith(">")), None)
    bottom = next((l for l in reversed(lines) if "LOG_ONLY" in l), None)
    assert top is not None, "No blockquote LOG_ONLY header found"
    assert bottom is not None, "No LOG_ONLY footer found"


def test_markdown_preliminary_candidate_in_review_queue():
    """preliminary_review_candidate cities appear in the Review Queue section."""
    inputs = _make_inputs(
        shadow_cities={"TestCity": _passing_shadow_data()},
        # No promotion_gate → preliminary_review_candidate
    )
    payload = _payload_from_inputs(inputs)
    md = render_markdown(payload)
    assert "preliminary_review_candidate" in md
    assert "TestCity" in md


# ---------------------------------------------------------------------------
# Integration — main() with temp paths
# ---------------------------------------------------------------------------

def test_main_writes_json_and_markdown():
    """main() with minimal temp input files exits 0 and writes valid outputs."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "policy_env.json").write_text(json.dumps({
            "variables": {
                "ACTIVE_TRADING_CITIES": "Shanghai",
                "BLOCKED_CITIES": "London",
                "CANARY_TRADING_CITIES": None,
            }
        }), encoding="utf-8")
        (tmp_path / "policy_state.json").write_text(json.dumps({
            "auto_canary_cities": {}, "auto_shadow_cities": {},
        }), encoding="utf-8")
        (tmp_path / "shadow_tracking.json").write_text(
            json.dumps({"cities": {}}), encoding="utf-8"
        )
        (tmp_path / "overrides.json").write_text(json.dumps({}), encoding="utf-8")

        json_out = tmp_path / "review.json"
        md_out = tmp_path / "review.md"

        result = main([
            "--policy-env", str(tmp_path / "policy_env.json"),
            "--policy-state", str(tmp_path / "policy_state.json"),
            "--shadow-tracking", str(tmp_path / "shadow_tracking.json"),
            "--overrides", str(tmp_path / "overrides.json"),
            "--json-output", str(json_out),
            "--md-output", str(md_out),
        ])

        assert result == 0 or result is None
        assert json_out.exists()
        assert md_out.exists()

        data = json.loads(json_out.read_text(encoding="utf-8"))
        assert data["log_only"] is True
        assert "No Phase C" in data["disclaimer"]
        assert "cities" in data


def test_main_fails_clean_on_missing_critical_input():
    """main() with missing critical input returns 1 without writing outputs."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        json_out = tmp_path / "review.json"
        md_out = tmp_path / "review.md"

        result = main([
            "--policy-env", str(tmp_path / "nonexistent.json"),
            "--policy-state", str(tmp_path / "nonexistent2.json"),
            "--shadow-tracking", str(tmp_path / "nonexistent3.json"),
            "--json-output", str(json_out),
            "--md-output", str(md_out),
        ])

        assert result == 1
        assert not json_out.exists()


# ---------------------------------------------------------------------------
# classify_lifecycle_stage unit tests
# ---------------------------------------------------------------------------

def test_classify_blocked_priority_over_auto_canary():
    stage = classify_lifecycle_stage(
        "Paris",
        active_cities=set(), blocked_cities={"Paris"}, canary_cities=set(),
        auto_canary_cities={"Paris"}, auto_shadow_cities=set(), overrides={},
    )
    assert stage == "blocked_by_source"


def test_classify_active_priority_over_auto_canary():
    stage = classify_lifecycle_stage(
        "Shanghai",
        active_cities={"Shanghai"}, blocked_cities=set(), canary_cities=set(),
        auto_canary_cities={"Shanghai"}, auto_shadow_cities=set(), overrides={},
    )
    assert stage == "active"


def test_classify_observed_audit_for_override_only_city():
    stage = classify_lifecycle_stage(
        "Los Angeles",
        active_cities=set(), blocked_cities=set(), canary_cities=set(),
        auto_canary_cities=set(), auto_shadow_cities=set(),
        overrides={"Los Angeles": {"manual_review_required_pre_canary": True}},
    )
    assert stage == "observed_audit"
