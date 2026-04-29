#!/usr/bin/env python3
"""
Read-only bankroll scaling check.

This tool evaluates whether evidence is sufficient to open a manual review for
the next bankroll tier. It never changes bankroll, writes files, sends Telegram,
or imports bot.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TIERS = [25, 35, 50, 75, 100]
DEFAULT_LOG_TAIL = 200
DB_STALE_HOURS = 48
GAP_THRESHOLD_HOURS = 18
DRAW_DOWN_LIMIT = -3.0

CRITICAL_EXECUTION_RE = re.compile(
    r"order rejected|insufficient funds|auth failed|not enough balance|allowance",
    re.IGNORECASE,
)
AUTH_OK_RE = re.compile(r"Autenticaci[oó]n OK|Authentication OK", re.IGNORECASE)
SQLITE_ERROR_RE = re.compile(r"SQLiteRecorder error", re.IGNORECASE)
WARNING_RE = re.compile(r"\bWARNING\b|Forecast.*502|city[-_ ]?intelligence", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only evidence check for manual bankroll scaling review."
    )
    parser.add_argument("--data-dir", default="data", help="Runtime data directory.")
    parser.add_argument("--db", default="data/polymarket.db", help="Path to polymarket.db.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown output.")
    parser.add_argument(
        "--current-bankroll",
        type=float,
        default=None,
        help="Current bankroll tier. Defaults to auto, then 25.",
    )
    parser.add_argument(
        "--target-tier",
        type=float,
        default=None,
        help="Target tier. Defaults to next tier after current bankroll.",
    )
    parser.add_argument(
        "--log-tail",
        type=int,
        default=DEFAULT_LOG_TAIL,
        help="Lines to inspect from decisions.log and trades.log.",
    )
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and value > 0:
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
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
    return round((utc_now() - dt).total_seconds() / 3600, 2)


def add_item(items: list[dict[str, str]], code: str, message: str) -> None:
    if not any(item["code"] == code for item in items):
        items.append({"code": code, "message": message})


def read_json(path: Path) -> tuple[Any, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
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
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
        except json.JSONDecodeError:
            malformed += 1
    return records, f"malformed_lines={malformed}" if malformed else None


def data_path(data_dir: Path, name: str) -> Path:
    direct = data_dir / name
    if direct.exists():
        return direct
    runtime_import = data_dir / "runtime_import" / name
    if runtime_import.exists():
        return runtime_import
    return direct


def bankroll_state_paths(data_dir: Path) -> list[Path]:
    candidates = [
        data_dir / "bankroll_readiness_state.json",
        Path("data") / "bankroll_readiness_state.json",
        Path("bankroll_readiness_state.json"),
    ]
    seen: set[str] = set()
    result: list[Path] = []
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def read_bankroll_state(data_dir: Path) -> tuple[Any, str | None, list[str]]:
    paths = bankroll_state_paths(data_dir)
    last_error = "missing"
    for path in paths:
        data, err = read_json(path)
        if err is None:
            return data, None, [str(item) for item in paths]
        if err != "missing":
            last_error = err
    return None, last_error, [str(item) for item in paths]


def first_present(data: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def find_nested(data: Any, keys: set[str]) -> Any:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys and value not in (None, ""):
                return value
        for value in data.values():
            found = find_nested(value, keys)
            if found is not None:
                return found
    if isinstance(data, list):
        for value in data:
            found = find_nested(value, keys)
            if found is not None:
                return found
    return None


def as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("$", "").replace("%", "")
    try:
        return float(text)
    except ValueError:
        return None


def infer_current_bankroll(state: Any, explicit: float | None) -> float:
    if explicit is not None:
        return explicit
    if isinstance(state, dict):
        value = find_nested(state, {"current_bankroll", "bankroll", "BANKROLL"})
        parsed = as_float(value)
        if parsed is not None:
            return parsed
    return 25.0


def infer_target_tier(current: float, explicit: float | None) -> float:
    if explicit is not None:
        return explicit
    for tier in TIERS:
        if tier > current:
            return float(tier)
    return float(TIERS[-1])


def threshold_for_target(target: float) -> dict[str, float | int]:
    if target <= 35:
        return {"cycles": 10, "trades": 30, "wr": 40.0, "score": 40.0, "phase1_exit": 1}
    if target <= 50:
        return {"cycles": 30, "trades": 30, "wr": 45.0, "score": 60.0, "phase1_exit": 0}
    if target <= 75:
        return {"cycles": 30, "trades": 30, "wr": 45.0, "score": 75.0, "phase1_exit": 0}
    return {"cycles": 60, "trades": 60, "wr": 45.0, "score": 75.0, "phase1_exit": 0}


def criterion(criteria: list[dict[str, Any]], name: str, status: str, value: Any, notes: str = "") -> None:
    criteria.append({"name": name, "status": status, "value": value, "notes": notes})


def open_db_readonly(db_path: Path) -> sqlite3.Connection:
    uri = db_path.resolve().as_posix()
    con = sqlite3.connect(f"file:{uri}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    return con


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def db_first_column(con: sqlite3.Connection, table: str, candidates: list[str]) -> str | None:
    cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
    for candidate in candidates:
        if candidate in cols:
            return candidate
    return None


def inspect_db(db_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(db_path),
        "exists": db_path.exists(),
        "readable": False,
        "tables": {},
        "cycle_count": None,
        "last_write": None,
        "last_write_age_hours": None,
        "large_gaps": [],
        "error": None,
    }
    if not db_path.exists():
        result["error"] = "missing"
        return result
    try:
        con = open_db_readonly(db_path)
    except sqlite3.Error as exc:
        result["error"] = str(exc)
        return result
    try:
        result["readable"] = True
        tables = ["cycle_events", "market_snapshots", "forecast_snapshots", "truth_records", "truth_revisions"]
        result["tables"] = {name: table_exists(con, name) for name in tables}
        if result["tables"].get("cycle_events"):
            result["cycle_count"] = int(con.execute("SELECT COUNT(*) FROM cycle_events").fetchone()[0])
            ts_col = db_first_column(con, "cycle_events", ["ts_utc", "timestamp_utc", "created_at", "ts"])
            if ts_col:
                rows = con.execute(
                    f"SELECT {ts_col} FROM cycle_events WHERE {ts_col} IS NOT NULL ORDER BY {ts_col} ASC"
                ).fetchall()
                timestamps = [parse_ts(row[0]) for row in rows]
                timestamps = [ts for ts in timestamps if ts is not None]
                if timestamps:
                    result["last_write"] = timestamps[-1].isoformat()
                    result["last_write_age_hours"] = age_hours(timestamps[-1])
                    gaps = []
                    for prev, curr in zip(timestamps, timestamps[1:]):
                        gap = (curr - prev).total_seconds() / 3600
                        if gap > GAP_THRESHOLD_HOURS:
                            gaps.append(
                                {"from": prev.isoformat(), "to": curr.isoformat(), "gap_hours": round(gap, 1)}
                            )
                    result["large_gaps"] = gaps[-5:]
    except sqlite3.Error as exc:
        result["error"] = str(exc)
    finally:
        con.close()
    return result


def extract_cycle_metrics(cycle_summary: Any, cycles_history: list[dict[str, Any]]) -> dict[str, Any]:
    last_cycle = cycle_summary if isinstance(cycle_summary, dict) else {}
    cycle_count = len(cycles_history)
    if cycle_count == 0 and last_cycle:
        cycle_count = 1
    latest_ts = None
    if cycles_history:
        latest_ts = parse_ts(first_present(cycles_history[-1], ["timestamp_utc", "ts_utc", "created_at", "ts"]))
    if latest_ts is None and last_cycle:
        latest_ts = parse_ts(first_present(last_cycle, ["timestamp_utc", "ts_utc", "created_at", "ts"]))
    reject_reasons = find_nested(last_cycle, {"execution_reject_reasons", "reject_reasons"}) or {}
    return {
        "cycles_available": cycle_count,
        "last_cycle_ts": latest_ts.isoformat() if latest_ts else None,
        "last_cycle_age_hours": age_hours(latest_ts),
        "execution_reject_reasons": reject_reasons,
        "buys": first_present(last_cycle, ["buys", "trades_executed", "executed_buys"]),
        "selected": first_present(last_cycle, ["selected", "candidates_selected"]),
        "with_edge": first_present(last_cycle, ["with_edge", "candidates_with_edge"]),
    }


def closed_trades_from_lifecycle(trade_lifecycle: Any) -> list[dict[str, Any]]:
    if not isinstance(trade_lifecycle, dict):
        return []
    records = trade_lifecycle.get("records")
    if not isinstance(records, list):
        records = trade_lifecycle.get("trades")
    if not isinstance(records, list):
        return []
    closed = []
    for row in records:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "")).lower()
        close_context = row.get("close_context") if isinstance(row.get("close_context"), dict) else {}
        pnl = first_present(row, ["pnl", "pnl_cash", "profit_loss", "realized_pnl"])
        if pnl is None:
            pnl = first_present(close_context, ["pnl_cash", "pnl", "profit_loss", "realized_pnl"])
        parsed = as_float(pnl)
        if status == "closed" or parsed is not None:
            closed_at = parse_ts(first_present(row, ["closed_at", "resolved_at", "updated_at", "ts_utc"]))
            closed.append({"pnl": parsed, "closed_at": closed_at, "raw": row})
    return closed


def extract_logic_series(value: Any) -> str | None:
    text = str(value or "").strip()
    match = re.search(r"v?(\d+\.\d+)", text)
    return match.group(1) if match else None


def infer_logic_series(cycle_summary: Any, cycles_history: list[dict[str, Any]]) -> str | None:
    candidates: list[Any] = []
    if isinstance(cycle_summary, dict):
        candidates.extend([cycle_summary.get("logic_series"), cycle_summary.get("version")])
    for row in reversed(cycles_history[-20:]):
        if isinstance(row, dict):
            candidates.extend([row.get("logic_series"), row.get("version")])
    for candidate in candidates:
        series = extract_logic_series(candidate)
        if series:
            return series
    return None


def trade_logic_series_values(row: dict[str, Any]) -> set[str]:
    raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
    close_context = raw.get("close_context") if isinstance(raw.get("close_context"), dict) else {}
    candidates = [
        raw.get("bot_version_opened"),
        raw.get("bot_version_closed"),
        close_context.get("bot_version"),
    ]
    for key in ("entry_context", "latest_entry_context"):
        ctx = raw.get(key) if isinstance(raw.get(key), dict) else {}
        candidates.append(ctx.get("bot_version"))
    values: set[str] = set()
    for candidate in candidates:
        series = extract_logic_series(candidate)
        if series:
            values.add(series)
    return values


def is_integrity_clean(row: dict[str, Any]) -> bool:
    raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
    integrity = raw.get("integrity")
    if not isinstance(integrity, dict):
        return False
    if integrity.get("analysis_ready") is not True:
        return False
    legacy_flags = ("partial_historical_record", "missing_buy_history", "close_only_record")
    return not any(bool(integrity.get(flag)) for flag in legacy_flags)


def performance_window_stats(name: str, rows: list[dict[str, Any]], min_sample: int) -> dict[str, Any]:
    values = [row["pnl"] for row in rows if row.get("pnl") is not None]
    dated = sorted(
        [row for row in rows if row.get("closed_at") is not None and row.get("pnl") is not None],
        key=lambda row: row["closed_at"],
    )
    recent_5 = dated[-5:]
    wins = sum(1 for value in values if value > 0)
    losses = sum(1 for value in values if value <= 0)
    return {
        "window": name,
        "closed": len(values),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wins / len(values) * 100, 1) if values else None,
        "pnl_total": round(sum(values), 2) if values else None,
        "drawdown_last_5": round(sum(row["pnl"] for row in recent_5), 2) if recent_5 else None,
        "sample_min": min_sample,
        "sample_ok": len(values) >= min_sample,
    }


def legacy_pnl_summary(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": stats.get("source"),
        "evaluation_window": stats.get("evaluation_window"),
        "closed_trades": stats.get("closed"),
        "wins": stats.get("wins"),
        "losses": stats.get("losses"),
        "win_rate_pct": stats.get("win_rate_pct"),
        "pnl_total": stats.get("pnl_total"),
        "drawdown_last_5": stats.get("drawdown_last_5"),
        "sample_ok": stats.get("sample_ok"),
        "sample_min": stats.get("sample_min"),
        "recent_closed": stats.get("recent_closed", []),
    }


def pnl_metrics(
    trade_lifecycle: Any,
    performance: Any,
    cycle_summary: Any = None,
    cycles_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    closed = closed_trades_from_lifecycle(trade_lifecycle)
    source = "trade_lifecycle"
    if not closed and isinstance(performance, dict):
        maybe = performance.get("closed_trades") or performance.get("trades") or performance.get("records")
        if isinstance(maybe, list):
            for row in maybe:
                if isinstance(row, dict):
                    pnl = as_float(first_present(row, ["pnl", "pnl_cash", "profit_loss", "realized_pnl"]))
                    closed.append({"pnl": pnl, "closed_at": parse_ts(first_present(row, ["closed_at", "ts_utc"])), "raw": row})
            source = "performance"
    closed_with_pnl = [row for row in closed if row.get("pnl") is not None]
    closed_sorted = sorted(
        [row for row in closed_with_pnl if row.get("closed_at") is not None],
        key=lambda row: row["closed_at"],
    )
    logic_series = infer_logic_series(cycle_summary, cycles_history or [])
    current_logic_rows = [
        row for row in closed_with_pnl
        if logic_series and logic_series in trade_logic_series_values(row)
    ]
    clean_rows = [row for row in closed_sorted if is_integrity_clean(row)]

    windows = {
        "historical_all": performance_window_stats("historical_all", closed_with_pnl, 30),
        "current_logic_series": performance_window_stats("current_logic_series", current_logic_rows, 30),
        "last_20_closed": performance_window_stats("last_20_closed", closed_sorted[-20:], 20),
        "last_30_clean_closed": performance_window_stats("last_30_clean_closed", clean_rows[-30:], 30),
    }
    windows["current_logic_series"]["logic_series"] = logic_series
    windows["last_30_clean_closed"]["clean_filter"] = {
        "analysis_ready": True,
        "excluded_flags": ["partial_historical_record", "missing_buy_history", "close_only_record"],
        "requires_integrity_fields": True,
    }

    if windows["last_30_clean_closed"]["closed"] >= 30:
        evaluation_window = "last_30_clean_closed"
    elif windows["current_logic_series"]["closed"] >= 30:
        evaluation_window = "current_logic_series"
    elif windows["last_20_closed"]["closed"] >= 20:
        evaluation_window = "last_20_closed"
    else:
        evaluation_window = "historical_all"

    evaluation = dict(windows[evaluation_window])
    evaluation["source"] = source if closed else None
    evaluation["evaluation_window"] = evaluation_window
    recent = closed_sorted[-5:]
    evaluation["recent_closed"] = [
            {
                "closed_at": row["closed_at"].isoformat() if row["closed_at"] else None,
                "pnl": row["pnl"],
            }
            for row in recent
        ]
    return {
        **legacy_pnl_summary(evaluation),
        "performance_windows": windows,
        "legacy_context": {
            "historical_all": windows["historical_all"],
            "historical_all_used_for_decision": evaluation_window == "historical_all",
        },
    }


def inspect_bankroll_score(state: Any, paths_checked: list[str]) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {
            "available": False,
            "score": None,
            "score_pct": None,
            "stage": None,
            "updated_at": None,
            "paths_checked": paths_checked,
            "message": "Bankroll readiness score state file not found; run/readiness score has not produced persistent state in this environment.",
        }
    score = first_present(state, ["composite", "score_pct", "bankroll_readiness_score", "readiness_score", "score"])
    if score is None:
        score = find_nested(state, {"composite", "score_pct", "bankroll_readiness_score", "readiness_score"})
    stage = first_present(state, ["stage", "label", "status"])
    if stage is None:
        stage = find_nested(state, {"stage", "label", "status"})
    updated_at = find_nested(state, {"updated_at", "generated_at", "timestamp"})
    return {
        "available": as_float(score) is not None,
        "score": as_float(score),
        "score_pct": as_float(score),
        "stage": stage,
        "updated_at": updated_at,
        "paths_checked": paths_checked,
        "message": None,
    }


def infer_phase1(db: dict[str, Any]) -> dict[str, Any]:
    if not db["exists"] or not db["readable"]:
        return {"exit_code": 2, "ready": False, "status": "db_unavailable"}
    required = ["cycle_events", "market_snapshots", "forecast_snapshots"]
    if not all(db["tables"].get(name) for name in required):
        return {"exit_code": 3, "ready": False, "status": "tables_missing"}
    fresh = db["last_write_age_hours"] is not None and db["last_write_age_hours"] <= 30
    enough_cycles = (db["cycle_count"] or 0) >= 21
    no_gaps = not db["large_gaps"]
    ready = fresh and enough_cycles and no_gaps
    return {
        "exit_code": 0 if ready else 1,
        "ready": ready,
        "status": "ready" if ready else "pending",
        "fresh": fresh,
        "cycles_actual": db["cycle_count"],
        "cycles_required": 21,
        "no_large_gaps": no_gaps,
    }


def inspect_logs(data_dir: Path, log_tail: int) -> dict[str, Any]:
    lines: list[str] = []
    errors: dict[str, str] = {}
    for name in ("decisions.log", "trades.log"):
        path = data_path(data_dir, name)
        tail, err = tail_lines(path, log_tail)
        if err:
            errors[name] = err
        lines.extend(tail)
    critical = [line for line in lines if CRITICAL_EXECUTION_RE.search(line)]
    auth_ok_positions = [idx for idx, line in enumerate(lines) if AUTH_OK_RE.search(line)]
    auth_failed_positions = [idx for idx, line in enumerate(lines) if re.search(r"auth failed", line, re.IGNORECASE)]
    auth_failed_without_later_ok = any(
        not any(ok_idx > fail_idx for ok_idx in auth_ok_positions) for fail_idx in auth_failed_positions
    )
    sqlite_errors = [line for line in lines if SQLITE_ERROR_RE.search(line)]
    warnings = [line for line in lines if WARNING_RE.search(line)]
    return {
        "lines_scanned": len(lines),
        "missing_or_errors": errors,
        "critical_execution_lines": critical[-5:],
        "auth_failed_without_later_ok": auth_failed_without_later_ok,
        "sqlite_recorder_error_count": len(sqlite_errors),
        "warnings": warnings[-5:],
    }


def inspect_positions(trade_lifecycle: Any) -> dict[str, Any]:
    open_count = 0
    pending_exit_count = 0
    stale_pending = 0
    if isinstance(trade_lifecycle, dict):
        records = trade_lifecycle.get("records")
        if isinstance(records, list):
            for row in records:
                if not isinstance(row, dict):
                    continue
                status = str(row.get("status", "")).lower()
                if status in {"open", "active"}:
                    open_count += 1
                if "pending" in status or row.get("pending_exit") is True:
                    pending_exit_count += 1
                    ts = parse_ts(first_present(row, ["updated_at", "closed_at", "created_at", "ts_utc"]))
                    hours = age_hours(ts)
                    if hours is None or hours > 24:
                        stale_pending += 1
    return {"open_positions": open_count, "pending_exits": pending_exit_count, "stale_pending_exits": stale_pending}


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = Path(args.data_dir)
    db_path = Path(args.db)
    hard_blockers: list[dict[str, str]] = []
    watch_items: list[dict[str, str]] = []
    missing_evidence: list[dict[str, str]] = []
    criteria: list[dict[str, Any]] = []

    cycle_summary, cycle_summary_err = read_json(data_path(data_dir, "cycle_summary.json"))
    cycles_history, cycles_history_err = read_jsonl_tail(data_path(data_dir, "cycles_history.jsonl"), 1000)
    trade_lifecycle, trade_lifecycle_err = read_json(data_path(data_dir, "trade_lifecycle.json"))
    postmortem, postmortem_err = read_json(data_path(data_dir, "postmortem.json"))
    performance, performance_err = read_json(data_path(data_dir, "performance.json"))
    bankroll_state, bankroll_state_err, bankroll_paths_checked = read_bankroll_state(data_dir)

    current = infer_current_bankroll(bankroll_state, args.current_bankroll)
    target = infer_target_tier(current, args.target_tier)
    thresholds = threshold_for_target(target)

    db = inspect_db(db_path)
    phase1 = infer_phase1(db)
    cycles = extract_cycle_metrics(cycle_summary, cycles_history)
    pnl = pnl_metrics(trade_lifecycle, performance, cycle_summary, cycles_history)
    score = inspect_bankroll_score(bankroll_state, bankroll_paths_checked)
    logs = inspect_logs(data_dir, args.log_tail)
    positions = inspect_positions(trade_lifecycle)

    db_fresh = db["readable"] and db["last_write_age_hours"] is not None and db["last_write_age_hours"] <= DB_STALE_HOURS
    criterion(criteria, "sqlite_recorder_fresh", "pass" if db_fresh else "fail", bool(db_fresh), f"age_hours={db['last_write_age_hours']}")
    if not db["exists"] or not db["readable"]:
        add_item(hard_blockers, "sqlite_db_not_readable", "polymarket.db is missing or not readable in read-only mode")
    elif not db_fresh:
        add_item(hard_blockers, "sqlite_recorder_stale", "SQLiteRecorder appears stale or has no timestamp evidence")

    no_large_gaps = not db["large_gaps"]
    criterion(criteria, "large_gaps_absent", "pass" if no_large_gaps else "fail", no_large_gaps, f"gaps={len(db['large_gaps'])}")
    if db["large_gaps"]:
        add_item(hard_blockers, "large_cycle_gaps", "Large gaps detected in SQLite cycle_events")

    phase1_allowed = int(thresholds["phase1_exit"])
    phase1_ready = bool(phase1.get("ready"))
    phase1_pending_allowed = phase1["exit_code"] == 1 and phase1_allowed >= 1
    phase1_status = "pass" if phase1_ready else "pending" if phase1_pending_allowed else "fail"
    phase1_notes = f"exit_code={phase1['exit_code']}"
    if phase1_pending_allowed:
        phase1_notes += "; Phase 1 readiness pending; expected until thresholds are met"
    criterion(criteria, "phase1_ready", phase1_status, phase1_ready, phase1_notes)
    if not phase1_ready and not phase1_pending_allowed:
        add_item(hard_blockers, "phase1_not_ready", "Phase 1 readiness is not ready enough for this tier")
    elif phase1_pending_allowed:
        add_item(watch_items, "phase1_pending", "Phase 1 readiness pending; expected until thresholds are met")

    cycles_available = max(cycles["cycles_available"], db["cycle_count"] or 0)
    cycles_ok = cycles_available >= int(thresholds["cycles"])
    criterion(criteria, "cycles_minimum", "pass" if cycles_ok else "fail", f"{cycles_available}/{thresholds['cycles']}")
    if not cycles_ok:
        add_item(hard_blockers, "insufficient_cycles", "Not enough stable cycles for the target tier")

    trades_ok = pnl["closed_trades"] >= int(thresholds["trades"])
    criterion(criteria, "clean_trades_minimum", "pass" if trades_ok else "unknown", f"{pnl['closed_trades']}/{thresholds['trades']}")
    if pnl["closed_trades"] == 0:
        add_item(missing_evidence, "closed_trades_unavailable", "Closed trade evidence is unavailable")
    elif not trades_ok:
        add_item(watch_items, "insufficient_closed_trades", "Closed trade sample is below policy target")

    pnl_ok = pnl["pnl_total"] is not None and pnl["pnl_total"] >= 0
    criterion(criteria, "pnl_non_negative", "pass" if pnl_ok else "fail" if pnl["pnl_total"] is not None else "unknown", pnl["pnl_total"])
    if pnl["pnl_total"] is None:
        add_item(missing_evidence, "pnl_unavailable", "PnL evidence is unavailable")
    elif not pnl_ok:
        add_item(hard_blockers, "pnl_negative", "PnL is negative for available closed trade evidence")

    wr_ok = pnl["win_rate_pct"] is not None and pnl["win_rate_pct"] >= float(thresholds["wr"])
    criterion(criteria, "win_rate_minimum", "pass" if wr_ok else "fail" if pnl["win_rate_pct"] is not None else "unknown", pnl["win_rate_pct"])
    if pnl["win_rate_pct"] is None:
        add_item(missing_evidence, "win_rate_unavailable", "Win rate evidence is unavailable")
    elif not wr_ok:
        add_item(hard_blockers, "win_rate_below_threshold", "Win rate is below policy threshold")

    dd_ok = pnl["drawdown_last_5"] is not None and pnl["drawdown_last_5"] > DRAW_DOWN_LIMIT
    criterion(criteria, "drawdown_last_5_above_limit", "pass" if dd_ok else "fail" if pnl["drawdown_last_5"] is not None else "unknown", pnl["drawdown_last_5"])
    if pnl["drawdown_last_5"] is None:
        add_item(missing_evidence, "drawdown_unavailable", "Recent drawdown cannot be calculated")
    elif not dd_ok:
        add_item(hard_blockers, "recent_drawdown_exceeded", "Drawdown across the last 5 closes is at or below -$3")

    score_ok = score["score_pct"] is not None and score["score_pct"] >= float(thresholds["score"])
    criterion(criteria, "bankroll_readiness_score", "pass" if score_ok else "fail" if score["score_pct"] is not None else "unknown", score["score_pct"])
    if score["score_pct"] is None:
        add_item(
            missing_evidence,
            "bankroll_readiness_score_unavailable",
            "Bankroll readiness score state file not found; run/readiness score has not produced persistent state in this environment.",
        )
    elif not score_ok:
        add_item(watch_items, "score_low", "Bankroll readiness score is below threshold")

    execution_reasons = cycles["execution_reject_reasons"]
    execution_text = json.dumps(execution_reasons, ensure_ascii=True) if execution_reasons else ""
    critical_execution = bool(CRITICAL_EXECUTION_RE.search(execution_text)) or bool(logs["critical_execution_lines"])
    criterion(criteria, "critical_execution_errors_absent", "pass" if not critical_execution else "fail", not critical_execution)
    if critical_execution:
        add_item(hard_blockers, "critical_execution_errors", "Critical execution errors detected in cycle summary or logs")

    if logs["auth_failed_without_later_ok"]:
        add_item(hard_blockers, "auth_failed_without_recovery", "auth failed appears without a later Authentication OK in inspected logs")
    if logs["sqlite_recorder_error_count"] >= 2:
        add_item(hard_blockers, "sqlite_recorder_error_repeated", "Repeated SQLiteRecorder errors detected in inspected logs")
    elif logs["sqlite_recorder_error_count"] == 1:
        add_item(watch_items, "sqlite_recorder_error_single", "One SQLiteRecorder error detected in inspected logs")
    if logs["warnings"]:
        add_item(watch_items, "observability_warnings", "Warnings or isolated forecast/city-intelligence issues found in logs")
    if (
        pnl.get("evaluation_window") != "historical_all"
        and pnl.get("performance_windows", {}).get("historical_all", {}).get("closed", 0) > 0
    ):
        add_item(watch_items, "historical_all_legacy_context", "Historical all-trades performance is reported as legacy context, not the primary scaling blocker")

    criterion(criteria, "pending_exits_clear", "pass" if positions["stale_pending_exits"] == 0 else "fail", positions)
    if positions["stale_pending_exits"]:
        add_item(hard_blockers, "pending_exits_stale", "Pending exits appear stuck")

    if target >= 50:
        truth_known = bool(db["tables"].get("truth_records") or db["tables"].get("truth_revisions"))
        criterion(criteria, "truth_pipeline_present", "pass" if truth_known else "fail", truth_known)
        if not truth_known:
            add_item(hard_blockers, "truth_pipeline_not_available", "Truth Pipeline evidence is required for $35->$50 and above")
    else:
        add_item(missing_evidence, "truth_pipeline_status_unknown", "Truth Pipeline status is not directly evaluated for this tier")

    if target >= 75:
        add_item(missing_evidence, "settlement_fidelity_status_unknown", "Settlement fidelity is not verifiable from available evidence")
    if target >= 100:
        add_item(missing_evidence, "replay_shadow_comparison_unknown", "Replay/backtest/shadow comparison evidence is unavailable")

    if postmortem_err:
        add_item(missing_evidence, "postmortem_unavailable", "postmortem.json is missing or unreadable")
    elif pnl["recent_closed"] and any((row["pnl"] or 0) < -1 for row in pnl["recent_closed"]):
        if not postmortem:
            add_item(hard_blockers, "loss_without_postmortem", "Recent loss worse than $1 found without readable postmortem evidence")

    add_item(missing_evidence, "recent_core_change_observation_unknown", "Recent trading core change observation window cannot be proven by this read-only tool")

    important_missing_codes = {
        "closed_trades_unavailable",
        "pnl_unavailable",
        "win_rate_unavailable",
        "drawdown_unavailable",
        "bankroll_readiness_score_unavailable",
        "recent_core_change_observation_unknown",
    }
    unknown_missing_codes = {
        "closed_trades_unavailable",
        "pnl_unavailable",
        "win_rate_unavailable",
        "drawdown_unavailable",
    }
    important_missing = any(item["code"] in important_missing_codes for item in missing_evidence)
    unknown_missing = any(item["code"] in unknown_missing_codes for item in missing_evidence)
    eligible = not hard_blockers and not important_missing
    if hard_blockers:
        status = "BLOCKED"
        decision = "do_not_increase"
    elif unknown_missing:
        status = "UNKNOWN"
        decision = "do_not_increase"
    elif eligible:
        status = "ELIGIBLE_FOR_MANUAL_REVIEW"
        decision = "manual_review_required"
    else:
        status = "NOT_ELIGIBLE"
        decision = "do_not_increase"

    return {
        "generated_at": utc_now().isoformat(),
        "current_bankroll": int(current) if current.is_integer() else current,
        "target_tier": int(target) if target.is_integer() else target,
        "eligible_for_manual_review": eligible,
        "decision": decision,
        "status": status,
        "hard_blockers": hard_blockers,
        "watch_items": watch_items,
        "missing_evidence": missing_evidence,
        "evaluation_window": pnl.get("evaluation_window"),
        "performance_windows": pnl.get("performance_windows", {}),
        "criteria": criteria,
        "evidence": {
            "phase1": phase1,
            "bankroll_score": score,
            "cycle_summary": cycles,
            "sqlite_recorder": db,
            "pnl_drawdown": pnl,
            "positions": positions,
            "logs": logs,
            "source_errors": {
                "cycle_summary": cycle_summary_err,
                "cycles_history": cycles_history_err,
                "trade_lifecycle": trade_lifecycle_err,
                "postmortem": postmortem_err,
                "performance": performance_err,
                "bankroll_readiness_state": bankroll_state_err,
            },
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    score_evidence = report["evidence"]["bankroll_score"]
    if score_evidence.get("available"):
        score_line = (
            f"{score_evidence.get('score_pct')} stage={score_evidence.get('stage')}"
        )
    else:
        score_line = "unavailable (state file not found)"
        if score_evidence.get("paths_checked"):
            score_line += f" paths_checked={json.dumps(score_evidence.get('paths_checked'), ensure_ascii=True)}"
    lines = [
        "# Bankroll Scaling Check",
        "",
        f"Status: {report['status']}",
        f"Current bankroll: ${report['current_bankroll']}",
        f"Target tier: ${report['target_tier']}",
        f"Generated: {report['generated_at']}",
        "",
        "## Decision",
        "Manual review required." if report["decision"] == "manual_review_required" else "Do not increase bankroll.",
        "",
        "## Hard blockers",
    ]
    if report["hard_blockers"]:
        lines.extend(f"- {item['code']}: {item['message']}" for item in report["hard_blockers"])
    else:
        lines.append("- None detected.")
    lines.extend(["", "## Watch items"])
    if report["watch_items"]:
        lines.extend(f"- {item['code']}: {item['message']}" for item in report["watch_items"])
    else:
        lines.append("- None detected.")
    lines.extend(["", "## Missing evidence"])
    if report["missing_evidence"]:
        lines.extend(f"- {item['code']}: {item['message']}" for item in report["missing_evidence"])
    else:
        lines.append("- None.")
    lines.extend(["", "## Criteria", "", "| Criterion | Status | Value | Notes |", "|---|---:|---|---|"])
    for item in report["criteria"]:
        value = json.dumps(item["value"], ensure_ascii=True) if isinstance(item["value"], (dict, list)) else item["value"]
        lines.append(f"| {item['name']} | {item['status']} | {value} | {item.get('notes', '')} |")
    windows = report.get("performance_windows", {})
    lines.extend(
        [
            "",
            "## Performance windows",
            "",
            "| Window | Closed | Wins | Losses | WR | PnL | Drawdown last 5 | Sample ok | Used for decision |",
            "|---|---:|---:|---:|---:|---:|---:|:---:|:---:|",
        ]
    )
    window_rows = []
    for name in ("historical_all", "current_logic_series", "last_20_closed", "last_30_clean_closed"):
        item = windows.get(name, {}) if isinstance(windows, dict) else {}
        used = "yes" if report.get("evaluation_window") == name else "no"
        wr = item.get("win_rate_pct")
        pnl_total = item.get("pnl_total")
        dd5 = item.get("drawdown_last_5")
        window_rows.append(
            f"| {name} | {item.get('closed', 0)} | {item.get('wins', 0)} | {item.get('losses', 0)} | "
            f"{'' if wr is None else wr} | {'' if pnl_total is None else pnl_total} | "
            f"{'' if dd5 is None else dd5} | {bool(item.get('sample_ok'))} | {used} |"
        )
    lines.extend(window_rows)
    evidence = report["evidence"]
    lines.extend(
        [
            "",
            "## Evidence",
            f"- Last cycle: {evidence['cycle_summary'].get('last_cycle_ts')} age_hours={evidence['cycle_summary'].get('last_cycle_age_hours')}",
            f"- SQLite recorder: readable={evidence['sqlite_recorder'].get('readable')} age_hours={evidence['sqlite_recorder'].get('last_write_age_hours')} gaps={len(evidence['sqlite_recorder'].get('large_gaps') or [])}",
            f"- Phase1 readiness: exit_code={evidence['phase1'].get('exit_code')} status={evidence['phase1'].get('status')}",
            f"- Bankroll readiness score: {score_line}",
            f"- Evaluation window: {report.get('evaluation_window')}",
            f"- PnL / drawdown: pnl_total={evidence['pnl_drawdown'].get('pnl_total')} drawdown_last_5={evidence['pnl_drawdown'].get('drawdown_last_5')} win_rate={evidence['pnl_drawdown'].get('win_rate_pct')}",
            f"- Recent trades: closed={evidence['pnl_drawdown'].get('closed_trades')} wins={evidence['pnl_drawdown'].get('wins')}",
            "",
            "## Manual rule",
            "This tool never authorizes automatic scaling. It only indicates whether manual review may be opened.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    report = evaluate(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
        return
    print(render_markdown(report))


if __name__ == "__main__":
    main()
