#!/usr/bin/env python3
"""Archive filtered signals.json snapshots and build a minimal pseudo-lifecycle.

Usage:
  python tools/traders_intelligence_snapshot.py
  python tools/traders_intelligence_snapshot.py --dry-run
  python tools/traders_intelligence_snapshot.py --run-id 2026-05-01T120000Z

This tool is observational only. It reads signals.json, filters the configured
lead traders/cities, writes an immutable-style snapshot plus a JSON report, and
never modifies the source signals.json or any trading policy.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNALS_PATH = REPO_ROOT / "data" / "runtime_import" / "signals.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "traders_intelligence"
DEFAULT_SNAPSHOT_DIR = DEFAULT_OUTPUT_DIR / "snapshots"
DEFAULT_REPORT_DIR = DEFAULT_OUTPUT_DIR / "reports"
DEFAULT_AUDIT_LOG = DEFAULT_OUTPUT_DIR / "pseudo_lifecycle_runs.jsonl"

TARGET_TRADERS = ("Thrifty-Original", "Entire-Hood")
TARGET_CITIES = ("Houston", "Los Angeles", "Manila", "Miami")

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Archiva snapshots filtrados de signals.json y construye un "
            "pseudo-lifecycle externo observacional para traders/cities objetivo."
        )
    )
    parser.add_argument("--signals", default=str(DEFAULT_SIGNALS_PATH), help="Ruta a data/runtime_import/signals.json.")
    parser.add_argument("--snapshot-dir", default=str(DEFAULT_SNAPSHOT_DIR), help="Directorio de snapshots filtrados.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Directorio de reportes JSON por run_id.")
    parser.add_argument("--audit-log", default=str(DEFAULT_AUDIT_LOG), help="JSONL audit independiente de corridas.")
    parser.add_argument("--run-id", default=None, help="ID idempotente de corrida. Default: timestamp UTC.")
    parser.add_argument("--snapshot-at", default=None, help="Timestamp ISO UTC opcional para pruebas/auditoria.")
    parser.add_argument("--dry-run", action="store_true", help="Calcula sin escribir snapshot, report ni audit log.")
    return parser.parse_args()


def clean_run_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._") or "manual_run"


def timestamp_to_run_id(value: str) -> str:
    return clean_run_id(value.replace("+00:00", "Z").replace(":", "").replace("-", ""))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input signals.json: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in signals.json: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"signals.json must contain a JSON object: {path}")
    if not isinstance(payload.get("signals"), list):
        raise ValueError(f"signals.json missing list field 'signals': {path}")
    return payload


def normalize(value: Any) -> str:
    return str(value or "").strip().casefold()


def signal_identity(row: dict[str, Any]) -> str:
    match_key = str(row.get("match_key") or "").strip()
    if match_key:
        return match_key
    parts = [
        row.get("city"),
        row.get("date"),
        row.get("condition"),
        row.get("temp"),
        row.get("unit"),
        row.get("outcome"),
        row.get("title"),
    ]
    return "|".join(str(part or "").strip() for part in parts)


def lifecycle_key(row: dict[str, Any]) -> str:
    return f"{row.get('trader')}|{signal_identity(row)}"


def minimal_signal(row: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "trader",
        "title",
        "city",
        "condition",
        "date",
        "temp",
        "unit",
        "outcome",
        "avg_price",
        "cur_price",
        "cash_pnl",
        "pct_pnl",
        "match_key",
        "trader_win_rate",
        "trader_pnl",
        "has_consensus",
        "consensus_with",
    )
    result = {key: row.get(key) for key in keep if key in row}
    result["signal_id"] = signal_identity(row)
    result["lifecycle_key"] = lifecycle_key(result)
    return result


def filter_signals(signals_payload: dict[str, Any]) -> list[dict[str, Any]]:
    trader_set = {normalize(name) for name in TARGET_TRADERS}
    city_set = {normalize(name) for name in TARGET_CITIES}
    rows = []
    for row in signals_payload.get("signals", []):
        if not isinstance(row, dict):
            continue
        if normalize(row.get("trader")) not in trader_set:
            continue
        if normalize(row.get("city")) not in city_set:
            continue
        rows.append(minimal_signal(row))
    rows.sort(key=lambda item: (str(item.get("trader")), str(item.get("city")), str(item.get("signal_id"))))
    return rows


def snapshot_path_for(snapshot_dir: Path, run_id: str) -> Path:
    return snapshot_dir / f"{clean_run_id(run_id)}.json"


def report_path_for(report_dir: Path, run_id: str) -> Path:
    return report_dir / f"{clean_run_id(run_id)}.json"


def read_snapshot(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("signals"), list):
        return None
    return payload


def load_prior_snapshots(snapshot_dir: Path, current_run_id: str) -> list[dict[str, Any]]:
    if not snapshot_dir.exists():
        return []
    snapshots = []
    for path in snapshot_dir.glob("*.json"):
        payload = read_snapshot(path)
        if not payload:
            continue
        if str(payload.get("run_id")) == current_run_id:
            continue
        payload["_path"] = str(path)
        snapshots.append(payload)
    snapshots.sort(key=lambda item: (str(item.get("snapshot_at") or ""), str(item.get("run_id") or "")))
    return snapshots


def map_by_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped = {}
    for row in rows:
        key = str(row.get("lifecycle_key") or lifecycle_key(row))
        if key:
            mapped[key] = row
    return mapped


def build_history_index(prior_snapshots: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for snapshot in prior_snapshots:
        snapshot_at = snapshot.get("snapshot_at")
        for row in snapshot.get("signals", []) or []:
            if not isinstance(row, dict):
                continue
            key = str(row.get("lifecycle_key") or lifecycle_key(row))
            if not key:
                continue
            entry = index.setdefault(
                key,
                {
                    "first_seen_at": snapshot_at,
                    "last_seen_at": snapshot_at,
                    "seen_count": 0,
                    "last_signal": None,
                },
            )
            entry["seen_count"] += 1
            entry["last_seen_at"] = snapshot_at
            entry["last_signal"] = row
    return index


def build_lifecycle(
    current_rows: list[dict[str, Any]],
    current_snapshot_at: str,
    prior_snapshots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    previous = prior_snapshots[-1] if prior_snapshots else None
    previous_at = previous.get("snapshot_at") if previous else None
    previous_rows = previous.get("signals", []) if previous else []
    previous_by_key = map_by_key(previous_rows)
    current_by_key = map_by_key(current_rows)
    history = build_history_index(prior_snapshots)

    events = []
    for key, row in sorted(current_by_key.items()):
        historical = history.get(key)
        was_previous = key in previous_by_key
        if was_previous:
            status = "still_present"
        elif historical:
            status = "reappeared"
        else:
            status = "appeared"
        events.append(
            {
                "status": status,
                "trader": row.get("trader"),
                "city": row.get("city"),
                "match_key": row.get("match_key"),
                "signal_id": row.get("signal_id"),
                "first_seen_at": historical.get("first_seen_at") if historical else current_snapshot_at,
                "last_seen_at": current_snapshot_at,
                "previous_seen_at": historical.get("last_seen_at") if historical else None,
                "previous_snapshot_at": previous_at,
                "seen_count_before_current": int(historical.get("seen_count", 0)) if historical else 0,
                "avg_price": row.get("avg_price"),
                "cur_price": row.get("cur_price"),
                "confidence": "medium" if previous else "low",
                "evidence": ["signals.json filtered snapshot series"],
            }
        )

    for key, row in sorted(previous_by_key.items()):
        if key in current_by_key:
            continue
        historical = history.get(key, {})
        events.append(
            {
                "status": "disappeared_apparent",
                "trader": row.get("trader"),
                "city": row.get("city"),
                "match_key": row.get("match_key"),
                "signal_id": row.get("signal_id"),
                "first_seen_at": historical.get("first_seen_at") or previous_at,
                "last_seen_at": previous_at,
                "previous_snapshot_at": previous_at,
                "seen_count_before_current": int(historical.get("seen_count", 0) or 0),
                "avg_price": row.get("avg_price"),
                "cur_price": row.get("cur_price"),
                "confidence": "medium",
                "caveat": "Apparent disappearance only; signals.json has no confirmed trader exit event.",
                "evidence": ["previous filtered snapshot", "current filtered snapshot"],
            }
        )

    events.sort(key=lambda item: (str(item.get("trader")), str(item.get("city")), str(item.get("signal_id")), item["status"]))
    return events


def status_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts = {name: 0 for name in ("appeared", "still_present", "disappeared_apparent", "reappeared")}
    for event in events:
        status = str(event.get("status"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def write_jsonl_idempotent(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [existing for existing in read_jsonl(path) if existing.get("run_id") != row.get("run_id")]
    rows.append(row)
    rows.sort(key=lambda item: str(item.get("snapshot_at") or item.get("generated_at") or ""))
    path.write_text(
        "".join(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n" for item in rows),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()

    snapshot_at = args.snapshot_at or utc_now().isoformat()
    run_id = clean_run_id(args.run_id) if args.run_id else timestamp_to_run_id(snapshot_at)
    signals_path = Path(args.signals)
    snapshot_dir = Path(args.snapshot_dir)
    report_dir = Path(args.report_dir)
    audit_log = Path(args.audit_log)

    try:
        signals_payload = load_json(signals_path)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 2

    filtered = filter_signals(signals_payload)
    prior_snapshots = load_prior_snapshots(snapshot_dir, run_id)
    lifecycle_events = build_lifecycle(filtered, snapshot_at, prior_snapshots)

    snapshot_payload = {
        "schema_version": "traders_intelligence_signal_snapshot_v1",
        "run_id": run_id,
        "snapshot_at": snapshot_at,
        "source_signals_path": str(signals_path),
        "source_signals_generated_at": signals_payload.get("generated"),
        "filters": {
            "traders": list(TARGET_TRADERS),
            "cities": list(TARGET_CITIES),
        },
        "n_signals": len(filtered),
        "signals": filtered,
    }
    report_payload = {
        "schema_version": "traders_intelligence_pseudo_lifecycle_v1",
        "run_id": run_id,
        "generated_at": utc_now().isoformat(),
        "snapshot_at": snapshot_at,
        "dry_run": bool(args.dry_run),
        "scope": {
            "traders": list(TARGET_TRADERS),
            "cities": list(TARGET_CITIES),
            "mode": "external_observational_only",
        },
        "inputs": {
            "signals": str(signals_path),
            "prior_snapshots": len(prior_snapshots),
        },
        "outputs": {
            "snapshot": str(snapshot_path_for(snapshot_dir, run_id)),
            "report": str(report_path_for(report_dir, run_id)),
            "audit_log": str(audit_log),
        },
        "summary": {
            "n_current_signals": len(filtered),
            "status_counts": status_counts(lifecycle_events),
            "n_prior_snapshots": len(prior_snapshots),
        },
        "lifecycle_events": lifecycle_events,
        "guardrails": {
            "does_not_modify_signals_json": True,
            "does_not_trade": True,
            "does_not_change_policy": True,
            "not_a_trading_signal": True,
        },
    }

    snapshot_path = snapshot_path_for(snapshot_dir, run_id)
    report_path = report_path_for(report_dir, run_id)
    audit_row = {
        "schema_version": "traders_intelligence_pseudo_lifecycle_run_v1",
        "run_id": run_id,
        "generated_at": report_payload["generated_at"],
        "snapshot_at": snapshot_at,
        "dry_run": bool(args.dry_run),
        "n_current_signals": len(filtered),
        "status_counts": report_payload["summary"]["status_counts"],
        "snapshot": str(snapshot_path),
        "report": str(report_path),
    }

    if not args.dry_run:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(snapshot_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        report_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        write_jsonl_idempotent(audit_log, audit_row)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "dry_run": bool(args.dry_run),
                "n_current_signals": len(filtered),
                "status_counts": report_payload["summary"]["status_counts"],
                "snapshot": str(snapshot_path),
                "report": str(report_path),
                "audit_log": str(audit_log),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
