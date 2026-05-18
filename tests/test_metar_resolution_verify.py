import json
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import metar_resolution_verify as verify


def _row(city="Madrid", day="2026-05-17", condition="at_or_above", threshold="20", outcome="Yes"):
    return {
        "city": city,
        "date": day,
        "condition": condition,
        "match_key": f"{city}|{day}|{condition}|{threshold}|C",
        "outcome": outcome,
        "close_price": 1.0,
        "resolved": True,
    }


def _snapshot(metar_dir, icao="LEMD", day="2026-05-17", tmax=22.0, status="ok", coverage_ok=True):
    (metar_dir / f"{icao}_{day}.json").write_text(
        json.dumps(
            {
                "city": "Madrid",
                "icao": icao,
                "date_local": day,
                "status": status,
                "tmax_c": tmax,
                "tmin_c": 7.0,
                "coverage": {"coverage_ok": coverage_ok, "obs_count": 24},
            }
        ),
        encoding="utf-8",
    )


def test_match_at_or_above_synthetic(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    _snapshot(metar_dir, tmax=22.0)

    result = verify.evaluate_row(_row(condition="at_or_above", threshold="20", outcome="Yes"), metar_dir, verify.build_city_station_map())

    assert result["status"] == "MATCH"
    assert result["metar_outcome"] == "Yes"
    assert result["delta_c"] == 2.0
    assert result["margin_to_flip"] == 2.0


def test_match_at_or_below_synthetic(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    _snapshot(metar_dir, tmax=18.0)

    result = verify.evaluate_row(_row(condition="at_or_below", threshold="20", outcome="Yes"), metar_dir, verify.build_city_station_map())

    assert result["status"] == "MATCH"
    assert result["metar_outcome"] == "Yes"
    assert result["delta_c"] == -2.0


def test_mismatch_synthetic(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    _snapshot(metar_dir, tmax=18.0)

    result = verify.evaluate_row(_row(condition="at_or_above", threshold="20", outcome="Yes"), metar_dir, verify.build_city_station_map())

    assert result["status"] == "MISMATCH"
    assert result["official_outcome"] == "Yes"
    assert result["metar_outcome"] == "No"


def test_no_snapshot(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()

    result = verify.evaluate_row(_row(), metar_dir, verify.build_city_station_map())

    assert result["status"] == "NO_SNAPSHOT"
    assert result["reason"] == "no_metar_file_for_city_date"


def test_insufficient_metar(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    _snapshot(metar_dir, tmax=None, status="insufficient_metar_coverage", coverage_ok=False)

    result = verify.evaluate_row(_row(), metar_dir, verify.build_city_station_map())

    assert result["status"] == "INSUFFICIENT_METAR"
    assert result["snapshots"][0]["status"] == "insufficient_metar_coverage"


def test_fahrenheit_threshold_from_match_key(tmp_path):
    metar_dir = tmp_path / "metar"
    metar_dir.mkdir()
    _snapshot(metar_dir, tmax=21.0)
    row = _row(city="Toronto", day="2026-05-17", condition="exact", threshold="70", outcome="Yes")
    row["match_key"] = "Toronto|2026-05-17|exact|70|F"
    _snapshot(metar_dir, icao="CYYZ", day="2026-05-17", tmax=21.0)

    result = verify.evaluate_row(row, metar_dir, verify.build_city_station_map())

    assert result["threshold_unit"] == "F"
    assert round(result["threshold_c"], 1) == 21.1
    assert result["status"] == "MATCH"


def test_real_local_data_has_visual_crossing_backfill_pilot_snapshots():
    args = SimpleNamespace(
        resolutions=str(REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"),
        metar_dir=str(REPO_ROOT / "data" / "metar_shadow"),
        city=None,
        limit=None,
        days=60,
        generated_at="2026-05-18T00:00:00+00:00",
    )

    payload = verify.build_report(args)

    assert payload["summary"]["status_counts"].get("MATCH", 0) == 34
    assert payload["summary"]["status_counts"].get("MISMATCH", 0) == 6
    assert payload["summary"]["status_counts"].get("NO_SNAPSHOT", 0) == 0


def test_apply_patch_review_requires_verified_candidate():
    summary = {
        "cities": {
            "Madrid": {
                "state": "SOURCE_VERIFIED_CANDIDATE",
                "n_compared": 50,
                "n_match": 50,
                "n_mismatch": 0,
            },
            "Toronto": {
                "state": "SOURCE_LIKELY_EQUIVALENT",
                "n_compared": 30,
                "n_match": 29,
                "n_mismatch": 1,
            },
        }
    }

    alerts = verify.build_alerts(summary)
    apply_patch_alerts = [alert for alert in alerts if alert["code"] == "A_APPLY_PATCH_REVIEW"]

    assert len(apply_patch_alerts) == 1
    assert apply_patch_alerts[0]["city"] == "Madrid"
    assert "Requires Opus review" in apply_patch_alerts[0]["message"]
