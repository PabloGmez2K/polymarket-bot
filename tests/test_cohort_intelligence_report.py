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
    ts_utc: str = "2026-05-27T00:00:00+00:00",
    side: str | None = None,
    city_mode: str = "shadow",
    would_buy: bool = False,
) -> dict:
    return {
        "ts_utc": ts_utc,
        "cycle_id": "2026-05-26T00:00",
        "eval_key": key,
        "city": city,
        "date_iso": "2026-05-26",
        "condition": condition,
        "threshold": threshold,
        "threshold_high": None,
        "unit": unit,
        "side": side,
        "city_mode": city_mode,
        "would_buy": would_buy,
        "bot_edge_pct_at_signal": round(our_prob - mkt_prob, 2),
        "skip_or_block_reason": "shadow_only_override" if gate in {"SHADOW_EXACT_NO_GLOBAL", "SHADOW_EXACT_NO_NEAR_THRESHOLD"} else None,
        "decision_gate": gate,
        "decision_confidence": our_prob,
        "our_prob": our_prob,
        "mkt_prob": mkt_prob,
        "forecast_max": forecast,
        "cohort_key": f"{condition}/{side or 'UNKNOWN'}/mode={city_mode}",
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
        "market_id": f"m:{key}",
        "condition_id": f"c:{key}",
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
    assert built["directional_forward_capture"]["directional_forward_seen"] == 1
    assert built["directional_forward_capture"]["status"] == "CAPTURE_ACTIVE_NO_RESOLUTIONS_YET"


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
    metrics = report.cohort_metrics("directional NO", [], rows)

    assert metrics["n_closed"] == 0
    assert metrics["n_executed_trades_unique"] == 2
    assert metrics["pnl_real_reported_noncanonical"] == -0.5


def test_duplicate_evaluations_same_market_count_once_for_calibration():
    key = "Singapore|2026-05-26|exact|33|C"
    evals = [
        eval_row(key, condition="exact", forecast=31.6, our_prob=80.0, mkt_prob=52.0),
        eval_row(key, condition="exact", forecast=31.7, our_prob=84.0, mkt_prob=52.0),
        eval_row(key, condition="exact", forecast=31.8, our_prob=82.0, mkt_prob=52.0),
    ]
    resolutions = [resolution_row(key, outcome="No")]

    signals = report.build_signal_rows(evals, [], resolutions)
    metrics = report.cohort_metrics("exact/NO near-threshold", signals)

    assert metrics["n_seen_raw"] == 3
    assert metrics["n_closed_raw"] == 3
    assert metrics["n_closed_calibration_unique"] == 1
    assert metrics["duplicates_removed_for_calibration"] == 2
    assert metrics["wins_calibration"] == 1
    assert metrics["data_quality_verdict"] == "DEDUPED_OK"
    assert metrics["duplicate_diagnostics"]["top_duplicate_calibration_keys"][0]["duplicates_removed"] == 2


def test_two_real_trades_same_market_do_not_disappear_from_executed_pnl():
    key = "Shanghai|2026-05-26|at_or_above|26|C"
    signals = [
        report.build_signal_rows(
            [eval_row(key, city="Shanghai", condition="at_or_above", threshold=26, gate="")],
            [],
            [resolution_row(key, city="Shanghai", condition="at_or_above", outcome="No")],
        )[0]
    ]
    lifecycle = {
        "records": [
            {
                "id": "buy-a",
                "position_key": "token:x|date:2026-05-26|side:NO",
                "city": "Shanghai",
                "side": "NO",
                "date": "2026-05-26",
                "condition": "at_or_above",
                "status": "closed",
                "opened_at": "2026-05-26T04:00:00+00:00",
                "closed_at": "2026-05-26T08:00:00+00:00",
                "entry_context": {"forecast_max": 25.3, "our_prob": 60.0, "mkt_price": 30.0},
                "close_context": {"close_action": "RESOLVED_WIN", "pnl_cash": 0.7},
            },
            {
                "id": "buy-b",
                "position_key": "token:x|date:2026-05-26|side:NO",
                "city": "Shanghai",
                "side": "NO",
                "date": "2026-05-26",
                "condition": "at_or_above",
                "status": "closed",
                "opened_at": "2026-05-26T10:00:00+00:00",
                "closed_at": "2026-05-26T14:00:00+00:00",
                "entry_context": {"forecast_max": 25.2, "our_prob": 61.0, "mkt_price": 31.0},
                "close_context": {"close_action": "LOSS_TOTAL", "pnl_cash": -0.4},
            },
        ]
    }

    metrics = report.cohort_metrics(
        "directional NO",
        signals,
        report.lifecycle_signal_rows(lifecycle),
    )

    assert metrics["n_closed_calibration_unique"] == 1
    assert metrics["n_executed_trades_unique"] == 2
    assert metrics["pnl_real_reported_noncanonical"] == 0.3


def test_directional_forward_linked_outcome_produces_one_calibration_unique(tmp_path):
    data_dir = tmp_path / "data"
    key = "Tokyo|2026-05-27|at_or_above|26|C"
    write_jsonl(
        data_dir / "bot_signal_evaluations.jsonl",
        [
            eval_row(key, city="Tokyo", condition="at_or_above", threshold=26, gate="", ts_utc="2026-05-27T00:00:00+00:00"),
            eval_row(key, city="Tokyo", condition="at_or_above", threshold=26, gate="", ts_utc="2026-05-27T04:00:00+00:00"),
        ],
    )
    write_jsonl(
        data_dir / "blocked_signals_resolutions.jsonl",
        [resolution_row(key, city="Tokyo", condition="at_or_above", outcome="No")],
    )
    write_jsonl(data_dir / "skip_log.jsonl", [])
    (data_dir / "trade_lifecycle.json").write_text(json.dumps({"records": []}), encoding="utf-8")

    built = report.build_report(data_dir=data_dir)
    directional = {row["cohort"]: row for row in built["main_cohorts"]}["directional NO"]

    assert directional["n_closed_raw"] == 2
    assert directional["n_closed_calibration_unique"] == 1
    assert directional["duplicates_removed_for_calibration"] == 1
    assert built["directional_forward_capture"]["directional_forward_seen"] == 2
    assert built["directional_forward_capture"]["directional_forward_resolved_calibration_unique"] == 1
    assert built["directional_forward_capture"]["status"] == "CALIBRATION_ACCUMULATING"


def test_historical_directional_resolution_does_not_drive_forward_gate(tmp_path):
    data_dir = tmp_path / "data"
    key = "Tokyo|2026-05-20|at_or_above|26|C"
    write_jsonl(
        data_dir / "bot_signal_evaluations.jsonl",
        [
            eval_row(
                key,
                city="Tokyo",
                condition="at_or_above",
                threshold=26,
                gate="",
                ts_utc="2026-05-20T00:00:00+00:00",
            )
        ],
    )
    write_jsonl(
        data_dir / "blocked_signals_resolutions.jsonl",
        [resolution_row(key, city="Tokyo", condition="at_or_above", outcome="No")],
    )
    write_jsonl(data_dir / "skip_log.jsonl", [])
    (data_dir / "trade_lifecycle.json").write_text(json.dumps({"records": []}), encoding="utf-8")

    built = report.build_report(data_dir=data_dir)

    assert {row["cohort"]: row for row in built["main_cohorts"]}["directional NO"]["n_closed_calibration_unique"] == 1
    assert built["directional_forward_capture"]["directional_forward_resolved_calibration_unique"] == 0
    assert built["summary_verdicts"]["DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND"] == "INSUFFICIENT_SAMPLE"


def test_surviving_cohorts_by_side_groups_forward_recorded_side_and_mode(tmp_path):
    data_dir = tmp_path / "data"
    exact_yes = "Dallas|2026-05-27|exact|28|C"
    directional_yes = "Dallas|2026-05-27|at_or_above|28|C"
    directional_no = "Tokyo|2026-05-27|at_or_below|20|C"
    write_jsonl(
        data_dir / "bot_signal_evaluations.jsonl",
        [
            eval_row(exact_yes, city="Dallas", condition="exact", threshold=28, side="YES", city_mode="active", would_buy=True),
            eval_row(directional_yes, city="Dallas", condition="at_or_above", threshold=28, side="YES", city_mode="active", would_buy=True),
            eval_row(directional_no, city="Tokyo", condition="at_or_below", threshold=20, side="NO", city_mode="shadow"),
        ],
    )
    write_jsonl(data_dir / "blocked_signals_resolutions.jsonl", [])
    write_jsonl(data_dir / "skip_log.jsonl", [])
    (data_dir / "trade_lifecycle.json").write_text(json.dumps({"records": []}), encoding="utf-8")

    built = report.build_report(data_dir=data_dir)
    rows = {(row["cohort"], row["city_mode"]): row for row in built["surviving_cohorts_by_side"]}

    assert rows[("exact / YES", "active")]["n_eval_forward"] == 1
    assert rows[("exact / YES", "active")]["n_would_buy"] == 1
    assert rows[("directional / YES", "active")]["n_eval_forward"] == 1
    assert rows[("directional / NO", "shadow")]["n_shadow"] == 1
    assert rows[("directional / NO", "shadow")]["n_resolved_calibration_unique"] == 0


def test_surviving_exact_no_is_protected_not_recovery_candidate(tmp_path):
    data_dir = tmp_path / "data"
    key = "Singapore|2026-05-27|exact|33|C"
    write_jsonl(
        data_dir / "bot_signal_evaluations.jsonl",
        [eval_row(key, condition="exact", side="NO", gate="SHADOW_EXACT_NO_GLOBAL", city_mode="shadow")],
    )
    write_jsonl(
        data_dir / "blocked_signals_resolutions.jsonl",
        [resolution_row(key, outcome="No")],
    )
    write_jsonl(data_dir / "skip_log.jsonl", [])
    (data_dir / "trade_lifecycle.json").write_text(json.dumps({"records": []}), encoding="utf-8")

    built = report.build_report(data_dir=data_dir)
    row = next(row for row in built["surviving_cohorts_by_side"] if row["cohort"] == "exact / NO")

    assert row["candidate_allowed"] is False
    assert row["protected_reason"] == "EXACT_NO_REMAINS_SHADOW_PROTECTED"
    assert row["manual_review_state"] == "ACCUMULATING_FORWARD_EVIDENCE"
    assert row["n_resolved_calibration_unique"] == 1


def test_legacy_rows_without_recorded_side_do_not_enter_surviving_forward_block(tmp_path):
    data_dir = tmp_path / "data"
    key = "Tokyo|2026-05-27|at_or_above|26|C"
    write_jsonl(
        data_dir / "bot_signal_evaluations.jsonl",
        [eval_row(key, city="Tokyo", condition="at_or_above", threshold=26, side=None, gate="")],
    )
    write_jsonl(
        data_dir / "blocked_signals_resolutions.jsonl",
        [resolution_row(key, city="Tokyo", condition="at_or_above", outcome="No")],
    )
    write_jsonl(data_dir / "skip_log.jsonl", [])
    (data_dir / "trade_lifecycle.json").write_text(json.dumps({"records": []}), encoding="utf-8")

    built = report.build_report(data_dir=data_dir)

    assert built["surviving_cohorts_by_side"] == []
    assert built["live_side_visibility_forward"]["n_forward_rows_with_recorded_side"] == 0


def test_directional_no_clean_resolution_cohort_is_not_artificially_reduced():
    evals = []
    resolutions = []
    for idx in range(18):
        key = f"Tokyo|2026-05-{idx + 1:02d}|at_or_above|26|C"
        evals.append(
            eval_row(
                key,
                city="Tokyo",
                condition="at_or_above",
                threshold=26,
                forecast=24,
                our_prob=61.0,
                mkt_prob=40.0,
                gate="",
            )
        )
        resolutions.append(
            resolution_row(
                key,
                city="Tokyo",
                condition="at_or_above",
                outcome="No" if idx < 10 else "Yes",
            )
        )

    metrics = report.cohort_metrics("directional NO", report.build_signal_rows(evals, [], resolutions))

    assert metrics["n_seen_raw"] == 18
    assert metrics["n_closed_raw"] == 18
    assert metrics["n_closed_calibration_unique"] == 18
    assert metrics["duplicates_removed_for_calibration"] == 0


def test_verdict_uses_calibration_unique_count_not_raw_duplicate_count():
    key = "Singapore|2026-05-26|exact|33|C"
    evals = [
        eval_row(key, condition="exact", forecast=31.6, our_prob=84.0, mkt_prob=52.0)
        for _ in range(12)
    ]
    signals = report.build_signal_rows(evals, [], [resolution_row(key, outcome="Yes")])

    metrics = report.cohort_metrics("exact/NO near-threshold", signals)

    assert metrics["n_closed_raw"] == 12
    assert metrics["n_closed_calibration_unique"] == 1
    assert metrics["decision_verdict"] == "INSUFFICIENT_SAMPLE"


def test_missing_calibration_key_degrades_to_data_quality_blocker():
    rows = [
        {
            "condition": "exact",
            "side": "NO",
            "outcome": "YES",
            "resolved": True,
            "win": False,
            "our_prob": 84.0,
            "simulated_unit_pnl": -0.52,
            "gate_current": "SHADOW",
        }
        for _ in range(10)
    ]

    metrics = report.cohort_metrics("exact/NO near-threshold", rows)

    assert metrics["data_quality_verdict"] == "DATA_QUALITY_BLOCKER"
    assert metrics["decision_verdict"] == "DATA_QUALITY_BLOCKER"
