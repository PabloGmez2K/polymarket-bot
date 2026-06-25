from __future__ import annotations

from datetime import datetime, timezone

import bot


def _base_signal(**extra):
    signal = {
        "trader": "Quality-Trader",
        "title": "Will the highest temperature in Reykjavik be 7C on May 5?",
        "city": "Reykjavik",
        "condition": "exact",
        "date": "2026-05-05",
        "temp": 7,
        "unit": "C",
        "outcome": "Yes",
        "avg_price": 0.42,
        "match_key": "Reykjavik|2026-05-05|exact|7|C",
        "trader_win_rate": 81.0,
        "signals_generated_at": "2026-05-04T08:00:00+00:00",
        "trader_win_rate_source": "polymarket_data_api_closed_positions_cashPnl",
        "trader_win_rate_closed_positions_count": 37,
        "trader_win_rate_asof_method": "snapshot_at_signals_generation_no_entry_cutoff",
        "trader_win_rate_cutoff_at": "unknown",
        "trader_win_rate_leakage_status": "not_auditable_no_entry_or_closed_position_cutoff",
        "has_consensus": True,
    }
    signal.update(extra)
    return signal


def _market():
    return {
        "question": "Will the highest temperature in Reykjavik be 7C on May 5?",
        "id": "m-1",
        "conditionId": "cond-1",
        "clobTokenIds": '["yes-token", "no-token"]',
        "slug": "reykjavik-7c-may-5",
    }


def test_blocked_signals_new_records_are_schema_v3_live_eval():
    record = bot._build_blocked_signal_resolution_record(
        _base_signal(bot_would_have_bought=True, bot_evaluation_source="live_eval"),
        _market(),
        [1.0, 0.0],
        datetime(2026, 5, 7, 9, 0, tzinfo=timezone.utc),
    )

    assert record["schema_version"] == 3
    assert record["bot_would_have_bought"] is True
    assert record["bot_evaluation_source"] == "live_eval"
    assert record["market_id"] == "m-1"
    assert record["condition_id"] == "cond-1"
    assert record["token_id_yes"] == "yes-token"
    assert record["token_id_no"] == "no-token"
    assert record["reason_blocked"] in {"condition_filtered", "mixed"}
    assert record["signals_generated_at"] == "2026-05-04T08:00:00+00:00"
    assert record["trader_win_rate_source"] == "polymarket_data_api_closed_positions_cashPnl"
    assert record["trader_win_rate_closed_positions_count"] == 37
    assert record["trader_win_rate_asof_method"] == "snapshot_at_signals_generation_no_entry_cutoff"
    assert record["trader_win_rate_cutoff_at"] == "unknown"
    assert record["trader_win_rate_leakage_status"] == "not_auditable_no_entry_or_closed_position_cutoff"


def test_blocked_signals_v3_does_not_invent_bot_buy_evidence():
    assert bot._blocked_signal_bot_eval_fields(_base_signal()) == {
        "bot_would_have_bought": False,
        "bot_evaluation_source": "unknown",
    }


def test_blocked_signals_v3_scope_guardrails():
    src = bot.maybe_run_blocked_signals_check.__code__.co_names
    assert "execute_trade" not in src
    assert "execute_buy" not in src
    assert "ACTIVE_TRADING_CITIES" not in src
    assert "CANARY_TRADING_CITIES" not in src
    assert "BANKROLL" not in src


def test_directional_no_with_match_key_is_forward_resolution_candidate():
    signal = _base_signal(
        condition="at_or_above",
        outcome="No",
        match_key="Reykjavik|2026-05-05|at_or_above|7|C",
    )

    assert bot._is_blocked_signal_resolution_candidate(signal, "2026-05-06") is True


def test_directional_yes_or_missing_match_key_is_not_forward_resolution_candidate():
    assert bot._is_blocked_signal_resolution_candidate(
        _base_signal(condition="at_or_above", outcome="Yes", match_key="Reykjavik|2026-05-05|at_or_above|7|C"),
        "2026-05-06",
    ) is False
    assert bot._is_blocked_signal_resolution_candidate(
        _base_signal(condition="at_or_below", outcome="No", match_key=""),
        "2026-05-06",
    ) is False


def test_blocked_signals_writer_is_append_only():
    assert "a" in bot.maybe_run_blocked_signals_check.__code__.co_consts
