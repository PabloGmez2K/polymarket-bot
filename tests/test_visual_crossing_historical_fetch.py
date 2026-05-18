"""Focal tests for tools/visual_crossing_historical_fetch.py.

All tests use mocked HTTP responses — no real network calls are made.
The API key is never printed or written to disk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import visual_crossing_historical_fetch as vc_fetch

_MOCK_KEY = "TESTKEY_NOTREAL_12345"


def _vc_response(tempmax: float = 28.5, tempmin: float = 15.2, source: str = "obs") -> dict:
    return {
        "days": [
            {
                "datetime": "2026-04-10",
                "tempmax": tempmax,
                "tempmin": tempmin,
                "source": source,
                "conditions": "Clear",
                "icon": "clear-day",
            }
        ],
        "stations": {
            "ZBAA": {"id": "ZBAA", "name": "Beijing Capital Int'l"},
        },
    }


def _mock_urlopen(response: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# Test 1: parses tempmax/tempmin correctly
def test_parse_vc_response_extracts_tempmax_tempmin():
    result = vc_fetch.parse_vc_day(_vc_response(tempmax=28.5, tempmin=15.2, source="obs"))

    assert result["status"] == "ok"
    assert result["tmax_c"] == 28.5
    assert result["tmin_c"] == 15.2
    assert result["vc_source"] == "obs"
    assert "ZBAA" in result["vc_stations"]


# Test 2: build_payload generates JSON compatible with metar_resolution_verify
def test_build_payload_generates_compatible_json():
    mock_resp = _mock_urlopen(_vc_response(tempmax=30.1, tempmin=18.3))

    with patch("urllib.request.urlopen", return_value=mock_resp):
        payload = vc_fetch.build_payload(
            icao="ZBAA",
            date_str="2026-04-10",
            tz_name="Asia/Shanghai",
            city="Beijing",
            location="ZBAA",
            api_key=_MOCK_KEY,
        )

    # Fields required by metar_resolution_verify.is_sufficient_metar
    assert payload["status"] == "ok"
    assert payload["coverage"]["coverage_ok"] is True
    assert payload["tmax_c"] == 30.1

    # Extra compatibility fields
    assert payload["log_only"] is True
    assert payload["source"] == "visual_crossing"
    assert payload["tmin_c"] == 18.3
    assert payload["coverage"]["obs_count"] == 1
    assert payload["icao"] == "ZBAA"
    assert payload["date"] == "2026-04-10"


# Test 3: --no-write does not create snapshot file
def test_no_write_does_not_create_file(tmp_path, monkeypatch):
    monkeypatch.setenv("VISUAL_CROSSING_API_KEY", _MOCK_KEY)
    mock_resp = _mock_urlopen(_vc_response())

    with patch("urllib.request.urlopen", return_value=mock_resp):
        exit_code = vc_fetch.main(
            [
                "--icao", "ZBAA",
                "--date", "2026-04-10",
                "--out-dir", str(tmp_path),
                "--no-write",
            ]
        )

    assert exit_code == 0
    assert not (tmp_path / "ZBAA_2026-04-10.json").exists()


# Test 4: fails cleanly when API key env var is missing
def test_missing_api_key_fails_cleanly(monkeypatch, capsys):
    monkeypatch.delenv("VISUAL_CROSSING_API_KEY", raising=False)

    exit_code = vc_fetch.main(["--icao", "OEJN", "--date", "2026-04-10"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "VISUAL_CROSSING_API_KEY" in captured.err
    assert "not set" in captured.err


# Test 5: API key value does not appear in payload JSON
def test_api_key_not_in_output():
    mock_resp = _mock_urlopen(_vc_response())

    with patch("urllib.request.urlopen", return_value=mock_resp):
        payload = vc_fetch.build_payload(
            icao="ZBAA",
            date_str="2026-04-10",
            tz_name="UTC",
            city=None,
            location="ZBAA",
            api_key=_MOCK_KEY,
        )

    payload_str = json.dumps(payload)
    assert _MOCK_KEY not in payload_str, "API key must not appear in serialized payload"
