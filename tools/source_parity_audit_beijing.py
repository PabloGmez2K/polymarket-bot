#!/usr/bin/env python3
"""Beijing Open-Meteo vs Weather Underground parity audit (LOG_ONLY).

Standalone source-parity dossier for Beijing/ZBAA. It never imports bot.py,
never writes runtime state, and does not scrape Weather Underground. If no
manual or future reliable WU dataset is provided, the audit reports
WU_FETCHER_MISSING.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLOCKED_INPUTS = [
    REPO_ROOT / "data" / "blocked_signals_resolutions.jsonl",
    REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl",
]
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "source_audits" / "beijing_open_meteo_vs_wu_parity.md"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "source_audits" / "beijing_open_meteo_vs_wu_parity.json"

CITY = "Beijing"
ICAO = "ZBAA"
LAT = 40.0799
LON = 116.6031
WU_URL = "https://www.wunderground.com/history/daily/cn/beijing/ZBAA"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
GAMMA_MARKET_BY_SLUG_URL = "https://gamma-api.polymarket.com/markets/slug/{slug}"

OPUS_MIN_N = 30
OPUS_MAX_MEDIAN_ABS_DELTA_C = 0.5
OPUS_MAX_PCT_ABS_DELTA_GE_1C = 10.0
OPUS_BLOCKED_MATCH_REQUIRED = 10
OPUS_BLOCKED_MATCH_TOTAL = 11

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY source-parity dossier. This does not authorize BUY/SELL/SKIP, "
    "whitelist, canary/active promotion, scheduler changes, env vars, DB writes, "
    "BANKROLL changes, Fase C, or Truth Pipeline activation."
)


@dataclass(frozen=True)
class DailyComparison:
    date_local: str
    open_meteo_max_c: float | None
    wu_high_c: float | None
    delta_c: float | None
    status: str


@dataclass(frozen=True)
class GammaSettlementComparison:
    date_local: str
    open_meteo_max_c: float | None
    settlement_temp_c: float | None
    delta_c: float | None
    status: str
    evidence: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def default_window(days: int) -> tuple[date, date]:
    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return start, end


def iter_dates(start: date, end: date) -> Iterable[str]:
    cur = start
    while cur <= end:
        yield cur.isoformat()
        cur += timedelta(days=1)


def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_daily_csv(path: Path, value_columns: tuple[str, ...]) -> dict[str, float]:
    """Load a date-keyed CSV with a temperature column in Celsius."""
    data: dict[str, float] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            date_local = row.get("date") or row.get("date_local") or row.get("day")
            if not date_local:
                continue
            value = None
            for column in value_columns:
                value = _to_float(row.get(column))
                if value is not None:
                    break
            if value is not None:
                data[str(date_local)] = round(value, 2)
    return data


def fetch_open_meteo_daily(start: date, end: date, lat: float = LAT, lon: float = LON) -> dict[str, float]:
    params = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_max",
            "timezone": "Asia/Shanghai",
        }
    )
    req = urllib.request.Request(f"{OPEN_METEO_ARCHIVE_URL}?{params}", headers={"User-Agent": "source-parity-audit/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    daily = payload.get("daily") if isinstance(payload, dict) else {}
    dates = daily.get("time") or []
    values = daily.get("temperature_2m_max") or []
    return {
        str(day): round(float(value), 2)
        for day, value in zip(dates, values)
        if value is not None
    }


def fetch_gamma_market_by_slug(slug: str, timeout: int = 30) -> dict:
    encoded = urllib.parse.quote(slug, safe="")
    req = urllib.request.Request(
        GAMMA_MARKET_BY_SLUG_URL.format(slug=encoded),
        headers={"User-Agent": "beijing-source-parity-audit/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Gamma market payload for {slug} is not an object")
    return payload


def month_name_to_number(month: str) -> int | None:
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    return months.get(str(month or "").strip().lower())


def date_to_slug_parts(date_local: str) -> tuple[str, int, int]:
    dt = parse_date(date_local)
    return dt.strftime("%B").lower(), dt.day, dt.year


def build_beijing_exact_slug(date_local: str, strike_c: float | int) -> str:
    month, day, year = date_to_slug_parts(date_local)
    strike = int(float(strike_c))
    return f"highest-temperature-in-beijing-on-{month}-{day}-{year}-{strike}c"


def parse_beijing_exact_slug(slug: str) -> dict | None:
    match = re.fullmatch(
        r"highest-temperature-in-beijing-on-([a-z]+)-(\d{1,2})-(\d{4})-(\d+)c",
        str(slug or "").strip().lower(),
    )
    if not match:
        return None
    month = month_name_to_number(match.group(1))
    if not month:
        return None
    day = int(match.group(2))
    year = int(match.group(3))
    strike = float(match.group(4))
    return {"date_local": f"{year:04d}-{month:02d}-{day:02d}", "strike_c": strike}


def parse_jsonish_list(value) -> list:
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


def yes_no_from_gamma_market(market: dict) -> bool | None:
    outcomes = parse_jsonish_list(market.get("outcomes"))
    prices = parse_jsonish_list(market.get("outcomePrices"))
    if len(outcomes) < 2 or len(prices) < 2:
        return None
    outcome_prices = {}
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


def extract_gamma_exact_result(market: dict, fallback_slug: str | None = None) -> dict:
    slug = str(market.get("slug") or fallback_slug or "")
    parsed = parse_beijing_exact_slug(slug)
    if not parsed:
        raise ValueError(f"Gamma market slug is not a Beijing exact-temperature slug: {slug}")
    source = str(market.get("resolutionSource") or "")
    if "wunderground.com" not in source.lower() or ICAO.lower() not in source.lower():
        raise ValueError(f"Gamma market source is not WU/{ICAO}: {source}")
    result_yes = yes_no_from_gamma_market(market)
    if result_yes is None:
        raise ValueError(f"Gamma market does not expose terminal YES/NO prices: {slug}")
    return {
        "date_local": parsed["date_local"],
        "strike_c": parsed["strike_c"],
        "slug": slug,
        "market_id": market.get("id"),
        "condition_id": market.get("conditionId") or market.get("condition_id"),
        "yes": result_yes,
        "resolution_source": source,
    }


def infer_settlement_from_exact_markets(markets: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """Infer integer settlement high from resolved exact markets.

    A date is reliable when exactly one exact market resolves YES and all
    available NO markets for that date are consistent with that YES strike.
    """
    by_date: dict[str, list[dict]] = {}
    warnings = []
    for market in markets:
        try:
            result = extract_gamma_exact_result(market)
        except ValueError as exc:
            warnings.append(str(exc))
            continue
        by_date.setdefault(result["date_local"], []).append(result)

    inferred: dict[str, dict] = {}
    for date_local, rows in sorted(by_date.items()):
        yes_rows = [row for row in rows if row["yes"] is True]
        no_rows = [row for row in rows if row["yes"] is False]
        if len(yes_rows) != 1:
            inferred[date_local] = {
                "date_local": date_local,
                "settlement_temp_c": None,
                "status": "unreliable",
                "reason": f"expected exactly one YES exact market, got {len(yes_rows)}",
                "markets": rows,
            }
            continue
        settlement = yes_rows[0]["strike_c"]
        inconsistent_no = [row for row in no_rows if row["strike_c"] == settlement]
        status = "inferred" if not inconsistent_no else "unreliable"
        reason = "single YES exact market" if status == "inferred" else "NO market conflicts with YES strike"
        inferred[date_local] = {
            "date_local": date_local,
            "settlement_temp_c": settlement if status == "inferred" else None,
            "status": status,
            "reason": reason,
            "markets": rows,
        }
    return inferred, warnings


def collect_gamma_markets_for_blocked_rows(
    blocked_rows: list[dict],
    fetcher=fetch_gamma_market_by_slug,
    neighbor_radius: int = 3,
) -> tuple[list[dict], list[dict]]:
    market_keys = set()
    requests = []
    by_date: dict[str, list[float]] = {}
    for row in blocked_rows:
        if row.get("condition") != "exact" or not row.get("date_local") or row.get("strike_c") is None:
            continue
        by_date.setdefault(row["date_local"], []).append(float(row["strike_c"]))

    for date_local, strikes in sorted(by_date.items()):
        low = int(min(strikes)) - max(0, int(neighbor_radius))
        high = int(max(strikes)) + max(0, int(neighbor_radius))
        for strike in range(low, high + 1):
            slug = build_beijing_exact_slug(date_local, strike)
            if slug in market_keys:
                continue
            market_keys.add(slug)
            requests.append({"date_local": date_local, "strike_c": float(strike), "slug": slug})

    markets = []
    errors = []
    for req in requests:
        try:
            market = fetcher(req["slug"])
            market["_requested_slug"] = req["slug"]
            markets.append(market)
        except Exception as exc:  # LOG_ONLY audit: keep collecting evidence.
            errors.append({**req, "error": str(exc)})
    return markets, errors


def build_gamma_settlement_comparisons(
    blocked_rows: list[dict],
    open_meteo: dict[str, float],
    fetcher=fetch_gamma_market_by_slug,
    neighbor_radius: int = 3,
) -> dict:
    markets, errors = collect_gamma_markets_for_blocked_rows(blocked_rows, fetcher=fetcher, neighbor_radius=neighbor_radius)
    inferred, warnings = infer_settlement_from_exact_markets(markets)

    target_dates = sorted({row["date_local"] for row in blocked_rows if row.get("date_local")})
    rows: list[GammaSettlementComparison] = []
    for day in target_dates:
        om_value = open_meteo.get(day)
        settlement = inferred.get(day, {})
        settlement_temp = settlement.get("settlement_temp_c")
        if not settlement:
            status = "missing_gamma_market"
            delta = None
            evidence = "no exact Gamma market fetched for date"
        elif settlement.get("status") != "inferred":
            status = "unreliable_gamma_derivation"
            delta = None
            evidence = settlement.get("reason", "")
        elif om_value is None:
            status = "missing_open_meteo"
            delta = None
            evidence = settlement.get("reason", "")
        else:
            status = "compared"
            delta = round(float(om_value) - float(settlement_temp), 2)
            evidence = settlement.get("reason", "")
        rows.append(GammaSettlementComparison(day, om_value, settlement_temp, delta, status, evidence))

    metrics = compute_gamma_settlement_metrics(rows, blocked_rows)
    verdict, reasons = decide_gamma_settlement_verdict(metrics, errors, warnings)
    return {
        "enabled": True,
        "neighbor_radius": neighbor_radius,
        "market_fetch_errors": errors,
        "warnings": warnings,
        "inferred_settlements": inferred,
        "comparisons": [row.__dict__ for row in rows],
        "metrics": metrics,
        "verdict": verdict,
        "verdict_reasons": reasons,
    }


def compute_gamma_settlement_metrics(rows: list[GammaSettlementComparison], blocked_rows: list[dict]) -> dict:
    compared = [row for row in rows if row.delta_c is not None]
    deltas = [row.delta_c for row in compared if row.delta_c is not None]
    abs_deltas = [abs(value) for value in deltas]
    exact_dates = {row["date_local"] for row in blocked_rows if row.get("condition") == "exact" and row.get("date_local")}
    return {
        "blocked_rows": len(blocked_rows),
        "blocked_exact_dates": len(exact_dates),
        "n_dates_compared": len(compared),
        "n_unreliable": sum(1 for row in rows if row.status == "unreliable_gamma_derivation"),
        "n_missing_gamma_market": sum(1 for row in rows if row.status == "missing_gamma_market"),
        "delta_median_c": round(statistics.median(deltas), 2) if deltas else None,
        "median_abs_delta_c": round(statistics.median(abs_deltas), 2) if abs_deltas else None,
        "max_abs_delta_c": round(max(abs_deltas), 2) if abs_deltas else None,
        "pct_abs_delta_ge_1c": round(100.0 * sum(1 for value in abs_deltas if value >= 1.0) / len(compared), 1) if compared else None,
        "pct_abs_delta_ge_2c": round(100.0 * sum(1 for value in abs_deltas if value >= 2.0) / len(compared), 1) if compared else None,
    }


def decide_gamma_settlement_verdict(metrics: dict, errors: list[dict], warnings: list[str]) -> tuple[str, list[str]]:
    reasons = []
    if warnings:
        reasons.append(f"gamma_warnings={len(warnings)}")
    if (metrics.get("n_unreliable") or 0) > 0:
        reasons.append(f"unreliable_derivations={metrics.get('n_unreliable')}")
    if (metrics.get("n_missing_gamma_market") or 0) > 0:
        reasons.append(f"missing_gamma_markets={metrics.get('n_missing_gamma_market')}")
    n_compared = metrics.get("n_dates_compared") or 0
    if n_compared == 0:
        if errors:
            reasons.append(f"gamma_fetch_errors={len(errors)}")
        return "INSUFFICIENT_GAMMA_MARKETS", reasons or ["no comparable Gamma-derived settlement dates"]
    median_abs = metrics.get("median_abs_delta_c")
    pct_ge_1 = metrics.get("pct_abs_delta_ge_1c")
    if median_abs is None or median_abs > OPUS_MAX_MEDIAN_ABS_DELTA_C:
        reasons.append(f"median_abs_delta_c={median_abs} > {OPUS_MAX_MEDIAN_ABS_DELTA_C}")
    if pct_ge_1 is None or pct_ge_1 > OPUS_MAX_PCT_ABS_DELTA_GE_1C:
        reasons.append(f"pct_abs_delta_ge_1c={pct_ge_1} > {OPUS_MAX_PCT_ABS_DELTA_GE_1C}")
    if any(reason.startswith(("median_abs_delta_c", "pct_abs_delta_ge_1c")) for reason in reasons):
        return "SETTLEMENT_GAMMA_PARITY_FAIL", reasons
    if any(reason.startswith(("gamma_warnings", "unreliable_derivations")) for reason in reasons):
        return "GAMMA_SETTLEMENT_DERIVATION_UNRELIABLE", reasons
    if reasons:
        return "SETTLEMENT_GAMMA_PARITY_FAIL", reasons
    return "SETTLEMENT_GAMMA_PARITY_PASS", ["Gamma-derived settlement triage criteria met"]


def build_comparisons(
    dates: Iterable[str],
    open_meteo: dict[str, float],
    wu: dict[str, float] | None,
) -> list[DailyComparison]:
    rows: list[DailyComparison] = []
    for day in dates:
        om_value = open_meteo.get(day)
        wu_value = wu.get(day) if wu is not None else None
        if wu is None:
            status = "wu_fetcher_missing"
            delta = None
        elif om_value is None and wu_value is None:
            status = "missing_both"
            delta = None
        elif om_value is None:
            status = "missing_open_meteo"
            delta = None
        elif wu_value is None:
            status = "missing_wu"
            delta = None
        else:
            delta = round(om_value - wu_value, 2)
            status = "compared"
        rows.append(DailyComparison(day, om_value, wu_value, delta, status))
    return rows


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * (pct / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 2)


def compute_metrics(rows: list[DailyComparison]) -> dict:
    compared = [row for row in rows if row.delta_c is not None]
    deltas = [row.delta_c for row in compared if row.delta_c is not None]
    abs_deltas = [abs(value) for value in deltas]
    n = len(compared)
    return {
        "n_days_requested": len(rows),
        "n_compared": n,
        "n_missing_open_meteo": sum(1 for row in rows if row.status == "missing_open_meteo"),
        "n_missing_wu": sum(1 for row in rows if row.status == "missing_wu"),
        "delta_median_c": round(statistics.median(deltas), 2) if deltas else None,
        "median_abs_delta_c": round(statistics.median(abs_deltas), 2) if abs_deltas else None,
        "delta_p95_abs_c": percentile(abs_deltas, 95),
        "pct_abs_delta_ge_1c": round(100.0 * sum(1 for value in abs_deltas if value >= 1.0) / n, 1) if n else None,
        "pct_abs_delta_ge_2c": round(100.0 * sum(1 for value in abs_deltas if value >= 2.0) / n, 1) if n else None,
    }


def _get_first(row: dict, names: tuple[str, ...]):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8-sig") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def choose_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if Path(path).exists():
            return Path(path)
    return None


def parse_blocked_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        match_key = str(row.get("match_key") or "")
        parts = match_key.split("|")
        city = _get_first(row, ("city",)) or (parts[0] if len(parts) >= 1 else None)
        if str(city or "").lower() != CITY.lower():
            continue
        date_local = _get_first(row, ("date", "date_local", "target_date")) or (parts[1] if len(parts) >= 2 else None)
        condition = _get_first(row, ("condition", "condition_type")) or (parts[2] if len(parts) >= 3 else None)
        strike = _to_float(_get_first(row, ("strike", "strike_c", "threshold_c", "target_temp_c")) or (parts[3] if len(parts) >= 4 else None))
        outcome = _get_first(row, ("outcome", "resolution_outcome", "polymarket_outcome"))
        out.append(
            {
                "date_local": str(date_local) if date_local else None,
                "condition": str(condition).lower() if condition else None,
                "strike_c": strike,
                "outcome": str(outcome) if outcome is not None else None,
                "win_for_trader": row.get("win_for_trader"),
                "trader": row.get("trader"),
                "has_consensus": row.get("has_consensus"),
                "match_key": match_key,
            }
        )
    return out


def expected_outcome_for_blocked(row: dict, wu_high_c: float | None) -> str | None:
    if wu_high_c is None or row.get("strike_c") is None:
        return None
    condition = row.get("condition")
    strike = float(row["strike_c"])
    if condition == "exact":
        return "Yes" if float(wu_high_c) == strike else "No"
    if condition == "at_or_above":
        return "Yes" if float(wu_high_c) >= strike else "No"
    if condition == "at_or_below":
        return "Yes" if float(wu_high_c) <= strike else "No"
    return None


def build_blocked_table(blocked_rows: list[dict], wu: dict[str, float] | None) -> tuple[list[dict], dict]:
    table = []
    comparable = 0
    matched = 0
    for row in blocked_rows:
        wu_high = wu.get(row["date_local"]) if wu is not None and row.get("date_local") else None
        expected = expected_outcome_for_blocked(row, wu_high)
        actual = row.get("outcome")
        match = None
        if expected is not None and actual:
            comparable += 1
            match = expected.lower() == str(actual).lower()
            matched += 1 if match else 0
        table.append({**row, "wu_high_c": wu_high, "expected_outcome_from_wu": expected, "outcome_matches_wu": match})
    return table, {"blocked_rows": len(blocked_rows), "blocked_comparable": comparable, "blocked_outcome_matches_wu": matched}


def decide_verdict(metrics: dict, wu_status: str, blocked_metrics: dict) -> tuple[str, list[str]]:
    reasons = []
    if wu_status == "missing_fetcher":
        return "WU_FETCHER_MISSING", ["no reliable WU/ZBAA fetcher exists in repo and no --wu-csv was provided"]
    n = metrics.get("n_compared") or 0
    if n == 0:
        return "INSUFFICIENT_WU_DATA", ["no overlapping Open-Meteo/WU daily rows"]
    if n < OPUS_MIN_N:
        reasons.append(f"n_compared={n} < {OPUS_MIN_N}")
    median_abs = metrics.get("median_abs_delta_c")
    if median_abs is None or median_abs > OPUS_MAX_MEDIAN_ABS_DELTA_C:
        reasons.append(f"median_abs_delta_c={median_abs} > {OPUS_MAX_MEDIAN_ABS_DELTA_C}")
    pct_ge_1 = metrics.get("pct_abs_delta_ge_1c")
    if pct_ge_1 is None or pct_ge_1 > OPUS_MAX_PCT_ABS_DELTA_GE_1C:
        reasons.append(f"pct_abs_delta_ge_1c={pct_ge_1} > {OPUS_MAX_PCT_ABS_DELTA_GE_1C}")
    blocked_comparable = blocked_metrics.get("blocked_comparable") or 0
    blocked_matches = blocked_metrics.get("blocked_outcome_matches_wu") or 0
    if blocked_comparable < OPUS_BLOCKED_MATCH_TOTAL:
        reasons.append(f"blocked_days_comparable={blocked_comparable} < {OPUS_BLOCKED_MATCH_TOTAL}")
    elif blocked_matches < OPUS_BLOCKED_MATCH_REQUIRED:
        reasons.append(f"blocked_outcome_matches_wu={blocked_matches} < {OPUS_BLOCKED_MATCH_REQUIRED}")
    if reasons:
        return "PARITY_FAIL" if n >= OPUS_MIN_N else "INSUFFICIENT_WU_DATA", reasons
    return "PARITY_PASS", ["all Opus parity criteria met"]


def render_markdown(report: dict) -> str:
    metrics = report["metrics"]
    gamma = report.get("gamma_settlement") or {}
    lines = [
        "# Beijing Open-Meteo vs WU/ZBAA Source Parity Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"**Verdict:** **{report['verdict']}**",
        "",
        f"> {LOG_ONLY_DISCLAIMER}",
        "",
        "## Objective",
        "",
        "Compare Beijing Open-Meteo proxy daily maximum temperature against the Polymarket settlement source, Weather Underground ZBAA, before any Opus promotion review.",
        "",
        "## Sources Used",
        "",
        f"- City/ICAO: `{CITY}` / `{ICAO}`",
        f"- Open-Meteo archive: `temperature_2m_max`, lat `{LAT}`, lon `{LON}`, timezone `Asia/Shanghai`",
        f"- Weather Underground settlement source: `{WU_URL}`",
        f"- WU data status: `{report['wu_status']}`",
        f"- Blocked signals source: `{report.get('blocked_source') or 'not found'}`",
        f"- Gamma settlement derivation: `{gamma.get('verdict', 'not_run')}`",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| n compared | {metrics.get('n_compared')} |",
        f"| median delta C | {metrics.get('delta_median_c')} |",
        f"| median abs delta C | {metrics.get('median_abs_delta_c')} |",
        f"| p95 abs delta C | {metrics.get('delta_p95_abs_c')} |",
        f"| pct abs delta >= 1C | {metrics.get('pct_abs_delta_ge_1c')} |",
        f"| pct abs delta >= 2C | {metrics.get('pct_abs_delta_ge_2c')} |",
        "",
        "## Opus Criteria",
        "",
        "| Criterion | Status |",
        "|---|---|",
        f"| n >= {OPUS_MIN_N} | {'MET' if (metrics.get('n_compared') or 0) >= OPUS_MIN_N else 'NOT_MET'} |",
        f"| median abs delta <= {OPUS_MAX_MEDIAN_ABS_DELTA_C}C | {'MET' if metrics.get('median_abs_delta_c') is not None and metrics.get('median_abs_delta_c') <= OPUS_MAX_MEDIAN_ABS_DELTA_C else 'NOT_MET'} |",
        f"| pct abs delta >= 1C <= {OPUS_MAX_PCT_ABS_DELTA_GE_1C}% | {'MET' if metrics.get('pct_abs_delta_ge_1c') is not None and metrics.get('pct_abs_delta_ge_1c') <= OPUS_MAX_PCT_ABS_DELTA_GE_1C else 'NOT_MET'} |",
        f"| blocked days >= {OPUS_BLOCKED_MATCH_REQUIRED}/{OPUS_BLOCKED_MATCH_TOTAL} match WU outcome | {report['blocked_metrics'].get('blocked_outcome_matches_wu')}/{report['blocked_metrics'].get('blocked_comparable')} comparable |",
        "",
        "Reasons:",
    ]
    lines.extend(f"- {reason}" for reason in report["verdict_reasons"])
    lines.extend(["", "## Day By Day", "", "| Date | Open-Meteo max C | WU high C | Delta C | Status |", "|---|---:|---:|---:|---|"])
    for row in report["comparisons"]:
        lines.append(
            f"| {row['date_local']} | {row.get('open_meteo_max_c')} | {row.get('wu_high_c')} | {row.get('delta_c')} | {row.get('status')} |"
        )
    lines.extend(
        [
            "",
            "## Gamma-Derived Settlement Triage",
            "",
        ]
    )
    if gamma:
        gamma_metrics = gamma.get("metrics", {})
        lines.extend(
            [
                f"**Verdict:** **{gamma.get('verdict')}**",
                "",
                "This section infers settlement temperature from resolved Polymarket/Gamma exact markets only. It does not scrape WU and does not replace formal WU parity.",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| blocked exact dates | {gamma_metrics.get('blocked_exact_dates')} |",
                f"| dates compared | {gamma_metrics.get('n_dates_compared')} |",
                f"| median delta C | {gamma_metrics.get('delta_median_c')} |",
                f"| median abs delta C | {gamma_metrics.get('median_abs_delta_c')} |",
                f"| max abs delta C | {gamma_metrics.get('max_abs_delta_c')} |",
                f"| pct abs delta >= 1C | {gamma_metrics.get('pct_abs_delta_ge_1c')} |",
                f"| pct abs delta >= 2C | {gamma_metrics.get('pct_abs_delta_ge_2c')} |",
                "",
                "Reasons:",
            ]
        )
        lines.extend(f"- {reason}" for reason in gamma.get("verdict_reasons", []))
        lines.extend(
            [
                "",
                "| Date | Open-Meteo max C | Gamma settlement C | Delta C | Status | Evidence |",
                "|---|---:|---:|---:|---|---|",
            ]
        )
        for row in gamma.get("comparisons", []):
            lines.append(
                f"| {row.get('date_local')} | {row.get('open_meteo_max_c')} | {row.get('settlement_temp_c')} | {row.get('delta_c')} | {row.get('status')} | {row.get('evidence')} |"
            )
        if gamma.get("market_fetch_errors"):
            lines.extend(["", "Gamma fetch errors:"])
            lines.extend(f"- `{err.get('slug')}`: {err.get('error')}" for err in gamma.get("market_fetch_errors", []))
        if gamma.get("warnings"):
            lines.extend(["", "Gamma derivation warnings:"])
            lines.extend(f"- {warning}" for warning in gamma.get("warnings", []))
    else:
        lines.append("Not run. Use `--settlement-from-gamma` for quick triage from resolved exact markets.")
    lines.extend(
        [
            "",
            "## Blocked Signals Days",
            "",
            "| Date | Condition | Strike C | Outcome | WU high C | Expected From WU | Match | Trader | Consensus |",
            "|---|---|---:|---|---:|---|---|---|---|",
        ]
    )
    for row in report["blocked_table"]:
        lines.append(
            f"| {row.get('date_local')} | {row.get('condition')} | {row.get('strike_c')} | {row.get('outcome')} | {row.get('wu_high_c')} | {row.get('expected_outcome_from_wu')} | {row.get('outcome_matches_wu')} | {row.get('trader')} | {row.get('has_consensus')} |"
        )
    lines.extend(
        [
            "",
            "## Pass/Fail",
            "",
            f"`{report['verdict']}`. This dossier remains LOG_ONLY and requires Opus review before any operational next step.",
            "",
            "## Next Trigger For Opus",
            "",
            "Provide a reliable WU/ZBAA daily-high dataset or repo-approved WU fetcher, rerun this tool, and ask Opus to review the parity dossier only if the Opus criteria are met.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(args) -> dict:
    start = parse_date(args.start) if args.start else None
    end = parse_date(args.end) if args.end else None
    if start is None or end is None:
        start, end = default_window(args.days)
    if start > end:
        raise SystemExit("--start must be <= --end")

    if args.open_meteo_csv:
        open_meteo = load_daily_csv(Path(args.open_meteo_csv), ("open_meteo_max_c", "temperature_2m_max", "max_c"))
        open_meteo_status = "csv"
    else:
        open_meteo = fetch_open_meteo_daily(start, end)
        open_meteo_status = "archive_api"

    if args.wu_csv:
        wu = load_daily_csv(Path(args.wu_csv), ("wu_high_c", "high_c", "temperature_high_c", "max_c"))
        wu_status = "csv"
    else:
        wu = None
        wu_status = "missing_fetcher"

    blocked_path = Path(args.blocked_resolutions) if args.blocked_resolutions else choose_existing(DEFAULT_BLOCKED_INPUTS)
    blocked_rows = parse_blocked_rows(load_jsonl(blocked_path)) if blocked_path and blocked_path.exists() else []

    comparisons = build_comparisons(iter_dates(start, end), open_meteo, wu)
    metrics = compute_metrics(comparisons)
    blocked_table, blocked_metrics = build_blocked_table(blocked_rows, wu)
    verdict, reasons = decide_verdict(metrics, wu_status, blocked_metrics)
    gamma_settlement = None
    if getattr(args, "settlement_from_gamma", False):
        gamma_settlement = build_gamma_settlement_comparisons(
            blocked_rows,
            open_meteo,
            neighbor_radius=getattr(args, "gamma_neighbor_radius", 3),
        )

    return {
        "generated_at": _now_iso(),
        "city": CITY,
        "icao": ICAO,
        "lat": LAT,
        "lon": LON,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "open_meteo_status": open_meteo_status,
        "wu_status": wu_status,
        "blocked_source": str(blocked_path) if blocked_path else None,
        "metrics": metrics,
        "blocked_metrics": blocked_metrics,
        "comparisons": [row.__dict__ for row in comparisons],
        "blocked_table": blocked_table,
        "gamma_settlement": gamma_settlement,
        "verdict": verdict,
        "verdict_reasons": reasons,
        "log_only": True,
    }


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", help="Start date YYYY-MM-DD. Default: today-60d through yesterday.")
    parser.add_argument("--end", help="End date YYYY-MM-DD. Default: yesterday.")
    parser.add_argument("--days", type=int, default=60, help="Default trailing window length when --start/--end omitted.")
    parser.add_argument("--open-meteo-csv", help="Optional CSV fixture/manual file with date,open_meteo_max_c.")
    parser.add_argument("--wu-csv", help="Optional manual WU/ZBAA CSV with date,wu_high_c. No WU scraping is attempted.")
    parser.add_argument(
        "--settlement-from-gamma",
        action="store_true",
        help="Derive quick triage settlement temps from resolved Polymarket/Gamma exact markets. No WU scraping.",
    )
    parser.add_argument(
        "--gamma-neighbor-radius",
        type=int,
        default=3,
        help="When deriving settlement from Gamma, probe exact slugs from min(blocked strike)-N to max(blocked strike)+N per date.",
    )
    parser.add_argument("--blocked-resolutions", help="Path to blocked_signals_resolutions.jsonl.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--no-write-json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    md = render_markdown(report)
    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8", newline="\n")
    if not args.no_write_json:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print_payload = {"verdict": report["verdict"], "wu_status": report["wu_status"], "md_out": str(md_path)}
    if report.get("gamma_settlement"):
        print_payload["gamma_verdict"] = report["gamma_settlement"]["verdict"]
    print(json.dumps(print_payload, ensure_ascii=False))
    allowed = {
        "PARITY_PASS",
        "WU_FETCHER_MISSING",
        "INSUFFICIENT_WU_DATA",
        "NEEDS_MANUAL_WU_CHECK",
        "PARITY_FAIL",
    }
    gamma_allowed = {
        "SETTLEMENT_GAMMA_PARITY_PASS",
        "SETTLEMENT_GAMMA_PARITY_FAIL",
        "INSUFFICIENT_GAMMA_MARKETS",
        "GAMMA_SETTLEMENT_DERIVATION_UNRELIABLE",
    }
    gamma_verdict = (report.get("gamma_settlement") or {}).get("verdict")
    return 0 if report["verdict"] in allowed and (gamma_verdict is None or gamma_verdict in gamma_allowed) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
