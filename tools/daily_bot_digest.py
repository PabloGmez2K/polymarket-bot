#!/usr/bin/env python3
"""Local Daily Bot Digest from external leaderboard P&L snapshots.

This tool is read-only by default. Telegram delivery is manual-only behind an
explicit flag; it does not touch runtime state, scheduler state, DB, or Railway.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


DEFAULT_SNAPSHOT_PATH = Path("data") / "observability" / "leaderboard_pnl_snapshots.jsonl"
MONEY_QUANT = Decimal("0.01")
SOURCE = "polymarket_leaderboard"
SOURCE_QUALITY = "external_opaque"
TELEGRAM_TIMEOUT_SECONDS = 15


class DigestError(Exception):
    pass


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read_snapshots(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DigestError(f"{path}:{line_no}: invalid JSONL: {exc.msg}") from exc
            if isinstance(row, dict):
                rows.append(row)
    return rows


def as_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def quantize_money(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def delta(latest: Any, previous: Any) -> float | None:
    latest_dec = as_decimal(latest)
    previous_dec = as_decimal(previous)
    if latest_dec is None or previous_dec is None:
        return None
    return quantize_money(latest_dec - previous_dec)


def trend_label_from_deltas(deltas: dict[str, float | None]) -> str:
    known = [as_decimal(value) for value in deltas.values() if value is not None]
    values = [value for value in known if value is not None]
    if not values:
        return "unknown"
    total = sum(values, Decimal("0"))
    if total > Decimal("0.01"):
        return "improving"
    if total < Decimal("-0.01"):
        return "worsening"
    return "flat"


def money(value: Any) -> str:
    parsed = as_decimal(value)
    if parsed is None:
        return "unknown"
    return f"{parsed.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):+,.2f}"


def plain_value(value: Any) -> str:
    parsed = as_decimal(value)
    if parsed is None:
        return "unknown"
    return f"{parsed.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):,.2f}"


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def build_deltas(latest: dict[str, Any] | None, previous: dict[str, Any] | None) -> dict[str, float | None]:
    if not latest or not previous:
        return {
            "day_delta": None,
            "week_delta": None,
            "month_delta": None,
            "all_delta": None,
        }
    return {
        "day_delta": delta(latest.get("pnl_day"), previous.get("pnl_day")),
        "week_delta": delta(latest.get("pnl_week"), previous.get("pnl_week")),
        "month_delta": delta(latest.get("pnl_month"), previous.get("pnl_month")),
        "all_delta": delta(latest.get("pnl_all"), previous.get("pnl_all")),
    }


def is_valid_trend_snapshot(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    if str(row.get("query_status", "")).lower() not in {"ok", "success"}:
        return False
    return all(row.get(f"pnl_{name}") is not None for name in ("day", "week", "month", "all"))


def valid_trend_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if is_valid_trend_snapshot(row)]


def normalized_latest(latest: dict[str, Any] | None) -> dict[str, Any] | None:
    if latest is None:
        return None
    normalized = dict(latest)
    normalized["source"] = SOURCE
    normalized["source_quality"] = SOURCE_QUALITY
    normalized["dashboard_equivalent"] = False
    normalized["usable_for_digest"] = True
    normalized["usable_for_trend"] = True
    normalized["usable_for_bankroll"] = False
    normalized["volume_label"] = "leaderboard_trading_volume"
    return normalized


def build_digest_from_rows(rows: list[dict[str, Any]], snapshot_file: str | Path) -> dict[str, Any]:
    latest = normalized_latest(rows[-1]) if rows else None
    valid_rows = valid_trend_snapshots(rows)
    latest_valid = normalized_latest(valid_rows[-1]) if valid_rows else None
    previous_valid = valid_rows[-2] if len(valid_rows) >= 2 else None
    deltas = build_deltas(latest_valid, previous_valid)
    trend_label = trend_label_from_deltas(deltas)
    if latest_valid and not previous_valid:
        trend_label = "unknown"

    payload: dict[str, Any] = {
        "snapshot_file": str(snapshot_file),
        "snapshot_count": len(rows),
        "valid_snapshot_count": len(valid_rows),
        "latest": latest,
        "latest_valid": latest_valid,
        "previous": previous_valid,
        "previous_valid": previous_valid,
        "deltas": deltas,
        "trend_label": trend_label,
        "source": SOURCE,
        "source_quality": SOURCE_QUALITY,
        "dashboard_equivalent": False,
        "usable_for_digest": True,
        "usable_for_trend": True,
        "usable_for_bankroll": False,
        "has_data": latest is not None,
        "latest_snapshot_query_status": latest.get("query_status") if latest else None,
        "no_previous_snapshot": latest_valid is not None and previous_valid is None,
    }
    payload["message"] = render_human_digest(payload)
    payload["telegram_preview"] = render_telegram_digest(payload)
    return payload


def build_digest(path: Path) -> dict[str, Any]:
    return build_digest_from_rows(read_snapshots(path), path)


def resolve_telegram_env() -> tuple[str, str, str | None, list[str]]:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    token_env = "TELEGRAM_BOT_TOKEN" if bot_token else None
    if not bot_token:
        bot_token = os.getenv("TELEGRAM_TOKEN", "")
        token_env = "TELEGRAM_TOKEN" if bot_token else None
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    missing: list[str] = []
    if not bot_token:
        missing.append("TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN")
    if not chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    return bot_token, chat_id, token_env, missing


def send_telegram_manual(message: str) -> dict[str, Any]:
    bot_token, chat_id, token_env, missing = resolve_telegram_env()
    if missing:
        return {
            "sent": False,
            "reason": "TELEGRAM_NOT_CONFIGURED",
            "missing_env": missing,
            "token_env_used": token_env,
        }
    payload = {"chat_id": chat_id, "text": message}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TELEGRAM_TIMEOUT_SECONDS) as resp:
            return {
                "sent": True,
                "reason": "sent",
                "http_code": getattr(resp, "status", None),
                "token_env_used": token_env,
            }
    except urllib.error.HTTPError as exc:
        return {
            "sent": False,
            "reason": "TELEGRAM_API_ERROR",
            "http_code": exc.code,
            "error": f"HTTPError: {exc.code}",
            "token_env_used": token_env,
        }
    except urllib.error.URLError as exc:
        return {
            "sent": False,
            "reason": "TELEGRAM_API_ERROR",
            "error": f"URLError: {exc.reason}",
            "token_env_used": token_env,
        }
    except TimeoutError as exc:
        return {
            "sent": False,
            "reason": "TELEGRAM_API_ERROR",
            "error": f"TimeoutError: {exc}",
            "token_env_used": token_env,
        }


def render_human_digest(digest: dict[str, Any]) -> str:
    latest = digest.get("latest")
    previous = digest.get("previous")
    deltas = digest.get("deltas") or {}
    lines = ["DAILY BOT DIGEST"]
    lines.append("")
    if not latest:
        lines.extend(
            [
                "data_unavailable: No leaderboard P&L snapshot data.",
                f"snapshot_count={digest.get('snapshot_count', 0)}",
                "",
                "P&L leaderboard:",
                "DAY: unknown",
                "WEEK: unknown",
                "MONTH: unknown",
                "ALL: unknown",
                "",
                "Leaderboard trading volume:",
                "DAY: unknown",
                "WEEK: unknown",
                "MONTH: unknown",
                "ALL: unknown",
                "",
                "Trend vs previous valid snapshot:",
                "trend_label=unknown",
                "",
                "Data quality:",
                f"source={SOURCE}",
                f"source_quality={SOURCE_QUALITY}",
                f"dashboard_equivalent={bool_text(False)}",
                f"usable_for_digest={bool_text(True)}",
                f"usable_for_trend={bool_text(True)}",
                f"usable_for_bankroll={bool_text(False)}",
                "",
                "Decision:",
                "No BANKROLL increase.",
                "Observability only.",
                "No BUY/SELL/SKIP.",
                "No Fase C.",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"captured_at_utc: {latest.get('captured_at_utc', 'unknown')}",
            f"query_status: {latest.get('query_status', 'unknown')}",
            "",
            "P&L leaderboard:",
            f"DAY: {money(latest.get('pnl_day'))}",
            f"WEEK: {money(latest.get('pnl_week'))}",
            f"MONTH: {money(latest.get('pnl_month'))}",
            f"ALL: {money(latest.get('pnl_all'))}",
            "",
            "Leaderboard trading volume:",
            f"DAY: {plain_value(latest.get('vol_day'))}",
            f"WEEK: {plain_value(latest.get('vol_week'))}",
            f"MONTH: {plain_value(latest.get('vol_month'))}",
            f"ALL: {plain_value(latest.get('vol_all'))}",
            "",
            "Trend vs previous valid snapshot:",
        ]
    )
    latest_valid = digest.get("latest_valid")
    if latest_valid and not is_valid_trend_snapshot(latest):
        lines.append(f"last_valid_snapshot_captured_at_utc: {latest_valid.get('captured_at_utc', 'unknown')}")
    if previous is None:
        lines.append("No previous valid snapshot yet")
    else:
        lines.append(f"previous_valid_captured_at_utc: {previous.get('captured_at_utc', 'unknown')}")
    lines.extend(
        [
            f"day_delta: {money(deltas.get('day_delta'))}",
            f"week_delta: {money(deltas.get('week_delta'))}",
            f"month_delta: {money(deltas.get('month_delta'))}",
            f"all_delta: {money(deltas.get('all_delta'))}",
            f"trend_label={digest.get('trend_label', 'unknown')}",
            "",
            "Data quality:",
            f"source={SOURCE}",
            f"source_quality={SOURCE_QUALITY}",
            f"dashboard_equivalent={bool_text(False)}",
            f"usable_for_digest={bool_text(True)}",
            f"usable_for_trend={bool_text(True)}",
            f"usable_for_bankroll={bool_text(False)}",
            "",
            "Decision:",
            "No BANKROLL increase.",
            "Observability only.",
            "No BUY/SELL/SKIP.",
            "No Fase C.",
        ]
    )
    return "\n".join(lines)


def render_telegram_digest(digest: dict[str, Any]) -> str:
    latest = digest.get("latest")
    if not latest:
        return "\n".join(
            [
                "DAILY BOT DIGEST",
                "data_unavailable: No leaderboard P&L snapshot data.",
                "",
                "P&L leaderboard",
                "DAY unknown | WEEK unknown",
                "MONTH unknown | ALL unknown",
                "",
                "Leaderboard trading volume",
                "DAY unknown | WEEK unknown",
                "MONTH unknown | ALL unknown",
                "",
                "Trend vs previous valid snapshot",
                "trend_label=unknown",
                "",
                f"source={SOURCE} | source_quality={SOURCE_QUALITY}",
                "dashboard_equivalent=false",
                "usable_for_digest=true | usable_for_trend=true | usable_for_bankroll=false",
                "Decision: No BANKROLL increase. Observability only. No BUY/SELL/SKIP. No Fase C.",
            ]
        )
    deltas = digest.get("deltas") or {}
    trend_intro = "No previous valid snapshot yet"
    previous = digest.get("previous")
    latest_valid = digest.get("latest_valid")
    if latest_valid and not is_valid_trend_snapshot(latest):
        trend_intro = f"last_valid_snapshot_captured_at_utc: {latest_valid.get('captured_at_utc', 'unknown')}"
    if previous:
        trend_intro = f"previous_valid_captured_at_utc: {previous.get('captured_at_utc', 'unknown')}"
    return "\n".join(
        [
            "DAILY BOT DIGEST",
            f"captured_at_utc: {latest.get('captured_at_utc', 'unknown')}",
            f"query_status: {latest.get('query_status', 'unknown')}",
            "",
            "P&L leaderboard",
            f"DAY {money(latest.get('pnl_day'))} | WEEK {money(latest.get('pnl_week'))}",
            f"MONTH {money(latest.get('pnl_month'))} | ALL {money(latest.get('pnl_all'))}",
            "",
            "Leaderboard trading volume",
            f"DAY {plain_value(latest.get('vol_day'))} | WEEK {plain_value(latest.get('vol_week'))}",
            f"MONTH {plain_value(latest.get('vol_month'))} | ALL {plain_value(latest.get('vol_all'))}",
            "",
            "Trend vs previous valid snapshot",
            trend_intro,
            (
                f"day_delta {money(deltas.get('day_delta'))} | "
                f"week_delta {money(deltas.get('week_delta'))}"
            ),
            (
                f"month_delta {money(deltas.get('month_delta'))} | "
                f"all_delta {money(deltas.get('all_delta'))}"
            ),
            f"trend_label={digest.get('trend_label', 'unknown')}",
            "",
            f"source={SOURCE} | source_quality={SOURCE_QUALITY}",
            "dashboard_equivalent=false",
            "usable_for_digest=true | usable_for_trend=true | usable_for_bankroll=false",
            "Decision: No BANKROLL increase. Observability only. No BUY/SELL/SKIP. No Fase C.",
        ]
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily Bot Digest dry-run and Telegram preview CLI.")
    parser.add_argument("--snapshot-file", default=str(DEFAULT_SNAPSHOT_PATH), help="Leaderboard snapshot JSONL path.")
    parser.add_argument("--dry-run", action="store_true", help="Print the human digest and write nothing.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON with latest, previous, deltas, and message.")
    parser.add_argument(
        "--telegram-preview",
        action="store_true",
        help="Print Telegram-ready preview text only. Does not send Telegram.",
    )
    parser.add_argument(
        "--send-telegram-manual",
        action="store_true",
        help="Manually send the Telegram digest after printing the preview. No scheduler or retries.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv or sys.argv[1:])
    try:
        digest = build_digest(Path(args.snapshot_file))
    except DigestError as exc:
        print(f"daily_bot_digest error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(digest, indent=2, sort_keys=True))
        return 0
    if args.telegram_preview or args.send_telegram_manual:
        print(digest["telegram_preview"])
        if args.send_telegram_manual:
            result = send_telegram_manual(digest["telegram_preview"])
            print("")
            print(f"telegram_manual_send={result.get('reason')}")
            if result.get("missing_env"):
                print("missing_env=" + ",".join(result["missing_env"]))
            if result.get("error"):
                print("telegram_error=" + str(result["error"]))
            return 0 if result.get("reason") in {"sent", "TELEGRAM_NOT_CONFIGURED"} else 2
        return 0
    print(digest["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
