#!/usr/bin/env python3
"""Read-only Shanghai shadow test snapshot."""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import bot  # type: ignore


DEFAULT_REINFORCED_PATH = REPO_ROOT / "data" / "city_watch_reinforced.json"
DEFAULT_CROSS_PATH = REPO_ROOT / "data" / "reference_trader_city_market_cross.json"
DEFAULT_ENRICHMENT_PATH = REPO_ROOT / "data" / "directional_trader_enrichment.json"
DEFAULT_PROBE_PATH = REPO_ROOT / "data" / "settlement_fidelity_probe.json"
DEFAULT_SHADOW_TRACKING_PATH = REPO_ROOT / "data" / "shadow_city_tracking.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "data" / "audit.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "shanghai_shadow_test.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "shanghai_shadow_test_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera un snapshot read-only del shadow test de Shanghai."
    )
    parser.add_argument("--city", default="Shanghai")
    parser.add_argument("--reinforced", default=str(DEFAULT_REINFORCED_PATH))
    parser.add_argument("--cross", default=str(DEFAULT_CROSS_PATH))
    parser.add_argument("--enrichment", default=str(DEFAULT_ENRICHMENT_PATH))
    parser.add_argument("--probe", default=str(DEFAULT_PROBE_PATH))
    parser.add_argument("--shadow-tracking", default=str(DEFAULT_SHADOW_TRACKING_PATH))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str, required=True):
    path = Path(path_str)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required input: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_policy_mode(city):
    lowered = str(city or "").strip().lower()
    if not lowered:
        return "unknown"
    if lowered in {str(item).strip().lower() for item in bot.BLOCKED_CITIES}:
        return "blocked"
    if city in bot.ACTIVE_TRADING_CITIES:
        return "active"
    if city in bot.CANARY_TRADING_CITIES:
        return "canary"
    return "shadow"


def find_city_row(rows, city):
    for row in rows or []:
        if row.get("city") == city:
            return row
    return {}


def build_reference_lookup(enrichment):
    lookup = {}
    for trader in enrichment.get("traders", []):
        label = trader.get("pseudonym") or trader.get("address", "")[:10]
        lookup[label] = trader
    return lookup


def summarize_reference_traders(city, reinforced_city, enrichment):
    reference_lookup = build_reference_lookup(enrichment)
    output = []
    for item in reinforced_city.get("reference_traders", []):
        label = item.get("trader")
        trader = reference_lookup.get(label)
        if not trader:
            continue
        output.append({
            "trader": label,
            "reference_quality": trader.get("reference_quality", ""),
            "closed_win_rate": trader.get("closed_summary", {}).get("win_rate"),
            "closed_pnl": trader.get("closed_summary", {}).get("total_closed_pnl"),
            "n_closed_directional_weather": trader.get("closed_summary", {}).get("n_closed_directional_weather"),
            "active_directional": trader.get("active_summary", {}).get("n_active_directional"),
            "top_active_cities": trader.get("active_summary", {}).get("top_active_cities", {}),
        })
    return output


def summarize_probe(city, probe):
    markets = [row for row in probe.get("markets", []) if row.get("city") == city]
    condition_counts = Counter(row.get("condition", "") for row in markets)
    forecast_values = [row.get("openmeteo_forecast_max_c") for row in markets if row.get("openmeteo_forecast_max_c") is not None]
    gaps = [row.get("forecast_vs_noaa_gap_c") for row in markets if row.get("forecast_vs_noaa_gap_c") is not None]
    comparable = [
        row for row in markets
        if row.get("market_prob_yes") is not None and 0.20 <= float(row.get("market_prob_yes")) <= 0.80
    ]
    return {
        "market_count": len(markets),
        "condition_counts": dict(condition_counts),
        "openmeteo_available": sum(1 for row in markets if row.get("openmeteo_forecast_max_c") is not None),
        "noaa_available": sum(1 for row in markets if row.get("noaa_observed_max_c") is not None),
        "avg_forecast_c": round(sum(forecast_values) / len(forecast_values), 2) if forecast_values else None,
        "avg_forecast_vs_noaa_gap_c": round(sum(gaps) / len(gaps), 2) if gaps else None,
        "comparable_market_count": len(comparable),
        "markets": [
            {
                "question": row.get("question"),
                "date_iso": row.get("date_iso"),
                "condition": row.get("condition"),
                "threshold": row.get("threshold"),
                "threshold_unit": row.get("threshold_unit"),
                "market_prob_yes": row.get("market_prob_yes"),
                "openmeteo_forecast_max_c": row.get("openmeteo_forecast_max_c"),
                "noaa_observed_max_c": row.get("noaa_observed_max_c"),
                "forecast_vs_noaa_gap_c": row.get("forecast_vs_noaa_gap_c"),
            }
            for row in markets[:8]
        ],
    }


