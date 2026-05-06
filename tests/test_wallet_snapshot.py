from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "wallet_snapshot.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("wallet_snapshot", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def wallet_snapshots(
    start: datetime | None = None,
    count: int = 15,
    step_hours: int = 12,
    possible_deposit_at: datetime | None = None,
) -> list[dict]:
    start = start or datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        at = start + timedelta(hours=step_hours * index)
        row = {
            "schema_version": 1,
            "snapshot_at": at.isoformat().replace("+00:00", "Z"),
            "api_ok": True,
            "total_value": 100.0 + index,
        }
        if possible_deposit_at is not None and at == possible_deposit_at:
            row["possible_deposit"] = True
        rows.append(row)
    return rows


def cash_flow_row(
    start: datetime,
    end: datetime,
    flow_type: str = "no_cash_flow_attestation",
    **extra,
) -> dict:
    row = {
        "schema_version": 2,
        "entry_id": extra.pop("entry_id", "WCF-20260508-0001"),
        "actor": extra.pop("actor", "pablo_manual"),
        "type": flow_type,
        "recorded_at": extra.pop("recorded_at", end.isoformat().replace("+00:00", "Z")),
        "period_start": start.isoformat().replace("+00:00", "Z"),
        "period_end": end.isoformat().replace("+00:00", "Z"),
    }
    if flow_type in {"deposit", "withdrawal", "adjustment"}:
        row["amount_usdc"] = extra.pop("amount_usdc", "0")
    row.update(extra)
    return row


def build_report_for(data_dir: Path) -> dict:
    module = load_tool_module()
    history_rows, history_warnings = module.read_jsonl(data_dir / "wallet_portfolio_snapshots.jsonl")
    valid = module.sorted_valid_snapshots(history_rows)
    flows, cash_flows, flow_warnings = module.load_cash_flows(data_dir / "wallet_cash_flows.jsonl", valid)
    snapshot = valid[-1] if valid else module.empty_snapshot(
        datetime(2026, 5, 8, 0, 0, tzinfo=timezone.utc),
        "no valid snapshots in history",
    )
    return module.build_report(
        snapshot,
        history_rows,
        flows,
        cash_flows,
        history_warnings + flow_warnings,
        datetime(2026, 5, 8, 0, 0, tzinfo=timezone.utc),
    )


def seeded_data_dir(tmp_path: Path) -> tuple[Path, datetime, datetime]:
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start))
    return tmp_path, start, latest


def assert_blocked(report: dict) -> None:
    assert report["phase2_readiness"]["phase2_ready"] is False
    assert report["wallet_pnl"]["wallet_pnl_confidence"] == "low"
    assert report["wallet_pnl"]["wallet_pnl_7d"] is None


def test_missing_cash_flows_blocks_readiness(tmp_path):
    report = build_report_for(tmp_path)

    assert report["cash_flows"]["status"] == "missing"
    assert report["phase2_readiness"]["phase2_ready"] is False
    assert report["phase2_readiness"]["phase2_ready_reason"] == "cash_flow_unknown"
    assert report["wallet_pnl"]["wallet_pnl_confidence"] == "low"
    assert report["wallet_pnl"]["wallet_pnl_7d"] is None


def test_empty_cash_flows_blocks_readiness(tmp_path):
    data_dir, _, _ = seeded_data_dir(tmp_path)
    (data_dir / "wallet_cash_flows.jsonl").write_text("", encoding="utf-8")

    report = build_report_for(data_dir)

    assert report["cash_flows"]["status"] == "empty_unattested"
    assert_blocked(report)


def test_example_entry_id_is_rejected(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(start, latest, entry_id="EXAMPLE-001")])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["rejected"] == 1
    assert "example_id" in report["cash_flows"]["rejection_reasons"]
    assert_blocked(report)


def test_example_only_marker_is_rejected(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(start, latest, marker="EXAMPLE_ONLY")])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["rejected"] == 1
    assert "example_marker" in report["cash_flows"]["rejection_reasons"]
    assert_blocked(report)


def test_legacy_schema_v1_row_is_rejected(tmp_path):
    data_dir, _, _ = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [{"type": "deposit", "amount": 10, "date": "2026-05-06"}])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["status"] == "invalid"
    assert "legacy_v1_row_rejected" in report["cash_flows"]["rejection_reasons"]
    assert_blocked(report)


def test_actor_mismatch_is_rejected(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(start, latest, actor="someone_else")])

    report = build_report_for(data_dir)

    assert "actor_mismatch" in report["cash_flows"]["rejection_reasons"]
    assert_blocked(report)


