#!/usr/bin/env python3
"""LOG_ONLY activity profiler for already-followed Polymarket traders."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_API_URL = os.getenv("DATA_API_URL", "https://data-api.polymarket.com").rstrip("/")
DEFAULT_TRADERS_DB = REPO_ROOT / "traders_db.json"
DEFAULT_TRADERS_INTELLIGENCE = REPO_ROOT / "data" / "traders_intelligence.json"
DEFAULT_SNAPSHOT_DIR = REPO_ROOT / "data" / "traders_intelligence" / "activity_snapshots"
SCHEMA_VERSION = "activity-profile-v0"
COMPARABLE_CITIES = {"Shanghai", "Tokyo", "Buenos Aires", "Ankara"}
COMPARABLE_CONDITIONS = {"exact", "at_or_above", "at_or_below"}
DISQUALIFYING_LABELS = {
    "BASKET_BURST",
    "HIGH_PRICE_ACTIVITY",
    "FREQUENT_BUY_SELL_ROTATION",
    "RANGE_DOMINANT",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LOG_ONLY profile of already-followed trader Activity API fills."
    )
    parser.add_argument("--external-report", help="JSON from traders_intelligence_report --external-observability.")
    parser.add_argument(
        "--cohort",
        choices=("external-report", "local-registry", "union"),
        help=(
            "Cohort to analyze. Default is external-report when --external-report is provided, "
            "otherwise local-registry."
        ),
    )
    parser.add_argument("--wallets", help="Optional csv or @file wallet filter.")
    parser.add_argument("--window-hours", type=int, default=168)
    parser.add_argument("--burst-window-sec", type=int, default=120)
    parser.add_argument("--burst-min-fills", type=int, default=4)
    parser.add_argument("--high-price-threshold", type=float, default=0.95)
    parser.add_argument("--rotation-window-min", type=int, default=60)
    parser.add_argument("--max-wallets", type=int, default=30)
    parser.add_argument("--max-fills-per-wallet", type=int, default=1000)
    parser.add_argument("--rate-limit-ms", type=int, default=250)
    parser.add_argument("--format", choices=("md", "json"), default="md")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--snapshot-dir", default=str(DEFAULT_SNAPSHOT_DIR))
    parser.add_argument("--traders-db", default=str(DEFAULT_TRADERS_DB))
    parser.add_argument("--traders-intelligence", default=str(DEFAULT_TRADERS_INTELLIGENCE))
    return parser.parse_args(argv)


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def normalize_wallet(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if text.startswith("0x") and len(text) == 42:
        return text
    return None


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_ts(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = int(value)
        return ts // 1000 if ts > 10_000_000_000 else ts
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return parse_ts(int(text))
    try:
        return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def iso_from_ts(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 4)
    rank = (len(ordered) - 1) * pct
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return round(ordered[low], 4)
    weight = rank - low
    return round(ordered[low] * (1 - weight) + ordered[high] * weight, 4)


def top_counter(counter: Counter, n: int = 5) -> list[dict[str, Any]]:
    return [{"value": key, "count": count} for key, count in counter.most_common(n)]


def should_bypass_proxy_env() -> bool:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        value = os.getenv(name, "")
        if "127.0.0.1:9" in value or "localhost:9" in value:
            return True
    return False


def request_json(url: str, timeout: int = 20) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "traders-activity-profile/0.1"})
    if should_bypass_proxy_env():
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        response = opener.open(request, timeout=timeout)
    else:
        response = urllib.request.urlopen(request, timeout=timeout)
    with response as resp:
        return json.loads(resp.read().decode("utf-8"))


def rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("activity", "data", "results", "items"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def activity_url(wallet: str, side: str, start_ts: int, limit: int, offset: int) -> str:
    params = urllib.parse.urlencode(
        {
            "user": wallet,
            "limit": str(limit),
            "offset": str(offset),
            "startTs": str(start_ts),
            "start_ts": str(start_ts),
            "type": "TRADE",
            "side": side,
        }
    )
    return f"{DATA_API_URL}/activity?{params}"


def split_fill_caps(max_fills_per_wallet: int) -> tuple[int, int]:
    buy_cap = max(1, max_fills_per_wallet // 2)
    sell_cap = max(1, max_fills_per_wallet - buy_cap)
    return buy_cap, sell_cap


def query_activity_side(
    wallet: str,
    side: str,
    start_ts: int,
    cap: int,
    rate_limit_ms: int,
) -> tuple[str, list[dict[str, Any]], str | None, bool]:
    rows: list[dict[str, Any]] = []
    offset = 0
    page_limit = min(500, max(1, cap))
    while len(rows) < cap:
        limit = min(page_limit, cap - len(rows))
        url = activity_url(wallet, side, start_ts, limit, offset)
        last_error: str | None = None
        page: list[dict[str, Any]] | None = None
        for attempt in range(2):
            try:
                page = rows_from_payload(request_json(url))
                break
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP {exc.code}: {exc.reason}"
                if exc.code != 429 or attempt == 1:
                    break
                time.sleep(max(rate_limit_ms / 1000.0, 0.25))
            except Exception as exc:
                last_error = str(exc)
                if attempt == 1:
                    break
                time.sleep(max(rate_limit_ms / 1000.0, 0.25))
        if page is None:
            return "failed", rows, last_error, False
        rows.extend(page)
        if len(page) < limit:
            break
        offset += len(page)
        if rate_limit_ms > 0:
            time.sleep(rate_limit_ms / 1000.0)
    capped = len(rows) >= cap
    return ("ok_capped" if capped else "ok_complete"), rows[:cap], None, capped


MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)


def normalize_city(city: str) -> str:
    city = re.sub(r"\s+", " ", city.strip(" -?:"))
    aliases = {"NYC": "New York City"}
    return aliases.get(city, city)


def parse_market_text(text: str) -> dict[str, Any]:
    cleaned = urllib.parse.unquote(str(text or "")).replace("-", " ")
    range_match = re.search(
        rf"temperature in (.+?) be between\s+(-?\d+(?:\.\d+)?)\s*(?:-|to|and)\s*(-?\d+(?:\.\d+)?)\s*°?\s*([CF]).*?(?:on\s+)?({MONTHS})\s+(\d+)",
        cleaned,
        re.IGNORECASE,
    )
    if range_match:
        return {
            "city": normalize_city(range_match.group(1)),
            "event_date": f"{range_match.group(5).title()} {range_match.group(6)}",
            "condition": "range",
            "threshold": as_float(range_match.group(2)),
            "threshold_high": as_float(range_match.group(3)),
            "unit": range_match.group(4).upper(),
        }
    match = re.search(
        rf"temperature in (.+?) (?:be |on )(-?\d+(?:\.\d+)?)\s*°?\s*([CF])(?:\s+or\s+(below|higher|above))?.*?(?:on\s+)?({MONTHS})\s+(\d+)",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        condition = "exact"
        mod = (match.group(4) or "").lower()
        if mod == "below":
            condition = "at_or_below"
        elif mod in {"higher", "above"}:
            condition = "at_or_above"
        return {
            "city": normalize_city(match.group(1)),
            "event_date": f"{match.group(5).title()} {match.group(6)}",
            "condition": condition,
            "threshold": as_float(match.group(2)),
            "threshold_high": None,
            "unit": match.group(3).upper(),
        }
    slug_text = str(text or "").lower()
    slug_market = re.search(
        r"(?:highest-)?temperature-in-(.+?)-on-([a-z]+)-(\d{1,2})-(20\d{2})-(-?\d+)(?:-(\d+))?([cf])?(?:-|$)",
        slug_text,
    )
    if slug_market:
        city = normalize_city(slug_market.group(1).replace("-", " ").title())
        high = as_float(slug_market.group(6))
        return {
            "city": city,
            "event_date": f"{slug_market.group(2).title()} {slug_market.group(3)} {slug_market.group(4)}",
            "condition": "range" if high is not None else "exact",
            "threshold": as_float(slug_market.group(5)),
            "threshold_high": high,
            "unit": (slug_market.group(7) or "").upper() or None,
        }
    slug_match = re.search(
        r"(?:temperature|temp)(?:-in)?-([a-z0-9-]+?)-(?:be-)?(?:between-)?(-?\d+)(?:-and-|-to-)?(-?\d+)?-?([cf])?(?:-|$)",
        slug_text,
    )
    if slug_match:
        city = normalize_city(slug_match.group(1).replace("-", " ").title())
        high = as_float(slug_match.group(3))
        return {
            "city": city,
            "event_date": None,
            "condition": "range" if high is not None else "exact",
            "threshold": as_float(slug_match.group(2)),
            "threshold_high": high,
            "unit": (slug_match.group(4) or "").upper() or None,
        }
    return {"city": None, "event_date": None, "condition": None, "threshold": None, "threshold_high": None, "unit": None}


def first_value(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row and row.get(name) not in (None, ""):
            return row.get(name)
    return None


def normalize_fill(row: dict[str, Any], forced_side: str) -> dict[str, Any]:
    slug = first_value(row, ("slug", "marketSlug", "market_slug", "conditionSlug")) or ""
    title = first_value(row, ("title", "question", "marketTitle", "market_title", "eventTitle")) or ""
    parsed = parse_market_text(str(title or slug))
    ts = parse_ts(first_value(row, ("timestamp", "ts", "time", "createdAt", "created_at", "transactionTimestamp")))
    price = as_float(first_value(row, ("price", "avgPrice", "avg_price")))
    size = as_float(first_value(row, ("size", "amount", "shares")))
    usdc = as_float(first_value(row, ("usdcSize", "usdc_size", "cashAmount", "notional", "value")))
    if usdc is None and price is not None and size is not None:
        usdc = price * size
    return {
        "ts": ts,
        "iso_ts": iso_from_ts(ts),
        "slug": str(slug or ""),
        "event_slug": str(first_value(row, ("eventSlug", "event_slug")) or ""),
        "market_id": str(first_value(row, ("market", "marketId", "market_id", "conditionId", "condition_id")) or ""),
        "city": parsed["city"],
        "event_date": parsed.get("event_date"),
        "condition": parsed["condition"],
        "threshold": parsed["threshold"],
        "threshold_high": parsed["threshold_high"],
        "unit": parsed["unit"],
        "outcome": str(first_value(row, ("outcome", "outcomeName", "outcome_name")) or ""),
        "side": str(first_value(row, ("side",)) or forced_side).upper(),
        "price": price,
        "size": size,
        "usdcSize": round(usdc, 4) if usdc is not None else None,
        "resolution_ts": parse_ts(first_value(row, ("resolution_ts", "resolutionTs", "resolvedAt", "end_date", "endDate"))),
    }


def example_from_fill(fill: dict[str, Any]) -> dict[str, Any]:
    return {
        "ts": fill.get("iso_ts"),
        "city": fill.get("city"),
        "condition": fill.get("condition"),
        "threshold": fill.get("threshold"),
        "outcome": fill.get("outcome"),
        "side": fill.get("side"),
        "price": fill.get("price"),
        "usdcSize": fill.get("usdcSize"),
        "slug": fill.get("slug"),
    }


def market_key(fill: dict[str, Any]) -> str:
    return fill.get("market_id") or fill.get("slug") or "|".join(
        str(fill.get(key) or "") for key in ("event_slug", "city", "condition", "threshold", "outcome")
    )


def event_date_key(fill: dict[str, Any]) -> str:
    if fill.get("city") and fill.get("event_date"):
        return f"{fill.get('city')}|{fill.get('event_date')}"
    slug = fill.get("event_slug") or fill.get("slug") or market_key(fill)
    date_match = re.search(r"20\d{2}-\d{2}-\d{2}", str(slug))
    date = date_match.group(0) if date_match else ""
    return "|".join(str(fill.get(key) or "") for key in ("event_slug", "city")) + f"|{date}"


def basket_leg(fill: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (fill.get("condition"), fill.get("threshold"), fill.get("outcome"))


def basket_groups(fills: list[dict[str, Any]]) -> dict[str, set[tuple[Any, Any, Any]]]:
    groups: dict[str, set[tuple[Any, Any, Any]]] = defaultdict(set)
    for fill in fills:
        key = event_date_key(fill)
        leg = basket_leg(fill)
        if key and fill.get("city") and fill.get("event_date") and (fill.get("threshold") is not None or fill.get("outcome")):
            groups[key].add(leg)
    return groups


def burst_has_basket_leg(burst: dict[str, Any], buys: list[dict[str, Any]]) -> bool:
    first = parse_ts(burst.get("first_ts"))
    last = parse_ts(burst.get("last_ts"))
    if first is None or last is None:
        return False
    grouped: dict[str, set[tuple[Any, Any, Any]]] = defaultdict(set)
    for fill in buys:
        ts = fill.get("ts")
        if ts is None or ts < first or ts > last:
            continue
        key = event_date_key(fill)
        if fill.get("city") and fill.get("event_date"):
            grouped[key].add(basket_leg(fill))
    return any(len(legs) >= 2 for legs in grouped.values())


def detect_bursts(buys: list[dict[str, Any]], window_sec: int, min_fills: int) -> list[dict[str, Any]]:
    ordered = sorted([fill for fill in buys if fill.get("ts") is not None], key=lambda row: row["ts"])
    bursts: list[dict[str, Any]] = []
    for idx, first in enumerate(ordered):
        group = [row for row in ordered[idx:] if row["ts"] - first["ts"] <= window_sec]
        if len(group) < min_fills:
            continue
        if bursts and first["ts"] <= bursts[-1]["last_ts_epoch"]:
            continue
        cities = Counter(row.get("city") for row in group if row.get("city"))
        first_ts = group[0]["ts"]
        last_ts = group[-1]["ts"]
        bursts.append(
            {
                "city": cities.most_common(1)[0][0] if cities else None,
                "date": iso_from_ts(first_ts)[:10] if first_ts else None,
                "n_fills": len(group),
                "n_slugs": len({row.get("slug") for row in group if row.get("slug")}),
                "window_sec": last_ts - first_ts,
                "first_ts": iso_from_ts(first_ts),
                "last_ts": iso_from_ts(last_ts),
                "last_ts_epoch": last_ts,
            }
        )
    for burst in bursts:
        burst.pop("last_ts_epoch", None)
    return bursts


def detect_rotations(
    buys: list[dict[str, Any]], sells: list[dict[str, Any]], window_min: int
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    sell_groups = defaultdict(list)
    for sell in sells:
        if sell.get("ts") is not None:
            sell_groups[(market_key(sell), sell.get("outcome"))].append(sell)
    for rows in sell_groups.values():
        rows.sort(key=lambda row: row["ts"])
    for buy in sorted([row for row in buys if row.get("ts") is not None], key=lambda row: row["ts"]):
        for sell in sell_groups.get((market_key(buy), buy.get("outcome")), []):
            lag = sell["ts"] - buy["ts"]
            if 0 <= lag <= window_min * 60:
                examples.append(
                    {
                        "market_id": buy.get("market_id"),
                        "slug": buy.get("slug"),
                        "outcome": buy.get("outcome"),
                        "buy_ts": buy.get("iso_ts"),
                        "sell_ts": sell.get("iso_ts"),
                        "lag_min": round(lag / 60, 2),
                        "buy_price": buy.get("price"),
                        "sell_price": sell.get("price"),
                    }
                )
                break
    return examples


def detect_position_building(buys: list[dict[str, Any]]) -> bool:
    groups = defaultdict(list)
    for buy in buys:
        if buy.get("ts") is not None:
            groups[(market_key(buy), buy.get("outcome"))].append(buy)
    for rows in groups.values():
        rows.sort(key=lambda row: row["ts"])
        for idx, first in enumerate(rows):
            group = [row for row in rows[idx:] if row["ts"] - first["ts"] <= 1800]
            prices = {row.get("price") for row in group if row.get("price") is not None}
            if len(group) >= 3 and len(prices) >= 2:
                return True
    return False


def condition_share_by_market(fills: list[dict[str, Any]]) -> tuple[Counter, int]:
    market_conditions: dict[str, str] = {}
    for fill in fills:
        key = market_key(fill)
        if key and fill.get("condition"):
            market_conditions.setdefault(key, fill["condition"])
    return Counter(market_conditions.values()), len(market_conditions)


def build_labels(
    fills: list[dict[str, Any]],
    buys: list[dict[str, Any]],
    sells: list[dict[str, Any]],
    bursts: list[dict[str, Any]],
    rotations: list[dict[str, Any]],
    high_price_ratio: float,
    high_price_threshold: float,
    lead_time: dict[str, Any],
) -> list[str]:
    labels: list[str] = []
    if len(fills) < 3:
        return ["UNKNOWN_STYLE"]
    markets = defaultdict(set)
    baskets = basket_groups(fills)
    for fill in fills:
        key = market_key(fill)
        if key:
            markets[key].add((fill.get("outcome"), fill.get("threshold")))
    if markets:
        single_share = sum(1 for values in markets.values() if len(values) == 1) / len(markets)
        if single_share >= 0.70:
            labels.append("SINGLE_OUTCOME_DIRECTIONAL")
        multi_share = sum(1 for values in baskets.values() if len(values) >= 2) / max(len(baskets), 1)
        if multi_share >= 0.30:
            labels.append("MULTI_OUTCOME_BASKET")
    if "MULTI_OUTCOME_BASKET" in labels and any(burst_has_basket_leg(burst, buys) for burst in bursts):
        labels.append("BASKET_BURST")
    if detect_position_building(buys):
        labels.append("POSITION_BUILDING")
    if buys and high_price_ratio >= 0.10:
        labels.append("HIGH_PRICE_ACTIVITY")
    if (
        "HIGH_PRICE_ACTIVITY" in labels
        and lead_time.get("status") == "ok"
        and lead_time.get("p50_hours") is not None
        and lead_time["p50_hours"] <= 6
    ):
        labels.append("NEAR_RESOLUTION_PROVISIONAL")
    if sells:
        labels.append("BUY_SELL_PRESENT")
    if len(rotations) >= 3:
        labels.append("FREQUENT_BUY_SELL_ROTATION")
    condition_counts, n_markets = condition_share_by_market(fills)
    if n_markets and condition_counts.get("range", 0) / n_markets > 0.50:
        labels.append("RANGE_DOMINANT")
    return labels


def lane_suggestion(
    labels: list[str],
    fills: list[dict[str, Any]],
    parse_unknown_ratio: float,
    query_status: str,
    sell_query_status: str,
) -> tuple[str, str, bool]:
    mixed_style = (
        "SINGLE_OUTCOME_DIRECTIONAL" in labels
        and any(label in labels for label in ("MULTI_OUTCOME_BASKET", "BASKET_BURST", "HIGH_PRICE_ACTIVITY", "POSITION_BUILDING"))
    )
    if "UNKNOWN_STYLE" in labels:
        lane = "WAITING_EVIDENCE"
        reason = "fewer than 3 fills in the selected window"
    elif mixed_style:
        lane = "REVIEW_REQUIRED"
        reason = "mixed_style_evidence"
    elif any(label in labels for label in DISQUALIFYING_LABELS):
        lane = "LEARNING_REFERENCE_CANDIDATE"
        reason = "provisional learning pattern present: " + ", ".join(label for label in labels if label in DISQUALIFYING_LABELS)
    else:
        condition_counts, n_markets = condition_share_by_market(fills)
        comparable_condition_share = (
            sum(count for cond, count in condition_counts.items() if cond in COMPARABLE_CONDITIONS) / n_markets
            if n_markets
            else 0.0
        )
        cities = {fill.get("city") for fill in fills if fill.get("city")}
        if cities & COMPARABLE_CITIES and comparable_condition_share >= 0.70:
            lane = "COMPARABLE_CANDIDATE"
            reason = "city overlap with comparable set and >=70% comparable conditions"
        else:
            lane = "REVIEW_REQUIRED"
            reason = "insufficient match for provisional comparable lane"
    incompatible_pairs = [
        {"SINGLE_OUTCOME_DIRECTIONAL", "BASKET_BURST"},
        {"SINGLE_OUTCOME_DIRECTIONAL", "MULTI_OUTCOME_BASKET"},
    ]
    incompatible = any(pair.issubset(set(labels)) for pair in incompatible_pairs)
    manual = (
        lane == "REVIEW_REQUIRED"
        or incompatible
        or mixed_style
        or parse_unknown_ratio > 0.20
        or query_status not in {"ok_complete", "ok_capped"}
        or sell_query_status not in {"ok_complete", "ok_capped"}
    )
    return lane, reason, manual


def external_not_loaded() -> dict[str, Any]:
    return {
        "alias": "not_loaded",
        "display_name": "not_loaded",
        "profile_url": "not_loaded",
        "pnl_weather_all": "not_loaded",
        "volume": "not_loaded",
    }


def extract_external_fields(row: dict[str, Any]) -> dict[str, Any]:
    external = row.get("external_observability") if isinstance(row.get("external_observability"), dict) else {}
    profile = external.get("public_profile", {}) if isinstance(external.get("public_profile"), dict) else {}
    weather = external.get("leaderboard_weather_all", {}) if isinstance(external.get("leaderboard_weather_all"), dict) else {}
    overall = external.get("leaderboard_overall_all", {}) if isinstance(external.get("leaderboard_overall_all"), dict) else {}
    return {
        "alias": row.get("alias") or row.get("pseudonym") or profile.get("pseudonym") or row.get("name"),
        "display_name": row.get("display_name") or profile.get("userName") or profile.get("name") or row.get("pseudonym"),
        "profile_url": row.get("profile_url") or profile.get("profile_url"),
        "pnl_weather_all": row.get("pnl_weather_all") or weather.get("pnl"),
        "volume": row.get("volume") or row.get("vol") or overall.get("vol") or weather.get("vol"),
    }


def iter_external_traders(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("traders") or payload.get("wallets") or []
        return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def cohort_source(sources: list[str]) -> str:
    source_set = set(sources)
    if "external_report" in source_set and "traders_db" in source_set:
        return "both"
    if "external_report" in source_set:
        return "external_report"
    if "traders_db" in source_set:
        return "traders_db"
    return "local_intelligence_only"


def resolve_cohort_mode(args: argparse.Namespace) -> str:
    if args.cohort:
        if args.cohort == "external-report" and not args.external_report:
            raise SystemExit("--cohort external-report requires --external-report <path>")
        return args.cohort
    return "external-report" if args.external_report else "local-registry"


def build_cohort(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cohort_mode = resolve_cohort_mode(args)
    cohort: dict[str, dict[str, Any]] = {}
    source_mentions = 0
    external_rows = iter_external_traders(load_json(args.external_report)) if args.external_report else []
    external_wallets: set[str] = set()
    external_cohort: dict[str, dict[str, Any]] = {}
    local_registry_cohort: dict[str, dict[str, Any]] = {}
    for row in external_rows:
        external = row.get("external_observability") if isinstance(row.get("external_observability"), dict) else {}
        wallet = normalize_wallet(
            row.get("wallet")
            or row.get("address")
            or row.get("proxy_wallet")
            or external.get("proxy_wallet")
            or external.get("proxyWallet")
        )
        if not wallet:
            continue
        source_mentions += 1
        external_wallets.add(wallet)
        fields = extract_external_fields(row)
        external_cohort[wallet] = {
            "wallet": wallet,
            "alias": fields.get("alias") or wallet[:10],
            "display_name": fields.get("display_name"),
            "external": fields,
            "sources": ["external_report"],
        }
    traders_db = load_json(args.traders_db) if Path(args.traders_db).exists() else {}
    for name, row in (traders_db.get("traders", {}) if isinstance(traders_db, dict) else {}).items():
        if not isinstance(row, dict):
            continue
        wallet = normalize_wallet(row.get("address") or row.get("proxy_wallet"))
        if not wallet:
            continue
        source_mentions += 1
        entry = local_registry_cohort.setdefault(
            wallet,
            {
                "wallet": wallet,
                "alias": row.get("pseudonym") or name or wallet[:10],
                "display_name": row.get("pseudonym") or name,
                "external": external_not_loaded(),
                "sources": [],
            },
        )
        entry["sources"].append("traders_db")
    intelligence = load_json(args.traders_intelligence) if Path(args.traders_intelligence).exists() else {}
    for row in intelligence.get("traders", []) if isinstance(intelligence, dict) else []:
        if not isinstance(row, dict):
            continue
        wallet = normalize_wallet(row.get("proxy_wallet") or row.get("address"))
        if not wallet:
            continue
        source_mentions += 1
        entry = local_registry_cohort.setdefault(
            wallet,
            {
                "wallet": wallet,
                "alias": row.get("pseudonym") or wallet[:10],
                "display_name": row.get("pseudonym"),
                "external": external_not_loaded(),
                "sources": [],
            },
        )
        entry["sources"].append("traders_intelligence")
    if cohort_mode == "external-report":
        cohort = dict(external_cohort)
        source_mentions = len(external_wallets)
    elif cohort_mode == "local-registry":
        cohort = dict(local_registry_cohort)
        source_mentions = sum(len(set(entry.get("sources", []))) for entry in cohort.values())
    else:
        cohort = dict(external_cohort)
        for wallet, local_entry in local_registry_cohort.items():
            if wallet in cohort:
                entry = cohort[wallet]
                for source in local_entry.get("sources", []):
                    entry.setdefault("sources", []).append(source)
            else:
                entry = dict(local_entry)
                entry["sources"] = list(local_entry.get("sources", []))
                cohort[wallet] = entry
    wallet_filter = load_wallet_filter(args.wallets)
    for entry in cohort.values():
        entry["sources"] = sorted(set(entry.get("sources", [])))
        entry["cohort_source"] = cohort_source(entry["sources"])
    rows = list(cohort.values())
    before_wallet_filter = len(rows)
    if wallet_filter is not None:
        rows = [row for row in rows if row["wallet"] in wallet_filter]
    after_wallet_filter = len(rows)
    rows.sort(key=lambda row: (0 if "external_report" in row["sources"] else 1, str(row["alias"]), row["wallet"]))
    truncated = rows[args.max_wallets :]
    analyzed = rows[: args.max_wallets]
    meta = {
        "cohort_mode": cohort_mode,
        "cohort_description": {
            "external-report": "Only wallets resolved from --external-report.",
            "local-registry": "Local registry wallets from traders_db.json and data/traders_intelligence.json.",
            "union": "Union of --external-report, traders_db.json, and data/traders_intelligence.json.",
        }[cohort_mode],
        "cohort_warning": (
            "local-registry/union may include discovered or historical registry wallets; this repo cannot prove they are actively followed from these files alone."
            if cohort_mode in {"local-registry", "union"}
            else None
        ),
        "n_external_report_rows": len(external_rows),
        "n_external_report_wallets": len(external_wallets),
        "n_external_report_missing_wallets": max(len(external_rows) - len(external_wallets), 0),
        "n_local_registry_added": sum(1 for row in analyzed if row["cohort_source"] == "traders_db"),
        "n_deduplicated": max(source_mentions - len(cohort), 0),
        "n_wallets_before_wallet_filter": before_wallet_filter,
        "n_wallets_after_wallet_filter": after_wallet_filter,
        "n_wallets_analyzed": len(analyzed),
        "n_wallets_available_after_filter": len(rows),
        "max_wallets_truncated": len(truncated) > 0,
        "max_wallets_truncated_count": len(truncated),
        "max_wallets_truncated_examples": [
            {"alias": row.get("alias"), "wallet": row.get("wallet"), "cohort_source": row.get("cohort_source")}
            for row in truncated[:10]
        ],
        "cohort_source_counts": dict(Counter(row["cohort_source"] for row in analyzed)),
    }
    return analyzed, meta


def load_wallet_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    if value.startswith("@"):
        text = Path(value[1:]).read_text(encoding="utf-8-sig")
    else:
        text = value
    wallets = {normalize_wallet(item.strip()) for item in re.split(r"[,\s]+", text) if item.strip()}
    return {wallet for wallet in wallets if wallet}


def profile_wallet(entry: dict[str, Any], args: argparse.Namespace, now_ts: int) -> dict[str, Any]:
    wallet = entry["wallet"]
    start_ts = now_ts - args.window_hours * 3600
    buy_cap, sell_cap = split_fill_caps(args.max_fills_per_wallet)
    buy_status, buy_rows, buy_error, buy_capped = query_activity_side(wallet, "BUY", start_ts, buy_cap, args.rate_limit_ms)
    if args.rate_limit_ms > 0:
        time.sleep(args.rate_limit_ms / 1000.0)
    sell_status, sell_rows, sell_error, sell_capped = query_activity_side(wallet, "SELL", start_ts, sell_cap, args.rate_limit_ms)
    buys = [normalize_fill(row, "BUY") for row in buy_rows]
    sells = [normalize_fill(row, "SELL") for row in sell_rows]
    fills = sorted(buys + sells, key=lambda row: row.get("ts") or 0)
    parse_unknown = sum(1 for fill in fills if not fill.get("city") or not fill.get("condition"))
    n_fills = len(fills)
    parse_unknown_ratio = round(parse_unknown / n_fills, 4) if n_fills else 0.0
    buy_prices = [fill["price"] for fill in buys if fill.get("price") is not None]
    high_price_fills = [fill for fill in buys if fill.get("price") is not None and fill["price"] >= args.high_price_threshold]
    high_price_ratio = len(high_price_fills) / len(buys) if buys else 0.0
    bursts = detect_bursts(buys, args.burst_window_sec, args.burst_min_fills)
    side_queries_ok = buy_status in {"ok_complete", "ok_capped"} and sell_status in {"ok_complete", "ok_capped"}
    rotations = detect_rotations(buys, sells, args.rotation_window_min) if side_queries_ok else []
    lead_hours = [
        (fill["resolution_ts"] - fill["ts"]) / 3600
        for fill in fills
        if fill.get("resolution_ts") is not None and fill.get("ts") is not None and fill["resolution_ts"] >= fill["ts"]
    ]
    lead_time = (
        {"status": "ok", "p25_hours": percentile(lead_hours, 0.25), "p50_hours": percentile(lead_hours, 0.50), "n": len(lead_hours)}
        if lead_hours
        else {"status": "not_available", "note": "not_available"}
    )
    labels = build_labels(fills, buys, sells, bursts, rotations, high_price_ratio, args.high_price_threshold, lead_time)
    parse_critical = parse_unknown_ratio > 0.50 and n_fills >= 3
    if buy_status == "failed" and sell_status == "failed":
        query_status = "failed"
    elif buy_status == "failed" or sell_status == "failed" or parse_critical:
        query_status = "partial"
    elif buy_capped or sell_capped:
        query_status = "ok_capped"
    else:
        query_status = "ok_complete"
    lane, reason, manual = lane_suggestion(labels, fills, parse_unknown_ratio, query_status, sell_status)
    if query_status in {"partial", "failed"} or buy_capped or sell_capped:
        manual = True
    confidence = "high" if n_fills >= 20 else "medium" if n_fills >= 5 else "low" if n_fills >= 3 else "insufficient_data"
    condition_counts, n_condition_markets = condition_share_by_market(fills)
    return {
        "wallet": wallet,
        "alias": entry.get("alias"),
        "display_name": entry.get("display_name"),
        "profile_url": entry.get("external", {}).get("profile_url"),
        "external": entry.get("external", external_not_loaded()),
        "sources": sorted(set(entry.get("sources", []))),
        "cohort_source": entry.get("cohort_source", cohort_source(entry.get("sources", []))),
        "query_status": query_status,
        "buy_query_status": buy_status,
        "sell_query_status": sell_status,
        "buy_capped": buy_capped,
        "sell_capped": sell_capped,
        "max_fills_buy": buy_cap,
        "max_fills_sell": sell_cap,
        "coverage_note": (
            "activity_count_high_but_capped_not_complete"
            if buy_capped or sell_capped
            else "activity_count_confidence_not_coverage_guarantee"
        ),
        "api_errors": {"buy": buy_error, "sell": sell_error},
        "metrics": {
            "n_fills": n_fills,
            "counters": {"BUY": len(buys), "SELL": len(sells)},
            "n_markets": len({market_key(fill) for fill in fills if market_key(fill)}),
            "n_slugs": len({fill.get("slug") for fill in fills if fill.get("slug")}),
            "usdc_total": round(sum(fill.get("usdcSize") or 0.0 for fill in fills), 4),
            "cities_top": top_counter(Counter(fill.get("city") for fill in fills if fill.get("city"))),
            "conditions_top": top_counter(Counter(fill.get("condition") for fill in fills if fill.get("condition"))),
            "outcomes": dict(Counter(fill.get("outcome") for fill in fills if fill.get("outcome"))),
            "entry_price_band": {
                "p25": percentile(buy_prices, 0.25),
                "p50": percentile(buy_prices, 0.50),
                "p75": percentile(buy_prices, 0.75),
                "n": len(buy_prices),
            },
            "high_price_fills": {
                "count": len(high_price_fills),
                "threshold": args.high_price_threshold,
                "ratio": round(high_price_ratio, 4),
                "examples": [example_from_fill(fill) for fill in high_price_fills[:5]],
            },
            "bursts": bursts,
            "rotation_signals": {"count": len(rotations), "examples": rotations[:5]},
            "lead_time_to_resolution": lead_time,
            "nearest_bot_cycle_lag_sec_p50": None,
            "parse_unknown": {"count": parse_unknown, "ratio": parse_unknown_ratio},
            "condition_market_mix": {"n_markets": n_condition_markets, "counts": dict(condition_counts)},
            "basket_grouping": {
                "key_strategy": "city|event_date parsed from title/slug; ignores strike so related weather legs group together",
                "groups_with_multi_legs": sum(1 for legs in basket_groups(fills).values() if len(legs) >= 2),
                "total_groups": len(basket_groups(fills)),
            },
        },
        "style_labels": labels,
        "lane_suggestion": lane,
        "lane_reason": reason,
        "confidence": confidence,
        "reason": reason,
        "manual_review_required": manual,
    }


def cohort_summary(traders: list[dict[str, Any]]) -> dict[str, Any]:
    fills = [row["metrics"]["n_fills"] for row in traders]
    p50s = [
        row["metrics"]["entry_price_band"]["p50"]
        for row in traders
        if row["metrics"]["entry_price_band"]["p50"] is not None
    ]
    high_ratios = [row["metrics"]["high_price_fills"]["ratio"] for row in traders]
    condition_mix = Counter()
    for row in traders:
        condition_mix.update(row["metrics"]["condition_market_mix"]["counts"])
    return {
        "n_wallets": len(traders),
        "fills_per_wallet": {"p25": percentile(fills, 0.25), "p50": percentile(fills, 0.5), "p75": percentile(fills, 0.75)},
        "entry_price_band_p50": {"p25": percentile(p50s, 0.25), "p50": percentile(p50s, 0.5), "p75": percentile(p50s, 0.75)},
        "burst_count": dict(Counter(len(row["metrics"]["bursts"]) for row in traders)),
        "high_price_ratio": {"p25": percentile(high_ratios, 0.25), "p50": percentile(high_ratios, 0.5), "p75": percentile(high_ratios, 0.75)},
        "rotation_signals_count": dict(Counter(row["metrics"]["rotation_signals"]["count"] for row in traders)),
        "conditions_mix": dict(condition_mix),
        "lane_counts": dict(Counter(row["lane_suggestion"] for row in traders)),
        "query_status_counts": dict(Counter(row["query_status"] for row in traders)),
        "capped_wallets": sum(1 for row in traders if row.get("buy_capped") or row.get("sell_capped")),
    }


def build_payload(args: argparse.Namespace, now_ts: int | None = None) -> dict[str, Any]:
    now_ts = now_ts or int(time.time())
    cohort, cohort_meta = build_cohort(args)
    traders = [profile_wallet(entry, args, now_ts) for entry in cohort]
    generated_at = iso_from_ts(now_ts)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "disclaimer": (
            "LOG_ONLY provisional activity profile. lane_suggestion is not definitive, does not authorize "
            "copy-trading, and does not change the bot."
        ),
        "window": {"hours": args.window_hours, "start_ts": iso_from_ts(now_ts - args.window_hours * 3600), "end_ts": generated_at},
        "parameters": {
            "burst_window_sec": args.burst_window_sec,
            "burst_min_fills": args.burst_min_fills,
            "high_price_threshold": args.high_price_threshold,
            "rotation_window_min": args.rotation_window_min,
            "max_wallets": args.max_wallets,
            "max_fills_per_wallet": args.max_fills_per_wallet,
            "max_fills_buy": split_fill_caps(args.max_fills_per_wallet)[0],
            "max_fills_sell": split_fill_caps(args.max_fills_per_wallet)[1],
            "activity_query_cap_policy": "split total cap per wallet into BUY cap=floor(max/2), SELL cap=remaining",
            "rate_limit_ms": args.rate_limit_ms,
            "external_report": str(args.external_report) if args.external_report else None,
        },
        "cohort": cohort_meta,
        "summary": cohort_summary(traders),
        "traders": traders,
    }


def render_md(payload: dict[str, Any]) -> str:
    params = payload["parameters"]
    lines = [
        "# Traders Activity Profile",
        "",
        f"- Schema: `{payload['schema_version']}`",
        f"- Generated: `{payload['generated_at']}`",
        f"- Window: `{payload['window']['hours']}h` (`{payload['window']['start_ts']}` to `{payload['window']['end_ts']}`)",
        f"- Wallets analyzed: `{payload['cohort']['n_wallets_analyzed']}`",
        f"- Cohort mode: `{payload['cohort']['cohort_mode']}` - {payload['cohort']['cohort_description']}",
        f"- Cohort warning: `{payload['cohort']['cohort_warning']}`",
        f"- External report rows: `{payload['cohort']['n_external_report_rows']}`; resolvable wallets: `{payload['cohort']['n_external_report_wallets']}`; missing wallets: `{payload['cohort']['n_external_report_missing_wallets']}`",
        f"- Wallet filter: before=`{payload['cohort']['n_wallets_before_wallet_filter']}` after=`{payload['cohort']['n_wallets_after_wallet_filter']}`",
        f"- Local registry added: `{payload['cohort']['n_local_registry_added']}`; deduplicated source mentions: `{payload['cohort']['n_deduplicated']}`",
        f"- Max-wallets truncated: `{payload['cohort']['max_wallets_truncated']}` count=`{payload['cohort']['max_wallets_truncated_count']}`",
        f"- Cohort source counts: `{payload['cohort']['cohort_source_counts']}`",
        f"- Params: burst `{params['burst_min_fills']}` fills / `{params['burst_window_sec']}`s; high price `>={params['high_price_threshold']}`; rotation `{params['rotation_window_min']}`min; cap `{params['max_fills_per_wallet']}` split BUY `{params['max_fills_buy']}` / SELL `{params['max_fills_sell']}`.",
        "",
        "> LOG_ONLY: lane_suggestion is provisional, not a definitive state, does not authorize copy-trading, and does not change the bot. `confidence=high` means high activity count, not complete Activity API coverage when capped.",
        "",
        "## Cohorte summary",
        "",
        f"- fills_per_wallet p50: `{payload['summary']['fills_per_wallet']['p50']}`",
        f"- entry_price_band p50 distribution: `{payload['summary']['entry_price_band_p50']}`",
        f"- burst_count histogram: `{payload['summary']['burst_count']}`",
        f"- high_price_ratio distribution: `{payload['summary']['high_price_ratio']}`",
        f"- rotation_signals_count histogram: `{payload['summary']['rotation_signals_count']}`",
        f"- conditions mix: `{payload['summary']['conditions_mix']}`",
        f"- lane counts: `{payload['summary']['lane_counts']}`",
        f"- query status counts: `{payload['summary']['query_status_counts']}`; capped wallets: `{payload['summary']['capped_wallets']}`",
        "",
        "## Resumen por trader",
        "",
        "| Trader | Source | Query | Capped | Fills | BUY | SELL | P50 entry | High ratio | Bursts | Rotations | Labels | Lane | Confidence | Manual review |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in payload["traders"]:
        metrics = row["metrics"]
        labels = ", ".join(row["style_labels"])
        lines.append(
            f"| {row.get('alias') or row['wallet'][:10]} | {row.get('cohort_source')} | {row['query_status']} | "
            f"B:{row['buy_capped']} S:{row['sell_capped']} | {metrics['n_fills']} | "
            f"{metrics['counters']['BUY']} | {metrics['counters']['SELL']} | {metrics['entry_price_band']['p50']} | "
            f"{metrics['high_price_fills']['ratio']} | {len(metrics['bursts'])} | {metrics['rotation_signals']['count']} | "
            f"{labels} | {row['lane_suggestion']} | {row['confidence']} | {row['manual_review_required']} |"
        )
    lines.extend(["", "## Fichas por trader", ""])
    for row in payload["traders"]:
        metrics = row["metrics"]
        lines.extend(
            [
                f"### {row.get('alias') or row['wallet']}",
                "",
                f"- Wallet: `{row['wallet']}`",
                f"- Cohort source: `{row.get('cohort_source')}`",
                f"- External: display=`{row.get('display_name')}`, profile=`{row.get('profile_url')}`, weather_pnl_all=`{row.get('external', {}).get('pnl_weather_all')}`, volume=`{row.get('external', {}).get('volume')}`",
                f"- Query status: buy=`{row['buy_query_status']}` capped=`{row['buy_capped']}` cap=`{row['max_fills_buy']}`, sell=`{row['sell_query_status']}` capped=`{row['sell_capped']}` cap=`{row['max_fills_sell']}`, overall=`{row['query_status']}`",
                f"- Coverage note: `{row['coverage_note']}`",
                f"- Metrics: fills=`{metrics['n_fills']}`, markets=`{metrics['n_markets']}`, slugs=`{metrics['n_slugs']}`, usdc_total=`{metrics['usdc_total']}`, outcomes=`{metrics['outcomes']}`",
                f"- Top cities: `{metrics['cities_top']}`",
                f"- Top conditions: `{metrics['conditions_top']}`",
                f"- Entry price band: `{metrics['entry_price_band']}`",
                f"- Lead time to resolution: `{metrics['lead_time_to_resolution']}`",
                f"- High-price fills top 5: `{metrics['high_price_fills']['examples']}`",
                f"- Bursts top 3: `{metrics['bursts'][:3]}`",
                f"- Rotation signals top 3: `{metrics['rotation_signals']['examples'][:3]}`",
                f"- Basket grouping: `{metrics['basket_grouping']}`",
                f"- Style labels: `{row['style_labels']}`",
                f"- Lane suggestion: `{row['lane_suggestion']}`; confidence=`{row['confidence']}`; lane_reason=`{row['lane_reason']}`; manual_review_required=`{row['manual_review_required']}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def write_snapshot(payload: dict[str, Any], snapshot_dir: str) -> Path:
    target_dir = Path(snapshot_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    path = target_dir / f"{stamp}.json"
    if path.exists():
        suffix = datetime.now(timezone.utc).strftime("%S")
        path = target_dir / f"{stamp}-{suffix}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    payload = build_payload(args)
    if args.snapshot:
        snapshot_path = write_snapshot(payload, args.snapshot_dir)
        payload.setdefault("snapshot", {})["path"] = str(snapshot_path)
    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_md(payload))


if __name__ == "__main__":
    main(sys.argv[1:])
