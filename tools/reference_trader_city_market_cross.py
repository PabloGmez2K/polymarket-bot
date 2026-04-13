#!/usr/bin/env python3
"""Cross enriched directional references with canonical effective city policy."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_ENRICHMENT_PATH = REPO_ROOT / "data" / "directional_trader_enrichment.json"
DEFAULT_PROBE_PATH = REPO_ROOT / "data" / "settlement_fidelity_probe.json"
DEFAULT_EFFECTIVE_VIEW_PATH = REPO_ROOT / "data" / "runtime_policy_effective_view.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "reference_trader_city_market_cross.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "reference_trader_city_market_cross_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Cruza referencias reales de traders con city policy y snapshot actual de mercados."
    )
    parser.add_argument("--enrichment", default=str(DEFAULT_ENRICHMENT_PATH))
    parser.add_argument("--probe", default=str(DEFAULT_PROBE_PATH))
    parser.add_argument("--effective-view", default=str(DEFAULT_EFFECTIVE_VIEW_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def normalize_city(city):
    return str(city).strip().lower()


def load_effective_modes(path_str):
    path = Path(path_str)
    if not path.exists():
        return {}
    payload = load_json(path_str)
    result = {}
    for row in payload.get("cities", []):
        city = row.get("city")
        if not city:
            continue
        result[normalize_city(city)] = row.get("effective_mode", "unknown")
    return result


def get_policy_context(city, effective_modes):
    effective_mode = effective_modes.get(normalize_city(city))
    if effective_mode:
        return effective_mode, "runtime_policy_effective_view.effective_mode"
    # If the effective view does not list the city, keep the canonical default:
    # cities not present in any explicit list remain shadow until proven otherwise.
    return "shadow", "effective_view_default_shadow"


def summarize_cross(enrichment, probe, effective_modes):
    probe_by_city = defaultdict(list)
    for market in probe.get("markets", []):
        probe_by_city[market.get("city", "")].append(market)

    city_rows = {}
    trader_rows = []

    for trader in enrichment.get("traders", []):
        trader_label = trader.get("pseudonym") or trader.get("address", "")[:10]
        census = trader.get("census_snapshot", {})
        active_summary = trader.get("active_summary", {})
        closed_summary = trader.get("closed_summary", {})

        relevant_cities = Counter()
        relevant_cities.update(census.get("top_cities", {}))
        relevant_cities.update(active_summary.get("top_active_cities", {}))

        trader_city_modes = {}
        for city in relevant_cities:
            policy_mode, policy_source = get_policy_context(city, effective_modes)
            trader_city_modes[city] = policy_mode
            row = city_rows.setdefault(city, {
                "city": city,
                "policy_mode": policy_mode,
                "policy_source": policy_source,
                "reference_traders": [],
                "reference_quality_counts": Counter(),
                "current_probe_markets": len(probe_by_city.get(city, [])),
                "probe_conditions": Counter(m.get("condition", "") for m in probe_by_city.get(city, [])),
                "openmeteo_available": sum(1 for m in probe_by_city.get(city, []) if m.get("openmeteo_forecast_max_c") is not None),
                "top_reference_examples": [],
            })
            row["reference_traders"].append(trader_label)
            row["reference_quality_counts"][trader.get("reference_quality", "unknown")] += 1
            if len(row["top_reference_examples"]) < 5:
                row["top_reference_examples"].append({
                    "trader": trader_label,
                    "reference_quality": trader.get("reference_quality", ""),
                    "closed_win_rate": closed_summary.get("win_rate"),
                    "closed_pnl": closed_summary.get("total_closed_pnl"),
                    "active_directional": active_summary.get("n_active_directional"),
                })

        trader_rows.append({
            "trader": trader_label,
            "reference_quality": trader.get("reference_quality", ""),
            "closed_win_rate": closed_summary.get("win_rate"),
            "closed_pnl": closed_summary.get("total_closed_pnl"),
            "n_closed_directional_weather": closed_summary.get("n_closed_directional_weather"),
            "dominant_city": census.get("dominant_city", ""),
            "policy_modes_seen": trader_city_modes,
            "cities_in_probe_now": [city for city in relevant_cities if city in probe_by_city],
        })

    final_city_rows = []
    for row in city_rows.values():
        high_refs = row["reference_quality_counts"].get("high_priority_reference", 0)
        candidate_refs = row["reference_quality_counts"].get("candidate_reference", 0)
        score = high_refs * 3 + candidate_refs * 1 + row["current_probe_markets"]
        if row["policy_mode"] == "active":
            score += 3
        elif row["policy_mode"] == "shadow":
            score += 2
        elif row["policy_mode"] == "blocked":
            score -= 1

        row["priority_score"] = score
        row["reference_traders"] = sorted(set(row["reference_traders"]))
        row["reference_quality_counts"] = dict(row["reference_quality_counts"])
        row["probe_conditions"] = dict(row["probe_conditions"])
        final_city_rows.append(row)

    final_city_rows.sort(key=lambda row: (-row["priority_score"], row["city"]))
    trader_rows.sort(key=lambda row: (row["reference_quality"] != "high_priority_reference", -float(row["closed_pnl"] or 0)))

    return {
        "city_rows": final_city_rows,
        "trader_rows": trader_rows,
        "summary": {
            "n_reference_traders": len(trader_rows),
            "n_cities_crossed": len(final_city_rows),
            "policy_mode_counts": dict(Counter(row["policy_mode"] for row in final_city_rows)),
        },
    }


def render_markdown(payload):
    lines = [
        "# Reference Trader x City x Market Cross",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Reference traders: `{payload['summary']['n_reference_traders']}`",
        f"- Cities crossed: `{payload['summary']['n_cities_crossed']}`",
        "",
        "## Priority cities",
        "",
        "| City | Policy | Priority | High refs | Probe markets now | Traders |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["city_rows"][:15]:
        lines.append(
            f"| {row['city']} | {row['policy_mode']} | {row['priority_score']} | "
            f"{row['reference_quality_counts'].get('high_priority_reference', 0)} | "
            f"{row['current_probe_markets']} | {', '.join(row['reference_traders'])} |"
        )
    lines.extend([
        "",
        "## Priority traders",
        "",
        "| Trader | Ref quality | Closed WR | Closed PnL | Dominant city | Policy modes seen | Cities in probe now |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in payload["trader_rows"][:15]:
        modes = ", ".join(f"{city}:{mode}" for city, mode in row["policy_modes_seen"].items())
        lines.append(
            f"| {row['trader']} | {row['reference_quality']} | {row['closed_win_rate']} | "
            f"{row['closed_pnl']} | {row['dominant_city']} | {modes} | {', '.join(row['cities_in_probe_now'])} |"
        )
    return "\n".join(lines) + "\n"


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main():
    args = parse_args()
    enrichment = load_json(args.enrichment)
    probe = load_json(args.probe)
    effective_modes = load_effective_modes(args.effective_view)
    cross = summarize_cross(enrichment, probe, effective_modes)
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "enrichment": args.enrichment,
            "probe": args.probe,
            "effective_view": args.effective_view,
        },
        **cross,
    }
    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Reference cross written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
