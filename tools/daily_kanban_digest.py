#!/usr/bin/env python3
"""Daily Bot Kanban Digest CLI.

Read-only, dry-run first digest for the Alerts + Kanban Lean design.
It stays isolated from the runtime bot module, Telegram, and state writes.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data"

ALLOWED_LEVELS = [
    "NO_ACTION",
    "WATCH",
    "WATCH_TECH",
    "WATCH_RISK",
    "ACTION_ANALYSIS",
    "ACTION_DESIGN",
    "ACTION_SAFETY",
]
LEVEL_RANK = {level: index for index, level in enumerate(ALLOWED_LEVELS)}
KANBAN_COLUMNS = [
    "BACKLOG",
    "READY",
    "DOING",
    "WAITING_EVIDENCE",
    "BLOCKED",
    "WATCH",
    "DONE",
    "DEFERRED",
    "SAFETY",
]
DISCLAIMER_NO_TRADING = "Esta alerta no autoriza cambios de trading."
DISCLAIMER_CALIBRATION = "calibration_global no es evidencia operativa."
P_L_CONTAMINATION_WARNING = (
    "P/L incluye registros reconstruidos/no audit-ready; no usar para BANKROLL ni decisiones operativas."
)
REQUIRED_WALLET_HISTORY_HOURS = 168


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_json(path: Path) -> Any | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def load_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows[-limit:]


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def money(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:+.2f}"


def display(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value)


def level_max(*levels: str) -> str:
    known = [level for level in levels if level in LEVEL_RANK]
    if not known:
        return "NO_ACTION"
    return max(known, key=lambda item: LEVEL_RANK[item])


def normalize_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for key in ("records", "trades", "positions"):
            value = data.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def record_pnl(record: dict[str, Any]) -> float | None:
    close_context = record.get("close_context") if isinstance(record.get("close_context"), dict) else {}
    for value in (close_context.get("pnl_cash"), record.get("pnl_cash"), record.get("pnl")):
        parsed = as_float(value)
        if parsed is not None:
            return parsed
    return None


def record_closed_at(record: dict[str, Any]) -> datetime | None:
    close_context = record.get("close_context") if isinstance(record.get("close_context"), dict) else {}
    return parse_ts(record.get("closed_at") or close_context.get("timestamp"))


def snapshot_at(row: dict[str, Any]) -> datetime | None:
    return parse_ts(row.get("snapshot_at") or row.get("timestamp") or row.get("captured_at"))


def is_valid_wallet_snapshot(row: dict[str, Any]) -> bool:
    return bool(
        row.get("api_ok") is True
        and as_float(row.get("total_value")) is not None
        and snapshot_at(row) is not None
    )


def sorted_valid_wallet_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [row for row in rows if is_valid_wallet_snapshot(row)],
        key=lambda row: snapshot_at(row) or datetime.min.replace(tzinfo=timezone.utc),
    )


def load_cash_flow_jsonl(path: Path) -> tuple[bool, int, list[dict[str, Any]], list[str]]:
    if not path.exists():
        return False, 0, [], []
    rows: list[dict[str, Any]] = []
    reasons: list[str] = []
    total = 0
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                total += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    reasons.append("json_decode")
                    continue
                if isinstance(row, dict):
                    rows.append(row)
                else:
                    reasons.append("not_object")
    except OSError:
        reasons.append("read_error")
    return True, total, rows, reasons


def unique_short(values: list[str], limit: int = 8) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
        if len(seen) >= limit:
            break
    return seen


def parse_cash_flow_ts(value: Any) -> tuple[datetime | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "period_format"
    text = value.strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return None, "period_format"
    if "T" not in text:
        return None, "period_format"
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, "period_format"
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        return None, "period_format"
    return parsed.astimezone(timezone.utc), None


def row_has_example_marker(row: dict[str, Any]) -> bool:
    marker = row.get("marker")
    if marker is None:
        return False
    return "EXAMPLE_ONLY" in str(marker).upper()


def adjustment_review_required(row: dict[str, Any]) -> bool:
    adjustment = row.get("adjustment") if isinstance(row.get("adjustment"), dict) else {}
    return row.get("review_required") is True or adjustment.get("review_required") is True


def validate_cash_flow_row(row: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    reasons: list[str] = []
    entry_id = row.get("entry_id")
    if row.get("schema_version") != 2:
        reasons.append("schema_version")
    if not isinstance(entry_id, str) or not entry_id.strip():
        reasons.append("entry_id")
    elif entry_id.startswith("EXAMPLE-"):
        reasons.append("example_id")
    if row_has_example_marker(row):
        reasons.append("example_marker")
    if row.get("actor") != "pablo_manual":
        reasons.append("actor_mismatch")
    flow_type = row.get("type")
    if flow_type not in {"deposit", "withdrawal", "no_cash_flow_attestation", "adjustment"}:
        reasons.append("type")

    recorded_at, recorded_reason = parse_cash_flow_ts(row.get("recorded_at"))
    period_start, start_reason = parse_cash_flow_ts(row.get("period_start"))
    period_end, end_reason = parse_cash_flow_ts(row.get("period_end"))
    for reason in (recorded_reason, start_reason, end_reason):
        if reason:
            reasons.append(reason)
    if period_start and period_end and period_start > period_end:
        reasons.append("period_order")

    amount = None
    if flow_type in {"deposit", "withdrawal", "adjustment"}:
        amount = as_float(row.get("amount_usdc"))
        if amount is None or amount < 0:
            reasons.append("amount_usdc")

    if reasons:
        return None, reasons
    return {
        "entry_id": entry_id,
        "type": flow_type,
        "recorded_at": recorded_at,
        "period_start": period_start,
        "period_end": period_end,
        "amount_usdc": amount,
        "review_required": flow_type == "adjustment" and adjustment_review_required(row),
    }, []


def interval_overlaps(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> bool:
    return start <= window_end and end >= window_start


def merged_coverage_seconds(intervals: list[tuple[datetime, datetime]]) -> tuple[float, bool]:
    if not intervals:
        return 0.0, False
    ordered = sorted(intervals, key=lambda item: item[0])
    merged: list[list[datetime]] = []
    contiguous = True
    for start, end in ordered:
        if start >= end:
            continue
        if not merged:
            merged.append([start, end])
            continue
        last = merged[-1]
        if start <= last[1]:
            if end > last[1]:
                last[1] = end
        elif start == last[1]:
            last[1] = end
        else:
            contiguous = False
            merged.append([start, end])
    seconds = sum((end - start).total_seconds() for start, end in merged)
    return seconds, contiguous and len(merged) == 1


def is_contaminated_lifecycle_record(record: dict[str, Any]) -> bool:
    integrity = record.get("integrity") if isinstance(record.get("integrity"), dict) else {}
    history_sources = record.get("history_sources") if isinstance(record.get("history_sources"), dict) else {}
    return (
        integrity.get("partial_historical_record") is True
        or history_sources.get("reconstructed") is True
        or integrity.get("analysis_ready") is False
        or record.get("decision_source") == "postmortem_sync"
        or record.get("close_only_record") is True
    )


def build_source_quality(closed: list[dict[str, Any]]) -> dict[str, Any]:
    closed_count = len(closed)
    contaminated_count = sum(1 for record in closed if is_contaminated_lifecycle_record(record))
    contamination_rate = round(contaminated_count / closed_count, 4) if closed_count else 0.0
    if not closed_count:
        status = "missing"
    elif contaminated_count:
        status = "contaminated"
    else:
        status = "reliable"
    quality = {
        "source": "trade_lifecycle.json",
        "status": status,
        "closed_records": closed_count,
        "contaminated_records": contaminated_count,
        "contamination_rate": contamination_rate,
    }
    if status == "contaminated":
        quality["warning"] = P_L_CONTAMINATION_WARNING
    return quality


def summarize_cash_flows(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "wallet_cash_flows.jsonl"
    exists, total_rows, rows, read_reasons = load_cash_flow_jsonl(path)
    snapshot_rows = load_jsonl(data_dir / "wallet_portfolio_snapshots.jsonl", limit=5000)
    snapshots = sorted_valid_wallet_snapshots(snapshot_rows)
    latest_at = snapshot_at(snapshots[-1]) if snapshots else None
    window_start = latest_at - timedelta(hours=REQUIRED_WALLET_HISTORY_HOURS) if latest_at else None
    coverage_window = (
        {
            "start": window_start.isoformat().replace("+00:00", "Z"),
            "end": latest_at.isoformat().replace("+00:00", "Z"),
        }
        if latest_at and window_start
        else None
    )

    base = {
        "source": "wallet_cash_flows.jsonl",
        "status": "missing",
        "n_records": 0,
        "n_records_total": 0,
        "n_records_valid": 0,
        "n_records_rejected": 0,
        "coverage_days_7d": 0,
        "coverage_window": coverage_window,
        "rejection_reasons": [],
        "attestation_count": 0,
        "last_attestation_at": None,
    }
    if not exists:
        return base
    base["n_records"] = total_rows
    base["n_records_total"] = total_rows
    if total_rows == 0:
        base["status"] = "empty_unattested"
        return base

    valid_rows: list[dict[str, Any]] = []
    rejection_reasons = list(read_reasons)
    example_rejections = 0
    for row in rows:
        valid_row, reasons = validate_cash_flow_row(row)
        if valid_row is None:
            rejection_reasons.extend(reasons)
            if "example_id" in reasons or "example_marker" in reasons:
                example_rejections += 1
            continue
        valid_rows.append(valid_row)

    rejected = total_rows - len(valid_rows)
    base["n_records_valid"] = len(valid_rows)
    base["n_records_rejected"] = rejected
    base["rejection_reasons"] = unique_short(rejection_reasons)
    attestations = [row for row in valid_rows if row["type"] == "no_cash_flow_attestation"]
    base["attestation_count"] = len(attestations)
    if attestations:
        last = max(row["recorded_at"] for row in attestations if row["recorded_at"])
        base["last_attestation_at"] = last.isoformat().replace("+00:00", "Z")

    if not valid_rows:
        base["status"] = "rejected_examples_only" if example_rejections == total_rows else "invalid"
        return base
    if latest_at is None or window_start is None:
        base["status"] = "attested_partial"
        return base

    coverage_intervals: list[tuple[datetime, datetime]] = []
    explaining_intervals: list[tuple[datetime, datetime]] = []
    pending_review = False
    for row in valid_rows:
        start = row["period_start"]
        end = row["period_end"]
        if not start or not end:
            continue
        if interval_overlaps(start, end, window_start, latest_at):
            explaining_intervals.append((start, end))
            if row["review_required"]:
                pending_review = True
            if row["type"] == "no_cash_flow_attestation":
                coverage_intervals.append((max(start, window_start), min(end, latest_at)))

    coverage_seconds, contiguous = merged_coverage_seconds(coverage_intervals)
    full_seconds = REQUIRED_WALLET_HISTORY_HOURS * 3600
    coverage_days = min(7.0, coverage_seconds / 86400)
    base["coverage_days_7d"] = int(coverage_days) if coverage_days.is_integer() else round(coverage_days, 3)

    full_coverage = (
        contiguous
        and coverage_seconds >= full_seconds
        and bool(coverage_intervals)
        and min(start for start, _ in coverage_intervals) <= window_start
        and max(end for _, end in coverage_intervals) >= latest_at
    )
    possible_unexplained = False
    for row in snapshots:
        row_at = snapshot_at(row)
        if row.get("possible_deposit") is not True or row_at is None:
            continue
        if row_at < window_start or row_at > latest_at:
            continue
        explained = any(start <= row_at <= end for start, end in explaining_intervals)
        if not explained:
            possible_unexplained = True
            break

    if pending_review or possible_unexplained:
        base["status"] = "unreconciled"
    elif full_coverage:
        base["status"] = "attested_full_7d"
    else:
        base["status"] = "attested_partial"
    return base


def summarize_wallet_pnl(data_dir: Path, cash_flows: dict[str, Any]) -> dict[str, Any]:
    path = data_dir / "wallet_portfolio_snapshots.jsonl"
    rows = load_jsonl(path, limit=5000)
    snapshot_file_present = path.exists() or bool(rows)
    valid = sorted_valid_wallet_snapshots(rows)
    latest = valid[-1] if valid else None
    oldest_at = snapshot_at(valid[0]) if valid else None
    latest_at = snapshot_at(latest) if latest else None
    span_hours = 0.0
    if oldest_at and latest_at:
        span_hours = max(0.0, (latest_at - oldest_at).total_seconds() / 3600)
    valid_days = len({(snapshot_at(row) or datetime.min.replace(tzinfo=timezone.utc)).date().isoformat() for row in valid})

    baseline = None
    if latest_at:
        cutoff = latest_at - timedelta(hours=REQUIRED_WALLET_HISTORY_HOURS)
        candidates = [
            row for row in valid
            if (snapshot_at(row) or latest_at) <= cutoff
        ]
        if candidates:
            baseline = candidates[-1]

    possible_recent = 0
    if latest_at:
        recent_cutoff = latest_at - timedelta(hours=REQUIRED_WALLET_HISTORY_HOURS)
        possible_recent = sum(
            1
            for row in valid
            if row.get("possible_deposit") is True
            and (snapshot_at(row) or latest_at) >= recent_cutoff
        )

    wallet_pnl_available = False
    wallet_pnl_7d = None
    wallet_pnl_method = "insufficient_history"
    wallet_pnl_confidence = "unavailable"
    if not snapshot_file_present or latest is None:
        wallet_pnl_method = "api_unavailable"
    elif baseline is not None:
        latest_total = as_float(latest.get("total_value"))
        baseline_total = as_float(baseline.get("total_value"))
        if latest_total is not None and baseline_total is not None and cash_flows.get("status") == "attested_full_7d":
            wallet_pnl_available = True
            wallet_pnl_7d = round(latest_total - baseline_total, 2)
            wallet_pnl_method = "snapshot_delta"
            wallet_pnl_confidence = "low" if possible_recent else "medium"

    if not snapshot_file_present:
        status = "missing"
        reason = "cash_flow_unknown" if cash_flows.get("status") != "attested_full_7d" else "missing"
    elif latest is None:
        status = "blocked"
        reason = "missing"
    elif cash_flows.get("status") != "attested_full_7d":
        status = "accumulating"
        reason = "cash_flow_unknown"
    elif span_hours < REQUIRED_WALLET_HISTORY_HOURS:
        status = "accumulating"
        reason = "need_more_history"
    elif baseline is None:
        status = "accumulating"
        reason = "need_7d_baseline"
    else:
        status = "ready"
        reason = "valid_7d_baseline_available"

    phase2_ready = bool(
        status == "ready"
        and wallet_pnl_available
        and len(valid) >= 14
        and valid_days >= 7
    )
    if not phase2_ready and reason == "valid_7d_baseline_available":
        reason = "need_more_history"

    return {
        "status": status,
        "source": "wallet_portfolio_snapshots.jsonl",
        "phase2_ready": phase2_ready,
        "phase2_ready_reason": reason,
        "valid_snapshots": len(valid),
        "valid_snapshot_days": valid_days,
        "history_span_hours": round(span_hours, 2),
        "required_history_hours": REQUIRED_WALLET_HISTORY_HOURS,
        "wallet_pnl_available": wallet_pnl_available and phase2_ready,
        "wallet_pnl_7d": wallet_pnl_7d if phase2_ready else None,
        "wallet_pnl_method": wallet_pnl_method if phase2_ready else ("api_unavailable" if status == "missing" else "insufficient_history"),
        "wallet_pnl_confidence": wallet_pnl_confidence if phase2_ready else "unavailable",
    }


def summarize_pnl_sources(data_dir: Path, profitability: dict[str, Any]) -> dict[str, Any]:
    source_quality = profitability.get("source_quality") or build_source_quality([])
    cash_flows = summarize_cash_flows(data_dir)
    wallet_pnl = summarize_wallet_pnl(data_dir, cash_flows)
    lifecycle = {
        "status": source_quality.get("status", "missing"),
        "source": "trade_lifecycle.json",
        "closed_records": source_quality.get("closed_records", 0),
        "contaminated_records": source_quality.get("contaminated_records", 0),
        "contamination_rate": source_quality.get("contamination_rate", 0.0),
        "operational_use": "untrusted_only"
        if source_quality.get("status") == "contaminated"
        else "audit_only",
    }
    return {
        "lifecycle": lifecycle,
        "wallet_pnl": wallet_pnl,
        "cash_flows": cash_flows,
        "dashboard": {
            "status": "manual_only",
            "source": "Polymarket dashboard",
            "auto_extractor_authorized": False,
        },
        "canonical_source": "none",
        "bankroll_readiness": "blocked",
    }


def summarize_operational(data_dir: Path, generated_at: datetime) -> dict[str, Any]:
    cycles = load_jsonl(data_dir / "cycles_history.jsonl")
    agent_events = load_jsonl(data_dir / "agent_events.jsonl")
    rows = cycles or agent_events
    recent_rows = []
    cutoff = generated_at - timedelta(days=1)
    for row in rows:
        ts = parse_ts(row.get("timestamp_utc") or row.get("ts_utc") or row.get("timestamp") or row.get("created_at"))
        if ts and ts >= cutoff:
            recent_rows.append(row)

    version = "unknown"
    mode = "unknown"
    bot_status = "unknown"
    if rows:
        latest = rows[-1]
        version = str(latest.get("bot_version") or latest.get("version") or "unknown")
        mode = str(latest.get("mode") or latest.get("bot_mode") or "unknown")
        bot_status = str(latest.get("status") or "data_available")

    status = "NO_ACTION" if rows else "WATCH_TECH"
    return {
        "title": "Estado operativo",
        "level": status,
        "status": bot_status,
        "bot_status": bot_status,
        "version": version,
        "mode": mode,
        "recent_cycles_24h": len(recent_rows) if rows else None,
        "source": "cycles_history.jsonl" if cycles else ("agent_events.jsonl" if agent_events else "missing"),
    }


def summarize_profitability(data_dir: Path, generated_at: datetime) -> dict[str, Any]:
    lifecycle = load_json(data_dir / "trade_lifecycle.json")
    records = normalize_records(lifecycle)
    if not records:
        source_quality = build_source_quality([])
        return {
            "title": "P/L / Profitability",
            "level": "WATCH_RISK",
            "status": "data_missing",
            "windows": {"1d": None, "7d": None, "30d": None, "all": None},
            "source_quality": source_quality,
            "note": "No hay datos fiables de lifecycle en disco local.",
        }

    closed = [
        record for record in records
        if record.get("status") == "closed" and record_pnl(record) is not None
    ]

    def stats(days: int | None) -> dict[str, Any]:
        selected = closed
        if days is not None:
            cutoff = generated_at - timedelta(days=days)
            selected = [record for record in closed if (record_closed_at(record) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
        pnl = round(sum(record_pnl(record) or 0.0 for record in selected), 2)
        wins = sum(1 for record in selected if (record_pnl(record) or 0.0) > 0)
        losses = sum(1 for record in selected if (record_pnl(record) or 0.0) < 0)
        total = len(selected)
        return {
            "n": total,
            "wins": wins,
            "losses": losses,
            "pnl": pnl,
            "wr": round(wins / total * 100.0, 1) if total else None,
        }

    windows = {
        "1d": stats(1),
        "7d": stats(7),
        "30d": stats(30),
        "all": stats(None),
    }
    source_quality = build_source_quality(closed)
    level = "WATCH_RISK" if not closed or source_quality["status"] == "contaminated" else "NO_ACTION"
    note = "No interpretar P/L contaminado como mejora limpia."
    return {
        "title": "P/L / Profitability",
        "level": level,
        "status": "ok" if closed else "data_missing",
        "windows": windows,
        "open_positions": sum(1 for record in records if record.get("status") == "open"),
        "source_quality": source_quality,
        "note": note,
    }


def summarize_activity(data_dir: Path, generated_at: datetime) -> dict[str, Any]:
    lifecycle = load_json(data_dir / "trade_lifecycle.json")
    records = normalize_records(lifecycle)
    cycles = load_jsonl(data_dir / "cycles_history.jsonl")
    cutoff_7d = generated_at - timedelta(days=7)
    recent_cycles = []
    for row in cycles:
        ts = parse_ts(row.get("timestamp_utc") or row.get("ts_utc") or row.get("timestamp") or row.get("created_at"))
        if ts and ts >= cutoff_7d:
            recent_cycles.append(row)

    recent_entries = []
    open_positions = 0
    if records:
        open_positions = sum(1 for record in records if record.get("status") == "open")
        for record in records:
            opened_at = parse_ts(record.get("opened_at") or record.get("created_at"))
            side = str(record.get("side") or "").lower()
            if opened_at and opened_at >= cutoff_7d and side in {"yes", "no", "buy"}:
                recent_entries.append(record)

    if not records and not cycles:
        return {
            "title": "Actividad",
            "level": "WATCH",
            "status": "data_missing",
            "recent_cycles_7d": None,
            "recent_entries_7d": None,
            "open_positions": None,
            "note": "Sin datos locales; no se infiere problema operativo.",
        }

    low_activity = bool(cycles and len(recent_cycles) == 0)
    return {
        "title": "Actividad",
        "level": "WATCH" if low_activity else "NO_ACTION",
        "status": "watch_low_activity" if low_activity else "ok",
        "recent_cycles_7d": len(recent_cycles) if cycles else None,
        "recent_entries_7d": len(recent_entries) if records else None,
        "open_positions": open_positions if records else None,
        "note": "Baja actividad implica observacion, no accion." if low_activity else "Sin accion requerida.",
    }


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def view_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='view' AND name=?", (name,)
    ).fetchone()
    return row is not None


def summarize_truth_pipeline(db_path: str | None) -> dict[str, Any]:
    if not db_path:
        return {
            "title": "Truth Pipeline",
            "level": "WATCH_TECH",
            "status": "unknown",
            "db_path": None,
            "truth_records": None,
            "n_resolved": None,
            "calibration_global": None,
            "disclaimer": DISCLAIMER_CALIBRATION,
        }

    path = Path(db_path)
    if not path.exists():
        return {
            "title": "Truth Pipeline",
            "level": "WATCH_TECH",
            "status": "schema_missing",
            "db_path": str(path),
            "truth_records": None,
            "n_resolved": None,
            "calibration_global": None,
            "detail": "db_not_found",
            "disclaimer": DISCLAIMER_CALIBRATION,
        }

    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        return {
            "title": "Truth Pipeline",
            "level": "WATCH_TECH",
            "status": "unknown",
            "db_path": str(path),
            "detail": str(exc),
            "truth_records": None,
            "n_resolved": None,
            "calibration_global": None,
            "disclaimer": DISCLAIMER_CALIBRATION,
        }

    try:
        if not table_exists(conn, "truth_records"):
            return {
                "title": "Truth Pipeline",
                "level": "WATCH_TECH",
                "status": "schema_missing",
                "db_path": str(path),
                "truth_records": None,
                "n_resolved": None,
                "calibration_global": None,
                "disclaimer": DISCLAIMER_CALIBRATION,
            }

        truth_records = conn.execute("SELECT COUNT(*) FROM truth_records").fetchone()[0]
        outcome_rows = conn.execute(
            "SELECT resolution_outcome, COUNT(*) AS n FROM truth_records GROUP BY resolution_outcome"
        ).fetchall()
        outcomes = {row["resolution_outcome"]: row["n"] for row in outcome_rows}
        n_resolved = outcomes.get("YES", 0) + outcomes.get("NO", 0)
        calibration_global = None
        status = "empty" if truth_records == 0 else "no_action"
        if view_exists(conn, "v_decision_truth"):
            try:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS n, SUM(CASE WHEN forecast_correct = 1 THEN 1 ELSE 0 END) AS ok
                    FROM v_decision_truth
                    WHERE forecast_correct IS NOT NULL
                    """
                ).fetchone()
                if row and row["n"]:
                    calibration_global = round(row["ok"] / row["n"], 3)
            except sqlite3.Error:
                status = "schema_missing"

        return {
            "title": "Truth Pipeline",
            "level": "NO_ACTION" if status == "no_action" else "WATCH_TECH",
            "status": status,
            "db_path": str(path),
            "truth_records": truth_records,
            "n_resolved": n_resolved,
            "calibration_global": calibration_global,
            "disclaimer": DISCLAIMER_CALIBRATION,
        }
    except sqlite3.Error as exc:
        return {
            "title": "Truth Pipeline",
            "level": "WATCH_TECH",
            "status": "schema_missing",
            "db_path": str(path),
            "detail": str(exc),
            "truth_records": None,
            "n_resolved": None,
            "calibration_global": None,
            "disclaimer": DISCLAIMER_CALIBRATION,
        }
    finally:
        conn.close()


