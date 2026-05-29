"""Tests for H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1.

All tests inject model/market fetchers — no real network calls.
Covers all 12 required test cases from the spec.
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

import pytest

# Engine imports
from tools._multimodel_engine import (
    EFFECTIVE_MODEL_IDS,
    H3_CANDIDATE_MODEL_ID,
    H3_FORMULA_VERSION,
    H3_HYPOTHESIS_ID,
    MIN_MODELS_REQUIRED,
    build_snapshot,
    brier,
    compute_candidate_prob,
    compute_consensus,
    compute_report,
    snapshot_key,
    ts_bucket_from_ts,
)

# ── Fixture data ──────────────────────────────────────────────────────────────

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "multimodel_open_meteo_sample.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _fixture_per_model_tmax() -> dict[str, float]:
    f = _load_fixture()
    return f["expected_per_model_tmax"]


# ── Stub fetchers ─────────────────────────────────────────────────────────────

def _stub_model_fetcher_ok(target_date, lat, lon, tz, model_ids):
    """Returns 5 models with distinct tmax values (fixture values for Shanghai)."""
    vals = {
        "ecmwf_ifs025": 27.4,
        "gfs_seamless":  28.1,
        "icon_seamless": 26.8,
        "jma_seamless":  25.9,
        "gem_seamless":  27.0,
    }
    return {m: vals.get(m) for m in model_ids}


def _stub_model_fetcher_3_models(target_date, lat, lon, tz, model_ids):
    """Returns only 3 models (below minimum)."""
    vals = {"ecmwf_ifs025": 27.4, "gfs_seamless": 28.1, "icon_seamless": 26.8}
    return {m: vals.get(m) for m in model_ids}


def _stub_market_ok(city, target_date, condition, threshold, unit="C"):
    return {
        "market_id": "mkt-test-001",
        "condition_id": "cond-test-001",
        "slug": "test-market-slug",
        "question": f"Will the highest temperature in {city} be {threshold}°C or higher on jun 1?",
        "mkt_prob_yes": 0.62,
    }


def _stub_market_none(city, target_date, condition, threshold, unit="C"):
    return None


# ── Test 1: Preflight/model parser with multi-model fixture ───────────────────

def test_fixture_loads_and_has_five_models():
    """Test 1: preflight/model parser with fixture of multiple models."""
    f = _load_fixture()
    tmax_map = f["expected_per_model_tmax"]
    assert len(tmax_map) == 5
    for m in EFFECTIVE_MODEL_IDS:
        assert m in tmax_map
        assert isinstance(tmax_map[m], (int, float))


# ── Test 2: consensus_mean_tmax ───────────────────────────────────────────────

def test_compute_consensus_mean():
    """Test 2: compute consensus_mean_tmax from fixture values."""
    per_model = _fixture_per_model_tmax()
    mean, _ = compute_consensus(per_model)
    expected_mean = round(sum(per_model.values()) / len(per_model), 4)
    assert abs(mean - expected_mean) < 0.01


# ── Test 3: inter_model_disagreement_std ─────────────────────────────────────

def test_compute_disagreement_std():
    """Test 3: compute inter_model_disagreement_std from fixture values."""
    per_model = _fixture_per_model_tmax()
    _, std = compute_consensus(per_model)
    # Sample std expected (n=5, ddof=1)
    vals = list(per_model.values())
    expected_std = round(statistics.stdev(vals), 4)
    assert abs(std - expected_std) < 0.02


# ── Test 4: candidate_prob_yes for at_or_above ────────────────────────────────

def test_candidate_prob_at_or_above():
    """Test 4: candidate_prob_yes for at_or_above condition."""
    per_model = _fixture_per_model_tmax()
    mean, std = compute_consensus(per_model)
    # Test threshold above mean: prob should be < 0.5
    prob = compute_candidate_prob(mean, std, mean + 1.0, "at_or_above")
    assert prob is not None
    assert 0.0 < prob < 0.5
    # Test threshold below mean: prob should be > 0.5
    prob2 = compute_candidate_prob(mean, std, mean - 1.0, "at_or_above")
    assert prob2 is not None
    assert prob2 > 0.5
    # At mean: prob ~= 0.5
    prob3 = compute_candidate_prob(mean, std, mean, "at_or_above")
    assert prob3 is not None
    assert abs(prob3 - 0.5) < 0.05


# ── Test 5: candidate_prob_yes for at_or_below ────────────────────────────────

def test_candidate_prob_at_or_below():
    """Test 5: candidate_prob_yes for at_or_below condition."""
    per_model = _fixture_per_model_tmax()
    mean, std = compute_consensus(per_model)
    # P(temp <= threshold) at threshold=mean ~= 0.5
    prob = compute_candidate_prob(mean, std, mean, "at_or_below")
    assert prob is not None
    assert abs(prob - 0.5) < 0.05
    # Threshold well below mean: prob should be < 0.5
    prob2 = compute_candidate_prob(mean, std, mean - 2.0, "at_or_below")
    assert prob2 is not None
    assert prob2 < 0.5
    # Symmetry: at_or_above + at_or_below at same threshold ≈ 1.0
    prob_above = compute_candidate_prob(mean, std, mean + 1.0, "at_or_above")
    prob_below = compute_candidate_prob(mean, std, mean + 1.0, "at_or_below")
    assert prob_above is not None and prob_below is not None
    assert abs(prob_above + prob_below - 1.0) < 0.001


# ── Test 6: fail-closed with fewer than MIN_MODELS_REQUIRED ──────────────────

def test_fail_closed_insufficient_models():
    """Test 6: build_snapshot fails closed when fewer than MIN_MODELS_REQUIRED models available."""
    with pytest.raises(ValueError, match="H3_MODEL_COVERAGE_PREFLIGHT_BLOCKED"):
        build_snapshot(
            city="Shanghai",
            target_date="2026-06-01",
            condition="at_or_above",
            threshold=28.0,
            unit="C",
            h3_prereg_cutoff_utc=None,
            model_fetch_fn=_stub_model_fetcher_3_models,
            market_fetch_fn=_stub_market_ok,
            model_ids=EFFECTIVE_MODEL_IDS,
        )


# ── Test 7: snapshot idempotency ──────────────────────────────────────────────

def test_snapshot_key_determinism():
    """Test 7: snapshot key is deterministic for same inputs."""
    k1 = snapshot_key("Shanghai", "mkt-001", "2026-06-01", "at_or_above", 28.0, "C", "2026-06-01T10:00:00Z")
    k2 = snapshot_key("Shanghai", "mkt-001", "2026-06-01", "at_or_above", 28.0, "C", "2026-06-01T10:00:00Z")
    assert k1 == k2

    # Different city → different key
    k3 = snapshot_key("Tokyo", "mkt-001", "2026-06-01", "at_or_above", 28.0, "C", "2026-06-01T10:00:00Z")
    assert k1 != k3

    # Different bucket → different key
    k4 = snapshot_key("Shanghai", "mkt-001", "2026-06-01", "at_or_above", 28.0, "C", "2026-06-01T11:00:00Z")
    assert k1 != k4


# ── Test 8: market_price and weather_models contemporaneous ───────────────────

def test_snapshot_contains_both_market_and_model_data():
    """Test 8: snapshot contains mkt_prob_yes and per_model_tmax from same call."""
    snap = build_snapshot(
        city="Shanghai",
        target_date="2026-06-01",
        condition="at_or_above",
        threshold=28.0,
        unit="C",
        h3_prereg_cutoff_utc="2026-06-01T00:00:00Z",
        model_fetch_fn=_stub_model_fetcher_ok,
        market_fetch_fn=_stub_market_ok,
        model_ids=EFFECTIVE_MODEL_IDS,
    )
    assert snap["mkt_prob_yes_at_snapshot"] == 0.62
    assert "per_model_tmax" in snap
    assert len(snap["per_model_tmax"]) == 5
    assert snap["n_models_available"] == 5
    assert snap["consensus_mean_tmax"] is not None
    assert snap["inter_model_disagreement_std"] is not None
    assert snap["candidate_prob_yes"] is not None
    assert snap["provenance"]["snapshot_contemporaneous"] is True


# ── Test 9: outcome join Gamma in report ──────────────────────────────────────

def test_report_joins_resolved_outcomes():
    """Test 9: compute_report correctly uses market_outcome_observed for scoring."""
    snaps = [
        {
            "h3_hypothesis_id": H3_HYPOTHESIS_ID,
            "candidate_prob_yes": 0.70,
            "mkt_prob_yes_at_snapshot": 0.60,
            "market_outcome_observed": "YES",
            "inter_model_disagreement_std": 1.2,
        },
        {
            "h3_hypothesis_id": H3_HYPOTHESIS_ID,
            "candidate_prob_yes": 0.30,
            "mkt_prob_yes_at_snapshot": 0.40,
            "market_outcome_observed": "NO",
            "inter_model_disagreement_std": 0.9,
        },
    ]
    report = compute_report(snaps)
    assert report["n_resolved"] == 2
    assert report["n_pending"] == 0
    assert report["brier_candidate"] is not None
    assert report["brier_market"] is not None
    assert report["brier_advantage_market"] is not None
    assert report["eligible_for_policy"] is False
    assert report["live_policy_eligible"] is False


# ── Test 10: readiness levels ─────────────────────────────────────────────────

def test_readiness_accruing_when_n_lt_20():
    """Test 10a: readiness=H3_HOLDOUT_ACCRUING when n_resolved < 20."""
    snaps = [
        {
            "h3_hypothesis_id": H3_HYPOTHESIS_ID,
            "candidate_prob_yes": 0.6,
            "mkt_prob_yes_at_snapshot": 0.5,
            "market_outcome_observed": "YES",
            "inter_model_disagreement_std": 1.0,
        }
    ] * 5  # n=5 < 20
    report = compute_report(snaps)
    assert report["readiness"] == "H3_HOLDOUT_ACCRUING"


def test_readiness_beats_market_when_n_ge_20_and_advantage_gt_0():
    """Test 10b: readiness=H3_BEATS_MARKET_OPUS_REVIEW when n>=20 and brier_advantage > 0."""
    # candidate much better than market
    snaps = [
        {
            "h3_hypothesis_id": H3_HYPOTHESIS_ID,
            "candidate_prob_yes": 0.95,
            "mkt_prob_yes_at_snapshot": 0.50,
            "market_outcome_observed": "YES",
            "inter_model_disagreement_std": 1.0,
        }
    ] * 20
    report = compute_report(snaps)
    assert report["readiness"] == "H3_BEATS_MARKET_OPUS_REVIEW"
    assert report["brier_advantage_market"] > 0


def test_readiness_falsified_when_n_ge_20_and_advantage_le_0():
    """Test 10c: readiness=H3_FALSIFIED_NO_INCREMENTAL_WEATHER_ALPHA when n>=20 and advantage<=0."""
    # market better than candidate
    snaps = [
        {
            "h3_hypothesis_id": H3_HYPOTHESIS_ID,
            "candidate_prob_yes": 0.50,
            "mkt_prob_yes_at_snapshot": 0.95,
            "market_outcome_observed": "YES",
            "inter_model_disagreement_std": 1.0,
        }
    ] * 20
    report = compute_report(snaps)
    assert report["readiness"] == "H3_FALSIFIED_NO_INCREMENTAL_WEATHER_ALPHA"
    assert report["brier_advantage_market"] <= 0


# ── Test 11: invariants ────────────────────────────────────────────────────────

def test_snapshot_invariants():
    """Test 11: eligible_for_policy=false, live_policy_eligible=false,
    no Weather Truth canonical, no P&L canonical, no bot.py integration."""
    snap = build_snapshot(
        city="Tokyo",
        target_date="2026-06-01",
        condition="at_or_above",
        threshold=30.0,
        unit="C",
        h3_prereg_cutoff_utc="2026-06-01T00:00:00Z",
        model_fetch_fn=_stub_model_fetcher_ok,
        market_fetch_fn=_stub_market_ok,
        model_ids=EFFECTIVE_MODEL_IDS,
    )
    assert snap["eligible_for_policy"] is False
    assert snap["live_policy_eligible"] is False
    assert snap["market_truth_canonical"] is False
    assert snap["weather_truth_canonical"] is False
    assert snap["pnl_canonical_confirmed"] is False
    assert snap["market_outcome_observed"] is None
    assert snap["partition"] == "h3_forward_holdout"
    assert snap["h3_hypothesis_id"] == H3_HYPOTHESIS_ID
    assert snap["h3_candidate_model_id"] == H3_CANDIDATE_MODEL_ID


def test_report_invariants():
    """Test 11b: report invariants are always false."""
    report = compute_report([])
    assert report["eligible_for_policy"] is False
    assert report["live_policy_eligible"] is False


# ── Test 12: no integration with bot.py, scheduler, BSE, or H2 ───────────────

def test_no_bot_py_import():
    """Test 12: _multimodel_engine does not import bot.py, H2 engine, or trading modules."""
    import re
    import tools._multimodel_engine as engine_module

    source_file = Path(engine_module.__file__)
    source_text = source_file.read_text(encoding="utf-8")

    # Check for actual import statements (not docstring mentions)
    forbidden_imports = [
        r"^import bot\b",
        r"^from bot\b",
        r"^import _self_evaluation_engine",
        r"^from _self_evaluation_engine",
    ]
    for pattern in forbidden_imports:
        matches = re.findall(pattern, source_text, re.MULTILINE)
        assert not matches, f"Forbidden import found: {pattern!r} -> {matches}"

    # These strings should never appear anywhere (not even in comments for these)
    absolutely_forbidden = [
        "H2_PREREG", "H2_CANDIDATE", "bot_signal_evaluations",
    ]
    for token in absolutely_forbidden:
        assert token not in source_text, f"Forbidden reference found: {token!r}"


def test_fail_closed_no_market():
    """Test 12b: build_snapshot fails closed if market_fetch_fn returns None."""
    with pytest.raises(ValueError, match="H3_FORWARD_MARKET_SNAPSHOT_BLOCKED"):
        build_snapshot(
            city="Shanghai",
            target_date="2026-06-01",
            condition="at_or_above",
            threshold=28.0,
            unit="C",
            h3_prereg_cutoff_utc=None,
            model_fetch_fn=_stub_model_fetcher_ok,
            market_fetch_fn=_stub_market_none,
            model_ids=EFFECTIVE_MODEL_IDS,
        )


# ── Test: exact and range are out of scope V1 ─────────────────────────────────

def test_exact_and_range_out_of_scope():
    """Test: compute_candidate_prob returns None for exact/range (V1 scope)."""
    prob_exact = compute_candidate_prob(27.0, 1.0, 27.0, "exact")
    prob_range = compute_candidate_prob(27.0, 1.0, 27.0, "range")
    assert prob_exact is None
    assert prob_range is None


# ── Test: sigma floor at MIN_SIGMA ────────────────────────────────────────────

def test_sigma_floor_applied():
    """Test: sigma_candidate = max(inter_model_std, 0.8) even if std is tiny."""
    # Build snapshot with models that have near-identical values (tiny std)
    def _stub_identical(target_date, lat, lon, tz, model_ids):
        return {m: 27.0 for m in model_ids}

    snap = build_snapshot(
        city="Shanghai",
        target_date="2026-06-01",
        condition="at_or_above",
        threshold=27.0,
        unit="C",
        h3_prereg_cutoff_utc=None,
        model_fetch_fn=_stub_identical,
        market_fetch_fn=_stub_market_ok,
        model_ids=EFFECTIVE_MODEL_IDS,
    )
    assert snap["inter_model_disagreement_std"] == 0.0
    assert snap["sigma_candidate"] >= 0.8
    # At threshold == mean with sigma >= 0.8, prob ~= 0.5
    assert abs(snap["candidate_prob_yes"] - 0.5) < 0.05


# ── Test: Buenos Aires and Ankara are in ACTIVE_CITY_COORDS ──────────────────

def test_all_active_cities_snapshottable():
    """Test: build_snapshot works for all 4 ACTIVE cities."""
    from tools._multimodel_engine import ACTIVE_CITY_COORDS
    for city in ACTIVE_CITY_COORDS:
        snap = build_snapshot(
            city=city,
            target_date="2026-06-01",
            condition="at_or_below",
            threshold=35.0,
            unit="C",
            h3_prereg_cutoff_utc="2026-06-01T00:00:00Z",
            model_fetch_fn=_stub_model_fetcher_ok,
            market_fetch_fn=_stub_market_ok,
            model_ids=EFFECTIVE_MODEL_IDS,
        )
        assert snap["city"] == city
        assert snap["eligible_for_policy"] is False
