from __future__ import annotations

import builtins
import json
from datetime import datetime, timezone

import bot


def _signal(**extra):
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


def test_record_bot_evaluation_writes_jsonl(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)

    ok = bot.record_bot_evaluation(
        "2026-05-18T08:00",
        "Reykjavik|2026-05-05|exact|7|C",
        True,
        city="Reykjavik",
        date_iso="2026-05-05",
        condition="exact",
        side="YES",
        city_mode="active",
        threshold=7,
        unit="C",
        condition_id="cond-1",
        market_id="market-1",
        edge_pct=12.3,
        our_prob=67.1,
        mkt_prob=54.8,
    )

    assert ok is True
    rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["evaluation_source"] == "live_eval"
    assert rows[0]["would_buy"] is True
    assert rows[0]["side"] == "YES"
    assert rows[0]["city_mode"] == "active"
    assert rows[0]["condition_id"] == "cond-1"
    assert rows[0]["market_id"] == "market-1"
    assert rows[0]["cohort_key"] == "exact/YES/mode=active/gate=live_or_passed_gate"
    assert rows[0]["bot_edge_pct_at_signal"] == 12.3


def test_record_bot_evaluation_persists_no_side_cohort(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)

    ok = bot.record_bot_evaluation(
        "2026-05-18T08:00",
        "Tokyo|2026-05-05|at_or_above|28|C",
        False,
        city="Tokyo",
        city_mode="shadow",
        date_iso="2026-05-05",
        condition="at_or_above",
        side="NO",
        threshold=28,
        unit="C",
        edge_pct=15.0,
        decision_gate="fuera_allowlist",
    )

    assert ok is True
    row = json.loads(target.read_text(encoding="utf-8").strip())
    assert row["side"] == "NO"
    assert row["cohort_key"] == "directional/NO/mode=shadow/gate=fuera_allowlist"


