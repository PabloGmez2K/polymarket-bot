#!/usr/bin/env python3
"""One-shot Telegram alerts for phase-5 visibility milestones."""

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKER_PATH = REPO_ROOT / "data" / "city_probe_visibility_tracker.json"
DEFAULT_COMPARATOR_PATH = REPO_ROOT / "data" / "shanghai_vs_chicago_comparator.json"
DEFAULT_OPERATIONAL_ACTION_PATH = REPO_ROOT / "data" / "phase5_operational_action.json"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "phase5_visibility_alert_state.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "phase5_visibility_alert_latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Envia alerta Telegram one-shot cuando aparece una coincidencia nueva Shanghai + Chicago."
    )
    parser.add_argument("--tracker", default=str(DEFAULT_TRACKER_PATH))
    parser.add_argument("--comparator", default=str(DEFAULT_COMPARATOR_PATH))
    parser.add_argument("--operational-action", default=str(DEFAULT_OPERATIONAL_ACTION_PATH))
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
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)
    return {"sent": True, "reason": "sent"}


def get_latest_snapshot(tracker):
    history = tracker.get("history", [])
    return history[-1] if history else {}


def should_alert(latest_snapshot, state):
    if not latest_snapshot:
        return False, "no_snapshot"
    if not latest_snapshot.get("simultaneous_visibility"):
        return False, "no_simultaneous_visibility"
    probe_generated_at = latest_snapshot.get("probe_generated_at")
    already_sent_for = state.get("last_simultaneous_alert_probe_generated_at")
    if probe_generated_at and probe_generated_at == already_sent_for:
        return False, "already_alerted_for_probe"
    return True, "new_simultaneous_visibility"


def build_message(latest_snapshot, tracker, comparator, operational_action):
    cities = latest_snapshot.get("cities", {})
    shanghai = cities.get("Shanghai", {})
    chicago = cities.get("Chicago", {})
    gap = comparator.get("gap", {}).get("dominant_gap")
    next_step = comparator.get("recommendation", {}).get("next_step")
    action = operational_action.get("action", {})
    lines = [
        "🔔 <b>Phase 5 Visibility</b>",
        "",
        "Nueva coincidencia <b>Shanghai + Chicago</b> detectada en el settlement probe.",
        f"Probe: <code>{latest_snapshot.get('probe_generated_at')}</code>",
        "",
        f"Shanghai: {shanghai.get('market_count', 0)} mercados",
        f"Chicago: {chicago.get('market_count', 0)} mercados",
        f"Coincidencias acumuladas: {tracker.get('summary', {}).get('simultaneous_visibility_count', 0)}",
        "",
        f"Gap dominante actual: <code>{gap}</code>",
        f"Siguiente paso comparador: <code>{next_step}</code>",
        f"Severidad operativa: <code>{action.get('severity')}</code>",
        f"Estado operativo: <code>{action.get('action_state')}</code>",
        f"Accion siguiente: <code>{action.get('next_operational_step')}</code>",
    ]
    if action.get("decision_note"):
        lines.extend([
            "",
            f"Lectura operativa: {action.get('decision_note')}",
        ])
    return "\n".join(lines)


def render_markdown(payload):
    lines = [
        "# Phase 5 Visibility Alert",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Should alert: `{payload['should_alert']}`",
        f"- Decision reason: `{payload['decision_reason']}`",
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
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    tracker = load_json(args.tracker, required=True)
    comparator = load_json(args.comparator, required=True)
    operational_action = load_json(args.operational_action, required=True)
    state = load_json(args.state_output, required=False) or {}
    latest_snapshot = get_latest_snapshot(tracker)
    should, reason = should_alert(latest_snapshot, state)

    message = ""
    telegram_result = {"sent": False, "reason": "not_attempted"}
    if should:
        message = build_message(latest_snapshot, tracker, comparator, operational_action)
        if args.dry_run:
            telegram_result = {"sent": False, "reason": "dry_run"}
        else:
            telegram_result = send_telegram(message)
        if telegram_result["reason"] in {"sent", "dry_run", "missing_telegram_env"}:
            state["last_simultaneous_alert_probe_generated_at"] = latest_snapshot.get("probe_generated_at")

    state["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    state_path = ensure_parent(args.state_output)
    md_path = ensure_parent(args.md_output)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "should_alert": should,
        "decision_reason": reason,
        "telegram_result": telegram_result,
        "message": message,
    }
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Alert state written to {state_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
