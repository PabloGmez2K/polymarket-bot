from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "daily_bot_observability_run.py"


@contextmanager
def local_tmp_dir():
    path = REPO_ROOT / f"_tmp_daily_bot_observability_run_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def load_tool():
    spec = importlib.util.spec_from_file_location("daily_bot_observability_run", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    try:
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(REPO_ROOT / "tools"))
        except ValueError:
            pass
    return module


def snapshot(**extra) -> dict:
    row = {
        "captured_at_utc": "2026-05-07T19:51:33Z",
        "captured_at_local": "2026-05-07T21:51:33+02:00",
        "wallet_masked": "0x1234...cdef",
        "user": "pablo",
        "source": "polymarket_leaderboard",
        "source_quality": "external_opaque",
        "dashboard_equivalent": False,
        "usable_for_digest": True,
        "usable_for_trend": True,
        "usable_for_bankroll": False,
        "pnl_day": 1.39,
        "pnl_week": 4.55,
        "pnl_month": 2.83,
        "pnl_all": -29.81,
        "vol_day": 3.44,
        "vol_week": 32.19,
        "vol_month": 40.81,
        "vol_all": 1875.89,
        "volume_label": "leaderboard_trading_volume",
        "query_status": "ok",
        "api_error": None,
    }
    row.update(extra)
    return row


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def create_throughput_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE cycle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_number INTEGER,
            ts_utc TEXT NOT NULL,
            markets_evaluated INTEGER,
            buys_count INTEGER,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_number INTEGER,
            ts_utc TEXT NOT NULL,
            city TEXT NOT NULL,
            date_iso TEXT NOT NULL,
            question TEXT,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE forecast_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_number INTEGER,
            ts_utc TEXT NOT NULL,
            city TEXT NOT NULL,
            target_date TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO cycle_events (cycle_number, ts_utc, markets_evaluated, buys_count, payload_json) VALUES (?, ?, ?, ?, ?)",
        (1, "2026-05-08T12:00:00Z", 141, 0, json.dumps({"scan": {"markets_evaluated": 141}})),
    )
    conn.execute(
        "INSERT INTO market_snapshots (cycle_number, ts_utc, city, date_iso, question, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
        (
            1,
            "2026-05-08T12:00:00Z",
            "Chicago",
            "2026-05-08",
            "Will the highest temperature in Chicago be exactly 20C on May 8?",
            "{}",
        ),
    )
    conn.commit()
    conn.close()


def run_cli(*args: str, snapshot_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), *args, "--snapshot-file", str(snapshot_file)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_runner_dry_run_does_not_write_file(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert result["snapshot_written"] is False
    assert result["mode"] == "dry_run"
    assert not path.exists()
    assert "Observability only." in result["message"]
    assert "usable_for_bankroll=false" in result["message"]


def test_runner_write_snapshot_writes_one_jsonl_line(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--write-snapshot", "--snapshot-file", str(path)])
        result = module.build_run(args)
        rows = path.read_text(encoding="utf-8").splitlines()

    assert result["snapshot_written"] is True
    assert len(rows) == 1
    written = json.loads(rows[0])
    assert written["query_status"] == "ok"
    assert written["usable_for_bankroll"] is False
    assert written["runner_mode"] == "write_snapshot"


def test_runner_telegram_preview_does_not_send_or_require_telegram_env_vars(monkeypatch):
    module = load_tool()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "must_not_be_read")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "must_not_be_read")
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--telegram-preview", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert "TELEGRAM PREVIEW ONLY" in result["message"]
    assert "📊 <b>RESUMEN DIARIO DEL BOT</b>" in result["telegram_preview"]
    assert "No cambia bankroll" in result["telegram_preview"]
    assert "usable_for_bankroll=false" in result["message"]
    assert "TELEGRAM_BOT_TOKEN" not in result["message"]
    assert "sent" not in result["message"].lower()


