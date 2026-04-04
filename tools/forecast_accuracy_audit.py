#!/usr/bin/env python3
"""Auditoria de forecast accuracy vs trades cerrados."""

import argparse
import base64
import json
import math
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_POSTMORTEM_PATH = REPO_ROOT / "data" / "postmortem.json"
DEFAULT_RAW_OUTPUT = REPO_ROOT / "data" / "forecast_accuracy_raw.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "forecast_accuracy_audit.md"
DEFAULT_DASHBOARD_URL = "https://polymarket-bot-production-4deb.up.railway.app/api/dashboard.json"
DEFAULT_DASHBOARD_USER = "pablo"
DEFAULT_DASHBOARD_PASSWORD = "polymarketbot26"
DEFAULT_REMOTE_POSTMORTEM_PATH = "/app/data/postmortem.json"
NOAA_NCEI_ACCESS_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
NOAA_OBSERVED_LAG_DAYS = 2
MIN_EDGE_DEFAULT = 7.0
CLOSED_ACTIONS = {"SELL", "LOSS_TOTAL", "RESOLVED_WIN"}


def get_model_sigma(days_ahead):
    return {0: 1.2, 1: 1.5, 2: 2.0, 3: 2.5}.get(
        days_ahead,
        3.0 if days_ahead <= 5 else 3.5,
    )


def normal_cdf(x, mu, sigma):
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def estimate_prob_with_sigma(
    forecast_max,
    threshold_c,
    condition,
    days_ahead,
    threshold_high_c=None,
    sigma_override=None,
):
    sigma = get_model_sigma(days_ahead) if sigma_override is None else sigma_override
    if condition == "exact":
        prob = normal_cdf(threshold_c + 0.5, forecast_max, sigma) - normal_cdf(
            threshold_c - 0.5,
            forecast_max,
            sigma,
        )
    elif condition == "at_or_below":
        prob = normal_cdf(threshold_c + 0.5, forecast_max, sigma)
    elif condition == "at_or_above":
        prob = 1.0 - normal_cdf(threshold_c - 0.5, forecast_max, sigma)
    elif condition == "range" and threshold_high_c is not None:
        prob = normal_cdf(threshold_high_c + 0.5, forecast_max, sigma) - normal_cdf(
            threshold_c - 0.5,
            forecast_max,
            sigma,
        )
    else:
        prob = 0.5
    return max(0.01, min(0.99, prob))


def parse_temperature_question_local(question):
    import re

    aliases = {"NYC": "New York City", "New York": "New York City", "BA": "Buenos Aires"}
    degree_token = r"(?:\u00b0|\u00c2\u00b0)?"
    robust_range = re.search(
        r"temperature in (.+?) be between "
        rf"(\d+)\s*[-\u2013]\s*(\d+){degree_token}([CF])"
        r".*?(?:on |)"
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)\s+\d+)",
        question,
        re.IGNORECASE,
    )
    if robust_range:
        city = aliases.get(robust_range.group(1).strip(), robust_range.group(1).strip())
        return {
            "city": city,
            "temp_threshold": int(robust_range.group(2)),
            "temp_threshold_high": int(robust_range.group(3)),
            "condition": "range",
            "date_str": robust_range.group(5),
            "unit": robust_range.group(4).upper(),
        }

    robust_match = re.search(
        r"temperature in (.+?) (?:be |on )"
        rf"(\d+){degree_token}([CF])"
        r"(?: or (below|higher|above))?"
        r".*?(?:on |)"
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)\s+\d+)",
        question,
        re.IGNORECASE,
    )
    if robust_match:
        condition = "exact"
        if robust_match.group(4):
            if robust_match.group(4).lower() == "below":
                condition = "at_or_below"
            elif robust_match.group(4).lower() in {"higher", "above"}:
                condition = "at_or_above"
        city = aliases.get(robust_match.group(1).strip(), robust_match.group(1).strip())
        return {
            "city": city,
            "temp_threshold": int(robust_match.group(2)),
            "temp_threshold_high": None,
            "condition": condition,
            "date_str": robust_match.group(5),
            "unit": robust_match.group(3).upper(),
        }

    range_match = re.search(
        r"temperature in (.+?) be between "
        r"(\d+)\s*[-–]\s*(\d+)°([CF])"
        r".*?(?:on |)"
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)\s+\d+)",
        question,
        re.IGNORECASE,
    )
    if range_match:
        city = aliases.get(range_match.group(1).strip(), range_match.group(1).strip())
        return {
            "city": city,
            "temp_threshold": int(range_match.group(2)),
            "temp_threshold_high": int(range_match.group(3)),
            "condition": "range",
            "date_str": range_match.group(5),
            "unit": range_match.group(4).upper(),
        }

    match = re.search(
        r"temperature in (.+?) (?:be |on )"
        r"(\d+)°([CF])"
        r"(?: or (below|higher|above))?"
        r".*?(?:on |)"
        r"((?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)\s+\d+)",
        question,
        re.IGNORECASE,
    )
    if not match:
        return None

    condition = "exact"
    if match.group(4):
        if match.group(4).lower() == "below":
            condition = "at_or_below"
        elif match.group(4).lower() in {"higher", "above"}:
            condition = "at_or_above"

    city = aliases.get(match.group(1).strip(), match.group(1).strip())
    return {
        "city": city,
        "temp_threshold": int(match.group(2)),
        "temp_threshold_high": None,
        "condition": condition,
        "date_str": match.group(5),
        "unit": match.group(3).upper(),
    }


