"""Tests for city_lifecycle_review_monitor (LOG_ONLY)."""

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
    build_city_records,
    check_t2_gates,
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
        "promotion_gate": None,
    }


def _passing_shadow_data():
    """Returns shadow data that satisfies all T2 gates."""
    return {
        "edge_hits": T2_MIN_EDGE_HITS,
        "best_edge_pct": T2_MIN_BEST_EDGE_PCT + 5,
        "cycles_seen": T2_MIN_CYCLES,
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
# T1: Test — LA con T2 gates + override → manual_review_pending, NUNCA canary_review
# ---------------------------------------------------------------------------

def test_la_t2_satisfied_override_gives_manual_review_pending():
    """LA with T2 gates satisfied + manual_review_required_pre_canary → manual_review_pending."""
    inputs = _make_inputs(
        overrides={
            "Los Angeles": {
                "manual_review_required_pre_canary": True,
                "reason": "OBSERVED_AUDIT-only authorization 2026-05-13",
                "scope": ["pre_canary", "pre_active"],
            }
        },
        shadow_cities={"Los Angeles": _passing_shadow_data()},
    )
    records = build_city_records(inputs)
    la = next(r for r in records if r["city"] == "Los Angeles")

    assert la["lifecycle_stage"] == "observed_audit"
    assert la["transition_proposed"] == "manual_review_pending"
    assert la["transition_proposed"] != "canary_review"
    assert any("manual_review_required_pre_canary=true" in n for n in la["notes"])
    assert any("OBSERVED_AUDIT does not authorize trading" in n for n in la["notes"])


def test_la_never_canary_review_while_override_active():
    """LA must never emit canary_review while manual_review_required_pre_canary=true."""
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
                }
            },
        )
        records = build_city_records(inputs)
        la = next(r for r in records if r["city"] == "Los Angeles")
        assert la["transition_proposed"] != "canary_review", (
            f"LA emitted canary_review with edge_hits={edge_hits} — override not respected"
        )


# ---------------------------------------------------------------------------
# T2: Test — gates T1 incompletos → transition_proposed=none + gates_failed
# ---------------------------------------------------------------------------

def test_incomplete_t2_gates_produces_none_with_gates_failed():
    """City with insufficient shadow data → none + non-empty gates_failed."""
    inputs = _make_inputs(
        shadow_cities={
            "TestCity": {
                "edge_hits": 1,            # below T2_MIN_EDGE_HITS
                "best_edge_pct": 5.0,      # below T2_MIN_BEST_EDGE_PCT
                "cycles_seen": 2,          # below T2_MIN_CYCLES
            }
        }
    )
    records = build_city_records(inputs)
    tc = next(r for r in records if r["city"] == "TestCity")

    assert tc["transition_proposed"] == "none"
    assert len(tc["gates_failed"]) > 0


def test_no_shadow_data_gates_failed():
    """City with no shadow data at all → none + gates_failed contains no_shadow_data."""
    passed, failed, _ = check_t2_gates(None)
    assert not passed
    assert "no_shadow_data" in failed


def test_partial_gates_lists_specific_failures():
    """check_t2_gates reports which specific gates failed."""
    shadow = {"edge_hits": T2_MIN_EDGE_HITS, "best_edge_pct": 5.0, "cycles_seen": T2_MIN_CYCLES}
    passed, failed, details = check_t2_gates(shadow)
    assert not passed
    assert any("best_edge_pct" in f for f in failed)
    assert not any("edge_hits" in f for f in failed)


# ---------------------------------------------------------------------------
# T3: Test — silent_promotion_detected cuando runtime mode cambia sin evidencia
# ---------------------------------------------------------------------------

def test_silent_promotion_detected_auto_canary_and_blocked():
    """City in auto_canary AND BLOCKED → silent_promotion_detected."""
    inputs = _make_inputs(
        blocked_cities="Paris",
        auto_canary={
            "Paris": {"promoted_at": "2026-04-25T10:08:18", "best_edge_pct": 50.4, "shadow_edges": 5}
        },
        shadow_cities={
            "Paris": {"edge_hits": 5, "best_edge_pct": 50.4, "cycles_seen": 36}
        },
    )
    records = build_city_records(inputs)
    paris = next(r for r in records if r["city"] == "Paris")

    assert paris["transition_proposed"] == "silent_promotion_detected"


# ---------------------------------------------------------------------------
# T4: Test — determinismo
# ---------------------------------------------------------------------------

