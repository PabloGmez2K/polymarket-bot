"""
signals_vs_edge_crosscheck.py - Cross-check bot edge (shadow_city_tracking) vs trader signals.

Standalone read-only tool. Run without args:
    python tools/signals_vs_edge_crosscheck.py

Outputs:
  - Markdown table to stdout (MATCH / BOT_ONLY / TRADER_ONLY)
  - Appends one JSON line to data/runtime_import_derived/signals_crosscheck.jsonl
"""

import argparse
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Cruza edge del bot vs senales de traders y escribe una corrida JSONL."
    )
    parser.add_argument("--signals", default=SIGNALS_FILE)
    parser.add_argument("--shadow", default=SHADOW_FILE)
    parser.add_argument("--policy", default=POLICY_FILE)
    parser.add_argument("--output", default=OUT_FILE)
    parser.add_argument("--no-append", action="store_true")
    return parser.parse_args()


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
    stats = defaultdict(
        lambda: {
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
        }
    )

    for signal in signals:
        city = signal["city"]
        st = stats[city]
        st["n_signals"] += 1
        if signal["has_consensus"]:
            st["n_consensus"] += 1
            st["has_consensus_market"] = True
        st["dates"].add(signal["date"])
        st["conditions"].add(signal["condition"])
        st["traders"].add(signal["trader"])
        if signal["trader_win_rate"] > st["max_wr"]:
            st["max_wr"] = signal["trader_win_rate"]
            st["best_example"] = signal
        st["signals_by_date"][signal["date"]].append(signal)
        if signal["condition"] in ALLOWED_CONDITIONS:
            st["allowed_signals"].append(signal)

    return stats


def build_crosscheck_record(
    signals_path=SIGNALS_FILE,
    shadow_path=SHADOW_FILE,
    policy_path=POLICY_FILE,
    run_at=None,
):
    sig_data = load_json(signals_path)
    shadow_data = load_json(shadow_path)
    try:
        policy_data = load_json(policy_path)
    except Exception:
        policy_data = {}

    signals = sig_data["signals"]
    shadow_cities = shadow_data["cities"]
    signals_generated_at = sig_data.get("generated", "")
    shadow_updated_at = shadow_data.get("updated_at", "")
    effective_run_at = run_at or datetime.now(timezone.utc).isoformat()

    canary_cities = set(policy_data.get("auto_canary_cities", {}).keys())
    city_signal_stats = build_city_signal_stats(signals)
    signal_city_names = set(city_signal_stats.keys())

    bot_edge_cities = {
        city
        for city, data in shadow_cities.items()
        if data.get("edge_hits", 0) >= EDGE_HIT_THRESHOLD
    }

    match_cities = sorted(signal_city_names & bot_edge_cities)
    bot_only_cities = sorted(bot_edge_cities - signal_city_names)
    trader_only_cities = sorted(signal_city_names - bot_edge_cities)

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

    match_rows = [make_city_row(city, "MATCH") for city in match_cities]
    bot_only_rows = [make_city_row(city, "BOT_ONLY") for city in bot_only_cities]
    trader_only_rows = [make_city_row(city, "TRADER_ONLY") for city in trader_only_cities]

    consensus_match = sum(1 for row in match_rows if row["has_consensus_market"])
    consensus_trader_only = sum(1 for row in trader_only_rows if row["has_consensus_market"])
    actionable_trader_only = [row for row in trader_only_rows if row["n_allowed_conditions"] > 0]
    match_with_allowed = [row for row in match_rows if row["n_allowed_conditions"] > 0]

    jsonl_record = {
        "run_at": effective_run_at,
        "signals_generated_at": signals_generated_at,
        "shadow_updated_at": shadow_updated_at,
        "match_cities": [row["city"] for row in match_rows],
        "bot_only_cities": [row["city"] for row in bot_only_rows],
        "trader_only_cities": [row["city"] for row in trader_only_rows],
        "match_count": len(match_cities),
        "bot_only_count": len(bot_only_cities),
        "trader_only_count": len(trader_only_cities),
        "consensus_match_count": consensus_match,
        "consensus_trader_only_count": consensus_trader_only,
        "actionable_trader_only_count": len(actionable_trader_only),
        "match_with_allowed_count": len(match_with_allowed),
        "match_details": match_rows,
        "bot_only_details": bot_only_rows,
        "trader_only_details": trader_only_rows,
    }
    return jsonl_record, sig_data


