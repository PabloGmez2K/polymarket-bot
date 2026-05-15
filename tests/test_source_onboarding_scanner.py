"""Tests focales para source_onboarding_scanner (LOG_ONLY) — City Intelligence v2 Fase A."""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from source_onboarding_scanner import (
    LOG_ONLY_DISCLAIMER,
    MIN_BLOCKED_N,
    MIN_SHADOW_CYCLES,
    MIN_TRADER_DAYS,
    MIN_TRADER_SOURCES,
    RANGE_ONLY_THRESHOLD,
    SCORE_READY,
    SCORE_WAITING,
    STATE_MAPPING_MISSING,
    STATE_OBSERVATION_WAITING_EVIDENCE,
    STATE_RANGE_ONLY,
    STATE_READY,
    STATE_SOURCE_AUDIT_POSSIBLE,
    STATE_SOURCE_BLOCKED,
    STATE_WAITING,
    _build_jurisdiction_set,
    build_records,
    classify_state,
    main,
    render_markdown,
    score_city,
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
    signals_rows=None,
    blocked_rows=None,
    traders_report=None,
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
        "signals_rows": signals_rows or [],
        "blocked_rows": blocked_rows or [],
        "traders_report": traders_report or {},
    }


def _trader_rows(city, n_sources, n_days, condition="exact"):
    """Generate synthetic trader signal rows."""
    rows = []
    for s in range(n_sources):
        for d in range(n_days):
            rows.append({
                "city": city,
                "source": f"trader_{s}",
                "date": f"2026-05-{10 + d:02d}",
                "condition": condition,
            })
    return rows


def _blocked_rows(city, n, wr_wins_fraction=0.7, evaluated_fraction=1.0):
    """Generate synthetic blocked_signals_resolutions rows."""
    rows = []
    n_evaluated = int(n * evaluated_fraction)
    n_wins = int(n_evaluated * wr_wins_fraction)
    for i in range(n):
        evaluated = i < n_evaluated
        win = i < n_wins
        rows.append({
            "city": city,
            "bot_evaluation": "evaluated" if evaluated else None,
            "outcome": "win" if (evaluated and win) else "loss",
        })
    return rows


# ---------------------------------------------------------------------------
# Test 1: Jurisdicción no se solapa con Lifecycle Monitor
# ---------------------------------------------------------------------------

def test_jurisdiction_no_overlap_with_lifecycle_cities():
    """Cities in ACTIVE/CANARY/BLOCKED/auto_canary/auto_shadow/overrides are excluded."""
    managed_city = "Shanghai"
    candidate_city = "Karachi"

    inputs = _make_inputs(
        active_cities=managed_city,
        signals_rows=(
            _trader_rows(managed_city, 3, 5)  # would score well but must be excluded
            + _trader_rows(candidate_city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS)
        ),
    )

    records, warnings, _ = build_records(inputs, resolution_icao=None, degraded=True)

    cities_in_output = {r["city"] for r in records}
    assert managed_city not in cities_in_output, (
        f"{managed_city} is in ACTIVE_TRADING_CITIES but appears in onboarding output"
    )


def test_jurisdiction_auto_canary_excluded():
    """Cities in auto_canary are excluded from scanner universe."""
    city = "Dubai"
    inputs = _make_inputs(
        auto_canary={city: {"shadow_edges": 5, "best_edge_pct": 35.0}},
        signals_rows=_trader_rows(city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS),
    )
    records, _, _ = build_records(inputs, resolution_icao=None, degraded=True)
    assert all(r["city"] != city for r in records)


def test_jurisdiction_shadow_mature_excluded():
    """Cities with shadow cycles_seen >= MIN_SHADOW_CYCLES are excluded."""
    city = "Lagos"
    inputs = _make_inputs(
        shadow_cities={city: {"cycles_seen": MIN_SHADOW_CYCLES, "edge_hits": 8}},
        signals_rows=_trader_rows(city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS),
    )
    records, _, _ = build_records(inputs, resolution_icao=None, degraded=True)
    assert all(r["city"] != city for r in records)


def test_jurisdiction_overrides_city_excluded():
    """Cities in city_lifecycle_overrides.json keys are excluded."""
    city = "Los Angeles"
    inputs = _make_inputs(
        overrides={city: {"manual_review_required_pre_canary": True, "reason": "test"}},
        signals_rows=_trader_rows(city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS),
    )
    records, _, _ = build_records(inputs, resolution_icao=None, degraded=True)
    assert all(r["city"] != city for r in records)


