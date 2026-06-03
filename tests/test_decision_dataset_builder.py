from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import decision_dataset_builder as builder


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _exact_row(
    eval_key: str = "Tokyo|2026-05-20|exact|25|C",
    market_id: str = "111",
    outcome: str = "NO",
    bucket: str = "settled_mature",
    p_model_no: float = 0.85,
    p_market_no: float = 0.79,
    sim_pnl: float = 0.21,
) -> dict:
    return {
        "calibration_audit_only": True,
        "source_artifact": "exact_no_qt_match_evaluations_log_only.jsonl",
        "eval_key": eval_key,
        "market_id": market_id,
        "condition_id": "0xabc",
        "city": eval_key.split("|")[0],
        "date_iso": eval_key.split("|")[1],
        "condition": "exact",
        "threshold": int(eval_key.split("|")[3]),
        "unit": "C",
        "best_side_log_only": "NO",
        "entry_edge_log_only": 7.0,
        "max_edge_log_only": 7.0,
        "market_outcome": outcome,
        "no_would_win": outcome == "NO",
        "resolution_source": "gamma_official",
        "resolved_at": "2026-05-21T12:00:00Z",
        "settlement_mature_t7": bucket == "settled_mature",
        "days_since_date": 12,
        "duplicate_count": 1,
        "p_model_no": p_model_no,
        "p_market_no_at_eval": p_market_no,
        "simulated_unit_pnl": sim_pnl if bucket == "settled_mature" else None,
        "calibration_gap_component": None,
        "bucket": bucket,
    }


def _bse_row(
    eval_key: str = "Tokyo|2026-05-20|at_or_above|25|C",
    ts_utc: str = "2026-05-20T03:00:00+00:00",
    our_prob: float | None = 64.0,
    mkt_prob: float | None = 55.0,
) -> dict:
    city, date_iso, condition, threshold, unit = eval_key.split("|")
    return {
        "schema_version": "bot_signal_evaluation_v1",
        "ts_utc": ts_utc,
        "cycle_id": "2026-05-20T03:00:00Z",
        "eval_key": eval_key,
        "city": city,
        "date_iso": date_iso,
        "condition": condition,
        "threshold": int(threshold),
        "threshold_high": None,
        "unit": unit,
        "would_buy": False,
        "bot_edge_pct_at_signal": 9.0,
        "evaluation_source": "shadow",
        "skip_or_block_reason": "shadow_city",
        "decision_gate": "blocked_by_city_mode",
        "our_prob": our_prob,
        "mkt_prob": mkt_prob,
        "forecast_max": 27.2,
        "sigma_used": 2.5,
        "days_ahead": 2,
    }


def _build(
    tmp_path: Path,
    exact_rows: list[dict],
    bsr_rows: list[dict] | None = None,
    bse_rows: list[dict] | None = None,
):
    exact = tmp_path / "exact_no_resolutions_log_only.jsonl"
    bsr = tmp_path / "blocked_signals_resolutions.jsonl"
    bse = tmp_path / "bot_signal_evaluations.jsonl"
    db = tmp_path / "decision_dataset.db"
    summary = tmp_path / "decision_dataset_summary.json"
    _write_jsonl(exact, exact_rows)
    _write_jsonl(bsr, bsr_rows or [])
    if bse_rows is not None:
        _write_jsonl(bse, bse_rows)
    result = builder.build_dataset(
        db_path=db,
        exact_no_resolutions=exact,
        blocked_signals_resolutions=bsr,
        bot_signal_evaluations=bse if bse_rows is not None else None,
        output_summary=summary,
        conflicts_path=tmp_path / "resolution_conflicts.jsonl",
    )
    return db, summary, result


def test_normalize_bot_signal_evaluation_maps_directional_yes_fields():
    row = _bse_row()
    record = builder.normalize_bot_signal_evaluation(
        row,
        {"source_file": "bot_signal_evaluations.jsonl", "sha256": "abc"},
        outcome=builder.Settlement(True, 1.0, 0.0, "2026-05-21T00:00:00Z", "YES"),
        today=builder.date(2026, 5, 30),
    )

    assert record["eval_source"] == "bot_signal_evaluations"
    assert record["side"] == "YES"
    assert record["snapshot_ts_utc"] == row["ts_utc"]
    assert record["model_prob"] == pytest.approx(0.64)
    assert record["market_prob_at_eval"] == pytest.approx(0.55)
    assert record["edge_pct_at_eval"] == pytest.approx(9.0)
    assert record["maturity_bucket"] == "settled_mature"
    assert record["sim_unit_pnl"] == pytest.approx(0.45)
    assert json.loads(record["payload_json"])["probability_convention"] == "our_prob_and_mkt_prob_are_yes_probabilities"


