#!/usr/bin/env python3
"""Source Onboarding Scanner — LOG_ONLY read-only tool. City Intelligence v2, Fase A.

Detects cities outside the runtime flow that show strong external signal (traders,
blocked_signals, shadow leak) and prioritizes them for manual source audit.

NO BUY/SELL/SKIP. NO BANKROLL. NO Phase C. NO Telegram. NO Railway. NO DB writes.
NO city mode changes. NO auto-promotion. Read-only. Human review required before any action.

Universe: cities NOT already in ACTIVE / CANARY / BLOCKED / OBSERVED_AUDIT / auto_canary
          / auto_shadow / shadow_tracking (cycles >= MIN_SHADOW_CYCLES) / overrides.

Outputs:
  --json-output  data/source_onboarding.json
  --md-output    docs/source_onboarding_latest.md
"""

import argparse
import ast
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SIGNALS_CROSSCHECK = REPO_ROOT / "data" / "runtime_import_derived" / "signals_crosscheck.jsonl"
DEFAULT_BLOCKED_RESOLUTIONS = REPO_ROOT / "data" / "runtime_import_derived" / "blocked_signals_resolutions.jsonl"
DEFAULT_SHADOW_TRACKING = REPO_ROOT / "data" / "runtime_import" / "shadow_city_tracking.json"
DEFAULT_POLICY_ENV = REPO_ROOT / "data" / "runtime_import" / "policy_env_snapshot.json"
DEFAULT_POLICY_STATE = REPO_ROOT / "data" / "runtime_import" / "city_policy_state.json"
DEFAULT_OVERRIDES = REPO_ROOT / "data" / "city_lifecycle_overrides.json"
DEFAULT_TRADERS_REPORT = REPO_ROOT / "data" / "intelligence" / "traders_operational_questions_report.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "source_onboarding.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "source_onboarding_latest.md"

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY — This report is observational only. "
    "No BUY, SELL, or SKIP decisions. No BANKROLL changes. No Phase C. "
    "No city mode changes. No auto-promotion. "
    "Source audit candidates require explicit human review before any policy action."
)

# Scoring thresholds (adjust without redeploy)
SCORE_READY = 1.5
SCORE_WAITING = 0.5
RANGE_ONLY_THRESHOLD = 0.7

# Sample minimums (anti-noise, from A7 audit lesson 2026-05-07)
MIN_BLOCKED_N = 20
MIN_TRADER_SOURCES = 2
MIN_TRADER_DAYS = 3
MIN_SHADOW_CYCLES = 10

# Fase A states
STATE_READY = "READY_FOR_SOURCE_AUDIT"
STATE_WAITING = "WAITING_EVIDENCE"
STATE_RANGE_ONLY = "RANGE_ONLY_NOT_OPERABLE"
STATE_SOURCE_BLOCKED = "SOURCE_BLOCKED"

VALID_STATES = {STATE_READY, STATE_WAITING, STATE_RANGE_ONLY, STATE_SOURCE_BLOCKED}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Source Onboarding Scanner (LOG_ONLY) — City Intelligence v2 Fase A")
    p.add_argument("--signals-crosscheck", default=str(DEFAULT_SIGNALS_CROSSCHECK))
    p.add_argument("--blocked-resolutions", default=str(DEFAULT_BLOCKED_RESOLUTIONS))
    p.add_argument("--shadow-tracking", default=str(DEFAULT_SHADOW_TRACKING))
    p.add_argument("--policy-env", default=str(DEFAULT_POLICY_ENV))
    p.add_argument("--policy-state", default=str(DEFAULT_POLICY_STATE))
    p.add_argument("--overrides", default=str(DEFAULT_OVERRIDES))
    p.add_argument("--traders-report", default=str(DEFAULT_TRADERS_REPORT))
    p.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    p.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return p.parse_args(argv)


