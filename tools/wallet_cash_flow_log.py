#!/usr/bin/env python3
"""Manual-only wallet cash-flow JSONL logger.

This tool is intentionally local and append-only. It never writes unless
``append --write`` is used, and it only creates the ledger with
``append --write --init`` after explicit confirmation.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
ACTOR = "pablo_manual"
LEDGER_FILENAME = "wallet_cash_flows.jsonl"
ALLOWED_TYPES = {"deposit", "withdrawal", "no_cash_flow_attestation", "adjustment"}
FORBIDDEN_TYPES = {"inferred", "auto", "reconstructed", "estimated"}
CONFIRMATION_TEXT = "YES I CONFIRM"


class CashFlowError(Exception):
    """Expected validation or CLI usage error."""


@dataclass(frozen=True)
class ExistingLedger:
    path: Path
    rows: list[dict[str, Any]]
    entry_ids: set[str]
    exists: bool


def ledger_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / LEDGER_FILENAME


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso_utc(value: str, field_name: str) -> datetime:
    text = str(value).strip()
    if not text or "T" not in text:
        raise CashFlowError(f"{field_name} must be an ISO-8601 UTC timestamp")
    if text.endswith("Z"):
        parseable = text[:-1] + "+00:00"
    else:
        parseable = text
    try:
        parsed = datetime.fromisoformat(parseable)
    except ValueError as exc:
        raise CashFlowError(f"{field_name} must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CashFlowError(f"{field_name} must include UTC timezone (Z or +00:00)")
    return parsed.astimezone(timezone.utc)


def normalize_iso_utc(value: str, field_name: str) -> str:
    parsed = parse_iso_utc(value, field_name)
    return parsed.isoformat().replace("+00:00", "Z")


def parse_amount(value: str | None, flow_type: str) -> str | None:
    if flow_type == "no_cash_flow_attestation":
        if value is not None:
            raise CashFlowError("no_cash_flow_attestation must not include amount_usdc")
        return None
    if flow_type in {"deposit", "withdrawal"} and value is None:
        raise CashFlowError(f"{flow_type} requires amount_usdc > 0")
    if flow_type == "adjustment" and value is None:
        raise CashFlowError("adjustment requires amount_usdc")
    assert value is not None
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise CashFlowError("amount_usdc must be numeric") from exc
    if flow_type in {"deposit", "withdrawal"} and amount <= 0:
        raise CashFlowError(f"{flow_type} requires amount_usdc > 0")
    return format(amount, "f")


def validate_type(flow_type: str) -> None:
    if flow_type in FORBIDDEN_TYPES:
        raise CashFlowError(f"type {flow_type!r} is forbidden")
    if flow_type not in ALLOWED_TYPES:
        raise CashFlowError(f"type {flow_type!r} is not allowed")


def validate_uuid4(entry_id: str, field_name: str = "entry_id") -> None:
    if entry_id.startswith("EXAMPLE-"):
        raise CashFlowError(f"{field_name} must not start with EXAMPLE-")
    try:
        parsed = uuid.UUID(entry_id, version=4)
    except ValueError as exc:
        raise CashFlowError(f"{field_name} must be a UUID4") from exc
    if str(parsed) != entry_id.lower() or parsed.version != 4:
        raise CashFlowError(f"{field_name} must be a UUID4")


def validate_row(row: dict[str, Any], entry_ids: set[str], line_no: int) -> None:
    prefix = f"line {line_no}: "
    required = {
        "schema_version",
        "entry_id",
        "recorded_at",
        "actor",
        "type",
        "period_start",
        "period_end",
    }
    missing = sorted(required - set(row))
    if missing:
        raise CashFlowError(prefix + "missing required fields: " + ", ".join(missing))
    if row.get("schema_version") != SCHEMA_VERSION:
        raise CashFlowError(prefix + "schema_version must be 2")
    if row.get("actor") != ACTOR:
        raise CashFlowError(prefix + "actor must be pablo_manual")
    flow_type = str(row.get("type"))
    validate_type(flow_type)
    entry_id = str(row.get("entry_id", ""))
    validate_uuid4(entry_id)
    if entry_id in entry_ids:
        raise CashFlowError(prefix + "duplicate entry_id")
    entry_ids.add(entry_id)
    parse_iso_utc(str(row.get("recorded_at")), "recorded_at")
    start = parse_iso_utc(str(row.get("period_start")), "period_start")
    end = parse_iso_utc(str(row.get("period_end")), "period_end")
    if end < start:
        raise CashFlowError(prefix + "period_end must be >= period_start")
    amount = row.get("amount_usdc")
    if flow_type == "no_cash_flow_attestation":
        if amount is not None:
            raise CashFlowError(prefix + "no_cash_flow_attestation must not include amount_usdc")
    else:
        normalized_amount = parse_amount(str(amount) if amount is not None else None, flow_type)
        if flow_type in {"deposit", "withdrawal"} and Decimal(normalized_amount or "0") <= 0:
            raise CashFlowError(prefix + f"{flow_type} requires amount_usdc > 0")
    note = str(row.get("note", "")).strip()
    if flow_type == "adjustment":
        if not note:
            raise CashFlowError(prefix + "adjustment requires non-empty note")
        if row.get("reviewed_by_opus") is not True:
            raise CashFlowError(prefix + "adjustment requires reviewed_by_opus=true")


def load_existing_ledger(path: Path) -> ExistingLedger:
    if not path.exists():
        return ExistingLedger(path=path, rows=[], entry_ids=set(), exists=False)
    rows: list[dict[str, Any]] = []
    entry_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CashFlowError(f"line {line_no}: corrupt JSONL: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise CashFlowError(f"line {line_no}: row must be a JSON object")
            validate_row(row, entry_ids, line_no)
            rows.append(row)
    return ExistingLedger(path=path, rows=rows, entry_ids=entry_ids, exists=True)


def build_row(args: argparse.Namespace, existing_ids: set[str]) -> dict[str, Any]:
    validate_type(args.type)
    start = normalize_iso_utc(args.period_start, "period_start")
    end = normalize_iso_utc(args.period_end, "period_end")
    if parse_iso_utc(end, "period_end") < parse_iso_utc(start, "period_start"):
        raise CashFlowError("period_end must be >= period_start")
    amount = parse_amount(args.amount_usdc, args.type)
    if args.type == "adjustment":
        if not str(args.note or "").strip():
            raise CashFlowError("adjustment requires non-empty note")
        if not args.reviewed_by_opus:
            raise CashFlowError("adjustment requires --reviewed-by-opus")
        if not args.confirm_adjustment:
            raise CashFlowError("adjustment requires --confirm-adjustment")
    elif args.reviewed_by_opus:
        raise CashFlowError("--reviewed-by-opus is only valid for adjustment")
    elif args.confirm_adjustment:
        raise CashFlowError("--confirm-adjustment is only valid for adjustment")
    entry_id = args.entry_id or str(uuid.uuid4())
    validate_uuid4(entry_id)
    if entry_id in existing_ids:
        raise CashFlowError("entry_id already exists")
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "entry_id": entry_id,
        "recorded_at": utc_now_iso(),
        "actor": ACTOR,
        "type": args.type,
        "period_start": start,
        "period_end": end,
    }
    if amount is not None:
        row["amount_usdc"] = amount
    if args.tx_ref:
        row["tx_ref"] = args.tx_ref
    if args.note:
        row["note"] = args.note
    if args.type == "adjustment":
        row["reviewed_by_opus"] = True
    return row


def print_payload(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_validate(args: argparse.Namespace) -> int:
    ledger = load_existing_ledger(ledger_path(args.data_dir))
    payload = {
        "ok": True,
        "path": str(ledger.path),
        "status": "valid" if ledger.exists else "missing",
        "rows": len(ledger.rows),
    }
    print_payload(payload, args.json)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    ledger = load_existing_ledger(ledger_path(args.data_dir))
    rows = ledger.rows[-args.last :] if args.last is not None else ledger.rows
    payload = {
        "ok": True,
        "path": str(ledger.path),
        "status": "valid" if ledger.exists else "missing",
        "rows": rows,
        "row_count": len(ledger.rows),
    }
    print_payload(payload, args.json)
    return 0


def confirm_init(path: Path, assume_yes: bool) -> None:
    if assume_yes:
        return
    print(f"INIT: {path} does not exist and will be created.")
    print("Type YES I CONFIRM to proceed:")
    answer = sys.stdin.readline().strip()
    if answer != CONFIRMATION_TEXT:
        raise CashFlowError("init confirmation failed; file was not created")


def cmd_append(args: argparse.Namespace) -> int:
    if args.init and not args.write:
        raise CashFlowError("--init is only valid with --write")
    path = ledger_path(args.data_dir)
    ledger = load_existing_ledger(path)
    row = build_row(args, ledger.entry_ids)
    if not args.write:
        print_payload({"dry_run": True, "path": str(path), "row": row}, args.json)
        if not args.json:
            print("DRY-RUN: row NOT written.")
        return 0
    if not ledger.exists and not args.init:
        raise CashFlowError("ledger does not exist; use --write --init to create it")
    if not ledger.exists:
        confirm_init(path, args.yes)
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    if args.json:
        print_payload({"appended": True, "path": str(path), "row": row}, True)
    else:
        print(f"APPENDED entry_id={row['entry_id']} to {path}")
        print_payload(row, False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual-only wallet cash-flow JSONL logger.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", description="Validate the existing ledger read-only.")
    validate.add_argument("--data-dir", default="data")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_validate)

    show = subparsers.add_parser("show", description="Show ledger rows read-only.")
    show.add_argument("--data-dir", default="data")
    show.add_argument("--last", type=int)
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_show)

    append = subparsers.add_parser("append", description="Dry-run or append a validated row.")
    append.add_argument("--type", required=True, choices=sorted(ALLOWED_TYPES | FORBIDDEN_TYPES))
    append.add_argument("--period-start", required=True)
    append.add_argument("--period-end", required=True)
    append.add_argument("--amount-usdc")
    append.add_argument("--tx-ref")
    append.add_argument("--note")
    append.add_argument("--reviewed-by-opus", action="store_true")
    append.add_argument("--confirm-adjustment", action="store_true")
    append.add_argument("--write", action="store_true")
    append.add_argument("--init", action="store_true")
    append.add_argument("--yes", action="store_true")
    append.add_argument("--data-dir", default="data")
    append.add_argument("--json", action="store_true")
    append.add_argument("--entry-id", help=argparse.SUPPRESS)
    append.set_defaults(func=cmd_append)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CashFlowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