def _parse_noaa_tmp_c_local(raw_value):
    if raw_value in (None, ""):
        return None
    value_token = str(raw_value).split(",", 1)[0].strip()
    try:
        value_tenths_c = int(value_token)
    except ValueError:
        return None
    if abs(value_tenths_c) >= 9999:
        return None
    return round(value_tenths_c / 10.0, 1)


def fetch_noaa_daily_tmax_local(daily_station_id, date_iso, retries=2, delay=0):
    if not daily_station_id or not date_iso:
        return None
    try:
        market_date = date.fromisoformat(date_iso)
    except ValueError:
        return None
    if (datetime.now(timezone.utc).date() - market_date).days < NOAA_OBSERVED_LAG_DAYS:
        return None

    params = urllib.parse.urlencode({
        "dataset": "daily-summaries",
        "stations": daily_station_id,
        "startDate": date_iso,
        "endDate": date_iso,
        "dataTypes": "TMAX",
        "format": "json",
        "units": "metric",
    })
    req = urllib.request.Request(f"{NOAA_NCEI_ACCESS_URL}?{params}")
    req.add_header("User-Agent", "forecast-accuracy-audit/1.0")
    for _ in range(max(1, retries)):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows = json.loads(resp.read())
            if not isinstance(rows, list):
                return None
            for row in rows:
                value = to_float(row.get("TMAX"))
                if value is not None:
                    return round(value, 1)
            return None
        except Exception:
            if delay:
                import time

                time.sleep(delay)
    return None


def _fetch_noaa_hourly_tmax_local(noaa_station_id, date_iso, retries=2, delay=0):
    if not noaa_station_id or not date_iso:
        return None
    try:
        market_date = date.fromisoformat(date_iso)
    except ValueError:
        return None
    if (datetime.now(timezone.utc).date() - market_date).days < NOAA_OBSERVED_LAG_DAYS:
        return None

    params = urllib.parse.urlencode({
        "dataset": "global-hourly",
        "stations": noaa_station_id,
        "startDate": f"{date_iso}T00:00:00",
        "endDate": f"{date_iso}T23:59:59",
        "dataTypes": "TMP",
        "format": "json",
    })
    req = urllib.request.Request(f"{NOAA_NCEI_ACCESS_URL}?{params}")
    req.add_header("User-Agent", "forecast-accuracy-audit/1.0")
    for _ in range(max(1, retries)):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows = json.loads(resp.read())
            if not isinstance(rows, list):
                return None
            temps = [
                _parse_noaa_tmp_c_local(row.get("TMP"))
                for row in rows
            ]
            temps = [value for value in temps if value is not None]
            return max(temps) if temps else None
        except Exception:
            if delay:
                import time

                time.sleep(delay)
    return None


def fetch_noaa_observed_max_local(noaa_station_id, date_iso, daily_station_id="", retries=2, delay=0):
    daily_tmax = fetch_noaa_daily_tmax_local(
        daily_station_id,
        date_iso,
        retries=retries,
        delay=delay,
    )
    if daily_tmax is not None:
        return daily_tmax, "daily-summaries_tmax"

    hourly_tmax = _fetch_noaa_hourly_tmax_local(
        noaa_station_id,
        date_iso,
        retries=retries,
        delay=delay,
    )
    if hourly_tmax is not None:
        return hourly_tmax, "global-hourly_tmp_max"
    return None, None


