#!/usr/bin/env python3
"""Fetch AviationWeather METAR observations as a LOG_ONLY measurement layer.

Standalone read-only tool. It never imports bot.py, never writes runtime state,
and does not authorize trading, promotion, scheduler, BANKROLL, or canonical
source changes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "metar_shadow"
AVIATIONWEATHER_METAR_URL = "https://aviationweather.gov/api/data/metar"
MIN_OBS_PER_DAY = 12
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY METAR/AviationWeather measurement layer. This does not authorize "
    "BUY/SELL/SKIP, promotion, scheduler changes, env vars, DB writes, BANKROLL, "
    "Fase C, Truth Pipeline, or canonical source changes."
)

WAVE1_STATIONS: dict[str, dict[str, str]] = {
    "ZBAA": {"city": "Beijing", "tz": "Asia/Shanghai"},
    "ZSPD": {"city": "Shanghai", "tz": "Asia/Shanghai"},
    "ZSSS": {"city": "Shanghai", "tz": "Asia/Shanghai"},
    "RJTT": {"city": "Tokyo", "tz": "Asia/Tokyo"},
    "RJAA": {"city": "Tokyo", "tz": "Asia/Tokyo"},
    "OEJN": {"city": "Jeddah", "tz": "Asia/Riyadh"},
    "SABE": {"city": "Buenos Aires", "tz": "America/Argentina/Buenos_Aires"},
    "SAEZ": {"city": "Buenos Aires", "tz": "America/Argentina/Buenos_Aires"},
    "LTAC": {"city": "Ankara", "tz": "Europe/Istanbul"},
    "ZUCK": {"city": "Chongqing", "tz": "Asia/Shanghai"},
}

WAVE2_STATIONS: dict[str, dict[str, str]] = {
    "RKSI": {"city": "Seoul", "tz": "Asia/Seoul"},
    "WSSS": {"city": "Singapore", "tz": "Asia/Singapore"},
    "CYYZ": {"city": "Toronto", "tz": "America/Toronto"},
    "NZWN": {"city": "Wellington", "tz": "Pacific/Auckland"},
    "LEMD": {"city": "Madrid", "tz": "Europe/Madrid"},
    "LIMC": {"city": "Milan", "tz": "Europe/Rome"},
    "EDDM": {"city": "Munich", "tz": "Europe/Berlin"},
}

METAR_STATIONS: dict[str, dict[str, str]] = {
    **WAVE1_STATIONS,
    **WAVE2_STATIONS,
}

TZ_FALLBACK_OFFSETS = {
    "UTC": 0,
    "Asia/Shanghai": 8,
    "Asia/Tokyo": 9,
    "Asia/Riyadh": 3,
    "America/Argentina/Buenos_Aires": -3,
    "Europe/Istanbul": 3,
    "Asia/Seoul": 9,
    "Asia/Singapore": 8,
    "America/Toronto": -5,
    "Pacific/Auckland": 12,
    "Europe/Madrid": 1,
    "Europe/Rome": 1,
    "Europe/Berlin": 1,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def should_bypass_proxy_env() -> bool:
    poisoned_markers = ("127.0.0.1:9", "localhost:9")
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        value = os.getenv(name, "")
        if any(marker in value for marker in poisoned_markers):
            return True
    return False


def open_url(request: urllib.request.Request, timeout: int):
    if should_bypass_proxy_env():
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return opener.open(request, timeout=timeout)
    return urllib.request.urlopen(request, timeout=timeout)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def station_timezone(icao: str) -> str:
    return METAR_STATIONS.get(str(icao).upper(), {}).get("tz", "UTC")


def station_city(icao: str, city: str | None = None) -> str | None:
    return city or METAR_STATIONS.get(str(icao).upper(), {}).get("city")


def parse_metar_temperature(raw_metar: str) -> tuple[float | None, float | None]:
    """Parse METAR temperature/dewpoint token in Celsius.

    Supports tokens such as `24/18`, `M05/M08`, `05/M01`, and missing sides
    like `24//`. Returned values are not invented when the token is absent.
    """
    token = None
    for candidate in re.findall(r"(?<![A-Z0-9])(M?\d{2}|//)/(M?\d{2}|//|/)?(?![A-Z0-9])", str(raw_metar or "")):
        token = candidate
    if token is None:
        return None, None

    def _part(value: str) -> float | None:
        if value in ("//", "/", None, ""):
            return None
        if value.startswith("M"):
            return -float(value[1:])
        return float(value)

    return _part(token[0]), _part(token[1])


def get_timezone(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        offset = TZ_FALLBACK_OFFSETS.get(tz_name)
        if offset is None:
            return timezone.utc
        hours = int(offset)
        minutes = int(round((float(offset) - hours) * 60))
        return timezone(timedelta(hours=hours, minutes=minutes), name=tz_name)


def _parse_report_time(row: dict[str, Any]) -> datetime | None:
    for key in ("reportTime", "receiptTime", "obsTime"):
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            if key == "obsTime" and isinstance(value, (int, float)):
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            continue
    return None


def _row_temperature_c(row: dict[str, Any]) -> float | None:
    for key in ("temp", "temp_c", "temperature"):
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    raw = row.get("rawOb") or row.get("raw_text") or row.get("metar") or ""
    temp, _dewpoint = parse_metar_temperature(str(raw))
    return temp


def derive_daily_temperatures(
    rows: list[dict[str, Any]],
    icao: str,
    date_local: str,
    tz_name: str,
    min_obs: int = MIN_OBS_PER_DAY,
) -> dict[str, Any]:
    tz = get_timezone(tz_name)
    observations: list[dict[str, Any]] = []
    for row in rows:
        observed_at = _parse_report_time(row)
        temp_c = _row_temperature_c(row)
        if observed_at is None or temp_c is None:
            continue
        local_dt = observed_at.astimezone(tz)
        if local_dt.date().isoformat() != date_local:
            continue
        observations.append(
            {
                "observed_at_utc": observed_at.replace(microsecond=0).isoformat(),
                "observed_at_local": local_dt.replace(microsecond=0).isoformat(),
                "local_hour": local_dt.hour,
                "temp_c": round(float(temp_c), 1),
                "raw_metar": row.get("rawOb") or row.get("raw_text") or row.get("metar"),
            }
        )
    observations.sort(key=lambda item: item["observed_at_utc"])
    hours = [item["local_hour"] for item in observations]
    sufficient = bool(observations) and len(observations) >= min_obs and min(hours) <= 3 and max(hours) >= 20
    temps = [item["temp_c"] for item in observations]
    status = "ok" if sufficient else "insufficient_metar_coverage"
    return {
        "icao": str(icao).upper(),
        "date_local": date_local,
        "timezone": tz_name,
        "status": status,
        "coverage": {
            "obs_count": len(observations),
            "min_required_obs": min_obs,
            "first_local_hour": min(hours) if hours else None,
            "last_local_hour": max(hours) if hours else None,
            "coverage_ok": sufficient,
        },
        "tmax_c": round(max(temps), 1) if sufficient else None,
        "tmin_c": round(min(temps), 1) if sufficient else None,
        "observations": observations,
    }


def _date_window_utc(date_local: str, tz_name: str) -> tuple[datetime, datetime]:
    tz = get_timezone(tz_name)
    day = parse_date(date_local)
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def build_aviationweather_url(icao: str, date_local: str, tz_name: str, now_utc: datetime | None = None) -> str:
    start_utc, end_utc = _date_window_utc(date_local, tz_name)
    now = now_utc or datetime.now(timezone.utc)
    lookback_end = max(end_utc, now)
    hours = max(48, int(math.ceil((lookback_end - start_utc).total_seconds() / 3600.0)) + 6)
    params = urllib.parse.urlencode({"ids": str(icao).upper(), "format": "json", "hours": hours})
    return f"{AVIATIONWEATHER_METAR_URL}?{params}"


def fetch_aviationweather_metar(icao: str, date_local: str, tz_name: str, timeout: int = 45) -> tuple[list[dict[str, Any]], str]:
    url = build_aviationweather_url(icao, date_local, tz_name)
    req = urllib.request.Request(url, headers={"User-Agent": "metar-shadow-fetch/0.1"})
    with open_url(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("AviationWeather METAR payload is not a JSON list")
    return payload, url


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    icao = str(args.icao).upper()
    date_local = parse_date(args.date).isoformat()
    tz_name = args.tz or station_timezone(icao)
    city = station_city(icao, args.city)
    source_url = None
    warnings: list[str] = []
    try:
        if args.input_file:
            raw_rows = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
            if not isinstance(raw_rows, list):
                raise ValueError("--input-file must contain a JSON list")
            source = "fixture"
        else:
            raw_rows, source_url = fetch_aviationweather_metar(icao, date_local, tz_name)
            source = "aviationweather_api"
    except Exception as exc:
        raw_rows = []
        source = "aviationweather_api"
        warnings.append(f"fetch_error: {exc}")

    derived = derive_daily_temperatures(raw_rows, icao, date_local, tz_name)
    if derived["status"] == "insufficient_metar_coverage":
        warnings.append("insufficient_metar_coverage: no TMAX/TMIN derived")
    return {
        "generated_at": _now_iso(),
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "city": city,
        "icao": icao,
        "date_local": date_local,
        "timezone": tz_name,
        "source": source,
        "source_url": source_url,
        "observed_dataset": "aviationweather_metar",
        "status": derived["status"],
        "tmax_c": derived["tmax_c"],
        "tmin_c": derived["tmin_c"],
        "coverage": derived["coverage"],
        "observations": derived["observations"],
        "warnings": warnings,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icao", required=True, help="ICAO station, e.g. ZBAA.")
    parser.add_argument("--date", required=True, help="Local date YYYY-MM-DD.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory. Default data/metar_shadow.")
    parser.add_argument("--city", help="Optional city label.")
    parser.add_argument("--tz", help="Optional IANA timezone override.")
    parser.add_argument("--input-file", help="Optional JSON fixture with AviationWeather-like rows. No network fetch.")
    parser.add_argument("--no-write", action="store_true", help="Print payload only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_payload(args)
    out_path = Path(args.out_dir) / f"{payload['icao']}_{payload['date_local']}.json"
    if not args.no_write:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": payload["status"], "out": str(out_path), "tmax_c": payload["tmax_c"], "tmin_c": payload["tmin_c"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
