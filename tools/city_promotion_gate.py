#!/usr/bin/env python3
"""Turn the city validation ledger into an explicit review queue and promotion gate."""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER_PATH = REPO_ROOT / "data" / "city_validation_ledger.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_promotion_gate.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_promotion_gate_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evalua el ledger y deja una cola explicita de revision/promocion por ciudad."
    )
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_codex_prompt(row, objective):
    city = row["city"]
    return (
        f"Revisa {city} dentro del city intelligence con foco en lectura operativa y evidencia util. "
        f"Lee AGENTS.md, el bloque reciente de CONTEXTO.md, data/city_validation_ledger.json, "
        f"data/city_promotion_gate.json y docs/city_intelligence_pipeline_latest.md. "
        f"Objetivo: {objective}. "
        f"Quiero un diagnostico claro del cuello de botella actual, si esto cambia la lectura operativa de hoy, "
        f"y el siguiente paso concreto sin tocar bot.py, policy live ni estado runtime salvo necesidad justificada."
    )


def compute_gate(row):
    recommendation = row.get("recommendation")
    bottleneck = row.get("bottleneck")
    policy_mode = row.get("policy_mode")
    runtime_policy_mode = row.get("runtime_policy_mode")
    cross_policy_mode = row.get("cross_policy_mode")
    drift_flags = row.get("drift_flags") or []
    visibility_score = row.get("visibility_evidence", {}).get("score", 0)
    edge_score = row.get("edge_evidence", {}).get("score", 0)
    structural_block_guardrail = row.get("structural_block_guardrail") or {}
    recent_skip_summary = row.get("recent_skip_evidence", {}) or {}
    useful_policy_gate_count = int(recent_skip_summary.get("useful_policy_gate_count", 0) or 0)

    if (
        runtime_policy_mode == "auto_canary"
        and useful_policy_gate_count == 0
        and "runtime_policy_collision" not in drift_flags
    ):
        return {
            "gate_status": "observe_runtime_canary",
            "review_priority": "watch",
            "codex_instruction": (
                f"Observar {row['city']} como canary runtime ya activo; el siguiente paso es medir "
                "si convierte edge/NOAA en evidencia operativa, no reabrir drift viejo."
            ),
            "codex_prompt": build_codex_prompt(
                row,
                "observar la ciudad como canary runtime ya activo y decidir como medir mejor su validacion operativa sin reabrir drift analitico viejo",
            ),
        }

    if (
        any(flag in drift_flags for flag in {"policy_divergence", "runtime_policy_collision"})
        or recommendation == "audit_runtime_drift"
    ):
        return {
            "gate_status": "audit_runtime_drift",
            "review_priority": "now",
            "codex_instruction": (
                f"Auditar drift de policy en {row['city']}: runtime={runtime_policy_mode}, "
                f"cross={cross_policy_mode}. No pedir canary si runtime ya decidio."
            ),
            "codex_prompt": build_codex_prompt(
                row,
                "auditar la divergencia entre policy runtime y policy analitica sin escribir estado runtime ni tocar bot.py",
            ),
        }
    if recommendation == "observe_runtime_canary":
        return {
            "gate_status": "observe_runtime_canary",
            "review_priority": "watch",
            "codex_instruction": f"Observar {row['city']} como canary runtime ya existente; no reabrir promocion.",
            "codex_prompt": build_codex_prompt(
                row,
                "observar la ciudad como canary runtime ya activo y separar evidencia operativa de validacion analitica",
            ),
        }
    if recommendation == "observe_runtime_blocked":
        return {
            "gate_status": "observe_runtime_blocked",
            "review_priority": "watch",
            "codex_instruction": f"Observar {row['city']} como bloqueada por runtime; no usar blocked como pausa operativa.",
            "codex_prompt": build_codex_prompt(
                row,
                "confirmar que el bloqueo runtime responde a fuente rota y no a pausa operativa",
            ),
        }
    if policy_mode == "blocked" and structural_block_guardrail:
        return {
            "gate_status": "blocked_with_signal",
            "review_priority": "soon" if (edge_score > 0 or visibility_score > 0) else "watch",
            "codex_instruction": (
                f"Revisar si {row['city']} sigue bloqueada por mismatch settlement/source documentado "
                f"o si el aviso analitico necesita refresh."
            ),
            "codex_prompt": build_codex_prompt(
                row,
                "auditar si el bloqueo estructural sigue bien modelado en city intelligence y separar fuente rota real de policy heredada",
            ),
        }
    if recommendation == "candidate_for_canary_validation":
        return {
            "gate_status": "review_for_canary",
            "review_priority": "now",
            "codex_instruction": f"Revisar {row['city']} para posible canary pequeno; validar shadow y source fidelity antes de tocar policy.",
            "codex_prompt": build_codex_prompt(
                row,
                "determinar si esta ciudad ya merece pasar a canary pequeno o si aun necesita mas validacion shadow/source fidelity",
            ),
        }
    if recommendation == "review_block_reason":
        return {
            "gate_status": "review_block_reason",
            "review_priority": "now",
            "codex_instruction": f"Revisar {row['city']} porque sigue bloqueada pero acumula senal externa util.",
            "codex_prompt": build_codex_prompt(
                row,
                "determinar si el bloqueo sigue justificado o si esta ciudad merece una ruta de validacion distinta",
            ),
        }
    if recommendation == "shadow_reinforced":
        return {
            "gate_status": "promote_to_shadow_validation",
            "review_priority": "soon",
            "codex_instruction": f"Refuerza observabilidad shadow en {row['city']} y mide si nuestro bot habria tenido edge propio.",
            "codex_prompt": build_codex_prompt(
                row,
                "disenar la siguiente mejora de validacion shadow para convertir discovery externo en evidencia propia util",
            ),
        }
    if recommendation == "watch_active_benchmark":
        return {
            "gate_status": "use_as_benchmark",
            "review_priority": "watch",
            "codex_instruction": f"Usar {row['city']} como benchmark activo para comparar contra candidatas shadow.",
            "codex_prompt": build_codex_prompt(
                row,
                "usar esta ciudad como benchmark activo y explicar como ayuda a desbloquear monetizacion del sistema",
            ),
        }
    if recommendation == "audit_trader_input":
        return {
            "gate_status": "audit_trader_input",
            "review_priority": "now",
            "codex_instruction": f"Auditar {row['city']} porque la inteligencia de traders se degrado y el ledger perdio fundamento.",
            "codex_prompt": build_codex_prompt(
                row,
                "auditar por que el input de traders se degrado, confirmar si la fuente externa sigue viva y decidir si esta ciudad debe seguir en review o pasar a pausa analitica",
            ),
        }
    if recommendation == "review_runtime_policy_gate" or bottleneck == "policy_execution_gate":
        useful_skips = row.get("recent_skip_evidence", {}).get("useful_reason_counts", {}) or {}
        return {
            "gate_status": "review_runtime_policy_gate",
            "review_priority": "now",
            "codex_instruction": (
                f"Revisar gate operativo en {row['city']}: runtime ya genero edge util reciente "
                f"pero la ejecucion quedo frenada por {useful_skips or 'policy gate'}."
            ),
            "codex_prompt": build_codex_prompt(
                row,
                "determinar si el cuello actual es policy shadow-only/allowlist, confirmar si eso explica la falta de throughput util y dejar la siguiente accion concreta sin tocar trading core",
            ),
        }
    if bottleneck == "shadow_validation":
        return {
            "gate_status": "needs_shadow_validation",
            "review_priority": "soon",
            "codex_instruction": f"{row['city']} tiene discovery suficiente para interesar, pero falta validacion shadow propia.",
            "codex_prompt": build_codex_prompt(
                row,
                "decidir como convertir discovery prometedor en validacion shadow medible y util para monetizar",
            ),
        }
    if bottleneck == "weak_city_hypothesis":
        return {
            "gate_status": "background_watch",
            "review_priority": "later",
            "codex_instruction": (
                f"{row['city']} ya tuvo visibilidad shadow repetida, pero sigue sin edge propio util; "
                "no priorizar monetizacion hasta que aparezca evidencia nueva."
            ),
            "codex_prompt": build_codex_prompt(
                row,
                "confirmar si la ciudad ya debe pasar a background watch por hipotesis debil en vez de seguir en review activa",
            ),
        }
    if bottleneck == "source_fidelity":
        return {
            "gate_status": "observe_with_source_caution",
            "review_priority": "watch" if visibility_score < 8 else "soon",
            "codex_instruction": f"{row['city']} tiene discovery prometedor, pero sigue frenada por source fidelity antes de pasar a shadow.",
            "codex_prompt": build_codex_prompt(
                row,
                "determinar que pieza concreta de source fidelity falta para convertir esta ciudad en candidata real de shadow validation",
            ),
        }
    if bottleneck == "market_visibility":
        return {
            "gate_status": "watch_closely",
            "review_priority": "watch",
            "codex_instruction": f"{row['city']} tiene discovery util, pero aun no aparece suficiente visibilidad de mercados para validacion shadow.",
            "codex_prompt": build_codex_prompt(
                row,
                "explicar que evidencia de visibilidad falta y como acercaria esta ciudad a una validacion shadow util",
            ),
        }
    if recommendation == "watch_closely":
        return {
            "gate_status": "watch_closely",
            "review_priority": "watch",
            "codex_instruction": f"Seguir acumulando evidencia en {row['city']}; cuello dominante: {bottleneck}.",
            "codex_prompt": build_codex_prompt(
                row,
                "explicar que evidencia falta para romper el cuello de botella actual y acercarnos a monetizacion",
            ),
        }
    if recommendation == "observe_with_source_caution":
        return {
            "gate_status": "observe_with_source_caution",
            "review_priority": "watch",
            "codex_instruction": f"Observar {row['city']} con cautela; la limitacion dominante actual es {bottleneck}.",
            "codex_prompt": build_codex_prompt(
                row,
                "diagnosticar si el problema real es source fidelity, visibilidad o una hipotesis debil de ciudad",
            ),
        }
    if policy_mode == "blocked" and visibility_score >= 8:
        return {
            "gate_status": "blocked_with_signal",
            "review_priority": "soon",
            "codex_instruction": f"Revisar si {row['city']} esta bloqueada por fuente rota o por policy desactualizada.",
            "codex_prompt": build_codex_prompt(
                row,
                "determinar si el bloqueo responde a una fuente rota real o a una policy que ya no refleja la evidencia",
            ),
        }
    return {
        "gate_status": "background_watch",
        "review_priority": "later",
        "codex_instruction": f"Sin accion inmediata en {row['city']}; seguir acumulando evidencia.",
        "codex_prompt": build_codex_prompt(
            row,
            "evaluar si esta linea de investigacion sigue teniendo valor o debe quedar en background watch",
        ),
    }


