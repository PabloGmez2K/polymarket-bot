#!/usr/bin/env python3
"""Local Daily Bot Digest from external leaderboard P&L snapshots.

This tool is read-only and preview-only. It does not send Telegram messages,
read Telegram environment variables, touch runtime state, or write files.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


DEFAULT_SNAPSHOT_PATH = Path("data") / "observability" / "leaderboard_pnl_snapshots.jsonl"
MONEY_QUANT = Decimal("0.01")
SOURCE = "polymarket_leaderboard"
SOURCE_QUALITY = "external_opaque"


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


def build_digest(path: Path) -> dict[str, Any]:
    rows = read_snapshots(path)
    latest = normalized_latest(rows[-1]) if rows else None
    previous = rows[-2] if len(rows) >= 2 else None
    deltas = build_deltas(latest, previous)
    trend_label = trend_label_from_deltas(deltas)
    if latest and not previous:
        trend_label = "unknown"

    payload: dict[str, Any] = {
        "snapshot_file": str(path),
        "snapshot_count": len(rows),
        "latest": latest,
        "previous": previous,
        "deltas": deltas,
        "trend_label": trend_label,
        "source": SOURCE,
        "source_quality": SOURCE_QUALITY,
        "dashboard_equivalent": False,
        "usable_for_digest": True,
        "usable_for_trend": True,
        "usable_for_bankroll": False,
        "has_data": latest is not None,
        "no_previous_snapshot": latest is not None and previous is None,
    }
    payload["message"] = render_human_digest(payload)
    payload["telegram_preview"] = render_telegram_digest(payload)
    return payload


def render_human_digest(digest: dict[str, Any]) -> str:
    latest = digest.get("latest")
    previous = digest.get("previous")
    deltas = digest.get("deltas") or {}
    lines = ["DAILY BOT DIGEST"]
    lines.append("")
    if not latest:
        lines.extend(
            [
                "No leaderboard P&L snapshot data.",
                f"snapshot_count={digest.get('snapshot_count', 0)}",
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
            "Trend vs previous snapshot:",
        ]
    )
    if previous is None:
        lines.append("No previous snapshot yet")
    else:
        lines.append(f"previous_captured_at_utc: {previous.get('captured_at_utc', 'unknown')}")
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
                "No leaderboard P&L snapshot data.",
                "trend_label=unknown",
                f"source={SOURCE} | source_quality={SOURCE_QUALITY}",
                "dashboard_equivalent=false",
                "usable_for_digest=true | usable_for_trend=true | usable_for_bankroll=false",
                "Decision: No BANKROLL increase. Observability only. No BUY/SELL/SKIP. No Fase C.",
            ]
        )
    deltas = digest.get("deltas") or {}
    trend_intro = "No previous snapshot yet"
    previous = digest.get("previous")
    if previous:
        trend_intro = f"previous_captured_at_utc: {previous.get('captured_at_utc', 'unknown')}"
    return "\n".join(
        [
            "DAILY BOT DIGEST",
            f"captured_at_utc: {latest.get('captured_at_utc', 'unknown')}",
            "",
            "P&L leaderboard",
            f"DAY {money(latest.get('pnl_day'))} | WEEK {money(latest.get('pnl_week'))}",
            f"MONTH {money(latest.get('pnl_month'))} | ALL {money(latest.get('pnl_all'))}",
            "",
            "Leaderboard trading volume",
            f"DAY {plain_value(latest.get('vol_day'))} | WEEK {plain_value(latest.get('vol_week'))}",
            f"MONTH {plain_value(latest.get('vol_month'))} | ALL {plain_value(latest.get('vol_all'))}",
            "",
            "Trend vs previous snapshot",
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
    if args.telegram_preview:
        print(digest["telegram_preview"])
        return 0
    print(digest["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
