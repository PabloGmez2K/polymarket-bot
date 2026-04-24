#!/usr/bin/env python3
"""Rebuild runtime_import artifacts and reconcile known stale legacy positions."""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import types
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOT_FILE = REPO_ROOT / "bot.py"
RUNTIME_DIR = REPO_ROOT / "data" / "runtime_import"
PERFORMANCE_SRC = RUNTIME_DIR / "performance.json"
POSTMORTEM_DST = RUNTIME_DIR / "postmortem.json"
TRADE_LIFECYCLE_DST = RUNTIME_DIR / "trade_lifecycle.json"
BOT_VERSION = "v10.6.30"

MANUAL_RESOLUTIONS = {
    ("Ankara", "2026-03-26", "NO"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved_yes",
        "close_subtype": "market_resolved_yes",
        "resolved_outcome": "10C",
        "estimated_position_outcome": "11C NO",
        "confidence": "media_alta",
        "closed_at": "2026-03-26T23:59:59+00:00",
    },
    ("London", "2026-03-26", "NO"): {
        "close_action": "LOSS_TOTAL",
        "close_reason": "market_resolved_no",
        "close_subtype": "market_resolved_no",
        "resolved_outcome": "10C",
        "estimated_position_outcome": "10C NO",
        "confidence": "alta",
        "closed_at": "2026-03-26T23:59:59+00:00",
    },
    ("Shanghai", "2026-03-27", "NO"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved_yes",
        "close_subtype": "market_resolved_yes",
        "resolved_outcome": "19C",
        "estimated_position_outcome": "18C NO",
        "confidence": "alta",
        "closed_at": "2026-03-27T23:59:59+00:00",
    },
    ("Wellington", "2026-03-28", "NO"): {
        "close_action": "RESOLVED_WIN",
        "close_reason": "market_resolved_yes",
        "close_subtype": "market_resolved_yes",
        "resolved_outcome": "22C",
        "estimated_position_outcome": "20C NO",
        "confidence": "alta",
        "closed_at": "2026-03-28T23:59:59+00:00",
    },
}


def configure_stdio():
    if hasattr(__import__("sys").stdout, "reconfigure"):
        __import__("sys").stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(__import__("sys").stderr, "reconfigure"):
        __import__("sys").stderr.reconfigure(encoding="utf-8", errors="replace")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_function_source(module_ast, code_lines, fn_name: str) -> str:
    for node in module_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            return "\n".join(code_lines[node.lineno - 1 : node.end_lineno])
    raise KeyError(fn_name)


def load_bot_namespace(perf_path: Path, postmortem_path: Path, lifecycle_path: Path):
    source = BOT_FILE.read_text(encoding="utf-8")
    module_ast = ast.parse(source)
    code_lines = source.splitlines()
    ns = {
        "os": os,
        "json": json,
        "re": re,
        "datetime": datetime,
        "timezone": timezone,
        "PERFORMANCE_FILE": str(perf_path),
        "POSTMORTEM_FILE": str(postmortem_path),
        "TRADE_LIFECYCLE_FILE": str(lifecycle_path),
        "log": types.SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None),
    }
    for fn_name in [
        "load_performance_history",
        "load_postmortem_data",
        "save_postmortem_data",
        "load_trade_lifecycle_data",
        "save_trade_lifecycle_data",
        "_lifecycle_clone",
        "_lifecycle_is_empty",
        "_parse_lifecycle_timestamp",
        "_to_lifecycle_float",
        "_normalize_trade_lifecycle_text",
        "_trade_lifecycle_market_key",
        "_trade_lifecycle_position_key",
        "_trade_lifecycle_entry_anchor",
        "_trade_lifecycle_merge_priority",
        "_trade_lifecycle_records_can_merge",
        "_trade_lifecycle_label",
        "_trade_lifecycle_record_id",
        "_find_trade_lifecycle_record",
        "_new_trade_lifecycle_record",
        "_merge_trade_lifecycle_context",
        "_merge_trade_lifecycle_record",
        "_coalesce_trade_lifecycle_records",
        "_build_trade_lifecycle_record_integrity",
        "_build_trade_lifecycle_integrity",
        "_copy_trade_lifecycle_dynamic_fields",
        "_timeline_event_from_entry",
        "_append_trade_lifecycle_event",
        "_append_trade_lifecycle_buy",
        "_append_trade_lifecycle_exit_attempt",
        "_update_trade_lifecycle_exit_attempt",
        "_apply_trade_lifecycle_close",
        "_append_synthetic_postmortem_close_event",
        "_build_trade_lifecycle_summary",
        "_find_open_postmortem",
        "_find_postmortem_by_position_key",
        "update_postmortem",
        "_sync_trade_lifecycle_from_sources",
    ]:
        exec(get_function_source(module_ast, code_lines, fn_name), ns)
    ns["_parse_position_label"] = lambda title, outcome="": f"{title} {outcome}".strip()
    return ns


