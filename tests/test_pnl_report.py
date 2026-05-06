from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "pnl_report.py"


def run_cli(data_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--data-dir",
            str(data_dir),
            "--json",
            "--generated-at",
            "2026-05-09T00:00:00Z",
            *extra,
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )


def load_payload(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def iso(at: datetime) -> str:
    return at.isoformat().replace("+00:00", "Z")


def snapshots(
    start: datetime,
    count: int,
    step_hours: int = 24,
    value_step: float = 1.0,
    extra_by_index: dict[int, dict] | None = None,
) -> list[dict]:
    extra_by_index = extra_by_index or {}
    rows = []
    for index in range(count):
        at = start + timedelta(hours=step_hours * index)
        row = {
            "schema_version": 1,
            "snapshot_at": iso(at),
            "api_ok": True,
            "total_value": 100 + value_step * index,
            "snapshot_id": f"S-{index:03d}",
        }
        row.update(extra_by_index.get(index, {}))
        rows.append(row)
    return rows


def cash_flow(
    start: datetime,
    end: datetime,
    flow_type: str = "no_cash_flow_attestation",
    entry_id: str = "WCF-001",
    amount: str | None = None,
    **extra,
) -> dict:
    row = {
        "schema_version": 2,
        "entry_id": entry_id,
        "actor": "pablo_manual",
        "type": flow_type,
        "recorded_at": iso(end),
        "period_start": iso(start),
        "period_end": iso(end),
    }
    if flow_type in {"deposit", "withdrawal", "adjustment"}:
        row["amount_usdc"] = amount or "0"
    row.update(extra)
    return row


def write_lifecycle(data_dir: Path, pnl: float, contaminated: bool = True) -> None:
    (data_dir / "trade_lifecycle.json").write_text(
        json.dumps(
            [
                {
                    "status": "closed",
                    "closed_at": "2026-05-08T00:00:00Z",
                    "pnl_cash": pnl,
                    "contaminated": contaminated,
                }
            ]
        ),
        encoding="utf-8",
    )


def test_missing_cash_flow_log(tmp_path):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 8))

    payload = load_payload(run_cli(tmp_path))

    assert payload["inputs"]["cash_flows"]["status"] == "missing"
    for horizon in payload["horizons"].values():
        assert horizon["status"] == "blocked"
        assert horizon["value_usdc"] is None
        assert "cash_flow_log missing" in horizon["reason"]
        assert horizon["promotion_blocked_by"] == ["cash_flows.status=missing"]
    assert payload["guardrails"]["would_send"] is False
    assert payload["guardrails"]["operational_use"] == "forbidden"
    assert payload["guardrails"]["promotes_canonical_source"] is False


def test_zero_snapshots(tmp_path):
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", [])
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [])

    payload = load_payload(run_cli(tmp_path))

    assert all(horizon["status"] == "unavailable" for horizon in payload["horizons"].values())
    assert all(horizon["value_usdc"] is None for horizon in payload["horizons"].values())


def test_single_snapshot(tmp_path):
    start = datetime(2026, 5, 8, tzinfo=timezone.utc)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 1))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(start - timedelta(days=1), start)])

    payload = load_payload(run_cli(tmp_path))

    assert payload["horizons"]["1D"]["status"] == "blocked"
    assert "single snapshot" in payload["horizons"]["1D"]["reason"]
    assert payload["horizons"]["1D"]["value_usdc"] is None


def test_7d_attestation_provisional(tmp_path):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 8))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(latest - timedelta(days=5), latest)])

    payload = load_payload(run_cli(tmp_path))

    assert payload["horizons"]["1W"]["status"] == "provisional"
    assert payload["horizons"]["1W"]["quality"] == "attested_partial"
    assert payload["horizons"]["1W"]["confidence"] == "low"
    assert payload["horizons"]["1W"]["value_usdc"] == 7.0


def test_28d_attestation_canonical_candidate(tmp_path):
    start = datetime(2026, 4, 1, tzinfo=timezone.utc)
    latest = start + timedelta(days=30)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 31))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(latest - timedelta(days=30), latest)])

    payload = load_payload(run_cli(tmp_path))

    assert payload["horizons"]["1M"]["status"] == "canonical_candidate"
    assert payload["horizons"]["1M"]["confidence"] == "medium"
    assert payload["horizons"]["1M"]["quality"] == "attested_full_7d"


