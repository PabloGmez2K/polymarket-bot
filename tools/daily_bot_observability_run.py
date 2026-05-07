#!/usr/bin/env python3
"""Run the local daily leaderboard snapshot + digest observability flow.

This runner is local-only. It can write the leaderboard JSONL snapshot when
explicitly requested, but it never sends Telegram messages, reads Telegram
environment variables, touches runtime state, DB, Railway, or trading code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import daily_bot_digest
import leaderboard_pnl_snapshot


DEFAULT_SNAPSHOT_PATH = leaderboard_pnl_snapshot.DEFAULT_SNAPSHOT_PATH


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


def build_run(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.snapshot_file)
    payload = leaderboard_pnl_snapshot.build_snapshot(snapshot_args(args))
    payload["runner_mode"] = "write_snapshot" if args.write_snapshot else "dry_run"
    payload["usable_for_bankroll"] = False
    payload["dashboard_equivalent"] = False
    payload["usable_for_digest"] = True
    payload["usable_for_trend"] = True

    written = False
    if args.write_snapshot:
        leaderboard_pnl_snapshot.append_snapshot(path, payload)
        written = True
        digest = daily_bot_digest.build_digest(path)
    else:
        rows = existing_rows(path)
        temp_payload = dict(payload)
        temp_payload["temporary_snapshot"] = True
        digest = daily_bot_digest.build_digest_from_rows(rows + [temp_payload], path)

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
        "decision": {
            "bankroll": "No BANKROLL increase.",
            "operational_use": "Observability only.",
            "trading": "No BUY/SELL/SKIP.",
            "fase_c": "No Fase C.",
        },
        "digest": digest,
        "message": render_run_message(digest, payload, written, args.telegram_preview),
        "telegram_preview": digest["telegram_preview"],
    }


def render_run_message(
    digest: dict[str, Any],
    snapshot: dict[str, Any],
    written: bool,
    include_telegram_preview: bool,
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
        lines.extend(["", "TELEGRAM PREVIEW ONLY", digest["telegram_preview"]])
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily local snapshot + digest observability runner.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Build a temporary snapshot and digest without writing JSONL.")
    mode.add_argument("--write-snapshot", action="store_true", help="Append a snapshot JSONL row before building the digest.")
    parser.add_argument("--telegram-preview", action="store_true", help="Print Telegram-ready preview text only; never sends.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    parser.add_argument("--snapshot-file", default=str(DEFAULT_SNAPSHOT_PATH), help="Leaderboard snapshot JSONL path.")
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
        return 0
    print(result["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
