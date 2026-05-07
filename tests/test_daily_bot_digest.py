from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import urllib.error
import uuid
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "daily_bot_digest.py"


@contextmanager
def local_tmp_dir():
    path = REPO_ROOT / f"_tmp_daily_bot_digest_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def load_tool():
    spec = importlib.util.spec_from_file_location("daily_bot_digest", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def snapshot(**extra) -> dict:
    row = {
        "captured_at_utc": "2026-05-07T19:51:33Z",
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
        "query_status": "ok",
    }
    row.update(extra)
    return row


def run_cli(*args: str, snapshot_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), *args, "--snapshot-file", str(snapshot_file)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_zero_snapshots_digest_indicates_no_data():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        digest = module.build_digest(tmp_dir / "missing.jsonl")

    assert digest["has_data"] is False
    assert digest["snapshot_count"] == 0
    assert digest["trend_label"] == "unknown"
    assert "No leaderboard P&L snapshot data." in digest["message"]
    assert "usable_for_bankroll=false" in digest["message"]
    assert "Observability only." in digest["message"]


def test_one_snapshot_has_unknown_trend_and_no_previous_snapshot():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(path, [snapshot()])
        digest = module.build_digest(path)

    assert digest["snapshot_count"] == 1
    assert digest["previous"] is None
    assert digest["trend_label"] == "unknown"
    assert digest["deltas"] == {
        "day_delta": None,
        "week_delta": None,
        "month_delta": None,
        "all_delta": None,
    }
    assert "No previous valid snapshot yet" in digest["message"]
    assert "trend_label=unknown" in digest["message"]


def test_two_snapshots_calculates_deltas_correctly():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(
            path,
            [
                snapshot(
                    captured_at_utc="2026-05-07T18:00:00Z",
                    pnl_day=1.0,
                    pnl_week=2.0,
                    pnl_month=3.0,
                    pnl_all=4.0,
                ),
                snapshot(
                    captured_at_utc="2026-05-07T19:00:00Z",
                    pnl_day=1.5,
                    pnl_week=1.0,
                    pnl_month=3.0,
                    pnl_all=5.0,
                ),
            ],
        )
        digest = module.build_digest(path)

    assert digest["deltas"]["day_delta"] == 0.5
    assert digest["deltas"]["week_delta"] == -1.0
    assert digest["deltas"]["month_delta"] == 0.0
    assert digest["deltas"]["all_delta"] == 1.0
    assert digest["trend_label"] == "improving"


def test_digest_skips_failed_snapshot_between_valid_snapshots():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(
            path,
            [
                snapshot(
                    captured_at_utc="2026-05-07T18:00:00Z",
                    pnl_day=1.0,
                    pnl_week=2.0,
                    pnl_month=3.0,
                    pnl_all=4.0,
                ),
                snapshot(
                    captured_at_utc="2026-05-07T18:30:00Z",
                    query_status="failed",
                    pnl_day=None,
                    pnl_week=None,
                    pnl_month=None,
                    pnl_all=None,
                ),
                snapshot(
                    captured_at_utc="2026-05-07T19:00:00Z",
                    pnl_day=1.5,
                    pnl_week=1.0,
                    pnl_month=3.0,
                    pnl_all=5.0,
                ),
            ],
        )
        digest = module.build_digest(path)

    assert digest["snapshot_count"] == 3
    assert digest["valid_snapshot_count"] == 2
    assert digest["previous"]["captured_at_utc"] == "2026-05-07T18:00:00Z"
    assert digest["deltas"]["day_delta"] == 0.5
    assert digest["deltas"]["week_delta"] == -1.0
    assert "previous_valid_captured_at_utc: 2026-05-07T18:00:00Z" in digest["message"]


def test_digest_latest_failed_shows_last_valid_without_trend():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(
            path,
            [
                snapshot(captured_at_utc="2026-05-07T18:00:00Z"),
                snapshot(
                    captured_at_utc="2026-05-07T19:00:00Z",
                    query_status="failed",
                    pnl_day=None,
                    pnl_week=None,
                    pnl_month=None,
                    pnl_all=None,
                ),
            ],
        )
        digest = module.build_digest(path)

    assert digest["latest"]["query_status"] == "failed"
    assert digest["latest_valid"]["captured_at_utc"] == "2026-05-07T18:00:00Z"
    assert digest["previous"] is None
    assert digest["trend_label"] == "unknown"
    assert "query_status: failed" in digest["message"]
    assert "last_valid_snapshot_captured_at_utc: 2026-05-07T18:00:00Z" in digest["message"]
    assert "usable_for_bankroll=false" in digest["message"]
    assert "Observability only." in digest["message"]


def test_digest_only_failed_has_no_valid_trend():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(
            path,
            [
                snapshot(
                    captured_at_utc="2026-05-07T19:00:00Z",
                    query_status="failed",
                    pnl_day=None,
                    pnl_week=None,
                    pnl_month=None,
                    pnl_all=None,
                ),
            ],
        )
        digest = module.build_digest(path)

    assert digest["valid_snapshot_count"] == 0
    assert digest["latest_valid"] is None
    assert digest["previous"] is None
    assert digest["trend_label"] == "unknown"
    assert digest["deltas"] == {
        "day_delta": None,
        "week_delta": None,
        "month_delta": None,
        "all_delta": None,
    }


def test_message_always_keeps_observability_only_and_no_bankroll():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(path, [snapshot()])
        digest = module.build_digest(path)

    for message in (digest["message"], digest["telegram_preview"]):
        assert "usable_for_bankroll=false" in message
        assert "Observability only." in message
        assert "No BANKROLL increase." in message
        assert "No BUY/SELL/SKIP." in message
        assert "No Fase C." in message


def test_volume_is_leaderboard_trading_volume_not_trade_count():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(path, [snapshot()])
        digest = module.build_digest(path)

    message = digest["message"]
    assert "Leaderboard trading volume:" in message
    assert "buy_count" not in message
    assert "trade_count" not in message
    assert digest["latest"]["volume_label"] == "leaderboard_trading_volume"


def test_json_cli_returns_latest_previous_deltas_and_message():
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(path, [snapshot()])
        result = run_cli("--json", "--dry-run", snapshot_file=path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["latest"]["captured_at_utc"] == "2026-05-07T19:51:33Z"
    assert payload["previous"] is None
    assert set(payload["deltas"]) == {"day_delta", "week_delta", "month_delta", "all_delta"}
    assert "DAILY BOT DIGEST" in payload["message"]


def test_telegram_preview_does_not_send_or_require_env_vars(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "must_not_be_read")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "must_not_be_read")
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(path, [snapshot()])
        result = run_cli("--telegram-preview", snapshot_file=path)

    assert result.returncode == 0, result.stderr
    assert "DAILY BOT DIGEST" in result.stdout
    assert "Leaderboard trading volume" in result.stdout
    assert "usable_for_bankroll=false" in result.stdout
    assert "sent" not in result.stdout.lower()
    assert "TELEGRAM_BOT_TOKEN" not in result.stdout


def test_manual_telegram_send_requires_explicit_flag(monkeypatch):
    module = load_tool()
    calls = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs: calls.append((args, kwargs)))

    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(path, [snapshot()])
        result = run_cli("--telegram-preview", snapshot_file=path)

    assert result.returncode == 0, result.stderr
    assert calls == []
    assert "secret-token" not in result.stdout
    assert "123456789" not in result.stdout


