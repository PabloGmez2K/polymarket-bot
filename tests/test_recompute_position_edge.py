from __future__ import annotations

import json
from datetime import date, timedelta

import bot


def _future_market_date() -> tuple[str, str]:
    target = date.today() + timedelta(days=1)
    return target.isoformat(), f"{target.strftime('%B')} {target.day}"


def _temperature_position(side: str, cur_price: float) -> dict:
    return {
        "title": "Will the highest temperature in Shanghai be 29C or higher tomorrow?",
        "outcome": side,
        "curPrice": cur_price,
        "currentValue": 2.0,
        "percentPnl": 0.0,
        "cashPnl": 0.0,
        "size": 10.0,
        "avgPrice": 0.20,
        "initialValue": 2.0,
        "asset": f"{side.lower()}-token",
    }


def _forecast_cache(temp_max: float = 28.5) -> dict:
    date_iso, _ = _future_market_date()
    return {"Shanghai": {date_iso: {"temp_max": temp_max}}}


def _patch_question_parsing(monkeypatch):
    date_iso, _ = _future_market_date()
    monkeypatch.setattr(
        bot,
        "parse_temperature_question",
        lambda _title: {
            "city": "Shanghai",
            "date_str": "tomorrow",
            "temp_threshold": 29,
            "temp_threshold_high": None,
            "condition": "at_or_above",
            "unit": "C",
        },
    )
    monkeypatch.setattr(bot, "date_text_to_iso", lambda _date_str: date_iso)


def test_recompute_position_edge_no_uses_no_token_cur_price(monkeypatch):
    _patch_question_parsing(monkeypatch)
    monkeypatch.setattr(bot, "estimate_prob_with_city", lambda *args, **kwargs: 0.50)

    fresh = bot.recompute_position_edge(_temperature_position("NO", 0.20), _forecast_cache())

    assert fresh is not None
    assert fresh["our_prob"] == 0.50
    assert fresh["mkt_price"] == 0.20
    assert round(fresh["edge_pct"], 1) == 30.0


def test_recompute_position_edge_yes_still_uses_yes_token_cur_price(monkeypatch):
    _patch_question_parsing(monkeypatch)
    monkeypatch.setattr(bot, "estimate_prob_with_city", lambda *args, **kwargs: 0.50)

    fresh = bot.recompute_position_edge(_temperature_position("YES", 0.20), _forecast_cache())

    assert fresh is not None
    assert fresh["our_prob"] == 0.50
    assert fresh["mkt_price"] == 0.20
    assert round(fresh["edge_pct"], 1) == 30.0


def test_manage_positions_keeps_no_when_reeval_edge_remains_positive(monkeypatch):
    class _Response:
        def read(self):
            return json.dumps([_temperature_position("NO", 0.20)]).encode("utf-8")

    monkeypatch.setenv("FUNDER", "0xabc")
    _patch_question_parsing(monkeypatch)
    monkeypatch.setattr(bot.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    monkeypatch.setattr(bot, "record_trade_lifecycle_position_snapshots", lambda *args, **kwargs: None)
    monkeypatch.setattr(bot, "load_trade_lifecycle_data", lambda: {"records": []})
    monkeypatch.setattr(bot, "get_forecast", lambda *args, **kwargs: _forecast_cache()["Shanghai"])
    monkeypatch.setattr(bot, "estimate_prob_with_city", lambda *args, **kwargs: 0.50)

    dl = []
    result = bot.manage_positions(client=None, dl=dl)

    assert result["n_sold"] == 0
    assert result["sells"] == []
    assert result["kept"] == 1
    assert not any("RE-EVAL" in line for line in dl)
