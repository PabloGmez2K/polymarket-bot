#!/usr/bin/env python3
"""Daily summary and V1 readiness monitor for traders_intelligence."""

from __future__ import annotations

import argparse
import html
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTELLIGENCE_PATH = REPO_ROOT / "data" / "traders_intelligence.json"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "traders_intelligence_daily_summary_state.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "traders_intelligence_daily_summary_latest.md"
V1_SNAPSHOT_TOOL_PATH = REPO_ROOT / "tools" / "traders_intelligence_snapshot.py"
V1_SNAPSHOT_DOC_PATH = REPO_ROOT / "docs" / "traders-intelligence-v1-snapshots.md"
TELEGRAM_SAFE_CHUNK_CHARS = 3800
TELEGRAM_SEND_RETRIES = 1
TELEGRAM_TIMEOUT_SECONDS = 10


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resume traders_intelligence y avisa cuando se cumplan los checks para pasar a v1."
    )
    parser.add_argument("--intelligence", default=str(DEFAULT_INTELLIGENCE_PATH))
    parser.add_argument("--state-output", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument(
        "--max-census-stale-days",
        type=int,
        default=int(os.getenv("TRADERS_INTELLIGENCE_V1_MAX_CENSUS_STALE_DAYS", "14")),
    )
    parser.add_argument(
        "--min-crosscheck-runs",
        type=int,
        default=int(os.getenv("TRADERS_INTELLIGENCE_V1_MIN_CROSSCHECK_RUNS", "5")),
    )
    parser.add_argument(
        "--min-strong-traders",
        type=int,
        default=int(os.getenv("TRADERS_INTELLIGENCE_V1_MIN_STRONG_TRADERS", "2")),
    )
    parser.add_argument(
        "--min-candidate-cities",
        type=int,
        default=int(os.getenv("TRADERS_INTELLIGENCE_V1_MIN_CANDIDATE_CITIES", "3")),
    )
    parser.add_argument(
        "--lead-active-now",
        type=int,
        default=int(os.getenv("TRADERS_INTELLIGENCE_V1_LEAD_ACTIVE_NOW", "15")),
    )
    parser.add_argument(
        "--lead-blocked-n",
        type=int,
        default=int(os.getenv("TRADERS_INTELLIGENCE_V1_LEAD_BLOCKED_N", "20")),
    )
    parser.add_argument(
        "--lead-blocked-wr",
        type=float,
        default=float(os.getenv("TRADERS_INTELLIGENCE_V1_LEAD_BLOCKED_WR", "75.0")),
    )
    parser.add_argument(
        "--strong-active-now",
        type=int,
        default=int(os.getenv("TRADERS_INTELLIGENCE_V1_STRONG_ACTIVE_NOW", "5")),
    )
    parser.add_argument(
        "--strong-blocked-n",
        type=int,
        default=int(os.getenv("TRADERS_INTELLIGENCE_V1_STRONG_BLOCKED_N", "5")),
    )
    parser.add_argument(
        "--strong-blocked-wr",
        type=float,
        default=float(os.getenv("TRADERS_INTELLIGENCE_V1_STRONG_BLOCKED_WR", "70.0")),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_json(path_str, required=True):
    path = Path(path_str)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required input: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def chunk_message(message: str, limit: int = TELEGRAM_SAFE_CHUNK_CHARS):
    text = str(message or "")
    if len(text) <= limit:
        return [text]

    chunks = []
    current = []
    current_len = 0
    for line in text.splitlines(keepends=True):
        if len(line) > limit:
            if current:
                chunks.append("".join(current).rstrip())
                current = []
                current_len = 0
            for idx in range(0, len(line), limit):
                chunks.append(line[idx:idx + limit].rstrip())
            continue
        if current and current_len + len(line) > limit:
            chunks.append("".join(current).rstrip())
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)
    if current:
        chunks.append("".join(current).rstrip())
    return [chunk for chunk in chunks if chunk]


def telegram_failure(reason: str, exc=None, sent_chunks: int = 0):
    result = {
        "sent": False,
        "reason": reason,
        "sent_chunks": sent_chunks,
    }
    if exc is not None:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def html_text(value) -> str:
    return html.escape(str(value), quote=False)


def plain_text_message(message: str) -> str:
    replacements = (
        ("<b>", ""),
        ("</b>", ""),
        ("<code>", ""),
        ("</code>", ""),
    )
    text = message
    for old, new in replacements:
        text = text.replace(old, new)
    return html.unescape(text)


def post_telegram_chunk(token: str, chat_id: str, chunk: str, parse_mode: str | None = None):
    payload = {"chat_id": chat_id, "text": chunk}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=TELEGRAM_TIMEOUT_SECONDS)


