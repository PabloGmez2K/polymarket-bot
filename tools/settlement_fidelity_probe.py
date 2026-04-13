#!/usr/bin/env python3
"""Read-only probe for settlement fidelity on directional weather markets."""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from forecast_accuracy_audit import load_bot_helpers  # noqa: E402


GAMMA_API = "https://gamma-api.polymarket.com"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_TEMP_TAG_ID = "103040"

DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "settlement_fidelity_probe.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "settlement_fidelity_probe_latest.md"

BOT_HELPERS = load_bot_helpers()
RESOLUTION_ICAO = dict(BOT_HELPERS["RESOLUTION_ICAO"])
RESOLUTION_STATIONS = dict(BOT_HELPERS["RESOLUTION_STATIONS"])
PARSE_TEMPERATURE_QUESTION = BOT_HELPERS["parse_temperature_question"]
FETCH_NOAA_OBSERVED_MAX = BOT_HELPERS["fetch_noaa_observed_max"]


def should_bypass_proxy_env():
    proxy_vars = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    )
    poisoned_markers = ("127.0.0.1:9", "localhost:9")
    for name in proxy_vars:
        value = os.getenv(name, "")
        if any(marker in value for marker in poisoned_markers):
            return True
    return False


def open_url(req, timeout):
    if should_bypass_proxy_env():
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Escanea mercados direccionales de temperatura, junta precio actual, "
            "forecast Open-Meteo y proxy observado NOAA cuando exista."
        )
    )
    parser.add_argument("--limit", type=int, default=30, help="Maximo de mercados direccionales a incluir.")
    parser.add_argument("--city", help="Filtra por ciudad exacta.")
    parser.add_argument("--skip-openmeteo", action="store_true", help="No consulta Open-Meteo.")
    parser.add_argument("--skip-noaa", action="store_true", help="No consulta NOAA para mercados pasados.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT), help="Ruta del JSON de salida.")
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT), help="Ruta del markdown de salida.")
    return parser.parse_args()


def api_get_json(url, user_agent="settlement-fidelity-probe/1.0", timeout=30):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", user_agent)
    with open_url(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def parse_date_to_iso(date_str):
    months = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }
    parts = (date_str or "").strip().split()
    if len(parts) != 2:
        return None
    month = months.get(parts[0].lower())
    if not month:
        return None
    try:
        day = int(parts[1])
    except ValueError:
        return None
    return f"2026-{month}-{day:02d}"


def load_prices(market):
    raw = market.get("outcomePrices", "[]")
    try:
        prices = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(prices, list):
        return []
    return prices


def get_active_directional_markets(limit, city_filter=None):
    directional = []
    seen_questions = set()

    for offset in range(0, 500, 50):
        url = (
            f"{GAMMA_API}/events"
            f"?tag_id={DAILY_TEMP_TAG_ID}"
            f"&active=true&closed=false"
            f"&limit=50&offset={offset}"
            f"&order=volume24hr&ascending=false"
        )
        events = api_get_json(url)
        if not isinstance(events, list) or not events:
            break

        for event in events:
            for market in event.get("markets", []):
                question = market.get("question", "")
                if question in seen_questions:
                    continue
                parsed = PARSE_TEMPERATURE_QUESTION(question) if question else None
                if not parsed:
                    continue
                condition = parsed.get("condition")
                if condition not in {"at_or_above", "at_or_below"}:
                    continue
                city = parsed.get("city")
                if city_filter and city != city_filter:
                    continue

                seen_questions.add(question)
                directional.append({
                    "event": event,
                    "market": market,
                    "parsed": parsed,
                })
                if len(directional) >= limit:
                    return directional

    return directional


def fetch_open_meteo_daily_max(lat, lon, market_date):
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max",
        "temperature_unit": "celsius",
        "timezone": "auto",
        "start_date": market_date,
        "end_date": market_date,
    })
    payload = api_get_json(f"{OPEN_METEO_FORECAST_URL}?{params}", user_agent="settlement-fidelity-probe-openmeteo/1.0")
    daily = payload.get("daily") if isinstance(payload, dict) else None
    if not isinstance(daily, dict):
        return None
    values = daily.get("temperature_2m_max")
    if not isinstance(values, list) or not values:
        return None
    try:
        return round(float(values[0]), 1)
    except (TypeError, ValueError):
        return None


def convert_threshold_to_c(parsed):
    temp = parsed.get("temp_threshold")
    unit = parsed.get("unit")
    if temp is None or unit not in {"C", "F"}:
        return None
    if unit == "C":
        return float(temp)
    return round((float(temp) - 32.0) * 5.0 / 9.0, 1)


