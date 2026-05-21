from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "wallet_cash_flow_pending_attestation.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("wallet_cash_flow_pending_attestation", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def wallet_snapshots(values: list[float], start: datetime | None = None, *, possible_deposit_at: int | None = None) -> list[dict]:
    start = start or datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
    rows = []
    for index, value in enumerate(values):
        at = start + timedelta(days=index)
        rows.append(
            {
                "schema_version": 1,
                "snapshot_at": at.isoformat().replace("+00:00", "Z"),
                "api_ok": True,
                "total_value": value,
                "possible_deposit": index == possible_deposit_at,
            }
        )
    return rows


def cash_flow_row(start: datetime, end: datetime, **extra) -> dict:
    row = {
        "schema_version": 2,
        "entry_id": extra.pop("entry_id", "PENDING-BASE-001"),
        "actor": "pablo_manual",
        "type": "no_cash_flow_attestation",
        "recorded_at": end.isoformat().replace("+00:00", "Z"),
        "period_start": start.isoformat().replace("+00:00", "Z"),
        "period_end": end.isoformat().replace("+00:00", "Z"),
    }
    row.update(extra)
    return row


def compute(data_dir: Path) -> dict:
    module = load_tool_module()
    return module.compute_pending_attestation(
        data_dir,
        data_dir / "wallet_portfolio_snapshots.jsonl",
        data_dir / "wallet_cash_flows.jsonl",
        generated_at=datetime(2026, 5, 10, 0, 0, tzinfo=timezone.utc),
    )


def test_gap_without_anomalies_emits_pending_no_cash_flow_attestation(tmp_path):
    start = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
    attested_end = start + timedelta(days=2)
    latest = start + timedelta(days=4)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots([100.0, 100.1, 100.0, 100.2, 100.1], start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow_row(start, attested_end)])

    report = compute(tmp_path)

    assert report["status"] == "pending_no_cash_flow_attestation"
    assert report["latest_attested_end"] == attested_end.isoformat().replace("+00:00", "Z")
    assert report["latest_snapshot_at"] == latest.isoformat().replace("+00:00", "Z")
    assert report["gap"]["period_start"] == attested_end.isoformat().replace("+00:00", "Z")
    assert report["gap"]["period_end"] == latest.isoformat().replace("+00:00", "Z")
    pending = report["pending_no_cash_flow_attestation"]
    assert pending["recommended_actor"] == "pablo_manual"
    assert pending["recommended_type"] == "no_cash_flow_attestation"
    assert pending["canonical_eligible"] is False
    assert pending["writes_wallet_cash_flows"] is False
    assert pending["manual_confirmation_required"] is True
    assert "--write" not in pending["suggested_command"]["argv"]


def test_gap_with_possible_deposit_and_equity_jump_requires_manual_review(tmp_path):
    start = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
    attested_end = start + timedelta(days=2)
    write_jsonl(
        tmp_path / "wallet_portfolio_snapshots.jsonl",
        wallet_snapshots([100.0, 100.0, 100.0, 112.0, 112.1], start=start, possible_deposit_at=3),
    )
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow_row(start, attested_end)])

    report = compute(tmp_path)

    assert report["status"] == "manual_review_required"
    assert "possible_deposit" in report["anomaly_flags"]
    assert "equity_jump" in report["anomaly_flags"]
    assert report["pending_no_cash_flow_attestation"] is None
    assert report["writes_wallet_cash_flows"] is False


def test_no_gap_emits_no_pending_attestation(tmp_path):
    start = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=4)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots([100.0, 100.0, 100.0, 100.0, 100.0], start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow_row(start, latest)])

    report = compute(tmp_path)

    assert report["status"] == "no_pending_attestation"
    assert report["gap"] is None
    assert report["pending_no_cash_flow_attestation"] is None
    assert report["writes_wallet_cash_flows"] is False


def test_write_latest_does_not_write_wallet_cash_flows(tmp_path):
    module = load_tool_module()
    start = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
    attested_end = start + timedelta(days=2)
    cash_flows_path = tmp_path / "wallet_cash_flows.jsonl"
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots([100.0, 100.1, 100.0, 100.2], start=start))
    write_jsonl(cash_flows_path, [cash_flow_row(start, attested_end)])
    before = cash_flows_path.read_text(encoding="utf-8")

    rc = module.main([
        "--data-dir",
        str(tmp_path),
        "--write-latest",
        "--output",
        str(tmp_path / "pending.json"),
        "--json",
        "--generated-at",
        "2026-05-10T00:00:00Z",
    ])

    assert rc == 0
    assert (tmp_path / "pending.json").exists()
    assert cash_flows_path.read_text(encoding="utf-8") == before
