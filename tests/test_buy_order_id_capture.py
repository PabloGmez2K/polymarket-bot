"""
Focal static-analysis tests for R1B_BUY_ORDER_ID_CAPTURE_LOG_ONLY.

These tests parse bot.py source (AST) so they fail if the patch is
reverted — unlike stub-based tests that always pass regardless.
"""
import ast
from pathlib import Path

BOT_PY = Path(__file__).parent.parent / "bot.py"


def _parse_bot():
    return ast.parse(BOT_PY.read_text(encoding="utf-8"), filename="bot.py")


def _find_track_trade_buy_calls(tree):
    """Return all AST Call nodes matching track_trade("BUY", ...)."""
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "track_trade"):
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and first.value == "BUY":
            calls.append(node)
    return calls


def _keyword_names(call):
    return {kw.arg for kw in call.keywords}


def _is_result_get_order_id(node):
    """True iff node is exactly result.get("order_id")."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "get"):
        return False
    if not (isinstance(func.value, ast.Name) and func.value.id == "result"):
        return False
    if len(node.args) != 1:
        return False
    arg = node.args[0]
    return isinstance(arg, ast.Constant) and arg.value == "order_id"


# ---------------------------------------------------------------------------
# Test 1 — BUY track_trade call passes order_id=result.get("order_id")
# ---------------------------------------------------------------------------

def test_buy_track_trade_call_includes_order_id_from_result_get():
    """
    At least one track_trade("BUY", ...) in bot.py must pass
    order_id=result.get("order_id") as a keyword argument.
    Fails if the patch is reverted or the value expression changes.
    """
    tree = _parse_bot()
    buy_calls = _find_track_trade_buy_calls(tree)
    assert buy_calls, "No track_trade('BUY', ...) call found in bot.py"

    matched = [
        c for c in buy_calls
        for kw in c.keywords
        if kw.arg == "order_id" and _is_result_get_order_id(kw.value)
    ]

    assert matched, (
        "No track_trade('BUY', ...) call passes order_id=result.get('order_id'). "
        f"Found {len(buy_calls)} BUY call(s) with keyword sets: "
        f"{[sorted(_keyword_names(c)) for c in buy_calls]}"
    )


# ---------------------------------------------------------------------------
# Test 2 — No BUY track_trade call is missing order_id
# ---------------------------------------------------------------------------

def test_no_buy_track_trade_call_without_order_id():
    """
    Every track_trade("BUY", ...) in bot.py must include the order_id keyword.
    A missing kwarg would silently omit the field for that execution path.
    """
    tree = _parse_bot()
    buy_calls = _find_track_trade_buy_calls(tree)
    assert buy_calls, "No track_trade('BUY', ...) call found in bot.py"

    missing = [c for c in buy_calls if "order_id" not in _keyword_names(c)]
    assert not missing, (
        f"{len(missing)} track_trade('BUY', ...) call(s) lack order_id "
        f"(line(s): {[c.lineno for c in missing]})"
    )


# ---------------------------------------------------------------------------
# Test 3 — execute_trade() includes order_id in every dict return
# ---------------------------------------------------------------------------

def test_execute_trade_returns_order_id_field_static():
    """
    Every dict-literal Return inside execute_trade() must contain 'order_id'.
    Covers dry_run, success, and error paths.
    """
    tree = _parse_bot()

    func_node = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "execute_trade"),
        None,
    )
    assert func_node is not None, "execute_trade() not found in bot.py"

    dict_returns = [
        node.value
        for node in ast.walk(func_node)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
    ]
    assert dict_returns, "No dict return statements found in execute_trade()"

    for ret in dict_returns:
        keys = {
            k.value if isinstance(k, ast.Constant) else None
            for k in ret.keys
        }
        assert "order_id" in keys, (
            f"A return dict in execute_trade() lacks 'order_id'. Keys: {keys}"
        )


# ---------------------------------------------------------------------------
# Test 4 — SELL order_id persistence is still present
# ---------------------------------------------------------------------------

def test_sell_track_trade_order_id_paths_still_present_static():
    """
    At least one track_trade("SELL_PENDING"|"SELL"|"SELL_FAILED", ...)
    must still pass order_id as a keyword (regression guard for SELL path).
    """
    tree = _parse_bot()

    sell_with_order_id = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "track_trade"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value in {"SELL", "SELL_PENDING", "SELL_FAILED"}
        and "order_id" in _keyword_names(node)
    ]

    assert sell_with_order_id, (
        "No SELL/SELL_PENDING/SELL_FAILED track_trade call with order_id "
        "found in bot.py — SELL path order_id persistence may be broken."
    )