def test_record_bot_evaluation_disable_switch_blocks_write(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.setenv("DISABLE_BOT_EVAL_CAPTURE", "1")

    ok = bot.record_bot_evaluation("cycle", "key", False, city="Reykjavik")

    assert ok is False
    assert not target.exists()


def test_record_bot_evaluation_is_no_throw_on_io_error(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)
    monkeypatch.setattr(builtins, "open", boom)

    assert bot.record_bot_evaluation("cycle", "key", False, city="Reykjavik") is False


def test_blocked_signal_resolver_joins_live_eval_when_read_gate_enabled(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.setenv("READ_BOT_EVAL_CAPTURE", "1")
    target.write_text(
        json.dumps({
            "schema_version": 1,
            "ts_utc": datetime(2026, 5, 18, tzinfo=timezone.utc).isoformat(),
            "cycle_id": "2026-05-18T08:00",
            "eval_key": "Reykjavik|2026-05-05|exact|7|C",
            "would_buy": True,
            "bot_edge_pct_at_signal": 14.2,
            "evaluation_source": "live_eval",
            "skip_or_block_reason": None,
            "decision_gate": None,
            "decision_confidence": 72.0,
        }) + "\n",
        encoding="utf-8",
    )

    record = bot._build_blocked_signal_resolution_record(
        _signal(),
        _market(),
        [1.0, 0.0],
        datetime(2026, 5, 18, tzinfo=timezone.utc),
    )

    assert record["bot_evaluation_source"] == "live_eval"
    assert record["bot_would_have_bought"] is True
    assert record["bot_edge_pct_at_signal"] == 14.2
    assert record["bot_evaluation_join_status"] == "captured"


def test_blocked_signal_resolver_marks_missing_when_read_gate_enabled(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.setenv("READ_BOT_EVAL_CAPTURE", "1")

    fields = bot._blocked_signal_bot_eval_fields(_signal(match_key="missing"))

    assert fields["bot_evaluation_source"] == "unknown"
    assert fields["bot_would_have_bought"] is False
    assert fields["bot_evaluation_join_status"] == "missing"


def test_shadow_only_skip_records_shadow_decision_gate(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)
    entry = bot._make_skip_entry(
        "shadow_only_override",
        cycle_id="2026-05-18T08:00",
        city="Reykjavik",
        date_iso="2026-05-05",
        side="NO",
        city_mode="shadow",
        condition="exact",
        threshold=7,
        unit="C",
    )

    ok = bot._record_bot_evaluation_from_skip_entry(entry)

    assert ok is True
    row = json.loads(target.read_text(encoding="utf-8").strip())
    assert row["would_buy"] is False
    assert row["side"] == "NO"
    assert row["city_mode"] == "shadow"
    assert row["skip_or_block_reason"] == "shadow_only_override"
    assert row["decision_gate"] == "shadow_only"


def test_price_filter_counterfactual_uses_existing_cache_and_excludes_exact_no(monkeypatch, tmp_path):
    target = tmp_path / "price_filter_counterfactual_log_only.jsonl"
    monkeypatch.setattr(bot, "PRICE_FILTER_COUNTERFACTUAL_FILE", str(target))
    calls = []

    def fake_estimate(forecast_max, threshold_c, condition, days_ahead, threshold_high_c=None, city=None):
        calls.append((forecast_max, threshold_c, condition, city))
        return 0.0

    monkeypatch.setattr(bot, "estimate_prob_with_city", fake_estimate)
    pending = [
        {
            "city": "Toronto",
            "city_mode": "active",
            "date_iso": "2026-05-27",
            "days_ahead": 1,
            "condition": "exact",
            "threshold": 28,
            "threshold_high": None,
            "unit": "C",
            "question": "Will Toronto be 28C?",
            "mkt_prob_yes": 0.05,
            "mkt_prob_no": 0.95,
            "market_id": "m1",
            "condition_id": "c1",
            "market_slug": "toronto-28c",
            "token_id_yes": "yes",
            "token_id_no": "no",
        },
        {
            "city": "Shadowtown",
            "city_mode": "shadow",
            "date_iso": "2026-05-27",
            "condition": "at_or_above",
            "threshold": 30,
            "unit": "C",
            "mkt_prob_yes": 0.05,
            "mkt_prob_no": 0.95,
        },
    ]

    rows = bot._build_price_filter_counterfactual_records(
        pending,
        cycle_id="2026-05-26T20:00",
        forecast_cache={"Toronto": {"2026-05-27": {"temp_max": 25.0}}},
        trader_signals={},
    )

    assert len(rows) == 1
    row = rows[0]
    assert calls == [(25.0, 28, "exact", "Toronto")]
    assert row["uses_new_external_forecast_calls"] is False
    assert row["condition_id"] == "c1"
    assert row["market_id"] == "m1"
    assert row["price_yes"] == 0.05
    assert row["price_no"] == 0.95
    assert row["side"] == "NO"
    assert row["counterfactual_status"] == "excluded_protected_exact_no"
    assert row["candidate_allowed"] is False
    assert row["candidate_exclusion_reason"] == "EXACT_NO_REMAINS_SHADOW_PROTECTED"


def test_price_filter_counterfactual_respects_cap_and_cache_miss(monkeypatch):
    monkeypatch.setattr(bot, "estimate_prob_with_city", lambda *args, **kwargs: 0.9)
    pending = [
        {
            "city": f"City{idx}",
            "city_mode": "canary",
            "date_iso": "2026-05-27",
            "days_ahead": 1,
            "condition": "at_or_above",
            "threshold": 30 + idx,
            "unit": "C",
            "mkt_prob_yes": 0.05,
            "mkt_prob_no": 0.95,
        }
        for idx in range(3)
    ]

    rows = bot._build_price_filter_counterfactual_records(
        pending,
        cycle_id="2026-05-26T20:00",
        forecast_cache={},
        max_records=2,
    )

    assert len(rows) == 2
    assert {row["counterfactual_status"] for row in rows} == {"forecast_not_in_existing_cycle_cache"}
    assert all(row["candidate_allowed"] is False for row in rows)


# ── Forward capture: candidate_side_source + eligible_for_policy_evaluation ──

def test_record_bot_evaluation_explicit_side_sets_runtime_source(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)

    bot.record_bot_evaluation(
        "2026-05-29T08:00",
        "Paris|2026-05-30|at_or_above|25|C",
        False,
        city="Paris",
        date_iso="2026-05-30",
        condition="at_or_above",
        side="YES",
        city_mode="canary",
        threshold=25,
        unit="C",
        our_prob=62.0,
        mkt_prob=55.0,
        decision_gate="fuera_allowlist",
    )

    row = json.loads(target.read_text(encoding="utf-8").strip())
    assert row["side"] == "YES"
    assert row["candidate_side_source"] == "runtime_evaluation_explicit"
    assert row["eligible_for_policy_evaluation"] is False


def test_record_bot_evaluation_no_side_sets_not_captured(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)

    bot.record_bot_evaluation(
        "2026-05-29T08:00",
        "Oslo|2026-05-30|at_or_above|15|C",
        False,
        city="Oslo",
        date_iso="2026-05-30",
        condition="at_or_above",
        city_mode="shadow",
        threshold=15,
        unit="C",
        our_prob=48.0,
        mkt_prob=50.0,
    )

    row = json.loads(target.read_text(encoding="utf-8").strip())
    assert row["side"] is None
    assert row["candidate_side_source"] == "not_captured_v2"
    assert row["eligible_for_policy_evaluation"] is False


def test_record_bot_evaluation_eligible_for_policy_evaluation_always_false(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)

    for side_val in ("YES", "NO", None):
        target.unlink(missing_ok=True)
        bot.record_bot_evaluation(
            "2026-05-29T08:00",
            f"Berlin|2026-05-30|at_or_above|20|C",
            True,
            city="Berlin",
            date_iso="2026-05-30",
            condition="at_or_above",
            side=side_val,
            threshold=20,
            unit="C",
        )
        row = json.loads(target.read_text(encoding="utf-8").strip())
        assert row["eligible_for_policy_evaluation"] is False


def test_record_bot_evaluation_our_prob_mkt_prob_decision_gate_provenance_preserved(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)

    bot.record_bot_evaluation(
        "2026-05-29T08:00",
        "Tokyo|2026-05-30|at_or_below|30|C",
        False,
        city="Tokyo",
        date_iso="2026-05-30",
        condition="at_or_below",
        side="NO",
        threshold=30,
        unit="C",
        our_prob=71.5,
        mkt_prob=63.2,
        decision_gate="sl_intra_guard",
        evaluation_source="live_eval",
    )

    row = json.loads(target.read_text(encoding="utf-8").strip())
    assert row["our_prob"] == 71.5
    assert row["mkt_prob"] == 63.2
    assert row["decision_gate"] == "sl_intra_guard"
    assert row["evaluation_source"] == "live_eval"
    assert row["candidate_side_source"] == "runtime_evaluation_explicit"


def test_record_bot_evaluation_would_buy_not_altered_by_capture(monkeypatch, tmp_path):
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)

    for would_buy_val in (True, False):
        target.unlink(missing_ok=True)
        bot.record_bot_evaluation(
            "2026-05-29T08:00",
            "Sydney|2026-05-30|at_or_above|22|C",
            would_buy_val,
            city="Sydney",
            date_iso="2026-05-30",
            condition="at_or_above",
            side="YES",
            threshold=22,
            unit="C",
        )
        row = json.loads(target.read_text(encoding="utf-8").strip())
        assert row["would_buy"] is would_buy_val
        assert row["candidate_side_source"] == "runtime_evaluation_explicit"


def test_record_bot_evaluation_schema_backward_compatible(monkeypatch, tmp_path):
    """Legacy v1 row shape still readable; new fields absent on old rows don't crash engine."""
    target = tmp_path / "bot_signal_evaluations.jsonl"
    monkeypatch.setattr(bot, "BOT_SIGNAL_EVALUATIONS_FILE", str(target))
    monkeypatch.delenv("DISABLE_BOT_EVAL_CAPTURE", raising=False)

    bot.record_bot_evaluation(
        "2026-05-29T08:00",
        "London|2026-05-30|at_or_above|18|C",
        False,
        city="London",
        date_iso="2026-05-30",
        condition="at_or_above",
        side="YES",
        threshold=18,
        unit="C",
    )

    row = json.loads(target.read_text(encoding="utf-8").strip())
    assert row["schema_version"] == 2
    assert "candidate_side_source" in row
    assert "eligible_for_policy_evaluation" in row
    assert row["eval_key"] == "London|2026-05-30|at_or_above|18|C"
