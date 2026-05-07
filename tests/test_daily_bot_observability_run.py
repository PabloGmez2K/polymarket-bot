from __future__ import annotations

import importlib.util
import json
import shutil
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


def test_runner_json_cli_with_fixture_path():
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        result = run_cli("--json", "--dry-run", "--wallet", "", "--env-file", "__missing_env_file__", snapshot_file=path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["snapshot_written"] is False
    assert payload["usable_for_bankroll"] is False
    assert payload["digest"]["latest"]["query_status"] == "NEEDS_MANUAL_WALLET_INPUT"
