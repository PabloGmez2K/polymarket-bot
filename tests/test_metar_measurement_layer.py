import json
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import metar_parity_report as report
import metar_shadow_fetch as fetch


def _row(hour, temp, raw=None):
    return {
        "reportTime": f"2026-05-13T{hour:02d}:00:00Z",
        "temp": temp,
        "rawOb": raw or f"ZBAA 13{hour:02d}00Z 00000KT 9999 FEW030 {int(temp):02d}/10 Q1010",
    }


def test_parse_metar_temperature_supports_negative_and_missing():
    assert fetch.parse_metar_temperature("ZBAA 131200Z 00000KT M05/M08 Q1010") == (-5.0, -8.0)
    assert fetch.parse_metar_temperature("ZBAA 131200Z 00000KT 24// Q1010") == (24.0, None)
    assert fetch.parse_metar_temperature("not a metar") == (None, None)


def test_wave2_station_metadata_is_log_only_and_wave1_remains_intact():
    assert set(fetch.WAVE1_STATIONS) == {
        "ZBAA",
        "ZSPD",
        "ZSSS",
        "RJTT",
        "RJAA",
        "OEJN",
        "SABE",
        "SAEZ",
        "LTAC",
        "ZUCK",
    }
    assert fetch.WAVE2_STATIONS == {
        "RKSI": {"city": "Seoul", "tz": "Asia/Seoul"},
        "WSSS": {"city": "Singapore", "tz": "Asia/Singapore"},
        "CYYZ": {"city": "Toronto", "tz": "America/Toronto"},
        "NZWN": {"city": "Wellington", "tz": "Pacific/Auckland"},
        "LEMD": {"city": "Madrid", "tz": "Europe/Madrid"},
        "LIMC": {"city": "Milan", "tz": "Europe/Rome"},
        "EDDM": {"city": "Munich", "tz": "Europe/Berlin"},
    }
    assert fetch.station_city("RKSI") == "Seoul"
    assert fetch.station_timezone("WSSS") == "Asia/Singapore"
    assert fetch.station_city("ZBAA") == "Beijing"


def test_daily_aggregation_derives_tmax_tmin_with_coverage():
    rows = [_row(hour, 10 + (hour % 8)) for hour in range(0, 24, 2)]
    rows.append(_row(23, 25))

    payload = fetch.derive_daily_temperatures(rows, "ZBAA", "2026-05-13", "UTC")

    assert payload["status"] == "ok"
    assert payload["tmax_c"] == 25
    assert payload["tmin_c"] == 10
    assert payload["coverage"]["coverage_ok"] is True


def test_insufficient_coverage_does_not_invent_tmax_tmin():
    payload = fetch.derive_daily_temperatures([_row(12, 31), _row(13, 32)], "ZBAA", "2026-05-13", "UTC")

    assert payload["status"] == "insufficient_metar_coverage"
    assert payload["tmax_c"] is None
    assert payload["tmin_c"] is None


def test_parity_drift_classification_flags_large_delta():
    metrics = {
        "n_compared_metar_wu": 31,
        "median_abs_metar_wu_delta_c": 0.4,
        "max_abs_metar_wu_delta_c": 1.2,
        "coverage_pct": 90.0,
    }

    verdict, reasons = report.classify_parity_drift(metrics)

    assert verdict == "A_METAR_PARITY_DRIFT"
    assert any(reason.startswith("median_abs_metar_wu_delta_c") for reason in reasons)
    assert any(reason.startswith("max_abs_metar_wu_delta_c") for reason in reasons)


