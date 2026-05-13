#!/usr/bin/env python3
"""Generate a read-only effective runtime policy view for cities."""

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_POLICY_STATE = REPO_ROOT / "data" / "runtime_import" / "city_policy_state.json"
DEFAULT_RUNTIME_MANIFEST = REPO_ROOT / "data" / "runtime_import" / "runtime_import_manifest.json"
DEFAULT_POLICY_ENV_SNAPSHOT = REPO_ROOT / "data" / "runtime_import" / "policy_env_snapshot.json"
DEFAULT_CROSS = REPO_ROOT / "data" / "reference_trader_city_market_cross.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "data" / "runtime_policy_effective_view.json"
DEFAULT_MD_OUTPUT = REPO_ROOT / "docs" / "runtime_policy_effective_view_latest.md"

RUNTIME_TO_EFFECTIVE = {
    "auto_blocked": "blocked",
    "auto_shadow": "shadow",
    "auto_canary": "canary",
}

# Keep env-list fallbacks empty unless the caller passes an explicit snapshot.
# This avoids turning a stale audited claim into a blocking declarative truth
# when the effective runtime policy already resolves the city differently.
DEFAULT_ACTIVE_CITIES = ""
DEFAULT_CANARY_CITIES = ""
DEFAULT_BLOCKED_CITIES = ""


def classify_collision(env_mode, runtime_mode, cross_mode, effective_mode, drift_flags):
    runtime_effective = RUNTIME_TO_EFFECTIVE.get(runtime_mode)

    if "env_runtime_collision" in drift_flags:
        if env_mode == "blocked" and effective_mode == "blocked":
            return "documented_drift"
        if env_mode in {"active", "canary"} and runtime_effective in {"active", "canary"} and effective_mode in {"active", "canary"}:
            return "documented_drift"
        return "blocking_operational_collision"

    if env_mode == "blocked" and effective_mode == "blocked" and cross_mode in {"active", "canary"}:
        return "documented_drift"

    if cross_mode in {"active", "canary"} and effective_mode in {"shadow", "blocked"}:
        return "blocking_operational_collision"

    if runtime_effective in {"canary", "active"} and cross_mode in {"shadow", "unknown", "untracked"}:
        return "documented_drift"

    if effective_mode == "shadow" and cross_mode == "untracked":
        return "collision_noise"

    if drift_flags:
        return "documented_drift"

    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a canonical read-only view of effective city policy."
    )
    parser.add_argument("--city-policy-state", default=str(DEFAULT_POLICY_STATE))
    parser.add_argument("--runtime-manifest", default=str(DEFAULT_RUNTIME_MANIFEST))
    parser.add_argument("--policy-env-snapshot", default=str(DEFAULT_POLICY_ENV_SNAPSHOT))
    parser.add_argument("--cross", default=str(DEFAULT_CROSS))
    parser.add_argument("--active-cities", default=None)
    parser.add_argument("--canary-cities", default=None)
    parser.add_argument("--blocked-cities", default=None)
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def load_json(path, required=True):
    item = Path(path)
    if not item.exists():
        if required:
            raise FileNotFoundError(f"Missing required input: {item}")
        return {}
    return json.loads(item.read_text(encoding="utf-8-sig"))


def split_city_list(value):
    if not value:
        return []
    cities = []
    for part in str(value).split(","):
        city = part.strip()
        if city and city.upper() != "NONE":
            cities.append(city)
    return sorted(dict.fromkeys(cities))


def normalize_city(city):
    return str(city).strip().lower()


def city_map(cities):
    return {normalize_city(city): city for city in cities if str(city).strip()}


def build_runtime_lookup(policy_state):
    lookup = {}
    sections = [
        ("auto_blocked_cities", "auto_blocked"),
        ("auto_shadow_cities", "auto_shadow"),
        ("auto_canary_cities", "auto_canary"),
    ]
    for section_name, runtime_mode in sections:
        section = policy_state.get(section_name, {})
        if not isinstance(section, dict):
            continue
        for city, details in section.items():
            key = normalize_city(city)
            if not key:
                continue
            entry = lookup.setdefault(key, {
                "city": str(city).strip(),
                "modes": [],
                "details": {},
            })
            entry["modes"].append({
                "runtime_policy_mode": runtime_mode,
                "source": section_name,
                "details": details if isinstance(details, dict) else {},
            })
            entry["details"][runtime_mode] = details if isinstance(details, dict) else {}
    return lookup


