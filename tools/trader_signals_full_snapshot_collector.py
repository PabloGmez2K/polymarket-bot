#!/usr/bin/env python3
"""Collect full normalized trader signal snapshots as LOG_ONLY JSONL.

This tool reads a signals.json snapshot and appends one normalized JSONL row per
signal. It is intentionally boring: no APIs, no trading state, no policy writes.
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
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "intelligence" / "trader_signals_snapshots.jsonl"
SCHEMA_VERSION = "trader_signals_full_snapshot_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LOG_ONLY collector for full normalized trader signals snapshots."
    )
    parser.add_argument("--signals", default=str(DEFAULT_SIGNALS_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--snapshot-at", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def clean_run_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return cleaned.strip("._") or "manual_run"


def load_signals(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required signals input: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("signals"), list):
        raise ValueError(f"signals input must be an object with list field 'signals': {path}")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
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


def signal_identity(row: dict[str, Any]) -> str:
    match_key = str(row.get("match_key") or "").strip()
    if match_key:
        return match_key
    parts = (
        row.get("trader"),
        row.get("city"),
        row.get("date"),
        row.get("condition"),
        row.get("temp"),
        row.get("unit"),
        row.get("outcome"),
        row.get("title"),
    )
    return "|".join(str(part or "").strip() for part in parts)


def build_run_id(source_generated_at: str | None, snapshot_at: str, override: str | None) -> str:
    if override:
        return clean_run_id(override)
    base = source_generated_at or snapshot_at
    return clean_run_id(base.replace("+00:00", "Z").replace(":", "").replace("-", ""))


def normalize_signal(
    row: dict[str, Any],
    *,
    index: int,
    snapshot_at: str,
    source_generated_at: str | None,
    run_id: str,
    source_path: Path,
) -> dict[str, Any]:
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "row_type": "signal",
        "run_id": run_id,
        "snapshot_at": snapshot_at,
        "source_generated_at": source_generated_at,
        "source_path": str(source_path),
        "source_label": "local/runtime_import",
        "signal_index": index,
        "signal_id": signal_identity(row),
        "trader": row.get("trader"),
        "city": row.get("city"),
        "condition": row.get("condition"),
        "outcome": row.get("outcome"),
        "avg_price": row.get("avg_price"),
        "cur_price": row.get("cur_price"),
        "match_key": row.get("match_key"),
        "has_consensus": bool(row.get("has_consensus", False)),
        "consensus_with": list(row.get("consensus_with") or []),
        "title": row.get("title"),
        "date": row.get("date"),
        "temp": row.get("temp"),
        "unit": row.get("unit"),
    }
    return normalized


def build_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    signals_path = Path(args.signals)
    payload = load_signals(signals_path)
    snapshot_at = args.snapshot_at or utc_now()
    source_generated_at = payload.get("generated")
    run_id = build_run_id(source_generated_at, snapshot_at, args.run_id)
    rows = [
        normalize_signal(
            row,
            index=index,
            snapshot_at=snapshot_at,
            source_generated_at=source_generated_at,
            run_id=run_id,
            source_path=signals_path,
        )
        for index, row in enumerate(payload.get("signals", []))
        if isinstance(row, dict)
    ]
    summary = {
        "run_id": run_id,
        "snapshot_at": snapshot_at,
        "source_generated_at": source_generated_at,
        "n_source_signals": len(payload.get("signals", [])),
        "n_rows": len(rows),
    }
    return rows, summary


def append_snapshot_rows(output_path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    existing = read_jsonl(output_path)
    run_id = summary.get("run_id")
    source_generated_at = summary.get("source_generated_at")
    duplicate_by_run = any(row.get("run_id") == run_id for row in existing)
    duplicate_by_generated = bool(source_generated_at) and any(
        row.get("source_generated_at") == source_generated_at for row in existing
    )
    if duplicate_by_run or duplicate_by_generated:
        return {
            **summary,
            "status": "skipped",
            "reason": "duplicate_snapshot",
            "duplicate_by_run_id": duplicate_by_run,
            "duplicate_by_source_generated_at": duplicate_by_generated,
            "written_rows": 0,
            "output": str(output_path),
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")

    return {
        **summary,
        "status": "completed",
        "reason": "written",
        "written_rows": len(rows),
        "output": str(output_path),
    }


def build_run(args: argparse.Namespace) -> dict[str, Any]:
    rows, summary = build_rows(args)
    output_path = Path(args.output)
    if args.dry_run:
        return {
            **summary,
            "status": "completed",
            "reason": "dry_run",
            "written_rows": 0,
            "output": str(output_path),
            "dry_run": True,
        }
    result = append_snapshot_rows(output_path, rows, summary)
    result["dry_run"] = False
    return result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = build_run(args)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
