"""Private helper for bot_brain.py --scope self_evaluation.

BOT_SELF_EVALUATION_OUTCOME_LOOP_V1 — stateless read-only Brier calibration report.

H1 pre-registered 2026-05-29:
  El predictor actual sobreestima YES en at_or_above.
  Una modificación futura de calibración solo podrá considerarse útil
  si obtiene brier_advantage > 0 frente al mercado en forward_holdout independiente.

No BUY/SELL/SKIP. No BANKROLL. No DB writes. No Railway writes.
No Weather Truth. No canonical settlement. No policy authorization.
eligible_for_policy=false. live_policy_eligible=false. market_truth_canonical=false.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_GAMMA_URL = "https://gamma-api.polymarket.com"
_DAILY_TEMP_TAG_ID = "103040"
_WIN_PRICE_THRESHOLD = 0.95
_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

# H1 cutoff: predictions before this date are evidence_frozen.
# Corresponds to pre-registration of H1 hypothesis in this contract.
SELF_EVAL_H1_PREREG_CUTOFF_UTC = datetime(2026, 5, 29, 0, 0, 0, tzinfo=timezone.utc)

SUPPORTED_CONDITIONS: frozenset[str] = frozenset({"at_or_above", "at_or_below"})

_SEOUL_NAMES: frozenset[str] = frozenset({"seoul", "서울"})

_H1_HYPOTHESIS = (
    "El predictor actual sobreestima YES en at_or_above. "
    "Una modificación futura de calibración solo podrá considerarse útil "
    "si obtiene brier_advantage > 0 frente al mercado "
    "en forward_holdout independiente."
)

_V1_DISCLAIMER = (
    "LOG_ONLY / NO_ACTION. Stateless read-only calibration report. "
    "eligible_for_policy=false. live_policy_eligible=false. "
    "market_truth_canonical=false. weather_truth_available=false. "
    "pnl_canonical_confirmed=false. No trading authorization."
)

# H2: market-anchored calibration candidate — pre-registered 2026-05-29T20:52:29Z
H2_CANDIDATE_MODEL_ID = "market_anchored_blend_v1_lambda050"
H2_CANDIDATE_HYPOTHESIS_ID = "H2_MARKET_ANCHORED_CALIBRATION_AT_OR_ABOVE"
H2_LAMBDA_PRIMARY: float = 0.5
H2_LAMBDA_DIAGNOSTIC: tuple[float, float] = (0.3, 0.7)
H2_PREREG_CUTOFF_UTC = datetime(2026, 5, 29, 20, 52, 29, tzinfo=timezone.utc)

_H2_HYPOTHESIS = (
    "H2: El predictor baseline sobreestima YES en at_or_above. "
    "Un candidato market-anchored fijo: "
    "candidate_prob_yes = 0.5 * our_prob_yes + 0.5 * mkt_prob_yes "
    "reducira el Brier frente al baseline en holdout independiente. "
    "H2 no afirma que el candidato bata al mercado. "
    "H2 no afirma causalidad sobre FORECAST_BIAS_C o sigma. "
    "H2 no autoriza trading. LOG_ONLY."
)

# Callable: eval_key -> "YES" | "NO" | None
GammaLookupFn = Callable[[str], "str | None"]


# ── IO helpers ────────────────────────────────────────────────────────────────

def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], bool]:
    if not path.exists():
        return [], False
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except Exception:
                continue
        return rows, True
    except Exception:
        return [], False


# ── Timestamp helper ──────────────────────────────────────────────────────────

def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
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


# ── Source fidelity exclusion ─────────────────────────────────────────────────

def _is_source_fidelity_suspect(row: dict[str, Any]) -> bool:
    """Exclude Seoul rows (source station mismatch history)."""
    return str(row.get("city") or "").strip().casefold() in _SEOUL_NAMES


# ── Deduplication ─────────────────────────────────────────────────────────────

def _deduplicate_by_eval_key(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep latest row per eval_key by ts_utc. Deterministic."""
    by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("eval_key") or "").strip()
        if not key:
            continue
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
        else:
            ts_new = _parse_ts(row.get("ts_utc"))
            ts_old = _parse_ts(existing.get("ts_utc"))
            if ts_new is not None and (ts_old is None or ts_new > ts_old):
                by_key[key] = row
    return list(by_key.values())


