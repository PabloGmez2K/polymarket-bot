#!/usr/bin/env python3
"""Focused city watch readout for the next operational phase."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WATCHLIST_PATH = REPO_ROOT / "data" / "city_watchlist_phase4.json"
DEFAULT_CROSS_PATH = REPO_ROOT / "data" / "reference_trader_city_market_cross.json"
DEFAULT_ENRICHMENT_PATH = REPO_ROOT / "data" / "directional_trader_enrichment.json"
DEFAULT_PROBE_PATH = REPO_ROOT / "data" / "settlement_fidelity_probe.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_watch_reinforced.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_watch_reinforced_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera un readout focalizado por ciudad para la siguiente fase operativa."
    )
    parser.add_argument("--cities", default="Shanghai,Chicago,Seoul", help="Lista coma-separada de ciudades.")
    parser.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST_PATH))
    parser.add_argument("--cross", default=str(DEFAULT_CROSS_PATH))
    parser.add_argument("--enrichment", default=str(DEFAULT_ENRICHMENT_PATH))
    parser.add_argument("--probe", default=str(DEFAULT_PROBE_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def normalize_cities(raw):
    return [part.strip() for part in raw.split(",") if part.strip()]


def build_reference_lookup(enrichment):
    lookup = {}
    for trader in enrichment.get("traders", []):
        label = trader.get("pseudonym") or trader.get("address", "")[:10]
        lookup[label] = trader
    return lookup


def recommend_next_step(city, watch_entry, probe_markets, trader_entries):
    action = watch_entry.get("action", "")
    if city == "Shanghai":
        return "prepare_shadow_test_design"
    if city == "Chicago":
        return "watch_live_active_city"
    if city == "Seoul":
        return "expand_shadow_observability"
    if action == "review_block_reason":
        return "review_block_reason"
    return "observe"


def build_city_note(city, watch_entry, probe_markets, trader_entries):
    if city == "Shanghai":
        return "Ciudad puente principal: ya esta en shadow, tiene 4 referencias reales y mercados visibles ahora mismo. Es la mejor candidata para un test controlado futuro sin tocar aun el core."
    if city == "Chicago":
        return "Ciudad operativa principal con señal trader real. Aunque no aparece en el probe actual, dos referencias fuertes la tocan y merece vigilancia reforzada antes de cambiar logica."
    if city == "Seoul":
        return "Ciudad shadow con mercados visibles y al menos una referencia fuerte activa. Buena candidata para observabilidad reforzada sin convertirla todavia en ciudad de trading."
    return watch_entry.get("thesis", "")


def build_readout(cities, watchlist, cross, enrichment, probe):
    watch_by_city = {row["city"]: row for row in watchlist.get("watchlist", [])}
    cross_by_city = {row["city"]: row for row in cross.get("city_rows", [])}
    probe_by_city = {}
    for market in probe.get("markets", []):
        probe_by_city.setdefault(market.get("city", ""), []).append(market)
    reference_lookup = build_reference_lookup(enrichment)

    rows = []
    for city in cities:
        watch_entry = watch_by_city.get(city, {
            "city": city,
            "policy_mode": "unknown",
            "action": "observe",
            "priority_score": 0,
            "reference_traders": [],
            "thesis": "",
        })
        cross_entry = cross_by_city.get(city, {})
        trader_entries = []
        for item in watch_entry.get("reference_traders", []):
            label = item.get("trader")
            if label and label in reference_lookup:
                trader = reference_lookup[label]
                trader_entries.append({
                    "trader": label,
                    "reference_quality": trader.get("reference_quality", ""),
                    "closed_win_rate": trader.get("closed_summary", {}).get("win_rate"),
                    "closed_pnl": trader.get("closed_summary", {}).get("total_closed_pnl"),
                    "n_closed_directional_weather": trader.get("closed_summary", {}).get("n_closed_directional_weather"),
                    "active_directional": trader.get("active_summary", {}).get("n_active_directional"),
                })

        row = {
            "city": city,
            "policy_mode": watch_entry.get("policy_mode", ""),
            "action": watch_entry.get("action", ""),
            "priority_score": watch_entry.get("priority_score", 0),
            "next_step": recommend_next_step(city, watch_entry, probe_by_city.get(city, []), trader_entries),
            "note": build_city_note(city, watch_entry, probe_by_city.get(city, []), trader_entries),
            "reference_count": len(trader_entries),
            "reference_traders": trader_entries,
            "current_probe_markets": [
                {
                    "condition": market.get("condition"),
                    "threshold": market.get("threshold"),
                    "threshold_unit": market.get("threshold_unit"),
                    "market_prob_yes": market.get("market_prob_yes"),
                    "openmeteo_forecast_max_c": market.get("openmeteo_forecast_max_c"),
                }
                for market in probe_by_city.get(city, [])[:6]
            ],
            "cross_summary": {
                "reference_quality_counts": cross_entry.get("reference_quality_counts", {}),
                "probe_conditions": cross_entry.get("probe_conditions", {}),
                "current_probe_markets": cross_entry.get("current_probe_markets", 0),
            },
        }
        rows.append(row)
    return rows


def render_markdown(payload):
    lines = [
        "# Reinforced City Watch",
        "",
        f"- Generated: `{payload['generated_at']}`",
        "",
    ]
    for row in payload["cities"]:
        lines.extend([
            f"## {row['city']}",
            "",
            f"- Policy: `{row['policy_mode']}`",
            f"- Action: `{row['action']}`",
            f"- Next step: `{row['next_step']}`",
            f"- Priority: `{row['priority_score']}`",
            f"- References: `{row['reference_count']}`",
            f"- Note: {row['note']}",
            "",
        ])
        if row["reference_traders"]:
            lines.append("| Trader | Quality | Closed WR | Closed PnL | Closed directional | Active directional |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for trader in row["reference_traders"]:
                lines.append(
                    f"| {trader['trader']} | {trader['reference_quality']} | {trader['closed_win_rate']} | "
                    f"{trader['closed_pnl']} | {trader['n_closed_directional_weather']} | {trader['active_directional']} |"
                )
            lines.append("")
        if row["current_probe_markets"]:
            lines.append("| Condition | Threshold | Mkt YES | Open-Meteo C |")
            lines.append("| --- | --- | --- | --- |")
            for market in row["current_probe_markets"]:
                threshold = f"{market['threshold']}{market['threshold_unit']}"
                lines.append(
                    f"| {market['condition']} | {threshold} | {market['market_prob_yes']} | {market['openmeteo_forecast_max_c']} |"
                )
            lines.append("")
    return "\n".join(lines) + "\n"


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main():
    args = parse_args()
    cities = normalize_cities(args.cities)
    watchlist = load_json(args.watchlist)
    cross = load_json(args.cross)
    enrichment = load_json(args.enrichment)
    probe = load_json(args.probe)
    readout = build_readout(cities, watchlist, cross, enrichment, probe)
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "watchlist": args.watchlist,
            "cross": args.cross,
            "enrichment": args.enrichment,
            "probe": args.probe,
        },
        "cities": readout,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Reinforced city watch written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps({"n_cities": len(readout)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
