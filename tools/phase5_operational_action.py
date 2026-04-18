#!/usr/bin/env python3
"""Convert phase-5 visibility evidence into a bounded operational action."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKER_PATH = REPO_ROOT / "data" / "city_probe_visibility_tracker.json"
DEFAULT_COMPARATOR_PATH = REPO_ROOT / "data" / "shanghai_vs_chicago_comparator.json"
DEFAULT_SHANGHAI_PATH = REPO_ROOT / "data" / "shanghai_shadow_test.json"
DEFAULT_CHICAGO_PATH = REPO_ROOT / "data" / "chicago_active_benchmark.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "phase5_operational_action.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "phase5_operational_action_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Clasifica la alerta Shanghai+Chicago en un estado operativo acotado "
            "sin ejecutar trading ni cambiar policy."
        )
    )
    parser.add_argument("--tracker", default=str(DEFAULT_TRACKER_PATH))
    parser.add_argument("--comparator", default=str(DEFAULT_COMPARATOR_PATH))
    parser.add_argument("--shanghai", default=str(DEFAULT_SHANGHAI_PATH))
    parser.add_argument("--chicago", default=str(DEFAULT_CHICAGO_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8-sig"))


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_latest_simultaneous_snapshot(tracker):
    history = tracker.get("history", [])
    simultaneous = [row for row in history if isinstance(row, dict) and row.get("simultaneous_visibility")]
    return simultaneous[-1] if simultaneous else {}


def derive_gap_trend(coincidence_count, dominant_gap, latest_snapshot, shanghai, chicago):
    shanghai_market_count = int(latest_snapshot.get("cities", {}).get("Shanghai", {}).get("market_count", 0) or 0)
    chicago_market_count = int(latest_snapshot.get("cities", {}).get("Chicago", {}).get("market_count", 0) or 0)
    shanghai_signal = shanghai.get("assessment", {}).get("signal_status")
    chicago_strength = chicago.get("benchmark_assessment", {}).get("benchmark_strength")

    if coincidence_count <= 1:
        return "new"
    if (
        dominant_gap == "evidence_asymmetry_between_shadow_and_active"
        and chicago_strength == "credible"
        and shanghai_signal == "building"
        and shanghai_market_count > 0
        and chicago_market_count > 0
    ):
        return "persistent"
    if coincidence_count >= 10 and dominant_gap == "market_visibility_and_selection":
        return "reframed"
    if coincidence_count >= 6:
        return "reinforced"
    return "stable"


def classify_action(tracker, comparator, shanghai, chicago):
    summary = tracker.get("summary", {})
    coincidence_count = int(summary.get("simultaneous_visibility_count", 0) or 0)
    latest_snapshot = get_latest_simultaneous_snapshot(tracker)
    dominant_gap = comparator.get("gap", {}).get("dominant_gap", "unknown")
    comparator_next_step = comparator.get("recommendation", {}).get("next_step", "unknown")
    shanghai_signal = shanghai.get("assessment", {}).get("signal_status", "unknown")
    chicago_strength = chicago.get("benchmark_assessment", {}).get("benchmark_strength", "unknown")
    shanghai_markets = int(latest_snapshot.get("cities", {}).get("Shanghai", {}).get("market_count", 0) or 0)
    chicago_markets = int(latest_snapshot.get("cities", {}).get("Chicago", {}).get("market_count", 0) or 0)
    gap_trend = derive_gap_trend(
        coincidence_count=coincidence_count,
        dominant_gap=dominant_gap,
        latest_snapshot=latest_snapshot,
        shanghai=shanghai,
        chicago=chicago,
    )

    severity = "info"
    action_state = "observe"
    next_operational_step = "keep_accumulating_shadow_evidence"
    closure_type = "gate_defined"
    closure_label = "gate definido"
    decision_note = (
        "La coincidencia existe, pero la lectura sigue siendo de observación read-only sin "
        "base suficiente para abrir revisión de policy o test controlado."
    )
    operational_change = (
        "El caso queda dentro del gate de observación y no debe cerrar solo como documentación; "
        "la siguiente coincidencia útil debe reevaluar si pasa a review prioritaria, test controlado "
        "o revisión de policy."
    )

    if coincidence_count == 0:
        severity = "info"
        action_state = "no_progress"
        next_operational_step = "deprioritize_case"
        closure_type = "alarm_rewritten"
        closure_label = "alarma reescrita"
        decision_note = "No hay coincidencias simultáneas acumuladas para justificar prioridad operativa."
        operational_change = (
            "La alarma deja de aportar valor operativo mientras no exista coincidencia simultánea; "
            "debe permanecer silenciosa hasta que vuelva a abrir un gate real."
        )
    elif dominant_gap == "evidence_asymmetry_between_shadow_and_active":
        if coincidence_count >= 8 and shanghai_markets > 0 and chicago_markets > 0:
            severity = "watch"
            action_state = "review"
            next_operational_step = "increase_review_priority"
            decision_note = (
                "La señal ya no parece aislada: el patrón Shanghai+Chicago se repite y merece "
                "revisión activa como caso de comparación hacia monetización, todavía sin abrir "
                "trading ni policy."
            )
            operational_change = (
                "El caso sube a la cola de review prioritaria: Shanghai deja de ser solo una ciudad "
                "a observar y pasa a compararse explícitamente contra Chicago como benchmark active "
                "en cualquier revisión de monetización."
            )
        elif coincidence_count >= 3:
            severity = "info"
            action_state = "observe"
            next_operational_step = "keep_accumulating_shadow_evidence"
            decision_note = (
                "La asimetría de evidencia ya existe, pero aún no llega a un nivel que obligue "
                "a una revisión operativa prioritaria."
            )
            operational_change = (
                "Se mantiene el gate de acumulación: la operativa no cambia todavía, pero el caso "
                "queda vivo y no debe cerrarse solo con documentación."
            )
    elif dominant_gap == "market_visibility_and_selection":
        if coincidence_count >= 3 and shanghai_signal == "building":
            severity = "watch"
            action_state = "review"
            next_operational_step = "increase_review_priority"
            decision_note = (
                "El patrón repetido sugiere que conviene revisar visibilidad/selección como "
                "paso previo antes de inferir edge o policy."
            )
            operational_change = (
                "El foco operativo cambia de observación pasiva a revisión del filtro de visibilidad "
                "y selección antes de discutir edge o policy."
            )

    if (
        severity in {"watch", "info"}
        and coincidence_count >= 12
        and shanghai_signal in {"building", "ready"}
        and chicago_strength == "credible"
        and shanghai_markets > 0
        and chicago_markets > 0
    ):
        severity = "actionable_review"
        action_state = "controlled_test_candidate"
        next_operational_step = "open_controlled_test_review"
        closure_type = "gate_defined"
        closure_label = "gate definido"
        decision_note = (
            "La coincidencia repetida y la comparabilidad suficiente justifican abrir una "
            "revisión humana acotada sobre test controlado, todavía en modo read-only."
        )
        operational_change = (
            "Se abre el gate formal para revisión de test controlado: la siguiente sesión debe "
            "salir con patch listo, cambio ejecutado o rechazo explícito del test."
        )

    if (
        coincidence_count >= 15
        and dominant_gap == "evidence_asymmetry_between_shadow_and_active"
        and shanghai_signal == "ready"
        and chicago_strength == "credible"
    ):
        severity = "policy_candidate"
        action_state = "policy_candidate"
        next_operational_step = "open_policy_gate_review"
        closure_type = "gate_defined"
        closure_label = "gate definido"
        decision_note = (
            "La repetición ya no sugiere solo falta de evidencia; empieza a parecer un caso "
            "honesto para revisar gating/policy."
        )
        operational_change = (
            "Se abre el gate formal de policy: la siguiente intervención debe decidir un cambio "
            "ejecutado, dejar un patch listo o cerrar el caso con rechazo explícito."
        )

    promotion_readiness = "not_ready"
    if action_state == "controlled_test_candidate":
        promotion_readiness = "candidate_for_controlled_test"
    elif action_state == "policy_candidate":
        promotion_readiness = "candidate_for_policy_review"

    policy_review_priority = "low"
    if next_operational_step == "increase_review_priority":
        policy_review_priority = "medium"
    elif next_operational_step in {"open_controlled_test_review", "open_policy_gate_review"}:
        policy_review_priority = "high"

    return {
        "trigger_probe_generated_at": latest_snapshot.get("probe_generated_at") or summary.get("latest_probe_generated_at"),
        "coincidence_count": coincidence_count,
        "candidate_city": "Shanghai",
        "benchmark_city": "Chicago",
        "dominant_gap": dominant_gap,
        "comparator_next_step": comparator_next_step,
        "gap_trend": gap_trend,
        "severity": severity,
        "action_state": action_state,
        "next_operational_step": next_operational_step,
        "closure_type": closure_type,
        "closure_label": closure_label,
        "decision_note": decision_note,
        "operational_change": operational_change,
        "promotion_readiness": promotion_readiness,
        "policy_review_priority": policy_review_priority,
        "evidence_snapshot": {
            "shanghai_market_count": shanghai_markets,
            "chicago_market_count": chicago_markets,
            "shanghai_signal_status": shanghai_signal,
            "chicago_benchmark_strength": chicago_strength,
        },
    }


def render_markdown(payload):
    action = payload["action"]
    lines = [
        "# Phase 5 Operational Action",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Trigger probe: `{action['trigger_probe_generated_at']}`",
        f"- Coincidence count: `{action['coincidence_count']}`",
        f"- Dominant gap: `{action['dominant_gap']}`",
        f"- Gap trend: `{action['gap_trend']}`",
        f"- Severity: `{action['severity']}`",
        f"- Action state: `{action['action_state']}`",
        f"- Next operational step: `{action['next_operational_step']}`",
        f"- Closure type: `{action['closure_type']}`",
        f"- Promotion readiness: `{action['promotion_readiness']}`",
        f"- Policy review priority: `{action['policy_review_priority']}`",
        "",
        "## Decision",
        "",
        action["decision_note"],
        "",
        "## Operational Change",
        "",
        action["operational_change"],
        "",
        "## Evidence Snapshot",
        "",
        f"- Shanghai market count: `{action['evidence_snapshot']['shanghai_market_count']}`",
        f"- Chicago market count: `{action['evidence_snapshot']['chicago_market_count']}`",
        f"- Shanghai signal status: `{action['evidence_snapshot']['shanghai_signal_status']}`",
        f"- Chicago benchmark strength: `{action['evidence_snapshot']['chicago_benchmark_strength']}`",
        f"- Comparator next step: `{action['comparator_next_step']}`",
        "",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()
    tracker = load_json(args.tracker)
    comparator = load_json(args.comparator)
    shanghai = load_json(args.shanghai)
    chicago = load_json(args.chicago)

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "tracker": args.tracker,
            "comparator": args.comparator,
            "shanghai": args.shanghai,
            "chicago": args.chicago,
        },
        "action": classify_action(tracker, comparator, shanghai, chicago),
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Operational action written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["action"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
