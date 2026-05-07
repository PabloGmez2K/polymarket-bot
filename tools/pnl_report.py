from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
SNAPSHOT_SCHEMA_VERSION = 1
CASH_FLOW_SCHEMA_VERSION = 2
HORIZON_ORDER = ("1D", "1W", "1M", "ALL")
HORIZON_HOURS = {"1D": 24, "1W": 24 * 7, "1M": 24 * 30}
DIVERGENCE_THRESHOLDS = {"1D": 0.50, "1W": 1.50, "1M": 3.00, "ALL": None}
MIN_SNAPSHOTS = {"1D": 2, "1W": 7, "1M": 28, "ALL": 2}
MIN_COVERAGE_DAYS = {"1D": 1.0, "1W": 5.0, "1M": 28.0, "ALL": None}
FULL_COVERAGE_DAYS = {"1D": 1.0, "1W": 7.0, "1M": 28.0, "ALL": None}


class InputError(Exception):
    pass


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} missing or not a string")
    text = value.strip()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InputError(f"{field} invalid datetime: {value}") from exc
    if parsed.tzinfo is None:
        raise InputError(f"{field} must be timezone-aware UTC")
    return parsed.astimezone(timezone.utc)


def money(value: Decimal | float | int | str | None) -> float | None:
    if value is None:
        return None
    quantized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(quantized)


def read_jsonl(path: Path, label: str) -> tuple[bool, list[dict[str, Any]]]:
    if not path.exists():
        return False, []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise InputError(f"{label}:{line_no}: invalid JSONL: {exc.msg}") from exc
            if not isinstance(item, dict):
                raise InputError(f"{label}:{line_no}: JSONL row must be an object")
            rows.append(item)
    return True, rows