def load_bot_helpers():
    """Importa helpers de bot.py; si falla, usa fallback local compatible."""
    try:
        import bot  # type: ignore

        return {
            "estimate_prob": bot.estimate_prob,
            "get_uncertainty": bot.get_uncertainty,
            "fetch_noaa_observed_max": bot.fetch_noaa_observed_max,
            "parse_temperature_question": bot.parse_temperature_question,
            "RESOLUTION_ICAO": dict(bot.RESOLUTION_ICAO),
            "RESOLUTION_STATIONS": dict(bot.RESOLUTION_STATIONS),
        }
    except Exception as exc:
        print(f"[WARN] No se pudo importar bot.py, uso fallback local: {exc}", file=sys.stderr)
        return {
            "estimate_prob": estimate_prob_with_sigma,
            "get_uncertainty": get_model_sigma,
            "fetch_noaa_observed_max": fetch_noaa_observed_max_local,
            "parse_temperature_question": parse_temperature_question_local,
            "RESOLUTION_ICAO": {
                "Chicago": {
                    "icao": "KORD",
                    "noaa_station_id": "72530094846",
                    "noaa_daily_station_id": "USW00094846",
                },
                "Atlanta": {
                    "icao": "KATL",
                    "noaa_station_id": "72219013874",
                    "noaa_daily_station_id": "USW00013874",
                },
                "Buenos Aires": {"icao": "SAEZ", "noaa_station_id": "87576099999"},
                "Dallas": {
                    "icao": "KDAL",
                    "noaa_station_id": "72258303927",
                    "noaa_daily_station_id": "USW00013960",
                },
            },
            "RESOLUTION_STATIONS": {
                "Chicago": {"lat": 41.9742, "lon": -87.9073},
                "Atlanta": {"lat": 33.6407, "lon": -84.4277},
                "Buenos Aires": {"lat": -34.8222, "lon": -58.5358},
                "Dallas": {"lat": 32.8471, "lon": -96.8518},
            },
        }


BOT_HELPERS = load_bot_helpers()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Audita forecast accuracy de trades cerrados y estima sigma empirica."
    )
    parser.add_argument(
        "--postmortem-source",
        choices=["auto", "local", "dashboard", "railway"],
        default="auto",
        help="Origen de postmortem cerrado.",
    )
    parser.add_argument("--postmortem-path", default=str(DEFAULT_POSTMORTEM_PATH))
    parser.add_argument("--dashboard-url", default=DEFAULT_DASHBOARD_URL)
    parser.add_argument("--dashboard-user", default=DEFAULT_DASHBOARD_USER)
    parser.add_argument("--dashboard-password", default=DEFAULT_DASHBOARD_PASSWORD)
    parser.add_argument("--remote-postmortem-path", default=DEFAULT_REMOTE_POSTMORTEM_PATH)
    parser.add_argument("--output-json", default=str(DEFAULT_RAW_OUTPUT))
    parser.add_argument("--output-md", default=str(DEFAULT_MARKDOWN_OUTPUT))
    parser.add_argument("--min-edge", type=float, default=MIN_EDGE_DEFAULT)
    parser.add_argument("--noaa-retries", type=int, default=2)
    parser.add_argument("--noaa-delay", type=float, default=0)
    return parser.parse_args()


def parse_timestamp(value):
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_non_null(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def unit_threshold_to_c(parsed_question):
    if not parsed_question or parsed_question.get("temp_threshold") is None:
        return None, None
    unit = parsed_question.get("unit", "C")
    low = parsed_question.get("temp_threshold")
    high = parsed_question.get("temp_threshold_high")
    threshold_c = ((low - 32) * 5 / 9) if unit == "F" else float(low)
    threshold_high_c = None
    if high is not None:
        threshold_high_c = ((high - 32) * 5 / 9) if unit == "F" else float(high)
    return threshold_c, threshold_high_c


def infer_days_ahead(market_date_iso, opened_at):
    try:
        market_date = date.fromisoformat(market_date_iso)
    except (TypeError, ValueError):
        return None
    opened_ts = parse_timestamp(opened_at)
    if opened_ts is None:
        return None
    return (market_date - opened_ts.date()).days


def condition_happened(observed_temp_c, condition, threshold_c, threshold_high_c=None):
    if observed_temp_c is None or threshold_c is None:
        return None
    if condition == "exact":
        return threshold_c - 0.5 <= observed_temp_c <= threshold_c + 0.5
    if condition == "at_or_below":
        return observed_temp_c <= threshold_c + 0.5
    if condition == "at_or_above":
        return observed_temp_c >= threshold_c - 0.5
    if condition == "range" and threshold_high_c is not None:
        return threshold_c - 0.5 <= observed_temp_c <= threshold_high_c + 0.5
    return None


def load_local_postmortem(path):
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"No existe {path_obj}")
    with path_obj.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, list):
        raise ValueError(f"{path_obj} no contiene una lista JSON")
    return payload, str(path_obj)