def send_telegram(message: str):
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return {"sent": False, "reason": "missing_telegram_env"}

    chunks = chunk_message(message)
    sent_chunks = 0
    for chunk in chunks:
        for attempt in range(TELEGRAM_SEND_RETRIES + 1):
            try:
                post_telegram_chunk(token, chat_id, chunk, parse_mode="HTML")
                sent_chunks += 1
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 400:
                    try:
                        post_telegram_chunk(token, chat_id, plain_text_message(chunk))
                        sent_chunks += 1
                        break
                    except Exception as fallback_exc:
                        if attempt >= TELEGRAM_SEND_RETRIES:
                            return telegram_failure("telegram_plain_text_fallback_error", fallback_exc, sent_chunks)
                if attempt >= TELEGRAM_SEND_RETRIES:
                    return telegram_failure("telegram_http_error", exc, sent_chunks)
            except urllib.error.URLError as exc:
                if attempt >= TELEGRAM_SEND_RETRIES:
                    return telegram_failure("telegram_url_error", exc, sent_chunks)
            except TimeoutError as exc:
                if attempt >= TELEGRAM_SEND_RETRIES:
                    return telegram_failure("telegram_timeout", exc, sent_chunks)
            except Exception as exc:
                if attempt >= TELEGRAM_SEND_RETRIES:
                    return telegram_failure("telegram_exception", exc, sent_chunks)
            time.sleep(1)

    return {"sent": True, "reason": "sent", "sent_chunks": sent_chunks}


def get_active_now(trader):
    return int(trader.get("activity", {}).get("n_active_signals_now", 0) or 0)


def get_blocked_n(trader):
    return int(trader.get("blocked_signal_performance", {}).get("n_resolved", 0) or 0)


def get_blocked_wr(trader):
    value = trader.get("blocked_signal_performance", {}).get("wr_pct")
    return float(value) if value is not None else None


def get_trader_only_cities(trader):
    return list(trader.get("vs_bot", {}).get("trader_only_cities_now", []) or [])


def v1_minimal_available():
    return V1_SNAPSHOT_TOOL_PATH.exists() and V1_SNAPSHOT_DOC_PATH.exists()


def classify_strong_traders(traders, args):
    lead_traders = []
    strong_traders = []

    for trader in traders:
        active_now = get_active_now(trader)
        blocked_n = get_blocked_n(trader)
        blocked_wr = get_blocked_wr(trader)

        is_lead = (
            active_now >= args.lead_active_now
            and blocked_n >= args.lead_blocked_n
            and blocked_wr is not None
            and blocked_wr >= args.lead_blocked_wr
        )
        if is_lead:
            lead_traders.append(trader)

        is_strong = (
            active_now >= args.strong_active_now
            and (
                trader.get("reference_quality") == "high_priority_reference"
                or (
                    blocked_n >= args.strong_blocked_n
                    and blocked_wr is not None
                    and blocked_wr >= args.strong_blocked_wr
                )
            )
        )
        if is_strong:
            strong_traders.append(trader)

    lead_traders.sort(key=lambda trader: (-get_active_now(trader), -(get_blocked_n(trader)), trader.get("pseudonym", "")))
    strong_traders.sort(key=lambda trader: (-get_active_now(trader), -(get_blocked_n(trader)), trader.get("pseudonym", "")))
    return lead_traders, strong_traders


