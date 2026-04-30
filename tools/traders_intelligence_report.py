#!/usr/bin/env python3
"""Build a read-only v0 intelligence layer for tracked traders."""

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SIGNALS_PATH = REPO_ROOT / "data" / "runtime_import" / "signals.json"
DEFAULT_CENSUS_PATH = REPO_ROOT / "data" / "directional_trader_census.json"
DEFAULT_ENRICHMENT_PATH = REPO_ROOT / "data" / "directional_trader_enrichment.json"
DEFAULT_CITY_CROSS_PATH = REPO_ROOT / "data" / "reference_trader_city_market_cross.json"
DEFAULT_CROSSCHECK_LIVE_PATH = REPO_ROOT / "data" / "signals_crosscheck.jsonl"
DEFAULT_CROSSCHECK_LEGACY_PATH = REPO_ROOT / "data" / "runtime_import_derived" / "signals_crosscheck.jsonl"
DEFAULT_CROSSCHECK_PATH = DEFAULT_CROSSCHECK_LIVE_PATH
DEFAULT_BLOCKED_LIVE_PATH = REPO_ROOT / "data" / "blocked_signals_resolutions.jsonl"
DEFAULT_BLOCKED_LEGACY_PATH = REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
DEFAULT_BLOCKED_PATH = DEFAULT_BLOCKED_LIVE_PATH
DEFAULT_LIFECYCLE_PATH = REPO_ROOT / "data" / "runtime_import" / "trade_lifecycle.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "traders_intelligence.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "traders_intelligence_latest.md"


UNANSWERABLE_REASON = (
    "v0 no archiva serie de signals.json; sin snapshots periódicos no se puede inferir SL/TP."
)
HOLD_REASON = (
    "v0 no archiva serie de signals.json; sin snapshots periódicos no se puede medir first_seen/last_seen."
)
SCALING_REASON = (
    "v0 no archiva serie de signals.json; sin trayectoria de avg_price no se puede inferir scale-in/scale-out."
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Construye la capa read-only traders_intelligence v0 sobre artefactos existentes."
    )
    parser.add_argument("--signals", default=str(DEFAULT_SIGNALS_PATH), help="Ruta a data/runtime_import/signals.json.")
    parser.add_argument("--census", default=str(DEFAULT_CENSUS_PATH), help="Ruta a directional_trader_census.json.")
    parser.add_argument("--enrichment", default=str(DEFAULT_ENRICHMENT_PATH), help="Ruta a directional_trader_enrichment.json.")
    parser.add_argument("--city-cross", default=str(DEFAULT_CITY_CROSS_PATH), help="Ruta a reference_trader_city_market_cross.json.")
    parser.add_argument("--crosscheck-series", default=str(DEFAULT_CROSSCHECK_PATH), help="Ruta a signals_crosscheck.jsonl.")
    parser.add_argument("--blocked-resolutions", default=str(DEFAULT_BLOCKED_PATH), help="Ruta a blocked_signals_resolutions.jsonl.")
    parser.add_argument("--trade-lifecycle", default=str(DEFAULT_LIFECYCLE_PATH), help="Ruta a trade_lifecycle.json.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT), help="Ruta del JSON de salida.")
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT), help="Ruta del markdown de salida.")
    parser.add_argument("--min-evidence", type=int, default=5, help="Minimo de evidencia para emitir tags discretos.")
    return parser.parse_args()


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_existing_path(path_str, fallback_paths=()):
    checked = []
    for candidate in [Path(path_str), *[Path(path) for path in fallback_paths]]:
        if candidate in checked:
            continue
        checked.append(candidate)
        if candidate.exists():
            return candidate, checked
    return checked[0], checked


def format_paths_checked(paths):
    return ", ".join(str(path) for path in paths)


def load_json_file(path_str, label, warnings):
    path = Path(path_str)
    if not path.exists():
        warnings.append(f"{label} missing: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        warnings.append(f"{label} unreadable: {path} ({exc})")
        return None


def load_jsonl_file(path_str, label, warnings, paths_checked=None):
    path = Path(path_str)
    if not path.exists():
        checked = paths_checked or [path]
        warnings.append(f"{label} missing: paths_checked=[{format_paths_checked(checked)}]")
        return []
    rows = []
    try:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                warnings.append(f"{label} contains invalid JSONL row in {path}")
                break
    except Exception as exc:
        warnings.append(f"{label} unreadable: {path} ({exc})")
    return rows


def parse_iso(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_name(value):
    return str(value or "").strip().lower()


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return round(ordered[0], 4)
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[lower], 4)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 4)


