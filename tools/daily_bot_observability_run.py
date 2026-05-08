#!/usr/bin/env python3
"""Run the local daily leaderboard snapshot + digest observability flow.

This runner is local-only. It can write the leaderboard JSONL snapshot when
explicitly requested. Telegram delivery is manual-only behind an explicit flag;
it never touches runtime state, DB, Railway, scheduler, or trading code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import daily_bot_digest
import db_throughput_report
import leaderboard_pnl_snapshot


DEFAULT_SNAPSHOT_PATH = leaderboard_pnl_snapshot.DEFAULT_SNAPSHOT_PATH
DEFAULT_DB_PATH = Path("data") / "polymarket.db"


class RunnerError(Exception):
    pass


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def snapshot_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        wallet=args.wallet,
        env_file=args.env_file,
        user=args.user,
        dashboard_1d=None,
        dashboard_1w=None,
        dashboard_1m=None,
        dashboard_1y=None,
        dashboard_captured_at=None,
    )


def existing_rows(path: Path) -> list[dict[str, Any]]:
    try:
        return leaderboard_pnl_snapshot.read_snapshots(path)
    except leaderboard_pnl_snapshot.SnapshotError as exc:
        raise RunnerError(str(exc)) from exc


def summarize_db_throughput(report: dict[str, Any]) -> dict[str, Any]:
    cycles = report.get("cycles") or {}
    markets = report.get("markets") or {}
    freshness = cycles.get("freshness") or {}
    by_slot = cycles.get("by_slot_utc") or []
    weak_slots = [
        {
            "slot_label": row.get("slot_label"),
            "slot_utc": row.get("slot_utc"),
            "cycles": row.get("cycles", 0),
            "markets_evaluated": row.get("markets_evaluated", 0),
            "buys": row.get("buys", 0),
        }
        for row in sorted(by_slot, key=lambda item: (item.get("buys", 0), -item.get("markets_evaluated", 0)))
        if row.get("markets_evaluated", 0) and row.get("buys", 0) == 0
    ][:3]
    condition_distribution = markets.get("condition_distribution") or {}
    condition_total = sum(int(value or 0) for value in condition_distribution.values())
    dominant_condition = "unknown"
    dominant_condition_count = 0
    if condition_distribution:
        dominant_condition, dominant_condition_count = max(
            condition_distribution.items(),
            key=lambda item: int(item[1] or 0),
        )
    bottlenecks = report.get("top_bottlenecks") or []
    gap_count = len(cycles.get("gaps") or [])
    status = "KEEP"
    suggested_action = "Mantener observacion; no hay accion operativa."
    if report.get("status") != "ok" or not freshness.get("is_fresh") or gap_count:
        status = "WATCH"
        suggested_action = "Revision manual de frescura/gaps antes de interpretar throughput."
    if weak_slots or any(item.get("severity") == "WATCH_RISK" for item in bottlenecks):
        status = "REVIEW_READY"
        suggested_action = "Revision manual; si toca estrategia, llevar a Opus antes de cambiar nada."
    return {
        "mode": "LOG_ONLY",
        "db_status": report.get("status"),
        "source_quality": (report.get("source_quality") or {}).get("status"),
        "fresh": bool(freshness.get("is_fresh")),
        "hours_ago": freshness.get("hours_ago"),
        "gap_count": gap_count,
        "weak_slots": weak_slots,
        "dominant_condition": dominant_condition,
        "dominant_condition_count": int(dominant_condition_count or 0),
        "condition_total": condition_total,
        "review_status": status,
        "suggested_action": suggested_action,
    }


def build_db_throughput_summary(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.db_throughput_report:
        return None
    report = db_throughput_report.build_report(args.db)
    return summarize_db_throughput(report)


def build_run(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.snapshot_file)
    payload = leaderboard_pnl_snapshot.build_snapshot(snapshot_args(args))
    payload["runner_mode"] = "write_snapshot" if args.write_snapshot else "dry_run"
    payload["usable_for_bankroll"] = False
    payload["dashboard_equivalent"] = False
    payload["usable_for_digest"] = True
    payload["usable_for_trend"] = True

    written = False
    db_summary = build_db_throughput_summary(args)

    if args.write_snapshot:
        leaderboard_pnl_snapshot.append_snapshot(path, payload)
        written = True
        digest = daily_bot_digest.build_digest(path, db_throughput=db_summary)
    else:
        rows = existing_rows(path)
        temp_payload = dict(payload)
        temp_payload["temporary_snapshot"] = True
        digest = daily_bot_digest.build_digest_from_rows(rows + [temp_payload], path, db_throughput=db_summary)

    telegram_send_result = {"sent": False, "reason": "not_attempted"}
    if args.send_telegram_manual:
        telegram_send_result = daily_bot_digest.send_telegram_manual(digest["telegram_preview"])

    return {
        "mode": "write_snapshot" if args.write_snapshot else "dry_run",
        "snapshot_file": str(path),
        "snapshot_written": written,
        "snapshot": payload,
        "query_status": payload.get("query_status", "unknown"),
        "source": "polymarket_leaderboard",
        "source_quality": "external_opaque",
        "dashboard_equivalent": False,
        "usable_for_digest": True,
        "usable_for_trend": True,
        "usable_for_bankroll": False,
        "db_throughput": db_summary,
        "decision": {
            "bankroll": "No BANKROLL increase.",
            "operational_use": "Observability only.",
            "trading": "No BUY/SELL/SKIP.",
            "fase_c": "No Fase C.",
        },
        "digest": digest,
        "message": render_run_message(
            digest,
            payload,
            written,
            args.telegram_preview or args.send_telegram_manual,
            telegram_send_result if args.send_telegram_manual else None,
        ),
        "telegram_preview": digest["telegram_preview"],
        "telegram_manual_send": telegram_send_result,
    }


def render_run_message(
    digest: dict[str, Any],
    snapshot: dict[str, Any],
    written: bool,
    include_telegram_preview: bool,
    telegram_send_result: dict[str, Any] | None = None,
) -> str:
    lines = [
        "DAILY BOT OBSERVABILITY RUN",
        f"snapshot_written={str(written).lower()}",
        f"query_status={snapshot.get('query_status', 'unknown')}",
        "source_quality=external_opaque",
        "dashboard_equivalent=false",
        "usable_for_digest=true",
        "usable_for_trend=true",
        "usable_for_bankroll=false",
        "Observability only.",
        "",
        digest["message"],
    ]
    if include_telegram_preview:
        heading = "TELEGRAM MANUAL SEND PREVIEW" if telegram_send_result is not None else "TELEGRAM PREVIEW ONLY"
        lines.extend(["", heading, digest["telegram_preview"]])
    if telegram_send_result is not None:
        lines.extend(["", f"telegram_manual_send={telegram_send_result.get('reason')}"])
        if telegram_send_result.get("missing_env"):
            lines.append("missing_env=" + ",".join(telegram_send_result["missing_env"]))
        if telegram_send_result.get("error"):
            lines.append("telegram_error=" + str(telegram_send_result["error"]))
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily local snapshot + digest observability runner.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Build a temporary snapshot and digest without writing JSONL.")
    mode.add_argument("--write-snapshot", action="store_true", help="Append a snapshot JSONL row before building the digest.")
    parser.add_argument("--telegram-preview", action="store_true", help="Print Telegram-ready preview text only; never sends.")
    parser.add_argument(
        "--send-telegram-manual",
        action="store_true",
        help="Manually send the Telegram digest after printing the preview. No scheduler or retries.",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    parser.add_argument("--snapshot-file", default=str(DEFAULT_SNAPSHOT_PATH), help="Leaderboard snapshot JSONL path.")
    parser.add_argument(
        "--db-throughput-report",
        action="store_true",
        help="Append a brief read-only DB throughput section to the digest.",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path for --db-throughput-report.")
    parser.add_argument("--wallet", help="Manual wallet/proxy wallet override. Output only shows masked wallet.")
    parser.add_argument("--env-file", default=".env", help=argparse.SUPPRESS)
    parser.add_argument("--user", help="Optional manual user label override.")
    args = parser.parse_args(argv)
    if not args.write_snapshot:
        args.dry_run = True
    return args


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv or sys.argv[1:])
    try:
        result = build_run(args)
    except (RunnerError, leaderboard_pnl_snapshot.SnapshotError, daily_bot_digest.DigestError) as exc:
        print(f"daily_bot_observability_run error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"daily_bot_observability_run unexpected error: {leaderboard_pnl_snapshot.compact_error(str(exc))}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.send_telegram_manual and result["telegram_manual_send"].get("reason") == "TELEGRAM_API_ERROR":
            return 2
        return 0
    print(result["message"])
    if args.send_telegram_manual and result["telegram_manual_send"].get("reason") == "TELEGRAM_API_ERROR":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