def compute_system_bottleneck(rows):
    policy_gate_hits = sum(
        int((row.get("recent_skip_evidence", {}).get("useful_policy_gate_count", 0) or 0))
        for row in rows
        if isinstance(row, dict)
    )
    if policy_gate_hits > 0:
        return "policy_execution_gate"
    counts = Counter(row.get("bottleneck") for row in rows)
    if not counts:
        return "unknown"
    return counts.most_common(1)[0][0]


def render_markdown(payload):
    lines = [
        "# City Promotion Gate",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Dominant bottleneck: `{payload['summary']['dominant_bottleneck']}`",
        f"- Runtime inputs status: `{payload['summary'].get('runtime_inputs_status', 'available')}`",
        f"- Gate counts: `{payload['summary']['gate_status_counts']}`",
        "",
        "## Review Queue",
        "",
        "| City | Gate | Priority | Runtime policy | Cross policy | Drift | Recommendation | Bottleneck |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["review_queue"]:
        lines.append(
            f"| {row['city']} | {row['gate_status']} | {row['review_priority']} | "
            f"{row.get('runtime_policy_mode', '-')} | {row.get('cross_policy_mode', '-')} | "
            f"{','.join(row.get('drift_flags', [])) or '-'} | {row['recommendation']} | {row['bottleneck']} |"
        )

    lines.extend([
        "",
        "## Codex Review",
        "",
    ])
    for row in payload["review_queue"][:10]:
        lines.append(f"- `{row['city']}`: {row['codex_instruction']}")
    lines.append("")
    return "\n".join(lines)


def build_runtime_unavailable_payload(ledger, args):
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    runtime_status = ledger.get("summary", {}).get("runtime_inputs_status", "missing")
    missing_inputs = ledger.get("summary", {}).get("missing_runtime_inputs", [])
    stale_inputs = ledger.get("summary", {}).get("stale_runtime_inputs", [])
    drift_inputs = ledger.get("summary", {}).get("manifest_drift_inputs", [])
    is_stale = runtime_status == "stale"
    is_drift = runtime_status == "manifest_drift"
    gate_status = (
        "runtime_manifest_drift"
        if is_drift
        else ("runtime_snapshot_stale" if is_stale else "runtime_inputs_missing")
    )
    bottleneck = (
        "runtime_inputs_manifest_drift"
        if is_drift
        else ("runtime_inputs_stale" if is_stale else "runtime_inputs_missing")
    )
    recommendation = (
        "audit_runtime_manifest"
        if is_drift
        else ("audit_runtime_snapshot" if is_stale else "audit_runtime_import")
    )
    instruction = (
        "city-intelligence tiene drift entre manifest runtime y archivos locales; no emitir gates por ciudad."
        if is_drift
        else "city-intelligence tiene artefactos runtime pero el snapshot esta obsoleto; no emitir gates por ciudad."
        if is_stale
        else "city-intelligence no tiene acceso a los artefactos runtime del bot; no interpretar ceros como ausencia de edge."
    )
    prompt = (
        "Revisa el manifest runtime de city-intelligence sin tocar bot.py. "
        "El ledger marco runtime_inputs_status=manifest_drift porque el directorio no es bijectivo con el manifest. "
        "Objetivo: limpiar el snapshot manifestado antes de emitir gates por ciudad."
        if is_drift
        else (
        "Revisa la frescura del snapshot runtime de city-intelligence sin tocar bot.py. "
        "El ledger marco runtime_inputs_status=stale porque el manifest falta, no parsea o supera el umbral de edad. "
        "Objetivo: refrescar transporte read-only antes de emitir gates por ciudad."
        if is_stale
        else (
            "Revisa la integracion runtime de city-intelligence sin tocar bot.py. "
            "El ledger marco runtime_inputs_status=missing porque faltan artefactos runtime "
            "como shadow_city_tracking.json, audit.json o city_policy_state.json. "
            "Objetivo: validar el fail-closed y decidir el transporte read-only correcto antes de emitir gates por ciudad."
        )
        )
    )
    row = {
        "city": "runtime",
        "gate_status": gate_status,
        "review_priority": "now",
        "recommendation": recommendation,
        "bottleneck": bottleneck,
        "codex_instruction": instruction,
        "codex_prompt": prompt,
        "missing_runtime_inputs": missing_inputs,
        "stale_runtime_inputs": stale_inputs,
        "manifest_drift_inputs": drift_inputs,
    }
    return {
        "generated_at": generated_at,
        "inputs": {
            "ledger": args.ledger,
        },
        "summary": {
            "n_cities": 0,
            "runtime_inputs_status": runtime_status,
            "missing_runtime_inputs": missing_inputs,
            "stale_runtime_inputs": stale_inputs,
            "manifest_drift_inputs": drift_inputs,
            "runtime_manifest": ledger.get("summary", {}).get("runtime_manifest", {}),
            "gate_status_counts": {gate_status: 1},
            "review_priority_counts": {"now": 1},
            "dominant_bottleneck": bottleneck,
        },
        "review_queue": [row],
        "cities": [],
    }


def main():
    args = parse_args()
    ledger = load_json(args.ledger)
    if ledger.get("summary", {}).get("runtime_inputs_status") in {"missing", "stale", "manifest_drift"}:
        payload = build_runtime_unavailable_payload(ledger, args)
        json_path = ensure_parent(args.json_output)
        md_path = ensure_parent(args.md_output)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(render_markdown(payload), encoding="utf-8")

        print(f"City promotion gate written to {json_path}")
        print(f"Markdown summary written to {md_path}")
        print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
        return

    rows = []
    for row in ledger.get("cities", []):
        gate = compute_gate(row)
        rows.append({**row, **gate})

    review_queue = [row for row in rows if row["review_priority"] in {"now", "soon", "watch"}]
    review_queue.sort(
        key=lambda row: (
            row["review_priority"] != "now",
            row["review_priority"] != "soon",
            row["gate_status"] == "background_watch",
            -row["visibility_evidence"]["score"],
            row["city"],
        )
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "ledger": args.ledger,
        },
        "summary": {
            "n_cities": len(rows),
            "runtime_inputs_status": ledger.get("summary", {}).get("runtime_inputs_status", "available"),
            "missing_runtime_inputs": ledger.get("summary", {}).get("missing_runtime_inputs", []),
            "stale_runtime_inputs": ledger.get("summary", {}).get("stale_runtime_inputs", []),
            "manifest_drift_inputs": ledger.get("summary", {}).get("manifest_drift_inputs", []),
            "runtime_manifest": ledger.get("summary", {}).get("runtime_manifest", {}),
            "gate_status_counts": dict(Counter(row["gate_status"] for row in rows)),
            "review_priority_counts": dict(Counter(row["review_priority"] for row in rows)),
            "dominant_bottleneck": compute_system_bottleneck(rows),
            "drift_flag_counts": dict(Counter(flag for row in rows for flag in row.get("drift_flags", []))),
        },
        "review_queue": review_queue,
        "cities": rows,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"City promotion gate written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
