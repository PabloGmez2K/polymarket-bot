#!/usr/bin/env python3
"""LOG_ONLY cohort intelligence report for weather signal families.

Reads existing runtime artifacts and emits manual review recommendations only.
It does not import bot.py, place orders, write state, send Telegram, or mutate DB.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
EXACT_NO_NEAR_THRESHOLD_C = 1.5
MIN_REVIEW_SAMPLE = 10
DIRECTIONAL_FORWARD_CAPTURE_START_UTC = "2026-05-26T16:15:11Z"
LIVE_SIDE_VISIBILITY_FORWARD_START_UTC = "2026-05-26T20:58:28Z"
VERDICTS = {
    "DATA_QUALITY_BLOCKER",
    "INSUFFICIENT_SAMPLE",
    "ACCUMULATING_FORWARD_EVIDENCE",
    "KEEP_SHADOW",
    "REVIEW_BLOCK_LIVE",
    "REVIEW_OPUS",
    "REVIEW_LIVE_COHORT_QUALITY",
    "REVIEW_LIVE_CONTAINMENT",
    "CANDIDATE_FOR_CANARY_REVIEW",
}
LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY: manual recommendations only. No BUY/SELL/SKIP, BANKROLL, sizing, "
    "guards, scheduler, whitelist, city modes, Fase C, env vars, or auto-promotion."
)


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build LOG_ONLY cohort performance recommendations.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--bot-evaluations", help="Path to bot_signal_evaluations.jsonl")
    parser.add_argument("--skip-log", help="Path to skip_log.jsonl")
    parser.add_argument("--resolutions", help="Path to blocked_signals_resolutions.jsonl")
    parser.add_argument("--trade-lifecycle", help="Path to trade_lifecycle.json")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    return parser.parse_args(argv)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc_timestamp(value: Any) -> datetime | None:
    text = normalize_text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def is_forward_directional_row(row: dict[str, Any]) -> bool:
    ts = parse_utc_timestamp(row.get("last_seen") or row.get("ts_utc"))
    start = parse_utc_timestamp(DIRECTIONAL_FORWARD_CAPTURE_START_UTC)
    return bool(ts and start and ts >= start)


def is_live_side_forward_row(row: dict[str, Any]) -> bool:
    ts = parse_utc_timestamp(row.get("last_seen") or row.get("ts_utc"))
    start = parse_utc_timestamp(LIVE_SIDE_VISIBILITY_FORWARD_START_UTC)
    return bool(ts and start and ts >= start and row.get("side_recorded") is True)


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_side(value: Any) -> str | None:
    text = normalize_text(value).upper()
    if text in {"YES", "Y"}:
        return "YES"
    if text in {"NO", "N"}:
        return "NO"
    return None


def normalize_condition(value: Any) -> str:
    text = normalize_text(value).lower()
    if text in {"at_or_above", "above", "directional_above"}:
        return "at_or_above"
    if text in {"at_or_below", "below", "directional_below"}:
        return "at_or_below"
    return text


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def parse_match_key(key: Any) -> dict[str, Any]:
    parts = normalize_text(key).split("|")
    if len(parts) < 5:
        return {}
    parsed: dict[str, Any] = {
        "city": parts[0],
        "date_iso": parts[1],
        "condition": normalize_condition(parts[2]),
        "unit": parts[4],
    }
    threshold = parts[3]
    if "-" in threshold:
        low, _, high = threshold.partition("-")
        parsed["threshold"] = as_float(low)
        parsed["threshold_high"] = as_float(high)
    else:
        parsed["threshold"] = as_float(threshold)
        parsed["threshold_high"] = None
    return parsed


def infer_threshold_from_text(value: Any) -> tuple[float | None, str | None]:
    text = normalize_text(value)
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*°?\s*([CF])\b", text, flags=re.IGNORECASE)
    if not match:
        return None, None
    return as_float(match.group(1)), match.group(2).upper()


def build_latest_index(rows: list[dict[str, Any]], key_names: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = ""
        for name in key_names:
            key = normalize_text(row.get(name))
            if key:
                break
        if key:
            index[key] = row
    return index


def build_skip_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        extras = row.get("extras") if isinstance(row.get("extras"), dict) else {}
        key = normalize_text(extras.get("qt_match_key")) or build_eval_key_from_row(row)
        if key:
            index[key] = row
    return index


def build_eval_key_from_row(row: dict[str, Any]) -> str:
    city = normalize_text(row.get("city"))
    date_iso = normalize_text(row.get("date_iso") or row.get("date"))
    condition = normalize_condition(row.get("condition"))
    unit = normalize_text(row.get("unit"))
    threshold = row.get("threshold")
    threshold_high = row.get("threshold_high")
    if not city or not date_iso or not condition or not unit or threshold is None:
        return ""
    if condition == "range" and threshold_high is not None:
        threshold_part = f"{threshold}-{threshold_high}"
    else:
        threshold_part = str(threshold)
    return f"{city}|{date_iso}|{condition}|{threshold_part}|{unit}"


def target_to_c(threshold: Any, unit: Any) -> float | None:
    value = as_float(threshold)
    if value is None:
        return None
    if normalize_text(unit).upper() == "F":
        return (value - 32.0) * 5.0 / 9.0
    return value


def distance_c(row: dict[str, Any], skip_row: dict[str, Any] | None = None) -> float | None:
    if skip_row:
        extras = skip_row.get("extras") if isinstance(skip_row.get("extras"), dict) else {}
        extra_distance = as_float(extras.get("abs_forecast_target_diff"))
        if extra_distance is not None:
            return abs(extra_distance)
    forecast = as_float(row.get("forecast_max"))
    target = target_to_c(row.get("threshold"), row.get("unit"))
    if forecast is None or target is None:
        return None
    return abs(forecast - target)


def distance_band(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < EXACT_NO_NEAR_THRESHOLD_C:
        return "near_lt_1_5c"
    return "far_gte_1_5c"


def infer_side(eval_row: dict[str, Any], skip_row: dict[str, Any] | None, resolution: dict[str, Any] | None) -> str | None:
    recorded_side = normalize_side(eval_row.get("side"))
    if recorded_side:
        return recorded_side
    if skip_row:
        side = normalize_side(skip_row.get("side"))
        if side:
            return side
    gate = normalize_text(eval_row.get("decision_gate"))
    if gate in {"SHADOW_EXACT_NO_GLOBAL", "SHADOW_EXACT_NO_NEAR_THRESHOLD", "PAUSE_WELLINGTON_EXACT_NO"}:
        return "NO"
    condition = normalize_condition(eval_row.get("condition"))
    if condition in {"exact", "at_or_above", "at_or_below"}:
        return "NO"
    return normalize_side(eval_row.get("side"))


def infer_gate(eval_row: dict[str, Any], skip_row: dict[str, Any] | None, resolution: dict[str, Any] | None) -> str:
    gate = normalize_text(eval_row.get("decision_gate"))
    skip_reason = normalize_text(eval_row.get("skip_or_block_reason"))
    if gate == "PAUSE_WELLINGTON_EXACT_NO":
        return "BLOCK"
    if gate in {"SHADOW_EXACT_NO_GLOBAL", "SHADOW_EXACT_NO_NEAR_THRESHOLD"} or skip_reason == "shadow_only_override":
        return "SHADOW"
    if skip_row and normalize_text(skip_row.get("skip_reason")) == "shadow_only_override":
        return "SHADOW"
    if bool(eval_row.get("would_buy")):
        return "LIVE"
    city_mode = normalize_text(eval_row.get("city_mode")).lower()
    if city_mode == "blocked":
        return "BLOCK"
    if city_mode == "shadow":
        return "SHADOW"
    if resolution:
        mode = normalize_text(resolution.get("city_mode_at_record_time")).lower()
        if mode == "blocked":
            return "BLOCK"
        if mode == "shadow":
            return "SHADOW"
        if mode in {"active", "canary"} and normalize_text(resolution.get("reason_blocked")):
            return "BLOCK"
    return "UNKNOWN"


def price_probability(eval_row: dict[str, Any], resolution: dict[str, Any] | None = None) -> float | None:
    mkt_prob = as_float(eval_row.get("mkt_prob"))
    if mkt_prob is not None:
        return max(0.0, min(1.0, mkt_prob / 100.0))
    if resolution:
        entered = as_float(resolution.get("avg_price_entered"))
        if entered is not None:
            return max(0.0, min(1.0, entered))
    return None


def simulated_unit_pnl(win: bool | None, price: float | None) -> float | None:
    if win is None or price is None:
        return None
    return (1.0 - price) if win else -price


def build_signal_rows(
    evaluations: list[dict[str, Any]],
    skip_rows: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    resolution_index = build_latest_index(resolutions, ("match_key", "eval_key"))
    skip_index = build_skip_index(skip_rows)
    signals: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for eval_row in evaluations:
        key = normalize_text(eval_row.get("eval_key")) or build_eval_key_from_row(eval_row)
        if not key:
            continue
        seen_keys.add(key)
        parsed = parse_match_key(key)
        merged = dict(parsed)
        merged.update(eval_row)
        resolution = resolution_index.get(key)
        skip_row = skip_index.get(key)
        side = infer_side(merged, skip_row, resolution)
        recorded_side = normalize_side(merged.get("side"))
        outcome = normalize_side(resolution.get("outcome")) if resolution else None
        resolved = bool(resolution and resolution.get("resolved") and outcome in {"YES", "NO"})
        win = (side == outcome) if resolved and side else None
        dist = distance_c(merged, skip_row)
        price = price_probability(merged, resolution)
        signals.append(
            {
                "eval_key": key,
                "ts_utc": merged.get("ts_utc"),
                "last_seen": merged.get("ts_utc"),
                "market_id": resolution.get("market_id") if resolution else merged.get("market_id"),
                "condition_id": resolution.get("condition_id") if resolution else merged.get("condition_id"),
                "city": merged.get("city"),
                "date_iso": merged.get("date_iso") or merged.get("date"),
                "condition": normalize_condition(merged.get("condition")),
                "side": side,
                "side_recorded": bool(recorded_side),
                "city_mode": normalize_text(merged.get("city_mode")).lower() or None,
                "cohort_key": normalize_text(merged.get("cohort_key")) or None,
                "evaluation_source": normalize_text(merged.get("evaluation_source")) or None,
                "would_buy": bool(merged.get("would_buy")),
                "threshold": merged.get("threshold"),
                "threshold_high": merged.get("threshold_high"),
                "unit": merged.get("unit"),
                "forecast": merged.get("forecast_max"),
                "abs_forecast_target_diff": dist,
                "distance_band": distance_band(dist),
                "our_prob": as_float(merged.get("our_prob") or merged.get("decision_confidence")),
                "mkt_prob": as_float(merged.get("mkt_prob")),
                "edge": as_float(merged.get("bot_edge_pct_at_signal")),
                "source": resolution.get("trader") if resolution else None,
                "gate_current": infer_gate(merged, skip_row, resolution),
                "decision_gate": merged.get("decision_gate"),
                "resolved": resolved,
                "outcome": outcome,
                "win": win,
                "simulated_unit_pnl": simulated_unit_pnl(win, price),
            }
        )
    for resolution in resolutions:
        key = normalize_text(resolution.get("match_key") or resolution.get("eval_key"))
        if not key or key in seen_keys:
            continue
        parsed = parse_match_key(key)
        if not parsed:
            continue
        condition = normalize_condition(resolution.get("condition") or parsed.get("condition"))
        outcome = normalize_side(resolution.get("outcome"))
        side = "NO" if condition in {"exact", "at_or_above", "at_or_below"} else outcome
        resolved = bool(resolution.get("resolved") and outcome in {"YES", "NO"})
        win = (side == outcome) if resolved and side else None
        dist = distance_c(parsed)
        price = price_probability({}, resolution)
        signals.append(
            {
                "eval_key": key,
                "ts_utc": resolution.get("checked_at"),
                "last_seen": resolution.get("checked_at"),
                "market_id": resolution.get("market_id"),
                "condition_id": resolution.get("condition_id"),
                "city": resolution.get("city") or parsed.get("city"),
                "date_iso": resolution.get("date") or parsed.get("date_iso"),
                "condition": condition,
                "side": side,
                "side_recorded": False,
                "city_mode": normalize_text(resolution.get("city_mode_at_record_time")).lower() or None,
                "cohort_key": None,
                "evaluation_source": "resolution_only",
                "would_buy": False,
                "threshold": parsed.get("threshold"),
                "threshold_high": parsed.get("threshold_high"),
                "unit": parsed.get("unit"),
                "forecast": None,
                "abs_forecast_target_diff": dist,
                "distance_band": distance_band(dist),
                "our_prob": None,
                "mkt_prob": None,
                "edge": None,
                "source": resolution.get("trader"),
                "gate_current": infer_gate({}, None, resolution),
                "decision_gate": None,
                "resolved": resolved,
                "outcome": outcome,
                "win": win,
                "simulated_unit_pnl": simulated_unit_pnl(win, price),
            }
        )
    return signals


def match_real_lifecycle_pnl(signals: list[dict[str, Any]], lifecycle_payload: Any) -> dict[str, float]:
    records = []
    if isinstance(lifecycle_payload, dict):
        records = lifecycle_payload.get("records") or lifecycle_payload.get("positions") or []
    elif isinstance(lifecycle_payload, list):
        records = lifecycle_payload
    pnl_by_key: dict[str, float] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        key = build_eval_key_from_row(record)
        if not key:
            ctx = record.get("entry_context") if isinstance(record.get("entry_context"), dict) else {}
            key = build_eval_key_from_row(ctx)
        pnl = as_float(record.get("pnl_cash") or record.get("realized_pnl") or record.get("pnl"))
        if key and pnl is not None:
            pnl_by_key[key] = pnl_by_key.get(key, 0.0) + pnl
    signal_keys = {row["eval_key"] for row in signals}
    return {key: value for key, value in pnl_by_key.items() if key in signal_keys}


def lifecycle_signal_rows(lifecycle_payload: Any) -> list[dict[str, Any]]:
    records = []
    if isinstance(lifecycle_payload, dict):
        records = lifecycle_payload.get("records") or lifecycle_payload.get("positions") or []
    elif isinstance(lifecycle_payload, list):
        records = lifecycle_payload
    rows: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        condition = normalize_condition(record.get("condition"))
        if condition not in {"exact", "at_or_above", "at_or_below"}:
            continue
        side = normalize_side(record.get("side"))
        if side != "NO":
            continue
        status = normalize_text(record.get("status")).lower()
        close_context = record.get("close_context") if isinstance(record.get("close_context"), dict) else {}
        closed = status == "closed" or bool(record.get("closed_at")) or bool(close_context)
        threshold, unit = infer_threshold_from_text(record.get("label") or record.get("question"))
        if unit is None:
            unit = normalize_text(record.get("unit")) or "C"
        key = build_eval_key_from_row(
            {
                "city": record.get("city"),
                "date_iso": record.get("date"),
                "condition": condition,
                "threshold": threshold,
                "unit": unit,
            }
        ) or f"lifecycle:{record.get('id') or record.get('position_key') or len(rows)}"
        entry_context = record.get("entry_context") if isinstance(record.get("entry_context"), dict) else {}
        pnl = as_float(close_context.get("pnl_cash") or record.get("pnl_cash"))
        close_action = normalize_text(close_context.get("close_action") or record.get("close_action")).upper()
        win = None
        if closed:
            if close_action == "RESOLVED_WIN" or (pnl is not None and pnl > 0):
                win = True
            elif close_action or pnl is not None:
                win = False
        forecast = as_float(entry_context.get("forecast_max"))
        dist = distance_c({"forecast_max": forecast, "threshold": threshold, "unit": unit})
        rows.append(
            {
                "eval_key": key,
                "ts_utc": record.get("opened_at") or entry_context.get("timestamp"),
                "last_seen": record.get("closed_at") or record.get("last_activity_at") or record.get("opened_at"),
                "market_id": record.get("market_id"),
                "condition_id": record.get("condition_id"),
                "city": record.get("city"),
                "date_iso": record.get("date"),
                "condition": condition,
                "side": side,
                "threshold": threshold,
                "threshold_high": None,
                "unit": unit,
                "forecast": forecast,
                "abs_forecast_target_diff": dist,
                "distance_band": distance_band(dist),
                "our_prob": as_float(entry_context.get("our_prob")),
                "mkt_prob": as_float(entry_context.get("mkt_price")),
                "edge": as_float(entry_context.get("edge_pct")),
                "source": "trade_lifecycle",
                "gate_current": "LIVE",
                "decision_gate": "LIVE",
                "resolved": bool(closed and win is not None),
                "outcome": side if win else ("YES" if win is False else None),
                "win": win,
                "simulated_unit_pnl": simulated_unit_pnl(win, price_probability({"mkt_prob": entry_context.get("mkt_price")})),
                "real_pnl": pnl,
                "execution_key": executed_trade_key(record),
                "data_quality_issues": [],
            }
        )
    return rows


def market_identity_key(row: dict[str, Any]) -> str:
    eval_key = normalize_text(row.get("eval_key"))
    if eval_key:
        return f"eval_key:{eval_key}"
    condition_id = normalize_text(row.get("condition_id"))
    if condition_id:
        return f"condition_id:{condition_id}"
    market_id = normalize_text(row.get("market_id"))
    if market_id:
        return f"market_id:{market_id}"
    return ""


def calibration_key(row: dict[str, Any]) -> str:
    identity = market_identity_key(row)
    side = normalize_side(row.get("side"))
    outcome = normalize_side(row.get("outcome"))
    if not identity or not side or not outcome:
        return ""
    return f"{identity}|side:{side}|outcome:{outcome}"


def row_sort_ts(row: dict[str, Any]) -> str:
    return normalize_text(row.get("last_seen") or row.get("ts_utc"))


def choose_calibration_representative(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def rank(row: dict[str, Any]) -> tuple[int, int, str]:
        return (
            1 if as_float(row.get("our_prob")) is not None else 0,
            1 if as_float(row.get("simulated_unit_pnl")) is not None else 0,
            row_sort_ts(row),
        )

    return sorted(rows, key=rank, reverse=True)[0]


def dedupe_calibration_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    closed = [row for row in rows if row.get("resolved") and row.get("win") is not None]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing_key = 0
    for row in closed:
        key = calibration_key(row)
        if not key:
            missing_key += 1
            continue
        grouped[key].append(row)
    unique = [choose_calibration_representative(items) for items in grouped.values()]
    top_duplicates = [
        {
            "key": key,
            "raw_rows": len(items),
            "duplicates_removed": len(items) - 1,
        }
        for key, items in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        if len(items) > 1
    ][:5]
    diagnostics = {
        "n_closed_raw": len(closed),
        "n_closed_calibration_unique": len(unique),
        "duplicates_removed_for_calibration": max(0, len(closed) - len(unique)),
        "missing_calibration_key_rows": missing_key,
        "top_duplicate_calibration_keys": top_duplicates,
    }
    return unique, diagnostics


def executed_trade_key(record: dict[str, Any]) -> str:
    record_id = normalize_text(record.get("id"))
    if record_id:
        return f"id:{record_id}"
    position_key = normalize_text(record.get("position_key"))
    opened_at = normalize_text(record.get("opened_at"))
    closed_at = normalize_text(record.get("closed_at"))
    entry_context = record.get("entry_context") if isinstance(record.get("entry_context"), dict) else {}
    entry_ts = normalize_text(entry_context.get("timestamp"))
    if position_key and (opened_at or entry_ts or closed_at):
        return f"position_key:{position_key}|entry:{opened_at or entry_ts}|closed:{closed_at}"
    return ""


def dedupe_executed_trade_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing_key = 0
    for row in rows:
        key = normalize_text(row.get("execution_key"))
        if not key:
            missing_key += 1
            continue
        grouped[key].append(row)
    unique = [sorted(items, key=row_sort_ts, reverse=True)[0] for items in grouped.values()]
    top_duplicates = [
        {
            "key": key,
            "raw_rows": len(items),
            "duplicates_removed": len(items) - 1,
        }
        for key, items in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        if len(items) > 1
    ][:5]
    diagnostics = {
        "n_executed_trade_rows_raw": len(rows),
        "n_executed_trades_unique": len(unique),
        "duplicates_removed_for_executed_trades": max(0, len(rows) - len(unique)),
        "missing_execution_key_rows": missing_key,
        "top_duplicate_execution_keys": top_duplicates,
    }
    return unique, diagnostics


def data_quality_verdict(calibration_diag: dict[str, Any], execution_diag: dict[str, Any]) -> str:
    if calibration_diag.get("missing_calibration_key_rows") or execution_diag.get("missing_execution_key_rows"):
        return "DATA_QUALITY_BLOCKER"
    if calibration_diag.get("duplicates_removed_for_calibration") or execution_diag.get("duplicates_removed_for_executed_trades"):
        return "DEDUPED_OK"
    return "OK"


def cohort_metrics(name: str, raw_rows: list[dict[str, Any]], executed_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    executed_rows = executed_rows or []
    calibration_closed, calibration_diag = dedupe_calibration_rows(raw_rows)
    executed_unique, execution_diag = dedupe_executed_trade_rows(executed_rows)
    closed = calibration_closed
    wins = sum(1 for row in closed if row.get("win") is True)
    losses = sum(1 for row in closed if row.get("win") is False)
    n_closed_calibration_unique = len(closed)
    wr_observed = round(wins / n_closed_calibration_unique, 4) if n_closed_calibration_unique else None
    probs = [as_float(row.get("our_prob")) for row in closed]
    probs = [prob for prob in probs if prob is not None]
    avg_our_prob = round((sum(probs) / len(probs)) / 100.0, 4) if probs else None
    calibration_gap = (
        round(avg_our_prob - wr_observed, 4)
        if avg_our_prob is not None and wr_observed is not None
        else None
    )
    sim_values = [as_float(row.get("simulated_unit_pnl")) for row in closed]
    sim_values = [value for value in sim_values if value is not None]
    simulated_unit_pnl_total = round(sum(sim_values), 4) if sim_values else None
    real_values = [as_float(row.get("real_pnl")) for row in executed_unique]
    real_values = [value for value in real_values if value is not None]
    real_pnl_total = round(sum(real_values), 4) if real_values else None
    gates = [normalize_text(row.get("gate_current")) for row in raw_rows if normalize_text(row.get("gate_current"))]
    gate_current = max(set(gates), key=gates.count) if gates else "UNKNOWN"
    last_seen = max((normalize_text(row.get("last_seen")) for row in [*raw_rows, *executed_rows] if row.get("last_seen")), default=None)
    dq_verdict = data_quality_verdict(calibration_diag, execution_diag)
    verdict = classify_verdict(
        n_closed_calibration_unique=n_closed_calibration_unique,
        wr_observed=wr_observed,
        calibration_gap=calibration_gap,
        simulated_unit_pnl_total=simulated_unit_pnl_total,
        real_pnl_total=real_pnl_total,
        gate_current=gate_current,
        data_quality_verdict=dq_verdict,
    )
    return {
        "cohort": name,
        "n_seen_raw": len(raw_rows),
        "n_closed_raw": calibration_diag["n_closed_raw"],
        "n_closed_calibration_unique": n_closed_calibration_unique,
        "n_executed_trades_unique": execution_diag["n_executed_trades_unique"],
        "duplicates_removed_for_calibration": calibration_diag["duplicates_removed_for_calibration"],
        "wins_calibration": wins,
        "losses_calibration": losses,
        "wr_calibration": wr_observed,
        "avg_our_prob_calibration": avg_our_prob,
        "calibration_gap": calibration_gap,
        "pnl_real_reported_noncanonical": real_pnl_total,
        "pnl_simulated_unit_calibration": simulated_unit_pnl_total,
        "last_seen": last_seen,
        "gate_current": gate_current,
        "data_quality_verdict": dq_verdict,
        "decision_verdict": verdict,
        "duplicate_diagnostics": {
            **calibration_diag,
            **execution_diag,
        },
        "manual_only": True,
        # Backward-compatible aliases for older digest/tests.
        "n_seen": len(raw_rows),
        "n_closed": n_closed_calibration_unique,
        "wins": wins,
        "losses": losses,
        "wr_observed": wr_observed,
        "avg_our_prob": avg_our_prob,
        "pnl_simulated_unit": simulated_unit_pnl_total,
        "verdict": verdict,
    }


def classify_verdict(
    *,
    n_closed_calibration_unique: int,
    wr_observed: float | None,
    calibration_gap: float | None,
    simulated_unit_pnl_total: float | None,
    real_pnl_total: float | None,
    gate_current: str,
    data_quality_verdict: str = "OK",
) -> str:
    if data_quality_verdict == "DATA_QUALITY_BLOCKER":
        return "DATA_QUALITY_BLOCKER"
    if n_closed_calibration_unique < MIN_REVIEW_SAMPLE:
        return "INSUFFICIENT_SAMPLE"
    negative_pnl = bool(simulated_unit_pnl_total is not None and simulated_unit_pnl_total < 0)
    positive_shadow_pnl = bool(simulated_unit_pnl_total is not None and simulated_unit_pnl_total > 0)
    if (
        (wr_observed is not None and wr_observed <= 0.40)
        or (calibration_gap is not None and calibration_gap >= 0.20)
    ) and negative_pnl:
        return "REVIEW_BLOCK_LIVE"
    if (
        gate_current == "SHADOW"
        and wr_observed is not None
        and wr_observed >= 0.60
        and calibration_gap is not None
        and calibration_gap <= 0.10
        and positive_shadow_pnl
    ):
        return "CANDIDATE_FOR_CANARY_REVIEW"
    if gate_current == "SHADOW":
        return "KEEP_SHADOW"
    return "REVIEW_OPUS"


def required_more(n_closed: int) -> int:
    return max(0, MIN_REVIEW_SAMPLE - int(n_closed or 0))


def select_cohorts(signals: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    cohorts: dict[str, list[dict[str, Any]]] = {
        "exact/NO near-threshold": [],
        "exact/NO far": [],
        "directional NO": [],
    }
    for row in signals:
        condition = row.get("condition")
        side = row.get("side")
        band = row.get("distance_band")
        if condition == "exact" and side == "NO":
            if band == "near_lt_1_5c":
                cohorts["exact/NO near-threshold"].append(row)
            elif band == "far_gte_1_5c":
                cohorts["exact/NO far"].append(row)
        if condition in {"at_or_above", "at_or_below"} and side == "NO":
            cohorts["directional NO"].append(row)
    return cohorts


def condition_family(row: dict[str, Any]) -> str:
    condition = normalize_condition(row.get("condition"))
    if condition == "exact":
        return "exact"
    if condition in {"at_or_above", "at_or_below"}:
        return "directional"
    if condition == "range":
        return "range"
    return condition or "unknown_condition"


def surviving_cohort_name(row: dict[str, Any]) -> str:
    return f"{condition_family(row)} / {normalize_side(row.get('side')) or 'UNKNOWN'}"


def live_side_verdict(metrics: dict[str, Any], *, protected_exact_no: bool) -> str:
    n_unique = int(metrics.get("n_closed_calibration_unique", 0) or 0)
    if n_unique < MIN_REVIEW_SAMPLE:
        return "ACCUMULATING_FORWARD_EVIDENCE" if int(metrics.get("n_eval_forward", 0) or 0) else "INSUFFICIENT_SAMPLE"
    gate = normalize_text(metrics.get("dominant_gate"))
    wr = metrics.get("wr_calibration")
    gap = metrics.get("calibration_gap")
    sim = metrics.get("pnl_simulated_unit_calibration")
    negative = bool(sim is not None and sim < 0)
    positive = bool(sim is not None and sim > 0)
    if gate == "LIVE" and (((wr is not None and wr <= 0.40) or (gap is not None and gap >= 0.20)) and negative):
        return "REVIEW_LIVE_CONTAINMENT"
    if gate == "LIVE":
        return "REVIEW_LIVE_COHORT_QUALITY"
    if protected_exact_no:
        return "ACCUMULATING_FORWARD_EVIDENCE"
    if (
        gate in {"SHADOW", "UNKNOWN"}
        and wr is not None
        and wr >= 0.60
        and gap is not None
        and gap <= 0.10
        and positive
    ):
        return "CANDIDATE_FOR_CANARY_REVIEW"
    return "ACCUMULATING_FORWARD_EVIDENCE"


def build_surviving_cohorts_by_side(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    forward_rows = [row for row in signals if is_live_side_forward_row(row)]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in forward_rows:
        name = surviving_cohort_name(row)
        mode = normalize_text(row.get("city_mode")).lower() or "unknown"
        grouped[(name, mode)].append(row)

    metrics_rows: list[dict[str, Any]] = []
    for (name, mode), rows in grouped.items():
        base = cohort_metrics(name, rows, [])
        gates = [normalize_text(row.get("gate_current")) for row in rows if normalize_text(row.get("gate_current"))]
        dominant_gate = max(set(gates), key=gates.count) if gates else "UNKNOWN"
        protected_exact_no = name == "exact / NO"
        candidate_allowed = not protected_exact_no
        verdict = live_side_verdict(
            {
                **base,
                "n_eval_forward": len(rows),
                "dominant_gate": dominant_gate,
            },
            protected_exact_no=protected_exact_no,
        )
        metrics_rows.append(
            {
                "cohort": name,
                "city_mode": mode,
                "n_eval_forward": len(rows),
                "n_would_buy": sum(1 for row in rows if row.get("would_buy")),
                "n_shadow": sum(1 for row in rows if row.get("gate_current") == "SHADOW"),
                "n_blocked": sum(1 for row in rows if row.get("gate_current") == "BLOCK"),
                "n_resolved_calibration_unique": base["n_closed_calibration_unique"],
                "wr_calibration": base["wr_calibration"],
                "pnl_simulated_unit_calibration": base["pnl_simulated_unit_calibration"],
                "calibration_gap": base["calibration_gap"],
                "dominant_gate": dominant_gate,
                "candidate_allowed": candidate_allowed,
                "protected_reason": "EXACT_NO_REMAINS_SHADOW_PROTECTED" if protected_exact_no else None,
                "manual_review_state": verdict,
                "last_seen": base["last_seen"],
            }
        )
    metrics_rows.sort(
        key=lambda row: (
            row["cohort"] == "exact / NO",
            row["cohort"],
            row["city_mode"],
        )
    )
    return metrics_rows


def build_directional_subcohorts(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        city = normalize_text(row.get("city")) or "unknown_city"
        source = normalize_text(row.get("source")) or "unknown_source"
        band = normalize_text(row.get("distance_band")) or "unknown"
        grouped[f"directional NO / city={city}"].append(row)
        grouped[f"directional NO / source={source}"].append(row)
        grouped[f"directional NO / distance={band}"].append(row)
    return dict(grouped)


def directional_forward_capture_status(metrics: dict[str, Any]) -> str:
    diag = metrics.get("duplicate_diagnostics", {})
    if diag.get("missing_calibration_key_rows"):
        return "DATA_CAPTURE_BLOCKER"
    if int(metrics.get("n_seen_raw", 0) or 0) == 0:
        return "CAPTURE_ACTIVE_NO_RESOLUTIONS_YET"
    if int(metrics.get("n_closed_calibration_unique", 0) or 0) == 0:
        return "CAPTURE_ACTIVE_NO_RESOLUTIONS_YET"
    return "CALIBRATION_ACCUMULATING"


def best_directional_subcohort(metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not metrics:
        return None
    candidate_rank = {
        "CANDIDATE_FOR_CANARY_REVIEW": 0,
        "KEEP_SHADOW": 1,
        "REVIEW_OPUS": 2,
        "REVIEW_BLOCK_LIVE": 3,
        "INSUFFICIENT_SAMPLE": 4,
    }
    return sorted(
        metrics,
        key=lambda row: (
            candidate_rank.get(row.get("decision_verdict"), 9),
            -int(row.get("n_closed_calibration_unique", 0) or 0),
            -(row.get("wr_calibration") if row.get("wr_calibration") is not None else -1),
            -(row.get("pnl_simulated_unit_calibration") if row.get("pnl_simulated_unit_calibration") is not None else -999),
            row.get("cohort", ""),
        ),
    )[0]


def build_report(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    bot_evaluations: Path | None = None,
    skip_log: Path | None = None,
    resolutions: Path | None = None,
    trade_lifecycle: Path | None = None,
) -> dict[str, Any]:
    bot_evaluations = bot_evaluations or data_dir / "bot_signal_evaluations.jsonl"
    skip_log = skip_log or data_dir / "skip_log.jsonl"
    resolutions = resolutions or data_dir / "blocked_signals_resolutions.jsonl"
    trade_lifecycle = trade_lifecycle or data_dir / "trade_lifecycle.json"

    eval_rows = read_jsonl(bot_evaluations)
    skip_rows = read_jsonl(skip_log)
    resolution_rows = read_jsonl(resolutions)
    lifecycle_payload = read_json(trade_lifecycle)
    signals = build_signal_rows(eval_rows, skip_rows, resolution_rows)
    lifecycle_rows = lifecycle_signal_rows(lifecycle_payload)
    surviving_by_side = build_surviving_cohorts_by_side(signals)

    cohorts = select_cohorts(signals)
    executed_cohorts = select_cohorts(lifecycle_rows)
    main_metrics = [
        cohort_metrics(name, rows, executed_cohorts.get(name, []))
        for name, rows in cohorts.items()
    ]
    directional_rows = cohorts["directional NO"]
    directional_executed_rows = executed_cohorts.get("directional NO", [])
    directional_executed_subcohorts = build_directional_subcohorts(directional_executed_rows)
    sub_metrics = [
        cohort_metrics(name, rows, directional_executed_subcohorts.get(name, []))
        for name, rows in build_directional_subcohorts(directional_rows).items()
    ]
    sub_metrics.sort(key=lambda row: (-int(row.get("n_closed", 0) or 0), row.get("cohort", "")))
    best_sub = best_directional_subcohort(sub_metrics)
    directional_forward_rows = [row for row in directional_rows if is_forward_directional_row(row)]
    directional_forward_metrics = cohort_metrics("directional NO / forward", directional_forward_rows, [])
    directional_forward_sub_metrics = [
        cohort_metrics(name, rows, [])
        for name, rows in build_directional_subcohorts(directional_forward_rows).items()
    ]
    directional_forward_status = directional_forward_capture_status(directional_forward_metrics)

    exact_near = next(row for row in main_metrics if row["cohort"] == "exact/NO near-threshold")
    directional = next(row for row in main_metrics if row["cohort"] == "directional NO")
    exact_status = (
        "YES"
        if exact_near["verdict"] in {"REVIEW_BLOCK_LIVE", "KEEP_SHADOW"}
        else "INSUFFICIENT_SAMPLE"
        if exact_near["verdict"] == "INSUFFICIENT_SAMPLE"
        else "NO"
    )
    candidate_found = any(
        row["decision_verdict"] == "CANDIDATE_FOR_CANARY_REVIEW"
        for row in [directional_forward_metrics, *directional_forward_sub_metrics]
    )
    directional_status = (
        "YES"
        if candidate_found
        else "INSUFFICIENT_SAMPLE"
        if directional_forward_metrics["n_closed_calibration_unique"] < MIN_REVIEW_SAMPLE
        else "NO"
    )
    return {
        "generated_at": now_utc(),
        "mode": "LOG_ONLY",
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "inputs": {
            "bot_evaluations": str(bot_evaluations),
            "skip_log": str(skip_log),
            "resolutions": str(resolutions),
            "trade_lifecycle": str(trade_lifecycle),
        },
        "source_counts": {
            "bot_evaluations": len(eval_rows),
            "skip_log": len(skip_rows),
            "resolutions": len(resolution_rows),
            "raw_signals": len(signals),
            "executed_trade_rows": len(lifecycle_rows),
            "joined_signals": len(signals) + len(lifecycle_rows),
        },
        "thresholds": {
            "exact_no_near_threshold_c": EXACT_NO_NEAR_THRESHOLD_C,
            "min_review_sample": MIN_REVIEW_SAMPLE,
        },
        "live_side_visibility_forward": {
            "forward_visibility_start": LIVE_SIDE_VISIBILITY_FORWARD_START_UTC,
            "n_forward_rows_with_recorded_side": sum(1 for row in signals if is_live_side_forward_row(row)),
            "note": (
                "SURVIVING_COHORTS_BY_SIDE uses only bot_signal_evaluations rows at or after "
                f"{LIVE_SIDE_VISIBILITY_FORWARD_START_UTC} with side explicitly recorded by the live evaluator. "
                "No historical side reconstruction is used."
            ),
        },
        "directional_forward_capture": {
            "forward_capture_start": DIRECTIONAL_FORWARD_CAPTURE_START_UTC,
            "directional_forward_seen": directional_forward_metrics["n_seen_raw"],
            "directional_forward_resolved_calibration_unique": directional_forward_metrics["n_closed_calibration_unique"],
            "status": directional_forward_status,
            "note": (
                "Directional NO promotion gates use only forward linked outcomes from "
                f"{DIRECTIONAL_FORWARD_CAPTURE_START_UTC}; legacy executed trades remain P&L-only."
            ),
        },
        "main_cohorts": main_metrics,
        "surviving_cohorts_by_side": surviving_by_side,
        "directional_no_forward": directional_forward_metrics,
        "directional_no_forward_subcohorts": directional_forward_sub_metrics,
        "directional_no_subcohorts": sub_metrics,
        "best_directional_no_subcohort": best_sub,
        "summary_verdicts": {
            "EXACT_NO_NEAR_SHADOW_STILL_JUSTIFIED": exact_status,
            "DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND": directional_status,
            "OPUS_REVIEW_REQUIRED_NOW": "YES" if candidate_found else "NO",
        },
        "directional_no_next_trigger": {
            "condition": "Open Opus review when directional NO or any subcohort reaches CANDIDATE_FOR_CANARY_REVIEW.",
            "condition_detail": "Directional NO review gates use forward linked outcomes only.",
            "current_n_closed_calibration_unique": directional_forward_metrics["n_closed_calibration_unique"],
            "resolutions_missing_for_min_sample": required_more(directional_forward_metrics["n_closed_calibration_unique"]),
        },
    }


def pct_text(value: Any) -> str:
    parsed = as_float(value)
    if parsed is None:
        return "n/a"
    return f"{parsed * 100:.1f}%"


def money_text(value: Any) -> str:
    parsed = as_float(value)
    if parsed is None:
        return "n/a"
    return f"{parsed:+.2f}"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Cohort Intelligence Loop v1",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Mode: `{report['mode']}`",
        f"- Disclaimer: {report['disclaimer']}",
        "",
        "## Main Cohorts",
        "",
        "| cohort | raw_seen | raw_closed | calibration_unique | executed_trades | dupes_removed | W-L cal | WR cal | avg_our_prob cal | gap | sim_unit_pnl cal | real_pnl_noncanonical | DQ | gate | verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in report["main_cohorts"]:
        lines.append(
            "| {cohort} | {n_seen_raw} | {n_closed_raw} | {n_closed_calibration_unique} | {n_executed_trades_unique} | {duplicates_removed_for_calibration} | {wins}-{losses} | {wr} | {prob} | {gap} | {sim} | {real} | {dq} | {gate} | {verdict} |".format(
                cohort=row["cohort"],
                n_seen_raw=row["n_seen_raw"],
                n_closed_raw=row["n_closed_raw"],
                n_closed_calibration_unique=row["n_closed_calibration_unique"],
                n_executed_trades_unique=row["n_executed_trades_unique"],
                duplicates_removed_for_calibration=row["duplicates_removed_for_calibration"],
                wins=row["wins_calibration"],
                losses=row["losses_calibration"],
                wr=pct_text(row["wr_calibration"]),
                prob=pct_text(row["avg_our_prob_calibration"]),
                gap=pct_text(row["calibration_gap"]),
                sim=money_text(row["pnl_simulated_unit_calibration"]),
                real=money_text(row["pnl_real_reported_noncanonical"]),
                dq=row["data_quality_verdict"],
                gate=row["gate_current"],
                verdict=row["decision_verdict"],
            )
        )
    best = report.get("best_directional_no_subcohort")
    forward = report.get("directional_forward_capture", {})
    side_forward = report.get("live_side_visibility_forward", {})
    surviving = report.get("surviving_cohorts_by_side", [])
    lines.extend(
        [
            "",
            "## SURVIVING_COHORTS_BY_SIDE",
            "",
            f"- forward_visibility_start = `{side_forward.get('forward_visibility_start')}`",
            f"- n_forward_rows_with_recorded_side = `{side_forward.get('n_forward_rows_with_recorded_side', 0)}`",
            f"- {side_forward.get('note', '')}",
            "",
            "| cohort | city_mode | n_eval_forward | would_buy | shadow | blocked | resolved_cal_unique | WR cal | sim_unit_pnl cal | gate | candidate_allowed | state |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
        ]
    )
    if surviving:
        for row in surviving:
            lines.append(
                "| {cohort} | {mode} | {n_eval} | {n_buy} | {n_shadow} | {n_blocked} | {n_resolved} | {wr} | {sim} | {gate} | {candidate} | {state} |".format(
                    cohort=row["cohort"],
                    mode=row["city_mode"],
                    n_eval=row["n_eval_forward"],
                    n_buy=row["n_would_buy"],
                    n_shadow=row["n_shadow"],
                    n_blocked=row["n_blocked"],
                    n_resolved=row["n_resolved_calibration_unique"],
                    wr=pct_text(row["wr_calibration"]),
                    sim=money_text(row["pnl_simulated_unit_calibration"]),
                    gate=row["dominant_gate"],
                    candidate="YES" if row["candidate_allowed"] else "NO",
                    state=row["manual_review_state"],
                )
            )
    else:
        lines.append("| none yet | n/a | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | ACCUMULATING_FORWARD_EVIDENCE |")
    lines.extend(["", "## Directional NO Best Subcohort", ""])
    if best:
        lines.append(
            "- `{cohort}`: n_closed={n_closed}, WR={wr}, gap={gap}, sim_unit_pnl={sim}, verdict=`{verdict}`.".format(
                cohort=best["cohort"],
                n_closed=best["n_closed_calibration_unique"],
                wr=pct_text(best["wr_calibration"]),
                gap=pct_text(best["calibration_gap"]),
                sim=money_text(best["pnl_simulated_unit_calibration"]),
                verdict=best["decision_verdict"],
            )
        )
    else:
        lines.append("- No directional NO subcohort available yet.")
    verdicts = report["summary_verdicts"]
    trigger = report["directional_no_next_trigger"]
    lines.extend(
        [
            "",
            "## Directional NO Forward Capture",
            "",
            f"- forward_capture_start = `{forward.get('forward_capture_start')}`",
            f"- directional_forward_seen = `{forward.get('directional_forward_seen', 0)}`",
            f"- directional_forward_resolved_calibration_unique = `{forward.get('directional_forward_resolved_calibration_unique', 0)}`",
            f"- status = `{forward.get('status', 'CAPTURE_ACTIVE_NO_RESOLUTIONS_YET')}`",
            f"- {forward.get('note', '')}",
            "",
            "## Verdicts",
            "",
            f"- EXACT_NO_NEAR_SHADOW_STILL_JUSTIFIED = `{verdicts['EXACT_NO_NEAR_SHADOW_STILL_JUSTIFIED']}`",
            f"- DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND = `{verdicts['DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND']}`",
            f"- OPUS_REVIEW_REQUIRED_NOW = `{verdicts['OPUS_REVIEW_REQUIRED_NOW']}`",
            f"- Directional NO missing resolutions for min sample: `{trigger['resolutions_missing_for_min_sample']}`",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = parse_args(argv or sys.argv[1:])
    report = build_report(
        data_dir=Path(args.data_dir),
        bot_evaluations=Path(args.bot_evaluations) if args.bot_evaluations else None,
        skip_log=Path(args.skip_log) if args.skip_log else None,
        resolutions=Path(args.resolutions) if args.resolutions else None,
        trade_lifecycle=Path(args.trade_lifecycle) if args.trade_lifecycle else None,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
