"""
truth_pipeline_alarms.py — Generador de alarmas Telegram para Truth Pipeline (Fase 1A.4).

Default OFF: TRUTH_PIPELINE_TELEGRAM_ENABLED=0
No envía Telegram real salvo habilitación explícita.
No usa canal operativo del bot. TRUTH_PIPELINE_TG_CHAT_ID es separado.
No importa bot.py. Solo stdlib.

Estado anti-spam: data/truth_pipeline_alerts_state.json (configurable).
En tests se pasa ruta tmp_path para no escribir en producción.

Niveles de alarma (taxonomía canónica Fase 1):
    NO_ACTION     — datos sanos o muestra insuficiente (sin alerta)
    WATCH         — calibración <50% con n_resolved≥10 (Sonnet triage)
    WATCH_TECH    — schema_missing o DB inaccesible (Sonnet diagnóstico)
    ACTION_DESIGN — drift ≥3 en 1 ciudad → revisión humana (Opus diseño)
    ACTION_SAFETY — drift ≥3 en 2+ ciudades → inconsistencia grave (Opus seguridad)

Prohibiciones absolutas en mensajes generados:
    - Sin instrucciones de compra, venta o skip operativos
    - Sin escalado de bankroll ni activación de Fase C
    - Sin recomendación de acción de trading
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TRUTH_PIPELINE_TELEGRAM_ENABLED_ENV = "TRUTH_PIPELINE_TELEGRAM_ENABLED"
TRUTH_PIPELINE_TG_CHAT_ID_ENV = "TRUTH_PIPELINE_TG_CHAT_ID"
_TG_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"

DEFAULT_STATE_FILE = "data/truth_pipeline_alerts_state.json"


def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─── Estado anti-spam ─────────────────────────────────────────────────────────

def _load_state(state_file: str) -> dict:
    p = Path(state_file)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state_file: str, state: dict) -> None:
    p = Path(state_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def already_sent_today(state_file: str) -> bool:
    """True si ya se envió una alerta hoy (UTC)."""
    return _load_state(state_file).get("last_sent_date") == _today_utc()


def record_sent(state_file: str, level: str) -> None:
    """Registra el envío en el state file."""
    state = _load_state(state_file)
    state["last_sent_date"] = _today_utc()
    state["last_sent_ts"] = _now_utc_str()
    state["last_level"] = level
    _save_state(state_file, state)


# ─── Clasificación de nivel ───────────────────────────────────────────────────

def classify_alarm_level(report: dict) -> str:
    """
    Clasifica el nivel de alarma a partir del output de generate_report().

    Taxonomía canónica Fase 1 (mapeada desde report status):
    - action_safety  → ACTION_SAFETY  (drift 2+ ciudades)
    - action_design  → ACTION_DESIGN  (drift 1 ciudad)
    - watch          → WATCH          (calibración baja + n≥10)
    - watch_tech / schema_missing → WATCH_TECH
    - no_action / empty / otro → NO_ACTION (sin alerta)
    """
    status = report.get("status")
    if status == "action_safety":
        return "ACTION_SAFETY"
    if status == "action_design":
        return "ACTION_DESIGN"
    if status in ("schema_missing", "watch_tech"):
        return "WATCH_TECH"
    if status == "watch":
        return "WATCH"
    return "NO_ACTION"


# ─── Formato del mensaje ──────────────────────────────────────────────────────

def format_alarm_message(report: dict, level: str) -> str:
    """
    Genera el texto del mensaje de Telegram.

    Garantías:
    - No contiene instrucciones de compra, venta ni acción operativa de trading.
    - Indica explícitamente que no autoriza cambios de trading.
    - Recomienda agente según nivel (Sonnet/Opus/Codex según corresponda).
    """
    ts = report.get("report_ts_utc", _now_utc_str())
    date_str = ts[:10] if ts else _today_utc()

    n_records = report.get("truth_records", 0)
    n_resolved = report.get("n_resolved", 0)
    cal = report.get("calibration_global")
    cal_pct = f"{cal * 100:.0f}%" if cal is not None else "N/A"

    lines: list[str] = [
        f"[Truth Pipeline — {level}]",
        f"Componente: Truth Pipeline Fase 1",
        f"Fecha: {date_str} UTC",
        "",
        f"Registros total:      {n_records}",
        f"Resueltos (YES/NO):   {n_resolved}",
    ]

    if cal is not None:
        lines.append(f"Calibración global:   {cal_pct} (forecast_ok / resueltos con forecast)")

    cal_cities = report.get("calibration_by_city", [])
    if cal_cities:
        lines.append("")
        lines.append("Por ciudad:")
        for c in cal_cities:
            pct = f"{c['calibration'] * 100:.0f}%" if c.get("calibration") is not None else "N/A"
            lines.append(f"  {c['city']:<16} n={c['n']}  calibración={pct}")

    drift_cities = report.get("drift_alert_cities", [])
    if drift_cities:
        lines.append("")
        lines.append("Drift sistemático detectado:")
        for d in drift_cities:
            lines.append(
                f"  {d['city']} ({d['condition']}): {d['n_wrong']} pronósticos incorrectos consecutivos"
            )

    lines += [
        "",
        f"Estado: {level}",
        "",
        "IMPORTANTE: Esta alerta no autoriza cambios de trading.",
        "Es observabilidad pura — solo para auditoría y seguimiento.",
        "",
    ]

    if level == "ACTION_SAFETY":
        lines += [
            "Agente recomendado: Opus (revisión de seguridad y diseño — no operativa).",
            "Codex solo si hay un patch concreto aprobado explícitamente por Pablo.",
        ]
    elif level == "ACTION_DESIGN":
        lines += [
            "Agente recomendado: Opus (revisión de diseño — no operativa).",
            "Codex solo si hay un patch concreto aprobado explícitamente.",
        ]
    elif level == "WATCH":
        lines += [
            "Agente recomendado: Sonnet (triage y documentación de hallazgos).",
        ]
    elif level == "WATCH_TECH":
        lines += [
            "Agente recomendado: Sonnet (diagnóstico técnico, sin acción operativa).",
        ]
    else:
        lines += ["Sin acción requerida."]

    return "\n".join(lines)


# ─── Envío Telegram ───────────────────────────────────────────────────────────

def _send_telegram(message: str, chat_id: str, bot_token: str) -> dict:
    """Envía mensaje a Telegram. Solo llamar si enabled=True."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"status": "sent", "http_code": resp.status}
    except urllib.error.HTTPError as exc:
        return {"status": "error", "http_code": exc.code, "error": str(exc)}
    except urllib.error.URLError as exc:
        return {"status": "error", "error": str(exc.reason)}


