"""Private engine for H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1.

Fetches temperature_2m_max from multiple deterministic NWP models (Open-Meteo)
and the current market YES price (Gamma) in the same snapshot, then computes a
candidate probability based on inter-model disagreement spread.

Guardrails (hard-coded invariants):
  eligible_for_policy = False
  live_policy_eligible = False
  market_truth_canonical = False
  weather_truth_canonical = False
  pnl_canonical_confirmed = False
  partition = "h3_forward_holdout"
  market_outcome_observed = null (until resolution)

No bot.py import. No scheduler. No DB writes. No Railway writes.
No trading authorization. No BUY/SELL/SKIP. No BANKROLL changes.
LOG_ONLY / READ_ONLY standalone tool.
"""
from __future__ import annotations

import json
import math
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

# ── Constants ─────────────────────────────────────────────────────────────────

H3_HYPOTHESIS_ID = "H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1_1"
H3_CANDIDATE_MODEL_ID = "multimodel_disagreement_candidate_v1"
H3_SCHEMA_VERSION = "h3_v1_1"
H3_FORMULA_VERSION = "inter_model_disagreement_v1_1"

# Minimum sigma to avoid degenerate distributions
_MIN_SIGMA: float = 0.8

# Minimum models required to compute a valid snapshot
MIN_MODELS_REQUIRED: int = 4

# Effective deterministic models confirmed in preflight 2026-05-29
EFFECTIVE_MODEL_IDS: list[str] = [
    "ecmwf_ifs025",
    "gfs_seamless",
    "icon_seamless",
    "jma_seamless",
    "gem_seamless",
]

# ACTIVE cities with ICAO coords (matching bot's RESOLUTION_STATIONS/ICAO for source fidelity)
ACTIVE_CITY_COORDS: dict[str, dict[str, Any]] = {
    "Shanghai":    {"lat": 31.1497, "lon": 121.8002, "icao": "ZSPD", "tz": "Asia/Shanghai"},
    "Tokyo":       {"lat": 35.5494, "lon": 139.7798, "icao": "RJTT", "tz": "Asia/Tokyo"},
    "Buenos Aires":{"lat": -34.8222,"lon": -58.5358, "icao": "SAEZ", "tz": "America/Argentina/Buenos_Aires"},
    "Ankara":      {"lat": 40.1282, "lon": 32.9951,  "icao": "LTAC", "tz": "Europe/Istanbul"},
}

# CLI city name aliases (underscored form used in args)
CITY_ALIASES: dict[str, str] = {
    "Shanghai": "Shanghai",
    "Tokyo": "Tokyo",
    "Buenos_Aires": "Buenos Aires",
    "BuenosAires": "Buenos Aires",
    "Buenos Aires": "Buenos Aires",
    "Ankara": "Ankara",
}

_GAMMA_URL = "https://gamma-api.polymarket.com"
_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_DAILY_TEMP_TAG_ID = "103040"
_MONTHS = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]

_LOG_ONLY_DISCLAIMER = (
    "H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1_1: LOG_ONLY / READ_ONLY. "
    "eligible_for_policy=false. live_policy_eligible=false. "
    "No trading authorization. No Weather Truth canonical. No P&L canonical."
)

# ── Type aliases ──────────────────────────────────────────────────────────────

ModelFetchFn = Callable[[str, float, float, str, list[str]], dict[str, float | None]]
MarketFetchFn = Callable[[str, str, str, float], dict[str, Any] | None]


# ── Math ──────────────────────────────────────────────────────────────────────

def _normal_cdf(x: float, mu: float, sigma: float) -> float:
    """Standard normal CDF via math.erf."""
    z = (x - mu) / (sigma * math.sqrt(2.0))
    return 0.5 * (1.0 + math.erf(z))