def fetch_dashboard_json(url, username, password):
    req = urllib.request.Request(url)
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("User-Agent", "forecast-accuracy-audit/1.0")
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read())


def load_dashboard_postmortem(url, username, password):
    dashboard = fetch_dashboard_json(url, username, password)
    if isinstance(dashboard, list):
        return dashboard, url
    for key in ["postmortem_records", "postmortem", "closed_postmortems", "recent_closed"]:
        rows = dashboard.get(key) if isinstance(dashboard, dict) else None
        if isinstance(rows, list) and rows:
            return rows, f"{url}#{key}"
    raise ValueError(
        "El dashboard JSON no expone postmortem completo; usa --postmortem-source local "
        "con una copia de postmortem.json o --postmortem-source railway."
    )


def load_railway_postmortem(remote_path):
    cmd = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(REPO_ROOT / "tools" / "railway_safe.ps1"),
        "ssh",
        f"cat {remote_path}",
    ]
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"railway_safe.ps1 ssh fallo: {stderr[:500]}")
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise ValueError(f"{remote_path} no devolvio una lista JSON")
    return payload, f"railway:{remote_path}"


def load_postmortem_records(args):
    errors = []
    if args.postmortem_source in {"auto", "local"}:
        try:
            return load_local_postmortem(args.postmortem_path)
        except Exception as exc:
            errors.append(f"local={exc}")
            if args.postmortem_source == "local":
                raise

    if args.postmortem_source in {"auto", "dashboard"}:
        try:
            return load_dashboard_postmortem(
                args.dashboard_url,
                args.dashboard_user,
                args.dashboard_password,
            )
        except Exception as exc:
            errors.append(f"dashboard={exc}")
            if args.postmortem_source == "dashboard":
                raise

    if args.postmortem_source in {"auto", "railway"}:
        try:
            return load_railway_postmortem(args.remote_postmortem_path)
        except Exception as exc:
            errors.append(f"railway={exc}")
            if args.postmortem_source == "railway":
                raise

    raise RuntimeError("No se pudo cargar postmortem: " + " | ".join(errors))


def fetch_open_meteo_observed_max(city, date_iso, resolution_stations):
    station = resolution_stations.get(city, {})
    lat = station.get("lat")
    lon = station.get("lon")
    if lat is None or lon is None or not date_iso:
        return None, None

    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "start_date": date_iso,
        "end_date": date_iso,
        "daily": "temperature_2m_max",
        "timezone": "UTC",
    })
    req = urllib.request.Request(f"https://archive-api.open-meteo.com/v1/archive?{params}")
    req.add_header("User-Agent", "forecast-accuracy-audit/1.0")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None, None

    temps = payload.get("daily", {}).get("temperature_2m_max", [])
    temp_c = to_float(temps[0] if temps else None)
    if temp_c is None:
        return None, None
    return round(temp_c, 1), "open_meteo_archive"


def get_observed_temperature(city, date_iso, args):
    meta = BOT_HELPERS["RESOLUTION_ICAO"].get(city, {})
    observed_temp, observed_source = BOT_HELPERS["fetch_noaa_observed_max"](
        meta.get("noaa_station_id"),
        date_iso,
        daily_station_id=meta.get("noaa_daily_station_id", ""),
        retries=args.noaa_retries,
        delay=args.noaa_delay,
    )
    if observed_temp is not None:
        return round(float(observed_temp), 1), observed_source or "noaa_ncei"
    return fetch_open_meteo_observed_max(
        city,
        date_iso,
        BOT_HELPERS["RESOLUTION_STATIONS"],
    )


def select_reference_buy(record):
    buys = record.get("buys") or []
    if buys:
        return dict(buys[0]), "first_buy"
    return {
        "forecast_max": record.get("latest_forecast_max"),
        "edge_pct": record.get("latest_edge_pct"),
        "our_prob": record.get("latest_our_prob"),
        "mkt_price": record.get("latest_mkt_price"),
        "timestamp": record.get("opened_at"),
    }, "latest_snapshot"


