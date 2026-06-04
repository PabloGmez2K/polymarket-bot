from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import trader_benchmark as bench


def _raw_row(
    *,
    match_key: str,
    trader: str,
    win: float = 1.0,
    price: float = 0.4,
    checked_at: str = "2026-06-01T00:00:00+00:00",
    date: str = "2026-06-01",
    wr: float = 82.0,
    outcome: str = "Yes",
    consensus: bool = False,
    city: str = "Tokyo",
) -> dict:
    return {
        "match_key": match_key,
        "city": city,
        "date": date,
        "condition": "exact",
        "trader": trader,
        "trader_historical_wr": wr,
        "outcome": outcome,
        "avg_price_entered": price,
        "close_price": 1.0 if win else 0.0,
        "resolved": True,
        "win_for_trader": win,
        "has_consensus": consensus,
        "checked_at": checked_at,
    }


def _rows_for_candidate() -> list[bench.BsrRow]:
    rows: list[bench.BsrRow] = []
    for i in range(30):
        rows.append(
            bench.row_from_json(
                _raw_row(
                    match_key=f"mk-{i}",
                    trader=f"T{i % 5}",
                    win=1.0,
                    price=0.35,
                    date="2026-06-01",
                )
            )
        )
    return [row for row in rows if row is not None]


def _summary(rows: list[bench.BsrRow], samples: int = 80) -> dict:
    return bench.build_summary(
        [],
        rows,
        source_description="fixture",
        bootstrap_samples=samples,
        seed=2026,
        cutoff_utc=bench.DEFAULT_CUTOFF_UTC,
        generated_at_utc="2026-06-04T00:00:00+00:00",
    )


def _cell(summary: dict, cohort: str) -> dict:
    return next(cell for cell in summary["l1_cells"] if cell["cohort"] == cohort)


def test_dedup_by_match_key_uses_oldest_checked_at():
    late = bench.row_from_json(
        _raw_row(match_key="dup", trader="T1", win=0.0, checked_at="2026-06-02T00:00:00+00:00")
    )
    early = bench.row_from_json(
        _raw_row(match_key="dup", trader="T2", win=1.0, checked_at="2026-06-01T00:00:00+00:00")
    )

    deduped = bench.dedup_by_match_key([late, early])  # type: ignore[list-item]

    assert len(deduped) == 1
    assert deduped[0].trader == "T2"
    assert deduped[0].win_for_trader == 1.0


def test_lto_removes_top_trader_and_recalculates_metrics():
    rows = [
        bench.row_from_json(_raw_row(match_key=f"a{i}", trader="T1", win=1.0, price=0.5))
        for i in range(3)
    ] + [
        bench.row_from_json(_raw_row(match_key="b1", trader="T2", win=0.0, price=0.5)),
        bench.row_from_json(_raw_row(match_key="c1", trader="T3", win=1.0, price=0.5)),
    ]
    clean = [row for row in rows if row is not None]

    remaining, removed = bench.leave_top_trader_out(clean)
    metrics = bench.metrics_for_rows(remaining, bootstrap_samples=20, seed=2026, seed_key="lto")

    assert removed["removed_label"] == "T1"
    assert removed["removed_n"] == 3
    assert metrics["n"] == 2
    assert metrics["n_traders"] == 2
    assert metrics["WR"] == pytest.approx(0.5)


def test_dominance_gate_marks_cell_non_promotable():
    rows = _rows_for_candidate()
    for i in range(31, 61):
        rows.append(
            bench.row_from_json(
                _raw_row(match_key=f"dom-{i}", trader="T0", win=1.0, price=0.35, date="2026-06-01")
            )
        )
    rows = [row for row in rows if row is not None]

    summary = _summary(rows)
    cell = _cell(summary, ">=80|trader_YES|no")

    assert cell["top1_pct"] > 50.0
    assert cell["verdict"] == "NON_PROMOTABLE_BY_DOMINANCE"
    assert not summary["top_candidates"]


def test_forward_dominance_marks_forward_dominated_when_post_dedup_balanced():
    rows: list[bench.BsrRow] = []
    for i in range(30):
        rows.append(
            bench.row_from_json(
                _raw_row(
                    match_key=f"old-{i}",
                    trader=f"T{i % 5}",
                    win=1.0,
                    price=0.35,
                    date="2026-05-20",
                )
            )
        )
    for i in range(10):
        rows.append(
            bench.row_from_json(
                _raw_row(
                    match_key=f"forward-{i}",
                    trader="T0" if i < 6 else f"T{i - 5}",
                    win=1.0,
                    price=0.35,
                    date="2026-06-01",
                )
            )
        )
    clean = [row for row in rows if row is not None]

    summary = _summary(clean)
    cell = _cell(summary, ">=80|trader_YES|no")

    assert cell["top1_pct"] <= 50.0
    assert cell["forward"]["top1_pct"] > 50.0
    assert cell["verdict"] == "FORWARD_DOMINATED"


def test_candidate_only_if_all_hard_gates_pass():
    summary = _summary(_rows_for_candidate())
    cell = _cell(summary, ">=80|trader_YES|no")

    assert cell["n"] == 30
    assert cell["n_traders"] == 5
    assert cell["top1_pct"] <= 50.0
    assert cell["lto"]["n"] >= 20
    assert cell["forward"]["n"] >= 10
    assert cell["edge_ci"]["lower"] > 0
    assert cell["verdict"] == "TRADER_ALPHA_CANDIDATE"
    assert summary["top_candidates"]


def test_aggregate_only_summary_excludes_row_level_identifiers_and_handles():
    rows = [
        bench.row_from_json(
            _raw_row(match_key="secret-match-key", trader="SensitiveHandle", win=1.0, price=0.4)
        )
    ]
    summary = _summary([row for row in rows if row is not None])
    text = json.dumps(summary)

    assert summary["eligible_for_policy"] is False
    assert summary["disclaimer"] == bench.DISCLAIMER
    assert "secret-match-key" not in text
    assert "SensitiveHandle" not in text
    assert "match_key" not in text


def test_cluster_bootstrap_is_deterministic():
    rows = _rows_for_candidate()
    first = bench.bootstrap_edge_by_trader(rows, samples=100, seed=2026, seed_key="same")
    second = bench.bootstrap_edge_by_trader(rows, samples=100, seed=2026, seed_key="same")

    assert first == second


def test_no_gamma_network_glob_bot_import_or_trades_log_references():
    source = Path("tools/trader_benchmark.py").read_text(encoding="utf-8")

    assert "urllib" not in source
    assert "requests" not in source
    assert "socket" not in source
    assert "import glob" not in source
    assert ".glob(" not in source
    assert "import bot" not in source
    assert "Gamma" not in source
    assert "open(\"trades.log\"" not in source
    assert "Path(\"trades.log\"" not in source


def test_output_disclaimer_and_policy_false(tmp_path: Path):
    input_path = tmp_path / "blocked_signals_resolutions.jsonl"
    input_path.write_text(
        "\n".join(json.dumps(_raw_row(match_key=f"mk-{i}", trader=f"T{i % 5}")) for i in range(5)),
        encoding="utf-8",
    )
    output = tmp_path / "summary.json"

    summary = bench.run_benchmark(input_path, output, bootstrap_samples=20)

    assert output.exists()
    assert summary["eligible_for_policy"] is False
    assert summary["disclaimer"] == bench.DISCLAIMER


def test_input_allowlist_rejects_unexpected_filename(tmp_path: Path):
    bad = tmp_path / "other.jsonl"
    bad.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="allowlist"):
        bench.run_benchmark(bad, tmp_path / "summary.json", bootstrap_samples=20)