def summarize_shadow_tracking(city, shadow_tracking):
    if not isinstance(shadow_tracking, dict):
        return {
            "available": False,
            "reason": "missing_file",
            "city_metrics": {},
            "matching_directional_history": [],
        }

    cities = shadow_tracking.get("cities", {})
    city_metrics = cities.get(city, {}) if isinstance(cities, dict) else {}
    history = shadow_tracking.get("directional_history", [])
    matches = [
        {
            "seen_at": row.get("seen_at"),
            "date": row.get("date"),
            "side": row.get("side"),
            "edge_hit": row.get("edge_hit"),
            "edge_pct": row.get("edge_pct"),
            "question": row.get("question"),
        }
        for row in history
        if isinstance(row, dict) and row.get("city") == city
    ][:10]
    return {
        "available": True,
        "reason": "ok",
        "city_metrics": {
            "markets_seen": int(city_metrics.get("markets_seen", 0) or 0),
            "edge_hits": int(city_metrics.get("edge_hits", 0) or 0),
            "cycles_seen": int(city_metrics.get("cycles_seen", 0) or 0),
            "best_edge_pct": float(city_metrics.get("best_edge_pct", 0) or 0),
            "best_ev": float(city_metrics.get("best_ev", 0) or 0),
            "last_date": city_metrics.get("last_date", ""),
            "last_question": city_metrics.get("last_question", ""),
            "recent_edges_count": len(city_metrics.get("recent_edges", []) if isinstance(city_metrics.get("recent_edges"), list) else []),
        },
        "matching_directional_history": matches,
    }


def summarize_audit(city, audit):
    if not isinstance(audit, dict):
        return {
            "available": False,
            "reason": "missing_file",
            "noaa_rows": 0,
            "latest_dates": [],
        }
    observed_rows = []
    for row in audit.get(bot.OBSERVED_AUDIT_KEY, []):
        if not isinstance(row, dict):
            continue
        if row.get("city") != city:
            continue
        if row.get("source") != "noaa_ncei":
            continue
        observed_rows.append(row)
    observed_rows.sort(key=lambda row: str(row.get("date", "")), reverse=True)
    return {
        "available": True,
        "reason": "ok",
        "noaa_rows": len(observed_rows),
        "latest_dates": [row.get("date") for row in observed_rows[:5]],
    }


def build_assessment(policy_mode, reinforced_city, probe_summary, shadow_summary, audit_summary, reference_traders):
    edge_hits = int(shadow_summary.get("city_metrics", {}).get("edge_hits", 0) or 0)
    cycles_seen = int(shadow_summary.get("city_metrics", {}).get("cycles_seen", 0) or 0)
    best_edge = float(shadow_summary.get("city_metrics", {}).get("best_edge_pct", 0) or 0)
    noaa_rows = int(audit_summary.get("noaa_rows", 0) or 0)
    market_count = int(probe_summary.get("market_count", 0) or 0)
    reference_count = len(reference_traders)

    if edge_hits >= bot.SHADOW_CANARY_MIN_EDGE_HITS and cycles_seen >= bot.SHADOW_CANARY_MIN_CYCLES:
        signal_status = "promising"
    elif market_count > 0 or edge_hits > 0 or cycles_seen > 0:
        signal_status = "building"
    else:
        signal_status = "none"

    if noaa_rows >= bot.OBSERVED_FORECAST_MIN_SAMPLE:
        data_quality = "strong"
    elif market_count > 0 or reference_count > 0:
        data_quality = "ok"
    else:
        data_quality = "weak"

    if signal_status == "promising" and data_quality in {"ok", "strong"} and reference_count >= 2:
        next_action = "prepare_controlled_test"
    elif market_count > 0 or reference_count > 0 or policy_mode == "shadow":
        next_action = "expand_observability"
    else:
        next_action = "stay_shadow"

    rationale = []
    if reference_count:
        rationale.append(f"{reference_count} referencias comparables")
    if market_count:
        rationale.append(f"{market_count} mercados visibles en probe")
    if edge_hits:
        rationale.append(f"{edge_hits} edge_hits shadow")
    if cycles_seen:
        rationale.append(f"{cycles_seen} ciclos con huella shadow")
    if noaa_rows:
        rationale.append(f"{noaa_rows} filas NOAA en audit")
    if best_edge:
        rationale.append(f"best_edge {best_edge:.1f}%")
    if not rationale:
        rationale.append("sin evidencia local suficiente todavia")

    return {
        "signal_status": signal_status,
        "data_quality": data_quality,
        "next_action": next_action,
        "rationale": "; ".join(rationale),
    }