def build_readiness_checks(payload, args):
    integrity = payload.get("integrity", {})
    aggregate = payload.get("aggregate", {})
    traders = payload.get("traders", [])

    lead_traders, strong_traders = classify_strong_traders(traders, args)
    candidate_cities = sorted({
        city
        for trader in strong_traders
        for city in get_trader_only_cities(trader)
    })

    checks = [
        {
            "id": "health_usable_signal",
            "label": "health_status usable_signal",
            "passed": payload.get("health_status") == "usable_signal",
            "detail": f"health_status={payload.get('health_status', 'unknown')}",
        },
        {
            "id": "census_fresh_enough",
            "label": f"census_stale_days <= {args.max_census_stale_days}",
            "passed": integrity.get("census_stale_days") is not None and integrity.get("census_stale_days") <= args.max_census_stale_days,
            "detail": f"census_stale_days={integrity.get('census_stale_days')}",
        },
        {
            "id": "crosscheck_series_deep_enough",
            "label": f"recent_crosscheck_runs >= {args.min_crosscheck_runs}",
            "passed": int(aggregate.get("recent_crosscheck", {}).get("recent_runs", 0) or 0) >= args.min_crosscheck_runs,
            "detail": f"recent_runs={aggregate.get('recent_crosscheck', {}).get('recent_runs', 0)}",
        },
        {
            "id": "lead_trader_present",
            "label": ">=1 lead trader fuerte y muy activo",
            "passed": len(lead_traders) >= 1,
            "detail": ", ".join(trader.get("pseudonym", "?") for trader in lead_traders) or "none",
        },
        {
            "id": "strong_trader_depth",
            "label": f">={args.min_strong_traders} traders fuertes",
            "passed": len(strong_traders) >= args.min_strong_traders,
            "detail": ", ".join(trader.get("pseudonym", "?") for trader in strong_traders) or "none",
        },
        {
            "id": "candidate_city_gap_exists",
            "label": f">={args.min_candidate_cities} cities trader_only en traders fuertes",
            "passed": len(candidate_cities) >= args.min_candidate_cities,
            "detail": ", ".join(candidate_cities[:8]) or "none",
        },
    ]

    ready = all(check["passed"] for check in checks)
    blockers = [check for check in checks if not check["passed"]]
    focus_traders = [trader.get("pseudonym") for trader in (lead_traders[:2] or strong_traders[:2])]
    focus_cities = candidate_cities[:4]
    if ready and v1_minimal_available():
        question = (
            "V1 minima implementada. Siguiente paso: ejecutar "
            "`python tools/traders_intelligence_snapshot.py` con signals.json fresco "
            "para acumular snapshots."
        )
    elif ready:
        question = (
            "Seguir snapshots de señales para inferir salidas aparentes de "
            f"{', '.join(focus_traders)} en {', '.join(focus_cities)}."
        )
    else:
        question = None

    return {
        "ready": ready,
        "checks": checks,
        "blockers": blockers,
        "lead_traders": [trader.get("pseudonym") for trader in lead_traders],
        "strong_traders": [trader.get("pseudonym") for trader in strong_traders],
        "candidate_cities": candidate_cities,
        "question_for_v1": question,
    }


def build_daily_summary(payload):
    traders = payload.get("traders", [])
    active = [trader for trader in traders if get_active_now(trader) > 0]
    active.sort(key=lambda trader: (-get_active_now(trader), trader.get("pseudonym", "")))
    return active[:5]


def progress_sentence(readiness):
    if readiness["ready"]:
        if v1_minimal_available():
            return "Los checks minimos estan completos y la v1 minima ya existe; ahora toca acumular snapshots frescos con la CLI manual."
        return "Los checks minimos ya estan completos; ya merece pasar a v1 para seguir lifecycle externo."
    blockers = [check["id"] for check in readiness["blockers"]]
    if "crosscheck_series_deep_enough" in blockers:
        return "Todavia falta serie temporal suficiente para justificar v1 sin riesgo de sobrerreaccion."
    if "census_fresh_enough" in blockers:
        return "La foto base de traders sigue stale; antes de v1 conviene refrescar la base para no archivar sobre una shortlist vieja."
    return "La capa v0 ya es util, pero aun no cumple los checks minimos para abrir v1 con una pregunta operativa clara."