def test_naive_timestamp_and_pure_dates_are_rejected(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    naive = cash_flow_row(start, latest, recorded_at="2026-05-08T00:00:00")
    pure_date = cash_flow_row(start, latest, entry_id="WCF-20260508-0002")
    pure_date["period_start"] = "2026-05-01"
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [naive, pure_date])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["status"] == "invalid"
    assert "period_format" in report["cash_flows"]["rejection_reasons"]
    assert_blocked(report)


def test_full_7d_attestation_can_unlock_phase2_with_sufficient_snapshots(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(start, latest)])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["status"] == "attested_full_7d"
    assert report["phase2_readiness"]["phase2_ready"] is True
    assert report["wallet_pnl"]["wallet_pnl_method"] == "snapshot_delta"
    assert report["wallet_pnl"]["wallet_pnl_confidence"] == "high"


def test_three_day_attestation_is_partial_and_blocked(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(latest - timedelta(days=3), latest)])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["status"] == "attested_partial"
    assert report["cash_flows"]["coverage_days_7d"] == 3
    assert_blocked(report)


def test_deposit_total_adjusts_wallet_pnl_only_with_full_attestation(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, latest),
        cash_flow_row(latest, latest, flow_type="deposit", entry_id="WCF-DEP", amount_usdc="10"),
    ])

    report = build_report_for(data_dir)

    assert report["wallet_pnl"]["cash_flows_7d_total"] == 10
    assert report["wallet_pnl"]["wallet_pnl_7d"] == 4


def test_withdrawal_total_adjusts_wallet_pnl_only_with_full_attestation(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, latest),
        cash_flow_row(latest, latest, flow_type="withdrawal", entry_id="WCF-WD", amount_usdc="5"),
    ])

    report = build_report_for(data_dir)

    assert report["wallet_pnl"]["cash_flows_7d_total"] == -5
    assert report["wallet_pnl"]["wallet_pnl_7d"] == 19


def test_deposit_does_not_unlock_without_full_attestation(tmp_path):
    data_dir, _, latest = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [
        cash_flow_row(latest, latest, flow_type="deposit", entry_id="WCF-DEP", amount_usdc="10"),
    ])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["status"] == "attested_partial"
    assert report["wallet_pnl"]["cash_flows_7d_total"] == 10
    assert_blocked(report)


def test_adjustment_pending_review_is_unreconciled(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    review_at = start + timedelta(days=2)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [
        cash_flow_row(start, latest),
        cash_flow_row(
            review_at,
            review_at,
            flow_type="adjustment",
            entry_id="WCF-ADJ",
            amount_usdc="0",
            review_required=True,
        ),
    ])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["status"] == "unreconciled"
    assert report["cash_flows"]["adjustments_pending"] == 1
    assert_blocked(report)


def test_possible_deposit_without_reconciliation_is_unreconciled(tmp_path):
    start = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    possible_at = start + timedelta(days=3)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", wallet_snapshots(start=start, possible_deposit_at=possible_at))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow_row(start, start + timedelta(days=7))])

    report = build_report_for(tmp_path)

    assert report["cash_flows"]["status"] == "unreconciled"
    assert_blocked(report)


def test_phase2_ready_invariant_requires_full_attestation(tmp_path):
    data_dir, start, latest = seeded_data_dir(tmp_path)
    for rows in (
        [],
        [cash_flow_row(latest - timedelta(days=1), latest)],
        [cash_flow_row(start, latest, entry_id="EXAMPLE-001")],
    ):
        if rows:
            write_jsonl(data_dir / "wallet_cash_flows.jsonl", rows)
        else:
            (data_dir / "wallet_cash_flows.jsonl").write_text("", encoding="utf-8")
        report = build_report_for(data_dir)
        assert report["cash_flows"]["status"] != "attested_full_7d"
        assert report["phase2_readiness"]["phase2_ready"] is False


def test_confidence_low_when_cash_flows_not_full(tmp_path):
    data_dir, start, _ = seeded_data_dir(tmp_path)
    write_jsonl(data_dir / "wallet_cash_flows.jsonl", [cash_flow_row(start, start + timedelta(days=1))])

    report = build_report_for(data_dir)

    assert report["cash_flows"]["status"] != "attested_full_7d"
    assert report["wallet_pnl"]["wallet_pnl_confidence"] == "low"


def test_report_only_cli_missing_cash_flow_smoke(tmp_path):
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--report-only", "--json", "--data-dir", str(tmp_path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["cash_flows"]["status"] == "missing"
    assert payload["phase2_readiness"]["phase2_ready"] is False
    assert payload["phase2_readiness"]["phase2_ready_reason"] == "cash_flow_unknown"
    assert payload["wallet_pnl"]["wallet_pnl_confidence"] == "low"
