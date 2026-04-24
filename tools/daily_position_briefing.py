#!/usr/bin/env python3
"""Briefing diario de posiciones abiertas y retrospective de SL."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIFECYCLE_FILE = REPO_ROOT / "data" / "trade_lifecycle.json"
DEFAULT_LIFECYCLE_FALLBACK = REPO_ROOT / "data" / "runtime_import" / "trade_lifecycle.json"
DEFAULT_SL_STATE_FILE = REPO_ROOT / "data" / "sl_retrospective_state.json"
DEFAULT_BRIEFING_STATE_FILE = REPO_ROOT / "data" / "daily_briefing_state.json"
TARGET_SAMPLE_SIZE = 16
APR28_CHECKPOINT = date(2026, 4, 28)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Construye el briefing diario de posiciones abiertas y cierres recientes."
    )
    parser.add_argument("--lifecycle-file", default=str(DEFAULT_LIFECYCLE_FILE))
    parser.add_argument("--sl-state-file", default=str(DEFAULT_SL_STATE_FILE))
    parser.add_argument("--briefing-state-file", default=str(DEFAULT_BRIEFING_STATE_FILE))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def resolve_lifecycle_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.exists():
        return path
    if path.resolve() == DEFAULT_LIFECYCLE_FILE.resolve() and DEFAULT_LIFECYCLE_FALLBACK.exists():
        return DEFAULT_LIFECYCLE_FALLBACK
    raise FileNotFoundError(f"Missing lifecycle file: {path}")


def load_json(path: Path, required: bool = True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required file: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def parse_dt(value: str | None):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_date(value: str | None):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_snapshot_metrics(record: dict):
    snapshots = record.get("position_snapshots") or []
    last_snapshot = snapshots[-1] if snapshots and isinstance(snapshots[-1], dict) else {}
    cur_price = None
    for key in ("cur_price", "current_price", "market_price", "price"):
        cur_price = as_float(last_snapshot.get(key))
        if cur_price is not None:
            break
    pct_pnl = None
    for key in ("pct_pnl", "pnl_pct", "unrealized_pnl_pct"):
        pct_pnl = as_float(last_snapshot.get(key))
        if pct_pnl is not None:
            break
    entry_price = as_float(record.get("avg_entry_price"))
    if pct_pnl is None and cur_price is not None and entry_price not in (None, 0):
        pct_pnl = ((cur_price / entry_price) - 1.0) * 100.0
    return {
        "cur_price": cur_price,
        "pct_pnl": pct_pnl,
        "snapshot_at": last_snapshot.get("timestamp") or last_snapshot.get("captured_at"),
    }


def build_open_positions(records: list[dict], today: date):
    active_rows = []
    stale_rows = []
    post_resolution_rows = []
    for record in records:
        if record.get("status") != "open":
            continue
        opened_at = parse_dt(record.get("opened_at"))
        resolution_date = parse_date(record.get("date"))
        metrics = extract_snapshot_metrics(record)
        snapshots = record.get("position_snapshots") or []
        market_observations = record.get("market_observations") or []
        has_live_context = bool(snapshots) or bool(market_observations) or metrics["cur_price"] is not None or metrics["pct_pnl"] is not None
        resolution_status = ""
        days_past_resolution = None
        if resolution_date is not None:
            if resolution_date < today:
                days_past_resolution = (today - resolution_date).days
                resolution_status = f" | ⚠ venció {resolution_date.isoformat()}"
            elif resolution_date <= (today + timedelta(days=2)):
                resolution_status = f" | ⏰ resuelve {resolution_date.isoformat()}"
        age_days = (today - opened_at.date()).days if opened_at else None
        row = {
            "label": record.get("label") or record.get("question") or "Unknown",
            "side": str(record.get("side", "") or "").upper(),
            "avg_entry_price": as_float(record.get("avg_entry_price")),
            "date": resolution_date.isoformat() if resolution_date else None,
            "opened_at": record.get("opened_at"),
            "age_days": age_days,
            "cur_price": metrics["cur_price"],
            "pct_pnl": metrics["pct_pnl"],
            "resolution_status": resolution_status,
            "days_past_resolution": days_past_resolution,
            "snapshot_count": len(snapshots),
            "market_obs_count": len(market_observations),
            "has_live_context": has_live_context,
        }
        if resolution_date is not None and resolution_date < today:
            if has_live_context:
                post_resolution_rows.append(row)
            else:
                stale_rows.append(row)
        else:
            active_rows.append(row)
    sort_key = lambda row: (row["date"] or "9999-12-31", row["label"])
    active_rows.sort(key=sort_key)
    stale_rows.sort(key=sort_key)
    post_resolution_rows.sort(key=sort_key)
    return {
        "active": active_rows,
        "stale": stale_rows,
        "post_resolution": post_resolution_rows,
    }


def build_recent_closes(records: list[dict], now: datetime):
    cutoff = now - timedelta(hours=24)
    rows = []
    for record in records:
        closed_at = parse_dt(record.get("closed_at"))
        if closed_at is None or closed_at < cutoff:
            continue
        close_context = record.get("close_context") or {}
        rows.append(
            {
                "label": record.get("label") or record.get("question") or "Unknown",
                "side": str(record.get("side", "") or "").upper(),
                "avg_entry_price": as_float(record.get("avg_entry_price")),
                "close_price": as_float(close_context.get("close_price")),
                "close_action": close_context.get("close_action") or "",
                "close_reason": close_context.get("close_reason") or "unknown",
                "pnl_pct": as_float(close_context.get("pnl_pct")),
                "closed_at": closed_at.isoformat(),
            }
        )
    rows.sort(key=lambda row: row["closed_at"], reverse=True)
    return rows


def describe_close_reason(row: dict):
    reason = str(row.get("close_reason", "") or "").strip()
    action = str(row.get("close_action", "") or "").strip()
    if reason == "market_resolved_yes":
        return "mercado resolvió a favor de nuestro token"
    if reason == "market_resolved_no":
        return "mercado resolvió en contra de nuestro token"
    if reason == "stop_loss_intra":
        return "salida por stop-loss intra"
    if reason == "stop_loss":
        return "salida por stop-loss"
    if reason == "take_profit_intra":
        return "salida por take-profit intra"
    if reason == "take_profit":
        return "salida por take-profit"
    if reason == "micro_position_unsellable":
        return "residuo micro sin salida"
    if reason:
        return reason
    if action == "RESOLVED_WIN":
        return "mercado resuelto a favor"
    if action == "LOSS_TOTAL":
        return "cierre total en contra"
    if action == "SELL":
        return "salida ejecutada"
    return "cierre sin detalle"


def build_sl_retro_line(state_path: Path):
    state = load_json(state_path, required=False)
    if not isinstance(state, dict):
        return "🔍 SL Retro: sin datos aún"
    n_resolved = state.get("n_resolved_last")
    if n_resolved is None:
        return "🔍 SL Retro: sin datos aún"
    verdict = state.get("final_verdict") or state.get("preliminary_verdict") or "acumulando datos"
    return f"🔍 SL Retro: {int(n_resolved)}/{TARGET_SAMPLE_SIZE} resueltos — {verdict}"


def build_message(open_sections: dict, recent_closes: list[dict], sl_retro_line: str, today: date):
    lines = [f"📋 Briefing Diario — {today.isoformat()}", ""]
    active_rows = open_sections.get("active", [])
    stale_rows = open_sections.get("stale", [])
    post_resolution_rows = open_sections.get("post_resolution", [])

    if active_rows:
        lines.append(f"📂 POSICIONES ABIERTAS ({len(active_rows)})")
        for row in active_rows:
            entry_text = f"{row['avg_entry_price']:.2f}" if row["avg_entry_price"] is not None else "n/d"
            pnl_text = f"{row['pct_pnl']:+.0f}%" if row["pct_pnl"] is not None else "n/d"
            age_text = f" | {row['age_days']}d abiertas" if row["age_days"] is not None else ""
            lines.append(
                f"  • {row['label']} — entrada {entry_text} | P&L: {pnl_text}{age_text}{row['resolution_status']}"
            )
    else:
        lines.append("📂 Sin posiciones abiertas")

    if post_resolution_rows:
        lines.append("")
        lines.append(f"⚠️ POSICIONES VENCIDAS PENDIENTES DE RECONCILIAR ({len(post_resolution_rows)})")
        for row in post_resolution_rows:
            entry_text = f"{row['avg_entry_price']:.2f}" if row["avg_entry_price"] is not None else "n/d"
            pnl_text = f"{row['pct_pnl']:+.0f}%" if row["pct_pnl"] is not None else "n/d"
            lag_text = (
                f"{row['days_past_resolution']}d tras resolución"
                if row["days_past_resolution"] is not None
                else "fecha de resolución pasada"
            )
            evidence_bits = []
            if row["snapshot_count"]:
                evidence_bits.append(f"{row['snapshot_count']} snapshots")
            if row["market_obs_count"]:
                evidence_bits.append(f"{row['market_obs_count']} obs mercado")
            evidence_text = f" | {' / '.join(evidence_bits)}" if evidence_bits else ""
            lines.append(
                f"  • {row['label']} — entrada {entry_text} | P&L: {pnl_text} | {lag_text}{evidence_text}"
            )

    if stale_rows:
        lines.append("")
        lines.append(f"🗃 LEGACY STALE NO RECONCILIADO ({len(stale_rows)})")
        for row in stale_rows:
            lag_text = (
                f"{row['days_past_resolution']}d vencida"
                if row["days_past_resolution"] is not None
                else "fecha pasada"
            )
            lines.append(
                f"  • {row['label']} — sigue marcada open pero sin snapshots ni cierre registrado | {lag_text}"
            )

    lines.append("")
    lines.append("🔄 ÚLTIMAS 24H")
    if recent_closes:
        for row in recent_closes:
            side_text = row["side"] or "?"
            entry_text = f"{row['avg_entry_price']:.2f}" if row["avg_entry_price"] is not None else "n/d"
            close_price = row.get("close_price")
            close_text = f" → salida {close_price:.2f}" if close_price is not None else ""
            pnl_text = f"{row['pnl_pct']:+.0f}%" if row["pnl_pct"] is not None else "n/d"
            lines.append(
                f"  • {row['label']} — {side_text} comprada @ {entry_text}{close_text} | "
                f"{describe_close_reason(row)} | {pnl_text}"
            )
    else:
        lines.append("  Sin actividad en las últimas 24h")

    lines.append("")
    lines.append(sl_retro_line)

    if today <= APR28_CHECKPOINT:
        lines.append("")
        lines.append("🎯 Apr 28: checkpoint condition_filtered (target ≥30 trades, WR≥55%)")

    return "\n".join(lines)


def send_telegram(message: str):
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return {"sent": False, "reason": "missing_telegram_env"}
    payload = {"chat_id": chat_id, "text": message}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)
    return {"sent": True, "reason": "sent"}


def main():
    configure_stdout()
    args = parse_args()
    lifecycle_path = resolve_lifecycle_path(args.lifecycle_file)
    payload = load_json(lifecycle_path)
    records = payload.get("records", []) if isinstance(payload, dict) else []
    now = datetime.now(timezone.utc).replace(microsecond=0)
    today = now.date()

    open_sections = build_open_positions(records, today)
    recent_closes = build_recent_closes(records, now)
    sl_retro_line = build_sl_retro_line(Path(args.sl_state_file))
    message = build_message(open_sections, recent_closes, sl_retro_line, today)

    print(message)
    print("")
    print(
        json.dumps(
            {
                "lifecycle_file_used": str(lifecycle_path),
                "open_positions": len(open_sections.get("active", [])),
                "post_resolution_positions": len(open_sections.get("post_resolution", [])),
                "stale_open_positions": len(open_sections.get("stale", [])),
                "recent_closes_24h": len(recent_closes),
                "sl_retro_line": sl_retro_line,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    if args.dry_run:
        return

    state_path = Path(args.briefing_state_file)
    state = load_json(state_path, required=False) or {}
    today_str = today.isoformat()
    if not args.force and state.get("last_sent_date") == today_str:
        telegram_result = {"sent": False, "reason": "already_sent_today"}
    else:
        telegram_result = send_telegram(message)
        if telegram_result.get("reason") in {"sent", "missing_telegram_env"}:
            state["last_sent_date"] = today_str

    state["updated_at"] = now.isoformat()
    ensure_parent(state_path).write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "telegram_result": telegram_result,
                "briefing_state_file": str(state_path),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