def runtime_mode_for(entry):
    if not entry:
        return "runtime_unknown", None, []
    priority = ["auto_blocked", "auto_shadow", "auto_canary"]
    modes = entry.get("modes", [])
    mode_names = [item["runtime_policy_mode"] for item in modes]
    for mode in priority:
        if mode in mode_names:
            source = next(item["source"] for item in modes if item["runtime_policy_mode"] == mode)
            return mode, source, modes
    return "runtime_unknown", None, modes


def env_declared_mode(key, active, canary, blocked):
    if key in blocked:
        return "blocked", "BLOCKED_CITIES"
    if key in active:
        return "active", "ACTIVE_TRADING_CITIES"
    if key in canary:
        return "canary", "CANARY_TRADING_CITIES"
    return "shadow", "default_shadow"


def effective_policy(env_mode, runtime_mode):
    if env_mode == "blocked":
        return "blocked", "BLOCKED_CITIES"
    if runtime_mode == "auto_blocked":
        return "blocked", "city_policy_state.auto_blocked_cities"
    if runtime_mode == "auto_shadow":
        return "shadow", "city_policy_state.auto_shadow_cities"
    if env_mode == "active":
        return "active", "ACTIVE_TRADING_CITIES"
    if runtime_mode == "auto_canary":
        return "canary", "city_policy_state.auto_canary_cities"
    if env_mode == "canary":
        return "canary", "CANARY_TRADING_CITIES"
    return "shadow", "default_shadow"


def load_cross_modes(path):
    payload = load_json(path, required=False)
    rows = payload.get("city_rows", []) if isinstance(payload, dict) else []
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("city"):
            continue
        result[normalize_city(row["city"])] = row.get("policy_mode", "unknown")
    return result


def load_policy_env_snapshot(path):
    payload = load_json(path, required=False)
    if not isinstance(payload, dict):
        return {}
    variables = payload.get("variables", {})
    return variables if isinstance(variables, dict) else {}


def resolve_env_list(cli_value, env_name, snapshot_vars, default_value):
    if cli_value is not None:
        return cli_value
    env_value = os.getenv(env_name)
    if env_value is not None:
        return env_value
    snapshot_value = snapshot_vars.get(env_name)
    if snapshot_value is not None:
        return snapshot_value
    return default_value


def build_rows(args):
    policy_state = load_json(args.city_policy_state)
    manifest = load_json(args.runtime_manifest, required=False)
    policy_env_snapshot = load_policy_env_snapshot(args.policy_env_snapshot)
    active = city_map(split_city_list(resolve_env_list(
        cli_value=args.active_cities,
        env_name="ACTIVE_TRADING_CITIES",
        snapshot_vars=policy_env_snapshot,
        default_value=DEFAULT_ACTIVE_CITIES,
    )))
    canary = city_map(split_city_list(resolve_env_list(
        cli_value=args.canary_cities,
        env_name="CANARY_TRADING_CITIES",
        snapshot_vars=policy_env_snapshot,
        default_value=DEFAULT_CANARY_CITIES,
    )))
    blocked = city_map(split_city_list(resolve_env_list(
        cli_value=args.blocked_cities,
        env_name="BLOCKED_CITIES",
        snapshot_vars=policy_env_snapshot,
        default_value=DEFAULT_BLOCKED_CITIES,
    )))
    runtime = build_runtime_lookup(policy_state)
    cross = load_cross_modes(args.cross)

    keys = set(active) | set(canary) | set(blocked) | set(runtime) | set(cross)
    rows = []
    for key in sorted(keys, key=lambda item: (runtime.get(item, {}).get("city") or active.get(item) or canary.get(item) or blocked.get(item) or item).lower()):
        city = runtime.get(key, {}).get("city") or active.get(key) or canary.get(key) or blocked.get(key) or key
        env_mode, env_source = env_declared_mode(key, active, canary, blocked)
        runtime_mode, runtime_source, runtime_modes = runtime_mode_for(runtime.get(key))
        effective_mode, source_of_truth = effective_policy(env_mode, runtime_mode)
        cross_mode = cross.get(key, "unknown")
        runtime_effective = RUNTIME_TO_EFFECTIVE.get(runtime_mode)

        drift_flags = []
        if len(runtime_modes) > 1:
            drift_flags.append("runtime_policy_collision")
        if runtime_effective and env_mode != "shadow" and env_mode != runtime_effective:
            drift_flags.append("env_runtime_collision")
        if runtime_effective and cross_mode not in {runtime_effective, "runtime_only", "unknown"}:
            drift_flags.append("cross_runtime_divergence")
        if cross_mode != "unknown" and cross_mode != effective_mode:
            drift_flags.append("cross_effective_divergence")
        collision_category = classify_collision(
            env_mode=env_mode,
            runtime_mode=runtime_mode,
            cross_mode=cross_mode,
            effective_mode=effective_mode,
            drift_flags=drift_flags,
        )

        rationale = (
            f"{source_of_truth} wins; env={env_mode}, runtime={runtime_mode}, cross={cross_mode}."
        )
        rows.append({
            "city": city,
            "env_declared_mode": env_mode,
            "env_source": env_source,
            "runtime_policy_mode": runtime_mode,
            "runtime_policy_source": runtime_source,
            "cross_policy_mode": cross_mode,
            "effective_mode": effective_mode,
            "source_of_truth": source_of_truth,
            "collision_flag": bool(collision_category),
            "drift_flags": drift_flags,
            "collision_category": collision_category,
            "rationale": rationale,
        })
    return rows, policy_state, manifest