def rebuild_runtime_snapshot():
    perf_entries = read_json(PERFORMANCE_SRC)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    temp_dir = REPO_ROOT / ".tmp" / f"runtime_import_reconcile_{stamp}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    perf_tmp = temp_dir / "performance.json"
    pm_tmp = temp_dir / "postmortem.json"
    tl_tmp = temp_dir / "trade_lifecycle.json"
    write_json(perf_tmp, perf_entries)
    write_json(pm_tmp, [])
    shutil.copy2(TRADE_LIFECYCLE_DST, tl_tmp)

    ns = load_bot_namespace(perf_tmp, pm_tmp, tl_tmp)
    for entry in perf_entries:
        ns["update_postmortem"](entry.get("action", ""), entry)
    lifecycle_payload = ns["_sync_trade_lifecycle_from_sources"]()
    postmortem_records = ns["load_postmortem_data"]()
    return temp_dir, ns, postmortem_records, lifecycle_payload


def close_payload(amount: float, shares: float, spec: dict):
    amount = round(float(amount or 0), 2)
    shares = round(float(shares or 0), 4)
    action = spec["close_action"]
    if action == "RESOLVED_WIN":
        return_est = round(shares, 2)
        pnl_cash = round(return_est - amount, 2)
        pnl_pct = round((return_est / amount - 1.0) * 100, 1) if amount > 0 else None
        close_price = 1.0
    else:
        return_est = 0.0
        pnl_cash = round(-amount, 2)
        pnl_pct = -100.0 if amount > 0 else None
        close_price = 0.0
    return {
        "close_price": close_price,
        "close_shares": shares,
        "return_est": return_est,
        "pnl_cash": pnl_cash,
        "pnl_pct": pnl_pct,
    }


def apply_manual_resolution_to_postmortem(records: list[dict]):
    patched = 0
    for record in records:
        key = (record.get("city"), record.get("date"), str(record.get("side", "")).upper())
        spec = MANUAL_RESOLUTIONS.get(key)
        if spec is None:
            continue
        payload = close_payload(record.get("total_amount"), record.get("total_shares"), spec)
        record["status"] = "closed"
        record["closed_at"] = spec["closed_at"]
        record["close_action"] = spec["close_action"]
        record["close_reason"] = spec["close_reason"]
        record["close_subtype"] = spec["close_subtype"]
        record["close_price"] = payload["close_price"]
        record["close_shares"] = payload["close_shares"]
        record["return_est"] = payload["return_est"]
        record["pnl_cash"] = payload["pnl_cash"]
        record["pnl_pct"] = payload["pnl_pct"]
        record["order_id"] = None
        record["bot_version_closed"] = BOT_VERSION
        record["resolved_outcome"] = spec["resolved_outcome"]
        record["estimated_position_outcome"] = spec["estimated_position_outcome"]
        record["reconciliation_confidence"] = spec["confidence"]
        record["reconciled_manually"] = True
        patched += 1
    return patched


