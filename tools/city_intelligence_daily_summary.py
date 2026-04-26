#!/usr/bin/env python3
"""Daily Telegram summary for city intelligence progress and Codex follow-up."""

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from time import sleep


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIPELINE_PATH = REPO_ROOT / "data" / "city_intelligence_pipeline.json"
DEFAULT_LEDGER_PATH = REPO_ROOT / "data" / "city_validation_ledger.json"
DEFAULT_GATE_PATH = REPO_ROOT / "data" / "city_promotion_gate.json"
DEFAULT_EFFECTIVE_VIEW_PATH = REPO_ROOT / "data" / "runtime_policy_effective_view.json"
DEFAULT_ALIGNMENT_PATH = REPO_ROOT / "data" / "system_alignment_check_operational.json"
DEFAULT_SERVICE_TRANSITION_PLAN_PATH = REPO_ROOT / "data" / "service_transition_followup.json"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "city_intelligence_daily_summary_state.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_intelligence_daily_summary_latest.md"
LOCK_STALE_SECONDS = 15 * 60
ACTIONABLE_GATE_STATUSES = {
    "audit_runtime_drift",
    "review_for_canary",
    "review_block_reason",
    "promote_to_shadow_validation",
    "review_runtime_policy_gate",
    "needs_shadow_validation",
    "audit_trader_input",
    "blocked_with_signal",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera el resumen diario del city intelligence para enviar por Telegram a las 07:00 UTC."
    )
    parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE_PATH))
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH))
    parser.add_argument("--gate", default=str(DEFAULT_GATE_PATH))
    parser.add_argument("--effective-view", default=str(DEFAULT_EFFECTIVE_VIEW_PATH))
    parser.add_argument("--alignment-operational", default=str(DEFAULT_ALIGNMENT_PATH))
    parser.add_argument("--service-transition-plan", default=str(DEFAULT_SERVICE_TRANSITION_PLAN_PATH))
    parser.add_argument("--state-output", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--dry-run", action="store_true")
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


def lock_path_for(state_path_str):
    state_path = Path(state_path_str)
    return state_path.with_name(f"{state_path.name}.lock")


def acquire_lock(lock_path, stale_seconds=LOCK_STALE_SECONDS, wait_seconds=3):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(max(1, wait_seconds * 10)):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            payload = {
                "pid": os.getpid(),
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            }
            os.write(fd, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return fd
        except FileExistsError:
            try:
                mtime = lock_path.stat().st_mtime
            except FileNotFoundError:
                continue
            age = datetime.now(timezone.utc).timestamp() - mtime
            if age > stale_seconds:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            sleep(0.1)
    return None


def release_lock(lock_fd, lock_path):
    try:
        if lock_fd is not None:
            os.close(lock_fd)
    finally:
        for _ in range(5):
            try:
                lock_path.unlink()
                return
            except FileNotFoundError:
                return
            except PermissionError:
                sleep(0.1)


def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return {"sent": False, "reason": "missing_telegram_env"}
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)
    return {"sent": True, "reason": "sent"}


def is_actionable_review_row(row):
    if not isinstance(row, dict):
        return False
    if row.get("review_priority") not in {"now", "soon"}:
        return False
    return row.get("gate_status") in ACTIONABLE_GATE_STATUSES


def pick_summary_rows(gate, ledger, limit=3):
    review_queue = gate.get("review_queue", []) or []
    actionable_rows = [row for row in review_queue if is_actionable_review_row(row)]
    if actionable_rows:
        return actionable_rows[:limit]
    watch_rows = [row for row in review_queue if row.get("review_priority") == "watch"]
    if watch_rows:
        return watch_rows[:limit]
    return (ledger.get("cities", []) or [])[:limit]


def pick_instruction_row(gate):
    review_queue = gate.get("review_queue", []) or []
    actionable_rows = [row for row in review_queue if is_actionable_review_row(row)]
    if actionable_rows:
        return actionable_rows[0]
    return None


def runtime_inputs_status(pipeline_summary, ledger_summary, gate_summary):
    for candidate in (
        ledger_summary.get("runtime_inputs_status"),
        gate_summary.get("runtime_inputs_status"),
        pipeline_summary.get("runtime_inputs_status"),
    ):
        if candidate:
            return candidate
    return ""


def compute_progress_state(pipeline_summary, ledger_summary, gate_summary, prev_state):
    current_runtime_status = runtime_inputs_status(pipeline_summary, ledger_summary, gate_summary)
    if current_runtime_status == "missing":
        return "runtime_inputs_missing"
    if current_runtime_status == "stale":
        return "runtime_inputs_stale"
    signal_health = pipeline_summary.get("signal_health", "")
    if signal_health == "input_degraded":
        return "input_degradado"
    if signal_health == "low_signal":
        return "senal_debil"
    actionable = int(pipeline_summary.get("actionable_cities", 0) or 0)
    building = int(pipeline_summary.get("building_cities", 0) or 0)
    insufficient = int(pipeline_summary.get("insufficient_cities", 0) or 0)
    prev_actionable = int(prev_state.get("last_actionable_cities", 0) or 0)
    prev_building = int(prev_state.get("last_building_cities", 0) or 0)
    prev_bottleneck = prev_state.get("last_dominant_bottleneck", "")
    current_bottleneck = pipeline_summary.get("dominant_bottleneck", "")

    if actionable > prev_actionable:
        return "mas_cerca"
    if building > prev_building and insufficient <= int(prev_state.get("last_insufficient_cities", insufficient) or insufficient):
        return "mejorando"
    if current_bottleneck != prev_bottleneck and current_bottleneck:
        return "cuello_cambio"
    if actionable == 0 and building == 0:
        return "sin_senal_util"
    return "seguimos_trabajando"


def progress_sentence(progress_state):
    mapping = {
        "mas_cerca": "Estamos mas cerca de una lectura operativa util, aunque todavia no de cambios de policy.",
        "mejorando": "Estamos mejorando, aunque todavia falta evidencia fresca para subir el siguiente escalon.",
        "cuello_cambio": "El sistema ha cambiado de cuello de botella; eso puede ser una mejora si atacamos bien el siguiente bloqueo.",
        "sin_senal_util": "La informacion de ayer todavia no alcanza para una lectura operativa mas fuerte.",
        "seguimos_trabajando": "Seguimos avanzando, pero el bloqueo principal sigue siendo de evidencia y no de wiring.",
        "input_degradado": "La fuente principal de inteligencia de traders se degrado; hoy el sistema no puede sostener recomendaciones fiables.",
        "senal_debil": "El sistema sigue corriendo, pero la senal de traders es debil y no justifica conclusiones fuertes.",
        "runtime_inputs_missing": "city-intelligence no tiene acceso al runtime del bot; hoy no puede sostener conclusiones fiables por ciudad.",
        "runtime_inputs_stale": "city-intelligence tiene un snapshot runtime obsoleto; hoy no puede sostener conclusiones fiables por ciudad.",
    }
    return mapping.get(progress_state, mapping["seguimos_trabajando"])


def build_service_transition_block(plan, today_utc):
    if not isinstance(plan, dict) or not plan.get("enabled", False):
        return []
    checkpoints = plan.get("checkpoints", []) or []
    pending = [
        row
        for row in checkpoints
        if row.get("status", "pending") == "pending" and row.get("due_date", "") <= today_utc
    ]
    if not pending:
        future = [
            row
            for row in checkpoints
            if row.get("status", "pending") == "pending" and row.get("due_date", "") > today_utc
        ]
        future.sort(key=lambda row: row.get("due_date", "9999-99-99"))
        if not future:
            return []
        next_row = future[0]
        return [
            "",
            "<b>Seguimiento programado</b>",
            (
                f"Proximo checkpoint <code>{next_row.get('due_date')}</code>: "
                f"{next_row.get('label', 'revision pendiente')}."
            ),
        ]

    pending.sort(key=lambda row: row.get("due_date", "9999-99-99"))
    row = pending[0]
    lines = [
        "",
        "<b>Seguimiento programado</b>",
        f"Checkpoint pendiente <code>{row.get('due_date')}</code>: {row.get('label', 'revision pendiente')}.",
    ]
    reminder = row.get("reminder")
    decision = row.get("decision")
    runbook = row.get("runbook")
    if reminder:
        lines.append(f"- {reminder}")
    if decision:
        lines.append(f"- Decision esperada: {decision}")
    if isinstance(runbook, list) and runbook:
        lines.append("- Como hacerlo:")
        lines.extend(f"  {item}" for item in runbook[:6] if item)
    return lines


def build_canonical_story(pipeline, ledger, gate, effective_view, alignment, progress_state, service_transition_plan=None):
    pipeline_summary = pipeline.get("summary", {})
    ledger_summary = ledger.get("summary", {})
    gate_summary = gate.get("summary", {})
    effective_summary = effective_view.get("summary", {})
    alignment_summary = alignment.get("summary", {})

    mode_counts = effective_summary.get("effective_mode_counts", {})
    review_counts = gate_summary.get("review_priority_counts", {})
    runtime_targets = pipeline.get("target_contract", {}).get("runtime_derived_targets", [])
    dominant_bottleneck = gate_summary.get("dominant_bottleneck") or pipeline_summary.get("dominant_bottleneck") or "unknown"
    signal_health = pipeline_summary.get("signal_health") or "unknown"
    blocking_collisions = effective_summary.get("blocking_operational_collision_count", 0)
    active_effective_count = effective_summary.get("active_effective_count", 0)
    operational_errors = alignment_summary.get("error", 0)
    runtime_pulled_at = effective_summary.get("runtime_snapshot_pulled_at", "")[:16].replace("T", " ")
    preflight_text = (
        "preflight operacional sin errores"
        if int(operational_errors or 0) == 0
        else f"preflight operacional con <code>error={operational_errors}</code>"
    )

    runtime_target_text = ", ".join(runtime_targets[:6]) if runtime_targets else "sin canaries efectivas visibles"
    watch_count = review_counts.get("watch", 0)
    now_count = review_counts.get("now", 0)
    soon_count = review_counts.get("soon", 0)

    lines = [
        f"<b>City Intelligence - resumen diario ({pipeline.get('generated_at', '')[:10]} UTC)</b>",
        "",
        "<b>Estado</b>",
        (
            f"Runtime read-only manifestado; {preflight_text} "
            f"y topologia efectiva <code>blocked={mode_counts.get('blocked', 0)}</code> / "
            f"<code>canary={mode_counts.get('canary', 0)}</code> / "
            f"<code>shadow={mode_counts.get('shadow', 0)}</code> / "
            f"<code>active={active_effective_count}</code>."
        ),
        "",
        "<b>Lo importante de ayer</b>",
        f"- `runtime_inputs_missing` ya no es el cuello dominante; runtime snapshot disponible desde <code>{runtime_pulled_at} UTC</code>.",
        f"- `blocking_operational_collision_count={blocking_collisions}` y preflight operacional en <code>error={operational_errors}</code>.",
        f"- Canaries efectivas visibles: <code>{runtime_target_text}</code>.",
        "",
        "<b>Lectura del sistema</b>",
        f"- {progress_sentence(progress_state)}",
        f"- Seguimos en observacion operativa: el bloqueo principal ya no es el transporte runtime, sino convertir evidencia nueva en lectura mas fuerte. Hoy city-intelligence ve <code>{dominant_bottleneck}</code> como cuello dominante.",
        f"- No toca repetir trabajo cerrado ni abrir policy: hay <code>now={now_count}</code>, <code>soon={soon_count}</code> y <code>watch={watch_count}</code> en la review queue, con <code>{signal_health}</code> como estado de senal.",
        "",
        "<b>Instruccion para Codex</b>",
        "No revalidar el transporte read-only del runtime. Si abres una sesion nueva, parte de `runtime_policy_effective_view`, `system_alignment_check --decision-mode operational` y la evidencia runtime manifestada para decidir si solo toca observar o si aparecio un blocker real.",
    ]
    today_utc = datetime.now(timezone.utc).date().isoformat()
    lines.extend(build_service_transition_block(service_transition_plan, today_utc))
    return "\n".join(lines)


def build_message(pipeline, ledger, gate, effective_view, alignment, progress_state, service_transition_plan=None):
    pipeline_summary = pipeline.get("summary", {})
    gate_summary = gate.get("summary", {})
    ledger_summary = ledger.get("summary", {})
    if (
        runtime_inputs_status(pipeline_summary, ledger_summary, gate_summary) == "missing"
        or runtime_inputs_status(pipeline_summary, ledger_summary, gate_summary) == "stale"
    ):
        runtime_status = (
            runtime_inputs_status(pipeline_summary, ledger_summary, gate_summary)
        )
        missing = (
            gate_summary.get("missing_runtime_inputs")
            or ledger_summary.get("missing_runtime_inputs", [])
        )
        stale = (
            gate_summary.get("stale_runtime_inputs")
            or ledger_summary.get("stale_runtime_inputs", [])
        )
        missing_labels = ", ".join(row.get("name", "") for row in missing if row.get("name")) or "artefactos runtime"
        stale_labels = ", ".join(
            f"{row.get('name')}:{row.get('reason')}"
            for row in stale
            if row.get("name")
        ) or "runtime_manifest:snapshot_stale"
        generated_at = pipeline.get("generated_at", "")
        return "\n".join([
            f"<b>City Intelligence - resumen diario ({generated_at[:10]} UTC)</b>",
            "",
            "<b>Estado</b>",
            progress_sentence("runtime_inputs_stale" if runtime_status == "stale" else "runtime_inputs_missing"),
            "",
            "<b>Lo importante de ayer</b>",
            f"- Cuello dominante: <code>{'runtime_inputs_stale' if runtime_status == 'stale' else 'runtime_inputs_missing'}</code>",
            f"- Inputs faltantes: <code>{missing_labels}</code>" if runtime_status != "stale" else f"- Inputs stale: <code>{stale_labels}</code>",
            "",
            "<b>Lectura del sistema</b>",
            "- No se puede interpretar <code>edge_evidence=0</code> como ausencia real de edge.",
            "- No se deben emitir recomendaciones por ciudad hasta tener runtime fresco en modo read-only.",
            "",
            "<b>Instruccion para Codex</b>",
            "Validar el transporte read-only del runtime y su manifest. No tocar bot.py ni city_policy_state.json.",
        ])

    if effective_view and alignment:
        return build_canonical_story(
            pipeline,
            ledger,
            gate,
            effective_view,
            alignment,
            progress_state,
            service_transition_plan=service_transition_plan,
        )

    summary_rows = pick_summary_rows(gate, ledger, limit=3)
    instruction_row = pick_instruction_row(gate)
    generated_at = pipeline.get("generated_at", "")
    actionable = pipeline_summary.get("actionable_cities")
    building = pipeline_summary.get("building_cities")
    insufficient = pipeline_summary.get("insufficient_cities")
    if actionable is None or building is None or insufficient is None:
        counts = ledger.get("summary", {}).get("evidence_status_counts", {})
        actionable = counts.get("actionable", 0)
        building = counts.get("building", 0)
        insufficient = counts.get("insufficient", 0)
    dominant_bottleneck = pipeline_summary.get("dominant_bottleneck") or gate_summary.get("dominant_bottleneck") or "unknown"
    signal_health = pipeline_summary.get("signal_health") or "unknown"
    trader_input_warning = pipeline_summary.get("trader_input_warning") or ""
    quality_reference_traders = pipeline_summary.get("quality_reference_traders", 0)
    review_count = (
        gate_summary.get("review_priority_counts", {}).get("now", 0)
        + gate_summary.get("review_priority_counts", {}).get("soon", 0)
        + gate_summary.get("review_priority_counts", {}).get("watch", 0)
    )

    lines = [
        f"<b>City Intelligence - resumen diario ({generated_at[:10]} UTC)</b>",
        "",
        "<b>Estado</b>",
        progress_sentence(progress_state),
        "",
        "<b>Lo importante de ayer</b>",
        f"- Cuello dominante: <code>{dominant_bottleneck}</code>",
        f"- Signal health: <code>{signal_health}</code> | Quality references: <code>{quality_reference_traders}</code>",
        f"- Ciudades en review queue: <code>{review_count}</code>",
        f"- Actionable: <code>{actionable}</code> | Building: <code>{building}</code> | Insufficient: <code>{insufficient}</code>",
        "",
        "<b>Lectura del sistema</b>",
    ]
    if trader_input_warning:
        lines.append(f"- <b>Warning</b>: {trader_input_warning}")
    for row in summary_rows:
        lines.append(
            f"- <b>{row['city']}</b>: {row['recommendation']} | cuello <code>{row['bottleneck']}</code> | {row['rationale']}"
        )

    if instruction_row:
        lines.extend([
            "",
            "<b>Instruccion para Codex</b>",
            instruction_row.get("codex_prompt", ""),
        ])
    else:
        lines.extend([
            "",
            "<b>Instruccion para Codex</b>",
            "No hace falta abrir una revision nueva hoy salvo que quieras auditar si el sistema esta produciendo senal util o solo ruido. Si revisas algo, usa la review queue vigente y no reabras ciudades que ya cayeron a background watch. Lee AGENTS.md, el bloque reciente de CONTEXTO.md, data/city_validation_ledger.json, data/city_promotion_gate.json y docs/city_intelligence_pipeline_latest.md.",
        ])
    today_utc = datetime.now(timezone.utc).date().isoformat()
    lines.extend(build_service_transition_block(service_transition_plan, today_utc))
    return "\n".join(lines)


def render_markdown(payload):
    lines = [
        "# City Intelligence Daily Summary",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Progress state: `{payload['progress_state']}`",
        f"- Telegram result: `{payload['telegram_result']['reason']}`",
        "",
        "## Message",
        "",
        "```html",
        payload["message"],
        "```",
        "",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()
    pipeline = load_json(args.pipeline, required=True)
    ledger = load_json(args.ledger, required=True)
    gate = load_json(args.gate, required=True)
    effective_view = load_json(args.effective_view, required=False) or {}
    alignment = load_json(args.alignment_operational, required=False) or {}
    service_transition_plan = load_json(args.service_transition_plan, required=False) or {}
    state_path = ensure_parent(args.state_output)
    md_path = ensure_parent(args.md_output)
    lock_path = lock_path_for(args.state_output)
    lock_fd = acquire_lock(lock_path, wait_seconds=3)
    if lock_fd is None:
        payload = {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "progress_state": "skipped",
            "telegram_result": {"sent": False, "reason": "already_running"},
            "message": "",
        }
        md_path.write_text(render_markdown(payload), encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    try:
        state = load_json(args.state_output, required=False) or {}
        progress_state = compute_progress_state(
            pipeline.get("summary", {}),
            ledger.get("summary", {}),
            gate.get("summary", {}),
            state,
        )
        message = build_message(
            pipeline,
            ledger,
            gate,
            effective_view,
            alignment,
            progress_state,
            service_transition_plan=service_transition_plan,
        )
        today_utc = datetime.now(timezone.utc).date().isoformat()

        if not args.dry_run and state.get("last_sent_date") == today_utc:
            telegram_result = {"sent": False, "reason": "already_sent_today"}
        elif args.dry_run:
            telegram_result = {"sent": False, "reason": "dry_run"}
        else:
            telegram_result = send_telegram(message)

        pipeline_summary = pipeline.get("summary", {})
        state.update({
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "last_progress_state": progress_state,
            "last_dominant_bottleneck": pipeline_summary.get("dominant_bottleneck"),
            "last_actionable_cities": pipeline_summary.get("actionable_cities", 0),
            "last_building_cities": pipeline_summary.get("building_cities", 0),
            "last_insufficient_cities": pipeline_summary.get("insufficient_cities", 0),
        })
        if telegram_result.get("reason") in {"sent", "missing_telegram_env"}:
            state["last_sent_date"] = today_utc

        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

        payload = {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "progress_state": progress_state,
            "telegram_result": telegram_result,
            "message": message,
        }
        md_path.write_text(render_markdown(payload), encoding="utf-8")
    finally:
        release_lock(lock_fd, lock_path)

    print(f"Daily summary state written to {state_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