def normalize_trade_record(record, args):
    if record.get("status") != "closed":
        return None, "not_closed"
    if record.get("close_action") not in CLOSED_ACTIONS:
        return None, "unsupported_close_action"

    city = first_non_null(record.get("city"), "?")
    date_iso = first_non_null(record.get("date"), "")
    question = first_non_null(record.get("question"), "")
    side = str(first_non_null(record.get("side"), "")).upper()

    parsed = BOT_HELPERS["parse_temperature_question"](question) if question else None
    condition = first_non_null(record.get("condition"), parsed.get("condition") if parsed else None)
    threshold_raw = parsed.get("temp_threshold") if parsed else None
    threshold_high_raw = parsed.get("temp_threshold_high") if parsed else None
    threshold_c, threshold_high_c = unit_threshold_to_c(parsed)
    threshold_source = "question_parser" if threshold_c is not None else "inferred_from_prob"

    buy_snapshot, reference_source = select_reference_buy(record)
    forecast_max = to_float(buy_snapshot.get("forecast_max"))
    edge_pct = to_float(buy_snapshot.get("edge_pct"))
    our_prob_raw = to_float(buy_snapshot.get("our_prob"))
    mkt_price_raw = to_float(buy_snapshot.get("mkt_price"))
    mkt_price = None if mkt_price_raw is None else (mkt_price_raw / 100.0 if mkt_price_raw > 1 else mkt_price_raw)
    our_prob = None if our_prob_raw is None else (our_prob_raw / 100.0 if our_prob_raw > 1 else our_prob_raw)
    opened_at = first_non_null(record.get("opened_at"), buy_snapshot.get("timestamp"))
    days_ahead = infer_days_ahead(date_iso, opened_at)

    if threshold_c is None and condition and forecast_max is not None and our_prob is not None and days_ahead is not None:
        threshold_c, threshold_high_c = infer_threshold_from_prob(
            forecast_max,
            condition,
            side,
            our_prob,
            days_ahead,
        )
        threshold_raw = round(threshold_c, 2) if threshold_c is not None else None
        threshold_high_raw = round(threshold_high_c, 2) if threshold_high_c is not None else None

    if forecast_max is None:
        return None, "missing_forecast_max"
    if threshold_c is None or not condition:
        return None, "missing_threshold_or_condition"
    if mkt_price is None or our_prob is None or edge_pct is None:
        return None, "missing_market_or_edge"
    if side not in {"YES", "NO"}:
        return None, "missing_side"
    if days_ahead is None:
        return None, "missing_days_ahead"

    trade = {
        "id": record.get("id"),
        "city": city,
        "date_iso": date_iso,
        "forecast_max": round(forecast_max, 2),
        "threshold": threshold_raw,
        "threshold_high": threshold_high_raw,
        "threshold_c": round(threshold_c, 2),
        "threshold_high_c": round(threshold_high_c, 2) if threshold_high_c is not None else None,
        "threshold_source": threshold_source,
        "condition": condition,
        "side": side,
        "our_prob": round(our_prob, 4),
        "mkt_price": round(mkt_price, 4),
        "edge_pct": round(edge_pct, 2),
        "close_action": record.get("close_action"),
        "pnl_cash": to_float(record.get("pnl_cash")),
        "opened_at": opened_at,
        "closed_at": record.get("closed_at"),
        "days_ahead": days_ahead,
        "reference_source": reference_source,
    }

    observed_real, observed_source = get_observed_temperature(city, date_iso, args)
    trade["observed_real"] = None if observed_real is None else round(observed_real, 2)
    trade["observed_source"] = observed_source
    if observed_real is None:
        trade["analysis_status"] = "missing_observed"
        return trade, "missing_observed"

    prob_with_real_yes = BOT_HELPERS["estimate_prob"](
        observed_real,
        threshold_c,
        condition,
        days_ahead,
        threshold_high_c,
    )
    prob_with_real_temp = prob_with_real_yes if side == "YES" else 1.0 - prob_with_real_yes
    real_edge = prob_with_real_temp - mkt_price
    actual_yes = condition_happened(observed_real, condition, threshold_c, threshold_high_c)
    outcome_correct = actual_yes if side == "YES" else not actual_yes

    trade.update({
        "forecast_error": round(forecast_max - observed_real, 2),
        "prob_with_real_temp_yes": round(prob_with_real_yes, 4),
        "prob_with_real_temp": round(prob_with_real_temp, 4),
        "real_edge": round(real_edge, 4),
        "would_have_traded": real_edge * 100 >= args.min_edge,
        "outcome_correct": bool(outcome_correct) if actual_yes is not None else None,
        "analysis_status": "ok",
    })
    return trade, "ok"


def mean(values):
    return sum(values) / len(values) if values else None


