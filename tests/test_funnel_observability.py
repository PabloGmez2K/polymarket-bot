from __future__ import annotations

import builtins
import json

import bot


def test_count_discovered_markets_unique_prefers_stable_ids_and_dedupes():
    markets = [
        {
            "conditionId": "cond-1",
            "id": "market-a",
            "slug": "slug-a",
            "question": "Will the highest temperature in Milan be 28C on May 21?",
        },
        {
            "condition_id": "cond-1",
            "id": "market-a-duplicate",
            "question": "Will the highest temperature in Milan be 28C on May 21?",
        },
        {
            "id": "market-b",
            "slug": "slug-b",
            "question": "Will the highest temperature in Seoul be 27C on May 21?",
        },
        {
            "slug": "slug-c",
            "question": "Will the highest temperature in Hong Kong be 31C on May 21?",
        },
    ]

    assert bot.count_discovered_markets_unique(markets) == 3


def test_count_discovered_markets_unique_fallback_uses_market_shape_not_token_side():
    markets = [
        {"question": "Will the highest temperature in Milan be 28C on May 21?"},
        {"question": "Will the highest temperature in Milan be 28C on May 21?"},
        {"question": "Will the highest temperature in Milan be 29C on May 21?"},
    ]

    assert bot.count_discovered_markets_unique(markets) == 2


def test_build_funnel_observability_record_maps_cycle_counters():
    cycle_data = {
        "version": "v10.6.99",
        "logic_series": "10.6",
        "cycle_number": 400,
        "logic_cycle_number": 12,
        "timestamp_utc": "2026-05-21T12:00:00+00:00",
        "mode": "REAL",
        "scan": {
            "markets_evaluated": 22,
            "with_edge": 2,
            "selected": 1,
            "shadow": 4,
            "condition_filtered": 11,
            "city_window_skipped": 154,
            "slot_metrics": {
                "reject_reasons": {
                    "price_out_of_range": 121,
                    "date_out_of_range_past": 33,
                    "date_out_of_range_future": 1,
                    "condition_filtered": 11,
                    "fuera_allowlist": 3,
                    "blocked_city": 1,
                    "shadow_only_override": 2,
                    "buy_min_size": 4,
                },
                "execution_reject_reasons": {"buy_min_size": 4},
            },
        },
        "buys": [{"city": "Milan"}],
    }

    record = bot.build_funnel_observability_record(cycle_data, discovered_markets_unique=330)

    assert record["log_only"] is True
    assert record["trading_authorization"] == "NO_ACTION"
    assert record["discovered_markets_unique"] == 330
    assert record["baseline_partial"] is False
    assert record["prefiltered"] == 22
    assert record["markets_evaluated"] == 22
    assert record["city_window_skipped"] == 154
    assert record["price_out_of_range"] == 121
    assert record["date_out_of_range"] == {"past": 33, "future": 1}
    assert record["condition_filtered"] == 11
    assert record["policy_source_blocked"] == {
        "fuera_allowlist": 3,
        "blocked_city": 1,
        "settlement_risk": 0,
        "shadow_only_mode": 2,
        "total": 6,
    }
    assert record["edge"] == 2
    assert record["shadow_edge"] == 4
    assert record["selected"] == 1
    assert record["real_buy"] == 1
    assert record["execution_rejects"] == {"buy_min_size": 4}


def test_build_funnel_observability_record_marks_partial_when_discovered_unknown():
    record = bot.build_funnel_observability_record({"scan": {}}, discovered_markets_unique=None)

    assert record["discovered_markets_unique"] is None
    assert record["baseline_partial"] is True


def test_write_funnel_observability_writes_jsonl_and_latest(tmp_path):
    jsonl_path = tmp_path / "funnel_observability_log_only.jsonl"
    latest_path = tmp_path / "funnel_observability_latest.json"
    record = {
        "schema_version": 1,
        "log_only": True,
        "trading_authorization": "NO_ACTION",
        "cycle_number": 400,
    }

    ok = bot.write_funnel_observability_log_only(
        record,
        jsonl_path=str(jsonl_path),
        latest_path=str(latest_path),
    )

    assert ok is True
    assert json.loads(jsonl_path.read_text(encoding="utf-8").strip()) == record
    assert json.loads(latest_path.read_text(encoding="utf-8")) == record


def test_write_funnel_observability_is_no_throw_on_io_error(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(builtins, "open", boom)

    ok = bot.write_funnel_observability_log_only({
        "schema_version": 1,
        "log_only": True,
        "trading_authorization": "NO_ACTION",
    })

    assert ok is False
