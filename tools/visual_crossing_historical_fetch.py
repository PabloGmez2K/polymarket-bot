#!/usr/bin/env python3
"""Fetch Visual Crossing historical daily weather for a single station/date.

LOG_ONLY standalone tool. It does not import bot.py, does not write runtime
state, and does not authorize trading, promotion, scheduler, BANKROLL, Fase C,
Truth Pipeline, or canonical source changes.

Output JSON is compatible with the schema consumed by
tools/metar_resolution_verify.py (status, tmax_c, tmin_c, coverage.coverage_ok).

Usage:
  python tools/visual_crossing_historical_fetch.py \\
      --icao ZBAA --date 2026-04-10 --tz Asia/Shanghai --city Beijing
  python tools/visual_crossing_historical_fetch.py \\
      --icao OEJN --date 2026-04-10 --lat 21.6796 --lon 39.1566 --no-write
  python tools/visual_crossing_historical_fetch.py \\
      --icao RJTT --date 2026-04-12 --tz Asia/Tokyo --api-key-env MY_VC_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "metar_shadow"
VC_TIMELINE_BASE = (
    "https://weather.visualcrossing.com"
    "/VisualCrossingWebServices/rest/services/timeline"
)
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY Visual Crossing historical measurement layer. This does not authorize "
    "BUY/SELL/SKIP, promotion, scheduler changes, env vars, DB writes, BANKROLL, "
    "Fase C, Truth Pipeline, or canonical source changes."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_vc_url(location: str, date_str: str, api_key: str) -> str:
    """Full URL with key — never log or store this string."""
    params = urllib.parse.urlencode(
        {
            "unitGroup": "metric",
            "include": "days,stations",
            "contentType": "json",
            "key": api_key,
        }
    )
    return f"{VC_TIMELINE_BASE}/{urllib.parse.quote(location, safe=',.')}/{date_str}?{params}"


def build_vc_url_safe(location: str, date_str: str) -> str:
    """URL without the key — safe for audit trail and logging."""
    params = urllib.parse.urlencode(
        {
            "unitGroup": "metric",
            "include": "days,stations",
            "contentType": "json",
        }
    )
    return f"{VC_TIMELINE_BASE}/{urllib.parse.quote(location, safe=',.')}/{date_str}?{params}"


def fetch_vc_day(
    location: str, date_str: str, api_key: str, timeout: int = 45
) -> dict[str, Any]:
    url = build_vc_url(location, date_str, api_key)
    req = urllib.request.Request(url, headers={"User-Agent": "vc-historical-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_vc_day(vc_response: dict[str, Any]) -> dict[str, Any]:
    """Extract tmax_c, tmin_c and audit fields from a Visual Crossing response."""
    days = vc_response.get("days") or []
    if not days:
        return {
            "status": "error",
            "reason": "no_days_in_response",
            "tmax_c": None,
            "tmin_c": None,
            "vc_stations": [],
            "vc_source": None,
            "raw_day": None,
        }

    day = days[0]
    tempmax = day.get("tempmax")
    tempmin = day.get("tempmin")

    vc_stations = sorted((vc_response.get("stations") or {}).keys())

    if tempmax is None or tempmin is None:
        return {
            "status": "insufficient_coverage",
            "reason": "tempmax_or_tempmin_missing",
            "tmax_c": None,
            "tmin_c": None,
            "vc_stations": vc_stations,
            "vc_source": day.get("source"),
            "raw_day": {
                k: day.get(k)
                for k in ("datetime", "tempmax", "tempmin", "source", "conditions")
            },
        }

    return {
        "status": "ok",
        "reason": None,
        "tmax_c": round(float(tempmax), 1),
        "tmin_c": round(float(tempmin), 1),
        "vc_stations": vc_stations,
        "vc_source": day.get("source"),
        "raw_day": {
            k: day.get(k)
            for k in ("datetime", "tempmax", "tempmin", "source", "conditions", "icon")
        },
    }


def build_payload(
    icao: str,
    date_str: str,
    tz_name: str,
    city: str | None,
    location: str,
    api_key: str,
    timeout: int = 45,
) -> dict[str, Any]:
    icao = icao.upper()
    warnings: list[str] = []
    vc_url_safe = build_vc_url_safe(location, date_str)

    try:
        vc_response = fetch_vc_day(location, date_str, api_key, timeout=timeout)
    except Exception as exc:
        return {
            "generated_at": _now_iso(),
            "log_only": True,
            "disclaimer": LOG_ONLY_DISCLAIMER,
            "source": "visual_crossing",
            "icao": icao,
            "date": date_str,
            "date_local": date_str,
            "timezone": tz_name,
            "city": city,
            "status": "error",
            "tmax_c": None,
            "tmin_c": None,
            "coverage": {
                "coverage_ok": False,
                "obs_count": 0,
                "source_note": "visual_crossing_daily_aggregate",
            },
            "vc_stations": None,
            "vc_source": None,
            "raw_day": None,
            "warnings": [f"fetch_error: {exc}"],
            "vc_url_safe": vc_url_safe,
        }

    parsed = parse_vc_day(vc_response)
    status = parsed.get("status", "error")
    tmax_c = parsed.get("tmax_c")
    tmin_c = parsed.get("tmin_c")

    if status != "ok":
        warnings.append(f"vc_parse: {parsed.get('reason', 'unknown')}")

    coverage_ok = status == "ok" and tmax_c is not None

    return {
        "generated_at": _now_iso(),
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "source": "visual_crossing",
        "icao": icao,
        "date": date_str,
        "date_local": date_str,
        "timezone": tz_name,
        "city": city,
        "status": status,
        "tmax_c": tmax_c,
        "tmin_c": tmin_c,
        "coverage": {
            "coverage_ok": coverage_ok,
            "obs_count": 1 if coverage_ok else 0,
            "source_note": "visual_crossing_daily_aggregate",
        },
        "vc_stations": parsed.get("vc_stations"),
        "vc_source": parsed.get("vc_source"),
        "raw_day": parsed.get("raw_day"),
        "warnings": warnings,
        "vc_url_safe": vc_url_safe,
    }


def resolve_location(icao: str, lat: float | None, lon: float | None) -> str:
    """Use lat,lon if provided; otherwise query by ICAO code."""
    if lat is not None and lon is not None:
        return f"{lat},{lon}"
    return icao.upper()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icao", required=True, help="ICAO station code, e.g. ZBAA.")
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD.")
    parser.add_argument(
        "--lat", type=float, default=None,
        help="Station latitude (optional; overrides ICAO as VC query location).",
    )
    parser.add_argument(
        "--lon", type=float, default=None,
        help="Station longitude (optional; overrides ICAO as VC query location).",
    )
    parser.add_argument("--tz", default="UTC", help="IANA timezone name (informational only).")
    parser.add_argument("--city", default=None, help="City label (informational only).")
    parser.add_argument(
        "--out-dir", default=str(DEFAULT_OUT_DIR),
        help="Output directory for snapshot JSON. Default: data/metar_shadow.",
    )
    parser.add_argument(
        "--no-write", action="store_true",
        help="Print summary only; do not write snapshot file.",
    )
    parser.add_argument(
        "--api-key-env", default="VISUAL_CROSSING_API_KEY",
        help="Name of the environment variable holding the API key.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        print(
            f"ERROR: {args.api_key_env} is not set. "
            "Set the env var and re-run. No network call made.",
            file=sys.stderr,
        )
        return 1

    icao = str(args.icao).upper()
    date_str = args.date
    location = resolve_location(icao, args.lat, args.lon)

    payload = build_payload(
        icao=icao,
        date_str=date_str,
        tz_name=args.tz,
        city=args.city,
        location=location,
        api_key=api_key,
    )

    out_path = Path(args.out_dir) / f"{icao}_{date_str}.json"

    if not args.no_write:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    summary = {
        "status": payload["status"],
        "out": str(out_path),
        "tmax_c": payload["tmax_c"],
        "tmin_c": payload["tmin_c"],
        "coverage_ok": payload["coverage"]["coverage_ok"],
        "log_only": True,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
