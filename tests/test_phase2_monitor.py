"""
Tests for Phase 2 mixed-condition monitor (v10.6.50).

Covers _phase2_monitor_stats, _build_phase2_monitor_message, maybe_run_phase2_monitor.
"""
import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import bot


def _make_lifecycle(records, tmp_path):
    path = tmp_path / "trade_lifecycle.json"
    path.write_text(json.dumps({"records": records}), encoding="utf-8")
    return str(path)


def _closed_record(condition, opened_at, pnl):
    win = pnl > 0
    return {
        "condition": condition,
        "opened_at": opened_at,
        "status": "closed",
        "close_context": {
            "pnl_cash": pnl,
            "close_action": "RESOLVED_WIN" if win else "RESOLVED_LOSS",
        },
    }


PHASE2_START = "2026-05-10"
BEFORE_PHASE2 = "2026-05-09"


def _patch_lifecycle(monkeypatch, path):
    monkeypatch.setattr(bot, "TRADE_LIFECYCLE_FILE", path)


class TestLegacyMonitorRetired:
    def test_legacy_monitor_returns_false_on_or_after_phase2_open(self):
        state = {}
        result = bot.maybe_run_condition_monitor(
            state, now=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
        )
        assert result is False

    def test_legacy_monitor_returns_false_after_phase2_open(self):
        state = {}
        result = bot.maybe_run_condition_monitor(
            state, now=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
        )
        assert result is False


class TestPhase2MonitorStats:
    def test_no_file_returns_empty(self, tmp_path, monkeypatch):
        _patch_lifecycle(monkeypatch, str(tmp_path / "nonexistent.json"))
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 20))
        assert stats["n_mixed"] == 0
        assert stats["mixed_kill_switch"] is False
        assert stats["exact_kill_switch"] is False
        assert stats["file_found"] is False

    def test_no_kill_switch_with_good_wr(self, tmp_path, monkeypatch):
        records = [_closed_record("exact", PHASE2_START + "T10:00:00Z", 1.0) for _ in range(15)]
        path = _make_lifecycle(records, tmp_path)
        _patch_lifecycle(monkeypatch, path)
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 20))
        assert stats["n_mixed"] == 15
        assert stats["wr_mixed"] == 1.0
        assert stats["mixed_kill_switch"] is False

    def test_mixed_kill_switch_triggers_at_n20_wr_below_40(self, tmp_path, monkeypatch):
        records = (
            [_closed_record("exact", PHASE2_START + "T10:00:00Z", 1.0) for _ in range(6)]
            + [_closed_record("at_or_above", PHASE2_START + "T10:00:00Z", -1.0) for _ in range(14)]
        )
        path = _make_lifecycle(records, tmp_path)
        _patch_lifecycle(monkeypatch, path)
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 20))
        assert stats["n_mixed"] == 20
        assert stats["mixed_kill_switch"] is True
        assert stats["wr_mixed"] == pytest.approx(6 / 20)

    def test_exact_kill_switch_triggers_at_n10_wr_below_40(self, tmp_path, monkeypatch):
        records = (
            [_closed_record("exact", PHASE2_START + "T10:00:00Z", 1.0) for _ in range(3)]
            + [_closed_record("exact", PHASE2_START + "T10:00:00Z", -1.0) for _ in range(7)]
        )
        path = _make_lifecycle(records, tmp_path)
        _patch_lifecycle(monkeypatch, path)
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 20))
        assert stats["n_exact"] == 10
        assert stats["exact_kill_switch"] is True
        assert stats["wr_exact"] == pytest.approx(3 / 10)

    def test_ignores_trades_before_phase2_start(self, tmp_path, monkeypatch):
        records = [_closed_record("exact", BEFORE_PHASE2 + "T10:00:00Z", -1.0) for _ in range(25)]
        path = _make_lifecycle(records, tmp_path)
        _patch_lifecycle(monkeypatch, path)
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 20))
        assert stats["n_mixed"] == 0
        assert stats["mixed_kill_switch"] is False

    def test_range_condition_excluded_from_mixed(self, tmp_path, monkeypatch):
        records = [_closed_record("range", PHASE2_START + "T10:00:00Z", -1.0) for _ in range(25)]
        path = _make_lifecycle(records, tmp_path)
        _patch_lifecycle(monkeypatch, path)
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 20))
        assert stats["n_mixed"] == 0
        assert stats["mixed_kill_switch"] is False

    def test_at_or_below_included_in_mixed(self, tmp_path, monkeypatch):
        records = [_closed_record("at_or_below", PHASE2_START + "T10:00:00Z", -1.0) for _ in range(20)]
        path = _make_lifecycle(records, tmp_path)
        _patch_lifecycle(monkeypatch, path)
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 20))
        assert stats["n_mixed"] == 20
        assert stats["mixed_kill_switch"] is True

    def test_ignores_open_trades(self, tmp_path, monkeypatch):
        records = [{
            "condition": "exact",
            "opened_at": PHASE2_START + "T10:00:00Z",
            "status": "open",
            "close_context": {"pnl_cash": -1.0},
        } for _ in range(25)]
        path = _make_lifecycle(records, tmp_path)
        _patch_lifecycle(monkeypatch, path)
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 20))
        assert stats["n_mixed"] == 0

    def test_days_since_open_computed_correctly(self, tmp_path, monkeypatch):
        _patch_lifecycle(monkeypatch, str(tmp_path / "nonexistent.json"))
        stats = bot._phase2_monitor_stats(today=date(2026, 5, 25))
        assert stats["days_since_open"] == 15


