#!/usr/bin/env python3
"""Answer six operational trader/city questions from local LOG_ONLY evidence."""

from __future__ import annotations

import argparse
import ast
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNALS_PATH = REPO_ROOT / "data" / "runtime_import" / "signals.json"
DEFAULT_SNAPSHOTS_PATH = REPO_ROOT / "data" / "intelligence" / "trader_signals_snapshots.jsonl"
DEFAULT_BLOCKED_LIVE_PATH = REPO_ROOT / "data" / "blocked_signals_resolutions.jsonl"
DEFAULT_BLOCKED_DERIVED_PATH = REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
DEFAULT_LIFECYCLE_PATH = REPO_ROOT / "data" / "runtime_import" / "trade_lifecycle.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "intelligence" / "traders_operational_questions_report.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "traders_operational_questions_report_latest.md"
SCHEMA_VERSION = "traders_operational_questions_report_v1"
LOCAL_SOURCE_LABEL = "local/runtime_import"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LOG_ONLY report for trader/city operational questions.")
    parser.add_argument("--signals", default=str(DEFAULT_SIGNALS_PATH))
    parser.add_argument("--snapshots", default=str(DEFAULT_SNAPSHOTS_PATH))
    parser.add_argument("--blocked-resolutions", default=str(DEFAULT_BLOCKED_LIVE_PATH))
    parser.add_argument("--blocked-fallback", default=str(DEFAULT_BLOCKED_DERIVED_PATH))
    parser.add_argument("--trade-lifecycle", default=str(DEFAULT_LIFECYCLE_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--min-hourly-snapshots", type=int, default=2)
    parser.add_argument("--min-trader-n", type=int, default=3)
    parser.add_argument("--min-bot-n", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_json(path: Path, warnings: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        warnings.append(f"{label} missing: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        warnings.append(f"{label} unreadable: {path} ({type(exc).__name__}: {exc})")
        return {}
    return payload if isinstance(payload, dict) else {}


def load_jsonl(path: Path, warnings: list[str], label: str) -> list[dict[str, Any]]:
    if not path.exists():
        warnings.append(f"{label} missing: {path}")
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            warnings.append(f"{label} invalid JSONL row skipped: {path}")
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def resolve_existing(primary: Path, fallback: Path | None) -> tuple[Path, list[Path]]:
    checked = [primary]
    if primary.exists():
        return primary, checked
    if fallback is not None:
        checked.append(fallback)
        if fallback.exists():
            return fallback, checked
    return primary, checked


def signal_id(row: dict[str, Any]) -> str:
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


def pct(wins: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round((wins / total) * 100, 1)


def confidence_from_n(n: int, high: int = 20, medium: int = 5) -> str:
    if n >= high:
        return "high"
    if n >= medium:
        return "medium"
    if n > 0:
        return "low"
    return "insufficient_data"


def load_observed_cities(bot_path: Path, warnings: list[str]) -> set[str]:
    try:
        tree = ast.parse(bot_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        warnings.append(f"OBSERVED_AUDIT_CITIES unavailable: {type(exc).__name__}: {exc}")
        return set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "OBSERVED_AUDIT_CITIES":
                try:
                    value = ast.literal_eval(node.value)
                except Exception as exc:
                    warnings.append(f"OBSERVED_AUDIT_CITIES parse failed: {type(exc).__name__}: {exc}")
                    return set()
                return {str(city) for city in value}
    warnings.append("OBSERVED_AUDIT_CITIES not found in bot.py")
    return set()


def current_signal_rows(signals_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in signals_payload.get("signals", []) if isinstance(row, dict)]


def aggregate_current_signals(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_trader = Counter(str(row.get("trader") or "unknown") for row in rows)
    by_city = Counter(str(row.get("city") or "unknown") for row in rows)
    city_traders: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        city = str(row.get("city") or "unknown")
        trader = str(row.get("trader") or "unknown")
        city_traders[city].add(trader)
    top_traders = [{"trader": trader, "current_signals": n} for trader, n in by_trader.most_common(20)]
    top_cities = [
        {"city": city, "current_signals": n, "distinct_traders": len(city_traders[city])}
        for city, n in by_city.most_common(20)
    ]
    return top_traders, top_cities


def aggregate_blocked(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    by_trader: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "wins": 0})
    by_city: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "wins": 0})
    for row in rows:
        if row.get("resolved") is False:
            continue
        trader = str(row.get("trader") or "unknown")
        city = str(row.get("city") or "unknown")
        by_trader[trader]["n"] += 1
        by_city[city]["n"] += 1
        if row.get("win_for_trader") is True:
            by_trader[trader]["wins"] += 1
            by_city[city]["wins"] += 1
    trader_rows = []
    for trader, stats in by_trader.items():
        n = stats["n"]
        wins = stats["wins"]
        trader_rows.append(
            {
                "trader": trader,
                "blocked_wr_pct": pct(wins, n),
                "blocked_n": n,
                "blocked_wins": wins,
                "confidence": confidence_from_n(n, high=20, medium=5),
            }
        )
    trader_rows.sort(key=lambda row: (-(row["blocked_wr_pct"] or -1), -row["blocked_n"], row["trader"]))
    return trader_rows, by_city


def aggregate_snapshot_activity(rows: list[dict[str, Any]], min_snapshots: int) -> dict[str, Any]:
    signal_rows = [row for row in rows if row.get("row_type", "signal") == "signal"]
    snapshots = sorted({str(row.get("snapshot_at")) for row in signal_rows if row.get("snapshot_at")})
    if len(snapshots) < min_snapshots:
        return {
            "answerability": "NO",
            "confidence": "insufficient_data",
            "distinct_snapshots": len(snapshots),
            "top_activity_hours_utc": [],
            "top_cities_by_snapshot_activity": [],
            "caveat": "Need at least two full snapshots to infer new appearances by hour.",
        }

    seen: set[str] = set()
    by_hour = Counter()
    by_city = Counter()
    ordered = sorted(signal_rows, key=lambda row: (str(row.get("snapshot_at") or ""), str(row.get("signal_id") or "")))
    for row in ordered:
        identity = f"{row.get('trader')}|{row.get('signal_id') or signal_id(row)}"
        if identity in seen:
            continue
        seen.add(identity)
        dt = parse_iso(row.get("snapshot_at"))
        hour = dt.hour if dt else None
        if hour is not None:
            by_hour[f"{hour:02d}:00Z"] += 1
        by_city[str(row.get("city") or "unknown")] += 1

    return {
        "answerability": "YES",
        "confidence": confidence_from_n(len(seen), high=30, medium=5),
        "distinct_snapshots": len(snapshots),
        "top_activity_hours_utc": [
            {"hour_utc": hour, "new_signal_appearances": count}
            for hour, count in by_hour.most_common(12)
        ],
        "top_cities_by_snapshot_activity": [
            {"city": city, "new_signal_appearances": count}
            for city, count in by_city.most_common(20)
        ],
        "caveat": "Counts first observed appearance in local full-snapshot JSONL, not confirmed trade time.",
    }


def aggregate_bot_city_results(lifecycle_payload: dict[str, Any]) -> dict[str, dict[str, int]]:
    by_city: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "wins": 0})
    for row in lifecycle_payload.get("records", []) or []:
        if not isinstance(row, dict):
            continue
        action = (row.get("close_context") or {}).get("close_action")
        city = str(row.get("city") or "unknown")
        if action == "RESOLVED_WIN":
            by_city[city]["n"] += 1
            by_city[city]["wins"] += 1
        elif action == "LOSS_TOTAL":
            by_city[city]["n"] += 1
    return by_city


def build_trader_winning_not_observed(
    blocked_by_city: dict[str, dict[str, int]],
    observed_cities: set[str],
    min_trader_n: int,
) -> list[dict[str, Any]]:
    rows = []
    for city, stats in blocked_by_city.items():
        n = stats["n"]
        wins = stats["wins"]
        if city in observed_cities or n < min_trader_n or wins <= 0:
            continue
        rows.append(
            {
                "city": city,
                "trader_wins": wins,
                "trader_n": n,
                "trader_wr_pct": pct(wins, n),
                "observed_by_us": False,
                "source_label": LOCAL_SOURCE_LABEL,
            }
        )
    rows.sort(key=lambda row: (-(row["trader_wr_pct"] or -1), -row["trader_n"], row["city"]))
    return rows[:20]


def build_trader_winning_bot_gap(
    blocked_by_city: dict[str, dict[str, int]],
    bot_by_city: dict[str, dict[str, int]],
    min_trader_n: int,
    min_bot_n: int,
) -> list[dict[str, Any]]:
    rows = []
    for city, trader_stats in blocked_by_city.items():
        trader_n = trader_stats["n"]
        trader_wins = trader_stats["wins"]
        trader_wr = pct(trader_wins, trader_n)
        if trader_n < min_trader_n or trader_wr is None or trader_wr < 60.0:
            continue
        bot_stats = bot_by_city.get(city, {"n": 0, "wins": 0})
        bot_n = bot_stats["n"]
        bot_wins = bot_stats["wins"]
        bot_wr = pct(bot_wins, bot_n)
        if bot_n < min_bot_n:
            classification = "TRADER_WINNING_BOT_INSUFFICIENT_N"
        elif bot_wr is not None and bot_wr < 50.0:
            classification = "TRADER_WINNING_BOT_NOT_WINNING"
        else:
            classification = "TRADER_WINNING_BOT_OK_OR_MIXED"
        rows.append(
            {
                "city": city,
                "classification": classification,
                "trader_wr_pct": trader_wr,
                "trader_n": trader_n,
                "trader_wins": trader_wins,
                "bot_wr_pct": bot_wr,
                "bot_n": bot_n,
                "bot_wins": bot_wins,
                "source_label": LOCAL_SOURCE_LABEL,
            }
        )
    priority = {
        "TRADER_WINNING_BOT_NOT_WINNING": 0,
        "TRADER_WINNING_BOT_INSUFFICIENT_N": 1,
        "TRADER_WINNING_BOT_OK_OR_MIXED": 2,
    }
    rows.sort(key=lambda row: (priority[row["classification"]], -(row["trader_wr_pct"] or -1), -row["trader_n"], row["city"]))
    return rows[:30]


def question_matrix(
    *,
    signals_payload: dict[str, Any],
    current_rows: list[dict[str, Any]],
    blocked_rows: list[dict[str, Any]],
    snapshot_activity: dict[str, Any],
    blocked_path: Path,
    snapshots_path: Path,
    lifecycle_path: Path,
    observed_cities: set[str],
    trader_winning_bot_gap: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_generated_at = signals_payload.get("generated")
    return [
        {
            "question": "A que hora tienen mas actividad los traders?",
            "answerability": snapshot_activity["answerability"],
            "confidence": snapshot_activity["confidence"],
            "evidence_files": [str(snapshots_path)],
            "fields": ["snapshot_at", "trader", "signal_id", "match_key"],
            "last_updated": source_generated_at,
            "caveats": [snapshot_activity["caveat"]],
        },
        {
            "question": "Que ciudades concentran mas señales/compras trader?",
            "answerability": "YES" if current_rows or blocked_rows else "NO",
            "confidence": confidence_from_n(len(current_rows) + len(blocked_rows), high=80, medium=10),
            "evidence_files": [str(DEFAULT_SIGNALS_PATH), str(blocked_path)],
            "fields": ["signals[].city", "signals[].trader", "blocked.city", "blocked.trader"],
            "last_updated": source_generated_at,
            "caveats": ["signals.json is a current local/runtime_import snapshot; blocked JSONL is historical resolved evidence."],
        },
        {
            "question": "Que traders tienen mas actividad y que WR tienen?",
            "answerability": "YES" if current_rows or blocked_rows else "NO",
            "confidence": confidence_from_n(len(current_rows) + len(blocked_rows), high=80, medium=10),
            "evidence_files": [str(DEFAULT_SIGNALS_PATH), str(blocked_path)],
            "fields": ["signals[].trader", "blocked.trader", "blocked.win_for_trader"],
            "last_updated": source_generated_at,
            "caveats": ["WR here is blocked-resolution WR, not a full external wallet WR."],
        },
        {
            "question": "Que traders tienen mayor WR?",
            "answerability": "YES" if blocked_rows else "NO",
            "confidence": confidence_from_n(len(blocked_rows), high=80, medium=10),
            "evidence_files": [str(blocked_path)],
            "fields": ["blocked.trader", "blocked.win_for_trader", "blocked.resolved"],
            "last_updated": None,
            "caveats": ["Uses local blocked_signals_resolutions sample; per-trader N varies."],
        },
        {
            "question": "Que ciudades son ganadoras para traders y nosotros no observamos?",
            "answerability": "PARTIAL" if blocked_rows and observed_cities else "NO",
            "confidence": "medium" if blocked_rows and observed_cities else "insufficient_data",
            "evidence_files": [str(blocked_path), str(REPO_ROOT / "bot.py")],
            "fields": ["blocked.city", "blocked.win_for_trader", "OBSERVED_AUDIT_CITIES"],
            "last_updated": None,
            "caveats": ["Observed set is read from local bot.py; do not treat local/runtime_import as live production proof."],
        },
        {
            "question": "Que ciudades son ganadoras para traders y no ganadoras para nosotros?",
            "answerability": "PARTIAL" if trader_winning_bot_gap else "NO",
            "confidence": "low" if trader_winning_bot_gap else "insufficient_data",
            "evidence_files": [str(blocked_path), str(lifecycle_path)],
            "fields": ["blocked.city", "blocked.win_for_trader", "trade_lifecycle.records[].close_context.close_action"],
            "last_updated": None,
            "caveats": ["City-level comparison only; low bot_n is classified as TRADER_WINNING_BOT_INSUFFICIENT_N."],
        },
    ]


def render_markdown(payload: dict[str, Any]) -> str:
    def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
        lines = ["| " + " | ".join(label for label, _ in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
        for row in rows:
            lines.append("| " + " | ".join(str(row.get(key, "")) for _, key in columns) + " |")
        return lines

    lines = [
        "# Traders Operational Questions Report",
        "",
        "> LOG_ONLY. Local/runtime_import evidence only. No BUY/SELL/SKIP, no policy, no bankroll.",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Source label: `{payload['source_label']}`",
        "",
        "## Matrix",
        "",
        "| Question | Answerability | Confidence | Caveat |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["questions"]:
        caveat = "; ".join(row.get("caveats", [])[:1])
        lines.append(f"| {row['question']} | {row['answerability']} | {row['confidence']} | {caveat} |")

    sections = [
        ("Top Traders By Activity", "top_traders_by_activity", [("Trader", "trader"), ("Current signals", "current_signals"), ("Blocked WR", "blocked_wr_pct"), ("Blocked n", "blocked_n")]),
        ("Top Traders By Blocked WR", "top_traders_by_blocked_wr", [("Trader", "trader"), ("Blocked WR", "blocked_wr_pct"), ("Blocked n", "blocked_n"), ("Wins", "blocked_wins")]),
        ("Top Cities By Current Trader Activity", "top_cities_by_current_trader_activity", [("City", "city"), ("Current signals", "current_signals"), ("Traders", "distinct_traders")]),
        ("Top Cities By Snapshot Activity", "top_cities_by_snapshot_activity", [("City", "city"), ("New appearances", "new_signal_appearances")]),
        ("Trader Winning Not Observed", "trader_winning_not_observed", [("City", "city"), ("Trader WR", "trader_wr_pct"), ("Trader n", "trader_n"), ("Wins", "trader_wins")]),
        ("Trader Winning Bot Gap", "trader_winning_bot_gap", [("City", "city"), ("Class", "classification"), ("Trader WR", "trader_wr_pct"), ("Trader n", "trader_n"), ("Bot WR", "bot_wr_pct"), ("Bot n", "bot_n")]),
    ]
    for title, key, columns in sections:
        lines.extend(["", f"## {title}", ""])
        rows = payload["tables"].get(key, [])
        if rows:
            lines.extend(table(rows[:12], columns))
        else:
            lines.append("- No data.")
    if payload.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    return "\n".join(lines) + "\n"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    warnings: list[str] = []
    signals_path = Path(args.signals)
    snapshots_path = Path(args.snapshots)
    blocked_path, blocked_checked = resolve_existing(Path(args.blocked_resolutions), Path(args.blocked_fallback))
    lifecycle_path = Path(args.trade_lifecycle)

    signals_payload = load_json(signals_path, warnings, "signals")
    snapshots = load_jsonl(snapshots_path, warnings, "trader_signals_snapshots")
    blocked_rows = load_jsonl(blocked_path, warnings, "blocked_resolutions")
    if not blocked_rows and len(blocked_checked) > 1:
        warnings.append("blocked_resolutions checked paths: " + ", ".join(str(path) for path in blocked_checked))
    lifecycle_payload = load_json(lifecycle_path, warnings, "trade_lifecycle")
    observed_cities = load_observed_cities(REPO_ROOT / "bot.py", warnings)

    current_rows = current_signal_rows(signals_payload)
    top_traders_activity, top_cities_current = aggregate_current_signals(current_rows)
    top_traders_wr, blocked_by_city = aggregate_blocked(blocked_rows)
    blocked_lookup = {row["trader"]: row for row in top_traders_wr}
    top_traders_activity_with_wr = [
        {**row, **{k: blocked_lookup.get(row["trader"], {}).get(k) for k in ("blocked_wr_pct", "blocked_n", "blocked_wins")}}
        for row in top_traders_activity
    ]
    snapshot_activity = aggregate_snapshot_activity(snapshots, args.min_hourly_snapshots)
    bot_by_city = aggregate_bot_city_results(lifecycle_payload)
    trader_winning_not_observed = build_trader_winning_not_observed(
        blocked_by_city,
        observed_cities,
        args.min_trader_n,
    )
    trader_winning_bot_gap = build_trader_winning_bot_gap(
        blocked_by_city,
        bot_by_city,
        args.min_trader_n,
        args.min_bot_n,
    )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "source_label": LOCAL_SOURCE_LABEL,
        "log_only": True,
        "inputs": {
            "signals": str(signals_path),
            "snapshots": str(snapshots_path),
            "blocked_resolutions": str(blocked_path),
            "blocked_paths_checked": [str(path) for path in blocked_checked],
            "trade_lifecycle": str(lifecycle_path),
            "observed_cities_source": str(REPO_ROOT / "bot.py"),
        },
        "source_generated_at": signals_payload.get("generated"),
        "summary": {
            "current_signals": len(current_rows),
            "snapshot_rows": len(snapshots),
            "distinct_snapshot_at": snapshot_activity.get("distinct_snapshots", 0),
            "blocked_rows": len(blocked_rows),
            "observed_cities": len(observed_cities),
            "trade_lifecycle_records": len(lifecycle_payload.get("records", []) or []),
        },
        "questions": [],
        "tables": {
            "top_traders_by_activity": top_traders_activity_with_wr[:20],
            "top_traders_by_blocked_wr": top_traders_wr[:20],
            "top_cities_by_current_trader_activity": top_cities_current[:20],
            "top_cities_by_snapshot_activity": snapshot_activity.get("top_cities_by_snapshot_activity", [])[:20],
            "top_activity_hours_utc": snapshot_activity.get("top_activity_hours_utc", [])[:12],
            "trader_winning_not_observed": trader_winning_not_observed,
            "trader_winning_bot_gap": trader_winning_bot_gap,
        },
        "warnings": warnings,
    }
    payload["questions"] = question_matrix(
        signals_payload=signals_payload,
        current_rows=current_rows,
        blocked_rows=blocked_rows,
        snapshot_activity=snapshot_activity,
        blocked_path=blocked_path,
        snapshots_path=snapshots_path,
        lifecycle_path=lifecycle_path,
        observed_cities=observed_cities,
        trader_winning_bot_gap=trader_winning_bot_gap,
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_report(args)
    if not args.dry_run:
        json_path = Path(args.json_output)
        md_path = Path(args.md_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "dry_run": bool(args.dry_run),
                "questions": {row["question"]: row["answerability"] for row in payload["questions"]},
                "warnings": len(payload["warnings"]),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