def confidence_from_n(n, high_threshold=10, medium_threshold=3):
    if n >= high_threshold:
        return "high"
    if n >= medium_threshold:
        return "medium"
    if n > 0:
        return "low"
    return "insufficient_data"


def summarize_entry_price_band(values):
    if not values:
        return None
    return {
        "p25": percentile(values, 0.25),
        "p50": percentile(values, 0.50),
        "p75": percentile(values, 0.75),
        "n": len(values),
    }


def summarize_outcome_bias(counter):
    total = sum(counter.values())
    if total <= 0:
        return {}
    yes = float(counter.get("Yes", 0) or 0)
    no = float(counter.get("No", 0) or 0)
    other = max(total - yes - no, 0.0)
    return {
        "Yes": round((yes / total) * 100, 1),
        "No": round((no / total) * 100, 1),
        "Other": round((other / total) * 100, 1),
    }


def pick_preference(counter):
    if not counter:
        return None, 0, 0.0
    total = sum(counter.values())
    name, count = max(counter.items(), key=lambda item: (item[1], item[0]))
    share = (count / total) if total else 0.0
    return name, count, round(share, 4)


def build_signals_lookup(signals_payload):
    trader_map = defaultdict(list)
    consensus_mentions = Counter()
    signal_rows = []

    if not signals_payload:
        return trader_map, consensus_mentions, signal_rows

    for signal in signals_payload.get("signals", []):
        trader = str(signal.get("trader", "")).strip()
        if not trader:
            continue
        key = normalize_name(trader)
        signal_copy = dict(signal)
        signal_copy["_trader_name"] = trader
        trader_map[key].append(signal_copy)
        signal_rows.append(signal_copy)
        for other in signal.get("consensus_with", []) or []:
            if other:
                consensus_mentions[normalize_name(other)] += 1

    return trader_map, consensus_mentions, signal_rows


def build_blocked_lookup(rows):
    blocked_map = defaultdict(list)
    for row in rows:
        trader = normalize_name(row.get("trader"))
        if not trader:
            continue
        blocked_map[trader].append(row)
    return blocked_map


def build_city_cross_lookup(city_cross_payload):
    city_rows = {}
    if not city_cross_payload:
        return city_rows
    for row in city_cross_payload.get("city_rows", []):
        city = str(row.get("city", "")).strip()
        if city:
            city_rows[normalize_name(city)] = row
    return city_rows


def build_enrichment_lookup(enrichment_payload):
    enrichment_map = {}
    summary = {}
    if not enrichment_payload:
        return enrichment_map, summary
    summary = enrichment_payload.get("summary", {})
    for row in enrichment_payload.get("traders", []):
        pseudonym = str(row.get("pseudonym", "")).strip()
        address = str(row.get("address", "")).strip()
        if pseudonym:
            enrichment_map[normalize_name(pseudonym)] = row
        elif address:
            enrichment_map[normalize_name(address)] = row
    return enrichment_map, summary


def build_census_lookup(census_payload):
    census_map = {}
    summary = {}
    if not census_payload:
        return census_map, summary
    summary = census_payload.get("summary", {})
    for row in census_payload.get("traders", []):
        pseudonym = str(row.get("pseudonym", "")).strip()
        address = str(row.get("address", "")).strip()
        if pseudonym:
            census_map[normalize_name(pseudonym)] = row
        elif address:
            census_map[normalize_name(address)] = row
    return census_map, summary


def latest_crosscheck_record(rows):
    if not rows:
        return None
    return max(rows, key=lambda row: parse_iso(row.get("run_at")) or datetime.min.replace(tzinfo=timezone.utc))