def test_gap_invalidates_horizon(tmp_path):
    start = datetime(2026, 5, 7, tzinfo=timezone.utc)
    rows = snapshots(start, 1) + snapshots(start + timedelta(hours=3), 1) + snapshots(start + timedelta(hours=24), 1)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", rows)
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(start, start + timedelta(hours=24))])

    payload = load_payload(run_cli(tmp_path))

    assert payload["horizons"]["1D"]["status"] == "blocked"
    assert payload["horizons"]["1D"]["coverage_gap"] is True
    assert "snapshot_gap_gt_2h" in payload["horizons"]["1D"]["promotion_blocked_by"]


def test_deposit_unreconciled_blocks(tmp_path):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(
        tmp_path / "wallet_portfolio_snapshots.jsonl",
        snapshots(start, 8, extra_by_index={3: {"possible_deposit": True}}),
    )
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(start, latest)])

    payload = load_payload(run_cli(tmp_path))

    assert payload["horizons"]["1W"]["status"] == "blocked"
    assert "possible_deposit_unreconciled" in payload["horizons"]["1W"]["promotion_blocked_by"]
    assert payload["horizons"]["1W"]["value_usdc"] is None


def test_lifecycle_always_non_canonical(tmp_path):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 8))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(start, latest)])
    write_lifecycle(tmp_path, pnl=7.0)

    payload = load_payload(run_cli(tmp_path))

    telemetry = payload["non_canonical_telemetry"]["trade_lifecycle"]
    assert telemetry["status"] == "contaminated"
    assert "non_canonical_telemetry" in telemetry["disclaimer"]
    assert payload["horizons"]["1W"]["source"] == "wallet_snapshot+cash_flow_log"
    assert payload["horizons"]["1W"]["confidence"] == "medium"


def test_divergence_alert(tmp_path):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 8))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(start, latest)])
    write_lifecycle(tmp_path, pnl=100.0)

    payload = load_payload(run_cli(tmp_path))

    horizon = payload["horizons"]["1W"]
    assert horizon["divergence_actual_usdc"] > horizon["divergence_threshold_usdc"]
    assert horizon["status"] == "provisional"
    assert horizon["confidence"] == "low"


def test_opus_attested_no_promotion(tmp_path):
    start = datetime(2026, 4, 1, tzinfo=timezone.utc)
    latest = start + timedelta(days=30)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 31))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(latest - timedelta(days=30), latest)])

    payload = load_payload(run_cli(tmp_path))

    statuses = [horizon["status"] for horizon in payload["horizons"].values()]
    confidences = [horizon["confidence"] for horizon in payload["horizons"].values()]
    assert "canonical" not in statuses
    assert "high" not in confidences
    assert payload["canonical_source"] == "none"
    assert payload["bankroll_readiness"] == "blocked"


def test_jsonl_corrupted(tmp_path):
    (tmp_path / "wallet_portfolio_snapshots.jsonl").write_text("{not-json}\n", encoding="utf-8")
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [])

    result = run_cli(tmp_path)

    assert result.returncode == 2
    assert "invalid JSONL" in result.stderr
    assert "Traceback" not in result.stderr


def test_determinism(tmp_path):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 8))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(start, latest)])

    first = run_cli(tmp_path)
    second = run_cli(tmp_path)

    assert first.returncode == 0
    assert first.stdout == second.stdout


def test_read_only_chmod(tmp_path):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    latest = start + timedelta(days=7)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 8))
    write_jsonl(tmp_path / "wallet_cash_flows.jsonl", [cash_flow(start, latest)])
    original_mode = stat.S_IMODE(os.stat(tmp_path).st_mode)
    os.chmod(tmp_path, stat.S_IREAD | stat.S_IEXEC)
    try:
        payload = load_payload(run_cli(tmp_path))
    finally:
        os.chmod(tmp_path, original_mode)

    assert payload["horizons"]["1W"]["value_usdc"] == 7.0


def test_write_report_no_init_dir(tmp_path):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    write_jsonl(tmp_path / "wallet_portfolio_snapshots.jsonl", snapshots(start, 8))
    report_path = tmp_path / "missing" / "report.json"

    result = run_cli(tmp_path, "--write-report", str(report_path))

    assert result.returncode == 2
    assert "write report directory does not exist" in result.stderr
    assert not report_path.exists()
