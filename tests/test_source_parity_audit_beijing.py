import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import source_parity_audit_beijing as parity


def test_comparison_metrics_use_absolute_thresholds():
    rows = parity.build_comparisons(
        ["2026-04-01", "2026-04-02", "2026-04-03"],
        {"2026-04-01": 20.0, "2026-04-02": 21.4, "2026-04-03": 19.0},
        {"2026-04-01": 20.2, "2026-04-02": 20.0, "2026-04-03": 17.0},
    )

    metrics = parity.compute_metrics(rows)

    assert [row.delta_c for row in rows] == [-0.2, 1.4, 2.0]
    assert metrics["n_compared"] == 3
    assert metrics["median_abs_delta_c"] == 1.4
    assert metrics["pct_abs_delta_ge_1c"] == 66.7
    assert metrics["pct_abs_delta_ge_2c"] == 33.3


def test_missing_wu_csv_returns_fetcher_missing_verdict(tmp_path):
    om_csv = tmp_path / "om.csv"
    om_csv.write_text("date,open_meteo_max_c\n2026-04-01,20\n", encoding="utf-8")
    md_out = tmp_path / "report.md"
    json_out = tmp_path / "report.json"

    args = SimpleNamespace(
        start="2026-04-01",
        end="2026-04-01",
        days=60,
        open_meteo_csv=str(om_csv),
        wu_csv=None,
        blocked_resolutions=None,
        md_out=str(md_out),
        json_out=str(json_out),
        no_write_json=False,
    )

    report = parity.build_report(args)

    assert report["verdict"] == "WU_FETCHER_MISSING"
    assert report["comparisons"][0]["status"] == "wu_fetcher_missing"


def test_blocked_exact_outcome_matches_wu_high():
    blocked = [
        {"date_local": "2026-04-18", "condition": "exact", "strike_c": 27.0, "outcome": "Yes"},
        {"date_local": "2026-04-18", "condition": "exact", "strike_c": 26.0, "outcome": "No"},
    ]

    table, metrics = parity.build_blocked_table(blocked, {"2026-04-18": 27.0})

    assert [row["outcome_matches_wu"] for row in table] == [True, True]
    assert metrics["blocked_comparable"] == 2
    assert metrics["blocked_outcome_matches_wu"] == 2