def build_instruction(readiness):
    if readiness["ready"]:
        if v1_minimal_available():
            return (
                "<b>Instruccion para Codex</b>\n"
                "V1 minima implementada. Siguiente paso: ejecutar "
                "<code>python tools/traders_intelligence_snapshot.py</code> con signals.json fresco para acumular snapshots. "
                "No tocar trading core, NOAA ni policy."
            )
        traders = ", ".join(readiness["lead_traders"][:2] or readiness["strong_traders"][:2])
        cities = ", ".join(readiness["candidate_cities"][:4])
        return (
            "<b>Instruccion para Codex</b>\n"
            f"Preparar v1 minimo de traders_intelligence. Alcance: archivar snapshots de signals.json y construir pseudo-lifecycle "
            f"solo para {html_text(traders)} en {html_text(cities)}. No tocar trading core, NOAA ni policy."
        )
    blocker = readiness["blockers"][0] if readiness["blockers"] else None
    if not blocker:
        return ""
    mapping = {
        "census_fresh_enough": (
            "<b>Instruccion para Codex</b>\n"
            "No abrir v1 hoy. Primero refrescar directional_trader_census y directional_trader_enrichment, luego re-evaluar la shortlist."
        ),
        "crosscheck_series_deep_enough": (
            "<b>Instruccion para Codex</b>\n"
            "No abrir v1 hoy. Dejar acumular al menos 5 corridas recientes de signals_crosscheck antes de archivar snapshots."
        ),
        "lead_trader_present": (
            "<b>Instruccion para Codex</b>\n"
            "No abrir v1 hoy. Seguir observando hasta que aparezca al menos un trader muy activo con muestra blocked robusta."
        ),
        "strong_trader_depth": (
            "<b>Instruccion para Codex</b>\n"
            "No abrir v1 hoy. Falta profundidad de traders fuertes; seguir con v0 y revalidar la shortlist operativa."
        ),
        "candidate_city_gap_exists": (
            "<b>Instruccion para Codex</b>\n"
            "No abrir v1 hoy. Falta un gap claro trader_only sobre ciudades concretas; seguir leyendo v0 y no archivar por archivar."
        ),
        "health_usable_signal": (
            "<b>Instruccion para Codex</b>\n"
            "No abrir v1 hoy. Arreglar primero la salud de inputs/salida de traders_intelligence."
        ),
    }
    return mapping.get(blocker["id"], "")


def build_message(payload, readiness, top_active):
    lines = [
        "<b>TRADERS INTELLIGENCE - resumen diario</b>",
        f"Health: <code>{html_text(payload.get('health_status', 'unknown'))}</code> | Traders: <code>{html_text(payload.get('integrity', {}).get('n_traders_profiled'))}</code>",
        f"Census stale days: <code>{html_text(payload.get('integrity', {}).get('census_stale_days'))}</code>",
        "",
        "<b>Lectura del sistema</b>",
        f"- {html_text(progress_sentence(readiness))}",
    ]

    if top_active:
        lines.extend(["", "<b>Wallets activas hoy</b>"])
        for trader in top_active[:5]:
            blocked = trader.get("blocked_signal_performance", {})
            blocked_wr = blocked.get("wr_pct")
            blocked_n = blocked.get("n_resolved")
            lines.append(
                f"- {html_text(trader.get('pseudonym'))}: active_now={html_text(get_active_now(trader))}, "
                f"blocked_wr={html_text(blocked_wr if blocked_wr is not None else 'n/d')} "
                f"(n={html_text(blocked_n if blocked_n is not None else 'n/d')})"
            )

    lines.extend(["", "<b>Checks para v1</b>"])
    for check in readiness["checks"]:
        badge = "OK" if check["passed"] else "WAIT"
        lines.append(f"- {badge} {html_text(check['label'])} ({html_text(check['detail'])})")

    if readiness["ready"]:
        lines.extend([
            "",
            "<b>V1 readiness</b>",
            f"- READY: {html_text(readiness['question_for_v1'])}",
        ])
    else:
        lines.extend([
            "",
            "<b>V1 readiness</b>",
            "- NOT READY",
        ])

    instruction = build_instruction(readiness)
    if instruction:
        lines.extend(["", instruction])

    warnings = payload.get("warnings", []) or []
    if warnings:
        lines.extend(["", "<b>Warnings</b>"])
        for warning in warnings[:3]:
            lines.append(f"- {html_text(warning)}")

    return "\n".join(lines)


