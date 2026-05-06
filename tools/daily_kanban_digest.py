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


def summarize_operational(data_dir: Path, generated_at: datetime) -> dict[str, Any]:
    cycles = load_jsonl(data_dir / "cycles_history.jsonl")
    agent_events = load_jsonl(data_dir / "agent_events.jsonl")
    rows = cycles or agent_events
    recent_rows = []
    cutoff = generated_at - timedelta(days=1)
    for row in rows:
        ts = parse_ts(row.get("ts_utc") or row.get("timestamp") or row.get("created_at"))
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
        return {
            "title": "P/L / Profitability",
            "level": "WATCH_RISK",
            "status": "data_missing",
            "windows": {"1d": None, "7d": None, "30d": None, "all": None},
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
    level = "WATCH_RISK" if not closed else "NO_ACTION"
    note = "No interpretar P/L contaminado como mejora limpia."
    return {
        "title": "P/L / Profitability",
        "level": level,
        "status": "ok" if closed else "data_missing",
        "windows": windows,
        "open_positions": sum(1 for record in records if record.get("status") == "open"),
        "note": note,
    }


def summarize_activity(data_dir: Path, generated_at: datetime) -> dict[str, Any]:
    lifecycle = load_json(data_dir / "trade_lifecycle.json")
    records = normalize_records(lifecycle)
    cycles = load_jsonl(data_dir / "cycles_history.jsonl")
    cutoff_7d = generated_at - timedelta(days=7)
    recent_cycles = []
    for row in cycles:
        ts = parse_ts(row.get("ts_utc") or row.get("timestamp") or row.get("created_at"))
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
    sections = {
        "operational": summarize_operational(data_dir, generated_at),
        "profitability": summarize_profitability(data_dir, generated_at),
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
    op = sections["operational"]
    pnl = sections["profitability"]
    activity = sections["activity"]
    truth = sections["truth_pipeline"]
    kanban = sections["kanban"]

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
        f"  - Nota: {pnl.get('note', 'unknown')}",
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
