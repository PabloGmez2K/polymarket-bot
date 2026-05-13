#!/usr/bin/env python3
"""Unified read-only SL_intra case readout.

This CLI joins local/runtime evidence from trade_lifecycle, the SL_intra
hazard monitor, INTRA-REEVAL shadow state, guard skips, and skip_log. It is
LOG_ONLY: it never imports bot.py, writes runtime files, sends Telegram, or
changes trading behavior.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY readout: no DB writes, no Telegram, no BANKROLL, no Fase C, "
    "no BUY/SELL/SKIP, no SL/guard/INTRA runtime changes."
)


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read_json(path: Path) -> tuple[Any, str | None]:
    if not path.exists():
        return {}, "missing"
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            return json.load(fh), None
    except json.JSONDecodeError as exc:
        return {}, f"invalid_json:{exc.msg}"
    except OSError as exc:
        return {}, f"read_error:{exc.__class__.__name__}"


def read_jsonl(path: Path, limit: int | None = None) -> tuple[list[dict[str, Any]], str | None]:
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            for line in fh:
                text = line.strip()
                if not text:
                    continue
                try:
                    loaded = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(loaded, dict):
                    rows.append(loaded)
    except OSError as exc:
        return [], f"read_error:{exc.__class__.__name__}"
    if limit is not None and len(rows) > limit:
        rows = rows[-limit:]
    return rows, None


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def lifecycle_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        records = payload.get("records") or payload.get("trades") or []
    else:
        records = payload
    return [row for row in records if isinstance(row, dict)] if isinstance(records, list) else []


def infer_condition(question: Any) -> str | None:
    text = str(question or "").lower()
    if not text:
        return None
    if re.search(r"\bbetween\b|\brange\b", text):
        return "range"
    if re.search(r"\bor higher\b|\bat or above\b|\bat least\b", text):
        return "at_or_above"
    if re.search(r"\bor below\b|\bat or below\b|\bat most\b", text):
        return "at_or_below"
    if re.search(r"\bbe\s+-?\d+(?:\.\d+)?\s*(?:deg|degrees|c|f|°)", text):
        return "exact"
    return None


def infer_date_from_question(question: Any, year_hint: int | None = None) -> str | None:
    text = str(question or "")
    match = re.search(
        r"\b("
        + "|".join(re.escape(name) for name in MONTHS)
        + r")\s+(\d{1,2})\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    month = MONTHS[match.group(1).lower()]
    day = int(match.group(2))
    year = year_hint or date.today().year
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def record_question(record: dict[str, Any]) -> str:
    entry = record.get("entry_context") or {}
    close = record.get("close_context") or {}
    return str(
        first_present(
            record.get("question"),
            entry.get("question"),
            close.get("question"),
            record.get("title"),
            record.get("label"),
        )
        or ""
    )


def record_date(record: dict[str, Any], year_hint: int | None = None) -> str | None:
    entry = record.get("entry_context") or {}
    for key in ("date", "date_iso", "target_date", "market_date"):
        value = first_present(record.get(key), entry.get(key))
        if value:
            return str(value)[:10]
    return infer_date_from_question(record_question(record), year_hint=year_hint)


def record_city(record: dict[str, Any]) -> str:
    entry = record.get("entry_context") or {}
    return str(first_present(record.get("city"), entry.get("city")) or "")


def record_side(record: dict[str, Any]) -> str:
    entry = record.get("entry_context") or {}
    return str(first_present(record.get("side"), record.get("outcome"), entry.get("side"), entry.get("outcome")) or "")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def token_matches(row: dict[str, Any], token_id: str) -> bool:
    target = str(token_id or "").strip()
    if not target:
        return False
    for key in ("token_id", "asset", "asset_id"):
        if str(row.get(key, "") or "").strip() == target:
            return True
    return False


def loose_case_match(row: dict[str, Any], *, city: str, target_date: str | None, title: str = "") -> bool:
    city_norm = normalize_text(city)
    if city_norm:
        row_city = normalize_text(first_present(row.get("city"), row.get("market_city")))
        row_title = normalize_text(first_present(row.get("title"), row.get("question"), row.get("label")))
        if row_city != city_norm and city_norm not in row_title:
            return False
    if target_date:
        for key in ("date", "date_iso", "target_date", "market_date"):
            if str(row.get(key, "") or "")[:10] == target_date:
                return True
        inferred = infer_date_from_question(first_present(row.get("title"), row.get("question")), year_hint=int(target_date[:4]))
        if inferred == target_date:
            return True
        return False
    if title:
        row_title = normalize_text(first_present(row.get("title"), row.get("question"), row.get("label")))
        return bool(row_title and row_title == normalize_text(title))
    return bool(city_norm)


def find_lifecycle_cases(
    records: list[dict[str, Any]],
    *,
    token_id: str | None,
    city: str | None,
    target_date: str | None,
    side: str | None,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    year_hint = int(target_date[:4]) if target_date else None
    for record in records:
        if token_id and not token_matches(record, token_id):
            continue
        if city and normalize_text(record_city(record)) != normalize_text(city):
            continue
        if target_date and record_date(record, year_hint=year_hint) != target_date:
            continue
        if side and normalize_text(record_side(record)) != normalize_text(side):
            continue
        matches.append(record)
    return matches


def load_sources(data_dir: Path, skip_log_limit: int | None) -> dict[str, Any]:
    sources: dict[str, Any] = {"warnings": []}
    for name in (
        "trade_lifecycle.json",
        "sl_intra_hazard_monitor_audit.json",
        "intra_reeval_state.json",
        "sl_intra_guard_audit.json",
    ):
        payload, err = read_json(data_dir / name)
        sources[name] = payload
        if err:
            sources["warnings"].append(f"{name}:{err}")
    skip_rows, skip_err = read_jsonl(data_dir / "skip_log.jsonl", limit=skip_log_limit)
    sources["skip_log.jsonl"] = skip_rows
    if skip_err:
        sources["warnings"].append(f"skip_log.jsonl:{skip_err}")
    return sources


def hazard_events(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("events") or []
    else:
        rows = payload
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def intra_triggers(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    shadow = payload.get("shadow_log") or {}
    rows = shadow.get("triggers") if isinstance(shadow, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def guard_skips(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("skips") or payload.get("events") or []
    else:
        rows = payload
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def matching_rows(
    rows: list[dict[str, Any]],
    *,
    token_id: str,
    city: str,
    target_date: str | None,
    title: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if token_id and token_matches(row, token_id):
            out.append(row)
        elif loose_case_match(row, city=city, target_date=target_date, title=title):
            out.append(row)
    return out


def buy_count(record: dict[str, Any]) -> int | None:
    for key in ("buy_count", "n_buys"):
        value = record.get(key)
        if isinstance(value, int):
            return value
    buys = record.get("buys")
    if isinstance(buys, list):
        return len(buys)
    timeline = record.get("timeline")
    if isinstance(timeline, list):
        return sum(1 for row in timeline if isinstance(row, dict) and row.get("action") == "BUY")
    return None


def total_amount(record: dict[str, Any]) -> float | None:
    entry = record.get("entry_context") or {}
    return as_float(first_present(record.get("total_amount"), entry.get("total_amount"), entry.get("amount")))


def avg_entry_price(record: dict[str, Any]) -> float | None:
    entry = record.get("entry_context") or {}
    price = as_float(first_present(record.get("avg_entry_price"), record.get("entry_price"), entry.get("price")))
    if price is not None:
        return price
    amount = total_amount(record)
    shares = as_float(first_present(record.get("total_shares"), entry.get("shares")))
    if amount is not None and shares:
        return round(amount / shares, 4)
    return None


def pnl_cash(record: dict[str, Any]) -> float | None:
    close = record.get("close_context") or {}
    return as_float(first_present(record.get("pnl_cash"), close.get("pnl_cash"), record.get("realized_pnl")))


def pnl_pct(record: dict[str, Any]) -> float | None:
    close = record.get("close_context") or {}
    cash = pnl_cash(record)
    amount = total_amount(record)
    if cash is not None and amount:
        return round((cash / amount) * 100.0, 1)
    explicit = as_float(first_present(record.get("pnl_pct"), close.get("pnl_pct")))
    if explicit is not None:
        return explicit
    return None


def close_price(record: dict[str, Any]) -> float | None:
    close = record.get("close_context") or {}
    price = as_float(first_present(record.get("close_price"), close.get("close_price")))
    if price is not None:
        return price
    action = close_action(record)
    if action == "RESOLVED_WIN":
        return 1.0
    if action == "LOSS_TOTAL":
        return 0.0
    return None


def close_action(record: dict[str, Any]) -> str:
    close = record.get("close_context") or {}
    return str(first_present(record.get("close_action"), close.get("close_action")) or "")


def close_reason(record: dict[str, Any]) -> str:
    close = record.get("close_context") or {}
    return str(first_present(record.get("close_reason"), close.get("close_reason")) or "")


def final_status(record: dict[str, Any]) -> str:
    return str(record.get("status") or "")


def is_final_win(record: dict[str, Any]) -> bool:
    action = close_action(record)
    cash = pnl_cash(record)
    return action == "RESOLVED_WIN" or (cash is not None and cash > 0)


def is_open(record: dict[str, Any]) -> bool:
    return final_status(record) in {"open", "pending_exit", "exit_failed"} or not close_action(record)


def min_numeric(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> float | None:
    values: list[float] = []
    for row in rows:
        for key in keys:
            value = as_float(row.get(key))
            if value is not None:
                values.append(value)
                break
    return min(values) if values else None


def classify_case(record: dict[str, Any], hazards: list[dict[str, Any]], reevals: list[dict[str, Any]]) -> str:
    if not record:
        return "INSUFFICIENT_DATA"
    if is_open(record):
        return "STILL_OPEN"
    final_win = is_final_win(record)
    has_hazard = bool(hazards)
    would_sell = any(row.get("would_sell") is True for row in reevals)
    if would_sell and final_win:
        return "REEVAL_WOULD_SELL_BUT_FINAL_WIN"
    if would_sell:
        for row in reevals:
            outcome = row.get("outcome_review") or {}
            if outcome.get("classification") == "GOOD_SHADOW":
                return "REEVAL_GOOD_SHADOW"
            if outcome.get("classification") == "BAD_SHADOW":
                return "REEVAL_BAD_SHADOW"
        trigger_prices = [as_float(row.get("cur_price")) for row in reevals]
        trigger_prices = [value for value in trigger_prices if value is not None]
        final_price = close_price(record)
        if final_price is not None and trigger_prices:
            if final_price < min(trigger_prices):
                return "REEVAL_GOOD_SHADOW"
            if final_price > max(trigger_prices):
                return "REEVAL_BAD_SHADOW"
    if has_hazard and final_win:
        return "HAZARD_OBSERVED_WIN"
    if has_hazard and not final_win:
        return "HAZARD_OBSERVED_LOSS"
    return "INSUFFICIENT_DATA"


def build_case(record: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    entry = record.get("entry_context") or {}
    token_id = str(record.get("token_id") or record.get("asset") or "")
    city = record_city(record)
    title = record_question(record)
    target_date = record_date(record)
    hazards = matching_rows(
        hazard_events(sources.get("sl_intra_hazard_monitor_audit.json")),
        token_id=token_id,
        city=city,
        target_date=target_date,
        title=title,
    )
    reevals = matching_rows(
        intra_triggers(sources.get("intra_reeval_state.json")),
        token_id=token_id,
        city=city,
        target_date=target_date,
        title=title,
    )
    guards = matching_rows(
        guard_skips(sources.get("sl_intra_guard_audit.json")),
        token_id=token_id,
        city=city,
        target_date=target_date,
        title=title,
    )
    skips = matching_rows(
        sources.get("skip_log.jsonl") or [],
        token_id=token_id,
        city=city,
        target_date=target_date,
        title=title,
    )

    latest_reeval = reevals[-1] if reevals else {}
    hazard_tiers = sorted({str(row.get("tier")) for row in hazards if row.get("tier")})
    max_drawdown = min_numeric(hazards + guards + reevals, ("pct_pnl", "pct_pnl_at_skip", "pnl_pct"))
    entry_edge = as_float(first_present(record.get("entry_edge_pct"), entry.get("edge_pct")))
    latest_edge = as_float(first_present(latest_reeval.get("fresh_edge_pct"), record.get("latest_entry_edge_pct")))
    edge_delta = None
    if latest_edge is not None and entry_edge is not None:
        edge_delta = round(latest_edge - entry_edge, 2)

    return {
        "token_id": token_id or None,
        "city": city or None,
        "title": title or None,
        "question": title or None,
        "condition": first_present(record.get("condition"), entry.get("condition"), infer_condition(title)),
        "date": target_date,
        "side": record_side(record) or None,
        "buy_count": buy_count(record),
        "total_amount": total_amount(record),
        "avg_entry_price": avg_entry_price(record),
        "entry_edge": entry_edge,
        "latest_entry_edge": latest_edge,
        "trader_confirmed": first_present(
            record.get("trader_confirmed"),
            entry.get("trader_confirmed"),
            entry.get("quality_trader_confirmed"),
        ),
        "hazard_tiers_detected": hazard_tiers,
        "hazard_event_count": len(hazards),
        "guard_skip_count": len(guards),
        "skip_log_count": len(skips),
        "max_drawdown_observed": max_drawdown,
        "intra_reeval": {
            "would_sell": bool(reevals and any(row.get("would_sell") is True for row in reevals)),
            "trigger_count": len(reevals),
            "price_at_would_sell": as_float(latest_reeval.get("cur_price")) if latest_reeval else None,
            "edge_now": latest_edge,
            "edge_entry": entry_edge,
            "edge_now_vs_entry": edge_delta,
            "latest_outcome_review": latest_reeval.get("outcome_review") if isinstance(latest_reeval, dict) else None,
        },
        "final_status": final_status(record) or None,
        "close_action": close_action(record) or None,
        "close_reason": close_reason(record) or None,
        "real_pnl_cash": pnl_cash(record),
        "real_pnl_pct": pnl_pct(record),
        "classification": classify_case(record, hazards, reevals),
        "evidence": {
            "hazard_events": hazards,
            "intra_reeval_triggers": reevals,
            "guard_skips": guards,
            "skip_log_rows": skips[-20:],
        },
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = Path(args.data_dir)
    sources = load_sources(data_dir, skip_log_limit=args.skip_log_limit)
    records = lifecycle_records(sources.get("trade_lifecycle.json"))
    cases = find_lifecycle_cases(
        records,
        token_id=args.token_id,
        city=args.city,
        target_date=args.date,
        side=args.side,
    )
    if not cases and (args.city or args.date):
        sources["warnings"].append("trade_lifecycle:no_matching_case")
    case_payloads = [build_case(record, sources) for record in cases]
    return {
        "status": "ok" if case_payloads else "no_matching_case",
        "verdict": "NO_EXISTING_TOOL_PATCH_READY",
        "data_dir": str(data_dir),
        "filters": {
            "token_id": args.token_id,
            "city": args.city,
            "date": args.date,
            "side": args.side,
        },
        "case_count": len(case_payloads),
        "cases": case_payloads,
        "warnings": sources["warnings"],
        "disclaimer": LOG_ONLY_DISCLAIMER,
    }


def fmt_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "n/a"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SL_intra Case Readout",
        "",
        f"- status: `{report['status']}`",
        f"- verdict: `{report['verdict']}`",
        f"- case_count: `{report['case_count']}`",
        f"- scope: {report['disclaimer']}",
    ]
    warnings = report.get("warnings") or []
    if warnings:
        lines.append(f"- warnings: `{', '.join(warnings)}`")
    for idx, case in enumerate(report.get("cases") or [], start=1):
        lines.extend(
            [
                "",
                f"## Case {idx}: {fmt_value(case.get('city'))} {fmt_value(case.get('date'))} {fmt_value(case.get('side'))}",
                "",
                f"- token_id: `{fmt_value(case.get('token_id'))}`",
                f"- title: {fmt_value(case.get('title'))}",
                f"- condition: `{fmt_value(case.get('condition'))}`",
                f"- buy_count: `{fmt_value(case.get('buy_count'))}`",
                f"- total_amount: `{fmt_value(case.get('total_amount'))}`",
                f"- avg_entry_price: `{fmt_value(case.get('avg_entry_price'))}`",
                f"- entry_edge -> latest_edge: `{fmt_value(case.get('entry_edge'))}` -> `{fmt_value(case.get('latest_entry_edge'))}`",
                f"- trader_confirmed: `{fmt_value(case.get('trader_confirmed'))}`",
                f"- hazard_tiers_detected: `{fmt_value(case.get('hazard_tiers_detected'))}`",
                f"- max_drawdown_observed: `{fmt_value(case.get('max_drawdown_observed'))}`",
                f"- intra_reeval would_sell: `{fmt_value((case.get('intra_reeval') or {}).get('would_sell'))}`",
                f"- price_at_would_sell: `{fmt_value((case.get('intra_reeval') or {}).get('price_at_would_sell'))}`",
                f"- edge_now_vs_entry: `{fmt_value((case.get('intra_reeval') or {}).get('edge_now_vs_entry'))}`",
                f"- final_status: `{fmt_value(case.get('final_status'))}`",
                f"- close_action: `{fmt_value(case.get('close_action'))}`",
                f"- close_reason: `{fmt_value(case.get('close_reason'))}`",
                f"- real_pnl_cash: `{fmt_value(case.get('real_pnl_cash'))}`",
                f"- real_pnl_pct: `{fmt_value(case.get('real_pnl_pct'))}`",
                f"- classification: `{fmt_value(case.get('classification'))}`",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified read-only SL_intra case readout (LOG_ONLY).")
    parser.add_argument("--data-dir", default="data/runtime_import", help="Directory containing runtime JSON/JSONL artifacts.")
    parser.add_argument("--token-id", default="", help="Filter by token_id/asset.")
    parser.add_argument("--city", default="", help="Filter by city.")
    parser.add_argument("--date", default="", help="Filter by market date YYYY-MM-DD.")
    parser.add_argument("--side", default="", help="Optional side/outcome filter, e.g. YES or NO.")
    parser.add_argument("--skip-log-limit", type=int, default=50000, help="Max recent skip_log rows to scan.")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default).")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv)
    report = build_report(args)
    if args.markdown:
        print(render_markdown(report), end="")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] in {"ok", "no_matching_case"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