def stddev(values):
    if len(values) < 2:
        return None
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def estimate_prob_with_empirical_sigma(trade, sigma_empirical):
    prob_yes = estimate_prob_with_sigma(
        trade["forecast_max"],
        trade["threshold_c"],
        trade["condition"],
        trade["days_ahead"],
        trade.get("threshold_high_c"),
        sigma_override=sigma_empirical,
    )
    return prob_yes if trade["side"] == "YES" else 1.0 - prob_yes


def infer_threshold_from_prob(forecast_max, condition, side, side_prob, days_ahead):
    """Reconstruye umbral en C cuando postmortem perdio question/threshold."""
    if forecast_max is None or condition not in {"exact", "at_or_below", "at_or_above", "range"}:
        return None, None

    target_yes = side_prob if side == "YES" else 1.0 - side_prob
    best_low = None
    best_high = None
    best_gap = float("inf")
    start = int(math.floor(forecast_max - 25.0))
    end = int(math.ceil(forecast_max + 25.0))

    for step in range(start * 10, end * 10 + 1):
        low = step / 10.0
        if condition == "range":
            width_options = [1.0, 0.6, 1.1]
        else:
            width_options = [None]

        for width in width_options:
            high = round(low + width, 1) if width is not None else None
            prob_yes = estimate_prob_with_sigma(
                forecast_max,
                low,
                condition,
                days_ahead,
                high,
            )
            gap = abs(prob_yes - target_yes)
            if gap < best_gap:
                best_gap = gap
                best_low = low
                best_high = high

    if best_gap > 0.08:
        return None, None
    return best_low, best_high


def build_group_stats(analyzed_trades, key_fields):
    grouped = defaultdict(list)
    for trade in analyzed_trades:
        grouped[tuple(trade.get(field) for field in key_fields)].append(trade)

    stats = []
    for key, rows in sorted(grouped.items(), key=lambda item: item[0]):
        errors = [row["forecast_error"] for row in rows if row.get("forecast_error") is not None]
        sigma_empirical = stddev(errors)
        row = {field: value for field, value in zip(key_fields, key)}
        row.update({
            "trades": len(rows),
            "wr_pct": round(100 * sum(1 for item in rows if item.get("outcome_correct")) / len(rows), 1),
            "forecast_error_mean": round(mean(errors), 3) if errors else None,
            "forecast_error_std": round(sigma_empirical, 3) if sigma_empirical is not None else None,
            "sigma_empirical": round(sigma_empirical, 3) if sigma_empirical is not None else None,
            "sigma_model": BOT_HELPERS["get_uncertainty"](row["days_ahead"]) if "days_ahead" in row else None,
            "loss_total": sum(1 for item in rows if item.get("close_action") == "LOSS_TOTAL"),
            "pnl_cash": round(sum(item.get("pnl_cash") or 0.0 for item in rows), 2),
        })
        stats.append(row)
    return stats


def enrich_with_empirical_sigma(trades, sigma_by_city_day, sigma_by_city, min_edge):
    for trade in trades:
        if trade.get("analysis_status") != "ok":
            continue

        sigma_empirical = sigma_by_city_day.get((trade["city"], trade["days_ahead"]))
        if sigma_empirical is None:
            sigma_empirical = sigma_by_city.get(trade["city"])
        if sigma_empirical is None:
            sigma_empirical = BOT_HELPERS["get_uncertainty"](trade["days_ahead"])

        prob_empirical = estimate_prob_with_empirical_sigma(trade, sigma_empirical)
        empirical_edge = prob_empirical - trade["mkt_price"]
        trade["sigma_empirical_used"] = round(sigma_empirical, 3)
        trade["prob_with_empirical_sigma"] = round(prob_empirical, 4)
        trade["empirical_edge"] = round(empirical_edge, 4)
        trade["would_have_traded_empirical_sigma"] = empirical_edge * 100 >= min_edge
        trade["fictitious_edge_gap_pct"] = round(trade["edge_pct"] - (trade["real_edge"] * 100), 2)


