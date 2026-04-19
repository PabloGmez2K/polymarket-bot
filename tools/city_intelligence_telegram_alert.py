#!/usr/bin/env python3
"""Send one-shot Telegram alerts when the city promotion gate needs review."""

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE_PATH = REPO_ROOT / "data" / "city_promotion_gate.json"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "city_intelligence_alert_state.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_intelligence_alert_latest.md"
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
        description="Envia alerta Telegram cuando una ciudad entra en review_queue."
    )
    parser.add_argument("--gate", default=str(DEFAULT_GATE_PATH))
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


def build_signature(row):
    runtime_names = ",".join(
        sorted(
            item.get("name", "")
            for item in (
                row.get("missing_runtime_inputs", [])
                + row.get("stale_runtime_inputs", [])
            )
            if item.get("name")
        )
    )
    return f"{row.get('city')}|{row.get('gate_status')}|{row.get('review_priority')}|{runtime_names}"


def is_actionable_alert_row(row):
    if not isinstance(row, dict):
        return False
    if row.get("review_priority") not in {"now", "soon"}:
        return False
    return row.get("gate_status") in ACTIONABLE_GATE_STATUSES


def select_new_alert_rows(gate, state):
    seen = set(state.get("seen_review_signatures", []))
    rows = []
    for row in gate.get("review_queue", []):
        if not is_actionable_alert_row(row):
            continue
        signature = build_signature(row)
        if signature in seen:
            continue
        rows.append(row)
    return rows


def build_message(gate, rows):
    dominant_bottleneck = gate.get("summary", {}).get("dominant_bottleneck")
    if dominant_bottleneck == "runtime_inputs_missing":
        missing = gate.get("summary", {}).get("missing_runtime_inputs", [])
        missing_labels = ", ".join(row.get("name", "") for row in missing if row.get("name")) or "artefactos runtime"
        return "\n".join([
            "<b>City Intelligence Review</b>",
            "",
            "<b>Estado</b>",
            "No puedo concluir nada fiable sobre ciudades porque falta acceso al runtime de <code>polymarket-bot</code>.",
            "",
            "<b>Que paso</b>",
            f"Faltan inputs runtime: <code>{missing_labels}</code>.",
            "",
            "<b>Por que importa</b>",
            "Sin esos archivos, <code>edge_evidence=0</code> seria un cero mudo, no evidencia real de ausencia de edge.",
            "",
            "<b>Instruccion para Codex</b>",
            "Validar el fail-closed de city-intelligence y decidir el transporte read-only del runtime antes de emitir gates por ciudad. No tocar bot.py ni policy runtime.",
        ])
    if dominant_bottleneck == "runtime_inputs_stale":
        stale = gate.get("summary", {}).get("stale_runtime_inputs", [])
        stale_labels = ", ".join(
            f"{row.get('name')}:{row.get('reason')}"
            for row in stale
            if row.get("name")
        ) or "runtime_manifest:snapshot_stale"
        return "\n".join([
            "<b>City Intelligence Review</b>",
            "",
            "<b>Estado</b>",
            "Tengo artefactos runtime, pero el snapshot no es fresco.",
            "",
            "<b>Que paso</b>",
            f"Inputs stale: <code>{stale_labels}</code>.",
            "",
            "<b>Por que importa</b>",
            "Un snapshot viejo puede parecer evidencia actual y crear gates falsos.",
            "",
            "<b>Instruccion para Codex</b>",
            "Refrescar el transporte read-only o revisar el manifest antes de emitir gates por ciudad. No tocar bot.py ni policy runtime.",
        ])

    top = rows[0]
    lines = [
        "<b>City Intelligence Review</b>",
        "",
        "<b>Estado</b>",
        "Base operativa disponible; la novedad es de seguimiento y lectura operativa, no de wiring ni de policy.",
        "",
        "<b>Que paso</b>",
        f"Hay {len(rows)} ciudad(es) con revision accionable nueva en el gate vigente.",
        f"La principal ahora es <b>{top['city']}</b> con gate <code>{top['gate_status']}</code>.",
        "",
        "<b>Por que importa</b>",
        f"El cuello dominante del sistema es <code>{dominant_bottleneck}</code>.",
        "Eso significa que el siguiente paso util debe atacar ese bloqueo y no reabrir lineas que el gate ya bajo a background watch.",
        "",
    ]
    for row in rows[:4]:
        lines.append(
            f"- <b>{row['city']}</b>: {row['codex_instruction']}"
        )
    lines.extend([
        "",
        "<b>Instruccion para Codex</b>",
        top.get("codex_prompt", ""),
    ])
    return "\n".join(lines)


def render_markdown(payload):
    lines = [
        "# City Intelligence Alert",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Should alert: `{payload['should_alert']}`",
        f"- New rows: `{payload['new_rows_count']}`",
        f"- Telegram result: `{payload['telegram_result']['reason']}`",
        "",
    ]
    if payload.get("message"):
        lines.extend([
            "## Message",
            "",
            "```html",
            payload["message"],
            "```",
            "",
        ])
    return "\n".join(lines)


def main():
    args = parse_args()
    gate = load_json(args.gate, required=True)
    state = load_json(args.state_output, required=False) or {}
    new_rows = select_new_alert_rows(gate, state)

    message = ""
    telegram_result = {"sent": False, "reason": "not_attempted"}
    should_alert = bool(new_rows)
    if should_alert:
        message = build_message(gate, new_rows)
        if args.dry_run:
            telegram_result = {"sent": False, "reason": "dry_run"}
        else:
            telegram_result = send_telegram(message)
        if telegram_result["reason"] in {"sent", "dry_run", "missing_telegram_env"}:
            seen = set(state.get("seen_review_signatures", []))
            seen.update(build_signature(row) for row in new_rows)
            state["seen_review_signatures"] = sorted(seen)

    state["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    state_path = ensure_parent(args.state_output)
    md_path = ensure_parent(args.md_output)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "should_alert": should_alert,
        "new_rows_count": len(new_rows),
        "telegram_result": telegram_result,
        "message": message,
    }
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"City intelligence alert state written to {state_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