def compute_consensus(per_model_tmax: dict[str, float]) -> tuple[float, float]:
    """Return (mean, sample_std) from per_model_tmax values.

    Raises ValueError if fewer than MIN_MODELS_REQUIRED values present.
    """
    vals = [v for v in per_model_tmax.values() if v is not None]
    if len(vals) < MIN_MODELS_REQUIRED:
        raise ValueError(
            f"H3_MODEL_COVERAGE_PREFLIGHT_BLOCKED: only {len(vals)} models "
            f"available, need >= {MIN_MODELS_REQUIRED}"
        )
    mean = statistics.mean(vals)
    std = statistics.pstdev(vals) if len(vals) < 2 else statistics.stdev(vals)
    return round(mean, 4), round(std, 4)


def compute_candidate_prob(
    consensus_mean: float,
    inter_model_std: float,
    threshold: float,
    condition: str,
) -> float | None:
    """Compute H3 candidate probability using inter_model_disagreement_std as sigma.

    Replicates bot.py's estimate_prob() integer-rounding convention: Polymarket
    temperatures are stated as integers so "at or above T" means T >= T-0.5 and
    "at or below T" means T <= T+0.5 (±0.5 boundary adjustment).

    sigma_candidate = max(inter_model_std, _MIN_SIGMA)
    condition 'at_or_above': P(temp >= threshold-0.5) = 1 - CDF(threshold-0.5, mu, sigma)
    condition 'at_or_below': P(temp <= threshold+0.5) = CDF(threshold+0.5, mu, sigma)
    'exact' and 'range' are out of scope for V1.

    Returns None for unsupported conditions.
    """
    if condition not in ("at_or_above", "at_or_below"):
        return None
    sigma = max(inter_model_std, _MIN_SIGMA)
    if condition == "at_or_above":
        return round(1.0 - _normal_cdf(threshold - 0.5, consensus_mean, sigma), 4)
    return round(_normal_cdf(threshold + 0.5, consensus_mean, sigma), 4)


# ── Snapshot key ─────────────────────────────────────────────────────────────

def snapshot_key(city: str, market_id: str, target_date: str,
                 condition: str, threshold: float, unit: str,
                 ts_bucket: str) -> str:
    """Deterministic snapshot key. Idempotent guard: same key = same snapshot."""
    return f"{city}|{market_id}|{target_date}|{condition}|{threshold}|{unit}|{ts_bucket}|{H3_CANDIDATE_MODEL_ID}"


