from __future__ import annotations

import json
from datetime import datetime, timezone

import bot


def _city_stat(
    *,
    allowed: int,
    consensus: int,
    consensus_traders: set[str] | None = None,
):
    return {
        "allowed": allowed,
        "consensus": consensus,
        "consensus_operable_traders": consensus_traders or {"t1"},
    }


def test_san_francisco_mapping_missing_is_watch_source_not_action():
    detail = bot._classify_trader_gap_city_severity(
        "San Francisco",
        _city_stat(allowed=2, consensus=2, consensus_traders={"t1"}),
        {
            "primary_status": "MAPPING_MISSING",
            "mapping_status": "MAPPING_MISSING",
            "source_feasibility": "no_icao",
        },
        {"cycles_seen": 1, "markets_seen": 3, "edge_hits": 0},
        [],
        now=datetime(2026, 5, 21, tzinfo=timezone.utc),
        city_mode="shadow",
        is_blocked=False,
        observed_audit_cities=set(),
    )

    assert detail["severity"] == "WATCH_SOURCE"
    assert detail["source_status"] == "MAPPING_MISSING/no_icao"
    assert detail["operable_signal_count"] == 2
    assert detail["markets_seen"] == 3
    assert detail["edge_hits"] == 0
    assert detail["gate_passed"] is False


def test_mapping_missing_hard_rule_blocks_action_even_when_gates_pass():
    previous = [
        {
            "run_at": "2026-05-19T08:00:00+00:00",
            "operational_trader_only_cities": ["San Francisco"],
        },
        {
            "run_at": "2026-05-20T08:00:00+00:00",
            "operational_trader_only_cities": ["San Francisco"],
        },
    ]

    detail = bot._classify_trader_gap_city_severity(
        "San Francisco",
        _city_stat(allowed=6, consensus=6, consensus_traders={"t1", "t2"}),
        {"mapping_status": "MAPPING_MISSING", "source_feasibility": "no_icao"},
        {"cycles_seen": 5, "markets_seen": 20, "edge_hits": 2},
        previous,
        now=datetime(2026, 5, 21, tzinfo=timezone.utc),
        city_mode="active",
        is_blocked=False,
        observed_audit_cities={"San Francisco"},
    )

    assert detail["gate_passed"] is True
    assert detail["severity"] == "WATCH_SOURCE"


def test_action_when_mapping_ready_gates_pass_and_city_context_allows_action():
    previous = [
        {
            "run_at": "2026-05-19T08:00:00+00:00",
            "operational_trader_only_cities": ["Chicago"],
        },
        {
            "run_at": "2026-05-20T08:00:00+00:00",
            "operational_trader_only_cities": ["Chicago"],
        },
    ]

    detail = bot._classify_trader_gap_city_severity(
        "Chicago",
        _city_stat(allowed=5, consensus=5, consensus_traders={"t1", "t2"}),
        {"mapping_status": "MAPPING_FULL", "primary_status": "READY_FOR_SOURCE_AUDIT"},
        {"cycles_seen": 5, "markets_seen": 20, "edge_hits": 1},
        previous,
        now=datetime(2026, 5, 21, tzinfo=timezone.utc),
        city_mode="active",
        is_blocked=False,
        observed_audit_cities=set(),
    )

    assert detail["gate_passed"] is True
    assert detail["severity"] == "ACTION"


def test_daily_crosscheck_message_reports_san_francisco_watch_source(monkeypatch, tmp_path):
    signals_file = tmp_path / "signals.json"
    shadow_file = tmp_path / "shadow_city_tracking.json"
    source_file = tmp_path / "source_onboarding.json"
    crosscheck_file = tmp_path / "signals_crosscheck.jsonl"

    signals_file.write_text(
        json.dumps(
            {
                "generated": "2026-05-21T08:00:00+00:00",
                "signals": [
                    {
                        "city": "San Francisco",
                        "condition": "at_or_above",
                        "date": "2026-05-21",
                        "trader": "t1",
                        "has_consensus": True,
                        "trader_win_rate": 80,
                    },
                    {
                        "city": "San Francisco",
                        "condition": "at_or_below",
                        "date": "2026-05-21",
                        "trader": "t2",
                        "has_consensus": True,
                        "trader_win_rate": 78,
                    },
                    {
                        "city": "San Francisco",
                        "condition": "range",
                        "date": "2026-05-21",
                        "trader": "t3",
                        "has_consensus": True,
                        "trader_win_rate": 75,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    shadow_file.write_text(
        json.dumps(
            {
                "updated_at": "2026-05-21T08:00:00+00:00",
                "cities": {
                    "San Francisco": {
                        "cycles_seen": 1,
                        "markets_seen": 3,
                        "edge_hits": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    source_file.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "city": "San Francisco",
                        "primary_status": "MAPPING_MISSING",
                        "mapping_status": "MAPPING_MISSING",
                        "source_feasibility": "no_icao",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    sent_messages = []
    monkeypatch.setattr(bot, "SIGNALS_FILE", str(signals_file))
    monkeypatch.setattr(bot, "SHADOW_TRACKING_FILE", str(shadow_file))
    monkeypatch.setattr(bot, "SOURCE_ONBOARDING_FILE", str(source_file))
    monkeypatch.setattr(bot, "SIGNALS_CROSSCHECK_FILE", str(crosscheck_file))
    monkeypatch.setattr(bot, "send_telegram", sent_messages.append)

    state = {}
    ok = bot.maybe_run_daily_crosscheck(
        state,
        now=datetime(2026, 5, 21, 9, 0, tzinfo=timezone.utc),
    )

    assert ok is True
    assert sent_messages
    assert "Nivel: <b>WATCH_SOURCE</b>" in sent_messages[0]
    assert "severity=WATCH_SOURCE" in sent_messages[0]
    assert "source=MAPPING_MISSING/no_icao" in sent_messages[0]

    record = json.loads(crosscheck_file.read_text(encoding="utf-8").strip())
    sf_detail = record["trader_only_severity_details"]["San Francisco"]
    assert sf_detail["severity"] == "WATCH_SOURCE"
    assert sf_detail["operable_signal_count"] == 2
    assert sf_detail["markets_seen"] == 3
    assert sf_detail["edge_hits"] == 0
