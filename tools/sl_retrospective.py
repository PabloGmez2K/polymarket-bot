#!/usr/bin/env python3
"""Retrospective de stop-loss con estado anti-spam y salida Telegram."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIFECYCLE_FILE = REPO_ROOT / "data" / "trade_lifecycle.json"
DEFAULT_LIFECYCLE_FALLBACK = REPO_ROOT / "data" / "runtime_import" / "trade_lifecycle.json"
DEFAULT_FORECAST_ACCURACY_FILE = REPO_ROOT / "data" / "forecast_accuracy_raw.json"
DEFAULT_AUDIT_FILE = REPO_ROOT / "data" / "runtime_import" / "audit.json"
DEFAULT_STATE_FILE = REPO_ROOT / "data" / "sl_retrospective_state.json"
TARGET_SAMPLE_SIZE = 16
PRELIMINARY_THRESHOLD = 8
FINAL_THRESHOLD = 12
SL_REASONS = {"stop_loss", "stop_loss_intra"}
# F1: pre-cooldown stop_loss_intra.
# F2: post-cooldown, pre-guard.
# F3: post-guard v10.6.40+, configuracion operativa actual.
PHASE_F1_CUTOFF = "2026-04-24T21:22:53+00:00"
PHASE_F2_CUTOFF = "2026-04-27T08:00:41+00:00"
MIN_CURRENT_CONFIG_SAMPLE = 5
DEFAULT_GUARD_FILE = REPO_ROOT / "data" / "sl_intra_guard_audit.json"
DEFAULT_GUARD_FALLBACK = REPO_ROOT / "data" / "runtime_import" / "sl_intra_guard_audit.json"


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


def to_probability(value):
    prob = as_float(value)
    if prob is None:
        return None
    return prob / 100.0 if prob > 1 else prob


def _normalize_text(value):
    return " ".join(str(value or "").strip().lower().split())


def _record_question_text(record: dict) -> str:
    question = str(record.get("question") or "").strip()
    if question:
        return question
    label = str(record.get("label") or "").strip()
    if label.startswith("Will the highest temperature") and "?" in label:
        return label[: label.index("?") + 1]
    return ""


def _question_signature(question: str):
    text = str(question or "").strip()
    if not text.startswith("Will the highest temperature in ") or "?" not in text:
        return None
    body = text[len("Will the highest temperature in ") : text.index("?")]
    def _parse_threshold(text_value: str):
        cleaned = (
            str(text_value or "")
            .replace("Â°", "")
            .replace("Âº", "")
            .replace("°", "")
            .replace("º", "")
            .replace("Â", "")
            .strip()
        )
        unit = cleaned[-1]
        value = float(cleaned[:-1])
        return value, unit

    if " be between " in body:
        city, rest = body.split(" be between ", 1)
        range_part, date_text = rest.split(" on ", 1)
        low_text, high_unit = range_part.split("-", 1)
        low, unit = _parse_threshold(low_text + high_unit[-1])
        high, unit = _parse_threshold(high_unit)
        condition = "range"
    elif " be " in body and " or higher on " in body:
        city, rest = body.split(" be ", 1)
        threshold_unit, date_text = rest.split(" or higher on ", 1)
        low, unit = _parse_threshold(threshold_unit)
        high = None
        condition = "at_or_above"
    elif " be " in body and " or below on " in body:
        city, rest = body.split(" be ", 1)
        threshold_unit, date_text = rest.split(" or below on ", 1)
        low, unit = _parse_threshold(threshold_unit)
        high = None
        condition = "at_or_below"
    elif " be " in body and " on " in body:
        city, rest = body.split(" be ", 1)
        threshold_unit, date_text = rest.split(" on ", 1)
        low, unit = _parse_threshold(threshold_unit)
        high = None
        condition = "exact"
    else:
        return None

    def _to_celsius(value):
        if unit.upper() == "F":
            return round((value - 32.0) * 5.0 / 9.0, 1)
        return round(value, 1)

    return {
        "city": city.strip(),
        "date_text": date_text.strip(),
        "condition": condition,
        "threshold_c": _to_celsius(low),
        "threshold_high_c": _to_celsius(high) if high is not None else None,
    }


def _resolution_lookup_key(city: str, date_iso: str, side: str, question: str = ""):
    parsed = _question_signature(question)
    condition = parsed.get("condition") if parsed else ""
    threshold_c = parsed.get("threshold_c") if parsed else None
    threshold_high_c = parsed.get("threshold_high_c") if parsed else None
    return (
        _normalize_text(city),
        str(date_iso or "").strip(),
        str(side or "").strip().upper(),
        condition,
        threshold_c,
        threshold_high_c,
    )


def normal_cdf(x, mu, sigma):
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def estimate_prob_with_sigma(
    forecast_max,
    threshold_c,
    condition,
    days_ahead,
    threshold_high_c=None,
):
    sigma = {0: 1.2, 1: 1.5, 2: 2.0, 3: 2.5}.get(
        days_ahead,
        3.0 if days_ahead <= 5 else 3.5,
    )
    if condition == "exact":
        prob = normal_cdf(threshold_c + 0.5, forecast_max, sigma) - normal_cdf(
            threshold_c - 0.5,
            forecast_max,
            sigma,
        )
    elif condition == "at_or_below":
        prob = normal_cdf(threshold_c + 0.5, forecast_max, sigma)
    elif condition == "at_or_above":
        prob = 1.0 - normal_cdf(threshold_c - 0.5, forecast_max, sigma)
    elif condition == "range" and threshold_high_c is not None:
        prob = normal_cdf(threshold_high_c + 0.5, forecast_max, sigma) - normal_cdf(
            threshold_c - 0.5,
            forecast_max,
            sigma,
        )
    else:
        prob = 0.5
    return max(0.01, min(0.99, prob))


def condition_happened(observed_temp_c, condition, threshold_c, threshold_high_c=None):
    if observed_temp_c is None or threshold_c is None:
        return None
    if condition == "exact":
        return threshold_c - 0.5 <= observed_temp_c <= threshold_c + 0.5
    if condition == "at_or_below":
        return observed_temp_c <= threshold_c + 0.5
    if condition == "at_or_above":
        return observed_temp_c >= threshold_c - 0.5
    if condition == "range" and threshold_high_c is not None:
        return threshold_c - 0.5 <= observed_temp_c <= threshold_high_c + 0.5
    return None


def infer_threshold_from_prob(forecast_max, condition, side, side_prob, days_ahead):
    if forecast_max is None or condition not in {"exact", "at_or_below", "at_or_above", "range"}:
        return None, None
    target_yes = side_prob if side == "YES" else 1.0 - side_prob
    best_low = None
    best_high = None
    best_gap = float("inf")
    start = int(math.floor(forecast_max - 25.0))
    end = int(math.ceil(forecast_max + 25.0))
    for step in range(start * 10, end * 10 + 1):
        low = step / 10.0
        width_options = [1.0, 0.6, 1.1] if condition == "range" else [None]
        for width in width_options:
            high = round(low + width, 1) if width is not None else None
            prob_yes = estimate_prob_with_sigma(
                forecast_max,
                low,
                condition,
                days_ahead,
                high,
            )
            gap = abs(prob_yes - target_yes)
            if gap < best_gap:
                best_gap = gap
                best_low = low
                best_high = high
    if best_gap > 0.08:
        return None, None
    return best_low, best_high


def load_resolution_stations():
    try:
        import bot  # type: ignore

        return dict(getattr(bot, "RESOLUTION_STATIONS", {}))
    except Exception:
        return {}


def fetch_open_meteo_observed_max(city: str, date_iso: str, resolution_stations: dict):
    station = resolution_stations.get(city, {})
    lat = station.get("lat")
    lon = station.get("lon")
    if lat is None or lon is None or not date_iso:
        return None, None
    params = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": date_iso,
            "end_date": date_iso,
            "daily": "temperature_2m_max",
            "timezone": "UTC",
        }
    )
    req = urllib.request.Request(f"https://archive-api.open-meteo.com/v1/archive?{params}")
    req.add_header("User-Agent", "sl-retrospective/1.0")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None, None
    temps = payload.get("daily", {}).get("temperature_2m_max", [])
    temp_c = as_float(temps[0] if temps else None)
    if temp_c is None:
        return None, None
    return round(temp_c, 1), "open_meteo_archive"


def fetch_live_observed_row(record: dict, resolution_stations: dict):
    observed_real, source = fetch_open_meteo_observed_max(
        str(record.get("city") or "").strip(),
        str(record.get("date") or "").strip(),
        resolution_stations,
    )
    if observed_real is None:
        return None
    return {
        "observed_temp_c": observed_real,
        "source": source or "",
        "observed_dataset": source or "",
    }


def load_resolution_fallback_rows(path: Path = DEFAULT_FORECAST_ACCURACY_FILE):
    payload = load_json(path, required=False) or {}
    rows = payload.get("trades") or payload.get("rows") or []
    by_id = {}
    by_key = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        outcome_correct = row.get("outcome_correct")
        if outcome_correct not in {True, False}:
            continue
        row_id = str(row.get("id") or "").strip()
        if row_id:
            by_id[row_id] = row
        key = (
            _normalize_text(row.get("city")),
            str(row.get("date_iso") or "").strip(),
            str(row.get("side") or "").strip().upper(),
            str(row.get("condition") or "").strip(),
            as_float(row.get("threshold_c")),
            as_float(row.get("threshold_high_c")),
        )
        by_key[key] = row
    return {"by_id": by_id, "by_key": by_key}


def load_observed_vs_forecast_rows(path: Path = DEFAULT_AUDIT_FILE):
    payload = load_json(path, required=False) or {}
    rows = payload.get("observed_vs_forecast") or []
    by_city_date = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        observed_temp_c = as_float(row.get("observed_temp_c"))
        date_iso = str(row.get("date") or "").strip()
        city = _normalize_text(row.get("city"))
        if observed_temp_c is None or not city or not date_iso:
            continue
        key = (city, date_iso)
        previous = by_city_date.get(key)
        if previous is None or str(row.get("checked_at") or "") >= str(previous.get("checked_at") or ""):
            by_city_date[key] = row
    return {"by_city_date": by_city_date}


def infer_observed_vs_forecast_verdict(record: dict, audit_lookup: dict, resolution_stations: dict | None = None):
    key = (
        _normalize_text(record.get("city")),
        str(record.get("date") or "").strip(),
    )
    row = (audit_lookup.get("by_city_date") or {}).get(key)
    if row is None and resolution_stations:
        row = fetch_live_observed_row(record, resolution_stations)
    if row is None:
        return None

    observed_real = as_float(row.get("observed_temp_c"))
    if observed_real is None:
        return None

    parsed = _question_signature(_record_question_text(record))
    condition = parsed.get("condition") if parsed else str(record.get("condition") or "").strip()
    threshold_c = parsed.get("threshold_c") if parsed else None
    threshold_high_c = parsed.get("threshold_high_c") if parsed else None

    if threshold_c is None:
        snapshots = [record.get("entry_context") or {}, record.get("latest_entry_context") or {}]
        snapshots.extend(record.get("buys") or [])
        for snapshot in snapshots:
            forecast_max = as_float(snapshot.get("forecast_max"))
            side_prob = to_probability(snapshot.get("our_prob"))
            days_ahead = snapshot.get("days_ahead")
            if (
                forecast_max is None
                or side_prob is None
                or days_ahead is None
                or not condition
            ):
                continue
            threshold_c, threshold_high_c = infer_threshold_from_prob(
                forecast_max,
                condition,
                str(record.get("side") or "").strip().upper(),
                side_prob,
                int(days_ahead),
            )
            if threshold_c is not None:
                break

    actual_yes = condition_happened(observed_real, condition, threshold_c, threshold_high_c)
    if actual_yes is None:
        return None

    side = str(record.get("side") or "").strip().upper()
    outcome_correct = actual_yes if side == "YES" else not actual_yes
    return {
        "verdict": "RIGHT" if outcome_correct else "WRONG",
        "source": "observed_vs_forecast",
        "observed_real": observed_real,
        "observed_source": row.get("source") or row.get("observed_dataset") or "",
    }


def infer_resolution_verdict(record: dict, resolution_lookup: dict):
    row = None
    record_id = str(record.get("id") or "").strip()
    if record_id:
        row = (resolution_lookup.get("by_id") or {}).get(record_id)
    if row is None:
        key = _resolution_lookup_key(
            record.get("city"),
            record.get("date"),
            record.get("side"),
            _record_question_text(record),
        )
        row = (resolution_lookup.get("by_key") or {}).get(key)
    if row is None:
        return None
    return {
        "verdict": "RIGHT" if row.get("outcome_correct") is True else "WRONG",
        "source": "resolved_outcome",
        "observed_real": as_float(row.get("observed_real")),
        "observed_source": row.get("observed_source") or "",
    }


def load_sl_rows(lifecycle_path: Path):
    payload = load_json(lifecycle_path)
    records = payload.get("records", []) if isinstance(payload, dict) else []
    resolution_lookup = load_resolution_fallback_rows()
    audit_path = lifecycle_path.parent / "audit.json"
    if not audit_path.exists():
        audit_path = DEFAULT_AUDIT_FILE
    audit_lookup = load_observed_vs_forecast_rows(audit_path)
    resolution_stations = load_resolution_stations()
    rows = []
    seen_order_ids = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        close_context = record.get("close_context") or {}
        close_reason = close_context.get("close_reason")
        if close_reason not in SL_REASONS:
            continue
        # Skip phantom legacy rows (shares==0 AND no token_id). The same trade
        # is indexed with a richer dated record; counting both inflates the
        # sample. Records missing total_shares entirely are left alone.
        total_shares = as_float(record.get("total_shares"))
        token_id = str(record.get("token_id") or "").strip()
        if total_shares == 0.0 and not token_id:
            continue
        # Dedup by close order_id across the few remaining records.
        order_id = str(close_context.get("order_id") or "").strip()
        if order_id:
            if order_id in seen_order_ids:
                continue
            seen_order_ids.add(order_id)
        post_exit = record.get("post_exit_analysis") or {}
        max_price = as_float(post_exit.get("max_price_after_close"))
        min_price = as_float(post_exit.get("min_price_after_close"))
        upside = as_float(post_exit.get("upside_left_cash_peak"))
        pnl_cash = as_float(close_context.get("pnl_cash"))
        close_shares = as_float(close_context.get("close_shares"))
        close_price = as_float(close_context.get("close_price"))
        market_seen = bool(post_exit.get("market_seen_after_close"))
        reached_98 = bool(post_exit.get("reached_98_after_close"))
        fallback = None
        if reached_98 or (max_price is not None and max_price >= 0.85):
            verdict = "RIGHT"
            verdict_source = "post_exit_market_data"
        elif market_seen and max_price is not None and max_price <= 0.15:
            verdict = "WRONG"
            verdict_source = "post_exit_market_data"
        else:
            verdict = "UNKNOWN"
            verdict_source = ""
        if verdict == "UNKNOWN":
            fallback = infer_observed_vs_forecast_verdict(record, audit_lookup, resolution_stations)
            if fallback is None:
                fallback = infer_resolution_verdict(record, resolution_lookup)
            if fallback is not None:
                verdict = fallback["verdict"]
                verdict_source = fallback["source"]
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
                "close_reason": close_reason,
                "verdict": verdict,
                "verdict_source": verdict_source,
                "reached_98_after_close": reached_98,
                "max_price_after_close": max_price,
                "min_price_after_close": min_price,
                "market_seen_after_close": market_seen,
                "observed_real": (fallback or {}).get("observed_real"),
                "observed_source": (fallback or {}).get("observed_source") or "",
                "upside_left_cash_peak": upside,
                "pnl_without_sl_best": pnl_without_sl_best,
                "pnl_without_sl_worst": pnl_without_sl_worst,
                "delta_vs_sl_best": delta_vs_sl_best,
                "delta_vs_sl_worst": delta_vs_sl_worst,
            }
        )
    rows.sort(key=lambda row: str(row.get("closed_at") or ""), reverse=True)
    return rows


def _summarize_type(rows: list[dict], close_reason: str) -> dict:
    sub = [r for r in rows if r.get("close_reason") == close_reason]
    n_right = sum(1 for r in sub if r["verdict"] == "RIGHT")
    n_wrong = sum(1 for r in sub if r["verdict"] == "WRONG")
    n_unknown = sum(1 for r in sub if r["verdict"] == "UNKNOWN")
    n_resolved = n_right + n_wrong
    return {
        "n": len(sub),
        "n_right": n_right,
        "n_wrong": n_wrong,
        "n_unknown": n_unknown,
        "n_resolved": n_resolved,
        "accuracy_pct": (n_right / n_resolved * 100.0) if n_resolved else None,
    }


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
        elif accuracy_pct is not None and accuracy_pct < 30:
            verdict_brief = "SL funciona correctamente"
        else:
            verdict_brief = "seguir monitorizando"
    verdict_is_conclusive = verdict_brief in {
        "SL corta posiciones correctas",
        "SL funciona correctamente",
    }
    if threshold_final and verdict_is_conclusive:
        verdict_final = verdict_brief + " (firme)"
    elif threshold_final:
        verdict_final = "seguir monitorizando"
    else:
        verdict_final = ""
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
        "by_type": {
            "stop_loss": _summarize_type(rows, "stop_loss"),
            "stop_loss_intra": _summarize_type(rows, "stop_loss_intra"),
        },
    }


def _load_guard_state(path=None) -> dict:
    paths = [Path(path)] if path is not None else [DEFAULT_GUARD_FILE, DEFAULT_GUARD_FALLBACK]
    for candidate in paths:
        try:
            if not candidate.exists():
                continue
            raw = candidate.read_text(encoding="utf-8-sig").strip()
            if not raw:
                return {}
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                rows = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(row, dict):
                        rows.append(row)
                return {"skips": rows} if rows else {}
            if isinstance(payload, dict):
                normalized = dict(payload)
                if "skips" in normalized and not isinstance(normalized.get("skips"), list):
                    normalized["skips"] = []
                return normalized
            if isinstance(payload, list):
                return {"skips": [row for row in payload if isinstance(row, dict)]}
            return {}
        except Exception:
            continue
    return {}


def _phase_iso(value: str | None) -> str:
    return str(value or "").strip().replace("Z", "+00:00")


def _rows_in_phase(rows, lo, hi) -> list:
    lo_key = _phase_iso(lo) if lo else ""
    hi_key = _phase_iso(hi) if hi else ""
    selected = []
    for row in rows:
        closed_at = _phase_iso(row.get("closed_at"))
        if not closed_at:
            continue
        if lo_key and closed_at < lo_key:
            continue
        if hi_key and closed_at >= hi_key:
            continue
        selected.append(row)
    return selected


def _phase_summaries(rows) -> dict:
    return {
        "F1": summarize(_rows_in_phase(rows, None, PHASE_F1_CUTOFF)),
        "F2": summarize(_rows_in_phase(rows, PHASE_F1_CUTOFF, PHASE_F2_CUTOFF)),
        "F3": summarize(_rows_in_phase(rows, PHASE_F2_CUTOFF, None)),
    }


def _guard_skip_rows(guard_state: dict | None) -> list:
    skips = (guard_state or {}).get("skips") if isinstance(guard_state, dict) else []
    if not isinstance(skips, list):
        skips = []
    return [row for row in skips if isinstance(row, dict)]


def _fmt_guard_ts(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:19].replace("T", " ")


def _build_current_config_block(phase_summaries: dict | None, guard_state: dict | None) -> list[str]:
    phases = phase_summaries or {}
    f3 = phases.get("F3") or {
        "n_right": 0,
        "n_wrong": 0,
        "n_unknown": 0,
        "n_resolved": 0,
        "accuracy_pct": None,
    }
    f3_right = f3.get("n_right", 0)
    f3_wrong = f3.get("n_wrong", 0)
    f3_unknown = f3.get("n_unknown", 0)
    f3_resolved = f3.get("n_resolved", f3_right + f3_wrong)
    total_f3 = f3_right + f3_wrong + f3_unknown
    min_sample = globals().get("MIN_CURRENT_CONFIG_SAMPLE", 5)
    skips = _guard_skip_rows(guard_state)
    skip_times = sorted(str(row.get("skipped_at") or "") for row in skips if row.get("skipped_at"))

    lines = [
        "──────────────────────────",
        f"📦 Config actual (post-guard v10.6.40, desde {PHASE_F2_CUTOFF[:10]}):",
        (
            f"  • n={total_f3} | falsas={f3_right} | correctos={f3_wrong} | "
            f"pendientes={f3_unknown} | resueltos={f3_resolved}"
        ),
    ]
    if f3_resolved < min_sample:
        lines.append(
            f"  ⚠️ Muestra insuficiente (n={f3_resolved}/{min_sample} mín) — sin veredicto config actual"
        )
    lines.extend(
        [
            "",
            "🛡️ Guard SL_intra:",
            f"  • {len(skips)} skip(s) registrados",
        ]
    )
    if skip_times:
        lines.append(f"  • desde {_fmt_guard_ts(skip_times[0])}")
    else:
        lines.append("  • sin skips registrados o sin datos suficientes")
    lines.append("──────────────────────────")
    return lines


def _current_config_verdict_lines(phase_summaries: dict | None) -> list[str]:
    f3 = (phase_summaries or {}).get("F3") or {}
    f3_resolved = f3.get("n_resolved", 0)
    f3_acc = f3.get("accuracy_pct")
    min_sample = globals().get("MIN_CURRENT_CONFIG_SAMPLE", 5)
    if f3_resolved < min_sample:
        return ["⚠️ Config actual post-guard: muestra insuficiente — seguir monitorizando"]
    if f3_acc is not None and f3_acc < 30:
        return ["✅ Config actual post-guard: funcionando correctamente"]
    if f3_acc is not None and f3_acc >= 60:
        return ["⚠️ Config actual: tasa de falsas alta — revisar"]
    return ["📊 Config actual: zona gris — seguir monitorizando"]


def build_message(
    summary: dict,
    *,
    phase_summaries: dict | None = None,
    guard_state: dict | None = None,
):
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
            peak_note = ""
            if (
                row.get("pnl_without_sl_best") is not None
                and row.get("pnl_cash_with_sl") is not None
                and row["pnl_without_sl_best"] > row["pnl_cash_with_sl"]
            ):
                peak_note = " ⚠️ pico temporal"
            lines.append(
                f"  • {row['label']}: con SL {row['pnl_cash_with_sl']:+.2f}$ → "
                f"sin SL {row['pnl_without_sl_best']:+.2f}${peak_note}"
            )
        lines.append("")

    by_type = summary.get("by_type", {})
    sl_main = by_type.get("stop_loss", {})
    sl_intra = by_type.get("stop_loss_intra", {})
    if sl_main.get("n", 0) > 0 or sl_intra.get("n", 0) > 0:
        lines.append("📋 Por tipo de SL:")
        for label, t in [("Ciclo principal (stop_loss)", sl_main), ("Intra-ciclo (stop_loss_intra)", sl_intra)]:
            n_t = t.get("n", 0)
            if n_t == 0:
                continue
            nr = t.get("n_right", 0)
            nw = t.get("n_wrong", 0)
            nu = t.get("n_unknown", 0)
            acc = t.get("accuracy_pct")
            acc_str = f" → {acc:.0f}% falsas salidas" if acc is not None else ""
            gray_note = " ⚠️ zona gris" if acc is not None and 30 <= acc <= 60 else ""
            lines.append(f"  • {label}: n={n_t}, falsas={nr}, correctos={nw}, pend={nu}{acc_str}{gray_note}")
        lines.append("")

    block_builder = globals().get("_build_current_config_block")
    if callable(block_builder):
        lines.extend(block_builder(phase_summaries, guard_state))
        lines.append("")

    conclusive = False
    verdict_brief = summary.get("preliminary_verdict") or "acumulando datos"
    if accuracy_pct is not None and accuracy_pct >= 60 and summary["threshold_preliminary"]:
        lines.append("⚠️ VEREDICTO PRELIMINAR: EL SL ESTÁ CORTANDO POSICIONES CORRECTAS")
        lines.append("→ Revisar gestión de posiciones en checkpoint Apr 28")
        conclusive = True
    elif accuracy_pct is not None and accuracy_pct < 30 and summary["threshold_preliminary"]:
        lines.append("✅ VEREDICTO PRELIMINAR: EL SL ESTÁ FUNCIONANDO CORRECTAMENTE")
        conclusive = True
    else:
        lines.append(
            f"📊 VEREDICTO: zona gris ({n_right} SLs acabaron ganando sin el corte) — seguimos monitorizando"
        )

    if summary["threshold_final"] and conclusive:
        lines.append("")
        lines.append(f"📊 Veredicto histórico: {verdict_brief.upper()}")
        lines.append(f"   ({n_resolved} SLs — histórico mezclado F1+F2+F3)")
        current_verdict = globals().get("_current_config_verdict_lines")
        if callable(current_verdict):
            lines.extend(current_verdict(phase_summaries))
    elif summary["threshold_final"]:
        lines.append("")
        lines.append(f"📊 Veredicto histórico: {verdict_brief.upper()}")
        lines.append(f"   ({n_resolved} SLs — histórico mezclado F1+F2+F3)")
        lines.append("🔁 Muestra completa pero señal no concluyente — seguir monitorizando")

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
    phases = _phase_summaries(rows)
    guard = _load_guard_state()
    message = build_message(summary, phase_summaries=phases, guard_state=guard)
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
