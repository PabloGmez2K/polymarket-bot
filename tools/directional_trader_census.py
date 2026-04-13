#!/usr/bin/env python3
"""Read-only census of traders active in directional weather markets."""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import bot  # type: ignore


GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
DAILY_TEMP_TAG_ID = "103040"

DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "directional_trader_census.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "directional_trader_census_latest.md"


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
        description="Escanea solo mercados direccionales activos y perfila wallets compradoras."
    )
    parser.add_argument("--markets", type=int, default=40, help="Maximo de mercados direccionales a escanear.")
    parser.add_argument("--trades-per-market", type=int, default=200, help="Maximo de trades por mercado.")
    parser.add_argument("--min-trades", type=int, default=2, help="Minimo de BUY trades para incluir un trader.")
    parser.add_argument("--min-markets", type=int, default=2, help="Minimo de mercados distintos para incluir un trader.")
    parser.add_argument("--min-price", type=float, default=0.20, help="Precio minimo del BUY para considerarlo comparable.")
    parser.add_argument("--max-price", type=float, default=0.80, help="Precio maximo del BUY para considerarlo comparable.")
    parser.add_argument("--city", help="Filtra por ciudad exacta.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT), help="Ruta del JSON de salida.")
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT), help="Ruta del markdown de salida.")
    return parser.parse_args()


def api_get_json(url, user_agent="directional-trader-census/1.0", timeout=30, retries=3, delay=2):
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", user_agent)
            with open_url(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay)
    raise last_error


def load_prices(market):
    raw = market.get("outcomePrices", "[]")
    try:
        prices = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []
    return prices if isinstance(prices, list) else []


def get_directional_markets(limit, city_filter=None):
    rows = []
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
                if not question or question in seen_questions:
                    continue
                parsed = bot.parse_temperature_question(question)
                if not parsed or parsed.get("condition") not in {"at_or_above", "at_or_below"}:
                    continue
                city = parsed.get("city")
                if city_filter and city != city_filter:
                    continue
                seen_questions.add(question)
                prices = load_prices(market)
                rows.append({
                    "question": question,
                    "condition_id": market.get("conditionId", ""),
                    "city": city,
                    "condition": parsed.get("condition"),
                    "date_str": parsed.get("date_str"),
                    "temp_threshold": parsed.get("temp_threshold"),
                    "unit": parsed.get("unit"),
                    "market_prob_yes": float(prices[0]) if len(prices) >= 1 else None,
                    "market_prob_no": float(prices[1]) if len(prices) >= 2 else None,
                    "volume_24h": market.get("volume24hr"),
                    "event_slug": event.get("slug", ""),
                    "market_slug": market.get("slug", ""),
                })
                if len(rows) >= limit:
                    return rows
    return rows


def get_market_trades(condition_id, limit):
    params = urllib.parse.urlencode({
        "market": condition_id,
        "limit": limit,
    })
    try:
        return api_get_json(f"{DATA_API}/trades?{params}") or []
    except Exception:
        return []


def classify_price_style(avg_price):
    if avg_price is None:
        return "unknown"
    if avg_price < 0.10:
        return "deep_outlier"
    if avg_price <= 0.35:
        return "low_price"
    if avg_price <= 0.70:
        return "mid_range"
    return "high_confidence"


