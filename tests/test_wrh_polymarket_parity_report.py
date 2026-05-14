import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import wrh_polymarket_parity_report as parity


def _row(date_local, strike, outcome="Yes"):
    return {
        "match_key": f"Istanbul|{date_local}|exact|{strike}|C",
        "city": "Istanbul",
        "date": date_local,
        "condition": "exact",
        "outcome": outcome,
        "resolved": True,
    }


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
