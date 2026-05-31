"""Pure reconciliation engine for R1 — API-fill based, LOG_ONLY.

No network. No DB. No bot.py imports. No side effects.
Canonical fill source: CLOB API fills accessed via order_id.
Context sources (non-canonical): performance.json, postmortem.json, trade_lifecycle.json.
Discarded source: trades.log (no order_id linkage).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = "r1_v1"
# 3307b4f fix: align Seoul forecast station with RKSI — deployed 2026-05-25
SEOUL_PATCH_DATE_ISO = "2026-05-25"


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def load_json_file(path: str | Path) -> Any:
    """Load JSON with BOM and SSH-preamble tolerance."""
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc).strip()
            for i, ch in enumerate(text):
                if ch in ("{", "["):
                    text = text[i:]
                    break
            return json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"Cannot parse JSON from {path}")


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def is_dev_fixture_path(path: str) -> bool:
    """Paths under data/runtime_import are dev fixtures — never eligible."""
    return "runtime_import" in str(path)


def is_seoul_pre_patch(city: str, date_iso: str) -> bool:
    """Seoul entries before the RKSI patch are suspect (station mismatch)."""
    return city.strip().lower() == "seoul" and bool(date_iso) and date_iso < SEOUL_PATCH_DATE_ISO


# ---------------------------------------------------------------------------
# Context normalization
# ---------------------------------------------------------------------------

def normalize_performance_entries(
    data: list[dict],
    provenance: dict,
) -> list[dict]:
    """Extract BUY/SELL context records from performance.json."""
    dev_fixture = is_dev_fixture_path(
        provenance.get("local_path", provenance.get("source_path", ""))
    )
    result = []
    for entry in data:
        action = (entry.get("action") or "").upper()
        if action not in ("BUY", "SELL"):
            continue
        result.append({
            "_source": "performance",
            "_dev_fixture": dev_fixture,
            "_provenance": provenance,
            "action": action,
            "order_id": entry.get("order_id") or None,
            "city": entry.get("city") or "",
            "date_iso": entry.get("date") or "",
            "condition": entry.get("condition") or "",
            "threshold": entry.get("threshold"),
            "unit": entry.get("unit"),
            "side": entry.get("side") or "",
            "token_id": entry.get("token_id") or "",
            "market_id": entry.get("market_id"),
            "condition_id": entry.get("condition_id"),
            "reason": entry.get("reason"),
            "fill_source": entry.get("fill_source"),
            "_embedded_fills": entry.get("fill_trades") or [],
        })
    return result


def normalize_postmortem_entries(
    data: list[dict],
    provenance: dict,
) -> list[dict]:
    """Extract BUY/SELL sub-records from postmortem.json positions."""
    dev_fixture = is_dev_fixture_path(
        provenance.get("local_path", provenance.get("source_path", ""))
    )
    result = []
    for pm in data:
        city = pm.get("city") or ""
        date_iso = pm.get("date") or ""
        for buy in (pm.get("buys") or []):
            result.append({
                "_source": "postmortem_buy",
                "_dev_fixture": dev_fixture,
                "_provenance": provenance,
                "action": "BUY",
                "order_id": buy.get("order_id") or None,
                "city": city,
                "date_iso": date_iso,
                "condition": pm.get("condition") or "",
                "threshold": pm.get("threshold"),
                "unit": pm.get("unit"),
                "side": pm.get("side") or "",
                "token_id": pm.get("token_id") or "",
                "market_id": pm.get("market_id"),
                "condition_id": pm.get("condition_id"),
                "reason": None,
                "fill_source": None,
                "_embedded_fills": [],
            })
        for sell in (pm.get("sells") or []):
            result.append({
                "_source": "postmortem_sell",
                "_dev_fixture": dev_fixture,
                "_provenance": provenance,
                "action": "SELL",
                "order_id": sell.get("order_id") or None,
                "city": city,
                "date_iso": date_iso,
                "condition": pm.get("condition") or "",
                "threshold": pm.get("threshold"),
                "unit": pm.get("unit"),
                "side": pm.get("side") or "",
                "token_id": pm.get("token_id") or "",
                "market_id": pm.get("market_id"),
                "condition_id": pm.get("condition_id"),
                "reason": sell.get("reason"),
                "fill_source": sell.get("fill_source"),
                "_embedded_fills": sell.get("fill_trades") or [],
            })
    return result


# ---------------------------------------------------------------------------
# Fill resolution
# ---------------------------------------------------------------------------

def get_fills_for_entry(
    entry: dict,
    offline_fills_map: dict[str, list[dict]],
) -> list[dict]:
    """Resolve canonical fills for an entry.

    Priority:
    1. offline_fills_map[order_id]  — injected externally (tests / --offline-fills-json)
    2. entry["_embedded_fills"]     — fills cached in context record at execution time
    3. [] → needs_reconciliation=True
    """
    order_id = entry.get("order_id")
    if not order_id:
        return []
    if order_id in offline_fills_map:
        return list(offline_fills_map[order_id])
    embedded = entry.get("_embedded_fills") or []
    return list(embedded)


# ---------------------------------------------------------------------------
# Output row construction
# ---------------------------------------------------------------------------

def _base_provenance_fields(prov: dict) -> dict:
    return {
        "source_path": prov.get("source_path"),
        "capture_ts": prov.get("capture_ts"),
        "capture_method": prov.get("capture_method"),
        "sha256": prov.get("sha256"),
    }


def build_output_rows(entry: dict, fills: list[dict]) -> list[dict]:
    """Build reconciled output rows for one context entry + its fills.

    Rules:
    - No order_id → missing_fill_identity, ineligible
    - order_id + no fills → fill_not_found, needs_reconciliation
    - order_id + fills → one row per fill, execution_id=order_id_NNNN
    - dev_fixture path → provenance_class=dev_fixture, ineligible
    - Seoul pre-patch → source_fidelity=suspect, ineligible
    - market_outcome always null in R1
    - pnl_realized null until buy-side reconciled
    """
    order_id = entry.get("order_id")
    city = entry.get("city", "")
    date_iso = entry.get("date_iso", "")
    is_dev = entry.get("_dev_fixture", False)
    prov = entry.get("_provenance", {})
    seoul_suspect = is_seoul_pre_patch(city, date_iso)

    base = {
        "schema_version": SCHEMA_VERSION,
        "order_id": order_id,
        "city": city,
        "date_iso": date_iso,
        "condition": entry.get("condition"),
        "threshold": entry.get("threshold"),
        "unit": entry.get("unit"),
        "side": entry.get("side"),
        "token_id": entry.get("token_id"),
        "market_id": entry.get("market_id"),
        "condition_id": entry.get("condition_id"),
        "market_outcome": None,
        "closure_reason": entry.get("reason"),
        **_base_provenance_fields(prov),
    }

    # Case 1: missing order_id
    if not order_id:
        return [{
            **base,
            "execution_id": None,
            "fill_index": None,
            "trade_id": None,
            "price": None,
            "size": None,
            "value": None,
            "fee": None,
            "timestamp": None,
            "transaction_hash": None,
            "pnl_realized": None,
            "pnl_realized_status": "not_computed_missing_order_id",
            "needs_reconciliation": True,
            "reconciliation_blocker": "missing_fill_identity",
            "eligible_for_learning": False,
            "eligible_for_calibration": False,
            "provenance_class": "dev_fixture" if is_dev else "context_index_only",
            "source_fidelity": "dev_fixture" if is_dev else "legacy_observability",
            "exclusion_reason": None,
        }]

    # Case 2: order_id exists but no fills found
    if not fills:
        return [{
            **base,
            "execution_id": None,
            "fill_index": None,
            "trade_id": None,
            "price": None,
            "size": None,
            "value": None,
            "fee": None,
            "timestamp": None,
            "transaction_hash": None,
            "pnl_realized": None,
            "pnl_realized_status": "not_computed_fill_not_found",
            "needs_reconciliation": True,
            "reconciliation_blocker": "fill_not_found",
            "eligible_for_learning": False,
            "eligible_for_calibration": False,
            "provenance_class": "dev_fixture" if is_dev else "order_id_only",
            "source_fidelity": "dev_fixture" if is_dev else ("suspect" if seoul_suspect else "confirmed"),
            "exclusion_reason": (
                "station_mismatch_kma_vs_rksi_pre_patch" if (seoul_suspect and not is_dev) else None
            ),
        }]

    # Case 3: order_id + fills → one row per fill
    rows = []
    for fill_idx, fill in enumerate(fills):
        execution_id = f"{order_id}_{fill_idx:04d}"

        if is_dev:
            prov_class = "dev_fixture"
            fidelity = "dev_fixture"
            elig_learn = False
            excl = None
        elif seoul_suspect:
            prov_class = "clob_embedded_suspect"
            fidelity = "suspect"
            elig_learn = False
            excl = "station_mismatch_kma_vs_rksi_pre_patch"
        else:
            prov_class = "clob_embedded"
            fidelity = "confirmed"
            elig_learn = True
            excl = None

        rows.append({
            **base,
            "execution_id": execution_id,
            "fill_index": fill_idx,
            "trade_id": fill.get("id"),
            "price": fill.get("price"),
            "size": fill.get("size"),
            "value": fill.get("value"),
            "fee": fill.get("fee"),
            "timestamp": fill.get("timestamp"),
            "transaction_hash": fill.get("transaction_hash"),
            "pnl_realized": None,
            "pnl_realized_status": "not_computed_buy_unreconciled",
            "needs_reconciliation": False,
            "reconciliation_blocker": None,
            "eligible_for_learning": elig_learn,
            "eligible_for_calibration": False,
            "provenance_class": prov_class,
            "source_fidelity": fidelity,
            "exclusion_reason": excl,
        })
    return rows


# ---------------------------------------------------------------------------
# Main reconciliation entry point
# ---------------------------------------------------------------------------

def reconcile(
    performance_data: Optional[list[dict]],
    postmortem_data: Optional[list[dict]],
    lifecycle_data: Optional[dict],
    context_provenance: dict,
    offline_fills_map: Optional[dict[str, list[dict]]] = None,
) -> list[dict]:
    """Reconcile context records against available fills.

    Args:
        performance_data: Parsed performance.json list (primary source of BUY/SELL entries).
        postmortem_data: Parsed postmortem.json list (context only; no order_ids expected).
        lifecycle_data: Parsed trade_lifecycle.json dict (accepted, rows not generated in R1).
        context_provenance: Provenance dict for the source files, keyed by file type or flat.
        offline_fills_map: Optional {order_id: [fill_dicts]} for offline/test mode.

    Returns:
        List of output row dicts, one per (context_entry × fill).
    """
    if offline_fills_map is None:
        offline_fills_map = {}

    # Normalize provenance: accept both flat dict and {"performance": {...}} style
    def _get_prov(key: str) -> dict:
        if key in context_provenance and isinstance(context_provenance[key], dict):
            return context_provenance[key]
        return context_provenance

    context_entries: list[dict] = []

    if performance_data:
        context_entries.extend(
            normalize_performance_entries(performance_data, _get_prov("performance"))
        )

    if postmortem_data:
        context_entries.extend(
            normalize_postmortem_entries(postmortem_data, _get_prov("postmortem"))
        )

    # lifecycle_data accepted but not iterated — no order_ids, no BUY/SELL sub-records
    # Its provenance is included in context_provenance for reference.

    output_rows: list[dict] = []
    for entry in context_entries:
        fills = get_fills_for_entry(entry, offline_fills_map)
        rows = build_output_rows(entry, fills)
        output_rows.extend(rows)

    return output_rows


# ---------------------------------------------------------------------------
# Coverage summary
# ---------------------------------------------------------------------------

def compute_coverage_summary(rows: list[dict]) -> dict:
    """Aggregate stats over reconciled rows."""
    total = len(rows)
    reconciled = sum(1 for r in rows if r.get("execution_id") and not r.get("needs_reconciliation"))
    needs_recon = sum(1 for r in rows if r.get("needs_reconciliation"))
    elig_learn = sum(1 for r in rows if r.get("eligible_for_learning"))
    missing_id = sum(1 for r in rows if r.get("reconciliation_blocker") == "missing_fill_identity")
    fill_not_found = sum(1 for r in rows if r.get("reconciliation_blocker") == "fill_not_found")
    suspect = sum(1 for r in rows if r.get("source_fidelity") == "suspect")
    dev_fix = sum(1 for r in rows if r.get("provenance_class") == "dev_fixture")
    has_order_id = sum(1 for r in rows if r.get("order_id"))
    no_order_id = sum(1 for r in rows if not r.get("order_id"))
    return {
        "total_rows": total,
        "reconciled_fills": reconciled,
        "needs_reconciliation": needs_recon,
        "missing_fill_identity": missing_id,
        "fill_not_found": fill_not_found,
        "eligible_for_learning": elig_learn,
        "suspect_fidelity": suspect,
        "dev_fixture": dev_fix,
        "rows_with_order_id": has_order_id,
        "rows_missing_order_id": no_order_id,
    }
