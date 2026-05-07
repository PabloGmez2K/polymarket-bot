from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "leaderboard_pnl_snapshot.py"


@contextmanager
def local_tmp_dir():
    path = REPO_ROOT / f"_tmp_leaderboard_pnl_snapshot_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def load_tool():
    import importlib.util

    spec = importlib.util.spec_from_file_location("leaderboard_pnl_snapshot", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def snapshot(**extra) -> dict:
    row = {
        "captured_at_utc": "2026-05-07T10:00:00Z",
        "captured_at_local": "2026-05-07T12:00:00+02:00",
        "wallet_masked": "0x1234...cdef",
        "user": "pablo",
        "source": "polymarket_leaderboard",
        "source_quality": "external_opaque",
        "dashboard_equivalent": False,
        "usable_for_digest": True,
        "usable_for_trend": True,
        "usable_for_bankroll": False,
        "pnl_day": 1.0,
        "pnl_week": 2.0,
        "pnl_month": 3.0,
        "pnl_all": 4.0,
        "vol_day": 10.0,
        "vol_week": 20.0,
        "vol_month": 30.0,
        "vol_all": 40.0,
        "confidence_day": "medium",
        "confidence_week": "medium",
        "confidence_month": "low",
        "confidence_all": "medium",
        "methodology_notes": "external only",
        "query_status": "ok",
        "api_error": None,
    }
    row.update(extra)
    return row


def test_snapshot_flags_are_never_bankroll_positive(monkeypatch):
    module = load_tool()

    def fake_query(wallet: str):
        assert wallet == "0x1234567890abcdef1234567890abcdef12345678"
        return (
            {
                "DAY": {"pnl": 1.23, "vol": 10.0},
                "WEEK": {"pnl": 2.34, "vol": 20.0},
                "MONTH": {"pnl": 3.45, "vol": 30.0},
                "ALL": {"pnl": 4.56, "vol": 40.0},
            },
            "ok",
            "pablo",
            None,
        )

    monkeypatch.setattr(module, "query_leaderboard", fake_query)
    args = module.parse_args(["--dry-run", "--wallet", "0x1234567890abcdef1234567890abcdef12345678"])
    payload = module.build_snapshot(args, now=datetime(2026, 5, 7, 10, tzinfo=timezone.utc))

    assert payload["usable_for_digest"] is True
    assert payload["usable_for_trend"] is True
    assert payload["usable_for_bankroll"] is False
    assert payload["dashboard_equivalent"] is False
    assert payload["source_quality"] == "external_opaque"
    assert payload["wallet_masked"] == "0x1234...5678"
    assert "readiness" not in payload
    assert "bankroll_readiness" not in payload


def test_summary_calculates_delta_against_previous_snapshot():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "observability" / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(
            path,
            [
                snapshot(captured_at_utc="2026-05-07T10:00:00Z", pnl_day=1.0, pnl_week=2.0, pnl_month=3.0, pnl_all=4.0),
                snapshot(captured_at_utc="2026-05-07T11:00:00Z", pnl_day=1.5, pnl_week=1.0, pnl_month=3.0, pnl_all=5.0),
            ],
        )

        summary = module.build_summary(path)

    assert summary["snapshot_count"] == 2
    assert summary["day_delta_vs_previous_snapshot"] == 0.5
    assert summary["week_delta_vs_previous_snapshot"] == -1.0
    assert summary["month_delta_vs_previous_snapshot"] == 0.0
    assert summary["all_delta_vs_previous_snapshot"] == 1.0
    assert summary["trend_label"] == "improving"


def test_api_failure_does_not_create_readiness_or_positive_bankroll_flags(monkeypatch):
    module = load_tool()

    def fake_query(wallet: str):
        return (
            {period: {"pnl": None, "vol": None} for period in module.PERIODS},
            "failed",
            None,
            "DAY: timeout",
        )

    monkeypatch.setattr(module, "query_leaderboard", fake_query)
    args = module.parse_args(["--dry-run", "--wallet", "0x1234567890abcdef1234567890abcdef12345678"])
    payload = module.build_snapshot(args, now=datetime(2026, 5, 7, 10, tzinfo=timezone.utc))

    assert payload["query_status"] == "failed"
    assert payload["api_error"] == "DAY: timeout"
    assert payload["usable_for_bankroll"] is False
    assert payload["dashboard_equivalent"] is False
    assert payload["pnl_day"] is None
    assert "readiness" not in payload
    assert "bankroll_readiness" not in payload


def test_missing_wallet_returns_needs_manual_wallet_input(monkeypatch):
    module = load_tool()
    for key in ("FUNDER", "POLYMARKET_WALLET", "WALLET_ADDRESS", "PROXY_WALLET"):
        monkeypatch.delenv(key, raising=False)

    args = module.parse_args(["--dry-run"])
    payload = module.build_snapshot(args, now=datetime(2026, 5, 7, 10, tzinfo=timezone.utc))

    assert payload["query_status"] == "NEEDS_MANUAL_WALLET_INPUT"
    assert payload["usable_for_bankroll"] is False
    assert payload["wallet_masked"] is None


def test_summary_cli_reads_existing_snapshots():
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(path, [snapshot(), snapshot(captured_at_utc="2026-05-07T11:00:00Z", pnl_all=6.0)])

        result = subprocess.run(
            [sys.executable, str(TOOL_PATH), "--summary", "--snapshot-file", str(path)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["snapshot_count"] == 2
    assert payload["all_delta_vs_previous_snapshot"] == 2.0
