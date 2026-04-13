#!/usr/bin/env python3
"""Contrast multiple city test snapshots for the next operational decision."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from shanghai_shadow_test import build_payload  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_phase5_contrast.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_phase5_contrast_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compara ciudades prioritarias para decidir la siguiente fase operativa."
    )
    parser.add_argument("--cities", default="Shanghai,Chicago,Seoul")
    parser.add_argument("--reinforced", default=str(REPO_ROOT / "data" / "city_watch_reinforced.json"))
    parser.add_argument("--cross", default=str(REPO_ROOT / "data" / "reference_trader_city_market_cross.json"))
    parser.add_argument("--enrichment", default=str(REPO_ROOT / "data" / "directional_trader_enrichment.json"))
    parser.add_argument("--probe", default=str(REPO_ROOT / "data" / "settlement_fidelity_probe.json"))
    parser.add_argument("--shadow-tracking", default=str(REPO_ROOT / "data" / "shadow_city_tracking.json"))
    parser.add_argument("--audit", default=str(REPO_ROOT / "data" / "audit.json"))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def normalize_cities(raw):
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_city_snapshot(base_args, city):
    args = argparse.Namespace(
        city=city,
        reinforced=base_args.reinforced,
        cross=base_args.cross,
        enrichment=base_args.enrichment,
        probe=base_args.probe,
        shadow_tracking=base_args.shadow_tracking,
        audit=base_args.audit,
        json_output="",
        md_output="",
    )
    payload = build_payload(args)
    assessment = payload.get("assessment", {})
    city_context = payload.get("city_context", {})
    probe_summary = payload.get("probe_summary", {})
    shadow_tracking = payload.get("shadow_tracking", {})
    audit_summary = payload.get("audit_summary", {})
    return {
        "city": city,
        "policy_mode": payload.get("policy_mode"),
        "reinforced_action": city_context.get("reinforced_action"),
        "reference_count": city_context.get("reference_count"),
        "cross_priority_score": city_context.get("cross_priority_score"),
        "probe_market_count": probe_summary.get("market_count"),
        "comparable_probe_markets": probe_summary.get("comparable_market_count"),
        "openmeteo_available": probe_summary.get("openmeteo_available"),
        "noaa_available": probe_summary.get("noaa_available"),
        "shadow_tracking_available": shadow_tracking.get("available"),
        "shadow_edge_hits": shadow_tracking.get("city_metrics", {}).get("edge_hits", 0),
        "shadow_cycles_seen": shadow_tracking.get("city_metrics", {}).get("cycles_seen", 0),
        "audit_noaa_rows": audit_summary.get("noaa_rows", 0),
        "signal_status": assessment.get("signal_status"),
        "data_quality": assessment.get("data_quality"),
        "next_action": assessment.get("next_action"),
        "rationale": assessment.get("rationale"),
        "full_snapshot": payload,
    }


def rank_cities(rows):
    def score(row):
        next_action = row.get("next_action")
        action_score = {
            "prepare_controlled_test": 3,
            "expand_observability": 2,
            "stay_shadow": 1,
        }.get(next_action, 0)
        signal_score = {
            "promising": 3,
            "building": 2,
            "none": 1,
        }.get(row.get("signal_status"), 0)
        policy_bonus = 1 if row.get("policy_mode") == "active" else 0
        return (
            action_score,
            signal_score,
            int(row.get("reference_count") or 0),
            int(row.get("probe_market_count") or 0),
            int(row.get("cross_priority_score") or 0) + policy_bonus,
        )

    return sorted(rows, key=score, reverse=True)


def build_recommendation(ranked_rows):
    if not ranked_rows:
        return {
            "primary_city": None,
            "secondary_city": None,
            "recommended_next_step": "insufficient_data",
            "note": "No hay ciudades para comparar.",
        }
    primary = ranked_rows[0]
    secondary = ranked_rows[1] if len(ranked_rows) > 1 else None
    if primary.get("city") == "Shanghai":
        step = "continue_shanghai_observability_plus_active_contrast"
        note = (
            "Shanghai sigue siendo la ciudad puente principal, pero ahora queda contrastada "
            "contra una activa real para evitar sobreajuste narrativo."
        )
    elif primary.get("policy_mode") == "active":
        step = "benchmark_active_city_before_shadow_escalation"
        note = "La ciudad activa ofrece mejor base inmediata; conviene usarla como benchmark antes de escalar shadow."
    else:
        step = "expand_cross_city_observability"
        note = "La evidencia sigue repartida; conviene ampliar observabilidad cruzada antes de decidir."
    return {
        "primary_city": primary.get("city"),
        "secondary_city": secondary.get("city") if secondary else None,
        "recommended_next_step": step,
        "note": note,
    }


def render_markdown(payload):
    lines = [
        "# City Phase 5 Contrast",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Recommended next step: `{payload['recommendation']['recommended_next_step']}`",
        f"- Note: {payload['recommendation']['note']}",
        "",
        "## Ranking",
        "",
        "| City | Policy | References | Probe mkts | Signal | Data | Next action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["cities_ranked"]:
        lines.append(
            f"| {row['city']} | {row['policy_mode']} | {row['reference_count']} | {row['probe_market_count']} | "
            f"{row['signal_status']} | {row['data_quality']} | {row['next_action']} |"
        )
    lines.extend(["", "## City Notes", ""])
    for row in payload["cities_ranked"]:
        lines.extend([
            f"### {row['city']}",
            "",
            f"- Rationale: {row['rationale']}",
            f"- Reinforced action: `{row['reinforced_action']}`",
            f"- Cross priority: `{row['cross_priority_score']}`",
            f"- Shadow tracking available: `{row['shadow_tracking_available']}`",
            f"- Audit NOAA rows: `{row['audit_noaa_rows']}`",
            "",
        ])
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    cities = normalize_cities(args.cities)
    rows = [build_city_snapshot(args, city) for city in cities]
    ranked = rank_cities(rows)
    recommendation = build_recommendation(ranked)
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "reinforced": args.reinforced,
            "cross": args.cross,
            "enrichment": args.enrichment,
            "probe": args.probe,
            "shadow_tracking": args.shadow_tracking,
            "audit": args.audit,
        },
        "cities_ranked": ranked,
        "recommendation": recommendation,
    }
    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"City contrast written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(recommendation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
