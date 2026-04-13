#!/usr/bin/env python3
"""Enrich directional trader census with closed-position performance data."""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trader_analyzer import get_positions, get_closed_positions, is_temperature_market, parse_city, parse_condition

DEFAULT_CENSUS_PATH = REPO_ROOT / "data" / "directional_trader_census.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "directional_trader_enrichment.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "directional_trader_enrichment_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Enriquece la shortlist del censo direccional con WR, PnL y posiciones activas/cerradas."
    )
    parser.add_argument("--input", default=str(DEFAULT_CENSUS_PATH), help="Ruta al JSON del censo direccional.")
    parser.add_argument("--top", type=int, default=10, help="Numero de traders del censo a enriquecer.")
    parser.add_argument("--closed-limit", type=int, default=100, help="Maximo de posiciones cerradas por trader.")
    parser.add_argument("--active-limit", type=int, default=50, help="Maximo de posiciones activas por trader.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT), help="Ruta del JSON de salida.")
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT), help="Ruta del markdown de salida.")
    return parser.parse_args()


def load_census(path_str):
    path = Path(path_str)
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_active_directional(positions):
    directional = []
    city_counter = Counter()
    condition_counter = Counter()

    for position in positions:
        title = position.get("title", "")
        if not is_temperature_market(title):
            continue
        condition = parse_condition(title)
        if condition not in {"at_or_above", "at_or_below"}:
            continue
        city = parse_city(title) or ""
        city_counter[city] += 1
        condition_counter[condition] += 1
        directional.append({
            "title": title[:120],
            "city": city,
            "condition": condition,
            "outcome": position.get("outcome", ""),
            "avg_price": round(float(position.get("avgPrice", 0) or 0), 4),
            "cur_price": round(float(position.get("curPrice", 0) or 0), 4),
            "cash_pnl": round(float(position.get("cashPnl", 0) or 0), 2),
            "percent_pnl": round(float(position.get("percentPnl", 0) or 0), 1),
        })

    return {
        "n_active_directional": len(directional),
        "top_active_cities": dict(city_counter.most_common(5)),
        "active_conditions": dict(condition_counter),
        "sample_active_directional": directional[:8],
    }


def summarize_closed_positions(closed):
    wins = sum(1 for row in closed if float(row.get("cashPnl", 0) or 0) > 0)
    losses = sum(1 for row in closed if float(row.get("cashPnl", 0) or 0) < 0)
    pushes = sum(1 for row in closed if float(row.get("cashPnl", 0) or 0) == 0)
    total_pnl = round(sum(float(row.get("cashPnl", 0) or 0) for row in closed), 2)
    directional_weather = []
    category_counter = Counter()

    for row in closed:
        title = row.get("title", "")
        if not is_temperature_market(title):
            continue
        condition = parse_condition(title)
        city = parse_city(title) or ""
        category_counter[condition] += 1
        directional_weather.append({
            "title": title[:120],
            "city": city,
            "condition": condition,
            "outcome": row.get("outcome", ""),
            "cash_pnl": round(float(row.get("cashPnl", 0) or 0), 2),
            "percent_pnl": round(float(row.get("percentPnl", 0) or 0), 1),
        })

    decisive = wins + losses
    win_rate = round((wins / decisive) * 100, 1) if decisive else 0.0
    directional_only = [row for row in directional_weather if row["condition"] in {"at_or_above", "at_or_below"}]
    directional_pnl = round(sum(row["cash_pnl"] for row in directional_only), 2)

    return {
        "n_closed_positions": len(closed),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": win_rate,
        "total_closed_pnl": total_pnl,
        "n_closed_weather": len(directional_weather),
        "n_closed_directional_weather": len(directional_only),
        "directional_weather_pnl": directional_pnl,
        "closed_weather_conditions": dict(category_counter),
        "sample_closed_directional": directional_only[:8],
    }


def classify_reference_quality(enriched):
    win_rate = enriched["closed_summary"]["win_rate"]
    total_pnl = enriched["closed_summary"]["total_closed_pnl"]
    n_directional_closed = enriched["closed_summary"]["n_closed_directional_weather"]

    if n_directional_closed >= 3 and win_rate >= 55 and total_pnl > 0:
        return "high_priority_reference"
    if total_pnl > 0 and win_rate >= 50:
        return "candidate_reference"
    if enriched["active_summary"]["n_active_directional"] > 0:
        return "active_but_unproven"
    return "low_signal"


