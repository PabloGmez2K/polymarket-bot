#!/usr/bin/env python3
"""
Read-only health check for the Railway Polymarket bot runtime files.

This tool is intentionally standalone: stdlib only, no bot.py import, no
network calls, no Telegram, and no writes to runtime data.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


EXPECTED_TABLES = ["cycle_events", "market_snapshots", "forecast_snapshots"]
DEFAULT_MIN_DAYS = 7
DEFAULT_MIN_CYCLES = 21
DEFAULT_MAX_DB_STALE_HOURS = 30
EXPECTED_CYCLES_PER_DAY = 3
GAP_THRESHOLD_HOURS = 18
RECENT_CYCLE_WINDOW = 40

NORMAL_REJECT_REASONS = {
    "price_out_of_range",
    "date_out_of_range_past",
    "condition_filtered",
    "below_min_edge",
    "fuera_allowlist",
    "liquidity_low",
    "parse_fail",
    "city_window_skipped",
    "blocked_city",
    "shadow_city",
    "shadow_only_mode",
    "no_edge",
}
CRITICAL_EXECUTION_RE = re.compile(
    r"order rejected|insufficient funds|auth failed|api[-_ ]?key|not enough balance|allowance",
    re.IGNORECASE,
)
CRITICAL_LOG_RE = re.compile(
    r"Traceback|cycle crash|SQLiteRecorder error|order rejected|insufficient funds|auth failed",
    re.IGNORECASE,
)
WARNING_LOG_RE = re.compile(r"\bWARNING\b|Forecast.*502|city intelligence", re.IGNORECASE)
AUTH_OK_RE = re.compile(r"Autenticaci[oó]n OK|Authentication OK", re.IGNORECASE)
OBSERVABILITY_LOG_RE = re.compile(
    r"traders intelligence summary|traders_intelligence_daily_summary\.py|city[-_ ]intelligence",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize bot runtime health from local/Railway data files."
    )
    parser.add_argument("--data-dir", default="data", help="Runtime data directory.")
    parser.add_argument("--db", default="data/polymarket.db", help="Path to polymarket.db.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown output.")
    parser.add_argument(
        "--max-cycle-age-hours",
        type=float,
        default=6,
        help="Maximum age for cycle_summary.json before ACTION.",
    )
    parser.add_argument(
        "--log-tail",
        type=int,
        default=200,
        help="Lines to inspect from decisions.log and trades.log.",
    )
    return parser.parse_args()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value <= 0:
            return None
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for candidate in (text, text.replace(" UTC", "+00:00")):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(text[:26], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def age_hours(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return round((now_utc() - dt).total_seconds() / 3600, 2)


def fmt_age(hours: float | None) -> str:
    if hours is None:
        return "unknown"
    if hours < 1:
        return f"{max(0, int(hours * 60))} min"
    if hours < 48:
        return f"{hours:.1f} h"
    return f"{hours / 24:.1f} days"


def read_json(path: Path) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh), None
    except Exception as exc:
        return None, f"read_error: {exc}"


def tail_lines(path: Path, limit: int) -> tuple[list[str], str | None]:
    if not path.exists():
        return [], "missing"
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        return [line.rstrip("\n") for line in lines[-max(0, limit):]], None
    except Exception as exc:
        return [], f"read_error: {exc}"


def read_jsonl_tail(path: Path, limit: int) -> tuple[list[dict[str, Any]], str | None]:
    lines, err = tail_lines(path, limit)
    if err:
        return [], err
    records: list[dict[str, Any]] = []
    malformed = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                records.append(parsed)
        except json.JSONDecodeError:
            malformed += 1
    return records, f"malformed_lines={malformed}" if malformed else None


def first_present(data: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def find_nested(data: Any, target_keys: set[str]) -> Any:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in target_keys and value not in (None, ""):
                return value
        for value in data.values():
            found = find_nested(value, target_keys)
            if found is not None:
                return found
    elif isinstance(data, list):
        for value in data:
            found = find_nested(value, target_keys)
            if found is not None:
                return found
    return None


def count_from_any(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        total = 0
        for item in value.values():
            total += count_from_any(item)
        return total
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def counter_from_any(value: Any) -> dict[str, int]:
    counter: Counter[str] = Counter()
    if isinstance(value, dict):
        for key, item in value.items():
            counter[str(key)] += count_from_any(item)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                counter[item] += 1
            elif isinstance(item, dict):
                reason = first_present(item, ["reason", "reject_reason", "code", "error"])
                if reason:
                    counter[str(reason)] += 1
    elif isinstance(value, str) and value:
        counter[value] += 1
    return dict(counter.most_common(8))


def is_normal_reject_reason(reason: str) -> bool:
    return reason.strip().lower() in NORMAL_REJECT_REASONS


def is_observability_log_line(line: str) -> bool:
    return bool(OBSERVABILITY_LOG_RE.search(line))


def add_issue(issues: list[dict[str, str]], status: str, reason: str, detail: str = "") -> None:
    issues.append({"status": status, "reason": reason, "detail": detail})


def worst_status(statuses: list[str]) -> str:
    rank = {"OK": 0, "INFO": 0, "UNKNOWN": 1, "WATCH": 2, "ACTION": 3}
    worst = "OK"
    for status in statuses:
        if rank.get(status, 0) > rank.get(worst, 0):
            worst = status
    return "WATCH" if worst == "UNKNOWN" else worst


def summarize_runtime(data_dir: Path, max_cycle_age_hours: float, issues: list[dict[str, str]]) -> dict[str, Any]:
    path = data_dir / "cycle_summary.json"
    raw, err = read_json(path)
    result: dict[str, Any] = {
        "path": str(path),
        "exists": err is None,
        "version": None,
        "mode": None,
        "last_cycle_ts": None,
        "last_cycle_age_hours": None,
        "cycle_number": None,
        "recent": False,
        "status": "UNKNOWN",
        "error": err,
    }
    if not isinstance(raw, dict):
        add_issue(issues, "WATCH", "cycle_summary unavailable", err or "not a JSON object")
        return result

    ts_value = first_present(
        raw,
        ["timestamp_utc", "ts_utc", "cycle_ts", "finished_at", "generated_at", "timestamp", "last_cycle_ts"],
    )
    if ts_value is None:
        ts_value = find_nested(raw, {"timestamp_utc", "ts_utc", "finished_at", "generated_at"})
    ts = parse_ts(ts_value)
    age = age_hours(ts)
    recent = age is not None and age <= max_cycle_age_hours
    result.update(
        {
            "version": first_present(raw, ["bot_version", "version", "BOT_VERSION"]),
            "mode": first_present(raw, ["mode", "run_mode", "trading_mode"]),
            "last_cycle_ts": ts.isoformat() if ts else ts_value,
            "last_cycle_age_hours": age,
            "cycle_number": first_present(raw, ["cycle_number", "cycle", "cycle_id"]),
            "recent": recent,
            "status": "OK" if recent else "ACTION",
            "error": None,
        }
    )
    if not recent:
        add_issue(issues, "ACTION", "last cycle stale", f"age={fmt_age(age)}, threshold={max_cycle_age_hours}h")
    return result


def summarize_cycles(data_dir: Path, issues: list[dict[str, str]]) -> dict[str, Any]:
    path = data_dir / "cycles_history.jsonl"
    records, err = read_jsonl_tail(path, RECENT_CYCLE_WINDOW)
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "records_tail": len(records),
        "last_cycle_ts": None,
        "last_cycle_age_hours": None,
        "last_cycle_finished": None,
        "large_gaps": [],
        "status": "OK" if records else "WATCH",
        "error": err,
    }
    if not records:
        add_issue(issues, "WATCH", "cycles_history has no readable records", err or "empty/missing")
        return result

    timestamps: list[datetime] = []
    for rec in records:
        ts = parse_ts(first_present(rec, ["timestamp_utc", "ts_utc", "finished_at", "generated_at", "timestamp"]))
        if ts:
            timestamps.append(ts)
    timestamps.sort()
    last_ts = timestamps[-1] if timestamps else None
    last_age = age_hours(last_ts)
    gaps = []
    for prev, curr in zip(timestamps, timestamps[1:]):
        gap_hours = (curr - prev).total_seconds() / 3600
        if gap_hours > GAP_THRESHOLD_HOURS:
            gaps.append({"from": prev.isoformat(), "to": curr.isoformat(), "gap_hours": round(gap_hours, 1)})

    last = records[-1]
    finished_value = first_present(last, ["finished", "completed", "cycle_finished", "success"])
    if finished_value is None:
        status_text = str(first_present(last, ["status", "result", "exit_status"]) or "").lower()
        finished_value = status_text in {"ok", "success", "completed", "finished"}

    result.update(
        {
            "last_cycle_ts": last_ts.isoformat() if last_ts else None,
            "last_cycle_age_hours": last_age,
            "last_cycle_finished": bool(finished_value),
            "large_gaps": gaps[-5:],
            "status": "WATCH" if gaps else "OK",
        }
    )
    if gaps:
        add_issue(issues, "WATCH", "large cycle gaps detected", f"{len(gaps)} gaps > {GAP_THRESHOLD_HOURS}h")
    return result


def open_db_readonly(db_path: Path) -> sqlite3.Connection:
    uri = db_path.resolve().as_posix()
    con = sqlite3.connect(f"file:{uri}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    return con


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def first_existing_column(con: sqlite3.Connection, table: str, candidates: list[str]) -> str | None:
    cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
    for candidate in candidates:
        if candidate in cols:
            return candidate
    return None


def count_rows(con: sqlite3.Connection, table: str) -> int | None:
    try:
        return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.Error:
        return None


def summarize_db(db_path: Path, issues: list[dict[str, str]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(db_path),
        "exists": db_path.exists(),
        "readable": False,
        "tables": {name: False for name in EXPECTED_TABLES},
        "row_counts": {},
        "last_write": None,
        "last_write_age_hours": None,
        "recorder_fresh": False,
        "cycles_recorded": 0,
        "large_gaps": [],
        "readiness": {
            "cycles_actual": 0,
            "cycles_required": DEFAULT_MIN_CYCLES,
            "days_actual": 0.0,
            "days_required": DEFAULT_MIN_DAYS,
            "recorder_fresh": False,
            "no_large_gaps": False,
            "eta_date": None,
            "ready": False,
        },
        "status": "WATCH",
        "error": None,
    }
    if not db_path.exists():
        add_issue(issues, "WATCH", "polymarket.db missing", str(db_path))
        result["error"] = "missing"
        return result

    try:
        con = open_db_readonly(db_path)
    except sqlite3.Error as exc:
        add_issue(issues, "ACTION", "cannot read polymarket.db", str(exc))
        result.update({"status": "ACTION", "error": str(exc)})
        return result

    try:
        tables = {name: table_exists(con, name) for name in EXPECTED_TABLES}
        result["tables"] = tables
        if not all(tables.values()):
            missing = [name for name, ok in tables.items() if not ok]
            add_issue(issues, "ACTION", "SQLiteRecorder tables missing", ", ".join(missing))
            result["status"] = "ACTION"
            return result

        row_counts = {name: count_rows(con, name) for name in EXPECTED_TABLES}
        cycle_total = int(row_counts.get("cycle_events") or 0)
        result.update({"readable": True, "row_counts": row_counts, "cycles_recorded": cycle_total})

        ts_col = first_existing_column(
            con,
            "cycle_events",
            ["ts_utc", "timestamp_utc", "created_at", "finished_at", "cycle_ts", "timestamp"],
        )
        timestamps: list[datetime] = []
        first_ts = last_ts = None
        if ts_col:
            rows = con.execute(
                f"SELECT {ts_col} FROM cycle_events WHERE {ts_col} IS NOT NULL ORDER BY {ts_col} ASC"
            ).fetchall()
            timestamps = [ts for ts in (parse_ts(row[0]) for row in rows) if ts is not None]
            if timestamps:
                first_ts, last_ts = timestamps[0], timestamps[-1]

        last_age = age_hours(last_ts)
        fresh = last_age is not None and last_age <= DEFAULT_MAX_DB_STALE_HOURS
        gaps = []
        for prev, curr in zip(timestamps, timestamps[1:]):
            gap_hours = (curr - prev).total_seconds() / 3600
            if gap_hours > GAP_THRESHOLD_HOURS:
                gaps.append({"from": prev.isoformat(), "to": curr.isoformat(), "gap_hours": round(gap_hours, 1)})

        days_actual = 0.0
        if first_ts and last_ts:
            days_actual = round((last_ts - first_ts).total_seconds() / 86400, 1)
        cycles_remaining = max(0, DEFAULT_MIN_CYCLES - cycle_total)
        days_remaining = max(0.0, DEFAULT_MIN_DAYS - days_actual)
        eta_date = None
        if cycles_remaining or days_remaining:
            by_cycles = cycles_remaining / EXPECTED_CYCLES_PER_DAY
            eta_days = max(days_remaining, by_cycles)
            eta_date = (now_utc() + timedelta(days=eta_days)).date().isoformat()

        readiness = {
            "cycles_actual": cycle_total,
            "cycles_required": DEFAULT_MIN_CYCLES,
            "days_actual": days_actual,
            "days_required": DEFAULT_MIN_DAYS,
            "recorder_fresh": fresh,
            "no_large_gaps": not gaps,
            "eta_date": eta_date,
            "ready": cycle_total >= DEFAULT_MIN_CYCLES
            and days_actual >= DEFAULT_MIN_DAYS
            and fresh
            and not gaps
            and all((row_counts.get(name) or 0) > 0 for name in EXPECTED_TABLES),
        }
        status = "OK"
        if last_age is None:
            status = "WATCH"
            add_issue(issues, "WATCH", "SQLiteRecorder has no timestamped cycle_events")
        elif not fresh:
            status = "ACTION"
            add_issue(issues, "ACTION", "SQLiteRecorder stale", f"age={fmt_age(last_age)}, threshold=30h")
        elif gaps:
            status = "WATCH"
            add_issue(issues, "WATCH", "SQLiteRecorder large gaps", f"{len(gaps)} gaps > {GAP_THRESHOLD_HOURS}h")
        elif not readiness["ready"]:
            status = "WATCH"
            add_issue(
                issues,
                "WATCH",
                "Phase 1 readiness pending, expected until threshold is reached",
                "more recorder data needed",
            )

        result.update(
            {
                "last_write": last_ts.isoformat() if last_ts else None,
                "last_write_age_hours": last_age,
                "recorder_fresh": fresh,
                "large_gaps": gaps[-5:],
                "readiness": readiness,
                "status": status,
            }
        )
    except sqlite3.Error as exc:
        add_issue(issues, "ACTION", "SQLite read error", str(exc))
        result.update({"status": "ACTION", "error": str(exc)})
    finally:
        con.close()
    return result


def summarize_trading(data_dir: Path, issues: list[dict[str, str]]) -> dict[str, Any]:
    raw, err = read_json(data_dir / "cycle_summary.json")
    summary = raw if isinstance(raw, dict) else {}
    buys = count_from_any(first_present(summary, ["buys", "buy_count", "executed_buys", "orders_bought"]))
    with_edge = count_from_any(first_present(summary, ["with_edge", "edge_count", "candidates_with_edge"]))
    selected = count_from_any(first_present(summary, ["selected", "selected_count", "selected_candidates"]))
    exec_reasons = counter_from_any(
        first_present(summary, ["execution_reject_reasons", "execution_rejects", "buy_execution_reject_reasons"])
    )
    reject_reasons = counter_from_any(first_present(summary, ["reject_reasons", "skip_reasons", "blocked_reasons"]))
    if not reject_reasons:
        reject_reasons = counter_from_any(find_nested(summary, {"reject_reasons", "skip_reasons"}))

    critical_exec = [reason for reason in exec_reasons if CRITICAL_EXECUTION_RE.search(reason)]
    if critical_exec:
        status = "ACTION"
        interpretation = "execution reject reasons include critical errors"
        add_issue(issues, "ACTION", "critical execution rejects", ", ".join(critical_exec))
    elif selected > 0 and buys == 0:
        status = "WATCH"
        interpretation = "selected opportunities but no buys"
        add_issue(issues, "WATCH", "selected>0 but buys=0", f"selected={selected}")
    elif buys == 0 and with_edge == 0 and selected == 0:
        normal_only = not reject_reasons or all(is_normal_reject_reason(reason) for reason in reject_reasons)
        status = "OK" if normal_only else "WATCH"
        interpretation = (
            "no buys because no operable opportunities were selected"
            if normal_only
            else "no buys with non-standard rejects"
        )
        if not normal_only:
            add_issue(issues, "WATCH", "non-standard reject reasons", ", ".join(reject_reasons))
    else:
        status = "OK"
        interpretation = "trading activity present or no execution issue detected"

    return {
        "cycle_summary_available": isinstance(raw, dict) and err is None,
        "buys_last_cycle": buys,
        "with_edge": with_edge,
        "selected": selected,
        "execution_reject_reasons": exec_reasons,
        "main_reject_reasons": reject_reasons,
        "interpretation": interpretation,
        "status": status,
    }


def summarize_positions(data_dir: Path) -> dict[str, Any]:
    cycle_raw, _ = read_json(data_dir / "cycle_summary.json")
    lifecycle_raw, lifecycle_err = read_json(data_dir / "trade_lifecycle.json")
    postmortem_raw, postmortem_err = read_json(data_dir / "postmortem.json")
    active_count = 0
    sources: list[str] = []
    if isinstance(cycle_raw, dict):
        value = first_present(cycle_raw, ["active_positions", "open_positions", "positions_open", "positions"])
        active_count = max(active_count, count_from_any(value))
        if value is not None:
            sources.append("cycle_summary")
    if isinstance(lifecycle_raw, dict):
        active = first_present(lifecycle_raw, ["open_positions", "active_positions", "positions_open"])
        active_count = max(active_count, count_from_any(active))
        if active is not None:
            sources.append("trade_lifecycle")
    return {
        "active_positions": active_count,
        "status": "OK",
        "sources": sources,
        "trade_lifecycle": "available" if lifecycle_err is None else lifecycle_err,
        "postmortem": "available" if postmortem_err is None else postmortem_err,
        "interpretation": "active positions present" if active_count else "0 positions reported",
    }


def summarize_optional_files(data_dir: Path) -> dict[str, Any]:
    out = {}
    for name in ["signals.json", "trade_lifecycle.json", "postmortem.json"]:
        path = data_dir / name
        raw, err = read_json(path)
        out[name] = {"exists": path.exists(), "readable": err is None, "error": err, "type": type(raw).__name__ if raw is not None else None}
    return out


def summarize_logs(data_dir: Path, log_tail: int, issues: list[dict[str, str]]) -> dict[str, Any]:
    result = {
        "tail_lines": log_tail,
        "files": {},
        "errors": [],
        "warnings": [],
        "known_noise": [],
        "critical": [],
        "status": "OK",
    }
    combined: list[str] = []
    for name in ["decisions.log", "trades.log"]:
        path = data_dir / name
        lines, err = tail_lines(path, log_tail)
        result["files"][name] = {"exists": path.exists(), "lines_read": len(lines), "error": err}
        combined.extend(f"{name}: {line}" for line in lines)
        if err:
            result["warnings"].append(f"{name}: {err}")

    auth_ok_seen = any(AUTH_OK_RE.search(line) for line in combined)
    traceback_count = 0
    sqlite_error_count = 0
    forecast_502_count = 0
    for line in combined:
        line_lower = line.lower()
        observability_line = is_observability_log_line(line)
        if "traceback" in line_lower and not observability_line:
            traceback_count += 1
        if "sqliterecorder error" in line_lower:
            sqlite_error_count += 1
        if "traceback" in line_lower and observability_line:
            result["warnings"].append(line[-220:])
            continue
        if "forecast" in line_lower and "502" in line_lower:
            forecast_502_count += 1
            result["known_noise"].append(line[-220:])
            continue
        if ("auth" in line_lower or "api-key" in line_lower) and "400" in line_lower and auth_ok_seen:
            result["known_noise"].append(line[-220:])
            continue
        if CRITICAL_LOG_RE.search(line):
            result["critical"].append(line[-220:])
        elif "error" in line_lower:
            result["errors"].append(line[-220:])
        elif WARNING_LOG_RE.search(line):
            result["warnings"].append(line[-220:])

    if traceback_count >= 2 or sqlite_error_count >= 2:
        result["status"] = "ACTION"
        add_issue(issues, "ACTION", "repeated critical log errors", f"tracebacks={traceback_count}, sqlite={sqlite_error_count}")
    elif result["critical"]:
        result["status"] = "ACTION"
        add_issue(issues, "ACTION", "critical log line detected", result["critical"][0])
    elif result["errors"] or result["warnings"] or forecast_502_count:
        result["status"] = "WATCH"
        if forecast_502_count:
            add_issue(issues, "WATCH", "forecast 502 seen in recent logs", f"count={forecast_502_count}")
        elif result["errors"] or result["warnings"]:
            add_issue(issues, "WATCH", "recent log warnings/errors", f"errors={len(result['errors'])}, warnings={len(result['warnings'])}")
    return result


def build_health(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = Path(args.data_dir)
    db_path = Path(args.db)
    issues: list[dict[str, str]] = []
    runtime = summarize_runtime(data_dir, args.max_cycle_age_hours, issues)
    cycles = summarize_cycles(data_dir, issues)
    db = summarize_db(db_path, issues)
    trading = summarize_trading(data_dir, issues)
    logs = summarize_logs(data_dir, args.log_tail, issues)
    positions = summarize_positions(data_dir)
    optional_files = summarize_optional_files(data_dir)
    statuses = [runtime["status"], cycles["status"], db["status"], trading["status"], logs["status"]]
    status = worst_status(statuses)
    reason = "All required health checks are clean." if status == "OK" else "; ".join(
        issue["reason"] for issue in issues if issue["status"] == status
    ) or "Warnings present."
    next_action = {
        "OK": "No action needed. Keep normal monitoring.",
        "WATCH": "Review the warnings and rerun after the next cycle.",
        "ACTION": "Inspect Railway runtime/logs before relying on the bot.",
    }[status]
    return {
        "generated_at": now_utc().replace(microsecond=0).isoformat(),
        "data_dir": str(data_dir),
        "db_path": str(db_path),
        "status": status,
        "reason": reason,
        "next_action": next_action,
        "runtime": runtime,
        "cycles": cycles,
        "trading_activity": trading,
        "sqlite_recorder": db,
        "logs": logs,
        "positions": positions,
        "optional_files": optional_files,
        "issues": issues,
        "read_only": True,
    }


def md_bool(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "unknown"
    return str(value)


def render_markdown(health: dict[str, Any]) -> str:
    runtime = health["runtime"]
    trading = health["trading_activity"]
    db = health["sqlite_recorder"]
    logs = health["logs"]
    positions = health["positions"]
    readiness = db["readiness"]
    issues = health["issues"]
    issue_lines = "\n".join(
        f"- {item['status']}: {item['reason']}{' - ' + item['detail'] if item.get('detail') else ''}"
        for item in issues[:10]
    ) or "- none"
    return "\n".join(
        [
            "# Bot Health Check",
            "",
            f"Status: {health['status']}",
            f"Generated: {health['generated_at']}",
            f"Data dir: {health['data_dir']}",
            f"DB: {health['db_path']}",
            "",
            "## Runtime",
            f"- Version: {runtime.get('version') or 'unknown'}",
            f"- Mode: {runtime.get('mode') or 'unknown'}",
            f"- Last cycle: {runtime.get('last_cycle_ts') or 'unknown'}",
            f"- Age: {fmt_age(runtime.get('last_cycle_age_hours'))}",
            f"- Cycle number: {runtime.get('cycle_number') or 'unknown'}",
            f"- Recent: {md_bool(runtime.get('recent'))}",
            "",
            "## Trading activity",
            f"- Buys last cycle: {trading['buys_last_cycle']}",
            f"- with_edge: {trading['with_edge']}",
            f"- selected: {trading['selected']}",
            f"- execution_reject_reasons: {trading['execution_reject_reasons'] or {}}",
            f"- Main reject reasons: {trading['main_reject_reasons'] or {}}",
            f"- Interpretation: {trading['interpretation']}",
            "",
            "## SQLite Recorder",
            f"- DB exists: {md_bool(db['exists'])}",
            f"- cycle_events: {md_bool(db['tables'].get('cycle_events'))} ({db['row_counts'].get('cycle_events', 'unknown')} rows)",
            f"- market_snapshots: {md_bool(db['tables'].get('market_snapshots'))} ({db['row_counts'].get('market_snapshots', 'unknown')} rows)",
            f"- forecast_snapshots: {md_bool(db['tables'].get('forecast_snapshots'))} ({db['row_counts'].get('forecast_snapshots', 'unknown')} rows)",
            f"- last write: {db.get('last_write') or 'unknown'}",
            f"- recorder_fresh: {md_bool(db.get('recorder_fresh'))}",
            f"- readiness: cycles {readiness['cycles_actual']}/{readiness['cycles_required']}, days {readiness['days_actual']}/{readiness['days_required']}, ready={md_bool(readiness['ready'])}",
            f"- ETA Fase 1: {readiness.get('eta_date') or 'unknown'}",
            "",
            "## Logs",
            f"- errors: {len(logs['errors'])}",
            f"- warnings: {len(logs['warnings'])}",
            f"- known noise: {len(logs['known_noise'])}",
            f"- critical: {len(logs['critical'])}",
            "",
            "## Positions",
            f"- Active positions: {positions['active_positions']}",
            f"- Interpretation: {positions['interpretation']}",
            "",
            "## Issues",
            issue_lines,
            "",
            "## Verdict",
            f"- Status: {health['status']}",
            f"- Reason: {health['reason']}",
            f"- Next action: {health['next_action']}",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    health = build_health(args)
    if args.json:
        print(json.dumps(health, indent=2, sort_keys=True))
    else:
        print(render_markdown(health))


if __name__ == "__main__":
    main()
