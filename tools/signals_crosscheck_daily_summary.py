#!/usr/bin/env python3
"""Daily temporal summary for trader-vs-bot crosscheck with optional Telegram send."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from signals_vs_edge_crosscheck import append_record, build_crosscheck_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CROSSCHECK_PRIMARY = REPO_ROOT / "data" / "signals_crosscheck.jsonl"
DEFAULT_CROSSCHECK_FALLBACK = REPO_ROOT / "data" / "runtime_import_derived" / "signals_crosscheck.jsonl"
DEFAULT_SIGNALS_PATH = REPO_ROOT / "data" / "runtime_import" / "signals.json"
DEFAULT_SHADOW_PATH = REPO_ROOT / "data" / "runtime_import" / "shadow_city_tracking.json"
DEFAULT_POLICY_PATH = REPO_ROOT / "data" / "runtime_import" / "city_policy_state.json"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "signals_crosscheck_daily_summary_state.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "signals_crosscheck_daily_summary_latest.md"


def pick_default_crosscheck_path() -> Path:
    if DEFAULT_CROSSCHECK_PRIMARY.exists():
        return DEFAULT_CROSSCHECK_PRIMARY
    return DEFAULT_CROSSCHECK_FALLBACK


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resume la serie temporal del cross-check traders vs bot y la puede enviar por Telegram."
    )
    parser.add_argument("--crosscheck-file", default=str(pick_default_crosscheck_path()))
    parser.add_argument("--signals", default=str(DEFAULT_SIGNALS_PATH))
    parser.add_argument("--shadow", default=str(DEFAULT_SHADOW_PATH))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--state-output", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument(
        "--window-runs",
        type=int,
        default=int(os.getenv("SIGNALS_CROSSCHECK_SUMMARY_WINDOW_RUNS", "7")),
    )
    parser.add_argument(
        "--min-runs",
        type=int,
        default=int(os.getenv("SIGNALS_CROSSCHECK_SUMMARY_MIN_RUNS", "5")),
    )
    parser.add_argument("--ingest-if-missing-today", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_json(path_str: str, required: bool = True):
    path = Path(path_str)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required input: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ensure_parent(path_str: str) -> Path:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def send_telegram(message: str):
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return {"sent": False, "reason": "missing_telegram_env"}
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)
    return {"sent": True, "reason": "sent"}


def load_jsonl_records(path: Path):
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("run_at"):
            records.append(row)
    return records


def parse_run_date(record: dict) -> str:
    run_at = str(record.get("run_at", ""))
    return run_at[:10]


def dedupe_latest_by_day(records: list[dict]) -> list[dict]:
    deduped = {}
    for record in records:
        day = parse_run_date(record)
        if not day:
            continue
        prev = deduped.get(day)
        if prev is None or str(record.get("run_at", "")) > str(prev.get("run_at", "")):
            deduped[day] = record
    return [deduped[key] for key in sorted(deduped.keys())]


def maybe_ingest_today(args, records: list[dict]):
    today = datetime.now(timezone.utc).date().isoformat()
    if any(parse_run_date(record) == today for record in records):
        return None
    signals_path = Path(args.signals)
    shadow_path = Path(args.shadow)
    if not signals_path.exists() or not shadow_path.exists():
        return None
    record, _ = build_crosscheck_record(
        signals_path=str(signals_path),
        shadow_path=str(shadow_path),
        policy_path=str(args.policy),
    )
    append_record(record, output_path=str(args.crosscheck_file))
    return record


def classify_gap_state(first_record: dict, last_record: dict):
    first_gap = int(first_record.get("trader_only_count", 0) or 0)
    last_gap = int(last_record.get("trader_only_count", 0) or 0)
    first_match = int(first_record.get("match_count", 0) or 0)
    last_match = int(last_record.get("match_count", 0) or 0)
    delta_gap = last_gap - first_gap
    delta_match = last_match - first_match
    if delta_gap <= -3:
        return "mejorando"
    if delta_gap >= 3 and delta_match <= 0:
        return "empeorando"
    if abs(delta_gap) <= 2 and abs(delta_match) <= 2:
        return "estructural"
    return "mixto"


def progress_sentence(gap_state: str):
    mapping = {
        "mejorando": "El gap traders-vs-bot se esta cerrando respecto al inicio de la serie reciente.",
        "empeorando": "El gap traders-vs-bot se amplio y hoy conviene tratarlo como cuello operativo real.",
        "estructural": "El gap sigue siendo estructural: no converge por si solo y merece seguimiento continuo.",
        "mixto": "La serie se mueve, pero todavia no da una historia unica de mejora o deterioro.",
        "insuficiente": "Aun no hay serie suficiente para concluir si el gap es estructural o solo ruido.",
    }
    return mapping.get(gap_state, mapping["insuficiente"])


def get_blocked_cities(policy_data: dict):
    blocked = set()
    for key in ("auto_blocked_cities", "blocked_cities", "manual_blocked_cities"):
        value = policy_data.get(key, {})
        if isinstance(value, dict):
            blocked.update(value.keys())
        elif isinstance(value, list):
            blocked.update(str(item) for item in value)
    return blocked


def build_today_operational_sample(signals_path: str, shadow_path: str, policy_path: str):
    try:
        sig_data = load_json(signals_path, required=True)
        shadow_data = load_json(shadow_path, required=True)
        policy_data = load_json(policy_path, required=False) or {}
    except FileNotFoundError:
        return []

    signals = sig_data.get("signals", []) if isinstance(sig_data, dict) else []
    shadow_cities = shadow_data.get("cities", {}) if isinstance(shadow_data, dict) else {}
    blocked_cities = get_blocked_cities(policy_data)
    allowed_conditions = {"at_or_above", "at_or_below"}

    stats = {}
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        city = signal.get("city")
        if not city:
            continue
        city_stat = stats.setdefault(city, {"allowed": 0, "consensus": 0, "max_wr": 0.0})
        if signal.get("condition") in allowed_conditions:
            city_stat["allowed"] += 1
        if signal.get("has_consensus"):
            city_stat["consensus"] += 1
        wr = float(signal.get("trader_win_rate") or 0.0)
        if wr > city_stat["max_wr"]:
            city_stat["max_wr"] = wr

    sample = []
    for city, city_stat in stats.items():
        if city in blocked_cities:
            continue
        if city_stat["allowed"] <= 0 or city_stat["consensus"] <= 0:
            continue
        shadow = shadow_cities.get(city, {}) if isinstance(shadow_cities, dict) else {}
        if int(shadow.get("edge_hits", 0) or 0) > 0:
            continue
        sample.append(
            {
                "city": city,
                "allowed": city_stat["allowed"],
                "consensus": city_stat["consensus"],
                "max_wr": city_stat["max_wr"],
            }
        )
    sample.sort(key=lambda row: (-row["consensus"], -row["allowed"], -row["max_wr"], row["city"]))
    return sample[:4]


def summarize_runs(records: list[dict], min_runs: int):
    run_count = len(records)
    if not records:
        return {
            "run_count": 0,
            "gap_state": "insuficiente",
            "stable_trader_only": [],
            "recurring_trader_only": [],
            "median_match_count": 0,
            "median_trader_only_count": 0,
            "median_bot_only_count": 0,
            "latest_record": {},
            "first_record": {},
        }

    trader_only_counter = Counter()
    for record in records:
        trader_only_counter.update(record.get("trader_only_cities", []))

    stable_trader_only = sorted(city for city, count in trader_only_counter.items() if count == run_count)
    recurring_threshold = max(2, run_count - 1)
    recurring_trader_only = sorted(
        city
        for city, count in trader_only_counter.items()
        if count >= recurring_threshold and city not in stable_trader_only
    )

    summary = {
        "run_count": run_count,
        "stable_trader_only": stable_trader_only,
        "recurring_trader_only": recurring_trader_only,
        "median_match_count": int(median(int(r.get("match_count", 0) or 0) for r in records)),
        "median_trader_only_count": int(median(int(r.get("trader_only_count", 0) or 0) for r in records)),
        "median_bot_only_count": int(median(int(r.get("bot_only_count", 0) or 0) for r in records)),
        "latest_record": records[-1],
        "first_record": records[0],
    }
    if run_count < min_runs:
        summary["gap_state"] = "insuficiente"
    else:
        summary["gap_state"] = classify_gap_state(records[0], records[-1])
    return summary


def build_message(summary: dict, today_operational_sample: list[dict]):
    latest = summary["latest_record"]
    stable = summary["stable_trader_only"][:8]
    recurring = summary["recurring_trader_only"][:6]

    if summary["run_count"] == 0:
        return "\n".join(
            [
                "<b>Cross-check traders vs bot - resumen diario</b>",
                "",
                "<b>Estado</b>",
                "Todavia no hay corridas acumuladas en <code>signals_crosscheck.jsonl</code>.",
                "",
                "<b>Instruccion para Codex</b>",
                "Primero asegurar la ingestión diaria del cross-check antes de sacar conclusiones de serie temporal.",
            ]
        )

    lines = [
        f"<b>Cross-check traders vs bot - resumen diario ({parse_run_date(latest)} UTC)</b>",
        "",
        "<b>Estado</b>",
        progress_sentence(summary["gap_state"]),
        "",
        "<b>Lo importante de ayer</b>",
        (
            f"- Serie reciente: <code>{summary['run_count']}</code> corridas | "
            f"medianas <code>MATCH={summary['median_match_count']}</code> / "
            f"<code>BOT_ONLY={summary['median_bot_only_count']}</code> / "
            f"<code>TRADER_ONLY={summary['median_trader_only_count']}</code>."
        ),
        (
            f"- Ultima corrida: <code>MATCH={int(latest.get('match_count', 0) or 0)}</code> / "
            f"<code>BOT_ONLY={int(latest.get('bot_only_count', 0) or 0)}</code> / "
            f"<code>TRADER_ONLY={int(latest.get('trader_only_count', 0) or 0)}</code>."
        ),
    ]
    if stable:
        lines.append(
            f"- TRADER_ONLY en {summary['run_count']}/{summary['run_count']} corridas: "
            f"<code>{', '.join(stable)}</code>."
        )
    if recurring:
        lines.append(
            f"- Casi persistente ({summary['run_count'] - 1}/{summary['run_count']}): "
            f"<code>{', '.join(recurring)}</code>."
        )

    action = classify_action_level(summary, today_operational_sample)

    lines.extend(["", "<b>Lectura del sistema</b>", f"- {progress_sentence(summary['gap_state'])}"])
    if today_operational_sample:
        sample_text = "; ".join(
            f"{row['city']} ({row['allowed']} sen, consenso={row['consensus']}, WR max {row['max_wr']:.0f}%)"
            for row in today_operational_sample
        )
        lines.append(f"- Gap operativo hoy fuera de blocked: <code>{sample_text}</code>.")
    else:
        lines.append("- Hoy no aparece un gap operativo fuerte fuera de blocked con consenso y condicion operable.")

    lines.extend(
        [
            "",
            "<b>Nivel de accion</b>",
            f"{action['label']}: {action['reason']}",
            "",
            "<b>Tarea para Codex</b>",
            action["task"],
        ]
    )
    return "\n".join(lines)


def classify_action_level(summary: dict, today_operational_sample: list[dict]) -> dict:
    """Translate the daily readout into a concrete next step."""
    run_count = int(summary.get("run_count", 0) or 0)
    stable = summary.get("stable_trader_only", []) or []
    recurring = summary.get("recurring_trader_only", []) or []

    if run_count < 5:
        return {
            "label": "INFO",
            "reason": "serie todavia corta; no hay base suficiente para decidir.",
            "task": "No tocar reglas. Confirmar que el cross-check sigue acumulando corridas diarias.",
        }

    if today_operational_sample:
        top_city = today_operational_sample[0]["city"]
        return {
            "label": "ACTION",
            "reason": "hay gap operativo real fuera de blocked con consenso y condicion operable.",
            "task": (
                f"Auditar <code>{top_city}</code> primero: whitelist, RESOLUTION_ICAO/estacion, "
                "OBSERVED_AUDIT_CITIES/cobertura NOAA y ultimas señales trader. Cerrar con decision: "
                "<code>sin cambio</code>, <code>preparar whitelist/canary</code> o <code>bloqueo por fuente</code>. "
                "No tocar reglas de entrada ni trading core en esta tarea."
            ),
        }

    if len(stable) >= 3 or len(recurring) >= 5:
        focus = stable[:3] or recurring[:3]
        return {
            "label": "WATCH",
            "reason": "hay persistencia trader-only, pero hoy no hay gap operativo accionable.",
            "task": (
                "Preparar backlog de revision para "
                f"<code>{', '.join(focus)}</code>: comprobar si faltan en whitelist o si falta cobertura observada. "
                "Ejecutar solo cuando alguna ciudad tambien aparezca como gap operativo real."
            ),
        }

    return {
        "label": "INFO",
        "reason": "sin gap operativo ni persistencia suficiente.",
        "task": "No abrir tarea nueva; continuar acumulando serie.",
    }


def render_markdown(payload: dict):
    return "\n".join(
        [
            "# Signals Crosscheck Daily Summary",
            "",
            f"- Generated: `{payload['generated_at']}`",
            f"- Crosscheck file: `{payload['crosscheck_file']}`",
            f"- Runs considered: `{payload['summary']['run_count']}`",
            f"- Telegram result: `{payload['telegram_result']['reason']}`",
            "",
            "## Message",
            "",
            "```html",
            payload["message"],
            "```",
            "",
        ]
    )


def main():
    args = parse_args()
    crosscheck_path = Path(args.crosscheck_file)
    crosscheck_path.parent.mkdir(parents=True, exist_ok=True)

    records = dedupe_latest_by_day(load_jsonl_records(crosscheck_path))
    ingested_record = None
    if args.ingest_if_missing_today:
        ingested_record = maybe_ingest_today(args, records)
        if ingested_record:
            records = dedupe_latest_by_day(load_jsonl_records(crosscheck_path))

    recent_records = records[-max(1, args.window_runs) :]
    summary = summarize_runs(recent_records, min_runs=args.min_runs)
    today_operational_sample = build_today_operational_sample(args.signals, args.shadow, args.policy)

    state = load_json(args.state_output, required=False) or {}
    today_utc = datetime.now(timezone.utc).date().isoformat()
    message = build_message(summary, today_operational_sample)

    if not args.dry_run and state.get("last_sent_date") == today_utc:
        telegram_result = {"sent": False, "reason": "already_sent_today"}
    elif args.dry_run:
        telegram_result = {"sent": False, "reason": "dry_run"}
    else:
        telegram_result = send_telegram(message)

    if telegram_result.get("reason") in {"sent", "missing_telegram_env"}:
        state["last_sent_date"] = today_utc
    state.update(
        {
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "last_crosscheck_file": str(crosscheck_path),
            "last_run_count": summary["run_count"],
            "last_gap_state": summary["gap_state"],
            "last_stable_trader_only": summary["stable_trader_only"],
            "last_ingested_run_at": ingested_record.get("run_at") if ingested_record else None,
        }
    )

    state_path = ensure_parent(args.state_output)
    md_path = ensure_parent(args.md_output)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "crosscheck_file": str(crosscheck_path),
        "summary": summary,
        "today_operational_sample": today_operational_sample,
        "telegram_result": telegram_result,
        "message": message,
    }
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Signals crosscheck summary state written to {state_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
