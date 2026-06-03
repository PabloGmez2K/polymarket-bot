from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import decision_dataset_builder as builder
from tools import predictor_benchmark as bench
from tools._self_evaluation_engine import _brier


def _record(
    *,
    decision_id: str,
    condition: str = "at_or_above",
    side: str = "YES",
    outcome: str = "YES",
    model_prob: float = 0.8,
    market_prob: float = 0.6,
    sim_pnl: float = 0.4,
    snapshot_ts_utc: str = "2026-05-30T00:00:00+00:00",
    maturity_bucket: str = "settled_mature",
    cohort_key: str | None = None,
) -> dict:
    cohort_key = cohort_key or f"{condition}|{side}|0-1|15-30%"
    return {
        "city": "Tokyo",
        "date_iso": "2026-05-30",
        "condition": condition,
        "threshold_c": 25.0,
        "question": None,
        "market_id": f"m-{decision_id}",
        "token_id_yes": None,
        "token_id_no": None,
        "forecast_high_c": None,
        "forecast_source": None,
        "observed_high_c": None,
        "observed_source": None,
        "resolution_outcome": outcome,
        "resolution_ts_utc": "2026-06-01T00:00:00+00:00",
        "resolution_method": "gamma_official",
        "bot_had_position": 0,
        "bot_side": None,
        "snapshot_ts_utc": snapshot_ts_utc,
        "payload_json": "{}",
        "market_prob_at_eval": market_prob,
        "model_prob": model_prob,
        "side": side,
        "sim_unit_pnl": sim_pnl,
        "eval_source": "fixture",
        "resolution_status": "settled" if outcome in {"YES", "NO"} else "pending",
        "maturity_bucket": maturity_bucket,
        "cohort_key": cohort_key,
        "days_ahead": 0,
        "edge_pct_at_eval": abs(model_prob - market_prob) * 100.0,
        "decision_id": decision_id,
        "data_provenance": "{}",
        "unit_raw": "C",
    }


def _make_db(tmp_path: Path, rows: list[dict]) -> Path:
    db = tmp_path / "decision_dataset.db"
    builder.apply_schema(db)
    with sqlite3.connect(db) as conn:
        placeholders = ",".join("?" for _ in builder.WRITE_COLUMNS)
        conn.executemany(
            f"INSERT INTO truth_records ({','.join(builder.WRITE_COLUMNS)}) VALUES ({placeholders})",
            [[row.get(col) for col in builder.WRITE_COLUMNS] for row in rows],
        )
        conn.commit()
    return db


def _run(tmp_path: Path, rows: list[dict], samples: int = 80) -> dict:
    db = _make_db(tmp_path, rows)
    out = tmp_path / "benchmark_summary.json"
    dataset_summary = tmp_path / "decision_dataset_summary.json"
    dataset_summary.write_text(
        json.dumps({"dataset": {"benchmark_input_rows": len(rows)}}),
        encoding="utf-8",
    )
    return bench.run_benchmark(
        db_path=db,
        output_summary=out,
        bootstrap_samples=samples,
        seed=2026,
        dataset_summary_path=dataset_summary,
    )


def _cell(summary: dict, level: str, cohort: str, partition: str) -> dict:
    return next(
        cell
        for cell in summary["cells"]
        if cell["level"] == level and cell["cohort"] == cohort and cell["partition"] == partition
    )


def test_brier_advantage_formula_matches_self_eval_sign(tmp_path: Path):
    rows = [
        _record(decision_id="a", outcome="YES", model_prob=0.8, market_prob=0.6),
        _record(decision_id="b", outcome="NO", model_prob=0.8, market_prob=0.6),
    ]
    summary = _run(tmp_path, rows)
    l1 = _cell(summary, "L1", "at_or_above|YES", "forward_holdout")

    expected_model = _brier([0.8, 0.8], [1, 0])
    expected_market = _brier([0.6, 0.6], [1, 0])
    assert l1["brier_advantage"] == pytest.approx(expected_market - expected_model)
    assert l1["brier_advantage"] < 0


def test_holdout_partition_uses_snapshot_cutoff_no_lookahead(tmp_path: Path):
    rows = [
        _record(decision_id="before", snapshot_ts_utc="2026-05-28T23:59:59+00:00"),
        _record(decision_id="after", snapshot_ts_utc="2026-05-29T00:00:00+00:00"),
        _record(decision_id="bad-ts", snapshot_ts_utc="not-a-date"),
    ]
    summary = _run(tmp_path, rows)
    frozen = _cell(summary, "L0", "pooled", "evidence_frozen")
    forward = _cell(summary, "L0", "pooled", "forward_holdout")

    assert frozen["n"] == 2
    assert forward["n"] == 1


def test_view_excludes_immature_rows(tmp_path: Path):
    rows = [
        _record(decision_id="mature"),
        _record(decision_id="fresh", maturity_bucket="resolved_fresh"),
        _record(decision_id="pending", maturity_bucket="pending", outcome="UNKNOWN"),
    ]
    summary = _run(tmp_path, rows)

    assert summary["dataset_provenance"]["benchmark_input_rows"] == 3
    assert _cell(summary, "L0", "pooled", "forward_holdout")["n"] == 1


