#!/usr/bin/env python3
"""Cross-city METAR/AviationWeather measurement-layer sample spike.

LOG_ONLY research tool. It does not import bot.py, does not write runtime state,
and does not change trading/city configuration. It compares recent Gamma-derived
exact settlement labels against AviationWeather METAR local-day maximums.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = REPO_ROOT / "bot.py"
DOCS_DIR = REPO_ROOT / "docs" / "source_audits"
DEFAULT_MD_OUTPUT = DOCS_DIR / "measurement_layer_cross_city_sample_2026_05_17.md"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "source_audits" / "measurement_layer_cross_city_sample_2026_05_17.json"

GAMMA_MARKET_BY_SLUG_URL = "https://gamma-api.polymarket.com/markets/slug/{slug}"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AVIATIONWEATHER_METAR_URL = "https://aviationweather.gov/api/data/metar"

DEFAULT_CANDIDATES = (
    "Beijing",
    "Jeddah",
    "Shanghai",
    "Tokyo",
    "Buenos Aires",
    "Ankara",
    "Lucknow",
    "Chongqing",
)

TZ_FALLBACK_OFFSETS = {
    "Asia/Shanghai": 8,
    "Asia/Riyadh": 3,
    "Asia/Tokyo": 9,
    "America/Argentina/Buenos_Aires": -3,
    "Europe/Istanbul": 3,
    "Asia/Kolkata": 5.5,
}

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY research dossier. This does not authorize BUY/SELL/SKIP, "
    "whitelist, canary/active promotion, city mode changes, scheduler changes, "
    "env vars, DB writes, BANKROLL changes, Fase C, or Truth Pipeline activation."
)


@dataclass(frozen=True)
class CityMeta:
    city: str
    icao: str
    lat: float | None
    lon: float | None
    tz: str
    wu_url: str
    source_fidelity: str
    noaa_station_id: str | None


def should_bypass_proxy_env() -> bool:
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


def open_url(req: urllib.request.Request, timeout: int):
    if should_bypass_proxy_env():
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def api_get_json(url: str, timeout: int = 30, user_agent: str = "measurement-layer-cross-city/0.1") -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with open_url(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def slugify_city(city: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(city or "").strip().lower())
    return value.strip("-")


def underscored_city(city: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", str(city or "").strip().lower())
    return value.strip("_")


def build_exact_slug(city: str, date_local: str, strike_c: int) -> str:
    dt = datetime.strptime(date_local, "%Y-%m-%d")
    month = dt.strftime("%B").lower()
    return f"highest-temperature-in-{slugify_city(city)}-on-{month}-{dt.day}-{dt.year}-{strike_c}c"


def parse_jsonish_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def yes_no_from_gamma_market(market: dict[str, Any]) -> bool | None:
    outcomes = parse_jsonish_list(market.get("outcomes"))
    prices = parse_jsonish_list(market.get("outcomePrices"))
    if len(outcomes) < 2 or len(prices) < 2:
        return None
    outcome_prices: dict[str, float] = {}
    for outcome, price in zip(outcomes, prices):
        try:
            outcome_prices[str(outcome).strip().lower()] = float(price)
        except (TypeError, ValueError):
            continue
    if outcome_prices.get("yes") == 1.0 and outcome_prices.get("no") == 0.0:
        return True
    if outcome_prices.get("yes") == 0.0 and outcome_prices.get("no") == 1.0:
        return False
    return None


def literal_assignment(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        return ast.literal_eval(node.value)
    return {}


def load_repo_metadata() -> tuple[dict[str, CityMeta], list[str]]:
    source = BOT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    stations = literal_assignment(tree, "RESOLUTION_STATIONS")
    timezones = literal_assignment(tree, "CITY_TIMEZONES")
    warnings: list[str] = []

    resolution: dict[str, dict[str, Any]] = {}
    in_block = False
    for raw in source.splitlines():
        line = raw.strip()
        if line.startswith("RESOLUTION_ICAO = {"):
            in_block = True
            continue
        if in_block and line.startswith("}"):
            break
        if not in_block:
            continue
        match = re.match(r'"(?P<city>[^"]+)":\s*\{(?P<body>.*)\},?\s*$', line)
        if not match:
            continue
        body = match.group("body")
        city = match.group("city")
        fields: dict[str, Any] = {}
        for key in ("icao", "noaa_station_id", "noaa_daily_station_id", "weather_gov_timeseries_site"):
            field_match = re.search(rf'"{key}"\s*:\s*"([^"]+)"', body)
            if field_match:
                fields[key] = field_match.group(1)
        wu_match = re.search(r'_wu_history_url\("([^"]+)"\)', body)
        if wu_match:
            fields["wu_url"] = f"https://www.wunderground.com/history/daily/{{country}}/{{city}}/{wu_match.group(1)}"
        if fields.get("icao"):
            resolution[city] = fields

    source_docs: dict[str, str] = {}
    for path in DOCS_DIR.glob("*_source_fidelity_resolver.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        city = path.name.replace("_source_fidelity_resolver.md", "").replace("_", " ").title()
        if "Buenos Aires" in text or path.name.startswith("buenos_aires"):
            city = "Buenos Aires"
        verdict = "SOURCE_FIDELITY_DOC"
        verdict_match = re.search(r"(?:\*\*)?Verdict:(?:\*\*)?\s+(?:\*\*)?`?([A-Z_]+)`?", text)
        if verdict_match:
            verdict = verdict_match.group(1)
        source_docs[city] = verdict

    meta: dict[str, CityMeta] = {}
    for city, fields in resolution.items():
        station = stations.get(city, {}) if isinstance(stations, dict) else {}
        icao = str(fields.get("icao") or "").upper()
        if not icao:
            continue
        meta[city] = CityMeta(
            city=city,
            icao=icao,
            lat=float(station["lat"]) if station.get("lat") is not None else None,
            lon=float(station["lon"]) if station.get("lon") is not None else None,
            tz=str(timezones.get(city) or "UTC"),
            wu_url=str(fields.get("wu_url") or f"https://www.wunderground.com/history/daily/{icao}"),
            source_fidelity=source_docs.get(city, "NO_SOURCE_FIDELITY_DOC"),
            noaa_station_id=fields.get("noaa_station_id"),
        )
    return meta, warnings


def fetch_open_meteo_daily(start: str, end: str, meta: CityMeta) -> dict[str, float]:
    if meta.lat is None or meta.lon is None:
        return {}
    params = urllib.parse.urlencode(
        {
            "latitude": meta.lat,
            "longitude": meta.lon,
            "start_date": start,
            "end_date": end,
            "daily": "temperature_2m_max",
            "timezone": meta.tz,
        }
    )
    payload = api_get_json(f"{OPEN_METEO_ARCHIVE_URL}?{params}", user_agent="measurement-layer-openmeteo/0.1")
    daily = payload.get("daily") if isinstance(payload, dict) else {}
    dates = daily.get("time") or []
    values = daily.get("temperature_2m_max") or []
    out: dict[str, float] = {}
    for day, value in zip(dates, values):
        if value is None:
            continue
        out[str(day)] = round(float(value), 1)
    return out


def fetch_gamma_market_by_slug(slug: str) -> dict[str, Any] | None:
    encoded = urllib.parse.quote(slug, safe="")
    url = GAMMA_MARKET_BY_SLUG_URL.format(slug=encoded)
    try:
        return api_get_json(url, user_agent="measurement-layer-gamma/0.1")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def collect_gamma_settlements(
    meta: CityMeta,
    dates: list[str],
    open_meteo: dict[str, float],
    radius: int,
    delay_s: float,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    settlements: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for day in dates:
        center = open_meteo.get(day)
        if center is None:
            warnings.append(f"{meta.city} {day}: missing Open-Meteo center; skipped Gamma slug sweep")
            continue
        low = math.floor(center) - radius
        high = math.ceil(center) + radius
        rows = []
        for strike in range(low, high + 1):
            slug = build_exact_slug(meta.city, day, strike)
            market = fetch_gamma_market_by_slug(slug)
            if delay_s:
                time.sleep(delay_s)
            if not isinstance(market, dict):
                continue
            source = str(market.get("resolutionSource") or "")
            if "wunderground.com" not in source.lower() or meta.icao.lower() not in source.lower():
                warnings.append(f"{meta.city} {day} {strike}C: Gamma source not WU/{meta.icao}")
                continue
            result = yes_no_from_gamma_market(market)
            if result is None:
                continue
            rows.append(
                {
                    "date_local": day,
                    "strike_c": float(strike),
                    "yes": result,
                    "slug": market.get("slug") or slug,
                    "market_id": market.get("id"),
                    "resolution_source": source,
                }
            )
        yes_rows = [row for row in rows if row["yes"] is True]
        if len(yes_rows) == 1:
            settlements[day] = {
                "date_local": day,
                "settlement_temp_c": yes_rows[0]["strike_c"],
                "status": "inferred",
                "gamma_markets_found": len(rows),
                "yes_slug": yes_rows[0]["slug"],
                "all_markets": rows,
            }
        elif rows:
            settlements[day] = {
                "date_local": day,
                "settlement_temp_c": None,
                "status": "unreliable",
                "reason": f"expected exactly one YES market, got {len(yes_rows)}",
                "gamma_markets_found": len(rows),
                "all_markets": rows,
            }
    return settlements, warnings


def fetch_metar_daily_max(meta: CityMeta, dates: list[str], hours: int) -> tuple[dict[str, float], str, list[str]]:
    params = urllib.parse.urlencode({"ids": meta.icao, "format": "json", "hours": hours})
    url = f"{AVIATIONWEATHER_METAR_URL}?{params}"
    warnings: list[str] = []
    try:
        payload = api_get_json(url, timeout=45, user_agent="measurement-layer-aviationweather/0.1")
    except Exception as exc:
        return {}, "METAR_FETCH_ERROR", [f"{meta.city}/{meta.icao}: {exc}"]
    if not isinstance(payload, list):
        return {}, "METAR_FETCH_ERROR", [f"{meta.city}/{meta.icao}: non-list AviationWeather payload"]
    tz = get_timezone(meta.tz)
    wanted = set(dates)
    by_day: dict[str, list[tuple[int, float]]] = {day: [] for day in dates}
    for row in payload:
        if not isinstance(row, dict):
            continue
        temp = row.get("temp")
        if temp is None:
            continue
        report_time = row.get("reportTime")
        obs_time = row.get("obsTime")
        try:
            if report_time:
                dt_utc = datetime.fromisoformat(str(report_time).replace("Z", "+00:00"))
            else:
                dt_utc = datetime.fromtimestamp(float(obs_time), tz=timezone.utc)
        except Exception:
            continue
        day = dt_utc.astimezone(tz).date().isoformat()
        if day in wanted:
            by_day[day].append((dt_utc.astimezone(tz).hour, float(temp)))
    out = {}
    for day, values in by_day.items():
        if not values:
            continue
        hours_seen = [hour for hour, _temp in values]
        # A daily high is only comparable when the local day is materially
        # complete. AviationWeather caps rows, so old edge dates can contain
        # only evening observations and create false low maxima.
        if len(values) < 12 or min(hours_seen) > 3 or max(hours_seen) < 20:
            warnings.append(
                f"{meta.city}/{meta.icao}: incomplete METAR coverage for {day} "
                f"(obs={len(values)}, local_hours={min(hours_seen)}..{max(hours_seen)})"
            )
            continue
        out[day] = max(temp for _hour, temp in values)
    status = "METAR_RECENT_ONLY" if out else "INSUFFICIENT_METAR_HISTORY"
    missing = sorted(wanted - set(out))
    if missing:
        warnings.append(f"{meta.city}/{meta.icao}: missing METAR local-day highs for {', '.join(missing)}")
    return out, status, warnings


def get_timezone(tz_name: str) -> tzinfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        offset = TZ_FALLBACK_OFFSETS.get(tz_name)
        if offset is None:
            return timezone.utc
        hours = int(offset)
        minutes = int(round((float(offset) - hours) * 60))
        return timezone(timedelta(hours=hours, minutes=minutes), name=tz_name)


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [float(row["delta_c"]) for row in rows if row.get("delta_c") is not None]
    abs_deltas = [abs(value) for value in deltas]
    n = len(abs_deltas)
    return {
        "n": n,
        "median_abs_delta_c": round(statistics.median(abs_deltas), 2) if abs_deltas else None,
        "max_abs_delta_c": round(max(abs_deltas), 2) if abs_deltas else None,
        "pct_abs_delta_ge_1c": round(100.0 * sum(1 for value in abs_deltas if value >= 1.0) / n, 1) if n else None,
        "pct_abs_delta_ge_2c": round(100.0 * sum(1 for value in abs_deltas if value >= 2.0) / n, 1) if n else None,
    }


def decide_city_verdict(metrics: dict[str, Any], metar_status: str) -> str:
    n = metrics.get("n") or 0
    if n == 0:
        return "METAR_INSUFFICIENT_HISTORY"
    if n < 3:
        return "METAR_INSUFFICIENT_HISTORY"
    median_abs = metrics.get("median_abs_delta_c")
    max_abs = metrics.get("max_abs_delta_c")
    pct_ge_1 = metrics.get("pct_abs_delta_ge_1c")
    if median_abs is not None and median_abs <= 0.5 and max_abs is not None and max_abs <= 1.0 and pct_ge_1 is not None and pct_ge_1 <= 10.0:
        return "PASS_RECENT_PROMISING"
    if metar_status == "INSUFFICIENT_METAR_HISTORY":
        return "METAR_INSUFFICIENT_HISTORY"
    return "FAIL_RECENT_SAMPLE"


def decide_overall_verdict(city_reports: list[dict[str, Any]], total_metrics: dict[str, Any]) -> str:
    n = total_metrics.get("n") or 0
    pass_cities = sum(1 for city in city_reports if city.get("city_verdict") == "PASS_RECENT_PROMISING")
    fail_cities = sum(1 for city in city_reports if city.get("city_verdict") == "FAIL_RECENT_SAMPLE")
    if n == 0:
        return "METAR_INSUFFICIENT_HISTORY"
    if fail_cities > 0:
        return "METAR_NOT_RELIABLE"
    if pass_cities >= 2 and n >= 6:
        return "METAR_CROSS_CITY_PROMISING"
    if pass_cities == 1:
        return "METAR_CITY_SPECIFIC_ONLY"
    return "METAR_INSUFFICIENT_HISTORY"


def audit_city(meta: CityMeta, start: str, end: str, radius: int, metar_hours: int, delay_s: float) -> dict[str, Any]:
    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end, "%Y-%m-%d").date()
    dates = [(start_dt + timedelta(days=offset)).isoformat() for offset in range((end_dt - start_dt).days + 1)]
    open_meteo = fetch_open_meteo_daily(start, end, meta)
    settlements, gamma_warnings = collect_gamma_settlements(meta, dates, open_meteo, radius=radius, delay_s=delay_s)
    comparable_dates = sorted(day for day, row in settlements.items() if row.get("settlement_temp_c") is not None)
    metar, metar_status, metar_warnings = fetch_metar_daily_max(meta, comparable_dates, hours=metar_hours)

    rows: list[dict[str, Any]] = []
    for day in comparable_dates:
        settlement = settlements[day]["settlement_temp_c"]
        metar_value = metar.get(day)
        delta = None if metar_value is None else round(float(metar_value) - float(settlement), 2)
        rows.append(
            {
                "date_local": day,
                "settlement_temp_c": settlement,
                "metar_max_c": metar_value,
                "delta_c": delta,
                "open_meteo_max_c": open_meteo.get(day),
                "gamma_markets_found": settlements[day].get("gamma_markets_found"),
                "yes_slug": settlements[day].get("yes_slug"),
                "status": "compared" if delta is not None else metar_status,
            }
        )
    metrics = compute_metrics(rows)
    city_verdict = decide_city_verdict(metrics, metar_status)
    return {
        "city": meta.city,
        "icao": meta.icao,
        "tz": meta.tz,
        "wu_url": meta.wu_url,
        "source_fidelity": meta.source_fidelity,
        "noaa_station_id": meta.noaa_station_id,
        "candidate_class": "source_fidelity_confirmed" if meta.source_fidelity == "SOURCE_MATCH_CONFIRMED" else "wu_icao_candidate",
        "gamma_settlement_dates": len(comparable_dates),
        "metar_status": metar_status,
        "metrics": metrics,
        "city_verdict": city_verdict,
        "rows": rows,
        "warnings": gamma_warnings + metar_warnings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    total = report["total_metrics"]
    lines = [
        "# Measurement Layer Cross-City METAR Sample",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"**Overall verdict:** **{report['overall_verdict']}**",
        "",
        f"> {LOG_ONLY_DISCLAIMER}",
        "",
        "## Objective",
        "",
        "Expand the Beijing METAR/AviationWeather spike across existing WU/ICAO cities and compare recent METAR local-day highs against Gamma-derived exact settlement labels.",
        "",
        "This sample is for deciding whether METAR deserves a LOG_ONLY implementation workstream. It does not unlock Beijing directly; Beijing still needs its own minimum threshold or continued monitoring.",
        "",
        "## Method",
        "",
        f"- Candidate cities: `{', '.join(report['filters']['cities'])}`",
        f"- Date window: `{report['filters']['start']}` through `{report['filters']['end']}`",
        f"- Gamma exact slug sweep: Open-Meteo daily max center +/- `{report['filters']['gamma_radius_c']}C`",
        f"- METAR source: AviationWeather `/api/data/metar`, local-day max from `temp` at each ICAO",
        "- Settlement label accepted only when Gamma source includes Weather Underground and the expected ICAO, and exactly one exact market resolves YES for that date.",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| n total | {total.get('n')} |",
        f"| median abs delta C | {total.get('median_abs_delta_c')} |",
        f"| max abs delta C | {total.get('max_abs_delta_c')} |",
        f"| pct abs delta >= 1C | {total.get('pct_abs_delta_ge_1c')} |",
        f"| pct abs delta >= 2C | {total.get('pct_abs_delta_ge_2c')} |",
        "",
        "## Cities Audited",
        "",
        "| City | ICAO | Candidate class | Source fidelity | Gamma dates | METAR n | Median | Max | >=1C | >=2C | Pass/Fail | Notes |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for city in report["cities"]:
        metrics = city["metrics"]
        notes = city["metar_status"]
        if city["noaa_station_id"]:
            notes += "; NOAA ids present but not used"
        lines.append(
            f"| {city['city']} | {city['icao']} | {city['candidate_class']} | {city['source_fidelity']} | "
            f"{city['gamma_settlement_dates']} | {metrics.get('n')} | {metrics.get('median_abs_delta_c')} | "
            f"{metrics.get('max_abs_delta_c')} | {metrics.get('pct_abs_delta_ge_1c')} | "
            f"{metrics.get('pct_abs_delta_ge_2c')} | {city['city_verdict']} | {notes} |"
        )
    lines.extend(["", "## Day-Level Comparisons", ""])
    for city in report["cities"]:
        lines.extend(
            [
                f"### {city['city']} / {city['icao']}",
                "",
                f"- WU URL template: `{city['wu_url']}`",
                f"- Source fidelity: `{city['source_fidelity']}`",
                f"- Verdict: `{city['city_verdict']}`",
                "",
                "| Date | Gamma settlement C | METAR max C | Delta C | Open-Meteo C | Gamma markets | Slug | Status |",
                "|---|---:|---:|---:|---:|---:|---|---|",
            ]
        )
        if city["rows"]:
            for row in city["rows"]:
                lines.append(
                    f"| {row['date_local']} | {row.get('settlement_temp_c')} | {row.get('metar_max_c')} | "
                    f"{row.get('delta_c')} | {row.get('open_meteo_max_c')} | {row.get('gamma_markets_found')} | "
                    f"`{row.get('yes_slug') or ''}` | {row.get('status')} |"
                )
        else:
            lines.append("| n/a |  |  |  |  |  |  | no comparable Gamma/METAR rows |")
        if city["warnings"]:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in city["warnings"][:12])
            if len(city["warnings"]) > 12:
                lines.append(f"- ... {len(city['warnings']) - 12} more")
        lines.append("")
    lines.extend(
        [
            "## Conclusion",
            "",
            f"Verdict: `{report['overall_verdict']}`.",
            "",
        ]
    )
    if report["overall_verdict"] == "METAR_CROSS_CITY_PROMISING":
        lines.extend(
            [
                "METAR/AviationWeather deserves a dedicated LOG_ONLY implementation workstream: a standalone station-observation fetcher, cached local-day high reconstruction, and continued Gamma-derived validation by city.",
                "",
                "This is not a Beijing unlock. Beijing remains governed by its own sample threshold/monitoring because the cross-city sample only tests whether the station-observation layer is worth productizing.",
            ]
        )
    elif report["overall_verdict"] == "METAR_CITY_SPECIFIC_ONLY":
        lines.append("The evidence is still city-specific. Keep METAR as a targeted Beijing-style monitor, not a generic measurement layer yet.")
    elif report["overall_verdict"] == "METAR_NOT_RELIABLE":
        lines.append("At least one comparable city failed the recent check. Do not productize METAR without a Visual Crossing or direct WU backfill spike.")
    else:
        lines.append("Recent AviationWeather history is too thin for a cross-city decision. Next best workstream is `NEED_VISUAL_CROSSING_SPIKE` for historical backfill.")
    lines.extend(
        [
            "",
            "## Sources",
            "",
            "- Local mappings: `bot.py` `RESOLUTION_ICAO`, `RESOLUTION_STATIONS`, `CITY_TIMEZONES`",
            "- Local source-fidelity docs: `docs/source_audits/*_source_fidelity_resolver.md`",
            "- Gamma market API: `https://gamma-api.polymarket.com/markets/slug/{slug}`",
            "- AviationWeather METAR API: `https://aviationweather.gov/api/data/metar`",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", action="append", dest="cities", help="City to audit. Repeatable. Default curated WU/ICAO set.")
    parser.add_argument("--start", default="2026-05-03", help="Start local date YYYY-MM-DD.")
    parser.add_argument("--end", default="2026-05-16", help="End local date YYYY-MM-DD.")
    parser.add_argument("--gamma-radius-c", type=int, default=8, help="Strike sweep radius around Open-Meteo daily max.")
    parser.add_argument("--metar-hours", type=int, default=400, help="AviationWeather recent METAR lookback hours.")
    parser.add_argument("--request-delay-s", type=float, default=0.0, help="Optional delay between Gamma slug requests.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--no-write-json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    metadata, warnings = load_repo_metadata()
    requested = args.cities or list(DEFAULT_CANDIDATES)
    city_reports: list[dict[str, Any]] = []
    for city in requested:
        meta = metadata.get(city)
        if not meta:
            city_reports.append(
                {
                    "city": city,
                    "icao": "",
                    "tz": "",
                    "wu_url": "",
                    "source_fidelity": "MAPPING_MISSING",
                    "noaa_station_id": None,
                    "candidate_class": "excluded",
                    "gamma_settlement_dates": 0,
                    "metar_status": "INSUFFICIENT_METAR_HISTORY",
                    "metrics": compute_metrics([]),
                    "city_verdict": "METAR_INSUFFICIENT_HISTORY",
                    "rows": [],
                    "warnings": [f"{city}: missing RESOLUTION_ICAO/WU mapping"],
                }
            )
            continue
        city_reports.append(
            audit_city(
                meta,
                start=args.start,
                end=args.end,
                radius=args.gamma_radius_c,
                metar_hours=args.metar_hours,
                delay_s=args.request_delay_s,
            )
        )
    all_rows = [row for city in city_reports for row in city.get("rows", [])]
    total_metrics = compute_metrics(all_rows)
    report = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "filters": {
            "cities": requested,
            "start": args.start,
            "end": args.end,
            "gamma_radius_c": args.gamma_radius_c,
            "metar_hours": args.metar_hours,
        },
        "metadata_warnings": warnings,
        "cities": city_reports,
        "total_metrics": total_metrics,
        "overall_verdict": decide_overall_verdict(city_reports, total_metrics),
        "log_only": True,
    }
    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    if not args.no_write_json:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"overall_verdict": report["overall_verdict"], "total_metrics": total_metrics, "md_out": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
