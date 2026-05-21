"""Tests focales para pnl_reconciliation_alert — hardening Telegram send."""

from __future__ import annotations

import importlib.util
import json
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "pnl_reconciliation_alert.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pnl_reconciliation_alert", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSendTelegram:
    def test_missing_env_returns_not_sent(self, monkeypatch):
        module = load_module()
        monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        result = module.send_telegram("test message")
        assert result["sent"] is False
        assert result["reason"] == "missing_telegram_env"

    def test_http_error_400_returns_not_sent_no_crash(self, monkeypatch):
        module = load_module()
        monkeypatch.setenv("TELEGRAM_TOKEN", "fake_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        exc = urllib.error.HTTPError(url="", code=400, msg="Bad Request", hdrs=None, fp=None)
        with patch.object(urllib.request, "urlopen", side_effect=exc):
            result = module.send_telegram("test <message> & entities > symbols")
        assert result["sent"] is False
        assert result["reason"] == "telegram_http_error"
        assert "400" in result.get("error_type", "")

    def test_url_error_returns_not_sent_no_crash(self, monkeypatch):
        module = load_module()
        monkeypatch.setenv("TELEGRAM_TOKEN", "fake_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        exc = urllib.error.URLError("connection timed out")
        with patch.object(urllib.request, "urlopen", side_effect=exc):
            result = module.send_telegram("test message")
        assert result["sent"] is False
        assert result["reason"] == "telegram_url_error"

    def test_generic_exception_returns_not_sent_no_crash(self, monkeypatch):
        module = load_module()
        monkeypatch.setenv("TELEGRAM_TOKEN", "fake_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        with patch.object(urllib.request, "urlopen", side_effect=RuntimeError("unexpected")):
            result = module.send_telegram("test message")
        assert result["sent"] is False
        assert result["reason"] == "telegram_exception"

    def test_success_returns_sent(self, monkeypatch):
        module = load_module()
        monkeypatch.setenv("TELEGRAM_TOKEN", "fake_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        with patch.object(urllib.request, "urlopen", return_value=MagicMock()):
            result = module.send_telegram("test message")
        assert result["sent"] is True
        assert result["reason"] == "sent"

    def test_no_parse_mode_html_in_payload(self, monkeypatch):
        """Verifica que parse_mode HTML no se incluye en el request."""
        module = load_module()
        monkeypatch.setenv("TELEGRAM_TOKEN", "fake_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["payload"] = json.loads(req.data.decode())
            return MagicMock()

        with patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            module.send_telegram("test message with <b>html</b> & entities > here")
        assert "parse_mode" not in captured.get("payload", {})
