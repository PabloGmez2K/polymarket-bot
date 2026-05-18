import json
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import visual_crossing_backfill_run as backfill


def _report(status="NO_SNAPSHOT"):
    return {
        "summary": {"status_counts": {status: 1}},
        "results": [
            {
                "city": "Madrid",
                "date": "2026-04-12",
                "icaos": ["LEMD"],
                "status": status,
            }
        ],
    }


def test_collect_missing_uses_verifier_snapshot_format(tmp_path):
    metar_dir = tmp_path / "metar_shadow"
    metar_dir.mkdir()

    missing = backfill.collect_missing_snapshots(_report(), metar_dir)

    assert missing == [
        {
            "icao": "LEMD",
            "date": "2026-04-12",
            "city": "Madrid",
            "tz": "Europe/Madrid",
        }
    ]


def test_existing_snapshot_is_skipped_and_not_missing(tmp_path):
    metar_dir = tmp_path / "metar_shadow"
    metar_dir.mkdir()
    (metar_dir / "LEMD_2026-04-12.json").write_text("{}", encoding="utf-8")

    assert backfill.collect_existing_wave_snapshots(_report(), metar_dir) == {("LEMD", "2026-04-12")}
    assert backfill.collect_missing_snapshots(_report(), metar_dir) == []


def test_load_state_resets_on_new_utc_day(tmp_path):
    state_path = tmp_path / "visual_crossing_backfill_state.json"
    state_path.write_text(
        json.dumps({"date_utc": "2026-05-17", "calls_used": 99, "runs": [{"calls_used": 99}]}),
        encoding="utf-8",
    )

    state = backfill.load_state(state_path, today="2026-05-18")

    assert state == {"date_utc": "2026-05-18", "calls_used": 0, "runs": []}


def test_resolve_resolutions_path_prefers_data_dir_runtime_import_derived(tmp_path):
    data_dir = tmp_path / "data"
    expected = data_dir / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
    expected.parent.mkdir(parents=True)
    expected.write_text("", encoding="utf-8")

    assert backfill.resolve_resolutions_path(data_dir) == expected


def test_resolve_resolutions_path_uses_railway_flat_data_dir_fallback(tmp_path):
    data_dir = tmp_path / "data"
    expected = data_dir / "blocked_signals_resolutions.jsonl"
    data_dir.mkdir()
    expected.write_text("", encoding="utf-8")

    assert backfill.resolve_resolutions_path(data_dir) == expected


def test_resolve_resolutions_path_errors_clearly_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(backfill, "REPO_ROOT", tmp_path / "repo")

    try:
        backfill.resolve_resolutions_path(tmp_path / "data")
    except SystemExit as exc:
        message = str(exc)
    else:
        raise AssertionError("missing resolutions path should abort")

    assert "ERROR: resolutions file not found. Checked:" in message
    assert "runtime_import_derived" in message
    assert "blocked_signals_resolutions.jsonl" in message


def test_dry_run_does_not_require_api_key_or_write_state(tmp_path, monkeypatch, capsys):
    data_dir = tmp_path / "data"
    metar_dir = data_dir / "metar_shadow"
    metar_dir.mkdir(parents=True)
    resolutions = data_dir / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
    resolutions.parent.mkdir()
    resolutions.write_text("", encoding="utf-8")
    monkeypatch.delenv("VISUAL_CROSSING_API_KEY", raising=False)
    monkeypatch.setenv("VISUAL_CROSSING_DAILY_BUDGET", "1")
    monkeypatch.setenv("VISUAL_CROSSING_MAX_CALLS_PER_RUN", "20")

    def fake_run_verifier(_data_dir, _metar_dir, _resolutions_path, write):
        assert write is False
        assert _resolutions_path == resolutions
        return _report()

    monkeypatch.setattr(backfill, "run_verifier", fake_run_verifier)
    monkeypatch.setattr(
        backfill,
        "build_verify_args",
        lambda _data_dir, _metar_dir, _resolutions_path: SimpleNamespace(md_out=str(tmp_path / "report.md")),
    )

    exit_code = backfill.main(["--data-dir", str(data_dir), "--dry-run"])

    assert exit_code == 0
    assert not (data_dir / "visual_crossing_backfill_state.json").exists()
    summary = json.loads(capsys.readouterr().out)
    assert summary["calls_used"] == 0
    assert summary["planned_calls"] == 1
    assert summary["budget_remaining"] == 1
    assert summary["new_snapshots"] == 0
