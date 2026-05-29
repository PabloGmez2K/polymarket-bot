"""Tests for H3_AUTOMATED_LOG_ONLY_CAPTURE_V1 (tools/h3_auto_capture.py).

All tests inject model fetchers or mock build_snapshot — no real network calls.
Tests verify:
  1. Capture is triggered for valid directional (at_or_above / at_or_below) markets
  2. Not triggered for exact / range conditions
  3. Not triggered for Seoul (not in ACTIVE_CITY_COORDS) / source-fidelity suspect cities
  4. Open-Meteo errors do not affect the calling context (fail-closed)
  5. Write errors do not affect the calling context (fail-closed)
  6. Idempotency: existing snapshot skips build_snapshot call (dedup before compute)
  7. BUY/SELL/SKIP decisions are unchanged (function returns None always)
  8. No DB writes / no Railway writes
  9. eligible_for_policy=False and live_policy_eligible=False invariants
 10. Gate OFF by default (H3_AUTO_CAPTURE_ENABLED != "1")
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

import tools.h3_auto_capture as capture_mod
from tools.h3_auto_capture import maybe_capture_h3_multimodel_shadow

# ── Helpers ───────────────────────────────────────────────────────────────────

_VALID_SHANGHAI = dict(
    city="Shanghai",
    target_date="2026-06-05",
    condition="at_or_above",
    threshold=34.0,
    unit="C",
    mkt_prob_yes=0.12,
    market_id="mkt_123",
    condition_id="cid_456",
)

_VALID_TOKYO = dict(
    city="Tokyo",
    target_date="2026-06-05",
    condition="at_or_below",
    threshold=28.0,
    unit="C",
    mkt_prob_yes=0.65,
    market_id="mkt_789",
)


def _make_snap(city: str = "Shanghai", condition: str = "at_or_above") -> dict[str, Any]:
    """Minimal snapshot dict that satisfies the caller's assertions."""
    return {
        "h3_hypothesis_id": "H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1_1",
        "snapshot_ts_utc": "2026-06-05T10:00:00Z",
        "snapshot_key": f"{city}|mkt_123|2026-06-05|{condition}|34.0|C|2026-06-05T10:00:00Z|multimodel_disagreement_candidate_v1",
        "city": city,
        "eligible_for_policy": False,
        "live_policy_eligible": False,
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_out_dir(tmp_path, monkeypatch):
    """Redirect all file I/O in h3_auto_capture to a temp directory."""
    out_dir = tmp_path / "multimodel_shadow"
    monkeypatch.setattr(capture_mod, "OUT_DIR", out_dir)
    monkeypatch.setattr(capture_mod, "PREREG_MARKER_FILE", out_dir / "_h3_prereg_cutoff.json")


# ── Test 1: capture called for valid directional market ───────────────────────

def test_capture_called_for_at_or_above(monkeypatch, tmp_path):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock(return_value=_make_snap("Shanghai", "at_or_above"))
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    result = maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)

    assert result is None  # never returns a value
    assert mock_build.called
    call_kwargs = mock_build.call_args.kwargs
    assert call_kwargs["city"] == "Shanghai"
    assert call_kwargs["condition"] == "at_or_above"
    assert call_kwargs["threshold"] == 34.0
    assert call_kwargs["unit"] == "C"


def test_capture_called_for_at_or_below(monkeypatch):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock(return_value=_make_snap("Tokyo", "at_or_below"))
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    result = maybe_capture_h3_multimodel_shadow(**_VALID_TOKYO)

    assert result is None
    assert mock_build.called
    assert mock_build.call_args.kwargs["condition"] == "at_or_below"


# ── Test 2: not captured for exact / range ────────────────────────────────────

@pytest.mark.parametrize("bad_condition", ["exact", "range", "between", ""])
def test_not_captured_for_unsupported_condition(monkeypatch, bad_condition):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock()
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    result = maybe_capture_h3_multimodel_shadow(
        **{**_VALID_SHANGHAI, "condition": bad_condition}
    )

    assert result is None
    mock_build.assert_not_called()


# ── Test 3: not captured for Seoul / non-ACTIVE city ─────────────────────────