def test_manual_telegram_send_missing_env_returns_not_configured(monkeypatch):
    module = load_tool()
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    result = module.send_telegram_manual("DAILY BOT DIGEST\nusable_for_bankroll=false")

    assert result["sent"] is False
    assert result["reason"] == "TELEGRAM_NOT_CONFIGURED"
    assert "TELEGRAM_CHAT_ID" in result["missing_env"]


def test_manual_telegram_send_uses_existing_env_without_printing_secrets(monkeypatch):
    module = load_tool()
    captured = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["body"] = req.data.decode("utf-8")
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")
    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    message = "DAILY BOT DIGEST\nusable_for_bankroll=false\nObservability only."
    result = module.send_telegram_manual(message)

    assert result["sent"] is True
    assert result["reason"] == "sent"
    assert result["token_env_used"] == "TELEGRAM_BOT_TOKEN"
    assert result["http_code"] == 200
    assert "secret-token" in captured["url"]
    assert "123456789" in captured["body"]
    assert "secret-token" not in json.dumps(result)
    assert "123456789" not in json.dumps(result)


def test_manual_telegram_send_api_error_does_not_retry(monkeypatch):
    module = load_tool()
    calls = {"n": 0}

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        raise urllib.error.URLError("network down")

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")
    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    result = module.send_telegram_manual("DAILY BOT DIGEST\nusable_for_bankroll=false")

    assert calls["n"] == 1
    assert result["sent"] is False
    assert result["reason"] == "TELEGRAM_API_ERROR"
    assert "secret-token" not in json.dumps(result)
    assert "123456789" not in json.dumps(result)
