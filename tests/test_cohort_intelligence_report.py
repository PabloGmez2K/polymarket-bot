from __future__ import annotations

import json
from pathlib import Path

from tools import cohort_intelligence_report as report


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def eval_row(
    key: str,
    *,
    condition: str,
    city: str = "Singapore",
    threshold: float = 33,
    unit: str = "C",
    forecast: float = 31.6,
    our_prob: float = 84.0,
    mkt_prob: float = 52.0,
    gate: str = "SHADOW_EXACT_NO_GLOBAL",
) -> dict:
    return {
        "ts_utc": "2026-05-26T00:00:00+00:00",
        "cycle_id": "2026-05-26T00:00",
        "eval_key": key,
        "city": city,
        "date_iso": "2026-05-26",
        "condition": condition,
        "threshold": threshold,
        "threshold_high": None,
        "unit": unit,
        "would_buy": False,
        "bot_edge_pct_at_signal": round(our_prob - mkt_prob, 2),
        "skip_or_block_reason": "shadow_only_override" if gate in {"SHADOW_EXACT_NO_GLOBAL", "SHADOW_EXACT_NO_NEAR_THRESHOLD"} else None,
        "decision_gate": gate,
        "decision_confidence": our_prob,
        "our_prob": our_prob,
        "mkt_prob": mkt_prob,
        "forecast_max": forecast,
    }


def resolution_row(key: str, *, outcome: str = "No", city: str = "Singapore", condition: str = "exact") -> dict:
    return {
        "match_key": key,
        "city": city,
        "date": "2026-05-26",
        "condition": condition,
        "trader": "Thrifty-Original",
        "outcome": outcome,
        "avg_price_entered": 0.52,
        "resolved": True,
        "win_for_trader": outcome == "No",
        "market_id": "m1",
        "condition_id": "c1",
        "city_mode_at_record_time": "shadow",
        "reason_blocked": "condition_filtered",
    }


def test_exact_no_near_threshold_metrics_and_review_block_verdict(tmp_path):
    evals = []
    resolutions = []
    for idx in range(10):
        key = f"Singapore|2026-05-{idx + 1:02d}|exact|33|C"
        evals.append(eval_row(key, condition="exact", forecast=31.6, our_prob=84.0, mkt_prob=52.0))
        resolutions.append(resolution_row(key, outcome="No" if idx < 4 else "Yes"))
    signals = report.build_signal_rows(evals, [], resolutions)
    metrics = report.cohort_metrics("exact/NO near-threshold", signals)

    assert metrics["n_closed"] == 10
    assert metrics["wins"] == 4
    assert metrics["losses"] == 6
    assert metrics["wr_observed"] == 0.4
    assert metrics["avg_our_prob"] == 0.84
    assert metrics["calibration_gap"] == 0.44
    assert metrics["pnl_simulated_unit"] < 0
    assert metrics["verdict"] == "REVIEW_BLOCK_LIVE"


def test_directional_no_candidate_for_canary_review(tmp_path):
    evals = []
    resolutions = []
    for idx in range(10):
        key = f"Tokyo|2026-05-{idx + 1:02d}|at_or_above|26|C"
        evals.append(
            eval_row(
                key,
                city="Tokyo",
                condition="at_or_above",
                threshold=26,
                forecast=24,
                our_prob=65.0,
                mkt_prob=40.0,
                gate="",
            )
        )
        resolutions.append(
            resolution_row(
                key,
                city="Tokyo",
                condition="at_or_above",
                outcome="No" if idx < 7 else "Yes",
            )
        )
    signals = report.build_signal_rows(evals, [], resolutions)
    metrics = report.cohort_metrics("directional NO", signals)

    assert metrics["n_closed"] == 10
    assert metrics["wr_observed"] == 0.7
    assert metrics["avg_our_prob"] == 0.65
    assert metrics["calibration_gap"] == -0.05
    assert metrics["pnl_simulated_unit"] > 0
    assert metrics["gate_current"] == "SHADOW"
    assert metrics["verdict"] == "CANDIDATE_FOR_CANARY_REVIEW"


