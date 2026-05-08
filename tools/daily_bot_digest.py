#!/usr/bin/env python3
"""Local Daily Bot Digest from external leaderboard P&L snapshots.

This tool is read-only by default. Telegram delivery is manual-only behind an
explicit flag; it does not touch runtime state, scheduler state, DB, or Railway.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_SNAPSHOT_PATH = Path("data") / "observability" / "leaderboard_pnl_snapshots.jsonl"
DEFAULT_ENV_PATH = Path(".env")
MONEY_QUANT = Decimal("0.01")
SOURCE = "polymarket_leaderboard"
SOURCE_QUALITY = "external_opaque"
TELEGRAM_TIMEOUT_SECONDS = 15
SPAIN_TZ = "Europe/Madrid"


class DigestError(Exception):
    pass


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read_snapshots(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DigestError(f"{path}:{line_no}: invalid JSONL: {exc.msg}") from exc
            if isinstance(row, dict):
                rows.append(row)
    return rows


def as_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def quantize_money(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def delta(latest: Any, previous: Any) -> float | None:
    latest_dec = as_decimal(latest)
    previous_dec = as_decimal(previous)
    if latest_dec is None or previous_dec is None:
        return None
    return quantize_money(latest_dec - previous_dec)


def trend_label_from_deltas(deltas: dict[str, float | None]) -> str:
    known = [as_decimal(value) for value in deltas.values() if value is not None]
    values = [value for value in known if value is not None]
    if not values:
        return "unknown"
    total = sum(values, Decimal("0"))
    if total > Decimal("0.01"):
        return "improving"
    if total < Decimal("-0.01"):
        return "worsening"
    return "flat"


def money(value: Any) -> str:
    parsed = as_decimal(value)
    if parsed is None:
        return "unknown"
    return f"{parsed.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):+,.2f}"


def plain_value(value: Any) -> str:
    parsed = as_decimal(value)
    if parsed is None:
        return "unknown"
    return f"{parsed.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):,.2f}"


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def telegram_money(value: Any) -> str:
    parsed = as_decimal(value)
    if parsed is None:
        return "no disponible"
    return f"{parsed.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):+,.2f}$"


def telegram_plain_value(value: Any) -> str:
    parsed = as_decimal(value)
    if parsed is None:
        return "no disponible"
    return f"{parsed.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):,.2f}$"


def telegram_delta(value: Any) -> str:
    parsed = as_decimal(value)
    if parsed is None:
        return "no disponible"
    if parsed == Decimal("0"):
        return "sin cambios"
    return f"{parsed.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):+,.2f}$"


def telegram_trend_sentence(trend_label: str) -> str:
    if trend_label == "improving":
        return "Mejora frente al último registro válido."
    if trend_label == "worsening":
        return "Empeora frente al último registro válido."
    if trend_label == "flat":
        return "Sin cambios relevantes frente al último registro válido."
    return "Aún no hay una tendencia clara."


def html_text(value: Any) -> str:
    return html.escape(str(value), quote=False)


def bold(value: Any) -> str:
    return f"<b>{html_text(value)}</b>"


def strip_html_tags(message: str) -> str:
    return html.unescape(re.sub(r"</?b>", "", message))


def last_sunday(year: int, month: int) -> datetime:
    day = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
    while day.weekday() != 6:
        day -= timedelta(days=1)
    return day


def madrid_offset_without_tzdata(utc_dt: datetime) -> int:
    year = utc_dt.year
    dst_start = last_sunday(year, 3).replace(hour=1, minute=0, second=0, microsecond=0)
    dst_end = last_sunday(year, 10).replace(hour=1, minute=0, second=0, microsecond=0)
    return 2 if dst_start <= utc_dt < dst_end else 1


def format_telegram_timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw or raw == "unknown":
        return "no disponible"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return html_text(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    try:
        local = parsed.astimezone(ZoneInfo(SPAIN_TZ))
        return local.strftime("%d/%m/%Y %H:%M hora España")
    except ZoneInfoNotFoundError:
        utc_dt = parsed.astimezone(timezone.utc)
        local = utc_dt + timedelta(hours=madrid_offset_without_tzdata(utc_dt))
        return local.strftime("%d/%m/%Y %H:%M hora España")


def build_deltas(latest: dict[str, Any] | None, previous: dict[str, Any] | None) -> dict[str, float | None]:
    if not latest or not previous:
        return {
            "day_delta": None,
            "week_delta": None,
            "month_delta": None,
            "all_delta": None,
        }
    return {
        "day_delta": delta(latest.get("pnl_day"), previous.get("pnl_day")),
        "week_delta": delta(latest.get("pnl_week"), previous.get("pnl_week")),
        "month_delta": delta(latest.get("pnl_month"), previous.get("pnl_month")),
        "all_delta": delta(latest.get("pnl_all"), previous.get("pnl_all")),
    }


def is_valid_trend_snapshot(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    if str(row.get("query_status", "")).lower() not in {"ok", "success"}:
        return False
    return all(row.get(f"pnl_{name}") is not None for name in ("day", "week", "month", "all"))


def valid_trend_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if is_valid_trend_snapshot(row)]


def normalized_latest(latest: dict[str, Any] | None) -> dict[str, Any] | None:
    if latest is None:
        return None
    normalized = dict(latest)
    normalized["source"] = SOURCE
    normalized["source_quality"] = SOURCE_QUALITY
    normalized["dashboard_equivalent"] = False
    normalized["usable_for_digest"] = True
    normalized["usable_for_trend"] = True
    normalized["usable_for_bankroll"] = False
    normalized["volume_label"] = "leaderboard_trading_volume"
    return normalized


def build_digest_from_rows(
    rows: list[dict[str, Any]],
    snapshot_file: str | Path,
    db_throughput: dict[str, Any] | None = None,
) -> dict[str, Any]:
    latest = normalized_latest(rows[-1]) if rows else None
    valid_rows = valid_trend_snapshots(rows)
    latest_valid = normalized_latest(valid_rows[-1]) if valid_rows else None
    previous_valid = valid_rows[-2] if len(valid_rows) >= 2 else None
    deltas = build_deltas(latest_valid, previous_valid)
    trend_label = trend_label_from_deltas(deltas)
    if latest_valid and not previous_valid:
        trend_label = "unknown"

    payload: dict[str, Any] = {
        "snapshot_file": str(snapshot_file),
        "snapshot_count": len(rows),
        "valid_snapshot_count": len(valid_rows),
        "latest": latest,
        "latest_valid": latest_valid,
        "previous": previous_valid,
        "previous_valid": previous_valid,
        "deltas": deltas,
        "trend_label": trend_label,
        "source": SOURCE,
        "source_quality": SOURCE_QUALITY,
        "dashboard_equivalent": False,
        "usable_for_digest": True,
        "usable_for_trend": True,
        "usable_for_bankroll": False,
        "has_data": latest is not None,
        "latest_snapshot_query_status": latest.get("query_status") if latest else None,
        "no_previous_snapshot": latest_valid is not None and previous_valid is None,
        "db_throughput": db_throughput,
    }
    payload["message"] = render_human_digest(payload)
    payload["telegram_preview"] = render_telegram_digest(payload)
    return payload


def build_digest(path: Path, db_throughput: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_digest_from_rows(read_snapshots(path), path, db_throughput=db_throughput)


def parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def read_env_file_values(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                parsed = parse_env_line(raw_line)
                if parsed is None:
                    continue
                key, value = parsed
                if key in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"}:
                    values[key] = value
    except OSError:
        return {}
    return values


def resolve_telegram_env() -> tuple[str, str, str | None, list[str]]:
    env_file_values = read_env_file_values()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    token_env = "TELEGRAM_BOT_TOKEN" if bot_token else None
    if not bot_token:
        bot_token = os.getenv("TELEGRAM_TOKEN", "")
        token_env = "TELEGRAM_TOKEN" if bot_token else None
    if not bot_token:
        bot_token = env_file_values.get("TELEGRAM_BOT_TOKEN", "")
        token_env = ".env:TELEGRAM_BOT_TOKEN" if bot_token else None
    if not bot_token:
        bot_token = env_file_values.get("TELEGRAM_TOKEN", "")
        token_env = ".env:TELEGRAM_TOKEN" if bot_token else None
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    chat_id_env = "TELEGRAM_CHAT_ID" if chat_id else None
    if not chat_id:
        chat_id = env_file_values.get("TELEGRAM_CHAT_ID", "")
        chat_id_env = ".env:TELEGRAM_CHAT_ID" if chat_id else None
    missing: list[str] = []
    if not bot_token:
        missing.append("TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN")
    if not chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    return bot_token, chat_id, token_env or chat_id_env, missing


def send_telegram_manual(message: str) -> dict[str, Any]:
    bot_token, chat_id, token_env, missing = resolve_telegram_env()
    if missing:
        return {
            "sent": False,
            "reason": "TELEGRAM_NOT_CONFIGURED",
            "missing_env": missing,
            "token_env_used": token_env,
        }
    def build_request(text: str, parse_mode: str | None = "HTML") -> urllib.request.Request:
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    try:
        with urllib.request.urlopen(build_request(message), timeout=TELEGRAM_TIMEOUT_SECONDS) as resp:
            return {
                "sent": True,
                "reason": "sent",
                "http_code": getattr(resp, "status", None),
                "parse_mode": "HTML",
                "token_env_used": token_env,
            }
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            try:
                with urllib.request.urlopen(
                    build_request(strip_html_tags(message), parse_mode=None),
                    timeout=TELEGRAM_TIMEOUT_SECONDS,
                ) as resp:
                    return {
                        "sent": True,
                        "reason": "sent_plain_text_fallback",
                        "http_code": getattr(resp, "status", None),
                        "parse_mode": None,
                        "token_env_used": token_env,
                    }
            except Exception as fallback_exc:
                return {
                    "sent": False,
                    "reason": "TELEGRAM_API_ERROR",
                    "http_code": exc.code,
                    "error": f"HTTPError: {exc.code}; fallback={type(fallback_exc).__name__}",
                    "token_env_used": token_env,
                }
        return {
            "sent": False,
            "reason": "TELEGRAM_API_ERROR",
            "http_code": exc.code,
            "error": f"HTTPError: {exc.code}",
            "token_env_used": token_env,
        }
    except urllib.error.URLError as exc:
        return {
            "sent": False,
            "reason": "TELEGRAM_API_ERROR",
            "error": f"URLError: {exc.reason}",
            "token_env_used": token_env,
        }
    except TimeoutError as exc:
        return {
            "sent": False,
            "reason": "TELEGRAM_API_ERROR",
            "error": f"TimeoutError: {exc}",
            "token_env_used": token_env,
        }


def render_db_throughput_human_lines(summary: dict[str, Any] | None) -> list[str]:
    if not summary:
        return []
    weak_slots = summary.get("weak_slots") or []
    weak_text = "none" if not weak_slots else "; ".join(
        f"{slot.get('slot_label', '??')} eval={slot.get('markets_evaluated', 0)} buys={slot.get('buys', 0)}"
        for slot in weak_slots[:3]
    )
    return [
        "DB Throughput:",
        f"status={summary.get('review_status', 'WATCH')}",
        f"db_status={summary.get('db_status', 'unknown')}",
        f"fresh={str(summary.get('fresh', False)).lower()} hours_ago={summary.get('hours_ago')}",
        f"gaps={summary.get('gap_count', 0)}",
        f"weak_slots={weak_text}",
        (
            f"dominant_condition={summary.get('dominant_condition', 'unknown')} "
            f"({summary.get('dominant_condition_count', 0)}/{summary.get('condition_total', 0)})"
        ),
        f"action={summary.get('suggested_action', 'Manual review only.')}",
        "LOG_ONLY: No BANKROLL, no BUY/SELL/SKIP, no Fase C.",
    ]


def render_db_throughput_telegram_lines(summary: dict[str, Any] | None) -> list[str]:
    if not summary:
        return []
    weak_slots = summary.get("weak_slots") or []
    if weak_slots:
        weak_text = "; ".join(
            f"{html_text(slot.get('slot_label', '??'))}: {slot.get('markets_evaluated', 0)} eval / {slot.get('buys', 0)} buys"
            for slot in weak_slots[:3]
        )
    else:
        weak_text = "sin slots flojos claros"
    freshness = "fresh" if summary.get("fresh") else "con gaps/stale"
    return [
        "",
        f"DB {bold('Throughput LOG_ONLY')}",
        f"Estado: {html_text(summary.get('review_status', 'WATCH'))} ({freshness}, gaps={summary.get('gap_count', 0)})",
        f"Slots flojos: {weak_text}",
        (
            "Condicion dominante: "
            f"{html_text(summary.get('dominant_condition', 'unknown'))} "
            f"({summary.get('dominant_condition_count', 0)}/{summary.get('condition_total', 0)})"
        ),
        f"Accion: {html_text(summary.get('suggested_action', 'Revision manual.'))}",
    ]


def render_human_digest(digest: dict[str, Any]) -> str:
    latest = digest.get("latest")
    previous = digest.get("previous")
    deltas = digest.get("deltas") or {}
    lines = ["DAILY BOT DIGEST"]
    lines.append("")
    if not latest:
        lines.extend(
            [
                "data_unavailable: No leaderboard P&L snapshot data.",
                f"snapshot_count={digest.get('snapshot_count', 0)}",
                "",
                "P&L leaderboard:",
                "DAY: unknown",
                "WEEK: unknown",
                "MONTH: unknown",
                "ALL: unknown",
                "",
                "Leaderboard trading volume:",
                "DAY: unknown",
                "WEEK: unknown",
                "MONTH: unknown",
                "ALL: unknown",
                "",
                "Trend vs previous valid snapshot:",
                "trend_label=unknown",
                "",
                "Data quality:",
                f"source={SOURCE}",
                f"source_quality={SOURCE_QUALITY}",
                f"dashboard_equivalent={bool_text(False)}",
                f"usable_for_digest={bool_text(True)}",
                f"usable_for_trend={bool_text(True)}",
                f"usable_for_bankroll={bool_text(False)}",
                "",
                "Decision:",
                "No BANKROLL increase.",
                "Observability only.",
                "No BUY/SELL/SKIP.",
                "No Fase C.",
            ]
        )
        db_lines = render_db_throughput_human_lines(digest.get("db_throughput"))
        if db_lines:
            lines.extend(["", *db_lines])
        return "\n".join(lines)

    lines.extend(
        [
            f"captured_at_utc: {latest.get('captured_at_utc', 'unknown')}",
            f"query_status: {latest.get('query_status', 'unknown')}",
            "",
            "P&L leaderboard:",
            f"DAY: {money(latest.get('pnl_day'))}",
            f"WEEK: {money(latest.get('pnl_week'))}",
            f"MONTH: {money(latest.get('pnl_month'))}",
            f"ALL: {money(latest.get('pnl_all'))}",
            "",
            "Leaderboard trading volume:",
            f"DAY: {plain_value(latest.get('vol_day'))}",
            f"WEEK: {plain_value(latest.get('vol_week'))}",
            f"MONTH: {plain_value(latest.get('vol_month'))}",
            f"ALL: {plain_value(latest.get('vol_all'))}",
            "",
            "Trend vs previous valid snapshot:",
        ]
    )
    latest_valid = digest.get("latest_valid")
    if latest_valid and not is_valid_trend_snapshot(latest):
        lines.append(f"last_valid_snapshot_captured_at_utc: {latest_valid.get('captured_at_utc', 'unknown')}")
    if previous is None:
        lines.append("No previous valid snapshot yet")
    else:
        lines.append(f"previous_valid_captured_at_utc: {previous.get('captured_at_utc', 'unknown')}")
    lines.extend(
        [
            f"day_delta: {money(deltas.get('day_delta'))}",
            f"week_delta: {money(deltas.get('week_delta'))}",
            f"month_delta: {money(deltas.get('month_delta'))}",
            f"all_delta: {money(deltas.get('all_delta'))}",
            f"trend_label={digest.get('trend_label', 'unknown')}",
            "",
            "Data quality:",
            f"source={SOURCE}",
            f"source_quality={SOURCE_QUALITY}",
            f"dashboard_equivalent={bool_text(False)}",
            f"usable_for_digest={bool_text(True)}",
            f"usable_for_trend={bool_text(True)}",
            f"usable_for_bankroll={bool_text(False)}",
            "",
            "Decision:",
            "No BANKROLL increase.",
            "Observability only.",
            "No BUY/SELL/SKIP.",
            "No Fase C.",
        ]
    )
    db_lines = render_db_throughput_human_lines(digest.get("db_throughput"))
    if db_lines:
        lines.extend(["", *db_lines])
    return "\n".join(lines)


def render_telegram_digest(digest: dict[str, Any]) -> str:
    latest = digest.get("latest")
    if not latest:
        return "\n".join(
            [
                f"📊 {bold('RESUMEN DIARIO DEL BOT')}",
                "",
                f"🕒 {bold('Actualización')}",
                "Aún no hay datos del leaderboard.",
                "",
                f"💰 {bold('Evolución P&L')}",
                "P&L leaderboard: no disponible",
                "",
                f"📈 {bold('Tendencia')}",
                "Aún no hay comparación disponible.",
                "",
                f"🔄 {bold('Actividad')}",
                "Volumen operado según leaderboard: no disponible",
                "",
                f"🧭 {bold('Lectura rápida')}",
                "No hay registro válido para resumir hoy.",
                "",
                f"ℹ️ {bold('Nota')}",
                "Mensaje informativo. No cambia bankroll, no compra, no vende y no activa Fase C.",
            ]
        )
    deltas = digest.get("deltas") or {}
    previous = digest.get("previous")
    latest_valid = digest.get("latest_valid")
    latest_failed = not is_valid_trend_snapshot(latest)
    update_line = format_telegram_timestamp(latest.get("captured_at_utc"))
    if latest_failed:
        update_line = "No se pudo actualizar el dato en este intento."
        if latest_valid:
            update_line += f" Último dato válido: {format_telegram_timestamp(latest_valid.get('captured_at_utc'))}."

    trend_lines: list[str]
    if latest_failed:
        trend_lines = ["Aun no hay comparacion disponible en este intento."]
    elif previous:
        trend_lines = [
            telegram_trend_sentence(str(digest.get("trend_label", "unknown"))),
            f"• Día: {telegram_delta(deltas.get('day_delta'))}",
            f"• Semana: {telegram_delta(deltas.get('week_delta'))}",
            f"• Mes: {telegram_delta(deltas.get('month_delta'))}",
            f"• Total: {telegram_delta(deltas.get('all_delta'))}",
        ]
    else:
        trend_lines = ["Aún no hay comparación disponible."]

    reading = {
        "improving": "El bot mejora respecto al último registro válido.",
        "worsening": "El bot empeora respecto al último registro válido.",
        "flat": "El bot se mantiene estable respecto al último registro válido.",
    }.get(str(digest.get("trend_label", "unknown")), "Lectura solo informativa; falta comparación suficiente.")
    if latest_valid and not is_valid_trend_snapshot(latest):
        reading = "El último intento falló; uso solo el último dato válido como referencia."

    lines = [
        f"📊 {bold('RESUMEN DIARIO DEL BOT')}",
        "",
        f"🕒 {bold('Actualización')}",
        update_line,
        "",
        f"💰 {bold('Evolución P&L')}",
        f"• Día: {telegram_money(latest.get('pnl_day'))}",
        f"• Semana: {telegram_money(latest.get('pnl_week'))}",
        f"• Mes: {telegram_money(latest.get('pnl_month'))}",
        f"• Total histórico: {telegram_money(latest.get('pnl_all'))}",
        "",
        f"📈 {bold('Tendencia')}",
        *trend_lines,
        "",
        f"🔄 {bold('Actividad')}",
        "Volumen operado según leaderboard:",
        f"• Día: {telegram_plain_value(latest.get('vol_day'))}",
        f"• Semana: {telegram_plain_value(latest.get('vol_week'))}",
        f"• Mes: {telegram_plain_value(latest.get('vol_month'))}",
        f"• Total histórico: {telegram_plain_value(latest.get('vol_all'))}",
        "",
        f"🧭 {bold('Lectura rápida')}",
        reading,
        "",
        f"ℹ️ {bold('Nota')}",
        "Mensaje informativo. No cambia bankroll, no compra, no vende y no activa Fase C.",
    ]
    lines.extend(render_db_throughput_telegram_lines(digest.get("db_throughput")))
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily Bot Digest dry-run and Telegram preview CLI.")
    parser.add_argument("--snapshot-file", default=str(DEFAULT_SNAPSHOT_PATH), help="Leaderboard snapshot JSONL path.")
    parser.add_argument("--dry-run", action="store_true", help="Print the human digest and write nothing.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON with latest, previous, deltas, and message.")
    parser.add_argument(
        "--telegram-preview",
        action="store_true",
        help="Print Telegram-ready preview text only. Does not send Telegram.",
    )
    parser.add_argument(
        "--send-telegram-manual",
        action="store_true",
        help="Manually send the Telegram digest after printing the preview. No scheduler or retries.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv or sys.argv[1:])
    try:
        digest = build_digest(Path(args.snapshot_file))
    except DigestError as exc:
        print(f"daily_bot_digest error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(digest, indent=2, sort_keys=True))
        return 0
    if args.telegram_preview or args.send_telegram_manual:
        print(digest["telegram_preview"])
        if args.send_telegram_manual:
            result = send_telegram_manual(digest["telegram_preview"])
            print("")
            print(f"telegram_manual_send={result.get('reason')}")
            if result.get("missing_env"):
                print("missing_env=" + ",".join(result["missing_env"]))
            if result.get("error"):
                print("telegram_error=" + str(result["error"]))
            return 0 if result.get("reason") in {"sent", "TELEGRAM_NOT_CONFIGURED"} else 2
        return 0
    print(digest["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
