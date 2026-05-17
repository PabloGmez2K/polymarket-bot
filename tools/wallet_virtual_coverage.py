#!/usr/bin/env python3
"""LOG_ONLY virtual wallet cash-flow coverage prototype."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


SNAPSHOT_SCHEMA_VERSION = 1
CASH_FLOW_SCHEMA_VERSION = 2
WINDOW_DAYS = 7
BASE_T0_EXPIRES_DAYS = 14
MIN_SNAPSHOTS = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute read-only LOG_ONLY wallet virtual coverage."
    )
    parser.add_argument("--data-dir", default="data", help="Runtime data directory.")
    parser.add_argument(
        "--snapshot-file",
        default=None,
        help="Defaults to data/wallet_portfolio_snapshots.jsonl.",
    )
    parser.add_argument(
        "--cash-flows-file",
        default=None,
        help="Defaults to data/wallet_cash_flows.jsonl.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).strip().replace("$", ""))
    except (TypeError, ValueError):
        return None


def read_jsonl(path: Path) -> tuple[bool, list[dict[str, Any]], list[str]]:
    if not path.exists():
        return False, [], []
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            for idx, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    warnings.append(f"{path.name}:{idx}:json_decode")
                    continue
                if isinstance(item, dict):
                    rows.append(item)
                else:
                    warnings.append(f"{path.name}:{idx}:not_object")
    except OSError as exc:
        warnings.append(f"{path.name}:read_error:{str(exc)[:120]}")
    return True, rows, warnings


def default_snapshot_file(data_dir: Path) -> Path:
    return data_dir / "wallet_portfolio_snapshots.jsonl"


def default_cash_flows_file(data_dir: Path) -> Path:
    return data_dir / "wallet_cash_flows.jsonl"


def valid_snapshot(row: dict[str, Any]) -> bool:
    return (
        row.get("schema_version") == SNAPSHOT_SCHEMA_VERSION
        and row.get("api_ok") is True
        and parse_dt(row.get("snapshot_at")) is not None
        and as_float(row.get("total_value")) is not None
    )


def sorted_valid_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [row for row in rows if valid_snapshot(row)],
        key=lambda row: parse_dt(row["snapshot_at"]) or datetime.min.replace(tzinfo=timezone.utc),
    )


def validate_cash_flow(row: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    reasons: list[str] = []
    if row.get("schema_version") != CASH_FLOW_SCHEMA_VERSION:
        reasons.append("schema_version")
    entry_id = row.get("entry_id")
    if not isinstance(entry_id, str) or not entry_id.strip():
        reasons.append("entry_id")
    elif entry_id.startswith("EXAMPLE-"):
        reasons.append("example_id")
    if row.get("actor") != "pablo_manual":
        reasons.append("actor_mismatch")
    flow_type = row.get("type")
    if flow_type not in {"deposit", "withdrawal", "no_cash_flow_attestation", "adjustment"}:
        reasons.append("type")
    recorded_at = parse_dt(row.get("recorded_at"))
    period_start = parse_dt(row.get("period_start"))
    period_end = parse_dt(row.get("period_end"))
    if recorded_at is None:
        reasons.append("recorded_at")
    if period_start is None:
        reasons.append("period_start")
    if period_end is None:
        reasons.append("period_end")
    if period_start and period_end and period_start > period_end:
        reasons.append("period_order")
    amount = None
    if flow_type in {"deposit", "withdrawal", "adjustment"}:
        amount = as_float(row.get("amount_usdc"))
        if amount is None or amount < 0:
            reasons.append("amount_usdc")
    adjustment = row.get("adjustment") if isinstance(row.get("adjustment"), dict) else {}
    review_required = row.get("review_required") is True or adjustment.get("review_required") is True
    if reasons:
        return None, reasons
    return {
        "entry_id": entry_id.strip(),
        "type": flow_type,
        "recorded_at": recorded_at,
        "period_start": period_start,
        "period_end": period_end,
        "amount_usdc": amount,
        "review_required": bool(review_required),
    }, []


def merged_coverage_days(intervals: list[tuple[datetime, datetime]], start: datetime, end: datetime) -> tuple[float, bool]:
    clipped = []
    for interval_start, interval_end in intervals:
        clipped_start = max(interval_start, start)
        clipped_end = min(interval_end, end)
        if clipped_start < clipped_end:
            clipped.append((clipped_start, clipped_end))
    if not clipped:
        return 0.0, False
    ordered = sorted(clipped, key=lambda item: item[0])
    merged: list[list[datetime]] = []
    for interval_start, interval_end in ordered:
        if not merged or interval_start > merged[-1][1]:
            merged.append([interval_start, interval_end])
        elif interval_end > merged[-1][1]:
            merged[-1][1] = interval_end
    seconds = sum((interval_end - interval_start).total_seconds() for interval_start, interval_end in merged)
    contiguous = len(merged) == 1 and merged[0][0] <= start and merged[0][1] >= end
    return round(seconds / 86400, 3), contiguous


def detector_threshold(base_value: float | None) -> float:
    if base_value is None:
        return 1.50
    return max(1.50, abs(base_value) * 0.05)


def equity_jump_threshold(previous_value: float | None) -> float:
    if previous_value is None:
        return 2.00
    return max(2.00, abs(previous_value) * 0.075)


def run_detectors(snapshots: list[dict[str, Any]], base_value: float | None) -> tuple[list[str], dict[str, Any]]:
    flags: list[str] = []
    details: dict[str, Any] = {
        "possible_deposit": {"status": "pass", "events": []},
        "possible_withdrawal": {"status": "pass", "events": []},
        "withdrawal_like_drop": {"status": "pass", "events": []},
        "equity_jump": {"status": "pass", "events": []},
        "adjustment_pending": {"status": "pass", "events": []},
        "missing_data": {"status": "pass", "events": []},
    }
    if len(snapshots) < MIN_SNAPSHOTS:
        flags.append("missing_data")
        details["missing_data"]["status"] = "fail"
        details["missing_data"]["events"].append({"reason": "insufficient_snapshots"})
        return flags, details

    deposit_threshold = detector_threshold(base_value)
    for previous, current in zip(snapshots, snapshots[1:]):
        previous_at = parse_dt(previous.get("snapshot_at"))
        current_at = parse_dt(current.get("snapshot_at"))
        previous_value = as_float(previous.get("total_value"))
        current_value = as_float(current.get("total_value"))
        if previous_at is None or current_at is None or previous_value is None or current_value is None:
            if "missing_data" not in flags:
                flags.append("missing_data")
            details["missing_data"]["status"] = "fail"
            details["missing_data"]["events"].append({"reason": "snapshot_field_missing"})
            continue
        delta = round(current_value - previous_value, 6)
        event = {
            "snapshot_at": iso(current_at),
            "previous_snapshot_at": iso(previous_at),
            "delta_usdc": round(delta, 2),
        }
        if current.get("possible_deposit") is True or delta > deposit_threshold:
            if "possible_deposit" not in flags:
                flags.append("possible_deposit")
            details["possible_deposit"]["status"] = "fail"
            details["possible_deposit"]["events"].append(event)
        if delta < -deposit_threshold:
            for name in ("possible_withdrawal", "withdrawal_like_drop"):
                if name not in flags:
                    flags.append(name)
                details[name]["status"] = "fail"
                details[name]["events"].append(event)
        if abs(delta) > equity_jump_threshold(previous_value):
            if "equity_jump" not in flags:
                flags.append("equity_jump")
            details["equity_jump"]["status"] = "fail"
            details["equity_jump"]["events"].append(event)
    return flags, details


def base_payload(row: dict[str, Any] | None, snapshot: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    total_value = as_float(snapshot.get("total_value")) if snapshot else None
    payload: dict[str, Any] = {
        "timestamp": iso(row.get("period_end")),
        "actor": "pablo_manual",
        "source": "wallet_cash_flows.jsonl",
        "entry_id": row.get("entry_id"),
    }
    if total_value is not None:
        payload["total_value_usdc"] = round(total_value, 2)
    return payload


def choose_base_row(flows: list[dict[str, Any]]) -> dict[str, Any] | None:
    anchors = [row for row in flows if row.get("type") == "no_cash_flow_attestation"]
    if not anchors:
        return None
    return max(anchors, key=lambda row: row.get("period_end") or datetime.min.replace(tzinfo=timezone.utc))


def latest_snapshot_at_or_none(snapshots: list[dict[str, Any]]) -> datetime | None:
    if not snapshots:
        return None
    return parse_dt(snapshots[-1].get("snapshot_at"))


def nearest_snapshot_at_or_before(snapshots: list[dict[str, Any]], at: datetime | None) -> dict[str, Any] | None:
    if at is None:
        return None
    candidates = [row for row in snapshots if (parse_dt(row.get("snapshot_at")) or datetime.max.replace(tzinfo=timezone.utc)) <= at]
    return candidates[-1] if candidates else None


def compute_virtual_coverage(data_dir: Path, snapshot_file: Path, cash_flows_file: Path, generated_at: datetime | None = None) -> dict[str, Any]:
    generated_at = generated_at or utc_now()
    snapshot_exists, snapshot_rows, snapshot_warnings = read_jsonl(snapshot_file)
    cash_exists, cash_rows, cash_warnings = read_jsonl(cash_flows_file)
    warnings = snapshot_warnings + cash_warnings

    output: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": iso(generated_at),
        "status": "missing",
        "coverage_days_explicit": 0,
        "coverage_days_virtual": 0,
        "base_t0": None,
        "actor": "derived_log_only",
        "anomaly_flags": [],
        "review_required": False,
        "fail_closed_reason": None,
        "last_detector_run_at": None,
        "dashboard_reconciliation_status": "not_supplied",
        "canonical_eligible": False,
        "inputs": {
            "data_dir": str(data_dir),
            "snapshot_file": str(snapshot_file),
            "cash_flows_file": str(cash_flows_file),
            "snapshot_file_exists": snapshot_exists,
            "cash_flows_file_exists": cash_exists,
        },
        "detectors": {},
        "warnings": warnings,
        "guardrails": {
            "log_only": True,
            "read_only": True,
            "writes_wallet_cash_flows": False,
            "integrates_pnl_report": False,
            "bankroll_authorized": False,
            "canonical_eligible": False,
        },
    }

    if snapshot_warnings:
        output["status"] = "unreconciled"
        output["anomaly_flags"] = ["missing_data"]
        output["review_required"] = True
        output["fail_closed_reason"] = "input_parse_error"
        output["detectors"] = {"missing_data": {"status": "fail", "events": snapshot_warnings}}
        return output
    if not snapshot_exists:
        output["status"] = "unreconciled"
        output["anomaly_flags"] = ["missing_data"]
        output["review_required"] = True
        output["fail_closed_reason"] = "missing_snapshots"
        output["detectors"] = {"missing_data": {"status": "fail", "events": [{"reason": "missing_snapshots"}]}}
        return output

    snapshots = sorted_valid_snapshots(snapshot_rows)
    latest_at = latest_snapshot_at_or_none(snapshots)
    output["last_detector_run_at"] = iso(latest_at)
    if len(snapshots) < MIN_SNAPSHOTS:
        flags, detectors = run_detectors(snapshots, None)
        output["status"] = "unreconciled"
        output["anomaly_flags"] = flags or ["missing_data"]
        output["review_required"] = True
        output["fail_closed_reason"] = "insufficient_snapshots"
        output["detectors"] = detectors
        return output

    if cash_warnings:
        output["status"] = "unreconciled"
        output["anomaly_flags"] = ["missing_data"]
        output["review_required"] = True
        output["fail_closed_reason"] = "cash_flows_parse_error"
        output["detectors"] = {"missing_data": {"status": "fail", "events": cash_warnings}}
        return output

    valid_flows: list[dict[str, Any]] = []
    rejection_reasons: list[str] = []
    for row in cash_rows:
        valid_row, reasons = validate_cash_flow(row)
        if valid_row is None:
            rejection_reasons.extend(reasons)
            continue
        valid_flows.append(valid_row)
    if rejection_reasons:
        output["status"] = "unreconciled"
        output["anomaly_flags"] = ["missing_data"]
        output["review_required"] = True
        output["fail_closed_reason"] = "cash_flows_invalid"
        output["detectors"] = {"missing_data": {"status": "fail", "events": rejection_reasons[:12]}}
        return output

    window_end = latest_at
    window_start = window_end - timedelta(days=WINDOW_DAYS) if window_end else None
    explicit_intervals = [
        (row["period_start"], row["period_end"])
        for row in valid_flows
        if row.get("type") == "no_cash_flow_attestation"
    ]
    if window_start and window_end:
        coverage_days_explicit, full_explicit = merged_coverage_days(explicit_intervals, window_start, window_end)
    else:
        coverage_days_explicit, full_explicit = 0.0, False
    output["coverage_days_explicit"] = int(coverage_days_explicit) if coverage_days_explicit.is_integer() else coverage_days_explicit

    adjustment_rows = [row for row in valid_flows if row.get("type") == "adjustment"]
    pending_adjustments = [row for row in adjustment_rows if row.get("review_required") is True]
    base_row = choose_base_row(valid_flows)
    base_snapshot = nearest_snapshot_at_or_before(snapshots, base_row.get("period_end") if base_row else None)
    output["base_t0"] = base_payload(base_row, base_snapshot)

    base_value = as_float(base_snapshot.get("total_value")) if base_snapshot else as_float(snapshots[0].get("total_value"))
    flags, detectors = run_detectors(snapshots, base_value)
    if pending_adjustments:
        flags.append("adjustment_pending")
        detectors["adjustment_pending"]["status"] = "fail"
        detectors["adjustment_pending"]["events"] = [
            {"entry_id": row.get("entry_id"), "period_end": iso(row.get("period_end"))}
            for row in pending_adjustments
        ]
    output["detectors"] = detectors

    if flags:
        output["status"] = "unreconciled"
        output["anomaly_flags"] = flags
        output["review_required"] = True
        output["fail_closed_reason"] = flags[0]
        return output

    if full_explicit:
        output["status"] = "attested_full_7d"
        return output

    if base_row is None:
        output["status"] = "missing"
        output["fail_closed_reason"] = "missing_base_t0"
        return output

    base_t0 = base_row.get("period_end")
    if not isinstance(base_t0, datetime) or latest_at is None or base_t0 > latest_at:
        output["status"] = "base_anchored"
        output["fail_closed_reason"] = "base_t0_not_covered"
        return output

    virtual_days = max(0.0, (latest_at - base_t0).total_seconds() / 86400)
    output["coverage_days_virtual"] = int(virtual_days) if virtual_days.is_integer() else round(virtual_days, 3)
    if virtual_days > BASE_T0_EXPIRES_DAYS:
        output["status"] = "base_anchored"
        output["fail_closed_reason"] = "base_t0_expired"
        return output

    output["status"] = "attested_virtual"
    return output


def emit_text(report: dict[str, Any]) -> None:
    print(f"status={report['status']}")
    print(f"coverage_days_explicit={report['coverage_days_explicit']}")
    print(f"coverage_days_virtual={report['coverage_days_virtual']}")
    print(f"canonical_eligible={str(report['canonical_eligible']).lower()}")
    if report.get("fail_closed_reason"):
        print(f"fail_closed_reason={report['fail_closed_reason']}")


def main() -> int:
    configure_stdout()
    args = parse_args()
    data_dir = Path(args.data_dir)
    snapshot_file = Path(args.snapshot_file) if args.snapshot_file else default_snapshot_file(data_dir)
    cash_flows_file = Path(args.cash_flows_file) if args.cash_flows_file else default_cash_flows_file(data_dir)
    report = compute_virtual_coverage(data_dir, snapshot_file, cash_flows_file)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        emit_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