def _load_json_optional(path_str, label):
    """Load JSON file. Returns (data, None) on success or (None, error_str) on failure."""
    path = Path(path_str)
    if not path.exists():
        return None, f"{label} not found: {path_str}"
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return json.loads(raw.decode("utf-8")), None
    except Exception as exc:
        return None, f"{label} parse error: {exc}"


def _load_jsonl_optional(path_str, label):
    """Load JSONL file as list of dicts. Returns (rows, None) or (None, error_str)."""
    path = Path(path_str)
    if not path.exists():
        return None, f"{label} not found: {path_str}"
    try:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows, None
    except Exception as exc:
        return None, f"{label} parse error: {exc}"


def _parse_env_list(val):
    if not val:
        return set()
    return {c.strip() for c in str(val).split(",") if c.strip()}


def load_inputs(args):
    """Load all inputs. Returns (inputs_dict, warnings, critical_error or None)."""
    warnings = []
    inputs = {}

    for key, attr, label in [
        ("policy_env", "policy_env", "policy_env_snapshot"),
        ("policy_state", "policy_state", "city_policy_state"),
        ("shadow_tracking", "shadow_tracking", "shadow_city_tracking"),
    ]:
        data, err = _load_json_optional(getattr(args, attr), label)
        if err:
            return None, warnings, f"CRITICAL: {err}"
        inputs[key] = data

    overrides, err = _load_json_optional(args.overrides, "city_lifecycle_overrides")
    if err:
        warnings.append(f"overrides missing, using empty: {err}")
        overrides = {}
    inputs["overrides"] = overrides

    traders_report, err = _load_json_optional(args.traders_report, "traders_operational_questions_report")
    if err:
        warnings.append(f"traders_report optional missing: {err}")
        traders_report = {}
    inputs["traders_report"] = traders_report

    signals_rows, err = _load_jsonl_optional(args.signals_crosscheck, "signals_crosscheck")
    if err:
        warnings.append(f"signals_crosscheck optional missing: {err}")
        signals_rows = []
    inputs["signals_rows"] = signals_rows or []

    blocked_rows, err = _load_jsonl_optional(args.blocked_resolutions, "blocked_signals_resolutions")
    if err:
        warnings.append(f"blocked_resolutions optional missing: {err}")
        blocked_rows = []
    inputs["blocked_rows"] = blocked_rows or []

    return inputs, warnings, None


