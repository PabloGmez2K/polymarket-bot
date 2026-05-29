"""Tests focales para BOT_SELF_EVALUATION_OUTCOME_LOOP_V1.

Invariantes V1:
  - eligible_for_policy=false en todos los cohorts siempre
  - live_policy_eligible=false global siempre
  - market_truth_canonical=false siempre
  - weather_truth_available=false siempre
  - pnl_canonical_confirmed=false siempre
  - Seoul excluido siempre (source_fidelity_suspect)
  - Partition inmutable por SELF_EVAL_H1_PREREG_CUTOFF_UTC
  - Deduplicación determinista por eval_key
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools._self_evaluation_engine import (
    SELF_EVAL_H1_PREREG_CUTOFF_UTC,
    SUPPORTED_CONDITIONS,
    build_self_evaluation_report,
    _deduplicate_by_eval_key,
    _is_source_fidelity_suspect,
    _partition,
    _score_cohort,
    _brier,
    _build_bsr_lookup,
    build_gamma_slug_from_eval_key,
    _build_gamma_question_text,
    _normalize_gamma_q,
)

# Fixed reference time for deterministic tests — must be AFTER cutoff
_NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
# Timestamps clearly before cutoff (evidence_frozen)
_TS_FROZEN = "2026-04-15T20:00:00+00:00"
# Timestamp after cutoff (forward_holdout)
_TS_HOLDOUT = "2026-05-30T08:00:00+00:00"

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "self_evaluation_directional_evidence_frozen_v1.json"


def _mk_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


def _write_bse(data_dir: Path, rows: list[dict]) -> None:
    path = data_dir / "bot_signal_evaluations.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _write_bsr(data_dir: Path, rows: list[dict]) -> None:
    path = data_dir / "blocked_signals_resolutions.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _make_bse_row(
    eval_key: str,
    condition: str = "at_or_above",
    our_prob: float = 70.0,
    mkt_prob: float = 60.0,
    city: str = "Paris",
    ts: str = _TS_FROZEN,
    side: str | None = None,
) -> dict:
    return {
        "eval_key": eval_key,
        "condition": condition,
        "city": city,
        "our_prob": our_prob,
        "mkt_prob": mkt_prob,
        "ts_utc": ts,
        "side": side,
        "evaluation_source": "live_eval",
    }


# ── 1. Slug determinista at_or_above ─────────────────────────────────────────

def test_slug_at_or_above() -> None:
    slug = build_gamma_slug_from_eval_key("Tokyo|2026-04-15|at_or_above|20|C")
    assert slug is not None
    assert "at_or_above" not in slug  # slug uses natural language
    assert "higher" in slug
    assert "tokyo" in slug
    assert "20" in slug
    assert "celsius" in slug


# ── 2. Slug determinista at_or_below ─────────────────────────────────────────

def test_slug_at_or_below() -> None:
    slug = build_gamma_slug_from_eval_key("Oslo|2026-04-15|at_or_below|10|C")
    assert slug is not None
    assert "lower" in slug
    assert "oslo" in slug
    assert "10" in slug
    assert "celsius" in slug


def test_slug_invalid_parts_returns_none() -> None:
    assert build_gamma_slug_from_eval_key("bad_key") is None
    assert build_gamma_slug_from_eval_key("") is None


# ── 3. Outcome desde outcomePrices pattern (via BSR outcome field) ───────────

def test_bsr_lookup_yes_outcome(tmp_path: Path) -> None:
    bsr_rows = [{"match_key": "Tokyo|2026-04-15|at_or_above|20|C", "outcome": "yes"}]
    lookup = _build_bsr_lookup(bsr_rows)
    assert lookup("Tokyo|2026-04-15|at_or_above|20|C") == "YES"


def test_bsr_lookup_no_outcome(tmp_path: Path) -> None:
    bsr_rows = [{"match_key": "Paris|2026-04-16|at_or_above|22|C", "outcome": "no"}]
    lookup = _build_bsr_lookup(bsr_rows)
    assert lookup("Paris|2026-04-16|at_or_above|22|C") == "NO"


def test_bsr_lookup_missing_key_returns_none() -> None:
    lookup = _build_bsr_lookup([])
    assert lookup("nonexistent|key") is None


# ── 4. Exclusión Seoul ────────────────────────────────────────────────────────

def test_seoul_excluded_from_scoring(tmp_path: Path) -> None:
    data_dir = _mk_data_dir(tmp_path)
    rows = [
        _make_bse_row("Seoul|2026-04-15|at_or_above|18|C", city="Seoul"),
        _make_bse_row("Paris|2026-04-16|at_or_above|22|C", city="Paris"),
    ]
    _write_bse(data_dir, rows)

    outcomes_called = []

    def mock_lookup(key: str) -> str | None:
        outcomes_called.append(key)
        return "YES"

    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=mock_lookup, now=_NOW)
    assert report["source_fidelity_excluded_count"] == 1
    # Seoul must not appear in outcomes_called
    assert not any("Seoul" in k for k in outcomes_called)
    # Paris row should have been processed (in evidence_frozen, outcome resolved)
    assert report["deduped_eval_keys"] == 1


def test_is_source_fidelity_suspect_seoul() -> None:
    assert _is_source_fidelity_suspect({"city": "Seoul"}) is True
    assert _is_source_fidelity_suspect({"city": "seoul"}) is True
    assert _is_source_fidelity_suspect({"city": "SEOUL"}) is True
    assert _is_source_fidelity_suspect({"city": "Paris"}) is False
    assert _is_source_fidelity_suspect({}) is False


# ── 5. Partition inmutable por cutoff ─────────────────────────────────────────

def test_partition_immutable_by_cutoff() -> None:
    cutoff = SELF_EVAL_H1_PREREG_CUTOFF_UTC
    # Verify cutoff is 2026-05-29T00:00:00Z
    assert cutoff == datetime(2026, 5, 29, 0, 0, 0, tzinfo=timezone.utc)

    rows_before = [{"ts_utc": "2026-04-15T20:00:00+00:00", "eval_key": "k1"}]
    rows_after = [{"ts_utc": "2026-05-30T08:00:00+00:00", "eval_key": "k2"}]
    rows_on_cutoff = [{"ts_utc": "2026-05-29T00:00:00+00:00", "eval_key": "k3"}]  # >= cutoff → holdout

    ef, fh = _partition(rows_before + rows_after + rows_on_cutoff, cutoff)
    assert len(ef) == 1
    assert ef[0]["eval_key"] == "k1"
    assert len(fh) == 2
    fh_keys = {r["eval_key"] for r in fh}
    assert fh_keys == {"k2", "k3"}


def test_partition_no_ts_goes_to_evidence_frozen() -> None:
    rows = [{"eval_key": "k_no_ts"}]  # no ts_utc field
    ef, fh = _partition(rows, SELF_EVAL_H1_PREREG_CUTOFF_UTC)
    assert len(ef) == 1
    assert len(fh) == 0


# ── 6. Deduplicación determinista ─────────────────────────────────────────────

def test_deduplication_keeps_latest_ts() -> None:
    rows = [
        {"eval_key": "k1", "ts_utc": "2026-04-10T00:00:00+00:00", "our_prob": 60.0},
        {"eval_key": "k1", "ts_utc": "2026-04-15T00:00:00+00:00", "our_prob": 70.0},
        {"eval_key": "k1", "ts_utc": "2026-04-12T00:00:00+00:00", "our_prob": 65.0},
    ]
    deduped = _deduplicate_by_eval_key(rows)
    assert len(deduped) == 1
    assert deduped[0]["our_prob"] == 70.0  # latest ts wins


def test_deduplication_deterministic_empty_key_skipped() -> None:
    rows = [
        {"eval_key": "", "ts_utc": _TS_FROZEN},
        {"ts_utc": _TS_FROZEN},  # no eval_key
        {"eval_key": "k1", "ts_utc": _TS_FROZEN},
    ]
    deduped = _deduplicate_by_eval_key(rows)
    assert len(deduped) == 1
    assert deduped[0]["eval_key"] == "k1"


def test_deduplication_different_keys_all_kept() -> None:
    rows = [
        {"eval_key": "k1", "ts_utc": _TS_FROZEN},
        {"eval_key": "k2", "ts_utc": _TS_FROZEN},
        {"eval_key": "k3", "ts_utc": _TS_FROZEN},
    ]
    deduped = _deduplicate_by_eval_key(rows)
    assert len(deduped) == 3


# ── 7. Invariante eligible_for_policy=false ───────────────────────────────────

def test_eligible_for_policy_always_false(tmp_path: Path) -> None:
    data_dir = _mk_data_dir(tmp_path)
    rows = [_make_bse_row("k1|2026-04-15|at_or_above|20|C")]
    _write_bse(data_dir, rows)
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=lambda k: "YES", now=_NOW)
    for cohort in report["cohorts"]:
        assert cohort["eligible_for_policy"] is False


# ── 8. Invariante live_policy_eligible=false ──────────────────────────────────

def test_live_policy_eligible_always_false(tmp_path: Path) -> None:
    data_dir = _mk_data_dir(tmp_path)
    rows = [_make_bse_row("k1|2026-04-15|at_or_above|20|C")]
    _write_bse(data_dir, rows)
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=lambda k: "YES", now=_NOW)
    assert report["live_policy_eligible"] is False
    assert report["eligible_for_policy"] is False
    for cohort in report["cohorts"]:
        assert cohort["live_policy_eligible"] is False


# ── 9. No settlement canónico, no Weather Truth, no P&L canónico ──────────────

def test_no_canonical_claims(tmp_path: Path) -> None:
    data_dir = _mk_data_dir(tmp_path)
    _write_bse(data_dir, [_make_bse_row("k1|2026-04-15|at_or_above|20|C")])
    report = build_self_evaluation_report(data_dir, now=_NOW)
    assert report["market_truth_canonical"] is False
    assert report["weather_truth_available"] is False
    assert report["pnl_canonical_confirmed"] is False
    # No settlement-related field should be True
    report_str = json.dumps(report)
    assert '"settlement_confirmed"' not in report_str
    assert '"weather_truth_canonical": true' not in report_str


# ── 10. Fixture reproduces evidence_frozen baselines ─────────────────────────

def _load_fixture() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _build_mock_lookup_from_fixture(fixture_rows: list[dict]):
    index = {
        r["eval_key"]: r["market_outcome_observed"]
        for r in fixture_rows
        if r.get("eval_key") and r.get("market_outcome_observed") in ("YES", "NO")
    }
    return lambda key: index.get(key)


def test_fixture_file_exists() -> None:
    assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"


def test_fixture_has_correct_counts() -> None:
    rows = _load_fixture()
    non_seoul = [r for r in rows if str(r.get("city", "")).casefold() != "seoul"]
    above = [r for r in non_seoul if r.get("condition") == "at_or_above"]
    below = [r for r in non_seoul if r.get("condition") == "at_or_below"]
    assert len(above) == 21, f"Expected 21 at_or_above, got {len(above)}"
    assert len(below) == 4, f"Expected 4 at_or_below, got {len(below)}"
    assert sum(1 for r in above if r.get("market_outcome_observed") == "YES") == 7
    assert sum(1 for r in above if r.get("market_outcome_observed") == "NO") == 14
    assert sum(1 for r in below if r.get("market_outcome_observed") == "YES") == 3
    assert sum(1 for r in below if r.get("market_outcome_observed") == "NO") == 1


def test_fixture_at_or_above_evidence_brier(tmp_path: Path) -> None:
    """Engine computes real Brier from real BSE+Gamma data (2026-05-29 snapshot)."""
    fixture_rows = _load_fixture()
    non_seoul = [r for r in fixture_rows if str(r.get("city", "")).casefold() != "seoul"]

    data_dir = _mk_data_dir(tmp_path)
    _write_bse(data_dir, non_seoul)

    mock_lookup = _build_mock_lookup_from_fixture(fixture_rows)
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=mock_lookup, now=_NOW)

    above_ef = next(
        c for c in report["cohorts"]
        if c["condition"] == "at_or_above" and c["partition"] == "evidence_frozen"
    )
    assert above_ef["n_resolved"] == 21, f"Expected n=21, got {above_ef['n_resolved']}"
    # Real Brier from 2026-05-29 snapshot. H1 confirmed: brier_advantage < 0.
    assert above_ef["brier_our"] == pytest.approx(0.4242, abs=0.001)
    assert above_ef["brier_mkt"] == pytest.approx(0.3303, abs=0.001)
    assert above_ef["brier_advantage"] == pytest.approx(-0.0939, abs=0.001)
    assert above_ef["readiness"] == "CURRENT_PREDICTOR_NOT_CANDIDATE"
    assert above_ef["eligible_for_policy"] is False


def test_fixture_at_or_below_evidence_brier(tmp_path: Path) -> None:
    """Engine computes real Brier for at_or_below cohort (n=4, real data)."""
    fixture_rows = _load_fixture()
    non_seoul = [r for r in fixture_rows if str(r.get("city", "")).casefold() != "seoul"]

    data_dir = _mk_data_dir(tmp_path)
    _write_bse(data_dir, non_seoul)

    mock_lookup = _build_mock_lookup_from_fixture(fixture_rows)
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=mock_lookup, now=_NOW)

    below_ef = next(
        c for c in report["cohorts"]
        if c["condition"] == "at_or_below" and c["partition"] == "evidence_frozen"
    )
    assert below_ef["n_resolved"] == 4, f"Expected n=4, got {below_ef['n_resolved']}"
    assert below_ef["brier_our"] == pytest.approx(0.1768, abs=0.001)
    assert below_ef["brier_mkt"] == pytest.approx(0.2473, abs=0.001)
    assert below_ef["brier_advantage"] == pytest.approx(0.0705, abs=0.001)
    assert below_ef["readiness"] == "HYPOTHESIS_ONLY_INSUFFICIENT_SAMPLE"
    assert below_ef["eligible_for_policy"] is False


def test_fixture_seoul_rows_excluded_from_scoring(tmp_path: Path) -> None:
    """3 Seoul rows in fixture must be excluded; only 24 non-Seoul rows scored."""
    fixture_rows = _load_fixture()
    data_dir = _mk_data_dir(tmp_path)
    _write_bse(data_dir, fixture_rows)  # includes Seoul rows

    mock_lookup = _build_mock_lookup_from_fixture(fixture_rows)
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=mock_lookup, now=_NOW)

    assert report["source_fidelity_excluded_count"] == 3
    assert report["deduped_eval_keys"] == 25

    # at_or_above must still have n=21 (not 24 if Seoul were included)
    above_ef = next(
        c for c in report["cohorts"]
        if c["condition"] == "at_or_above" and c["partition"] == "evidence_frozen"
    )
    assert above_ef["n_resolved"] == 21


# ── 11. Holdout state ─────────────────────────────────────────────────────────

def test_holdout_accruing_when_n_below_20(tmp_path: Path) -> None:
    data_dir = _mk_data_dir(tmp_path)
    # 5 holdout rows
    rows = [
        _make_bse_row(f"k{i}|2026-05-30|at_or_above|20|C", ts=_TS_HOLDOUT)
        for i in range(5)
    ]
    _write_bse(data_dir, rows)
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=lambda k: "YES", now=_NOW)
    assert report["experiment_readiness"] == "HOLDOUT_ACCRUING"


def test_holdout_ready_when_n_above_20(tmp_path: Path) -> None:
    data_dir = _mk_data_dir(tmp_path)
    # 25 holdout rows
    rows = [
        _make_bse_row(f"kh{i}|2026-05-30|at_or_above|20|C", ts=_TS_HOLDOUT, city=f"City{i}")
        for i in range(25)
    ]
    _write_bse(data_dir, rows)
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=lambda k: "YES", now=_NOW)
    above_fh = next(
        c for c in report["cohorts"]
        if c["condition"] == "at_or_above" and c["partition"] == "forward_holdout"
    )
    assert above_fh["readiness"] == "HOLDOUT_READY_FOR_OPUS_EXPERIMENT_REVIEW"
    assert report["experiment_readiness"] == "HOLDOUT_READY_FOR_OPUS_EXPERIMENT_REVIEW"


# ── Additional: empty BSE, global fields, BSR fallback ───────────────────────

def test_empty_bse_returns_valid_structure(tmp_path: Path) -> None:
    data_dir = _mk_data_dir(tmp_path)
    report = build_self_evaluation_report(data_dir, now=_NOW)
    assert report["matches_found"] is True
    assert report["bse_present"] is False
    assert report["bse_rows_total"] == 0
    assert report["live_policy_eligible"] is False
    assert report["market_truth_canonical"] is False
    assert "cohorts" in report
    assert report["experiment_readiness"] == "HOLDOUT_ACCRUING"


def test_bsr_fallback_resolves_outcomes(tmp_path: Path) -> None:
    data_dir = _mk_data_dir(tmp_path)
    _write_bse(data_dir, [
        _make_bse_row("Tokyo|2026-04-15|at_or_above|20|C", city="Tokyo"),
    ])
    _write_bsr(data_dir, [
        {"match_key": "Tokyo|2026-04-15|at_or_above|20|C", "outcome": "yes"},
    ])
    # No explicit gamma_lookup_fn → engine uses BSR fallback
    report = build_self_evaluation_report(data_dir, now=_NOW)
    above_ef = next(
        c for c in report["cohorts"]
        if c["condition"] == "at_or_above" and c["partition"] == "evidence_frozen"
    )
    assert above_ef["n_resolved"] == 1


def test_unsupported_condition_excluded() -> None:
    """exact condition rows must not appear in directional evaluation."""
    rows = [
        {"eval_key": "k1", "condition": "exact", "our_prob": 70.0, "mkt_prob": 60.0},
    ]
    # All rows are 'exact' — no supported conditions
    from tools._self_evaluation_engine import SUPPORTED_CONDITIONS
    directional = [r for r in rows if r.get("condition") in SUPPORTED_CONDITIONS]
    assert len(directional) == 0


def test_brier_computation_is_real_not_constant() -> None:
    """Verify _brier computes mean squared error, not a constant."""
    # Perfect predictions: all probs=1, all outcomes=1 → Brier=0
    assert _brier([1.0, 1.0], [1, 1]) == pytest.approx(0.0)
    # Worst predictions: all probs=0, all outcomes=1 → Brier=1
    assert _brier([0.0, 0.0], [1, 1]) == pytest.approx(1.0)
    # Mixed: (0.8-1)^2=0.04 and (0.8-0)^2=0.64 → avg=0.34
    assert _brier([0.8, 0.8], [1, 0]) == pytest.approx(0.34)


# ── 12. Gamma question text builder ──────────────────────────────────────────

def test_gamma_question_text_at_or_above() -> None:
    q = _build_gamma_question_text("Denver|2026-05-20|at_or_above|56|F")
    assert q is not None
    assert "denver" in q
    assert "56" in q
    assert "°f" in q or "f" in q
    assert "or higher" in q
    assert "may 20" in q


def test_gamma_question_text_at_or_below() -> None:
    q = _build_gamma_question_text("Beijing|2026-05-23|at_or_below|26|C")
    assert q is not None
    assert "beijing" in q
    assert "26" in q
    assert "or below" in q
    assert "may 23" in q


def test_gamma_question_text_invalid_returns_none() -> None:
    assert _build_gamma_question_text("bad") is None
    assert _build_gamma_question_text("") is None
    assert _build_gamma_question_text("a|b|c") is None


def test_gamma_question_text_normalize_strips_question_mark() -> None:
    q = _normalize_gamma_q("Will the highest temperature in Denver be 56°F or higher on May 20?")
    assert not q.endswith("?")
    assert q == q.lower()


# ── 13. OUTCOMES_NOT_RESOLVED when n_resolved=0 ───────────────────────────────

def test_cohort_readiness_outcomes_not_resolved_when_no_outcomes(tmp_path: Path) -> None:
    """evidence_frozen cohort with no resolved outcomes should show OUTCOMES_NOT_RESOLVED."""
    data_dir = _mk_data_dir(tmp_path)
    rows = [_make_bse_row("k1|2026-04-15|at_or_above|20|C")]
    _write_bse(data_dir, rows)
    # Lookup returns None for everything → n_resolved=0
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=lambda k: None, now=_NOW)
    above_ef = next(
        c for c in report["cohorts"]
        if c["condition"] == "at_or_above" and c["partition"] == "evidence_frozen"
    )
    assert above_ef["n_resolved"] == 0
    assert above_ef["readiness"] == "OUTCOMES_NOT_RESOLVED"


# ── 14. Holdout readiness uses n_resolved only (not n_pending) ────────────────

def test_holdout_readiness_does_not_count_pending(tmp_path: Path) -> None:
    """experiment_readiness must NOT count pending predictions as resolved."""
    data_dir = _mk_data_dir(tmp_path)
    # 25 holdout rows but lookup returns None → n_resolved=0, n_pending=25
    rows = [
        _make_bse_row(f"kh{i}|2026-05-30|at_or_above|20|C", ts=_TS_HOLDOUT, city=f"City{i}")
        for i in range(25)
    ]
    _write_bse(data_dir, rows)
    report = build_self_evaluation_report(data_dir, gamma_lookup_fn=lambda k: None, now=_NOW)
    # n_pending=25 but n_resolved=0 → HOLDOUT_ACCRUING (not READY)
    assert report["experiment_readiness"] == "HOLDOUT_ACCRUING"
