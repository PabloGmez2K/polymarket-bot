#!/usr/bin/env python3
"""Direct operational comparator between Shanghai shadow test and Chicago active benchmark."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHANGHAI_PATH = REPO_ROOT / "data" / "shanghai_shadow_test.json"
DEFAULT_CHICAGO_PATH = REPO_ROOT / "data" / "chicago_active_benchmark.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "shanghai_vs_chicago_comparator.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "shanghai_vs_chicago_comparator_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compara Shanghai vs Chicago para identificar el gap operativo dominante."
    )
    parser.add_argument("--shanghai", default=str(DEFAULT_SHANGHAI_PATH))
    parser.add_argument("--chicago", default=str(DEFAULT_CHICAGO_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def compare_dimensions(shanghai, chicago):
    s_ctx = shanghai.get("city_context", {})
    c_ctx = chicago.get("city_context", {})
    s_probe = shanghai.get("probe_summary", {})
    c_probe = chicago.get("probe_summary", {})
    s_assessment = shanghai.get("assessment", {})
    c_assessment = chicago.get("benchmark_assessment", {})

    dims = []

    dims.append({
        "dimension": "policy_role",
        "shanghai": shanghai.get("policy_mode"),
        "chicago": chicago.get("policy_mode"),
        "winner": "Chicago",
        "reading": "Chicago ya opera en modo active; Shanghai sigue en shadow y aun actua como ciudad puente.",
    })

    dims.append({
        "dimension": "reference_depth",
        "shanghai": s_ctx.get("reference_count", 0),
        "chicago": c_ctx.get("reference_count", 0),
        "winner": "Shanghai" if int(s_ctx.get("reference_count", 0) or 0) > int(c_ctx.get("reference_count", 0) or 0) else "Chicago",
        "reading": "Shanghai tiene mas referencias comparables alrededor; Chicago tiene menos, pero de calidad alta y mas alineadas al universo active.",
    })

    dims.append({
        "dimension": "current_market_visibility",
        "shanghai": s_probe.get("market_count", 0),
        "chicago": c_probe.get("market_count", 0),
        "winner": "Shanghai" if int(s_probe.get("market_count", 0) or 0) > int(c_probe.get("market_count", 0) or 0) else "Chicago",
        "reading": "En el snapshot local Shanghai tenia mercados visibles; Chicago no aparecia en probe.",
    })

    dims.append({
        "dimension": "comparable_market_visibility",
        "shanghai": s_probe.get("comparable_market_count", 0),
        "chicago": c_probe.get("comparable_market_count", 0),
        "winner": "Tie",
        "reading": "Ninguna de las dos mostro mercados en rango comparable 0.20-0.80 en este snapshot local.",
    })

    dims.append({
        "dimension": "next_read_only_action",
        "shanghai": s_assessment.get("next_action"),
        "chicago": c_assessment.get("next_action"),
        "winner": "Split",
        "reading": "Shanghai pide expand_observability; Chicago pide use_as_active_benchmark. Cumplen roles distintos y complementarios.",
    })

    return dims


def identify_gap(shanghai, chicago):
    s_probe = shanghai.get("probe_summary", {})
    c_probe = chicago.get("probe_summary", {})
    s_assessment = shanghai.get("assessment", {})
    chicago_benchmark = chicago.get("benchmark_assessment", {})

    if int(s_probe.get("market_count", 0) or 0) > 0 and int(c_probe.get("market_count", 0) or 0) == 0:
        gap = "market_visibility_and_selection"
        note = (
            "El mayor gap observable hoy no parece ser forecast puro, sino visibilidad/seleccion: "
            "Shanghai aparece en el flujo de mercados y Chicago no en este snapshot."
        )
    elif s_assessment.get("signal_status") == "building" and chicago_benchmark.get("benchmark_strength") == "credible":
        gap = "evidence_asymmetry_between_shadow_and_active"
        note = (
            "Chicago ya sirve como benchmark active creible, mientras Shanghai aun acumula evidencia. "
            "El cuello actual es la asimetria de evidencia, no una conclusion cerrada sobre edge."
        )
    else:
        gap = "insufficient_live_evidence"
        note = "Los dos snapshots siguen muy limitados por falta de shadow_tracking/audit live local."
    return {"dominant_gap": gap, "note": note}


def build_recommendation(gap_info):
    gap = gap_info["dominant_gap"]
    if gap == "market_visibility_and_selection":
        return {
            "next_step": "track_chicago_visibility_and_compare_when_probe_catches_it",
            "note": "La siguiente mejora debe reforzar la observabilidad comparativa de mercados visibles antes de inferir timing o forecast edge.",
        }
    if gap == "evidence_asymmetry_between_shadow_and_active":
        return {
            "next_step": "use_chicago_as_benchmark_while_shanghai_accumulates_shadow_evidence",
            "note": "La mejor secuencia ahora es usar Chicago como baseline active y seguir acumulando evidencia en Shanghai.",
        }
    return {
        "next_step": "wait_for_live_shadow_and_audit_data",
        "note": "Antes de profundizar en gap de edge hace falta evidencia live adicional.",
    }


def render_markdown(payload):
    lines = [
        "# Shanghai vs Chicago Comparator",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Dominant gap: `{payload['gap']['dominant_gap']}`",
        f"- Gap note: {payload['gap']['note']}",
        f"- Recommended next step: `{payload['recommendation']['next_step']}`",
        f"- Recommendation note: {payload['recommendation']['note']}",
        "",
        "## Dimension Comparison",
        "",
        "| Dimension | Shanghai | Chicago | Winner | Reading |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["dimensions"]:
        lines.append(
            f"| {row['dimension']} | {row['shanghai']} | {row['chicago']} | {row['winner']} | {row['reading']} |"
        )
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    shanghai = load_json(args.shanghai)
    chicago = load_json(args.chicago)
    dimensions = compare_dimensions(shanghai, chicago)
    gap = identify_gap(shanghai, chicago)
    recommendation = build_recommendation(gap)
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "shanghai": args.shanghai,
            "chicago": args.chicago,
        },
        "dimensions": dimensions,
        "gap": gap,
        "recommendation": recommendation,
    }
    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Comparator written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps({"gap": gap, "recommendation": recommendation}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