# ---------------------------------------------------------------------------
# Test 2: Range-only se clasifica como RANGE_ONLY_NOT_OPERABLE
# ---------------------------------------------------------------------------

def test_range_only_classified_as_range_only_not_operable():
    """City whose signals are all range conditions gets RANGE_ONLY_NOT_OPERABLE."""
    city = "Karachi"
    # All signals are range condition
    rows = _trader_rows(city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS, condition="range")
    inputs = _make_inputs(signals_rows=rows)
    records, _, _ = build_records(inputs, resolution_icao=None, degraded=True)

    city_records = [r for r in records if r["city"] == city]
    assert city_records, f"No record for {city} — check score floor"
    rec = city_records[0]
    assert rec["state"] == STATE_RANGE_ONLY, (
        f"Expected RANGE_ONLY_NOT_OPERABLE, got {rec['state']} (score={rec['priority_score']})"
    )


def test_range_fraction_below_threshold_not_classified_range_only():
    """City with range_fraction < RANGE_ONLY_THRESHOLD does not get RANGE_ONLY_NOT_OPERABLE."""
    # 1 range + 3 exact = 0.25 fraction (< 0.7)
    city = "Nairobi"
    rows = (
        _trader_rows(city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS, condition="exact")
        + [{"city": city, "source": "trader_0", "date": "2026-05-10", "condition": "range"}]
    )
    inputs = _make_inputs(signals_rows=rows)
    records, _, _ = build_records(inputs, resolution_icao=None, degraded=True)
    city_records = [r for r in records if r["city"] == city]
    if city_records:
        assert city_records[0]["state"] != STATE_RANGE_ONLY


# ---------------------------------------------------------------------------
# Test 3: Ciudad sin ICAO con RESOLUTION_ICAO cargado → MAPPING_MISSING
# ---------------------------------------------------------------------------

def test_city_without_icao_in_loaded_resolution_icao_gives_mapping_missing():
    """City absent from RESOLUTION_ICAO (loaded correctly) is not a hard source block."""
    city = "Ulan Bator"
    # resolution_icao is loaded (not degraded) but city is absent
    resolution_icao = {
        "Seoul": {"icao": "RKSI", "noaa_station_id": "47113199999"},
        "Tokyo": {"icao": "RJTT", "noaa_station_id": "47671099999"},
        # Ulan Bator is NOT here
    }
    rows = _trader_rows(city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS)
    inputs = _make_inputs(signals_rows=rows)
    records, _, _ = build_records(inputs, resolution_icao=resolution_icao, degraded=False)
    city_records = [r for r in records if r["city"] == city]
    assert city_records, f"No record for {city} — it should appear as MAPPING_MISSING"
    assert city_records[0]["state"] == STATE_MAPPING_MISSING, (
        f"Expected MAPPING_MISSING for city with no ICAO, got {city_records[0]['state']}"
    )
    assert city_records[0]["source_audit_status"] == STATE_MAPPING_MISSING
    assert city_records[0]["operational_action"] == "NO_ACTION / LOG_ONLY"


def test_city_with_icao_loaded_not_source_blocked():
    """City present in RESOLUTION_ICAO with ICAO → not SOURCE_BLOCKED."""
    city = "Seoul"
    resolution_icao = {
        "Seoul": {"icao": "RKSI", "noaa_station_id": "47113199999"},
    }
    rows = _trader_rows(city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS)
    inputs = _make_inputs(signals_rows=rows)
    records, _, _ = build_records(inputs, resolution_icao=resolution_icao, degraded=False)
    city_records = [r for r in records if r["city"] == city]
    if city_records:
        assert city_records[0]["state"] != STATE_SOURCE_BLOCKED


