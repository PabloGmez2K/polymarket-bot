#!/usr/bin/env python3
"""
exact_no_proto_r2_resolver.py

Proto-R2 audit resolver — LOG_ONLY, read-only tool.

Resolves official Polymarket/Gamma outcomes for exact/NO shadow captures
logged in data/exact_no_qt_match_evaluations_log_only.jsonl.

Writes: data/exact_no_resolutions_log_only.jsonl  (gitignored, audit-only)

Authorized by Opus 2026-06-01 (GO_WITH_MODIFICATIONS):
  - Outcome source: official Gamma settlement only (outcomePrices >= 0.95).
  - T+7 mandatory for calibration-eligible bucket.
  - resolved_fresh: observability only, NOT eligible for calibration.
  - Cross-check against blocked_signals_resolutions.jsonl (BSR) required.
  - Mismatch with BSR resolved=True → abort, no output written.
  - Output is calibration_audit_only — does NOT feed gates, cohort_intelligence_report,
    or satisfy n_closed_calibration_unique trigger.

DISCLAIMER (printed at runtime):
  calibration_audit_only — NO levanta gate, NO alimenta cohort_intelligence_report,
  NO satisface trigger n_closed_calibration_unique>=10. Solo habilita revisión Opus futura.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

SOURCE_FILE = DATA_DIR / "exact_no_qt_match_evaluations_log_only.jsonl"
BSR_FILE = DATA_DIR / "blocked_signals_resolutions.jsonl"
OUTPUT_FILE = DATA_DIR / "exact_no_resolutions_log_only.jsonl"

GAMMA_URL = "https://gamma-api.polymarket.com"
WIN_THRESHOLD = 0.95          # price >= this = settled/won
T7_DAYS = 7                   # mature threshold
API_DELAY = 0.35              # seconds between API calls


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------
DISCLAIMER = (
    "calibration_audit_only — NO levanta gate, NO alimenta cohort_intelligence_report, "
    "NO satisface trigger n_closed_calibration_unique>=10. Solo habilita revisión Opus futura."
)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _api_get(endpoint: str, retries: int = 3, delay: float = 3.0) -> Any:
    url = GAMMA_URL + endpoint
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "exact-no-proto-r2-resolver/1.0")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            last_err = exc
            if attempt < retries - 1:
                print(f"    [retry {attempt + 1}/{retries}] {exc}", flush=True)
                time.sleep(delay)
    raise RuntimeError(f"Gamma API failed for {endpoint}: {last_err}") from last_err


def fetch_market_by_id(market_id: str) -> dict | None:
    """Return Gamma market dict or None if not found."""
    try:
        result = _api_get(f"/markets/{market_id}")
        if isinstance(result, dict) and result:
            return result
        return None
    except Exception as exc:
        print(f"  [warn] market_id={market_id} fetch failed: {exc}", flush=True)
        return None


def extract_prices(market: dict) -> tuple[float | None, float | None]:
    """Return (yes_price, no_price) from outcomePrices field."""
    raw = market.get("outcomePrices", "[]")
    try:
        prices = json.loads(raw) if isinstance(raw, str) else raw
        if len(prices) >= 2:
            return float(prices[0]), float(prices[1])
    except Exception:
        pass
    return None, None


def determine_settlement(
    market: dict | None,
) -> tuple[bool, float | None, float | None, str | None]:
    """
    Returns (settled, yes_price, no_price, resolved_at_iso).
    settled=True if one side >= WIN_THRESHOLD.
    resolved_at_iso from market.endDate or None.
    """
    if market is None:
        return False, None, None, None

    yes_price, no_price = extract_prices(market)
    if yes_price is None or no_price is None:
        return False, None, None, None

    settled = yes_price >= WIN_THRESHOLD or no_price >= WIN_THRESHOLD
    resolved_at = market.get("endDate") or market.get("resolutionTime") or None
    return settled, yes_price, no_price, resolved_at


# ---------------------------------------------------------------------------
# BSR cross-check
# ---------------------------------------------------------------------------

def load_bsr(bsr_path: Path) -> dict[str, dict]:
    """
    Load BSR resolved=True rows keyed by match_key.
    Only keeps resolved=True entries. Last entry wins per match_key.
    """
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
                mk = row.get("match_key", "")
                if mk:
                    index[mk] = row
    return index


def bsr_no_would_win(bsr_row: dict) -> bool | None:
    """
    Derive whether NO would win from a BSR row.
    BSR tracks quality-trader signals; outcome = trader's side.
    win_for_trader = True if that side won.
    Returns True if NO won, False if YES won, None if indeterminate.
    """
    outcome = (bsr_row.get("outcome") or "").strip()
    win = bsr_row.get("win_for_trader")
    if win is None:
        return None
    if outcome == "No":
        return bool(win)       # trader bet No → if win, No won
    if outcome == "Yes":
        return not bool(win)   # trader bet Yes → if win, Yes won → No lost
    return None


# ---------------------------------------------------------------------------
# Dedup logic
# ---------------------------------------------------------------------------

def dedup_groups(rows: list[dict]) -> list[dict]:
    """
    Deduplicate by (market_id, condition_id, eval_key).
    Within each group:
      - entry_edge = best_edge_pct_log_only of the FIRST row (by ts_utc).
      - max_edge = max best_edge_pct_log_only across all rows in group.
      - duplicate_count = total captures.
    Returns one representative row per group with extra dedup metadata.
    """
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (
            row.get("market_id", ""),
            row.get("condition_id", ""),
            row.get("eval_key", ""),
        )
        groups.setdefault(key, []).append(row)

    result = []
    for group_rows in groups.values():
        # Sort by ts_utc ascending to find first
        sorted_rows = sorted(
            group_rows,
            key=lambda r: r.get("ts_utc", ""),
        )
        first = sorted_rows[0]
        edges = [
            r.get("best_edge_pct_log_only")
            for r in sorted_rows
            if r.get("best_edge_pct_log_only") is not None
        ]
        max_edge = max(edges) if edges else None
        entry_edge = first.get("best_edge_pct_log_only")
        rep = dict(first)
        rep["_entry_edge"] = entry_edge
        rep["_max_edge"] = max_edge
        rep["_duplicate_count"] = len(sorted_rows)
        result.append(rep)

    return result


# ---------------------------------------------------------------------------
# Bucket classification
# ---------------------------------------------------------------------------

def classify_bucket(date_iso: str, settled: bool, today: date) -> str:
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


# ---------------------------------------------------------------------------
# Simulated unit PnL
# ---------------------------------------------------------------------------

def simulated_unit_pnl(no_would_win: bool | None, p_no_at_eval: float | None) -> float | None:
    """
    Unit PnL per share bought at price p_no_at_eval.
    win  → (1 - price)
    lose → -price
    """
    if no_would_win is None or p_no_at_eval is None:
        return None
    return (1.0 - p_no_at_eval) if no_would_win else -p_no_at_eval


# ---------------------------------------------------------------------------
# Calibration gap component
# ---------------------------------------------------------------------------

def calibration_gap_component(p_model_no: float | None, no_would_win: bool | None) -> float | None:
    """model_prob - observed_outcome (0/1)."""
    if p_model_no is None or no_would_win is None:
        return None
    return round(p_model_no - (1.0 if no_would_win else 0.0), 6)


# ---------------------------------------------------------------------------
# Cross-check validation
# ---------------------------------------------------------------------------

def cross_check_bsr(
    eval_key: str,
    no_would_win: bool | None,
    bsr_index: dict[str, dict],
) -> tuple[bool, str | None]:
    """
    Returns (ok, error_msg).
    ok=True if no mismatch; ok=False triggers abort.
    Only checks entries where BSR resolved=True.
    """
    bsr_row = bsr_index.get(eval_key)
    if bsr_row is None:
        return True, None   # not in BSR → no cross-check needed
    if no_would_win is None:
        return True, None   # we haven't resolved → no conflict yet
    bsr_win = bsr_no_would_win(bsr_row)
    if bsr_win is None:
        return True, None   # BSR indeterminate → skip
    if bsr_win != no_would_win:
        return False, (
            f"MISMATCH eval_key={eval_key}: "
            f"Gamma no_would_win={no_would_win}, BSR no_would_win={bsr_win} "
            f"(bsr outcome={bsr_row.get('outcome')}, win_for_trader={bsr_row.get('win_for_trader')})"
        )
    return True, None


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------

def resolve(
    source_path: Path,
    bsr_path: Path,
    output_path: Path,
    today: date | None = None,
) -> dict:
    """
    Run the full resolution pipeline.
    Returns summary dict.
    Raises SystemExit or RuntimeError on hard abort conditions.
    """
    if today is None:
        today = date.today()

    # ------------------------------------------------------------------
    # 1. Load source
    # ------------------------------------------------------------------
    if not source_path.exists():
        print(f"ERROR: Source file not found: {source_path}", flush=True)
        sys.exit(1)

    raw_rows: list[dict] = []
    with open(source_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                raw_rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"  [warn] JSON parse error: {exc}", flush=True)

    print(f"Loaded {len(raw_rows)} raw rows from {source_path.name}", flush=True)

    # ------------------------------------------------------------------
    # 2. Dedup
    # ------------------------------------------------------------------
    groups = dedup_groups(raw_rows)
    n_unique_seen = len(groups)
    print(f"Unique groups after dedup: {n_unique_seen}", flush=True)

    # ------------------------------------------------------------------
    # 3. Load BSR for cross-check
    # ------------------------------------------------------------------
    bsr_index = load_bsr(bsr_path)
    print(f"BSR resolved entries loaded: {len(bsr_index)}", flush=True)

    # ------------------------------------------------------------------
    # 4. Resolve each group via Gamma
    # ------------------------------------------------------------------
    output_rows: list[dict] = []
    mismatches: list[str] = []

    n_settled_mature = 0
    n_resolved_fresh = 0
    n_pending = 0
    n_no_would_win_mature = 0
    n_no_would_win_fresh = 0
    mature_sim_pnl: list[float] = []
    mature_edges_correct: list[float] = []
    mature_edges_wrong: list[float] = []
    calibration_gaps: list[float] = []

    print(f"\nResolving {n_unique_seen} groups via Gamma API...", flush=True)
    for i, rep in enumerate(groups, 1):
        market_id = rep.get("market_id", "")
        eval_key = rep.get("eval_key", "")
        date_iso = rep.get("date_iso", "")
        p_model_no = rep.get("our_prob_no")
        p_market_no_at_eval = rep.get("mkt_prob_no")

        print(f"  [{i}/{n_unique_seen}] {eval_key} market={market_id}", end=" ", flush=True)

        market = fetch_market_by_id(market_id)
        settled, yes_price, no_price, resolved_at = determine_settlement(market)

        no_would_win: bool | None = None
        market_outcome: str | None = None

        if settled and no_price is not None and yes_price is not None:
            no_would_win = no_price >= WIN_THRESHOLD
            market_outcome = "NO" if no_would_win else "YES"

        # Days since date
        try:
            d = date.fromisoformat(date_iso)
            days_since = (today - d).days
        except ValueError:
            days_since = None

        # Cross-check BSR
        ok, mismatch_msg = cross_check_bsr(eval_key, no_would_win, bsr_index)
        if not ok:
            mismatches.append(mismatch_msg)
            print(f"MISMATCH!", flush=True)
            continue

        bucket = classify_bucket(date_iso, settled, today)
        print(f"-> {bucket}", flush=True)

        # Simulated PnL and calibration gap (only if mature)
        sim_pnl = simulated_unit_pnl(no_would_win, p_market_no_at_eval)
        cal_gap = calibration_gap_component(p_model_no, no_would_win)

        entry_edge = rep.get("_entry_edge")
        max_edge = rep.get("_max_edge")

        row: dict[str, Any] = {
            "calibration_audit_only": True,
            "source_artifact": "exact_no_qt_match_evaluations_log_only.jsonl",
            "eval_key": eval_key,
            "market_id": market_id,
            "condition_id": rep.get("condition_id"),
            "city": rep.get("city"),
            "date_iso": date_iso,
            "condition": rep.get("condition"),
            "threshold": rep.get("threshold"),
            "unit": rep.get("unit"),
            "best_side_log_only": rep.get("best_side_log_only"),
            "entry_edge_log_only": entry_edge,
            "max_edge_log_only": max_edge,
            "market_outcome": market_outcome,
            "no_would_win": no_would_win,
            "resolution_source": "gamma_official" if settled else None,
            "resolved_at": resolved_at,
            "settlement_mature_t7": bucket == "settled_mature",
            "days_since_date": days_since,
            "duplicate_count": rep.get("_duplicate_count", 1),
            "p_model_no": p_model_no,
            "p_market_no_at_eval": p_market_no_at_eval,
            "simulated_unit_pnl": sim_pnl if bucket == "settled_mature" else None,
            "calibration_gap_component": cal_gap if bucket == "settled_mature" else None,
            "bucket": bucket,
        }
        output_rows.append(row)

        # Accumulate metrics
        if bucket == "settled_mature":
            n_settled_mature += 1
            if no_would_win:
                n_no_would_win_mature += 1
            if sim_pnl is not None:
                mature_sim_pnl.append(sim_pnl)
            if cal_gap is not None:
                calibration_gaps.append(cal_gap)
            if entry_edge is not None:
                if no_would_win:
                    mature_edges_correct.append(entry_edge)
                elif no_would_win is False:
                    mature_edges_wrong.append(entry_edge)
        elif bucket == "resolved_fresh":
            n_resolved_fresh += 1
            if no_would_win:
                n_no_would_win_fresh += 1
        else:
            n_pending += 1

        time.sleep(API_DELAY)

    # ------------------------------------------------------------------
    # 5. Abort if any BSR mismatch
    # ------------------------------------------------------------------
    if mismatches:
        print("\n" + "=" * 60, flush=True)
        print("ABORT: BSR cross-check mismatch(es) detected:", flush=True)
        for m in mismatches:
            print(f"  {m}", flush=True)
        print("Output NOT written.", flush=True)
        print("=" * 60, flush=True)
        sys.exit(2)

    # ------------------------------------------------------------------
    # 6. Write output atomically
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path_str = tempfile.mkstemp(
        dir=output_path.parent, prefix=".exact_no_r2_tmp_", suffix=".jsonl"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            for row in output_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        os.replace(tmp_path_str, output_path)
    except Exception:
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        raise

    print(f"\nOutput written: {output_path} ({len(output_rows)} rows)", flush=True)

    # ------------------------------------------------------------------
    # 7. Build summary
    # ------------------------------------------------------------------
    wr_no_mature = (
        round(n_no_would_win_mature / n_settled_mature, 4)
        if n_settled_mature > 0 else None
    )
    wr_no_fresh = (
        round(n_no_would_win_fresh / n_resolved_fresh, 4)
        if n_resolved_fresh > 0 else None
    )
    total_sim_pnl = round(sum(mature_sim_pnl), 4) if mature_sim_pnl else None
    avg_edge_correct = (
        round(sum(mature_edges_correct) / len(mature_edges_correct), 2)
        if mature_edges_correct else None
    )
    avg_edge_wrong = (
        round(sum(mature_edges_wrong) / len(mature_edges_wrong), 2)
        if mature_edges_wrong else None
    )
    mean_cal_gap = (
        round(sum(calibration_gaps) / len(calibration_gaps), 4)
        if calibration_gaps else None
    )

    n_likely_closed = n_settled_mature + n_resolved_fresh

    return {
        "n_unique_seen": n_unique_seen,
        "n_likely_closed": n_likely_closed,
        "n_settled_mature": n_settled_mature,
        "n_resolved_fresh": n_resolved_fresh,
        "n_pending": n_pending,
        "settled_mature": {
            "n_resolved": n_settled_mature,
            "n_no_would_win": n_no_would_win_mature,
            "WR_NO": wr_no_mature,
            "avg_edge_correct": avg_edge_correct,
            "avg_edge_wrong": avg_edge_wrong,
            "simulated_unit_pnl": total_sim_pnl,
            "calibration_gap": mean_cal_gap,
            "note": "calibration_eligible",
        },
        "resolved_fresh": {
            "n_resolved_fresh": n_resolved_fresh,
            "n_no_would_win_fresh": n_no_would_win_fresh,
            "WR_NO_fresh": wr_no_fresh,
            "note": "observabilidad, NO elegible para calibración",
        },
        "pending": {
            "n_pending": n_pending,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_summary(summary: dict) -> None:
    print("\n" + "=" * 70, flush=True)
    print("PROTO-R2 RESOLVER — SUMMARY", flush=True)
    print("=" * 70, flush=True)
    print(f"  n_unique_seen        : {summary['n_unique_seen']}", flush=True)
    print(f"  n_likely_closed      : {summary['n_likely_closed']}", flush=True)
    print(f"  n_settled_mature     : {summary['n_settled_mature']}", flush=True)
    print(f"  n_resolved_fresh     : {summary['n_resolved_fresh']}", flush=True)
    print(f"  n_pending            : {summary['n_pending']}", flush=True)
    print(flush=True)

    sm = summary["settled_mature"]
    print("  [settled_mature] — calibration eligible:", flush=True)
    print(f"    n_resolved         : {sm['n_resolved']}", flush=True)
    print(f"    n_no_would_win     : {sm['n_no_would_win']}", flush=True)
    print(f"    WR_NO              : {sm['WR_NO']}", flush=True)
    print(f"    avg_edge_correct   : {sm['avg_edge_correct']}", flush=True)
    print(f"    avg_edge_wrong     : {sm['avg_edge_wrong']}", flush=True)
    print(f"    simulated_unit_pnl : {sm['simulated_unit_pnl']}", flush=True)
    print(f"    calibration_gap    : {sm['calibration_gap']}", flush=True)
    print(flush=True)

    rf = summary["resolved_fresh"]
    print("  [resolved_fresh] — observabilidad, NO elegible para calibración:", flush=True)
    print(f"    n_resolved_fresh   : {rf['n_resolved_fresh']}", flush=True)
    print(f"    n_no_would_win_fresh: {rf['n_no_would_win_fresh']}", flush=True)
    print(f"    WR_NO_fresh        : {rf['WR_NO_fresh']}", flush=True)
    print(flush=True)

    pend = summary["pending"]
    print("  [pending]:", flush=True)
    print(f"    n_pending          : {pend['n_pending']}", flush=True)
    print(flush=True)
    print(f"  *** {DISCLAIMER} ***", flush=True)
    print("=" * 70, flush=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Proto-R2 exact/NO audit resolver (LOG_ONLY)")
    parser.add_argument(
        "--source",
        default=str(SOURCE_FILE),
        help="Path to exact_no_qt_match_evaluations_log_only.jsonl",
    )
    parser.add_argument(
        "--bsr",
        default=str(BSR_FILE),
        help="Path to blocked_signals_resolutions.jsonl",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_FILE),
        help="Path to output exact_no_resolutions_log_only.jsonl",
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Override today date (YYYY-MM-DD) for testing",
    )
    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else None

    print(f"\n{DISCLAIMER}\n", flush=True)

    summary = resolve(
        source_path=Path(args.source),
        bsr_path=Path(args.bsr),
        output_path=Path(args.output),
        today=today,
    )
    print_summary(summary)


if __name__ == "__main__":
    main()
