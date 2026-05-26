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


def _pause_helper():
    ns = {}
    exec(_function_source("_is_wellington_exact_no_paused"), ns)
    return ns["_is_wellington_exact_no_paused"]


def _global_shadow_helper():
    ns = {
        "EXACT_NO_NEAR_THRESHOLD_C": 1.5,
        "EXACT_NO_NEAR_THRESHOLD_F": 2.7,
    }
    exec(_function_source("_is_exact_no_global_shadowed"), ns)
    return ns["_is_exact_no_global_shadowed"]


def _distance_helper():
    ns = {
        "EXACT_NO_NEAR_THRESHOLD_C": 1.5,
        "EXACT_NO_NEAR_THRESHOLD_F": 2.7,
    }
    exec(_function_source("_exact_no_distance_telemetry"), ns)
    return ns["_exact_no_distance_telemetry"]


def test_wellington_exact_no_is_paused():
    is_paused = _pause_helper()

    assert is_paused("Wellington", "exact", "NO") is True
    assert is_paused(" wellington ", " EXACT ", " no ") is True


def test_pause_scope_does_not_catch_yes_other_conditions_or_cities():
    is_paused = _pause_helper()

    assert is_paused("Wellington", "exact", "YES") is False
    assert is_paused("Wellington", "range", "NO") is False
    assert is_paused("Tokyo", "exact", "NO") is False


def test_exact_no_global_shadow_scope_celsius_near_and_far():
    is_shadowed = _global_shadow_helper()

    assert is_shadowed("exact", "NO", 15.6, 16, "C") is True
    assert is_shadowed(" exact ", " no ", "14.6", "16", "C") is True
    assert is_shadowed("exact", "NO", 14.5, 16, "C") is True


def test_exact_no_global_shadow_scope_fahrenheit_equivalent_near_and_far():
    is_shadowed = _global_shadow_helper()

    assert is_shadowed("exact", "NO", 69.6, 67, "F") is True
    assert is_shadowed("exact", "NO", 69.8, 67, "F") is True


def test_exact_no_global_shadow_does_not_catch_yes_range_or_range_thresholds():
    is_shadowed = _global_shadow_helper()

    assert is_shadowed("exact", "YES", 15.6, 16, "C") is False
    assert is_shadowed("range", "NO", 15.6, 16, "C") is False
    assert is_shadowed("exact", "NO", 15.6, 16, "C", threshold_high=17) is False
    assert is_shadowed("exact", "NO", None, 16, "C") is True
    assert is_shadowed("exact", "NO", "not-a-number", None, "C") is True


def test_exact_no_distance_band_telemetry_is_preserved_when_parseable():
    distance = _distance_helper()

    assert distance(15.6, 16, "C")["distance_band"] == "near_lt_1_5c_equiv"
    assert distance(14.5, 16, "C")["distance_band"] == "far_gte_1_5c_equiv"
    assert distance(69.8, 67, "F")["distance_band"] == "far_gte_1_5c_equiv"
    assert distance("not-a-number", 16, "C") is None


def test_admission_gate_is_traced_before_buy_append():
    code = BOT_PATH.read_text(encoding="utf-8")
    gate = 'if _is_wellington_exact_no_paused(city, condition_name, side):'
    shadow_gate = "if _is_exact_no_global_shadowed("
    trade_append = "trades.append({"

    assert 'WELLINGTON_EXACT_NO_PAUSE_ID = "PAUSE_WELLINGTON_EXACT_NO"' in code
    assert 'EXACT_NO_GLOBAL_SHADOW_ID = "SHADOW_EXACT_NO_GLOBAL"' in code
    assert '"cohort_paused"' in code
    assert gate in code
    assert shadow_gate in code
    assert code.index(gate) < code.index(trade_append)
    assert code.index(gate) < code.index(shadow_gate) < code.index(trade_append)
    assert 'skip_or_block_reason="cohort_paused"' in code
    assert "decision_gate=WELLINGTON_EXACT_NO_PAUSE_ID" in code
    assert 'skip_or_block_reason="shadow_only_override"' in code
    assert "decision_gate=EXACT_NO_GLOBAL_SHADOW_ID" in code
