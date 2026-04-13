#!/usr/bin/env python3
"""Build a phase-4 operational watchlist from cross/research artifacts."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CROSS_PATH = REPO_ROOT / "data" / "reference_trader_city_market_cross.json"
DEFAULT_ENRICHMENT_PATH = REPO_ROOT / "data" / "directional_trader_enrichment.json"
DEFAULT_PROBE_PATH = REPO_ROOT / "data" / "settlement_fidelity_probe.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_watchlist_phase4.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_watchlist_phase4_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Construye una watchlist operativa por ciudad a partir de la fase 4."
    )
    parser.add_argument("--cross", default=str(DEFAULT_CROSS_PATH))
    parser.add_argument("--enrichment", default=str(DEFAULT_ENRICHMENT_PATH))
    parser.add_argument("--probe", default=str(DEFAULT_PROBE_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def build_reference_lookup(enrichment):
    lookup = {}
    for trader in enrichment.get("traders", []):
        label = trader.get("pseudonym") or trader.get("address", "")[:10]
        lookup[label] = {
            "reference_quality": trader.get("reference_quality", ""),
            "closed_win_rate": trader.get("closed_summary", {}).get("win_rate"),
            "closed_pnl": trader.get("closed_summary", {}).get("total_closed_pnl"),
            "active_directional": trader.get("active_summary", {}).get("n_active_directional"),
        }
    return lookup


def classify_action(city_row):
    mode = city_row.get("policy_mode")
    high_refs = city_row.get("reference_quality_counts", {}).get("high_priority_reference", 0)
    current_markets = city_row.get("current_probe_markets", 0)

    if mode == "active" and high_refs >= 1:
        return "watch_active"
    if mode == "shadow" and high_refs >= 2 and current_markets >= 1:
        return "prepare_test"
    if mode == "blocked" and high_refs >= 2:
        return "review_block_reason"
    if mode in {"shadow", "untracked"} and high_refs >= 1:
        return "observe_closely"
    return "background_watch"


def build_thesis(city_row):
    mode = city_row.get("policy_mode")
    city = city_row.get("city", "")
    refs = city_row.get("reference_traders", [])
    current_markets = city_row.get("current_probe_markets", 0)

    if mode == "active":
        return f"{city} ya es operativa y ademas aparece tocada por referencias reales; conviene vigilarla antes de tocar logica."
    if mode == "shadow" and current_markets:
        return f"{city} ya esta en observacion y ademas tiene mercados visibles ahora mismo con referencias reales alrededor; es la mejor ciudad puente para un test controlado futuro."
    if mode == "blocked":
        return f"{city} concentra referencia trader pero sigue bloqueada; la accion correcta no es operar ya, sino revisar si el bloqueo sigue siendo estructural."
    if refs:
        return f"{city} aun no forma parte clara del marco operativo local, pero aparece repetida en traders de referencia y merece seguimiento."
    return f"{city} queda en vigilancia de fondo."


def build_watchlist(cross, enrichment, probe):
    reference_lookup = build_reference_lookup(enrichment)
    probe_by_city = {}
    for market in probe.get("markets", []):
        probe_by_city.setdefault(market.get("city", ""), []).append(market)

    rows = []
    for city_row in cross.get("city_rows", []):
        city = city_row.get("city", "")
        current_markets = probe_by_city.get(city, [])
        row = {
            "city": city,
            "policy_mode": city_row.get("policy_mode", ""),
            "action": classify_action(city_row),
            "priority_score": city_row.get("priority_score", 0),
            "current_probe_markets": city_row.get("current_probe_markets", 0),
            "current_probe_sample": [
                {
                    "condition": m.get("condition"),
                    "threshold": m.get("threshold"),
                    "threshold_unit": m.get("threshold_unit"),
                    "market_prob_yes": m.get("market_prob_yes"),
                    "openmeteo_forecast_max_c": m.get("openmeteo_forecast_max_c"),
                }
                for m in current_markets[:4]
            ],
            "reference_traders": [
                {
                    "trader": trader,
                    **reference_lookup.get(trader, {}),
                }
                for trader in city_row.get("reference_traders", [])
            ],
            "thesis": build_thesis(city_row),
        }
        rows.append(row)

    action_rank = {
        "prepare_test": 0,
        "watch_active": 1,
        "review_block_reason": 2,
        "observe_closely": 3,
        "background_watch": 4,
    }
    rows.sort(key=lambda row: (action_rank.get(row["action"], 99), -row["priority_score"], row["city"]))
    return rows


def render_markdown(payload):
    lines = [
        "# City Watchlist - Phase 4",
        "",
        f"- Generated: `{payload['generated_at']}`",
        "",
        "## Recommended order",
        "",
        "| City | Action | Policy | Priority | Probe markets | References |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["watchlist"][:15]:
        refs = ", ".join(item["trader"] for item in row["reference_traders"])
        lines.append(
            f"| {row['city']} | {row['action']} | {row['policy_mode']} | "
            f"{row['priority_score']} | {row['current_probe_markets']} | {refs} |"
        )
    lines.extend([
        "",
        "## Notes",
        "",
    ])
    for row in payload["watchlist"][:8]:
        lines.append(f"- `{row['city']}`: {row['thesis']}")
    return "\n".join(lines) + "\n"


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main():
    args = parse_args()
    cross = load_json(args.cross)
    enrichment = load_json(args.enrichment)
    probe = load_json(args.probe)
    watchlist = build_watchlist(cross, enrichment, probe)
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "cross": args.cross,
            "enrichment": args.enrichment,
            "probe": args.probe,
        },
        "watchlist": watchlist,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"City watchlist written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps({"n_watchlist_rows": len(watchlist)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
