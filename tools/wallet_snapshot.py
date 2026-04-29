#!/usr/bin/env python3
"""Read-only Polymarket wallet/portfolio snapshot utility."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timezone, timedelta
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DATA_API_URL = os.getenv("DATA_API_URL", "https://data-api.polymarket.com").rstrip("/")
CLOB_HOST = os.getenv("CLOB_HOST", "https://clob.polymarket.com")
REQUIRED_HISTORY_HOURS = 168


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a read-only Polymarket wallet/portfolio value snapshot."
    )
    parser.add_argument("--data-dir", default="data", help="Runtime data directory.")
    parser.add_argument(
        "--snapshot-file",
        default=None,
        help="JSONL snapshot file. Defaults to data/wallet_portfolio_snapshots.jsonl.",
    )
    parser.add_argument(
        "--cash-flows-file",
        default=None,
        help="Optional JSONL manual cash-flow file. Defaults to data/wallet_cash_flows.jsonl.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write a new snapshot.")
    parser.add_argument("--json", action="store_true", help="Emit stable JSON output.")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown output.")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Do not call APIs or write; only read existing snapshot history.",
    )
    parser.add_argument(
        "--deposit-threshold",
        type=float,
        default=8.0,
        help="Flag possible manual reloads above this value between snapshots.",
    )
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_day(value: Any) -> date | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).strip().replace("$", ""))
    except (TypeError, ValueError):
        return None


def money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}"


def compact_error(message: str) -> str:
    text = " ".join(str(message).split())
    return text[:240]


def default_snapshot(data_dir: Path) -> Path:
    return data_dir / "wallet_portfolio_snapshots.jsonl"


def default_flows(data_dir: Path) -> Path:
    return data_dir / "wallet_cash_flows.jsonl"


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            for idx, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        rows.append(item)
                    else:
                        warnings.append(f"{path.name}:{idx}: ignored non-object JSONL row")
                except json.JSONDecodeError:
                    warnings.append(f"{path.name}:{idx}: ignored invalid JSON")
    except Exception as exc:
        warnings.append(f"{path.name}: read_error: {compact_error(str(exc))}")
    return rows, warnings


def valid_snapshot(row: dict[str, Any]) -> bool:
    return bool(
        row.get("schema_version") == SCHEMA_VERSION
        and row.get("api_ok") is True
        and as_float(row.get("total_value")) is not None
        and parse_dt(row.get("snapshot_at")) is not None
    )


def sorted_valid_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted([row for row in rows if valid_snapshot(row)], key=lambda row: parse_dt(row["snapshot_at"]) or datetime.min.replace(tzinfo=timezone.utc))


def load_cash_flows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows, warnings = read_jsonl(path)
    flows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        flow_date = parse_day(row.get("date"))
        amount = as_float(row.get("amount"))
        flow_type = str(row.get("type") or "").strip().lower()
        if flow_date is None or amount is None or amount < 0 or flow_type not in {"deposit", "withdrawal"}:
            warnings.append(f"{path.name}:{idx}: ignored invalid cash-flow row")
            continue
        flows.append({"date": flow_date.isoformat(), "amount": round(amount, 2), "type": flow_type})
    return flows, warnings


def flows_between(flows: list[dict[str, Any]], start: datetime, end: datetime) -> list[dict[str, Any]]:
    selected = []
    for flow in flows:
        flow_day = parse_day(flow.get("date"))
        if flow_day is None:
            continue
        flow_at = day_start(flow_day)
        if start <= flow_at <= end:
            selected.append(flow)
    return selected


def flow_totals(flows: list[dict[str, Any]]) -> tuple[float, float]:
    deposits = sum(float(flow["amount"]) for flow in flows if flow.get("type") == "deposit")
    withdrawals = sum(float(flow["amount"]) for flow in flows if flow.get("type") == "withdrawal")
    return round(deposits, 2), round(withdrawals, 2)


def cash_flow_explains(flows: list[dict[str, Any]], start: datetime, end: datetime, delta: float) -> bool:
    deposits, withdrawals = flow_totals(flows_between(flows, start, end))
    return (deposits - withdrawals) >= max(0.0, delta - 0.01)


def fetch_positions(funder: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "user": funder.lower(),
            "sizeThreshold": "0",
            "limit": "500",
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        }
    )
    req = urllib.request.Request(f"{DATA_API_URL}/positions?{params}")
    req.add_header("User-Agent", "polymarket-wallet-snapshot/1.0")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    if not isinstance(data, list):
        raise ValueError("positions response is not a list")
    return [item for item in data if isinstance(item, dict)]


def fetch_cash_available(funder: str) -> float:
    key = os.getenv("PK")
    if not key:
        raise RuntimeError("missing PK for CLOB balance read")
    try:
        from py_clob_client_v2.client import ClobClient
        from py_clob_client_v2.clob_types import AssetType, BalanceAllowanceParams
    except Exception as exc:
        raise RuntimeError(f"missing CLOB client dependency: {compact_error(str(exc))}") from exc

    client = ClobClient(CLOB_HOST, key=key, chain_id=137, signature_type=1, funder=funder)
    client.set_api_creds(client.create_or_derive_api_key())
    result = client.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
    raw = result.get("balance", 0) if isinstance(result, dict) else result
    return float(raw) / 1e6


def classify_positions(positions: list[dict[str, Any]]) -> tuple[float, float, int]:
    active_value = 0.0
    resolved_value = 0.0
    open_count = 0
    for pos in positions:
        current_value = as_float(pos.get("currentValue")) or 0.0
        current_price = as_float(pos.get("curPrice")) or 0.0
        if current_value <= 0.0:
            continue
        if current_price >= 0.98 or bool(pos.get("redeemable")):
            resolved_value += current_value
        elif current_value >= 0.10:
            active_value += current_value
            open_count += 1
    return round(active_value, 2), round(resolved_value, 2), open_count


def empty_snapshot(now: datetime, error: str, partial: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_at": now.isoformat(),
        "cash_available": None,
        "active_positions_value": None,
        "resolved_pending_value": None,
        "total_value": None,
        "positions_count_open": None,
        "source": "polymarket_api",
        "api_ok": False,
        "error": compact_error(error),
        "possible_deposit": False,
    }
    if partial:
        snapshot.update(partial)
    return snapshot


def take_snapshot(now: datetime, previous_valid: dict[str, Any] | None, flows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    funder = os.getenv("FUNDER", "").strip()
    if not funder:
        return empty_snapshot(now, "missing FUNDER")

    positions: list[dict[str, Any]] = []
    cash: float | None = None
    errors: list[str] = []
    try:
        positions = fetch_positions(funder)
    except Exception as exc:
        errors.append(f"positions: {compact_error(str(exc))}")
    try:
        cash = fetch_cash_available(funder)
    except Exception as exc:
        errors.append(f"cash: {compact_error(str(exc))}")

    if errors:
        partial: dict[str, Any] = {}
        if positions:
            active_value, resolved_value, open_count = classify_positions(positions)
            partial.update(
                {
                    "active_positions_value": active_value,
                    "resolved_pending_value": resolved_value,
                    "positions_count_open": open_count,
                }
            )
        if cash is not None:
            partial["cash_available"] = round(cash, 2)
        return empty_snapshot(now, "; ".join(errors), partial)

    active_value, resolved_value, open_count = classify_positions(positions)
    total_value = round((cash or 0.0) + active_value + resolved_value, 2)
    possible_deposit = False
    if previous_valid:
        previous_at = parse_dt(previous_valid.get("snapshot_at"))
        previous_total = as_float(previous_valid.get("total_value"))
        if previous_at is not None and previous_total is not None:
            delta = total_value - previous_total
            possible_deposit = delta > threshold and not cash_flow_explains(flows, previous_at, now, delta)

    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_at": now.isoformat(),
        "cash_available": round(cash or 0.0, 2),
        "active_positions_value": active_value,
        "resolved_pending_value": resolved_value,
        "total_value": total_value,
        "positions_count_open": open_count,
        "source": "polymarket_api",
        "api_ok": True,
        "error": None,
        "possible_deposit": bool(possible_deposit),
    }


def append_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snapshot, sort_keys=True, ensure_ascii=False) + "\n")


def build_report(snapshot: dict[str, Any] | None, history_rows: list[dict[str, Any]], flows: list[dict[str, Any]], warnings: list[str], now: datetime) -> dict[str, Any]:
    valid = sorted_valid_snapshots(history_rows)
    latest = valid[-1] if valid else None
    latest_at = parse_dt(latest.get("snapshot_at")) if latest else None
    oldest_at = parse_dt(valid[0].get("snapshot_at")) if valid else None
    span_hours = 0.0
    if oldest_at is not None and latest_at is not None:
        span_hours = max(0.0, (latest_at - oldest_at).total_seconds() / 3600)
    valid_days = len({(parse_dt(row.get("snapshot_at")) or now).date().isoformat() for row in valid})

    baseline = None
    if latest_at is not None:
        cutoff = latest_at - timedelta(hours=REQUIRED_HISTORY_HOURS)
        candidates = [row for row in valid if (parse_dt(row.get("snapshot_at")) or latest_at) <= cutoff]
        if candidates:
            baseline = candidates[-1]
    baseline_at = parse_dt(baseline.get("snapshot_at")) if baseline else None

    possible_recent = 0
    if latest_at is not None:
        recent_cutoff = latest_at - timedelta(hours=REQUIRED_HISTORY_HOURS)
        possible_recent = sum(
            1
            for row in valid
            if row.get("possible_deposit") is True
            and (parse_dt(row.get("snapshot_at")) or latest_at) >= recent_cutoff
        )

    window_flows: list[dict[str, Any]] = []
    wallet_pnl_available = False
    wallet_pnl_7d = None
    wallet_pnl_method = "insufficient_history"
    confidence = "unavailable"
    if latest is None:
        wallet_pnl_method = "api_unavailable"
    elif baseline is not None and baseline_at is not None and latest_at is not None:
        window_flows = flows_between(flows, baseline_at, latest_at)
        deposits, withdrawals = flow_totals(window_flows)
        baseline_total = as_float(baseline.get("total_value"))
        latest_total = as_float(latest.get("total_value"))
        if baseline_total is not None and latest_total is not None:
            wallet_pnl_available = True
            wallet_pnl_7d = round((latest_total - baseline_total) - deposits + withdrawals, 2)
            if possible_recent:
                wallet_pnl_method = "cash_flow_unknown"
                confidence = "low"
            else:
                wallet_pnl_method = "snapshot_delta"
                confidence = "medium" if window_flows else "high"

    deposits_7d, withdrawals_7d = flow_totals(window_flows)
    cash_flows_total = round(deposits_7d - withdrawals_7d, 2)

    if latest is None:
        ready = False
        reason = "api_unavailable"
    elif baseline is None:
        ready = False
        reason = "need_more_history" if span_hours < REQUIRED_HISTORY_HOURS else "need_7d_baseline"
    elif not wallet_pnl_available:
        ready = False
        reason = "need_7d_baseline"
    elif possible_recent:
        ready = False
        reason = "cash_flow_unknown"
    else:
        ready = True
        reason = "valid_7d_baseline_available"

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(),
        "snapshot": snapshot,
        "history": {
            "valid_snapshots": len(valid),
            "valid_snapshot_days": valid_days,
            "history_span_hours": round(span_hours, 2),
            "required_history_hours": REQUIRED_HISTORY_HOURS,
            "baseline_snapshot_at": baseline_at.isoformat() if baseline_at else None,
            "latest_snapshot_at": latest_at.isoformat() if latest_at else None,
        },
        "wallet_pnl": {
            "wallet_pnl_available": wallet_pnl_available,
            "wallet_pnl_7d": wallet_pnl_7d,
            "wallet_pnl_method": wallet_pnl_method,
            "wallet_pnl_confidence": confidence,
            "cash_flows_7d_total": cash_flows_total,
            "cash_flows_7d_count": len(window_flows),
            "possible_deposits_7d_count": possible_recent,
        },
        "phase2_readiness": {
            "phase2_ready": ready,
            "phase2_ready_reason": reason,
            "valid_snapshot_days": valid_days,
            "required_snapshot_days": 7,
            "required_history_hours": REQUIRED_HISTORY_HOURS,
            "wallet_pnl_available": wallet_pnl_available,
        },
        "warnings": warnings,
    }


def render_text(report: dict[str, Any], markdown: bool = False) -> str:
    snapshot = report.get("snapshot") or {}
    history = report["history"]
    pnl = report["wallet_pnl"]
    readiness = report["phase2_readiness"]
    snapshot_at = parse_dt(snapshot.get("snapshot_at")) or parse_dt(history.get("latest_snapshot_at")) or parse_dt(report.get("generated_at")) or utc_now()
    status = "ACTIVO" if pnl["wallet_pnl_available"] else "ACUMULANDO"
    total = as_float(snapshot.get("total_value"))
    cash = as_float(snapshot.get("cash_available"))
    active = as_float(snapshot.get("active_positions_value"))
    resolved = as_float(snapshot.get("resolved_pending_value"))
    missing_hours = max(0.0, REQUIRED_HISTORY_HOURS - float(history.get("history_span_hours") or 0.0))
    ready_text = "READY" if readiness["phase2_ready"] else "NOT READY"
    ready_reason = (
        "wallet delta 7d disponible"
        if readiness["phase2_ready"]
        else f"faltan {missing_hours:.0f}h de baseline"
        if readiness["phase2_ready_reason"] in {"need_more_history", "need_7d_baseline"}
        else readiness["phase2_ready_reason"]
    )
    deposit_count = pnl["possible_deposits_7d_count"]

    if markdown:
        lines = [
            "# Wallet Snapshot",
            "",
            f"- Estado: **{status}**",
            f"- Fecha: {snapshot_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## Valor actual",
            f"- Valor total: **{money(total)}**",
            f"- Cash: {money(cash)}",
            f"- Posiciones activas: {money(active)}",
            f"- Resolved pending: {money(resolved)}",
            "",
            "## P/L 7d snapshot",
            f"- Disponible: {pnl['wallet_pnl_available']}",
            f"- Metodo: {pnl['wallet_pnl_method']}",
            f"- P/L: {money(pnl['wallet_pnl_7d']) if pnl['wallet_pnl_available'] else 'insuficiente historia'}",
            f"- Confianza: {pnl['wallet_pnl_confidence']}",
            "",
            "## Cash flows",
            f"- Anotados 7d: {pnl['cash_flows_7d_count']}",
            f"- Total neto 7d: {money(pnl['cash_flows_7d_total'])}",
            f"- Posibles depositos detectados: {deposit_count}",
            "",
            "## Phase 2 readiness",
            f"- Estado: **{ready_text}**",
            f"- Razon: {readiness['phase2_ready_reason']}",
            "",
            "## Warnings",
        ]
        warnings = list(report.get("warnings") or [])
        if snapshot.get("possible_deposit"):
            warnings.append("POSIBLE DEPOSITO detectado: anotar en wallet_cash_flows.jsonl si fue recarga manual.")
        lines.extend([f"- {item}" for item in warnings] if warnings else ["- sin warnings"])
        return "\n".join(lines)

    lines = [
        f"Wallet Snapshot - {snapshot_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Estado         : {status}",
        f"Valor total    : {money(total)}  (cash {money(cash)} | activas {money(active)} | resolved {money(resolved)})",
    ]
    if pnl["wallet_pnl_available"]:
        lines.extend(
            [
                f"P/L 7d snapshot: {money(pnl['wallet_pnl_7d'])}",
                f"Cash flows 7d  : {pnl['cash_flows_7d_count']} anotados | {money(pnl['cash_flows_7d_total'])}",
                f"Posibles depositos detectados: {deposit_count}",
                f"Phase 2 readiness: {ready_text} - {ready_reason}",
            ]
        )
    else:
        lines.extend(
            [
                f"Historia       : {history['valid_snapshots']} snapshots validos | {history['history_span_hours']:.0f}h / {REQUIRED_HISTORY_HOURS}h",
                "P/L 7d         : insuficiente historia",
                f"Phase 2 readiness: {ready_text} - {ready_reason}",
            ]
        )
    if snapshot.get("possible_deposit"):
        lines.append("POSIBLE DEPOSITO detectado - anotar en wallet_cash_flows.jsonl si fue recarga manual.")
    for warning in report.get("warnings") or []:
        lines.append(f"Warning        : {warning}")
    return "\n".join(lines)


def main() -> int:
    configure_stdout()
    args = parse_args()
    data_dir = Path(args.data_dir)
    snapshot_file = Path(args.snapshot_file) if args.snapshot_file else default_snapshot(data_dir)
    flows_file = Path(args.cash_flows_file) if args.cash_flows_file else default_flows(data_dir)
    now = utc_now()

    history_rows, history_warnings = read_jsonl(snapshot_file)
    flows, flow_warnings = load_cash_flows(flows_file)
    warnings = history_warnings + flow_warnings

    snapshot: dict[str, Any] | None = None
    if not args.report_only:
        previous_valid = sorted_valid_snapshots(history_rows)
        snapshot = take_snapshot(now, previous_valid[-1] if previous_valid else None, flows, args.deposit_threshold)
        history_for_report = history_rows + [snapshot]
        if not args.dry_run:
            append_snapshot(snapshot_file, snapshot)
    else:
        history_for_report = history_rows
        valid = sorted_valid_snapshots(history_rows)
        snapshot = valid[-1] if valid else empty_snapshot(now, "no valid snapshots in history")

    report = build_report(snapshot, history_for_report, flows, warnings, now)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    elif args.markdown:
        print(render_text(report, markdown=True))
    else:
        print(render_text(report, markdown=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
