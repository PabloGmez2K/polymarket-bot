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
        settlement_from_gamma=False,
        gamma_neighbor_radius=3,
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


def _gamma_market(slug, yes=True):
    return {
        "id": slug,
        "slug": slug,
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["1", "0"]' if yes else '["0", "1"]',
        "resolutionSource": "https://www.wunderground.com/history/daily/cn/beijing/ZBAA",
    }


def test_gamma_exact_markets_infer_single_yes_settlement():
    markets = [
        _gamma_market("highest-temperature-in-beijing-on-april-18-2026-26c", yes=False),
        _gamma_market("highest-temperature-in-beijing-on-april-18-2026-27c", yes=True),
    ]

    inferred, warnings = parity.infer_settlement_from_exact_markets(markets)

    assert warnings == []
    assert inferred["2026-04-18"]["status"] == "inferred"
    assert inferred["2026-04-18"]["settlement_temp_c"] == 27.0


def test_gamma_exact_markets_reject_multiple_yes_settlements():
    markets = [
        _gamma_market("highest-temperature-in-beijing-on-april-18-2026-26c", yes=True),
        _gamma_market("highest-temperature-in-beijing-on-april-18-2026-27c", yes=True),
    ]

    inferred, warnings = parity.infer_settlement_from_exact_markets(markets)

    assert warnings == []
    assert inferred["2026-04-18"]["status"] == "unreliable"
    assert inferred["2026-04-18"]["settlement_temp_c"] is None


def test_gamma_settlement_comparison_uses_blocked_exact_slugs():
    blocked = [
        {"date_local": "2026-04-18", "condition": "exact", "strike_c": 26.0, "outcome": "No"},
        {"date_local": "2026-04-18", "condition": "exact", "strike_c": 27.0, "outcome": "Yes"},
    ]

    def fetcher(slug):
        if not (slug.endswith("-26c") or slug.endswith("-27c")):
            raise ValueError("not found")
        return _gamma_market(slug, yes=slug.endswith("-27c"))

    report = parity.build_gamma_settlement_comparisons(blocked, {"2026-04-18": 25.0}, fetcher=fetcher, neighbor_radius=0)

    assert report["verdict"] == "SETTLEMENT_GAMMA_PARITY_FAIL"
    assert report["comparisons"][0]["settlement_temp_c"] == 27.0
    assert report["comparisons"][0]["delta_c"] == -2.0
    assert report["metrics"]["n_dates_compared"] == 1


def test_gamma_settlement_comparison_probes_neighbor_winner():
    blocked = [
        {"date_local": "2026-04-18", "condition": "exact", "strike_c": 26.0, "outcome": "No"},
    ]

    def fetcher(slug):
        if slug.endswith("-26c"):
            return _gamma_market(slug, yes=False)
        if slug.endswith("-27c"):
            return _gamma_market(slug, yes=True)
        raise ValueError("not found")

    report = parity.build_gamma_settlement_comparisons(blocked, {"2026-04-18": 25.0}, fetcher=fetcher, neighbor_radius=1)

    assert report["comparisons"][0]["settlement_temp_c"] == 27.0
    assert report["metrics"]["n_dates_compared"] == 1
    assert report["verdict"] == "SETTLEMENT_GAMMA_PARITY_FAIL"