def build_payload(args):
    city = args.city
    reinforced = load_json(args.reinforced, required=True)
    cross = load_json(args.cross, required=True)
    enrichment = load_json(args.enrichment, required=True)
    probe = load_json(args.probe, required=True)
    shadow_tracking = load_json(args.shadow_tracking, required=False)
    audit = load_json(args.audit, required=False)

    reinforced_city = find_city_row(reinforced.get("cities", []), city)
    cross_city = find_city_row(cross.get("city_rows", []), city)
    reference_traders = summarize_reference_traders(city, reinforced_city, enrichment)
    probe_summary = summarize_probe(city, probe)
    shadow_summary = summarize_shadow_tracking(city, shadow_tracking)
    audit_summary = summarize_audit(city, audit)

    policy_mode = get_policy_mode(city)
    resolution_meta = bot.RESOLUTION_ICAO.get(city, {})

    assessment = build_assessment(
        policy_mode=policy_mode,
        reinforced_city=reinforced_city,
        probe_summary=probe_summary,
        shadow_summary=shadow_summary,
        audit_summary=audit_summary,
        reference_traders=reference_traders,
    )

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "city": city,
        "policy_mode": policy_mode,
        "inputs": {
            "reinforced": args.reinforced,
            "cross": args.cross,
            "enrichment": args.enrichment,
            "probe": args.probe,
            "shadow_tracking": args.shadow_tracking,
            "audit": args.audit,
        },
        "baseline": {
            "allowed_conditions": ["at_or_above", "at_or_below"],
            "min_edge_pct": bot.MIN_EDGE,
            "shadow_canary_gate": {
                "edge_hits": bot.SHADOW_CANARY_MIN_EDGE_HITS,
                "cycles": bot.SHADOW_CANARY_MIN_CYCLES,
                "best_edge_pct": bot.SHADOW_CANARY_MIN_BEST_EDGE,
                "support": bot.SHADOW_CANARY_MIN_SUPPORT,
            },
            "observed_goal": bot.OBSERVED_FORECAST_MIN_SAMPLE,
        },
        "city_context": {
            "reinforced_action": reinforced_city.get("action"),
            "reinforced_next_step": reinforced_city.get("next_step"),
            "reinforced_priority_score": reinforced_city.get("priority_score"),
            "reference_count": reinforced_city.get("reference_count", len(reference_traders)),
            "cross_priority_score": cross_city.get("priority_score"),
            "resolution_icao": resolution_meta.get("icao", ""),
            "has_wu_url": bool(resolution_meta.get("wu_url")),
            "has_noaa_station_id": bool(resolution_meta.get("noaa_station_id")),
            "has_noaa_daily_station_id": bool(resolution_meta.get("noaa_daily_station_id")),
        },
        "reference_traders": reference_traders,
        "probe_summary": probe_summary,
        "shadow_tracking": shadow_summary,
        "audit_summary": audit_summary,
        "assessment": assessment,
    }


