#!/usr/bin/env python3
"""Read-only DB throughput report for the Polymarket weather bot.

The report is LOG_ONLY: it reads SQLite recorder data and emits diagnostics.
It stays isolated from the runtime bot module, does not place orders, does not
send Telegram, does not change env vars, and does not write to the database.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


EXPECTED_TABLES = ("cycle_events", "market_snapshots", "forecast_snapshots")
LARGE_GAP_HOURS = 18.0
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY / OPUS_REVIEW_REQUIRED before any trading, BANKROLL, Fase C, sizing, "
    "city mode, whitelist, risk rule, scheduler, env var, DB schema, or Telegram change."
)


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_ts(value: Any) -> datetime | None:
    if value is None:
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
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pct(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def safe_json_loads(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def sqlite_readonly_uri(path: Path) -> str:
    resolved = path.resolve()
    normalized = str(resolved).replace("\\", "/")
    return f"file:{quote(normalized, safe='/:')}?mode=ro"


def open_readonly_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(sqlite_readonly_uri(path), uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, name: str) -> set[str]:
    try:
        return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({name})").fetchall()}
    except sqlite3.Error:
        return set()


def infer_condition(question: Any) -> str | None:
    text = str(question or "").lower()
    if not text:
        return None
    normalized = re.sub(r"\s+", " ", text)
    if re.search(r"\bbetween\b|\bfrom\s+-?\d+(?:\.\d+)?\s*(?:c|f)?\s+to\b|\brange\b", normalized):
        return "range"
    if re.search(r"\bat\s+or\s+above\b|\babove\s+or\s+equal\b|\bat\s+least\b|\bno\s+less\s+than\b", normalized):
        return "at_or_above"
    if re.search(r"\bat\s+or\s+below\b|\bbelow\s+or\s+equal\b|\bat\s+most\b|\bno\s+more\s+than\b", normalized):
        return "at_or_below"
    if re.search(r"\bexactly\b|\bbe\s+-?\d+(?:\.\d+)?\s*(?:c|f)\b|\bbe\s+-?\d+(?:\.\d+)?\s+degrees\b", normalized):
        return "exact"
    return None


def condition_from_snapshot(row: sqlite3.Row, columns: set[str]) -> tuple[str, str]:
    if "condition" in columns and row["condition"]:
        return str(row["condition"]), "native_column"
    payload = safe_json_loads(row["payload_json"] if "payload_json" in columns else None)
    payload_condition = payload.get("condition")
    if payload_condition:
        return str(payload_condition), "payload_json"
    question = row["question"] if "question" in columns else payload.get("question")
    inferred = infer_condition(question)
    if inferred:
        return inferred, "question_inferred"
    return "unknown", "unavailable"


def collect_schema(conn: sqlite3.Connection) -> dict[str, Any]:
    tables = {table: table_exists(conn, table) for table in EXPECTED_TABLES}
    row_counts: dict[str, int | None] = {}
    for table, present in tables.items():
        if not present:
            row_counts[table] = None
            continue
        try:
            row_counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        except sqlite3.Error:
            row_counts[table] = None
    schema_version = None
    if table_exists(conn, "schema_version"):
        try:
            row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            schema_version = row[0] if row else None
        except sqlite3.Error:
            schema_version = None
    return {"tables": tables, "row_counts": row_counts, "schema_version": schema_version}


def collect_cycles(conn: sqlite3.Connection, warnings: list[str]) -> dict[str, Any]:
    if not table_exists(conn, "cycle_events"):
        warnings.append("missing_table:cycle_events")
        return {
            "total": 0,
            "first_ts": None,
            "last_ts": None,
            "freshness": {"hours_ago": None, "is_fresh": False},
            "by_slot_utc": [],
            "gaps": [],
        }

    columns = table_columns(conn, "cycle_events")
    rows = conn.execute("SELECT * FROM cycle_events ORDER BY ts_utc ASC").fetchall()
    slots: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "slot_utc": None,
            "cycles": 0,
            "markets_evaluated": 0,
            "with_edge": 0,
            "selected": 0,
            "condition_filtered": 0,
            "buys": 0,
        }
    )
    timestamps: list[datetime] = []
    first_ts_raw = None
    last_ts_raw = None
    json_payload_rows = 0

    for row in rows:
        ts_raw = row["ts_utc"] if "ts_utc" in columns else None
        ts = parse_ts(ts_raw)
        if ts is None:
            warnings.append("cycle_events:unparseable_ts")
            continue
        if first_ts_raw is None:
            first_ts_raw = ts_raw
        last_ts_raw = ts_raw
        timestamps.append(ts)
        payload = safe_json_loads(row["payload_json"] if "payload_json" in columns else None)
        if payload:
            json_payload_rows += 1
        scan = payload.get("scan") if isinstance(payload.get("scan"), dict) else {}
        slot_metrics = scan.get("slot_metrics") if isinstance(scan.get("slot_metrics"), dict) else {}
        slot = int(slot_metrics.get("slot_hour_utc", ts.hour) if slot_metrics else ts.hour)
        bucket = slots[slot]
        bucket["slot_utc"] = slot
        bucket["cycles"] += 1
        bucket["markets_evaluated"] += as_int(
            row["markets_evaluated"] if "markets_evaluated" in columns else scan.get("markets_evaluated")
        )
        bucket["with_edge"] += as_int(scan.get("with_edge"))
        bucket["selected"] += as_int(scan.get("selected"))
        bucket["condition_filtered"] += as_int(scan.get("condition_filtered"))
        bucket["buys"] += as_int(row["buys_count"] if "buys_count" in columns else None)

    gaps = []
    for previous, current in zip(timestamps, timestamps[1:]):
        gap_hours = (current - previous).total_seconds() / 3600
        if gap_hours > LARGE_GAP_HOURS:
            gaps.append(
                {
                    "from": previous.isoformat().replace("+00:00", "Z"),
                    "to": current.isoformat().replace("+00:00", "Z"),
                    "gap_hours": round(gap_hours, 2),
                }
            )

    by_slot = []
    for slot in sorted(slots):
        bucket = dict(slots[slot])
        bucket["slot_label"] = f"{slot:02d}h"
        bucket["markets_evaluated_per_cycle"] = round(
            bucket["markets_evaluated"] / bucket["cycles"], 2
        ) if bucket["cycles"] else 0.0
        bucket["buy_rate_per_market_evaluated"] = pct(bucket["buys"], bucket["markets_evaluated"])
        bucket["buy_rate_per_selected"] = pct(bucket["buys"], bucket["selected"])
        by_slot.append(bucket)

    last_ts = timestamps[-1] if timestamps else None
    hours_ago = None
    if last_ts:
        hours_ago = round((datetime.now(timezone.utc) - last_ts).total_seconds() / 3600, 2)
    if rows and json_payload_rows == 0:
        warnings.append("cycle_events:payload_json_missing_or_invalid")

    return {
        "total": len(rows),
        "first_ts": first_ts_raw,
        "last_ts": last_ts_raw,
        "freshness": {
            "hours_ago": hours_ago,
            "is_fresh": bool(hours_ago is not None and hours_ago <= 30.0),
            "threshold_hours": 30.0,
        },
        "by_slot_utc": by_slot,
        "gaps": gaps,
        "payload_rows_parsed": json_payload_rows,
    }


def collect_markets(conn: sqlite3.Connection, warnings: list[str]) -> dict[str, Any]:
    if not table_exists(conn, "market_snapshots"):
        warnings.append("missing_table:market_snapshots")
        return {
            "total": 0,
            "snapshots_by_city": [],
            "condition_distribution": {},
            "condition_source_counts": {},
        }

    columns = table_columns(conn, "market_snapshots")
    rows = conn.execute("SELECT * FROM market_snapshots ORDER BY ts_utc ASC").fetchall()
    city_counts: Counter[str] = Counter()
    city_cycles: dict[str, set[Any]] = defaultdict(set)
    city_first_last: dict[str, list[str | None]] = {}
    conditions: Counter[str] = Counter()
    condition_sources: Counter[str] = Counter()

    for row in rows:
        city = str(row["city"] if "city" in columns else "unknown" or "unknown")
        city_counts[city] += 1
        if "cycle_number" in columns:
            city_cycles[city].add(row["cycle_number"])
        ts_raw = row["ts_utc"] if "ts_utc" in columns else None
        if city not in city_first_last:
            city_first_last[city] = [ts_raw, ts_raw]
        else:
            city_first_last[city][1] = ts_raw
        condition, source = condition_from_snapshot(row, columns)
        conditions[condition] += 1
        condition_sources[source] += 1

    snapshots_by_city = []
    for city, count in city_counts.most_common():
        first, last = city_first_last.get(city, [None, None])
        snapshots_by_city.append(
            {
                "city": city,
                "snapshots": count,
                "cycles_seen": len(city_cycles.get(city, set())),
                "first_ts": first,
                "last_ts": last,
            }
        )

    if conditions.get("unknown"):
        warnings.append("condition:some_unknown")
    return {
        "total": len(rows),
        "snapshots_by_city": snapshots_by_city,
        "condition_distribution": dict(conditions.most_common()),
        "condition_source_counts": dict(condition_sources.most_common()),
    }


def build_bottlenecks(cycles: dict[str, Any], markets: dict[str, Any]) -> list[dict[str, Any]]:
    bottlenecks: list[dict[str, Any]] = []
    for row in sorted(
        cycles.get("by_slot_utc", []),
        key=lambda item: (item.get("buys", 0), -item.get("markets_evaluated", 0)),
    ):
        if row.get("markets_evaluated", 0) <= 0:
            continue
        if row.get("buys", 0) == 0:
            bottlenecks.append(
                {
                    "type": "slot_evaluated_no_buys",
                    "severity": "WATCH",
                    "slot_utc": row["slot_utc"],
                    "summary": (
                        f"{row['slot_label']} evaluated {row['markets_evaluated']} markets "
                        f"across {row['cycles']} cycles but recorded 0 buys."
                    ),
                    "review": "LOG_ONLY / OPUS_REVIEW_REQUIRED",
                }
            )
        elif row.get("buy_rate_per_market_evaluated", 0.0) < 0.02:
            bottlenecks.append(
                {
                    "type": "slot_low_conversion",
                    "severity": "WATCH",
                    "slot_utc": row["slot_utc"],
                    "summary": (
                        f"{row['slot_label']} buy rate per evaluated market is "
                        f"{row['buy_rate_per_market_evaluated']:.2%}."
                    ),
                    "review": "LOG_ONLY / OPUS_REVIEW_REQUIRED",
                }
            )

    condition_distribution = markets.get("condition_distribution") or {}
    total_conditions = sum(as_int(v) for v in condition_distribution.values())
    exact_range = as_int(condition_distribution.get("exact")) + as_int(condition_distribution.get("range"))
    if total_conditions and exact_range / total_conditions >= 0.5:
        bottlenecks.append(
            {
                "type": "condition_mix_exact_range_heavy",
                "severity": "WATCH_RISK",
                "summary": (
                    f"exact/range account for {exact_range}/{total_conditions} market snapshots "
                    f"({exact_range / total_conditions:.1%})."
                ),
                "review": "LOG_ONLY / OPUS_REVIEW_REQUIRED",
            }
        )
    for gap in cycles.get("gaps", [])[:3]:
        bottlenecks.append(
            {
                "type": "cycle_gap",
                "severity": "WATCH_TECH",
                "summary": f"Cycle gap {gap['gap_hours']}h from {gap['from']} to {gap['to']}.",
                "review": "LOG_ONLY",
            }
        )
    return bottlenecks[:10]


def source_quality(warnings: list[str], schema: dict[str, Any]) -> dict[str, Any]:
    missing = [table for table, present in (schema.get("tables") or {}).items() if not present]
    if missing:
        status = "degraded_missing_tables"
    elif warnings:
        status = "degraded_with_warnings"
    else:
        status = "ok"
    return {
        "status": status,
        "warnings": sorted(set(warnings)),
        "missing_tables": missing,
        "notes": [
            "SQLite opened with URI mode=ro and PRAGMA query_only=ON.",
            "Condition may be inferred from question text when no native condition column exists.",
            LOG_ONLY_DISCLAIMER,
        ],
    }


def build_report(db_path: str) -> dict[str, Any]:
    path = Path(db_path)
    warnings: list[str] = []
    if not path.exists():
        return {
            "generated_at_utc": now_utc(),
            "mode": "LOG_ONLY",
            "status": "db_not_found",
            "db": {"path": db_path, "exists": False},
            "source_quality": {
                "status": "unavailable",
                "warnings": ["db_not_found"],
                "missing_tables": list(EXPECTED_TABLES),
                "notes": [LOG_ONLY_DISCLAIMER],
            },
            "recommendations": ["LOG_ONLY: verify the --db path before interpreting throughput."],
        }

    try:
        conn = open_readonly_db(path)
    except sqlite3.Error as exc:
        return {
            "generated_at_utc": now_utc(),
            "mode": "LOG_ONLY",
            "status": "db_open_error",
            "db": {"path": db_path, "exists": True},
            "error": str(exc),
            "source_quality": {
                "status": "unavailable",
                "warnings": ["db_open_error"],
                "missing_tables": list(EXPECTED_TABLES),
                "notes": [LOG_ONLY_DISCLAIMER],
            },
            "recommendations": ["LOG_ONLY: inspect DB accessibility; do not change runtime behavior."],
        }

    try:
        schema = collect_schema(conn)
        cycles = collect_cycles(conn, warnings)
        markets = collect_markets(conn, warnings)
        bottlenecks = build_bottlenecks(cycles, markets)
        quality = source_quality(warnings, schema)
        status = "ok" if quality["status"] == "ok" else "degraded"
        return {
            "generated_at_utc": now_utc(),
            "mode": "LOG_ONLY",
            "status": status,
            "db": {"path": str(path), "exists": True, **schema},
            "cycles": cycles,
            "markets": markets,
            "top_bottlenecks": bottlenecks,
            "recommendations": [
                "LOG_ONLY: use this report to choose the next read-only audit question.",
                "OPUS_REVIEW_REQUIRED before changing trading, BANKROLL, Fase C, sizing, gates, or schedules.",
            ],
            "source_quality": quality,
        }
    except sqlite3.Error as exc:
        warnings.append("db_read_error")
        return {
            "generated_at_utc": now_utc(),
            "mode": "LOG_ONLY",
            "status": "db_read_error",
            "db": {"path": str(path), "exists": True},
            "error": str(exc),
            "source_quality": {
                "status": "degraded_with_warnings",
                "warnings": warnings,
                "missing_tables": [],
                "notes": [LOG_ONLY_DISCLAIMER],
            },
            "recommendations": ["LOG_ONLY: schema mismatch; inspect read-only before drawing conclusions."],
        }
    finally:
        conn.close()


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def format_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DB Throughput Report",
        "",
        f"- Generated UTC: `{report.get('generated_at_utc')}`",
        f"- Mode: `{report.get('mode', 'LOG_ONLY')}`",
        f"- Status: `{report.get('status')}`",
        f"- DB: `{(report.get('db') or {}).get('path')}`",
        f"- Source quality: `{(report.get('source_quality') or {}).get('status')}`",
        f"- Scope: {LOG_ONLY_DISCLAIMER}",
        "",
        "## DB Freshness",
    ]
    cycles = report.get("cycles") or {}
    freshness = cycles.get("freshness") or {}
    db = report.get("db") or {}
    row_counts = db.get("row_counts") or {}
    lines.extend(
        [
            f"- Tables: `{db.get('tables')}`",
            f"- Row counts: `{row_counts}`",
            f"- First cycle: `{cycles.get('first_ts')}`",
            f"- Last cycle: `{cycles.get('last_ts')}`",
            f"- Hours ago: `{freshness.get('hours_ago')}`",
            f"- Fresh: `{freshness.get('is_fresh')}`",
            "",
            "## Funnel By Slot UTC",
        ]
    )
    slot_rows = []
    for row in cycles.get("by_slot_utc", []):
        slot_rows.append(
            [
                row.get("slot_label"),
                row.get("cycles"),
                row.get("markets_evaluated"),
                row.get("with_edge"),
                row.get("selected"),
                row.get("buys"),
                f"{row.get('buy_rate_per_market_evaluated', 0.0):.2%}",
                f"{row.get('buy_rate_per_selected', 0.0):.2%}",
            ]
        )
    lines.extend(markdown_table(
        ["Slot", "Cycles", "Evaluated", "Edge", "Selected", "Buys", "Buy/Eval", "Buy/Selected"],
        slot_rows or [["-", 0, 0, 0, 0, 0, "0.00%", "0.00%"]],
    ))
    markets = report.get("markets") or {}
    lines.extend(["", "## Snapshots By City"])
    city_rows = [
        [row.get("city"), row.get("snapshots"), row.get("cycles_seen"), row.get("first_ts"), row.get("last_ts")]
        for row in (markets.get("snapshots_by_city") or [])[:12]
    ]
    lines.extend(markdown_table(
        ["City", "Snapshots", "Cycles Seen", "First", "Last"],
        city_rows or [["-", 0, 0, "-", "-"]],
    ))
    lines.extend(
        [
            "",
            "## Conditions",
            f"- Distribution: `{markets.get('condition_distribution') or {}}`",
            f"- Source counts: `{markets.get('condition_source_counts') or {}}`",
            "",
            "## Gaps",
        ]
    )
    gaps = cycles.get("gaps") or []
    if gaps:
        for gap in gaps[:10]:
            lines.append(f"- `{gap['gap_hours']}h`: `{gap['from']}` -> `{gap['to']}`")
    else:
        lines.append("- No large gaps detected.")
    lines.extend(["", "## Top Bottlenecks"])
    bottlenecks = report.get("top_bottlenecks") or []
    if bottlenecks:
        for item in bottlenecks[:10]:
            lines.append(f"- `{item.get('severity')}` `{item.get('type')}`: {item.get('summary')}")
    else:
        lines.append("- No bottleneck detected from available DB fields.")
    lines.extend(["", "## Recommendations"])
    for recommendation in report.get("recommendations") or []:
        lines.append(f"- {recommendation}")
    warnings = (report.get("source_quality") or {}).get("warnings") or []
    if warnings:
        lines.extend(["", "## Warnings"])
        for warning in warnings:
            lines.append(f"- `{warning}`")
    return "\n".join(lines) + "\n"


def write_or_print(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only DB throughput report (LOG_ONLY).")
    parser.add_argument("--db", required=True, help="Path to polymarket.db")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default)")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown")
    parser.add_argument("--output", default=None, help="Optional local output path. Default: stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv)
    report = build_report(args.db)
    if args.markdown:
        write_or_print(format_markdown(report), args.output)
    else:
        write_or_print(json.dumps(report, indent=2, ensure_ascii=False) + "\n", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