def build_report(records, source_name, args):
    trades = []
    skipped = Counter()
    for record in records:
        trade, status = normalize_trade_record(record, args)
        if trade is not None:
            trades.append(trade)
        skipped[status] += 1

    analyzed_trades = [trade for trade in trades if trade.get("analysis_status") == "ok"]
    city_stats = build_group_stats(analyzed_trades, ["city"])
    city_day_stats = build_group_stats(analyzed_trades, ["city", "days_ahead"])
    sigma_by_city_day = {
        (row["city"], row["days_ahead"]): row["sigma_empirical"]
        for row in city_day_stats
        if row.get("sigma_empirical") is not None
    }
    sigma_by_city = {
        row["city"]: row["sigma_empirical"]
        for row in city_stats
        if row.get("sigma_empirical") is not None
    }
    enrich_with_empirical_sigma(trades, sigma_by_city_day, sigma_by_city, args.min_edge)

    analyzed_trades = [trade for trade in trades if trade.get("analysis_status") == "ok"]
    side_counts = Counter(trade["side"] for trade in analyzed_trades)
    loss_total_count = sum(1 for trade in analyzed_trades if trade.get("close_action") == "LOSS_TOTAL")
    fake_edge_negative = sum(1 for trade in analyzed_trades if trade.get("real_edge", 0) < 0)
    not_traded_empirical = sum(
        1
        for trade in analyzed_trades
        if trade.get("would_have_traded_empirical_sigma") is False
    )
    top_bad = sorted(
        analyzed_trades,
        key=lambda row: row.get("fictitious_edge_gap_pct", float("-inf")),
        reverse=True,
    )[:5]

    return {
        "metadata": {
            "min_edge_pct": args.min_edge,
            "forecast_error_definition": "forecast_max - observed_real",
            "reference_buy_policy": "first_buy if available; latest_snapshot fallback",
            "source_name": source_name,
        },
        "summary": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source_name": source_name,
            "total_records_input": len(records),
            "trades_normalized": len(trades),
            "trades_analyzed": len(analyzed_trades),
            "missing_observed": skipped["missing_observed"],
            "skipped_counts": dict(skipped),
            "win_rate_pct": round(
                100 * sum(1 for trade in analyzed_trades if trade.get("outcome_correct")) / len(analyzed_trades),
                1,
            ) if analyzed_trades else None,
            "loss_total_pct": round(100 * loss_total_count / len(analyzed_trades), 1) if analyzed_trades else None,
            "forecast_error_mean": round(
                mean([trade["forecast_error"] for trade in analyzed_trades]),
                3,
            ) if analyzed_trades else None,
            "forecast_error_std": round(
                stddev([trade["forecast_error"] for trade in analyzed_trades]),
                3,
            ) if len(analyzed_trades) >= 2 else None,
            "real_edge_negative_pct": round(100 * fake_edge_negative / len(analyzed_trades), 1)
            if analyzed_trades else None,
            "not_traded_with_empirical_sigma_pct": round(100 * not_traded_empirical / len(analyzed_trades), 1)
            if analyzed_trades else None,
            "side_bias": {
                "YES": side_counts.get("YES", 0),
                "NO": side_counts.get("NO", 0),
                "YES_pct": round(100 * side_counts.get("YES", 0) / len(analyzed_trades), 1)
                if analyzed_trades else None,
                "NO_pct": round(100 * side_counts.get("NO", 0) / len(analyzed_trades), 1)
                if analyzed_trades else None,
            },
        },
        "sigma_by_city_days_ahead": city_day_stats,
        "summary_by_city": city_stats,
        "top_5_worst_fictitious_edge": top_bad,
        "trades": trades,
    }


def fmt_num(value, digits=2, suffix=""):
    if value is None:
        return "n/d"
    return f"{value:.{digits}f}{suffix}"


def fmt_pct(value):
    return fmt_num(value, 1, "%")


def table_row(values):
    return "| " + " | ".join(str(value) for value in values) + " |"


