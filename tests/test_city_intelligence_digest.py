"""Focal tests for city_intelligence_digest — LOG_ONLY, read-only digest tool.

Tests:
  1. lifecycle manual_review_pending appears in Review Queue
  2. source onboarding candidates appear in Source Onboarding section
  3. WAITING_EVIDENCE is summarized (count) and does not produce per-city entries
  4. source audit NEEDS_MANUAL_SOURCE_LOOKUP appears as actionable
  5. Markdown/Telegram copy contains LOG_ONLY and all prohibitions
  6. silent_promotion_detected appears in both Review Queue and Drift section
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from city_intelligence_digest import (
    LOG_ONLY_DISCLAIMER,
    _ONBOARDING_QUIET_STATES,
    _REVIEW_QUEUE_TRANSITIONS,
    build_digest,
    build_onboarding_section,
    build_review_queue,
    build_source_audit_section,
    load_inputs,
    main,
    render_markdown,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_lifecycle_data(cities=None):
    return {
        "generated_at": "2026-05-14T10:00:00+00:00",
        "log_only": True,
        "summary": {
            "n_cities": len(cities or []),
            "transition_counts": {},
        },
        "cities": cities or [],
    }


def _make_onboarding_data(cities=None, degraded=False):
    return {
        "generated_at": "2026-05-14T10:00:00+00:00",
        "log_only": True,
        "degraded": degraded,
        "summary": {
            "n_candidates": len(cities or []),
            "state_counts": {},
        },
        "cities": cities or [],
    }


def _make_inputs(lifecycle_cities=None, onboarding_cities=None, audits=None):
    return {
        "lifecycle": _make_lifecycle_data(lifecycle_cities),
        "onboarding": _make_onboarding_data(onboarding_cities),
        "source_audits": audits or [],
        "promotion_gate": None,
    }


# ---------------------------------------------------------------------------
# Test 1: lifecycle manual_review_pending appears in Review Queue
# ---------------------------------------------------------------------------

def test_manual_review_pending_appears_in_review_queue():
    lifecycle_cities = [
        {
            "city": "Los Angeles",
            "lifecycle_stage": "observed_audit",
            "transition_proposed": "manual_review_pending",
            "override": {"manual_review_required_pre_canary": True, "reason": "test"},
            "gates_failed": [],
            "notes": ["manual_review_required_pre_canary=true (test)"],
        },
        {
            "city": "Tokyo",
            "lifecycle_stage": "active",
            "transition_proposed": "none",
            "override": None,
            "gates_failed": [],
            "notes": ["already active"],
        },
    ]
    inputs = _make_inputs(lifecycle_cities=lifecycle_cities)
    digest = build_digest(inputs)
    queue = digest["review_queue"]

    assert len(queue) == 1
    assert queue[0]["city"] == "Los Angeles"
    assert queue[0]["transition_proposed"] == "manual_review_pending"

    md = render_markdown(
        {"generated_at": "2026-05-14T10:00:00+00:00", "log_only": True},
        digest,
        [],
    )
    assert "Los Angeles" in md
    assert "manual_review_pending" in md
    assert "Tokyo" not in md.split("## 1.")[1].split("## 2.")[0]


# ---------------------------------------------------------------------------
# Test 2: source onboarding candidates appear in Source Onboarding section
# ---------------------------------------------------------------------------

def test_onboarding_ready_candidates_appear_in_section():
    onboarding_cities = [
        {
            "city": "Lucknow",
            "state": "READY_FOR_SOURCE_AUDIT",
            "priority_score": 2.1,
            "source_feasibility": "icao_and_station",
            "trader": {"n_sources": 3, "n_days": 5, "total_signals": 10, "range_count": 1, "range_fraction": 0.1},
            "blocked_signals": {"n": 25, "n_evaluated": 20, "wr": 0.72, "qualifies": True},
            "shadow": {"cycles_seen": 3, "edge_hits": 0},
            "score_components": {},
        },
    ]
    inputs = _make_inputs(onboarding_cities=onboarding_cities)
    digest = build_digest(inputs)
    onboarding = digest["onboarding"]

    assert len(onboarding["ready"]) == 1
    assert onboarding["ready"][0]["city"] == "Lucknow"

    md = render_markdown(
        {"generated_at": "2026-05-14T10:00:00+00:00", "log_only": True},
        digest,
        [],
    )
    assert "Lucknow" in md
    assert "READY_FOR_SOURCE_AUDIT" in md
    assert "2.10" in md or "2.1" in md


# ---------------------------------------------------------------------------
# Test 3: WAITING_EVIDENCE is summarized, not listed per city
# ---------------------------------------------------------------------------

def test_waiting_evidence_summarized_not_per_city():
    onboarding_cities = [
        {
            "city": "Karachi",
            "state": "WAITING_EVIDENCE",
            "priority_score": 0.6,
            "source_feasibility": "icao_and_station",
            "trader": {"n_sources": 1, "n_days": 2, "total_signals": 3, "range_count": 0, "range_fraction": 0.0},
            "blocked_signals": {"n": 5, "n_evaluated": 0, "wr": None, "qualifies": False},
            "shadow": {"cycles_seen": 0, "edge_hits": 0},
            "score_components": {},
        },
        {
            "city": "Brisbane",
            "state": "WAITING_EVIDENCE",
            "priority_score": 0.55,
            "source_feasibility": "icao_only",
            "trader": {"n_sources": 1, "n_days": 1, "total_signals": 2, "range_count": 0, "range_fraction": 0.0},
            "blocked_signals": {"n": 3, "n_evaluated": 0, "wr": None, "qualifies": False},
            "shadow": {"cycles_seen": 0, "edge_hits": 0},
            "score_components": {},
        },
    ]
    inputs = _make_inputs(onboarding_cities=onboarding_cities)
    digest = build_digest(inputs)
    onboarding = digest["onboarding"]

    assert onboarding["waiting_count"] == 2
    assert len(onboarding["ready"]) == 0

    md = render_markdown(
        {"generated_at": "2026-05-14T10:00:00+00:00", "log_only": True},
        digest,
        [],
    )
    # Individual cities should NOT appear in onboarding detail
    onboarding_section = md.split("## 2.")[1].split("## 3.")[0] if "## 2." in md else md
    assert "Karachi" not in onboarding_section
    assert "Brisbane" not in onboarding_section
    # But count should appear
    assert "2" in onboarding_section


# ---------------------------------------------------------------------------
# Test 4: source audit NEEDS_MANUAL_SOURCE_LOOKUP appears as actionable
# ---------------------------------------------------------------------------

def test_needs_manual_source_lookup_is_actionable():
    audits = [
        {
            "city": "San Francisco",
            "status": "NEEDS_MANUAL_SOURCE_LOOKUP",
            "log_only": True,
            "generated_at": "2026-05-14T08:38:48+00:00",
            "recommendation": "wait",
            "proposed_next_step": "manual source lookup",
        },
    ]
    inputs = _make_inputs(audits=audits)
    digest = build_digest(inputs)
    audit_section = digest["source_audits"]

    assert len(audit_section["actionable"]) == 1
    assert audit_section["actionable"][0]["city"] == "San Francisco"
    assert audit_section["actionable"][0]["status"] == "NEEDS_MANUAL_SOURCE_LOOKUP"

    md = render_markdown(
        {"generated_at": "2026-05-14T10:00:00+00:00", "log_only": True},
        digest,
        [],
    )
    assert "San Francisco" in md
    assert "NEEDS_MANUAL_SOURCE_LOOKUP" in md
    assert "manual source lookup" in md


# ---------------------------------------------------------------------------
# Test 5: Markdown/Telegram copy contains LOG_ONLY and all prohibitions
# ---------------------------------------------------------------------------

def test_markdown_contains_log_only_and_prohibitions():
    inputs = _make_inputs()
    digest = build_digest(inputs)
    md = render_markdown(
        {"generated_at": "2026-05-14T10:00:00+00:00", "log_only": True},
        digest,
        [],
    )

    assert "LOG_ONLY" in md
    assert "No BUY" in md or "No BUY, SELL" in md
    assert "BANKROLL" in md
    assert "Phase C" in md or "Fase C" in md or "No Phase C" in md
    assert "env vars" in md or "No env vars" in md
    assert "Railway" in md or "No Railway" in md
    assert "whitelist" in md or "canary" in md

    # LOG_ONLY_DISCLAIMER must be in the module constant and in the MD
    assert "LOG_ONLY" in LOG_ONLY_DISCLAIMER
    assert "No BUY" in LOG_ONLY_DISCLAIMER or "SELL" in LOG_ONLY_DISCLAIMER
    assert "BANKROLL" in LOG_ONLY_DISCLAIMER
    assert "Phase C" in LOG_ONLY_DISCLAIMER or "No Phase C" in LOG_ONLY_DISCLAIMER


# ---------------------------------------------------------------------------
# Test 6: silent_promotion_detected appears in Review Queue AND Drift section
# ---------------------------------------------------------------------------

def test_silent_promotion_appears_in_review_queue_and_drift():
    lifecycle_cities = [
        {
            "city": "Chicago",
            "lifecycle_stage": "blocked_by_source",
            "transition_proposed": "silent_promotion_detected",
            "override": None,
            "gates_failed": [],
            "notes": ["reason: city_in_auto_canary_and_blocked"],
        },
        {
            "city": "Istanbul",
            "lifecycle_stage": "shadow",
            "transition_proposed": "canary_review",
            "override": None,
            "gates_failed": [],
            "notes": ["T2 gates pass, promotion_gate=review_runtime_policy_gate"],
        },
    ]
    inputs = _make_inputs(lifecycle_cities=lifecycle_cities)
    digest = build_digest(inputs)

    review_queue = digest["review_queue"]
    drift = digest["drift"]

    # Both should appear in review queue
    queue_cities = {r["city"] for r in review_queue}
    assert "Chicago" in queue_cities
    assert "Istanbul" in queue_cities

    # Only Chicago (silent_promotion) should appear in drift
    assert len(drift) == 1
    assert drift[0]["city"] == "Chicago"

    # silent_promotion_detected sorts first
    assert review_queue[0]["city"] == "Chicago"
    assert review_queue[0]["transition_proposed"] == "silent_promotion_detected"

    md = render_markdown(
        {"generated_at": "2026-05-14T10:00:00+00:00", "log_only": True},
        digest,
        [],
    )
    assert "silent_promotion_detected" in md
    assert "Chicago" in md
    # Should appear in both Review Queue and Drift sections
    review_section = md.split("## 1.")[1].split("## 2.")[0] if "## 1." in md else ""
    drift_section = md.split("## 4.")[1].split("## 5.")[0] if "## 4." in md else ""
    assert "Chicago" in review_section
    assert "Chicago" in drift_section


def test_canary_watch_is_grouped_and_keeps_review_queue_count():
    lifecycle_cities = [
        {
            "city": "Toronto",
            "lifecycle_stage": "canary",
            "transition_proposed": "canary_watch",
            "effective_policy_status": "canary",
            "override": None,
            "gates_failed": ["canary_closed_trades<5(got 0)"],
            "gate_details": {
                "canary_closed_trades": 0,
                "canary_wr_closed": None,
                "canary_realized_pnl": 0.0,
            },
            "notes": ["Canary watch, not active-ready", "NO_ACTION / LOG_ONLY. Do not promote."],
        }
    ]
    inputs = _make_inputs(lifecycle_cities=lifecycle_cities)
    digest = build_digest(inputs)
    assert len(digest["review_queue"]) == 1
    assert digest["review_queue"][0]["transition_proposed"] == "canary_watch"

    md = render_markdown(
        {"generated_at": "2026-05-14T10:00:00+00:00", "log_only": True},
        digest,
        [],
    )
    assert "Canary Watch" in md
    assert "not active-ready" in md
    assert "Toronto" in md


def test_reporting_drift_blocked_effective_appears_in_drift_no_action():
    lifecycle_cities = [
        {
            "city": "Paris",
            "lifecycle_stage": "blocked_by_source",
            "effective_policy_status": "blocked",
            "transition_proposed": "reporting_drift_blocked_effective",
            "override": None,
            "gates_failed": [],
            "gate_details": {"operational_action": "NO_ACTION_LOG_ONLY"},
            "notes": ["Blocked effective - no action, reporting drift", "NO_ACTION / LOG_ONLY. Do not promote."],
        }
    ]
    inputs = _make_inputs(lifecycle_cities=lifecycle_cities)
    digest = build_digest(inputs)
    assert digest["drift"][0]["city"] == "Paris"
    assert digest["drift"][0]["transition_proposed"] == "reporting_drift_blocked_effective"

    md = render_markdown(
        {"generated_at": "2026-05-14T10:00:00+00:00", "log_only": True},
        digest,
        [],
    )
    assert "REPORTING_DRIFT_BLOCKED_EFFECTIVE" in md
    assert "NO_ACTION / LOG_ONLY" in md


# ---------------------------------------------------------------------------
# Integration test: main() writes JSON + MD files
# ---------------------------------------------------------------------------

def test_main_writes_outputs_with_minimal_inputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create minimal lifecycle JSON
        lifecycle_path = tmpdir_path / "lifecycle.json"
        lifecycle_path.write_text(json.dumps(_make_lifecycle_data([])), encoding="utf-8")

        # Create minimal onboarding JSON
        onboarding_path = tmpdir_path / "onboarding.json"
        onboarding_path.write_text(json.dumps(_make_onboarding_data([])), encoding="utf-8")

        audits_dir = tmpdir_path / "source_audits"
        audits_dir.mkdir()

        json_out = tmpdir_path / "digest.json"
        md_out = tmpdir_path / "digest.md"

        rc = main([
            "--lifecycle-review", str(lifecycle_path),
            "--source-onboarding", str(onboarding_path),
            "--source-audits-dir", str(audits_dir),
            "--json-output", str(json_out),
            "--md-output", str(md_out),
        ])

        assert rc == 0
        assert json_out.exists()
        assert md_out.exists()

        digest_data = json.loads(json_out.read_text(encoding="utf-8"))
        assert digest_data["log_only"] is True
        assert "LOG_ONLY" in digest_data["disclaimer"]
        assert "review_queue" in digest_data
        assert "summary" in digest_data

        md_content = md_out.read_text(encoding="utf-8")
        assert "LOG_ONLY" in md_content
        assert "City Intelligence Digest" in md_content
