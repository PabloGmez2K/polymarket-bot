#!/usr/bin/env python3
"""Read-only daily monitor for Unsellable Guard v1 LOG_ONLY candidates."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


GUARD_VERSION = "unsellable_v1"
CANDIDATE_REASON = "unsellable_guard_candidate"
REAL_SKIP_REASON = "unsellable_liquidity_guard"
ROTATED_LOG_RE = re.compile(r"^skip_log\.(\d{4}-\d{2}-\d{2})\.jsonl$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize Unsellable Guard v1 LOG_ONLY candidates from skip_log."
    )
    parser.add_argument("--data-dir", default="data", help="Runtime data directory.")
    parser.add_argument(
        "--skip-log",
        default=None,
        help="Path to skip_log.jsonl. Defaults to <data-dir>/skip_log.jsonl.",
    )
    parser.add_argument("--hours", type=float, default=24.0, help="Lookback window in hours.")
    parser.add_argument("--json", action="store_true", help="Emit stable JSON output.")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown output.")
    parser.add_argument("--now-utc", default=None, help="Override current UTC ISO timestamp.")
    parser.add_argument("--dry-run", action="store_true", help="Accepted for consistency; no writes occur.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
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


def parse_now(value: str | None) -> datetime:
    parsed = parse_dt(value)
    if parsed is not None:
        return parsed
    return datetime.now(timezone.utc)


def default_skip_log(data_dir: Path) -> Path:
    return data_dir / "skip_log.jsonl"


def iter_log_paths(skip_log: Path) -> list[Path]:
    data_dir = skip_log.parent
    paths: list[tuple[datetime, Path]] = []
    if data_dir.exists():
        for path in data_dir.iterdir():
            match = ROTATED_LOG_RE.match(path.name)
            if not match:
                continue
            parsed = parse_dt(match.group(1) + "T00:00:00+00:00")
            if parsed is not None:
                paths.append((parsed, path))
    paths.sort(key=lambda item: (item[0], item[1].name))
    ordered = [path for _, path in paths]
    if skip_log.exists():
        ordered.append(skip_log)
    return ordered


def load_rows(skip_log: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0
    for path in iter_log_paths(skip_log):
        try:
            with path.open("r", encoding="utf-8-sig") as handle:
                for lineno, raw_line in enumerate(handle, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        malformed += 1
                        continue
                    if not isinstance(payload, dict):
                        malformed += 1
                        continue
                    payload["_source_file"] = path.name
                    payload["_source_line"] = lineno
                    payload["_ts_dt"] = parse_dt(payload.get("ts_utc"))
                    rows.append(payload)
        except OSError:
            malformed += 1
    rows.sort(
        key=lambda row: (
            row.get("_ts_dt") or datetime.min.replace(tzinfo=timezone.utc),
            str(row.get("cycle_id") or ""),
            str(row.get("city") or ""),
            int(row.get("_source_line") or 0),
        )
    )
    return rows, malformed


def extras(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("extras")
    return value if isinstance(value, dict) else {}


def is_candidate(row: dict[str, Any]) -> bool:
    extra = extras(row)
    return (
        row.get("skip_reason") == CANDIDATE_REASON
        and extra.get("guard_version") == GUARD_VERSION
        and extra.get("guard_action") == "would_skip"
    )


def text_has_real_skip(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    return REAL_SKIP_REASON in text or "unsellable liquidity guard" in text


def is_unexpected_real_skip(row: dict[str, Any]) -> bool:
    extra = extras(row)
    return (
        row.get("skip_reason") == REAL_SKIP_REASON
        or extra.get("guard_action") == "skipped"
        or text_has_real_skip(row.get("reason"))
        or text_has_real_skip(row.get("msg"))
        or text_has_real_skip(extra.get("reason"))
        or text_has_real_skip(extra.get("msg"))
    )


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).strip().replace("$", ""))
    except (TypeError, ValueError):
        return None


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def compact_example(row: dict[str, Any]) -> dict[str, Any]:
    extra = extras(row)
    question = str(extra.get("question") or row.get("question") or "")
    if len(question) > 120:
        question = question[:117] + "..."
    return {
        "ts_utc": row.get("ts_utc"),
        "city": row.get("city"),
        "date_iso": row.get("date_iso"),
        "side": extra.get("side", row.get("side")),
        "condition": row.get("condition"),
        "price_at_guard": as_float(extra.get("price_at_guard")),
        "amount": as_float(extra.get("amount")),
        "size_ratio": as_float(extra.get("size_ratio")),
        "edge_pct": as_float(extra.get("edge_pct", row.get("edge_pct"))),
        "question": question,
    }


def status_for(candidates_24h: int, candidates_all_time: int, safety_count: int) -> str:
    if safety_count > 0:
        return "ACTION_SAFETY"
    if candidates_24h >= 3 or candidates_all_time >= 5:
        return "ACTION_REVIEW"
    if candidates_24h >= 1:
        return "WATCH"
    return "OK"


def build_report(skip_log: Path, now: datetime, hours: float) -> dict[str, Any]:
    rows, malformed = load_rows(skip_log)
    cutoff_24h = now - timedelta(hours=max(0.0, hours))
    cutoff_7d = now - timedelta(days=7)

    candidate_rows = [row for row in rows if is_candidate(row)]
    safety_rows = [row for row in rows if is_unexpected_real_skip(row)]

    candidates_24h = [
        row for row in candidate_rows
        if row.get("_ts_dt") is not None and row["_ts_dt"] >= cutoff_24h
    ]
    candidates_7d = [
        row for row in candidate_rows
        if row.get("_ts_dt") is not None and row["_ts_dt"] >= cutoff_7d
    ]
    safety_24h = [
        row for row in safety_rows
        if row.get("_ts_dt") is not None and row["_ts_dt"] >= cutoff_24h
    ]
    safety_count = len(safety_rows)

    cities = Counter(str(row.get("city") or "unknown") for row in candidates_24h)
    conditions = Counter(str(row.get("condition") or "unknown") for row in candidates_24h)
    size_ratios = [
        value for row in candidates_24h
        for value in [as_float(extras(row).get("size_ratio"))]
        if value is not None
    ]
    prices = [
        value for row in candidates_24h
        for value in [as_float(extras(row).get("price_at_guard"))]
        if value is not None
    ]
    candidate_times = [
        row["_ts_dt"] for row in candidate_rows
        if row.get("_ts_dt") is not None
    ]
    safety_times = [
        row["_ts_dt"] for row in safety_rows
        if row.get("_ts_dt") is not None
    ]
    top_candidate_examples = sorted(
        candidates_24h,
        key=lambda row: as_float(extras(row).get("size_ratio")) or 0.0,
        reverse=True,
    )[:3]
    top_safety_examples = sorted(
        safety_rows,
        key=lambda row: row.get("_ts_dt") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:3]

    report = {
        "schema_version": 1,
        "guard_version": GUARD_VERSION,
        "status": status_for(len(candidates_24h), len(candidate_rows), safety_count),
        "generated_at": now.isoformat(),
        "window_hours": hours,
        "skip_log": str(skip_log),
        "log_files_read": [str(path) for path in iter_log_paths(skip_log)],
        "malformed_rows": malformed,
        "total_candidates_24h": len(candidates_24h),
        "total_candidates_7d": len(candidates_7d),
        "total_candidates_all_time": len(candidate_rows),
        "unexpected_real_skips_count": safety_count,
        "unexpected_real_skips_24h": len(safety_24h),
        "first_candidate_at": min(candidate_times).isoformat() if candidate_times else None,
        "last_candidate_at": max(candidate_times).isoformat() if candidate_times else None,
        "last_safety_at": max(safety_times).isoformat() if safety_times else None,
        "top_cities": [{"city": city, "count": count} for city, count in cities.most_common(10)],
        "conditions": [{"condition": cond, "count": count} for cond, count in conditions.most_common()],
        "avg_size_ratio": average(size_ratios),
        "avg_price_at_guard": average(prices),
        "examples": [compact_example(row) for row in top_candidate_examples],
        "safety_examples": [compact_example(row) for row in top_safety_examples],
        "manual_review_required": len(candidates_24h) >= 1 or safety_count > 0,
        "promotion_note": "Revision manual / Opus requerida antes de promocion. No activar SKIP automaticamente.",
    }
    return report


def fmt_float(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def format_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Unsellable Guard Monitor",
        "",
        f"- Status: **{report.get('status')}**",
        f"- Window: last {fmt_float(report.get('window_hours'), 1)}h",
        f"- Candidates 24h: {report.get('total_candidates_24h', 0)}",
        f"- Candidates 7d: {report.get('total_candidates_7d', 0)}",
        f"- Candidates all-time: {report.get('total_candidates_all_time', 0)}",
        f"- Unexpected real skips: {report.get('unexpected_real_skips_count', 0)}",
        f"- First candidate: {report.get('first_candidate_at') or 'n/a'}",
        f"- Last candidate: {report.get('last_candidate_at') or 'n/a'}",
        f"- Avg size_ratio: {fmt_float(report.get('avg_size_ratio'), 4)}",
        f"- Avg price_at_guard: {fmt_float(report.get('avg_price_at_guard'), 4)}",
        "",
        "## Top Cities",
    ]
    cities = report.get("top_cities") or []
    if cities:
        lines.extend(f"- {item.get('city')}: {item.get('count')}" for item in cities)
    else:
        lines.append("- none")

    lines.extend(["", "## Conditions"])
    conditions = report.get("conditions") or []
    if conditions:
        lines.extend(f"- {item.get('condition')}: {item.get('count')}" for item in conditions)
    else:
        lines.append("- none")

    lines.extend(["", "## Examples"])
    examples = report.get("examples") or []
    if examples:
        for idx, item in enumerate(examples, start=1):
            lines.append(
                f"{idx}. {item.get('city') or '?'} {item.get('side') or '?'} "
                f"{item.get('condition') or '?'} | price={fmt_float(item.get('price_at_guard'))} "
                f"| size_ratio={fmt_float(item.get('size_ratio'), 4)}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Action", str(report.get("promotion_note") or "")])
    return "\n".join(lines)


def main() -> int:
    configure_stdout()
    args = parse_args()
    data_dir = Path(args.data_dir)
    skip_log = Path(args.skip_log) if args.skip_log else default_skip_log(data_dir)
    now = parse_now(args.now_utc)
    report = build_report(skip_log, now, args.hours)
    if args.json or not args.markdown:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(format_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
