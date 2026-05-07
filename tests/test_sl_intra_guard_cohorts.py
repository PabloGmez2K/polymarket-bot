import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_cohort_helper():
    source = (ROOT / "bot.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    helper = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_sl_intra_guard_cohort_fields":
            helper = node
            break
    assert helper is not None
    ns = {
        "SL_INTRA_GUARD_COHORT_SCHEMA_VERSION": "sl_intra_guard_cohort_v1",
        "SL_INTRA_GUARD_CATCHABLE_THRESHOLD_PCT": -35.0,
        "SL_INTRA_GUARD_DEEP_DRAWDOWN_LOW_PCT": -75.0,
        "SL_INTRA_GUARD_DEEP_DRAWDOWN_HIGH_PCT": -35.0,
    }
    exec(compile(ast.Module(body=[helper], type_ignores=[]), "bot.py", "exec"), ns)
    return ns["_sl_intra_guard_cohort_fields"]


def test_sl_intra_guard_cohort_boundaries():
    classify = _load_cohort_helper()

    zone_a = classify(-29.6)
    assert zone_a["cohort"] == "zone_a"
    assert zone_a["sl_window_catchable"] is True
    assert zone_a["deep_drawdown_at_skip"] is False

    zone_b = classify(-65.8)
    assert zone_b["cohort"] == "zone_b"
    assert zone_b["sl_window_catchable"] is False
    assert zone_b["deep_drawdown_at_skip"] is True

    zone_c = classify(-92.0)
    assert zone_c["cohort"] == "zone_c"
    assert zone_c["sl_window_catchable"] is False
    assert zone_c["deep_drawdown_at_skip"] is False


def test_sl_intra_guard_cohort_threshold_edges_and_unknown():
    classify = _load_cohort_helper()

    assert classify(-34.999)["cohort"] == "zone_a"
    assert classify(-35.0)["cohort"] == "zone_b"
    assert classify(-74.999)["cohort"] == "zone_b"
    assert classify(-75.0)["cohort"] == "zone_c"

    missing = classify(None)
    assert missing["cohort"] == "unknown"
    assert missing["sl_window_catchable"] is None
    assert missing["deep_drawdown_at_skip"] is None

    invalid = classify("not-a-number")
    assert invalid["cohort"] == "unknown"
    assert invalid["cohort_schema_version"] == "sl_intra_guard_cohort_v1"