def test_build_dataset_loads_bse_directional_rows_and_exposes_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(
        builder,
        "_resolve_bse_outcomes",
        lambda rows: {
            row["eval_key"]: builder.Settlement(True, 1.0, 0.0, "2026-05-21T00:00:00Z", "YES")
            for row in rows
        },
    )
    db, _, result = _build(tmp_path, [], bse_rows=[_bse_row()])

    assert result["inputs"]["bot_signal_evaluations"]["status"] == "loaded"
    assert result["inputs"]["bot_signal_evaluations"]["accepted_rows"] == 1
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            """
            SELECT eval_source, side, snapshot_ts_utc, model_prob, market_prob_at_eval
            FROM v_benchmark_input
            WHERE eval_source='bot_signal_evaluations'
            """
        ).fetchone()
    assert row == ("bot_signal_evaluations", "YES", "2026-05-20T03:00:00+00:00", 0.64, 0.55)


def test_bse_loader_excludes_seoul_for_self_eval_parity(monkeypatch, tmp_path):
    monkeypatch.setattr(
        builder,
        "_resolve_bse_outcomes",
        lambda rows: {
            row["eval_key"]: builder.Settlement(True, 1.0, 0.0, "2026-05-21T00:00:00Z", "YES")
            for row in rows
        },
    )
    rows = [
        _bse_row("Seoul|2026-05-20|at_or_above|25|C"),
        _bse_row("Tokyo|2026-05-20|at_or_above|25|C"),
    ]
    db, _, result = _build(tmp_path, [], bse_rows=rows)

    assert result["inputs"]["bot_signal_evaluations"]["source_fidelity_excluded_seoul_rows"] == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM truth_records WHERE city='Seoul'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM truth_records WHERE city='Tokyo'").fetchone()[0] == 1


def test_reproduces_proto_r2_exact_no_from_local_oracle(tmp_path):
    oracle = Path("data/exact_no_resolutions_log_only.jsonl")
    if not oracle.exists():
        pytest.skip("local exact_no_resolutions_log_only.jsonl oracle is unavailable")

    db = tmp_path / "decision_dataset.db"
    summary = tmp_path / "decision_dataset_summary.json"
    result = builder.build_dataset(
        db_path=db,
        exact_no_resolutions=oracle,
        blocked_signals_resolutions=Path("data/runtime_import_derived/blocked_signals_resolutions.jsonl"),
        bot_signal_evaluations=None,
        output_summary=summary,
        conflicts_path=tmp_path / "resolution_conflicts.jsonl",
    )

    proto = result["proto_r2_exact_no"]
    assert proto["settled_mature_n"] == 17
    assert proto["WR_NO"] == pytest.approx(0.5882, abs=0.0001)
    assert proto["sim_pnl"] == pytest.approx(-1.6035, abs=0.0001)
    assert proto["calibration_gap"] == pytest.approx(0.2476, abs=0.0001)


def test_idempotent_upsert_does_not_duplicate_rows(tmp_path):
    rows = [_exact_row()]
    db, summary, first = _build(tmp_path, rows)
    second = builder.build_dataset(
        db_path=db,
        exact_no_resolutions=tmp_path / "exact_no_resolutions_log_only.jsonl",
        blocked_signals_resolutions=tmp_path / "blocked_signals_resolutions.jsonl",
        bot_signal_evaluations=None,
        output_summary=summary,
        conflicts_path=tmp_path / "resolution_conflicts.jsonl",
    )

    assert first["write_counts"]["inserted"] == 1
    assert second["write_counts"]["inserted"] == 0
    assert second["write_counts"]["updated"] == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM truth_records").fetchone()[0] == 1


def test_no_accidental_jsonl_ingestion_by_allowlist(tmp_path):
    exact_rows = [_exact_row()]
    _build(tmp_path, exact_rows)
    _write_jsonl(tmp_path / "stray_runtime_file.jsonl", [_exact_row(market_id="999")])

    db, _, result = _build(tmp_path, exact_rows)
    assert "stray_runtime_file" not in json.dumps(result)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM truth_records").fetchone()[0] == 1
    assert ".glob(" not in Path(builder.__file__).read_text(encoding="utf-8")


