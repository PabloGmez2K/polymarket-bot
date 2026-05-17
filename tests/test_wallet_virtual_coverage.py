from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "wallet_virtual_coverage.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("wallet_virtual_coverage", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def wallet_snapshots(values: list[float], start: datetime | None = None) -> list[dict]:
    start = start or datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    rows = []
    for index, value in enumerate(values):
        at = start + timedelta(days=index)
        rows.append(
            {
                "schema_version": 1,
                "snapshot_at": at.isoformat().replace("+00:00", "Z"),
                "api_ok": True,
                "total_value": value,
            }
        )
    return rows


def cash_flow_row(start: datetime, end: datetime, flow_type: str = "no_cash_flow_attestation", **extra) -> dict:
    row = {
        "schema_version": 2,
        "entry_id": extra.pop("entry_id", "WVC-BASE-001"),
        "actor": extra.pop("actor", "pablo_manual"),
        "type": flow_type,
        "recorded_at": extra.pop("recorded_at", end.isoformat().replace("+00:00", "Z")),
        "period_start": start.isoformat().replace("+00:00", "Z"),
        "period_end": end.isoformat().replace("+00:00", "Z"),
    }
    if flow_type in {"deposit", "withdrawal", "adjustment"}:
        row["amount_usdc"] = extra.pop("amount_usdc", "1.00")
    row.update(extra)
    return row


def compute(data_dir: Path) -> dict:
    module = load_tool_module()
    return module.compute_virtual_coverage(
        data_dir,
        data_dir / "wallet_portfolio_snapshots.jsonl",
        data_dir / "wallet_cash_flows.jsonl",
        generated_at=datetime(2026, 5, 10, 0, 0, tzinfo=timezone.utc),
    )


def seed_virtual_base(data_dir: Path, values: list[float]) -> tuple[datetime, datetime]:
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    base = start + timedelta(days=2)
    write_jsonl(data_dir / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(values, start=start))
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(start, base)])
    return start, base


def test_happy_path_attested_virtual(tmp_path):
    seed_virtual_base(tmp_path, [100.0, 100.2, 100.1, 100.3, 100.4])

    report = compute(tmp_path)

    assert report["status"] == "attested_virtual"
    assert report["coverage_days_virtual"] == 2
    assert report["coverage_days_explicit"] == 2
    assert report["anomaly_flags"] == []
    assert report["review_required"] is False
    assert report["canonical_eligible"] is False


def test_deposit_equity_jump_fails_closed_to_unreconciled(tmp_path):
    seed_virtual_base(tmp_path, [100.0, 100.1, 100.0, 112.5, 112.6])

    report = compute(tmp_path)

    assert report["status"] == "unreconciled"
    assert "possible_deposit" in report["anomaly_flags"]
    assert "equity_jump" in report["anomaly_flags"]
    assert report["review_required"] is True
    assert report["canonical_eligible"] is False


def test_withdrawal_like_drop_fails_closed_to_unreconciled(tmp_path):
    seed_virtual_base(tmp_path, [100.0, 100.1, 100.0, 91.0, 90.9])

    report = compute(tmp_path)

    assert report["status"] == "unreconciled"
    assert "possible_withdrawal" in report["anomaly_flags"]
    assert "withdrawal_like_drop" in report["anomaly_flags"]
    assert report["review_required"] is True
    assert report["canonical_eligible"] is False


def test_missing_snapshots_fails_closed_to_unreconciled(tmp_path):
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow_row(start, start + timedelta(days=1))])

    report = compute(tmp_path)

    assert report["status"] == "unreconciled"
    assert report["fail_closed_reason"] == "missing_snapshots"
    assert report["anomaly_flags"] == ["missing_data"]
    assert report["canonical_eligible"] is False


def test_canonical_eligible_always_false_for_full_explicit_coverage(tmp_path):
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=8)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots([100.0] * 9, start=start))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow_row(start, latest)])

    report = compute(tmp_path)

    assert report["status"] == "attested_full_7d"
    assert report["coverage_days_explicit"] == 7
    assert report["canonical_eligible"] is False