def test_build_report_groups_main_and_directional_subcohorts(tmp_path):
    data_dir = tmp_path / "data"
    evals = []
    resolutions = []
    for idx in range(10):
        key = f"Tokyo|2026-05-{idx + 1:02d}|at_or_below|20|C"
        evals.append(
            eval_row(
                key,
                city="Tokyo",
                condition="at_or_below",
                threshold=20,
                forecast=23,
                our_prob=62.0,
                mkt_prob=45.0,
                gate="",
            )
        )
        resolutions.append(
            resolution_row(
                key,
                city="Tokyo",
                condition="at_or_below",
                outcome="No" if idx < 6 else "Yes",
            )
        )
    near_key = "Singapore|2026-05-26|exact|33|C"
    evals.append(eval_row(near_key, condition="exact", forecast=31.6))
    resolutions.append(resolution_row(near_key, outcome="No"))
    write_jsonl(data_dir / "bot_signal_evaluations.jsonl", evals)
    write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", resolutions)
    write_jsonl(data_dir / "skip_log.jsonl", [])
    (data_dir / "trade_lifecycle.json").write_text(json.dumps({"records": []}), encoding="utf-8")

    built = report.build_report(data_dir=data_dir)

    main = {row["cohort"]: row for row in built["main_cohorts"]}
    assert main["directional NO"]["n_closed"] == 10
    assert main["exact/NO near-threshold"]["n_closed"] == 1
    assert any(row["cohort"] == "directional NO / city=Tokyo" for row in built["directional_no_subcohorts"])
    assert built["best_directional_no_subcohort"]["cohort"] == "directional NO / city=Tokyo"
    assert built["summary_verdicts"]["DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND"] == "YES"


def test_insufficient_sample_reports_missing_resolution_count(tmp_path):
    data_dir = tmp_path / "data"
    key = "Tokyo|2026-05-26|at_or_above|26|C"
    write_jsonl(
        data_dir / "bot_signal_evaluations.jsonl",
        [eval_row(key, city="Tokyo", condition="at_or_above", gate="")],
    )
    write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [])
    write_jsonl(data_dir / "skip_log.jsonl", [])

    built = report.build_report(data_dir=data_dir)

    assert built["summary_verdicts"]["DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND"] == "INSUFFICIENT_SAMPLE"
    assert built["directional_no_next_trigger"]["resolutions_missing_for_min_sample"] == 10


def test_resolution_only_directional_no_rows_are_counted():
    resolutions = []
    for idx in range(10):
        key = f"Hong Kong|2026-05-{idx + 1:02d}|at_or_above|31|C"
        resolutions.append(
            resolution_row(
                key,
                city="Hong Kong",
                condition="at_or_above",
                outcome="No" if idx < 6 else "Yes",
            )
        )

    signals = report.build_signal_rows([], [], resolutions)
    metrics = report.cohort_metrics("directional NO", signals)

    assert metrics["n_closed"] == 10
    assert metrics["wins"] == 6
    assert metrics["losses"] == 4
    assert metrics["wr_observed"] == 0.6


def test_trade_lifecycle_directional_no_rows_are_counted_with_real_pnl():
    payload = {
        "records": [
            {
                "id": "a",
                "label": "Seoul 26C May17 NO",
                "question": "Will the highest temperature in Seoul be 26C or higher on May 17?",
                "city": "Seoul",
                "side": "NO",
                "date": "2026-05-17",
                "condition": "at_or_above",
                "status": "closed",
                "opened_at": "2026-05-17T04:00:00+00:00",
                "closed_at": "2026-05-17T08:00:00+00:00",
                "entry_context": {"forecast_max": 25.3, "our_prob": 54.0, "mkt_price": 24.0, "edge_pct": 30.0},
                "close_context": {"close_action": "RESOLVED_WIN", "pnl_cash": 0.5},
            },
            {
                "id": "b",
                "label": "Tokyo 31C May18 NO",
                "question": "Will the highest temperature in Tokyo be 31C or higher on May 18?",
                "city": "Tokyo",
                "side": "NO",
                "date": "2026-05-18",
                "condition": "at_or_above",
                "status": "closed",
                "opened_at": "2026-05-18T04:00:00+00:00",
                "closed_at": "2026-05-18T08:00:00+00:00",
                "entry_context": {"forecast_max": 30.5, "our_prob": 60.0, "mkt_price": 30.0, "edge_pct": 30.0},
                "close_context": {"close_action": "LOSS_TOTAL", "pnl_cash": -1.0},
            },
        ]
    }

    rows = report.lifecycle_signal_rows(payload)
    metrics = report.cohort_metrics("directional NO", rows)

    assert metrics["n_closed"] == 2
    assert metrics["wins"] == 1
    assert metrics["losses"] == 1
    assert metrics["pnl_real_reported_noncanonical"] == -0.5