def test_does_not_open_forbidden_human_trade_log(monkeypatch, tmp_path):
    opened: list[str] = []
    real_open = open

    def spy_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", spy_open)
    _build(tmp_path, [_exact_row()])

    assert all(Path(path).name != "trades.log" for path in opened)


def test_summary_is_aggregate_and_labels_sim_pnl_non_canonical(tmp_path):
    _, summary_path, result = _build(tmp_path, [_exact_row()])
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["dataset"]["pnl_label"] == "simulated_non_canonical_not_money"
    assert payload["dataset"]["eligible_for_policy"] is False
    assert "source_row" not in summary_path.read_text(encoding="utf-8")
    assert result["proto_r2_exact_no"]["settled_mature_n"] == 1


def test_benchmark_view_filters_settled_mature_with_probs(tmp_path):
    mature = _exact_row(eval_key="Tokyo|2026-05-20|exact|25|C", market_id="1")
    fresh = _exact_row(
        eval_key="Paris|2026-05-28|exact|24|C",
        market_id="3",
        outcome="NO",
        bucket="resolved_fresh",
        p_model_no=0.5,
        p_market_no=0.5,
        sim_pnl=0.0,
    )
    pending = _exact_row(
        eval_key="Seoul|2026-05-20|exact|26|C",
        market_id="2",
        outcome=None,
        bucket="pending",
        p_model_no=0.5,
        p_market_no=0.5,
        sim_pnl=0.0,
    )
    db, _, _ = _build(tmp_path, [mature, fresh, pending])

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM v_benchmark_input").fetchone()[0] == 1
        row = conn.execute("SELECT side, snapshot_ts_utc, model_prob, market_prob_at_eval FROM v_benchmark_input").fetchone()
        assert row == ("NO", "2026-05-21T12:00:00Z", 0.85, 0.79)


def test_real_bse_acceptance_reproduces_or_skips_data_missing(tmp_path):
    bse = Path("data/runtime_import/bot_signal_evaluations.jsonl")
    if not bse.exists():
        pytest.skip("DATA_MISSING_BSE_LOCAL")

    db = tmp_path / "decision_dataset.db"
    summary = tmp_path / "decision_dataset_summary.json"
    result = builder.build_dataset(
        db_path=db,
        exact_no_resolutions=Path("data/exact_no_resolutions_log_only.jsonl"),
        blocked_signals_resolutions=Path("data/runtime_import_derived/blocked_signals_resolutions.jsonl"),
        bot_signal_evaluations=bse,
        output_summary=summary,
        conflicts_path=tmp_path / "resolution_conflicts.jsonl",
    )

    assert result["bse_directional_at_or_above"]["brier_advantage"] == pytest.approx(-0.0939, abs=0.0001)


def test_builder_has_no_bot_import():
    import_lines = [
        line.strip()
        for line in Path(builder.__file__).read_text(encoding="utf-8").splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    assert "import bot" not in import_lines
    assert "from bot import" not in "\n".join(import_lines)


def test_cli_direct_script_smoke(tmp_path):
    exact = tmp_path / "exact.jsonl"
    bsr = tmp_path / "bsr.jsonl"
    db = tmp_path / "cli.db"
    summary = tmp_path / "summary.json"
    _write_jsonl(exact, [_exact_row()])
    _write_jsonl(bsr, [])

    result = subprocess.run(
        [
            sys.executable,
            "tools/decision_dataset_builder.py",
            "--db",
            str(db),
            "--exact-no-resolutions",
            str(exact),
            "--blocked-signals-resolutions",
            str(bsr),
            "--output-summary",
            str(summary),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["proto_r2_exact_no"]["settled_mature_n"] == 1
    assert summary.exists()


def test_bsr_cross_check_quarantines_mismatch(tmp_path):
    eval_key = "Tokyo|2026-05-20|exact|25|C"
    exact = [_exact_row(eval_key=eval_key, outcome="NO")]
    bsr = [{"match_key": eval_key, "resolved": True, "outcome": "No", "win_for_trader": False}]
    db, _, result = _build(tmp_path, exact, bsr)

    assert result["conflicts"]["count"] == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM truth_records").fetchone()[0] == 0
