#!/usr/bin/env python3
"""Retrospective de stop-loss con estado anti-spam y salida Telegram."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIFECYCLE_FILE = REPO_ROOT / "data" / "trade_lifecycle.json"
DEFAULT_LIFECYCLE_FALLBACK = REPO_ROOT / "data" / "runtime_import" / "trade_lifecycle.json"
DEFAULT_STATE_FILE = REPO_ROOT / "data" / "sl_retrospective_state.json"
TARGET_SAMPLE_SIZE = 16
PRELIMINARY_THRESHOLD = 8
FINAL_THRESHOLD = 12


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analiza retrospectivamente si los SL cortaron posiciones correctas."
    )
    parser.add_argument("--lifecycle-file", default=str(DEFAULT_LIFECYCLE_FILE))
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    parser.add_argument("--dry-run", action="store_true")
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


def load_json(path: Path, required: bool = True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required file: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_sl_rows(lifecycle_path: Path):
    payload = load_json(lifecycle_path)
    records = payload.get("records", []) if isinstance(payload, dict) else []
    rows = []
    for record in records:
        if not isinstance(record, dict):
            continue
        close_context = record.get("close_context") or {}
        if close_context.get("close_reason") != "stop_loss":
            continue
        post_exit = record.get("post_exit_analysis") or {}
        max_price = as_float(post_exit.get("max_price_after_close"))
        min_price = as_float(post_exit.get("min_price_after_close"))
        upside = as_float(post_exit.get("upside_left_cash_peak"))
        pnl_cash = as_float(close_context.get("pnl_cash"))
        close_shares = as_float(close_context.get("close_shares"))
        close_price = as_float(close_context.get("close_price"))
        market_seen = bool(post_exit.get("market_seen_after_close"))
        reached_98 = bool(post_exit.get("reached_98_after_close"))
        if reached_98 or (max_price is not None and max_price >= 0.85):
            verdict = "RIGHT"
        elif market_seen and max_price is not None and max_price <= 0.15:
            verdict = "WRONG"
        else:
            verdict = "UNKNOWN"
        pnl_without_sl_best = None
        pnl_without_sl_worst = None
        delta_vs_sl_best = None
        delta_vs_sl_worst = None
        if None not in (pnl_cash, close_price, close_shares, max_price):
            delta_vs_sl_best = round((max_price - close_price) * close_shares, 2)
            pnl_without_sl_best = round(pnl_cash + delta_vs_sl_best, 2)
        if None not in (pnl_cash, close_price, close_shares, min_price):
            delta_vs_sl_worst = round((min_price - close_price) * close_shares, 2)
            pnl_without_sl_worst = round(pnl_cash + delta_vs_sl_worst, 2)
        rows.append(
            {
                "label": record.get("label") or record.get("question") or "Unknown",
                "side": record.get("side") or "?",
                "avg_entry_price": as_float(record.get("avg_entry_price")),
                "close_price": close_price,
                "pnl_pct": as_float(close_context.get("pnl_pct")),
                "pnl_cash_with_sl": pnl_cash,
                "close_shares": close_shares,
                "closed_at": record.get("closed_at"),
                "verdict": verdict,
                "reached_98_after_close": reached_98,
                "max_price_after_close": max_price,
                "min_price_after_close": min_price,
                "market_seen_after_close": market_seen,
                "upside_left_cash_peak": upside,
                "pnl_without_sl_best": pnl_without_sl_best,
                "pnl_without_sl_worst": pnl_without_sl_worst,
                "delta_vs_sl_best": delta_vs_sl_best,
                "delta_vs_sl_worst": delta_vs_sl_worst,
            }
        )
    rows.sort(key=lambda row: str(row.get("closed_at") or ""), reverse=True)
    return rows


def summarize(rows: list[dict]):
    n_right = sum(1 for row in rows if row["verdict"] == "RIGHT")
    n_wrong = sum(1 for row in rows if row["verdict"] == "WRONG")
    n_unknown = sum(1 for row in rows if row["verdict"] == "UNKNOWN")
    n_resolved = n_right + n_wrong
    accuracy_pct = (n_right / n_resolved * 100.0) if n_resolved else None
    cash_rows = [
        row for row in rows
        if row["verdict"] == "RIGHT" and row.get("upside_left_cash_peak") is not None
    ]
    cash_lost = round(sum(row["upside_left_cash_peak"] for row in cash_rows), 2)
    false_exit_rows = [
        row for row in rows
        if row["verdict"] == "RIGHT"
        and row.get("pnl_cash_with_sl") is not None
        and row.get("pnl_without_sl_best") is not None
    ]
    protected_rows = [
        row for row in rows
        if row["verdict"] == "WRONG"
        and row.get("pnl_cash_with_sl") is not None
        and row.get("pnl_without_sl_best") is not None
    ]
    threshold_preliminary = n_resolved >= PRELIMINARY_THRESHOLD
    threshold_final = n_resolved >= FINAL_THRESHOLD
    verdict_brief = "acumulando datos"
    if threshold_preliminary:
        if accuracy_pct is not None and accuracy_pct >= 60:
            verdict_brief = "SL corta posiciones correctas"
        elif accuracy_pct is not None and accuracy_pct < 40:
            verdict_brief = "SL funciona correctamente"
        else:
            verdict_brief = "datos mixtos"
    verdict_final = verdict_brief + " (firme)" if threshold_final else ""
    return {
        "n_right": n_right,
        "n_wrong": n_wrong,
        "n_unknown": n_unknown,
        "n_resolved": n_resolved,
        "accuracy_pct": accuracy_pct,
        "cash_lost_by_sl": cash_lost,
        "cash_rows": cash_rows,
        "false_exit_rows": false_exit_rows,
        "protected_rows": protected_rows,
        "false_exit_with_sl_total": round(sum(row["pnl_cash_with_sl"] for row in false_exit_rows), 2),
        "false_exit_without_sl_best_total": round(sum(row["pnl_without_sl_best"] for row in false_exit_rows), 2),
        "protected_with_sl_total": round(sum(row["pnl_cash_with_sl"] for row in protected_rows), 2),
        "protected_without_sl_best_total": round(sum(row["pnl_without_sl_best"] for row in protected_rows), 2),
        "threshold_preliminary": threshold_preliminary,
        "threshold_final": threshold_final,
        "preliminary_verdict": verdict_brief if threshold_preliminary else "",
        "final_verdict": verdict_final,
    }


def build_message(summary: dict):
    n_resolved = summary["n_resolved"]
    n_right = summary["n_right"]
    n_wrong = summary["n_wrong"]
    n_unknown = summary["n_unknown"]
    accuracy_pct = summary["accuracy_pct"]

    if n_resolved == 0:
        return "🔍 SL Retrospective — acumulando datos\nAún no hay SLs resueltos para analizar."

    false_exit_helped = round(
        summary["false_exit_without_sl_best_total"] - summary["false_exit_with_sl_total"],
        2,
    )
    protected_saved = round(
        summary["protected_with_sl_total"] - summary["protected_without_sl_best_total"],
        2,
    )

    if n_resolved < PRELIMINARY_THRESHOLD:
        lines = [
            "🔍 SL Retrospective",
            f"Resueltos: {n_resolved}/{TARGET_SAMPLE_SIZE} — faltan {PRELIMINARY_THRESHOLD - n_resolved} para conclusión preliminar",
            f"🚫 Falsas salidas por SL: {n_right}",
            f"🛡️ SL correctos: {n_wrong}",
        ]
        if summary["false_exit_rows"]:
            lines.extend(
                [
                    "",
                    "En las falsas salidas ya confirmadas:",
                    f"• Con SL: {summary['false_exit_with_sl_total']:+.2f}$",
                    f"• Sin SL (mejor precio visto después): {summary['false_exit_without_sl_best_total']:+.2f}$",
                    f"• Diferencia atribuible al SL: {false_exit_helped:+.2f}$",
                ]
            )
        return "\n".join(lines)

    wrong_pct = 100.0 - (accuracy_pct or 0.0)
    lines = [
        "🔍 SL Retrospective — ¿Cortamos bien o mal?",
        "",
        f"📊 Resueltos: {n_resolved}/{TARGET_SAMPLE_SIZE} SLs",
        f"🚫 Falsas salidas por SL: {n_right} ({accuracy_pct:.0f}%)",
        f"🛡️ SL correctos: {n_wrong} ({wrong_pct:.0f}%)",
        f"⏳ Pendientes: {n_unknown}",
        "",
    ]

    if summary["false_exit_rows"]:
        lines.append("💸 Impacto de las falsas salidas ya confirmadas:")
        lines.append(f"  • Con SL: {summary['false_exit_with_sl_total']:+.2f}$")
        lines.append(
            f"  • Sin SL (mejor precio visto después): {summary['false_exit_without_sl_best_total']:+.2f}$"
        )
        lines.append(f"  • Diferencia atribuible al SL: {false_exit_helped:+.2f}$")
        for row in summary["false_exit_rows"]:
            lines.append(
                f"  • {row['label']}: con SL {row['pnl_cash_with_sl']:+.2f}$ → "
                f"sin SL {row['pnl_without_sl_best']:+.2f}$"
            )
        lines.append("")

    if summary["protected_rows"]:
        lines.append("🛡️ En los SL correctos ya medidos:")
        lines.append(f"  • Con SL: {summary['protected_with_sl_total']:+.2f}$")
        lines.append(
            f"  • Sin SL (mejor precio visto después): {summary['protected_without_sl_best_total']:+.2f}$"
        )
        lines.append(f"  • Pérdida adicional evitada por el SL: {protected_saved:+.2f}$")
        for row in summary["protected_rows"]:
            lines.append(
                f"  • {row['label']}: con SL {row['pnl_cash_with_sl']:+.2f}$ → "
                f"sin SL {row['pnl_without_sl_best']:+.2f}$"
            )
        lines.append("")

    if accuracy_pct is not None and accuracy_pct >= 60 and summary["threshold_preliminary"]:
        lines.append("⚠️ VEREDICTO PRELIMINAR: EL SL ESTÁ CORTANDO POSICIONES CORRECTAS")
        lines.append("→ Revisar gestión de posiciones en checkpoint Apr 28")
    elif accuracy_pct is not None and accuracy_pct < 40 and summary["threshold_preliminary"]:
        lines.append("✅ VEREDICTO PRELIMINAR: EL SL ESTÁ FUNCIONANDO CORRECTAMENTE")
    else:
        lines.append("📊 VEREDICTO: datos mixtos, seguir acumulando")

    if summary["threshold_final"]:
        lines.append("")
        lines.append("🚨 CONCLUSIÓN FIRME — tenemos datos suficientes para tomar acción")

    return "\n".join(lines)


def should_send(state: dict, summary: dict, now: datetime):
    last_sent_at = parse_dt(state.get("last_sent_at"))
    prev_n_resolved = int(state.get("n_resolved_last", -1) or -1)
    same_resolved = prev_n_resolved == summary["n_resolved"]
    reminder_due = last_sent_at is None or now - last_sent_at >= timedelta(hours=24)
    threshold_reached_first_time = prev_n_resolved < PRELIMINARY_THRESHOLD <= summary["n_resolved"]

    if threshold_reached_first_time:
        return True, "threshold_reached_first_time"
    if not same_resolved:
        return True, "new_resolved_data"
    if reminder_due:
        return True, "daily_reminder"
    return False, "no_change"


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


def print_table(rows: list[dict]):
    print("SL retrospective rows:")
    header = (
        f"{'VERDICT':<8} {'SIDE':<4} {'ENTRY':>6} {'CLOSE':>6} {'PNL%':>6} "
        f"{'WITH_SL':>9} {'NO_SL':>9} {'MAX':>6} LABEL"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        entry = f"{row['avg_entry_price']:.2f}" if row["avg_entry_price"] is not None else "n/d"
        close = f"{row['close_price']:.2f}" if row["close_price"] is not None else "n/d"
        pnl = f"{row['pnl_pct']:.0f}" if row["pnl_pct"] is not None else "n/d"
        pnl_with_sl = (
            f"{row['pnl_cash_with_sl']:+.2f}"
            if row["pnl_cash_with_sl"] is not None
            else "n/d"
        )
        pnl_without_sl = (
            f"{row['pnl_without_sl_best']:+.2f}"
            if row["pnl_without_sl_best"] is not None
            else "n/d"
        )
        max_price = (
            f"{row['max_price_after_close']:.2f}"
            if row["max_price_after_close"] is not None
            else "n/d"
        )
        print(
            f"{row['verdict']:<8} {row['side']:<4} {entry:>6} {close:>6} {pnl:>6} "
            f"{pnl_with_sl:>9} {pnl_without_sl:>9} {max_price:>6} {row['label']}"
        )


def main():
    configure_stdout()
    args = parse_args()
    lifecycle_path = resolve_lifecycle_path(args.lifecycle_file)
    rows = load_sl_rows(lifecycle_path)
    summary = summarize(rows)
    message = build_message(summary)
    state_path = Path(args.state_file)
    state = load_json(state_path, required=False) or {}
    now = datetime.now(timezone.utc).replace(microsecond=0)

    print_table(rows)
    print("")
    print("Telegram message:")
    print(message)
    print("")

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "lifecycle_file_used": str(lifecycle_path),
                    "summary": summary,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    send_now, reason = should_send(state, summary, now)
    telegram_result = {"sent": False, "reason": "not_attempted"}
    if send_now:
        telegram_result = send_telegram(message)

    state.update(
        {
            "last_run_at": now.isoformat(),
            "preliminary_verdict": summary["preliminary_verdict"],
            "final_verdict": summary["final_verdict"],
        }
    )
    if send_now and telegram_result.get("reason") in {"sent", "missing_telegram_env"}:
        state["last_sent_at"] = now.isoformat()
        state["n_resolved_last"] = summary["n_resolved"]

    ensure_parent(state_path).write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "lifecycle_file_used": str(lifecycle_path),
                "should_send": send_now,
                "reason": reason,
                "telegram_result": telegram_result,
                "summary": summary,
                "state_file": str(state_path),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
