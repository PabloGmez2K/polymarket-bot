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
        encoding="utf-8",
        errors="replace",
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


def test_telegram_preview_mixed_day_worse_avoids_global_improves_copy():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(
            path,
            [
                snapshot(
                    captured_at_utc="2026-05-22T18:00:00Z",
                    pnl_day=0.0,
                    pnl_week=1.0,
                    pnl_month=2.0,
                    pnl_all=-30.0,
                ),
                snapshot(
                    captured_at_utc="2026-05-22T20:00:00Z",
                    pnl_day=-1.43,
                    pnl_week=2.0,
                    pnl_month=3.0,
                    pnl_all=-29.0,
                ),
            ],
        )
        digest = module.build_digest(path)

    preview = digest["telegram_preview"]
    assert digest["trend_label"] == "improving"
    assert digest["deltas"]["day_delta"] == -1.43
    assert digest["deltas"]["week_delta"] == 1.0
    assert "Balance mixto frente al ultimo registro valido." in preview
    assert "Dia empeora; no interpretarlo como mejora diaria." in preview
    assert "El bot mejora" not in preview


def test_telegram_preview_clear_positive_and_negative_keep_direct_copy():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        positive = tmp_dir / "positive.jsonl"
        write_jsonl(
            positive,
            [
                snapshot(captured_at_utc="2026-05-22T18:00:00Z", pnl_day=0.0, pnl_week=1.0, pnl_month=2.0, pnl_all=3.0),
                snapshot(captured_at_utc="2026-05-22T20:00:00Z", pnl_day=1.0, pnl_week=2.0, pnl_month=3.0, pnl_all=4.0),
            ],
        )
        positive_digest = module.build_digest(positive)

        negative = tmp_dir / "negative.jsonl"
        write_jsonl(
            negative,
            [
                snapshot(captured_at_utc="2026-05-22T18:00:00Z", pnl_day=1.0, pnl_week=2.0, pnl_month=3.0, pnl_all=4.0),
                snapshot(captured_at_utc="2026-05-22T20:00:00Z", pnl_day=0.0, pnl_week=1.0, pnl_month=2.0, pnl_all=3.0),
            ],
        )
        negative_digest = module.build_digest(negative)

    assert "Mejora frente" in positive_digest["telegram_preview"]
    assert "Balance mixto" not in positive_digest["telegram_preview"]
    assert "Empeora frente" in negative_digest["telegram_preview"]
    assert "Balance mixto" not in negative_digest["telegram_preview"]


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

    assert "usable_for_bankroll=false" in digest["message"]
    assert "Observability only." in digest["message"]
    assert "No BANKROLL increase." in digest["message"]
    assert "No BUY/SELL/SKIP." in digest["message"]
    assert "No Fase C." in digest["message"]
    assert "Mensaje informativo." in digest["telegram_preview"]
    assert "No cambia bankroll" in digest["telegram_preview"]
    assert "no compra, no vende" in digest["telegram_preview"]
    assert "no activa Fase C" in digest["telegram_preview"]


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
    assert "📊 <b>RESUMEN DIARIO DEL BOT</b>" in result.stdout
    assert "Volumen operado según leaderboard" in result.stdout
    assert "No cambia bankroll" in result.stdout
    assert "sent" not in result.stdout.lower()
    assert "TELEGRAM_BOT_TOKEN" not in result.stdout


def test_telegram_preview_is_human_readable_and_hides_technical_fields():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(
            path,
            [
                snapshot(captured_at_utc="2026-05-07T18:00:00Z"),
                snapshot(captured_at_utc="2026-05-07T19:00:00Z"),
            ],
        )
        digest = module.build_digest(path)

    preview = digest["telegram_preview"]
    for expected in (
        "📊 <b>RESUMEN DIARIO DEL BOT</b>",
        "🕒 <b>Actualización</b>",
        "07/05/2026 21:00 hora España",
        "💰 <b>Evolución P&amp;L</b>",
        "📈 <b>Tendencia</b>",
        "🔄 <b>Actividad</b>",
        "🧭 <b>Lectura rápida</b>",
        "ℹ️ <b>Nota</b>",
        "• Día: +1.39$",
        "• Semana: +4.55$",
        "• Mes: +2.83$",
        "• Total histórico: -29.81$",
        "• Día: sin cambios",
        "• Semana: sin cambios",
        "• Mes: sin cambios",
        "• Total: sin cambios",
        "Mensaje informativo. No cambia bankroll, no compra, no vende y no activa Fase C.",
    ):
        assert expected in preview
    assert "2026-05-07T19:00:00Z" not in preview
    for hidden in (
        "source_quality=external_opaque",
        "dashboard_equivalent=false",
        "usable_for_digest=true",
        "usable_for_trend=true",
        "usable_for_bankroll=false",
        "query_status",
    ):
        assert hidden not in preview