def render_markdown(payload):
    lines = [
        "# Shanghai Shadow Test",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- City: `{payload['city']}`",
        f"- Policy mode: `{payload['policy_mode']}`",
        f"- Assessment: `{payload['assessment']['next_action']}`",
        f"- Rationale: {payload['assessment']['rationale']}",
        "",
        "## Baseline",
        "",
        f"- Allowed conditions: `{', '.join(payload['baseline']['allowed_conditions'])}`",
        f"- MIN_EDGE: `{payload['baseline']['min_edge_pct']}`",
        f"- Shadow canary gate: `edges>={payload['baseline']['shadow_canary_gate']['edge_hits']}`, `cycles>={payload['baseline']['shadow_canary_gate']['cycles']}`, `best_edge>={payload['baseline']['shadow_canary_gate']['best_edge_pct']}`",
        f"- NOAA observed goal: `{payload['baseline']['observed_goal']}`",
        "",
        "## City Context",
        "",
        f"- Reinforced action: `{payload['city_context']['reinforced_action']}`",
        f"- Reinforced next step: `{payload['city_context']['reinforced_next_step']}`",
        f"- Reinforced priority: `{payload['city_context']['reinforced_priority_score']}`",
        f"- Cross priority: `{payload['city_context']['cross_priority_score']}`",
        f"- Reference traders: `{payload['city_context']['reference_count']}`",
        f"- Resolution ICAO: `{payload['city_context']['resolution_icao']}`",
        f"- NOAA configured: `{payload['city_context']['has_noaa_station_id']}`",
        "",
    ]

    if payload["reference_traders"]:
        lines.extend([
            "## Reference Traders",
            "",
            "| Trader | Quality | Closed WR | Closed PnL | Closed directional | Active directional |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for trader in payload["reference_traders"]:
            lines.append(
                f"| {trader['trader']} | {trader['reference_quality']} | {trader['closed_win_rate']} | "
                f"{trader['closed_pnl']} | {trader['n_closed_directional_weather']} | {trader['active_directional']} |"
            )
        lines.append("")

    lines.extend([
        "## Probe Summary",
        "",
        f"- Market count: `{payload['probe_summary']['market_count']}`",
        f"- Comparable price-range markets: `{payload['probe_summary']['comparable_market_count']}`",
        f"- Open-Meteo available: `{payload['probe_summary']['openmeteo_available']}`",
        f"- NOAA available: `{payload['probe_summary']['noaa_available']}`",
        f"- Avg forecast C: `{payload['probe_summary']['avg_forecast_c']}`",
        f"- Avg forecast vs NOAA gap C: `{payload['probe_summary']['avg_forecast_vs_noaa_gap_c']}`",
        "",
    ])

    if payload["probe_summary"]["markets"]:
        lines.extend([
            "| Date | Condition | Threshold | Mkt YES | Open-Meteo C | NOAA C | Gap C |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])
        for market in payload["probe_summary"]["markets"]:
            threshold = f"{market['threshold']}{market['threshold_unit']}"
            lines.append(
                f"| {market['date_iso']} | {market['condition']} | {threshold} | {market['market_prob_yes']} | "
                f"{market['openmeteo_forecast_max_c']} | {market['noaa_observed_max_c']} | {market['forecast_vs_noaa_gap_c']} |"
            )
        lines.append("")

    lines.extend([
        "## Shadow Tracking",
        "",
        f"- Available: `{payload['shadow_tracking']['available']}`",
        f"- Reason: `{payload['shadow_tracking']['reason']}`",
    ])
    city_metrics = payload["shadow_tracking"].get("city_metrics", {})
    if city_metrics:
        lines.extend([
            f"- Markets seen: `{city_metrics.get('markets_seen')}`",
            f"- Edge hits: `{city_metrics.get('edge_hits')}`",
            f"- Cycles seen: `{city_metrics.get('cycles_seen')}`",
            f"- Best edge pct: `{city_metrics.get('best_edge_pct')}`",
            f"- Best EV: `{city_metrics.get('best_ev')}`",
            "",
        ])
    else:
        lines.append("")

    if payload["shadow_tracking"].get("matching_directional_history"):
        lines.extend([
            "| Seen at | Date | Side | Edge hit | Edge pct | Question |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for row in payload["shadow_tracking"]["matching_directional_history"]:
            lines.append(
                f"| {row['seen_at']} | {row['date']} | {row['side']} | {row['edge_hit']} | {row['edge_pct']} | {row['question']} |"
            )
        lines.append("")

    lines.extend([
        "## Audit Summary",
        "",
        f"- Available: `{payload['audit_summary']['available']}`",
        f"- Reason: `{payload['audit_summary']['reason']}`",
        f"- NOAA rows for city: `{payload['audit_summary']['noaa_rows']}`",
        f"- Latest dates: `{', '.join(payload['audit_summary']['latest_dates'])}`",
        "",
        "## Assessment",
        "",
        f"- Signal status: `{payload['assessment']['signal_status']}`",
        f"- Data quality: `{payload['assessment']['data_quality']}`",
        f"- Next action: `{payload['assessment']['next_action']}`",
        f"- Rationale: {payload['assessment']['rationale']}",
        "",
    ])
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    payload = build_payload(args)
    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Shanghai shadow test written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["assessment"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
