#!/usr/bin/env python3
"""Audit observed Polymarket temperature universe and temporal price behavior."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = REPO_ROOT / "data" / "runtime_import"
PRE_EDGE_REASONS = {
    "condition_filtered",
    "below_min_edge",
    "kelly_too_low",
    "no_edge",
    "shadow_only_override",
    "existing_position",
    "existing_order",
    "sold_this_cycle",
    "liquidity_low",
    "forecast_missing",
}
STALE_REASONS = {
    "date_out_of_range_past",
    "date_out_of_range_future",
    "timezone_filter",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit observed market universe and price_out_of_range temporal behavior from data/runtime_import."
    )
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=DEFAULT_RUNTIME_DIR,
        help=f"Runtime snapshot directory (default: {DEFAULT_RUNTIME_DIR}).",
    )
    parser.add_argument(
        "--last-n-cycles",
        type=int,
        default=29,
        help="Limit analysis to the last N normal cycles (default: 29).",
    )
    return parser.parse_args()


def parse_ts(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for raw in handle:
            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def pick_cycle_id(ts: datetime, known_cycles: dict[str, datetime]) -> str:
    candidate = ts.strftime("%Y-%m-%dT%H:%M")
    if candidate in known_cycles:
        return candidate
    for cycle_id, cycle_ts in known_cycles.items():
        if abs((cycle_ts - ts).total_seconds()) <= 120:
            return cycle_id
    return candidate


def load_cycle_maps(runtime_dir: Path) -> tuple[list[tuple[str, datetime, set[tuple[str, str, str]]]], Counter[int]]:
    skip_rows = load_jsonl(runtime_dir / "skip_log.jsonl")
    cycle_markets: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    cycle_ts: dict[str, datetime] = {}

    for row in skip_rows:
        city = row.get("city")
        date_iso = row.get("date_iso")
        question = row.get("question")
        cycle_id = row.get("cycle_id")
        if not city or not date_iso or not question or not cycle_id:
            continue
        cycle_markets[cycle_id].add((city, date_iso, question))
        cycle_ts[cycle_id] = parse_ts(row["ts_utc"])

    for row in load_jsonl(runtime_dir / "cycles_history.jsonl"):
        ts = parse_ts(row["timestamp_utc"])
        cycle_id = pick_cycle_id(ts, cycle_ts)
        cycle_ts[cycle_id] = ts
        for market in row.get("scanned_markets", []) or []:
            city = market.get("city")
            date_iso = market.get("date")
            question = market.get("question")
            if not city or not date_iso or not question:
                continue
            cycle_markets[cycle_id].add((city, date_iso, question))

    ordered = sorted(
        ((cycle_id, cycle_ts[cycle_id], cycle_markets[cycle_id]) for cycle_id in cycle_markets),
        key=lambda item: item[1],
    )
    normal_cycles = [(cycle_id, ts, markets) for cycle_id, ts, markets in ordered if len(markets) >= 320]
    return normal_cycles, Counter(len(markets) for _, _, markets in normal_cycles)


def build_market_histories(runtime_dir: Path) -> dict[tuple[str, str, str], list[tuple[datetime, str, float | None]]]:
    histories: dict[tuple[str, str, str], list[tuple[datetime, str, float | None]]] = defaultdict(list)
    for row in load_jsonl(runtime_dir / "skip_log.jsonl"):
        city = row.get("city")
        date_iso = row.get("date_iso")
        question = row.get("question")
        if not city or not date_iso or not question:
            continue
        histories[(city, date_iso, question)].append(
            (parse_ts(row["ts_utc"]), str(row.get("skip_reason") or ""), row.get("mkt_prob"))
        )

    for key in list(histories):
        histories[key].sort(key=lambda item: item[0])
    return histories


def render_pct(part: int, whole: int) -> str:
    if whole <= 0:
        return "n/a"
    return f"{(part / whole) * 100:.1f}%"


def main() -> None:
    args = parse_args()
    runtime_dir = args.runtime_dir
    normal_cycles, cycle_size_hist = load_cycle_maps(runtime_dir)
    if not normal_cycles:
        raise SystemExit("No normal cycles found.")

    selected_cycles = normal_cycles[-args.last_n_cycles :]
    cycle_ids = {cycle_id for cycle_id, _, _ in selected_cycles}
    counts = [len(markets) for _, _, markets in selected_cycles]
    city_date_to_questions: dict[tuple[str, str], set[str]] = defaultdict(set)
    unique_markets: set[tuple[str, str, str]] = set()
    per_cycle_city_dates: list[int] = []

    for _, _, markets in selected_cycles:
        city_dates = {(city, date_iso) for city, date_iso, _ in markets}
        per_cycle_city_dates.append(len(city_dates))
        for city, date_iso, question in markets:
            city_date_to_questions[(city, date_iso)].add(question)
            unique_markets.add((city, date_iso, question))

    city_date_hist = Counter(len(questions) for questions in city_date_to_questions.values())
    by_market_date = Counter()
    for (_, date_iso), questions in city_date_to_questions.items():
        by_market_date[date_iso] += len(questions)

    histories = build_market_histories(runtime_dir)
    price_summary = Counter()
    price_first_probs: list[float] = []
    price_max_probs: list[float] = []
    price_pre_edge_wait_hours: list[float] = []
    price_stale_wait_hours: list[float] = []
    city_price_total = Counter()
    city_price_pre_edge = Counter()

    for key, events in histories.items():
        price_indices = [idx for idx, (_, reason, _) in enumerate(events) if reason == "price_out_of_range"]
        if not price_indices:
            continue
        first_idx = price_indices[0]
        first_price_ts = events[first_idx][0]
        city = key[0]
        city_price_total[city] += 1
        price_summary["markets_with_price"] += 1

        price_probs = [
            float(prob)
            for _, reason, prob in events
            if reason == "price_out_of_range" and isinstance(prob, (int, float))
        ]
        if price_probs:
            price_first_probs.append(price_probs[0])
            price_max_probs.append(max(price_probs))

        later_non_price = [event for event in events[first_idx + 1 :] if event[1] != "price_out_of_range"]
        later_pre_edge = [event for event in later_non_price if event[1] in PRE_EDGE_REASONS]
        later_stale = [event for event in later_non_price if event[1] in STALE_REASONS]

        if later_pre_edge:
            price_summary["ever_pre_edge_after_price"] += 1
            city_price_pre_edge[city] += 1
            delta_h = (later_pre_edge[0][0] - first_price_ts).total_seconds() / 3600.0
            price_pre_edge_wait_hours.append(delta_h)
        elif later_stale:
            price_summary["stale_after_price_without_pre_edge"] += 1
            delta_h = (later_stale[0][0] - first_price_ts).total_seconds() / 3600.0
            price_stale_wait_hours.append(delta_h)
        else:
            price_summary["always_price_only"] += 1

    print("# Market Universe Audit")
    print()
    print(f"- runtime_dir: `{runtime_dir}`")
    print(f"- normal_cycles_read: `{len(selected_cycles)}`")
    print(
        f"- cycle_window: `{selected_cycles[0][1].isoformat()}` -> `{selected_cycles[-1][1].isoformat()}`"
    )
    print(f"- observed_markets_per_cycle: min `{min(counts)}`, median `{median(counts):.0f}`, max `{max(counts)}`")
    print(
        f"- city_date_pairs_per_cycle: min `{min(per_cycle_city_dates)}`, median `{median(per_cycle_city_dates):.0f}`, max `{max(per_cycle_city_dates)}`"
    )
    print(f"- unique_markets_in_window: `{len(unique_markets)}`")
    print(f"- unique_city_dates_in_window: `{len(city_date_to_questions)}`")
    print()
    print("## Normal Cycle Size Histogram")
    for size in sorted(cycle_size_hist):
        print(f"- `{size}` markets: `{cycle_size_hist[size]}` cycles")
    print()
    print("## City-Date Market Count Histogram")
    for size in sorted(city_date_hist):
        print(f"- `{size}` markets per city-date: `{city_date_hist[size]}` city-dates")
    print()
    print("## Market-Date Totals")
    for date_iso in sorted(by_market_date):
        print(f"- `{date_iso}`: `{by_market_date[date_iso]}` observed markets")
    print()
    print("# Price Temporal Audit")
    print()
    total_price = price_summary["markets_with_price"]
    print(f"- unique_markets_that_hit_price_out_of_range: `{total_price}`")
    print(
        "- outcome_split:"
        f" stale_only=`{price_summary['stale_after_price_without_pre_edge']}` ({render_pct(price_summary['stale_after_price_without_pre_edge'], total_price)}),"
        f" always_price=`{price_summary['always_price_only']}` ({render_pct(price_summary['always_price_only'], total_price)}),"
        f" ever_pre_edge=`{price_summary['ever_pre_edge_after_price']}` ({render_pct(price_summary['ever_pre_edge_after_price'], total_price)})"
    )
    if price_first_probs:
        lt20_first = sum(1 for value in price_first_probs if value < 20)
        lt20_max = sum(1 for value in price_max_probs if value < 20)
        print(
            f"- first_price_below_20: `{lt20_first}` / `{len(price_first_probs)}` ({render_pct(lt20_first, len(price_first_probs))})"
        )
        print(
            f"- max_seen_price_below_20: `{lt20_max}` / `{len(price_max_probs)}` ({render_pct(lt20_max, len(price_max_probs))})"
        )
    if price_pre_edge_wait_hours:
        print(
            f"- wait_to_pre_edge_hours: min `{min(price_pre_edge_wait_hours):.2f}`, median `{median(price_pre_edge_wait_hours):.2f}`, max `{max(price_pre_edge_wait_hours):.2f}`"
        )
    if price_stale_wait_hours:
        print(
            f"- wait_to_stale_hours: min `{min(price_stale_wait_hours):.2f}`, median `{median(price_stale_wait_hours):.2f}`, max `{max(price_stale_wait_hours):.2f}`"
        )
    print()
    print("## Cities With Most Price Bucket Markets")
    for city, total in city_price_total.most_common(12):
        pre_edge = city_price_pre_edge[city]
        print(
            f"- `{city}`: price_bucket=`{total}`, ever_pre_edge=`{pre_edge}` ({render_pct(pre_edge, total)})"
        )


if __name__ == "__main__":
    main()
