import ast
from pathlib import Path


BOT_PATH = Path(__file__).resolve().parents[1] / "bot.py"


def _function_source(name: str) -> str:
    code = BOT_PATH.read_text(encoding="utf-8")
    module = ast.parse(code)
    lines = code.splitlines()
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"function not found: {name}")


def _policy_namespace(blocked=None, active=None, canary=None, auto_canary=None):
    ns = {
        "BLOCKED_CITIES": {c.lower() for c in (blocked or [])},
        "ACTIVE_TRADING_CITIES": set(active or []),
        "CANARY_TRADING_CITIES": set(canary or []),
        "OBSERVED_AUDIT_CITIES": {"Paris", "London", "Atlanta", "Chicago", "Munich", "Seoul"},
        "RESOLUTION_ICAO": {
            "Paris": {"noaa_station_id": "07157099999", "noaa_daily_station_id": "FRM00007149"},
            "London": {"noaa_station_id": "03768399999", "noaa_daily_station_id": "UKE00107650"},
            "Atlanta": {"noaa_station_id": "72219013874", "noaa_daily_station_id": "USW00013874"},
            "Chicago": {"noaa_station_id": "72530094846", "noaa_daily_station_id": "USW00094846"},
            "Munich": {"noaa_station_id": "10866099999", "noaa_daily_station_id": "GMM00010870"},
            "Seoul": {"noaa_station_id": "47113199999", "noaa_daily_station_id": "KS000047112"},
            "No Proxy": {"icao": "XXXX"},
        },
        "load_city_policy_state": lambda: {
            "auto_blocked_cities": {},
            "auto_shadow_cities": {},
            "auto_canary_cities": auto_canary or {},
            "auto_canary_from_active": {},
        },
        "_normalize_city_policy_state": lambda state: state,
    }
    for fn in ("is_city_blocked", "_city_has_observed_proxy", "should_skip_observation", "_city_requires_manual_proxy_canary_review", "get_effective_city_mode"):
        exec(_function_source(fn), ns)
    return ns


def test_blocked_cities_hard_block_even_with_noaa_proxy():
    ns = _policy_namespace(
        blocked={"Paris", "London", "Atlanta", "Chicago"},
        active={"Atlanta", "Chicago"},
        canary={"Paris", "London"},
        auto_canary={"Paris": {}, "London": {}, "Atlanta": {}, "Chicago": {}},
    )

    for city in ("Paris", "London", "Atlanta", "Chicago"):
        assert ns["is_city_blocked"](city) is True
        assert ns["get_effective_city_mode"](city) == "blocked"


def test_blocked_cities_with_proxy_still_allow_observation_path():
    ns = _policy_namespace(blocked={"Paris", "London", "Atlanta", "Chicago", "No Proxy"})

    for city in ("Paris", "London", "Atlanta", "Chicago"):
        assert ns["_city_has_observed_proxy"](city) is True
        assert ns["should_skip_observation"](city) is False

    assert ns["is_city_blocked"]("No Proxy") is True
    assert ns["should_skip_observation"]("No Proxy") is True


def test_canary_cities_remain_permitted_when_not_blocked():
    ns = _policy_namespace(
        blocked={"Paris", "London", "Atlanta", "Chicago"},
        canary={"Munich", "Seoul"},
        auto_canary={"Munich": {}, "Seoul": {}},
    )

    assert ns["is_city_blocked"]("Munich") is False
    assert ns["is_city_blocked"]("Seoul") is False
    assert ns["get_effective_city_mode"]("Munich") == "canary"
    assert ns["get_effective_city_mode"]("Seoul") == "canary"


def test_admission_paths_use_hard_block_and_observation_split():
    code = BOT_PATH.read_text(encoding="utf-8")
    assert "if should_skip_observation(city):" in code
    assert "and not is_city_blocked(city)" in code
    assert "c[\"exact_range_canary\"] = True" in code
    assert "if not c.get(\"allowlisted\", True):" in code
