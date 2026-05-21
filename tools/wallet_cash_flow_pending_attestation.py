#!/usr/bin/env python3
"""LOG_ONLY pending wallet cash-flow attestation helper.

This tool proposes a manual no-cash-flow attestation when wallet snapshots have
advanced beyond the last explicit manual attestation. It never writes to
wallet_cash_flows.jsonl.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SNAPSHOT_SCHEMA_VERSION = 1
CASH_FLOW_SCHEMA_VERSION = 2
DEFAULT_OUTPUT_NAME = "wallet_cash_flow_pending_attestation.json"
RECOMMENDED_ACTOR = "pablo_manual"
RECOMMENDED_TYPE = "no_cash_flow_attestation"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute a LOG_ONLY pending no-cash-flow attestation proposal."
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
    parser.add_argument(
        "--output",
        default=None,
        help="Defaults to data/wallet_cash_flow_pending_attestation.json when --write-latest is used.",
    )
    parser.add_argument("--write-latest", action="store_true", help="Write the LOG_ONLY JSON artifact.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument("--generated-at", help="Testing hook: ISO-8601 UTC timestamp.")
    return parser.parse_args(argv)


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
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
        return None
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
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    warnings.append(f"{path.name}:{line_no}:json_decode")
                    continue
                if isinstance(row, dict):
                    rows.append(row)
                else:
                    warnings.append(f"{path.name}:{line_no}:not_object")
    except OSError as exc:
        warnings.append(f"{path.name}:read_error:{str(exc)[:120]}")
    return True, rows, warnings


def default_snapshot_file(data_dir: Path) -> Path:
    return data_dir / "wallet_portfolio_snapshots.jsonl"


def default_cash_flows_file(data_dir: Path) -> Path:
    return data_dir / "wallet_cash_flows.jsonl"


def default_output_file(data_dir: Path) -> Path:
    return data_dir / DEFAULT_OUTPUT_NAME


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
        key=lambda row: parse_dt(row.get("snapshot_at")) or datetime.min.replace(tzinfo=timezone.utc),
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
    if row.get("actor") != RECOMMENDED_ACTOR:
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
    if reasons:
        return None, reasons
    return {
        "entry_id": entry_id.strip(),
        "type": flow_type,
        "recorded_at": recorded_at,
        "period_start": period_start,
        "period_end": period_end,
        "amount_usdc": amount,
    }, []


def latest_attested_end(flows: list[dict[str, Any]]) -> datetime | None:
    ends = [
        row["period_end"]
        for row in flows
        if row.get("type") == RECOMMENDED_TYPE and isinstance(row.get("period_end"), datetime)
    ]
    return max(ends) if ends else None


def detector_threshold(base_value: float | None) -> float:
    if base_value is None:
        return 1.50
    return max(1.50, abs(base_value) * 0.05)


def equity_jump_threshold(previous_value: float | None) -> float:
    if previous_value is None:
        return 2.00
    return max(2.00, abs(previous_value) * 0.075)


def run_gap_detectors(snapshots: list[dict[str, Any]], gap_start: datetime, gap_end: datetime) -> tuple[list[str], dict[str, Any]]:
    selected = [
        row for row in snapshots
        if gap_start <= (parse_dt(row.get("snapshot_at")) or datetime.min.replace(tzinfo=timezone.utc)) <= gap_end
    ]
    details: dict[str, Any] = {
        "possible_deposit": {"status": "pass", "events": []},
        "possible_withdrawal": {"status": "pass", "events": []},
        "withdrawal_like_drop": {"status": "pass", "events": []},
        "equity_jump": {"status": "pass", "events": []},
        "missing_data": {"status": "pass", "events": []},
    }
    flags: list[str] = []
    if len(selected) < 2:
        flags.append("missing_data")
        details["missing_data"]["status"] = "fail"
        details["missing_data"]["events"].append({"reason": "insufficient_gap_snapshots"})
        return flags, details

    base_value = as_float(selected[0].get("total_value"))
    deposit_threshold = detector_threshold(base_value)
    for previous, current in zip(selected, selected[1:]):
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


def suggested_command(data_dir: Path, period_start: str, period_end: str, note: str) -> dict[str, Any]:
    argv = [
        "python",
        "tools/wallet_cash_flow_log.py",
        "append",
        "--type",
        RECOMMENDED_TYPE,
        "--period-start",
        period_start,
        "--period-end",
        period_end,
        "--note",
        note,
        "--data-dir",
        str(data_dir),
        "--json",
    ]
    return {"argv": argv, "text": " ".join(shlex.quote(part) for part in argv)}


def base_report(
    data_dir: Path,
    snapshot_file: Path,
    cash_flows_file: Path,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": iso(generated_at),
        "status": "no_pending_attestation",
        "latest_attested_end": None,
        "latest_snapshot_at": None,
        "gap": None,
        "pending_no_cash_flow_attestation": None,
        "manual_confirmation_required": False,
        "canonical_eligible": False,
        "writes_wallet_cash_flows": False,
        "changes_canonical_source": False,
        "changes_bankroll": False,
        "detectors": {},
        "anomaly_flags": [],
        "warnings": [],
        "inputs": {
            "data_dir": str(data_dir),
            "snapshot_file": str(snapshot_file),
            "cash_flows_file": str(cash_flows_file),
        },
    }


def compute_pending_attestation(
    data_dir: Path,
    snapshot_file: Path,
    cash_flows_file: Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or utc_now()
    report = base_report(data_dir, snapshot_file, cash_flows_file, generated_at)
    snapshot_exists, snapshot_rows, snapshot_warnings = read_jsonl(snapshot_file)
    cash_exists, cash_rows, cash_warnings = read_jsonl(cash_flows_file)
    report["warnings"] = snapshot_warnings + cash_warnings

    if snapshot_warnings or cash_warnings:
        report.update(
            {
                "status": "manual_review_required",
                "manual_confirmation_required": True,
                "anomaly_flags": ["input_parse_error"],
            }
        )
        return report
    if not snapshot_exists:
        report.update(
            {
                "status": "manual_review_required",
                "manual_confirmation_required": True,
                "anomaly_flags": ["missing_snapshots"],
            }
        )
        return report

    snapshots = sorted_valid_snapshots(snapshot_rows)
    if not snapshots:
        report.update(
            {
                "status": "manual_review_required",
                "manual_confirmation_required": True,
                "anomaly_flags": ["missing_valid_snapshots"],
            }
        )
        return report
    latest_snapshot = parse_dt(snapshots[-1].get("snapshot_at"))
    report["latest_snapshot_at"] = iso(latest_snapshot)

    valid_flows: list[dict[str, Any]] = []
    rejection_reasons: list[str] = []
    if cash_exists:
        for row in cash_rows:
            valid_row, reasons = validate_cash_flow(row)
            if valid_row is None:
                rejection_reasons.extend(reasons)
                continue
            valid_flows.append(valid_row)
    if rejection_reasons:
        report.update(
            {
                "status": "manual_review_required",
                "manual_confirmation_required": True,
                "anomaly_flags": ["cash_flows_invalid"],
                "warnings": report["warnings"] + rejection_reasons[:12],
            }
        )
        return report

    attested_end = latest_attested_end(valid_flows)
    report["latest_attested_end"] = iso(attested_end)
    if attested_end is None:
        report.update(
            {
                "status": "manual_review_required",
                "manual_confirmation_required": True,
                "anomaly_flags": ["missing_attestation_anchor"],
            }
        )
        return report
    if latest_snapshot is None or latest_snapshot <= attested_end:
        return report

    gap_days = round((latest_snapshot - attested_end).total_seconds() / 86400, 3)
    report["gap"] = {
        "period_start": iso(attested_end),
        "period_end": iso(latest_snapshot),
        "days": int(gap_days) if float(gap_days).is_integer() else gap_days,
    }
    flags, detectors = run_gap_detectors(snapshots, attested_end, latest_snapshot)
    report["detectors"] = detectors
    report["anomaly_flags"] = flags
    if flags:
        report.update(
            {
                "status": "manual_review_required",
                "manual_confirmation_required": True,
            }
        )
        return report

    start_text = iso(attested_end) or ""
    end_text = iso(latest_snapshot) or ""
    note = "Pablo manual confirmation requested: no deposits, withdrawals, or other external Polymarket cash flows during this period."
    report.update(
        {
            "status": "pending_no_cash_flow_attestation",
            "manual_confirmation_required": True,
            "pending_no_cash_flow_attestation": {
                "period_start": start_text,
                "period_end": end_text,
                "recommended_actor": RECOMMENDED_ACTOR,
                "recommended_type": RECOMMENDED_TYPE,
                "suggested_note": note,
                "canonical_eligible": False,
                "writes_wallet_cash_flows": False,
                "manual_confirmation_required": True,
                "suggested_command": suggested_command(data_dir, start_text, end_text, note),
            },
        }
    )
    return report


def emit_text(report: dict[str, Any]) -> None:
    print(f"status={report['status']}")
    gap = report.get("gap") if isinstance(report.get("gap"), dict) else None
    if gap:
        print(f"gap={gap.get('period_start')} -> {gap.get('period_end')}")
    if report.get("manual_confirmation_required"):
        print("manual_confirmation_required=true")
    if report.get("anomaly_flags"):
        print("anomaly_flags=" + ",".join(report["anomaly_flags"]))
    pending = report.get("pending_no_cash_flow_attestation")
    if isinstance(pending, dict):
        command = pending.get("suggested_command") if isinstance(pending.get("suggested_command"), dict) else {}
        print("suggested_command=" + str(command.get("text", "")))


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv)
    data_dir = Path(args.data_dir)
    snapshot_file = Path(args.snapshot_file) if args.snapshot_file else default_snapshot_file(data_dir)
    cash_flows_file = Path(args.cash_flows_file) if args.cash_flows_file else default_cash_flows_file(data_dir)
    generated_at = parse_dt(args.generated_at) if args.generated_at else None
    if args.generated_at and generated_at is None:
        print("ERROR: --generated-at must be ISO-8601 UTC", file=sys.stderr)
        return 2
    report = compute_pending_attestation(data_dir, snapshot_file, cash_flows_file, generated_at=generated_at)
    if args.write_latest:
        output = Path(args.output) if args.output else default_output_file(data_dir)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        emit_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