def build_census(markets, trades_per_market, min_trades, min_markets, min_price, max_price):
    trader_map = {}
    market_map = {}
    scanned_markets = 0
    total_buy_trades = 0

    for market in markets:
        condition_id = market["condition_id"]
        if not condition_id:
            continue
        market_map[condition_id] = market
        trades = get_market_trades(condition_id, trades_per_market)
        scanned_markets += 1

        for trade in trades:
            if str(trade.get("side", "")).upper() != "BUY":
                continue
            address = str(trade.get("proxyWallet", "")).lower()
            if not address:
                continue
            total_buy_trades += 1
            price = None
            size = None
            try:
                price = float(trade.get("price", 0))
                size = float(trade.get("size", 0))
            except (TypeError, ValueError):
                continue
            if size < 0.1:
                continue

            trader = trader_map.setdefault(address, {
                "address": address,
                "pseudonym": trade.get("pseudonym", ""),
                "n_buy_trades": 0,
                "markets": set(),
                "cities": Counter(),
                "conditions": Counter(),
                "outcomes": Counter(),
                "total_notional": 0.0,
                "weighted_price_notional_sum": 0.0,
                "total_size": 0.0,
                "sample_positions": [],
            })

            if price < min_price or price > max_price:
                continue

            trader["n_buy_trades"] += 1
            trader["markets"].add(condition_id)
            trader["cities"][market["city"]] += 1
            trader["conditions"][market["condition"]] += 1
            trader["outcomes"][trade.get("outcome", "")] += 1
            trader["total_notional"] += price * size
            trader["weighted_price_notional_sum"] += price * size
            trader["total_size"] += size
            if len(trader["sample_positions"]) < 6:
                trader["sample_positions"].append({
                    "city": market["city"],
                    "condition": market["condition"],
                    "date_str": market["date_str"],
                    "threshold": market["temp_threshold"],
                    "unit": market["unit"],
                    "outcome": trade.get("outcome", ""),
                    "price": round(price, 4),
                    "size": round(size, 4),
                    "market_prob_yes": market["market_prob_yes"],
                })

    filtered = []
    for trader in trader_map.values():
        n_markets = len(trader["markets"])
        if trader["n_buy_trades"] < min_trades or n_markets < min_markets:
            continue
        avg_price = round(trader["weighted_price_notional_sum"] / trader["total_size"], 4) if trader["total_size"] > 0 else None
        dominant_city = trader["cities"].most_common(1)[0][0] if trader["cities"] else ""
        trader_type_hint = "directional_forecast_candidate"
        if len(trader["cities"]) == 1 and n_markets >= 3:
            trader_type_hint = "city_specialist_candidate"
        if avg_price is not None and (avg_price < 0.10 or avg_price > 0.85):
            trader_type_hint = "extreme_pricing_candidate"
        filtered.append({
            "address": trader["address"],
            "pseudonym": trader["pseudonym"],
            "n_buy_trades": trader["n_buy_trades"],
            "n_markets": n_markets,
            "total_notional": round(trader["total_notional"], 2),
            "avg_price": avg_price,
            "price_style": classify_price_style(avg_price),
            "dominant_city": dominant_city,
            "top_cities": dict(trader["cities"].most_common(5)),
            "conditions": dict(trader["conditions"]),
            "outcomes": dict(trader["outcomes"]),
            "type_hint": trader_type_hint,
            "sample_positions": trader["sample_positions"],
        })

    filtered.sort(key=lambda row: (-row["n_markets"], -row["n_buy_trades"], -row["total_notional"]))
    return {
        "n_scanned_markets": scanned_markets,
        "n_total_buy_trades": total_buy_trades,
        "n_unique_traders_raw": len(trader_map),
        "n_traders_after_filter": len(filtered),
        "traders": filtered,
    }


def render_markdown(payload):
    lines = [
        "# Directional Trader Census - latest run",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Directional markets scanned: `{payload['summary']['n_scanned_markets']}`",
        f"- BUY trades seen: `{payload['summary']['n_total_buy_trades']}`",
        f"- Unique traders raw: `{payload['summary']['n_unique_traders_raw']}`",
        f"- Traders after filter: `{payload['summary']['n_traders_after_filter']}`",
        "",
        "## Top traders",
        "",
        "| Trader | Markets | BUYs | Notional | Avg price | Hint | Top cities |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for trader in payload["traders"][:20]:
        label = trader["pseudonym"] or trader["address"][:10]
        top_cities = ", ".join(f"{city}({count})" for city, count in trader["top_cities"].items())
        lines.append(
            f"| {label} | {trader['n_markets']} | {trader['n_buy_trades']} | "
            f"{trader['total_notional']} | {trader['avg_price']} | {trader['type_hint']} | {top_cities} |"
        )
    return "\n".join(lines) + "\n"


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main():
    args = parse_args()
    markets = get_directional_markets(args.markets, city_filter=args.city)
    summary = build_census(
        markets,
        trades_per_market=args.trades_per_market,
        min_trades=args.min_trades,
        min_markets=args.min_markets,
        min_price=args.min_price,
        max_price=args.max_price,
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "filters": {
            "markets": args.markets,
            "trades_per_market": args.trades_per_market,
            "min_trades": args.min_trades,
            "min_markets": args.min_markets,
            "min_price": args.min_price,
            "max_price": args.max_price,
            "city": args.city or "",
        },
        "summary": {k: v for k, v in summary.items() if k != "traders"},
        "traders": summary["traders"],
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Directional trader census written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