def apply_manual_resolution_to_lifecycle(records: list[dict], ns: dict, pm_lookup: dict):
    patched = 0
    for record in records:
        key = (record.get("city"), record.get("date"), str(record.get("side", "")).upper())
        spec = MANUAL_RESOLUTIONS.get(key)
        if spec is None:
            continue

        pm_record = pm_lookup.get(key)
        if pm_record:
            record["total_amount"] = pm_record.get("total_amount", record.get("total_amount"))
            record["total_shares"] = pm_record.get("total_shares", record.get("total_shares"))
            record["avg_entry_price"] = pm_record.get("avg_entry_price", record.get("avg_entry_price"))
            record["buy_count"] = pm_record.get("buy_count", record.get("buy_count"))

        payload = close_payload(record.get("total_amount"), record.get("total_shares"), spec)
        record["status"] = "closed"
        record["closed_at"] = spec["closed_at"]
        close_context = record.setdefault("close_context", {})
        close_context.update(
            {
                "close_action": spec["close_action"],
                "close_reason": spec["close_reason"],
                "close_subtype": spec["close_subtype"],
                "close_price": payload["close_price"],
                "close_shares": payload["close_shares"],
                "return_est": payload["return_est"],
                "pnl_cash": payload["pnl_cash"],
                "pnl_pct": payload["pnl_pct"],
                "order_id": "",
                "timestamp": spec["closed_at"],
                "bot_version": BOT_VERSION,
                "resolved_outcome": spec["resolved_outcome"],
                "estimated_position_outcome": spec["estimated_position_outcome"],
                "reconciliation_confidence": spec["confidence"],
            }
        )
        record.setdefault("timeline", []).append(
            {
                "timestamp": spec["closed_at"],
                "action": spec["close_action"],
                "reason": spec["close_reason"],
                "decision_note": "manual_runtime_import_reconciliation",
                "decision_source": "manual_reconciliation",
                "price": payload["close_price"],
                "shares": payload["close_shares"],
                "amount": None,
                "return_est": payload["return_est"],
                "pnl_pct": payload["pnl_pct"],
                "pnl_cash": payload["pnl_cash"],
                "loss": None if spec["close_action"] == "RESOLVED_WIN" else abs(payload["pnl_cash"]),
                "forecast_max": None,
                "edge_pct": None,
                "our_prob": None,
                "mkt_price": None,
                "days_ahead": None,
                "order_id": "",
                "bot_version": BOT_VERSION,
                "source_file": "manual_reconciliation",
            }
        )
        record["timeline"].sort(key=lambda item: str(item.get("timestamp", "")))
        record["integrity"] = ns["_build_trade_lifecycle_record_integrity"](record)
        record["label"] = ns["_trade_lifecycle_label"](record)
        patched += 1
    return patched


def backup_file(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_suffix(path.suffix + f".bak_{stamp}")
    shutil.copy2(path, backup)
    return backup


def main():
    configure_stdio()
    temp_dir, ns, pm_records, lifecycle_payload = rebuild_runtime_snapshot()
    tl_records = lifecycle_payload.get("records", [])

    pm_auto_closed = sum(1 for record in pm_records if record.get("status") == "closed")
    pm_lookup = {
        (record.get("city"), record.get("date"), str(record.get("side", "")).upper()): record
        for record in pm_records
    }
    manual_pm = apply_manual_resolution_to_postmortem(pm_records)
    manual_tl = apply_manual_resolution_to_lifecycle(tl_records, ns, pm_lookup)

    lifecycle_payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    lifecycle_payload["summary"] = ns["_build_trade_lifecycle_summary"](tl_records)
    lifecycle_payload["integrity"] = ns["_build_trade_lifecycle_integrity"](
        tl_records,
        duplicate_collisions=(lifecycle_payload.get("integrity") or {}).get("duplicate_id_collisions_resolved", 0),
    )

    pm_backup = backup_file(POSTMORTEM_DST)
    tl_backup = backup_file(TRADE_LIFECYCLE_DST)
    write_json(POSTMORTEM_DST, pm_records)
    write_json(TRADE_LIFECYCLE_DST, lifecycle_payload)

    open_targets = [
        key
        for key in MANUAL_RESOLUTIONS
        if any(
            record.get("city") == key[0]
            and record.get("date") == key[1]
            and str(record.get("side", "")).upper() == key[2]
            and record.get("status") == "open"
            for record in tl_records
        )
    ]

    print("runtime_import reconciliado")
    print(f"- temp dir: {temp_dir}")
    print(f"- backup postmortem: {pm_backup}")
    print(f"- backup trade_lifecycle: {tl_backup}")
    print(f"- cierres reconstruidos desde performance: {pm_auto_closed}")
    print(f"- cierres manuales postmortem: {manual_pm}")
    print(f"- cierres manuales trade_lifecycle: {manual_tl}")
    print(f"- targets manuales aun open: {len(open_targets)}")
    for key, spec in MANUAL_RESOLUTIONS.items():
        print(
            f"  * {key[0]} {key[1]} {key[2]} -> {spec['close_action']} / "
            f"{spec['close_reason']} / outcome {spec['resolved_outcome']} / {spec['confidence']}"
        )


if __name__ == "__main__":
    main()
