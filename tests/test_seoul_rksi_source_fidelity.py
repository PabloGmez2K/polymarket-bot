from __future__ import annotations

from datetime import date, timedelta

import bot


def test_seoul_settlement_and_forecast_station_are_aligned_to_rksi():
    resolution = bot.RESOLUTION_ICAO["Seoul"]
    station = bot.RESOLUTION_STATIONS["Seoul"]

    assert resolution["icao"] == "RKSI"
    assert "RKSI" in station["name"]
    assert "Incheon" in station["name"]
    assert "KMA" not in station["name"]
    assert station["lat"] == 37.4602
    assert station["lon"] == 126.4407
    assert (station["lat"], station["lon"]) != (37.5665, 126.9780)


def test_recompute_position_edge_fetches_seoul_forecast_from_rksi_station(monkeypatch):
    target_date = date.today() + timedelta(days=1)
    date_iso = target_date.isoformat()
    calls = []

    monkeypatch.setattr(
        bot,
        "parse_temperature_question",
        lambda _title: {
            "city": "Seoul",
            "date_str": "tomorrow",
            "temp_threshold": 25,
            "temp_threshold_high": None,
            "condition": "at_or_above",
            "unit": "C",
        },
    )
    monkeypatch.setattr(bot, "date_text_to_iso", lambda _date_str: date_iso)

    def fake_get_forecast(lat, lon):
        calls.append((lat, lon))
        return {date_iso: {"temp_max": 24.0}}

    monkeypatch.setattr(bot, "get_forecast", fake_get_forecast)
    monkeypatch.setattr(bot, "estimate_prob_with_city", lambda *args, **kwargs: 0.40)

    fresh = bot.recompute_position_edge(
        {
            "title": "Will the highest temperature in Seoul be 25C or higher tomorrow?",
            "outcome": "NO",
            "curPrice": 0.30,
        },
        forecast_cache={},
    )

    station = bot.RESOLUTION_STATIONS["Seoul"]
    assert calls == [(station["lat"], station["lon"])]
    assert fresh is not None
    assert fresh["city"] == "Seoul"
    assert fresh["forecast_max"] == 24.0


def test_seoul_pre_edge_source_metadata_would_report_rksi_if_reenabled():
    station = bot.RESOLUTION_STATIONS["Seoul"]
    resolution = bot.RESOLUTION_ICAO["Seoul"]

    assert station["name"] == "Incheon Intl (RKSI)"
    assert resolution["icao"] == "RKSI"