def test_telegram_preview_failed_snapshot_uses_human_error_copy():
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

    preview = digest["telegram_preview"]
    assert "No se pudo actualizar el dato en este intento." in preview
    assert "Último dato válido: 07/05/2026 20:00 hora España." in preview
    assert "query_status=failed" not in preview
    assert "query_status: failed" not in preview


def test_telegram_preview_without_previous_snapshot_uses_human_copy():
    module = load_tool()
    with local_tmp_dir() as tmp_dir:
        path = tmp_dir / "leaderboard_pnl_snapshots.jsonl"
        write_jsonl(path, [snapshot()])
        digest = module.build_digest(path)

    assert "Aún no hay comparación disponible." in digest["telegram_preview"]


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

    with local_tmp_dir() as tmp_dir:
        monkeypatch.chdir(tmp_dir)
        result = module.send_telegram_manual("DAILY BOT DIGEST\nusable_for_bankroll=false")

    assert result["sent"] is False
    assert result["reason"] == "TELEGRAM_NOT_CONFIGURED"
    assert "TELEGRAM_CHAT_ID" in result["missing_env"]


def test_manual_telegram_send_reads_telegram_token_from_env_file(monkeypatch):
    module = load_tool()
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with local_tmp_dir() as tmp_dir:
        (tmp_dir / ".env").write_text(
            "TELEGRAM_TOKEN=file-token\nTELEGRAM_CHAT_ID=987654321\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_dir)
        bot_token, chat_id, token_env, missing = module.resolve_telegram_env()

    assert bot_token == "file-token"
    assert chat_id == "987654321"
    assert token_env == ".env:TELEGRAM_TOKEN"
    assert missing == []


def test_manual_telegram_send_reads_bot_token_from_env_file(monkeypatch):
    module = load_tool()
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with local_tmp_dir() as tmp_dir:
        (tmp_dir / ".env").write_text(
            'TELEGRAM_BOT_TOKEN="bot-token-from-file"\nTELEGRAM_CHAT_ID="987654321"\n',
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_dir)
        bot_token, chat_id, token_env, missing = module.resolve_telegram_env()

    assert bot_token == "bot-token-from-file"
    assert chat_id == "987654321"
    assert token_env == ".env:TELEGRAM_BOT_TOKEN"
    assert missing == []


def test_manual_telegram_loaded_env_vars_take_priority_over_env_file(monkeypatch):
    module = load_tool()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "loaded-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111222333")
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    with local_tmp_dir() as tmp_dir:
        (tmp_dir / ".env").write_text(
            "TELEGRAM_BOT_TOKEN=file-token\nTELEGRAM_CHAT_ID=987654321\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_dir)
        bot_token, chat_id, token_env, missing = module.resolve_telegram_env()

    assert bot_token == "loaded-token"
    assert chat_id == "111222333"
    assert token_env == "TELEGRAM_BOT_TOKEN"
    assert missing == []


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
    body = json.loads(captured["body"])
    assert body["parse_mode"] == "HTML"
    assert body["text"] == message
    assert "secret-token" in captured["url"]
    assert "123456789" in captured["body"]
    assert "secret-token" not in json.dumps(result)
    assert "123456789" not in json.dumps(result)


def test_manual_telegram_send_html_parse_mode_falls_back_to_plain_text(monkeypatch):
    module = load_tool()
    requests = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout):
        requests.append(json.loads(req.data.decode("utf-8")))
        if len(requests) == 1:
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", hdrs=None, fp=None)
        return Response()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")
    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    result = module.send_telegram_manual("📊 <b>RESUMEN</b>")

    assert result["sent"] is True
    assert result["reason"] == "sent_plain_text_fallback"
    assert requests[0]["parse_mode"] == "HTML"
    assert requests[0]["text"] == "📊 <b>RESUMEN</b>"
    assert "parse_mode" not in requests[1]
    assert requests[1]["text"] == "📊 RESUMEN"


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
