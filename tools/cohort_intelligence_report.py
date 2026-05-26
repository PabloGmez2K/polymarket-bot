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
VERDICTS = {
    "INSUFFICIENT_SAMPLE",
    "KEEP_SHADOW",
    "REVIEW_BLOCK_LIVE",
    "CANDIDATE_FOR_CANARY_REVIEW",
    "REVIEW_OPUS",
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
            }
        )
    return rows


def cohort_metrics(name: str, rows: list[dict[str, Any]], real_pnl_by_key: dict[str, float] | None = None) -> dict[str, Any]:
    real_pnl_by_key = real_pnl_by_key or {}
    closed = [row for row in rows if row.get("resolved") and row.get("win") is not None]
    wins = sum(1 for row in closed if row.get("win") is True)
    losses = sum(1 for row in closed if row.get("win") is False)
    n_closed = len(closed)
    wr_observed = round(wins / n_closed, 4) if n_closed else None
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
    real_keys = {row["eval_key"] for row in closed}
    real_values = [value for key, value in real_pnl_by_key.items() if key in real_keys]
    real_values.extend(value for value in (as_float(row.get("real_pnl")) for row in closed) if value is not None)
    real_pnl_total = round(sum(real_values), 4) if real_values else None
    gates = [normalize_text(row.get("gate_current")) for row in rows if normalize_text(row.get("gate_current"))]
    gate_current = max(set(gates), key=gates.count) if gates else "UNKNOWN"
    last_seen = max((normalize_text(row.get("last_seen")) for row in rows if row.get("last_seen")), default=None)
    verdict = classify_verdict(
        n_closed=n_closed,
        wr_observed=wr_observed,
        calibration_gap=calibration_gap,
        simulated_unit_pnl_total=simulated_unit_pnl_total,
        real_pnl_total=real_pnl_total,
        gate_current=gate_current,
    )
    return {
        "cohort": name,
        "n_seen": len(rows),
        "n_closed": n_closed,
        "wins": wins,
        "losses": losses,
        "wr_observed": wr_observed,
        "avg_our_prob": avg_our_prob,
        "calibration_gap": calibration_gap,
        "pnl_real_reported_noncanonical": real_pnl_total,
        "pnl_simulated_unit": simulated_unit_pnl_total,
        "last_seen": last_seen,
        "gate_current": gate_current,
        "verdict": verdict,
        "manual_only": True,
    }


def classify_verdict(
    *,
    n_closed: int,
    wr_observed: float | None,
    calibration_gap: float | None,
    simulated_unit_pnl_total: float | None,
    real_pnl_total: float | None,
    gate_current: str,
) -> str:
    if n_closed < MIN_REVIEW_SAMPLE:
        return "INSUFFICIENT_SAMPLE"
    pnl_for_gate = simulated_unit_pnl_total if simulated_unit_pnl_total is not None else real_pnl_total
    negative_pnl = bool(pnl_for_gate is not None and pnl_for_gate < 0)
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
            candidate_rank.get(row.get("verdict"), 9),
            -int(row.get("n_closed", 0) or 0),
            -(row.get("wr_observed") if row.get("wr_observed") is not None else -1),
            -(row.get("pnl_simulated_unit") if row.get("pnl_simulated_unit") is not None else -999),
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
    signals.extend(lifecycle_signal_rows(lifecycle_payload))
    real_pnl_by_key = match_real_lifecycle_pnl(signals, lifecycle_payload)

    cohorts = select_cohorts(signals)
    main_metrics = [cohort_metrics(name, rows, real_pnl_by_key) for name, rows in cohorts.items()]
    directional_rows = cohorts["directional NO"]
    sub_metrics = [
        cohort_metrics(name, rows, real_pnl_by_key)
        for name, rows in build_directional_subcohorts(directional_rows).items()
    ]
    sub_metrics.sort(key=lambda row: (-int(row.get("n_closed", 0) or 0), row.get("cohort", "")))
    best_sub = best_directional_subcohort(sub_metrics)

    exact_near = next(row for row in main_metrics if row["cohort"] == "exact/NO near-threshold")
    directional = next(row for row in main_metrics if row["cohort"] == "directional NO")
    exact_status = (
        "YES"
        if exact_near["verdict"] in {"REVIEW_BLOCK_LIVE", "KEEP_SHADOW"}
        else "INSUFFICIENT_SAMPLE"
        if exact_near["verdict"] == "INSUFFICIENT_SAMPLE"
        else "NO"
    )
    candidate_found = any(row["verdict"] == "CANDIDATE_FOR_CANARY_REVIEW" for row in [directional, *sub_metrics])
    directional_status = (
        "YES"
        if candidate_found
        else "INSUFFICIENT_SAMPLE"
        if directional["n_closed"] < MIN_REVIEW_SAMPLE
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
            "joined_signals": len(signals),
        },
        "thresholds": {
            "exact_no_near_threshold_c": EXACT_NO_NEAR_THRESHOLD_C,
            "min_review_sample": MIN_REVIEW_SAMPLE,
        },
        "main_cohorts": main_metrics,
        "directional_no_subcohorts": sub_metrics,
        "best_directional_no_subcohort": best_sub,
        "summary_verdicts": {
            "EXACT_NO_NEAR_SHADOW_STILL_JUSTIFIED": exact_status,
            "DIRECTIONAL_NO_CANARY_CANDIDATE_FOUND": directional_status,
            "OPUS_REVIEW_REQUIRED_NOW": "YES" if candidate_found else "NO",
        },
        "directional_no_next_trigger": {
            "condition": "Open Opus review when directional NO or any subcohort reaches CANDIDATE_FOR_CANARY_REVIEW.",
            "current_n_closed": directional["n_closed"],
            "resolutions_missing_for_min_sample": required_more(directional["n_closed"]),
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
        "| cohort | n_closed | W-L | WR | avg_our_prob | gap | sim_unit_pnl | real_pnl_noncanonical | gate | verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in report["main_cohorts"]:
        lines.append(
            "| {cohort} | {n_closed} | {wins}-{losses} | {wr} | {prob} | {gap} | {sim} | {real} | {gate} | {verdict} |".format(
                cohort=row["cohort"],
                n_closed=row["n_closed"],
                wins=row["wins"],
                losses=row["losses"],
                wr=pct_text(row["wr_observed"]),
                prob=pct_text(row["avg_our_prob"]),
                gap=pct_text(row["calibration_gap"]),
                sim=money_text(row["pnl_simulated_unit"]),
                real=money_text(row["pnl_real_reported_noncanonical"]),
                gate=row["gate_current"],
                verdict=row["verdict"],
            )
        )
    best = report.get("best_directional_no_subcohort")
    lines.extend(["", "## Directional NO Best Subcohort", ""])
    if best:
        lines.append(
            "- `{cohort}`: n_closed={n_closed}, WR={wr}, gap={gap}, sim_unit_pnl={sim}, verdict=`{verdict}`.".format(
                cohort=best["cohort"],
                n_closed=best["n_closed"],
                wr=pct_text(best["wr_observed"]),
                gap=pct_text(best["calibration_gap"]),
                sim=money_text(best["pnl_simulated_unit"]),
                verdict=best["verdict"],
            )
        )
    else:
        lines.append("- No directional NO subcohort available yet.")
    verdicts = report["summary_verdicts"]
    trigger = report["directional_no_next_trigger"]
    lines.extend(
        [
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