def render_markdown(payload):
    summary = payload["summary"]
    lines = [
        "# Runtime Policy Effective View",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Runtime snapshot pulled_at: `{summary.get('runtime_snapshot_pulled_at') or 'unknown'}`",
        f"- Effective mode counts: `{summary['effective_mode_counts']}`",
        f"- Collision count: `{summary['collision_count']}`",
        f"- Collision category counts: `{summary['collision_category_counts']}`",
        f"- Blocking operational collisions: `{summary['blocking_operational_collision_count']}`",
        f"- Active effective count: `{summary['active_effective_count']}`",
        "",
        "## Contract",
        "",
        "`effective_mode` is the operational mode humans and tools should cite. Env lists and runtime auto policy are shown as inputs, not as standalone truth.",
        "",
        "Priority: manual blocked, auto blocked, auto shadow, manual active, auto canary, manual canary, default shadow.",
        "",
        "## Cities",
        "",
        "| City | Env | Runtime | Cross | Effective | Collision | Category | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["cities"]:
        flags = ",".join(row["drift_flags"]) or "-"
        category = row.get("collision_category") or "-"
        lines.append(
            f"| {row['city']} | {row['env_declared_mode']} | {row['runtime_policy_mode']} | "
            f"{row['cross_policy_mode']} | {row['effective_mode']} | {flags} | {category} | {row['source_of_truth']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    rows, policy_state, manifest = build_rows(args)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    summary = {
        "n_cities": len(rows),
        "effective_mode_counts": dict(Counter(row["effective_mode"] for row in rows)),
        "env_declared_mode_counts": dict(Counter(row["env_declared_mode"] for row in rows)),
        "runtime_policy_mode_counts": dict(Counter(row["runtime_policy_mode"] for row in rows)),
        "cross_policy_mode_counts": dict(Counter(row["cross_policy_mode"] for row in rows)),
        "collision_count": sum(1 for row in rows if row["collision_flag"]),
        "collision_category_counts": dict(Counter(row["collision_category"] for row in rows if row["collision_category"])),
        "blocking_operational_collision_count": sum(
            1 for row in rows if row.get("collision_category") == "blocking_operational_collision"
        ),
        "active_effective_count": sum(1 for row in rows if row["effective_mode"] == "active"),
        "runtime_snapshot_pulled_at": manifest.get("pulled_at") if isinstance(manifest, dict) else None,
        "city_policy_state_updated_at": policy_state.get("updated_at") if isinstance(policy_state, dict) else None,
    }
    payload = {
        "generated_at": now,
        "inputs": {
            "city_policy_state": args.city_policy_state,
            "runtime_manifest": args.runtime_manifest,
            "cross": args.cross,
            "active_cities": split_city_list(args.active_cities),
            "canary_cities": split_city_list(args.canary_cities),
            "blocked_cities": split_city_list(args.blocked_cities),
        },
        "summary": summary,
        "cities": rows,
    }

    json_path = Path(args.json_output)
    md_path = Path(args.md_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Runtime policy effective view written to {json_path}")
    print(f"Markdown summary written to {md_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