def test_runner_manual_telegram_send_only_with_explicit_flag(monkeypatch):
    module = load_tool()
    calls = []
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    monkeypatch.setattr(
        module.daily_bot_digest,
        "send_telegram_manual",
        lambda message: calls.append(message) or {"sent": True, "reason": "sent"},
    )

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        preview_args = module.parse_args(["--dry-run", "--telegram-preview", "--snapshot-file", str(path)])
        preview_result = module.build_run(preview_args)
        send_args = module.parse_args(["--dry-run", "--send-telegram-manual", "--snapshot-file", str(path)])
        send_result = module.build_run(send_args)

    assert calls == [send_result["telegram_preview"]]
    assert preview_result["telegram_manual_send"]["reason"] == "not_attempted"
    assert send_result["telegram_manual_send"]["reason"] == "sent"
    assert "TELEGRAM MANUAL SEND PREVIEW" in send_result["message"]
    assert "usable_for_bankroll=false" in send_result["message"]


def test_runner_manual_telegram_missing_env_is_non_fatal(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    monkeypatch.setattr(
        module.daily_bot_digest,
        "send_telegram_manual",
        lambda message: {
            "sent": False,
            "reason": "TELEGRAM_NOT_CONFIGURED",
            "missing_env": ["TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"],
        },
    )

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--send-telegram-manual", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert result["telegram_manual_send"]["reason"] == "TELEGRAM_NOT_CONFIGURED"
    assert "telegram_manual_send=TELEGRAM_NOT_CONFIGURED" in result["message"]
    assert "TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN" in result["message"]
    assert "usable_for_bankroll=false" in result["message"]


def test_runner_digest_shows_deltas_with_existing_snapshot(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(
        module.leaderboard_pnl_snapshot,
        "build_snapshot",
        lambda args: snapshot(
            captured_at_utc="2026-05-07T20:00:00Z",
            pnl_day=2.0,
            pnl_week=6.0,
            pnl_month=3.0,
            pnl_all=-28.0,
        ),
    )
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(
            path,
            [
                snapshot(
                    captured_at_utc="2026-05-07T19:00:00Z",
                    pnl_day=1.0,
                    pnl_week=4.0,
                    pnl_month=2.0,
                    pnl_all=-30.0,
                )
            ],
        )
        args = module.parse_args(["--dry-run", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert "day_delta: +1.00" in result["message"]
    assert "week_delta: +2.00" in result["message"]
    assert "month_delta: +1.00" in result["message"]
    assert "all_delta: +2.00" in result["message"]


def test_runner_output_keeps_no_bankroll_and_observability_only(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot(query_status="failed"))
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert result["query_status"] == "failed"
    assert result["usable_for_bankroll"] is False
    assert result["snapshot"]["usable_for_bankroll"] is False
    assert "query_status=failed" in result["message"]
    assert "usable_for_bankroll=false" in result["message"]
    assert "Observability only." in result["message"]
    assert "readiness" not in result["message"].lower()


def test_runner_db_throughput_report_adds_log_only_digest_section(monkeypatch, tmp_path):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    db = tmp_path / "polymarket.db"
    create_throughput_db(db)
    path = tmp_path / "leaderboard_pnl_snapshots.jsonl"
    args = module.parse_args([
        "--dry-run",
        "--db-throughput-report",
        "--db",
        str(db),
        "--snapshot-file",
        str(path),
    ])
    result = module.build_run(args)

    db_summary = result["db_throughput"]
    assert db_summary["mode"] == "LOG_ONLY"
    assert db_summary["review_status"] == "REVIEW_READY"
    assert db_summary["weak_slots"][0]["slot_label"] == "12h"
    assert db_summary["dominant_condition"] == "exact"
    assert "DB Throughput:" in result["message"]
    assert "LOG_ONLY: No BANKROLL, no BUY/SELL/SKIP, no Fase C." in result["message"]
    assert "DB <b>Throughput LOG_ONLY</b>" in result["telegram_preview"]
    assert "Revision manual" in result["telegram_preview"]


def test_runner_includes_cohort_intelligence_by_default(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    monkeypatch.setattr(
        module,
        "build_cohort_intelligence_summary",
        lambda args: {
            "ok": True,
            "main_cohorts": [
                {"cohort": "exact/NO near-threshold", "n_closed": 10, "wr_observed": 0.3, "calibration_gap": 0.5, "pnl_simulated_unit": -2.0, "verdict": "REVIEW_BLOCK_LIVE"},
                {"cohort": "exact/NO far", "n_closed": 2, "wr_observed": 0.5, "calibration_gap": 0.1, "pnl_simulated_unit": 0.1, "verdict": "INSUFFICIENT_SAMPLE"},
                {"cohort": "directional NO", "n_closed": 10, "wr_observed": 0.7, "calibration_gap": -0.05, "pnl_simulated_unit": 2.0, "verdict": "CANDIDATE_FOR_CANARY_REVIEW"},
            ],
            "best_directional_no_subcohort": {"cohort": "directional NO / city=Tokyo", "n_closed": 10, "wr_observed": 0.7, "verdict": "CANDIDATE_FOR_CANARY_REVIEW"},
            "summary_verdicts": {
                "EXACT_NO_NEAR_SHADOW_STILL_JUSTIFIED": "YES",
                "DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND": "YES",
                "OPUS_REVIEW_REQUIRED_NOW": "YES",
            },
            "directional_no_next_trigger": {"resolutions_missing_for_min_sample": 0},
            "directional_forward_capture": {
                "directional_forward_seen": 10,
                "directional_forward_resolved_calibration_unique": 10,
                "status": "CALIBRATION_ACCUMULATING",
            },
        },
    )

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert result["cohort_intelligence"]["ok"] is True
    assert "Cohort Intelligence (LOG_ONLY)" in result["telegram_preview"]
    assert "directional_candidate=YES" in result["telegram_preview"]
    assert "directional forward: seen=10 | cal=10 | CALIBRATION_ACCUMULATING" in result["telegram_preview"]
    assert "No BUY/SELL/SKIP" in result["telegram_preview"]


def test_runner_json_cli_with_fixture_path():
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        result = run_cli("--json", "--dry-run", "--wallet", "", "--env-file", "__missing_env_file__", snapshot_file=path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["snapshot_written"] is False
    assert payload["usable_for_bankroll"] is False
    assert payload["digest"]["latest"]["query_status"] == "NEEDS_MANUAL_WALLET_INPUT"


# --- Traders activity profile integration tests ---

def _fake_traders_activity_summary_ok() -> dict:
    return {
        "ok": True,
        "generated_at": "2026-05-22T08:00:00Z",
        "cohort_mode": "local-registry",
        "cohort_warning": "local-registry/union may include discovered or historical registry wallets.",
        "n_wallets": 5,
        "lane_counts": {"REVIEW_REQUIRED": 3, "COMPARABLE_CANDIDATE": 2},
        "query_status_counts": {"ok_complete": 4, "ok_capped": 1},
        "capped_wallets": 1,
        "n_failures": 0,
        "comparable_candidates": ["ColdMath", "Entire-Hood"],
    }


def test_traders_activity_summary_disabled_by_default(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert result["traders_activity"]["ok"] is False
    assert result["traders_activity"]["error"] == "disabled"


def test_traders_activity_summary_fail_open_on_exception(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    monkeypatch.setattr(module, "_TAP_AVAILABLE", True)
    monkeypatch.setattr(module, "_tap", None)  # force module_not_available path

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--traders-activity-profile", "--snapshot-file", str(path)])
        result = module.build_run(args)

    # digest should still succeed
    assert result["usable_for_bankroll"] is False
    ta = result["traders_activity"]
    assert ta["ok"] is False
    assert "error" in ta


def test_traders_activity_summary_returns_ok_with_mock(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    expected = _fake_traders_activity_summary_ok()
    monkeypatch.setattr(module, "build_traders_activity_summary", lambda args: expected)

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--traders-activity-profile", "--snapshot-file", str(path)])
        result = module.build_run(args)

    ta = result["traders_activity"]
    assert ta["ok"] is True
    assert ta["n_wallets"] == 5
    assert ta["comparable_candidates"] == ["ColdMath", "Entire-Hood"]


def test_render_traders_activity_telegram_disabled():
    module = load_tool()
    section = module.render_traders_activity_telegram({"ok": False, "error": "disabled"})
    assert section == ""


def test_render_traders_activity_telegram_error():
    module = load_tool()
    section = module.render_traders_activity_telegram({"ok": False, "error": "connection timeout"})
    assert "🔬" in section
    assert "Error" in section
    assert "connection timeout" in section


def test_render_traders_activity_telegram_ok():
    module = load_tool()
    section = module.render_traders_activity_telegram(_fake_traders_activity_summary_ok())
    assert "🔬" in section
    assert "Wallets: 5" in section
    assert "COMPARABLE_CANDIDATE=2" in section
    assert "ColdMath" in section
    assert "LOG_ONLY" in section
    assert "local-registry" in section


def test_build_run_with_traders_activity_extends_preview(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    monkeypatch.setattr(module, "build_traders_activity_summary", lambda args: _fake_traders_activity_summary_ok())

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--traders-activity-profile", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert "🔬" in result["telegram_preview"]
    assert "Wallets: 5" in result["telegram_preview"]
    assert "📊" in result["telegram_preview"]  # original digest header still present


def test_build_run_without_traders_activity_flag_no_section(monkeypatch):
    module = load_tool()
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args(["--dry-run", "--snapshot-file", str(path)])
        result = module.build_run(args)

    assert "🔬" not in result["telegram_preview"]
    assert "Traders Activity" not in result["telegram_preview"]


def test_traders_activity_telegram_send_uses_extended_preview(monkeypatch):
    module = load_tool()
    calls = []
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())
    monkeypatch.setattr(module, "build_traders_activity_summary", lambda args: _fake_traders_activity_summary_ok())
    monkeypatch.setattr(
        module.daily_bot_digest,
        "send_telegram_manual",
        lambda message: calls.append(message) or {"sent": True, "reason": "sent"},
    )

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        args = module.parse_args([
            "--dry-run", "--send-telegram-manual", "--traders-activity-profile",
            "--snapshot-file", str(path),
        ])
        result = module.build_run(args)

    assert len(calls) == 1
    assert calls[0] == result["telegram_preview"]
    assert "🔬" in calls[0]


def test_bot_py_daily_digest_command_includes_traders_activity_flag():
    """Verify bot.py's maybe_send_daily_bot_digest command activates --traders-activity-profile."""
    bot_src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")
    func_start = bot_src.find("def maybe_send_daily_bot_digest(")
    assert func_start != -1, "maybe_send_daily_bot_digest not found in bot.py"
    func_end = bot_src.find("\ndef ", func_start + 1)
    func_body = bot_src[func_start:func_end] if func_end != -1 else bot_src[func_start:]
    assert "--traders-activity-profile" in func_body, (
        "maybe_send_daily_bot_digest must pass --traders-activity-profile to the daily digest script"
    )


def test_traders_activity_constants_cover_full_cohort():
    """Max wallets must be enough to cover all traders in local-registry cohort (~44)."""
    module = load_tool()
    assert module.TRADERS_ACTIVITY_MAX_WALLETS >= 44


def test_traders_activity_snapshot_not_written_in_dry_run(monkeypatch, tmp_path):
    module = load_tool()
    snapshot_calls = []
    monkeypatch.setattr(module.leaderboard_pnl_snapshot, "build_snapshot", lambda args: snapshot())

    def fake_build_payload(args):
        return {
            "generated_at": "2026-05-22T08:00:00Z",
            "summary": {"n_wallets": 3, "lane_counts": {}, "query_status_counts": {}, "capped_wallets": 0},
            "traders": [],
            "cohort": {"cohort_mode": "local-registry", "cohort_warning": None},
        }

    def fake_write_snapshot(payload, snapshot_dir):
        snapshot_calls.append(snapshot_dir)
        return tmp_path / "snap.json"

    if module._TAP_AVAILABLE and module._tap is not None:
        monkeypatch.setattr(module._tap, "build_payload", fake_build_payload)
        monkeypatch.setattr(module._tap, "write_snapshot", fake_write_snapshot)

    path = tmp_path / "leaderboard_pnl_snapshots.jsonl"
    args = module.parse_args(["--dry-run", "--traders-activity-profile", "--snapshot-file", str(path)])
    module.build_run(args)

    assert snapshot_calls == [], "write_snapshot must NOT be called in dry-run mode"