def render_markdown(payload, readiness, top_active, telegram_result):
    lines = [
        "# Traders Intelligence Daily Summary",
        "",
        f"- Generated: `{datetime.now(timezone.utc).replace(microsecond=0).isoformat()}`",
        f"- Health status: `{payload.get('health_status', 'unknown')}`",
        f"- Traders profiled: `{payload.get('integrity', {}).get('n_traders_profiled')}`",
        f"- Census stale days: `{payload.get('integrity', {}).get('census_stale_days')}`",
        f"- V1 readiness: `{'ready' if readiness['ready'] else 'not_ready'}`",
        f"- Telegram result: `{telegram_result.get('reason')}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in readiness["checks"]:
        lines.append(f"| {check['label']} | {'OK' if check['passed'] else 'WAIT'} | {check['detail']} |")

    lines.extend(["", "## Active Traders", "", "| Trader | Active now | Blocked WR | Blocked n |", "| --- | --- | --- | --- |"])
    for trader in top_active:
        blocked = trader.get("blocked_signal_performance", {})
        lines.append(
            f"| {trader.get('pseudonym')} | {get_active_now(trader)} | "
            f"{blocked.get('wr_pct') if blocked.get('wr_pct') is not None else 'n/d'} | "
            f"{blocked.get('n_resolved') if blocked.get('n_resolved') is not None else 'n/d'} |"
        )

    lines.extend([
        "",
        "## Guidance",
        "",
        f"- {progress_sentence(readiness)}",
    ])
    if readiness["ready"]:
        lines.append(f"- READY question: {readiness['question_for_v1']}")
    else:
        lines.append("- No abrir v1 hoy; usar los blockers como checklist de desbloqueo.")
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    payload = load_json(args.intelligence, required=False) or {
        "health_status": "unusable",
        "integrity": {"n_traders_profiled": 0, "census_stale_days": None},
        "traders": [],
        "warnings": [f"Missing traders intelligence input: {args.intelligence}"],
    }

    state = load_json(args.state_output, required=False) or {}
    readiness = build_readiness_checks(payload, args)
    top_active = build_daily_summary(payload)
    message = build_message(payload, readiness, top_active)

    today_utc = datetime.now(timezone.utc).date().isoformat()
    previous_ready = bool(state.get("last_v1_ready", False))
    readiness_transition = readiness["ready"] and not previous_ready

    if not args.dry_run and state.get("last_sent_date") == today_utc and not readiness_transition:
        telegram_result = {"sent": False, "reason": "already_sent_today"}
    elif args.dry_run:
        telegram_result = {"sent": False, "reason": "dry_run"}
    else:
        telegram_result = send_telegram(message)

    state.update(
        {
            "last_generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "last_readiness_status": "ready" if readiness["ready"] else "not_ready",
            "last_v1_ready": readiness["ready"],
            "last_ready_traders": readiness["lead_traders"] or readiness["strong_traders"][:2],
            "last_ready_cities": readiness["candidate_cities"][:6],
            "last_health_status": payload.get("health_status", "unknown"),
            "last_census_stale_days": payload.get("integrity", {}).get("census_stale_days"),
            "last_crosscheck_runs": payload.get("aggregate", {}).get("recent_crosscheck", {}).get("recent_runs", 0),
        }
    )
    if telegram_result.get("reason") in {"sent", "missing_telegram_env"}:
        state["last_sent_date"] = today_utc

    state_path = ensure_parent(args.state_output)
    md_path = ensure_parent(args.md_output)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload, readiness, top_active, telegram_result), encoding="utf-8")

    print(f"Traders intelligence daily summary state written to {state_path}")
    print(f"Markdown summary written to {md_path}")
    print(
        json.dumps(
            {
                "v1_readiness": "ready" if readiness["ready"] else "not_ready",
                "telegram_result": telegram_result.get("reason"),
                "readiness_transition": readiness_transition,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