def build_markdown_report(report):
    summary = report["summary"]
    lines = [
        "# Forecast Accuracy Audit",
        "",
        "## Resumen ejecutivo",
        "",
        f"- Generado: `{summary['generated_at']}`",
        f"- Fuente postmortem: `{summary['source_name']}`",
        f"- Trades analizados con observado: `{summary['trades_analyzed']}` / normalizados `{summary['trades_normalized']}` / input `{summary['total_records_input']}`",
        f"- Win rate observado ex-post: `{fmt_pct(summary['win_rate_pct'])}`",
        f"- LOSS_TOTAL: `{fmt_pct(summary['loss_total_pct'])}`",
        f"- Error forecast medio `forecast_max - observed_real`: `{fmt_num(summary['forecast_error_mean'], 3, ' °C')}`",
        f"- Sigma forecast error global: `{fmt_num(summary['forecast_error_std'], 3, ' °C')}`",
        f"- Trades con `real_edge < 0`: `{fmt_pct(summary['real_edge_negative_pct'])}`",
        f"- Trades que no pasarían `MIN_EDGE` usando sigma empírica: `{fmt_pct(summary['not_traded_with_empirical_sigma_pct'])}`",
        f"- Sesgo por lado: `YES={summary['side_bias']['YES']} ({fmt_pct(summary['side_bias']['YES_pct'])})` | `NO={summary['side_bias']['NO']} ({fmt_pct(summary['side_bias']['NO_pct'])})`",
        f"- Trades sin observado recuperado: `{summary['missing_observed']}`",
        "",
        "## Sigma empírica por ciudad y days_ahead",
        "",
        table_row(["Ciudad", "days_ahead", "trades", "WR", "forecast_error_mean", "sigma_empirica", "sigma_modelo", "PnL"]),
        table_row(["---", "---", "---", "---", "---", "---", "---", "---"]),
    ]
    for row in report["sigma_by_city_days_ahead"]:
        lines.append(table_row([
            row.get("city", "n/d"),
            row.get("days_ahead", "n/d"),
            row.get("trades", 0),
            fmt_pct(row.get("wr_pct")),
            fmt_num(row.get("forecast_error_mean"), 3),
            fmt_num(row.get("sigma_empirical"), 3),
            fmt_num(row.get("sigma_model"), 2),
            fmt_num(row.get("pnl_cash"), 2, "$"),
        ]))

    lines.extend([
        "",
        "## Resumen por ciudad",
        "",
        table_row(["Ciudad", "trades", "WR", "forecast_error_mean", "sigma_empirica", "PnL", "LOSS_TOTAL"]),
        table_row(["---", "---", "---", "---", "---", "---", "---"]),
    ])
    for row in report["summary_by_city"]:
        lines.append(table_row([
            row.get("city", "n/d"),
            row.get("trades", 0),
            fmt_pct(row.get("wr_pct")),
            fmt_num(row.get("forecast_error_mean"), 3),
            fmt_num(row.get("sigma_empirical"), 3),
            fmt_num(row.get("pnl_cash"), 2, "$"),
            row.get("loss_total", 0),
        ]))

    lines.extend([
        "",
        "## Top 5 peores trades por edge ficticio",
        "",
        table_row(["Ciudad", "Fecha", "Side", "Forecast", "Obs", "Edge original", "Real edge", "Gap ficticio", "Close", "PnL"]),
        table_row(["---", "---", "---", "---", "---", "---", "---", "---", "---", "---"]),
    ])
    for row in report["top_5_worst_fictitious_edge"]:
        real_edge_pct = row.get("real_edge") * 100 if row.get("real_edge") is not None else None
        lines.append(table_row([
            row.get("city", "n/d"),
            row.get("date_iso", "n/d"),
            row.get("side", "n/d"),
            fmt_num(row.get("forecast_max"), 1, "C"),
            fmt_num(row.get("observed_real"), 1, "C"),
            fmt_num(row.get("edge_pct"), 1, "%"),
            fmt_num(real_edge_pct, 1, "%"),
            fmt_num(row.get("fictitious_edge_gap_pct"), 1, "%"),
            row.get("close_action", "n/d"),
            fmt_num(row.get("pnl_cash"), 2, "$"),
        ]))

    lines.extend([
        "",
        "## Notas de interpretación",
        "",
        "- `forecast_error = forecast_max - observed_real`; positivo significa que Open-Meteo sobreestimó la máxima.",
        "- `real_edge` se calcula contra la probabilidad del lado comprado usando la temperatura observada como media de la normal y la sigma del modelo v10.3.",
        "- `sigma_empirica` es el desvío estándar muestral del error en cada bucket; si `n < 2`, se usa bucket ciudad o sigma del modelo para el recálculo.",
        "- La referencia por trade es `first_buy` si existe; si no, se usa snapshot `latest_*`.",
        "- Si `question` venía vacío en postmortem, el umbral se infiere por grid-search contra `our_prob` y queda marcado como `threshold_source=inferred_from_prob` en el JSON.",
        "",
        "## Registros omitidos o degradados",
        "",
        "```json",
        json.dumps(summary.get("skipped_counts", {}), indent=2, ensure_ascii=False),
        "```",
        "",
    ])
    return "\n".join(lines)


def write_outputs(report, output_json, output_md):
    json_path = Path(output_json)
    md_path = Path(output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    with md_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(build_markdown_report(report))


def main():
    args = parse_args()
    records, source_name = load_postmortem_records(args)
    report = build_report(records, source_name, args)
    write_outputs(report, args.output_json, args.output_md)
    summary = report["summary"]
    print(
        "forecast_accuracy_audit OK | "
        f"source={source_name} | analyzed={summary['trades_analyzed']} | "
        f"missing_observed={summary['missing_observed']} | "
        f"real_edge<0={fmt_pct(summary['real_edge_negative_pct'])} | "
        f"out={args.output_md}"
    )


if __name__ == "__main__":
    main()