def append_record(record, output_path=OUT_FILE):
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def print_crosscheck_report(jsonl_record, sig_data, output_path):
    print(f"# signals_vs_edge_crosscheck - {jsonl_record['run_at'][:19]} UTC")
    print(f"signals.json: {jsonl_record['signals_generated_at'][:19]}")
    print(f"shadow_city_tracking: {jsonl_record['shadow_updated_at'][:19]}")
    print()

    match_rows = jsonl_record["match_details"]
    bot_only_rows = jsonl_record["bot_only_details"]
    trader_only_rows = jsonl_record["trader_only_details"]
    match_cities = jsonl_record["match_cities"]
    trader_only_cities = jsonl_record["trader_only_cities"]
    actionable_trader_only = [row for row in trader_only_rows if row["n_allowed_conditions"] > 0]
    match_with_allowed = [row for row in match_rows if row["n_allowed_conditions"] > 0]
    signals = sig_data.get("signals", [])

    def print_table(title, rows, cols):
        print(f"## {title} ({len(rows)} cities)")
        if not rows:
            print("  (none)")
            print()
            return
        header = "| " + " | ".join(cols) + " |"
        sep = "| " + " | ".join(["---"] * len(cols)) + " |"
        print(header)
        print(sep)
        for row in rows:
            def fmt(key):
                value = row.get(key, "")
                if isinstance(value, list):
                    return ",".join(str(item) for item in value)
                if isinstance(value, float):
                    return f"{value:.1f}"
                if isinstance(value, bool):
                    return "Y" if value else ""
                return str(value) if value is not None else ""

            print("| " + " | ".join(fmt(col) for col in cols) + " |")
        print()

    match_cols = [
        "city",
        "edge_hits",
        "bot_best_edge_pct",
        "n_signals",
        "n_consensus",
        "n_allowed_conditions",
        "is_canary",
        "conditions",
    ]
    bot_cols = ["city", "edge_hits", "cycles_seen", "bot_best_edge_pct"]
    trader_cols = [
        "city",
        "n_signals",
        "n_consensus",
        "n_allowed_conditions",
        "max_trader_wr",
        "has_consensus_market",
        "conditions",
    ]

    print_table("MATCH - bot edge AND trader signals", match_rows, match_cols)
    print_table("BOT_ONLY - bot edge, NO trader signals", bot_only_rows, bot_cols)
    print_table("TRADER_ONLY - trader signals, bot edge_hits=0", trader_only_rows, trader_cols)

    print("## Summary")
    print(f"- Total signals: {len(signals)} ({sig_data.get('n_quality_traders', 0)} quality traders)")
    print(
        f"- MATCH:        {jsonl_record['match_count']} cities "
        f"({jsonl_record['consensus_match_count']} with consensus, {len(match_with_allowed)} with allowed conds)"
    )
    print(f"- BOT_ONLY:     {jsonl_record['bot_only_count']} cities (bot sees edge, traders ignore)")
    print(
        f"- TRADER_ONLY:  {jsonl_record['trader_only_count']} cities "
        f"({jsonl_record['consensus_trader_only_count']} with consensus, {len(actionable_trader_only)} with allowed conds)"
    )
    print()

    print("## Validation checks")
    signal_cities = {str(signal.get("city", "")) for signal in signals if isinstance(signal, dict)}
    if "Austin" in signal_cities:
        austin_ok = "Austin" in trader_only_cities
        print(
            f"- Austin in TRADER_ONLY: {'PASS' if austin_ok else 'FAIL'} "
            "(expected when Austin is present in signals)"
        )
        if not austin_ok:
            print("  ERROR: Austin should be TRADER_ONLY - check city name matching")
            sys.exit(1)
    else:
        print("- Austin in TRADER_ONLY: SKIP (Austin not present in current signals snapshot)")

    seoul_ok = "Seoul" in match_cities
    print(f"- Seoul in MATCH:        {'PASS' if seoul_ok else 'FAIL'} (expected: canary with edge_hits>=1)")
    if not seoul_ok:
        print("  ERROR: Seoul should be MATCH - check shadow_city_tracking edge_hits")
        sys.exit(1)
    print()

    if actionable_trader_only:
        print("## Actionable TRADER_ONLY (allowed conditions - bot could trade these)")
        for row in sorted(actionable_trader_only, key=lambda item: -item["n_consensus"]):
            example = row.get("best_signal_example", {})
            match_key = example.get("match_key", "")
            print(
                f"  - {row['city']}: {row['n_allowed_conditions']} allowed signals, "
                f"n_consensus={row['n_consensus']}, max_wr={row['max_trader_wr']:.0f}%"
                f"{' | example: ' + match_key if match_key else ''}"
            )

    print()
    print(f"Output appended to: {output_path}")


def run_crosscheck(
    signals_path=SIGNALS_FILE,
    shadow_path=SHADOW_FILE,
    policy_path=POLICY_FILE,
    output_path=OUT_FILE,
    append=True,
):
    jsonl_record, sig_data = build_crosscheck_record(
        signals_path=signals_path,
        shadow_path=shadow_path,
        policy_path=policy_path,
    )
    if append:
        append_record(jsonl_record, output_path=output_path)
    print_crosscheck_report(jsonl_record, sig_data, output_path)
    return jsonl_record


if __name__ == "__main__":
    args = parse_args()
    run_crosscheck(
        signals_path=args.signals,
        shadow_path=args.shadow,
        policy_path=args.policy,
        output_path=args.output,
        append=not args.no_append,
    )