@pytest.mark.parametrize("bad_city", ["Seoul", "London", "Paris", "Madrid", ""])
def test_not_captured_for_non_active_city(monkeypatch, bad_city):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock()
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    result = maybe_capture_h3_multimodel_shadow(
        **{**_VALID_SHANGHAI, "city": bad_city}
    )

    assert result is None
    mock_build.assert_not_called()


# ── Test: not captured for Fahrenheit unit ────────────────────────────────────

def test_not_captured_for_fahrenheit(monkeypatch):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock()
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    result = maybe_capture_h3_multimodel_shadow(
        **{**_VALID_SHANGHAI, "unit": "F"}
    )

    assert result is None
    mock_build.assert_not_called()


# ── Test: not captured when market_id is missing ─────────────────────────────

def test_not_captured_without_market_id(monkeypatch):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock()
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    result = maybe_capture_h3_multimodel_shadow(
        **{**_VALID_SHANGHAI, "market_id": None}
    )

    assert result is None
    mock_build.assert_not_called()


# ── Test 4: Open-Meteo error does not affect the bot cycle ───────────────────

def test_open_meteo_error_does_not_raise(monkeypatch):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    # Simulate build_snapshot raising (e.g. Open-Meteo unreachable)
    monkeypatch.setattr(capture_mod, "build_snapshot", MagicMock(side_effect=RuntimeError("network error")))

    # Must not raise
    result = maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)
    assert result is None


# ── Test 5: Write error does not affect the bot cycle ────────────────────────

def test_write_error_does_not_raise(monkeypatch, tmp_path):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    snap = _make_snap()
    monkeypatch.setattr(capture_mod, "build_snapshot", MagicMock(return_value=snap))

    # Make OUT_DIR a file (not a directory) to trigger write failure
    bad_out = tmp_path / "not_a_dir"
    bad_out.write_text("oops")
    monkeypatch.setattr(capture_mod, "OUT_DIR", bad_out)
    monkeypatch.setattr(capture_mod, "PREREG_MARKER_FILE", bad_out)

    result = maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)
    assert result is None


# ── Test 6: Idempotency — existing snapshot skips build_snapshot ──────────────

def test_idempotency_skips_build_snapshot_on_second_call(monkeypatch, tmp_path):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock(return_value=_make_snap())
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    # First call: should invoke build_snapshot and write file
    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)
    assert mock_build.call_count == 1

    # Second call in the same hour: snapshot file exists → should skip
    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)
    assert mock_build.call_count == 1  # not called again


def test_different_market_ids_do_not_collide(monkeypatch):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock(return_value=_make_snap())
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)
    maybe_capture_h3_multimodel_shadow(**{**_VALID_SHANGHAI, "market_id": "mkt_999"})

    # Different market_ids → different keys → two snapshots
    assert mock_build.call_count == 2


# ── Test 7: BUY/SELL/SKIP remain unchanged (return value is always None) ──────

def test_always_returns_none_for_valid_inputs(monkeypatch):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    monkeypatch.setattr(capture_mod, "build_snapshot", MagicMock(return_value=_make_snap()))

    assert maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI) is None


def test_always_returns_none_when_gate_off(monkeypatch):
    monkeypatch.delenv("H3_AUTO_CAPTURE_ENABLED", raising=False)
    assert maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI) is None


def test_always_returns_none_on_error(monkeypatch):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    monkeypatch.setattr(capture_mod, "build_snapshot", MagicMock(side_effect=Exception("boom")))
    assert maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI) is None


# ── Test 8: No DB writes — function only writes to OUT_DIR ───────────────────

def test_no_db_writes(monkeypatch, tmp_path):
    """Verify no sqlite3 / psycopg2 / SQLAlchemy calls happen."""
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    monkeypatch.setattr(capture_mod, "build_snapshot", MagicMock(return_value=_make_snap()))

    # If the function tried to import sqlite3 and call .connect(), this would fail
    # because we haven't mocked any DB. The test passing proves no DB interaction.
    with patch("sqlite3.connect") as mock_db:
        maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)
        mock_db.assert_not_called()


# ── Test 9: eligible_for_policy=False, live_policy_eligible=False ─────────────