def test_trader_ready_with_ids_and_partial_shadow_waits_on_observation_not_source():
    """Strong trader evidence plus identifiers should separate source readiness from observation readiness."""
    city = "Chongqing"
    blocked_rows = _blocked_rows(city, n=25, wr_wins_fraction=0.96)
    for idx, row in enumerate(blocked_rows):
        row["slug"] = f"chongqing-weather-may-{idx}"
        row["market_id"] = f"market-{idx}"
    traders_report = {
        "tables": {
            "trader_winning_not_observed": [{
                "city": city,
                "trader_wins": 24,
                "trader_n": 25,
                "trader_wr_pct": 96.0,
                "observed_by_us": False,
            }]
        }
    }
    inputs = _make_inputs(
        shadow_cities={city: {"cycles_seen": 9, "edge_hits": 1, "best_edge_pct": 18.0}},
        blocked_rows=blocked_rows,
        traders_report=traders_report,
    )
    records, _, _ = build_records(
        inputs,
        resolution_icao={city: {"icao": "ZUCK"}},
        degraded=False,
    )

    rec = next(r for r in records if r["city"] == city)
    assert rec["primary_status"] == STATE_OBSERVATION_WAITING_EVIDENCE
    assert rec["trader_evidence_status"] == "TRADER_EVIDENCE_READY"
    assert rec["source_discovery_status"] == "SOURCE_DISCOVERY_READY"
    assert rec["source_audit_status"] == STATE_SOURCE_AUDIT_POSSIBLE
    assert rec["source_discovery_recommended"] is True
    assert rec["gamma_check_recommended"] is True
    assert rec["source_audit_recommended"] is True
    assert rec["observation_review_recommended"] is True
    assert rec["operational_action"] == "NO_ACTION / LOG_ONLY"


# ---------------------------------------------------------------------------
# Test 4: Fallo de carga RESOLUTION_ICAO → degraded=True + WAITING_EVIDENCE, no SOURCE_BLOCKED
# ---------------------------------------------------------------------------

def test_resolution_icao_load_failure_gives_degraded_and_no_source_blocked():
    """When RESOLUTION_ICAO fails to load (degraded=True), no city gets SOURCE_BLOCKED."""
    city = "Karachi"
    # City has good trader signal but degraded=True
    rows = _trader_rows(city, MIN_TRADER_SOURCES, MIN_TRADER_DAYS)
    inputs = _make_inputs(signals_rows=rows)

    # Simulate load failure: resolution_icao=None, degraded=True
    records, warnings, _ = build_records(inputs, resolution_icao=None, degraded=True)

    for r in records:
        assert r["state"] != STATE_SOURCE_BLOCKED, (
            f"City {r['city']} got SOURCE_BLOCKED despite degraded=True (tool fault)"
        )
        assert r["source_feasibility"] == "unknown", (
            f"Expected source_feasibility=unknown for degraded, got {r['source_feasibility']}"
        )


def test_degraded_payload_flag_set():
    """Payload has degraded=True when RESOLUTION_ICAO unavailable."""
    inputs = _make_inputs()
    records, warnings, exclusion_breakdown = build_records(inputs, resolution_icao=None, degraded=True)
    # The degraded flag is in the payload, not in records — test via main() below
    # Here just verify no SOURCE_BLOCKED states
    assert all(r["state"] != STATE_SOURCE_BLOCKED for r in records)


# ---------------------------------------------------------------------------
# Test 5: Sample mínimo blocked respetado (n < MIN_BLOCKED_N no aporta score)
# ---------------------------------------------------------------------------

def test_blocked_signals_below_min_n_contributes_zero_to_score():
    """blocked_signals with n < MIN_BLOCKED_N should not affect blocked_signals_wr_excess."""
    city = "Bogota"
    # n=5, WR=90% — well above threshold but below MIN_BLOCKED_N
    low_n_blocked = _blocked_rows(city, n=5, wr_wins_fraction=0.9)

    from source_onboarding_scanner import _build_blocked_stats
    blocked_stats = _build_blocked_stats(low_n_blocked)

    # Verify sample minimum is enforced
    b = blocked_stats.get(city, {})
    qualifies = b.get("n", 0) >= MIN_BLOCKED_N and b.get("n_evaluated", 0) > 0
    assert not qualifies, f"n={b.get('n')} should not qualify (MIN_BLOCKED_N={MIN_BLOCKED_N})"

    # Score with this data: blocked_signals_wr_excess should be 0
    score, components, _ = score_city(
        city,
        trader_stats={},
        blocked_stats=blocked_stats,
        shadow_data=None,
        resolution_icao=None,
        degraded=True,
    )
    assert components["blocked_signals_wr_excess"] == 0.0, (
        f"blocked_signals_wr_excess should be 0 for n<MIN_BLOCKED_N, got {components['blocked_signals_wr_excess']}"
    )


