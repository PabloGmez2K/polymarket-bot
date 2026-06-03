#!/usr/bin/env python3
"""
Canonical outcome resolver helpers for offline decision learning datasets.

LOG_ONLY utilities only. This module does not import bot.py, place orders,
read environment trading knobs, or write production state.
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any

GAMMA_URL = "https://gamma-api.polymarket.com"
WIN_THRESHOLD = 0.95
T7_DAYS = 7
DAILY_TEMP_TAG_ID = "103040"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


@dataclass(frozen=True)
class Settlement:
    settled: bool
    yes_price: float | None
    no_price: float | None
    resolved_at: str | None
    market_outcome: str | None


def _api_get(endpoint: str, retries: int = 3, delay: float = 3.0) -> Any:
    url = GAMMA_URL + endpoint
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "canonical-decision-resolver/1.0")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(delay)
    raise RuntimeError(f"Gamma API failed for {endpoint}: {last_err}") from last_err


def fetch_market_by_id(market_id: str) -> dict | None:
    """Return a Gamma market dict from /markets/{id}, or None if unavailable."""
    try:
        result = _api_get(f"/markets/{market_id}")
        if isinstance(result, dict) and result:
            return result
        return None
    except Exception:
        return None


def extract_prices(market: dict) -> tuple[float | None, float | None]:
    """Return (yes_price, no_price) from Gamma outcomePrices."""
    raw = market.get("outcomePrices", "[]")
    try:
        prices = json.loads(raw) if isinstance(raw, str) else raw
        if len(prices) >= 2:
            return float(prices[0]), float(prices[1])
    except Exception:
        pass
    return None, None


def determine_settlement(market: dict | None) -> tuple[bool, float | None, float | None, str | None]:
    """
    Proto-R2 compatible settlement tuple:
    (settled, yes_price, no_price, resolved_at_iso).
    """
    if market is None:
        return False, None, None, None

    yes_price, no_price = extract_prices(market)
    if yes_price is None or no_price is None:
        return False, None, None, None

    settled = yes_price >= WIN_THRESHOLD or no_price >= WIN_THRESHOLD
    resolved_at = market.get("endDate") or market.get("resolutionTime") or None
    return settled, yes_price, no_price, resolved_at


def fetch_outcome(market_id: str) -> Settlement:
    """Fetch and classify official Gamma settlement for a market id."""
    market = fetch_market_by_id(market_id)
    settled, yes_price, no_price, resolved_at = determine_settlement(market)
    market_outcome: str | None = None
    if settled and yes_price is not None and no_price is not None:
        market_outcome = "NO" if no_price >= WIN_THRESHOLD else "YES"
    return Settlement(settled, yes_price, no_price, resolved_at, market_outcome)


def _normalize_gamma_question(text: str) -> str:
    return text.lower().strip().rstrip("?").rstrip(".")


def _question_from_eval_key(eval_key: str) -> str | None:
    parts = eval_key.split("|")
    if len(parts) != 5:
        return None
    city, date_iso, condition, threshold, unit = parts
    try:
        _, month, day = date_iso.split("-")
        month_name = MONTHS[int(month) - 1]
        day_number = str(int(day))
    except Exception:
        return None

    city_lower = city.lower()
    unit_lower = unit.lower()
    if condition == "at_or_above":
        return _normalize_gamma_question(
            f"will the highest temperature in {city_lower} be "
            f"{threshold}deg{unit_lower} or higher on {month_name} {day_number}"
        )
    if condition == "at_or_below":
        return _normalize_gamma_question(
            f"will the highest temperature in {city_lower} be "
            f"{threshold}deg{unit_lower} or below on {month_name} {day_number}"
        )
    return None


def fetch_market_by_eval_key(eval_key: str, tag_id: str = DAILY_TEMP_TAG_ID) -> dict | None:
    """Return a closed Gamma temperature market matching an eval_key question."""
    target = _question_from_eval_key(eval_key)
    if target is None:
        return None
    offset = 0
    page_size = 100
    while True:
        try:
            events = _api_get(
                f"/events?tag_id={tag_id}&closed=true&limit={page_size}"
                f"&offset={offset}&order=startDate&ascending=false"
            )
        except Exception:
            return None
        if not events:
            return None
        for event in events:
            for market in event.get("markets", []):
                question = str(market.get("question") or "")
                normalized = _normalize_gamma_question(
                    question.replace(chr(176), "deg").replace(" degrees ", "deg")
                )
                if normalized == target:
                    return market
        if len(events) < page_size:
            return None
        offset += page_size


def fetch_outcome_by_eval_key(eval_key: str) -> Settlement:
    """Fetch and classify official Gamma settlement for a directional eval_key."""
    market = fetch_market_by_eval_key(eval_key)
    settled, yes_price, no_price, resolved_at = determine_settlement(market)
    market_outcome: str | None = None
    if settled and yes_price is not None and no_price is not None:
        market_outcome = "NO" if no_price >= WIN_THRESHOLD else "YES"
    return Settlement(settled, yes_price, no_price, resolved_at, market_outcome)


def fetch_outcomes_by_eval_key(eval_keys: list[str], tag_id: str = DAILY_TEMP_TAG_ID) -> dict[str, Settlement]:
    """Bulk official Gamma lookup for directional eval_keys."""
    targets = {key: _question_from_eval_key(key) for key in eval_keys}
    wanted = {question for question in targets.values() if question is not None}
    if not wanted:
        return {}

    by_question: dict[str, Settlement] = {}
    offset = 0
    page_size = 100
    while wanted - set(by_question):
        try:
            events = _api_get(
                f"/events?tag_id={tag_id}&closed=true&limit={page_size}"
                f"&offset={offset}&order=startDate&ascending=false"
            )
        except Exception:
            break
        if not events:
            break
        for event in events:
            for market in event.get("markets", []):
                question = str(market.get("question") or "")
                normalized = _normalize_gamma_question(
                    question.replace(chr(176), "deg").replace(" degrees ", "deg")
                )
                if normalized not in wanted:
                    continue
                settled, yes_price, no_price, resolved_at = determine_settlement(market)
                market_outcome: str | None = None
                if settled and yes_price is not None and no_price is not None:
                    market_outcome = "NO" if no_price >= WIN_THRESHOLD else "YES"
                by_question[normalized] = Settlement(
                    settled,
                    yes_price,
                    no_price,
                    resolved_at,
                    market_outcome,
                )
        if len(events) < page_size:
            break
        offset += page_size

    return {
        key: by_question[question]
        for key, question in targets.items()
        if question is not None and question in by_question
    }


def classify_maturity(date_iso: str, settled: bool, today: date) -> str:
    try:
        d = date.fromisoformat(date_iso)
    except ValueError:
        return "pending"
    days_ago = (today - d).days
    if not settled or days_ago < 0:
        return "pending"
    if days_ago >= T7_DAYS:
        return "settled_mature"
    return "resolved_fresh"


def classify_bucket(date_iso: str, settled: bool, today: date) -> str:
    """Backward-compatible alias for Proto-R2 tests and tools."""
    return classify_maturity(date_iso, settled, today)


def simulated_unit_pnl(side_won: bool | None, price_at_eval: float | None) -> float | None:
    """
    Unit PnL per theoretical share bought at price_at_eval.
    win -> 1 - price; lose -> -price.
    """
    if side_won is None or price_at_eval is None:
        return None
    return (1.0 - price_at_eval) if side_won else -price_at_eval


def calibration_gap_component(model_prob: float | None, outcome01: bool | int | float | None) -> float | None:
    """Return model_prob - observed outcome, rounded as Proto-R2 does."""
    if model_prob is None or outcome01 is None:
        return None
    observed = 1.0 if bool(outcome01) else 0.0
    return round(model_prob - observed, 6)


def bsr_no_would_win(bsr_row: dict) -> bool | None:
    """Derive whether NO won from a resolved BSR trader-centric row."""
    outcome = (bsr_row.get("outcome") or "").strip()
    win = bsr_row.get("win_for_trader")
    if win is None:
        return None
    if outcome == "No":
        return bool(win)
    if outcome == "Yes":
        return not bool(win)
    return None


def load_bsr(bsr_path) -> dict[str, dict]:
    """Load resolved BSR rows keyed by match_key."""
    index: dict[str, dict] = {}
    if not bsr_path.exists():
        return index
    with open(bsr_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("resolved"):
                match_key = row.get("match_key") or ""
                if match_key:
                    index[match_key] = row
    return index


def cross_check_bsr(
    eval_key: str,
    no_would_win: bool | None,
    bsr_index: dict[str, dict],
) -> tuple[bool, str | None]:
    """Return (ok, error_msg) for Gamma-vs-BSR NO outcome consistency."""
    bsr_row = bsr_index.get(eval_key)
    if bsr_row is None or no_would_win is None:
        return True, None
    bsr_win = bsr_no_would_win(bsr_row)
    if bsr_win is None or bsr_win == no_would_win:
        return True, None
    return False, (
        f"MISMATCH eval_key={eval_key}: "
        f"Gamma no_would_win={no_would_win}, BSR no_would_win={bsr_win} "
        f"(bsr outcome={bsr_row.get('outcome')}, win_for_trader={bsr_row.get('win_for_trader')})"
    )


def dedup_groups(rows: list[dict]) -> list[dict]:
    """
    Deduplicate by (market_id, condition_id, eval_key).
    Entry edge is the first capture by ts_utc; max edge is metadata only.
    """
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row.get("market_id", ""), row.get("condition_id", ""), row.get("eval_key", ""))
        groups.setdefault(key, []).append(row)

    result: list[dict] = []
    for group_rows in groups.values():
        sorted_rows = sorted(group_rows, key=lambda r: r.get("ts_utc", ""))
        first = sorted_rows[0]
        edges = [
            r.get("best_edge_pct_log_only")
            for r in sorted_rows
            if r.get("best_edge_pct_log_only") is not None
        ]
        rep = dict(first)
        rep["_entry_edge"] = first.get("best_edge_pct_log_only")
        rep["_max_edge"] = max(edges) if edges else None
        rep["_duplicate_count"] = len(sorted_rows)
        return_row = rep
        result.append(return_row)
    return result


def side_won_from_outcome(side: str | None, resolution_outcome: str | None) -> bool | None:
    if side not in {"YES", "NO"} or resolution_outcome not in {"YES", "NO"}:
        return None
    return side == resolution_outcome