def summarize_kanban(data_dir: Path) -> dict[str, Any]:
    state = load_json(data_dir / "kanban_state.json")
    columns: dict[str, list[Any]] = {column: [] for column in KANBAN_COLUMNS}
    source = "synthetic_default"
    if isinstance(state, dict):
        raw_columns = state.get("columns") if isinstance(state.get("columns"), dict) else state
        for column in KANBAN_COLUMNS:
            value = raw_columns.get(column) if isinstance(raw_columns, dict) else None
            if isinstance(value, list):
                columns[column] = value
        source = "kanban_state.json"
    else:
        columns["WATCH"] = ["Daily digest dry-run: observar sin activar runtime."]
        columns["SAFETY"] = []

    return {
        "title": "Kanban",
        "level": "NO_ACTION",
        "status": "ok",
        "source": source,
        "columns": columns,
    }


def build_digest(data_dir: Path, db_path: str | None = None) -> dict[str, Any]:
    generated_at = now_utc()
    profitability = summarize_profitability(data_dir, generated_at)
    sections = {
        "operational": summarize_operational(data_dir, generated_at),
        "profitability": profitability,
        "activity": summarize_activity(data_dir, generated_at),
        "truth_pipeline": summarize_truth_pipeline(db_path),
        "kanban": summarize_kanban(data_dir),
    }
    level = level_max(*(section.get("level", "NO_ACTION") for section in sections.values()))
    next_step = next_step_for_level(level)
    return {
        "generated_at_utc": generated_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "level": level,
        "sections": sections,
        "pnl_sources": summarize_pnl_sources(data_dir, profitability),
        "next_step": next_step,
        "disclaimers": [DISCLAIMER_NO_TRADING, DISCLAIMER_CALIBRATION],
        "would_send": False,
    }


