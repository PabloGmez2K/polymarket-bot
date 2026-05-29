#!/usr/bin/env python3
"""H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1 — standalone LOG_ONLY shadow tool.

Captures multi-model NWP disagreement vs. Polymarket weather market prices.
Purely read-only diagnostic. Never imports bot.py. Never authorizes trading.

Modes:
  --preflight          Probe Open-Meteo models for ACTIVE cities (read-only check)
  --forward-snapshot   Capture contemporaneous market price + NWP models for given cities
  --report             Read local snapshots, join Gamma outcomes for closed markets, compute Brier

Usage:
  python tools/multimodel_shadow.py --preflight
  python tools/multimodel_shadow.py --forward-snapshot --cities Shanghai Tokyo Buenos_Aires Ankara
  python tools/multimodel_shadow.py --forward-snapshot --cities Shanghai --target-date 2026-06-01
  python tools/multimodel_shadow.py --report

Output dir: data/multimodel_shadow/  (gitignored, local only)

Guardrails (non-negotiable):
  eligible_for_policy = False  (hardcoded, never changes)
  live_policy_eligible = False  (hardcoded, never changes)
  No bot.py import. No scheduler integration. No DB writes. No Railway writes.
  No trading. No BANKROLL. No BUY/SELL/SKIP. No city mode changes.
  H3_PREREG_CUTOFF_UTC is fixed at first successful forward snapshot.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from _multimodel_engine import (
    ACTIVE_CITY_COORDS,
    CITY_ALIASES,
    EFFECTIVE_MODEL_IDS,
    H3_CANDIDATE_MODEL_ID,
    H3_FORMULA_VERSION,
    H3_HYPOTHESIS_ID,
    MIN_MODELS_REQUIRED,
    build_snapshot,
    compute_report,
    fetch_multimodel_tmax,
    fetch_open_market,
    resolve_outcome_from_gamma,
    snapshot_key,
    ts_bucket_from_ts,
)

OUT_DIR = REPO_ROOT / "data" / "multimodel_shadow"
PREREG_MARKER_FILE = OUT_DIR / "_h3_prereg_cutoff.json"

_LOG_ONLY_HEADER = (
    "H3_MULTIMODEL_DISAGREEMENT_SIGNAL_V1_1 | LOG_ONLY | READ_ONLY\n"
    "eligible_for_policy=false | live_policy_eligible=false\n"
    "No trading authorization. No Weather Truth canonical. No P&L canonical.\n"
)


# ── Prereg cutoff ────────────────────────────────────────────────────────────

def _load_prereg_cutoff() -> str | None:
    if PREREG_MARKER_FILE.exists():
        try:
            data = json.loads(PREREG_MARKER_FILE.read_text(encoding="utf-8"))
            return data.get("h3_prereg_cutoff_utc")
        except Exception:
            pass
    return None


def _save_prereg_cutoff(ts: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREREG_MARKER_FILE.write_text(
        json.dumps({"h3_prereg_cutoff_utc": ts, "note": "Fixed at first valid forward snapshot. Never change."}, indent=2),
        encoding="utf-8",
    )


def _get_or_create_prereg_cutoff(first_snapshot_ts: str) -> str:
    existing = _load_prereg_cutoff()
    if existing:
        return existing
    _save_prereg_cutoff(first_snapshot_ts)
    print(f"[H3] H3_PREREG_CUTOFF_UTC registered: {first_snapshot_ts}")
    return first_snapshot_ts


# ── Snapshot I/O ─────────────────────────────────────────────────────────────

def _snapshot_path(snap_key: str) -> Path:
    safe_key = snap_key.replace("|", "_").replace(":", "-").replace(" ", "_")[:160]
    return OUT_DIR / f"{safe_key}.json"


def _load_all_snapshots() -> list[dict]:
    if not OUT_DIR.exists():
        return []
    snaps = []
    for f in sorted(OUT_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("h3_hypothesis_id") == H3_HYPOTHESIS_ID:
                snaps.append(data)
        except Exception:
            pass
    return snaps


def _save_snapshot(snap: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(snap["snapshot_key"])
    path.write_text(json.dumps(snap, indent=2, default=str), encoding="utf-8")
    return path


# ── Preflight mode ────────────────────────────────────────────────────────────

def cmd_preflight() -> int:
    print(_LOG_ONLY_HEADER)
    print("=== OPEN-METEO MODEL PREFLIGHT ===")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    all_ok = True
    for city, info in ACTIVE_CITY_COORDS.items():
        result = fetch_multimodel_tmax(
            tomorrow, info["lat"], info["lon"], info["tz"], EFFECTIVE_MODEL_IDS
        )
        ok_models = [m for m, v in result.items() if v is not None]
        n_ok = len(ok_models)
        status = "PASS" if n_ok >= MIN_MODELS_REQUIRED else "FAIL"
        if n_ok < MIN_MODELS_REQUIRED:
            all_ok = False
        print(f"\n{city} ({info['icao']}): {n_ok}/{len(EFFECTIVE_MODEL_IDS)} OK [{status}]")
        for m, v in result.items():
            mark = "OK" if v is not None else "FAIL"
            print(f"  {mark}  {m}: {v}")

    if all_ok:
        print(f"\nGATE: H3_MODEL_PREFLIGHT_PASS — {len(EFFECTIVE_MODEL_IDS)} models effective across all ACTIVE cities")
        print(f"Effective model IDs: {EFFECTIVE_MODEL_IDS}")
    else:
        print("\nGATE: H3_MODEL_COVERAGE_PREFLIGHT_BLOCKED")
    return 0 if all_ok else 1


# ── Forward snapshot mode ─────────────────────────────────────────────────────

def cmd_forward_snapshot(cities: list[str], target_date: str | None = None) -> int:
    print(_LOG_ONLY_HEADER)
    print("=== H3 FORWARD SNAPSHOT ===")

    if target_date is None:
        target_date = (date.today() + timedelta(days=1)).isoformat()

    resolved_cities = []
    for c in cities:
        canonical = CITY_ALIASES.get(c)
        if canonical is None:
            print(f"[SKIP] Unknown city alias: {c!r}. Known: {list(CITY_ALIASES.keys())}")
            continue
        resolved_cities.append(canonical)

    if not resolved_cities:
        print("ERROR: No valid cities. Aborting.")
        return 1

    prereg = _load_prereg_cutoff()
    n_written = 0
    n_skipped = 0

    for city in resolved_cities:
        city_info = ACTIVE_CITY_COORDS[city]
        print(f"\n--- {city} ({city_info['icao']}) / {target_date} ---")

        # For forward snapshot, we scan open markets for this city
        # We try common conditions: at_or_above and at_or_below
        # with thresholds typical for each city (we'll discover from Gamma)
        # Since we don't know the thresholds ahead of time, we fetch all open
        # markets for the city from Gamma and pick relevant ones.
        markets_found = _discover_open_markets_for_city(city, target_date)

        if not markets_found:
            print(f"  [SKIP] No open temperature markets found for {city}/{target_date}")
            continue

        for mkt in markets_found[:3]:  # cap at 3 per city to avoid excessive scope
            condition = mkt["condition"]
            threshold = mkt["threshold"]
            unit = mkt["unit"]

            # Check idempotency
            ts_now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            bucket = ts_bucket_from_ts(ts_now)
            sk = snapshot_key(
                city, mkt["market_id"], target_date, condition, threshold, unit, bucket
            )
            path = _snapshot_path(sk)
            if path.exists():
                print(f"  [SKIP/idempotent] Snapshot already exists: {path.name}")
                n_skipped += 1
                continue

            try:
                snap = build_snapshot(
                    city=city,
                    target_date=target_date,
                    condition=condition,
                    threshold=threshold,
                    unit=unit,
                    h3_prereg_cutoff_utc=prereg,
                    model_ids=EFFECTIVE_MODEL_IDS,
                )
            except ValueError as e:
                print(f"  [BLOCKED] {e}")
                continue

            # Register prereg cutoff on first successful snapshot
            if prereg is None:
                prereg = _get_or_create_prereg_cutoff(snap["snapshot_ts_utc"])
                snap["h3_prereg_cutoff_utc"] = prereg

            saved_path = _save_snapshot(snap)
            n_written += 1
            print(f"  [OK] condition={condition} threshold={threshold}{unit}")
            print(f"       mkt_prob_yes={snap['mkt_prob_yes_at_snapshot']}")
            print(f"       consensus_mean={snap['consensus_mean_tmax']} std={snap['inter_model_disagreement_std']}")
            print(f"       candidate_prob_yes={snap['candidate_prob_yes']}")
            print(f"       snapshot_key={snap['snapshot_key'][:80]}...")
            print(f"       saved: {saved_path}")

    print(f"\n=== RESULT: {n_written} snapshots written, {n_skipped} skipped (idempotent) ===")
    if prereg:
        print(f"H3_PREREG_CUTOFF_UTC: {prereg}")
    return 0


def _discover_open_markets_for_city(city: str, target_date: str) -> list[dict]:
    """Discover open temperature markets for a city/date from Gamma.

    Probes common conditions and returns list of {market_id, condition_id,
    slug, condition, threshold, unit, mkt_prob_yes}.
    """
    import urllib.request as ur
    try:
        req = ur.Request(
            f"https://gamma-api.polymarket.com/events"
            f"?tag_id=103040&closed=false&limit=200&order=startDate&ascending=false"
        )
        req.add_header("User-Agent", "polymarket-multimodel-shadow/1.0")
        with ur.urlopen(req, timeout=20) as resp:
            events = json.loads(resp.read())
    except Exception:
        return []

    city_lower = city.lower()
    results = []
    seen_ids: set[str] = set()

    for event in events:
        for market in event.get("markets", []):
            q = str(market.get("question") or "").lower()
            if city_lower not in q:
                continue

            # Parse condition and threshold from question text
            condition, threshold, unit = _parse_condition_from_question(q, city_lower)
            if condition is None or threshold is None:
                continue

            # Check target date in question
            try:
                yr, mo, dy = target_date.split("-")
                from _multimodel_engine import _MONTHS
                month_name = _MONTHS[int(mo) - 1]
                day_no_zero = str(int(dy))
                if month_name not in q or day_no_zero not in q:
                    continue
            except Exception:
                continue

            market_id = str(market.get("id") or "")
            if market_id in seen_ids:
                continue
            seen_ids.add(market_id)

            prices_raw = market.get("outcomePrices", "[]")
            try:
                prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                yes_price = round(float(prices[0]), 4) if prices else None
            except Exception:
                yes_price = None

            if yes_price is None:
                continue

            # Only at_or_above / at_or_below (exact/range out of scope V1)
            if condition not in ("at_or_above", "at_or_below"):
                continue

            results.append({
                "market_id": market_id,
                "condition_id": str(market.get("conditionId") or ""),
                "slug": str(market.get("slug") or ""),
                "question": str(market.get("question") or ""),
                "condition": condition,
                "threshold": threshold,
                "unit": unit,
                "mkt_prob_yes": yes_price,
            })

    return results


def _parse_condition_from_question(q: str, city_lower: str) -> tuple[str | None, float | None, str]:
    """Parse condition, threshold, unit from a Gamma question text.

    Returns (condition, threshold, unit) or (None, None, 'C').
    """
    import re

    # Try at_or_above: "or higher"
    m = re.search(r"be (\d+(?:\.\d+)?)[°]?([cCfF])?\s*(?:degrees\s*(?:celsius|fahrenheit))?\s*or higher", q)
    if m:
        thresh = float(m.group(1))
        unit = (m.group(2) or "C").upper()
        return "at_or_above", thresh, unit

    # Try at_or_below: "or below"
    m = re.search(r"be (\d+(?:\.\d+)?)[°]?([cCfF])?\s*(?:degrees\s*(?:celsius|fahrenheit))?\s*or below", q)
    if m:
        thresh = float(m.group(1))
        unit = (m.group(2) or "C").upper()
        return "at_or_below", thresh, unit

    # Fallback: look for °C or °F pattern
    m = re.search(r"(\d+(?:\.\d+)?)°([cCfF])", q)
    if m:
        thresh = float(m.group(1))
        unit = m.group(2).upper()
        if "or higher" in q:
            return "at_or_above", thresh, unit
        if "or below" in q:
            return "at_or_below", thresh, unit

    return None, None, "C"


# ── Report mode ───────────────────────────────────────────────────────────────

def cmd_report() -> int:
    print(_LOG_ONLY_HEADER)
    print("=== H3 HOLDOUT REPORT ===")

    prereg = _load_prereg_cutoff()
    print(f"H3_PREREG_CUTOFF_UTC: {prereg or 'NOT_YET_REGISTERED'}")

    snapshots = _load_all_snapshots()
    print(f"Snapshots found: {len(snapshots)}")

    if not snapshots:
        print("\nreadiness: H3_HOLDOUT_ACCRUING (no snapshots yet)")
        print("\neligible_for_policy=false | live_policy_eligible=false")
        return 0

    # Try to fill in outcomes for snapshots that don't have them yet
    updated = 0
    for snap in snapshots:
        if snap.get("market_outcome_observed") is None:
            mid = snap.get("market_id", "")
            if mid:
                outcome = resolve_outcome_from_gamma(mid)
                if outcome in ("YES", "NO"):
                    snap["market_outcome_observed"] = outcome
                    # Persist updated snapshot
                    try:
                        _save_snapshot(snap)
                        updated += 1
                    except Exception:
                        pass

    if updated:
        print(f"Outcomes joined from Gamma: {updated}")

    report = compute_report(snapshots)

    print(f"\nn_total={report['n_total']} n_resolved={report['n_resolved']} n_pending={report['n_pending']}")
    if report.get("n_scored") is not None:
        print(f"n_scored={report['n_scored']}")
    print(f"brier_candidate={report['brier_candidate']}")
    print(f"brier_market={report['brier_market']}")
    print(f"brier_advantage_market={report['brier_advantage_market']} (>0 = H3 beats market)")
    print(f"inter_model_disagreement_std_mean={report['inter_model_disagreement_std_mean']}")
    print(f"\nreadiness: {report['readiness']}")
    print("\neligible_for_policy=false | live_policy_eligible=false")

    # Show snapshot details
    if snapshots:
        print(f"\n--- Snapshot details ({len(snapshots)} total) ---")
        for snap in snapshots[:10]:
            ts = snap.get("snapshot_ts_utc", "?")[:16]
            city = snap.get("city", "?")
            td = snap.get("target_date", "?")
            cond = snap.get("condition", "?")
            thr = snap.get("threshold", "?")
            cp = snap.get("candidate_prob_yes", "?")
            mp = snap.get("mkt_prob_yes_at_snapshot", "?")
            outcome = snap.get("market_outcome_observed") or "pending"
            std = snap.get("inter_model_disagreement_std", "?")
            print(f"  {ts} {city}/{td} {cond}/{thr}: cand={cp} mkt={mp} std={std} outcome={outcome}")

    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="H3 multimodel disagreement shadow tool (LOG_ONLY)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true",
                       help="Probe Open-Meteo models for ACTIVE cities")
    group.add_argument("--forward-snapshot", action="store_true",
                       help="Capture market price + NWP models snapshot")
    group.add_argument("--report", action="store_true",
                       help="Compute H3 holdout report from local snapshots")
    group.add_argument("--backfill-diagnostic", action="store_true",
                       help="Not implemented: H3_BACKFILL_NOT_DECISION_COMPARABLE_USE_FORWARD_ONLY")

    parser.add_argument("--cities", nargs="+", default=[],
                        help="Cities for --forward-snapshot (e.g. Shanghai Tokyo Buenos_Aires Ankara)")
    parser.add_argument("--target-date", default=None,
                        help="Target date YYYY-MM-DD for --forward-snapshot (default: tomorrow)")

    args = parser.parse_args()

    if args.preflight:
        return cmd_preflight()
    if args.forward_snapshot:
        if not args.cities:
            print("ERROR: --forward-snapshot requires --cities")
            return 1
        return cmd_forward_snapshot(args.cities, args.target_date)
    if args.report:
        return cmd_report()
    if args.backfill_diagnostic:
        print("H3_BACKFILL_NOT_DECISION_COMPARABLE_USE_FORWARD_ONLY")
        print("Backfill mode not implemented: cannot guarantee temporal alignment")
        print("between historical market prices and NWP model runs without look-ahead.")
        print("Use --forward-snapshot for forward capture only.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