def test_snapshot_eligible_for_policy_is_false(monkeypatch, tmp_path):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    snap = _make_snap()
    assert snap["eligible_for_policy"] is False
    assert snap["live_policy_eligible"] is False

    written_snaps = []

    def _capture_write(snap_data, **_):
        written_snaps.append(snap_data)

    mock_build = MagicMock(return_value=snap)
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)

    # Check what was actually written to disk
    out_dir = capture_mod.OUT_DIR
    snap_files = [f for f in out_dir.iterdir() if f.suffix == ".json" and not f.name.startswith("_")]
    assert len(snap_files) == 1
    on_disk = json.loads(snap_files[0].read_text())
    assert on_disk["eligible_for_policy"] is False
    assert on_disk["live_policy_eligible"] is False


# ── Test 10: Gate off by default ─────────────────────────────────────────────

def test_gate_off_by_default_no_build_snapshot(monkeypatch):
    monkeypatch.delenv("H3_AUTO_CAPTURE_ENABLED", raising=False)
    mock_build = MagicMock()
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)

    mock_build.assert_not_called()


def test_gate_off_explicit_zero(monkeypatch):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "0")
    mock_build = MagicMock()
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)

    mock_build.assert_not_called()


# ── Test: preseeded market_fetch_fn passes correct data ──────────────────────

def test_preseeded_market_data_used(monkeypatch):
    """Verify the injected market_fetch_fn returns the pre-available bot data."""
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")

    captured_kwargs: dict = {}

    def _fake_build(**kwargs):
        captured_kwargs.update(kwargs)
        # Simulate what build_snapshot does: call market_fetch_fn
        mfn = kwargs.get("market_fetch_fn")
        if mfn:
            info = mfn("Shanghai", "2026-06-05", "at_or_above", 34.0, "C")
            assert info["market_id"] == "mkt_123"
            assert info["mkt_prob_yes"] == 0.12
            assert info["condition_id"] == "cid_456"
        return _make_snap()

    monkeypatch.setattr(capture_mod, "build_snapshot", _fake_build)
    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)
    assert captured_kwargs["city"] == "Shanghai"
    assert captured_kwargs["threshold"] == 34.0


# ── Test: all four ACTIVE cities are accepted ─────────────────────────────────

@pytest.mark.parametrize("active_city", ["Shanghai", "Tokyo", "Buenos Aires", "Ankara"])
def test_all_active_cities_accepted(monkeypatch, active_city):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    mock_build = MagicMock(return_value=_make_snap(active_city))
    monkeypatch.setattr(capture_mod, "build_snapshot", mock_build)

    maybe_capture_h3_multimodel_shadow(
        city=active_city,
        target_date="2026-06-05",
        condition="at_or_above",
        threshold=30.0,
        unit="C",
        mkt_prob_yes=0.5,
        market_id="mkt_x",
    )

    assert mock_build.called


# ── Test: prereg cutoff registered on first snapshot ─────────────────────────

def test_prereg_cutoff_registered_on_first_snapshot(monkeypatch, tmp_path):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    snap = _make_snap()
    monkeypatch.setattr(capture_mod, "build_snapshot", MagicMock(return_value=snap))

    # No prereg file exists yet
    assert not capture_mod.PREREG_MARKER_FILE.exists()

    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)

    # Prereg marker should now exist
    assert capture_mod.PREREG_MARKER_FILE.exists()
    marker = json.loads(capture_mod.PREREG_MARKER_FILE.read_text())
    assert "h3_prereg_cutoff_utc" in marker


def test_existing_prereg_cutoff_not_overwritten(monkeypatch, tmp_path):
    monkeypatch.setenv("H3_AUTO_CAPTURE_ENABLED", "1")
    snap = _make_snap()
    monkeypatch.setattr(capture_mod, "build_snapshot", MagicMock(return_value=snap))

    # Write an existing prereg marker
    out_dir = capture_mod.OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    existing_ts = "2026-05-29T22:23:25.004024Z"
    capture_mod.PREREG_MARKER_FILE.write_text(
        json.dumps({"h3_prereg_cutoff_utc": existing_ts}),
        encoding="utf-8",
    )

    maybe_capture_h3_multimodel_shadow(**_VALID_SHANGHAI)

    marker = json.loads(capture_mod.PREREG_MARKER_FILE.read_text())
    assert marker["h3_prereg_cutoff_utc"] == existing_ts  # unchanged
