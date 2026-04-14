#!/usr/bin/env python3
"""
condition_reopen_monitor.py

Read-only monitor: tracks Win Rate of bot trades with condition in {exact, range}
placed since the canary opened on 2026-04-14.

Used to evaluate checkpoint decisions:
  - Day 7  (2026-04-21): WR<50% n>=15 -> close canary
  - Day 14 (2026-04-28): WR>=55% n>=30 -> promote; WR<50% -> close
  - Kill-switch (any day): WR<45% n>=20 rolling -> close immediately

Usage:
    python tools/condition_reopen_monitor.py

Returns structured stats dict when imported (for bot.py integration).
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
TRADE_LIFECYCLE_FILE = BASE_DIR / "data" / "trade_lifecycle.json"

CANARY_OPEN_DATE = date(2026, 4, 14)
CHECKPOINT_DAY7 = date(2026, 4, 21)
CHECKPOINT_DAY14 = date(2026, 4, 28)

# Thresholds (from Opus handoff)
KILL_WR = 0.45
KILL_N = 20
DAY7_CLOSE_WR = 0.50
DAY7_CLOSE_N = 15
DAY14_PROMOTE_WR = 0.55
DAY14_PROMOTE_N = 30
DAY14_CLOSE_WR = 0.50


# ---------------------------------------------------------------------------
# Core stats calculation
# ---------------------------------------------------------------------------

def _trade_is_win(record):
    """Win if pnl_cash > 0 in close_context, fallback to RESOLVED_WIN action."""
    cc = record.get("close_context") or {}
    pnl = cc.get("pnl_cash")
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    return cc.get("close_action") == "RESOLVED_WIN"


def compute_stats(today=None):
    """
    Load trade_lifecycle.json and compute WR for exact/range canary trades.

    Returns dict with keys:
        n_closed  — number of closed trades
        n_wins    — number of wins
        wr        — win rate as float [0, 1]
        wr_pct    — win rate as percentage string e.g. "66.7"
        by_city   — dict: city -> {"wins": int, "total": int}
        days_since_open — int days since CANARY_OPEN_DATE
        verdict   — "OK" | "ALERT" | "KILL_SWITCH" | "INSUFFICIENT"
        kill_switch — bool
        file_found  — bool
    """
    if today is None:
        today = date.today()

    days_since = (today - CANARY_OPEN_DATE).days

    result = {
        "n_closed": 0,
        "n_wins": 0,
        "wr": 0.0,
        "wr_pct": "0.0",
        "by_city": {},
        "days_since_open": days_since,
        "verdict": "INSUFFICIENT",
        "kill_switch": False,
        "file_found": False,
    }

    if not TRADE_LIFECYCLE_FILE.exists():
        return result

    result["file_found"] = True

    try:
        with open(TRADE_LIFECYCLE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[warn] Could not load {TRADE_LIFECYCLE_FILE}: {e}", file=sys.stderr)
        return result

    records = data.get("records", []) if isinstance(data, dict) else []

    # Filter: condition exact/range, opened since canary start, closed
    canary_start = CANARY_OPEN_DATE.isoformat()  # "2026-04-14"
    trades = []
    for r in records:
        if not isinstance(r, dict):
            continue
        if r.get("condition") not in {"exact", "range"}:
            continue
        opened = str(r.get("opened_at") or "")
        if opened[:10] < canary_start:
            continue
        if r.get("status") != "closed":
            continue
        trades.append(r)

    n_closed = len(trades)
    n_wins = sum(1 for r in trades if _trade_is_win(r))

    by_city = {}
    for r in trades:
        city = r.get("city", "?")
        if city not in by_city:
            by_city[city] = {"wins": 0, "total": 0}
        by_city[city]["total"] += 1
        if _trade_is_win(r):
            by_city[city]["wins"] += 1

    wr = (n_wins / n_closed) if n_closed > 0 else 0.0
    wr_pct = f"{wr * 100:.1f}"

    # Kill-switch: WR < 45% with n >= 20
    kill_switch = wr < KILL_WR and n_closed >= KILL_N

    # Verdict for reporting
    if kill_switch:
        verdict = "KILL_SWITCH"
    elif days_since >= 14:
        if n_closed >= DAY14_PROMOTE_N and wr >= DAY14_PROMOTE_WR:
            verdict = "PROMOTE"
        elif n_closed >= DAY14_PROMOTE_N and wr >= DAY14_CLOSE_WR:
            verdict = "EXTEND"
        elif n_closed >= DAY14_PROMOTE_N and wr < DAY14_CLOSE_WR:
            verdict = "CLOSE"
        else:
            verdict = "INSUFFICIENT"
    elif days_since >= 7:
        if n_closed >= DAY7_CLOSE_N and wr < DAY7_CLOSE_WR:
            verdict = "CLOSE"
        elif n_closed >= DAY7_CLOSE_N and wr < 0.70:
            verdict = "ALERT"
        elif n_closed >= DAY7_CLOSE_N:
            verdict = "OK"
        else:
            verdict = "INSUFFICIENT"
    else:
        verdict = "INSUFFICIENT"

    result.update({
        "n_closed": n_closed,
        "n_wins": n_wins,
        "wr": wr,
        "wr_pct": wr_pct,
        "by_city": by_city,
        "verdict": verdict,
        "kill_switch": kill_switch,
    })
    return result


# ---------------------------------------------------------------------------
# Human-readable output (stdout)
# ---------------------------------------------------------------------------

def print_report(stats, today=None):
    if today is None:
        today = date.today()

    days = stats["days_since_open"]
    n = stats["n_closed"]
    wins = stats["n_wins"]
    wr_pct = stats["wr_pct"]
    verdict = stats["verdict"]
    kill = stats["kill_switch"]

    print("=" * 60)
    print("condition_reopen_monitor")
    print("=" * 60)
    print(f"Canary open date  : {CANARY_OPEN_DATE}  (day {days})")
    print(f"Report date       : {today}")
    print(f"Closed trades     : {n}")
    print(f"Wins              : {wins}")
    print(f"WR                : {wr_pct}%")
    print(f"Kill-switch       : {'YES (WR<45% n>=20)' if kill else 'NO'}")
    print(f"Verdict           : {verdict}")

    if stats["by_city"]:
        print("\nBy city:")
        for city, cs in sorted(stats["by_city"].items(), key=lambda x: -x[1]["total"]):
            cwr = cs["wins"] / cs["total"] * 100 if cs["total"] > 0 else 0
            print(f"  {city:<20s}: {cs['wins']}/{cs['total']} = {cwr:.1f}%")

    if not stats["file_found"]:
        print("\n[INFO] trade_lifecycle.json not found — no trades yet.")

    print("=" * 60)

    # Next checkpoint
    if today < CHECKPOINT_DAY7:
        print(f"Next checkpoint   : Day 7 — {CHECKPOINT_DAY7}")
    elif today < CHECKPOINT_DAY14:
        print(f"Next checkpoint   : Day 14 — {CHECKPOINT_DAY14}")
    else:
        print("Both checkpoints passed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = date.today()
    stats = compute_stats(today=today)
    print_report(stats, today=today)


if __name__ == "__main__":
    main()
