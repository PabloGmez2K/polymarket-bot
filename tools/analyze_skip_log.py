#!/usr/bin/env python3
"""Offline analyzer for R3 skip_log.jsonl."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_MIN_EDGE = 3.0
DEFAULT_LAST_N_CYCLES = 30
DEFAULT_RUNTIME_IMPORT_DIRNAME = "runtime_import"
EXPECTED_SKIP_REASONS = [
    "no_edge",
    "below_min_edge",
    "kelly_too_low",
    "shadow_only_override",
    "existing_order",
    "sold_this_cycle",
    "existing_position",
    "blocked_city",
    "fuera_allowlist",
    "timezone_filter",
    "date_out_of_range_past",
    "date_out_of_range_future",
    "price_out_of_range",
    "liquidity_low",
    "condition_filtered",
    "forecast_missing",
    "parse_fail",
]
ROTATED_LOG_RE = re.compile(r"^skip_log\.(\d{4}-\d{2}-\d{2})\.jsonl$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze skip_log.jsonl from data/runtime_import/ (preferred) or data/ and rotated R3 skip logs."
    )
    parser.add_argument(
        "--last-n-cycles",
        type=int,
        default=DEFAULT_LAST_N_CYCLES,
        help=f"Limit analysis to the last N unique cycle_id values (default: {DEFAULT_LAST_N_CYCLES}).",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Keep rows with ts_utc on or after this UTC date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--city",
        type=str,
        help="Optional city filter (case-insensitive exact match).",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Optional path to export the filtered raw rows as CSV.",
    )
    parser.add_argument(
        "--min-edge",
        type=float,
        default=DEFAULT_MIN_EDGE,
        help=f"MIN_EDGE threshold used for near-miss detection (default: {DEFAULT_MIN_EDGE:.1f}).",
    )
    args = parser.parse_args()
    if args.last_n_cycles is not None and args.last_n_cycles < 1:
        parser.error("--last-n-cycles must be >= 1")
    return args


def stderr_warning(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def parse_ts_utc(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
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


def parse_since_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"--since inválido: {value!r}. Usá YYYY-MM-DD.") from exc
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


def iter_log_paths(data_dir: Path) -> list[Path]:
    current_path = data_dir / "skip_log.jsonl"
    if not current_path.exists():
        return []

    rotated: list[tuple[date, Path]] = []
    for path in data_dir.iterdir():
        match = ROTATED_LOG_RE.match(path.name)
        if not match:
            continue
        try:
            day = date.fromisoformat(match.group(1))
        except ValueError:
            stderr_warning(f"ignoring rotated log with invalid date: {path.name}")
            continue
        rotated.append((day, path))

    rotated.sort(key=lambda item: (item[0], item[1].name))
    return [item[1] for item in rotated] + [current_path]


def load_records(data_dir: Path) -> tuple[list[dict], int]:
    records: list[dict] = []
    malformed_count = 0

    for path in iter_log_paths(data_dir):
        try:
            with path.open("r", encoding="utf-8") as handle:
                for lineno, raw_line in enumerate(handle, start=1):
                    line = raw_line.strip().lstrip("\ufeff")
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError as exc:
                        malformed_count += 1
                        stderr_warning(f"{path.name}:{lineno}: malformed JSON skipped ({exc.msg})")
                        continue
                    if not isinstance(payload, dict):
                        malformed_count += 1
                        stderr_warning(f"{path.name}:{lineno}: non-object JSON skipped")
                        continue
                    payload["_source_file"] = path.name
                    payload["_source_line"] = lineno
                    payload["_ts_dt"] = parse_ts_utc(payload.get("ts_utc"))
                    records.append(payload)
        except OSError as exc:
            stderr_warning(f"{path.name}: read failed ({exc})")

    records.sort(
        key=lambda row: (
            row.get("_ts_dt") or datetime.min.replace(tzinfo=timezone.utc),
            str(row.get("cycle_id") or ""),
            str(row.get("city") or ""),
            str(row.get("skip_reason") or ""),
            row.get("_source_file") or "",
            int(row.get("_source_line") or 0),
        )
    )
    return records, malformed_count


def normalize_city(city: object) -> str:
    return str(city or "").strip().casefold()


def filter_records(records: list[dict], args: argparse.Namespace) -> list[dict]:
    filtered = list(records)

    since_dt = parse_since_date(args.since)
    if since_dt is not None:
        filtered = [row for row in filtered if row.get("_ts_dt") and row["_ts_dt"] >= since_dt]

    if args.city:
        target_city = normalize_city(args.city)
        filtered = [row for row in filtered if normalize_city(row.get("city")) == target_city]

    if args.last_n_cycles:
        cycle_order: list[str] = []
        seen_cycles: set[str] = set()
        for row in filtered:
            cycle_id = row.get("cycle_id")
            if not cycle_id or cycle_id in seen_cycles:
                continue
            seen_cycles.add(cycle_id)
            cycle_order.append(cycle_id)
        keep_cycles = set(cycle_order[-args.last_n_cycles :])
        filtered = [row for row in filtered if row.get("cycle_id") in keep_cycles]

    return filtered


def format_pct(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "n/a"
    return f"{value:.1f}%"


def format_number(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if value is None:
        return "n/a"
    return str(value)


def format_delta(value: int) -> str:
    return f"{value:+d}"


def format_delta_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    if math.isinf(value):
        return "+inf%"
    return f"{value:+.1f}%"


def render_table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    row_strings = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in row_strings:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def build_line(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values))

    lines = [
        build_line(headers),
        "-+-".join("-" * width for width in widths),
    ]
    for row in row_strings:
        lines.append(build_line(row))
    return "\n".join(lines)


def build_distribution_section(records: list[dict]) -> str:
    city_reason_counts: dict[str, Counter[str]] = defaultdict(Counter)
    city_totals: Counter[str] = Counter()

    for row in records:
        city = row.get("city") or "(null)"
        reason = row.get("skip_reason") or "(missing)"
        city_reason_counts[city][reason] += 1
        city_totals[city] += 1

    rows: list[list[object]] = []
    for city, total in sorted(city_totals.items(), key=lambda item: (-item[1], item[0])):
        reason_counts = city_reason_counts[city]
        for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0])):
            pct = (count / total * 100.0) if total else 0.0
            rows.append([city, total, reason, count, format_pct(pct)])

    if not rows:
        return "1. Distribución de skip_reason por ciudad\n\nSin filas para los filtros solicitados."

    table = render_table(
        ["City", "Total", "Skip Reason", "Count", "% City"],
        rows,
    )
    return f"1. Distribución de skip_reason por ciudad\n\n{table}"


def build_trend_section(records: list[dict]) -> str:
    cycle_order: list[str] = []
    seen: set[str] = set()
    for row in records:
        cycle_id = row.get("cycle_id")
        if not cycle_id or cycle_id in seen:
            continue
        seen.add(cycle_id)
        cycle_order.append(cycle_id)

    if len(cycle_order) < 2:
        return (
            "2. Trend temporal\n\n"
            "No hay suficientes ciclos para comparar ventanas. Hacen falta al menos 2 cycle_id distintos."
        )

    half = len(cycle_order) // 2
    if half < 1:
        half = 1
    older_cycles = cycle_order[-(2 * half) : -half]
    newer_cycles = cycle_order[-half:]

    older_set = set(older_cycles)
    newer_set = set(newer_cycles)
    older_counts: Counter[str] = Counter()
    newer_counts: Counter[str] = Counter()

    for row in records:
        reason = row.get("skip_reason") or "(missing)"
        cycle_id = row.get("cycle_id")
        if cycle_id in older_set:
            older_counts[reason] += 1
        elif cycle_id in newer_set:
            newer_counts[reason] += 1

    reasons = list(EXPECTED_SKIP_REASONS)
    for reason in sorted(set(older_counts) | set(newer_counts)):
        if reason not in reasons:
            reasons.append(reason)

    rows: list[list[object]] = []
    for reason in reasons:
        older = older_counts.get(reason, 0)
        newer = newer_counts.get(reason, 0)
        delta_abs = newer - older
        if older == 0:
            delta_pct = math.inf if newer > 0 else 0.0
        else:
            delta_pct = (delta_abs / older) * 100.0
        arrow = ""
        if older > 0 and abs(delta_pct) > 20.0:
            arrow = "↑" if delta_pct > 0 else "↓"
        elif older == 0 and newer > 0:
            arrow = "↑"
        rows.append(
            [
                reason,
                older,
                newer,
                format_delta(delta_abs),
                format_delta_pct(delta_pct),
                arrow,
            ]
        )

    table = render_table(
        ["Skip Reason", f"Prev {half}c", f"Last {half}c", "Delta", "Delta %", "Mark"],
        rows,
    )
    meta = (
        f"Ventanas comparadas: previas={half} ciclos ({older_cycles[0]} → {older_cycles[-1]}) | "
        f"últimas={half} ciclos ({newer_cycles[0]} → {newer_cycles[-1]})"
    )
    return f"2. Trend temporal\n\n{meta}\n\n{table}"


def build_near_misses(records: list[dict], min_edge: float) -> list[dict]:
    lower_bound = min_edge - 3.0
    near_misses = []
    for row in records:
        if row.get("skip_reason") != "below_min_edge":
            continue
        edge_pct = row.get("edge_pct")
        if not isinstance(edge_pct, (int, float)):
            continue
        if lower_bound <= edge_pct < min_edge:
            near_misses.append(row)

    near_misses.sort(
        key=lambda row: (
            -float(row.get("edge_pct") or float("-inf")),
            str(row.get("city") or ""),
            str(row.get("date_iso") or ""),
            str(row.get("side") or ""),
        )
    )
    return near_misses[:20]


def build_near_misses_section(records: list[dict], min_edge: float) -> str:
    near_misses = build_near_misses(records, min_edge)
    if not near_misses:
        return (
            "3. Near-misses\n\n"
            f"No hay filas `below_min_edge` en el rango [{min_edge - 3.0:.1f}, {min_edge:.1f})."
        )

    rows = []
    for row in near_misses:
        rows.append(
            [
                row.get("city") or "(null)",
                row.get("date_iso") or "n/a",
                row.get("side") or "n/a",
                format_number(row.get("edge_pct")),
                format_number(row.get("our_prob")),
                format_number(row.get("mkt_prob")),
                format_number(row.get("forecast_max")),
            ]
        )
    table = render_table(
        ["City", "Date", "Side", "Edge %", "Our %", "Mkt %", "Forecast Max"],
        rows,
    )
    return (
        "3. Near-misses\n\n"
        f"Top 20 para `below_min_edge` con edge_pct en [{min_edge - 3.0:.1f}, {min_edge:.1f}).\n\n"
        f"{table}"
    )


def write_csv(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ts_utc",
        "cycle_id",
        "city",
        "date_iso",
        "side",
        "skip_reason",
        "city_mode",
        "allowlisted",
        "days_ahead",
        "edge_pct",
        "our_prob",
        "mkt_prob",
        "min_edge",
        "forecast_max",
        "threshold",
        "threshold_high",
        "unit",
        "condition",
        "sigma_used",
        "question",
        "extras_json",
        "_source_file",
        "_source_line",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    "ts_utc": row.get("ts_utc"),
                    "cycle_id": row.get("cycle_id"),
                    "city": row.get("city"),
                    "date_iso": row.get("date_iso"),
                    "side": row.get("side"),
                    "skip_reason": row.get("skip_reason"),
                    "city_mode": row.get("city_mode"),
                    "allowlisted": row.get("allowlisted"),
                    "days_ahead": row.get("days_ahead"),
                    "edge_pct": row.get("edge_pct"),
                    "our_prob": row.get("our_prob"),
                    "mkt_prob": row.get("mkt_prob"),
                    "min_edge": row.get("min_edge"),
                    "forecast_max": row.get("forecast_max"),
                    "threshold": row.get("threshold"),
                    "threshold_high": row.get("threshold_high"),
                    "unit": row.get("unit"),
                    "condition": row.get("condition"),
                    "sigma_used": row.get("sigma_used"),
                    "question": row.get("question"),
                    "extras_json": json.dumps(row.get("extras", {}), ensure_ascii=True, sort_keys=True),
                    "_source_file": row.get("_source_file"),
                    "_source_line": row.get("_source_line"),
                }
            )


def main() -> int:
    args = parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    repo_data_dir = Path(__file__).resolve().parent.parent / "data"
    runtime_import_dir = repo_data_dir / DEFAULT_RUNTIME_IMPORT_DIRNAME
    data_dir = runtime_import_dir if (runtime_import_dir / "skip_log.jsonl").exists() else repo_data_dir
    current_log = data_dir / "skip_log.jsonl"
    if not current_log.exists():
        print("skip_log.jsonl no existe ni en data/runtime_import ni en data/.", file=sys.stderr)
        return 1

    all_records, _malformed = load_records(data_dir)
    if not all_records:
        print("skip_log vacío — aún no corrió ningún ciclo con R3")
        return 0

    filtered = filter_records(all_records, args)
    if args.csv:
        write_csv(filtered, Path(args.csv))

    sections = [
        build_distribution_section(filtered),
        build_trend_section(filtered),
        build_near_misses_section(filtered, args.min_edge),
    ]
    print("\n\n".join(sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