class TestBuildPhase2MonitorMessage:
    def _base_stats(self, mixed_kill=False, exact_kill=False):
        return {
            "mixed_kill_switch": mixed_kill,
            "exact_kill_switch": exact_kill,
            "wr_mixed_pct": "30.0",
            "n_mixed": 20,
            "n_mixed_wins": 6,
            "wr_exact_pct": "30.0",
            "n_exact": 10,
            "n_exact_wins": 3,
            "days_since_open": 10,
        }

    def test_no_kill_switch_returns_empty(self):
        msg = bot._build_phase2_monitor_message(self._base_stats())
        assert msg == ""

    def test_mixed_kill_switch_message_contains_rollback(self):
        msg = bot._build_phase2_monitor_message(self._base_stats(mixed_kill=True))
        assert "Phase 2 mixed-condition rollback recommended" in msg
        assert "QUALITY_TRADER_CONDITIONS=" in msg
        assert "ACTIVE_TRADING_CITIES=NONE" in msg
        assert "BUY" not in msg
        assert "SELL" not in msg

    def test_exact_kill_switch_message_contains_degraded(self):
        msg = bot._build_phase2_monitor_message(self._base_stats(exact_kill=True))
        assert "Exact slice degraded" in msg
        assert "QUALITY_TRADER_CONDITIONS=" in msg
        assert "at_or_above" in msg

    def test_both_kill_switches_produces_two_parts(self):
        msg = bot._build_phase2_monitor_message(self._base_stats(mixed_kill=True, exact_kill=True))
        assert "Phase 2 mixed-condition rollback recommended" in msg
        assert "Exact slice degraded" in msg


class TestMaybeRunPhase2Monitor:
    def _no_kill_stats(self):
        return {
            "mixed_kill_switch": False,
            "exact_kill_switch": False,
            "wr_mixed_pct": "60.0",
            "wr_exact_pct": "60.0",
            "n_mixed": 5,
            "n_exact": 3,
            "days_since_open": 5,
            "file_found": False,
        }

    def _mixed_kill_stats(self):
        return {
            "mixed_kill_switch": True,
            "exact_kill_switch": False,
            "wr_mixed_pct": "30.0",
            "n_mixed": 20,
            "n_mixed_wins": 6,
            "wr_exact_pct": "60.0",
            "n_exact": 5,
            "n_exact_wins": 3,
            "days_since_open": 10,
            "file_found": True,
        }

    def test_returns_false_when_no_kill_switch(self, monkeypatch):
        monkeypatch.setattr(bot, "_phase2_monitor_stats", lambda **kw: self._no_kill_stats())
        state = {}
        result = bot.maybe_run_phase2_monitor(state, now=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc))
        assert result is False

    def test_sends_and_returns_true_on_kill_switch(self, monkeypatch):
        monkeypatch.setattr(bot, "_phase2_monitor_stats", lambda **kw: self._mixed_kill_stats())
        sent = []
        monkeypatch.setattr(bot, "send_telegram", lambda msg: sent.append(msg))
        state = {}
        result = bot.maybe_run_phase2_monitor(state, now=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc))
        assert result is True
        assert len(sent) == 1
        assert "Phase 2 mixed-condition rollback recommended" in sent[0]

    def test_anti_spam_same_day(self, monkeypatch):
        monkeypatch.setattr(bot, "_phase2_monitor_stats", lambda **kw: self._mixed_kill_stats())
        sent = []
        monkeypatch.setattr(bot, "send_telegram", lambda msg: sent.append(msg))
        state = {
            "phase2_monitor_last_sent": {
                "date": "2026-05-20",
                "mixed_kill": True,
                "exact_kill": False,
            }
        }
        result = bot.maybe_run_phase2_monitor(state, now=datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc))
        assert result is False
        assert len(sent) == 0

    def test_sends_again_next_day(self, monkeypatch):
        monkeypatch.setattr(bot, "_phase2_monitor_stats", lambda **kw: self._mixed_kill_stats())
        sent = []
        monkeypatch.setattr(bot, "send_telegram", lambda msg: sent.append(msg))
        state = {
            "phase2_monitor_last_sent": {
                "date": "2026-05-19",
                "mixed_kill": True,
                "exact_kill": False,
            }
        }
        result = bot.maybe_run_phase2_monitor(state, now=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc))
        assert result is True
        assert len(sent) == 1

    def test_state_updated_after_send(self, monkeypatch):
        monkeypatch.setattr(bot, "_phase2_monitor_stats", lambda **kw: self._mixed_kill_stats())
        monkeypatch.setattr(bot, "send_telegram", lambda msg: None)
        state = {}
        bot.maybe_run_phase2_monitor(state, now=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc))
        assert state["phase2_monitor_last_sent"]["date"] == "2026-05-20"
        assert state["phase2_monitor_last_sent"]["mixed_kill"] is True