# ── Partition ─────────────────────────────────────────────────────────────────

def _partition(
    rows: list[dict[str, Any]],
    cutoff: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split into evidence_frozen (pre-cutoff) and forward_holdout (post-cutoff).

    Rows with no parseable ts_utc are treated as evidence_frozen.
    """
    evidence_frozen: list[dict[str, Any]] = []
    forward_holdout: list[dict[str, Any]] = []
    for row in rows:
        ts = _parse_ts(row.get("ts_utc"))
        if ts is None or ts < cutoff:
            evidence_frozen.append(row)
        else:
            forward_holdout.append(row)
    return evidence_frozen, forward_holdout


# ── Brier scoring ─────────────────────────────────────────────────────────────

def _brier(probs: list[float], outcomes: list[int]) -> float:
    """Brier score = mean((prob_yes - outcome_yes)^2). Caller ensures non-empty."""
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def _score_cohort(
    rows: list[dict[str, Any]],
    outcomes_map: dict[str, str],
) -> dict[str, Any]:
    """Score rows against known outcomes (eval_key -> 'YES'|'NO').

    our_prob and mkt_prob are stored as percentages (0-100) in BSE;
    divide by 100 for probability domain before Brier computation.
    """
    our_probs: list[float] = []
    mkt_probs: list[float] = []
    outcome_values: list[int] = []
    n_pending = 0
    n_side_explicit = 0
    n_side_inferred = 0

    for row in rows:
        key = str(row.get("eval_key") or "").strip()
        outcome_str = outcomes_map.get(key)
        if outcome_str not in ("YES", "NO"):
            n_pending += 1
            continue
        our_p_raw = row.get("our_prob")
        mkt_p_raw = row.get("mkt_prob")
        if our_p_raw is None or mkt_p_raw is None:
            n_pending += 1
            continue
        try:
            our_p = float(our_p_raw) / 100.0
            mkt_p = float(mkt_p_raw) / 100.0
        except (TypeError, ValueError):
            n_pending += 1
            continue

        our_probs.append(our_p)
        mkt_probs.append(mkt_p)
        outcome_values.append(1 if outcome_str == "YES" else 0)

        cand_src = str(row.get("candidate_side_source") or "").strip()
        side = str(row.get("side") or "").strip()
        if cand_src == "runtime_evaluation_explicit" and side:
            n_side_explicit += 1
        else:
            n_side_inferred += 1

    n_resolved = len(our_probs)
    brier_our: float | None = _brier(our_probs, outcome_values) if n_resolved > 0 else None
    brier_mkt: float | None = _brier(mkt_probs, outcome_values) if n_resolved > 0 else None
    brier_adv: float | None = (
        (brier_mkt - brier_our)  # type: ignore[operator]
        if (brier_our is not None and brier_mkt is not None)
        else None
    )
    mean_our: float | None = sum(our_probs) / n_resolved if n_resolved > 0 else None
    mean_mkt: float | None = sum(mkt_probs) / n_resolved if n_resolved > 0 else None
    yes_rate: float | None = sum(outcome_values) / n_resolved if n_resolved > 0 else None

    return {
        "n_resolved": n_resolved,
        "n_pending": n_pending,
        "n_side_explicit": n_side_explicit,
        "n_side_inferred_legacy": n_side_inferred,
        "mean_our_prob_yes": round(mean_our, 4) if mean_our is not None else None,
        "mean_mkt_prob_yes": round(mean_mkt, 4) if mean_mkt is not None else None,
        "observed_yes_rate": round(yes_rate, 4) if yes_rate is not None else None,
        "brier_our": round(brier_our, 4) if brier_our is not None else None,
        "brier_mkt": round(brier_mkt, 4) if brier_mkt is not None else None,
        "brier_advantage": round(brier_adv, 4) if brier_adv is not None else None,
        "eligible_for_policy": False,
        "live_policy_eligible": False,
    }


# ── Readiness ─────────────────────────────────────────────────────────────────

def _cohort_readiness(condition: str, partition: str, n_resolved: int) -> str:
    if partition == "evidence_frozen":
        if n_resolved == 0:
            return "OUTCOMES_NOT_RESOLVED"
        if condition == "at_or_above":
            return "CURRENT_PREDICTOR_NOT_CANDIDATE"
        if condition == "at_or_below":
            return "HYPOTHESIS_ONLY_INSUFFICIENT_SAMPLE"
        return "EVIDENCE_FROZEN_BASELINE"
    # forward_holdout
    if n_resolved >= 20:
        return "HOLDOUT_READY_FOR_OPUS_EXPERIMENT_REVIEW"
    return "HOLDOUT_ACCRUING"


# ── Gamma API helpers ─────────────────────────────────────────────────────────

def _gamma_api_get(endpoint: str, retries: int = 3, delay: float = 3.0) -> Any:
    url = _GAMMA_URL + endpoint
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-self-eval/1.0")
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read())
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay)
    raise last_error  # type: ignore[misc]


def _normalize_gamma_q(s: str) -> str:
    s = s.replace("┬░", "°")  # fix corrupted degree sign: ┬░ → °
    return s.lower().strip().rstrip("?").rstrip(".")


def _build_gamma_question_text(eval_key: str) -> str | None:
    """Build normalized Gamma question text from eval_key for closed-market lookup.

    Polymarket question format (as observed in gamma-api.polymarket.com):
      at_or_above: "will the highest temperature in {city} be {N}°{unit} or higher on {mon} {d}"
      at_or_below: "will the highest temperature in {city} be {N}°{unit} or below on {mon} {d}"
    """
    parts = eval_key.split("|")
    if len(parts) != 5:
        return None
    city, date_str, condition, threshold, unit = parts
    try:
        yr, mo, dy = date_str.split("-")
        month_name = _MONTHS[int(mo) - 1]
        day_no_zero = str(int(dy))
    except Exception:
        return None
    city_lower = city.lower()
    unit_lower = unit.lower()
    if condition == "at_or_above":
        return _normalize_gamma_q(
            f"will the highest temperature in {city_lower} be "
            f"{threshold}°{unit_lower} or higher on {month_name} {day_no_zero}"
        )
    if condition == "at_or_below":
        return _normalize_gamma_q(
            f"will the highest temperature in {city_lower} be "
            f"{threshold}°{unit_lower} or below on {month_name} {day_no_zero}"
        )
    return None


def _extract_gamma_outcome(market: dict[str, Any]) -> str | None:
    """YES if yes_price >= 0.95, NO if no_price >= 0.95, None if unresolved."""
    prices_raw = market.get("outcomePrices", "[]")
    try:
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        if len(prices) >= 2:
            yes_p = float(prices[0])
            no_p = float(prices[1])
            if yes_p >= _WIN_PRICE_THRESHOLD:
                return "YES"
            if no_p >= _WIN_PRICE_THRESHOLD:
                return "NO"
    except Exception:
        pass
    return None


def build_gamma_lookup_fn(
    tag_id: str = _DAILY_TEMP_TAG_ID,
    page_size: int = 100,
    request_delay: float = 0.3,
) -> "GammaLookupFn":
    """Fetch closed temperature markets from Gamma and return injectable lookup fn.

    Paginates /events with tag_id until exhausted; builds question-text index.
    Returns GammaLookupFn: eval_key -> "YES" | "NO" | None.
    Read-only. No writes. No BANKROLL. No trading authorization.
    """
    question_map: dict[str, str] = {}
    offset = 0

    while True:
        try:
            events = _gamma_api_get(
                f"/events?tag_id={tag_id}&closed=true&limit={page_size}"
                f"&offset={offset}&order=startDate&ascending=false"
            )
        except Exception:
            break
        if not events:
            break
        for event in events:
            for market in event.get("markets", []):
                question = str(market.get("question") or "").strip()
                if not question:
                    continue
                key = _normalize_gamma_q(question)
                outcome = _extract_gamma_outcome(market)
                if outcome is not None:
                    question_map[key] = outcome
        n = len(events)
        if request_delay > 0:
            time.sleep(request_delay)
        if n < page_size:
            break
        offset += page_size

    def _lookup(eval_key: str) -> str | None:
        q = _build_gamma_question_text(eval_key)
        if q is None:
            return None
        return question_map.get(q)

    return _lookup


# ── BSR-based outcome lookup ──────────────────────────────────────────────────

def _build_bsr_lookup(bsr_rows: list[dict[str, Any]]) -> GammaLookupFn:
    """Build lookup fn from BSR rows using outcome field (market YES/NO, not trader side)."""
    index: dict[str, str] = {}
    for row in bsr_rows:
        mk = str(row.get("match_key") or "").strip()
        if not mk:
            continue
        raw_outcome = str(row.get("outcome") or "").strip().lower()
        if raw_outcome in ("yes", "true", "1"):
            index[mk] = "YES"
        elif raw_outcome in ("no", "false", "0"):
            index[mk] = "NO"
    return lambda key: index.get(key)


# ── Outcome resolution ────────────────────────────────────────────────────────

def _resolve_outcomes(
    rows: list[dict[str, Any]],
    lookup_fn: GammaLookupFn,
) -> tuple[dict[str, str], int]:
    outcomes: dict[str, str] = {}
    failed = 0
    for row in rows:
        key = str(row.get("eval_key") or "").strip()
        if not key:
            continue
        try:
            result = lookup_fn(key)
            if result in ("YES", "NO"):
                outcomes[key] = result
            else:
                failed += 1
        except Exception:
            failed += 1
    return outcomes, failed


# ── Slug helper (for Gamma lookup, injectable) ───────────────────────────────

def build_gamma_slug_from_eval_key(eval_key: str) -> str | None:
    """Derive deterministic market slug from eval_key for Gamma closed-market lookup.

    Format: {city}|{date}|{condition}|{threshold}|{unit}
    Slug pattern: will-the-high-temperature-in-{city}-be-{threshold}-{unit}-or-higher-on-{date}
    Not used directly in this report; provided for external integration.
    """
    parts = eval_key.split("|")
    if len(parts) != 5:
        return None
    city, date, condition, threshold, unit = parts
    city_slug = city.lower().replace(" ", "-")
    unit_word = "celsius" if unit.upper() == "C" else "fahrenheit"
    date_parts = date.split("-")
    if len(date_parts) != 3:
        return None
    if condition == "at_or_above":
        return (
            f"will-the-high-temperature-in-{city_slug}-be-"
            f"{threshold}-degrees-{unit_word}-or-higher-on-"
            f"{date_parts[1]}-{date_parts[2]}-{date_parts[0]}"
        )
    if condition == "at_or_below":
        return (
            f"will-the-high-temperature-in-{city_slug}-be-"
            f"{threshold}-degrees-{unit_word}-or-lower-on-"
            f"{date_parts[1]}-{date_parts[2]}-{date_parts[0]}"
        )
    return None


# ── H2 candidate scoring ──────────────────────────────────────────────────────

def _row_is_h2_forward(row: dict[str, Any], h2_cutoff: datetime) -> bool:
    ts = _parse_ts(row.get("ts_utc"))
    return ts is not None and ts >= h2_cutoff


def _compute_h2_blend_metrics(
    our_probs: list[float],
    mkt_probs: list[float],
    outcomes: list[int],
    lambda_primary: float,
    lambda_diag: tuple[float, float],
) -> "dict[str, Any] | None":
    """Compute H2 blend candidate Brier metrics. Returns None if no rows."""
    n = len(our_probs)
    if n == 0:
        return None
    cands = [lambda_primary * o + (1 - lambda_primary) * m for o, m in zip(our_probs, mkt_probs)]
    cands_d0 = [lambda_diag[0] * o + (1 - lambda_diag[0]) * m for o, m in zip(our_probs, mkt_probs)]
    cands_d1 = [lambda_diag[1] * o + (1 - lambda_diag[1]) * m for o, m in zip(our_probs, mkt_probs)]
    b_base = _brier(our_probs, outcomes)
    b_cand = _brier(cands, outcomes)
    b_mkt = _brier(mkt_probs, outcomes)
    return {
        "n_resolved": n,
        "mean_candidate_prob_yes": round(sum(cands) / n, 4),
        "brier_baseline": round(b_base, 4),
        "brier_candidate": round(b_cand, 4),
        "brier_market": round(b_mkt, 4),
        "candidate_vs_baseline_advantage": round(b_base - b_cand, 4),
        "candidate_vs_market_advantage": round(b_mkt - b_cand, 4),
        "brier_lambda_diag_0": round(_brier(cands_d0, outcomes), 4),
        "brier_lambda_diag_1": round(_brier(cands_d1, outcomes), 4),
    }


def _score_h2_candidate_metrics(
    rows: list[dict[str, Any]],
    outcomes_map: dict[str, str],
    h2_cutoff: datetime,
    lambda_primary: float = H2_LAMBDA_PRIMARY,
    lambda_diag: tuple[float, float] = H2_LAMBDA_DIAGNOSTIC,
) -> dict[str, Any]:
    """Compute H2 market-anchored candidate Brier metrics for a cohort.

    Splits rows by h2_cutoff → forward (post-cutoff) and diagnostic (pre-cutoff).
    Forward metrics drive readiness. Diagnostic metrics are non-gating.
    LOG_ONLY. Not policy-eligible.
    """
    fwd_our: list[float] = []
    fwd_mkt: list[float] = []
    fwd_out: list[int] = []
    diag_our: list[float] = []
    diag_mkt: list[float] = []
    diag_out: list[int] = []

    for row in rows:
        key = str(row.get("eval_key") or "").strip()
        outcome_str = outcomes_map.get(key)
        if outcome_str not in ("YES", "NO"):
            continue
        our_raw = row.get("our_prob")
        mkt_raw = row.get("mkt_prob")
        if our_raw is None or mkt_raw is None:
            continue
        try:
            o = float(our_raw) / 100.0
            m = float(mkt_raw) / 100.0
        except (TypeError, ValueError):
            continue
        v = 1 if outcome_str == "YES" else 0
        if _row_is_h2_forward(row, h2_cutoff):
            fwd_our.append(o)
            fwd_mkt.append(m)
            fwd_out.append(v)
        else:
            diag_our.append(o)
            diag_mkt.append(m)
            diag_out.append(v)

    return {
        "n_h2_fwd_resolved": len(fwd_our),
        "n_h2_diag_resolved": len(diag_our),
        "forward_metrics": _compute_h2_blend_metrics(fwd_our, fwd_mkt, fwd_out, lambda_primary, lambda_diag),
        "diagnostic_metrics": _compute_h2_blend_metrics(diag_our, diag_mkt, diag_out, lambda_primary, lambda_diag),
    }


def _h2_candidate_readiness(
    h2_partition: str,
    n_h2_fwd_resolved: int,
    cand_vs_baseline: "float | None",
    cand_vs_market: "float | None",
) -> str:
    """H2 candidate readiness label. LOG_ONLY. Never authorizes policy."""
    if h2_partition == "h2_evidence_diagnostic_only":
        return "CANDIDATE_EVIDENCE_DIAGNOSTIC_ONLY"
    # h2_forward_holdout
    if n_h2_fwd_resolved < 20:
        return "CANDIDATE_HOLDOUT_ACCRUING"
    if cand_vs_baseline is None or cand_vs_baseline <= 0:
        return "CANDIDATE_FALSIFIED_NO_BASELINE_IMPROVEMENT"
    if cand_vs_market is None or cand_vs_market <= 0:
        return "CANDIDATE_BEATS_BASELINE_NOT_MARKET_OPUS_REVIEW"
    return "CANDIDATE_BEATS_BASELINE_AND_MARKET_OPUS_REVIEW"


# ── Main report builder ───────────────────────────────────────────────────────

def build_self_evaluation_report(
    data_dir: Path,
    gamma_lookup_fn: "GammaLookupFn | None" = None,
    now: "datetime | None" = None,
) -> dict[str, Any]:
    """Build V1 stateless self-evaluation calibration report.

    gamma_lookup_fn: inject mock in tests; falls back to BSR outcome index if None.
    No writes. No BANKROLL. No trading authorization.
    """
    now = now or datetime.now(timezone.utc)
    bse_path = data_dir / "bot_signal_evaluations.jsonl"
    bsr_path = data_dir / "blocked_signals_resolutions.jsonl"

    bse_rows, bse_ok = _read_jsonl(bse_path)
    bsr_rows, _bsr_ok = _read_jsonl(bsr_path)

    effective_lookup: GammaLookupFn = (
        gamma_lookup_fn if gamma_lookup_fn is not None
        else _build_bsr_lookup(bsr_rows)
    )

    # Filter for supported directional conditions
    directional = [r for r in bse_rows if r.get("condition") in SUPPORTED_CONDITIONS]

    # Exclude Seoul / source-fidelity suspect
    fidelity_suspect = [r for r in directional if _is_source_fidelity_suspect(r)]
    eligible = [r for r in directional if not _is_source_fidelity_suspect(r)]

    # Deduplicate by eval_key (keep latest)
    deduped = _deduplicate_by_eval_key(eligible)

    # Partition by H1 preregistration cutoff
    cutoff = SELF_EVAL_H1_PREREG_CUTOFF_UTC
    evidence_frozen, forward_holdout = _partition(deduped, cutoff)

    # Resolve outcomes for both partitions
    ef_outcomes, ef_failed = _resolve_outcomes(evidence_frozen, effective_lookup)
    fh_outcomes, fh_failed = _resolve_outcomes(forward_holdout, effective_lookup)
    gamma_lookup_failed = ef_failed + fh_failed

    # Score cohorts
    cohorts: list[dict[str, Any]] = []
    for condition in ("at_or_above", "at_or_below"):
        for partition_name, partition_rows, outcomes_map in (
            ("evidence_frozen", evidence_frozen, ef_outcomes),
            ("forward_holdout", forward_holdout, fh_outcomes),
        ):
            cond_rows = [r for r in partition_rows if r.get("condition") == condition]
            scored = _score_cohort(cond_rows, outcomes_map)
            readiness = _cohort_readiness(condition, partition_name, scored["n_resolved"])

            # H2 candidate fields
            h2_part = (
                "h2_evidence_diagnostic_only" if partition_name == "evidence_frozen"
                else "h2_forward_holdout"
            )
            h2_data = _score_h2_candidate_metrics(cond_rows, outcomes_map, H2_PREREG_CUTOFF_UTC)
            n_h2_fwd = h2_data["n_h2_fwd_resolved"]
            fwd_m = h2_data["forward_metrics"]
            diag_m = h2_data["diagnostic_metrics"]
            cand_vs_baseline = fwd_m["candidate_vs_baseline_advantage"] if fwd_m else None
            cand_vs_market = fwd_m["candidate_vs_market_advantage"] if fwd_m else None
            h2_readiness = _h2_candidate_readiness(h2_part, n_h2_fwd, cand_vs_baseline, cand_vs_market)
            # Report forward metrics when available; fall back to diagnostic for display
            active_m = fwd_m or diag_m

            cohorts.append({
                "condition": condition,
                "probability_basis": "YES",
                "partition": partition_name,
                **scored,
                "readiness": readiness,
                # H2 candidate
                "candidate_model_id": H2_CANDIDATE_MODEL_ID,
                "candidate_hypothesis_id": H2_CANDIDATE_HYPOTHESIS_ID,
                "candidate_lambda": H2_LAMBDA_PRIMARY,
                "h2_partition": h2_part,
                "n_h2_fwd_resolved": n_h2_fwd,
                "n_h2_diag_resolved": h2_data["n_h2_diag_resolved"],
                "mean_candidate_prob_yes": active_m["mean_candidate_prob_yes"] if active_m else None,
                "brier_baseline": active_m["brier_baseline"] if active_m else None,
                "brier_candidate": active_m["brier_candidate"] if active_m else None,
                "brier_market_h2": active_m["brier_market"] if active_m else None,
                "candidate_vs_baseline_advantage": cand_vs_baseline,
                "candidate_vs_market_advantage": cand_vs_market,
                "candidate_diagnostic_brier": {
                    "n_resolved": h2_data["n_h2_diag_resolved"],
                    "brier_lambda_03": diag_m["brier_lambda_diag_0"] if diag_m else None,
                    "brier_lambda_05": diag_m["brier_candidate"] if diag_m else None,
                    "brier_lambda_07": diag_m["brier_lambda_diag_1"] if diag_m else None,
                },
                "candidate_readiness": h2_readiness,
            })

    # Holdout accrual state — pending predictions never count toward readiness
    fh_n_above = sum(
        c.get("n_resolved") or 0
        for c in cohorts
        if c["condition"] == "at_or_above" and c["partition"] == "forward_holdout"
    )
    fh_n_below = sum(
        c.get("n_resolved") or 0
        for c in cohorts
        if c["condition"] == "at_or_below" and c["partition"] == "forward_holdout"
    )
    experiment_readiness = (
        "HOLDOUT_READY_FOR_OPUS_EXPERIMENT_REVIEW"
        if max(fh_n_above, fh_n_below) >= 20
        else "HOLDOUT_ACCRUING"
    )

    return {
        "matches_found": True,
        "schema_version": "bot_self_evaluation_outcome_loop_v1",
        "generated_at": now.isoformat(),
        "self_eval_h1_prereg_cutoff_utc": cutoff.isoformat(),
        "h1_hypothesis_preregistered": _H1_HYPOTHESIS,
        "h2_prereg_cutoff_utc": H2_PREREG_CUTOFF_UTC.isoformat(),
        "h2_hypothesis_preregistered": _H2_HYPOTHESIS,
        "h2_candidate_model_id": H2_CANDIDATE_MODEL_ID,
        "prediction_provenance": "bot_forecast_self_eval",
        "market_outcome_source": "polymarket_market_price",
        "market_truth_canonical": False,
        "weather_truth_available": False,
        "pnl_canonical_confirmed": False,
        "disclaimer": _V1_DISCLAIMER,
        "bse_artifact": str(bse_path),
        "bse_present": bse_ok,
        "bse_rows_total": len(bse_rows),
        "bse_directional_rows": len(directional),
        "source_fidelity_excluded_count": len(fidelity_suspect),
        "deduped_eval_keys": len(deduped),
        "evidence_frozen_count": len(evidence_frozen),
        "forward_holdout_count": len(forward_holdout),
        "gamma_lookup_failed_count": gamma_lookup_failed,
        "cohorts": cohorts,
        "experiment_readiness": experiment_readiness,
        "forward_holdout_n_above": fh_n_above,
        "forward_holdout_n_below": fh_n_below,
        "live_policy_eligible": False,
        "eligible_for_policy": False,
    }
