#!/usr/bin/env python3
"""Append-only external Polymarket leaderboard P&L snapshot utility."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


DATA_API_URL = os.getenv("DATA_API_URL", "https://data-api.polymarket.com").rstrip("/")
DEFAULT_SNAPSHOT_PATH = Path("data") / "observability" / "leaderboard_pnl_snapshots.jsonl"
PERIODS = ("DAY", "WEEK", "MONTH", "ALL")
CONFIDENCE = {"DAY": "medium", "WEEK": "medium", "MONTH": "low", "ALL": "medium"}
METHODOLOGY_NOTES = (
    "External opaque Polymarket leaderboard.pnl snapshot for digest/trend only. "
    "Not dashboard-equivalent, not canonical P&L, and never usable for BANKROLL readiness. "
    "B4.3 interpretation: DAY and WEEK appear calendar/UTC closed-position realizedPnl-like; "
    "MONTH remains opaque; ALL matched a manual 1Y check but is not proven equivalent. "
    "vol_day/week/month/all are Polymarket leaderboard trading volume, not buy_count or trade_count."
)
VOLUME_LABEL = "leaderboard_trading_volume"
VOLUME_NOTES = "vol_day/week/month/all are leaderboard trading volume; they are not buy_count or operation count."


class SnapshotError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_local(dt: datetime) -> str:
    return dt.astimezone().replace(microsecond=0).isoformat()


def parse_utc(value: str, field: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SnapshotError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SnapshotError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def decimal_or_none(value: str | None, field: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise SnapshotError(f"{field} must be numeric") from exc


def money(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return None


def mask_wallet(wallet: str | None) -> str | None:
    if not wallet:
        return None
    text = wallet.strip()
    if len(text) <= 12:
        return "***"
    return f"{text[:6]}...{text[-4:]}"


def normalize_wallet(wallet: str | None) -> str | None:
    if not wallet:
        return None
    text = wallet.strip()
    if not text:
        return None
    if text.lower().startswith("0x") and len(text) == 42:
        return text.lower()
    return text


def read_funder_from_env_file(path: str | Path = ".env") -> str | None:
    env_path = Path(path)
    if not env_path.exists():
        return None
    try:
        lines = env_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "FUNDER":
            continue
        return value.strip().strip('"').strip("'")
    return None


def configured_wallet(args: argparse.Namespace) -> str | None:
    return normalize_wallet(
        args.wallet
        or os.getenv("FUNDER")
        or os.getenv("POLYMARKET_WALLET")
        or os.getenv("WALLET_ADDRESS")
        or os.getenv("PROXY_WALLET")
        or read_funder_from_env_file(args.env_file)
    )


def leaderboard_url(wallet: str, period: str, order_by: str = "PNL") -> str:
    params = urllib.parse.urlencode(
        {
            "user": wallet,
            "timePeriod": period,
            "orderBy": order_by,
            "limit": "1",
        }
    )
    return f"{DATA_API_URL}/v1/leaderboard?{params}"


def request_json(url: str) -> Any:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "polymarket-leaderboard-pnl-snapshot/1.0")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def rows_from_response(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("leaderboard", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        if any(key in payload for key in ("pnl", "profit", "proxyWallet", "userName", "username")):
            return [payload]
    return []


def pick_wallet_row(payload: Any, wallet: str) -> dict[str, Any] | None:
    rows = rows_from_response(payload)
    wallet_l = wallet.lower()
    for row in rows:
        candidate = str(
            row.get("proxyWallet")
            or row.get("proxy_wallet")
            or row.get("wallet")
            or row.get("address")
            or row.get("user")
            or ""
        ).lower()
        if candidate == wallet_l:
            return row
    return rows[0] if len(rows) == 1 else None


def extract_user(row: dict[str, Any] | None, fallback: str | None) -> str | None:
    if row is None:
        return fallback
    for key in ("userName", "username", "name", "user"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return fallback


def extract_metric(row: dict[str, Any] | None, names: tuple[str, ...]) -> float | None:
    if row is None:
        return None
    for name in names:
        if name in row:
            return money(row.get(name))
    return None


def query_leaderboard(wallet: str) -> tuple[dict[str, dict[str, Any]], str, str | None, str | None]:
    by_period: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    user: str | None = None
    for period in PERIODS:
        try:
            payload = request_json(leaderboard_url(wallet, period))
            row = pick_wallet_row(payload, wallet)
            by_period[period] = {
                "pnl": extract_metric(row, ("pnl", "profit", "realizedPnl", "realized_pnl")),
                "vol": extract_metric(row, ("vol", "volume", "totalVolume", "total_volume")),
            }
            user = extract_user(row, user)
            if row is None:
                errors.append(f"{period}: wallet_not_found")
        except Exception as exc:
            by_period[period] = {"pnl": None, "vol": None}
            errors.append(f"{period}: {compact_error(str(exc))}")
    if errors:
        return by_period, "failed", user, "; ".join(errors)
    return by_period, "ok", user, None


def compact_error(message: str) -> str:
    return " ".join(str(message).split())[:300]


def base_snapshot(now: datetime, wallet: str | None, user: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "captured_at_utc": iso_utc(now),
        "captured_at_local": iso_local(now),
        "wallet_masked": mask_wallet(wallet),
        "user": user,
        "source": "polymarket_leaderboard",
        "source_quality": "external_opaque",
        "dashboard_equivalent": False,
        "usable_for_digest": True,
        "usable_for_trend": True,
        "usable_for_bankroll": False,
        "pnl_day": None,
        "pnl_week": None,
        "pnl_month": None,
        "pnl_all": None,
        "vol_day": None,
        "vol_week": None,
        "vol_month": None,
        "vol_all": None,
        "volume_label": VOLUME_LABEL,
        "volume_notes": VOLUME_NOTES,
        "confidence_day": CONFIDENCE["DAY"],
        "confidence_week": CONFIDENCE["WEEK"],
        "confidence_month": CONFIDENCE["MONTH"],
        "confidence_all": CONFIDENCE["ALL"],
        "methodology_notes": METHODOLOGY_NOTES,
        "query_status": "unknown",
        "api_error": None,
    }
    return payload


def build_snapshot(args: argparse.Namespace, now: datetime | None = None) -> dict[str, Any]:
    captured = now or utc_now()
    wallet = configured_wallet(args)
    payload = base_snapshot(captured, wallet, args.user)
    if not wallet:
        payload["query_status"] = "NEEDS_MANUAL_WALLET_INPUT"
        payload["api_error"] = "wallet not found in --wallet, FUNDER, POLYMARKET_WALLET, WALLET_ADDRESS, PROXY_WALLET, or local .env FUNDER"
        add_dashboard_fields(payload, args)
        return payload

    metrics, status, user, api_error = query_leaderboard(wallet)
    payload["user"] = args.user or user
    for period in PERIODS:
        suffix = period.lower()
        payload[f"pnl_{suffix}"] = metrics[period]["pnl"]
        payload[f"vol_{suffix}"] = metrics[period]["vol"]
    payload["query_status"] = status
    payload["api_error"] = api_error
    add_dashboard_fields(payload, args)
    return payload


def add_dashboard_fields(payload: dict[str, Any], args: argparse.Namespace) -> None:
    manual = {
        "dashboard_1d": decimal_or_none(args.dashboard_1d, "--dashboard-1d"),
        "dashboard_1w": decimal_or_none(args.dashboard_1w, "--dashboard-1w"),
        "dashboard_1m": decimal_or_none(args.dashboard_1m, "--dashboard-1m"),
        "dashboard_1y": decimal_or_none(args.dashboard_1y, "--dashboard-1y"),
    }
    if all(value is None for value in manual.values()) and not args.dashboard_captured_at:
        return
    captured_at = args.dashboard_captured_at
    if captured_at:
        captured_at = iso_utc(parse_utc(captured_at, "--dashboard-captured-at"))
    payload.update({key: money(value) for key, value in manual.items()})
    payload["dashboard_capture_at"] = captured_at
    payload["delta_day"] = delta(payload.get("pnl_day"), payload.get("dashboard_1d"))
    payload["delta_week"] = delta(payload.get("pnl_week"), payload.get("dashboard_1w"))
    payload["delta_month"] = delta(payload.get("pnl_month"), payload.get("dashboard_1m"))
    payload["delta_all_vs_1y"] = delta(payload.get("pnl_all"), payload.get("dashboard_1y"))


def delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return money(Decimal(str(left)) - Decimal(str(right)))


def read_snapshots(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SnapshotError(f"{path}:{line_no}: invalid JSONL: {exc.msg}") from exc
            if isinstance(item, dict):
                rows.append(item)
    return rows


def append_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def build_summary(path: Path) -> dict[str, Any]:
    rows = read_snapshots(path)
    latest = rows[-1] if rows else None
    previous = rows[-2] if len(rows) >= 2 else None
    summary: dict[str, Any] = {
        "path": str(path),
        "snapshot_count": len(rows),
        "latest_snapshot": latest,
        "previous_snapshot_captured_at_utc": previous.get("captured_at_utc") if previous else None,
        "day_delta_vs_previous_snapshot": None,
        "week_delta_vs_previous_snapshot": None,
        "month_delta_vs_previous_snapshot": None,
        "all_delta_vs_previous_snapshot": None,
        "trend_label": "unknown",
    }
    if latest and previous:
        for name in ("day", "week", "month", "all"):
            summary[f"{name}_delta_vs_previous_snapshot"] = delta(latest.get(f"pnl_{name}"), previous.get(f"pnl_{name}"))
        summary["trend_label"] = trend_label(summary)
    return summary


def trend_label(summary: dict[str, Any]) -> str:
    values = [
        summary.get("day_delta_vs_previous_snapshot"),
        summary.get("week_delta_vs_previous_snapshot"),
        summary.get("month_delta_vs_previous_snapshot"),
        summary.get("all_delta_vs_previous_snapshot"),
    ]
    known = [Decimal(str(value)) for value in values if value is not None]
    if not known:
        return "unknown"
    total = sum(known, Decimal("0"))
    if total > Decimal("0.01"):
        return "improving"
    if total < Decimal("-0.01"):
        return "worsening"
    return "flat"


def output(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture append-only external leaderboard P&L snapshots.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Query API, print JSON, do not write.")
    mode.add_argument("--write", action="store_true", help="Query API and append one JSONL row.")
    mode.add_argument("--summary", action="store_true", help="Read existing snapshots and print latest/delta summary.")
    parser.add_argument("--snapshot-file", default=str(DEFAULT_SNAPSHOT_PATH), help="JSONL snapshot output path.")
    parser.add_argument("--wallet", help="Manual wallet/proxy wallet override. Output only shows masked wallet.")
    parser.add_argument("--env-file", default=".env", help=argparse.SUPPRESS)
    parser.add_argument("--user", help="Optional manual user label override.")
    parser.add_argument("--dashboard-1d")
    parser.add_argument("--dashboard-1w")
    parser.add_argument("--dashboard-1m")
    parser.add_argument("--dashboard-1y")
    parser.add_argument("--dashboard-captured-at")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    path = Path(args.snapshot_file)
    try:
        if args.summary:
            output(build_summary(path))
            return 0
        payload = build_snapshot(args)
        if args.write:
            append_snapshot(path, payload)
            payload = {"written": True, "path": str(path), "snapshot": payload}
        output(payload)
        return 0
    except SnapshotError as exc:
        print(f"leaderboard_pnl_snapshot error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"leaderboard_pnl_snapshot unexpected error: {compact_error(str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