def test_deterministic_output_same_inputs():
    """Two runs with identical inputs produce identical JSON output."""
    inputs = _make_inputs(
        active_cities="Shanghai",
        blocked_cities="London",
        auto_canary={
            "Tokyo": {"promoted_at": "2026-04-06T07:20:18", "best_edge_pct": 28.3, "shadow_edges": 4}
        },
        shadow_cities={
            "Shanghai": {"edge_hits": 10, "best_edge_pct": 38.7, "cycles_seen": 15},
            "London": {"edge_hits": 2, "best_edge_pct": 20, "cycles_seen": 5},
            "Tokyo": {"edge_hits": 4, "best_edge_pct": 28.3, "cycles_seen": 10},
        },
    )
    records1 = build_city_records(inputs)
    records2 = build_city_records(inputs)

    assert json.dumps(records1, sort_keys=True) == json.dumps(records2, sort_keys=True)


# ---------------------------------------------------------------------------
# T5: Test — Markdown contiene disclaimer LOG_ONLY sin BUY/SELL/SKIP/BANKROLL/Fase C
# ---------------------------------------------------------------------------

def test_markdown_contains_log_only_disclaimer():
    """Markdown output contains full LOG_ONLY disclaimer with required keywords."""
    payload = _payload_from_inputs(_make_inputs())
    md = render_markdown(payload)

    assert "LOG_ONLY" in md
    assert "No BUY" in md
    assert "No BANKROLL" in md
    assert "No Phase C" in md
    assert LOG_ONLY_DISCLAIMER in md


def test_markdown_contains_disclaimer_at_top_and_bottom():
    """LOG_ONLY disclaimer appears at both top (blockquote) and footer of Markdown."""
    payload = _payload_from_inputs(_make_inputs())
    md = render_markdown(payload)
    lines = md.splitlines()

    top_disclaimer_line = next((l for l in lines if "LOG_ONLY" in l and l.startswith(">")), None)
    bottom_disclaimer_line = next((l for l in reversed(lines) if "LOG_ONLY" in l), None)

    assert top_disclaimer_line is not None, "No blockquote LOG_ONLY header found"
    assert bottom_disclaimer_line is not None, "No LOG_ONLY footer found"


# ---------------------------------------------------------------------------
# Integration — main() with temp paths
# ---------------------------------------------------------------------------

def test_main_writes_json_and_markdown():
    """main() with temp input files exits 0 and writes valid JSON + Markdown."""
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
            "auto_canary_cities": {},
            "auto_shadow_cities": {},
        }), encoding="utf-8")
        (tmp_path / "shadow_tracking.json").write_text(json.dumps({"cities": {}}), encoding="utf-8")
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
        assert "disclaimer" in data
        assert "LOG_ONLY" in data["disclaimer"]
        assert "cities" in data
        assert "summary" in data


def test_main_fails_clean_on_missing_critical_input():
    """main() with missing critical input returns 1 without writing outputs."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        json_out = tmp_path / "review.json"
        md_out = tmp_path / "review.md"

        result = main([
            "--policy-env", str(tmp_path / "nonexistent_policy_env.json"),
            "--policy-state", str(tmp_path / "nonexistent_policy_state.json"),
            "--shadow-tracking", str(tmp_path / "nonexistent_shadow.json"),
            "--json-output", str(json_out),
            "--md-output", str(md_out),
        ])

        assert result == 1
        assert not json_out.exists()


# ---------------------------------------------------------------------------
# classify_lifecycle_stage unit tests
# ---------------------------------------------------------------------------

def test_classify_blocked_has_priority_over_auto_canary():
    """blocked_by_source takes priority over auto_canary."""
    stage = classify_lifecycle_stage(
        "Paris",
        active_cities=set(),
        blocked_cities={"Paris"},
        canary_cities=set(),
        auto_canary_cities={"Paris"},
        auto_shadow_cities=set(),
        overrides={},
    )
    assert stage == "blocked_by_source"


def test_classify_active_has_priority_over_auto_canary():
    """active takes priority over auto_canary."""
    stage = classify_lifecycle_stage(
        "Shanghai",
        active_cities={"Shanghai"},
        blocked_cities=set(),
        canary_cities=set(),
        auto_canary_cities={"Shanghai"},
        auto_shadow_cities=set(),
        overrides={},
    )
    assert stage == "active"


def test_classify_observed_audit_for_override_only_city():
    """City not in any trading list but with override → observed_audit."""
    stage = classify_lifecycle_stage(
        "Los Angeles",
        active_cities=set(),
        blocked_cities=set(),
        canary_cities=set(),
        auto_canary_cities=set(),
        auto_shadow_cities=set(),
        overrides={"Los Angeles": {"manual_review_required_pre_canary": True}},
    )
    assert stage == "observed_audit"
