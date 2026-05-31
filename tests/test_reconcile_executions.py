"""Tests for R1 reconcile_executions engine.

All tests are offline — no API calls, no Railway, no DB, no bot.py.
Fixtures are synthetic; real provenance paths are never used in eligibility tests.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tools._reconcile_engine import (
    SCHEMA_VERSION,
    build_output_rows,
    compute_coverage_summary,
    get_fills_for_entry,
    is_dev_fixture_path,
    is_seoul_pre_patch,
    load_json_file,
    normalize_performance_entries,
    reconcile,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_CLEAN_PROV = {
    "source_path": "/app/data/performance.json",
    "capture_ts": "2026-05-31T12:00:00Z",
    "capture_method": "railway_ssh_cat",
    "sha256": "AABBCCDD",
    "local_path": "/some/clean/path/performance.json",
}

_DEV_PROV = {
    "source_path": "/app/data/performance.json",
    "capture_ts": "2026-05-31T12:00:00Z",
    "capture_method": "railway_ssh_cat",
    "sha256": "AABBCCDD",
    "local_path": "data/runtime_import/performance.json",
}

_FILL_A = {
    "id": "fill-001",
    "price": 0.42,
    "size": 4.2,
    "value": 1.764,
    "timestamp": "1779363524",
    "transaction_hash": "0xabc123",
}

_FILL_B = {
    "id": "fill-002",
    "price": 0.40,
    "size": 2.0,
    "value": 0.80,
    "timestamp": "1779363600",
    "transaction_hash": "0xdef456",
}


def _sell_ctx(order_id="0xAA", city="Madrid", date_iso="2026-05-21",
              condition="exact", fills=None, prov=None, dev=False):
    return {
        "_source": "performance",
        "_dev_fixture": dev,
        "_provenance": prov or _CLEAN_PROV,
        "action": "SELL",
        "order_id": order_id,
        "city": city,
        "date_iso": date_iso,
        "condition": condition,
        "threshold": None,
        "unit": None,
        "side": "No",
        "token_id": "tok_123",
        "market_id": None,
        "condition_id": None,
        "reason": "stop_loss",
        "fill_source": "clob_trades",
        "_embedded_fills": fills or [],
    }


def _buy_ctx(order_id=None, city="Milan", date_iso="2026-05-21",
             prov=None, dev=False):
    return {
        "_source": "performance",
        "_dev_fixture": dev,
        "_provenance": prov or _CLEAN_PROV,
        "action": "BUY",
        "order_id": order_id,
        "city": city,
        "date_iso": date_iso,
        "condition": "exact",
        "threshold": None,
        "unit": None,
        "side": "NO",
        "token_id": "tok_456",
        "market_id": None,
        "condition_id": None,
        "reason": None,
        "fill_source": None,
        "_embedded_fills": [],
    }


# ---------------------------------------------------------------------------
# Test 1: order_id + 1 fill → execution_id = order_id_0000
# ---------------------------------------------------------------------------

def test_single_fill_generates_execution_id_0000():
    ctx = _sell_ctx(order_id="0xORDER1", fills=[_FILL_A])
    rows = build_output_rows(ctx, [_FILL_A])
    assert len(rows) == 1
    assert rows[0]["execution_id"] == "0xORDER1_0000"
    assert rows[0]["fill_index"] == 0
    assert rows[0]["trade_id"] == "fill-001"
    assert rows[0]["order_id"] == "0xORDER1"


# ---------------------------------------------------------------------------
# Test 2: order_id + 2 fills → _0000 and _0001
# ---------------------------------------------------------------------------

def test_two_fills_generate_separate_execution_ids():
    ctx = _sell_ctx(order_id="0xORDER2", fills=[_FILL_A, _FILL_B])
    rows = build_output_rows(ctx, [_FILL_A, _FILL_B])
    assert len(rows) == 2
    assert rows[0]["execution_id"] == "0xORDER2_0000"
    assert rows[1]["execution_id"] == "0xORDER2_0001"
    assert rows[0]["fill_index"] == 0
    assert rows[1]["fill_index"] == 1


# ---------------------------------------------------------------------------
# Test 3: BUY without order_id → missing_fill_identity
# ---------------------------------------------------------------------------

def test_buy_without_order_id_missing_fill_identity():
    ctx = _buy_ctx(order_id=None)
    rows = build_output_rows(ctx, [])
    assert len(rows) == 1
    r = rows[0]
    assert r["needs_reconciliation"] is True
    assert r["reconciliation_blocker"] == "missing_fill_identity"
    assert r["eligible_for_learning"] is False
    assert r["eligible_for_calibration"] is False
    assert r["execution_id"] is None
    assert r["order_id"] is None
    assert r["provenance_class"] == "context_index_only"


# ---------------------------------------------------------------------------
# Test 4: SELL with order_id + CLOB fill → eligible for learning (non-fixture)
# ---------------------------------------------------------------------------

def test_sell_with_clob_fill_eligible_for_learning():
    ctx = _sell_ctx(order_id="0xSELL1", fills=[_FILL_A])
    rows = build_output_rows(ctx, [_FILL_A])
    assert len(rows) == 1
    r = rows[0]
    assert r["needs_reconciliation"] is False
    assert r["reconciliation_blocker"] is None
    assert r["eligible_for_learning"] is True
    assert r["eligible_for_calibration"] is False
    assert r["source_fidelity"] == "confirmed"
    assert r["provenance_class"] == "clob_embedded"


# ---------------------------------------------------------------------------
# Test 5: Seoul pre-patch → source_fidelity=suspect, ineligible
# ---------------------------------------------------------------------------

def test_seoul_pre_patch_suspect_ineligible():
    ctx = _sell_ctx(
        order_id="0xSEOUL1",
        city="Seoul",
        date_iso="2026-05-22",
        fills=[_FILL_A],
    )
    rows = build_output_rows(ctx, [_FILL_A])
    assert len(rows) == 1
    r = rows[0]
    assert r["source_fidelity"] == "suspect"
    assert r["eligible_for_learning"] is False
    assert r["eligible_for_calibration"] is False
    assert r["exclusion_reason"] == "station_mismatch_kma_vs_rksi_pre_patch"
    assert r["provenance_class"] == "clob_embedded_suspect"


# ---------------------------------------------------------------------------
# Test 6: dev_fixture path → provenance_class=dev_fixture, ineligible
# ---------------------------------------------------------------------------

def test_dev_fixture_path_ineligible():
    ctx = _sell_ctx(order_id="0xDEV1", fills=[_FILL_A], prov=_DEV_PROV, dev=True)
    rows = build_output_rows(ctx, [_FILL_A])
    assert len(rows) == 1
    r = rows[0]
    assert r["provenance_class"] == "dev_fixture"
    assert r["eligible_for_learning"] is False
    assert r["eligible_for_calibration"] is False


# ---------------------------------------------------------------------------
# Test 7: market_outcome is always None in R1
# ---------------------------------------------------------------------------

def test_market_outcome_always_null():
    ctx_buy = _buy_ctx(order_id=None)
    ctx_sell = _sell_ctx(order_id="0xX", fills=[_FILL_A])
    for ctx, fills in [(ctx_buy, []), (ctx_sell, [_FILL_A])]:
        rows = build_output_rows(ctx, fills)
        for r in rows:
            assert r["market_outcome"] is None, f"market_outcome must be null in R1"


# ---------------------------------------------------------------------------
# Test 8: no P&L aggregation — pnl_realized stays null
# ---------------------------------------------------------------------------

def test_pnl_realized_null_in_r1():
    ctx = _sell_ctx(order_id="0xPNL1", fills=[_FILL_A])
    rows = build_output_rows(ctx, [_FILL_A])
    assert rows[0]["pnl_realized"] is None
    assert rows[0]["pnl_realized_status"] == "not_computed_buy_unreconciled"


# ---------------------------------------------------------------------------
# Test 9: no heuristic identity — missing order_id cannot build execution_id
# ---------------------------------------------------------------------------

def test_no_heuristic_identity():
    ctx = _buy_ctx(
        order_id=None,
        city="Shanghai",
        date_iso="2026-05-18",
    )
    rows = build_output_rows(ctx, [])
    assert rows[0]["execution_id"] is None
    # Must not construct identity from city/date/side/token_id
    assert rows[0]["reconciliation_blocker"] == "missing_fill_identity"


# ---------------------------------------------------------------------------
# Test 10: missing provenance → ineligible (provenance fields null)
# ---------------------------------------------------------------------------

def test_missing_provenance_produces_null_fields():
    """Provenance is mandatory per R1 design doc.

    When provenance dict is empty, output row must contain the provenance
    fields with null values so downstream validation can detect and reject.
    """
    ctx = {
        "_source": "performance",
        "_dev_fixture": False,
        "_provenance": {},  # explicitly empty — no source_path, no sha256
        "action": "SELL",
        "order_id": "0xNOPROV",
        "city": "Madrid",
        "date_iso": "2026-05-21",
        "condition": "exact",
        "threshold": None,
        "unit": None,
        "side": "No",
        "token_id": "tok_np",
        "market_id": None,
        "condition_id": None,
        "reason": None,
        "fill_source": "clob_trades",
        "_embedded_fills": [_FILL_A],
    }
    rows = build_output_rows(ctx, [_FILL_A])
    r = rows[0]
    # Provenance schema fields must be present (even if null) for downstream rejection
    assert "source_path" in r
    assert "capture_ts" in r
    assert "sha256" in r
    assert "capture_method" in r
    # With empty provenance the values are None — caller/validator must catch this
    assert r["source_path"] is None
    assert r["sha256"] is None


# ---------------------------------------------------------------------------
# Test 11: order_id exists but no fills → needs_reconciliation=True
# ---------------------------------------------------------------------------

def test_order_id_without_fills_needs_reconciliation():
    ctx = _sell_ctx(order_id="0xNOFILL", fills=[])
    rows = build_output_rows(ctx, [])
    assert len(rows) == 1
    r = rows[0]
    assert r["needs_reconciliation"] is True
    assert r["reconciliation_blocker"] == "fill_not_found"
    assert r["eligible_for_learning"] is False
    assert r["execution_id"] is None


# ---------------------------------------------------------------------------
# Test 12: reconcile() end-to-end with synthetic performance data
# ---------------------------------------------------------------------------

def test_reconcile_end_to_end():
    perf_data = [
        {
            "action": "SELL",
            "order_id": "0xSELL_E2E",
            "city": "Madrid",
            "date": "2026-05-21",
            "condition": "exact",
            "side": "No",
            "token_id": "tok_e2e",
            "fill_source": "clob_trades",
            "fill_trades": [_FILL_A],
        },
        {
            "action": "BUY",
            "city": "Milan",
            "date": "2026-05-21",
            "condition": "exact",
            "side": "NO",
            "token_id": "tok_buy_e2e",
        },
        {
            "action": "LOSS_TOTAL",
            "city": "Tokyo",
            "date": "2026-05-20",
        },
    ]
    prov = {
        "performance": {
            **_CLEAN_PROV,
            "local_path": "/clean/performance.json",
        }
    }
    rows = reconcile(
        performance_data=perf_data,
        postmortem_data=None,
        lifecycle_data=None,
        context_provenance=prov,
    )
    # LOSS_TOTAL ignored
    assert len(rows) == 2

    sell_row = next(r for r in rows if r.get("order_id") == "0xSELL_E2E")
    buy_row = next(r for r in rows if r.get("order_id") is None)

    assert sell_row["execution_id"] == "0xSELL_E2E_0000"
    assert sell_row["eligible_for_learning"] is True
    assert sell_row["market_outcome"] is None

    assert buy_row["needs_reconciliation"] is True
    assert buy_row["reconciliation_blocker"] == "missing_fill_identity"


# ---------------------------------------------------------------------------
# Test 13: offline_fills_map overrides embedded fills
# ---------------------------------------------------------------------------

def test_offline_fills_map_overrides_embedded():
    perf_data = [
        {
            "action": "SELL",
            "order_id": "0xOVERRIDE",
            "city": "Wellington",
            "date": "2026-05-22",
            "condition": "exact",
            "side": "No",
            "token_id": "tok_wgt",
            "fill_trades": [_FILL_A],  # embedded fill
        }
    ]
    override_fill = {
        "id": "fill-override",
        "price": 0.50,
        "size": 10.0,
        "value": 5.0,
        "timestamp": "1779999999",
        "transaction_hash": "0xoverride",
    }
    prov = {"performance": {**_CLEAN_PROV, "local_path": "/clean/performance.json"}}
    rows = reconcile(
        performance_data=perf_data,
        postmortem_data=None,
        lifecycle_data=None,
        context_provenance=prov,
        offline_fills_map={"0xOVERRIDE": [override_fill]},
    )
    assert len(rows) == 1
    assert rows[0]["trade_id"] == "fill-override"
    assert rows[0]["price"] == 0.50


# ---------------------------------------------------------------------------
# Test 14: coverage summary correct counts
# ---------------------------------------------------------------------------

def test_coverage_summary():
    rows = [
        {"execution_id": "a_0000", "needs_reconciliation": False,
         "eligible_for_learning": True, "eligible_for_calibration": False,
         "source_fidelity": "confirmed", "provenance_class": "clob_embedded",
         "reconciliation_blocker": None, "order_id": "0xA"},
        {"execution_id": None, "needs_reconciliation": True,
         "eligible_for_learning": False, "eligible_for_calibration": False,
         "source_fidelity": "legacy_observability", "provenance_class": "context_index_only",
         "reconciliation_blocker": "missing_fill_identity", "order_id": None},
        {"execution_id": None, "needs_reconciliation": True,
         "eligible_for_learning": False, "eligible_for_calibration": False,
         "source_fidelity": "confirmed", "provenance_class": "order_id_only",
         "reconciliation_blocker": "fill_not_found", "order_id": "0xB"},
    ]
    s = compute_coverage_summary(rows)
    assert s["total_rows"] == 3
    assert s["reconciled_fills"] == 1
    assert s["needs_reconciliation"] == 2
    assert s["missing_fill_identity"] == 1
    assert s["fill_not_found"] == 1
    assert s["eligible_for_learning"] == 1
    assert s["rows_with_order_id"] == 2
    assert s["rows_missing_order_id"] == 1


# ---------------------------------------------------------------------------
# Test 15: schema_version present on all rows
# ---------------------------------------------------------------------------

def test_schema_version_on_all_rows():
    ctxs = [
        _buy_ctx(order_id=None),
        _sell_ctx(order_id="0xSV", fills=[_FILL_A]),
        _sell_ctx(order_id="0xSVNF", fills=[]),
    ]
    fill_sets = [[], [_FILL_A], []]
    for ctx, fills in zip(ctxs, fill_sets):
        rows = build_output_rows(ctx, fills)
        for r in rows:
            assert r["schema_version"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Test 16: is_dev_fixture_path detection
# ---------------------------------------------------------------------------

def test_is_dev_fixture_path():
    assert is_dev_fixture_path("data/runtime_import/performance.json") is True
    assert is_dev_fixture_path("data/runtime_import_derived/x.json") is True
    assert is_dev_fixture_path("/clean/performance.json") is False
    assert is_dev_fixture_path("") is False


# ---------------------------------------------------------------------------
# Test 17: Seoul pre-patch detection
# ---------------------------------------------------------------------------

def test_is_seoul_pre_patch():
    assert is_seoul_pre_patch("Seoul", "2026-05-22") is True
    assert is_seoul_pre_patch("Seoul", "2026-05-24") is True
    assert is_seoul_pre_patch("Seoul", "2026-05-25") is False  # patch date
    assert is_seoul_pre_patch("Seoul", "2026-05-26") is False
    assert is_seoul_pre_patch("Madrid", "2026-05-22") is False
    assert is_seoul_pre_patch("seoul", "2026-05-22") is True  # lowercase


# ---------------------------------------------------------------------------
# Test 18: normalize_performance_entries ignores non-BUY/SELL actions
# ---------------------------------------------------------------------------

def test_normalize_performance_filters_non_trade_actions():
    data = [
        {"action": "BUY", "city": "Tokyo", "date": "2026-05-20", "token_id": "t1"},
        {"action": "SELL", "city": "Tokyo", "date": "2026-05-21", "token_id": "t1",
         "order_id": "0xT1"},
        {"action": "LOSS_TOTAL", "city": "Tokyo", "date": "2026-05-22"},
        {"action": "BANKROLL_UPDATE"},
    ]
    entries = normalize_performance_entries(data, _CLEAN_PROV)
    assert len(entries) == 2
    assert all(e["action"] in ("BUY", "SELL") for e in entries)


# ---------------------------------------------------------------------------
# Test 19: load_json_file handles BOM and preamble
# ---------------------------------------------------------------------------

def test_load_json_file_handles_bom(tmp_path: Path):
    data = [{"action": "BUY", "city": "Tokyo"}]
    # Write with BOM
    p = tmp_path / "test_bom.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8"))
    loaded = load_json_file(p)
    assert loaded == data


def test_load_json_file_handles_ssh_preamble(tmp_path: Path):
    data = {"key": "value"}
    preamble = "Warning: SSH connection established\n"
    p = tmp_path / "test_preamble.json"
    p.write_bytes((preamble + json.dumps(data)).encode("utf-8"))
    loaded = load_json_file(p)
    assert loaded == data


# ---------------------------------------------------------------------------
# Test 20: liquidity_exit closure_reason preserved, no market_outcome
# ---------------------------------------------------------------------------

def test_liquidity_exit_no_market_outcome():
    ctx = _sell_ctx(order_id="0xLIQ1", city="Wellington", date_iso="2026-05-22")
    ctx["reason"] = "micro_position_unsellable"
    rows = build_output_rows(ctx, [_FILL_A])
    assert len(rows) == 1
    r = rows[0]
    assert r["closure_reason"] == "micro_position_unsellable"
    assert r["market_outcome"] is None
    assert r["eligible_for_calibration"] is False
