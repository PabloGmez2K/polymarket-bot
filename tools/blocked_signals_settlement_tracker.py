#!/usr/bin/env python3
"""
blocked_signals_settlement_tracker.py

Read-only tool: measures the Win Rate of quality-trader exact/range signals
that are blocked by the condition_filtered policy in bot.py.

Purpose: provide empirical data to decide whether condition_filtered should
be reopened. Does NOT touch bot.py, trading config, or Railway env vars.

Usage:
    python tools/blocked_signals_settlement_tracker.py

Outputs:
    data/runtime_import_derived/blocked_signals_resolutions.jsonl  (append-only)
    docs/blocked-signals-wr-baseline-2026-04-13.md                 (overwritten)
"""

import io
import json
import sys
import time
import urllib.request
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Ensure stdout/stderr handle Unicode on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GAMMA_URL = "https://gamma-api.polymarket.com"
DAILY_TEMP_TAG_ID = "103040"

BASE_DIR = Path(__file__).parent.parent
SIGNALS_FILE = BASE_DIR / "data" / "runtime_import" / "signals.json"
OUTPUT_JSONL = BASE_DIR / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
READOUT_FILE = BASE_DIR / "docs" / "blocked-signals-wr-baseline-2026-04-13.md"

# Win threshold: price on the trader's outcome side must be >= this to count as resolved win
WIN_PRICE_THRESHOLD = 0.95
LOSS_PRICE_THRESHOLD = 0.05


# ---------------------------------------------------------------------------
# API helpers (same pattern as bot.py)
# ---------------------------------------------------------------------------

def api_get(endpoint, retries=3, delay=3):
    url = GAMMA_URL + endpoint
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "polymarket-blocked-tracker/1.0")
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read())
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                print(f"    [retry {attempt+1}/{retries}] {e}", flush=True)
                time.sleep(delay)
    raise last_error


def _normalize_title(s):
    """
    Lowercase, strip whitespace, and fix the degree-sign encoding artifact.
    signals.json stores the degree sign as the two-char sequence U+252C U+2591
    (┬░) instead of U+00B0 (°). The Polymarket API returns the correct °.
    We normalize both sides to the correct ° before comparing.
    """
    # Fix corrupted degree sign: ┬░ (U+252C U+2591) -> ° (U+00B0)
    s = s.replace('\u252c\u2591', '\u00b0')
    return s.lower().strip()


# ---------------------------------------------------------------------------
# Market fetching: closed temperature markets
# ---------------------------------------------------------------------------

def build_closed_market_map():
    """
    Fetches recent closed temperature events from Polymarket gamma API.
    Returns dict: normalized_question_text -> market_dict

    Paginates until API returns fewer results than the page size.
    """
    print("Fetching closed temperature markets from Polymarket...", flush=True)
    market_map = {}
    page_size = 100
    offset = 0

    while True:
        try:
            events = api_get(
                f"/events?tag_id={DAILY_TEMP_TAG_ID}"
                f"&closed=true&limit={page_size}&offset={offset}"
                f"&order=startDate&ascending=false"
            )
        except Exception as e:
            print(f"  [warn] Failed at offset={offset}: {e}", flush=True)
            break

        if not events:
            break

        for event in events:
            for market in event.get("markets", []):
                question = market.get("question", "").strip()
                if question:
                    key = _normalize_title(question)
                    market_map[key] = market

        n = len(events)
        print(f"  offset={offset:4d} -> {n} events, {len(market_map)} markets indexed", flush=True)
        time.sleep(0.3)

        if n < page_size:
            break  # last page
        offset += page_size

    print(f"Total markets in map: {len(market_map)}", flush=True)
    return market_map


# ---------------------------------------------------------------------------
# Close-price extraction
# ---------------------------------------------------------------------------

def extract_prices(market):
    """
    Returns (yes_price, no_price) from a market's outcomePrices field.
    Returns (None, None) if unavailable.
    Polymarket outcomes are always [Yes, No] in that order.
    """
    prices_raw = market.get("outcomePrices", "[]")
    try:
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        if len(prices) >= 2:
            return float(prices[0]), float(prices[1])
    except Exception:
        pass
    return None, None


