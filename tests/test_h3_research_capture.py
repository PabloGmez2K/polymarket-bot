"""Tests for H3_RESEARCH_CAPTURE_SCHEDULE_V1 (maybe_run_h3_research_capture in bot.py).

Verified properties:
  1. Job does not run when H3_RESEARCH_CAPTURE_ENABLED=0 (default)
  2. Job runs when H3_RESEARCH_CAPTURE_ENABLED=1
  3. Job respects cooldown window (skip before cooldown_hours elapsed)
  4. Job runs again after cooldown expires
  5. BUY/SELL/SKIP decisions are not affected (function never touches trading state)
  6. Job uses standalone path (--forward-snapshot), not loop candidates
  7. Fail-closed: subprocess exception does not propagate, returns False
  8. Fail-closed: subprocess timeout does not propagate, returns False
  9. Idempotency within cooldown: second call within window is skipped
 10. No policy authorization: subprocess command never includes policy flags
 11. Function records last_run timestamp in state after successful run
 12. Malformed last_run timestamp treated as absent (proceeds)
 13. Non-zero subprocess exit code still marks as run (fail-closed, logs warning)
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call

import pytest

import bot


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fresh_state() -> dict:
    return {"h3_research_capture_last_run": None}


def _now_utc() -> datetime:
    return datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _completed_proc(returncode: int = 0) -> MagicMock:
    p = MagicMock(spec=subprocess.CompletedProcess)
    p.returncode = returncode
    p.stdout = ""
    p.stderr = ""
    return p


# ── Test 1: disabled by default ───────────────────────────────────────────────

def test_disabled_by_default(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", False)
    state = _fresh_state()
    with patch("subprocess.run") as mock_run:
        result = bot.maybe_run_h3_research_capture(state, now=_now_utc())
    assert result is False
    mock_run.assert_not_called()
    assert state["h3_research_capture_last_run"] is None


# ── Test 2: runs when enabled ─────────────────────────────────────────────────

def test_runs_when_enabled(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = _fresh_state()
    now = _now_utc()
    with patch("subprocess.run", return_value=_completed_proc()) as mock_run:
        result = bot.maybe_run_h3_research_capture(state, now=now)
    assert result is True
    mock_run.assert_called_once()
    assert state["h3_research_capture_last_run"] is not None


# ── Test 3: cooldown respected — skip before window expires ───────────────────

def test_cooldown_respected_skip(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    now = _now_utc()
    last_run = now - timedelta(hours=2)  # only 2h ago, cooldown is 4h
    state = {"h3_research_capture_last_run": last_run.isoformat()}
    with patch("subprocess.run") as mock_run:
        result = bot.maybe_run_h3_research_capture(state, now=now)
    assert result is False
    mock_run.assert_not_called()


# ── Test 4: runs after cooldown expires ───────────────────────────────────────

def test_runs_after_cooldown_expires(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    now = _now_utc()
    last_run = now - timedelta(hours=5)  # 5h ago, cooldown is 4h
    state = {"h3_research_capture_last_run": last_run.isoformat()}
    with patch("subprocess.run", return_value=_completed_proc()) as mock_run:
        result = bot.maybe_run_h3_research_capture(state, now=now)
    assert result is True
    mock_run.assert_called_once()


# ── Test 5: BUY/SELL/SKIP decisions not touched ───────────────────────────────

def test_no_trading_state_mutation(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    trading_keys = ["buy_candidates", "sell_candidates", "skip_reasons", "edge", "sizing"]
    state = _fresh_state()
    for k in trading_keys:
        state[k] = "ORIGINAL"
    with patch("subprocess.run", return_value=_completed_proc()):
        bot.maybe_run_h3_research_capture(state, now=_now_utc())
    for k in trading_keys:
        assert state[k] == "ORIGINAL", f"trading key {k!r} was mutated"


# ── Test 6: uses standalone path, not loop candidates ─────────────────────────

def test_uses_standalone_forward_snapshot_path(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = _fresh_state()
    with patch("subprocess.run", return_value=_completed_proc()) as mock_run:
        bot.maybe_run_h3_research_capture(state, now=_now_utc())
    args = mock_run.call_args[0][0]  # positional: the command list
    assert "--forward-snapshot" in args
    assert bot.H3_RESEARCH_CAPTURE_SCRIPT in args
    # Cities: at_or_above/at_or_below only (no exact/range)
    assert "Shanghai" in args
    assert "Tokyo" in args
    assert "Buenos_Aires" in args
    assert "Ankara" in args


# ── Test 7: fail-closed on subprocess exception ───────────────────────────────

def test_fail_closed_on_subprocess_exception(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = _fresh_state()
    with patch("subprocess.run", side_effect=RuntimeError("Open-Meteo unreachable")):
        result = bot.maybe_run_h3_research_capture(state, now=_now_utc())
    assert result is False
    # last_run NOT updated (no successful execution)
    assert state["h3_research_capture_last_run"] is None


# ── Test 8: fail-closed on subprocess timeout ─────────────────────────────────

def test_fail_closed_on_timeout(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = _fresh_state()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=120)):
        result = bot.maybe_run_h3_research_capture(state, now=_now_utc())
    assert result is False
    assert state["h3_research_capture_last_run"] is None


# ── Test 9: idempotency — second call within cooldown skipped ─────────────────

def test_idempotency_within_cooldown(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = _fresh_state()
    now = _now_utc()
    with patch("subprocess.run", return_value=_completed_proc()) as mock_run:
        r1 = bot.maybe_run_h3_research_capture(state, now=now)
        r2 = bot.maybe_run_h3_research_capture(state, now=now + timedelta(minutes=30))
    assert r1 is True
    assert r2 is False
    assert mock_run.call_count == 1


# ── Test 10: no policy authorization in command ───────────────────────────────

def test_no_policy_flags_in_command(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = _fresh_state()
    with patch("subprocess.run", return_value=_completed_proc()) as mock_run:
        bot.maybe_run_h3_research_capture(state, now=_now_utc())
    cmd = " ".join(str(a) for a in mock_run.call_args[0][0])
    for forbidden in ("--buy", "--sell", "--policy", "eligible_for_policy=true", "live_policy"):
        assert forbidden not in cmd.lower(), f"Policy flag {forbidden!r} found in command"


# ── Test 11: records last_run timestamp ──────────────────────────────────────

def test_records_last_run_timestamp(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = _fresh_state()
    now = _now_utc()
    with patch("subprocess.run", return_value=_completed_proc()):
        bot.maybe_run_h3_research_capture(state, now=now)
    assert state["h3_research_capture_last_run"] == now.isoformat()


# ── Test 12: malformed last_run proceeds ─────────────────────────────────────

def test_malformed_last_run_proceeds(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = {"h3_research_capture_last_run": "not-a-timestamp"}
    with patch("subprocess.run", return_value=_completed_proc()) as mock_run:
        result = bot.maybe_run_h3_research_capture(state, now=_now_utc())
    assert result is True
    mock_run.assert_called_once()


# ── Test 13: non-zero exit still marks run and returns True ──────────────────

def test_nonzero_exit_marks_run(monkeypatch):
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_ENABLED", True)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_COOLDOWN_HOURS", 4)
    monkeypatch.setattr(bot, "H3_RESEARCH_CAPTURE_TIMEOUT_SECONDS", 120)
    state = _fresh_state()
    now = _now_utc()
    with patch("subprocess.run", return_value=_completed_proc(returncode=1)):
        result = bot.maybe_run_h3_research_capture(state, now=now)
    # subprocess ran (no_eligible_markets logs exit=1 in multimodel_shadow)
    assert result is True
    assert state["h3_research_capture_last_run"] == now.isoformat()