def load_snapshots(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    exists, rows = read_jsonl(path, "wallet_portfolio_snapshots.jsonl")
    snapshots: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        missing = [field for field in ("schema_version", "snapshot_at", "api_ok", "total_value") if field not in row]
        if missing:
            raise InputError(f"wallet_portfolio_snapshots.jsonl:{idx}: missing required field(s): {', '.join(missing)}")
        if row.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
            raise InputError(f"wallet_portfolio_snapshots.jsonl:{idx}: unsupported schema_version")
        if row.get("api_ok") is not True:
            continue
        try:
            total_value = Decimal(str(row["total_value"]))
        except Exception as exc:
            raise InputError(f"wallet_portfolio_snapshots.jsonl:{idx}: total_value invalid") from exc
        snapshot_at = parse_utc(row["snapshot_at"], f"wallet_portfolio_snapshots.jsonl:{idx}:snapshot_at")
        snapshots.append(
            {
                "snapshot_at": snapshot_at,
                "total_value": total_value,
                "id": str(row.get("snapshot_id") or row.get("id") or iso_utc(snapshot_at)),
                "possible_deposit": row.get("possible_deposit") is True,
            }
        )
    snapshots.sort(key=lambda item: item["snapshot_at"])
    return exists, snapshots


def validate_cash_flow(row: dict[str, Any], idx: int) -> dict[str, Any]:
    missing = [
        field
        for field in ("schema_version", "entry_id", "actor", "type", "recorded_at", "period_start", "period_end")
        if field not in row
    ]
    if missing:
        raise InputError(f"wallet_cash_flows.jsonl:{idx}: missing required field(s): {', '.join(missing)}")
    if row.get("schema_version") != CASH_FLOW_SCHEMA_VERSION:
        raise InputError(f"wallet_cash_flows.jsonl:{idx}: unsupported schema_version")
    if row.get("actor") != "pablo_manual":
        raise InputError(f"wallet_cash_flows.jsonl:{idx}: actor must be pablo_manual")
    flow_type = row.get("type")
    if flow_type not in {"no_cash_flow_attestation", "deposit", "withdrawal", "adjustment"}:
        raise InputError(f"wallet_cash_flows.jsonl:{idx}: unsupported type")
    period_start = parse_utc(row["period_start"], f"wallet_cash_flows.jsonl:{idx}:period_start")
    period_end = parse_utc(row["period_end"], f"wallet_cash_flows.jsonl:{idx}:period_end")
    recorded_at = parse_utc(row["recorded_at"], f"wallet_cash_flows.jsonl:{idx}:recorded_at")
    if period_start > period_end:
        raise InputError(f"wallet_cash_flows.jsonl:{idx}: period_start after period_end")
    amount = Decimal("0")
    if flow_type in {"deposit", "withdrawal", "adjustment"}:
        if "amount_usdc" not in row:
            raise InputError(f"wallet_cash_flows.jsonl:{idx}: amount_usdc required for {flow_type}")
        try:
            amount = Decimal(str(row["amount_usdc"]))
        except Exception as exc:
            raise InputError(f"wallet_cash_flows.jsonl:{idx}: amount_usdc invalid") from exc
        if amount < 0:
            raise InputError(f"wallet_cash_flows.jsonl:{idx}: amount_usdc must be non-negative")
    adjustment = row.get("adjustment") if isinstance(row.get("adjustment"), dict) else {}
    return {
        "entry_id": str(row["entry_id"]),
        "type": flow_type,
        "recorded_at": recorded_at,
        "period_start": period_start,
        "period_end": period_end,
        "amount_usdc": amount,
        "review_required": row.get("review_required") is True or adjustment.get("review_required") is True,
    }


def load_cash_flows(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    exists, rows = read_jsonl(path, "wallet_cash_flows.jsonl")
    flows = [validate_cash_flow(row, idx) for idx, row in enumerate(rows, start=1)]
    flows.sort(key=lambda item: (item["period_start"], item["entry_id"]))
    return exists, flows


def load_trade_lifecycle(path: Path) -> dict[str, Any]:
    base = {
        "path": str(path),
        "status": "missing",
        "contamination_rate": None,
        "realized_pnl_usdc": None,
        "n_closed_trades": 0,
        "disclaimer": "non_canonical_telemetry - no usar para BANKROLL, Telegram real, o decisiones operativas.",
    }
    if not path.exists():
        return base
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise InputError(f"trade_lifecycle.json: invalid JSON: {exc.msg}") from exc
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("records")
        if not isinstance(records, list):
            records = payload.get("trades", [])
    else:
        records = []
    if not isinstance(records, list):
        raise InputError("trade_lifecycle.json: expected list or object with trades list")
    closed = 0
    contaminated = 0
    pnl = Decimal("0")
    for row in records:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or row.get("state") or "").lower()
        close_context = row.get("close_context") if isinstance(row.get("close_context"), dict) else {}
        is_closed = status == "closed" or bool(row.get("closed_at")) or bool(close_context)
        if not is_closed:
            continue
        closed += 1
        if row.get("contaminated") is True or row.get("reconciliation_needed") is True or row.get("source_quality") == "contaminated":
            contaminated += 1
        raw_pnl = row.get("pnl_cash", close_context.get("pnl_cash"))
        if raw_pnl is not None:
            try:
                pnl += Decimal(str(raw_pnl))
            except Exception:
                contaminated += 1
    if closed:
        contaminated = closed
        base["status"] = "contaminated"
        base["contamination_rate"] = money(Decimal(contaminated) / Decimal(closed))
        base["realized_pnl_usdc"] = money(pnl)
        base["n_closed_trades"] = closed
    else:
        base["status"] = "partial"
    return base


def intervals_overlap(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> bool:
    return start <= window_end and end >= window_start


def merged_coverage_days(flows: list[dict[str, Any]], start: datetime, end: datetime) -> tuple[float, bool]:
    intervals = []
    for flow in flows:
        if flow["type"] != "no_cash_flow_attestation":
            continue
        if intervals_overlap(flow["period_start"], flow["period_end"], start, end):
            interval_start = max(flow["period_start"], start)
            interval_end = min(flow["period_end"], end)
            if interval_start < interval_end:
                intervals.append((interval_start, interval_end))
    if not intervals:
        return 0.0, False
    intervals.sort(key=lambda item: item[0])
    merged: list[list[datetime]] = []
    for interval_start, interval_end in intervals:
        if not merged or interval_start > merged[-1][1]:
            merged.append([interval_start, interval_end])
        elif interval_end > merged[-1][1]:
            merged[-1][1] = interval_end
    seconds = sum((item[1] - item[0]).total_seconds() for item in merged)
    contiguous = len(merged) == 1 and merged[0][0] <= start and merged[0][1] >= end
    return round(seconds / 86400, 3), contiguous


def cash_flow_adjustment(flows: list[dict[str, Any]], start: datetime, end: datetime) -> Decimal:
    adjustment = Decimal("0")
    for flow in flows:
        if not (start <= flow["period_start"] <= end):
            continue
        if flow["type"] == "deposit":
            adjustment += flow["amount_usdc"]
        elif flow["type"] == "withdrawal":
            adjustment -= flow["amount_usdc"]
    return adjustment


def has_unreconciled_deposit(snapshots: list[dict[str, Any]], flows: list[dict[str, Any]], start: datetime, end: datetime) -> bool:
    explaining = [
        (flow["period_start"], flow["period_end"])
        for flow in flows
        if flow["type"] in {"deposit", "withdrawal", "adjustment"} and intervals_overlap(flow["period_start"], flow["period_end"], start, end)
    ]
    for snapshot in snapshots:
        at = snapshot["snapshot_at"]
        if snapshot["possible_deposit"] and start <= at <= end and not any(item[0] <= at <= item[1] for item in explaining):
            return True
    return False


def has_pending_adjustment(flows: list[dict[str, Any]], start: datetime, end: datetime) -> bool:
    return any(
        flow["type"] == "adjustment"
        and flow["review_required"]
        and intervals_overlap(flow["period_start"], flow["period_end"], start, end)
        for flow in flows
    )


def lifecycle_pnl_for_window(trade_lifecycle: dict[str, Any], horizon: str) -> float | None:
    if horizon == "ALL":
        return trade_lifecycle.get("realized_pnl_usdc")
    return trade_lifecycle.get("realized_pnl_usdc")


def empty_horizon(horizon: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "value_usdc": None,
        "source": "none",
        "quality": "missing",
        "confidence": "untrusted",
        "coverage_gap": True,
        "window": {"start": None, "end": None, "hours": None},
        "n_snapshots": 0,
        "snapshots_used": [],
        "cash_flow_adjustment_usdc": None,
        "lifecycle_cross_check_usdc": None,
        "divergence_threshold_usdc": DIVERGENCE_THRESHOLDS[horizon],
        "divergence_actual_usdc": None,
        "reason": "not evaluated",
        "promotion_blocked_by": [],
    }


def mark_blocked_for_missing_cash_flow(horizon: str) -> dict[str, Any]:
    item = empty_horizon(horizon)
    item.update(
        {
            "status": "blocked",
            "source": "none",
            "quality": "missing",
            "confidence": "untrusted",
            "reason": "cash_flow_log missing - no es posible ajustar delta P&L por cash flows",
            "promotion_blocked_by": ["cash_flows.status=missing"],
        }
    )
    return item


def horizon_window(horizon: str, snapshots: list[dict[str, Any]], flows: list[dict[str, Any]]) -> tuple[datetime | None, datetime | None]:
    if not snapshots:
        return None, None
    end = snapshots[-1]["snapshot_at"]
    if horizon == "ALL":
        candidates = [flow["period_start"] for flow in flows if flow["type"] in {"no_cash_flow_attestation", "deposit", "withdrawal"}]
        return (min(candidates), end) if candidates else (None, end)
    return end - timedelta(hours=HORIZON_HOURS[horizon]), end


def excessive_snapshot_gap(horizon: str, selected: list[dict[str, Any]]) -> bool:
    if horizon != "1D" or len(selected) < 2:
        return False
    max_gap = max(
        (selected[idx]["snapshot_at"] - selected[idx - 1]["snapshot_at"]).total_seconds() / 3600
        for idx in range(1, len(selected))
    )
    return max_gap > 2


def build_horizon(
    horizon: str,
    snapshots: list[dict[str, Any]],
    cash_flows: list[dict[str, Any]],
    cash_flow_exists: bool,
    trade_lifecycle: dict[str, Any],
) -> dict[str, Any]:
    if not cash_flow_exists:
        return mark_blocked_for_missing_cash_flow(horizon)

    item = empty_horizon(horizon)
    start, end = horizon_window(horizon, snapshots, cash_flows)
    if horizon == "ALL" and start is None:
        item["reason"] = "t0 not defined - no valid cash_flow_log entry with type=no_cash_flow_attestation or type=deposit found"
        item["promotion_blocked_by"] = ["t0_all_missing"]
        return item
    if start is None or end is None:
        item["reason"] = "no wallet snapshots found for this horizon"
        item["promotion_blocked_by"] = ["wallet_snapshots.missing"]
        return item

    selected = [snapshot for snapshot in snapshots if start <= snapshot["snapshot_at"] <= end]
    item["window"] = {"start": iso_utc(start), "end": iso_utc(end), "hours": money((end - start).total_seconds() / 3600)}
    item["n_snapshots"] = len(selected)
    item["snapshots_used"] = [snapshot["id"] for snapshot in selected[:1] + selected[-1:] if selected]
    item["source"] = "wallet_snapshot+cash_flow_log"
    item["lifecycle_cross_check_usdc"] = lifecycle_pnl_for_window(trade_lifecycle, horizon)

    if not selected:
        item["reason"] = "no wallet snapshots found for this horizon"
        item["promotion_blocked_by"] = ["wallet_snapshots.missing"]
        return item
    if len(selected) == 1:
        item.update({"status": "blocked", "quality": "accumulating", "reason": "single snapshot - delta requires at least 2 snapshots"})
        item["promotion_blocked_by"] = ["wallet_snapshots.single_snapshot"]
        return item

    coverage_days, contiguous = merged_coverage_days(cash_flows, start, end)
    required_min = MIN_COVERAGE_DAYS[horizon]
    full_required = FULL_COVERAGE_DAYS[horizon]
    item["coverage_gap"] = not contiguous

    blockers: list[str] = []
    if horizon == "1D" and excessive_snapshot_gap(horizon, selected):
        blockers.append("snapshot_gap_gt_2h")
        item["coverage_gap"] = True
    if has_unreconciled_deposit(selected, cash_flows, start, end):
        blockers.append("possible_deposit_unreconciled")
    if has_pending_adjustment(cash_flows, start, end):
        blockers.append("adjustment_review_pending")

    if required_min is not None and coverage_days < required_min:
        item.update(
            {
                "status": "blocked",
                "quality": "attested_partial" if coverage_days > 0 else "missing",
                "confidence": "low" if coverage_days > 0 else "untrusted",
                "reason": f"attested_partial coverage ({coverage_days:g}d) below minimum required for {horizon} ({required_min:g}d)",
                "promotion_blocked_by": blockers + [f"cash_flow_coverage_below_{horizon}"],
            }
        )
        return item
    if blockers:
        item.update(
            {
                "status": "blocked",
                "quality": "unreconciled" if any("deposit" in blocker or "adjustment" in blocker for blocker in blockers) else "attested_partial",
                "confidence": "untrusted",
                "reason": "coverage or reconciliation blocker present: " + ", ".join(blockers),
                "promotion_blocked_by": blockers,
            }
        )
        return item

    first = selected[0]
    latest = selected[-1]
    adjustment = cash_flow_adjustment(cash_flows, first["snapshot_at"], latest["snapshot_at"])
    value = (latest["total_value"] - first["total_value"]) - adjustment
    item["cash_flow_adjustment_usdc"] = money(adjustment)
    item["value_usdc"] = money(value)

    lifecycle_value = item["lifecycle_cross_check_usdc"]
    if lifecycle_value is not None:
        item["divergence_actual_usdc"] = money(abs(Decimal(str(item["value_usdc"])) - Decimal(str(lifecycle_value))))
    threshold = item["divergence_threshold_usdc"]
    divergence_blocks_candidate = threshold is not None and item["divergence_actual_usdc"] is not None and item["divergence_actual_usdc"] > threshold

    enough_snapshots = len(selected) >= MIN_SNAPSHOTS[horizon]
    full_coverage = full_required is not None and coverage_days >= full_required and contiguous
    if enough_snapshots and full_coverage and not divergence_blocks_candidate:
        item.update(
            {
                "status": "canonical_candidate",
                "quality": "attested_full_7d",
                "confidence": "medium",
                "coverage_gap": False,
                "reason": "attested coverage complete for B3; canonical promotion remains blocked pending B5/B6",
                "promotion_blocked_by": ["canonical_requires_B5_B6_opus_review_pablo_signoff"],
            }
        )
    else:
        reason_parts = [f"calculation provisional with coverage {coverage_days:g}d"]
        if not enough_snapshots:
            reason_parts.append(f"n_snapshots {len(selected)} below target {MIN_SNAPSHOTS[horizon]}")
        if divergence_blocks_candidate:
            reason_parts.append("lifecycle divergence exceeds threshold")
        item.update(
            {
                "status": "provisional",
                "quality": "attested_partial",
                "confidence": "low",
                "reason": "; ".join(reason_parts),
                "promotion_blocked_by": ["canonical_requires_B5_B6_opus_review_pablo_signoff"],
            }
        )
    return item


def build_report(data_dir: Path, generated_at: datetime | None = None) -> dict[str, Any]:
    snapshots_path = data_dir / "wallet_portfolio_snapshots.jsonl"
    cash_flows_path = data_dir / "wallet_cash_flows.jsonl"
    lifecycle_path = data_dir / "trade_lifecycle.json"
    snapshot_exists, snapshots = load_snapshots(snapshots_path)
    cash_flow_exists, cash_flows = load_cash_flows(cash_flows_path)
    trade_lifecycle = load_trade_lifecycle(lifecycle_path)
    generated_at_text = iso_utc(generated_at or datetime.now(timezone.utc))
    coverage_days = 0
    if snapshots and cash_flows:
        start = snapshots[-1]["snapshot_at"] - timedelta(days=7)
        coverage_days, _ = merged_coverage_days(cash_flows, start, snapshots[-1]["snapshot_at"])

    horizons = {
        horizon: build_horizon(horizon, snapshots, cash_flows, cash_flow_exists, trade_lifecycle)
        for horizon in HORIZON_ORDER
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at_text,
        "canonical_source": "none",
        "bankroll_readiness": "blocked",
        "inputs": {
            "snapshots": {
                "path": str(snapshots_path),
                "status": "present" if snapshot_exists else "missing",
                "n_records": len(snapshots),
            },
            "cash_flows": {
                "path": str(cash_flows_path),
                "status": "present" if cash_flow_exists else "missing",
                "n_records": len(cash_flows),
                "coverage_days": coverage_days,
            },
            "trade_lifecycle": {
                "path": str(lifecycle_path),
                "status": trade_lifecycle["status"],
                "contamination_rate": trade_lifecycle["contamination_rate"],
            },
        },
        "horizons": horizons,
        "non_canonical_telemetry": {"trade_lifecycle": trade_lifecycle},
        "guardrails": {
            "max_confidence_b3": "medium",
            "canonical_requires": "B5_B6_opus_review_pablo_signoff",
            "tool_scope": "read_only_log_only",
            "no_operational_use": True,
            "would_send": False,
            "operational_use": "forbidden",
            "promotes_canonical_source": False,
        },
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    if not path.parent.exists():
        raise InputError(f"write report directory does not exist: {path.parent}")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only B3 wallet P&L report generator.")
    parser.add_argument("--data-dir", default="data", help="Directory containing wallet JSONL inputs.")
    parser.add_argument("--json", action="store_true", help="Emit JSON payload to stdout.")
    parser.add_argument("--write-report", help="Optional report output path outside data/. Parent directory must already exist.")
    parser.add_argument("--generated-at", help="Testing hook: fixed ISO-8601 UTC generated_at timestamp.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        generated_at = parse_utc(args.generated_at, "--generated-at") if args.generated_at else None
        payload = build_report(Path(args.data_dir), generated_at=generated_at)
        if args.write_report:
            report_path = Path(args.write_report)
            if "data" in report_path.parts:
                raise InputError("--write-report must not write inside data/")
            write_report(report_path, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except InputError as exc:
        print(f"pnl_report input error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"pnl_report unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