def test_report_remains_log_only_and_avoids_trading_or_canonical(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    (metar_dir / "ZBAA_2026-05-13.json").write_text(
        json.dumps(
            {
                "city": "Beijing",
                "icao": "ZBAA",
                "date_local": "2026-05-13",
                "status": "ok",
                "tmax_c": 27.0,
                "coverage": {"coverage_ok": True, "obs_count": 24},
            }
        ),
        encoding="utf-8",
    )
    wu_csv = tmp_path / "wu.csv"
    wu_csv.write_text("icao,date,wu_high_c\nZBAA,2026-05-13,27.2\n", encoding="utf-8")
    args = SimpleNamespace(
        metar_dir=str(metar_dir),
        icao=None,
        wu_csv=str(wu_csv),
        gamma_csv=None,
        open_meteo_csv=None,
    )

    payload = report.build_report(args)
    markdown = report.render_markdown(payload)

    assert payload["log_only"] is True
    assert "does not authorize runtime integration" in markdown
    assert "canonical source changes" in markdown
    assert "BUY/SELL/SKIP" in markdown


def test_operational_readout_surfaces_coverage_drift_om_and_lucknow_watch(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    (metar_dir / "ZBAA_2026-05-13.json").write_text(
        json.dumps(
            {
                "city": "Beijing",
                "icao": "ZBAA",
                "date_local": "2026-05-13",
                "status": "ok",
                "tmax_c": 30.0,
                "coverage": {"coverage_ok": True, "obs_count": 24},
            }
        ),
        encoding="utf-8",
    )
    (metar_dir / "ZUCK_2026-05-13.json").write_text(
        json.dumps(
            {
                "city": "Chongqing",
                "icao": "ZUCK",
                "date_local": "2026-05-13",
                "status": "insufficient_metar_coverage",
                "tmax_c": None,
                "coverage": {"coverage_ok": False, "obs_count": 3},
            }
        ),
        encoding="utf-8",
    )
    wu_csv = tmp_path / "wu.csv"
    wu_csv.write_text(
        "icao,date,wu_high_c\n"
        "ZBAA,2026-05-13,28.5\n",
        encoding="utf-8",
    )
    om_csv = tmp_path / "om.csv"
    om_csv.write_text(
        "icao,date,open_meteo_max_c\n"
        "ZBAA,2026-05-13,28.7\n",
        encoding="utf-8",
    )
    args = SimpleNamespace(
        metar_dir=str(metar_dir),
        icao=None,
        wu_csv=str(wu_csv),
        gamma_csv=None,
        open_meteo_csv=str(om_csv),
    )

    payload = report.build_report(args)
    markdown = report.render_markdown(payload)
    codes = {alert["code"] for alert in payload["alerts"]}

    assert "## Operational Readout" in markdown
    assert "A_METAR_PARITY_DRIFT" in codes
    assert "A_METAR_COVERAGE_GAP" in codes
    assert "A_METAR_VS_OM_DELTA" in codes
    assert "LUCKNOW_COMPARABLE_DAYS_WATCH" in codes
    assert payload["station_summary"][0]["parity_status"] in {"DRIFT", "COVERAGE_GAP"}


def test_cyyz_incomplete_current_local_day_is_waiting_not_coverage_gap(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    (metar_dir / "CYYZ_2026-05-17.json").write_text(
        json.dumps(
            {
                "city": "Toronto",
                "icao": "CYYZ",
                "date_local": "2026-05-17",
                "timezone": "America/Toronto",
                "status": "insufficient_metar_coverage",
                "tmax_c": None,
                "coverage": {
                    "coverage_ok": False,
                    "obs_count": 21,
                    "first_local_hour": 0,
                    "last_local_hour": 16,
                },
            }
        ),
        encoding="utf-8",
    )
    args = SimpleNamespace(
        metar_dir=str(metar_dir),
        icao=None,
        wu_csv=None,
        gamma_csv=None,
        open_meteo_csv=None,
        generated_at="2026-05-17T22:02:47+00:00",
    )

    payload = report.build_report(args)
    cyyz = next(station for station in payload["station_summary"] if station["icao"] == "CYYZ")
    wave2 = next(wave for wave in payload["wave_summary"] if wave["wave"] == "Wave 2")
    codes = {alert["code"] for alert in payload["alerts"] if alert.get("icao") == "CYYZ"}

    assert cyyz["parity_status"] == "WAITING_LOCAL_DAY_CLOSE"
    assert cyyz["insufficient_coverage_rows"] == 0
    assert cyyz["waiting_local_day_close_rows"] == 1
    assert wave2["coverage_status"] == "WAITING_LOCAL_DAY_CLOSE"
    assert "A_METAR_COVERAGE_GAP" not in codes


def test_cyyz_closed_prior_local_day_coverage_ok(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    (metar_dir / "CYYZ_2026-05-16.json").write_text(
        json.dumps(
            {
                "city": "Toronto",
                "icao": "CYYZ",
                "date_local": "2026-05-16",
                "timezone": "America/Toronto",
                "status": "ok",
                "tmax_c": 21.0,
                "tmin_c": 9.0,
                "coverage": {
                    "coverage_ok": True,
                    "obs_count": 30,
                    "first_local_hour": 0,
                    "last_local_hour": 23,
                },
            }
        ),
        encoding="utf-8",
    )
    args = SimpleNamespace(
        metar_dir=str(metar_dir),
        icao=None,
        wu_csv=None,
        gamma_csv=None,
        open_meteo_csv=None,
        generated_at="2026-05-17T22:02:47+00:00",
    )

    payload = report.build_report(args)
    cyyz = next(station for station in payload["station_summary"] if station["icao"] == "CYYZ")
    row = payload["rows"][0]

    assert row["coverage_status"] == "coverage_ok"
    assert cyyz["coverage_pct"] == 100.0
    assert cyyz["insufficient_coverage_rows"] == 0
    assert cyyz["waiting_local_day_close_rows"] == 0
    assert cyyz["parity_status"] == "WAITING_WU_OR_GAMMA"