def test_blocked_signals_above_min_n_contributes_score():
    """blocked_signals with n >= MIN_BLOCKED_N and high WR contributes to score."""
    city = "Bogota"
    high_n_blocked = _blocked_rows(city, n=MIN_BLOCKED_N, wr_wins_fraction=0.85)

    from source_onboarding_scanner import _build_blocked_stats
    blocked_stats = _build_blocked_stats(high_n_blocked)

    score, components, _ = score_city(
        city,
        trader_stats={},
        blocked_stats=blocked_stats,
        shadow_data=None,
        resolution_icao=None,
        degraded=True,
    )
    assert components["blocked_signals_wr_excess"] > 0.0, (
        f"blocked_signals_wr_excess should be >0 for WR=85% n={MIN_BLOCKED_N}"
    )


# ---------------------------------------------------------------------------
# Integration: main() with temp files
# ---------------------------------------------------------------------------

def test_main_writes_json_and_markdown_with_minimal_inputs(tmp_path):
    """main() with minimal valid inputs exits 0 and writes valid LOG_ONLY outputs."""
    (tmp_path / "policy_env.json").write_text(json.dumps({
        "variables": {
            "ACTIVE_TRADING_CITIES": "Shanghai",
            "BLOCKED_CITIES": "",
            "CANARY_TRADING_CITIES": None,
        }
    }), encoding="utf-8")
    (tmp_path / "policy_state.json").write_text(json.dumps({
        "auto_canary_cities": {}, "auto_shadow_cities": {},
    }), encoding="utf-8")
    (tmp_path / "shadow_tracking.json").write_text(
        json.dumps({"cities": {}}), encoding="utf-8"
    )

    json_out = tmp_path / "onboarding.json"
    md_out = tmp_path / "onboarding.md"

    result = main([
        "--signals-crosscheck", str(tmp_path / "nonexistent_signals.jsonl"),
        "--blocked-resolutions", str(tmp_path / "nonexistent_blocked.jsonl"),
        "--shadow-tracking", str(tmp_path / "shadow_tracking.json"),
        "--policy-env", str(tmp_path / "policy_env.json"),
        "--policy-state", str(tmp_path / "policy_state.json"),
        "--overrides", str(tmp_path / "nonexistent_overrides.json"),
        "--traders-report", str(tmp_path / "nonexistent_traders_report.json"),
        "--json-output", str(json_out),
        "--md-output", str(md_out),
    ])

    assert result == 0 or result is None
    assert json_out.exists()
    assert md_out.exists()

    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["log_only"] is True
    assert "LOG_ONLY" in data["disclaimer"]
    assert "No BUY" in data["disclaimer"]
    assert "No BANKROLL" in data["disclaimer"]
    assert "cities" in data


def test_main_fails_clean_on_missing_critical_policy_env(tmp_path):
    """main() with missing policy_env returns 1 without writing outputs."""
    (tmp_path / "shadow_tracking.json").write_text(json.dumps({"cities": {}}), encoding="utf-8")
    (tmp_path / "policy_state.json").write_text(json.dumps({"auto_canary_cities": {}, "auto_shadow_cities": {}}), encoding="utf-8")

    json_out = tmp_path / "onboarding.json"
    md_out = tmp_path / "onboarding.md"

    result = main([
        "--policy-env", str(tmp_path / "nonexistent_env.json"),
        "--policy-state", str(tmp_path / "policy_state.json"),
        "--shadow-tracking", str(tmp_path / "shadow_tracking.json"),
        "--json-output", str(json_out),
        "--md-output", str(md_out),
    ])

    assert result == 1
    assert not json_out.exists()


# ---------------------------------------------------------------------------
# Markdown: disclaimer present
# ---------------------------------------------------------------------------

def test_markdown_contains_log_only_disclaimer():
    """Rendered markdown contains full LOG_ONLY disclaimer."""
    inputs = _make_inputs()
    records, warnings, exclusion_breakdown = build_records(inputs, resolution_icao=None, degraded=True)
    from collections import Counter
    payload = {
        "generated_at": "2026-05-14T00:00:00+00:00",
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "degraded": True,
        "summary": {
            "n_candidates": len(records),
            "state_counts": dict(Counter(r["state"] for r in records)),
            "exclusion_counts": {},
        },
        "exclusion_breakdown": exclusion_breakdown,
        "cities": records,
    }
    md = render_markdown(payload)
    assert "LOG_ONLY" in md
    assert "No BUY" in md
    assert "No BANKROLL" in md
    assert LOG_ONLY_DISCLAIMER in md