def determine_outcome(outcome, yes_price, no_price):
    """
    Returns:
        (close_price, resolved, win_for_trader)
    resolved = True if the market has clearly settled (one side >= 0.95)
    win_for_trader = True if the trader's predicted outcome won
    """
    if yes_price is None or no_price is None:
        return None, False, False

    resolved = yes_price >= WIN_PRICE_THRESHOLD or no_price >= WIN_PRICE_THRESHOLD

    if outcome == "Yes":
        close_price = yes_price
        win = yes_price >= WIN_PRICE_THRESHOLD
    elif outcome == "No":
        close_price = no_price
        win = no_price >= WIN_PRICE_THRESHOLD
    else:
        close_price = yes_price
        win = False

    # If not resolved, win is meaningless
    if not resolved:
        win = False

    return close_price, resolved, win


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # -----------------------------------------------------------------------
    # Load signals
    # -----------------------------------------------------------------------
    if not SIGNALS_FILE.exists():
        print(f"ERROR: {SIGNALS_FILE} not found", file=sys.stderr)
        sys.exit(1)

    with open(SIGNALS_FILE, encoding="utf-8-sig") as f:
        signals_data = json.load(f)

    all_signals = signals_data.get("signals", [])
    quality_traders = set(signals_data.get("quality_traders", []))

    today_str = date.today().isoformat()  # e.g. "2026-04-13"
    cutoff = (date.today() - timedelta(days=1)).isoformat()  # "2026-04-12"

    print(f"Today: {today_str}  |  Cutoff (date <=): {cutoff}", flush=True)
    print(f"Quality traders: {sorted(quality_traders)}", flush=True)

    # Filter: exact/range condition, date <= cutoff
    candidates = [
        s for s in all_signals
        if s.get("condition") in {"exact", "range"}
        and s.get("date", "") <= cutoff
    ]

    # Show breakdown
    exact_count = sum(1 for s in candidates if s.get("condition") == "exact")
    range_count = sum(1 for s in candidates if s.get("condition") == "range")
    print(f"\nTotal signals in file:         {len(all_signals)}", flush=True)
    print(f"exact/range (all dates):        "
          f"{sum(1 for s in all_signals if s.get('condition') in {'exact','range'})}",
          flush=True)
    print(f"exact/range with date <= cutoff: {len(candidates)} "
          f"({exact_count} exact + {range_count} range)", flush=True)

    if not candidates:
        print("\nNo candidates found. Exiting.", flush=True)
        return

    # -----------------------------------------------------------------------
    # Build market map from Polymarket
    # -----------------------------------------------------------------------
    market_map = build_closed_market_map()

    # -----------------------------------------------------------------------
    # Load existing records (dedup by match_key)
    # -----------------------------------------------------------------------
    existing_keys = set()
    existing_records = []
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    existing_keys.add(rec["match_key"])
                    existing_records.append(rec)
                except Exception:
                    pass
        print(f"\nExisting records in JSONL: {len(existing_records)}", flush=True)

    # -----------------------------------------------------------------------
    # Process candidates
    # -----------------------------------------------------------------------
    print(f"\nProcessing {len(candidates)} candidates...\n", flush=True)
    new_records = []
    not_found = []
    unresolved = []

    for signal in candidates:
        match_key = signal.get("match_key", "")
        title = signal.get("title", "").strip()
        outcome = signal.get("outcome", "")
        city = signal.get("city", "")
        condition = signal.get("condition", "")
        sig_date = signal.get("date", "")
        trader = signal.get("trader", "")
        trader_wr = signal.get("trader_win_rate", 0)
        avg_price = signal.get("avg_price", 0)
        has_consensus = signal.get("has_consensus", False)

        # Skip already processed
        if match_key in existing_keys:
            print(f"  [skip-dup] {match_key}", flush=True)
            continue

        # Find in market map
        market = market_map.get(_normalize_title(title))

        if not market:
            print(f"  [not-found] {match_key} | '{title[:70]}'", flush=True)
            not_found.append(match_key)
            continue

        yes_price, no_price = extract_prices(market)
        close_price, resolved, win = determine_outcome(outcome, yes_price, no_price)

        if close_price is None:
            print(f"  [no-price]  {match_key}", flush=True)
            continue

        if not resolved:
            status = "OPEN"
            unresolved.append(match_key)
        else:
            status = "WIN " if win else "LOSS"

        print(
            f"  [{status}] {match_key:45s} | {outcome:3s} | "
            f"yes={yes_price:.3f} no={no_price:.3f} | "
            f"close={close_price:.3f}",
            flush=True
        )

        record = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "match_key": match_key,
            "city": city,
            "date": sig_date,
            "condition": condition,
            "trader": trader,
            "trader_historical_wr": trader_wr,
            "outcome": outcome,
            "avg_price_entered": avg_price,
            "close_price": close_price,
            "yes_price": yes_price,
            "no_price": no_price,
            "resolved": resolved,
            "win_for_trader": bool(win),
            "has_consensus": has_consensus,
        }

        new_records.append(record)
        existing_keys.add(match_key)

    # -----------------------------------------------------------------------
    # Append new records
    # -----------------------------------------------------------------------
    if new_records:
        with open(OUTPUT_JSONL, "a", encoding="utf-8") as f:
            for rec in new_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"\nWrote {len(new_records)} new records -> {OUTPUT_JSONL}", flush=True)
    else:
        print("\nNo new records to write.", flush=True)

    # Summary info
    if not_found:
        print(f"\nNot found in API ({len(not_found)}): {not_found[:5]}{'...' if len(not_found)>5 else ''}",
              flush=True)
    if unresolved:
        print(f"Still open (price not settled): {len(unresolved)}", flush=True)

    # -----------------------------------------------------------------------
    # Load ALL records for analysis
    # -----------------------------------------------------------------------
    all_records = existing_records + new_records

    if not all_records:
        print("\nNo records available for analysis.", flush=True)
        return

    generate_summary(all_records)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def generate_summary(all_records):
    resolved = [r for r in all_records if r.get("resolved")]
    n_total = len(all_records)
    n_resolved = len(resolved)
    n_win = sum(1 for r in resolved if r.get("win_for_trader"))
    wr_pct = (n_win / n_resolved * 100) if n_resolved > 0 else 0.0

    # By condition
    by_condition = {}
    for r in resolved:
        cond = r.get("condition", "?")
        by_condition.setdefault(cond, {"wins": 0, "total": 0})
        by_condition[cond]["total"] += 1
        if r.get("win_for_trader"):
            by_condition[cond]["wins"] += 1

    # By city (n >= 3)
    by_city = {}
    for r in resolved:
        city = r.get("city", "?")
        by_city.setdefault(city, {"wins": 0, "total": 0})
        by_city[city]["total"] += 1
        if r.get("win_for_trader"):
            by_city[city]["wins"] += 1

    # Consensus vs non-consensus
    consensus_wins = sum(1 for r in resolved if r.get("has_consensus") and r.get("win_for_trader"))
    consensus_total = sum(1 for r in resolved if r.get("has_consensus"))
    solo_wins = sum(1 for r in resolved if not r.get("has_consensus") and r.get("win_for_trader"))
    solo_total = sum(1 for r in resolved if not r.get("has_consensus"))
    consensus_wr = (consensus_wins / consensus_total * 100) if consensus_total > 0 else None
    solo_wr = (solo_wins / solo_total * 100) if solo_total > 0 else None

    # Threshold interpretation
    if n_resolved >= 30:
        if wr_pct >= 55:
            threshold_verdict = f"REOPEN CANDIDATE (WR={wr_pct:.1f}% >= 55% on n={n_resolved})"
        elif wr_pct >= 50:
            threshold_verdict = f"GRAY ZONE (WR={wr_pct:.1f}% in 50-55% on n={n_resolved}) -- expand sample"
        else:
            threshold_verdict = f"FILTER VALIDATED (WR={wr_pct:.1f}% < 50% on n={n_resolved})"
    else:
        threshold_verdict = f"INSUFFICIENT SAMPLE (n={n_resolved} < 30) -- accumulate more resolutions"

    # ---------------------------------------------------------------------------
    # Print to stdout
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 65, flush=True)
    print("BLOCKED SIGNALS WR BASELINE", flush=True)
    print("=" * 65, flush=True)
    print(f"Records in JSONL : {n_total}", flush=True)
    print(f"Resolved          : {n_resolved}", flush=True)
    print(f"Wins              : {n_win}", flush=True)
    print(f"Overall WR        : {wr_pct:.1f}%", flush=True)
    print(f"\nVerdict           : {threshold_verdict}", flush=True)

    print("\nBy condition:", flush=True)
    for cond, stats in sorted(by_condition.items()):
        cwr = stats["wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {cond:8s}: {stats['wins']}/{stats['total']} = {cwr:.1f}%", flush=True)

    print("\nBy city (n >= 3):", flush=True)
    for city, stats in sorted(by_city.items(), key=lambda x: -x[1]["total"]):
        if stats["total"] >= 3:
            cwr = stats["wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {city:20s}: {stats['wins']}/{stats['total']} = {cwr:.1f}%", flush=True)

    if consensus_total > 0 or solo_total > 0:
        print("\nConsensus vs solo:", flush=True)
        if consensus_total > 0:
            print(f"  Consensus: {consensus_wins}/{consensus_total} = {consensus_wr:.1f}%", flush=True)
        if solo_total > 0:
            print(f"  Solo:      {solo_wins}/{solo_total} = {solo_wr:.1f}%", flush=True)

    # ---------------------------------------------------------------------------
    # Write readout markdown
    # ---------------------------------------------------------------------------
    lines = []
    lines.append("# Blocked Signals WR Baseline — 2026-04-13")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Source:** `data/runtime_import/signals.json` (Apr 13 snapshot)")
    lines.append(f"**Scope:** quality-trader signals with `condition in {{exact, range}}` and `date <= cutoff-1d`")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Records in JSONL | {n_total} |")
    lines.append(f"| Resolved | {n_resolved} |")
    lines.append(f"| Wins | {n_win} |")
    lines.append(f"| **WR** | **{wr_pct:.1f}%** |")
    lines.append("")
    lines.append(f"**Verdict:** {threshold_verdict}")
    lines.append("")
    lines.append("## By Condition")
    lines.append("")
    lines.append("| Condition | Wins | Total | WR |")
    lines.append("|-----------|------|-------|----|")
    for cond, stats in sorted(by_condition.items()):
        cwr = stats["wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
        lines.append(f"| `{cond}` | {stats['wins']} | {stats['total']} | {cwr:.1f}% |")
    lines.append("")
    lines.append("## By City (n >= 3)")
    lines.append("")
    lines.append("| City | Wins | Total | WR |")
    lines.append("|------|------|-------|----|")
    for city, stats in sorted(by_city.items(), key=lambda x: -x[1]["total"]):
        if stats["total"] >= 3:
            cwr = stats["wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
            lines.append(f"| {city} | {stats['wins']} | {stats['total']} | {cwr:.1f}% |")
    lines.append("")
    lines.append("## Consensus vs Solo")
    lines.append("")
    lines.append("| Type | Wins | Total | WR |")
    lines.append("|------|------|-------|----|")
    if consensus_total > 0:
        lines.append(f"| Consensus | {consensus_wins} | {consensus_total} | {consensus_wr:.1f}% |")
    if solo_total > 0:
        lines.append(f"| Solo | {solo_wins} | {solo_total} | {solo_wr:.1f}% |")
    lines.append("")
    lines.append("## Decision Thresholds (from handoff)")
    lines.append("")
    lines.append("| Range | Action |")
    lines.append("|-------|--------|")
    lines.append("| WR >= 55% (n >= 50) | Reopen filter with canary experiment |")
    lines.append("| 50–55% | Gray zone — expand sample before deciding |")
    lines.append("| WR < 50% | Filter validated — freeze 3+ months |")
    lines.append("")
    lines.append(f"*Robust decision threshold: n >= 50. Current: n = {n_resolved}.*")

    READOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(READOUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nReadout -> {READOUT_FILE}", flush=True)


if __name__ == "__main__":
    main()