def recent_crosscheck_rows(rows, limit=7):
    ordered = sorted(
        rows,
        key=lambda row: parse_iso(row.get("run_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return ordered[:limit]


def summarize_recent_crosscheck(rows):
    trader_only_counts = Counter()
    match_counts = Counter()
    total_rows = len(rows)

    for row in rows:
        for city in row.get("trader_only_cities", []) or []:
            trader_only_counts[str(city)] += 1
        for city in row.get("match_cities", []) or []:
            match_counts[str(city)] += 1

    return {
        "recent_runs": total_rows,
        "top_trader_only_persistence": [
            {"city": city, "runs": runs}
            for city, runs in trader_only_counts.most_common(10)
        ],
        "top_match_persistence": [
            {"city": city, "runs": runs}
            for city, runs in match_counts.most_common(10)
        ],
    }


def current_multi_strike_groups(signals):
    groups = defaultdict(set)
    for row in signals:
        city = row.get("city")
        date = row.get("date")
        condition = row.get("condition")
        unit = row.get("unit")
        temp = row.get("temp")
        if city and date and condition and unit and temp is not None:
            groups[(city, date, condition, unit)].add(temp)

    results = []
    for (city, date, condition, unit), strikes in groups.items():
        if len(strikes) < 2:
            continue
        ordered = sorted(strikes)
        results.append({
            "city": city,
            "date": date,
            "condition": condition,
            "unit": unit,
            "n_strikes": len(ordered),
            "strikes": ordered,
        })
    results.sort(key=lambda row: (-row["n_strikes"], row["city"], row["date"], row["condition"]))
    return results


def compute_profile_tags(
    trader_name,
    census_snapshot,
    blocked_rows,
    multi_strike_rows,
    consensus_mentions,
    min_evidence,
):
    tags = []
    city_counter = Counter(census_snapshot.get("top_cities", {}))
    condition_counter = Counter(census_snapshot.get("conditions", {}))
    outcome_counter = Counter(census_snapshot.get("outcomes", {}))

    dominant_city, city_count, city_share = pick_preference(city_counter)
    if dominant_city and city_count >= min_evidence and city_share >= 0.60:
        tags.append(f"specialist_{dominant_city}")

    dominant_condition, condition_count, condition_share = pick_preference(condition_counter)
    if dominant_condition and condition_count >= min_evidence and condition_share >= 0.60:
        tags.append(f"specialist_{dominant_condition}")

    total_outcomes = sum(outcome_counter.values())
    if total_outcomes >= min_evidence:
        yes_share = (outcome_counter.get("Yes", 0) / total_outcomes) if total_outcomes else 0.0
        no_share = (outcome_counter.get("No", 0) / total_outcomes) if total_outcomes else 0.0
        if yes_share - no_share > 0.30:
            tags.append("yes_biased")
        elif no_share - yes_share > 0.30:
            tags.append("no_biased")

    if multi_strike_rows:
        tags.append("multi_strike_issuer")

    mention_count = int(consensus_mentions.get(normalize_name(trader_name), 0) or 0)
    if mention_count >= 3:
        tags.append("consensus_hub")

    prices = [float(row.get("avg_price_entered", 0) or 0) for row in blocked_rows if row.get("avg_price_entered") is not None]
    if len(prices) >= min_evidence:
        avg_entry = sum(prices) / len(prices)
        wins = sum(1 for row in blocked_rows if row.get("win_for_trader") is True)
        wr = (wins / len(blocked_rows)) * 100 if blocked_rows else 0.0
        if avg_entry <= 0.30:
            tags.append("deep_value_entrant")
        if avg_entry >= 0.70:
            tags.append("favorite_entrant")
        if wr >= 70.0:
            tags.append("high_blocked_wr")

    return sorted(set(tags))


def compute_candidate_profiles(census_snapshot, blocked_rows, multi_strike_rows, min_evidence):
    profiles = []
    price_style = census_snapshot.get("price_style")
    condition_counter = Counter(census_snapshot.get("conditions", {}))
    outcome_counter = Counter(census_snapshot.get("outcomes", {}))
    blocked_prices = [float(row.get("avg_price_entered", 0) or 0) for row in blocked_rows if row.get("avg_price_entered") is not None]
    blocked_avg = (sum(blocked_prices) / len(blocked_prices)) if blocked_prices else None
    dominant_condition, condition_count, _ = pick_preference(condition_counter)

    if dominant_condition in {"exact", "at_or_above", "at_or_below"} and not multi_strike_rows and condition_count >= min_evidence:
        profiles.append({
            "name": "directional_forecaster",
            "confidence": "medium",
            "evidence": [
                f"census.conditions dominant={dominant_condition} n={condition_count}",
                f"census.price_style={price_style}",
            ],
        })

    if multi_strike_rows:
        profiles.append({
            "name": "multi_strike_structurer",
            "confidence": "medium",
            "evidence": [f"signals.json multi_strike_groups={len(multi_strike_rows)}"],
        })

    if blocked_avg is not None and len(blocked_prices) >= min_evidence and blocked_avg >= 0.75:
        profiles.append({
            "name": "favorite_chaser",
            "confidence": "medium",
            "evidence": [f"blocked_signals_resolutions.jsonl avg_entry={blocked_avg:.4f} n={len(blocked_prices)}"],
        })

    if blocked_avg is not None and len(blocked_prices) >= min_evidence and blocked_avg <= 0.30:
        profiles.append({
            "name": "deep_value_taker",
            "confidence": "medium",
            "evidence": [f"blocked_signals_resolutions.jsonl avg_entry={blocked_avg:.4f} n={len(blocked_prices)}"],
        })

    if not profiles and sum(outcome_counter.values()) > 0:
        profiles.append({
            "name": "insufficient_profile_signal",
            "confidence": "low",
            "evidence": ["v0 evidence insufficient for a stronger archetype"],
        })

    return profiles


def build_trader_block(
    trader_name,
    enrichment_row,
    census_row,
    signals,
    blocked_rows,
    latest_crosscheck,
    consensus_mentions,
    min_evidence,
):
    census_snapshot = {}
    if enrichment_row:
        census_snapshot = enrichment_row.get("census_snapshot", {}) or {}
    if not census_snapshot and census_row:
        census_snapshot = census_row

    closed_summary = enrichment_row.get("closed_summary", {}) if enrichment_row else {}
    reference_quality = enrichment_row.get("reference_quality", "unknown") if enrichment_row else "unknown"
    address = None
    if enrichment_row:
        address = enrichment_row.get("address")
    elif census_snapshot:
        address = census_snapshot.get("address")

    active_cities = sorted({str(row.get("city")) for row in signals if row.get("city")})
    current_signals_count = len(signals)
    multi_strike_rows = current_multi_strike_groups(signals)

    activity_confidence = "high" if current_signals_count and closed_summary else "medium" if (current_signals_count or closed_summary) else "insufficient_data"
    activity_block = {
        "n_active_signals_now": current_signals_count,
        "n_distinct_cities_active_now": len(active_cities),
        "n_closed_positions_recent": int(closed_summary.get("n_closed_positions", 0) or 0) if closed_summary else 0,
        "closed_weather_conditions": closed_summary.get("closed_weather_conditions", {}) if closed_summary else {},
        "confidence": activity_confidence,
        "evidence": [
            f"signals.json n={current_signals_count}",
            f"directional_trader_enrichment.json closed_n={int(closed_summary.get('n_closed_positions', 0) or 0)}",
        ],
    }

    style_city_counter = Counter(census_snapshot.get("top_cities", {}))
    if not style_city_counter and active_cities:
        style_city_counter = Counter(row.get("city") for row in signals if row.get("city"))
    style_condition_counter = Counter(census_snapshot.get("conditions", {}))
    if not style_condition_counter and signals:
        style_condition_counter = Counter(row.get("condition") for row in signals if row.get("condition"))
    style_outcome_counter = Counter(census_snapshot.get("outcomes", {}))
    if not style_outcome_counter and signals:
        style_outcome_counter = Counter(row.get("outcome") for row in signals if row.get("outcome"))

    dominant_city, _, _ = pick_preference(style_city_counter)
    dominant_condition, condition_count, _ = pick_preference(style_condition_counter)
    price_samples = [
        float(sample.get("price", 0) or 0)
        for sample in census_snapshot.get("sample_positions", []) or []
        if sample.get("price") is not None
    ]
    price_samples.extend(
        float(row.get("avg_price_entered", 0) or 0)
        for row in blocked_rows
        if row.get("avg_price_entered") is not None
    )
    price_band = summarize_entry_price_band(price_samples)
    style_confidence = confidence_from_n(price_band["n"] if price_band else 0)
    style_block = {
        "dominant_city": dominant_city,
        "top_cities": dict(style_city_counter),
        "condition_preference": dominant_condition,
        "outcome_bias_pct": summarize_outcome_bias(style_outcome_counter),
        "price_style": census_snapshot.get("price_style"),
        "entry_price_band": price_band,
        "confidence": style_confidence,
        "evidence": [
            f"census.sample_positions n={len(census_snapshot.get('sample_positions', []) or [])}",
            f"blocked_signals_resolutions.jsonl n={len(blocked_rows)}",
        ],
    }

    unique_consensus_match_keys = len({row.get("match_key") for row in signals if row.get("has_consensus")})
    unique_counterparties = sorted({
        other
        for row in signals
        for other in (row.get("consensus_with", []) or [])
        if other
    })
    grid_confidence = "high" if signals else "insufficient_data"
    grid_block = {
        "multi_strike_signals": multi_strike_rows,
        "any_consensus_with_others": unique_consensus_match_keys > 0,
        "n_consensus_match_keys": unique_consensus_match_keys,
        "n_consensus_counterparties": len(unique_counterparties),
        "confidence": grid_confidence,
        "evidence": [f"signals.json signals n={current_signals_count}"],
    }

    realized_confidence = "medium" if closed_summary else "insufficient_data"
    realized_block = {
        "closed_win_rate_pct": closed_summary.get("win_rate"),
        "closed_pnl_cash": closed_summary.get("total_closed_pnl"),
        "closed_n": closed_summary.get("n_closed_positions"),
        "confidence": realized_confidence,
        "caveat": "Polymarket enrichment cohort, no necesariamente weather-only",
        "evidence": [f"directional_trader_enrichment.json closed_n={int(closed_summary.get('n_closed_positions', 0) or 0)}"],
    }

    blocked_wins = sum(1 for row in blocked_rows if row.get("win_for_trader") is True)
    blocked_avg_entry = round(
        sum(float(row.get("avg_price_entered", 0) or 0) for row in blocked_rows) / len(blocked_rows),
        4,
    ) if blocked_rows else None
    blocked_avg_close = round(
        sum(float(row.get("close_price", 0) or 0) for row in blocked_rows) / len(blocked_rows),
        4,
    ) if blocked_rows else None
    blocked_confidence = confidence_from_n(len(blocked_rows), high_threshold=max(min_evidence, 10), medium_threshold=1)
    blocked_block = {
        "n_resolved": len(blocked_rows),
        "n_wins": blocked_wins,
        "wr_pct": round((blocked_wins / len(blocked_rows)) * 100, 1) if blocked_rows else None,
        "avg_entry_price": blocked_avg_entry,
        "avg_close_price": blocked_avg_close,
        "confidence": blocked_confidence,
        "evidence": [f"blocked_signals_resolutions.jsonl n={len(blocked_rows)}"],
    }

    if latest_crosscheck:
        match_cities = set(latest_crosscheck.get("match_cities", []) or [])
        trader_only_cities = set(latest_crosscheck.get("trader_only_cities", []) or [])
        signal_cities = {row.get("city") for row in signals if row.get("city")}
        overlap_signals = [row for row in signals if row.get("city") in match_cities]
        vs_bot_block = {
            "recent_crosscheck_run_at": latest_crosscheck.get("run_at"),
            "n_match_keys_overlap_recent": len({row.get("match_key") for row in overlap_signals if row.get("match_key")}),
            "n_cities_bot_only": int(latest_crosscheck.get("bot_only_count", 0) or 0),
            "n_cities_trader_only": len(signal_cities & trader_only_cities),
            "trader_only_cities_now": sorted(signal_cities & trader_only_cities),
            "confidence": "high",
            "evidence": [
                "signals.json active signals",
                "signals_crosscheck.jsonl latest record",
            ],
        }
    else:
        vs_bot_block = {
            "recent_crosscheck_run_at": None,
            "n_match_keys_overlap_recent": None,
            "n_cities_bot_only": None,
            "n_cities_trader_only": None,
            "trader_only_cities_now": [],
            "confidence": "insufficient_data",
            "evidence": ["signals_crosscheck.jsonl missing"],
        }

    profile_tags = compute_profile_tags(
        trader_name,
        census_snapshot,
        blocked_rows,
        multi_strike_rows,
        consensus_mentions,
        min_evidence,
    )
    candidate_profiles = compute_candidate_profiles(
        census_snapshot,
        blocked_rows,
        multi_strike_rows,
        min_evidence,
    )

    return {
        "pseudonym": trader_name,
        "address": address,
        "reference_quality": reference_quality,
        "activity": activity_block,
        "style": style_block,
        "grid_structure": grid_block,
        "realized_performance": realized_block,
        "blocked_signal_performance": blocked_block,
        "vs_bot": vs_bot_block,
        "exit_behaviour": {
            "answerable": False,
            "reason": UNANSWERABLE_REASON,
            "confidence": "insufficient_data",
        },
        "hold_duration": {
            "answerable": False,
            "reason": HOLD_REASON,
            "confidence": "insufficient_data",
        },
        "scaling_behaviour": {
            "answerable": False,
            "reason": SCALING_REASON,
            "confidence": "insufficient_data",
        },
        "candidate_profiles": candidate_profiles,
        "profile_tags": profile_tags,
    }


def build_city_rollup(signals_rows, city_cross_lookup, latest_crosscheck):
    city_to_signals = defaultdict(list)
    for row in signals_rows:
        city = str(row.get("city", "")).strip()
        if city:
            city_to_signals[city].append(row)

    latest_match_cities = set(latest_crosscheck.get("match_cities", []) or []) if latest_crosscheck else set()
    rollup = []

    for city, rows in city_to_signals.items():
        trader_counts = Counter(row.get("trader") for row in rows if row.get("trader"))
        dominant_trader = trader_counts.most_common(1)[0][0] if trader_counts else None
        cross_row = city_cross_lookup.get(normalize_name(city), {})
        rollup.append({
            "city": city,
            "policy_mode": cross_row.get("policy_mode", "shadow"),
            "n_reference_traders_active": len(trader_counts),
            "dominant_trader_now": dominant_trader,
            "any_consensus_now": any(bool(row.get("has_consensus")) for row in rows),
            "bot_overlap_recent": city in latest_match_cities if latest_crosscheck else False,
            "confidence": "high" if latest_crosscheck else "medium",
            "evidence": [
                f"signals.json active_signals={len(rows)}",
                "reference_trader_city_market_cross.json",
            ],
        })

    rollup.sort(
        key=lambda row: (
            -row["n_reference_traders_active"],
            row["policy_mode"] != "canary",
            row["city"],
        )
    )
    return rollup


def build_bot_context(lifecycle_payload):
    if not lifecycle_payload:
        return {
            "summary": {},
            "confidence": "insufficient_data",
            "evidence": ["trade_lifecycle.json missing"],
        }

    summary = lifecycle_payload.get("summary", {}) or {}
    return {
        "summary": {
            "tracked_positions": summary.get("tracked_positions"),
            "open_positions": summary.get("open_positions"),
            "closed_positions": summary.get("closed_positions"),
            "take_profit_closes": summary.get("take_profit_closes"),
            "stop_loss_closes": summary.get("stop_loss_closes"),
            "reeval_closes": summary.get("reeval_closes"),
            "with_market_data_after_close": summary.get("with_market_data_after_close"),
        },
        "confidence": "high",
        "evidence": ["trade_lifecycle.json summary"],
    }


def compute_health_status(traders, missing_labels, likely_input_degraded):
    if not traders:
        return "unusable"
    if likely_input_degraded or missing_labels:
        return "degraded"
    return "usable_signal"


def render_markdown(payload):
    lines = [
        "# Traders Intelligence - latest run",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Health status: `{payload['health_status']}`",
        f"- Traders profiled: `{payload['integrity']['n_traders_profiled']}`",
        f"- Census stale days: `{payload['integrity']['census_stale_days']}`",
        f"- Bot closed positions context: `{payload['bot_context']['summary'].get('closed_positions')}`",
        "",
        "## Traders",
        "",
        "| Trader | Quality | Dominant city | Condition pref | Outcome bias | Closed WR | Blocked WR | Active now | Tags |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for trader in payload.get("traders", []):
        style = trader.get("style", {})
        blocked = trader.get("blocked_signal_performance", {})
        realized = trader.get("realized_performance", {})
        bias = style.get("outcome_bias_pct", {})
        if bias:
            bias_text = f"Y {bias.get('Yes', 0)} / N {bias.get('No', 0)}"
        else:
            bias_text = "-"
        tags = ", ".join(trader.get("profile_tags", [])) or "-"
        lines.append(
            f"| {trader['pseudonym']} | {trader.get('reference_quality', 'unknown')} | "
            f"{style.get('dominant_city') or '-'} | {style.get('condition_preference') or '-'} | "
            f"{bias_text} | {realized.get('closed_win_rate_pct') if realized.get('closed_win_rate_pct') is not None else '-'} | "
            f"{blocked.get('wr_pct') if blocked.get('wr_pct') is not None else '-'} | "
            f"{trader.get('activity', {}).get('n_active_signals_now', 0)} | {tags} |"
        )

    lines.extend([
        "",
        "## No responde honestamente hoy",
        "",
        f"- `exit_behaviour`: {UNANSWERABLE_REASON}",
        f"- `hold_duration`: {HOLD_REASON}",
        f"- `scaling_behaviour`: {SCALING_REASON}",
        "",
        "## Top mismatches recientes",
        "",
    ])

    recent = payload.get("aggregate", {}).get("recent_crosscheck", {})
    trader_only_rows = recent.get("top_trader_only_persistence", [])
    if trader_only_rows:
        lines.extend([
            "| City | Trader-only runs |",
            "| --- | --- |",
        ])
        for row in trader_only_rows[:10]:
            lines.append(f"| {row['city']} | {row['runs']} |")
    else:
        lines.append("- `signals_crosscheck.jsonl` no disponible para anexo reciente.")

    warnings = payload.get("warnings", [])
    if warnings:
        lines.extend([
            "",
            "## Warnings",
            "",
        ])
        for warning in warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    warnings = []

    crosscheck_path, crosscheck_paths_checked = resolve_existing_path(
        args.crosscheck_series,
        fallback_paths=[DEFAULT_CROSSCHECK_LEGACY_PATH],
    )
    blocked_path, blocked_paths_checked = resolve_existing_path(
        args.blocked_resolutions,
        fallback_paths=[DEFAULT_BLOCKED_LEGACY_PATH],
    )

    signals_payload = load_json_file(args.signals, "signals", warnings)
    census_payload = load_json_file(args.census, "census", warnings)
    enrichment_payload = load_json_file(args.enrichment, "enrichment", warnings)
    city_cross_payload = load_json_file(args.city_cross, "city_cross", warnings)
    crosscheck_rows = load_jsonl_file(
        crosscheck_path,
        "crosscheck_series",
        warnings,
        paths_checked=crosscheck_paths_checked,
    )
    blocked_rows = load_jsonl_file(
        blocked_path,
        "blocked_resolutions",
        warnings,
        paths_checked=blocked_paths_checked,
    )
    lifecycle_payload = load_json_file(args.trade_lifecycle, "trade_lifecycle", warnings)

    signals_by_trader, consensus_mentions, signal_rows = build_signals_lookup(signals_payload)
    blocked_by_trader = build_blocked_lookup(blocked_rows)
    enrichment_map, enrichment_summary = build_enrichment_lookup(enrichment_payload)
    census_map, census_summary = build_census_lookup(census_payload)
    city_cross_lookup = build_city_cross_lookup(city_cross_payload)
    latest_crosscheck = latest_crosscheck_record(crosscheck_rows)
    recent_crosschecks = recent_crosscheck_rows(crosscheck_rows, limit=7)

    trader_names = set(signals_by_trader.keys()) | set(enrichment_map.keys()) | set(census_map.keys()) | set(blocked_by_trader.keys())
    traders = []
    dropped = 0
    incomplete_profiles = []

    for trader_key in sorted(trader_names):
        enrichment_row = enrichment_map.get(trader_key)
        census_row = census_map.get(trader_key)
        trader_signals = signals_by_trader.get(trader_key, [])
        trader_blocked = blocked_by_trader.get(trader_key, [])

        trader_name = None
        if enrichment_row and enrichment_row.get("pseudonym"):
            trader_name = enrichment_row.get("pseudonym")
        elif census_row and census_row.get("pseudonym"):
            trader_name = census_row.get("pseudonym")
        elif trader_signals:
            trader_name = trader_signals[0].get("_trader_name")
        elif trader_blocked:
            trader_name = trader_blocked[0].get("trader")

        if not trader_name:
            dropped += 1
            continue

        trader_payload = build_trader_block(
            trader_name=trader_name,
            enrichment_row=enrichment_row,
            census_row=census_row,
            signals=trader_signals,
            blocked_rows=trader_blocked,
            latest_crosscheck=latest_crosscheck,
            consensus_mentions=consensus_mentions,
            min_evidence=args.min_evidence,
        )
        if not enrichment_row or not census_row:
            incomplete_profiles.append(trader_name)
        traders.append(trader_payload)

    traders.sort(
        key=lambda row: (
            row.get("reference_quality") != "high_priority_reference",
            row.get("reference_quality") != "candidate_reference",
            -(row.get("activity", {}).get("n_active_signals_now", 0) or 0),
            row.get("pseudonym", ""),
        )
    )

    city_rollup = build_city_rollup(signal_rows, city_cross_lookup, latest_crosscheck)
    bot_context = build_bot_context(lifecycle_payload)
    recent_crosscheck_summary = summarize_recent_crosscheck(recent_crosschecks)
    likely_input_degraded = bool(enrichment_summary.get("likely_input_degraded", False))

    missing_labels = []
    for label, payload in (
        ("signals", signals_payload),
        ("census", census_payload),
        ("enrichment", enrichment_payload),
        ("city_cross", city_cross_payload),
        ("crosscheck_series", crosscheck_rows),
        ("blocked_resolutions", blocked_rows),
        ("trade_lifecycle", lifecycle_payload),
    ):
        if payload is None or payload == []:
            missing_labels.append(label)

    generated_at = iso_now()
    census_generated_at = census_payload.get("generated_at") if census_payload else None
    census_dt = parse_iso(census_generated_at)
    census_stale_days = (datetime.now(timezone.utc) - census_dt).days if census_dt else None
    if census_stale_days is not None and census_stale_days > 14:
        warnings.append(f"census.generated_at is {census_stale_days} days old; top_cities/conditions may be stale")
    if blocked_rows:
        warnings.append(
            f"blocked_signals_resolutions.jsonl n={len(blocked_rows)} global; per-trader N varies"
        )
    if likely_input_degraded:
        warnings.append("directional_trader_enrichment.summary.likely_input_degraded=true")

    top_blocked_wr = []
    for trader in traders:
        blocked = trader.get("blocked_signal_performance", {})
        n_resolved = blocked.get("n_resolved") or 0
        wr_pct = blocked.get("wr_pct")
        if wr_pct is None or n_resolved < args.min_evidence:
            continue
        top_blocked_wr.append({
            "trader": trader.get("pseudonym"),
            "wr_pct": wr_pct,
            "n": n_resolved,
        })
    top_blocked_wr.sort(key=lambda row: (-row["wr_pct"], -row["n"], row["trader"]))

    aggregate = {
        "reference_quality_counts": enrichment_summary.get("reference_quality_counts", {}),
        "n_traders_profiled": len(traders),
        "n_high_priority": sum(1 for trader in traders if trader.get("reference_quality") == "high_priority_reference"),
        "n_low_signal": sum(1 for trader in traders if trader.get("reference_quality") == "low_signal"),
        "n_active_but_unproven": sum(1 for trader in traders if trader.get("reference_quality") == "active_but_unproven"),
        "top_blocked_wr": top_blocked_wr[:5],
        "traders_profile_incomplete": sorted(incomplete_profiles),
        "recent_crosscheck": recent_crosscheck_summary,
        "confidence": "high" if traders else "insufficient_data",
        "evidence": [
            "directional_trader_enrichment.json",
            "blocked_signals_resolutions.jsonl",
            "signals_crosscheck.jsonl",
        ],
    }

    payload = {
        "schema_version": "v0",
        "generated_at": generated_at,
        "health_status": compute_health_status(traders, missing_labels, likely_input_degraded),
        "inputs": {
            "signals": str(Path(args.signals)),
            "census": str(Path(args.census)),
            "enrichment": str(Path(args.enrichment)),
            "city_cross": str(Path(args.city_cross)),
            "crosscheck_series": str(crosscheck_path),
            "blocked_resolutions": str(blocked_path),
            "trade_lifecycle": str(Path(args.trade_lifecycle)),
        },
        "integrity": {
            "signals_generated_at": signals_payload.get("generated") if signals_payload else None,
            "census_generated_at": census_generated_at,
            "census_stale_days": census_stale_days,
            "enrichment_generated_at": enrichment_payload.get("generated_at") if enrichment_payload else None,
            "n_traders_profiled": len(traders),
            "n_traders_dropped_insufficient_data": dropped,
            "likely_input_degraded": likely_input_degraded,
            "missing_inputs": missing_labels,
        },
        "bot_context": bot_context,
        "traders": traders,
        "city_rollup": city_rollup,
        "aggregate": aggregate,
        "warnings": warnings,
    }

    json_path = ensure_parent(args.json_output)
    md_path = ensure_parent(args.md_output)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Traders intelligence written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps({
        "health_status": payload["health_status"],
        "n_traders_profiled": payload["integrity"]["n_traders_profiled"],
        "warnings": len(payload["warnings"]),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
