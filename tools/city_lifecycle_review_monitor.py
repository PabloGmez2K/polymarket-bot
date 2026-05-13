#!/usr/bin/env python3
"""City Lifecycle Review Monitor — LOG_ONLY read-only tool.

Classifies cities by lifecycle stage and proposes transitions for human review.
NO BUY/SELL/SKIP. NO BANKROLL. NO Telegram. NO Phase C. NO Railway writes.

Inputs (read-only):
  --policy-env        data/runtime_import/policy_env_snapshot.json
  --policy-state      data/runtime_import/city_policy_state.json
  --shadow-tracking   data/runtime_import/shadow_city_tracking.json
  --overrides         data/city_lifecycle_overrides.json (optional)
  --promotion-gate    data/city_promotion_gate.json (optional)

Outputs:
  --json-output       data/city_lifecycle_review.json
  --md-output         docs/city_lifecycle_review_latest.md
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
DEFAULT_PROMOTION_GATE = REPO_ROOT / "data" / "city_promotion_gate.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "city_lifecycle_review.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "city_lifecycle_review_latest.md"

LOG_ONLY_DISCLAIMER = (
    "LOG_ONLY — This report is observational only. "
    "No BUY, SELL, or SKIP decisions. No BANKROLL changes. No Phase C. "
    "Transitions proposed require explicit human review before any policy change."
)

# T2 gate thresholds (v1)
T2_MIN_EDGE_HITS = 5
T2_MIN_BEST_EDGE_PCT = 20
T2_MIN_CYCLES = 10


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="City Lifecycle Review Monitor (LOG_ONLY)")
    p.add_argument("--overrides", default=str(DEFAULT_OVERRIDES))
    p.add_argument("--policy-env", default=str(DEFAULT_POLICY_ENV))
    p.add_argument("--policy-state", default=str(DEFAULT_POLICY_STATE))
    p.add_argument("--shadow-tracking", default=str(DEFAULT_SHADOW_TRACKING))
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
        text = path.read_bytes()
        # Handle optional UTF-8 BOM
        if text.startswith(b"\xef\xbb\xbf"):
            text = text[3:]
        return json.loads(text.decode("utf-8")), None
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

    return inputs, warnings, None


def _parse_env_list(val):
    if not val:
        return set()
    return {c.strip() for c in str(val).split(",") if c.strip()}


def classify_lifecycle_stage(city, active_cities, blocked_cities, canary_cities,
                              auto_canary_cities, auto_shadow_cities, overrides):
    """Classify city into a lifecycle stage (priority order)."""
    if city in blocked_cities:
        return "blocked_by_source"
    if city in active_cities:
        return "active"
    if city in canary_cities or city in auto_canary_cities:
        return "canary"
    if city in auto_shadow_cities:
        return "shadow"
    if overrides.get(city):
        return "observed_audit"
    return "shadow"


def check_t2_gates(shadow_data):
    """Check T2 gates: shadow/observed_audit → canary candidate.

    Returns (passed, gates_failed_list, details_dict).
    Range condition is excluded — does not trigger canary_review on its own.
    """
    if not shadow_data:
        return False, ["no_shadow_data"], {}

    edge_hits = int(shadow_data.get("edge_hits", 0) or 0)
    best_edge_pct = float(shadow_data.get("best_edge_pct", 0) or 0)
    cycles_seen = int(shadow_data.get("cycles_seen", 0) or 0)

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

    return len(failed) == 0, failed, details


def detect_silent_promotion(city, auto_canary_cities, blocked_cities):
    """Detect if city is in auto_canary AND also in BLOCKED (policy conflict)."""
    if city in auto_canary_cities and city in blocked_cities:
        return True, "city_in_auto_canary_and_blocked"
    return False, None


def propose_transition(city, stage, shadow_data, override,
                       auto_canary_cities, blocked_cities, active_cities,
                       silent_promo, silent_reason):
    """Propose lifecycle transition. Returns (proposed, gates_failed, gate_details, notes)."""
    notes = []

    if silent_promo:
        return "silent_promotion_detected", [], {}, [f"reason: {silent_reason}"]

    if stage == "blocked_by_source":
        return "none", [], {}, ["WATCH: source/proxy data needed for T1 observed_audit_review"]

    if stage in ("observed_audit", "shadow"):
        t2_pass, gates_failed, gate_details = check_t2_gates(shadow_data)
        if not t2_pass:
            return "none", gates_failed, gate_details, ["T2 gates not satisfied"]

        if override.get("manual_review_required_pre_canary"):
            reason = override.get("reason", "override")
            notes.append(f"manual_review_required_pre_canary=true ({reason})")
            notes.append("OBSERVED_AUDIT does not authorize trading")
            return "manual_review_pending", [], gate_details, notes

        return "canary_review", [], gate_details, notes

    if stage == "canary":
        if city in active_cities:
            return "none", [], {}, ["already active"]
        t2_pass, gates_failed, gate_details = check_t2_gates(shadow_data)
        if t2_pass:
            return "active_review", [], gate_details, ["T3: canary with sufficient evidence"]
        return "none", gates_failed, gate_details, ["T3: insufficient evidence for active_review"]

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
    auto_canary_cities = set(policy_state.get("auto_canary_cities", {}).keys())
    auto_shadow_cities = set(policy_state.get("auto_shadow_cities", {}).keys())
    shadow_cities_data = shadow_tracking.get("cities", {})

    all_cities = set()
    all_cities.update(active_cities)
    all_cities.update(blocked_cities)
    all_cities.update(canary_cities)
    all_cities.update(auto_canary_cities)
    all_cities.update(auto_shadow_cities)
    all_cities.update(shadow_cities_data.keys())
    all_cities.update(overrides.keys())

    records = []
    for city in sorted(all_cities):
        shadow_data = shadow_cities_data.get(city)
        override = overrides.get(city, {})

        stage = classify_lifecycle_stage(
            city, active_cities, blocked_cities, canary_cities,
            auto_canary_cities, auto_shadow_cities, overrides,
        )

        silent_promo, silent_reason = detect_silent_promotion(
            city, auto_canary_cities, blocked_cities,
        )

        transition, gates_failed, gate_details, notes = propose_transition(
            city, stage, shadow_data, override,
            auto_canary_cities, blocked_cities, active_cities,
            silent_promo, silent_reason,
        )

        records.append({
            "city": city,
            "lifecycle_stage": stage,
            "transition_proposed": transition,
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
        "## Manual Review Queue",
        "",
        "Cities requiring human action:",
        "",
    ]
    action_transitions = {
        "manual_review_pending", "canary_review", "active_review",
        "observed_audit_review", "silent_promotion_detected", "regression_detected",
    }
    queue = [r for r in payload["cities"] if r["transition_proposed"] in action_transitions]
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
