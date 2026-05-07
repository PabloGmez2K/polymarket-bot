from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "bankroll_scaling_check.py"


def run_check(data_dir: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--data-dir",
            str(data_dir),
            "--current-bankroll",
            "25",
            "--target-tier",
            "35",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def closed_trade(index: int, closed_at: datetime, pnl: float) -> dict:
    return {
        "status": "closed",
        "closed_at": closed_at.isoformat(),
        "total_amount": 1.0,
        "bot_version_opened": "v10.6.99",
        "bot_version_closed": "v10.6.99",
        "close_context": {"pnl_cash": pnl, "close_reason": "take_profit"},
        "integrity": {
            "analysis_ready": True,
            "partial_historical_record": False,
            "missing_buy_history": False,
            "close_only_record": False,
        },
        "id": f"T-{index:03d}",
    }


def test_non_canonical_lifecycle_pnl_blocks_bankroll_readiness(tmp_path):
    now = datetime.now(timezone.utc)
    write_json(
        tmp_path / "cycle_summary.json",
        {"timestamp_utc": now.isoformat(), "version": "v10.6.99"},
    )
    write_jsonl(
        tmp_path / "cycles_history.jsonl",
        [{"timestamp_utc": (now - timedelta(hours=idx)).isoformat(), "version": "v10.6.99"} for idx in range(12)],
    )
    write_json(
        tmp_path / "trade_lifecycle.json",
        {"records": [closed_trade(idx, now - timedelta(hours=idx), 1.0) for idx in range(30)]},
    )
    write_json(tmp_path / "performance.json", [])
    write_json(tmp_path / "postmortem.json", [])
    write_json(
        tmp_path / "bankroll_readiness_state.json",
        {"generated_at": now.isoformat(), "composite": 80.0, "status": "add_capital"},
    )
    write_jsonl(tmp_path / "decisions.log", [])

    payload = run_check(tmp_path)
    criteria = {item["name"]: item for item in payload["criteria"]}
    hard_codes = {item["code"] for item in payload["hard_blockers"]}

    assert criteria["pnl_source_quality"]["status"] == "blocked"
    assert criteria["pnl_non_negative"]["status"] == "blocked"
    assert criteria["win_rate_minimum"]["status"] == "blocked"
    assert criteria["drawdown_last_5_above_limit"]["status"] == "blocked"
    assert payload["evidence"]["pnl_drawdown"]["source_quality"] == "non_canonical_telemetry"
    assert "pnl_source_non_canonical" in hard_codes
    assert payload["decision"] == "do_not_increase"


def test_stale_runtime_import_blocks_review(tmp_path):
    old = datetime(2026, 4, 27, tzinfo=timezone.utc)
    write_json(tmp_path / "cycle_summary.json", {"timestamp_utc": old.isoformat(), "version": "v10.6.99"})
    write_jsonl(tmp_path / "cycles_history.jsonl", [{"timestamp_utc": old.isoformat(), "version": "v10.6.99"}])
    write_json(tmp_path / "trade_lifecycle.json", {"records": []})
    write_json(tmp_path / "performance.json", [])
    write_json(tmp_path / "postmortem.json", [])
    write_json(tmp_path / "bankroll_readiness_state.json", {"generated_at": old.isoformat(), "composite": 80.0})

    payload = run_check(tmp_path)
    criteria = {item["name"]: item for item in payload["criteria"]}
    hard_codes = {item["code"] for item in payload["hard_blockers"]}

    assert criteria["runtime_data_fresh"]["status"] == "fail"
    assert "runtime_data_stale" in hard_codes
