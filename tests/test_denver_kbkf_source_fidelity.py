from __future__ import annotations

from datetime import date, timedelta

import bot


def test_denver_settlement_and_forecast_station_are_aligned_to_kbkf():
    resolution = bot.RESOLUTION_ICAO["Denver"]
    station = bot.RESOLUTION_STATIONS["Denver"]

    assert resolution["icao"] == "KBKF"
    assert resolution["wu_url"] == bot._wu_history_url("KBKF")
    assert station["name"] == "Buckley Space Force Base (KBKF)"
    assert station["lat"] == 39.701761
    assert station["lon"] == -104.751961
    assert (station["lat"], station["lon"]) != (39.7392, -104.9903)
    assert "noaa_station_id" not in resolution
    assert "noaa_daily_station_id" not in resolution
    assert "Denver" not in bot.OBSERVED_AUDIT_CITIES


def test_recompute_position_edge_fetches_denver_forecast_from_kbkf_station(monkeypatch):
    target_date = date.today() + timedelta(days=1)
    date_iso = target_date.isoformat()
    calls = []

    monkeypatch.setattr(
        bot,
        "parse_temperature_question",
        lambda _title: {
            "city": "Denver",
            "date_str": "tomorrow",
            "temp_threshold": 74,
            "temp_threshold_high": None,
            "condition": "at_or_above",
            "unit": "F",
        },
    )
    monkeypatch.setattr(bot, "date_text_to_iso", lambda _date_str: date_iso)
    monkeypatch.setattr(
        bot,
        "get_coordinates_fallback",
        lambda city: (_ for _ in ()).throw(AssertionError(f"unexpected fallback for {city}")),
    )

    def fake_get_forecast(lat, lon):
        calls.append((lat, lon))
        return {date_iso: {"temp_max": 24.0}}

    monkeypatch.setattr(bot, "get_forecast", fake_get_forecast)
    monkeypatch.setattr(bot, "estimate_prob_with_city", lambda *args, **kwargs: 0.70)

    fresh = bot.recompute_position_edge(
        {
            "title": "Will the highest temperature in Denver be 74F or higher tomorrow?",
            "outcome": "YES",
            "curPrice": 0.30,
        },
        forecast_cache={},
    )

    station = bot.RESOLUTION_STATIONS["Denver"]
    assert calls == [(station["lat"], station["lon"])]
    assert fresh is not None
    assert fresh["city"] == "Denver"
    assert fresh["forecast_max"] == 24.0


def test_denver_remains_shadow_only_after_source_alignment():
    policy_state = {
        "auto_canary_cities": {},
        "auto_canary_from_active": {},
        "auto_shadow_cities": {},
        "auto_blocked_cities": {},
        "transition_history": [],
    }

    assert "Denver" not in bot.ACTIVE_TRADING_CITIES
    assert "Denver" not in bot.CANARY_TRADING_CITIES
    assert bot.get_effective_city_mode("Denver", policy_state=policy_state) == "shadow"
    assert bot.EXACT_NO_GLOBAL_SHADOW_ID == "SHADOW_EXACT_NO_GLOBAL"
    assert bot.WELLINGTON_EXACT_NO_PAUSE_ID == "PAUSE_WELLINGTON_EXACT_NO"