def build_market_row(entry, skip_openmeteo=False, skip_noaa=False):
    event = entry["event"]
    market = entry["market"]
    parsed = entry["parsed"]
    city = parsed.get("city")
    question = market.get("question", "")
    date_iso = parse_date_to_iso(parsed.get("date_str"))
    condition = parsed.get("condition")
    resolution_meta = RESOLUTION_ICAO.get(city, {})
    station_meta = RESOLUTION_STATIONS.get(city, {})
    prices = load_prices(market)
    market_prob_yes = None
    market_prob_no = None
    if len(prices) >= 2:
        try:
            market_prob_yes = round(float(prices[0]), 4)
            market_prob_no = round(float(prices[1]), 4)
        except (TypeError, ValueError):
            market_prob_yes = None
            market_prob_no = None

    today = datetime.now(timezone.utc).date()
    days_ahead = None
    if date_iso:
        days_ahead = (date.fromisoformat(date_iso) - today).days

    openmeteo_forecast_c = None
    if not skip_openmeteo and date_iso and station_meta.get("lat") is not None and station_meta.get("lon") is not None:
        try:
            openmeteo_forecast_c = fetch_open_meteo_daily_max(
                station_meta["lat"],
                station_meta["lon"],
                date_iso,
            )
        except Exception:
            openmeteo_forecast_c = None

    noaa_observed_c = None
    noaa_dataset = None
    if not skip_noaa and date_iso and days_ahead is not None and days_ahead <= -2:
        try:
            noaa_observed_c, noaa_dataset = FETCH_NOAA_OBSERVED_MAX(
                resolution_meta.get("noaa_station_id", ""),
                date_iso,
                daily_station_id=resolution_meta.get("noaa_daily_station_id", ""),
            )
        except Exception:
            noaa_observed_c, noaa_dataset = None, None

    forecast_vs_noaa_gap_c = None
    if openmeteo_forecast_c is not None and noaa_observed_c is not None:
        forecast_vs_noaa_gap_c = round(openmeteo_forecast_c - noaa_observed_c, 2)

    return {
        "question": question,
        "event_slug": event.get("slug", ""),
        "market_slug": market.get("slug", ""),
        "city": city,
        "date_iso": date_iso,
        "days_ahead": days_ahead,
        "condition": condition,
        "threshold": parsed.get("temp_threshold"),
        "threshold_high": parsed.get("temp_threshold_high"),
        "threshold_unit": parsed.get("unit"),
        "threshold_c": convert_threshold_to_c(parsed),
        "market_prob_yes": market_prob_yes,
        "market_prob_no": market_prob_no,
        "volume_24h": market.get("volume24hr"),
        "liquidity": market.get("liquidityNum"),
        "resolution_icao": resolution_meta.get("icao", ""),
        "resolution_wu_url": resolution_meta.get("wu_url", ""),
        "noaa_station_id": resolution_meta.get("noaa_station_id", ""),
        "noaa_daily_station_id": resolution_meta.get("noaa_daily_station_id", ""),
        "openmeteo_forecast_max_c": openmeteo_forecast_c,
        "noaa_observed_max_c": noaa_observed_c,
        "noaa_dataset": noaa_dataset,
        "forecast_vs_noaa_gap_c": forecast_vs_noaa_gap_c,
        "wu_forecast_status": "pending_not_automated",
        "probe_readiness": {
            "has_resolution_meta": bool(resolution_meta.get("icao")),
            "has_wu_url": bool(resolution_meta.get("wu_url")),
            "has_openmeteo": openmeteo_forecast_c is not None,
            "has_noaa_observed": noaa_observed_c is not None,
        },
    }


def summarize(rows):
    city_counts = Counter(row["city"] for row in rows if row.get("city"))
    condition_counts = Counter(row["condition"] for row in rows if row.get("condition"))
    with_openmeteo = sum(1 for row in rows if row.get("openmeteo_forecast_max_c") is not None)
    with_noaa = sum(1 for row in rows if row.get("noaa_observed_max_c") is not None)
    with_gap = [row["forecast_vs_noaa_gap_c"] for row in rows if row.get("forecast_vs_noaa_gap_c") is not None]
    return {
        "n_markets": len(rows),
        "n_with_openmeteo": with_openmeteo,
        "n_with_noaa_observed": with_noaa,
        "avg_forecast_vs_noaa_gap_c": round(sum(with_gap) / len(with_gap), 2) if with_gap else None,
        "cities": dict(city_counts.most_common()),
        "conditions": dict(condition_counts.most_common()),
    }


def render_markdown(payload):
    rows = payload["markets"]
    summary = payload["summary"]
    lines = [
        "# Settlement Fidelity Probe - latest run",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Markets scanned: `{summary['n_markets']}`",
        f"- Open-Meteo available: `{summary['n_with_openmeteo']}`",
        f"- NOAA observed available: `{summary['n_with_noaa_observed']}`",
        f"- Avg forecast_vs_noaa gap (where available): `{summary['avg_forecast_vs_noaa_gap_c']}`",
        "",
        "## Notes",
        "",
        "- This probe is read-only and does not change bot behavior.",
        "- `wu_forecast_status` remains pending: the current implementation measures Open-Meteo plus observed NOAA proxy and resolution metadata.",
        "- The purpose is to locate where evidence is missing before changing the core strategy.",
        "",
        "## Sample",
        "",
        "| City | Date | Condition | Mkt YES | Open-Meteo C | NOAA C | Gap C | ICAO |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows[:20]:
        lines.append(
            f"| {row.get('city','')} | {row.get('date_iso','')} | {row.get('condition','')} | "
            f"{row.get('market_prob_yes','')} | {row.get('openmeteo_forecast_max_c','')} | "
            f"{row.get('noaa_observed_max_c','')} | {row.get('forecast_vs_noaa_gap_c','')} | "
            f"{row.get('resolution_icao','')} |"
        )
    lines.extend([
        "",
        "## Top cities",
        "",
    ])
    for city, count in payload["summary"]["cities"].items():
        lines.append(f"- `{city}`: `{count}`")
    return "\n".join(lines) + "\n"


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main():
    args = parse_args()
    directional_markets = get_active_directional_markets(args.limit, city_filter=args.city)
    rows = [
        build_market_row(
            entry,
            skip_openmeteo=args.skip_openmeteo,
            skip_noaa=args.skip_noaa,
        )
        for entry in directional_markets
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "filters": {
            "limit": args.limit,
            "city": args.city or "",
            "skip_openmeteo": args.skip_openmeteo,
            "skip_noaa": args.skip_noaa,
        },
        "summary": summarize(rows),
        "markets": rows,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Settlement fidelity probe written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
