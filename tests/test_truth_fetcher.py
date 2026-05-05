"""
tests/test_truth_fetcher.py — Tests unitarios para truth_pipeline_fetcher.py

Todos los tests usan mocks de red. No se hacen llamadas reales a Open-Meteo.
"""
from __future__ import annotations

import json
import sys
import unittest
import urllib.error
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch

# Asegurar que tools/ está en el path sin importar bot.py
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from truth_pipeline_fetcher import (
    CITY_COORDS,
    FINAL_QUALITY_AFTER_DAYS,
    fetch_observed_high,
    _determine_quality,
)


def _make_archive_response(temp_value):
    """Construye payload JSON de Open-Meteo con temperature_2m_max dado."""
    payload = {
        "latitude": 49.0,
        "longitude": 2.5,
        "daily": {
            "time": ["2026-05-01"],
            "temperature_2m_max": [temp_value],
        },
    }
    return BytesIO(json.dumps(payload).encode())


class TestFetcherCityKnown(unittest.TestCase):
    """Test 1: ciudad conocida → observed_high_c correcto."""

    def test_paris_returns_correct_temp(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "latitude": 49.0,
            "longitude": 2.5,
            "daily": {
                "time": ["2025-01-01"],
                "temperature_2m_max": [12.5],
            },
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_observed_high("Paris", "2025-01-01")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["observed_high_c"], 12.5)
        self.assertEqual(result["city"], "Paris")
        self.assertEqual(result["date"], "2025-01-01")
        self.assertEqual(result["source"], "open_meteo_archive")
        self.assertIn("latitude", result)
        self.assertIn("longitude", result)
        self.assertIn("url", result)
        self.assertIn("fetched_at_utc", result)


class TestFetcherCityNotFound(unittest.TestCase):
    """Test 2: ciudad sin mapping → status=city_not_found."""

    def test_unknown_city(self):
        result = fetch_observed_high("Atlantis", "2026-05-01")
        self.assertEqual(result["status"], "city_not_found")
        self.assertIn("error", result)
        self.assertEqual(result["city"], "Atlantis")

    def test_unknown_city_no_network_call(self):
        with patch("urllib.request.urlopen") as mock_url:
            fetch_observed_high("Neverland", "2026-05-01")
            mock_url.assert_not_called()


class TestFetcherRateLimit(unittest.TestCase):
    """Test 3: API rate limit 429 → status=api_error con error claro."""

    def test_rate_limit_429(self):
        http_err = urllib.error.HTTPError(
            url="http://example.com", code=429, msg="Too Many Requests",
            hdrs=None, fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=http_err):
            result = fetch_observed_high("Paris", "2025-01-01")

        self.assertEqual(result["status"], "api_error")
        self.assertIn("429", result.get("error", ""))
        self.assertIn("rate limit", result.get("error", "").lower())


class TestFetcherTimeout(unittest.TestCase):
    """Test 4: Timeout → status=api_error."""

    def test_timeout(self):
        import socket
        url_err = urllib.error.URLError(reason=socket.timeout("timed out"))
        with patch("urllib.request.urlopen", side_effect=url_err):
            result = fetch_observed_high("Tokyo", "2025-01-01")

        self.assertEqual(result["status"], "api_error")
        self.assertIn("error", result)