def ts_bucket_from_ts(ts_utc: str) -> str:
    """Round timestamp down to the hour for idempotency bucketing."""
    try:
        dt = datetime.fromisoformat(ts_utc.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%dT%H:00:00Z")
    except Exception:
        return ts_utc[:13] + ":00:00Z"


# ── Open-Meteo fetcher ────────────────────────────────────────────────────────

def _open_meteo_url_for_model(
    lat: float, lon: float, model: str, timezone_str: str
) -> str:
    """Build Open-Meteo daily forecast URL for a single model.

    timezone_str must be the contractual local timezone for the city so that
    the returned daily.time[] aligns with the market's calendar day, not UTC.
    """
    return (
        f"{_OPEN_METEO_URL}?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max&models={model}"
        f"&forecast_days=7&timezone={timezone_str}"
    )


def fetch_multimodel_tmax(
    target_date: str,
    lat: float,
    lon: float,
    timezone_str: str,
    model_ids: list[str],
) -> dict[str, float | None]:
    """Fetch temperature_2m_max for target_date from each model via Open-Meteo.

    Uses timezone_str (city's contractual local timezone) so that the daily
    time axis aligns with the market's calendar day, not UTC.

    Returns {model_id: tmax_value_or_None}.
    Fails closed: if a model errors or has no data for target_date, value=None.
    """
    results: dict[str, float | None] = {}
    for model in model_ids:
        url = _open_meteo_url_for_model(lat, lon, model, timezone_str)
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-multimodel-shadow/1.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            times = data.get("daily", {}).get("time", [])
            tmax_vals = data.get("daily", {}).get("temperature_2m_max", [])
            val: float | None = None
            for t, v in zip(times, tmax_vals):
                if t == target_date and v is not None:
                    val = float(v)
                    break
            results[model] = val
        except Exception:
            results[model] = None
    return results


# ── Gamma market fetcher ──────────────────────────────────────────────────────

def _gamma_api_get(endpoint: str, retries: int = 3, delay: float = 2.0) -> Any:
    url = _GAMMA_URL + endpoint
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-multimodel-shadow/1.0")
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(delay)
    raise last_err  # type: ignore[misc]


def _normalize_q(s: str) -> str:
    return s.replace("°", "°").lower().strip().rstrip("?").rstrip(".")


def _build_question_fragment(city: str, threshold: float, unit: str, condition: str) -> str:
    """Build lowercase fragment to match against Gamma question text."""
    c = city.lower()
    u = unit.lower()
    t = int(threshold) if threshold == int(threshold) else threshold
    if condition == "at_or_above":
        return f"will the highest temperature in {c} be {t}°{u} or higher"
    if condition == "at_or_below":
        return f"will the highest temperature in {c} be {t}°{u} or below"
    return ""


def fetch_open_market(
    city: str,
    target_date: str,
    condition: str,
    threshold: float,
    unit: str = "C",
) -> dict[str, Any] | None:
    """Find an open weather market for city/date/condition/threshold on Gamma.

    Returns dict with keys: market_id, condition_id, slug, mkt_prob_yes, question
    or None if not found / ambiguous / unavailable.

    Read-only. No writes. No BANKROLL. No trading.
    """
    fragment = _build_question_fragment(city, threshold, unit, condition)
    if not fragment:
        return None

    try:
        events = _gamma_api_get(
            f"/events?tag_id={_DAILY_TEMP_TAG_ID}&closed=false"
            f"&limit=200&order=startDate&ascending=false"
        )
    except Exception:
        return None

    if not isinstance(events, list):
        return None

    candidates = []
    for event in events:
        for market in event.get("markets", []):
            q = _normalize_q(str(market.get("question") or ""))
            if fragment not in q:
                continue
            # Check date appears in question
            try:
                yr, mo, dy = target_date.split("-")
                month_name = _MONTHS[int(mo) - 1]
                day_no_zero = str(int(dy))
                date_fragment = f"{month_name} {day_no_zero}"
            except Exception:
                date_fragment = ""
            if date_fragment and date_fragment not in q:
                continue
            prices_raw = market.get("outcomePrices", "[]")
            try:
                prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                yes_price = float(prices[0]) if prices else None
            except Exception:
                yes_price = None
            if yes_price is None:
                continue
            candidates.append({
                "market_id": str(market.get("id") or ""),
                "condition_id": str(market.get("conditionId") or ""),
                "slug": str(market.get("slug") or ""),
                "question": str(market.get("question") or ""),
                "mkt_prob_yes": round(yes_price, 4),
            })

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        # Multiple matches: return the first but note ambiguity
        result = dict(candidates[0])
        result["_ambiguous_count"] = len(candidates)
        return result
    return None


# ── Snapshot builder ──────────────────────────────────────────────────────────

def build_snapshot(
    city: str,
    target_date: str,
    condition: str,
    threshold: float,
    unit: str,
    h3_prereg_cutoff_utc: str | None,
    model_fetch_fn: ModelFetchFn = fetch_multimodel_tmax,
    market_fetch_fn: MarketFetchFn = fetch_open_market,
    model_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a complete H3 forward snapshot.

    Fails closed if:
    - market price cannot be fetched (market_id=null → error)
    - fewer than MIN_MODELS_REQUIRED models return usable tmax

    Both the market price and model forecasts are captured in the same
    function call so they are contemporaneous by construction.
    """
    if model_ids is None:
        model_ids = EFFECTIVE_MODEL_IDS

    city_info = ACTIVE_CITY_COORDS.get(city)
    if city_info is None:
        raise ValueError(f"City not in ACTIVE_CITY_COORDS: {city!r}")

    snapshot_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ts_bucket = ts_bucket_from_ts(snapshot_ts)

    # 1. Fetch market price (contemporaneous with models)
    market_info = market_fetch_fn(city, target_date, condition, threshold, unit)
    if market_info is None:
        raise ValueError(
            f"H3_FORWARD_MARKET_SNAPSHOT_BLOCKED: no open market found for "
            f"{city}/{target_date}/{condition}/{threshold}{unit}"
        )

    mkt_prob_yes = market_info["mkt_prob_yes"]

    # 2. Fetch all models (contemporaneous with market price)
    per_model_tmax = model_fetch_fn(
        target_date, city_info["lat"], city_info["lon"],
        city_info["tz"], model_ids
    )

    # Filter out None values for consensus computation
    usable = {k: v for k, v in per_model_tmax.items() if v is not None}
    n_available = len(usable)

    if n_available < MIN_MODELS_REQUIRED:
        raise ValueError(
            f"H3_MODEL_COVERAGE_PREFLIGHT_BLOCKED: only {n_available} models "
            f"available for {city}/{target_date}, need >= {MIN_MODELS_REQUIRED}"
        )

    consensus_mean, inter_model_std = compute_consensus(usable)
    candidate_prob = compute_candidate_prob(
        consensus_mean, inter_model_std, float(threshold), condition
    )

    snap_key = snapshot_key(
        city, market_info["market_id"], target_date,
        condition, threshold, unit, ts_bucket
    )

    snap: dict[str, Any] = {
        "schema_version": H3_SCHEMA_VERSION,
        "h3_hypothesis_id": H3_HYPOTHESIS_ID,
        "h3_candidate_model_id": H3_CANDIDATE_MODEL_ID,
        "h3_prereg_cutoff_utc": h3_prereg_cutoff_utc,
        "snapshot_ts_utc": snapshot_ts,
        "snapshot_key": snap_key,
        "city": city,
        "icao": city_info["icao"],
        "lat": city_info["lat"],
        "lon": city_info["lon"],
        "market_day_timezone": city_info["tz"],
        "source_fidelity_basis": "icao_station_coords",
        "target_date": target_date,
        "condition": condition,
        "threshold": threshold,
        "unit": unit,
        "market_id": market_info["market_id"],
        "condition_id": market_info.get("condition_id", ""),
        "market_slug": market_info.get("slug", ""),
        "market_question": market_info.get("question", ""),
        "mkt_prob_yes_at_snapshot": mkt_prob_yes,
        "model_ids_effective": model_ids,
        "per_model_tmax": per_model_tmax,
        "n_models_available": n_available,
        "n_models_requested": len(model_ids),
        "consensus_mean_tmax": consensus_mean,
        "inter_model_disagreement_std": inter_model_std,
        "sigma_candidate": round(max(inter_model_std, _MIN_SIGMA), 4),
        "candidate_prob_yes": candidate_prob,
        "candidate_formula_version": H3_FORMULA_VERSION,
        "partition": "h3_forward_holdout",
        "market_outcome_observed": None,
        "eligible_for_policy": False,
        "live_policy_eligible": False,
        "market_truth_canonical": False,
        "weather_truth_canonical": False,
        "pnl_canonical_confirmed": False,
        "h3_backfill_diagnostic_only": False,
        "provenance": {
            "model_source": "open-meteo.com deterministic NWP",
            "market_source": "gamma-api.polymarket.com read-only",
            "snapshot_contemporaneous": True,
        },
        "_disclaimer": _LOG_ONLY_DISCLAIMER,
    }

    return snap


# ── Report helpers ────────────────────────────────────────────────────────────

def brier(probs: list[float], outcomes: list[int]) -> float:
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def unique_market_key(snap: dict) -> str:
    """Deterministic key identifying a unique market across snapshots.

    Primary: market_id (Gamma ID is globally unique).
    Fallback: composite of semantic fields (city/date/condition/threshold/unit/slug).
    Three snapshots of the same market at different lead-times share the same key.
    """
    mid = snap.get("market_id", "")
    if mid:
        return mid
    city = snap.get("city", "")
    target_date = snap.get("target_date", "")
    condition = snap.get("condition", "")
    threshold = snap.get("threshold", "")
    unit = snap.get("unit", "")
    slug = snap.get("market_slug", "")
    return f"{city}|{target_date}|{condition}|{threshold}|{unit}|{slug}"


def resolve_outcome_from_gamma(
    market_id: str, _market_data: "dict | None" = None
) -> "str | None":
    """Lookup resolved outcome for a closed market by market_id.

    Requires market.closed == True from Gamma before interpreting prices.
    Open markets with extreme prices are NOT treated as resolved.

    _market_data: inject a pre-fetched market dict (tests only).
    Returns 'YES', 'NO', or None if not closed / unresolved / error.
    Read-only.
    """
    try:
        if _market_data is None:
            raw = _gamma_api_get(f"/markets/{market_id}")
            if isinstance(raw, list):
                market = raw[0] if raw else {}
            elif isinstance(raw, dict):
                market = raw
            else:
                return None
        else:
            market = _market_data
        # Guard: only score markets that Gamma marks as closed.
        # An open market with extreme price (e.g. YES=0.003) is NOT an outcome.
        if not market.get("closed"):
            return None
        prices_raw = market.get("outcomePrices", "[]")
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        if len(prices) >= 2:
            yes_p = float(prices[0])
            no_p = float(prices[1])
            if yes_p >= 0.95:
                return "YES"
            if no_p >= 0.95:
                return "NO"
    except Exception:
        pass
    return None


def compute_report(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute H3 holdout report from resolved snapshots.

    Returns two levels of metrics:
      snapshot-level (diagnostic): counts and Brier over all snapshots
      market-level (alpha evidence): counts and Brier aggregated per unique market

    Readiness gates on n_unique_markets_resolved, not n_snapshots_resolved.
    Three snapshots of the same market are NOT independent evidence.

    Lead-time analysis (per-snapshot Brier by days-ahead) is out of scope here.
    """
    n_total = len(snapshots)
    resolved_snaps = []
    n_pending = 0

    for snap in snapshots:
        outcome = snap.get("market_outcome_observed")
        if outcome in ("YES", "NO"):
            resolved_snaps.append(snap)
        else:
            n_pending += 1

    n_resolved = len(resolved_snaps)

    # Unique-market counts
    all_market_keys = {unique_market_key(s) for s in snapshots}
    resolved_market_keys = {unique_market_key(s) for s in resolved_snaps}
    n_unique_markets_total = len(all_market_keys)
    n_unique_markets_resolved = len(resolved_market_keys)
    n_unique_markets_pending = len(all_market_keys - resolved_market_keys)

    _base: dict[str, Any] = {
        "n_total": n_total,
        "n_snapshots_total": n_total,
        "n_resolved": n_resolved,
        "n_snapshots_resolved": n_resolved,
        "n_pending": n_pending,
        "n_snapshots_pending": n_pending,
        "n_unique_markets_total": n_unique_markets_total,
        "n_unique_markets_resolved": n_unique_markets_resolved,
        "n_unique_markets_pending": n_unique_markets_pending,
        "brier_candidate": None,
        "brier_market": None,
        "brier_advantage_market": None,
        "brier_candidate_snapshot_weighted": None,
        "brier_market_snapshot_weighted": None,
        "brier_candidate_market_weighted": None,
        "brier_market_market_weighted": None,
        "brier_advantage_market_weighted": None,
        "inter_model_disagreement_std_mean": None,
        "readiness": "H3_HOLDOUT_ACCRUING",
        "eligible_for_policy": False,
        "live_policy_eligible": False,
    }

    if n_resolved == 0:
        return _base

    # ── Snapshot-level Brier (diagnostic; counts repeated snapshots) ──────────
    cand_probs, mkt_probs, outcome_vals = [], [], []
    disagree_stds = []

    for snap in resolved_snaps:
        outcome_str = snap["market_outcome_observed"]
        o = 1 if outcome_str == "YES" else 0
        cp = snap.get("candidate_prob_yes")
        mp = snap.get("mkt_prob_yes_at_snapshot")
        if cp is None or mp is None:
            continue
        cand_probs.append(float(cp))
        mkt_probs.append(float(mp))
        outcome_vals.append(o)
        std = snap.get("inter_model_disagreement_std")
        if std is not None:
            disagree_stds.append(float(std))

    n_scored = len(cand_probs)
    mean_std = round(statistics.mean(disagree_stds), 4) if disagree_stds else None

    if n_scored > 0:
        brier_cand_snap = round(brier(cand_probs, outcome_vals), 4)
        brier_mkt_snap = round(brier(mkt_probs, outcome_vals), 4)
        brier_adv_snap = round(brier_mkt_snap - brier_cand_snap, 4)
        _base.update({
            "n_scored": n_scored,
            "brier_candidate": brier_cand_snap,
            "brier_market": brier_mkt_snap,
            "brier_advantage_market": brier_adv_snap,
            "brier_candidate_snapshot_weighted": brier_cand_snap,
            "brier_market_snapshot_weighted": brier_mkt_snap,
            "inter_model_disagreement_std_mean": mean_std,
        })

    # ── Market-level Brier (alpha evidence; one data point per unique market) ─
    # Group resolved snapshots by unique market. Aggregate probs with mean
    # (simple average across lead-times; lead-time analysis is future work).
    market_groups: dict[str, list[dict]] = {}
    for snap in resolved_snaps:
        mk = unique_market_key(snap)
        market_groups.setdefault(mk, []).append(snap)

    mkt_cand_probs: list[float] = []
    mkt_mkt_probs: list[float] = []
    mkt_outcome_vals: list[int] = []

    for snaps_for_market in market_groups.values():
        o = 1 if snaps_for_market[0]["market_outcome_observed"] == "YES" else 0
        cvals = [float(s["candidate_prob_yes"]) for s in snaps_for_market if s.get("candidate_prob_yes") is not None]
        mvals = [float(s["mkt_prob_yes_at_snapshot"]) for s in snaps_for_market if s.get("mkt_prob_yes_at_snapshot") is not None]
        if not cvals or not mvals:
            continue
        mkt_cand_probs.append(statistics.mean(cvals))
        mkt_mkt_probs.append(statistics.mean(mvals))
        mkt_outcome_vals.append(o)

    n_markets_scored = len(mkt_cand_probs)

    if n_markets_scored > 0:
        brier_cand_mkt = round(brier(mkt_cand_probs, mkt_outcome_vals), 4)
        brier_mkt_mkt = round(brier(mkt_mkt_probs, mkt_outcome_vals), 4)
        brier_adv_mkt = round(brier_mkt_mkt - brier_cand_mkt, 4)
        _base.update({
            "n_markets_scored": n_markets_scored,
            "brier_candidate_market_weighted": brier_cand_mkt,
            "brier_market_market_weighted": brier_mkt_mkt,
            "brier_advantage_market_weighted": brier_adv_mkt,
        })

    # ── Readiness: gates on unique resolved markets, not snapshot count ────────
    if n_unique_markets_resolved >= 20 and n_markets_scored >= 20:
        brier_adv_mkt_val = _base.get("brier_advantage_market_weighted")
        if brier_adv_mkt_val is not None and brier_adv_mkt_val > 0:
            readiness = "H3_BEATS_MARKET_OPUS_REVIEW"
        else:
            readiness = "H3_FALSIFIED_NO_INCREMENTAL_WEATHER_ALPHA"
    else:
        readiness = "H3_HOLDOUT_ACCRUING"

    _base["readiness"] = readiness
    _base["_disclaimer"] = _LOG_ONLY_DISCLAIMER
    return _base