def next_step_for_level(level: str) -> str:
    if level == "NO_ACTION":
        return "Siguiente paso concreto: ninguno; continuar observacion."
    if level == "WATCH_RISK":
        return "Siguiente paso concreto: revisar datos de P/L y separar datos contaminados de lectura limpia."
    if level == "WATCH_TECH":
        return "Siguiente paso concreto: revisar disponibilidad local de DB/datos antes de interpretar el digest."
    if level == "ACTION_SAFETY":
        return "Siguiente paso concreto: escalar revision manual de seguridad."
    return "Siguiente paso concreto: revisar evidencia y documentar hallazgos antes de implementar cambios."


def format_window(label: str, value: dict[str, Any] | None) -> str:
    if not value:
        return f"  - {label}: unknown"
    wr = value.get("wr")
    wr_text = "unknown" if wr is None else f"{wr:.1f}%"
    return f"  - {label}: P/L {money(value.get('pnl'))} | WR {wr_text} | n={value.get('n', 0)}"


def format_human(digest: dict[str, Any]) -> str:
    sections = digest["sections"]
    pnl_sources = digest.get("pnl_sources") or {}
    op = sections["operational"]
    pnl = sections["profitability"]
    activity = sections["activity"]
    truth = sections["truth_pipeline"]
    kanban = sections["kanban"]
    source_quality = pnl.get("source_quality") or {}
    lifecycle_source = pnl_sources.get("lifecycle") or {}
    wallet_source = pnl_sources.get("wallet_pnl") or {}
    cash_flow_source = pnl_sources.get("cash_flows") or {}
    dashboard_source = pnl_sources.get("dashboard") or {}
    quality_rate = source_quality.get("contamination_rate")
    quality_rate_text = "unknown" if quality_rate is None else f"{quality_rate * 100.0:.1f}%"

    lines = [
        f"Daily Bot Kanban Digest - {digest['generated_at_utc']}",
        f"Nivel: {digest['level']}",
        "Modo: dry-run / LOG_ONLY / default OFF",
        f"would_send: {str(digest['would_send']).lower()}",
        "",
        "1. Estado operativo",
        f"  - Bot status: {display(op.get('bot_status'))}",
        f"  - Version: {display(op.get('version'))}",
        f"  - Modo bot: {display(op.get('mode'))}",
        f"  - Ciclos recientes 24h: {display(op.get('recent_cycles_24h'))}",
        "",
        "2. P/L / Profitability",
        f"  - Status: {pnl.get('status', 'unknown')}",
        format_window("1D", (pnl.get("windows") or {}).get("1d")),
        format_window("7D", (pnl.get("windows") or {}).get("7d")),
        format_window("30D", (pnl.get("windows") or {}).get("30d")),
        format_window("All", (pnl.get("windows") or {}).get("all")),
        (
            f"  - Calidad fuente: {source_quality.get('status', 'unknown')} "
            f"({source_quality.get('contaminated_records', 0)}/"
            f"{source_quality.get('closed_records', 0)} registros; rate {quality_rate_text})"
        ),
        f"  - Warning: {source_quality['warning']}" if source_quality.get("warning") else None,
        f"  - Nota: {pnl.get('note', 'unknown')}",
        "",
        "2b. P/L Sources",
        (
            f"  - Lifecycle: {lifecycle_source.get('status', 'unknown')} | "
            f"{lifecycle_source.get('operational_use', 'audit_only')} | "
            f"{lifecycle_source.get('contaminated_records', 0)}/"
            f"{lifecycle_source.get('closed_records', 0)} contaminated"
        ),
        (
            f"  - Wallet 7d: {wallet_source.get('status', 'unknown')} | "
            f"phase2_ready={str(wallet_source.get('phase2_ready', False)).lower()} | "
            f"reason={wallet_source.get('phase2_ready_reason', 'unknown')} | "
            f"snapshots={wallet_source.get('valid_snapshots', 0)} | "
            f"days={wallet_source.get('valid_snapshot_days', 0)} | "
            f"span_h={wallet_source.get('history_span_hours', 0.0)}"
        ),
        (
            f"  - Wallet P/L available: "
            f"{str(wallet_source.get('wallet_pnl_available', False)).lower()} | "
            f"method={wallet_source.get('wallet_pnl_method', 'unknown')} | "
            f"confidence={wallet_source.get('wallet_pnl_confidence', 'unknown')}"
        ),
        (
            f"  - Cash flows: {cash_flow_source.get('status', 'unknown')} | "
            f"records={cash_flow_source.get('n_records', 0)}"
        ),
        (
            f"  - Dashboard: {dashboard_source.get('status', 'unknown')} | "
            f"auto_extractor_authorized="
            f"{str(dashboard_source.get('auto_extractor_authorized', False)).lower()}"
        ),
        f"  - Canonical source: {pnl_sources.get('canonical_source', 'none')}",
        f"  - BANKROLL ready: {pnl_sources.get('bankroll_readiness', 'blocked')}",
        "",
        "3. Actividad",
        f"  - Ciclos recientes 7d: {display(activity.get('recent_cycles_7d'))}",
        f"  - Compras recientes 7d: {display(activity.get('recent_entries_7d'))}",
        f"  - Operaciones abiertas: {display(activity.get('open_positions'))}",
        f"  - Lectura: {activity.get('note', 'unknown')}",
        "",
        "4. Truth Pipeline",
        f"  - Status: {display(truth.get('status'))}",
        f"  - truth_records: {display(truth.get('truth_records'))}",
        f"  - n_resolved: {display(truth.get('n_resolved'))}",
        f"  - calibration_global: {display(truth.get('calibration_global'))}",
        f"  - Disclaimer: {DISCLAIMER_CALIBRATION}",
        "",
        "5. Kanban",
    ]
    for column in KANBAN_COLUMNS:
        items = kanban["columns"].get(column) or []
        if not items:
            value = "0"
        else:
            rendered = []
            for item in items[:3]:
                if isinstance(item, dict):
                    rendered.append(str(item.get("title") or item.get("id") or "item"))
                else:
                    rendered.append(str(item))
            value = " | ".join(rendered)
        lines.append(f"  - {column}: {value}")

    lines = [line for line in lines if line is not None]

    lines.extend([
        "",
        DISCLAIMER_NO_TRADING,
        digest["next_step"],
    ])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily Bot Kanban Digest dry-run CLI")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run/read-only mode")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--db", default=None, help="Optional SQLite DB path for Truth Pipeline read-only summary")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Local data directory to inspect")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv)
    dry_run = bool(args.dry_run)
    if not dry_run:
        # First release is still read-only/default OFF even when the flag is omitted.
        dry_run = True
    digest = build_digest(Path(args.data_dir), args.db)
    if args.json:
        print(json.dumps(digest, indent=2, ensure_ascii=False))
    else:
        print(format_human(digest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
