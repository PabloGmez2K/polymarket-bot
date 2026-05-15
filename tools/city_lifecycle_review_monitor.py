#!/usr/bin/env python3
"""City Lifecycle Review Monitor — LOG_ONLY read-only tool.

Classifies cities by lifecycle stage and proposes transitions for human review.
NO BUY/SELL/SKIP. NO BANKROLL. NO Telegram. NO Phase C. NO Railway writes.

Inputs (read-only):
  --policy-env        data/runtime_import/policy_env_snapshot.json
  --policy-state      data/runtime_import/city_policy_state.json
  --shadow-tracking   data/runtime_import/shadow_city_tracking.json
  --trade-lifecycle   data/runtime_import/trade_lifecycle.json (optional)
  --overrides         data/city_lifecycle_overrides.json (optional)
  --promotion-gate    data/city_promotion_gate.json (optional)

Outputs:
  --json-output       data/city_lifecycle_review.json
  --md-output         docs/city_lifecycle_review_latest.md

Transition hierarchy (weakest to strongest):
  none < preliminary_review_candidate < canary_review / active_review
                                      < manual_review_pending (override path)
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OVERRIDES = REPO_ROOT / "data" / "city_lifecycle_overrides.json"
DEFAULT_POLICY_ENV = REPO_ROOT / "data" / "runtime_import" / "policy_env_snapshot.json"
DEFAULT_POLICY_STATE = REPO_ROOT / "data" / "runtime_import" / "city_policy_state.json"
DEFAULT_SHADOW_TRACKING = REPO_ROOT / "data" / "runtime_import" / "shadow_city_tracking.json"
DEFAULT_TRADE_LIFECYCLE = REPO_ROOT / "data" / "runtime_import" / "trade_lifecycle.json"
DEFAULT_PROMOTION_GATE = REPO_ROOT / "data" / "city_promotion_gate.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_lifecycle_review.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_lifecycle_review_latest.md"

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY — This report is observational only. "
    "No BUY, SELL, or SKIP decisions. No BANKROLL changes. No Phase C. "
    "Transitions proposed require explicit human review before any policy change."
)

# T2 gate thresholds v1.1 (shadow/observed_audit → canary candidate)
T2_MIN_EDGE_HITS = 5
T2_MIN_BEST_EDGE_PCT = 20
T2_MIN_CYCLES = 10

# T3 gate thresholds (canary → active candidate)
# Uses auto_canary entry metrics at promotion time, not shadow_tracking stats.
T3_MIN_SHADOW_EDGES_AT_PROMOTION = 5
T3_MIN_BEST_EDGE_PCT_AT_PROMOTION = 30
T3_MIN_CANARY_CLOSED_TRADES = 5
T3_MIN_CANARY_WR = 60.0
T3_MIN_CANARY_PNL = 0.0

REPORTING_DRIFT_BLOCKED_EFFECTIVE = "reporting_drift_blocked_effective"

# Promotion-gate gate_status values that confirm an active canary (T3 path).
_T3_CONFIRM_STATUSES = {"observe_runtime_canary"}

# Promotion-gate statuses that block canary_review even if T2 stats pass (T2 path).
_T2_BLOCKING_STATUSES = {
    "background_watch",
    "needs_shadow_validation",
    "watch_closely",
    "observe_with_source_caution",
    "audit_trader_input",
}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="City Lifecycle Review Monitor (LOG_ONLY)")
    p.add_argument("--overrides", default=str(DEFAULT_OVERRIDES))
    p.add_argument("--policy-env", default=str(DEFAULT_POLICY_ENV))
    p.add_argument("--policy-state", default=str(DEFAULT_POLICY_STATE))
    p.add_argument("--shadow-tracking", default=str(DEFAULT_SHADOW_TRACKING))
    p.add_argument("--trade-lifecycle", default=str(DEFAULT_TRADE_LIFECYCLE))
    p.add_argument("--promotion-gate", default=str(DEFAULT_PROMOTION_GATE))
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
        if raw.startswith(b"\xef\xbb\xbf"):   # strip optional UTF-8 BOM
            raw = raw[3:]
        return json.loads(raw.decode("utf-8")), None
    except Exception as exc:
        return None, f"{label} parse error: {exc}"


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

    promo_gate, err = _load_json_optional(args.promotion_gate, "city_promotion_gate")
    if err:
        warnings.append(f"promotion_gate optional missing: {err}")
        promo_gate = None
    inputs["promotion_gate"] = promo_gate

    trade_lifecycle, err = _load_json_optional(args.trade_lifecycle, "trade_lifecycle")
    if err:
        warnings.append(f"trade_lifecycle optional missing: {err}")
        trade_lifecycle = None
    inputs["trade_lifecycle"] = trade_lifecycle

    return inputs, warnings, None


def _city_key(city):
    return str(city or "").strip().lower()


def _merge_city_mapping(mapping):
    """Return normalized key maps for city-keyed dictionaries."""
    names = {}
    values = {}
    if not isinstance(mapping, dict):
        return names, values
    for city in sorted(mapping):
        key = _city_key(city)
        if not key:
            continue
        names.setdefault(key, str(city).strip())
        values.setdefault(key, mapping[city])
    return names, values


def _contains_city(collection, key):
    if isinstance(collection, dict):
        return key in collection or any(_city_key(city) == key for city in collection)
    return any(_city_key(city) == key for city in (collection or []))


def _parse_env_list(val):
    if not val:
        return {}
    result = {}
    for part in str(val).split(","):
        city = part.strip()
        key = _city_key(city)
        if key:
            result.setdefault(key, city)
    return result


def _has_non_range_edge(recent_edges):
    """Return True if at least one recent edge has edge_hit=True and is not a range condition.

    Range condition: question contains "between" (e.g. "between 44-45°F").
    Cities whose only operable signals are range conditions are excluded — range is
    not tradeable under current Phase 2 policy.
    """
    for edge in recent_edges or []:
        if edge.get("edge_hit") and "between" not in edge.get("question", "").lower():
            return True
    return False


def classify_lifecycle_stage(city, active_cities, blocked_cities, canary_cities,
                              auto_canary_cities, auto_shadow_cities, overrides):
    """Classify city into a lifecycle stage (priority order)."""
    key = _city_key(city)
    if _contains_city(blocked_cities, key):
        return "blocked_by_source"
    if _contains_city(active_cities, key):
        return "active"
    if _contains_city(canary_cities, key) or _contains_city(auto_canary_cities, key):
        return "canary"
    if _contains_city(auto_shadow_cities, key):
        return "shadow"
    if _contains_city(overrides, key):
        return "observed_audit"
    return "shadow"


def effective_policy_status(city, active_cities, blocked_cities, canary_cities,
                            auto_canary_cities, auto_shadow_cities):
    """Resolve effective policy with blocked winning over stale overlays."""
    key = _city_key(city)
    if _contains_city(blocked_cities, key):
        return "blocked", "BLOCKED_CITIES"
    if _contains_city(auto_shadow_cities, key):
        return "shadow", "city_policy_state.auto_shadow_cities"
    if _contains_city(active_cities, key):
        return "active", "ACTIVE_TRADING_CITIES"
    if _contains_city(auto_canary_cities, key):
        return "canary", "city_policy_state.auto_canary_cities"
    if _contains_city(canary_cities, key):
        return "canary", "CANARY_TRADING_CITIES"
    return "shadow", "default_shadow"


def check_t2_gates(shadow_data):
    """Check T2 gates: shadow/observed_audit → canary candidate.

    Gate 1-3: cumulative shadow statistics.
    Gate 4: at least one recent edge_hit=True with a non-range condition.
             Range-only cities are excluded — they are not operable under Phase 2.

    Returns (passed, gates_failed_list, details_dict).
    """
    if not shadow_data:
        return False, ["no_shadow_data"], {}

    edge_hits = int(shadow_data.get("edge_hits", 0) or 0)
    best_edge_pct = float(shadow_data.get("best_edge_pct", 0) or 0)
    cycles_seen = int(shadow_data.get("cycles_seen", 0) or 0)
    recent_edges = shadow_data.get("recent_edges") or []

    details = {
        "edge_hits": edge_hits,
        "best_edge_pct": best_edge_pct,
        "cycles_seen": cycles_seen,
        "t2_min_edge_hits": T2_MIN_EDGE_HITS,
        "t2_min_best_edge_pct": T2_MIN_BEST_EDGE_PCT,
        "t2_min_cycles": T2_MIN_CYCLES,
    }

    failed = []
    if edge_hits < T2_MIN_EDGE_HITS:
        failed.append(f"edge_hits<{T2_MIN_EDGE_HITS}(got {edge_hits})")
    if best_edge_pct < T2_MIN_BEST_EDGE_PCT:
        failed.append(f"best_edge_pct<{T2_MIN_BEST_EDGE_PCT}(got {best_edge_pct})")
    if cycles_seen < T2_MIN_CYCLES:
        failed.append(f"cycles_seen<{T2_MIN_CYCLES}(got {cycles_seen})")

    if not _has_non_range_edge(recent_edges):
        if recent_edges:
            failed.append("no_non_range_edge_hit(range_only_or_all_filtered)")
        else:
            failed.append("no_recent_edges_to_verify_condition")

    return len(failed) == 0, failed, details


def check_t3_gates(auto_canary_entry, promo_gate_row, has_promotion_gate,
                   canary_metrics=None):
    """Check T3 gates: canary → active_review candidate.

    Uses auto_canary entry metrics (shadow_edges, best_edge_pct at promotion time),
    NOT shadow_tracking stats. Also requires promotion_gate confirmation.

    Returns (proposed_transition, gates_failed, details, notes).
    """
    if not auto_canary_entry:
        return "none", ["no_auto_canary_entry"], {}, [
            "T3: city not in auto_canary — no promotion evidence"
        ]

    shadow_edges = int(auto_canary_entry.get("shadow_edges", 0) or 0)
    best_edge_pct = float(auto_canary_entry.get("best_edge_pct", 0) or 0)

    details = {
        "shadow_edges_at_promotion": shadow_edges,
        "best_edge_pct_at_promotion": best_edge_pct,
        "t3_min_shadow_edges": T3_MIN_SHADOW_EDGES_AT_PROMOTION,
        "t3_min_best_edge_pct": T3_MIN_BEST_EDGE_PCT_AT_PROMOTION,
    }

    failed = []
    if shadow_edges < T3_MIN_SHADOW_EDGES_AT_PROMOTION:
        failed.append(
            f"shadow_edges_at_promotion<{T3_MIN_SHADOW_EDGES_AT_PROMOTION}(got {shadow_edges})"
        )
    if best_edge_pct < T3_MIN_BEST_EDGE_PCT_AT_PROMOTION:
        failed.append(
            f"best_edge_pct_at_promotion<{T3_MIN_BEST_EDGE_PCT_AT_PROMOTION}(got {best_edge_pct})"
        )

    if failed:
        return "none", failed, details, ["T3: promotion metrics below threshold"]

    if not has_promotion_gate:
        return "preliminary_review_candidate", [], details, [
            "T3: promotion metrics pass but promotion_gate unavailable — insufficient for active_review"
        ]

    if promo_gate_row is None:
        return "preliminary_review_candidate", ["city_not_in_promotion_gate"], details, [
            "T3: promotion metrics pass but city absent from promotion_gate"
        ]

    gate_status = promo_gate_row.get("gate_status", "")
    if gate_status in _T3_CONFIRM_STATUSES:
        metrics = canary_metrics or {}
        closed = int(metrics.get("closed", 0) or 0)
        wr = metrics.get("wr_closed")
        pnl = float(metrics.get("realized_pnl", 0.0) or 0.0)
        details = {
            **details,
            "promotion_gate_status": gate_status,
            "canary_closed_trades": closed,
            "canary_wr_closed": wr,
            "canary_realized_pnl": round(pnl, 2),
            "t3_min_canary_closed_trades": T3_MIN_CANARY_CLOSED_TRADES,
            "t3_min_canary_wr": T3_MIN_CANARY_WR,
            "t3_min_canary_pnl": T3_MIN_CANARY_PNL,
        }
        failed = []
        if closed < T3_MIN_CANARY_CLOSED_TRADES:
            failed.append(f"canary_closed_trades<{T3_MIN_CANARY_CLOSED_TRADES}(got {closed})")
        if wr is None:
            failed.append("canary_wr_unavailable")
        elif float(wr) < T3_MIN_CANARY_WR:
            failed.append(f"canary_wr<{T3_MIN_CANARY_WR}(got {wr})")
        if pnl < T3_MIN_CANARY_PNL:
            failed.append(f"canary_pnl<{T3_MIN_CANARY_PNL}(got {round(pnl, 2)})")
        if failed:
            return "canary_watch", failed, details, [
                "Canary watch, not active-ready: runtime canary exists but closed-trade evidence is below T3 minimum",
                "NO_ACTION / LOG_ONLY. Do not promote.",
            ]
        return "active_review", [], details, [
            f"T3: active review candidate confirmed, promotion_gate={gate_status}",
            "LOG_ONLY review only; does not authorize active promotion",
        ]

    return "preliminary_review_candidate", [f"promotion_gate={gate_status}"], {
        **details, "promotion_gate_status": gate_status
    }, [f"T3: metrics pass but promotion_gate='{gate_status}' — insufficient for active_review"]


def detect_silent_promotion(city, auto_canary_cities, blocked_cities):
    """Detect if city is in auto_canary AND also in BLOCKED (policy conflict)."""
    key = _city_key(city)
    if key in auto_canary_cities and key in blocked_cities:
        return True, "city_in_auto_canary_and_blocked"
    return False, None


def build_canary_trade_metrics(trade_lifecycle, auto_canary_by_key):
    """Summarize canary-era closed trade evidence per normalized city key."""
    records = []
    if isinstance(trade_lifecycle, dict):
        records = trade_lifecycle.get("records", []) or []
    if not isinstance(records, list):
        return {}

    metrics = {}
    for key, entry in auto_canary_by_key.items():
        promoted_at = ""
        if isinstance(entry, dict):
            promoted_at = str(entry.get("promoted_at") or "")
        rows = []
        for record in records:
            if not isinstance(record, dict) or _city_key(record.get("city")) != key:
                continue
            opened_at = str(record.get("opened_at") or "")
            if promoted_at and opened_at < promoted_at:
                continue
            rows.append(record)

        closed_rows = [r for r in rows if str(r.get("status") or "") != "open"]
        wins = []
        pnl = 0.0
        for record in closed_rows:
            close_context = record.get("close_context") or {}
            try:
                pnl_cash = float(close_context.get("pnl_cash") or 0.0)
            except (TypeError, ValueError):
                pnl_cash = 0.0
            pnl += pnl_cash
            status = str(record.get("status") or "").lower()
            if "win" in status or pnl_cash > 0:
                wins.append(record)

        metrics[key] = {
            "n_canary_records": len(rows),
            "closed": len(closed_rows),
            "wins": len(wins),
            "wr_closed": round(100.0 * len(wins) / len(closed_rows), 1) if closed_rows else None,
            "realized_pnl": round(pnl, 2),
            "open": len([r for r in rows if str(r.get("status") or "") == "open"]),
        }
    return metrics


def propose_transition(city, stage, shadow_data, override,
                       auto_canary_cities, blocked_cities, active_cities,
                       silent_promo, silent_reason,
                       auto_canary_entry=None,
                       promo_gate_row=None, has_promotion_gate=False,
                       canary_metrics=None):
    """Propose lifecycle transition. Returns (proposed, gates_failed, gate_details, notes)."""
    if silent_promo:
        return REPORTING_DRIFT_BLOCKED_EFFECTIVE, [], {
            "operational_action": "NO_ACTION_LOG_ONLY",
        }, [
            f"reason: {silent_reason}",
            "Blocked effective - no action, reporting drift",
            "NO_ACTION / LOG_ONLY. Do not promote.",
        ]

    if stage == "blocked_by_source":
        return "none", [], {}, ["WATCH: source/proxy data needed for T1 observed_audit_review"]

    if stage in ("observed_audit", "shadow"):
        # T2: shadow/observed_audit → canary candidate
        t2_pass, gates_failed, gate_details = check_t2_gates(shadow_data)
        if not t2_pass:
            return "none", gates_failed, gate_details, ["T2 gates not satisfied"]

        # Override takes priority — checked before promotion_gate requirement
        if override.get("manual_review_required_pre_canary"):
            reason = override.get("reason", "override")
            return "manual_review_pending", [], gate_details, [
                f"manual_review_required_pre_canary=true ({reason})",
                "OBSERVED_AUDIT does not authorize trading",
            ]

        # Beyond shadow stats, promotion_gate evidence is required
        if not has_promotion_gate:
            return "preliminary_review_candidate", [], gate_details, [
                "T2 gates pass but promotion_gate unavailable — insufficient for canary_review"
            ]

        if promo_gate_row is None:
            return "preliminary_review_candidate", ["city_not_in_promotion_gate"], gate_details, [
                "T2 gates pass but city absent from promotion_gate"
            ]

        gate_status = promo_gate_row.get("gate_status", "")
        if gate_status in _T2_BLOCKING_STATUSES:
            return "preliminary_review_candidate", [f"promotion_gate={gate_status}"], gate_details, [
                f"T2 stats pass but promotion_gate='{gate_status}' — insufficient for canary_review"
            ]

        return "canary_review", [], {**gate_details, "promotion_gate_status": gate_status}, [
            f"T2 gates pass, promotion_gate={gate_status}"
        ]

    if stage == "canary":
        if _city_key(city) in active_cities:
            return "none", [], {}, ["already active"]
        # T3: canary → active candidate (independent from T2 shadow stats)
        return check_t3_gates(
            auto_canary_entry,
            promo_gate_row,
            has_promotion_gate,
            canary_metrics=canary_metrics,
        )

    if stage == "active":
        return "none", [], {}, ["already active — no transition needed"]

    return "none", [], {}, []


def build_city_records(inputs):
    """Build all city records from the loaded inputs dict."""
    policy_env = inputs["policy_env"]
    policy_state = inputs["policy_state"]
    shadow_tracking = inputs["shadow_tracking"]
    overrides = inputs["overrides"]

    variables = policy_env.get("variables", {})
    active_cities = _parse_env_list(variables.get("ACTIVE_TRADING_CITIES"))
    blocked_cities = _parse_env_list(variables.get("BLOCKED_CITIES"))
    canary_cities = _parse_env_list(variables.get("CANARY_TRADING_CITIES"))
    auto_canary_dict = policy_state.get("auto_canary_cities", {})
    auto_canary_names, auto_canary_by_key = _merge_city_mapping(auto_canary_dict)
    auto_canary_cities = set(auto_canary_by_key)
    auto_shadow_names, auto_shadow_by_key = _merge_city_mapping(policy_state.get("auto_shadow_cities", {}))
    auto_shadow_cities = set(auto_shadow_by_key)
    shadow_names, shadow_cities_data = _merge_city_mapping(shadow_tracking.get("cities", {}))
    override_names, overrides_by_key = _merge_city_mapping(overrides)
    canary_trade_metrics = build_canary_trade_metrics(
        inputs.get("trade_lifecycle"), auto_canary_by_key
    )

    # Build promotion gate index (only when runtime inputs are available)
    promo_gate_data = inputs.get("promotion_gate")
    has_promotion_gate = False
    promo_gate_by_city = {}
    if promo_gate_data:
        pg_summary = promo_gate_data.get("summary", {})
        if pg_summary.get("runtime_inputs_status", "missing") == "available":
            has_promotion_gate = True
            for row in promo_gate_data.get("cities", []):
                city_name = row.get("city")
                if city_name:
                    promo_gate_by_city[_city_key(city_name)] = row

    all_cities = set()
    all_cities.update(active_cities.keys())
    all_cities.update(blocked_cities.keys())
    all_cities.update(canary_cities.keys())
    all_cities.update(auto_canary_cities)
    all_cities.update(auto_shadow_cities)
    all_cities.update(shadow_cities_data.keys())
    all_cities.update(overrides_by_key.keys())

    records = []
    for key in sorted(all_cities):
        city = (
            active_cities.get(key) or blocked_cities.get(key) or canary_cities.get(key)
            or auto_canary_names.get(key) or auto_shadow_names.get(key)
            or shadow_names.get(key) or override_names.get(key) or key
        )
        shadow_data = shadow_cities_data.get(key)
        override = overrides_by_key.get(key, {})
        auto_canary_entry = auto_canary_by_key.get(key)

        stage = classify_lifecycle_stage(
            city, active_cities, blocked_cities, canary_cities,
            auto_canary_cities, auto_shadow_cities, overrides_by_key,
        )
        effective_status, effective_source = effective_policy_status(
            city, active_cities, blocked_cities, canary_cities,
            auto_canary_cities, auto_shadow_cities,
        )

        silent_promo, silent_reason = detect_silent_promotion(
            city, auto_canary_cities, blocked_cities,
        )

        promo_gate_row = promo_gate_by_city.get(key) if has_promotion_gate else None

        transition, gates_failed, gate_details, notes = propose_transition(
            city, stage, shadow_data, override,
            auto_canary_cities, blocked_cities, active_cities,
            silent_promo, silent_reason,
            auto_canary_entry=auto_canary_entry,
            promo_gate_row=promo_gate_row,
            has_promotion_gate=has_promotion_gate,
            canary_metrics=canary_trade_metrics.get(key),
        )

        records.append({
            "city": city,
            "lifecycle_stage": stage,
            "effective_policy_status": effective_status,
            "effective_policy_source": effective_source,
            "transition_proposed": transition,
            "operational_action": "NO_ACTION_LOG_ONLY",
            "override": override or None,
            "gates_failed": gates_failed,
            "gate_details": gate_details,
            "notes": notes,
        })

    return records


def render_markdown(payload):
    lines = [
        "# City Lifecycle Review Monitor",
        "",
        f"> **{LOG_ONLY_DISCLAIMER}**",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Cities reviewed: `{payload['summary']['n_cities']}`",
        f"- Transitions: `{payload['summary']['transition_counts']}`",
        "",
        "## City Review",
        "",
        "| City | Stage | Transition | Override | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in payload["cities"]:
        override_flag = "yes" if r.get("override") else "-"
        notes_str = "; ".join(r.get("notes", [])) or "-"
        lines.append(
            f"| {r['city']} | {r['lifecycle_stage']} | {r['transition_proposed']}"
            f" | {override_flag} | {notes_str} |"
        )
    lines += [
        "",
        "## Review Queue",
        "",
        "Cities requiring human attention (strongest signal first):",
        "",
    ]
    action_transitions = {
        "manual_review_pending", "canary_review", "active_review",
        "observed_audit_review", "preliminary_review_candidate",
        "canary_watch", REPORTING_DRIFT_BLOCKED_EFFECTIVE,
        "silent_promotion_detected", "regression_detected",
    }
    priority_order = [
        REPORTING_DRIFT_BLOCKED_EFFECTIVE, "silent_promotion_detected",
        "manual_review_pending", "active_review", "canary_review",
        "canary_watch",
        "preliminary_review_candidate", "observed_audit_review",
    ]
    queue = [r for r in payload["cities"] if r["transition_proposed"] in action_transitions]
    queue.sort(key=lambda r: (
        priority_order.index(r["transition_proposed"])
        if r["transition_proposed"] in priority_order else 99,
        r["city"],
    ))
    if queue:
        for r in queue:
            notes_str = "; ".join(r["notes"]) if r["notes"] else r["transition_proposed"]
            lines.append(f"- **{r['city']}** (`{r['transition_proposed']}`): {notes_str}")
    else:
        lines.append("- None at this time.")
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

    records = build_city_records(inputs)

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "log_only": True,
        "disclaimer": LOG_ONLY_DISCLAIMER,
        "inputs": {
            "policy_env": args.policy_env,
            "policy_state": args.policy_state,
            "shadow_tracking": args.shadow_tracking,
            "trade_lifecycle": args.trade_lifecycle,
            "overrides": args.overrides,
        },
        "warnings": warnings,
        "summary": {
            "n_cities": len(records),
            "stage_counts": dict(Counter(r["lifecycle_stage"] for r in records)),
            "transition_counts": dict(Counter(r["transition_proposed"] for r in records)),
        },
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
    print(f"City lifecycle review written to {out_json}")
    print(f"Markdown summary written to {out_md}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