def _load_resolution_icao():
    """Attempt to import RESOLUTION_ICAO from bot module.

    Returns (dict_or_None, degraded_bool, warning_str_or_None).
    Failure to load the module is NOT a city-level fault — it's a tool-level fault.
    """
    try:
        import importlib.util
        repo_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("bot", repo_root / "bot.py")
        # Use a minimal loader that only reads the module source for the dict,
        # avoiding full execution. We parse it with ast instead.
        import ast
        bot_src = (repo_root / "bot.py").read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(bot_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "RESOLUTION_ICAO":
                        # Evaluate the dict literal — keys are city strings, values are dicts
                        # Values may call _wu_history_url() which we don't need; just extract keys
                        # and icao/noaa_station_id fields.
                        result = {}
                        if isinstance(node.value, ast.Dict):
                            for k, v in zip(node.value.keys, node.value.values):
                                if not isinstance(k, ast.Constant):
                                    continue
                                city = k.value
                                meta = {}
                                if isinstance(v, ast.Dict):
                                    for mk, mv in zip(v.keys, v.values):
                                        if isinstance(mk, ast.Constant) and mk.value in (
                                            "icao", "noaa_station_id", "noaa_daily_station_id"
                                        ):
                                            if isinstance(mv, ast.Constant):
                                                meta[mk.value] = mv.value
                                result[city] = meta
                        return result, False, None
        return None, True, "RESOLUTION_ICAO_UNAVAILABLE: dict not found in bot.py AST"
    except Exception as exc:
        return None, True, f"RESOLUTION_ICAO_UNAVAILABLE: {exc}"


def _load_observed_audit_cities():
    """Read OBSERVED_AUDIT_CITIES via AST without importing bot.py."""
    try:
        bot_src = (REPO_ROOT / "bot.py").read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(bot_src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "OBSERVED_AUDIT_CITIES":
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception as exc:
                        return set(), f"OBSERVED_AUDIT_CITIES_UNAVAILABLE: {exc}"
                    return {str(city) for city in value}, None
        return set(), "OBSERVED_AUDIT_CITIES_UNAVAILABLE: not found in bot.py AST"
    except Exception as exc:
        return set(), f"OBSERVED_AUDIT_CITIES_UNAVAILABLE: {exc}"


def _build_jurisdiction_set(inputs):
    """Build the set of cities already managed by Lifecycle Monitor (excluded from scanner)."""
    policy_env = inputs["policy_env"]
    policy_state = inputs["policy_state"]
    shadow_tracking = inputs["shadow_tracking"]
    overrides = inputs["overrides"]

    variables = policy_env.get("variables", {})
    active_cities = _parse_env_list(variables.get("ACTIVE_TRADING_CITIES"))
    blocked_cities = _parse_env_list(variables.get("BLOCKED_CITIES"))
    canary_cities = _parse_env_list(variables.get("CANARY_TRADING_CITIES"))
    observed_audit_cities = set(inputs.get("observed_audit_cities", set()))
    auto_canary_cities = set(policy_state.get("auto_canary_cities", {}).keys())
    auto_shadow_cities = set(policy_state.get("auto_shadow_cities", {}).keys())
    override_cities = set(overrides.keys())

    shadow_cities_data = shadow_tracking.get("cities", {})
    shadow_mature = {
        city for city, data in shadow_cities_data.items()
        if int(data.get("cycles_seen", 0) or 0) >= MIN_SHADOW_CYCLES
    }

    excluded = (
        active_cities
        | blocked_cities
        | canary_cities
        | observed_audit_cities
        | auto_canary_cities
        | auto_shadow_cities
        | shadow_mature
        | override_cities
    )
    return excluded, {
        "active": sorted(active_cities),
        "blocked": sorted(blocked_cities),
        "canary": sorted(canary_cities),
        "observed_audit": sorted(observed_audit_cities),
        "auto_canary": sorted(auto_canary_cities),
        "auto_shadow": sorted(auto_shadow_cities),
        "shadow_mature": sorted(shadow_mature),
        "overrides": sorted(override_cities),
    }


def _build_trader_stats(signals_rows):
    """Aggregate trader signals per city.

    Returns dict: city -> {sources: set, days: set, range_count: int, total_count: int}
    """
    by_city = defaultdict(lambda: {"sources": set(), "days": set(), "range_count": 0, "total_count": 0})

    def add_signal(city, source=None, day=None, condition=None, count=1, n_traders=None, dates=None, conditions=None):
        if not city:
            return
        bucket = by_city[str(city)]
        if n_traders is not None:
            for idx in range(int(n_traders or 0)):
                bucket["sources"].add(f"source_{idx}")
        elif source:
            bucket["sources"].add(str(source))
        if dates:
            for value in dates:
                if value:
                    bucket["days"].add(str(value))
        elif day:
            bucket["days"].add(str(day))
        cond_values = conditions if conditions is not None else [condition]
        range_count = 0
        for value in cond_values or []:
            text = str(value or "").lower()
            if "range" in text or "between" in text:
                range_count += 1
        bucket["range_count"] += range_count if conditions is not None else (1 if range_count else 0)
        bucket["total_count"] += max(int(count or 0), 1)

    for row in signals_rows:
        city = row.get("city") or row.get("market_city")
        source = row.get("source") or row.get("trader_id") or row.get("trader")
        day = row.get("date") or row.get("day") or row.get("market_date")
        condition = str(row.get("condition", "") or row.get("signal_type", "") or "").lower()
        if city:
            add_signal(city, source=source, day=day, condition=condition)
        for detail_key in ("trader_only_details", "match_details"):
            for detail in row.get(detail_key, []) or []:
                if not isinstance(detail, dict):
                    continue
                add_signal(
                    detail.get("city"),
                    count=detail.get("n_signals", 1),
                    n_traders=detail.get("n_traders"),
                    dates=detail.get("dates"),
                    conditions=detail.get("conditions"),
                )
    return dict(by_city)


def _build_blocked_stats(blocked_rows):
    """Aggregate blocked_signals_resolutions per city.

    Only counts if bot_evaluation is populated (lesson A7 2026-05-07).
    Returns dict: city -> {n: int, n_evaluated: int, wr: float or None}
    """
    by_city = defaultdict(lambda: {"n": 0, "n_evaluated": 0, "wins": 0})
    for row in blocked_rows:
        city = row.get("city") or row.get("market_city")
        if not city:
            continue
        by_city[city]["n"] += 1
        bot_eval = row.get("bot_evaluation")
        has_eval = bot_eval is not None and str(bot_eval).strip()
        has_trader_outcome = row.get("win_for_trader") is not None
        if has_eval or has_trader_outcome:
            by_city[city]["n_evaluated"] += 1
            outcome = str(row.get("outcome", "") or row.get("resolution", "") or "").lower()
            if row.get("win_for_trader") is True or outcome in ("win", "correct", "true", "1"):
                by_city[city]["wins"] += 1

    result = {}
    for city, d in by_city.items():
        wr = d["wins"] / d["n_evaluated"] if d["n_evaluated"] > 0 else None
        result[city] = {"n": d["n"], "n_evaluated": d["n_evaluated"], "wr": wr}
    return result


def _build_trader_report_stats(traders_report):
    by_city = {}
    for row in ((traders_report or {}).get("tables") or {}).get("trader_winning_not_observed", []) or []:
        if not isinstance(row, dict) or not row.get("city"):
            continue
        by_city[str(row["city"])] = {
            "trader_wins": row.get("trader_wins"),
            "trader_n": row.get("trader_n"),
            "trader_wr_pct": row.get("trader_wr_pct"),
            "observed_by_us": bool(row.get("observed_by_us")),
            "source_label": row.get("source_label"),
        }
    return by_city


def _collect_market_identifiers(blocked_rows):
    by_city = defaultdict(lambda: {"slugs": set(), "market_ids": set(), "condition_ids": set()})
    for row in blocked_rows:
        city = row.get("city") or row.get("market_city")
        if not city:
            continue
        for key, target in (("slug", "slugs"), ("market_slug", "slugs"), ("market_id", "market_ids"), ("condition_id", "condition_ids")):
            value = row.get(key)
            if value:
                by_city[str(city)][target].add(str(value))
    return {
        city: {key: sorted(values) for key, values in values_by_key.items()}
        for city, values_by_key in by_city.items()
    }


def score_city(city, trader_stats, blocked_stats, shadow_data, resolution_icao, degraded):
    """Compute priority_score and score component breakdown for a city.

    Returns (score, components_dict, source_feasibility_str).
    """
    components = {
        "trader_consensus_strength": 0.0,
        "blocked_signals_wr_excess": 0.0,
        "shadow_edge_leak": 0.0,
        "trader_only_persistence": 0.0,
        "range_only_fraction": 0.0,
        "source_risk_flag": 0.0,
        "no_local_station": 0.0,
    }

    # Trader consensus / persistence
    t = trader_stats.get(city, {})
    n_sources = len(t.get("sources", set()))
    n_days = len(t.get("days", set()))
    total_signals = t.get("total_count", 0)
    range_count = t.get("range_count", 0)

    if n_sources >= MIN_TRADER_SOURCES and n_days >= MIN_TRADER_DAYS:
        # consensus strength: fraction of sources that agree (use n_sources/max_known as proxy)
        # Simple heuristic: normalize by 5 (typical max sources observed)
        components["trader_consensus_strength"] = min(1.0, n_sources / 5.0)
        # persistence: days observed, normalized, capped 1
        components["trader_only_persistence"] = min(1.0, (n_days - MIN_TRADER_DAYS) / 7.0)

    # Blocked signals WR excess
    b = blocked_stats.get(city, {})
    if b.get("n", 0) >= MIN_BLOCKED_N and b.get("n_evaluated", 0) > 0 and b.get("wr") is not None:
        excess = max(0.0, b["wr"] - 0.55) * 2
        components["blocked_signals_wr_excess"] = min(1.0, excess)

    # Shadow edge leak (shadow data from cities still below MIN_SHADOW_CYCLES)
    if shadow_data:
        cycles_seen = int(shadow_data.get("cycles_seen", 0) or 0)
        if cycles_seen >= MIN_SHADOW_CYCLES:
            # This city shouldn't be here (jurisdiction), but if it is, count leak
            edge_hits = int(shadow_data.get("edge_hits", 0) or 0)
            if edge_hits > 0:
                components["shadow_edge_leak"] = 1.0
        # Note: for cities with cycles < MIN_SHADOW_CYCLES (normal case for onboarding candidates)
        # we still check for any edge signal
        elif cycles_seen > 0:
            edge_hits = int(shadow_data.get("edge_hits", 0) or 0)
            if edge_hits > 0:
                components["shadow_edge_leak"] = min(1.0, edge_hits / 5.0)

    # Range-only penalty
    range_fraction = (range_count / total_signals) if total_signals > 0 else 0.0
    components["range_only_fraction"] = range_fraction

    # Source feasibility via RESOLUTION_ICAO
    source_feasibility = "unknown"
    if not degraded and resolution_icao is not None:
        city_meta = resolution_icao.get(city)
        if city_meta is None:
            # City completely absent from RESOLUTION_ICAO
            components["source_risk_flag"] = 1.0
            source_feasibility = "no_icao"
        else:
            icao = city_meta.get("icao")
            station_id = city_meta.get("noaa_station_id")
            if not icao:
                components["source_risk_flag"] = 1.0
                source_feasibility = "no_icao"
            elif not station_id:
                components["no_local_station"] = 0.5
                source_feasibility = "icao_only"
            else:
                source_feasibility = "icao_and_station"
    elif degraded:
        source_feasibility = "unknown"

    score = (
        1.5 * components["trader_consensus_strength"]
        + 1.0 * components["blocked_signals_wr_excess"]
        + 1.0 * components["shadow_edge_leak"]
        + 0.5 * components["trader_only_persistence"]
        - 0.8 * components["range_only_fraction"]
        - 1.0 * components["source_risk_flag"]
        - 0.5 * components["no_local_station"]
    )

    return score, components, source_feasibility


def classify_state(score, range_fraction, source_feasibility, degraded):
    """Classify city into Fase A state."""
    # SOURCE_BLOCKED only when RESOLUTION_ICAO loaded correctly and city has no ICAO
    if not degraded and source_feasibility == "no_icao":
        return STATE_SOURCE_BLOCKED

    # Range-only check before score threshold
    if range_fraction >= RANGE_ONLY_THRESHOLD:
        return STATE_RANGE_ONLY

    if score >= SCORE_READY:
        return STATE_READY

    if score >= SCORE_WAITING:
        return STATE_WAITING

    return None  # below floor — excluded from review queue


def build_records(inputs, resolution_icao, degraded):
    """Build onboarding candidate records from all inputs.

    Returns (records, warnings, excluded_set).
    """
    warnings = []
    excluded_set, exclusion_breakdown = _build_jurisdiction_set(inputs)

    trader_stats = _build_trader_stats(inputs["signals_rows"])
    blocked_stats = _build_blocked_stats(inputs["blocked_rows"])
    trader_report_stats = _build_trader_report_stats(inputs.get("traders_report"))
    market_identifiers = _collect_market_identifiers(inputs["blocked_rows"])

    shadow_tracking = inputs["shadow_tracking"]
    shadow_cities_data = shadow_tracking.get("cities", {})

    # Candidate universe: cities appearing in any signal source but NOT in excluded_set
    all_signal_cities = set(trader_stats.keys()) | set(blocked_stats.keys()) | set(trader_report_stats.keys())

    records = []
    for city in sorted(all_signal_cities):
        # Jurisdiction check
        if city in excluded_set:
            continue

        # Leak detection: verify the city should not be here
        for set_name, members in exclusion_breakdown.items():
            if city in members:
                warnings.append(f"JURISDICTION_LEAK: {city} in {set_name} but reached scoring")
                break

        shadow_data = shadow_cities_data.get(city)
        score, components, source_feasibility = score_city(
            city, trader_stats, blocked_stats, shadow_data, resolution_icao, degraded
        )

        t = trader_stats.get(city, {})
        b = blocked_stats.get(city, {})
        trader_report = trader_report_stats.get(city, {})
        ids = market_identifiers.get(city, {})
        range_count = t.get("range_count", 0)
        total_signals = t.get("total_count", 0)
        range_fraction = (range_count / total_signals) if total_signals > 0 else 0.0

        state = classify_state(score, range_fraction, source_feasibility, degraded)
        if state is None:
            continue  # below SCORE_WAITING floor

        reason_detected = []
        if city in trader_report_stats:
            reason_detected.append("trader-winning-not-observed")
        if b.get("n", 0):
            reason_detected.append("blocked_signals_resolutions")
        if city in trader_stats:
            reason_detected.append("signals_crosscheck")
        if shadow_data:
            reason_detected.append("shadow_city_tracking")

        record = {
            "city": city,
            "state": state,
            "recommended_state": state,
            "priority_score": round(score, 4),
            "reason_detected": reason_detected,
            "source_feasibility": source_feasibility,
            "internal_mapping_status": source_feasibility,
            "bot_seen": bool(shadow_data),
            "observed_by_us": bool(trader_report.get("observed_by_us", False)),
            "human_review_required": True,
            "operational_action": "NO_ACTION / LOG_ONLY",
            "source_evidence_available": bool(ids.get("slugs") or ids.get("market_ids") or ids.get("condition_ids")),
            "gamma_source_rules_summary": "not_consulted",
            "trader": {
                "n_sources": len(t.get("sources", set())),
                "n_days": len(t.get("days", set())),
                "total_signals": total_signals,
                "range_count": range_count,
                "range_fraction": round(range_fraction, 4),
            },
            "trader_report": {
                "trader_wins": trader_report.get("trader_wins"),
                "trader_n": trader_report.get("trader_n"),
                "trader_wr_pct": trader_report.get("trader_wr_pct"),
            },
            "blocked_signals": {
                "n": b.get("n", 0),
                "n_evaluated": b.get("n_evaluated", 0),
                "wr": round(b["wr"], 4) if b.get("wr") is not None else None,
                "qualifies": b.get("n", 0) >= MIN_BLOCKED_N and b.get("n_evaluated", 0) > 0,
            },
            "shadow": {
                "cycles_seen": int(shadow_data.get("cycles_seen", 0) or 0) if shadow_data else 0,
                "edge_hits": int(shadow_data.get("edge_hits", 0) or 0) if shadow_data else 0,
                "best_edge_pct": shadow_data.get("best_edge_pct") if shadow_data else None,
                "last_seen_at": shadow_data.get("last_seen_at") if shadow_data else None,
            },
            "market_identifiers": {
                "slugs": ids.get("slugs", []),
                "market_ids": ids.get("market_ids", []),
                "condition_ids": ids.get("condition_ids", []),
            },
            "score_components": {k: round(v, 4) for k, v in components.items()},
        }
        records.append(record)

    # Sort by priority_score descending
    records.sort(key=lambda r: -r["priority_score"])
    return records, warnings, exclusion_breakdown


def render_markdown(payload):
    lines = [
        "# Source Onboarding Scanner — City Intelligence v2",
        "",
        f"> **{LOG_ONLY_DISCLAIMER}**",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Candidates in review queue: `{payload['summary']['n_candidates']}`",
        f"- State counts: `{payload['summary']['state_counts']}`",
    ]
    if payload.get("degraded"):
        lines += [
            "",
            "> ⚠ **DEGRADED**: RESOLUTION_ICAO could not be loaded. "
            "Source feasibility is unknown. No city is classified as SOURCE_BLOCKED. "
            "Re-run after resolving bot.py import.",
        ]
    lines += [
        "",
        "## Onboarding Candidates",
        "",
        "| City | Reason | Trader WR | Bot seen | Shadow | Source evidence | Mapping | Recommended state | Human review | Operational action |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in payload["cities"]:
        t = r["trader"]
        b = r["blocked_signals"]
        tr = r.get("trader_report", {})
        trader_wr = "-"
        if tr.get("trader_wr_pct") is not None:
            trader_wr = f"{tr.get('trader_wr_pct')}% ({tr.get('trader_wins')}/{tr.get('trader_n')})"
        elif b["wr"] is not None and b["qualifies"]:
            trader_wr = f"{b['wr']:.0%} ({b['n_evaluated']}/{b['n']})"
        shadow = r.get("shadow", {})
        shadow_text = f"cycles={shadow.get('cycles_seen', 0)} edges={shadow.get('edge_hits', 0)}"
        source_text = "yes" if r.get("source_evidence_available") else "no"
        lines.append(
            f"| {r['city']} | {', '.join(r.get('reason_detected', [])) or '-'}"
            f" | {trader_wr} | {r.get('bot_seen')} | {shadow_text}"
            f" | {source_text}; Gamma={r.get('gamma_source_rules_summary')}"
            f" | {r.get('internal_mapping_status')} | {r.get('recommended_state')}"
            f" | {r.get('human_review_required')} | {r.get('operational_action')} |"
        )

    lines += [
        "",
        "## Jurisdiction Excluded",
        "",
        "Cities skipped because they are already managed by Lifecycle Monitor or policy:",
        "",
    ]
    for group, members in payload.get("exclusion_breakdown", {}).items():
        if members:
            lines.append(f"- **{group}**: {', '.join(members)}")

    lines += [
        "",
        "---",
        "",
        f"*{LOG_ONLY_DISCLAIMER}*",
    ]
    return "\n".join(lines)


def main(argv=None):
    args = parse_args(argv)
    inputs, warnings, critical = load_inputs(args)

    if critical:
        print(f"ERROR: {critical}", file=sys.stderr)
        return 1

    resolution_icao, degraded, ri_warning = _load_resolution_icao()
    if ri_warning:
        warnings.append(ri_warning)
    observed_audit_cities, observed_warning = _load_observed_audit_cities()
    if observed_warning:
        warnings.append(observed_warning)
    inputs["observed_audit_cities"] = observed_audit_cities

    records, build_warnings, exclusion_breakdown = build_records(inputs, resolution_icao, degraded)
    warnings.extend(build_warnings)

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "degraded": degraded,
        "source_feasibility_note": "unknown — RESOLUTION_ICAO unavailable" if degraded else "loaded",
        "inputs": {
            "signals_crosscheck": args.signals_crosscheck,
            "blocked_resolutions": args.blocked_resolutions,
            "shadow_tracking": args.shadow_tracking,
            "policy_env": args.policy_env,
            "policy_state": args.policy_state,
            "overrides": args.overrides,
            "traders_report": args.traders_report,
        },
        "warnings": warnings,
        "summary": {
            "n_candidates": len(records),
            "state_counts": dict(Counter(r["state"] for r in records)),
            "exclusion_counts": {k: len(v) for k, v in exclusion_breakdown.items()},
        },
        "exclusion_breakdown": exclusion_breakdown,
        "cities": records,
    }

    out_json = Path(args.json_output)
    out_md = Path(args.md_output)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(render_markdown(payload), encoding="utf-8")

    for w in warnings:
        print(f"  WARN: {w}")
    if degraded:
        print("  WARN: RESOLUTION_ICAO_UNAVAILABLE — report is degraded, source_feasibility=unknown")
    print(f"Source onboarding report written to {out_json}")
    print(f"Markdown summary written to {out_md}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
