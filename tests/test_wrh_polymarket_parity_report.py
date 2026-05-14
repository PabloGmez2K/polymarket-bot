import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import wrh_polymarket_parity_report as parity


def _row(date_local, strike, outcome="Yes", **extra):
    row = {
        "match_key": f"Istanbul|{date_local}|exact|{strike}|C",
        "city": "Istanbul",
        "date": date_local,
        "condition": "exact",
        "outcome": outcome,
        "resolved": True,
    }
    row.update(extra)
    return row


def _fetcher(values, calls=None):
    def fetch(site, date_local):
        if calls is not None:
            calls.append((site, date_local))
        value = values.get(date_local)
        return {
            "site": site,
            "date_local": date_local,
            "source_url": f"https://www.weather.gov/wrh/timeseries?site={site}",
            "observed_dataset": "weather_gov_wrh_timeseries",
            "temp_column_found": value is not None,
            "temp_column": "air_temp_set_1" if value is not None else None,
            "daily_max_c": value,
            "raw_rows_count": 10 if value is not None else 0,
            "warnings": [] if value is not None else ["missing fixture daily_max"],
            "confidence": "high" if value is not None else "none",
        }
    return fetch


def test_exact_daily_max_equal_strike_expected_yes():
    report = parity.build_report([_row("2026-05-06", 17, "Yes")], fetcher=_fetcher({"2026-05-06": 17}))

    row = report["rows"][0]
    assert row["expected_yes"] is True
    assert row["parity_match"] is True
    assert report["metrics"]["n_match"] == 1


def test_exact_daily_max_different_strike_expected_no():
    report = parity.build_report([_row("2026-05-06", 20, "No")], fetcher=_fetcher({"2026-05-06": 17}))

    row = report["rows"][0]
    assert row["expected_yes"] is False
    assert row["parity_match"] is True
    assert row["delta_c"] == -3


def test_multiple_rows_same_day_use_single_fetch():
    calls = []
    rows = [_row("2026-05-06", 17, "Yes"), _row("2026-05-06", 20, "No")]

    report = parity.build_report(rows, fetcher=_fetcher({"2026-05-06": 17}, calls))

    assert calls == [("LTFM", "2026-05-06")]
    assert report["metrics"]["unique_dates_fetched"] == 1
    assert report["metrics"]["n_compared"] == 2
    assert report["metrics"]["n_match"] == 2
    assert report["metrics"]["input_row_n"] == 2
    assert report["metrics"]["candidate_row_n"] == 2
    assert report["metrics"]["compared_row_n"] == 2


def test_report_marks_weather_gov_wrh_dataset():
    report = parity.build_report([_row("2026-05-06", 17, "Yes")], fetcher=_fetcher({"2026-05-06": 17}))

    assert report["observed_dataset"] == "weather_gov_wrh_timeseries"
    assert report["rows"][0]["observed_dataset"] == "weather_gov_wrh_timeseries"
    assert report["log_only"] is True


def test_missing_daily_max_row_unknown_not_invented():
    report = parity.build_report([_row("2026-05-06", 17, "Yes")], fetcher=_fetcher({"2026-05-06": None}))

    row = report["rows"][0]
    assert row["daily_max_c"] is None
    assert row["expected_yes"] is None
    assert row["parity_match"] is None
    assert row["status"] == "unknown"
    assert report["verdict"] == "NEED_MORE_DATA"


def test_dedupe_separates_canonical_unique_markets_from_rows():
    rows = [
        _row(
            "2026-05-07",
            23,
            "No",
            market_id="2162211",
            condition_id="0xabc",
            slug="highest-temperature-in-istanbul-on-may-7-2026-23c",
        ),
        _row(
            "2026-05-07",
            23,
            "No",
            market_id="2162211",
            condition_id="0xabc",
            slug="highest-temperature-in-istanbul-on-may-7-2026-23c",
        ),
        _row("2026-04-13", 14, "No"),
    ]

    report = parity.build_report(rows, fetcher=_fetcher({"2026-05-07": 22, "2026-04-13": 12}))
    metrics = report["metrics"]

    assert metrics["candidate_row_n"] == 3
    assert metrics["compared_row_n"] == 3
    assert metrics["canonical_unique_market_n"] == 1
    assert metrics["unique_market_n"] == 1
    assert metrics["fallback_estimated_unique_market_n"] == 2
    assert metrics["rows_without_canonical_market_id_n"] == 1


def test_preliminary_outcome_pass_does_not_meet_opus_gate():
    rows = [
        _row("2026-05-06", 17, "Yes", condition_id="0x17"),
        _row("2026-05-06", 20, "No", condition_id="0x20"),
        _row("2026-05-07", 22, "Yes", condition_id="0x22"),
        _row("2026-05-07", 23, "No", condition_id="0x23"),
        _row("2026-05-13", 23, "Yes", condition_id="0x13"),
    ]

    report = parity.build_report(
        rows,
        fetcher=_fetcher({"2026-05-06": 17, "2026-05-07": 22, "2026-05-13": 23}),
    )

    assert report["verdict"] == "WRH_PARITY_PASS_PRELIMINARY"
    gate = report["opus_reevaluation_gate"]
    assert gate["OPUS_REEVALUATION_GATE_MET"] is False
    assert any(reason.startswith("no_20_demonstrable_unique_markets") for reason in gate["reasons"])
    assert any(reason == "missing_second_explicit_wrh_candidate_city" for reason in gate["reasons"])


def test_markdown_names_outcome_parity_and_opus_gate_separately():
    report = parity.build_report([_row("2026-05-06", 17, "Yes")], fetcher=_fetcher({"2026-05-06": 17}))

    markdown = parity.render_markdown(report)

    assert "## Outcome Parity Metrics" in markdown
    assert "## Opus Re-Evaluation Gate" in markdown
    assert "OPUS_REEVALUATION_GATE_MET" in markdown
    assert "not authorize observed-audit inclusion" in markdown
