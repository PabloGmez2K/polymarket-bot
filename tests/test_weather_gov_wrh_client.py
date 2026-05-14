import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import weather_gov_wrh_client as wrh


MINIMAL_WRH_HTML = """
<html>
  <body>
    <table>
      <thead>
        <tr><th>Local Date Time</th><th>Temp</th><th>Dew Point</th></tr>
      </thead>
      <tbody>
        <tr><td>2026-05-13 09:00</td><td>21.1</td><td>10</td></tr>
        <tr><td>2026-05-13 13:00</td><td>24.4 C</td><td>11</td></tr>
        <tr><td>2026-05-13 16:00</td><td>23.0</td><td>12</td></tr>
        <tr><td>2026-05-14 13:00</td><td>26.0</td><td>13</td></tr>
      </tbody>
    </table>
  </body>
</html>
"""


def test_parser_extracts_temp_column_from_minimal_wrh_fixture():
    payload = wrh.parse_wrh_timeseries(MINIMAL_WRH_HTML, "LTFM", "2026-05-13")

    assert payload["temp_column_found"] is True
    assert payload["temp_column"] == "Temp"
    assert payload["raw_rows_count"] == 4
    assert payload["confidence"] == "high"


def test_parser_calculates_daily_max_for_local_date():
    payload = wrh.parse_wrh_timeseries(MINIMAL_WRH_HTML, "LTFM", "2026-05-13")

    assert payload["daily_max_c"] == 24.4


def test_missing_temp_column_returns_controlled_warning():
    fixture = """Date,Wind,Humidity
2026-05-13,5,80
2026-05-13,6,70
"""

    payload = wrh.parse_wrh_timeseries(fixture, "LTFM", "2026-05-13")

    assert payload["temp_column_found"] is False
    assert payload["daily_max_c"] is None
    assert "Temp column not found" in payload["warnings"]
    assert payload["confidence"] == "low"


def test_payload_includes_weather_gov_wrh_dataset():
    payload = wrh.parse_wrh_timeseries(MINIMAL_WRH_HTML, "LTFM", "2026-05-13")

    assert payload["observed_dataset"] == "weather_gov_wrh_timeseries"
    assert payload["source_url"] == "https://www.weather.gov/wrh/timeseries?site=LTFM"


def test_parser_does_not_require_noaa_station_id():
    payload = wrh.parse_wrh_timeseries(
        "Date,Temp\n2026-05-13,22.0\n2026-05-13,25.5\n",
        site="LTFM",
        date_local="2026-05-13",
    )

    assert payload["site"] == "LTFM"
    assert payload["daily_max_c"] == 25.5
    assert "noaa_station_id" not in payload


def test_defensive_no_tabular_rows_does_not_invent_data():
    payload = wrh.parse_wrh_timeseries(
        "<html><script>window.app = {dynamic: true}</script></html>",
        "LTFM",
        "2026-05-13",
    )

    assert payload["raw_rows_count"] == 0
    assert payload["daily_max_c"] is None
    assert payload["confidence"] == "none"
    assert "no parseable tabular rows found" in payload["warnings"]
