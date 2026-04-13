#!/usr/bin/env python3
"""Read-only Chicago active benchmark snapshot."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import bot  # type: ignore
from shanghai_shadow_test import build_payload as build_city_payload  # type: ignore


DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "chicago_active_benchmark.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "chicago_active_benchmark_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera un snapshot read-only de Chicago como benchmark operativo active."
    )
    parser.add_argument("--city", default="Chicago")
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


def build_benchmark_assessment(payload):
    city_context = payload.get("city_context", {})
    probe_summary = payload.get("probe_summary", {})
    shadow_tracking = payload.get("shadow_tracking", {})
    audit_summary = payload.get("audit_summary", {})
    references = payload.get("reference_traders", [])

    reference_count = len(references)
    probe_market_count = int(probe_summary.get("market_count", 0) or 0)
    noaa_rows = int(audit_summary.get("noaa_rows", 0) or 0)
    shadow_available = bool(shadow_tracking.get("available"))
    active_policy = payload.get("policy_mode") == "active"

    if active_policy and reference_count >= 2:
        benchmark_strength = "credible"
    elif reference_count >= 1:
        benchmark_strength = "partial"
    else:
        benchmark_strength = "weak"

    if noaa_rows >= bot.OBSERVED_FORECAST_MIN_SAMPLE:
        observability_status = "strong"
    elif probe_market_count > 0 or city_context.get("has_noaa_station_id"):
        observability_status = "ok"
    else:
        observability_status = "thin"

    if benchmark_strength == "credible" and observability_status in {"ok", "strong"}:
        next_action = "use_as_active_benchmark"
    elif benchmark_strength == "partial":
        next_action = "keep_under_watch"
    else:
        next_action = "insufficient_benchmark_signal"

    rationale = []
    if active_policy:
        rationale.append("ciudad active")
    if reference_count:
        rationale.append(f"{reference_count} referencias comparables")
    if probe_market_count:
        rationale.append(f"{probe_market_count} mercados visibles en probe")
    if noaa_rows:
        rationale.append(f"{noaa_rows} filas NOAA en audit")
    if shadow_available:
        rationale.append("shadow tracking local disponible")
    if not rationale:
        rationale.append("sin evidencia local suficiente todavia")

    return {
        "benchmark_strength": benchmark_strength,
        "observability_status": observability_status,
        "next_action": next_action,
        "rationale": "; ".join(rationale),
    }


def render_markdown(payload):
    benchmark = payload["benchmark_assessment"]
    lines = [
        "# Chicago Active Benchmark",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- City: `{payload['city']}`",
        f"- Policy mode: `{payload['policy_mode']}`",
        f"- Next action: `{benchmark['next_action']}`",
        f"- Rationale: {benchmark['rationale']}",
        "",
        "## Benchmark Role",
        "",
        f"- Benchmark strength: `{benchmark['benchmark_strength']}`",
        f"- Observability status: `{benchmark['observability_status']}`",
        f"- Reinforced action: `{payload['city_context']['reinforced_action']}`",
        f"- Reinforced next step: `{payload['city_context']['reinforced_next_step']}`",
        f"- Cross priority: `{payload['city_context']['cross_priority_score']}`",
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
        f"- Comparable probe markets: `{payload['probe_summary']['comparable_market_count']}`",
        f"- Open-Meteo available: `{payload['probe_summary']['openmeteo_available']}`",
        f"- NOAA available: `{payload['probe_summary']['noaa_available']}`",
        f"- Avg forecast C: `{payload['probe_summary']['avg_forecast_c']}`",
        "",
        "## Local Evidence",
        "",
        f"- Shadow tracking available: `{payload['shadow_tracking']['available']}`",
        f"- Audit available: `{payload['audit_summary']['available']}`",
        f"- Audit NOAA rows: `{payload['audit_summary']['noaa_rows']}`",
        "",
    ])
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    base_payload = build_city_payload(args)
    benchmark_assessment = build_benchmark_assessment(base_payload)
    payload = {
        **base_payload,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "benchmark_assessment": benchmark_assessment,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Chicago benchmark written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(benchmark_assessment, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
