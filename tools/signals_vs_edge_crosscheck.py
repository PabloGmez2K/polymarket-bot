"""
signals_vs_edge_crosscheck.py — Cross-check bot edge (shadow_city_tracking) vs trader signals.

Standalone read-only tool. Run without args:
    python tools/signals_vs_edge_crosscheck.py

Outputs:
  - Markdown table to stdout (MATCH / BOT_ONLY / TRADER_ONLY)
  - Appends one JSON line to data/runtime_import_derived/signals_crosscheck.jsonl
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

# --- Paths ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_FILE = os.path.join(ROOT, "data", "runtime_import", "signals.json")
SHADOW_FILE = os.path.join(ROOT, "data", "runtime_import", "shadow_city_tracking.json")
POLICY_FILE = os.path.join(ROOT, "data", "runtime_import", "city_policy_state.json")
OUT_DIR = os.path.join(ROOT, "data", "runtime_import_derived")
OUT_FILE = os.path.join(OUT_DIR, "signals_crosscheck.jsonl")

EDGE_HIT_THRESHOLD = 1  # min edge_hits to count as "bot sees edge"
ALLOWED_CONDITIONS = {"at_or_above", "at_or_below"}


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def build_city_signal_stats(signals):
    """
    Returns dict: city -> {
        n_signals, n_consensus, dates, conditions, max_wr,
        n_traders, has_consensus_market,
        signals_by_date: {date: [signal, ...]},
        allowed_signals: [signals with allowed conditions],
    }
    """
    stats = defaultdict(lambda: {
        "n_signals": 0,
        "n_consensus": 0,
        "dates": set(),
        "conditions": set(),
        "max_wr": 0.0,
        "traders": set(),
        "has_consensus_market": False,
        "signals_by_date": defaultdict(list),
        "allowed_signals": [],
        "best_example": None,
    })

    for s in signals:
        city = s["city"]
        st = stats[city]
        st["n_signals"] += 1
        if s["has_consensus"]:
            st["n_consensus"] += 1
            st["has_consensus_market"] = True
        st["dates"].add(s["date"])
        st["conditions"].add(s["condition"])
        st["traders"].add(s["trader"])
        if s["trader_win_rate"] > st["max_wr"]:
            st["max_wr"] = s["trader_win_rate"]
            st["best_example"] = s
        st["signals_by_date"][s["date"]].append(s)
        if s["condition"] in ALLOWED_CONDITIONS:
            st["allowed_signals"].append(s)

    return stats


def run_crosscheck():
    # --- Load data ---
    sig_data = load_json(SIGNALS_FILE)
    shadow_data = load_json(SHADOW_FILE)
    try:
        policy_data = load_json(POLICY_FILE)
    except Exception:
        policy_data = {}

    signals = sig_data["signals"]
    shadow_cities = shadow_data["cities"]
    signals_generated_at = sig_data.get("generated", "")
    shadow_updated_at = shadow_data.get("updated_at", "")
    run_at = datetime.now(timezone.utc).isoformat()

    # Canary / mode info for enrichment
    canary_cities = set(policy_data.get("auto_canary_cities", {}).keys())

    # --- Build signal stats per city ---
    city_signal_stats = build_city_signal_stats(signals)
    signal_city_names = set(city_signal_stats.keys())

    # --- Cities with bot edge ---
    bot_edge_cities = {
        city for city, data in shadow_cities.items()
        if data.get("edge_hits", 0) >= EDGE_HIT_THRESHOLD
    }

    # --- Buckets ---
    match_cities = sorted(signal_city_names & bot_edge_cities)
    bot_only_cities = sorted(bot_edge_cities - signal_city_names)
    trader_only_cities = sorted(signal_city_names - bot_edge_cities)

    # --- Build detail rows ---
    def make_city_row(city, bucket):
        sig_st = city_signal_stats.get(city, {})
        shadow_st = shadow_cities.get(city, {})
        best_ex = sig_st.get("best_example")

        row = {
            "city": city,
            "bucket": bucket,
            "edge_hits": shadow_st.get("edge_hits", 0),
            "cycles_seen": shadow_st.get("cycles_seen", 0),
            "bot_best_edge_pct": shadow_st.get("best_edge_pct", 0.0),
            "n_signals": sig_st.get("n_signals", 0),
            "n_consensus": sig_st.get("n_consensus", 0),
            "has_consensus_market": sig_st.get("has_consensus_market", False),
            "n_traders": len(sig_st.get("traders", set())),
            "max_trader_wr": sig_st.get("max_wr", 0.0),
            "conditions": sorted(sig_st.get("conditions", set())),
            "n_allowed_conditions": len(sig_st.get("allowed_signals", [])),
            "dates": sorted(sig_st.get("dates", set())),
            "is_canary": city in canary_cities,
        }
        if best_ex:
            row["best_signal_example"] = {
                "match_key": best_ex["match_key"],
                "date": best_ex["date"],
                "condition": best_ex["condition"],
                "temp": best_ex["temp"],
                "unit": best_ex["unit"],
                "mkt_price": best_ex.get("cur_price"),
                "trader_wr": best_ex["trader_win_rate"],
                "has_consensus": best_ex["has_consensus"],
            }
        return row

    match_rows = [make_city_row(c, "MATCH") for c in match_cities]
    bot_only_rows = [make_city_row(c, "BOT_ONLY") for c in bot_only_cities]
    trader_only_rows = [make_city_row(c, "TRADER_ONLY") for c in trader_only_cities]

    # --- Counts ---
    match_count = len(match_cities)
    bot_only_count = len(bot_only_cities)
    trader_only_count = len(trader_only_cities)

    consensus_match = sum(1 for r in match_rows if r["has_consensus_market"])
    consensus_trader_only = sum(1 for r in trader_only_rows if r["has_consensus_market"])

    # Actionable: TRADER_ONLY with allowed conditions (bot could theoretically trade)
    actionable_trader_only = [r for r in trader_only_rows if r["n_allowed_conditions"] > 0]
    # MATCH with allowed conditions (confirmation overlap)
    match_with_allowed = [r for r in match_rows if r["n_allowed_conditions"] > 0]

    # --- JSONL output ---
    os.makedirs(OUT_DIR, exist_ok=True)
    jsonl_record = {
        "run_at": run_at,
        "signals_generated_at": signals_generated_at,
        "shadow_updated_at": shadow_updated_at,
        "match_cities": [r["city"] for r in match_rows],
        "bot_only_cities": [r["city"] for r in bot_only_rows],
        "trader_only_cities": [r["city"] for r in trader_only_rows],
        "match_count": match_count,
        "bot_only_count": bot_only_count,
        "trader_only_count": trader_only_count,
        "consensus_match_count": consensus_match,
        "consensus_trader_only_count": consensus_trader_only,
        "actionable_trader_only_count": len(actionable_trader_only),
        "match_with_allowed_count": len(match_with_allowed),
        "match_details": match_rows,
        "bot_only_details": bot_only_rows,
        "trader_only_details": trader_only_rows,
    }

    with open(OUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(jsonl_record, ensure_ascii=False, default=str) + "\n")

    # --- Stdout table ---
    print(f"# signals_vs_edge_crosscheck — {run_at[:19]} UTC")
    print(f"signals.json: {signals_generated_at[:19]}")
    print(f"shadow_city_tracking: {shadow_updated_at[:19]}")
    print()

    def print_table(title, rows, cols):
        print(f"## {title} ({len(rows)} cities)")
        if not rows:
            print("  (none)")
            print()
            return
        # Header
        header = "| " + " | ".join(cols) + " |"
        sep = "| " + " | ".join(["---"] * len(cols)) + " |"
        print(header)
        print(sep)
        for r in rows:
            def fmt(key):
                v = r.get(key, "")
                if isinstance(v, list):
                    return ",".join(str(x) for x in v)
                if isinstance(v, float):
                    return f"{v:.1f}"
                if isinstance(v, bool):
                    return "Y" if v else ""
                return str(v) if v is not None else ""
            print("| " + " | ".join(fmt(c) for c in cols) + " |")
        print()

    # MATCH table
    match_cols = ["city", "edge_hits", "bot_best_edge_pct", "n_signals",
                  "n_consensus", "n_allowed_conditions", "is_canary", "conditions"]
    print_table("MATCH — bot edge AND trader signals", match_rows, match_cols)

    # BOT_ONLY table
    bot_cols = ["city", "edge_hits", "cycles_seen", "bot_best_edge_pct"]
    print_table("BOT_ONLY — bot edge, NO trader signals", bot_only_rows, bot_cols)

    # TRADER_ONLY table
    trader_cols = ["city", "n_signals", "n_consensus", "n_allowed_conditions",
                   "max_trader_wr", "has_consensus_market", "conditions"]
    print_table("TRADER_ONLY — trader signals, bot edge_hits=0", trader_only_rows, trader_cols)

    # Summary
    print("## Summary")
    print(f"- Total signals: {len(signals)} ({sig_data.get('n_quality_traders',0)} quality traders)")
    print(f"- MATCH:        {match_count} cities ({consensus_match} with consensus, {len(match_with_allowed)} with allowed conds)")
    print(f"- BOT_ONLY:     {bot_only_count} cities (bot sees edge, traders ignore)")
    print(f"- TRADER_ONLY:  {trader_only_count} cities ({consensus_trader_only} with consensus, {len(actionable_trader_only)} with allowed conds)")
    print()

    # Validation checks
    print("## Validation checks")
    austin_ok = "Austin" in trader_only_cities
    seoul_ok = "Seoul" in match_cities
    print(f"- Austin in TRADER_ONLY: {'PASS' if austin_ok else 'FAIL'} (expected: edge_hits=0, consensus=2)")
    print(f"- Seoul in MATCH:        {'PASS' if seoul_ok else 'FAIL'} (expected: canary with edge_hits>=1)")
    if not austin_ok:
        print("  ERROR: Austin should be TRADER_ONLY — check city name matching")
        sys.exit(1)
    if not seoul_ok:
        print("  ERROR: Seoul should be MATCH — check shadow_city_tracking edge_hits")
        sys.exit(1)
    print()

    # Actionable highlights
    if actionable_trader_only:
        print("## Actionable TRADER_ONLY (allowed conditions — bot could trade these)")
        for r in sorted(actionable_trader_only, key=lambda x: -x["n_consensus"]):
            ex = r.get("best_signal_example", {})
            mk = ex.get("match_key", "")
            mkt = ex.get("mkt_price", "?")
            print(f"  - {r['city']}: {r['n_allowed_conditions']} allowed signals, "
                  f"n_consensus={r['n_consensus']}, max_wr={r['max_trader_wr']:.0f}%"
                  f"{' | example: ' + mk if mk else ''}")

    print()
    print(f"Output appended to: {OUT_FILE}")

    return jsonl_record


if __name__ == "__main__":
    run_crosscheck()
