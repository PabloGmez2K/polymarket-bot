"""
truth_pipeline_fetcher.py — Fetcher standalone de temperatura observada (Open-Meteo Archive).

Fase 1A.2 del Truth Pipeline. Solo stdlib + urllib. No importa bot.py.
No escribe en DB ni en archivos runtime. Solo observación/diagnóstico.

Uso:
    python tools/truth_pipeline_fetcher.py --city Paris --date 2026-05-01 --json
    python tools/truth_pipeline_fetcher.py --city Paris --date 2026-05-01 --dry-run --json

Regla de quality:
    - "preliminary": (date.today() - target_date).days < FINAL_QUALITY_AFTER_DAYS (14)
      Los datos de Open-Meteo Archive para fechas recientes pueden aún estar sujetos
      a corrección; se consideran definitivos solo tras 14 días de la fecha objetivo.
    - "final": (date.today() - target_date).days >= FINAL_QUALITY_AFTER_DAYS (14)
    - "missing": la API devolvió None o el campo temperature_2m_max no está presente.

Exit codes:
    0 — ok o dry_run
    1 — city_not_found, date_not_available, api_error
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

# ─── Constantes ──────────────────────────────────────────────────────────────

ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Un dato se considera "final" solo cuando han pasado al menos este número de días
# desde la fecha objetivo. Por debajo → "preliminary" (Open-Meteo puede aún corregir).
# Regla canónica Fase 1: target_date + 14 días.
FINAL_QUALITY_AFTER_DAYS = 14

REQUEST_TIMEOUT_SECONDS = 15

# ─── Mapping ciudad → coordenadas ─────────────────────────────────────────────
# Coordenadas copiadas y aisladas de RESOLUTION_STATIONS en bot.py.
# Standalone: no importa bot.py. Alineadas con las estaciones de resolución
# que usa Polymarket para cada ciudad.
CITY_COORDS: dict[str, dict[str, float]] = {
    "Seoul":          {"lat": 37.5665,  "lon": 126.9780},
    "London":         {"lat": 51.5048,  "lon":   0.0495},
    "Tel Aviv":       {"lat": 32.0114,  "lon":  34.8867},
    "Shanghai":       {"lat": 31.1443,  "lon": 121.8083},
    "Tokyo":          {"lat": 35.5494,  "lon": 139.7798},
    "New York City":  {"lat": 40.7772,  "lon": -73.8726},
    "Beijing":        {"lat": 40.0799,  "lon": 116.6031},
    "Hong Kong":      {"lat": 22.3080,  "lon": 113.9185},
    "Singapore":      {"lat":  1.3502,  "lon": 103.9940},
    "Toronto":        {"lat": 43.6772,  "lon": -79.6306},
    "Chicago":        {"lat": 41.9742,  "lon": -87.9073},
    "Wellington":     {"lat":-41.3272,  "lon": 174.8053},
    "Munich":         {"lat": 48.3538,  "lon":  11.7861},
    "Warsaw":         {"lat": 52.1657,  "lon":  20.9671},
    "Ankara":         {"lat": 40.1281,  "lon":  32.9951},
    "Atlanta":        {"lat": 33.6407,  "lon": -84.4277},
    "Shenzhen":       {"lat": 22.6393,  "lon": 113.8107},
    "Paris":          {"lat": 49.0097,  "lon":   2.5479},
    "Buenos Aires":   {"lat":-34.8222,  "lon": -58.5358},
    "Miami":          {"lat": 25.7954,  "lon": -80.2901},
    "Madrid":         {"lat": 40.4936,  "lon":  -3.5668},
    "Seattle":        {"lat": 47.4499,  "lon":-122.3118},
    "Dallas":         {"lat": 32.8459,  "lon": -96.8510},
    "Lucknow":        {"lat": 26.7606,  "lon":  80.8893},
    "Sao Paulo":      {"lat":-23.4355,  "lon": -46.4730},
    "Taipei":         {"lat": 25.0777,  "lon": 121.2330},
    "Milan":          {"lat": 45.6306,  "lon":   8.7281},
    "Chongqing":      {"lat": 29.7123,  "lon": 106.6519},
    "Chengdu":        {"lat": 30.5737,  "lon": 103.9415},
    "Wuhan":          {"lat": 30.7748,  "lon": 114.2137},
    "Houston":        {"lat": 29.9902,  "lon": -95.3368},
    "Jakarta":        {"lat": -6.2666,  "lon": 106.8906},
    "Kuala Lumpur":   {"lat":  2.7456,  "lon": 101.7099},
    "Moscow":         {"lat": 55.9726,  "lon":  37.4146},
    "Amsterdam":      {"lat": 52.3105,  "lon":   4.7683},
    "Jeddah":         {"lat": 21.6796,  "lon":  39.1565},
    "Istanbul":       {"lat": 40.9769,  "lon":  28.8147},
    "Helsinki":       {"lat": 60.3172,  "lon":  24.9633},
    "Busan":          {"lat": 35.1795,  "lon": 128.9380},
}


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _build_url(lat: float, lon: float, date_iso: str) -> str:
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "start_date": date_iso,
        "end_date": date_iso,
        "daily": "temperature_2m_max",
        "timezone": "UTC",
    })
    return f"{ARCHIVE_BASE_URL}?{params}"


def _determine_quality(date_iso: str, observed_high_c: float | None) -> str:
    if observed_high_c is None:
        return "missing"
    try:
        target = date.fromisoformat(date_iso)
    except ValueError:
        return "missing"
    delta = (date.today() - target).days
    if delta < FINAL_QUALITY_AFTER_DAYS:
        return "preliminary"
    return "final"


def _fetch_archive(url: str) -> dict:
    """Hace la llamada HTTP al archive de Open-Meteo. Retorna parsed JSON."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─── Función pública ──────────────────────────────────────────────────────────