def build_health_summary(enriched_rows):
    reference_counts = Counter(row["reference_quality"] for row in enriched_rows)
    quality_refs = int(reference_counts.get("high_priority_reference", 0) or 0) + int(
        reference_counts.get("candidate_reference", 0) or 0
    )
    active_directional_traders = sum(
        1 for row in enriched_rows if row["active_summary"]["n_active_directional"] > 0
    )
    traders_with_closed_positions = sum(
        1 for row in enriched_rows if row["closed_summary"]["n_closed_positions"] > 0
    )
    traders_with_active_positions = sum(
        1 for row in enriched_rows if row["source_diagnostics"]["n_active_positions_raw"] > 0
    )
    traders_with_closed_directional = sum(
        1 for row in enriched_rows if row["closed_summary"]["n_closed_directional_weather"] > 0
    )

    likely_input_degraded = (
        bool(enriched_rows)
        and quality_refs == 0
        and active_directional_traders == 0
        and traders_with_closed_positions == 0
        and traders_with_active_positions == 0
        and traders_with_closed_directional == 0
    )
    if likely_input_degraded:
        status = "input_degraded"
    elif quality_refs == 0:
        status = "low_signal"
    else:
        status = "usable_signal"

    return {
        "reference_quality_counts": dict(reference_counts),
        "quality_reference_traders": quality_refs,
        "active_directional_traders": active_directional_traders,
        "traders_with_closed_positions": traders_with_closed_positions,
        "traders_with_active_positions": traders_with_active_positions,
        "traders_with_closed_directional": traders_with_closed_directional,
        "health_status": status,
        "likely_input_degraded": likely_input_degraded,
    }


def enrich_trader(trader, closed_limit, active_limit):
    address = trader["address"]
    active = get_positions(address, limit=active_limit)
    closed = get_closed_positions(address, limit=closed_limit)

    enriched = {
        "address": address,
        "pseudonym": trader.get("pseudonym", ""),
        "census_snapshot": trader,
        "active_summary": summarize_active_directional(active),
        "closed_summary": summarize_closed_positions(closed),
        "source_diagnostics": {
            "n_active_positions_raw": len(active),
            "n_closed_positions_raw": len(closed),
        },
    }
    enriched["reference_quality"] = classify_reference_quality(enriched)
    return enriched


def render_markdown(payload):
    lines = [
        "# Directional Trader Enrichment - latest run",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Traders enriched: `{payload['summary']['n_traders_enriched']}`",
        f"- Health status: `{payload['summary']['health_status']}`",
        f"- Quality references: `{payload['summary']['quality_reference_traders']}`",
        f"- Traders with active positions: `{payload['summary']['traders_with_active_positions']}`",
        f"- Traders with closed positions: `{payload['summary']['traders_with_closed_positions']}`",
        "",
        "## Ranked shortlist",
        "",
        "| Trader | Ref quality | Closed WR | Closed PnL | Closed directional | Active directional | Dominant city |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for trader in payload["traders"]:
        label = trader["pseudonym"] or trader["address"][:10]
        lines.append(
            f"| {label} | {trader['reference_quality']} | {trader['closed_summary']['win_rate']} | "
            f"{trader['closed_summary']['total_closed_pnl']} | {trader['closed_summary']['n_closed_directional_weather']} | "
            f"{trader['active_summary']['n_active_directional']} | {trader['census_snapshot']['dominant_city']} |"
        )
    return "\n".join(lines) + "\n"


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main():
    args = parse_args()
    census = load_census(args.input)
    traders = census.get("traders", [])[: args.top]
    enriched = [enrich_trader(trader, closed_limit=args.closed_limit, active_limit=args.active_limit) for trader in traders]
    enriched.sort(
        key=lambda row: (
            row["reference_quality"] != "high_priority_reference",
            row["reference_quality"] != "candidate_reference",
            -row["closed_summary"]["total_closed_pnl"],
            -row["closed_summary"]["win_rate"],
        )
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "input": args.input,
        "summary": {
            "n_traders_enriched": len(enriched),
            **build_health_summary(enriched),
        },
        "traders": enriched,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Directional trader enrichment written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