class TestFetcherMissingField(unittest.TestCase):
    """Test 5: Payload sin temperature_2m_max → status=date_not_available."""

    def test_missing_temperature_field(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "latitude": 49.0,
            "longitude": 2.5,
            "daily": {
                "time": ["2026-05-01"],
                # temperature_2m_max ausente intencionalmente
            },
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_observed_high("Paris", "2026-05-01")

        self.assertEqual(result["status"], "date_not_available")
        self.assertEqual(result["quality"], "missing")


class TestFetcherNoneValue(unittest.TestCase):
    """Test 6: API devuelve None para el día → status=date_not_available + quality=missing."""

    def test_none_temperature_value(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "latitude": 49.0,
            "longitude": 2.5,
            "daily": {
                "time": ["2026-05-01"],
                "temperature_2m_max": [None],
            },
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_observed_high("Paris", "2026-05-01")

        self.assertEqual(result["status"], "date_not_available")
        self.assertEqual(result["quality"], "missing")


class TestFetcherQualityPreliminary(unittest.TestCase):
    """Test 7: Fecha reciente (< FINAL_QUALITY_AFTER_DAYS días) → quality=preliminary."""

    def test_recent_date_is_preliminary(self):
        # Siempre dentro de la ventana preliminary: FINAL_QUALITY_AFTER_DAYS - 1 días atrás
        recent_date = (date.today() - timedelta(days=FINAL_QUALITY_AFTER_DAYS - 1)).isoformat()

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "latitude": 49.0,
            "longitude": 2.5,
            "daily": {
                "time": [recent_date],
                "temperature_2m_max": [25.0],
            },
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_observed_high("Paris", recent_date)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["quality"], "preliminary")

    def test_determine_quality_preliminary(self):
        # 1 día atrás: siempre < FINAL_QUALITY_AFTER_DAYS (14)
        recent = (date.today() - timedelta(days=1)).isoformat()
        self.assertEqual(_determine_quality(recent, 20.0), "preliminary")

    def test_determine_quality_boundary_preliminary(self):
        # FINAL_QUALITY_AFTER_DAYS - 1 días: aún preliminary
        boundary = (date.today() - timedelta(days=FINAL_QUALITY_AFTER_DAYS - 1)).isoformat()
        self.assertEqual(_determine_quality(boundary, 20.0), "preliminary")


class TestFetcherQualityFinal(unittest.TestCase):
    """Test 8: Fecha histórica → quality=final."""

    def test_old_date_is_final(self):
        old_date = "2025-01-01"

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "latitude": 49.0,
            "longitude": 2.5,
            "daily": {
                "time": [old_date],
                "temperature_2m_max": [8.3],
            },
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_observed_high("Paris", old_date)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["quality"], "final")

    def test_determine_quality_final(self):
        # 2025-01-01 siempre es >= FINAL_QUALITY_AFTER_DAYS (14) días en el pasado
        old = "2025-01-01"
        self.assertEqual(_determine_quality(old, 10.0), "final")

    def test_determine_quality_boundary_final(self):
        # Exactamente FINAL_QUALITY_AFTER_DAYS días atrás → final
        boundary = (date.today() - timedelta(days=FINAL_QUALITY_AFTER_DAYS)).isoformat()
        self.assertEqual(_determine_quality(boundary, 10.0), "final")

    def test_determine_quality_missing_when_none(self):
        self.assertEqual(_determine_quality("2025-01-01", None), "missing")


class TestFetcherDryRun(unittest.TestCase):
    """Test 9: --dry-run → no hace llamada de red y devuelve url preview."""

    def test_dry_run_no_network_call(self):
        with patch("urllib.request.urlopen") as mock_url:
            result = fetch_observed_high("Seoul", "2026-05-01", dry_run=True)
            mock_url.assert_not_called()

        self.assertEqual(result["status"], "dry_run")
        self.assertIn("url", result)
        self.assertIn("preview", result)
        self.assertEqual(result["city"], "Seoul")
        self.assertEqual(result["date"], "2026-05-01")

    def test_dry_run_city_not_found_still_short_circuits(self):
        with patch("urllib.request.urlopen") as mock_url:
            result = fetch_observed_high("Atlantis", "2026-05-01", dry_run=True)
            mock_url.assert_not_called()
        self.assertEqual(result["status"], "city_not_found")


class TestFetcherNoImportBot(unittest.TestCase):
    """Test 10: El módulo no importa bot.py ni módulos de trading core."""

    def test_no_bot_import(self):
        fetcher_path = os.path.join(
            os.path.dirname(__file__), "..", "tools", "truth_pipeline_fetcher.py"
        )
        with open(fetcher_path, "r", encoding="utf-8") as f:
            source = f.read()

        forbidden = [
            "import bot",
            "from bot",
            "execute_trade",
            "manage_positions",
            "intra_cycle_sl_check",
            "import requests",
            "import httpx",
            "import aiohttp",
        ]
        for pattern in forbidden:
            self.assertNotIn(
                pattern, source,
                msg=f"Forbidden pattern found in fetcher: '{pattern}'",
            )


if __name__ == "__main__":
    unittest.main()