# ─── Función pública ──────────────────────────────────────────────────────────

def run_alarm(
    report: dict,
    *,
    state_file: str = DEFAULT_STATE_FILE,
    enabled: bool | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """
    Evalúa el reporte y, si corresponde, genera/envía alarma Telegram.

    enabled:    si None, lee TRUTH_PIPELINE_TELEGRAM_ENABLED del entorno.
    dry_run:    genera el mensaje pero no envía ni escribe estado.
    force:      ignora anti-spam (para testing/preview manual).
    state_file: ruta al JSON de estado anti-spam (usar tmp_path en tests).

    Retorna dict con: action, level, y message (si aplica).
    action ∈ {disabled, dry_run, suppressed, no_change, sent, error}
    """
    if enabled is None:
        enabled = os.environ.get(TRUTH_PIPELINE_TELEGRAM_ENABLED_ENV, "0") == "1"

    level = classify_alarm_level(report)
    message = format_alarm_message(report, level)

    if not enabled and not dry_run:
        return {
            "action": "disabled",
            "level": level,
            "message": message,
            "reason": f"{TRUTH_PIPELINE_TELEGRAM_ENABLED_ENV} != 1",
        }

    if dry_run:
        return {
            "action": "dry_run",
            "level": level,
            "message": message,
            "would_send": enabled and (force or not already_sent_today(state_file)),
        }

    # Anti-spam: máximo 1 alerta por día (salvo force)
    if not force and already_sent_today(state_file):
        return {
            "action": "suppressed",
            "level": level,
            "reason": "already_sent_today",
            "last_sent_date": _load_state(state_file).get("last_sent_date"),
        }

    # Nivel NO_ACTION → no enviar alerta
    if level == "NO_ACTION":
        return {
            "action": "no_change",
            "level": level,
            "reason": "level_no_action_no_alert_needed",
        }

    chat_id = os.environ.get(TRUTH_PIPELINE_TG_CHAT_ID_ENV, "")
    bot_token = os.environ.get(_TG_TOKEN_ENV, "")

    if not chat_id or not bot_token:
        return {
            "action": "error",
            "level": level,
            "error": (
                f"{TRUTH_PIPELINE_TG_CHAT_ID_ENV} o {_TG_TOKEN_ENV} "
                "no configurados — no se puede enviar Telegram."
            ),
        }

    result = _send_telegram(message, chat_id, bot_token)
    if result.get("status") == "sent":
        record_sent(state_file, level)
        return {
            "action": "sent",
            "level": level,
            "message": message,
        }
    return {
        "action": "error",
        "level": level,
        "error": result.get("error"),
    }
