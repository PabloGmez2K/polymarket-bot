#!/usr/bin/env python3
"""P/L reconciliation readout with explicit Telegram instructions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIFECYCLE_FILE = REPO_ROOT / "data" / "trade_lifecycle.json"
DEFAULT_LIFECYCLE_FALLBACK = REPO_ROOT / "data" / "runtime_import" / "trade_lifecycle.json"
DEFAULT_STATE_FILE = REPO_ROOT / "data" / "pnl_reconciliation_state.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "pnl-reconciliation-readout-latest.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reconcilia la lectura de P/L del bot con la lectura wallet de Polymarket."
    )
    parser.add_argument("--lifecycle-file", default=str(DEFAULT_LIFECYCLE_FILE))
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument(
        "--polymarket-weekly-pnl",
        type=float,
        default=None,
        help="P/L 1W visto en Polymarket, si se pega manualmente desde dashboard.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
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


def parse_dt(value):
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


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def record_pnl(record: dict):
    close_context = record.get("close_context") or {}
    for key in ("pnl_cash",):
        value = as_float(close_context.get(key))
        if value is not None:
            return value
    return as_float(record.get("pnl_cash"))


def record_close_subtype(record: dict) -> str:
    close_context = record.get("close_context") or {}
    return str(
        close_context.get("close_subtype")
        or close_context.get("close_reason")
        or record.get("close_subtype")
        or record.get("close_reason")
        or ""
    )


def record_close_reason(record: dict) -> str:
    close_context = record.get("close_context") or {}
    return str(
        close_context.get("close_reason")
        or record.get("close_reason")
        or record_close_subtype(record)
        or "unknown"
    )


def record_closed_at(record: dict):
    return parse_dt(record.get("closed_at") or (record.get("close_context") or {}).get("timestamp"))


def record_opened_at(record: dict):
    return parse_dt(record.get("opened_at") or record.get("created_at"))


def record_market_date(record: dict):
    raw = str(record.get("date") or "").strip()[:10]
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_real_closed(record: dict) -> bool:
    if record.get("status") != "closed":
        return False
    if as_float(record.get("total_amount")) is not None and as_float(record.get("total_amount")) <= 0:
        return False
    subtype = record_close_subtype(record)
    if subtype in {"legacy_unresolved", "expired_no_evidence"}:
        return False
    return record_pnl(record) is not None and record_closed_at(record) is not None


def latest_open_mark(record: dict):
    snapshots = record.get("position_snapshots") or []
    if not snapshots:
        return None
    last = snapshots[-1] if isinstance(snapshots[-1], dict) else {}
    for key in ("current_value", "value", "market_value"):
        value = as_float(last.get(key))
        if value is not None:
            amount = as_float(record.get("total_amount"))
            if amount is not None:
                return value - amount
    cur_price = None
    for key in ("cur_price", "current_price", "market_price", "price"):
        cur_price = as_float(last.get(key))
        if cur_price is not None:
            break
    shares = as_float(record.get("total_shares"))
    amount = as_float(record.get("total_amount"))
    if cur_price is not None and shares is not None and amount is not None:
        return (cur_price * shares) - amount
    return None


def summarize_records(records: list[dict], now: datetime, polymarket_weekly_pnl=None):
    closed = [record for record in records if is_real_closed(record)]
    open_records = [record for record in records if record.get("status") == "open"]
    pending_exit = [record for record in records if record.get("status") == "pending_exit"]
    excluded_legacy = [
        record for record in records
        if record.get("status") == "closed" and record_close_subtype(record) == "legacy_unresolved"
    ]
    no_pnl_closed = [
        record for record in records
        if record.get("status") == "closed"
        and record_close_subtype(record) != "legacy_unresolved"
        and record_pnl(record) is None
    ]

    def window(days: int):
        cutoff = now - timedelta(days=days)
        return [record for record in closed if record_closed_at(record) >= cutoff]

    def stats(rows: list[dict]):
        pnl = sum(record_pnl(record) or 0.0 for record in rows)
        wins = sum(1 for record in rows if (record_pnl(record) or 0.0) > 0)
        losses = sum(1 for record in rows if (record_pnl(record) or 0.0) < 0)
        n = len(rows)
        wr = (wins / n * 100.0) if n else 0.0
        return {
            "n": n,
            "wins": wins,
            "losses": losses,
            "wr": round(wr, 1),
            "pnl": round(pnl, 2),
        }

    windows = {
        "7d": stats(window(7)),
        "30d": stats(window(30)),
        "60d": stats(window(60)),
    }
    recent20 = sorted(closed, key=record_closed_at)[-20:]
    windows["last20"] = stats(recent20)

    cutoff7 = now - timedelta(days=7)
    recent7 = window(7)
    resolution_batch = []
    for record in recent7:
        reason = record_close_reason(record)
        if not reason.startswith("market_resolved"):
            continue
        opened_at = record_opened_at(record)
        market_date = record_market_date(record)
        if (opened_at and opened_at < cutoff7) or (market_date and market_date < cutoff7):
            resolution_batch.append(record)
    resolution_batch_stats = stats(resolution_batch)

    group_fields = {
        "city": lambda r: str(r.get("city") or "?"),
        "condition": lambda r: str(r.get("condition") or "?"),
        "side": lambda r: str(r.get("side") or "?").upper(),
        "exit": record_close_reason,
    }
    grouped = {}
    for name, getter in group_fields.items():
        buckets = defaultdict(lambda: {"n": 0, "pnl": 0.0, "wins": 0})
        for record in recent7:
            key = getter(record)
            pnl = record_pnl(record) or 0.0
            buckets[key]["n"] += 1
            buckets[key]["pnl"] += pnl
            if pnl > 0:
                buckets[key]["wins"] += 1
        rows = []
        for key, data in buckets.items():
            rows.append({
                "key": key,
                "n": data["n"],
                "wins": data["wins"],
                "wr": round(data["wins"] / data["n"] * 100.0, 1) if data["n"] else 0.0,
                "pnl": round(data["pnl"], 2),
            })
        grouped[name] = sorted(rows, key=lambda row: (row["pnl"], -row["n"]))[:5]

    top_losses = sorted(recent7, key=lambda r: record_pnl(r) or 0.0)[:5]
    top_wins = sorted(recent7, key=lambda r: record_pnl(r) or 0.0, reverse=True)[:5]

    open_mtm_values = [latest_open_mark(record) for record in open_records]
    open_mtm_values = [value for value in open_mtm_values if value is not None]
    open_mtm = round(sum(open_mtm_values), 2) if open_mtm_values else None

    lifecycle_7d = windows["7d"]["pnl"]
    delta_vs_polymarket = None
    if polymarket_weekly_pnl is not None:
        delta_vs_polymarket = round(lifecycle_7d - polymarket_weekly_pnl, 2)

    close_reason_counts = Counter(record_close_reason(record) for record in recent7)

    status = "needs_wallet_reconciliation"
    if polymarket_weekly_pnl is None:
        status = "wallet_pnl_missing"
    elif abs(delta_vs_polymarket or 0.0) <= 1.0:
        status = "aligned_enough"

    return {
        "generated_at": now.replace(microsecond=0).isoformat(),
        "status": status,
        "source": {
            "records": len(records),
            "real_closed": len(closed),
            "open": len(open_records),
            "pending_exit": len(pending_exit),
            "excluded_legacy_unresolved": len(excluded_legacy),
            "closed_without_pnl": len(no_pnl_closed),
        },
        "windows": windows,
        "open_mtm_estimate": open_mtm,
        "resolution_batch_7d": resolution_batch_stats,
        "polymarket_weekly_pnl": polymarket_weekly_pnl,
        "delta_lifecycle7d_minus_polymarket": delta_vs_polymarket,
        "recent7_close_reasons": dict(close_reason_counts),
        "groups": grouped,
        "top_losses": [format_trade_row(record) for record in top_losses],
        "top_wins": [format_trade_row(record) for record in top_wins],
    }


def format_trade_row(record: dict):
    pnl = record_pnl(record)
    return {
        "closed_at": record_closed_at(record).isoformat() if record_closed_at(record) else "",
        "city": str(record.get("city") or "?"),
        "side": str(record.get("side") or "?").upper(),
        "condition": str(record.get("condition") or "?"),
        "pnl": round(pnl, 2) if pnl is not None else None,
        "exit": record_close_reason(record),
        "label": str(record.get("label") or record.get("question") or record.get("id") or "")[:120],
    }


def money(value):
    if value is None:
        return "n/d"
    return f"${value:+.2f}"


def build_message(summary: dict) -> str:
    w = summary["windows"]
    source = summary["source"]
    pm_pnl = summary.get("polymarket_weekly_pnl")
    delta = summary.get("delta_lifecycle7d_minus_polymarket")
    status = summary.get("status")
    resolution_batch = summary.get("resolution_batch_7d") or {}
    if status == "aligned_enough":
        headline = "LECTURA: lifecycle y Polymarket estan razonablemente alineados."
    elif status == "needs_wallet_reconciliation":
        headline = "LECTURA: hay divergencia material entre lifecycle y Polymarket."
    else:
        headline = "LECTURA: falta P/L wallet Polymarket para reconciliacion completa."

    worst_city = (summary["groups"].get("city") or [{}])[0]
    worst_condition = (summary["groups"].get("condition") or [{}])[0]
    worst_exit = (summary["groups"].get("exit") or [{}])[0]

    lines = [
        "<b>P/L Reconciliation - lectura diaria</b>",
        "",
        f"<b>{headline}</b>",
        "",
        "<b>Bot lifecycle realizado</b>",
        f"- 7d: {money(w['7d']['pnl'])} | WR {w['7d']['wr']:.1f}% ({w['7d']['wins']}/{w['7d']['n']})",
        f"- 30d: {money(w['30d']['pnl'])} | WR {w['30d']['wr']:.1f}% ({w['30d']['wins']}/{w['30d']['n']})",
        f"- Ultimos 20: {money(w['last20']['pnl'])} | WR {w['last20']['wr']:.1f}% ({w['last20']['wins']}/{w['last20']['n']})",
        "",
        "<b>Wallet / Polymarket</b>",
    ]
    if pm_pnl is None:
        lines.append("- P/L 1W Polymarket: n/d en runtime. La captura/dashboard sigue siendo fuente de verdad del dinero.")
    else:
        lines.append(f"- P/L 1W Polymarket: {money(pm_pnl)}")
        lines.append(f"- Delta lifecycle_7d - Polymarket_1W: {money(delta)}")
    lines += [
        "",
        "<b>Semantica</b>",
        f"- Real closed usados: {source['real_closed']}",
        f"- Open: {source['open']} | pending_exit: {source['pending_exit']}",
        f"- Excluidos legacy_unresolved: {source['excluded_legacy_unresolved']} | closed sin P/L: {source['closed_without_pnl']}",
        f"- Batch market_resolved antiguo dentro de 7d: {money(resolution_batch.get('pnl'))} n={resolution_batch.get('n', 0)}",
    ]
    if summary.get("open_mtm_estimate") is not None:
        lines.append(f"- MTM abierto estimado: {money(summary['open_mtm_estimate'])}")
    lines += [
        "",
        "<b>Peores buckets 7d</b>",
        f"- Ciudad: {worst_city.get('key', 'n/d')} {money(worst_city.get('pnl'))} n={worst_city.get('n', 0)} WR={worst_city.get('wr', 0.0):.1f}%",
        f"- Condicion: {worst_condition.get('key', 'n/d')} {money(worst_condition.get('pnl'))} n={worst_condition.get('n', 0)} WR={worst_condition.get('wr', 0.0):.1f}%",
        f"- Exit: {worst_exit.get('key', 'n/d')} {money(worst_exit.get('pnl'))} n={worst_exit.get('n', 0)} WR={worst_exit.get('wr', 0.0):.1f}%",
        "",
        "<b>Tarea para Codex</b>",
    ]
    if status == "needs_wallet_reconciliation":
        lines += [
            "1. No tocar trading core.",
            "2. Separar P/L realizado por transaccion reciente de batch market_resolved antiguo.",
            "3. Auditar fills/redeems/mark-to-market que expliquen el delta wallet vs lifecycle.",
            "4. Si el wallet sigue negativo pero lifecycle positivo, priorizar reconciliacion de caja antes de nuevas reglas.",
        ]
    elif resolution_batch.get("n", 0):
        lines += [
            "1. No tocar trading core.",
            "2. No interpretar el P/L 7d como mejora limpia: contiene batch market_resolved antiguo.",
            "3. Si el wallet sigue negativo pero lifecycle positivo, priorizar reconciliacion de caja antes de nuevas reglas.",
        ]
    elif status == "aligned_enough":
        lines += [
            "1. No tocar trading core.",
            "2. Usar los peores buckets 7d para decidir si hace falta una auditoria acotada.",
            "3. No subir bankroll salvo que readiness y P/L wallet tambien lo permitan.",
        ]
    else:
        lines += [
            "1. No tocar trading core.",
            "2. Comparar esta lectura con el P/L 1W visible en Polymarket.",
            "3. Si Polymarket 1W < 0 y lifecycle 7d >= 0, abrir auditoria de reconciliacion wallet/fills.",
        ]
    return "\n".join(lines)


def build_markdown(summary: dict, message: str) -> str:
    lines = [
        "# P/L Reconciliation Readout - latest",
        "",
        f"Generated: `{summary['generated_at']}`",
        f"Status: `{summary['status']}`",
        "",
        "## Telegram message",
        "",
        "```html",
        message,
        "```",
        "",
        "## Top losses 7d",
        "",
        "| Closed | City | Side | Condition | Exit | PnL |",
        "|---|---|---|---|---|---:|",
    ]
    for row in summary["top_losses"]:
        lines.append(
            f"| {row['closed_at'][:10]} | {row['city']} | {row['side']} | "
            f"{row['condition']} | {row['exit']} | {money(row['pnl'])} |"
        )
    lines += [
        "",
        "## Top wins 7d",
        "",
        "| Closed | City | Side | Condition | Exit | PnL |",
        "|---|---|---|---|---|---:|",
    ]
    for row in summary["top_wins"]:
        lines.append(
            f"| {row['closed_at'][:10]} | {row['city']} | {row['side']} | "
            f"{row['condition']} | {row['exit']} | {money(row['pnl'])} |"
        )
    lines += [
        "",
        "## Machine summary",
        "",
        "```json",
        json.dumps(summary, indent=2, ensure_ascii=False),
        "```",
    ]
    return "\n".join(lines) + "\n"


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


def should_send(state: dict, summary: dict, now: datetime, force: bool):
    if force:
        return True, "force"
    today = now.date().isoformat()
    if state.get("last_sent_date") == today:
        return False, "already_sent_today"
    if summary["status"] == "needs_wallet_reconciliation":
        return True, "wallet_delta"
    return True, "daily_readout"


def main():
    configure_stdout()
    args = parse_args()
    now = datetime.now(timezone.utc)
    lifecycle_path = resolve_lifecycle_path(args.lifecycle_file)
    data = load_json(lifecycle_path)
    records = data.get("records", []) if isinstance(data, dict) else []
    summary = summarize_records(records, now, args.polymarket_weekly_pnl)
    message = build_message(summary)
    markdown = build_markdown(summary, message)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(message)

    if not args.dry_run:
        ensure_parent(Path(args.md_output)).write_text(markdown, encoding="utf-8")

    state_path = Path(args.state_file)
    state = load_json(state_path, required=False) or {}
    send_now, reason = should_send(state, summary, now, args.force)
    telegram_result = {"sent": False, "reason": "not_attempted"}
    if not args.dry_run and send_now:
        telegram_result = send_telegram(message)

    if not args.dry_run:
        state.update({
            "last_run_at": now.replace(microsecond=0).isoformat(),
            "last_status": summary["status"],
            "last_lifecycle_7d_pnl": summary["windows"]["7d"]["pnl"],
        })
        if send_now and telegram_result.get("reason") in {"sent", "missing_telegram_env"}:
            state["last_sent_date"] = now.date().isoformat()
            state["last_sent_at"] = now.replace(microsecond=0).isoformat()
        ensure_parent(state_path).write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    result = {
        "lifecycle_file_used": str(lifecycle_path),
        "md_output": str(args.md_output),
        "should_send": send_now,
        "reason": reason,
        "telegram_result": telegram_result,
        "status": summary["status"],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