def fetch_observed_high(city: str, date_iso: str, dry_run: bool = False) -> dict:
    """
    Obtiene la temperatura máxima observada para una ciudad y fecha.

    En dry_run=True no hace llamada de red: devuelve url + status=dry_run.
    """
    coords = CITY_COORDS.get(city)
    if coords is None:
        return {
            "city": city,
            "date": date_iso,
            "status": "city_not_found",
            "error": f"City '{city}' not in CITY_COORDS mapping",
        }

    lat = coords["lat"]
    lon = coords["lon"]
    url = _build_url(lat, lon, date_iso)

    if dry_run:
        return {
            "city": city,
            "date": date_iso,
            "latitude": lat,
            "longitude": lon,
            "url": url,
            "status": "dry_run",
            "source": "open_meteo_archive",
            "preview": {
                "endpoint": ARCHIVE_BASE_URL,
                "params": {
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": date_iso,
                    "end_date": date_iso,
                    "daily": "temperature_2m_max",
                    "timezone": "UTC",
                },
            },
        }

    fetched_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        data = _fetch_archive(url)
    except urllib.error.HTTPError as exc:
        status = "api_error"
        error_detail = f"HTTP {exc.code}: {exc.reason}"
        if exc.code == 429:
            error_detail = "HTTP 429: rate limited by Open-Meteo"
        return {
            "city": city,
            "date": date_iso,
            "latitude": lat,
            "longitude": lon,
            "url": url,
            "status": status,
            "source": "open_meteo_archive",
            "error": error_detail,
            "fetched_at_utc": fetched_at_utc,
        }
    except urllib.error.URLError as exc:
        return {
            "city": city,
            "date": date_iso,
            "latitude": lat,
            "longitude": lon,
            "url": url,
            "status": "api_error",
            "source": "open_meteo_archive",
            "error": f"URL error: {exc.reason}",
            "fetched_at_utc": fetched_at_utc,
        }

    # Extraer temperature_2m_max del payload
    daily = data.get("daily", {})
    temps = daily.get("temperature_2m_max")

    if not temps:
        return {
            "city": city,
            "date": date_iso,
            "latitude": lat,
            "longitude": lon,
            "url": url,
            "status": "date_not_available",
            "source": "open_meteo_archive",
            "quality": "missing",
            "error": "temperature_2m_max not present in response",
            "fetched_at_utc": fetched_at_utc,
        }

    observed_high_c = temps[0] if temps else None

    if observed_high_c is None:
        return {
            "city": city,
            "date": date_iso,
            "latitude": lat,
            "longitude": lon,
            "url": url,
            "status": "date_not_available",
            "source": "open_meteo_archive",
            "quality": "missing",
            "error": "temperature_2m_max value is None for requested date",
            "fetched_at_utc": fetched_at_utc,
        }

    quality = _determine_quality(date_iso, observed_high_c)

    return {
        "city": city,
        "date": date_iso,
        "latitude": lat,
        "longitude": lon,
        "observed_high_c": observed_high_c,
        "source": "open_meteo_archive",
        "quality": quality,
        "status": "ok",
        "url": url,
        "fetched_at_utc": fetched_at_utc,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetcher Open-Meteo Archive — temperatura máxima observada"
    )
    parser.add_argument("--city", required=True, help="Nombre de la ciudad (ej: Paris)")
    parser.add_argument(
        "--date", required=True,
        help="Fecha ISO YYYY-MM-DD (ej: 2026-05-01)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Imprime resultado en JSON (por defecto siempre activo en CLI)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="No hace llamada de red; imprime URL y preview estructurado",
    )
    args = parser.parse_args()

    result = fetch_observed_high(
        city=args.city,
        date_iso=args.date,
        dry_run=args.dry_run,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    ok_statuses = {"ok", "dry_run"}
    return 0 if result.get("status") in ok_statuses else 1


if __name__ == "__main__":
    sys.exit(main())