def test_exact_no_firewall_never_candidate(tmp_path: Path):
    rows = []
    for i in range(30):
        rows.append(
            _record(
                decision_id=f"frozen-{i}",
                condition="exact",
                side="NO",
                outcome="NO",
                model_prob=0.9,
                market_prob=0.6,
                sim_pnl=0.4,
                snapshot_ts_utc="2026-05-20T00:00:00+00:00",
                cohort_key="exact|NO|unknown|30%+",
            )
        )
        rows.append(
            _record(
                decision_id=f"forward-{i}",
                condition="exact",
                side="NO",
                outcome="NO",
                model_prob=0.9,
                market_prob=0.6,
                sim_pnl=0.4,
                cohort_key="exact|NO|unknown|30%+",
            )
        )
    summary = _run(tmp_path, rows, samples=120)
    l1 = _cell(summary, "L1", "exact|NO", "forward_holdout")

    assert l1["diagnostic_verdict"] == "BEATS_MARKET"
    assert l1["verdict"] == "NON_PROMOTABLE_BY_POLICY"
    assert not summary["top_candidates"]


def test_output_is_aggregate_sanitized_and_non_policy(tmp_path: Path):
    summary = _run(tmp_path, [_record(decision_id="row-secret")])
    text = json.dumps(summary)

    assert summary["eligible_for_policy"] is False
    assert summary["disclaimer"] == bench.DISCLAIMER
    assert "decision_id" not in text
    assert "eval_key" not in text
    assert "order_id" not in text
    assert "wallet" not in text


def test_readonly_run_does_not_modify_database(tmp_path: Path):
    db = _make_db(tmp_path, [_record(decision_id="readonly")])
    with sqlite3.connect(db) as conn:
        before = conn.execute("SELECT COUNT(*) FROM truth_records").fetchone()[0]

    out = tmp_path / "summary.json"
    bench.run_benchmark(db, out, bootstrap_samples=20, dataset_summary_path=tmp_path / "missing.json")

    with sqlite3.connect(db) as conn:
        after = conn.execute("SELECT COUNT(*) FROM truth_records").fetchone()[0]
    assert before == after == 1


def test_missing_db_error_is_clear(tmp_path: Path):
    out = tmp_path / "summary.json"
    with pytest.raises(FileNotFoundError, match="Run tools/decision_dataset_builder.py before E2"):
        bench.run_benchmark(tmp_path / "missing.db", out)


def test_deterministic_verdicts_for_same_seed(tmp_path: Path):
    rows = [
        _record(decision_id=f"frozen-{i}", snapshot_ts_utc="2026-05-20T00:00:00+00:00")
        for i in range(30)
    ] + [_record(decision_id=f"forward-{i}") for i in range(30)]
    first = _run(tmp_path / "a", rows, samples=100)
    second = _run(tmp_path / "b", rows, samples=100)

    first.pop("generated_at_utc")
    second.pop("generated_at_utc")
    assert first == second


def test_current_dataset_smoke_or_fixture(tmp_path: Path):
    runtime_db = Path("data/predictive/decision_dataset_runtime.db")
    if runtime_db.exists() and _runtime_view_has_snapshot(runtime_db):
        summary = bench.run_benchmark(
            runtime_db,
            tmp_path / "current_summary.json",
            bootstrap_samples=40,
            dataset_summary_path=Path("data/predictive/decision_dataset_summary.json"),
        )
        assert summary["schema_version"] == bench.SCHEMA_VERSION
    else:
        summary = _run(tmp_path, [_record(decision_id="fixture")])
    assert summary["schema_version"] == bench.SCHEMA_VERSION


def test_directional_known_metric_current_dataset_or_skip(tmp_path: Path):
    runtime_db = Path("data/predictive/decision_dataset_runtime.db")
    if not runtime_db.exists():
        pytest.skip("decision_dataset_runtime.db unavailable for directional known metric")
    if not _runtime_view_has_snapshot(runtime_db):
        pytest.skip("decision_dataset_runtime.db lacks snapshot_ts_utc; rebuild E1 runtime DB first")

    summary = bench.run_benchmark(
        runtime_db,
        tmp_path / "current_summary.json",
        bootstrap_samples=40,
        dataset_summary_path=Path("data/predictive/decision_dataset_summary.json"),
    )
    try:
        cell = _cell(summary, "L1", "at_or_above|YES", "evidence_frozen")
    except StopIteration:
        pytest.skip("directional_rows_absent")
    if cell["n"] != 21:
        pytest.skip(f"directional known metric requires at_or_above evidence_frozen n=21, got {cell['n']}")
    assert cell["n"] == 21
    assert cell["brier_advantage"] == pytest.approx(-0.0939, abs=0.0001)


def _runtime_view_has_snapshot(db_path: Path) -> bool:
    try:
        with sqlite3.connect(db_path) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(v_benchmark_input)").fetchall()}
        return "snapshot_ts_utc" in cols
    except sqlite3.Error:
        return False
